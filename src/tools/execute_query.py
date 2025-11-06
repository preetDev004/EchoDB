"""Tool for executing read-only SQL queries."""
from sqlalchemy import text

from src.utils.db import ensure_engine, is_select_only, rows_to_dicts
from src.utils.format import format_rows


def execute_query(sql: str) -> str:
    """Execute a read-only SELECT SQL query and return formatted results.

    IMPORTANT FORMATTING INSTRUCTIONS FOR AI:
    When presenting query results to the user, you MUST follow these formatting rules:
    
    1. SINGLE RECORD (1 row): Present as plain text with key-value pairs, one per line.
       Example:
       name: John Doe
       email: john@example.com
       sales: $5000
    
    2. MULTIPLE RECORDS (2 or more rows): ALWAYS present as a markdown table.
       NEVER present multiple records as separate text blocks or lists.
       The results are already formatted as a markdown table - use them directly.
       Example format:
       | name | email | sales |
       |------|-------|-------|
       | John | john@example.com | $5000 |
       | Jane | jane@example.com | $4500 |
    
    3. When combining multiple queries (e.g., finding an actor and their films):
       - If the actor query returns 1 record: present as text
       - If the films query returns 2+ records: present as a table (ALWAYS)
       - Do NOT reformat the table results into text blocks
    
    Security: Only SELECT statements are allowed. Multiple statements are rejected.
    
    Returns:
        Formatted string - markdown table for 2+ rows, plain text for single row
    """
    if not is_select_only(sql):
        return "Error: Only single SELECT statements are allowed."

    try:
        engine = ensure_engine()
    except RuntimeError as e:
        return f"Connection Error: {e}"
    
    try:
        with engine.connect() as conn:
            # Best-effort read-only enforcement (supported DBs like Postgres)
            try:
                conn.execute(text("SET TRANSACTION READ ONLY"))
            except Exception:
                # Some dialects (e.g., SQLite) won't support this; rely on validation
                pass
            sql_to_run = sql.rstrip()
            if sql_to_run.endswith(";"):
                sql_to_run = sql_to_run[:-1].rstrip()
            result = conn.execute(text(sql_to_run))
            rows = rows_to_dicts(result)
        return format_rows(rows)
    except Exception as e:
        return f"Query Error: {e}"


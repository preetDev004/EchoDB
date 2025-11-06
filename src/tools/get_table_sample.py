"""Tool for retrieving sample data from database tables."""
from sqlalchemy import inspect, text

from src.utils.db import ensure_engine, rows_to_dicts
from src.utils.format import format_rows


def get_table_sample(table_name: str, limit: int = 10) -> str:
    """Return up to `limit` rows from the specified table.
    
    IMPORTANT FORMATTING INSTRUCTIONS FOR AI:
    When presenting table sample results to the user, you MUST follow these formatting rules:
    
    1. SINGLE RECORD (1 row): Present as plain text with key-value pairs, one per line.
       Example:
       id: 1
       name: Example Product
       price: $99.99
    
    2. MULTIPLE RECORDS (2 or more rows): ALWAYS present as a markdown table.
       NEVER present multiple records as separate text blocks, bullet points, or lists.
       The results are already formatted as a markdown table - use them directly without modification.
       Example format:
       | id | name | price |
       |----|------|-------|
       | 1  | Product A | $99.99 |
       | 2  | Product B | $149.99 |
    
    3. If you receive table-formatted results, preserve that format in your response.
       Do NOT convert table results into text blocks or other formats.
    
    Returns:
        Formatted string - markdown table for 2+ rows, plain text for single row
    """
    try:
        engine = ensure_engine()
    except RuntimeError as e:
        return f"Connection Error: {e}"
    
    try:
        inspector = inspect(engine)
        valid_tables = set(inspector.get_table_names())
        if table_name not in valid_tables:
            return f"Error: Unknown table: {table_name}"
        if limit <= 0:
            limit = 10
        quoted = inspect(engine).dialect.identifier_preparer.quote(table_name)
        query = text(f"SELECT * FROM {quoted} LIMIT :limit")
        with engine.connect() as conn:
            try:
                conn.execute(text("SET TRANSACTION READ ONLY"))
            except Exception:
                pass
            result = conn.execute(query, {"limit": limit})
            rows = rows_to_dicts(result)
        return format_rows(rows)
    except Exception as e:
        return f"Error: {e}"


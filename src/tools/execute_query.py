"""Tool for executing read-only SQL queries."""
from typing import Any, Dict

from sqlalchemy import text

from src.utils.db import ensure_engine, is_select_only, rows_to_dicts


def execute_query(sql: str) -> Dict[str, Any]:
    """
    Execute a read-only SELECT SQL query and return results.
    
    Returns: {"rows": [...]} - Array of row objects with column names as keys.
    Results should be displayed as a markdown table.
    
    Security: Only SELECT statements are allowed. Multiple statements are rejected.
    """
    if not is_select_only(sql):
        return {"error": "Only single SELECT statements are allowed."}

    engine = ensure_engine()
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
    return {"rows": rows}


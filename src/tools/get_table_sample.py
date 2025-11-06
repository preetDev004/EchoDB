"""Tool for retrieving sample data from database tables."""
from typing import Any, Dict

from sqlalchemy import inspect, text

from src.utils.db import ensure_engine, rows_to_dicts


def get_table_sample(table_name: str, limit: int = 10) -> Dict[str, Any]:
    """
    Get a sample of up to `limit` rows from the specified table.
    
    Returns: {"rows": [...]} - Array of row objects with column names as keys.
    Results should be displayed as a markdown table.
    """
    engine = ensure_engine()
    inspector = inspect(engine)
    valid_tables = set(inspector.get_table_names())
    if table_name not in valid_tables:
        return {"error": f"Unknown table: {table_name}"}
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
    return {"rows": rows}


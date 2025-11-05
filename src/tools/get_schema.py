"""Tool for retrieving database schema information."""
from typing import Any, Dict, List

from sqlalchemy import inspect

from src.utils.db import ensure_engine


def get_schema() -> Dict[str, Any]:
    """Return database schema: tables, columns, primary keys, foreign keys, indexes."""
    engine = ensure_engine()
    inspector = inspect(engine)
    schema: Dict[str, Any] = {"tables": []}

    for table_name in inspector.get_table_names():
        columns_info: List[Dict[str, Any]] = []
        for col in inspector.get_columns(table_name):
            columns_info.append(
                {
                    "name": col.get("name"),
                    "type": str(col.get("type")),
                    "nullable": bool(col.get("nullable")),
                    "default": str(col.get("default")) if col.get("default") is not None else None,
                }
            )

        pk = inspector.get_pk_constraint(table_name)
        fks = inspector.get_foreign_keys(table_name)
        try:
            indexes = inspector.get_indexes(table_name)
        except Exception:
            indexes = []

        schema["tables"].append(
            {
                "name": table_name,
                "columns": columns_info,
                "primary_key": pk.get("constrained_columns", []) if pk else [],
                "foreign_keys": [
                    {
                        "constrained_columns": fk.get("constrained_columns", []),
                        "referred_table": fk.get("referred_table"),
                        "referred_columns": fk.get("referred_columns", []),
                    }
                    for fk in (fks or [])
                ],
                "indexes": [
                    {
                        "name": idx.get("name"),
                        "unique": bool(idx.get("unique")),
                        "column_names": idx.get("column_names", []),
                    }
                    for idx in (indexes or [])
                ],
            }
        )

    return schema


import logging
import os
import re
from typing import Any, Dict, List

from mcp.server.fastmcp import FastMCP
from sqlalchemy import MetaData, create_engine, inspect, text
from sqlalchemy.engine import Engine, Result


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echodb")


mcp = FastMCP("echodb")

state: Dict[str, Any] = {
    "engine": None,  # type: ignore[assignment]
    "db_uri": None,
}

def _create_engine(db_uri: str) -> Engine:
    engine = create_engine(db_uri, pool_pre_ping=True, future=True)
    return engine


def _ensure_engine() -> Engine:
    engine: Engine | None = state.get("engine")
    if engine is not None:
        return engine
    env_uri = os.getenv("DATABASE_URI")
    if not env_uri:
        raise RuntimeError(
            "DATABASE_URI not set. Set it in the client config or call connect_database."
        )
    engine = _create_engine(env_uri)
    state["engine"] = engine
    state["db_uri"] = env_uri
    return engine


def _is_select_only(sql: str) -> bool:
    # Remove leading comments and whitespace
    stripped = re.sub(r"^\s*(--.*?$|/\*[\s\S]*?\*/)+", "", sql, flags=re.MULTILINE).strip()
    # Normalize optional trailing semicolon and whitespace
    if stripped.endswith(";"):
        stripped = stripped[:-1].rstrip()
    # Single statement, must start with SELECT (case-insensitive)
    if not re.match(r"^select\b", stripped, flags=re.IGNORECASE):
        return False
    # Disallow any remaining semicolons (would indicate multiple statements)
    return ";" not in stripped


def _rows_to_dicts(result: Result) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = [dict(row._mapping) for row in result]
    return rows


@mcp.tool()
def connect_database(uri: str) -> Dict[str, Any]:
    """Connect to a database using the provided SQLAlchemy URI.

    Accepts PostgreSQL/MySQL/SQLite URIs. Credentials in URI are never logged.
    """
    engine = _create_engine(uri)
    # Test connection
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    state["engine"] = engine
    state["db_uri"] = uri
    return {"status": "connected"}


@mcp.tool()
def get_schema() -> Dict[str, Any]:
    """Return database schema: tables, columns, primary keys, foreign keys, indexes."""
    engine = _ensure_engine()
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


@mcp.tool()
def execute_query(sql: str) -> Dict[str, Any]:
    """Execute a read-only SELECT SQL query and return rows as JSON.

    Security: Only SELECT statements are allowed. Multiple statements are rejected.
    """
    if not _is_select_only(sql):
        return {"error": "Only single SELECT statements are allowed."}

    engine = _ensure_engine()
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
        rows = _rows_to_dicts(result)
    return {"rows": rows}


@mcp.tool()
def get_table_sample(table_name: str, limit: int = 10) -> Dict[str, Any]:
    """Return up to `limit` rows from the specified table."""
    engine = _ensure_engine()
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
        rows = _rows_to_dicts(result)
    return {"rows": rows}


def main() -> None:
    # Bootstrap engine from env if provided to allow immediate use
    env_uri = os.getenv("DATABASE_URI")
    if env_uri:
        try:
            engine = _create_engine(env_uri)
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            state["engine"] = engine
            state["db_uri"] = env_uri
            logger.info("Connected using DATABASE_URI from environment.")
        except Exception as exc:
            logger.warning("Failed to preconnect using DATABASE_URI: %s", exc)

    mcp.run(transport='stdio')


if __name__ == "__main__":
    main()

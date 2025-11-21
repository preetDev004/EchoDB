"""Database connection and utility functions."""
import os
import re
from typing import Any, Dict, List

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.engine import Engine, Result


# Global state for database connection
state: Dict[str, Any] = {
    "engine": None,  # type: ignore[assignment]
    "db_uri": None,
}


def create_engine(db_uri: str) -> Engine:
    """Create a SQLAlchemy engine from a database URI."""
    engine = sa_create_engine(db_uri, pool_pre_ping=True)
    return engine


def ensure_engine() -> Engine:
    """Ensure a database engine is available, creating one if needed."""
    engine: Engine | None = get_state().get("engine")
    if engine is not None:
        return engine
    env_uri = os.getenv("DATABASE_URI")
    if not env_uri:
        raise RuntimeError(
            "DATABASE_URI not set. Set it in the client config or call connect_database."
        )
    engine = create_engine(env_uri)
    set_engine(engine, env_uri)
    return engine


def is_select_only(sql: str) -> bool:
    """Validate that SQL is a single SELECT statement only.
    
    Security: Only SELECT statements are allowed. Multiple statements are rejected.
    """
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


def rows_to_dicts(result: Result) -> List[Dict[str, Any]]:
    """Convert SQLAlchemy result rows to a list of dictionaries."""
    rows: List[Dict[str, Any]] = [dict(row._mapping) for row in result]
    return rows


def get_state() -> Dict[str, Any]:
    """Get the global database state."""
    return state


def set_engine(engine: Engine, db_uri: str) -> None:
    """Set the global database engine and URI."""
    state["engine"] = engine
    state["db_uri"] = db_uri


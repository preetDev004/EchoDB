"""Tool for connecting to a database."""
from typing import Any, Dict

from src.utils.db import create_engine, set_engine


def connect_database(uri: str) -> Dict[str, Any]:
    """Connect to a database using the provided SQLAlchemy URI.

    Accepts PostgreSQL/MySQL/SQLite URIs. Credentials in URI are never logged.
    """
    engine = create_engine(uri)
    # Test connection
    with engine.connect() as conn:
        conn.exec_driver_sql("SELECT 1")
    set_engine(engine, uri)
    return {"status": "connected"}


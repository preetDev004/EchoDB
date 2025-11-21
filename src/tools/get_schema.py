from langchain_core.tools import tool
from src.utils import db

def get_get_schema_tool(engine):
    @tool
    def get_schema() -> dict:
        """Get the database schema including tables, columns, types, primary keys, and foreign keys. Always call this first to understand the database structure."""
        return db.get_schema(engine)
    return get_schema

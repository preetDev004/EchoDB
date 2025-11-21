from langchain_core.tools import tool
from src.utils import db

def get_get_table_sample_tool(engine):
    @tool
    def get_table_sample(table_name: str, limit: int = 5) -> str:
        """Get a sample of rows from a specific table to understand the data format and content."""
        result, error = db.get_table_sample(engine, table_name, limit)
        if error:
            return f"Error: {error}"
        return result.to_markdown(index=False)
    return get_table_sample

from langchain_core.tools import tool
from src.utils import db

def get_execute_query_tool(engine):
    @tool
    def execute_query(query: str) -> str:
        """Execute a read-only SQL query (SELECT only). Use this to answer questions about the data."""
        result, error = db.run_query(engine, query)
        if error:
            return f"Error: {error}"
        return result.to_markdown(index=False)
    return execute_query

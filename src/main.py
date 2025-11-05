"""Main entry point for EchoDB MCP server."""
import logging
import os
import sys
from pathlib import Path

# Add project root to path to allow imports when running as script
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP

from src.tools import connect_database, execute_query, get_schema, get_table_sample
from src.utils.db import create_engine, get_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echodb")

mcp = FastMCP("echodb")

# Register all MCP tools
mcp.tool()(connect_database.connect_database)
mcp.tool()(get_schema.get_schema)
mcp.tool()(execute_query.execute_query)
mcp.tool()(get_table_sample.get_table_sample)


def main() -> None:
    # Bootstrap engine from env if provided to allow immediate use
    env_uri = os.getenv("DATABASE_URI")
    if env_uri:
        try:
            engine = create_engine(env_uri)
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            state = get_state()
            state["engine"] = engine
            state["db_uri"] = env_uri
            logger.info("Connected using DATABASE_URI from environment.")
        except Exception as exc:
            logger.warning("Failed to preconnect using DATABASE_URI: %s", exc)

    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

"""Main entry point for EchoDB MCP server."""

import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Add project root to path to allow imports when running as script
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP

from src.tools import connect_database, execute_query, get_schema, get_table_sample
from src.utils.db import create_engine, get_state
from src.prompts.formatting import FORMATTING_INSTRUCTIONS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echodb")

mcp = FastMCP("echodb", instructions=FORMATTING_INSTRUCTIONS)

# Register all MCP tools with clear descriptions
mcp.tool()(connect_database.connect_database)
mcp.tool()(get_schema.get_schema)
mcp.tool()(execute_query.execute_query)
mcp.tool()(get_table_sample.get_table_sample)


def main(transport: str = "stdio") -> None:
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

    logger.info(f"Running MCP server... using {transport} transport")
    mcp.run(transport=transport)


if __name__ == "__main__":
    main("stdio")

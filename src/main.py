"""Main entry point for EchoDB MCP server."""
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path to allow imports when running as script
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server.fastmcp import FastMCP

from src.prompts.handlers import get_prompt_handler, list_prompts_handler
from src.tools import connect_database, execute_query, get_schema, get_table_sample
from src.utils.db import create_engine, get_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echodb")

# ============================================================================
# MCP Server Setup
# ============================================================================

mcp = FastMCP("echodb")

# ============================================================================
# Register MCP Tools
# ============================================================================

mcp.tool()(connect_database.connect_database)
mcp.tool()(get_schema.get_schema)
mcp.tool()(execute_query.execute_query)
mcp.tool()(get_table_sample.get_table_sample)

# ============================================================================
# Register MCP Prompts
# ============================================================================

def _register_prompts() -> None:
    """Register prompt handlers with the MCP server."""
    try:
        # Access underlying server if FastMCP exposes it
        if hasattr(mcp, "_server"):
            server = mcp._server
            from mcp.types import PromptsCapability, ServerCapabilities, Capabilities
            
            # Set prompts capability
            if hasattr(server, "set_capabilities"):
                server.set_capabilities(
                    Capabilities(
                        server=ServerCapabilities(
                            prompts=PromptsCapability(listChanged=True)
                        )
                    )
                )
            
            # Register prompt handlers
            @server.list_prompts()
            async def async_list_prompts(cursor: str | None = None):
                return list_prompts_handler(cursor)
            
            @server.get_prompt()
            async def async_get_prompt(name: str, arguments: Dict[str, Any] | None = None):
                return get_prompt_handler(name, arguments)
            
            logger.info("Registered prompts via underlying MCP server")
            return
        
        # Try FastMCP's prompt registration if it exists
        if hasattr(mcp, "prompt"):
            mcp.prompt()(list_prompts_handler)
            mcp.prompt()(get_prompt_handler)
            logger.info("Registered prompts via FastMCP.prompt()")
            return
        
        # Fallback: log warning
        logger.warning(
            "FastMCP prompt registration not detected. "
            "Prompts may need to be registered manually. "
            "See src/main_prompts.py for alternative implementation."
        )
    except Exception as e:
        logger.warning(f"Could not register prompts: {e}")
        logger.info("Prompts functionality may not be available. See src/main_prompts.py for alternative.")


_register_prompts()


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> None:
    """Main entry point for the MCP server."""
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

    # Run the MCP server
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

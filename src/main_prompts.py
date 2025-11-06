"""Alternative implementation using standard MCP server for prompts support."""
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    Capabilities,
    ServerCapabilities,
    PromptsCapability,
)

from src.prompts.handlers import get_prompt, list_prompts
from src.tools import connect_database, execute_query, get_schema, get_table_sample
from src.utils.db import create_engine, get_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("echodb")

# Create MCP server with prompts capability
server = Server("echodb")

# Set capabilities including prompts
server.set_capabilities(
    Capabilities(
        server=ServerCapabilities(
            prompts=PromptsCapability(listChanged=True)
        )
    )
)


# Register tools
@server.list_tools()
async def handle_list_tools() -> list:
    """List available tools."""
    return [
        {
            "name": "connect_database",
            "description": connect_database.connect_database.__doc__,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "uri": {"type": "string", "description": "Database connection URI"}
                },
                "required": ["uri"]
            }
        },
        {
            "name": "get_schema",
            "description": get_schema.get_schema.__doc__,
            "inputSchema": {"type": "object", "properties": {}}
        },
        {
            "name": "execute_query",
            "description": execute_query.execute_query.__doc__,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {"type": "string", "description": "SQL SELECT query"}
                },
                "required": ["sql"]
            }
        },
        {
            "name": "get_table_sample",
            "description": get_table_sample.get_table_sample.__doc__,
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_name": {"type": "string"},
                    "limit": {"type": "integer", "default": 10}
                },
                "required": ["table_name"]
            }
        },
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list:
    """Handle tool calls."""
    if name == "connect_database":
        result = connect_database.connect_database(arguments["uri"])
        return [{"type": "text", "text": str(result)}]
    elif name == "get_schema":
        result = get_schema.get_schema()
        return [{"type": "text", "text": str(result)}]
    elif name == "execute_query":
        result = execute_query.execute_query(arguments["sql"])
        return [{"type": "text", "text": str(result)}]
    elif name == "get_table_sample":
        result = get_table_sample.get_table_sample(
            arguments["table_name"],
            arguments.get("limit", 10)
        )
        return [{"type": "text", "text": str(result)}]
    else:
        raise ValueError(f"Unknown tool: {name}")


# Register prompt handlers
@server.list_prompts()
async def handle_list_prompts(cursor: str | None = None) -> Dict[str, Any]:
    """List all available prompts."""
    prompts = list_prompts()
    return {
        "prompts": prompts,
        "nextCursor": None,
    }


@server.get_prompt()
async def handle_get_prompt(name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Get a specific prompt with arguments."""
    try:
        return get_prompt(name, arguments or {})
    except ValueError as e:
        raise ValueError(f"Invalid prompt request: {e}")
    except Exception as e:
        logger.error(f"Error getting prompt {name}: {e}", exc_info=True)
        raise


async def main() -> None:
    # Bootstrap engine from env if provided
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

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())


# EchoDB

Natural Language Database Interface via MCP (Model Context Protocol)

## Project Structure

```
EchoDB/
├── src/
│   ├── __init__.py
│   ├── main.py                 # MCP server entry point
│   ├── tools/                  # MCP tools directory
│   │   ├── __init__.py
│   │   ├── connect_database.py # Database connection tool
│   │   ├── get_schema.py       # Schema retrieval tool
│   │   ├── execute_query.py    # Query execution tool
│   │   └── get_table_sample.py # Table sampling tool
│   └── utils/                  # Utility modules
│       ├── __init__.py
│       └── db.py               # Database connection utilities
├── mcp_config.json             # MCP server configuration
├── pyproject.toml              # Project dependencies and metadata
├── uv.lock                     # Dependency lock file
├── PROJECT_PLAN.md             # Project planning document
└── README.md                   # This file
```

## Overview

EchoDB is an MCP server that provides natural language database querying capabilities. It exposes database operations as MCP tools that can be used by AI assistants like Claude Desktop.

### Core Components

- **`src/main.py`**: Entry point that initializes the MCP server and registers all tools
- **`src/tools/`**: Contains all MCP tools for database operations
- **`src/utils/db.py`**: Centralized database connection and utility functions

### MCP Tools

1. **`connect_database`**: Connect to a database using a SQLAlchemy URI
2. **`get_schema`**: Retrieve database schema (tables, columns, keys, indexes)
3. **`execute_query`**: Execute read-only SELECT queries
4. **`get_table_sample`**: Get sample rows from a table

## Installation

```bash
# Install dependencies using uv
uv sync
```

## Configuration

Configure the MCP server in your Claude Desktop `mcp_config.json`:

```json
{
  "mcpServers": {
    "echodb": {
      "command": "${uvcommand}",
      "args": [
        "run",
        "--directory",
        "/path/to/EchoDB",
        "src/main.py"
      ],
      "env": {
        "DATABASE_URI": "postgresql+psycopg2://user:pass@host:port/db"
      }
    }
  }
}
```

## Usage

Once configured, you can interact with your database through Claude Desktop using natural language queries. The AI will automatically:
- Connect to your database
- Understand the schema
- Generate and execute SQL queries
- Format and present results

## Features

- 🔒 **Secure**: Read-only queries, SQL injection protection
- 🗄️ **Multi-Database**: Supports PostgreSQL, MySQL, SQLite
- 🤖 **AI-Powered**: Natural language query interface
- 📊 **Schema-Aware**: Automatic schema introspection
- 🔍 **Safe**: Only SELECT statements allowed




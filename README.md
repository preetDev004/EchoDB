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
│   ├── prompts/                # LLM prompt configurations
│   │   ├── __init__.py
│   │   └── formatting.py       # Output formatting instructions
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
- **`src/prompts/`**: Contains instructions or system prompts for the Agent.
- **`src/utils/db.py`**: Centralized database connection and utility functions

### MCP Tools

1. **`connect_database`**: Connect to a database using a SQLAlchemy URI
2. **`get_schema`**: Retrieve database schema (tables, columns, keys, indexes)
3. **`execute_query`**: Execute read-only SELECT queries
4. **`get_table_sample`**: Get sample rows from a table

## Installation

### Prerequisites
- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) package manager
- A supported database (PostgreSQL, MySQL, or SQLite)

### Setup

```bash
# Clone the repository
git clone https://github.com/preetDev004/EchoDB.git
cd EchoDB

# Install dependencies using uv
uv sync
```

## Configuration

### Claude Desktop Setup

1. Locate your Claude Desktop configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Add the EchoDB server configuration:

```json
{
  "mcpServers": {
    "echodb": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "/absolute/path/to/EchoDB",
        "src/main.py"
      ],
      "env": {
        "DATABASE_URI": "postgresql+psycopg2://user:password@host:port/database"
      }
    }
  }
}
```

3. Replace `/absolute/path/to/EchoDB` with the actual path to your EchoDB directory

4. Update the `DATABASE_URI` with your database connection string:
   - **PostgreSQL**: `postgresql+psycopg2://user:password@host:port/database`
   - **MySQL**: `mysql+pymysql://user:password@host:port/database`
   - **SQLite**: `sqlite:///path/to/database.db`

5. Restart Claude Desktop for changes to take effect

### Environment Variables

Alternatively, you can set the database URI as an environment variable:

```bash
export DATABASE_URI="postgresql+psycopg2://user:password@host:port/database"
```

Or use a `.env` file in the project root:

```
DATABASE_URI=postgresql+psycopg2://user:password@host:port/database
```

## Usage

Once configured, you can interact with your database through Claude Desktop using natural language queries. The AI will automatically:
- Connect to your database
- Understand the schema
- Generate and execute SQL queries
- Format and present results

### Example Queries

```
"Show me all tables in the database"
"What are the top 10 customers by revenue?"
"Give me a sample of 5 rows from the users table"
"How many orders were placed last month?"
"Show the schema for the products table"
```

### Output Formatting

EchoDB automatically formats query results as markdown tables with:
- Proper column alignment
- Number formatting with commas
- Date formatting (YYYY-MM-DD)
- Brief insights and analysis after each result

## Features

- 🔒 **Secure**: Read-only queries, SQL injection protection
- 🗄️ **Multi-Database**: Supports PostgreSQL, MySQL, SQLite
- 🤖 **AI-Powered**: Natural language query interface
- 📊 **Schema-Aware**: Automatic schema introspection
- 🔍 **Safe**: Only SELECT statements allowed
- 📋 **Smart Formatting**: Automatic markdown table generation with insights
- 🔌 **MCP Protocol**: Native integration with Claude Desktop
- ⚡ **Fast**: Direct SQLAlchemy connections with connection pooling

## Dependencies

- **mcp[cli]**: Model Context Protocol server implementation
- **SQLAlchemy>=2.0**: Universal database adapter
- **pydantic>=2.7**: Data validation and schema management
- **psycopg2-binary>=2.9.11**: PostgreSQL driver
- **pymysql>=1.1.2**: MySQL driver
- **python-dotenv>=1.2.1**: Environment variable management

## Security Notes

- **Read-Only**: EchoDB only executes SELECT queries. INSERT, UPDATE, DELETE, and other write operations are blocked.
- **SQL Injection Protection**: Uses SQLAlchemy's parameterized queries and text() with proper escaping.
- **Connection Security**: Database credentials are stored securely in environment variables or Claude Desktop config.

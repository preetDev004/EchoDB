import sqlalchemy
from sqlalchemy import create_engine, inspect, text
import pandas as pd
import re

MAX_ROWS = 100

def get_db_connection(uri):
    """Establishes and tests a database connection."""
    try:
        engine = create_engine(uri)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine, None
    except Exception as e:
        return None, str(e)

def get_schema(engine):
    """Retrieves the database schema in a structured JSON-like format."""
    inspector = inspect(engine)
    schema_info = {}
    
    for table_name in inspector.get_table_names():
        columns = []
        for col in inspector.get_columns(table_name):
            columns.append({
                "name": col["name"],
                "type": str(col["type"]),
                "primary_key": col.get("primary_key", False),
                "nullable": col.get("nullable", True),
                "default": str(col.get("default")) if col.get("default") else None
            })
        
        pk_constraint = inspector.get_pk_constraint(table_name)
        pks = pk_constraint.get('constrained_columns', []) if pk_constraint else []
        
        fks = []
        for fk in inspector.get_foreign_keys(table_name):
            fks.append({
                "constrained_columns": fk["constrained_columns"],
                "referred_table": fk["referred_table"],
                "referred_columns": fk["referred_columns"]
            })
            
        indexes = []
        for idx in inspector.get_indexes(table_name):
            indexes.append({
                "name": idx["name"],
                "column_names": idx["column_names"],
                "unique": idx["unique"]
            })

        schema_info[table_name] = {
            "columns": columns,
            "primary_keys": pks,
            "foreign_keys": fks,
            "indexes": indexes
        }
        
    return schema_info

def is_select_only(query):
    """Validates that the query is a read-only SELECT statement."""
    query = query.strip().lower()
    
    # Basic keyword check
    forbidden_keywords = ['insert', 'update', 'delete', 'drop', 'alter', 'create', 'truncate', 'grant', 'revoke']
    for keyword in forbidden_keywords:
        # Check for keyword boundaries to avoid matching substrings (e.g. "update" in "last_update")
        if re.search(r'\b' + keyword + r'\b', query):
            return False, f"Forbidden keyword detected: {keyword}"
            
    # Must start with SELECT or WITH (for CTEs)
    if not (query.startswith('select') or query.startswith('with')):
        return False, "Query must start with SELECT or WITH"
        
    return True, ""

def run_query(engine, query):
    """Executes a read-only SQL query."""
    is_valid, error_msg = is_select_only(query)
    if not is_valid:
        return None, f"Error: {error_msg}"
        
    try:
        with engine.connect() as conn:
            # Attempt to set read-only transaction if supported
            if engine.dialect.name in ['postgresql', 'mysql']:
                conn.execution_options(isolation_level="READ COMMITTED", readonly=True)
            
            result = conn.execute(text(query))
            df = pd.DataFrame(result.fetchall(), columns=result.keys())
            
            if len(df) > MAX_ROWS:
                df = df.head(MAX_ROWS)
                return df, f"Note: Result truncated to {MAX_ROWS} rows."
            
            return df, None
    except Exception as e:
        return None, str(e)

def get_table_sample(engine, table_name, limit=5):
    """Fetches a sample of rows from a table."""
    query = f"SELECT * FROM {table_name} LIMIT {limit}"
    return run_query(engine, query)

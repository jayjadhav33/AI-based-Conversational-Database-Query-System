import time
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import SQLAlchemyError

# In-memory cache: key -> (timestamp, schema)
_SCHEMA_CACHE = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

def extract_schema(host: str, port: int, user: str, password: str, database: str, force_refresh: bool = False):
    """
    Connects to the given MySQL database and extracts its schema 
    including tables, columns, primary keys, and foreign keys.
    Results are cached in memory to speed up AI query response times.
    """
    cache_key = f"{host}:{port}:{user}:{database}"
    current_time = time.time()
    
    if not force_refresh and cache_key in _SCHEMA_CACHE:
        cached_time, cached_schema = _SCHEMA_CACHE[cache_key]
        if current_time - cached_time < _CACHE_TTL_SECONDS:
            return True, cached_schema

    conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        engine = create_engine(conn_str, connect_args={"connect_timeout": 5})
        inspector = inspect(engine)
        
        schema = []
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            pk = inspector.get_pk_constraint(table_name)
            fks = inspector.get_foreign_keys(table_name)
            
            table_info = {
                "table_name": table_name,
                "columns": [{"name": c["name"], "type": str(c["type"])} for c in columns],
                "primary_keys": pk.get("constrained_columns", []),
                "foreign_keys": [
                    {
                        "constrained_columns": fk["constrained_columns"], 
                        "referred_table": fk["referred_table"], 
                        "referred_columns": fk["referred_columns"]
                    } for fk in fks
                ]
            }
            schema.append(table_info)
            
        _SCHEMA_CACHE[cache_key] = (current_time, schema)
        return True, schema
    except SQLAlchemyError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)


from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from app.services.sql_validator import validate_sql

def execute_safe_query(host: str, port: int, user: str, password: str, database: str, sql_query: str):
    """
    Validates and executes a SQL query on the target database, returning the results.
    """
    # 1. Validate SQL
    is_safe, msg = validate_sql(sql_query)
    if not is_safe:
        return False, msg, None

    # 2. Execute SQL
    conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        engine = create_engine(conn_str, connect_args={"connect_timeout": 5})
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            
            # Fetch column names
            keys = list(result.keys())
            
            # Fetch rows
            rows = [dict(zip(keys, row)) for row in result.fetchall()]
            
            return True, "Success", {"columns": keys, "rows": rows}
    except SQLAlchemyError as e:
        return False, f"Database Error: {str(e)}", None
    except Exception as e:
        return False, f"Execution Error: {str(e)}", None

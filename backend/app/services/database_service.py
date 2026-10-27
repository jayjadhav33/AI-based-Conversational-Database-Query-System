from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

def test_mysql_connection(host: str, port: int, user: str, password: str, database: str):
    """
    Tests the connection to a MySQL database.
    Returns True if successful, raises an exception otherwise.
    """
    # Create connection string
    conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        engine = create_engine(conn_str, connect_args={"connect_timeout": 5})
        connection = engine.connect()
        connection.close()
        return True, "Connection successful"
    except SQLAlchemyError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

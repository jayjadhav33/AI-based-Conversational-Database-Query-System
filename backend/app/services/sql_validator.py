import sqlparse

def validate_sql(sql_query: str) -> tuple[bool, str]:
    """
    Validates that a SQL query is strictly read-only (SELECT).
    Blocks multiple statements and any modifying commands.
    """
    if not sql_query or not sql_query.strip():
        return False, "Query cannot be empty."

    # Parse the SQL string
    parsed = sqlparse.parse(sql_query)
    
    if not parsed:
        return False, "Failed to parse SQL."
        
    # Prevent multiple statements (e.g., SELECT * FROM t; DROP TABLE t)
    # sqlparse.parse returns a list of statements. Some might be empty whitespace statements.
    real_statements = [stmt for stmt in parsed if stmt.get_type() != 'UNKNOWN' and stmt.tokens]
    
    if len(real_statements) > 1:
        return False, "Multiple SQL statements are not allowed for security reasons."
        
    if not real_statements:
        return False, "No valid SQL statement found."

    statement = real_statements[0]
    command_type = statement.get_type()

    if command_type.upper() != 'SELECT':
        return False, f"Only SELECT queries are allowed. Disallowed command: {command_type}"

    return True, "Query is safe."

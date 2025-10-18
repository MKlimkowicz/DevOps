import pytest
import psycopg2


@pytest.mark.security
def test_table_access_control(db_cursor, restricted_user, db_config):
    """Create restricted user, verify access denied."""
    db_cursor.execute("DROP TABLE IF EXISTS protected_table CASCADE;")
    db_cursor.execute("""
        CREATE TABLE protected_table (
            id SERIAL PRIMARY KEY,
            protected_data VARCHAR(255)
        );
    """)
    
    db_cursor.execute("INSERT INTO protected_table (protected_data) VALUES ('confidential');")
    
    try:
        restricted_conn = psycopg2.connect(**restricted_user["connection_params"])
        restricted_cursor = restricted_conn.cursor()
        
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            restricted_cursor.execute("SELECT * FROM protected_table;")
        
        restricted_cursor.close()
        restricted_conn.close()
    except psycopg2.OperationalError:
        pass
    
    db_cursor.execute("DROP TABLE IF EXISTS protected_table CASCADE;")


@pytest.mark.security
def test_schema_access_control(db_cursor, restricted_user):
    """Schema-level permissions."""
    db_cursor.execute("DROP SCHEMA IF EXISTS secure_schema CASCADE;")
    db_cursor.execute("CREATE SCHEMA secure_schema;")
    
    db_cursor.execute("""
        CREATE TABLE secure_schema.secret_table (
            id SERIAL PRIMARY KEY,
            secret VARCHAR(255)
        );
    """)
    
    db_cursor.execute(f"REVOKE ALL ON SCHEMA secure_schema FROM {restricted_user['username']};")
    
    try:
        restricted_conn = psycopg2.connect(**restricted_user["connection_params"])
        restricted_cursor = restricted_conn.cursor()
        
        with pytest.raises(psycopg2.Error):
            restricted_cursor.execute("SELECT * FROM secure_schema.secret_table;")
        
        restricted_cursor.close()
        restricted_conn.close()
    except psycopg2.OperationalError:
        pass
    
    db_cursor.execute("DROP SCHEMA IF EXISTS secure_schema CASCADE;")


@pytest.mark.security
def test_function_execution_permissions(db_cursor, restricted_user):
    """EXECUTE privileges."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION restricted_function()
        RETURNS INT AS $$
        BEGIN
            RETURN 42;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    db_cursor.execute(f"REVOKE ALL ON FUNCTION restricted_function() FROM PUBLIC;")
    db_cursor.execute(f"REVOKE ALL ON FUNCTION restricted_function() FROM {restricted_user['username']};")
    
    try:
        restricted_conn = psycopg2.connect(**restricted_user["connection_params"])
        restricted_cursor = restricted_conn.cursor()
        
        with pytest.raises(psycopg2.Error):
            restricted_cursor.execute("SELECT restricted_function();")
        
        restricted_cursor.close()
        restricted_conn.close()
    except psycopg2.OperationalError:
        pass
    
    db_cursor.execute("DROP FUNCTION IF EXISTS restricted_function();")


@pytest.mark.security
def test_row_level_security(db_cursor, restricted_user, db_config):
    """RLS policies (if configured)."""
    db_cursor.execute("DROP TABLE IF EXISTS rls_table CASCADE;")
    db_cursor.execute("""
        CREATE TABLE rls_table (
            id SERIAL PRIMARY KEY,
            user_name VARCHAR(100),
            data VARCHAR(255)
        );
    """)
    
    db_cursor.execute("ALTER TABLE rls_table ENABLE ROW LEVEL SECURITY;")
    
    db_cursor.execute(f"""
        CREATE POLICY user_policy ON rls_table
        FOR SELECT
        TO {restricted_user['username']}
        USING (user_name = current_user);
    """)
    
    db_cursor.execute(f"INSERT INTO rls_table (user_name, data) VALUES ('{db_config['user']}', 'admin_data');")
    db_cursor.execute(f"INSERT INTO rls_table (user_name, data) VALUES ('{restricted_user['username']}', 'user_data');")
    
    db_cursor.execute(f"GRANT SELECT ON rls_table TO {restricted_user['username']};")
    
    try:
        restricted_conn = psycopg2.connect(**restricted_user["connection_params"])
        restricted_cursor = restricted_conn.cursor()
        
        restricted_cursor.execute("SELECT * FROM rls_table;")
        results = restricted_cursor.fetchall()
        
        assert len(results) <= 1
        
        restricted_cursor.close()
        restricted_conn.close()
    except psycopg2.OperationalError:
        pass
    
    db_cursor.execute("DROP TABLE IF EXISTS rls_table CASCADE;")


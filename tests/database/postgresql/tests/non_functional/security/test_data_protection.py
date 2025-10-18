import pytest
import psycopg2


@pytest.mark.security
def test_sensitive_data_exposure(db_cursor, benchmark_table):
    """Verify sensitive data handling."""
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (9001, "sensitive_user", "sensitive@test.com", 100.0, True))
    
    db_cursor.execute(f"""
        SELECT username, email FROM {benchmark_table} WHERE user_id = 9001;
    """)
    result = db_cursor.fetchone()
    
    assert result['username'] == "sensitive_user"
    assert result['email'] == "sensitive@test.com"


@pytest.mark.security
def test_password_storage(db_cursor):
    """Encrypted password storage patterns."""
    db_cursor.execute("DROP TABLE IF EXISTS user_credentials CASCADE;")
    db_cursor.execute("""
        CREATE TABLE user_credentials (
            id SERIAL PRIMARY KEY,
            username VARCHAR(100) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL
        );
    """)
    
    plaintext_password = "MySecurePassword123!"
    
    db_cursor.execute("""
        INSERT INTO user_credentials (username, password_hash)
        VALUES (%s, crypt(%s, gen_salt('bf')));
    """, ("test_user_crypt", plaintext_password))
    
    db_cursor.execute("""
        SELECT (password_hash = crypt(%s, password_hash)) AS password_match
        FROM user_credentials
        WHERE username = %s;
    """, (plaintext_password, "test_user_crypt"))
    
    result = db_cursor.fetchone()
    assert result['password_match'] is True
    
    db_cursor.execute("""
        SELECT (password_hash = crypt(%s, password_hash)) AS password_match
        FROM user_credentials
        WHERE username = %s;
    """, ("WrongPassword", "test_user_crypt"))
    
    result_wrong = db_cursor.fetchone()
    assert result_wrong['password_match'] is False
    
    db_cursor.execute("DROP TABLE IF EXISTS user_credentials CASCADE;")


@pytest.mark.security
def test_audit_logging(db_cursor):
    """Log security-relevant operations."""
    db_cursor.execute("DROP TABLE IF EXISTS security_audit_log CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS sensitive_data CASCADE;")
    
    db_cursor.execute("""
        CREATE TABLE sensitive_data (
            id SERIAL PRIMARY KEY,
            data VARCHAR(255)
        );
    """)
    
    db_cursor.execute("""
        CREATE TABLE security_audit_log (
            id SERIAL PRIMARY KEY,
            table_name VARCHAR(100),
            operation VARCHAR(50),
            user_name VARCHAR(100),
            timestamp TIMESTAMP DEFAULT NOW()
        );
    """)
    
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION audit_security_func()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO security_audit_log (table_name, operation, user_name)
            VALUES (TG_TABLE_NAME, TG_OP, current_user);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    db_cursor.execute("""
        CREATE TRIGGER security_audit_trigger
        AFTER INSERT OR UPDATE OR DELETE ON sensitive_data
        FOR EACH ROW EXECUTE FUNCTION audit_security_func();
    """)
    
    db_cursor.execute("INSERT INTO sensitive_data (data) VALUES ('secret1');")
    db_cursor.execute("UPDATE sensitive_data SET data = 'secret2' WHERE id = 1;")
    
    db_cursor.execute("SELECT COUNT(*) FROM security_audit_log;")
    log_count = db_cursor.fetchone()['count']
    assert log_count >= 2
    
    db_cursor.execute("DROP TABLE IF EXISTS security_audit_log CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS sensitive_data CASCADE;")
    db_cursor.execute("DROP FUNCTION IF EXISTS audit_security_func CASCADE;")


@pytest.mark.security
def test_prepared_statement_security(db_cursor, benchmark_table):
    """Prepared statements vs string concat."""
    malicious_input = "'; DROP TABLE benchmark_table; --"
    
    db_cursor.execute(f"""
        PREPARE safe_insert AS
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES ($1, $2, $3, $4, $5);
    """)
    
    db_cursor.execute("EXECUTE safe_insert(9002, %s, 'safe@test.com', 50.0, true);", (malicious_input,))
    
    db_cursor.execute(f"""
        SELECT username FROM {benchmark_table} WHERE user_id = 9002;
    """)
    result = db_cursor.fetchone()
    assert result['username'] == malicious_input
    
    db_cursor.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '{benchmark_table}'
        );
    """)
    table_exists = db_cursor.fetchone()[0]
    assert table_exists is True
    
    db_cursor.execute("DEALLOCATE safe_insert;")


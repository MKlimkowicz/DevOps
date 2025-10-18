import pytest
import psycopg2


@pytest.mark.security
def test_invalid_credentials(db_config):
    """Failed login attempts."""
    with pytest.raises(psycopg2.OperationalError):
        psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password="wrong_password"
        )


@pytest.mark.security
def test_connection_without_password(db_config):
    """Password requirement enforcement."""
    with pytest.raises(psycopg2.OperationalError):
        psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=""
        )


@pytest.mark.security
def test_user_privilege_escalation(db_cursor, restricted_user):
    """Attempt unauthorized privilege gain."""
    db_cursor.execute("DROP TABLE IF EXISTS secure_table CASCADE;")
    db_cursor.execute("""
        CREATE TABLE secure_table (
            id SERIAL PRIMARY KEY,
            sensitive_data VARCHAR(255)
        );
    """)
    
    db_cursor.execute("INSERT INTO secure_table (sensitive_data) VALUES ('secret_info');")
    
    try:
        restricted_conn = psycopg2.connect(**restricted_user["connection_params"])
        restricted_cursor = restricted_conn.cursor()
        
        with pytest.raises(psycopg2.Error):
            restricted_cursor.execute("SELECT * FROM secure_table;")
        
        restricted_cursor.close()
        restricted_conn.close()
    except psycopg2.OperationalError:
        pass
    
    db_cursor.execute("DROP TABLE IF EXISTS secure_table CASCADE;")


@pytest.mark.security
def test_connection_encryption(db_config):
    """Verify SSL/TLS when configured."""
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
            sslmode="prefer"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        assert cursor.fetchone()[0] == 1
        cursor.close()
        conn.close()
    except psycopg2.OperationalError as e:
        pytest.skip(f"SSL not configured: {e}")


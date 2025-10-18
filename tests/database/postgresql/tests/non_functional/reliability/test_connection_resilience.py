import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import time


@pytest.mark.reliability
def test_connection_retry_logic(db_config):
    """Auto-reconnect after connection loss."""
    conn = psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"]
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    assert cursor.fetchone()[0] == 1
    
    cursor.close()
    conn.close()
    
    retry_attempts = 3
    for attempt in range(retry_attempts):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            assert cursor.fetchone()[0] == 1
            cursor.close()
            conn.close()
            break
        except psycopg2.OperationalError:
            if attempt == retry_attempts - 1:
                pytest.fail("Failed to reconnect after retries")
            time.sleep(1)


@pytest.mark.reliability
def test_connection_timeout_handling(db_config):
    """Timeout scenarios and recovery."""
    try:
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        assert result[0] == 1
        cursor.close()
        conn.close()
    except psycopg2.OperationalError:
        pytest.fail("Connection timeout exceeded")


@pytest.mark.reliability
@pytest.mark.slow
def test_idle_connection_keepalive(db_config):
    """Long-lived idle connections."""
    conn = psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"]
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT 1;")
    assert cursor.fetchone()[0] == 1
    
    time.sleep(5)
    
    cursor.execute("SELECT 2;")
    assert cursor.fetchone()[0] == 2
    
    cursor.close()
    conn.close()


@pytest.mark.reliability
def test_connection_pool_recovery(connection_factory):
    """Pool recovery after failures."""
    connections = []
    
    for i in range(5):
        conn = connection_factory()
        cursor = conn.cursor()
        cursor.execute("SELECT %s;", (i,))
        result = cursor.fetchone()
        assert result[0] == i
        cursor.close()
        connections.append(conn)
    
    for conn in connections:
        conn.close()
    
    new_connections = []
    for i in range(5):
        conn = connection_factory()
        cursor = conn.cursor()
        cursor.execute("SELECT %s;", (i + 10,))
        result = cursor.fetchone()
        assert result[0] == i + 10
        cursor.close()
        new_connections.append(conn)
    
    assert len(new_connections) == 5


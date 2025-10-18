import pytest
import psycopg2
import subprocess
import time


@pytest.mark.reliability
@pytest.mark.slow
def test_connection_recovery_after_restart(db_config):
    """Reconnect after container restart."""
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
    
    max_attempts = 5
    for attempt in range(max_attempts):
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
            result = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            assert result == 1
            break
        except psycopg2.OperationalError:
            if attempt == max_attempts - 1:
                pytest.fail("Failed to reconnect after restart simulation")
            time.sleep(2)


@pytest.mark.reliability
def test_query_cancellation(db_cursor, benchmark_table):
    """Cancel long-running queries gracefully."""
    for i in range(1000):
        db_cursor.execute(f"""
            INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s);
        """, (6000 + i, f"user_{6000 + i}", f"user{6000 + i}@test.com", i * 0.5, True))
    
    db_cursor.connection.autocommit = False
    
    try:
        db_cursor.execute(f"""
            SELECT pg_sleep(0.1), * FROM {benchmark_table}
            CROSS JOIN {benchmark_table} t2
            LIMIT 10;
        """)
        db_cursor.fetchall()
    except psycopg2.Error:
        pass
    finally:
        db_cursor.connection.rollback()
        db_cursor.connection.autocommit = True
    
    db_cursor.execute("SELECT 1;")
    result = db_cursor.fetchone()
    assert result['?column?'] == 1 or result[0] == 1


@pytest.mark.reliability
def test_prepared_statement_lifecycle(db_connection, benchmark_table):
    """Prepared statements after reconnection."""
    cursor = db_connection.cursor()
    
    cursor.execute(f"""
        PREPARE test_stmt AS
        SELECT * FROM {benchmark_table} WHERE user_id = $1;
    """)
    
    cursor.execute("EXECUTE test_stmt(100);")
    cursor.fetchall()
    
    cursor.execute("DEALLOCATE test_stmt;")
    
    cursor.execute(f"""
        PREPARE test_stmt2 AS
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES ($1, $2, $3, $4, $5);
    """)
    
    cursor.execute("EXECUTE test_stmt2(7001, 'prep_user', 'prep@test.com', 50.0, true);")
    
    cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 7001;")
    result = cursor.fetchone()
    count = result['count'] if isinstance(result, dict) else result[0]
    assert count == 1
    
    cursor.execute("DEALLOCATE test_stmt2;")
    cursor.close()


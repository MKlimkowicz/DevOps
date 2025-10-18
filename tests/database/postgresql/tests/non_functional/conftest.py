import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from faker import Faker
import threading
import os

fake = Faker()


@pytest.fixture
def performance_cursor(db_connection):
    """Cursor that tracks query execution time."""
    cursor = db_connection.cursor()
    cursor.execution_times = []
    
    original_execute = cursor.execute
    
    def timed_execute(*args, **kwargs):
        start = time.perf_counter()
        result = original_execute(*args, **kwargs)
        end = time.perf_counter()
        cursor.execution_times.append(end - start)
        return result
    
    cursor.execute = timed_execute
    
    try:
        yield cursor
    finally:
        cursor.close()


@pytest.fixture(scope="function")
def benchmark_table(db_cursor):
    """Standardized table for performance comparisons."""
    table_name = "benchmark_table"
    
    try:
        db_cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
    except Exception:
        pass
    
    db_cursor.execute(f"""
        CREATE TABLE {table_name} (
            id SERIAL PRIMARY KEY,
            user_id INT,
            username VARCHAR(255),
            email VARCHAR(255),
            score DOUBLE PRECISION,
            created_at TIMESTAMP,
            is_active BOOLEAN,
            metadata JSONB
        );
    """)
    
    yield table_name
    
    try:
        db_cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
    except Exception:
        pass


@pytest.fixture
def large_dataset(db_cursor, benchmark_table):
    """Pre-populated table with 10K rows for testing."""
    records = []
    for i in range(10000):
        records.append((
            i % 1000,
            fake.user_name(),
            fake.email(),
            fake.pyfloat(min_value=0, max_value=1000, right_digits=2),
            fake.date_time_this_year(),
            fake.boolean(),
            psycopg2.extras.Json({"key": f"value_{i}", "index": i})
        ))
    
    insert_sql = f"""
        INSERT INTO {benchmark_table} 
        (user_id, username, email, score, created_at, is_active, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    
    for record in records:
        db_cursor.execute(insert_sql, record)
    
    yield benchmark_table


@pytest.fixture
def concurrent_connections(db_config):
    """Pool of database connections for load tests."""
    connections = []
    
    def create_connection():
        return psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
            cursor_factory=RealDictCursor
        )
    
    for _ in range(10):
        try:
            conn = create_connection()
            conn.autocommit = True
            connections.append(conn)
        except Exception:
            pass
    
    yield connections
    
    for conn in connections:
        try:
            conn.close()
        except Exception:
            pass


@pytest.fixture(scope="function")
def restricted_user(db_cursor, db_config):
    """Low-privilege database user for security tests."""
    username = "test_restricted_user"
    password = "test_password_123"
    
    try:
        db_cursor.execute(f"DROP USER IF EXISTS {username};")
    except Exception:
        pass
    
    db_cursor.execute(f"CREATE USER {username} WITH PASSWORD '{password}';")
    db_cursor.execute(f"REVOKE ALL PRIVILEGES ON DATABASE {db_config['database']} FROM {username};")
    
    user_info = {
        "username": username,
        "password": password,
        "connection_params": {
            "host": db_config["host"],
            "port": db_config["port"],
            "database": db_config["database"],
            "user": username,
            "password": password
        }
    }
    
    yield user_info
    
    try:
        db_cursor.execute(f"DROP USER IF EXISTS {username};")
    except Exception:
        pass


@pytest.fixture
def connection_factory(db_config):
    """Factory function for creating new database connections."""
    created_connections = []
    
    def factory():
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"],
            cursor_factory=RealDictCursor
        )
        created_connections.append(conn)
        return conn
    
    yield factory
    
    for conn in created_connections:
        try:
            conn.close()
        except Exception:
            pass


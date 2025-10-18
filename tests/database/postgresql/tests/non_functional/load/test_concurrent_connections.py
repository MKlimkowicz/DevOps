import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time


@pytest.mark.load
@pytest.mark.slow
def test_max_concurrent_connections(db_config):
    """Test up to 100 simultaneous connections."""
    connections = []
    errors = []
    
    def create_connection(conn_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"],
                cursor_factory=RealDictCursor
            )
            connections.append(conn)
        except Exception as e:
            errors.append((conn_id, str(e)))
    
    threads = []
    for i in range(100):
        thread = threading.Thread(target=create_connection, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    assert len(connections) > 50
    
    for conn in connections:
        try:
            conn.close()
        except Exception:
            pass


@pytest.mark.load
def test_connection_pool_exhaustion(concurrent_connections, db_cursor):
    """Verify behavior at pool limits."""
    active_cursors = []
    
    for conn in concurrent_connections:
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT 1;")
            cursor.fetchone()
            active_cursors.append(cursor)
        except Exception as e:
            pytest.fail(f"Connection pool exhausted: {e}")
    
    assert len(active_cursors) == len(concurrent_connections)
    
    for cursor in active_cursors:
        cursor.close()


@pytest.mark.load
@pytest.mark.slow
def test_concurrent_reads(db_config, large_dataset):
    """50+ threads reading simultaneously."""
    results = []
    errors = []
    
    def read_operation(thread_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"],
                cursor_factory=RealDictCursor
            )
            cursor = conn.cursor()
            
            for _ in range(10):
                cursor.execute(f"SELECT * FROM {large_dataset} WHERE user_id = %s;", (thread_id % 100,))
                cursor.fetchall()
            
            results.append(thread_id)
            cursor.close()
            conn.close()
        except Exception as e:
            errors.append((thread_id, str(e)))
    
    threads = []
    for i in range(50):
        thread = threading.Thread(target=read_operation, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    assert len(results) >= 45
    assert len(errors) < 5


@pytest.mark.load
@pytest.mark.slow
def test_concurrent_writes(db_config, benchmark_table):
    """Multiple writers with lock contention."""
    results = []
    errors = []
    
    def write_operation(thread_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"],
                cursor_factory=RealDictCursor
            )
            conn.autocommit = True
            cursor = conn.cursor()
            
            for i in range(20):
                cursor.execute(f"""
                    INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
                    VALUES (%s, %s, %s, %s, %s);
                """, (thread_id, f"user_{thread_id}_{i}", f"email{thread_id}_{i}@test.com", i * 1.5, True))
            
            results.append(thread_id)
            cursor.close()
            conn.close()
        except Exception as e:
            errors.append((thread_id, str(e)))
    
    threads = []
    for i in range(20):
        thread = threading.Thread(target=write_operation, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    assert len(results) >= 18
    assert len(errors) < 2


@pytest.mark.load
@pytest.mark.slow
def test_mixed_workload(db_config, large_dataset):
    """Concurrent reads/writes/updates (70/20/10 ratio)."""
    operations = []
    errors = []
    
    def read_op(thread_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {large_dataset} LIMIT 100;")
            cursor.fetchall()
            operations.append(('read', thread_id))
            cursor.close()
            conn.close()
        except Exception as e:
            errors.append(('read', thread_id, str(e)))
    
    def write_op(thread_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT INTO {large_dataset} (user_id, username, email, score, is_active)
                VALUES (%s, %s, %s, %s, %s);
            """, (thread_id, f"user_{thread_id}", f"email{thread_id}@test.com", 100.0, True))
            operations.append(('write', thread_id))
            cursor.close()
            conn.close()
        except Exception as e:
            errors.append(('write', thread_id, str(e)))
    
    def update_op(thread_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            conn.autocommit = True
            cursor = conn.cursor()
            cursor.execute(f"UPDATE {large_dataset} SET score = score + 1 WHERE user_id = %s;", (thread_id % 100,))
            operations.append(('update', thread_id))
            cursor.close()
            conn.close()
        except Exception as e:
            errors.append(('update', thread_id, str(e)))
    
    threads = []
    for i in range(70):
        threads.append(threading.Thread(target=read_op, args=(i,)))
    for i in range(20):
        threads.append(threading.Thread(target=write_op, args=(i + 100,)))
    for i in range(10):
        threads.append(threading.Thread(target=update_op, args=(i + 200,)))
    
    for thread in threads:
        thread.start()
    
    for thread in threads:
        thread.join()
    
    assert len(operations) >= 90
    assert len(errors) < 10


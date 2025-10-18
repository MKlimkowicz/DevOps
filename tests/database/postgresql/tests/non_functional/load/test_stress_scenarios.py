import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time


@pytest.mark.load
@pytest.mark.slow
def test_rapid_connection_cycling(db_config):
    """Connect/disconnect cycles."""
    successful_cycles = 0
    
    for i in range(100):
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
            cursor.fetchone()
            cursor.close()
            conn.close()
            successful_cycles += 1
        except Exception:
            pass
    
    assert successful_cycles >= 95


@pytest.mark.load
@pytest.mark.slow
def test_large_result_sets(db_cursor, large_dataset):
    """Query returning 100K+ rows."""
    for i in range(10000, 110000):
        db_cursor.execute(f"""
            INSERT INTO {large_dataset} (user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s);
        """, (i % 1000, f"user_{i}", f"email{i}@test.com", i * 0.01, i % 2 == 0))
    
    start = time.perf_counter()
    db_cursor.execute(f"SELECT * FROM {large_dataset};")
    results = db_cursor.fetchall()
    end = time.perf_counter()
    
    assert len(results) >= 100000
    assert (end - start) < 30.0


@pytest.mark.load
@pytest.mark.slow
def test_complex_query_under_load(db_config, large_dataset):
    """CTEs, subqueries, window functions under load."""
    results = []
    errors = []
    
    def complex_query(thread_id):
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
            
            cursor.execute(f"""
                WITH user_stats AS (
                    SELECT 
                        user_id,
                        COUNT(*) as total_records,
                        AVG(score) as avg_score,
                        ROW_NUMBER() OVER (ORDER BY COUNT(*) DESC) as rank
                    FROM {large_dataset}
                    GROUP BY user_id
                ),
                top_users AS (
                    SELECT * FROM user_stats WHERE rank <= 10
                )
                SELECT 
                    t.user_id,
                    t.total_records,
                    t.avg_score,
                    (SELECT COUNT(*) FROM {large_dataset} d WHERE d.user_id = t.user_id AND d.is_active = true) as active_count
                FROM top_users t
                ORDER BY t.avg_score DESC;
            """)
            
            result = cursor.fetchall()
            results.append((thread_id, len(result)))
            cursor.close()
            conn.close()
        except Exception as e:
            errors.append((thread_id, str(e)))
    
    threads = []
    for i in range(10):
        thread = threading.Thread(target=complex_query, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join(timeout=30)
    
    assert len(results) >= 8
    assert len(errors) < 2


@pytest.mark.load
def test_deadlock_scenarios(db_config, benchmark_table):
    """Intentional deadlock detection and recovery."""
    for i in range(100):
        db_config_conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
        cursor = db_config_conn.cursor()
        cursor.execute(f"""
            INSERT INTO {benchmark_table} (id, user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (i, i, f"user_{i}", f"email{i}@test.com", i * 1.0, True))
        db_config_conn.commit()
        cursor.close()
        db_config_conn.close()
    
    deadlock_detected = False
    results = []
    
    def update_forward(thread_id):
        nonlocal deadlock_detected
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            conn.autocommit = False
            cursor = conn.cursor()
            
            cursor.execute(f"UPDATE {benchmark_table} SET score = score + 1 WHERE id = 10;")
            time.sleep(0.1)
            cursor.execute(f"UPDATE {benchmark_table} SET score = score + 1 WHERE id = 20;")
            
            conn.commit()
            results.append(('forward', thread_id))
            cursor.close()
            conn.close()
        except psycopg2.extensions.TransactionRollbackError:
            deadlock_detected = True
            results.append(('forward_deadlock', thread_id))
        except Exception:
            results.append(('forward_error', thread_id))
    
    def update_backward(thread_id):
        nonlocal deadlock_detected
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            conn.autocommit = False
            cursor = conn.cursor()
            
            cursor.execute(f"UPDATE {benchmark_table} SET score = score + 1 WHERE id = 20;")
            time.sleep(0.1)
            cursor.execute(f"UPDATE {benchmark_table} SET score = score + 1 WHERE id = 10;")
            
            conn.commit()
            results.append(('backward', thread_id))
            cursor.close()
            conn.close()
        except psycopg2.extensions.TransactionRollbackError:
            deadlock_detected = True
            results.append(('backward_deadlock', thread_id))
        except Exception:
            results.append(('backward_error', thread_id))
    
    thread1 = threading.Thread(target=update_forward, args=(1,))
    thread2 = threading.Thread(target=update_backward, args=(2,))
    
    thread1.start()
    thread2.start()
    
    thread1.join(timeout=10)
    thread2.join(timeout=10)
    
    assert len(results) == 2


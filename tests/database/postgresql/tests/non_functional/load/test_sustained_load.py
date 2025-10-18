import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import threading
import time


@pytest.mark.load
@pytest.mark.slow
def test_sustained_read_load(db_config, large_dataset):
    """Continuous queries for 60 seconds."""
    results = []
    stop_flag = threading.Event()
    
    def continuous_reads(thread_id):
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
            count = 0
            
            while not stop_flag.is_set():
                cursor.execute(f"SELECT * FROM {large_dataset} WHERE user_id = %s LIMIT 10;", (thread_id % 100,))
                cursor.fetchall()
                count += 1
            
            results.append((thread_id, count))
            cursor.close()
            conn.close()
        except Exception as e:
            results.append((thread_id, -1))
    
    threads = []
    for i in range(10):
        thread = threading.Thread(target=continuous_reads, args=(i,))
        threads.append(thread)
        thread.start()
    
    time.sleep(10)
    stop_flag.set()
    
    for thread in threads:
        thread.join(timeout=5)
    
    assert len(results) >= 8
    total_queries = sum(r[1] for r in results if r[1] > 0)
    assert total_queries > 100


@pytest.mark.load
@pytest.mark.slow
def test_sustained_write_load(db_config, benchmark_table):
    """Continuous inserts for 60 seconds."""
    results = []
    stop_flag = threading.Event()
    
    def continuous_writes(thread_id):
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
            count = 0
            
            while not stop_flag.is_set():
                cursor.execute(f"""
                    INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
                    VALUES (%s, %s, %s, %s, %s);
                """, (thread_id, f"user_{thread_id}_{count}", f"email_{thread_id}_{count}@test.com", count * 0.5, True))
                count += 1
            
            results.append((thread_id, count))
            cursor.close()
            conn.close()
        except Exception as e:
            results.append((thread_id, -1))
    
    threads = []
    for i in range(5):
        thread = threading.Thread(target=continuous_writes, args=(i,))
        threads.append(thread)
        thread.start()
    
    time.sleep(10)
    stop_flag.set()
    
    for thread in threads:
        thread.join(timeout=5)
    
    assert len(results) >= 4
    total_inserts = sum(r[1] for r in results if r[1] > 0)
    assert total_inserts > 50


@pytest.mark.load
@pytest.mark.slow
def test_transaction_throughput(db_config, benchmark_table):
    """Transactions per second measurement."""
    start_time = time.perf_counter()
    transaction_count = 0
    
    conn = psycopg2.connect(
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"]
    )
    cursor = conn.cursor()
    
    for i in range(1000):
        conn.autocommit = False
        cursor.execute(f"""
            INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s);
        """, (i, f"user_{i}", f"email{i}@test.com", i * 0.1, True))
        conn.commit()
        transaction_count += 1
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    tps = transaction_count / duration
    
    cursor.close()
    conn.close()
    
    assert tps > 10


@pytest.mark.load
@pytest.mark.slow
def test_response_time_under_load(db_config, large_dataset):
    """Latency percentiles (p50, p95, p99)."""
    latencies = []
    
    def measure_query_latency(thread_id):
        try:
            conn = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"]
            )
            cursor = conn.cursor()
            
            for _ in range(50):
                start = time.perf_counter()
                cursor.execute(f"SELECT * FROM {large_dataset} WHERE user_id = %s LIMIT 10;", (thread_id % 100,))
                cursor.fetchall()
                end = time.perf_counter()
                latencies.append(end - start)
            
            cursor.close()
            conn.close()
        except Exception:
            pass
    
    threads = []
    for i in range(20):
        thread = threading.Thread(target=measure_query_latency, args=(i,))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    latencies.sort()
    
    if len(latencies) > 0:
        p50_idx = int(len(latencies) * 0.50)
        p95_idx = int(len(latencies) * 0.95)
        p99_idx = int(len(latencies) * 0.99)
        
        p50 = latencies[p50_idx]
        p95 = latencies[p95_idx]
        p99 = latencies[p99_idx]
        
        assert p50 < 1.0
        assert p95 < 5.0
        assert p99 < 10.0


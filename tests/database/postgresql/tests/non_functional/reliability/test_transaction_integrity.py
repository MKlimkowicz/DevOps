import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
import threading


@pytest.mark.reliability
def test_transaction_rollback_consistency(db_cursor, benchmark_table):
    """Verify rollback completeness."""
    db_cursor.connection.autocommit = False
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (999, "test_user", "test@example.com", 100.0, True))
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 999;")
    assert db_cursor.fetchone()['count'] == 1
    
    db_cursor.connection.rollback()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 999;")
    assert db_cursor.fetchone()['count'] == 0
    
    db_cursor.connection.autocommit = True


@pytest.mark.reliability
def test_savepoint_recovery(db_cursor, benchmark_table):
    """Partial transaction rollback."""
    db_cursor.connection.autocommit = False
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (1001, "user_1001", "user1001@test.com", 50.0, True))
    
    db_cursor.execute("SAVEPOINT sp1;")
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (1002, "user_1002", "user1002@test.com", 60.0, True))
    
    db_cursor.execute("ROLLBACK TO SAVEPOINT sp1;")
    
    db_cursor.connection.commit()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 1001;")
    assert db_cursor.fetchone()['count'] == 1
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 1002;")
    assert db_cursor.fetchone()['count'] == 0
    
    db_cursor.connection.autocommit = True


@pytest.mark.reliability
def test_concurrent_transaction_isolation(db_config, benchmark_table):
    """ACID isolation levels."""
    for i in range(5):
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
            INSERT INTO {benchmark_table} (id, user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s, %s);
        """, (2000 + i, i, f"isolation_user_{i}", f"iso{i}@test.com", i * 10.0, True))
        cursor.close()
        conn.close()
    
    results = []
    
    def transaction_1():
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
        conn.autocommit = False
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        cursor = conn.cursor()
        
        cursor.execute(f"UPDATE {benchmark_table} SET score = score + 10 WHERE id = 2000;")
        cursor.execute(f"SELECT score FROM {benchmark_table} WHERE id = 2000;")
        results.append(('t1', cursor.fetchone()[0]))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    def transaction_2():
        conn = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_config["password"]
        )
        conn.autocommit = False
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)
        cursor = conn.cursor()
        
        cursor.execute(f"SELECT score FROM {benchmark_table} WHERE id = 2000;")
        results.append(('t2', cursor.fetchone()[0]))
        
        conn.commit()
        cursor.close()
        conn.close()
    
    thread1 = threading.Thread(target=transaction_1)
    thread2 = threading.Thread(target=transaction_2)
    
    thread1.start()
    thread1.join()
    
    thread2.start()
    thread2.join()
    
    assert len(results) == 2


@pytest.mark.reliability
def test_long_running_transaction(db_cursor, benchmark_table):
    """Transactions spanning multiple operations."""
    db_cursor.connection.autocommit = False
    
    for i in range(100):
        db_cursor.execute(f"""
            INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s);
        """, (3000 + i, f"long_txn_user_{i}", f"ltxn{i}@test.com", i * 1.5, i % 2 == 0))
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id >= 3000 AND user_id < 3100;")
    count = db_cursor.fetchone()['count']
    assert count == 100
    
    db_cursor.connection.commit()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id >= 3000 AND user_id < 3100;")
    count_committed = db_cursor.fetchone()['count']
    assert count_committed == 100
    
    db_cursor.connection.autocommit = True


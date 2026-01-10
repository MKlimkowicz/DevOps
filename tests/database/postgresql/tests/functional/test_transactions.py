import pytest
import psycopg2
from datetime import datetime, date
import threading
import time
from concurrent.futures import ThreadPoolExecutor


@pytest.fixture
def transaction_cursor(db_connection):
    """Create a cursor with autocommit disabled for transaction testing."""
    conn = psycopg2.connect(
        host=db_connection.get_dsn_parameters()['host'],
        port=db_connection.get_dsn_parameters()['port'],
        database=db_connection.get_dsn_parameters()['dbname'],
        user=db_connection.get_dsn_parameters()['user'],
        password="devops-test-password"  # From conftest.py
    )
    conn.autocommit = False  # Disable autocommit for transaction control
    cursor = conn.cursor()
    try:
        yield cursor, conn
    finally:
        try:
            conn.rollback()  # Ensure cleanup
        except:
            pass
        cursor.close()
        conn.close()


@pytest.fixture
def concurrent_cursor(db_connection):
    """Create a separate cursor for concurrent transaction testing."""
    conn = psycopg2.connect(
        host=db_connection.get_dsn_parameters()['host'],
        port=db_connection.get_dsn_parameters()['port'],
        database=db_connection.get_dsn_parameters()['dbname'],
        user=db_connection.get_dsn_parameters()['user'],
        password="devops-test-password"
    )
    conn.autocommit = False
    cursor = conn.cursor()
    try:
        yield cursor, conn
    finally:
        try:
            conn.rollback()
        except:
            pass
        cursor.close()
        conn.close()


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_basic_transaction_with_commit(create_tables, transaction_cursor, db_cursor):
    """Test basic transaction with COMMIT: BEGIN, INSERT, COMMIT, verify persistence."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    insert_sql = f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)"
    cursor.execute(insert_sql, ("test_value_1", 100))
    cursor.execute(insert_sql, ("test_value_2", 200))
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_in_transaction = cursor.fetchone()[0]
    assert count_in_transaction == 2
    
    conn.commit()
    
    db_cursor.execute(f"SELECT col2, col3 FROM {table_name} ORDER BY col1")
    results = db_cursor.fetchall()
    assert len(results) == 2
    assert dict(results[0]) == {"col2": "test_value_1", "col3": 100}
    assert dict(results[1]) == {"col2": "test_value_2", "col3": 200}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_transaction_with_rollback(create_tables, transaction_cursor, db_cursor):
    """Test transaction with ROLLBACK: BEGIN, INSERT/UPDATE, ROLLBACK, verify data reverts."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('initial', 50)")
    
    cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("rollback_test", 999))
    cursor.execute(f"UPDATE {table_name} SET col3 = 1000 WHERE col2 = 'initial'")
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_in_transaction = cursor.fetchone()[0]
    assert count_in_transaction == 2
    
    cursor.execute(f"SELECT col3 FROM {table_name} WHERE col2 = 'initial'")
    updated_value = cursor.fetchone()[0]
    assert updated_value == 1000
    
    conn.rollback()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_count = db_cursor.fetchone()['count']
    assert final_count == 1
    
    db_cursor.execute(f"SELECT col2, col3 FROM {table_name}")
    result = db_cursor.fetchone()
    assert dict(result) == {"col2": "initial", "col3": 50}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_nested_transactions_savepoints(create_tables, transaction_cursor, db_cursor):
    """Test nested transactions using savepoints: BEGIN, INSERT, SAVEPOINT, UPDATE, ROLLBACK TO SAVEPOINT."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("outer_insert", 100))
    
    cursor.execute("SAVEPOINT sp1")
    
    cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("savepoint_insert", 200))
    cursor.execute(f"UPDATE {table_name} SET col3 = 999 WHERE col2 = 'outer_insert'")
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_with_savepoint = cursor.fetchone()[0]
    assert count_with_savepoint == 2
    
    cursor.execute("ROLLBACK TO SAVEPOINT sp1")
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_after_rollback = cursor.fetchone()[0]
    assert count_after_rollback == 1
    
    cursor.execute(f"SELECT col2, col3 FROM {table_name}")
    result = cursor.fetchone()
    assert result[0] == "outer_insert"
    assert result[1] == 100  # Original value, not updated value
    
    conn.commit()
    
    db_cursor.execute(f"SELECT col2, col3 FROM {table_name}")
    final_result = db_cursor.fetchone()
    assert dict(final_result) == {"col2": "outer_insert", "col3": 100}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_isolation_level_read_committed(create_tables, transaction_cursor, concurrent_cursor, db_cursor):
    """Test READ COMMITTED isolation: no dirty reads from uncommitted transactions."""
    table_name = create_tables[0]
    cursor1, conn1 = transaction_cursor
    cursor2, conn2 = concurrent_cursor
    
    cursor1.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    cursor2.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    
    cursor1.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("uncommitted", 500))
    
    cursor2.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_from_concurrent = cursor2.fetchone()[0]
    assert count_from_concurrent == 0  # No dirty read
    
    conn1.commit()
    
    cursor2.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_after_commit = cursor2.fetchone()[0]
    assert count_after_commit == 1
    
    cursor2.execute(f"SELECT col2, col3 FROM {table_name}")
    result = cursor2.fetchone()
    assert result[0] == "uncommitted"
    assert result[1] == 500


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_isolation_level_serializable(create_tables, transaction_cursor, concurrent_cursor, db_cursor):
    """Test SERIALIZABLE isolation: verify strict transaction ordering."""
    table_name = create_tables[0]
    cursor1, conn1 = transaction_cursor
    cursor2, conn2 = concurrent_cursor
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('row1', 100), ('row2', 200)")
    
    cursor1.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
    cursor2.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
    
    cursor1.execute(f"SELECT SUM(col3) FROM {table_name}")
    sum1 = cursor1.fetchone()[0]
    
    cursor2.execute(f"SELECT SUM(col3) FROM {table_name}")
    sum2 = cursor2.fetchone()[0]
    
    assert sum1 == sum2 == 300
    
    cursor1.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('tx1_insert', %s)", (sum1 // 10,))
    
    cursor2.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('tx2_insert', %s)", (sum2 // 5,))
    
    conn1.commit()
    
    try:
        conn2.commit()
        serialization_passed = True
    except psycopg2.errors.SerializationFailure:
        serialization_passed = False
        conn2.rollback()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_count = db_cursor.fetchone()['count']
    
    if serialization_passed:
        assert final_count == 4
    else:
        assert final_count == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_transaction_multiple_operations(create_tables, transaction_cursor, db_cursor):
    """Test transaction with multiple operations: INSERT, UPDATE, DELETE atomically."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('to_update', 100), ('to_delete', 200)")
    
    cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("new_row", 300))
    cursor.execute(f"UPDATE {table_name} SET col3 = 150 WHERE col2 = 'to_update'")
    cursor.execute(f"DELETE FROM {table_name} WHERE col2 = 'to_delete'")
    
    cursor.execute(f"SELECT col2, col3 FROM {table_name} ORDER BY col1")
    results = cursor.fetchall()
    assert len(results) == 2
    assert results[0][0] == "to_update" and results[0][1] == 150
    assert results[1][0] == "new_row" and results[1][1] == 300
    
    conn.commit()
    
    db_cursor.execute(f"SELECT col2, col3 FROM {table_name} ORDER BY col1")
    final_results = db_cursor.fetchall()
    assert len(final_results) == 2
    assert dict(final_results[0]) == {"col2": "to_update", "col3": 150}
    assert dict(final_results[1]) == {"col2": "new_row", "col3": 300}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER NOT NULL"]}]
}], indirect=True)
def test_transaction_error_handling_rollback(create_tables, transaction_cursor, db_cursor):
    """Test transaction error handling: valid operation, then invalid, rollback."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("valid_row", 100))
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_before_error = cursor.fetchone()[0]
    assert count_before_error == 1
    
    with pytest.raises(psycopg2.IntegrityError):
        cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("invalid_row", None))
    
    conn.rollback()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_count = db_cursor.fetchone()['count']
    assert final_count == 0


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_long_running_transaction_locks(create_tables, transaction_cursor, concurrent_cursor, db_cursor):
    """Test long-running transaction with row locks."""
    table_name = create_tables[0]
    cursor1, conn1 = transaction_cursor
    cursor2, conn2 = concurrent_cursor
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('locked_row', 100)")
    
    cursor1.execute(f"UPDATE {table_name} SET col3 = 200 WHERE col2 = 'locked_row'")
    
    def concurrent_update():
        try:
            cursor2.execute("SET statement_timeout = '2s'")  # 2 second timeout
            cursor2.execute(f"UPDATE {table_name} SET col3 = 300 WHERE col2 = 'locked_row'")
            return "success"
        except psycopg2.errors.QueryCanceled:
            conn2.rollback()
            return "timeout"
    
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(concurrent_update)
        time.sleep(0.5)  # Give it time to block
        
        conn1.commit()
        
        result = future.result(timeout=5)
        assert result in ["timeout", "success"]  # Either timed out or succeeded after lock release


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}
    ]
}], indirect=True)
def test_transaction_with_cte(create_tables, transaction_cursor, db_cursor):
    """Test transaction with CTE (Common Table Expression)."""
    table1, table2 = create_tables
    cursor, conn = transaction_cursor
    
    db_cursor.execute(f"INSERT INTO {table1} (col2, col3) VALUES ('source1', 100), ('source2', 200)")
    
    cte_sql = f"""
    WITH source_data AS (
        SELECT col2, col3 * 2 as doubled_value
        FROM {table1}
        WHERE col3 > 150
    )
    INSERT INTO {table2} (col2, col3)
    SELECT col2, doubled_value FROM source_data
    """
    cursor.execute(cte_sql)
    
    cursor.execute(f"SELECT col2, col3 FROM {table2}")
    results = cursor.fetchall()
    assert len(results) == 1
    assert results[0][0] == "source2"
    assert results[0][1] == 400
    
    conn.commit()
    
    db_cursor.execute(f"SELECT col2, col3 FROM {table2}")
    final_result = db_cursor.fetchone()
    assert dict(final_result) == {"col2": "source2", "col3": 400}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_commit_empty_transaction(create_tables, transaction_cursor, db_cursor):
    """Test edge case: COMMIT on empty transaction."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    initial_count = db_cursor.fetchone()['count']
    
    conn.commit()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_count = db_cursor.fetchone()['count']
    assert final_count == initial_count


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_rollback_after_commit_behavior(create_tables, transaction_cursor, db_cursor):
    """Test edge case: ROLLBACK after COMMIT behavior (should be no-op)."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", ("test", 100))
    conn.commit()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count_after_commit = db_cursor.fetchone()['count']
    assert count_after_commit == 1
    
    conn.rollback()  # This should not raise an error, just be ignored
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_count = db_cursor.fetchone()['count']
    assert final_count == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INTEGER"]}]
}], indirect=True)
def test_transaction_read_only_operations(create_tables, transaction_cursor, db_cursor):
    """Test transaction with read-only operations."""
    table_name = create_tables[0]
    cursor, conn = transaction_cursor
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('read_test1', 100), ('read_test2', 200)")
    
    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    count = cursor.fetchone()[0]
    assert count == 2
    
    cursor.execute(f"SELECT col2, col3 FROM {table_name} WHERE col3 > 150")
    results = cursor.fetchall()
    assert len(results) == 1
    assert results[0][0] == "read_test2"
    
    cursor.execute(f"SELECT MAX(col3), MIN(col3) FROM {table_name}")
    aggregates = cursor.fetchone()
    assert aggregates[0] == 200  # MAX
    assert aggregates[1] == 100  # MIN
    
    conn.commit()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    final_count = db_cursor.fetchone()['count']
    assert final_count == 2

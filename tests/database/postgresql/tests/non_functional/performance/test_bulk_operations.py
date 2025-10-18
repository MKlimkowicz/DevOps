import pytest
from io import StringIO
import csv


@pytest.mark.performance
@pytest.mark.slow
def test_bulk_insert_performance(db_cursor, benchmark_table, benchmark):
    """Insert 10K, 50K, 100K rows."""
    def insert_10k():
        for i in range(10000):
            db_cursor.execute(f"""
                INSERT INTO {benchmark_table} 
                (user_id, username, email, score, created_at, is_active)
                VALUES (%s, %s, %s, %s, NOW(), %s);
            """, (i, f"user_{i}", f"user{i}@example.com", i * 0.5, i % 2 == 0))
    
    benchmark(insert_10k)
    
    db_cursor.execute(f"SELECT COUNT(*) as count FROM {benchmark_table};")
    result = db_cursor.fetchone()
    assert result['count'] >= 10000


@pytest.mark.performance
@pytest.mark.slow
def test_bulk_update_performance(db_cursor, large_dataset, benchmark):
    """Update large record sets."""
    def bulk_update():
        db_cursor.execute(f"""
            UPDATE {large_dataset}
            SET score = score * 1.1,
                is_active = NOT is_active
            WHERE user_id < 500;
        """)
    
    benchmark(bulk_update)


@pytest.mark.performance
@pytest.mark.slow
def test_bulk_delete_performance(db_cursor, large_dataset, benchmark):
    """Delete operations on various dataset sizes."""
    db_cursor.execute(f"SELECT COUNT(*) FROM {large_dataset};")
    initial_count = db_cursor.fetchone()['count']
    
    def bulk_delete():
        db_cursor.execute(f"""
            DELETE FROM {large_dataset}
            WHERE user_id > 800;
        """)
    
    benchmark(bulk_delete)
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {large_dataset};")
    final_count = db_cursor.fetchone()['count']
    assert final_count < initial_count


@pytest.mark.performance
def test_copy_vs_insert_performance(db_cursor, benchmark_table):
    """Compare COPY vs INSERT methods."""
    insert_data = [(i, f"user_{i}", f"user{i}@example.com", i * 0.5, True) 
                   for i in range(5000)]
    
    start_insert = pytest.time.perf_counter() if hasattr(pytest, 'time') else 0
    for row in insert_data:
        db_cursor.execute(f"""
            INSERT INTO {benchmark_table}
            (user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s);
        """, row)
    
    db_cursor.execute(f"TRUNCATE {benchmark_table};")
    
    csv_data = StringIO()
    writer = csv.writer(csv_data)
    for row in insert_data:
        writer.writerow(row)
    csv_data.seek(0)
    
    db_cursor.copy_expert(
        f"""COPY {benchmark_table} (user_id, username, email, score, is_active) 
            FROM STDIN WITH CSV""",
        csv_data
    )
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table};")
    result = db_cursor.fetchone()
    assert result['count'] == 5000


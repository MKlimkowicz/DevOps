import pytest
import time


@pytest.mark.performance
def test_select_performance_indexed_vs_unindexed(db_cursor, large_dataset, benchmark):
    """Compare query times with and without indexes."""
    def query_without_index():
        db_cursor.execute(f"SELECT * FROM {large_dataset} WHERE user_id = 500;")
        return db_cursor.fetchall()
    
    result = benchmark(query_without_index)
    assert len(result) >= 0
    
    db_cursor.execute(f"CREATE INDEX idx_user_id ON {large_dataset}(user_id);")
    
    def query_with_index():
        db_cursor.execute(f"SELECT * FROM {large_dataset} WHERE user_id = 500;")
        return db_cursor.fetchall()
    
    result_indexed = benchmark(query_with_index)
    assert len(result_indexed) >= 0


@pytest.mark.performance
def test_join_performance_multiple_tables(db_cursor, benchmark):
    """Benchmark 2-way, 3-way, 4-way joins."""
    tables = []
    for i in range(4):
        table_name = f"perf_table_{i}"
        db_cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
        db_cursor.execute(f"""
            CREATE TABLE {table_name} (
                id SERIAL PRIMARY KEY,
                ref_id INT,
                value VARCHAR(100)
            );
        """)
        
        for j in range(1000):
            db_cursor.execute(
                f"INSERT INTO {table_name} (ref_id, value) VALUES (%s, %s);",
                (j % 100, f"value_{j}")
            )
        tables.append(table_name)
    
    def join_query():
        query = f"""
            SELECT t0.id, t1.value, t2.value, t3.value
            FROM {tables[0]} t0
            JOIN {tables[1]} t1 ON t0.ref_id = t1.ref_id
            JOIN {tables[2]} t2 ON t1.ref_id = t2.ref_id
            JOIN {tables[3]} t3 ON t2.ref_id = t3.ref_id
            LIMIT 100;
        """
        db_cursor.execute(query)
        return db_cursor.fetchall()
    
    result = benchmark(join_query)
    assert len(result) > 0
    
    for table in tables:
        db_cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")


@pytest.mark.performance
def test_aggregation_performance(db_cursor, large_dataset, benchmark):
    """GROUP BY, COUNT, SUM, AVG on large datasets."""
    def aggregation_query():
        db_cursor.execute(f"""
            SELECT 
                user_id,
                COUNT(*) as count,
                SUM(score) as total_score,
                AVG(score) as avg_score,
                MAX(score) as max_score,
                MIN(score) as min_score
            FROM {large_dataset}
            GROUP BY user_id
            HAVING COUNT(*) > 5
            ORDER BY total_score DESC;
        """)
        return db_cursor.fetchall()
    
    result = benchmark(aggregation_query)
    assert len(result) > 0


@pytest.mark.performance
def test_full_text_search_performance(db_cursor, large_dataset, benchmark):
    """pg_trgm trigram search benchmarks."""
    db_cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_username_trgm ON {large_dataset} USING gin (username gin_trgm_ops);")
    
    def search_query():
        db_cursor.execute(f"""
            SELECT * FROM {large_dataset}
            WHERE username ILIKE %s
            LIMIT 100;
        """, ('%john%',))
        return db_cursor.fetchall()
    
    result = benchmark(search_query)
    assert isinstance(result, list)


@pytest.mark.performance
def test_json_query_performance(db_cursor, large_dataset, benchmark):
    """JSON field extraction and filtering."""
    def json_query():
        db_cursor.execute(f"""
            SELECT id, metadata->>'key' as key_value
            FROM {large_dataset}
            WHERE metadata->>'index' IS NOT NULL
            LIMIT 1000;
        """)
        return db_cursor.fetchall()
    
    result = benchmark(json_query)
    assert len(result) > 0


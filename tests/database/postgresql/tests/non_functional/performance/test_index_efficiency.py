import pytest


@pytest.mark.performance
def test_btree_index_performance(db_cursor, large_dataset, benchmark):
    """Standard B-tree index efficiency."""
    db_cursor.execute(f"CREATE INDEX idx_btree_score ON {large_dataset} USING btree (score);")
    
    def btree_query():
        db_cursor.execute(f"""
            SELECT * FROM {large_dataset}
            WHERE score BETWEEN 100 AND 500
            ORDER BY score;
        """)
        return db_cursor.fetchall()
    
    result = benchmark(btree_query)
    assert len(result) > 0
    
    db_cursor.execute(f"DROP INDEX IF EXISTS idx_btree_score;")


@pytest.mark.performance
def test_hash_index_performance(db_cursor, large_dataset, benchmark):
    """Hash index for equality operations."""
    db_cursor.execute(f"CREATE INDEX idx_hash_user_id ON {large_dataset} USING hash (user_id);")
    
    def hash_query():
        db_cursor.execute(f"""
            SELECT * FROM {large_dataset}
            WHERE user_id = 250;
        """)
        return db_cursor.fetchall()
    
    result = benchmark(hash_query)
    assert len(result) >= 0
    
    db_cursor.execute(f"DROP INDEX IF EXISTS idx_hash_user_id;")


@pytest.mark.performance
def test_gin_index_performance(db_cursor, large_dataset, benchmark):
    """GIN index for array/JSONB queries."""
    db_cursor.execute(f"CREATE INDEX idx_gin_metadata ON {large_dataset} USING gin (metadata);")
    
    def gin_query():
        db_cursor.execute(f"""
            SELECT * FROM {large_dataset}
            WHERE metadata @> '{{"key": "value_100"}}'::jsonb;
        """)
        return db_cursor.fetchall()
    
    result = benchmark(gin_query)
    assert isinstance(result, list)
    
    db_cursor.execute(f"DROP INDEX IF EXISTS idx_gin_metadata;")


@pytest.mark.performance
def test_gist_index_performance(db_cursor, benchmark_table, benchmark):
    """GiST index for geometric/full-text."""
    for i in range(1000):
        db_cursor.execute(f"""
            INSERT INTO {benchmark_table} (username)
            VALUES (%s);
        """, (f"testuser_{i}_searchable",))
    
    db_cursor.execute(f"CREATE INDEX idx_gist_username ON {benchmark_table} USING gist (username gist_trgm_ops);")
    
    def gist_query():
        db_cursor.execute(f"""
            SELECT * FROM {benchmark_table}
            WHERE username ILIKE %s;
        """, ('%search%',))
        return db_cursor.fetchall()
    
    result = benchmark(gist_query)
    assert isinstance(result, list)
    
    db_cursor.execute(f"DROP INDEX IF EXISTS idx_gist_username;")


@pytest.mark.performance
def test_index_size_vs_performance(db_cursor, large_dataset):
    """Index overhead analysis."""
    db_cursor.execute(f"""
        SELECT pg_size_pretty(pg_total_relation_size('{large_dataset}')) as table_size;
    """)
    table_size_before = db_cursor.fetchone()
    
    db_cursor.execute(f"CREATE INDEX idx_composite ON {large_dataset} (user_id, score, is_active);")
    
    db_cursor.execute(f"""
        SELECT pg_size_pretty(pg_total_relation_size('{large_dataset}')) as table_size;
    """)
    table_size_after = db_cursor.fetchone()
    
    db_cursor.execute(f"""
        SELECT pg_size_pretty(pg_relation_size('idx_composite')) as index_size;
    """)
    index_size = db_cursor.fetchone()
    
    assert table_size_before is not None
    assert table_size_after is not None
    assert index_size is not None
    
    db_cursor.execute(f"DROP INDEX IF EXISTS idx_composite;")


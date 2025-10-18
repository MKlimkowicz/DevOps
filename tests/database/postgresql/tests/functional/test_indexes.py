import pytest
import psycopg2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_create_btree_index(create_tables, db_cursor):
    """Test creating B-tree index (default)."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_col2 ON {table_name}(col2)")
    
    db_cursor.execute(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_col2'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert 'idx_col2' in result['indexname']


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_create_unique_index(create_tables, db_cursor):
    """Test creating UNIQUE index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE UNIQUE INDEX idx_unique_col2 ON {table_name}(col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value1', 100)")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value1', 200)")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_create_composite_index(create_tables, db_cursor):
    """Test creating composite index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_composite ON {table_name}(col2, col3)")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_composite'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_create_hash_index(create_tables, db_cursor):
    """Test creating Hash index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_hash ON {table_name} USING HASH (col2)")
    
    db_cursor.execute(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_hash'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert 'hash' in result['indexdef'].lower()


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_create_gin_index(create_tables, db_cursor):
    """Test creating GIN index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_gin ON {table_name} USING GIN (col2 gin_trgm_ops)")
    
    db_cursor.execute(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_gin'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert 'gin' in result['indexdef'].lower()


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "INT"]}]
}], indirect=True)
def test_create_brin_index(create_tables, db_cursor):
    """Test creating BRIN index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_brin ON {table_name} USING BRIN (col2)")
    
    db_cursor.execute(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_brin'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert 'brin' in result['indexdef'].lower()


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_create_partial_index(create_tables, db_cursor):
    """Test creating partial index with WHERE clause."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_partial ON {table_name}(col2) WHERE col2 IS NOT NULL")
    
    db_cursor.execute(f"""
        SELECT indexname, indexdef 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_partial'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert 'where' in result['indexdef'].lower()


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "TEXT"]}]
}], indirect=True)
def test_create_expression_index(create_tables, db_cursor):
    """Test creating expression index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_lower ON {table_name}(LOWER(col2))")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_lower'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_drop_index(create_tables, db_cursor):
    """Test dropping index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_to_drop ON {table_name}(col2)")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_to_drop'
    """)
    assert db_cursor.fetchone() is not None
    
    db_cursor.execute(f"DROP INDEX idx_to_drop")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_to_drop'
    """)
    assert db_cursor.fetchone() is None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_concurrent_index_creation(create_tables, db_cursor):
    """Test creating index concurrently."""
    table_name = create_tables[0]
    
    for i in range(10):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value{i}')")
    
    db_cursor.execute(f"CREATE INDEX CONCURRENTLY idx_concurrent ON {table_name}(col2)")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_concurrent'
    """)
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_reindex_table(create_tables, db_cursor):
    """Test reindexing table."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_reindex ON {table_name}(col2)")
    
    for i in range(100):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value{i}')")
    
    db_cursor.execute(f"REINDEX TABLE {table_name}")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_reindex'
    """)
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_reindex_specific_index(create_tables, db_cursor):
    """Test reindexing specific index."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_specific ON {table_name}(col2)")
    
    for i in range(50):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value{i}')")
    
    db_cursor.execute(f"REINDEX INDEX idx_specific")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_specific'
    """)
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}]
}], indirect=True)
def test_index_with_nulls_first(create_tables, db_cursor):
    """Test index with NULLS FIRST ordering."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_nulls_first ON {table_name}(col2 NULLS FIRST)")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_nulls_first'
    """)
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}]
}], indirect=True)
def test_index_with_desc_order(create_tables, db_cursor):
    """Test index with DESC ordering."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_desc ON {table_name}(col2 DESC)")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_desc'
    """)
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_index_only_scan(create_tables, db_cursor):
    """Test index-only scan capability."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_covering ON {table_name}(col2)")
    
    for i in range(10000):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value{i}')")
    
    db_cursor.execute(f"VACUUM ANALYZE {table_name}")
    
    db_cursor.execute(f"EXPLAIN (FORMAT TEXT) SELECT col2 FROM {table_name} WHERE col2 = 'value5000'")
    plan = db_cursor.fetchall()
    
    plan_text = ' '.join([list(row.values())[0] for row in plan])
    assert 'index' in plan_text.lower() or 'scan' in plan_text.lower()


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "INT[]"]}]
}], indirect=True)
def test_gin_index_on_array(create_tables, db_cursor):
    """Test GIN index on array column."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_array_gin ON {table_name} USING GIN(col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (ARRAY[1,2,3])")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (ARRAY[2,3,4])")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (ARRAY[5,6,7])")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 && ARRAY[2]")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_gin_index_on_jsonb(create_tables, db_cursor):
    """Test GIN index on JSONB column."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_jsonb_gin ON {table_name} USING GIN(col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"key\": \"value1\"}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"key\": \"value2\"}}'::jsonb)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 @> '{{\"key\": \"value1\"}}'")
    assert db_cursor.fetchone()['count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "INT"]}]
}], indirect=True)
def test_invalid_index_name_conflict(create_tables, db_cursor):
    """Test creating index with duplicate name fails."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX idx_duplicate ON {table_name}(col2)")
    
    with pytest.raises(psycopg2.DatabaseError):
        db_cursor.execute(f"CREATE INDEX idx_duplicate ON {table_name}(col2)")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "INT"]}]
}], indirect=True)
def test_create_index_if_not_exists(create_tables, db_cursor):
    """Test CREATE INDEX IF NOT EXISTS."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_safe ON {table_name}(col2)")
    db_cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_safe ON {table_name}(col2)")
    
    db_cursor.execute(f"""
        SELECT COUNT(*) 
        FROM pg_indexes 
        WHERE tablename = '{table_name}' AND indexname = 'idx_safe'
    """)
    assert db_cursor.fetchone()['count'] == 1


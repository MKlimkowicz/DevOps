import pytest
import psycopg2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_create_simple_view(create_tables, db_cursor):
    """Test creating a simple view."""
    table_name = create_tables[0]
    view_name = f"{table_name}_view"
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i * 10})")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT col2, col3 FROM {table_name}")
    
    db_cursor.execute(f"SELECT viewname FROM pg_views WHERE viewname = '{view_name}'")
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_query_view(create_tables, db_cursor):
    """Test querying data from a view."""
    table_name = create_tables[0]
    view_name = f"{table_name}_view"
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i * 10})")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT col2, col3 FROM {table_name} WHERE col3 > 20")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_view_with_aggregation(create_tables, db_cursor):
    """Test view with aggregation."""
    table_name = create_tables[0]
    view_name = f"{table_name}_agg_view"
    
    for i in range(10):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('category{i % 3}', {i})")
    
    db_cursor.execute(f"""
        CREATE VIEW {view_name} AS 
        SELECT col2, COUNT(*) as count, SUM(col3) as total 
        FROM {table_name} 
        GROUP BY col2
    """)
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    assert db_cursor.fetchone()['count'] == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_view_with_join(create_tables, db_cursor):
    """Test view with JOIN."""
    table1, table2 = create_tables
    view_name = f"{table1}_join_view"
    
    db_cursor.execute(f"INSERT INTO {table1} (col2) VALUES ('parent1'), ('parent2')")
    db_cursor.execute(f"SELECT col1 FROM {table1} ORDER BY col1")
    parent_ids = [row['col1'] for row in db_cursor.fetchall()]
    
    db_cursor.execute(f"INSERT INTO {table2} (col2, col3) VALUES ({parent_ids[0]}, 'child1')")
    db_cursor.execute(f"INSERT INTO {table2} (col2, col3) VALUES ({parent_ids[1]}, 'child2')")
    
    db_cursor.execute(f"""
        CREATE VIEW {view_name} AS 
        SELECT t1.col2 as parent_name, t2.col3 as child_name 
        FROM {table1} t1 
        INNER JOIN {table2} t2 ON t1.col1 = t2.col2
    """)
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_drop_view(create_tables, db_cursor):
    """Test dropping a view."""
    table_name = create_tables[0]
    view_name = f"{table_name}_drop_view"
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"SELECT viewname FROM pg_views WHERE viewname = '{view_name}'")
    assert db_cursor.fetchone() is not None
    
    db_cursor.execute(f"DROP VIEW {view_name}")
    
    db_cursor.execute(f"SELECT viewname FROM pg_views WHERE viewname = '{view_name}'")
    assert db_cursor.fetchone() is None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_create_or_replace_view(create_tables, db_cursor):
    """Test CREATE OR REPLACE VIEW."""
    table_name = create_tables[0]
    view_name = f"{table_name}_replace_view"
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT col2 FROM {table_name}")
    
    db_cursor.execute(f"CREATE OR REPLACE VIEW {view_name} AS SELECT col2, col3 FROM {table_name}")
    
    db_cursor.execute(f"SELECT * FROM {view_name} LIMIT 1")
    result = db_cursor.fetchone()
    assert 'col2' in result and 'col3' in result


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_materialized_view_creation(create_tables, db_cursor):
    """Test creating a materialized view."""
    table_name = create_tables[0]
    mv_name = f"{table_name}_mv"
    
    for i in range(10):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"CREATE MATERIALIZED VIEW {mv_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"SELECT matviewname FROM pg_matviews WHERE matviewname = '{mv_name}'")
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_materialized_view_data_snapshot(create_tables, db_cursor):
    """Test that materialized view is a snapshot."""
    table_name = create_tables[0]
    mv_name = f"{table_name}_snapshot_mv"
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('initial', 1)")
    
    db_cursor.execute(f"CREATE MATERIALIZED VIEW {mv_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('after_mv', 2)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {mv_name}")
    mv_count = db_cursor.fetchone()['count']
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    table_count = db_cursor.fetchone()['count']
    
    assert mv_count == 1
    assert table_count == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_refresh_materialized_view(create_tables, db_cursor):
    """Test refreshing materialized view."""
    table_name = create_tables[0]
    mv_name = f"{table_name}_refresh_mv"
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('initial', 1)")
    
    db_cursor.execute(f"CREATE MATERIALIZED VIEW {mv_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('new_data', 2)")
    
    db_cursor.execute(f"REFRESH MATERIALIZED VIEW {mv_name}")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {mv_name}")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_materialized_view_with_index(create_tables, db_cursor):
    """Test creating index on materialized view."""
    table_name = create_tables[0]
    mv_name = f"{table_name}_indexed_mv"
    
    for i in range(100):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"CREATE MATERIALIZED VIEW {mv_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"CREATE INDEX idx_{mv_name}_col3 ON {mv_name}(col3)")
    
    db_cursor.execute(f"""
        SELECT indexname 
        FROM pg_indexes 
        WHERE tablename = '{mv_name}'
    """)
    assert db_cursor.fetchone() is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_drop_materialized_view(create_tables, db_cursor):
    """Test dropping materialized view."""
    table_name = create_tables[0]
    mv_name = f"{table_name}_drop_mv"
    
    db_cursor.execute(f"CREATE MATERIALIZED VIEW {mv_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"SELECT matviewname FROM pg_matviews WHERE matviewname = '{mv_name}'")
    assert db_cursor.fetchone() is not None
    
    db_cursor.execute(f"DROP MATERIALIZED VIEW {mv_name}")
    
    db_cursor.execute(f"SELECT matviewname FROM pg_matviews WHERE matviewname = '{mv_name}'")
    assert db_cursor.fetchone() is None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_view_with_check_option(create_tables, db_cursor):
    """Test view with CHECK OPTION."""
    table_name = create_tables[0]
    view_name = f"{table_name}_check_view"
    
    for i in range(10):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"""
        CREATE VIEW {view_name} AS 
        SELECT * FROM {table_name} WHERE col3 < 5 
        WITH CHECK OPTION
    """)
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    assert db_cursor.fetchone()['count'] == 5


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_updatable_view(create_tables, db_cursor):
    """Test updating through a simple view."""
    table_name = create_tables[0]
    view_name = f"{table_name}_updatable_view"
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('original', 10)")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT * FROM {table_name}")
    
    db_cursor.execute(f"SELECT col1 FROM {view_name}")
    row_id = db_cursor.fetchone()['col1']
    
    db_cursor.execute(f"UPDATE {view_name} SET col2 = 'updated' WHERE col1 = {row_id}")
    
    db_cursor.execute(f"SELECT col2 FROM {table_name} WHERE col1 = {row_id}")
    assert db_cursor.fetchone()['col2'] == 'updated'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_deletable_view(create_tables, db_cursor):
    """Test deleting through a simple view."""
    table_name = create_tables[0]
    view_name = f"{table_name}_deletable_view"
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT * FROM {table_name} WHERE col3 < 3")
    
    db_cursor.execute(f"DELETE FROM {view_name} WHERE col3 = 1")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    assert db_cursor.fetchone()['count'] == 4


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_recursive_view(create_tables, db_cursor):
    """Test recursive view creation."""
    table_name = create_tables[0]
    view_name = f"{table_name}_recursive_view"
    
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (1, 'item1', NULL)")
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (2, 'item2', 1)")
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (3, 'item3', 2)")
    
    db_cursor.execute(f"""
        CREATE VIEW {view_name} AS 
        WITH RECURSIVE tree AS (
            SELECT col1, col2, col3, 0 as level 
            FROM {table_name} 
            WHERE col3 IS NULL
            UNION ALL
            SELECT t.col1, t.col2, t.col3, v.level + 1 
            FROM {table_name} t 
            INNER JOIN tree v ON t.col3 = v.col1
        )
        SELECT * FROM tree
    """)
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    assert db_cursor.fetchone()['count'] == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_view_with_distinct(create_tables, db_cursor):
    """Test view with DISTINCT."""
    table_name = create_tables[0]
    view_name = f"{table_name}_distinct_view"
    
    for i in range(10):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value{i % 3}')")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT DISTINCT col2 FROM {table_name}")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {view_name}")
    assert db_cursor.fetchone()['count'] == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_materialized_view_with_no_data(create_tables, db_cursor):
    """Test creating materialized view with NO DATA."""
    table_name = create_tables[0]
    mv_name = f"{table_name}_nodata_mv"
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"CREATE MATERIALIZED VIEW {mv_name} AS SELECT * FROM {table_name} WITH NO DATA")
    
    db_cursor.execute(f"SELECT matviewname FROM pg_matviews WHERE matviewname = '{mv_name}'")
    assert db_cursor.fetchone() is not None
    
    with pytest.raises(psycopg2.DatabaseError):
        db_cursor.execute(f"SELECT COUNT(*) FROM {mv_name}")


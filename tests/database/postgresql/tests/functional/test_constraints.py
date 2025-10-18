import pytest
import psycopg2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_primary_key_constraint_creation(create_tables, db_cursor):
    """Test creating table with PRIMARY KEY constraint."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"""
        SELECT constraint_name, constraint_type 
        FROM information_schema.table_constraints 
        WHERE table_name = '{table_name}' AND constraint_type = 'PRIMARY KEY'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert result['constraint_type'] == 'PRIMARY KEY'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_primary_key_uniqueness(create_tables, db_cursor):
    """Test PRIMARY KEY enforces uniqueness."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (1, 'test1')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (1, 'test2')")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_primary_key_not_null(create_tables, db_cursor):
    """Test PRIMARY KEY enforces NOT NULL."""
    table_name = create_tables[0]
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (NULL, 'test')")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_foreign_key_constraint_creation(create_tables, db_cursor):
    """Test creating FOREIGN KEY constraint."""
    parent_table, child_table = create_tables
    
    db_cursor.execute(f"""
        ALTER TABLE {child_table} 
        ADD CONSTRAINT fk_parent 
        FOREIGN KEY (col2) REFERENCES {parent_table}(col1)
    """)
    
    db_cursor.execute(f"""
        SELECT constraint_name, constraint_type 
        FROM information_schema.table_constraints 
        WHERE table_name = '{child_table}' AND constraint_type = 'FOREIGN KEY'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert result['constraint_type'] == 'FOREIGN KEY'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_foreign_key_referential_integrity(create_tables, db_cursor):
    """Test FOREIGN KEY enforces referential integrity."""
    parent_table, child_table = create_tables
    
    db_cursor.execute(f"""
        ALTER TABLE {child_table} 
        ADD CONSTRAINT fk_parent 
        FOREIGN KEY (col2) REFERENCES {parent_table}(col1)
    """)
    
    db_cursor.execute(f"INSERT INTO {parent_table} (col2) VALUES ('parent1')")
    db_cursor.execute(f"SELECT col1 FROM {parent_table}")
    parent_id = db_cursor.fetchone()['col1']
    
    db_cursor.execute(f"INSERT INTO {child_table} (col2, col3) VALUES ({parent_id}, 'child1')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {child_table} (col2, col3) VALUES (9999, 'child2')")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_foreign_key_on_delete_cascade(create_tables, db_cursor):
    """Test FOREIGN KEY with ON DELETE CASCADE."""
    parent_table, child_table = create_tables
    
    db_cursor.execute(f"""
        ALTER TABLE {child_table} 
        ADD CONSTRAINT fk_parent 
        FOREIGN KEY (col2) REFERENCES {parent_table}(col1)
        ON DELETE CASCADE
    """)
    
    db_cursor.execute(f"INSERT INTO {parent_table} (col2) VALUES ('parent1')")
    db_cursor.execute(f"SELECT col1 FROM {parent_table}")
    parent_id = db_cursor.fetchone()['col1']
    
    db_cursor.execute(f"INSERT INTO {child_table} (col2, col3) VALUES ({parent_id}, 'child1')")
    
    db_cursor.execute(f"DELETE FROM {parent_table} WHERE col1 = {parent_id}")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {child_table}")
    assert db_cursor.fetchone()['count'] == 0


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_unique_constraint_creation(create_tables, db_cursor):
    """Test creating UNIQUE constraint."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT unique_col2 UNIQUE (col2)")
    
    db_cursor.execute(f"""
        SELECT constraint_name, constraint_type 
        FROM information_schema.table_constraints 
        WHERE table_name = '{table_name}' AND constraint_type = 'UNIQUE'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert result['constraint_type'] == 'UNIQUE'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_unique_constraint_enforcement(create_tables, db_cursor):
    """Test UNIQUE constraint enforces uniqueness."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT unique_col2 UNIQUE (col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('unique_value')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('unique_value')")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_unique_constraint_allows_null(create_tables, db_cursor):
    """Test UNIQUE constraint allows NULL values."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT unique_col2 UNIQUE (col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (NULL)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (NULL)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 IS NULL")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "INT"]}]
}], indirect=True)
def test_check_constraint_creation(create_tables, db_cursor):
    """Test creating CHECK constraint."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT check_positive CHECK (col2 > 0)")
    
    db_cursor.execute(f"""
        SELECT constraint_name, constraint_type 
        FROM information_schema.table_constraints 
        WHERE table_name = '{table_name}' AND constraint_type = 'CHECK'
    """)
    result = db_cursor.fetchone()
    
    assert result is not None
    assert result['constraint_type'] == 'CHECK'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "INT"]}]
}], indirect=True)
def test_check_constraint_enforcement(create_tables, db_cursor):
    """Test CHECK constraint enforces condition."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT check_positive CHECK (col2 > 0)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (5)")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (-1)")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "INT"]}]
}], indirect=True)
def test_check_constraint_multiple_columns(create_tables, db_cursor):
    """Test CHECK constraint with multiple columns."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT check_range CHECK (col2 < col3)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (5, 10)")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (15, 10)")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100) NOT NULL"]}]
}], indirect=True)
def test_not_null_constraint_enforcement(create_tables, db_cursor):
    """Test NOT NULL constraint enforces non-null values."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('not_null_value')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (NULL)")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_add_not_null_constraint_to_existing_column(create_tables, db_cursor):
    """Test adding NOT NULL constraint to existing column."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value1')")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value2')")
    
    db_cursor.execute(f"ALTER TABLE {table_name} ALTER COLUMN col2 SET NOT NULL")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (NULL)")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "INT", "VARCHAR(100)"]}]
}], indirect=True)
def test_composite_primary_key(create_tables, db_cursor):
    """Test composite PRIMARY KEY constraint."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD PRIMARY KEY (col1, col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (1, 1, 'test1')")
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (1, 2, 'test2')")
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (2, 1, 'test3')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (1, 1, 'test4')")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "VARCHAR(100)"]}]
}], indirect=True)
def test_composite_unique_constraint(create_tables, db_cursor):
    """Test composite UNIQUE constraint."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT unique_cols UNIQUE (col2, col3)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('a', 'b')")
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('a', 'c')")
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('b', 'b')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('a', 'b')")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]}]
}], indirect=True)
def test_drop_constraint(create_tables, db_cursor):
    """Test dropping constraint."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"ALTER TABLE {table_name} ADD CONSTRAINT unique_col2 UNIQUE (col2)")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value1')")
    
    db_cursor.execute(f"ALTER TABLE {table_name} DROP CONSTRAINT unique_col2")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('value1')")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 = 'value1'")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_foreign_key_prevents_parent_deletion(create_tables, db_cursor):
    """Test FOREIGN KEY prevents parent deletion when child records exist."""
    parent_table, child_table = create_tables
    
    db_cursor.execute(f"""
        ALTER TABLE {child_table} 
        ADD CONSTRAINT fk_parent 
        FOREIGN KEY (col2) REFERENCES {parent_table}(col1)
    """)
    
    db_cursor.execute(f"INSERT INTO {parent_table} (col2) VALUES ('parent1')")
    db_cursor.execute(f"SELECT col1 FROM {parent_table}")
    parent_id = db_cursor.fetchone()['col1']
    
    db_cursor.execute(f"INSERT INTO {child_table} (col2, col3) VALUES ({parent_id}, 'child1')")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute(f"DELETE FROM {parent_table} WHERE col1 = {parent_id}")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_foreign_key_on_update_cascade(create_tables, db_cursor):
    """Test FOREIGN KEY with ON UPDATE CASCADE."""
    parent_table, child_table = create_tables
    
    db_cursor.execute(f"""
        ALTER TABLE {child_table} 
        ADD CONSTRAINT fk_parent 
        FOREIGN KEY (col2) REFERENCES {parent_table}(col1)
        ON UPDATE CASCADE
    """)
    
    db_cursor.execute(f"INSERT INTO {parent_table} (col1, col2) VALUES (100, 'parent1')")
    db_cursor.execute(f"INSERT INTO {child_table} (col2, col3) VALUES (100, 'child1')")
    
    db_cursor.execute(f"UPDATE {parent_table} SET col1 = 200 WHERE col1 = 100")
    
    db_cursor.execute(f"SELECT col2 FROM {child_table}")
    assert db_cursor.fetchone()['col2'] == 200


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "INT", "VARCHAR(100)"]}
    ]
}], indirect=True)
def test_foreign_key_on_delete_set_null(create_tables, db_cursor):
    """Test FOREIGN KEY with ON DELETE SET NULL."""
    parent_table, child_table = create_tables
    
    db_cursor.execute(f"""
        ALTER TABLE {child_table} 
        ADD CONSTRAINT fk_parent 
        FOREIGN KEY (col2) REFERENCES {parent_table}(col1)
        ON DELETE SET NULL
    """)
    
    db_cursor.execute(f"INSERT INTO {parent_table} (col2) VALUES ('parent1')")
    db_cursor.execute(f"SELECT col1 FROM {parent_table}")
    parent_id = db_cursor.fetchone()['col1']
    
    db_cursor.execute(f"INSERT INTO {child_table} (col2, col3) VALUES ({parent_id}, 'child1')")
    
    db_cursor.execute(f"DELETE FROM {parent_table} WHERE col1 = {parent_id}")
    
    db_cursor.execute(f"SELECT col2 FROM {child_table}")
    assert db_cursor.fetchone()['col2'] is None


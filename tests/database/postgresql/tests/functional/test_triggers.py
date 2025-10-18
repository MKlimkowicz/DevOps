import pytest
import psycopg2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "TIMESTAMP DEFAULT NOW()"]}
    ]
}], indirect=True)
def test_before_insert_trigger(create_tables, db_cursor):
    """Test BEFORE INSERT trigger."""
    main_table, log_table = create_tables
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_before_insert() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES ('before_insert');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_before_insert 
        BEFORE INSERT ON {main_table}
        FOR EACH ROW EXECUTE FUNCTION log_before_insert()
    """)
    
    db_cursor.execute(f"INSERT INTO {main_table} (col2, col3) VALUES ('test', 100)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {log_table} WHERE col2 = 'before_insert'")
    assert db_cursor.fetchone()['count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "TIMESTAMP DEFAULT NOW()"]}
    ]
}], indirect=True)
def test_after_insert_trigger(create_tables, db_cursor):
    """Test AFTER INSERT trigger."""
    main_table, log_table = create_tables
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_after_insert() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES ('after_insert');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_after_insert 
        AFTER INSERT ON {main_table}
        FOR EACH ROW EXECUTE FUNCTION log_after_insert()
    """)
    
    db_cursor.execute(f"INSERT INTO {main_table} (col2, col3) VALUES ('test', 100)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {log_table} WHERE col2 = 'after_insert'")
    assert db_cursor.fetchone()['count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "TIMESTAMP DEFAULT NOW()"]}
    ]
}], indirect=True)
def test_before_update_trigger(create_tables, db_cursor):
    """Test BEFORE UPDATE trigger."""
    main_table, log_table = create_tables
    
    db_cursor.execute(f"INSERT INTO {main_table} (col2, col3) VALUES ('original', 100)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_before_update() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES (OLD.col2 || '_to_' || NEW.col2);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_before_update 
        BEFORE UPDATE ON {main_table}
        FOR EACH ROW EXECUTE FUNCTION log_before_update()
    """)
    
    db_cursor.execute(f"UPDATE {main_table} SET col2 = 'updated'")
    
    db_cursor.execute(f"SELECT col2 FROM {log_table}")
    result = db_cursor.fetchone()
    assert result['col2'] == 'original_to_updated'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "TIMESTAMP DEFAULT NOW()"]}
    ]
}], indirect=True)
def test_after_update_trigger(create_tables, db_cursor):
    """Test AFTER UPDATE trigger."""
    main_table, log_table = create_tables
    
    db_cursor.execute(f"INSERT INTO {main_table} (col2, col3) VALUES ('original', 100)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_after_update() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES ('updated');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_after_update 
        AFTER UPDATE ON {main_table}
        FOR EACH ROW EXECUTE FUNCTION log_after_update()
    """)
    
    db_cursor.execute(f"UPDATE {main_table} SET col2 = 'new_value'")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {log_table} WHERE col2 = 'updated'")
    assert db_cursor.fetchone()['count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "TIMESTAMP DEFAULT NOW()"]}
    ]
}], indirect=True)
def test_before_delete_trigger(create_tables, db_cursor):
    """Test BEFORE DELETE trigger."""
    main_table, log_table = create_tables
    
    db_cursor.execute(f"INSERT INTO {main_table} (col2, col3) VALUES ('to_delete', 100)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_before_delete() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES (OLD.col2);
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_before_delete 
        BEFORE DELETE ON {main_table}
        FOR EACH ROW EXECUTE FUNCTION log_before_delete()
    """)
    
    db_cursor.execute(f"DELETE FROM {main_table} WHERE col2 = 'to_delete'")
    
    db_cursor.execute(f"SELECT col2 FROM {log_table}")
    assert db_cursor.fetchone()['col2'] == 'to_delete'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]},
        {"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "TIMESTAMP DEFAULT NOW()"]}
    ]
}], indirect=True)
def test_after_delete_trigger(create_tables, db_cursor):
    """Test AFTER DELETE trigger."""
    main_table, log_table = create_tables
    
    db_cursor.execute(f"INSERT INTO {main_table} (col2, col3) VALUES ('to_delete', 100)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_after_delete() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES ('deleted');
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_after_delete 
        AFTER DELETE ON {main_table}
        FOR EACH ROW EXECUTE FUNCTION log_after_delete()
    """)
    
    db_cursor.execute(f"DELETE FROM {main_table}")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {log_table} WHERE col2 = 'deleted'")
    assert db_cursor.fetchone()['count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_trigger_prevents_operation(create_tables, db_cursor):
    """Test trigger that prevents an operation."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION prevent_delete() RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.col3 > 100 THEN
                RAISE EXCEPTION 'Cannot delete rows where col3 > 100';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_prevent_delete 
        BEFORE DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION prevent_delete()
    """)
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value1', 50)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value2', 150)")
    
    db_cursor.execute(f"DELETE FROM {table_name} WHERE col3 = 50")
    
    with pytest.raises(psycopg2.DatabaseError):
        db_cursor.execute(f"DELETE FROM {table_name} WHERE col3 = 150")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 4, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT", "TIMESTAMP"]}]
}], indirect=True)
def test_trigger_modifies_new_value(create_tables, db_cursor):
    """Test trigger that modifies NEW values."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION auto_timestamp() RETURNS TRIGGER AS $$
        BEGIN
            NEW.col4 = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_auto_timestamp 
        BEFORE INSERT ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION auto_timestamp()
    """)
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test', 100)")
    
    db_cursor.execute(f"SELECT col4 FROM {table_name}")
    result = db_cursor.fetchone()
    assert result['col4'] is not None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_statement_level_trigger(create_tables, db_cursor):
    """Test statement-level trigger."""
    table_name = create_tables[0]
    counter_table = f"{table_name}_counter"
    
    db_cursor.execute(f"CREATE TABLE {counter_table} (count INT DEFAULT 0)")
    db_cursor.execute(f"INSERT INTO {counter_table} (count) VALUES (0)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION increment_counter() RETURNS TRIGGER AS $$
        BEGIN
            UPDATE {counter_table} SET count = count + 1;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_statement 
        AFTER INSERT ON {table_name}
        FOR EACH STATEMENT EXECUTE FUNCTION increment_counter()
    """)
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i})")
    
    db_cursor.execute(f"SELECT count FROM {counter_table}")
    assert db_cursor.fetchone()['count'] == 5
    
    db_cursor.execute(f"DROP TABLE {counter_table}")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_disable_enable_trigger(create_tables, db_cursor):
    """Test disabling and enabling trigger."""
    table_name = create_tables[0]
    counter_table = f"{table_name}_trigger_counter"
    
    db_cursor.execute(f"CREATE TABLE {counter_table} (count INT DEFAULT 0)")
    db_cursor.execute(f"INSERT INTO {counter_table} (count) VALUES (0)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION count_inserts() RETURNS TRIGGER AS $$
        BEGIN
            UPDATE {counter_table} SET count = count + 1;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_count 
        AFTER INSERT ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION count_inserts()
    """)
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test1', 1)")
    
    db_cursor.execute(f"ALTER TABLE {table_name} DISABLE TRIGGER trigger_count")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test2', 2)")
    
    db_cursor.execute(f"SELECT count FROM {counter_table}")
    assert db_cursor.fetchone()['count'] == 1
    
    db_cursor.execute(f"ALTER TABLE {table_name} ENABLE TRIGGER trigger_count")
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test3', 3)")
    
    db_cursor.execute(f"SELECT count FROM {counter_table}")
    assert db_cursor.fetchone()['count'] == 2
    
    db_cursor.execute(f"DROP TABLE {counter_table}")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_drop_trigger(create_tables, db_cursor):
    """Test dropping trigger."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION dummy_function() RETURNS TRIGGER AS $$
        BEGIN
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_to_drop 
        BEFORE INSERT ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION dummy_function()
    """)
    
    db_cursor.execute(f"""
        SELECT tgname 
        FROM pg_trigger 
        WHERE tgname = 'trigger_to_drop'
    """)
    assert db_cursor.fetchone() is not None
    
    db_cursor.execute(f"DROP TRIGGER trigger_to_drop ON {table_name}")
    
    db_cursor.execute(f"""
        SELECT tgname 
        FROM pg_trigger 
        WHERE tgname = 'trigger_to_drop'
    """)
    assert db_cursor.fetchone() is None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_conditional_trigger_when_clause(create_tables, db_cursor):
    """Test trigger with WHEN condition."""
    table_name = create_tables[0]
    log_table = f"{table_name}_log"
    
    db_cursor.execute(f"CREATE TABLE {log_table} (col2 VARCHAR(100))")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_high_values() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (col2) VALUES (NEW.col2);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_conditional 
        AFTER INSERT ON {table_name}
        FOR EACH ROW 
        WHEN (NEW.col3 > 100)
        EXECUTE FUNCTION log_high_values()
    """)
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('low', 50)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('high', 150)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {log_table}")
    assert db_cursor.fetchone()['count'] == 1
    
    db_cursor.execute(f"DROP TABLE {log_table}")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_trigger_with_tg_op(create_tables, db_cursor):
    """Test trigger using TG_OP variable."""
    table_name = create_tables[0]
    log_table = f"{table_name}_op_log"
    
    db_cursor.execute(f"CREATE TABLE {log_table} (operation VARCHAR(50))")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION log_operation() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {log_table} (operation) VALUES (TG_OP);
            RETURN COALESCE(NEW, OLD);
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_all_ops 
        AFTER INSERT OR UPDATE OR DELETE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION log_operation()
    """)
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test', 1)")
    db_cursor.execute(f"SELECT col1 FROM {table_name}")
    row_id = db_cursor.fetchone()['col1']
    
    db_cursor.execute(f"UPDATE {table_name} SET col3 = 2 WHERE col1 = {row_id}")
    db_cursor.execute(f"DELETE FROM {table_name} WHERE col1 = {row_id}")
    
    db_cursor.execute(f"SELECT operation FROM {log_table} ORDER BY operation")
    operations = [row['operation'] for row in db_cursor.fetchall()]
    
    assert set(operations) == {'INSERT', 'UPDATE', 'DELETE'}
    
    db_cursor.execute(f"DROP TABLE {log_table}")


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_instead_of_trigger_on_view(create_tables, db_cursor):
    """Test INSTEAD OF trigger on view."""
    table_name = create_tables[0]
    view_name = f"{table_name}_view"
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('original', 1)")
    
    db_cursor.execute(f"CREATE VIEW {view_name} AS SELECT col1, col2, col3 FROM {table_name}")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION handle_view_insert() RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO {table_name} (col2, col3) VALUES (NEW.col2, NEW.col3 * 10);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute(f"""
        CREATE TRIGGER trigger_instead_of 
        INSTEAD OF INSERT ON {view_name}
        FOR EACH ROW EXECUTE FUNCTION handle_view_insert()
    """)
    
    db_cursor.execute(f"INSERT INTO {view_name} (col2, col3) VALUES ('test', 5)")
    
    db_cursor.execute(f"SELECT col3 FROM {table_name} WHERE col2 = 'test'")
    assert db_cursor.fetchone()['col3'] == 50
    
    db_cursor.execute(f"DROP VIEW {view_name}")


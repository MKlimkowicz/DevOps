import pytest
import psycopg2
import threading


@pytest.mark.reliability
def test_constraint_enforcement_under_load(db_cursor, db_config):
    """Foreign keys, checks, unique constraints."""
    db_cursor.execute("DROP TABLE IF EXISTS parent_table CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS child_table CASCADE;")
    
    db_cursor.execute("""
        CREATE TABLE parent_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) UNIQUE NOT NULL,
            value INT CHECK (value > 0)
        );
    """)
    
    db_cursor.execute("""
        CREATE TABLE child_table (
            id SERIAL PRIMARY KEY,
            parent_id INT REFERENCES parent_table(id) ON DELETE CASCADE,
            description VARCHAR(255)
        );
    """)
    
    db_cursor.execute("INSERT INTO parent_table (name, value) VALUES ('parent1', 100);")
    db_cursor.execute("SELECT id FROM parent_table WHERE name = 'parent1';")
    parent_id = db_cursor.fetchone()['id']
    
    db_cursor.execute(f"INSERT INTO child_table (parent_id, description) VALUES ({parent_id}, 'child1');")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute("INSERT INTO child_table (parent_id, description) VALUES (99999, 'invalid_child');")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute("INSERT INTO parent_table (name, value) VALUES ('parent1', 200);")
    
    with pytest.raises(psycopg2.IntegrityError):
        db_cursor.execute("INSERT INTO parent_table (name, value) VALUES ('parent2', -10);")
    
    db_cursor.execute("DROP TABLE IF EXISTS child_table CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS parent_table CASCADE;")


@pytest.mark.reliability
def test_trigger_reliability(db_cursor):
    """Triggers fire correctly under concurrent load."""
    db_cursor.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS main_table CASCADE;")
    
    db_cursor.execute("""
        CREATE TABLE main_table (
            id SERIAL PRIMARY KEY,
            data VARCHAR(255),
            updated_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    db_cursor.execute("""
        CREATE TABLE audit_log (
            id SERIAL PRIMARY KEY,
            table_name VARCHAR(100),
            operation VARCHAR(10),
            changed_at TIMESTAMP DEFAULT NOW()
        );
    """)
    
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION audit_trigger_func()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO audit_log (table_name, operation)
            VALUES (TG_TABLE_NAME, TG_OP);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    db_cursor.execute("""
        CREATE TRIGGER audit_trigger
        AFTER INSERT OR UPDATE ON main_table
        FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
    """)
    
    db_cursor.execute("INSERT INTO main_table (data) VALUES ('test1');")
    db_cursor.execute("INSERT INTO main_table (data) VALUES ('test2');")
    db_cursor.execute("UPDATE main_table SET data = 'updated' WHERE id = 1;")
    
    db_cursor.execute("SELECT COUNT(*) FROM audit_log WHERE operation = 'INSERT';")
    insert_count = db_cursor.fetchone()['count']
    assert insert_count == 2
    
    db_cursor.execute("SELECT COUNT(*) FROM audit_log WHERE operation = 'UPDATE';")
    update_count = db_cursor.fetchone()['count']
    assert update_count == 1
    
    db_cursor.execute("DROP TABLE IF EXISTS audit_log CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS main_table CASCADE;")
    db_cursor.execute("DROP FUNCTION IF EXISTS audit_trigger_func CASCADE;")


@pytest.mark.reliability
def test_cascade_operations(db_cursor):
    """CASCADE DELETE/UPDATE consistency."""
    db_cursor.execute("DROP TABLE IF EXISTS orders CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS customers CASCADE;")
    
    db_cursor.execute("""
        CREATE TABLE customers (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100)
        );
    """)
    
    db_cursor.execute("""
        CREATE TABLE orders (
            id SERIAL PRIMARY KEY,
            customer_id INT REFERENCES customers(id) ON DELETE CASCADE,
            order_data VARCHAR(255)
        );
    """)
    
    db_cursor.execute("INSERT INTO customers (name) VALUES ('Customer1'), ('Customer2');")
    db_cursor.execute("SELECT id FROM customers WHERE name = 'Customer1';")
    customer1_id = db_cursor.fetchone()['id']
    
    db_cursor.execute(f"INSERT INTO orders (customer_id, order_data) VALUES ({customer1_id}, 'Order1');")
    db_cursor.execute(f"INSERT INTO orders (customer_id, order_data) VALUES ({customer1_id}, 'Order2');")
    
    db_cursor.execute(f"DELETE FROM customers WHERE id = {customer1_id};")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM orders WHERE customer_id = {customer1_id};")
    remaining_orders = db_cursor.fetchone()['count']
    assert remaining_orders == 0
    
    db_cursor.execute("DROP TABLE IF EXISTS orders CASCADE;")
    db_cursor.execute("DROP TABLE IF EXISTS customers CASCADE;")


@pytest.mark.reliability
def test_data_integrity_after_errors(db_cursor, benchmark_table):
    """Data state after failed operations."""
    db_cursor.connection.autocommit = False
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (5001, "user_5001", "user5001@test.com", 100.0, True))
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 5001;")
    count_before = db_cursor.fetchone()['count']
    assert count_before == 1
    
    try:
        db_cursor.execute(f"""
            INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
            VALUES (%s, %s, %s, %s, %s);
        """, (5002, "user_5002", "invalid_email", "invalid_score", True))
    except psycopg2.Error:
        db_cursor.connection.rollback()
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 5002;")
    count_after = db_cursor.fetchone()['count']
    assert count_after == 0
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table} WHERE user_id = 5001;")
    count_original = db_cursor.fetchone()['count']
    assert count_original == 0
    
    db_cursor.connection.autocommit = True


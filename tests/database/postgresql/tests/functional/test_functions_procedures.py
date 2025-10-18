import pytest
import psycopg2


def test_create_simple_function(db_cursor):
    """Test creating a simple function."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION add_numbers(a INT, b INT) RETURNS INT AS $$
        BEGIN
            RETURN a + b;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT add_numbers(5, 3) as result")
    assert db_cursor.fetchone()['result'] == 8


def test_function_with_default_parameter(db_cursor):
    """Test function with default parameter value."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION multiply(a INT, b INT DEFAULT 2) RETURNS INT AS $$
        BEGIN
            RETURN a * b;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT multiply(5) as result")
    assert db_cursor.fetchone()['result'] == 10
    
    db_cursor.execute("SELECT multiply(5, 3) as result")
    assert db_cursor.fetchone()['result'] == 15


def test_function_returning_record(db_cursor):
    """Test function returning a record."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION get_person_info() 
        RETURNS TABLE(name VARCHAR, age INT) AS $$
        BEGIN
            RETURN QUERY SELECT 'John'::VARCHAR, 30::INT;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT * FROM get_person_info()")
    result = db_cursor.fetchone()
    
    assert result['name'] == 'John'
    assert result['age'] == 30


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_function_with_table_query(create_tables, db_cursor):
    """Test function that queries a table."""
    table_name = create_tables[0]
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i * 10})")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION count_rows() RETURNS INT AS $$
        DECLARE
            row_count INT;
        BEGIN
            SELECT COUNT(*) INTO row_count FROM {table_name};
            RETURN row_count;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT count_rows() as result")
    assert db_cursor.fetchone()['result'] == 5


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_function_with_out_parameter(create_tables, db_cursor):
    """Test function with OUT parameter."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test', 100)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION get_stats(OUT total INT, OUT avg_val NUMERIC) AS $$
        BEGIN
            SELECT COUNT(*), AVG(col3) INTO total, avg_val FROM {table_name};
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT * FROM get_stats()")
    result = db_cursor.fetchone()
    
    assert result['total'] == 1
    assert result['avg_val'] == 100


def test_function_with_if_condition(db_cursor):
    """Test function with IF/ELSE condition."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION check_positive(num INT) RETURNS VARCHAR AS $$
        BEGIN
            IF num > 0 THEN
                RETURN 'positive';
            ELSIF num < 0 THEN
                RETURN 'negative';
            ELSE
                RETURN 'zero';
            END IF;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT check_positive(5) as result")
    assert db_cursor.fetchone()['result'] == 'positive'
    
    db_cursor.execute("SELECT check_positive(-5) as result")
    assert db_cursor.fetchone()['result'] == 'negative'
    
    db_cursor.execute("SELECT check_positive(0) as result")
    assert db_cursor.fetchone()['result'] == 'zero'


def test_function_with_loop(db_cursor):
    """Test function with loop."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION factorial(n INT) RETURNS BIGINT AS $$
        DECLARE
            result BIGINT := 1;
            i INT;
        BEGIN
            FOR i IN 1..n LOOP
                result := result * i;
            END LOOP;
            RETURN result;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT factorial(5) as result")
    assert db_cursor.fetchone()['result'] == 120


def test_function_with_while_loop(db_cursor):
    """Test function with WHILE loop."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION sum_up_to(n INT) RETURNS INT AS $$
        DECLARE
            result INT := 0;
            i INT := 1;
        BEGIN
            WHILE i <= n LOOP
                result := result + i;
                i := i + 1;
            END LOOP;
            RETURN result;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT sum_up_to(10) as result")
    assert db_cursor.fetchone()['result'] == 55


def test_function_with_exception_handling(db_cursor):
    """Test function with exception handling."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION safe_divide(a NUMERIC, b NUMERIC) RETURNS NUMERIC AS $$
        BEGIN
            RETURN a / b;
        EXCEPTION
            WHEN division_by_zero THEN
                RETURN NULL;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT safe_divide(10, 2) as result")
    assert db_cursor.fetchone()['result'] == 5
    
    db_cursor.execute("SELECT safe_divide(10, 0) as result")
    assert db_cursor.fetchone()['result'] is None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_function_returning_setof(create_tables, db_cursor):
    """Test function returning SETOF records."""
    table_name = create_tables[0]
    
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('value{i}', {i * 10})")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION get_high_values(threshold INT) 
        RETURNS SETOF {table_name} AS $$
        BEGIN
            RETURN QUERY SELECT * FROM {table_name} WHERE col3 > threshold;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT * FROM get_high_values(20)")
    results = db_cursor.fetchall()
    
    assert len(results) == 2


def test_variadic_function(db_cursor):
    """Test function with VARIADIC parameter."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION sum_all(VARIADIC numbers INT[]) RETURNS INT AS $$
        DECLARE
            total INT := 0;
            num INT;
        BEGIN
            FOREACH num IN ARRAY numbers LOOP
                total := total + num;
            END LOOP;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT sum_all(1, 2, 3, 4, 5) as result")
    assert db_cursor.fetchone()['result'] == 15


def test_function_with_sql_language(db_cursor):
    """Test function using SQL language."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION square(n INT) RETURNS INT AS $$
            SELECT n * n;
        $$ LANGUAGE sql
    """)
    
    db_cursor.execute("SELECT square(7) as result")
    assert db_cursor.fetchone()['result'] == 49


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_procedure_basic(create_tables, db_cursor):
    """Test basic stored procedure."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"""
        CREATE OR REPLACE PROCEDURE insert_data(name VARCHAR, value INT) AS $$
        BEGIN
            INSERT INTO {table_name} (col2, col3) VALUES (name, value);
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("CALL insert_data('test', 100)")
    
    db_cursor.execute(f"SELECT col2, col3 FROM {table_name}")
    result = db_cursor.fetchone()
    
    assert result['col2'] == 'test'
    assert result['col3'] == 100


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_procedure_with_inout_parameter(create_tables, db_cursor):
    """Test procedure with INOUT parameter."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test', 100)")
    
    db_cursor.execute(f"""
        CREATE OR REPLACE PROCEDURE get_and_increment(INOUT counter INT) AS $$
        BEGIN
            SELECT COUNT(*) INTO counter FROM {table_name};
            counter := counter + 1;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("CALL get_and_increment(0)")
    result = db_cursor.fetchone()
    
    assert result['counter'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(100)", "INT"]}]
}], indirect=True)
def test_procedure_with_transaction_control(create_tables, db_cursor):
    """Test procedure with COMMIT/ROLLBACK."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"""
        CREATE OR REPLACE PROCEDURE safe_insert(name VARCHAR, value INT, do_commit BOOLEAN) AS $$
        BEGIN
            INSERT INTO {table_name} (col2, col3) VALUES (name, value);
            IF do_commit THEN
                COMMIT;
            ELSE
                ROLLBACK;
            END IF;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("CALL safe_insert('test1', 100, true)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    assert db_cursor.fetchone()['count'] == 1


def test_drop_function(db_cursor):
    """Test dropping a function."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION temp_function() RETURNS INT AS $$
        BEGIN
            RETURN 42;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("""
        SELECT proname FROM pg_proc WHERE proname = 'temp_function'
    """)
    assert db_cursor.fetchone() is not None
    
    db_cursor.execute("DROP FUNCTION temp_function()")
    
    db_cursor.execute("""
        SELECT proname FROM pg_proc WHERE proname = 'temp_function'
    """)
    assert db_cursor.fetchone() is None


def test_drop_procedure(db_cursor):
    """Test dropping a procedure."""
    db_cursor.execute("""
        CREATE OR REPLACE PROCEDURE temp_procedure() AS $$
        BEGIN
            NULL;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("""
        SELECT proname FROM pg_proc WHERE proname = 'temp_procedure'
    """)
    assert db_cursor.fetchone() is not None
    
    db_cursor.execute("DROP PROCEDURE temp_procedure()")
    
    db_cursor.execute("""
        SELECT proname FROM pg_proc WHERE proname = 'temp_procedure'
    """)
    assert db_cursor.fetchone() is None


def test_function_with_composite_type(db_cursor):
    """Test function returning composite type."""
    db_cursor.execute("""
        CREATE TYPE person_type AS (name VARCHAR, age INT)
    """)
    
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION create_person(p_name VARCHAR, p_age INT) 
        RETURNS person_type AS $$
        DECLARE
            result person_type;
        BEGIN
            result.name := p_name;
            result.age := p_age;
            RETURN result;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT * FROM create_person('Alice', 25)")
    result = db_cursor.fetchone()
    
    assert result['name'] == 'Alice'
    assert result['age'] == 25
    
    db_cursor.execute("DROP FUNCTION create_person(VARCHAR, INT)")
    db_cursor.execute("DROP TYPE person_type")


def test_function_with_array_parameter(db_cursor):
    """Test function with array parameter."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION sum_array(arr INT[]) RETURNS INT AS $$
        DECLARE
            total INT := 0;
            num INT;
        BEGIN
            FOREACH num IN ARRAY arr LOOP
                total := total + num;
            END LOOP;
            RETURN total;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT sum_array(ARRAY[1, 2, 3, 4, 5]) as result")
    assert db_cursor.fetchone()['result'] == 15


def test_function_immutable_volatile(db_cursor):
    """Test function with different volatility categories."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION get_constant() RETURNS INT AS $$
        BEGIN
            RETURN 42;
        END;
        $$ LANGUAGE plpgsql IMMUTABLE
    """)
    
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION get_random() RETURNS FLOAT AS $$
        BEGIN
            RETURN random();
        END;
        $$ LANGUAGE plpgsql VOLATILE
    """)
    
    db_cursor.execute("SELECT get_constant() as result")
    assert db_cursor.fetchone()['result'] == 42
    
    db_cursor.execute("SELECT get_random() as result")
    result = db_cursor.fetchone()['result']
    assert 0 <= result <= 1
    
    db_cursor.execute("DROP FUNCTION get_constant()")
    db_cursor.execute("DROP FUNCTION get_random()")


def test_recursive_function(db_cursor):
    """Test recursive function."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION fibonacci(n INT) RETURNS INT AS $$
        BEGIN
            IF n <= 1 THEN
                RETURN n;
            ELSE
                RETURN fibonacci(n-1) + fibonacci(n-2);
            END IF;
        END;
        $$ LANGUAGE plpgsql
    """)
    
    db_cursor.execute("SELECT fibonacci(7) as result")
    assert db_cursor.fetchone()['result'] == 13
    
    db_cursor.execute("DROP FUNCTION fibonacci(INT)")


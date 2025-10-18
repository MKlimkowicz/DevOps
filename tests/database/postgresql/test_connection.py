import pytest


def test_simple_select_one(db_cursor):
    """Test basic PostgreSQL connectivity with SELECT 1."""
    db_cursor.execute("SELECT 1;")
    result = db_cursor.fetchone()
    assert result is not None
    assert list(result.values())[0] == 1 

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 3,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(255)" ]},
        {"num_columns": 4, "column_types": ["BOOLEAN", "DATE", "FLOAT", "TEXT"]},
        {"num_columns": 10, "column_types": ["SMALLINT", "BIGINT", "SERIAL", "NUMERIC", "REAL", "DOUBLE PRECISION", "CHAR(5)", "TIMESTAMP", "TIME", "JSON"]}
    ]
}], indirect=True)
def test_create_multiple_tables(create_tables, db_cursor):
    """Test creating multiple tables with varying columns and data types."""
    table_names = create_tables
    for table in table_names:
        db_cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table}');")
        result = db_cursor.fetchone()
        assert result['exists'] == True 

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]},
        {"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 50}], indirect=True)
@pytest.mark.parametrize("generate_floats", [{"num_rows": 50}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 50}], indirect=True)
@pytest.mark.parametrize("generate_timestamps", [{"num_rows": 50}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 50}], indirect=True)
@pytest.mark.parametrize("generate_bools", [{"num_rows": 50}], indirect=True)
def test_insert_data_into_tables(create_tables, generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools, db_cursor):
    """Test creating 2 tables with columns for each data type and inserting 50 rows into each."""
    table_names = create_tables
    data = [generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools]
    for table in table_names:
        for row in zip(*data):
            placeholders = ', '.join(['%s'] * len(row))
            insert_sql = f"INSERT INTO {table} (col1, col2, col3, col4, col5, col6) VALUES ({placeholders});"
            db_cursor.execute(insert_sql, row)
        db_cursor.execute(f"SELECT COUNT(*) FROM {table};")
        result = db_cursor.fetchone()
        assert result['count'] == 50
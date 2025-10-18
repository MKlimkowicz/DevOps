
import pytest
from datetime import datetime, date, timedelta
import psycopg2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_insert_single_row(create_tables, db_cursor):
    table_name = create_tables[0]
    insert_sql = f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
    values = (42, 3.14, "test_string", datetime.now(), date.today(), True)
    db_cursor.execute(insert_sql, values)
    db_cursor.execute(f"SELECT * FROM {table_name};")
    result = db_cursor.fetchone()
    assert tuple(result.values()) == values

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools", [(
    {"num_rows": 10}, {"num_rows": 10}, {"num_rows": 10}, {"num_rows": 10}, {"num_rows": 10}, {"num_rows": 10}
)], indirect=True)
def test_insert_multiple_rows(create_tables, generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools))
    for row in data:
        insert_sql = f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
        db_cursor.execute(insert_sql, row)
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    assert db_cursor.fetchone()['count'] == 10

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_insert_with_null_values(create_tables, db_cursor):
    table_name = create_tables[0]
    insert_sql = f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
    values_with_nulls = (None, 3.14, None, datetime.now(), None, True)
    db_cursor.execute(insert_sql, values_with_nulls)
    db_cursor.execute(f"SELECT * FROM {table_name} WHERE col1 IS NULL AND col3 IS NULL AND col5 IS NULL;")
    result = db_cursor.fetchone()
    assert result is not None
    assert result['col1'] is None
    assert result['col3'] is None
    assert result['col5'] is None

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools", [(
    {"num_rows": 5}, {"num_rows": 5}, {"num_rows": 5}, {"num_rows": 5}, {"num_rows": 5}, {"num_rows": 5}
)], indirect=True)
def test_select_all_rows(create_tables, generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_ints, generate_floats, generate_strings, generate_timestamps, generate_dates, generate_bools))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
, row)
    db_cursor.execute(f"SELECT * FROM {table_name};")
    results = db_cursor.fetchall()
    assert len(results) == 5
    for res, orig in zip(results, data):
        assert tuple(res.values()) == orig

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints, generate_bools", [(
    {"num_rows": 5}, {"num_rows": 5}
)], indirect=True)
def test_select_specific_columns(create_tables, generate_ints, generate_bools, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_ints, [0]*5, [""] *5, [datetime.now()]*5, [date.today()]*5, generate_bools))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
, row)
    db_cursor.execute(f"SELECT col1, col6 FROM {table_name};")
    results = db_cursor.fetchall()
    assert len(results) == 5
    for res, (int_val, bool_val) in zip(results, zip(generate_ints, generate_bools)):
        assert res['col1'] == int_val
        assert res['col6'] == bool_val

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints, generate_bools", [(
    {"num_rows": 5}, {"num_rows": 5}
)], indirect=True)
def test_select_with_where_clause(create_tables, generate_ints, generate_bools, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_ints, [0.0]*5, [""] *5, [datetime.now()]*5, [date.today()]*5, generate_bools))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
, row)
    threshold = generate_ints[2]
    db_cursor.execute(f"SELECT * FROM {table_name} WHERE col1 > %s OR col6 = TRUE;"
, (threshold,))
    results = db_cursor.fetchall()
    expected = [row for row in data if row[0] > threshold or row[5] is True]
    assert len(results) == len(expected)
    for res, exp_row in zip(results, expected):
        assert tuple(res.values()) == exp_row

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_update_single_row(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (1, 1.0, 'old', NOW(), CURRENT_DATE, FALSE);")
    db_cursor.execute(f"UPDATE {table_name} SET col2 = 2.0, col3 = 'new' WHERE col1 = 1;")
    db_cursor.execute(f"SELECT col2, col3 FROM {table_name} WHERE col1 = 1;")
    result = db_cursor.fetchone()
    assert result['col2'] == 2.0
    assert result['col3'] == 'new'

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 5}], indirect=True)
def test_update_multiple_rows_with_condition(create_tables, generate_dates, db_cursor):
    table_name = create_tables[0]
    data = [(i, 0.0, '', datetime.now(), gen_date, False) for i, gen_date in enumerate(generate_dates, 1)]
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
, row)
    threshold_date = generate_dates[2]
    db_cursor.execute(f"UPDATE {table_name} SET col6 = TRUE WHERE col5 > %s;"
, (threshold_date,))
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col6 = TRUE;")
    updated_count = db_cursor.fetchone()['count']
    expected_count = sum(1 for d in generate_dates if d > threshold_date)
    assert updated_count == expected_count

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_update_to_null(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (1, 1.0, 'value', NOW(), CURRENT_DATE, TRUE);")
    db_cursor.execute(f"UPDATE {table_name} SET col3 = NULL WHERE col1 = 1;")
    db_cursor.execute(f"SELECT col3 FROM {table_name} WHERE col1 = 1;")
    result = db_cursor.fetchone()
    assert result['col3'] is None

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
def test_delete_single_row(create_tables, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = [(gen_int, 0.0, '', datetime.now(), date.today(), False) for gen_int in generate_ints]
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
, row)
    unique_int = generate_ints[0]
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col1 = %s;"
, (unique_int,))
    assert db_cursor.fetchone()['count'] == 1
    db_cursor.execute(f"DELETE FROM {table_name} WHERE col1 = %s;"
, (unique_int,))
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    assert db_cursor.fetchone()['count'] == 4

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_bools", [{"num_rows": 5}], indirect=True)
def test_delete_multiple_rows_with_condition(create_tables, generate_bools, db_cursor):
    table_name = create_tables[0]
    data = [(i, 0.0, '', datetime.now(), date.today(), gen_bool) for i, gen_bool in enumerate(generate_bools, 1)]
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES (%s, %s, %s, %s, %s, %s);"
, row)
    db_cursor.execute(f"DELETE FROM {table_name} WHERE col6 = FALSE;")
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    remaining = db_cursor.fetchone()['count']
    expected_remaining = sum(1 for b in generate_bools if b is True)
    assert remaining == expected_remaining

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_delete_all_rows(create_tables, db_cursor):
    table_name = create_tables[0]
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4, col5, col6) VALUES ({i}, 0.0, 'test', NOW(), CURRENT_DATE, TRUE);")
    db_cursor.execute(f"DELETE FROM {table_name};")
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    assert db_cursor.fetchone()['count'] == 0

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_insert_invalid_data_types(create_tables, db_cursor):
    table_name = create_tables[0]
    insert_sql = f"INSERT INTO {table_name} (col1) VALUES (%s);"
    with pytest.raises(psycopg2.Error):
        db_cursor.execute(insert_sql, ("invalid_string",))

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_update_with_invalid_data(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (1);")
    with pytest.raises(psycopg2.Error):
        db_cursor.execute(f"UPDATE {table_name} SET col1 = 'invalid' WHERE col1 = 1;")

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_select_on_empty_table(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"SELECT * FROM {table_name};")
    assert len(db_cursor.fetchall()) == 0

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 6, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(255)", "TIMESTAMP", "DATE", "BOOLEAN"]}]
}], indirect=True)
def test_delete_on_empty_table(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"DELETE FROM {table_name};")
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
    assert db_cursor.fetchone()['count'] == 0

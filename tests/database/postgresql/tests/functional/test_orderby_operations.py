import pytest
from datetime import datetime, date, timedelta
import psycopg2
import random

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
def test_order_by_single_column_ascending(create_tables, generate_ints, db_cursor):
    table_name = create_tables[0]
    # Shuffle to ensure unsorted insertion
    data = generate_ints[:]
    random.shuffle(data)
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1 FROM {table_name} ORDER BY col1 ASC;")
    results = [row['col1'] for row in db_cursor.fetchall()]
    expected = sorted(data)
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(255)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
def test_order_by_single_column_descending(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings[:]
    random.shuffle(data)
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1 FROM {table_name} ORDER BY col1 DESC;")
    results = [row['col1'] for row in db_cursor.fetchall()]
    expected = sorted(data, key=lambda s: s.lower(), reverse=True)
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_order_by_multiple_columns(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    categories = generate_strings[:3] * 3 + [generate_strings[4]]  # Some repeats
    sales = generate_ints[:10]
    data = list(zip(categories, sales))
    random.shuffle(data)
    for cat, sale in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", (cat, sale))
    db_cursor.execute(f"SELECT col1, col2 FROM {table_name} ORDER BY col1 ASC, col2 DESC;")
    results = [(row['col1'], row['col2']) for row in db_cursor.fetchall()]
    expected = sorted(data, key=lambda x: (x[0].lower(), -x[1]))
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
def test_order_by_with_nulls_last(create_tables, db_cursor):
    table_name = create_tables[0]
    data = [1, None, 3, None, 2]
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1 FROM {table_name} ORDER BY col1 ASC NULLS LAST;")
    results = [row['col1'] for row in db_cursor.fetchall()]
    expected = [1, 2, 3, None, None]
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
def test_order_by_with_nulls_first(create_tables, db_cursor):
    table_name = create_tables[0]
    data = [1, None, 3, None, 2]
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1 FROM {table_name} ORDER BY col1 ASC NULLS FIRST;")
    results = [row['col1'] for row in db_cursor.fetchall()]
    expected = [None, None, 1, 2, 3]
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
def test_order_by_with_limit_and_offset(create_tables, db_cursor):
    table_name = create_tables[0]
    data = [5, 3, 1, 7, 9, 2, 4, 6, 8, 10]
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1 FROM {table_name} ORDER BY col1 ASC LIMIT 5 OFFSET 3;")
    results = [row['col1'] for row in db_cursor.fetchall()]
    expected = [4, 5, 6, 7, 8]
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["TIMESTAMP"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_timestamps", [{"num_rows": 5}], indirect=True)
def test_order_by_on_datetime_columns(create_tables, generate_timestamps, db_cursor):
    table_name = create_tables[0]
    data = generate_timestamps[:]
    random.shuffle(data)
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1 FROM {table_name} ORDER BY col1 DESC;")
    results = [row['col1'] for row in db_cursor.fetchall()]
    expected = sorted(data, reverse=True)
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(255)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
def test_order_by_with_expressions(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings[:]
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, LENGTH(col1) AS len FROM {table_name} ORDER BY len ASC;")
    results = [(row['col1'], row['len']) for row in db_cursor.fetchall()]
    expected = sorted([(s, len(s)) for s in data], key=lambda x: x[1])
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_order_by_combined_with_group_by_and_aggregates(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    categories = generate_strings[:5] * 2
    sales = generate_ints[:10]
    data = list(zip(categories, sales))
    for cat, sale in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", (cat, sale))
    db_cursor.execute(f"SELECT col1, SUM(col2) AS total FROM {table_name} GROUP BY col1 ORDER BY total DESC;")
    results = [(row['col1'], row['total']) for row in db_cursor.fetchall()]
    from collections import defaultdict
    totals = defaultdict(int)
    for cat, sale in data:
        totals[cat] += sale
    expected = sorted(totals.items(), key=lambda x: -x[1])
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "INT"]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 3}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 6}], indirect=True)
def test_order_by_with_join(create_tables, generate_strings, generate_ints, db_cursor):
    left_table, right_table = create_tables
    left_data = list(zip([1,2,3], generate_strings))
    right_data = list(zip([1,2,3], generate_ints[:3])) + list(zip([1,2,3], generate_ints[3:]))
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1, l.col2 AS left_col2, r.col2 AS right_col2 FROM {left_table} l INNER JOIN {right_table} r ON l.col1 = r.col1 ORDER BY r.col2 ASC;")
    results = [(row['col1'], row['left_col2'], row['right_col2']) for row in db_cursor.fetchall()]
    joined_data = []
    for lid, lstr in left_data:
        for rid, rval in right_data:
            if lid == rid:
                joined_data.append((lid, lstr, rval))
    expected = sorted(joined_data, key=lambda x: x[2])
    assert results == expected

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
def test_order_by_on_empty_table(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"SELECT * FROM {table_name} ORDER BY col1 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 0

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["INT", "INT"]}]
}], indirect=True)
def test_order_by_with_all_identical_values(create_tables, db_cursor):
    table_name = create_tables[0]
    data = [(i+1, 42) for i in range(5)]
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, col2 FROM {table_name} ORDER BY col2 ASC;")
    results = [(row['col1'], row['col2']) for row in db_cursor.fetchall()]
    # Assuming stable sort preserves insertion order
    assert results == data
    # Also verify all col2 are 42
    assert all(r[1] == 42 for r in results)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
def test_invalid_order_by_non_existent_column(create_tables, db_cursor):
    table_name = create_tables[0]
    with pytest.raises(psycopg2.Error):
        db_cursor.execute(f"SELECT * FROM {table_name} ORDER BY fake_col;")

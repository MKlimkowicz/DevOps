import pytest
from datetime import datetime, date
import psycopg2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
def test_inner_join_matching_columns(create_tables, generate_ints, generate_strings, db_cursor):
    left_table, right_table = create_tables
    left_data = list(zip([1,2,3,6,7], generate_strings[:5]))  # Fixed IDs: 1-3 match, 6-7 no
    right_data = list(zip([1,2,3,8,9], generate_strings[:5]))  # Matching 1-3, 8-9 no
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1 AS left_id, l.col2 AS left_str, r.col2 AS right_str FROM {left_table} l INNER JOIN {right_table} r ON l.col1 = r.col1 ORDER BY l.col1 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 3  # Only matching IDs
    expected = sorted([(id, left_str, right_str) for id, left_str in left_data[:3] for _, right_str in right_data if id == _], key=lambda x: x[0])
    for res, exp in zip(results, expected):
        assert (res['left_id'], res['left_str'], res['right_str']) == exp

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 4}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 4}], indirect=True)
def test_left_join_with_nulls(create_tables, generate_ints, generate_strings, db_cursor):
    left_table, right_table = create_tables
    left_data = list(zip([1,2,3,4], generate_strings))  # 4 rows
    right_data = list(zip([1,2], generate_strings[:2]))  # Only 2 matching
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1 AS left_id, l.col2 AS left_str, r.col2 AS right_str FROM {left_table} l LEFT JOIN {right_table} r ON l.col1 = r.col1 ORDER BY l.col1 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 4
    for res in results[2:]:
        assert res['right_str'] is None

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 4}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 4}], indirect=True)
def test_right_join_with_nulls(create_tables, generate_ints, generate_strings, db_cursor):
    left_table, right_table = create_tables
    left_data = list(zip([1,2], generate_strings[:2]))
    right_data = list(zip([1,2,3,4], generate_strings))
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1 AS left_id, l.col2 AS left_str, r.col2 AS right_str FROM {left_table} l RIGHT JOIN {right_table} r ON l.col1 = r.col1 ORDER BY r.col1 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 4
    for res in results[2:]:
        assert res['left_str'] is None

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
def test_full_outer_join(create_tables, generate_ints, generate_strings, db_cursor):
    left_table, right_table = create_tables
    left_data = list(zip([1,2,3,4], generate_strings[:4]))  # 4 rows, overlap on 3-4
    right_data = list(zip([3,4,5], generate_strings[2:]))  # 3 rows, overlap on 3-4
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1 AS left_id, l.col2 AS left_str, r.col1 AS right_id, r.col2 AS right_str FROM {left_table} l FULL OUTER JOIN {right_table} r ON l.col1 = r.col1 ORDER BY COALESCE(l.col1, r.col1) ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 5  # 2 unique left, 1 unique right, 2 matches
    null_count = sum(1 for res in results if res['left_id'] is None or res['right_id'] is None)
    assert null_count == 3

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 1, "column_types": ["VARCHAR(50)" ]},
        {"num_columns": 1, "column_types": ["VARCHAR(50)" ]}
    ]
}], indirect=True)
def test_cross_join(create_tables, db_cursor):
    left_table, right_table = create_tables
    left_data = [('A'), ('B'), ('C')]
    right_data = [('X'), ('Y'), ('Z')]
    for val in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1) VALUES (%s);", val)
    for val in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1) VALUES (%s);", val)
    db_cursor.execute(f"SELECT l.col1 AS left_val, r.col1 AS right_val FROM {left_table} l CROSS JOIN {right_table} r;")
    results = db_cursor.fetchall()
    assert len(results) == 9

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "INT" ]}]  # employee_id, name, manager_id
}], indirect=True)
def test_self_join(create_tables, db_cursor):
    table_name = create_tables[0]
    data = [(1, 'CEO', None), (2, 'Manager', 1), (3, 'Employee', 2), (4, 'Employee2', 2)]
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    db_cursor.execute(f"SELECT e.col2 AS employee, m.col2 AS manager FROM {table_name} e LEFT JOIN {table_name} m ON e.col3 = m.col1;")
    results = db_cursor.fetchall()
    assert len(results) == 4
    assert results[0]['manager'] is None  # CEO has no manager
    assert results[1]['manager'] == 'CEO'

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DATE" ]},
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DATE" ]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 5}], indirect=True)
def test_join_with_multiple_conditions(create_tables, generate_dates, db_cursor):
    left_table, right_table = create_tables
    left_data = [(1, f'Left1', generate_dates[0]), (2, f'Left2', generate_dates[1]), (3, f'Left3', generate_dates[2]), (4, f'Left4', generate_dates[3]), (5, f'Left5', generate_dates[4])]
    right_data = [(1, f'Right1', generate_dates[0]), (2, f'Right2', generate_dates[1]), (3, f'Right3', generate_dates[2]), (4, f'Right4', generate_dates[3]), (5, f'Right5', generate_dates[4])]
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    threshold_date = generate_dates[2]
    db_cursor.execute(f"SELECT l.col1, l.col2, r.col2 FROM {left_table} l INNER JOIN {right_table} r ON l.col1 = r.col1 AND (l.col3 > %s OR r.col3 > %s) ORDER BY l.col1 ASC;", (threshold_date, threshold_date))
    results = db_cursor.fetchall()
    expected_count = sum(1 for i in range(5) if left_data[i][2] > threshold_date or right_data[i][2] > threshold_date)
    assert len(results) == expected_count

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
def test_join_with_aliases_and_column_selection(create_tables, db_cursor):
    left_table, right_table = create_tables
    data1 = [(1, 'A'), (2, 'B')]
    data2 = [(1, 'X'), (2, 'Y')]
    for row in data1:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in data2:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1 AS id, l.col2 AS left_name, r.col2 AS right_name FROM {left_table} AS l INNER JOIN {right_table} AS r ON l.col1 = r.col1 ORDER BY l.col1 ASC, r.col2 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 2
    assert all('id' in res and 'left_name' in res and 'right_name' in res for res in results)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["VARCHAR(50)", "INT" ]},
        {"num_columns": 2, "column_types": ["VARCHAR(50)", "INT" ]}
    ]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 3}], indirect=True)
def test_join_on_non_integer_columns(create_tables, generate_strings, db_cursor):
    left_table, right_table = create_tables
    left_data = list(zip(generate_strings, [1,2,3]))
    right_data = list(zip(generate_strings[:2], [4,5]))  # Match first 2
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1, l.col2, r.col2 FROM {left_table} l INNER JOIN {right_table} r ON l.col1 = r.col1 ORDER BY l.col1 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 1, "column_types": ["INT" ]},
        {"num_columns": 1, "column_types": ["INT" ]}
    ]
}], indirect=True)
def test_join_on_empty_tables(create_tables, db_cursor):
    left_table, right_table = create_tables
    for join_type in ['INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'FULL OUTER JOIN']:
        db_cursor.execute(f"SELECT COUNT(*) FROM {left_table} l {join_type} {right_table} r ON l.col1 = r.col1;")
        assert db_cursor.fetchone()['count'] == 0

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
def test_join_with_no_matches(create_tables, db_cursor):
    left_table, right_table = create_tables
    left_data = [(1, 'A'), (2, 'B')]
    right_data = [(3, 'C'), (4, 'D')]
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT COUNT(*) FROM {left_table} l INNER JOIN {right_table} r ON l.col1 = r.col1;")
    assert db_cursor.fetchone()['count'] == 0
    db_cursor.execute(f"SELECT COUNT(*) FROM {left_table} l LEFT JOIN {right_table} r ON l.col1 = r.col1;")
    assert db_cursor.fetchone()['count'] == 2  # All left with NULLs

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)" ]}
    ]
}], indirect=True)
def test_join_with_duplicate_matches(create_tables, db_cursor):
    left_table, right_table = create_tables
    left_data = [(1, 'A'), (2, 'B')]
    right_data = [(1, 'X'), (1, 'Y'), (2, 'Z')]
    for row in left_data:
        db_cursor.execute(f"INSERT INTO {left_table} (col1, col2) VALUES (%s, %s);", row)
    for row in right_data:
        db_cursor.execute(f"INSERT INTO {right_table} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT l.col1, l.col2, r.col2 FROM {left_table} l INNER JOIN {right_table} r ON l.col1 = r.col1 ORDER BY l.col1 ASC;")
    results = db_cursor.fetchall()
    assert len(results) == 3  # Duplicates for ID 1


import pytest
from datetime import date, timedelta
import psycopg2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
def test_group_by_single_column_with_count(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings[:5] + generate_strings[:5]
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1;")
    results = db_cursor.fetchall()
    assert len(results) == 5  # 5 unique
    for res in results:
        assert res['count'] == 2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["VARCHAR(50)", "DATE", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_group_by_multiple_columns_with_sum(create_tables, generate_strings, generate_dates, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_strings[:5] + generate_strings[:5], generate_dates[:5] + generate_dates[:5], generate_ints))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    db_cursor.execute(f"SELECT col1, col2, SUM(col3) AS total FROM {table_name} GROUP BY col1, col2;")
    results = db_cursor.fetchall()
    from collections import defaultdict
    expected = defaultdict(int)
    for cat, dt, val in data:
        expected[(cat, dt)] += val
    assert len(results) == len(expected)
    for res in results:
        key = (res['col1'], res['col2'])
        assert res['total'] == expected[key]

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_floats", [{"num_rows": 10}], indirect=True)
def test_group_by_with_avg_min_max(create_tables, generate_strings, generate_floats, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_strings[:5] + generate_strings[:5], generate_floats))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, AVG(col2) AS avg_val, MIN(col2) AS min_val, MAX(col2) AS max_val FROM {table_name} GROUP BY col1;")
    results = db_cursor.fetchall()
    from collections import defaultdict
    groups = defaultdict(list)
    for cat, val in data:
        groups[cat].append(val)
    assert len(results) == 5
    for res in results:
        cat = res['col1']
        vals = groups[cat]
        assert res['avg_val'] == pytest.approx(sum(vals) / len(vals), 0.01)
        assert res['min_val'] == min(vals)
        assert res['max_val'] == max(vals)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 12}], indirect=True)
def test_group_by_with_having_clause(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings[:3]*2 + generate_strings[3:6]*3
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1 HAVING COUNT(*) > 2;")
    results = db_cursor.fetchall()
    assert len(results) == 3
    for res in results:
        assert res['count'] == 3

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_group_by_with_order_by(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_strings[:5]*2, generate_ints))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, SUM(col2) AS total FROM {table_name} GROUP BY col1 ORDER BY total DESC;")
    results = db_cursor.fetchall()
    totals = {cat: sum(val for c, val in data if c == cat) for cat in set(generate_strings[:5])}
    sorted_totals = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    for res, (cat, total) in zip(results, sorted_totals):
        assert res['col1'] == cat
        assert res['total'] == total

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["TIMESTAMP", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_timestamps", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_group_by_on_date_time_columns(create_tables, generate_timestamps, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_timestamps, generate_ints))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT DATE(col1) AS day, COUNT(*) AS count FROM {table_name} GROUP BY day;")
    results = db_cursor.fetchall()
    from collections import defaultdict
    expected = defaultdict(int)
    for ts, _ in data:
        expected[ts.date()] += 1
    assert len(results) == len(expected)
    for res in results:
        assert res['count'] == expected[res['day']]

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
def test_group_by_with_null_values(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings + [None] * 3  # 5 non-null, 3 null
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1;")
    results = db_cursor.fetchall()
    null_group = [res for res in results if res['col1'] is None]
    assert len(null_group) == 1
    assert null_group[0]['count'] == 3

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_group_by_with_distinct_in_aggregates(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    categories = generate_strings[:5]
    unique_ints = sorted(set(generate_ints[:10]))  # Take 10 unique
    while len(unique_ints) < 10:  # If duplicates, add more
        unique_ints.append(max(unique_ints) + 1 if unique_ints else 1)
    data = []
    for i, cat in enumerate(categories):
        data.append((cat, unique_ints[i*2]))
        data.append((cat, unique_ints[i*2 + 1]))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, COUNT(DISTINCT col2) AS unique_count FROM {table_name} GROUP BY col1;")
    results = db_cursor.fetchall()
    assert len(results) == 5
    for res in results:
        assert res['unique_count'] == 2  

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
def test_group_by_on_empty_table(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"SELECT col1, COUNT(*) FROM {table_name} GROUP BY col1;")
    assert len(db_cursor.fetchall()) == 0

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
def test_group_by_with_all_unique_values(create_tables, generate_ints, db_cursor):
    table_name = create_tables[0]
    for val in generate_ints:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1;")
    results = db_cursor.fetchall()
    assert len(results) == 5
    for res in results:
        assert res['count'] == 1

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "DATE"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 5}], indirect=True)
def test_group_by_without_aggregates(create_tables, generate_strings, generate_dates, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_strings + generate_strings[:3], generate_dates + generate_dates[:3]))  
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, col2 FROM {table_name} GROUP BY col1, col2;")
    results = db_cursor.fetchall()
    unique = set(data)
    assert len(results) == len(unique)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 5}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
def test_invalid_group_by(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    for row in zip(generate_strings, generate_ints):
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    with pytest.raises(psycopg2.ProgrammingError):
        db_cursor.execute(f"SELECT col1, col2 FROM {table_name} GROUP BY col1;")  
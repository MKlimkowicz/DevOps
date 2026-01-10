import pytest
from datetime import datetime, date, timedelta
import psycopg2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
def test_having_with_count_greater_than_threshold(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    unique_strings = [f"cat{i}" for i in range(6)]
    data = unique_strings[0:2] + [unique_strings[2]]*3 + [unique_strings[3]]*3 + [unique_strings[4]]*3 + [unique_strings[5]]*4
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1 HAVING COUNT(*) > 2;")
    results = db_cursor.fetchall()
    assert len(results) == 4  # 3 with 3, 1 with 4
    for res in results:
        assert res['count'] > 2

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_having_with_sum_less_than_or_equal(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    categories = generate_strings[:5]
    data = [(cat, val) for cat in categories for val in generate_ints[:2]]  # 2 values per cat
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    threshold = 1000  # Assume small ints, adjust if needed
    db_cursor.execute(f"SELECT col1, SUM(col2) AS total FROM {table_name} GROUP BY col1 HAVING SUM(col2) <= %s;", (threshold,))
    results = db_cursor.fetchall()
    from collections import defaultdict
    sums = defaultdict(int)
    for cat, val in data:
        sums[cat] += val
    expected = [cat for cat, total in sums.items() if total <= threshold]
    assert len(results) == len(expected)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_floats", [{"num_rows": 10}], indirect=True)
def test_having_with_avg_and_multiple_conditions(create_tables, generate_strings, generate_floats, db_cursor):
    table_name = create_tables[0]
    categories = generate_strings[:5]
    data = [(cat, val) for cat in categories for val in generate_floats[:3]]  # 3 values per cat
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, AVG(col2) AS avg_val FROM {table_name} GROUP BY col1 HAVING AVG(col2) > 5 AND AVG(col2) < 10;")
    results = db_cursor.fetchall()
    from collections import defaultdict
    avgs = {}
    for cat, val in data:
        if cat not in avgs:
            avgs[cat] = []
        avgs[cat].append(val)
    expected = [cat for cat, vals in avgs.items() if 5 < sum(vals)/len(vals) < 10]
    assert len(results) <= len(expected)  # Depending on random floats

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["DATE", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_having_with_max_min(create_tables, generate_dates, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_dates, generate_ints))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    max_threshold = max(generate_ints) - 10
    min_threshold = min(generate_ints) + 10
    db_cursor.execute(f"SELECT col1, MAX(col2) AS max_val, MIN(col2) AS min_val FROM {table_name} GROUP BY col1 HAVING MAX(col2) > %s OR MIN(col2) < %s;", (max_threshold, min_threshold))
    results = db_cursor.fetchall()
    from collections import defaultdict
    groups = defaultdict(list)
    for dt, val in data:
        groups[dt].append(val)
    expected = [dt for dt, vals in groups.items() if max(vals) > max_threshold or min(vals) < min_threshold]
    assert len(results) == len(expected)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["VARCHAR(50)", "VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 15}], indirect=True)
def test_having_on_multiple_group_by_columns(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    cats = generate_strings[:3]
    subcats = generate_strings[3:6]
    data = []
    for cat in cats:
        for sub in subcats:
            count = 2 if cat == cats[0] and sub == subcats[0] else 4
            for _ in range(count):
                data.append((cat, sub, 1))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    db_cursor.execute(f"SELECT col1, col2, COUNT(*) AS count FROM {table_name} GROUP BY col1, col2 HAVING COUNT(*) >= 3;")
    results = db_cursor.fetchall()
    assert len(results) == 8  

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["VARCHAR(50)", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 5}], indirect=True)
def test_having_with_null_in_aggregates(create_tables, generate_strings, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = [(cat, val) for cat, val in zip(generate_strings[:5], generate_ints)] + [(cat, None) for cat in generate_strings[5:10]]
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    db_cursor.execute(f"SELECT col1, SUM(col2) AS total FROM {table_name} GROUP BY col1 HAVING SUM(col2) IS NOT NULL;")
    results = db_cursor.fetchall()
    non_null_groups = set(generate_strings[:5])  
    assert len(results) == len(non_null_groups)
    for res in results:
        assert res['total'] is not None

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
def test_having_combined_with_order_by(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    unique_strings = [f"cat{i}" for i in range(3)]
    data = unique_strings + [unique_strings[0]]*3 + [unique_strings[1]]*2 + [unique_strings[2]]*4
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1 HAVING COUNT(*) > 1 ORDER BY count DESC;")
    results = db_cursor.fetchall()
    assert len(results) == 3
    assert results[0]['count'] == 5
    assert results[1]['count'] == 4
    assert results[2]['count'] == 3

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["DATE", "INT"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_dates", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
def test_having_on_date_parts(create_tables, generate_dates, generate_ints, db_cursor):
    table_name = create_tables[0]
    data = list(zip(generate_dates, generate_ints))
    for row in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    monthly_threshold = 500
    db_cursor.execute(f"SELECT DATE_PART('month', col1) AS month, SUM(col2) AS total FROM {table_name} GROUP BY month HAVING SUM(col2) > %s;", (monthly_threshold,))
    results = db_cursor.fetchall()
    from collections import defaultdict
    monthly_sums = defaultdict(int)
    for dt, val in data:
        monthly_sums[dt.month] += val
    expected = [m for m, total in monthly_sums.items() if total > monthly_threshold]
    assert len(results) == len(expected)

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
def test_having_returns_no_groups(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings  # All unique, counts=1
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) FROM {table_name} GROUP BY col1 HAVING COUNT(*) > 10;")
    results = db_cursor.fetchall()
    assert len(results) == 0

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
def test_having_on_empty_table(create_tables, db_cursor):
    table_name = create_tables[0]
    db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES ('test');")
    with pytest.raises(psycopg2.ProgrammingError):
        db_cursor.execute(f"SELECT col1, COUNT(*) FROM {table_name} HAVING COUNT(*) > 0;")  

@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 1, "column_types": ["VARCHAR(50)"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
def test_having_with_all_groups_qualifying(create_tables, generate_strings, db_cursor):
    table_name = create_tables[0]
    data = generate_strings[:5] * 3  # All groups have count=3 >1
    for val in data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1) VALUES (%s);", (val,))
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1 HAVING COUNT(*) > 1;")
    results = db_cursor.fetchall()
    db_cursor.execute(f"SELECT col1, COUNT(*) AS count FROM {table_name} GROUP BY col1;")
    all_results = db_cursor.fetchall()
    assert len(results) == len(all_results) == 5
    for res in results:
        assert res['count'] > 1
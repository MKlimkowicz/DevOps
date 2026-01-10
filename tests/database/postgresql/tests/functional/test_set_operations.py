import pytest
from datetime import datetime, date
import psycopg2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_union_combine_unique_rows(create_tables, db_cursor):
    """UNION to Combine Unique Rows: Verify results include all unique rows from both, no duplicates."""
    table1, table2 = create_tables
    
    table1_data = [(1, 'apple'), (2, 'banana'), (3, 'cherry')]
    table2_data = [(2, 'banana'), (3, 'cherry'), (4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    results = db_cursor.fetchall()
    
    expected_unique = [(1, 'apple'), (2, 'banana'), (3, 'cherry'), (4, 'date')]
    assert len(results) == 4
    for i, result in enumerate(results):
        assert (result['col1'], result['col2']) == expected_unique[i]


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_union_all_combine_with_duplicates(create_tables, db_cursor):
    """UNION ALL to Combine with Duplicates: Verify all rows including duplicates, asserting higher count than UNION."""
    table1, table2 = create_tables
    
    identical_data = [(1, 'apple'), (2, 'banana')]
    table1_data = identical_data + [(3, 'cherry')]
    table2_data = identical_data + [(4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION ALL 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    union_all_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    union_results = db_cursor.fetchall()
    
    assert len(union_all_results) == 6  # 3 + 3 = 6 total rows
    assert len(union_results) == 4      # 4 unique rows
    assert len(union_all_results) > len(union_results)


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_intersect_common_rows(create_tables, db_cursor):
    """INTERSECT for Common Rows: Verify only matching rows returned."""
    table1, table2 = create_tables
    
    table1_data = [(1, 'apple'), (2, 'banana'), (3, 'cherry')]
    table2_data = [(2, 'banana'), (3, 'cherry'), (4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        INTERSECT 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    results = db_cursor.fetchall()
    
    expected_common = [(2, 'banana'), (3, 'cherry')]
    assert len(results) == 2
    for i, result in enumerate(results):
        assert (result['col1'], result['col2']) == expected_common[i]


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_except_differences(create_tables, db_cursor):
    """EXCEPT (or MINUS) for Differences: Verify rows in table1 but not table2."""
    table1, table2 = create_tables
    
    table1_data = [(1, 'apple'), (2, 'banana'), (3, 'cherry')]
    table2_data = [(2, 'banana'), (4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        EXCEPT 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    results = db_cursor.fetchall()
    
    expected_difference = [(1, 'apple'), (3, 'cherry')]
    assert len(results) == 2
    for i, result in enumerate(results):
        assert (result['col1'], result['col2']) == expected_difference[i]


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 3,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_nested_set_operations(create_tables, db_cursor):
    """Nested Set Operations: Combine multiple sets with complex operations."""
    table1, table2, table3 = create_tables
    
    table1_data = [(1, 'apple'), (2, 'banana')]
    table2_data = [(2, 'banana'), (3, 'cherry')]
    table3_data = [(2, 'banana'), (4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    for row in table3_data:
        db_cursor.execute(f"INSERT INTO {table3} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        (SELECT col1, col2 FROM {table1} 
         UNION 
         SELECT col1, col2 FROM {table2}) 
        INTERSECT 
        SELECT col1, col2 FROM {table3} 
        ORDER BY col1 ASC;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 1
    assert (results[0]['col1'], results[0]['col2']) == (2, 'banana')


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_with_order_by_limit(create_tables, db_cursor):
    """Set Operations with ORDER BY and LIMIT: Verify sorted and limited results."""
    table1, table2 = create_tables
    
    table1_data = [(1, 'apple'), (3, 'cherry'), (5, 'elderberry')]
    table2_data = [(2, 'banana'), (4, 'date'), (6, 'fig')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION ALL 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC 
        LIMIT 3;
    """)
    results = db_cursor.fetchall()
    
    expected = [(1, 'apple'), (2, 'banana'), (3, 'cherry')]
    assert len(results) == 3
    for i, result in enumerate(results):
        assert (result['col1'], result['col2']) == expected[i]


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_different_column_counts_invalid(create_tables, db_cursor):
    """Set Operations with Different Column Counts (Invalid): Assert raises SQL error."""
    table1, table2 = create_tables
    
    db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (1, 'apple');")
    db_cursor.execute(f"INSERT INTO {table2} (col1, col2, col3) VALUES (1, 'apple', 'red');")
    
    with pytest.raises(psycopg2.ProgrammingError):
        db_cursor.execute(f"""
            SELECT col1, col2 FROM {table1} 
            UNION 
            SELECT col1, col2, col3 FROM {table2};
        """)


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_on_subqueries(create_tables, db_cursor):
    """Set Operations on Subqueries: Verify combined filtered results."""
    table1, table2 = create_tables
    
    table1_data = [(1, 'apple'), (2, 'banana'), (3, 'cherry')]
    table2_data = [(2, 'blueberry'), (3, 'cranberry'), (4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        (SELECT col1, col2 FROM {table1} WHERE col1 <= 2) 
        UNION 
        (SELECT col1, col2 FROM {table2} WHERE col1 >= 3) 
        ORDER BY col1 ASC;
    """)
    results = db_cursor.fetchall()
    
    expected = [(1, 'apple'), (2, 'banana'), (3, 'cranberry'), (4, 'date')]
    assert len(results) == 4
    for i, result in enumerate(results):
        assert (result['col1'], result['col2']) == expected[i]


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_with_null_values(create_tables, db_cursor):
    """Set Operations with NULL Values: Verify NULLs treated as equal where applicable."""
    table1, table2 = create_tables
    
    table1_data = [(1, 'apple'), (None, 'banana'), (3, None)]
    table2_data = [(None, 'banana'), (3, None), (4, 'date')]
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 NULLS FIRST, col2 NULLS FIRST;
    """)
    union_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        INTERSECT 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 NULLS FIRST, col2 NULLS FIRST;
    """)
    intersect_results = db_cursor.fetchall()
    
    assert len(union_results) == 4  # Unique rows including NULLs
    assert len(intersect_results) == 2  # Two matching rows with NULLs


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_on_empty_tables(create_tables, db_cursor):
    """Edge Case: Set Operations on Empty Tables: Verify 0 rows or appropriate empty sets."""
    table1, table2 = create_tables
    
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION 
        SELECT col1, col2 FROM {table2};
    """)
    union_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        INTERSECT 
        SELECT col1, col2 FROM {table2};
    """)
    intersect_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        EXCEPT 
        SELECT col1, col2 FROM {table2};
    """)
    except_results = db_cursor.fetchall()
    
    assert len(union_results) == 0
    assert len(intersect_results) == 0
    assert len(except_results) == 0


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_with_identical_data(create_tables, db_cursor):
    """Edge Case: Set Operations with All Identical Data."""
    table1, table2 = create_tables
    
    identical_data = [(1, 'apple'), (2, 'banana'), (3, 'cherry')]
    
    for row in identical_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    union_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        UNION ALL 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    union_all_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        INTERSECT 
        SELECT col1, col2 FROM {table2} 
        ORDER BY col1 ASC;
    """)
    intersect_results = db_cursor.fetchall()
    
    db_cursor.execute(f"""
        SELECT col1, col2 FROM {table1} 
        EXCEPT 
        SELECT col1, col2 FROM {table2};
    """)
    except_results = db_cursor.fetchall()
    
    assert len(union_results) == 3      # Unique rows
    assert len(union_all_results) == 6  # All rows including duplicates
    assert len(intersect_results) == 3  # All rows are common
    assert len(except_results) == 0     # No differences


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 1, "column_types": ["INT"]},
        {"num_columns": 1, "column_types": ["VARCHAR(50)"]}
    ]
}], indirect=True)
def test_set_operations_incompatible_types(create_tables, db_cursor):
    """Edge Case: Set Operations with Incompatible Types: Assert raises SQL error."""
    table1, table2 = create_tables
    
    db_cursor.execute(f"INSERT INTO {table1} (col1) VALUES (42);")
    db_cursor.execute(f"INSERT INTO {table2} (col1) VALUES ('apple');")
    
    with pytest.raises(psycopg2.ProgrammingError):
        db_cursor.execute(f"""
            SELECT col1 FROM {table1} 
            UNION 
            SELECT col1 FROM {table2};
        """)

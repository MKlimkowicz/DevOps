import pytest
from datetime import datetime, date
import psycopg2

# 1. Non-Correlated Subquery in WHERE Clause
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
@pytest.mark.parametrize("generate_ints", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_strings", [{"num_rows": 10}], indirect=True)
@pytest.mark.parametrize("generate_floats", [{"num_rows": 10}], indirect=True)
def test_non_correlated_subquery_where_above_average(create_tables, generate_ints, generate_strings, generate_floats, db_cursor):
    """Test non-correlated subquery: SELECT rows WHERE numeric_col > (SELECT AVG(numeric_col) FROM same_table)"""
    table_name = create_tables[0]
    
    # Insert test data with known values for predictable average
    test_data = list(zip([1,2,3,4,5,6,7,8,9,10], generate_strings, [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]))
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    # Average is 55.0, so values > 55.0 should be returned (60.0, 70.0, 80.0, 90.0, 100.0)
    db_cursor.execute(f"SELECT col1, col3 FROM {table_name} WHERE col3 > (SELECT AVG(col3) FROM {table_name}) ORDER BY col3;")
    results = db_cursor.fetchall()
    
    assert len(results) == 5
    expected_values = [60.0, 70.0, 80.0, 90.0, 100.0]
    for i, result in enumerate(results):
        assert result['col3'] == expected_values[i]

# 2. Correlated Subquery in WHERE Clause
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["VARCHAR(50)", "DOUBLE PRECISION", "INT"]}]
}], indirect=True)
def test_correlated_subquery_where_above_category_average(create_tables, db_cursor):
    """Test correlated subquery: SELECT category WHERE sales > (SELECT AVG(sales) FROM table WHERE category = outer.category)"""
    table_name = create_tables[0]
    
    # Insert hierarchical data with categories
    test_data = [
        ('Electronics', 100.0, 1), ('Electronics', 200.0, 2), ('Electronics', 300.0, 3),  # avg = 200
        ('Books', 50.0, 4), ('Books', 100.0, 5), ('Books', 150.0, 6),  # avg = 100
        ('Clothing', 80.0, 7), ('Clothing', 120.0, 8)  # avg = 100
    ]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    # Find rows where sales > average for that category
    db_cursor.execute(f"""
        SELECT col1 as category, col2 as sales, col3 as id 
        FROM {table_name} o1 
        WHERE col2 > (SELECT AVG(col2) FROM {table_name} o2 WHERE o2.col1 = o1.col1) 
        ORDER BY col1, col2;
    """)
    results = db_cursor.fetchall()
    
    # Expected: Books (150.0), Clothing (120.0), Electronics (300.0) - ordered by category alphabetically
    assert len(results) == 3
    expected = [('Books', 150.0), ('Clothing', 120.0), ('Electronics', 300.0)]
    for i, result in enumerate(results):
        assert (result['category'], result['sales']) == expected[i]

# 3. Subquery in SELECT Clause (Scalar)
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["VARCHAR(50)", "DOUBLE PRECISION", "INT"]}]
}], indirect=True)
def test_scalar_subquery_in_select(create_tables, db_cursor):
    """Test scalar subquery: SELECT category, (SELECT MAX(sales) FROM table) AS global_max"""
    table_name = create_tables[0]
    
    # Insert test data
    test_data = [
        ('Electronics', 100.0, 1), ('Electronics', 250.0, 2), ('Books', 75.0, 3), ('Books', 125.0, 4)
    ]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1 as category, col2 as sales, 
               (SELECT MAX(col2) FROM {table_name}) as global_max 
        FROM {table_name} 
        ORDER BY col1, col2;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 4
    # All rows should have same global_max value (250.0)
    for result in results:
        assert result['global_max'] == 250.0

# 4. Subquery in FROM Clause (Derived Table)
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["VARCHAR(50)", "DOUBLE PRECISION", "INT"]}]
}], indirect=True)
def test_derived_table_subquery(create_tables, db_cursor):
    """Test derived table: SELECT * FROM (SELECT category, SUM(sales) FROM table GROUP BY category) WHERE total > threshold"""
    table_name = create_tables[0]
    
    # Insert test data
    test_data = [
        ('Electronics', 100.0, 1), ('Electronics', 200.0, 2), ('Electronics', 300.0, 3),  # total = 600
        ('Books', 50.0, 4), ('Books', 75.0, 5),  # total = 125
        ('Clothing', 80.0, 6), ('Clothing', 120.0, 7), ('Clothing', 200.0, 8)  # total = 400
    ]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT * FROM (
            SELECT col1 as category, SUM(col2) as total 
            FROM {table_name} 
            GROUP BY col1
        ) AS sub 
        WHERE total > 200 
        ORDER BY total DESC;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 2  # Electronics (600) and Clothing (400)
    assert results[0]['category'] == 'Electronics' and results[0]['total'] == 600.0
    assert results[1]['category'] == 'Clothing' and results[1]['total'] == 400.0

# 5. EXISTS Subquery
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "DOUBLE PRECISION"]}
    ]
}], indirect=True)
def test_exists_subquery(create_tables, db_cursor):
    """Test EXISTS subquery: SELECT * FROM table1 WHERE EXISTS (SELECT 1 FROM table2 WHERE table1.id = table2.id)"""
    table1, table2 = create_tables
    
    # Insert related data
    table1_data = [(1, 'Product A'), (2, 'Product B'), (3, 'Product C'), (4, 'Product D')]
    table2_data = [(1, 100.0), (2, 200.0), (5, 300.0)]  # IDs 1,2 match, 3,4 don't, 5 extra
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table1} 
        WHERE EXISTS (SELECT 1 FROM {table2} WHERE {table1}.col1 = {table2}.col1) 
        ORDER BY col1;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 2  # Only IDs 1 and 2 have matches
    assert results[0]['id'] == 1 and results[0]['name'] == 'Product A'
    assert results[1]['id'] == 2 and results[1]['name'] == 'Product B'

# 6. NOT EXISTS Subquery
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "DOUBLE PRECISION"]}
    ]
}], indirect=True)
def test_not_exists_subquery(create_tables, db_cursor):
    """Test NOT EXISTS subquery: verify rows without matches in second table"""
    table1, table2 = create_tables
    
    # Insert related data
    table1_data = [(1, 'Product A'), (2, 'Product B'), (3, 'Product C'), (4, 'Product D')]
    table2_data = [(1, 100.0), (2, 200.0)]  # Only IDs 1,2 have matches
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table1} 
        WHERE NOT EXISTS (SELECT 1 FROM {table2} WHERE {table1}.col1 = {table2}.col1) 
        ORDER BY col1;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 2  # IDs 3 and 4 don't have matches
    assert results[0]['id'] == 3 and results[0]['name'] == 'Product C'
    assert results[1]['id'] == 4 and results[1]['name'] == 'Product D'

# 7. IN Subquery
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_in_subquery(create_tables, db_cursor):
    """Test IN subquery: SELECT * FROM table1 WHERE id IN (SELECT id FROM table2 WHERE condition)"""
    table1, table2 = create_tables
    
    # Insert data
    table1_data = [(1, 'Product A'), (2, 'Product B'), (3, 'Product C'), (4, 'Product D'), (5, 'Product E')]
    table2_data = [(1, 'Active'), (2, 'Inactive'), (3, 'Active'), (6, 'Active')]  # IDs 1,3 are 'Active'
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table1} 
        WHERE col1 IN (SELECT col1 FROM {table2} WHERE col2 = 'Active') 
        ORDER BY col1;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 2  # IDs 1 and 3 match 'Active' condition
    assert results[0]['id'] == 1 and results[0]['name'] == 'Product A'
    assert results[1]['id'] == 3 and results[1]['name'] == 'Product C'

# 8. NOT IN Subquery with NULL Handling
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]},
        {"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}
    ]
}], indirect=True)
def test_not_in_subquery_with_nulls(create_tables, db_cursor):
    """Test NOT IN subquery with NULL handling: verify correct behavior when subquery contains NULLs"""
    table1, table2 = create_tables
    
    # Insert data with NULLs in subquery
    table1_data = [(1, 'Product A'), (2, 'Product B'), (3, 'Product C'), (4, 'Product D')]
    table2_data = [(1, 'Status A'), (None, 'Status B'), (5, 'Status C')]  # NULL in col1
    
    for row in table1_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2) VALUES (%s, %s);", row)
    for row in table2_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2) VALUES (%s, %s);", row)
    
    # When subquery contains NULL, NOT IN returns no rows (standard SQL behavior)
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table1} 
        WHERE col1 NOT IN (SELECT col1 FROM {table2}) 
        ORDER BY col1;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 0  # NOT IN with NULL returns no rows
    
    # Test with NULL-safe alternative using NOT EXISTS
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table1} 
        WHERE NOT EXISTS (SELECT 1 FROM {table2} WHERE {table2}.col1 = {table1}.col1) 
        ORDER BY col1;
    """)
    results_safe = db_cursor.fetchall()
    
    assert len(results_safe) == 3  # IDs 2, 3, 4 don't match

# 9. Nested Subqueries
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "DOUBLE PRECISION", "VARCHAR(50)"]}]
}], indirect=True)
def test_nested_subqueries(create_tables, db_cursor):
    """Test nested subqueries: SELECT * FROM table WHERE col > (SELECT AVG(col) FROM (SELECT col FROM table WHERE condition))"""
    table_name = create_tables[0]
    
    # Insert test data
    test_data = [
        (1, 100.0, 'A'), (2, 200.0, 'A'), (3, 300.0, 'A'), (4, 400.0, 'A'),  # Group A: 100,200,300,400 avg=250
        (5, 50.0, 'B'), (6, 150.0, 'B'), (7, 250.0, 'B')  # Group B: 50,150,250 avg=150
    ]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    # Find rows where value > average of group A values
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as value, col3 as category 
        FROM {table_name} 
        WHERE col2 > (
            SELECT AVG(col2) 
            FROM (
                SELECT col2 
                FROM {table_name} 
                WHERE col3 = 'A'
            ) AS inner_query
        ) 
        ORDER BY col2;
    """)
    results = db_cursor.fetchall()
    
    # Average of A group is 250, so values > 250 are: 300, 400
    assert len(results) == 2
    assert results[0]['value'] == 300.0 and results[0]['category'] == 'A'
    assert results[1]['value'] == 400.0 and results[1]['category'] == 'A'

# 10. Edge Case: Subquery Returning No Rows
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}]
}], indirect=True)
def test_subquery_no_rows_edge_case(create_tables, db_cursor):
    """Test edge case: subquery with impossible condition (WHERE 1=0)"""
    table_name = create_tables[0]
    
    # Insert test data
    test_data = [(1, 'A'), (2, 'B'), (3, 'C')]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    
    # Test EXISTS with empty subquery
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table_name} 
        WHERE EXISTS (SELECT 1 FROM {table_name} WHERE 1=0);
    """)
    results_exists = db_cursor.fetchall()
    assert len(results_exists) == 0  # EXISTS with empty subquery returns no rows
    
    # Test IN with empty subquery
    db_cursor.execute(f"""
        SELECT col1 as id, col2 as name 
        FROM {table_name} 
        WHERE col1 IN (SELECT col1 FROM {table_name} WHERE 1=0);
    """)
    results_in = db_cursor.fetchall()
    assert len(results_in) == 0  # IN with empty subquery returns no rows

# 11. Edge Case: Subquery Returning Multiple Rows in Scalar Context (Invalid)
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["INT", "VARCHAR(50)"]}]
}], indirect=True)
def test_scalar_subquery_multiple_rows_error(create_tables, db_cursor):
    """Test edge case: subquery returning multiple rows in scalar context should raise error"""
    table_name = create_tables[0]
    
    # Insert test data
    test_data = [(1, 'A'), (2, 'B'), (3, 'C')]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2) VALUES (%s, %s);", row)
    
    # This should raise an error: scalar subquery returns multiple rows
    with pytest.raises(psycopg2.DatabaseError):
        db_cursor.execute(f"""
            SELECT col1 as id, col2 as name 
            FROM {table_name} 
            WHERE col1 = (SELECT col1 FROM {table_name});
        """)

# 12. Edge Case: Correlated Subquery with No Correlation Match
@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["VARCHAR(50)", "DOUBLE PRECISION", "VARCHAR(50)"]}]
}], indirect=True)
def test_correlated_subquery_no_match(create_tables, db_cursor):
    """Test edge case: correlated subquery with no correlation match"""
    table_name = create_tables[0]
    
    # Insert test data with non-matching categories
    test_data = [
        ('Electronics', 100.0, 'Type1'), ('Electronics', 200.0, 'Type2'), 
        ('Books', 150.0, 'Type1'), ('Books', 250.0, 'Type2')
    ]
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    # Look for correlation that doesn't exist (category 'Clothing')
    db_cursor.execute(f"""
        SELECT col1 as category, col2 as sales 
        FROM {table_name} o1 
        WHERE col1 = 'Clothing' 
        AND col2 > (SELECT AVG(col2) FROM {table_name} o2 WHERE o2.col1 = o1.col1) 
        ORDER BY col2;
    """)
    results = db_cursor.fetchall()
    
    assert len(results) == 0  # No matches for non-existent category
    
    # Test another case: category exists but no rows meet the correlation condition
    db_cursor.execute(f"""
        SELECT col1 as category, col2 as sales 
        FROM {table_name} o1 
        WHERE col2 > (SELECT MAX(col2) + 100 FROM {table_name} o2 WHERE o2.col1 = o1.col1) 
        ORDER BY col2;
    """)
    results_no_condition = db_cursor.fetchall()
    
    assert len(results_no_condition) == 0  # No rows meet impossible condition

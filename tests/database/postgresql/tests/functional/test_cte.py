import pytest
from datetime import datetime, date
import psycopg2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "BOOLEAN"]}]
}], indirect=True)
def test_basic_cte_for_temporary_view(create_tables, db_cursor):
    """Basic CTE for Temporary View: Create a table, insert data. Define a simple CTE as SELECT * FROM table WHERE condition."""
    table_name = create_tables[0]
    
    test_data = [
        (1, "active", True),
        (2, "inactive", False),
        (3, "active", True),
        (4, "pending", False),
        (5, "active", True)
    ]
    
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    cte_query = f"""
    WITH active_records AS (
        SELECT * FROM {table_name} WHERE col2 = 'active'
    )
    SELECT * FROM active_records ORDER BY col1;
    """
    
    db_cursor.execute(cte_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 3
    expected_ids = [1, 3, 5]
    actual_ids = [row['col1'] for row in results]
    assert actual_ids == expected_ids
    
    for row in results:
        assert row['col2'] == 'active'
        assert row['col3'] is True


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
def test_cte_with_aggregates(create_tables, db_cursor):
    """CTE with Aggregates: Insert data with categories. Define CTE with GROUP BY category, SUM(numeric_col)."""
    table_name = create_tables[0]
    
    test_data = [
        (1, "electronics", 100.50),
        (2, "books", 25.99),
        (3, "electronics", 75.25),
        (4, "clothing", 45.00),
        (5, "books", 15.50),
        (6, "electronics", 200.00),
        (7, "clothing", 60.75)
    ]
    
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    cte_query = f"""
    WITH category_totals AS (
        SELECT col2 as category, SUM(col3) as total_amount, COUNT(*) as item_count
        FROM {table_name} 
        GROUP BY col2
    )
    SELECT * FROM category_totals ORDER BY category;
    """
    
    db_cursor.execute(cte_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 3
    
    results_dict = {row['category']: (row['total_amount'], row['item_count']) for row in results}
    
    assert results_dict['electronics'] == (375.75, 3)
    assert results_dict['books'][0] == pytest.approx(41.49, rel=1e-9)
    assert results_dict['books'][1] == 2
    assert results_dict['clothing'] == (105.75, 2)


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 4, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION", "DATE"]}]
}], indirect=True)
def test_multiple_ctes_in_chain(create_tables, db_cursor):
    """Multiple CTEs in Chain: Define CTE1 as filtered select, CTE2 as aggregate on CTE1."""
    table_name = create_tables[0]
    
    test_data = [
        (1, "premium", 100.00, "2023-01-15"),
        (2, "basic", 25.00, "2023-01-16"),
        (3, "premium", 150.00, "2023-01-17"),
        (4, "premium", 200.00, "2023-02-01"),
        (5, "basic", 30.00, "2023-02-02"),
        (6, "premium", 175.00, "2023-02-03")
    ]
    
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3, col4) VALUES (%s, %s, %s, %s);", row)
    
    cte_query = f"""
    WITH premium_records AS (
        SELECT * FROM {table_name} WHERE col2 = 'premium'
    ),
    monthly_premium_totals AS (
        SELECT 
            EXTRACT(MONTH FROM col4) as month,
            SUM(col3) as monthly_total,
            COUNT(*) as transaction_count
        FROM premium_records 
        GROUP BY EXTRACT(MONTH FROM col4)
    )
    SELECT * FROM monthly_premium_totals ORDER BY month;
    """
    
    db_cursor.execute(cte_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 2
    
    assert results[0]['month'] == 1
    assert results[0]['monthly_total'] == 250.00
    assert results[0]['transaction_count'] == 2
    
    assert results[1]['month'] == 2
    assert results[1]['monthly_total'] == 375.00
    assert results[1]['transaction_count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "INT"]},
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}
    ]
}], indirect=True)
def test_cte_with_join_inside(create_tables, db_cursor):
    """CTE with JOIN Inside: Create two tables, insert matching data. Define CTE with INNER JOIN between tables."""
    table1, table2 = create_tables
    
    users_data = [
        (1, "john_doe", 101),
        (2, "jane_smith", 102),
        (3, "bob_wilson", 103)
    ]
    
    for row in users_data:
        db_cursor.execute(f"INSERT INTO {table1} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    dept_data = [
        (101, "Engineering", 75000.00),
        (102, "Marketing", 65000.00),
        (104, "Finance", 70000.00)  # No matching user
    ]
    
    for row in dept_data:
        db_cursor.execute(f"INSERT INTO {table2} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    cte_query = f"""
    WITH user_department_info AS (
        SELECT 
            u.col1 as user_id,
            u.col2 as username,
            d.col2 as department,
            d.col3 as salary
        FROM {table1} u
        INNER JOIN {table2} d ON u.col3 = d.col1
    )
    SELECT * FROM user_department_info ORDER BY user_id;
    """
    
    db_cursor.execute(cte_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 2
    
    assert results[0]['user_id'] == 1
    assert results[0]['username'] == 'john_doe'
    assert results[0]['department'] == 'Engineering'
    assert results[0]['salary'] == 75000.00
    
    assert results[1]['user_id'] == 2
    assert results[1]['username'] == 'jane_smith'
    assert results[1]['department'] == 'Marketing'
    assert results[1]['salary'] == 65000.00


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "INT"]}]
}], indirect=True)
def test_recursive_cte_for_hierarchy(create_tables, db_cursor):
    """Recursive CTE for Hierarchy: Create table with parent-child IDs (e.g., tree structure)."""
    table_name = create_tables[0]
    
    hierarchy_data = [
        (1, "CEO", None),           # Root
        (2, "CTO", 1),              # Level 1
        (3, "CFO", 1),              # Level 1
        (4, "Dev Manager", 2),       # Level 2
        (5, "QA Manager", 2),        # Level 2
        (6, "Senior Dev", 4),        # Level 3
        (7, "Junior Dev", 4),        # Level 3
        (8, "QA Lead", 5)            # Level 3
    ]
    
    for row in hierarchy_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    recursive_query = f"""
    WITH RECURSIVE org_hierarchy AS (
        -- Base case: root nodes (no parent)
        SELECT col1 as id, col2 as name, col3 as parent_id, 0 as level, col2::TEXT as path
        FROM {table_name}
        WHERE col3 IS NULL
        
        UNION ALL
        
        -- Recursive case: children of current level
        SELECT 
            e.col1 as id, 
            e.col2 as name, 
            e.col3 as parent_id, 
            h.level + 1 as level,
            (h.path || ' -> ' || e.col2)::TEXT as path
        FROM {table_name} e
        INNER JOIN org_hierarchy h ON e.col3 = h.id
    )
    SELECT * FROM org_hierarchy ORDER BY level, id;
    """
    
    db_cursor.execute(recursive_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 8
    
    levels = {}
    for row in results:
        level = row['level']
        if level not in levels:
            levels[level] = []
        levels[level].append(row['name'])
    
    assert levels[0] == ['CEO']
    assert set(levels[1]) == {'CTO', 'CFO'}
    assert set(levels[2]) == {'Dev Manager', 'QA Manager'}
    assert set(levels[3]) == {'Senior Dev', 'Junior Dev', 'QA Lead'}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "INT"]}]
}], indirect=True)
def test_recursive_cte_with_cycle_detection(create_tables, db_cursor):
    """Recursive CTE with Cycle Detection: Insert data with a cycle in hierarchy."""
    table_name = create_tables[0]
    
    cycle_data = [
        (1, "Node1", None),
        (2, "Node2", 1),
        (3, "Node3", 2),
        (4, "Node4", 3),
        (5, "Node5", 4),
        (6, "Node6", 2)  # Creates a potential cycle path
    ]
    
    for row in cycle_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    cycle_detection_query = f"""
    WITH RECURSIVE hierarchy_with_cycle_check AS (
        -- Base case: root nodes
        SELECT 
            col1 as id, 
            col2 as name, 
            col3 as parent_id, 
            0 as level,
            ARRAY[col1] as path,
            false as cycle_detected
        FROM {table_name}
        WHERE col3 IS NULL
        
        UNION ALL
        
        -- Recursive case with cycle detection
        SELECT 
            e.col1 as id, 
            e.col2 as name, 
            e.col3 as parent_id, 
            h.level + 1 as level,
            h.path || e.col1 as path,
            e.col1 = ANY(h.path) as cycle_detected
        FROM {table_name} e
        INNER JOIN hierarchy_with_cycle_check h ON e.col3 = h.id
        WHERE NOT (e.col1 = ANY(h.path)) AND h.level < 10  -- Prevent infinite recursion
    )
    SELECT * FROM hierarchy_with_cycle_check ORDER BY level, id;
    """
    
    db_cursor.execute(cycle_detection_query)
    results = db_cursor.fetchall()
    
    assert len(results) > 0
    
    for row in results:
        path = row['path']
        assert len(path) == len(set(path)), f"Cycle detected in path: {path}"


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
def test_cte_with_order_by_and_limit(create_tables, db_cursor):
    """CTE with ORDER BY and LIMIT: Define CTE as SELECT with aggregates, then query CTE with ORDER BY aggregate DESC LIMIT N."""
    table_name = create_tables[0]
    
    test_data = [
        (1, "product_a", 150.00),
        (2, "product_b", 75.50),
        (3, "product_a", 200.00),
        (4, "product_c", 95.25),
        (5, "product_b", 125.75),
        (6, "product_a", 180.50),
        (7, "product_c", 110.00),
        (8, "product_d", 300.00)
    ]
    
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    cte_query = f"""
    WITH product_totals AS (
        SELECT 
            col2 as product_name,
            SUM(col3) as total_sales,
            COUNT(*) as sale_count,
            AVG(col3) as avg_sale
        FROM {table_name} 
        GROUP BY col2
    )
    SELECT * FROM product_totals 
    ORDER BY total_sales DESC 
    LIMIT 2;
    """
    
    db_cursor.execute(cte_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 2
    
    assert results[0]['product_name'] == 'product_a'
    assert results[0]['total_sales'] == 530.50
    assert results[0]['sale_count'] == 3
    
    assert results[1]['product_name'] == 'product_d'
    assert results[1]['total_sales'] == 300.00
    assert results[1]['sale_count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 2,
    "tables": [
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]},
        {"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}
    ]
}], indirect=True)
def test_cte_used_in_insert_update(create_tables, db_cursor):
    """CTE Used in INSERT/UPDATE: Define CTE to compute values, then INSERT INTO another table FROM CTE."""
    source_table, target_table = create_tables
    
    source_data = [
        (1, "electronics", 100.00),
        (2, "electronics", 150.00),
        (3, "books", 25.00),
        (4, "books", 35.00),
        (5, "electronics", 200.00)
    ]
    
    for row in source_data:
        db_cursor.execute(f"INSERT INTO {source_table} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    insert_with_cte = f"""
    WITH category_summaries AS (
        SELECT 
            ROW_NUMBER() OVER (ORDER BY col2) as id,
            col2 as category,
            SUM(col3) as total_amount
        FROM {source_table}
        GROUP BY col2
    )
    INSERT INTO {target_table} (col1, col2, col3)
    SELECT id, category, total_amount FROM category_summaries;
    """
    
    db_cursor.execute(insert_with_cte)
    
    db_cursor.execute(f"SELECT * FROM {target_table} ORDER BY col2;")
    results = db_cursor.fetchall()
    
    assert len(results) == 2
    
    books_row = [r for r in results if r['col2'] == 'books'][0]
    assert books_row['col3'] == 60.00
    
    electronics_row = [r for r in results if r['col2'] == 'electronics'][0]
    assert electronics_row['col3'] == 450.00


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
def test_non_recursive_cte_vs_subquery(create_tables, db_cursor):
    """Non-Recursive CTE with Subquery Equivalent: Define CTE for a subquery (e.g., max value). Query using CTE vs. subquery."""
    table_name = create_tables[0]
    
    test_data = [
        (1, "item_a", 150.00),
        (2, "item_b", 200.00),  # Max value
        (3, "item_c", 175.00),
        (4, "item_d", 125.00),
        (5, "item_e", 190.00)
    ]
    
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    cte_query = f"""
    WITH max_value AS (
        SELECT MAX(col3) as max_amount FROM {table_name}
    )
    SELECT t.* FROM {table_name} t, max_value m
    WHERE t.col3 = m.max_amount;
    """
    
    db_cursor.execute(cte_query)
    cte_results = db_cursor.fetchall()
    
    subquery_query = f"""
    SELECT * FROM {table_name}
    WHERE col3 = (SELECT MAX(col3) FROM {table_name});
    """
    
    db_cursor.execute(subquery_query)
    subquery_results = db_cursor.fetchall()
    
    assert len(cte_results) == len(subquery_results) == 1
    assert cte_results[0]['col1'] == subquery_results[0]['col1'] == 2
    assert cte_results[0]['col2'] == subquery_results[0]['col2'] == 'item_b'
    assert cte_results[0]['col3'] == subquery_results[0]['col3'] == 200.00


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "DOUBLE PRECISION"]}]
}], indirect=True)
def test_cte_on_empty_table(create_tables, db_cursor):
    """Edge Case: CTE on Empty Table: Define CTE as SELECT from empty table. Query CTE."""
    table_name = create_tables[0]
    
    
    cte_query = f"""
    WITH empty_results AS (
        SELECT col1, col2, SUM(col3) as total
        FROM {table_name}
        GROUP BY col1, col2
    )
    SELECT * FROM empty_results;
    """
    
    db_cursor.execute(cte_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 0


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["INT", "VARCHAR(50)", "INT"]}]
}], indirect=True)
def test_recursive_cte_with_no_base_case(create_tables, db_cursor):
    """Edge Case: Recursive CTE with No Base Case: Define recursive CTE with empty base (e.g., WHERE false)."""
    table_name = create_tables[0]
    
    test_data = [
        (1, "item1", 2),
        (2, "item2", 3),
        (3, "item3", None)
    ]
    
    for row in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col1, col2, col3) VALUES (%s, %s, %s);", row)
    
    recursive_query = f"""
    WITH RECURSIVE empty_recursive AS (
        -- Base case that returns no rows
        SELECT col1, col2, col3, 0 as level
        FROM {table_name}
        WHERE FALSE  -- This ensures no base case rows
        
        UNION ALL
        
        -- Recursive case (will never execute due to empty base)
        SELECT t.col1, t.col2, t.col3, r.level + 1
        FROM {table_name} t
        INNER JOIN empty_recursive r ON t.col3 = r.col1
    )
    SELECT * FROM empty_recursive;
    """
    
    db_cursor.execute(recursive_query)
    results = db_cursor.fetchall()
    
    assert len(results) == 0


def test_invalid_cte_recursive_without_union(db_cursor):
    """Edge Case: Invalid CTE (Recursive without UNION): Attempt CTE without proper recursion syntax."""
    
    invalid_recursive_query = """
    WITH RECURSIVE invalid_cte AS (
        SELECT 1 as id, 'test' as name
        -- Missing UNION ALL for recursion
        SELECT id + 1, name FROM invalid_cte WHERE id < 5
    )
    SELECT * FROM invalid_cte;
    """
    
    with pytest.raises(psycopg2.Error):
        db_cursor.execute(invalid_recursive_query)

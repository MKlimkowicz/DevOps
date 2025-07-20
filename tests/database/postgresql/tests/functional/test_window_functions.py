import pytest
import psycopg2
from datetime import datetime, date, timedelta


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 4, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER", "DATE"]}]
}], indirect=True)
def test_row_number_over_partition(create_tables, db_cursor):
    """Test ROW_NUMBER() OVER (PARTITION BY category ORDER BY sales DESC)."""
    table_name = create_tables[0]
    
    # Insert test data with categories and sales
    test_data = [
        ("Electronics", 1000, "2024-01-01"),
        ("Electronics", 1500, "2024-01-02"),
        ("Electronics", 800, "2024-01-03"),
        ("Books", 200, "2024-01-01"),
        ("Books", 350, "2024-01-02"),
        ("Books", 150, "2024-01-03"),
        ("Clothing", 500, "2024-01-01"),
        ("Clothing", 750, "2024-01-02")
    ]
    
    for category, sales, sale_date in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3, col4) VALUES (%s, %s, %s)", 
                         (category, sales, sale_date))
    
    # Test ROW_NUMBER() with partition
    db_cursor.execute(f"""
        SELECT col2 as category, col3 as sales, 
               ROW_NUMBER() OVER (PARTITION BY col2 ORDER BY col3 DESC) as row_num
        FROM {table_name} 
        ORDER BY col2, row_num
    """)
    
    results = db_cursor.fetchall()
    
    # Verify results for each category
    electronics_rows = [r for r in results if r['category'] == 'Electronics']
    books_rows = [r for r in results if r['category'] == 'Books']
    clothing_rows = [r for r in results if r['category'] == 'Clothing']
    
    # Electronics: 1500 (row_num=1), 1000 (row_num=2), 800 (row_num=3)
    assert electronics_rows[0]['sales'] == 1500 and electronics_rows[0]['row_num'] == 1
    assert electronics_rows[1]['sales'] == 1000 and electronics_rows[1]['row_num'] == 2
    assert electronics_rows[2]['sales'] == 800 and electronics_rows[2]['row_num'] == 3
    
    # Books: 350 (row_num=1), 200 (row_num=2), 150 (row_num=3)
    assert books_rows[0]['sales'] == 350 and books_rows[0]['row_num'] == 1
    assert books_rows[1]['sales'] == 200 and books_rows[1]['row_num'] == 2
    assert books_rows[2]['sales'] == 150 and books_rows[2]['row_num'] == 3
    
    # Clothing: 750 (row_num=1), 500 (row_num=2)
    assert clothing_rows[0]['sales'] == 750 and clothing_rows[0]['row_num'] == 1
    assert clothing_rows[1]['sales'] == 500 and clothing_rows[1]['row_num'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_rank_and_dense_rank_with_ties(create_tables, db_cursor):
    """Test RANK() and DENSE_RANK() with tied values."""
    table_name = create_tables[0]
    
    # Insert data with ties in sales values
    test_sales = [1000, 1000, 800, 800, 800, 600, 500]
    for i, sales in enumerate(test_sales):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (f"product_{i+1}", sales))
    
    # Test RANK() and DENSE_RANK()
    db_cursor.execute(f"""
        SELECT col2 as product, col3 as sales,
               RANK() OVER (ORDER BY col3 DESC) as rank_val,
               DENSE_RANK() OVER (ORDER BY col3 DESC) as dense_rank_val
        FROM {table_name}
        ORDER BY col3 DESC, col1
    """)
    
    results = db_cursor.fetchall()
    
    # Verify RANK() and DENSE_RANK() behavior with ties
    expected_results = [
        # sales=1000 (2 ties): rank=1,1 dense_rank=1,1
        (1000, 1, 1), (1000, 1, 1),
        # sales=800 (3 ties): rank=3,3,3 dense_rank=2,2,2  
        (800, 3, 2), (800, 3, 2), (800, 3, 2),
        # sales=600: rank=6 dense_rank=3
        (600, 6, 3),
        # sales=500: rank=7 dense_rank=4
        (500, 7, 4)
    ]
    
    for i, (expected_sales, expected_rank, expected_dense_rank) in enumerate(expected_results):
        assert results[i]['sales'] == expected_sales
        assert results[i]['rank_val'] == expected_rank
        assert results[i]['dense_rank_val'] == expected_dense_rank


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "DATE", "INTEGER"]}]
}], indirect=True)
def test_lag_and_lead_offset_functions(create_tables, db_cursor):
    """Test LAG() and LEAD() for time-series data."""
    table_name = create_tables[0]
    
    # Insert time-series data
    base_date = date(2024, 1, 1)
    values = [100, 150, 120, 180, 200]
    
    for i, value in enumerate(values):
        current_date = base_date + timedelta(days=i)
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (current_date, value))
    
    # Test LAG() and LEAD()
    db_cursor.execute(f"""
        SELECT col2 as date_col, col3 as value,
               LAG(col3) OVER (ORDER BY col2) as prev_value,
               LEAD(col3) OVER (ORDER BY col2) as next_value
        FROM {table_name}
        ORDER BY col2
    """)
    
    results = db_cursor.fetchall()
    
    # Verify LAG() and LEAD() results
    assert len(results) == 5
    
    # First row: LAG should be NULL, LEAD should be 150
    assert results[0]['value'] == 100
    assert results[0]['prev_value'] is None
    assert results[0]['next_value'] == 150
    
    # Middle row: LAG should be 150, LEAD should be 180
    assert results[2]['value'] == 120
    assert results[2]['prev_value'] == 150
    assert results[2]['next_value'] == 180
    
    # Last row: LAG should be 180, LEAD should be NULL
    assert results[4]['value'] == 200
    assert results[4]['prev_value'] == 180
    assert results[4]['next_value'] is None


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_ntile_bucketing(create_tables, db_cursor):
    """Test NTILE() for dividing rows into buckets."""
    table_name = create_tables[0]
    
    # Insert 12 rows with different sales values
    sales_values = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]
    
    for i, sales in enumerate(sales_values):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (f"item_{i+1}", sales))
    
    # Test NTILE(4) - divide into 4 buckets
    db_cursor.execute(f"""
        SELECT col2 as item, col3 as sales,
               NTILE(4) OVER (ORDER BY col3) as bucket
        FROM {table_name}
        ORDER BY col3
    """)
    
    results = db_cursor.fetchall()
    
    # Verify NTILE distribution (12 rows into 4 buckets = 3 rows per bucket)
    bucket_counts = {}
    for result in results:
        bucket = result['bucket']
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    
    # Each bucket should have 3 rows
    assert len(bucket_counts) == 4
    for bucket_num in [1, 2, 3, 4]:
        assert bucket_counts[bucket_num] == 3
    
    # Verify bucket assignments
    assert results[0]['sales'] == 100 and results[0]['bucket'] == 1  # First bucket
    assert results[3]['sales'] == 400 and results[3]['bucket'] == 2  # Second bucket
    assert results[6]['sales'] == 700 and results[6]['bucket'] == 3  # Third bucket
    assert results[9]['sales'] == 1000 and results[9]['bucket'] == 4  # Fourth bucket


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 4, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "DATE", "INTEGER"]}]
}], indirect=True)
def test_sum_over_window_with_frame(create_tables, db_cursor):
    """Test SUM() OVER window with frame specification."""
    table_name = create_tables[0]
    
    # Insert data with categories and dates
    test_data = [
        ("A", "2024-01-01", 100),
        ("A", "2024-01-02", 200),
        ("A", "2024-01-03", 150),
        ("B", "2024-01-01", 300),
        ("B", "2024-01-02", 250),
        ("B", "2024-01-03", 400)
    ]
    
    for category, sale_date, sales in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3, col4) VALUES (%s, %s, %s)", 
                         (category, sale_date, sales))
    
    # Test SUM() with sliding window frame
    db_cursor.execute(f"""
        SELECT col2 as category, col3 as date_col, col4 as sales,
               SUM(col4) OVER (
                   PARTITION BY col2 
                   ORDER BY col3 
                   ROWS BETWEEN 1 PRECEDING AND CURRENT ROW
               ) as rolling_sum
        FROM {table_name}
        ORDER BY col2, col3
    """)
    
    results = db_cursor.fetchall()
    
    # Verify rolling sums for category A
    category_a = [r for r in results if r['category'] == 'A']
    assert category_a[0]['sales'] == 100 and category_a[0]['rolling_sum'] == 100  # First row: just current
    assert category_a[1]['sales'] == 200 and category_a[1]['rolling_sum'] == 300  # 100 + 200
    assert category_a[2]['sales'] == 150 and category_a[2]['rolling_sum'] == 350  # 200 + 150
    
    # Verify rolling sums for category B
    category_b = [r for r in results if r['category'] == 'B']
    assert category_b[0]['sales'] == 300 and category_b[0]['rolling_sum'] == 300  # First row: just current
    assert category_b[1]['sales'] == 250 and category_b[1]['rolling_sum'] == 550  # 300 + 250
    assert category_b[2]['sales'] == 400 and category_b[2]['rolling_sum'] == 650  # 250 + 400


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_avg_over_entire_window(create_tables, db_cursor):
    """Test AVG() OVER () for entire result set."""
    table_name = create_tables[0]
    
    # Insert test data
    values = [100, 200, 300, 400, 500]
    expected_avg = sum(values) / len(values)  # 300
    
    for i, value in enumerate(values):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (f"item_{i+1}", value))
    
    # Test AVG() over entire window
    db_cursor.execute(f"""
        SELECT col2 as item, col3 as value,
               AVG(col3) OVER () as overall_avg
        FROM {table_name}
        ORDER BY col1
    """)
    
    results = db_cursor.fetchall()
    
    # Verify same average appears for all rows
    assert len(results) == 5
    for result in results:
        assert result['overall_avg'] == expected_avg


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 4, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "DATE", "INTEGER"]}]
}], indirect=True)
def test_first_value_and_last_value(create_tables, db_cursor):
    """Test FIRST_VALUE() and LAST_VALUE() with partitions."""
    table_name = create_tables[0]
    
    # Insert data with categories and dates
    test_data = [
        ("X", "2024-01-01", 100),
        ("X", "2024-01-02", 200),
        ("X", "2024-01-03", 150),
        ("Y", "2024-01-01", 300),
        ("Y", "2024-01-02", 250)
    ]
    
    for category, sale_date, sales in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3, col4) VALUES (%s, %s, %s)", 
                         (category, sale_date, sales))
    
    # Test FIRST_VALUE() and LAST_VALUE()
    db_cursor.execute(f"""
        SELECT col2 as category, col3 as date_col, col4 as sales,
               FIRST_VALUE(col4) OVER (
                   PARTITION BY col2 
                   ORDER BY col3
               ) as first_sales,
               LAST_VALUE(col4) OVER (
                   PARTITION BY col2 
                   ORDER BY col3 
                   ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
               ) as last_sales
        FROM {table_name}
        ORDER BY col2, col3
    """)
    
    results = db_cursor.fetchall()
    
    # Verify FIRST_VALUE and LAST_VALUE for category X
    category_x = [r for r in results if r['category'] == 'X']
    for row in category_x:
        assert row['first_sales'] == 100  # First chronologically
        assert row['last_sales'] == 150   # Last chronologically
    
    # Verify FIRST_VALUE and LAST_VALUE for category Y
    category_y = [r for r in results if r['category'] == 'Y']
    for row in category_y:
        assert row['first_sales'] == 300  # First chronologically
        assert row['last_sales'] == 250   # Last chronologically


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_window_with_group_by_and_order_by(create_tables, db_cursor):
    """Test window function over GROUP BY aggregates."""
    table_name = create_tables[0]
    
    # Insert data for aggregation
    test_data = [
        ("Electronics", 1000), ("Electronics", 1500), ("Electronics", 800),
        ("Books", 200), ("Books", 350), ("Books", 150),
        ("Clothing", 500), ("Clothing", 750)
    ]
    
    for category, sales in test_data:
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (category, sales))
    
    # Test window function over aggregated data
    db_cursor.execute(f"""
        SELECT category, total_sales,
               RANK() OVER (ORDER BY total_sales DESC) as sales_rank
        FROM (
            SELECT col2 as category, SUM(col3) as total_sales
            FROM {table_name}
            GROUP BY col2
        ) aggregated
        ORDER BY sales_rank
    """)
    
    results = db_cursor.fetchall()
    
    # Verify aggregated totals and ranks
    # Electronics: 1000+1500+800 = 3300 (rank 1)
    # Clothing: 500+750 = 1250 (rank 2)  
    # Books: 200+350+150 = 700 (rank 3)
    
    assert len(results) == 3
    assert results[0]['category'] == 'Electronics' and results[0]['total_sales'] == 3300 and results[0]['sales_rank'] == 1
    assert results[1]['category'] == 'Clothing' and results[1]['total_sales'] == 1250 and results[1]['sales_rank'] == 2
    assert results[2]['category'] == 'Books' and results[2]['total_sales'] == 700 and results[2]['sales_rank'] == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_window_function_in_subquery_filtering(create_tables, db_cursor):
    """Test window function in subquery with WHERE clause filtering."""
    table_name = create_tables[0]
    
    # Insert test data
    values = [100, 200, 300, 400, 500, 600, 700, 800, 900, 1000]
    for i, value in enumerate(values):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (f"item_{i+1}", value))
    
    # Test window function in subquery with outer WHERE filtering
    db_cursor.execute(f"""
        SELECT item, sales, row_num
        FROM (
            SELECT col2 as item, col3 as sales,
                   ROW_NUMBER() OVER (ORDER BY col3 DESC) as row_num
            FROM {table_name}
        ) ranked
        WHERE row_num <= 3
        ORDER BY row_num
    """)
    
    results = db_cursor.fetchall()
    
    # Verify top 3 records by sales
    assert len(results) == 3
    assert results[0]['sales'] == 1000 and results[0]['row_num'] == 1
    assert results[1]['sales'] == 900 and results[1]['row_num'] == 2
    assert results[2]['sales'] == 800 and results[2]['row_num'] == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_window_function_on_empty_table(create_tables, db_cursor):
    """Test window function on empty table."""
    table_name = create_tables[0]
    
    # Don't insert any data - table remains empty
    
    # Test ROW_NUMBER() on empty table
    db_cursor.execute(f"""
        SELECT col2 as item, col3 as value,
               ROW_NUMBER() OVER (ORDER BY col3) as row_num
        FROM {table_name}
    """)
    
    results = db_cursor.fetchall()
    
    # Verify 0 rows returned
    assert len(results) == 0


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_window_function_all_ties(create_tables, db_cursor):
    """Test window function with all identical values."""
    table_name = create_tables[0]
    
    # Insert 5 rows with identical values
    for i in range(5):
        db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES (%s, %s)", 
                         (f"item_{i+1}", 100))
    
    # Test RANK() with all ties
    db_cursor.execute(f"""
        SELECT col2 as item, col3 as value,
               RANK() OVER (ORDER BY col3 DESC) as rank_val,
               DENSE_RANK() OVER (ORDER BY col3 DESC) as dense_rank_val
        FROM {table_name}
        ORDER BY col1
    """)
    
    results = db_cursor.fetchall()
    
    # Verify all ranks are 1 (all tied for first place)
    assert len(results) == 5
    for result in results:
        assert result['value'] == 100
        assert result['rank_val'] == 1
        assert result['dense_rank_val'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 3, "column_types": ["SERIAL PRIMARY KEY", "VARCHAR(50)", "INTEGER"]}]
}], indirect=True)
def test_invalid_window_missing_over_clause(create_tables, db_cursor):
    """Test invalid window function syntax (missing OVER clause)."""
    table_name = create_tables[0]
    
    # Insert some test data
    db_cursor.execute(f"INSERT INTO {table_name} (col2, col3) VALUES ('test', 100)")
    
    # Test ROW_NUMBER() without OVER clause - should raise WrongObjectType error
    with pytest.raises(psycopg2.errors.WrongObjectType):
        db_cursor.execute(f"SELECT col2, ROW_NUMBER() FROM {table_name}")

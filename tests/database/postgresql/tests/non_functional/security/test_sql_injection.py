import pytest
import psycopg2


@pytest.mark.security
def test_sql_injection_prevention_select(db_cursor, benchmark_table):
    """Parameterized queries prevent SELECT injection."""
    malicious_input = "1 OR 1=1; DROP TABLE benchmark_table; --"
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (8001, "safe_user", "safe@test.com", 100.0, True))
    
    db_cursor.execute(f"""
        SELECT * FROM {benchmark_table} WHERE username = %s;
    """, (malicious_input,))
    
    results = db_cursor.fetchall()
    assert len(results) == 0
    
    db_cursor.execute(f"""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = '{benchmark_table}'
        );
    """)
    table_exists = db_cursor.fetchone()[0]
    assert table_exists is True


@pytest.mark.security
def test_sql_injection_prevention_insert(db_cursor, benchmark_table):
    """Injection prevention in INSERT statements."""
    malicious_username = "admin'; DROP TABLE users; --"
    malicious_email = "test@test.com' OR '1'='1"
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (8002, malicious_username, malicious_email, 50.0, True))
    
    db_cursor.execute(f"""
        SELECT username, email FROM {benchmark_table} WHERE user_id = 8002;
    """)
    result = db_cursor.fetchone()
    
    assert result['username'] == malicious_username
    assert result['email'] == malicious_email


@pytest.mark.security
def test_sql_injection_prevention_update(db_cursor, benchmark_table):
    """Injection prevention in UPDATE statements."""
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (8003, "original_user", "original@test.com", 75.0, True))
    
    malicious_update = "100.0; DELETE FROM benchmark_table; --"
    
    db_cursor.execute(f"""
        UPDATE {benchmark_table}
        SET score = %s
        WHERE user_id = %s;
    """, (malicious_update, 8003))
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {benchmark_table};")
    count = db_cursor.fetchone()['count']
    assert count > 0


@pytest.mark.security
def test_sql_injection_union_attacks(db_cursor, benchmark_table):
    """UNION-based injection attempts."""
    malicious_input = "1 UNION SELECT id, username, email, score, created_at, is_active, metadata FROM other_table --"
    
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (8004, "test_user", "test@test.com", 50.0, True))
    
    db_cursor.execute(f"""
        SELECT * FROM {benchmark_table}
        WHERE user_id = %s;
    """, (malicious_input,))
    
    results = db_cursor.fetchall()
    assert len(results) == 0


@pytest.mark.security
def test_sql_injection_blind_attacks(db_cursor, benchmark_table):
    """Boolean-based blind injection."""
    db_cursor.execute(f"""
        INSERT INTO {benchmark_table} (user_id, username, email, score, is_active)
        VALUES (%s, %s, %s, %s, %s);
    """, (8005, "blind_test", "blind@test.com", 60.0, True))
    
    malicious_condition = "8005' AND '1'='1"
    
    db_cursor.execute(f"""
        SELECT * FROM {benchmark_table}
        WHERE user_id = %s;
    """, (malicious_condition,))
    
    results = db_cursor.fetchall()
    assert len(results) == 0


@pytest.mark.security
def test_stored_procedure_injection(db_cursor):
    """Injection via function parameters."""
    db_cursor.execute("""
        CREATE OR REPLACE FUNCTION get_user_by_id(p_user_id INT)
        RETURNS TABLE(user_id INT, username VARCHAR) AS $$
        BEGIN
            RETURN QUERY SELECT 1 as user_id, 'test'::VARCHAR as username;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    malicious_input = "1; DROP TABLE benchmark_table; --"
    
    with pytest.raises(psycopg2.Error):
        db_cursor.execute(f"SELECT * FROM get_user_by_id({malicious_input});")
    
    db_cursor.execute("DROP FUNCTION IF EXISTS get_user_by_id(INT);")


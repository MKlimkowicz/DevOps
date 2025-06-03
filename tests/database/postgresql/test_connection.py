import pytest


def test_simple_select_one(db_cursor):
    """Test basic PostgreSQL connectivity with SELECT 1."""
    db_cursor.execute("SELECT 1;")
    result = db_cursor.fetchone()
    
    assert result is not None
    assert result[0] == 1 
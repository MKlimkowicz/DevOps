import pytest
import psycopg2
import json


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSON"]}]
}], indirect=True)
def test_insert_json_data(create_tables, db_cursor):
    """Test inserting JSON data."""
    table_name = create_tables[0]
    
    json_data = {"name": "test", "value": 123, "nested": {"key": "val"}}
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (%s)", (json.dumps(json_data),))
    
    db_cursor.execute(f"SELECT col2 FROM {table_name}")
    result = db_cursor.fetchone()['col2']
    
    assert result == json_data


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_insert_jsonb_data(create_tables, db_cursor):
    """Test inserting JSONB data."""
    table_name = create_tables[0]
    
    json_data = {"name": "test", "value": 456}
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES (%s)", (json.dumps(json_data),))
    
    db_cursor.execute(f"SELECT col2 FROM {table_name}")
    result = db_cursor.fetchone()['col2']
    
    assert result == json_data


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_containment_operator(create_tables, db_cursor):
    """Test JSONB @> containment operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"c\": 3}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"b\": 2, \"c\": 3}}'::jsonb)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 @> '{{\"a\": 1}}'")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_contained_by_operator(create_tables, db_cursor):
    """Test JSONB <@ contained by operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2}}'::jsonb)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 <@ '{{\"a\": 1, \"b\": 2, \"c\": 3}}'")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_key_exists_operator(create_tables, db_cursor):
    """Test JSONB ? key exists operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"name\": \"test\", \"age\": 30}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"name\": \"test2\"}}'::jsonb)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 ? 'age'")
    assert db_cursor.fetchone()['count'] == 1


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_any_key_exists_operator(create_tables, db_cursor):
    """Test JSONB ?| any key exists operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"c\": 3, \"d\": 4}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"e\": 5}}'::jsonb)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 ?| array['a', 'c']")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_all_keys_exist_operator(create_tables, db_cursor):
    """Test JSONB ?& all keys exist operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2, \"c\": 3}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2}}'::jsonb)")
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1}}'::jsonb)")
    
    db_cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE col2 ?& array['a', 'b']")
    assert db_cursor.fetchone()['count'] == 2


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_extract_value(create_tables, db_cursor):
    """Test extracting value from JSONB using -> operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"name\": \"John\", \"age\": 30}}'::jsonb)")
    
    db_cursor.execute(f"SELECT col2 ->> 'name' as name FROM {table_name}")
    result = db_cursor.fetchone()['name']
    
    assert result == 'John'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_extract_text_value(create_tables, db_cursor):
    """Test extracting text value from JSONB using ->> operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"name\": \"Jane\", \"age\": 25}}'::jsonb)")
    
    db_cursor.execute(f"SELECT col2 ->> 'name' as name FROM {table_name}")
    result = db_cursor.fetchone()['name']
    
    assert result == "Jane"


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_nested_access(create_tables, db_cursor):
    """Test accessing nested JSONB values."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"user\": {{\"name\": \"Bob\", \"address\": {{\"city\": \"NYC\"}}}}}}'::jsonb)")
    
    db_cursor.execute(f"SELECT col2 #>> '{{{{user,address,city}}}}' as city FROM {table_name}")
    result = db_cursor.fetchone()['city']
    
    assert result == 'NYC'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_nested_text_access(create_tables, db_cursor):
    """Test accessing nested JSONB values as text."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"user\": {{\"name\": \"Alice\", \"age\": 28}}}}'::jsonb)")
    
    db_cursor.execute(f"SELECT col2 #>> '{{{{user,name}}}}' as name FROM {table_name}")
    result = db_cursor.fetchone()['name']
    
    assert result == "Alice"


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_array_element_access(create_tables, db_cursor):
    """Test accessing JSONB array elements."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"items\": [1, 2, 3, 4, 5]}}'::jsonb)")
    
    db_cursor.execute(f"SELECT col2 -> 'items' -> 2 as third_item FROM {table_name}")
    result = db_cursor.fetchone()['third_item']
    
    assert result == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_array_length(create_tables, db_cursor):
    """Test getting length of JSONB array."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"items\": [\"a\", \"b\", \"c\"]}}'::jsonb)")
    
    db_cursor.execute(f"SELECT jsonb_array_length(col2 -> 'items') as length FROM {table_name}")
    result = db_cursor.fetchone()['length']
    
    assert result == 3


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_object_keys(create_tables, db_cursor):
    """Test extracting JSONB object keys."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2, \"c\": 3}}'::jsonb)")
    
    db_cursor.execute(f"SELECT jsonb_object_keys(col2) as key FROM {table_name}")
    keys = [row['key'] for row in db_cursor.fetchall()]
    
    assert set(keys) == {'a', 'b', 'c'}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_concatenation(create_tables, db_cursor):
    """Test JSONB concatenation operator."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1}}'::jsonb)")
    
    db_cursor.execute(f"UPDATE {table_name} SET col2 = col2 || '{{\"b\": 2}}'::jsonb")
    
    db_cursor.execute(f"SELECT col2 FROM {table_name}")
    result = db_cursor.fetchone()['col2']
    
    assert result == {"a": 1, "b": 2}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_delete_key(create_tables, db_cursor):
    """Test deleting key from JSONB."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1, \"b\": 2, \"c\": 3}}'::jsonb)")
    
    db_cursor.execute(f"UPDATE {table_name} SET col2 = col2 - 'b'")
    
    db_cursor.execute(f"SELECT col2 FROM {table_name}")
    result = db_cursor.fetchone()['col2']
    
    assert result == {"a": 1, "c": 3}


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_set_value(create_tables, db_cursor):
    """Test setting value in JSONB using jsonb_set."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"name\": \"old\", \"age\": 20}}'::jsonb)")
    
    db_cursor.execute(f"UPDATE {table_name} SET col2 = jsonb_set(col2, '{{name}}', '\"new\"')")
    
    db_cursor.execute(f"SELECT col2 ->> 'name' as name FROM {table_name}")
    result = db_cursor.fetchone()['name']
    
    assert result == "new"


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_insert_value(create_tables, db_cursor):
    """Test inserting value in JSONB using jsonb_insert."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\": 1}}'::jsonb)")
    
    db_cursor.execute(f"UPDATE {table_name} SET col2 = jsonb_insert(col2, '{{b}}', '2')")
    
    db_cursor.execute(f"SELECT col2 FROM {table_name}")
    result = db_cursor.fetchone()['col2']
    
    assert 'b' in result


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_typeof(create_tables, db_cursor):
    """Test getting JSONB value type."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"str\": \"text\", \"num\": 123, \"bool\": true}}'::jsonb)")
    
    db_cursor.execute(f"SELECT jsonb_typeof(col2 -> 'str') as str_type, jsonb_typeof(col2 -> 'num') as num_type FROM {table_name}")
    result = db_cursor.fetchone()
    
    assert result['str_type'] == 'string'
    assert result['num_type'] == 'number'


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSONB"]}]
}], indirect=True)
def test_jsonb_to_record(create_tables, db_cursor):
    """Test converting JSONB to record."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"name\": \"Test\", \"value\": 100}}'::jsonb)")
    
    db_cursor.execute(f"SELECT * FROM {table_name}, jsonb_to_record(col2) as x(name text, value int)")
    result = db_cursor.fetchone()
    
    assert result['name'] == 'Test'
    assert result['value'] == 100


@pytest.mark.parametrize("create_tables", [{
    "num_tables": 1,
    "tables": [{"num_columns": 2, "column_types": ["SERIAL PRIMARY KEY", "JSON"]}]
}], indirect=True)
def test_json_vs_jsonb_storage(create_tables, db_cursor):
    """Test that JSON and JSONB handle whitespace differently."""
    table_name = create_tables[0]
    
    db_cursor.execute(f"INSERT INTO {table_name} (col2) VALUES ('{{\"a\":  1,  \"b\":  2}}')")
    
    db_cursor.execute(f"SELECT col2::text as json_text FROM {table_name}")
    result = db_cursor.fetchone()['json_text']
    
    assert result == '{"a":  1,  "b":  2}'


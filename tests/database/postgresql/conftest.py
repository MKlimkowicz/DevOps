import pytest
import psycopg2
import time
import subprocess
import sys
import os
from psycopg2.extras import RealDictCursor
from psycopg2 import sql
import random
from datetime import datetime, timedelta, date
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))


@pytest.fixture(scope="session")
def db_config():
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "database": os.getenv("POSTGRES_DB", "appdb"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "devops-test-password")
    }


@pytest.fixture(scope="session")
def ensure_postgres_running(db_config):
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=postgres-test", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            check=True
        )
        
        if "postgres-test" not in result.stdout:
            subprocess.run(
                ["docker-compose", "up", "-d", "postgresql"],
                cwd=os.path.dirname(os.path.abspath(__file__)),
                check=True
            )
            
            max_attempts = 30
            for attempt in range(max_attempts):
                try:
                    result = subprocess.run(
                        ["docker", "exec", "postgres-test", "pg_isready", 
                         "-U", db_config["user"], "-d", db_config["database"]],
                        capture_output=True,
                        check=True
                    )
                    if result.returncode == 0:
                        break
                except subprocess.CalledProcessError:
                    pass
                
                if attempt == max_attempts - 1:
                    pytest.fail("PostgreSQL failed to start within expected time")
                
                time.sleep(2)
            
    except subprocess.CalledProcessError as e:
        pytest.fail(f"Failed to start PostgreSQL container: {e}")


@pytest.fixture(scope="session")
def db_connection(db_config, ensure_postgres_running):
    connection = None
    max_attempts = 10
    
    for attempt in range(max_attempts):
        try:
            connection = psycopg2.connect(
                host=db_config["host"],
                port=db_config["port"],
                database=db_config["database"],
                user=db_config["user"],
                password=db_config["password"],
                cursor_factory=RealDictCursor
            )
            connection.autocommit = True
            break
        except psycopg2.OperationalError as e:
            if attempt == max_attempts - 1:
                pytest.fail(f"Failed to connect to PostgreSQL after {max_attempts} attempts: {e}")
            time.sleep(2)
    
    try:
        yield connection
    finally:
        if connection:
            connection.close()


@pytest.fixture
def db_cursor(db_connection):
    cursor = db_connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


@pytest.fixture(scope="function")
def create_tables(db_cursor, request):
    config = getattr(request, "param", {})
    num_tables = config.get("num_tables", 1)
    tables_config = config.get("tables", [{} for _ in range(num_tables)])
    
    if len(tables_config) != num_tables:
        pytest.fail("Number of table configs must match num_tables")
    
    created_tables = []
    
    for i in range(num_tables):
        table_name = f"test_table_{i+1}"
        created_tables.append(table_name)
        try:
            db_cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE;")
        except Exception:
            pass
    
    try:
        for i in range(num_tables):
            table_config = tables_config[i]
            num_columns = table_config.get("num_columns", 1)
            column_types = table_config.get("column_types", ["VARCHAR(255)"] * num_columns)
            
            if len(column_types) != num_columns:
                pytest.fail(f"Number of column types must match num_columns for table {i+1}")
            
            table_name = created_tables[i]
            columns = ", ".join([f"col{j+1} {column_types[j]}" for j in range(num_columns)])
            create_sql = f"CREATE TABLE {table_name} ({columns});"
            
            db_cursor.execute(create_sql)
        
        yield created_tables
    
    finally:
        for table in created_tables:
            try:
                db_cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
            except Exception:
                pass


@pytest.fixture
def generate_ints(request):
    params = getattr(request, 'param', {})
    num_rows = params.get('num_rows', 10)
    length = params.get('length', None)
    if length:
        min_val = 10 ** (length - 1)
        max_val = (10 ** length) - 1
    else:
        min_val = 0
        max_val = 1000
    return [random.randint(min_val, max_val) for _ in range(num_rows)]

@pytest.fixture
def generate_floats(request):
    params = getattr(request, 'param', {})
    num_rows = params.get('num_rows', 10)
    length = params.get('length', 2)
    min_val = 0.0
    max_val = 1000.0
    return [round(random.uniform(min_val, max_val), length) for _ in range(num_rows)]

@pytest.fixture
def generate_strings(request):
    params = getattr(request, 'param', {})
    num_rows = params.get('num_rows', 10)
    length = params.get('length', 10)
    import string
    return [''.join(random.choices(string.ascii_letters + string.digits, k=length)) for _ in range(num_rows)]

@pytest.fixture
def generate_timestamps(request):
    params = getattr(request, 'param', {})
    num_rows = params.get('num_rows', 10)
    start = datetime.now() - timedelta(days=365)
    return [start + timedelta(seconds=random.randint(0, 365*24*60*60)) for _ in range(num_rows)]

@pytest.fixture
def generate_dates(request):
    params = getattr(request, 'param', {})
    num_rows = params.get('num_rows', 10)
    start = date.today() - timedelta(days=365)
    return [start + timedelta(days=random.randint(0, 365)) for _ in range(num_rows)]

@pytest.fixture
def generate_bools(request):
    params = getattr(request, 'param', {})
    num_rows = params.get('num_rows', 10)
    return [random.choice([True, False]) for _ in range(num_rows)]


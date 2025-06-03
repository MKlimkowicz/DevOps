import pytest
import psycopg2
import boto3
from psycopg2.extras import RealDictCursor


@pytest.fixture(scope="session")
def db_config():
    """Database configuration for PostgreSQL instance."""
    return {
        "host": "10.0.20.81",  # Application instance private IP
        "port": 30432,
        "database": "appdb",
        "user": "postgres",
        "region": "eu-central-1"
    }


@pytest.fixture(scope="session")
def db_password(db_config):
    """Retrieve PostgreSQL password from AWS Parameter Store."""
    ssm = boto3.client('ssm', region_name=db_config["region"])
    
    try:
        response = ssm.get_parameter(
            Name='/devops/dev/postgres/password',
            WithDecryption=True
        )
        return response['Parameter']['Value']
    except Exception as e:
        pytest.fail(f"Failed to retrieve PostgreSQL password from Parameter Store: {e}")


@pytest.fixture(scope="session")
def db_connection(db_config, db_password):
    """Create PostgreSQL database connection."""
    connection = None
    try:
        connection = psycopg2.connect(
            host=db_config["host"],
            port=db_config["port"],
            database=db_config["database"],
            user=db_config["user"],
            password=db_password,
            cursor_factory=RealDictCursor
        )
        connection.autocommit = True
        yield connection
    except Exception as e:
        pytest.fail(f"Failed to connect to PostgreSQL: {e}")
    finally:
        if connection:
            connection.close()


@pytest.fixture
def db_cursor(db_connection):
    """Create database cursor for executing queries."""
    cursor = db_connection.cursor()
    try:
        yield cursor
    finally:
        cursor.close() 
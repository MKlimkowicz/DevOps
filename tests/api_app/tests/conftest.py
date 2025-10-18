import pytest
import asyncio
import sys
import os

os.environ.setdefault("API_KEY", "test-api-key-for-testing")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import db
from auth import API_KEY


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def mock_rate_limit_dependency():
    pass


async def mock_strict_rate_limit_dependency():
    pass


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from rate_limiter import rate_limit_dependency, strict_rate_limit_dependency
    
    app.dependency_overrides[rate_limit_dependency] = mock_rate_limit_dependency
    app.dependency_overrides[strict_rate_limit_dependency] = mock_strict_rate_limit_dependency
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    import httpx
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), 
        base_url="http://test"
    ) as async_test_client:
        yield async_test_client


@pytest.fixture
def auth_headers():
    return {"Authorization": f"Bearer {API_KEY}"}


@pytest.fixture
def invalid_auth_headers():
    return {"Authorization": "Bearer invalid-key"}


@pytest.fixture(autouse=True)
def reset_database():
    db.__init__()
    yield


@pytest.fixture
def sample_book_data():
    return {
        "title": "Test Book",
        "author": "Test Author", 
        "publication_year": 2020,
        "description": "Test description"
    }


@pytest.fixture
def minimal_book_data():
    return {
        "title": "Minimal Test Book",
        "author": "Minimal Author",
        "publication_year": 2021
    }


@pytest.fixture
def update_book_data():
    return {
        "title": "Updated Test Book",
        "author": "Updated Author",
        "publication_year": 2022,
        "description": "Updated description"
    }


@pytest.fixture
def invalid_book_data():
    return {
        "future_year": {
            "title": "Future Book",
            "author": "Future Author",
            "publication_year": 2026
        },
        "past_year": {
            "title": "Ancient Book", 
            "author": "Ancient Author",
            "publication_year": 1899
        },
        "invalid_year_type": {
            "title": "Invalid Year Book",
            "author": "Invalid Author", 
            "publication_year": "not_a_number"
        },
        "long_title": {
            "title": "A" * 201,
            "author": "Long Title Author",
            "publication_year": 2020
        },
        "long_author": {
            "title": "Long Author Book",
            "author": "B" * 101,
            "publication_year": 2020
        },
        "long_description": {
            "title": "Long Description Book",
            "author": "Long Description Author",
            "publication_year": 2020,
            "description": "C" * 1001
        }
    }


@pytest.fixture
def db_with_bulk_data():
    from database import db
    
    db.__init__()
    db.populate_bulk_data(100)
    yield db
    db.__init__()


@pytest.fixture
def db_with_large_dataset():
    from database import db
    
    db.__init__()
    db.populate_bulk_data(1000)
    yield db
    db.__init__()


@pytest.fixture
def performance_client(client):
    from utils.performance import ResponseTimer
    
    client.timer = ResponseTimer()
    return client


@pytest.fixture
def security_test_data():
    from factories import malicious_input_generator, edge_case_generator
    
    return {
        "malicious": malicious_input_generator(),
        "edge_cases": edge_case_generator()
    }


@pytest.fixture
def load_test_config():
    return {
        "concurrent_users_baseline": 10,
        "concurrent_users_normal": 50,
        "concurrent_users_high": 100,
        "test_duration_seconds": 60,
        "ramp_up_seconds": 10,
        "think_time_seconds": 1
    }

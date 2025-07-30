import pytest
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app
from database import db
from auth import API_KEY


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


async def mock_rate_limit_dependency():
    """Mock rate limiter that does nothing during tests"""
    pass


async def mock_strict_rate_limit_dependency():
    """Mock strict rate limiter that does nothing during tests"""
    pass


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from fastapi.testclient import TestClient
    from rate_limiter import rate_limit_dependency, strict_rate_limit_dependency
    
    app.dependency_overrides[rate_limit_dependency] = mock_rate_limit_dependency
    app.dependency_overrides[strict_rate_limit_dependency] = mock_strict_rate_limit_dependency
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client():
    """Create an async test client for the FastAPI app."""
    import httpx
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), 
        base_url="http://test"
    ) as async_test_client:
        yield async_test_client


@pytest.fixture
def auth_headers():
    """Return authentication headers with valid API key."""
    return {"Authorization": f"Bearer {API_KEY}"}


@pytest.fixture
def invalid_auth_headers():
    """Return authentication headers with invalid API key."""
    return {"Authorization": "Bearer invalid-key"}


@pytest.fixture(autouse=True)
def reset_database():
    """Reset the database before each test to ensure clean state."""
    db.__init__()
    yield


@pytest.fixture
def sample_book_data():
    """Return sample book data for testing."""
    return {
        "title": "Test Book",
        "author": "Test Author", 
        "publication_year": 2020,
        "description": "Test description"
    }


@pytest.fixture
def minimal_book_data():
    """Return minimal required book data for testing."""
    return {
        "title": "Minimal Test Book",
        "author": "Minimal Author",
        "publication_year": 2021
    }


@pytest.fixture
def update_book_data():
    """Return book data for update operations."""
    return {
        "title": "Updated Test Book",
        "author": "Updated Author",
        "publication_year": 2022,
        "description": "Updated description"
    }


@pytest.fixture
def invalid_book_data():
    """Return various invalid book data for validation testing."""
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
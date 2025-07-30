# Functional Tests for Books Management API

This directory contains comprehensive functional tests for the Books Management API, covering all 26 scenarios requested.

## Test Structure

### Test Files

1. **`test_books_crud.py`** - Core CRUD operations (Scenarios 1-12)
2. **`test_books_error_handling.py`** - Error handling and validation (Scenarios 13-18)
3. **`test_books_advanced.py`** - Advanced features and edge cases (Scenarios 19-26)

### Configuration

- **`conftest.py`** - Pytest fixtures and test configuration
- **`pytest.ini`** - Pytest settings and markers
- **`__init__.py`** - Package initialization

## Test Scenarios Coverage

### Basic CRUD Operations (Scenarios 1-12)
- ✅ Retrieve all books (39 books total)
- ✅ Retrieve single book by valid ID (ID 1 and 22)
- ✅ Filter books by author (George Orwell)
- ✅ Filter books by publication year (1951)
- ✅ Combined author and year filtering
- ✅ Filter with no matches
- ✅ Add new book with complete data
- ✅ Add new book with minimum required fields
- ✅ Update existing book (full and partial)
- ✅ Delete existing book

### Error Handling & Validation (Scenarios 13-18)
- ✅ Retrieve non-existent book (404 error)
- ✅ Add book with invalid year (too old/too new)
- ✅ Update with invalid data types
- ✅ Delete non-existent book
- ✅ Filter with invalid query parameters
- ✅ Authentication errors (missing/invalid API key)
- ✅ Input validation (string length limits)

### Advanced Features & Edge Cases (Scenarios 19-26)
- ✅ Duplicate book handling
- ✅ Large dataset pagination simulation
- ✅ Rate limiting behavior
- ✅ Case sensitivity in filters
- ✅ Empty database state simulation
- ✅ Concurrent operations
- ✅ Input validation for strings
- ✅ Boundary value testing
- ✅ Special characters and Unicode support

## Running the Tests

### Prerequisites

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure the API server is available (tests use TestClient, no separate server needed)

### Run All Tests

```bash
# Run all functional tests
pytest tests/functional/

# Run with verbose output
pytest tests/functional/ -v

# Run specific test file
pytest tests/functional/test_books_crud.py

# Run specific test
pytest tests/functional/test_books_crud.py::TestBooksCRUD::test_retrieve_all_books
```

### Run Tests by Category

```bash
# Run CRUD tests only
pytest tests/functional/test_books_crud.py

# Run error handling tests
pytest tests/functional/test_books_error_handling.py

# Run advanced feature tests
pytest tests/functional/test_books_advanced.py
```

### Generate Test Report

```bash
# Generate HTML report
pytest tests/functional/ --html=report.html --self-contained-html

# Generate coverage report
pytest tests/functional/ --cov=. --cov-report=html
```

## Test Data

The tests use the predefined sample data from the API:
- 39 books with IDs 1-39
- Authors include George Orwell, Harper Lee, etc.
- Publication years range from 1925 to 2018
- Complete book details with titles, authors, years, and descriptions

## Authentication

Tests use the configured API key: `your-secret-api-key-12345`

Write operations (POST, PUT, DELETE) require authentication:
- Valid authentication headers are provided via fixtures
- Invalid authentication scenarios are tested explicitly

## Database Reset

Each test runs with a fresh database state using the `reset_database` fixture, ensuring test isolation and repeatability.

## Expected Results

All tests should pass when run against a properly functioning Books Management API. Any failures indicate:

1. **API implementation issues** - If core functionality doesn't work as expected
2. **Data inconsistencies** - If the sample data doesn't match expected values
3. **Configuration problems** - If authentication or rate limiting isn't configured properly
4. **Environment issues** - If dependencies or test setup is incorrect

## Test Coverage Summary

- **CRUD Operations**: 12 scenarios ✅
- **Error Handling**: 6 scenarios ✅ 
- **Advanced Features**: 8 scenarios ✅
- **Total**: 26 scenarios ✅

Each scenario thoroughly validates:
- HTTP status codes
- Response structure
- Data accuracy
- Error messages
- Edge cases
- Concurrent behavior

## Notes

- Tests are designed to be independent and can run in any order
- Database state is reset between tests for consistency
- Authentication headers are handled automatically via fixtures
- Rate limiting tests may behave differently depending on server load
- Unicode and special character tests ensure proper encoding support 
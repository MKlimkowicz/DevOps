# Books Management API

A production-ready RESTful API built with FastAPI for managing a collection of books. Features comprehensive CRUD operations, authentication, rate limiting, and extensive test coverage with 200+ tests across functional, security, performance, load, and reliability categories.

## Features

- **CRUD Operations**: Create, Read, Update, and Delete books
- **Data Validation**: Comprehensive input validation using Pydantic models
- **Filtering**: Search books by author or publication year
- **Authentication**: Environment-based API key authentication for write operations
- **Rate Limiting**: Built-in rate limiting (100 req/min read, 10 req/min write)
- **Error Handling**: Proper HTTP status codes and error messages
- **Interactive Documentation**: Auto-generated Swagger UI and ReDoc
- **CORS Support**: Configurable cross-origin resource sharing
- **Modular Structure**: Clean architecture with routers and utilities
- **Environment Configuration**: Secure configuration management with .env files
- **Extensive Testing**: 200+ tests covering all aspects of the API

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)
- Virtual environment (recommended)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd DevOps/tests/api_app
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env to set your API_KEY
   ```

5. **Start the server:**
   ```bash
   python main.py
   ```

   The API will be available at: http://localhost:8000

## Configuration

### Environment Variables

Create a `.env` file in the project root (copy from `.env.example`):

```env
# API Configuration
API_KEY=your-secret-api-key-12345

# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=sqlite:///./books.db

# CORS Configuration (comma-separated list)
CORS_ORIGINS=*

# Rate Limiting
RATE_LIMIT_READ_MAX=100
RATE_LIMIT_WRITE_MAX=10
RATE_LIMIT_WINDOW_SECONDS=60
```

#### Environment Variable Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_KEY` | **Yes** | None | Secret key for API authentication. Used to authorize write operations (POST, PUT, DELETE) |
| `HOST` | No | `0.0.0.0` | Server host address. Use `127.0.0.1` for localhost only, `0.0.0.0` for all interfaces |
| `PORT` | No | `8000` | Server port number |
| `LOG_LEVEL` | No | `info` | Logging verbosity level (`debug`, `info`, `warning`, `error`, `critical`) |
| `ENVIRONMENT` | No | `development` | Runtime environment. Set to `production` to disable auto-reload |
| `DATABASE_URL` | No | `sqlite:///./books.db` | Database connection string (currently unused - in-memory DB) |
| `CORS_ORIGINS` | No | `*` | Comma-separated list of allowed CORS origins. Use `*` for all origins or specify domains like `http://localhost:3000,https://example.com` |
| `RATE_LIMIT_READ_MAX` | No | `100` | Maximum number of read requests (GET) allowed per time window |
| `RATE_LIMIT_WRITE_MAX` | No | `10` | Maximum number of write requests (POST, PUT, DELETE) allowed per time window |
| `RATE_LIMIT_WINDOW_SECONDS` | No | `60` | Time window in seconds for rate limiting |

#### Configuration Examples

**Development (default):**
```env
API_KEY=dev-key-12345
ENVIRONMENT=development
LOG_LEVEL=debug
CORS_ORIGINS=*
```

**Production:**
```env
API_KEY=prod-secure-key-xyz789
ENVIRONMENT=production
LOG_LEVEL=warning
CORS_ORIGINS=https://myapp.com,https://api.myapp.com
RATE_LIMIT_READ_MAX=1000
RATE_LIMIT_WRITE_MAX=50
```

**Testing:**
```env
API_KEY=test-api-key
ENVIRONMENT=development
LOG_LEVEL=info
RATE_LIMIT_READ_MAX=10000
RATE_LIMIT_WRITE_MAX=10000
```

## API Documentation

Once the server is running, you can access:

- **Swagger UI (Interactive)**: http://localhost:8000/docs
- **ReDoc (Alternative)**: http://localhost:8000/redoc
- **API Info**: http://localhost:8000/info
- **Health Check**: http://localhost:8000/health

## Endpoints

### Public Endpoints (No Authentication Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/books` | Get all books with optional filtering |
| GET | `/books/{book_id}` | Get a specific book by ID |
| GET | `/health` | Health check endpoint |
| GET | `/info` | API information and usage guide |

### Protected Endpoints (API Key Required)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/books` | Create a new book |
| PUT | `/books/{book_id}` | Update an existing book |
| DELETE | `/books/{book_id}` | Delete a book |

## Authentication

Write operations require API key authentication. Include the API key in the Authorization header:

```bash
Authorization: Bearer your-secret-api-key-12345
```

The API key is configured via the `.env` file and should never be committed to version control.

## Data Model

Books contain the following fields:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | integer | Auto-generated | Unique | Book identifier |
| `title` | string | Yes | 1-200 characters | Book title |
| `author` | string | Yes | 1-100 characters | Book author |
| `publication_year` | integer | Yes | 1900 to current year | Publication year |
| `description` | string | No | Max 1000 characters | Book description |

## Usage Examples

### Get All Books

```bash
curl -X GET "http://localhost:8000/books"
```

### Filter Books by Author

```bash
curl -X GET "http://localhost:8000/books?author=George%20Orwell"
```

### Create a New Book

```bash
curl -X POST "http://localhost:8000/books" \
  -H "Authorization: Bearer your-secret-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The Hobbit",
    "author": "J.R.R. Tolkien",
    "publication_year": 1937,
    "description": "A fantasy adventure novel"
  }'
```

### Update a Book

```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Authorization: Bearer your-secret-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description"}'
```

### Delete a Book

```bash
curl -X DELETE "http://localhost:8000/books/1" \
  -H "Authorization: Bearer your-secret-api-key-12345"
```

## Testing

### Test Suite Overview

The API includes comprehensive test coverage with 200+ tests across multiple categories:

- **Functional Tests**: CRUD operations, filtering, data integrity
- **Security Tests**: Authentication, input validation, API security
- **Performance Tests**: Response time, resource usage
- **Load Tests**: Concurrent users, sustained load, stress testing
- **Reliability Tests**: Error recovery, stability

### Running Tests

**Install test dependencies:**
```bash
pip install -r requirements.txt
```

**Run all tests:**
```bash
pytest tests/
```

**Quick functional tests (exclude slow tests):**
```bash
pytest -m "functional and not slow"
```

**Run tests by category:**
```bash
pytest -m security        # Security tests only
pytest -m performance     # Performance tests only
pytest -m load           # Load tests only
pytest -m reliability    # Reliability tests only
```

**Run specific test file:**
```bash
pytest tests/functional/test_books_crud.py
pytest tests/non-functional/test_security_auth.py
```

**Run with verbose output:**
```bash
pytest -v tests/
```

### Test Categories

#### Functional Tests
- **CRUD Operations**: Basic create, read, update, delete operations
- **Advanced Filtering**: Case sensitivity, unicode, special characters
- **Data Integrity**: Concurrent operations, race conditions, idempotency

#### Security Tests
- **Authentication**: API key validation, bypass attempts, malformed tokens
- **Input Validation**: SQL injection, XSS, command injection, path traversal
- **API Security**: CORS, malformed requests, parameter pollution

#### Performance Tests
- **Response Time**: SLA compliance for all endpoints
- **Resource Usage**: Memory, CPU monitoring, leak detection
- **Optimization**: Query efficiency with large datasets

#### Load Tests
- **Concurrent Users**: 10, 50, 100+ concurrent users
- **Sustained Load**: Constant load over time
- **Stress Testing**: Finding breaking points, recovery testing

#### Reliability Tests
- **Error Recovery**: Database reset, malformed requests, rollback
- **Stability**: 1000+ repeated operations, random sequences

### Test Infrastructure

**Test Utilities** (`tests/utils/`):
- `performance.py`: Response timing, resource monitoring, load generation
- `security.py`: Security scanners, payload collections

**Test Factories** (`tests/factories.py`):
- Data generators for various test scenarios
- Bulk data generation for load testing
- Malicious input generators for security testing

**Test Fixtures** (`tests/conftest.py`):
- Standard fixtures for client, auth, sample data
- Bulk data fixtures (100, 1000 books)
- Performance and security testing fixtures

### Performance Metrics

**SLA Targets** (measured with 10 sample books):
- GET all books: < 100ms
- GET single book: < 50ms
- POST book creation: < 200ms
- PUT book update: < 150ms
- DELETE book: < 100ms

**Load Testing Results**:
- Tested with up to 1000 books in database
- Handles 100+ concurrent users
- 95%+ success rate under normal load

## Sample Data

The API comes pre-loaded with 10 sample books:

1. **To Kill a Mockingbird** by Harper Lee (1960)
2. **1984** by George Orwell (1949)
3. **The Great Gatsby** by F. Scott Fitzgerald (1925)
4. **The Catcher in the Rye** by J.D. Salinger (1951)
5. **Animal Farm** by George Orwell (1945)
6. **Brave New World** by Aldous Huxley (1932)
7. **The Hobbit** by J.R.R. Tolkien (1937)
8. **The Fellowship of the Ring** by J.R.R. Tolkien (1954)
9. **Foundation** by Isaac Asimov (1951)
10. **Gone Girl** by Gillian Flynn (2012)

## Project Structure

```
api_app/
├── main.py                      # FastAPI application entry point
├── models.py                    # Pydantic data models
├── database.py                  # In-memory database management
├── auth.py                      # Authentication utilities
├── rate_limiter.py              # Rate limiting functionality
├── routers/
│   ├── __init__.py
│   └── books.py                 # Book-related endpoints
├── tests/
│   ├── conftest.py              # Test fixtures and configuration
│   ├── factories.py             # Test data generators
│   ├── utils/
│   │   ├── performance.py       # Performance testing utilities
│   │   └── security.py          # Security testing utilities
│   ├── functional/
│   │   ├── test_books_crud.py
│   │   ├── test_books_filtering.py
│   │   ├── test_books_integrity.py
│   │   ├── test_books_advanced.py
│   │   └── test_books_error_handling.py
│   └── non-functional/
│       ├── test_security_auth.py
│       ├── test_security_input.py
│       ├── test_security_api.py
│       ├── test_performance_response.py
│       ├── test_performance_resources.py
│       ├── test_load_concurrent.py
│       ├── test_load_sustained.py
│       ├── test_load_stress.py
│       ├── test_reliability_recovery.py
│       └── test_reliability_stability.py
├── .env                         # Environment variables (not in git)
├── .env.example                 # Environment template (committed)
├── .gitignore                   # Git ignore patterns
├── requirements.txt             # Python dependencies
├── pytest.ini                   # Pytest configuration
└── README.md                    # This file
```

## Development Best Practices

### Virtual Environment

Always use a virtual environment:
```bash
python -m venv venv
source venv/bin/activate
```

### Environment Variables

Never commit `.env` files. Always use `.env.example` as a template:
```bash
cp .env.example .env
# Edit .env with your values
```

### Running Tests Before Commits

Run quick tests:
```bash
pytest -m "functional and not slow"
```

Run security tests:
```bash
pytest -m security
```

### Test Markers

Use markers for selective testing:
- `functional`: Functional/integration tests
- `security`: Security-focused tests
- `performance`: Performance benchmarks
- `load`: Load and stress tests
- `reliability`: Reliability and stability tests
- `slow`: Tests that take > 30 seconds

## CI/CD Integration

### Suggested Test Pipeline

**Fast Feedback (< 2 min):**
```bash
pytest -m "functional and not slow"
```

**Security Scan (< 5 min):**
```bash
pytest -m security
```

**Performance Baseline (< 10 min):**
```bash
pytest -m "performance and not slow"
```

**Full Suite (< 30 min):**
```bash
pytest tests/
```

### Test Environment Configuration

For CI/CD, set environment variables:
```bash
export API_KEY=test-api-key-for-ci
export ENVIRONMENT=testing
pytest tests/
```

## Security Considerations

### Production Deployment Checklist

- [ ] Use strong, unique API key in `.env`
- [ ] Never commit `.env` file to version control
- [ ] Implement proper database persistence
- [ ] Configure specific CORS origins (not `*`)
- [ ] Enable HTTPS/TLS
- [ ] Add request logging and monitoring
- [ ] Implement rate limiting per user/IP
- [ ] Consider OAuth2 for user authentication
- [ ] Regular security audits with test suite
- [ ] Keep dependencies updated

### Environment-Based API Key

The API key is now managed through environment variables:
- Development: Set in `.env` file
- Production: Set via environment variables or secrets manager
- Testing: Can be overridden in test fixtures

## Error Handling

The API returns appropriate HTTP status codes:

- `200 OK`: Successful GET/PUT requests
- `201 Created`: Successful POST requests
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `409 Conflict`: Duplicate book (same title and author)
- `422 Unprocessable Entity`: Validation errors
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Contributing

When contributing:

1. Create a virtual environment and install dependencies
2. Copy `.env.example` to `.env` and configure
3. Write tests for new features
4. Run the test suite before submitting
5. Follow the existing code style (no comments, minimal docstrings)
6. Update README if adding new features

## License

This project is licensed under the MIT License.

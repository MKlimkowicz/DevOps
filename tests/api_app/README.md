# Books Management API

A simple RESTful API built with FastAPI for managing a collection of books. This API provides full CRUD operations with built-in data validation, authentication, rate limiting, and comprehensive error handling.

## Features

- ✅ **CRUD Operations**: Create, Read, Update, and Delete books
- ✅ **Data Validation**: Comprehensive input validation using Pydantic models
- ✅ **Filtering**: Search books by author or publication year
- ✅ **Authentication**: API key authentication for write operations
- ✅ **Rate Limiting**: Built-in rate limiting to handle high request volumes
- ✅ **Error Handling**: Proper HTTP status codes and error messages
- ✅ **Interactive Documentation**: Auto-generated Swagger UI and ReDoc
- ✅ **CORS Support**: Cross-origin resource sharing enabled
- ✅ **Modular Structure**: Organized with separate routers and components

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

### Installation

1. **Navigate to the project directory:**
   ```bash
   cd DevOps/tests/api_app
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the server:**
   ```bash
   python main.py
   ```

   The API will be available at: http://localhost:8000

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

## Rate Limiting

- **Read operations**: 100 requests per minute
- **Write operations**: 10 requests per minute

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

### 1. Get All Books

```bash
curl -X GET "http://localhost:8000/books"
```

### 2. Filter Books by Author

```bash
curl -X GET "http://localhost:8000/books?author=George%20Orwell"
```

### 3. Filter Books by Publication Year

```bash
curl -X GET "http://localhost:8000/books?publication_year=2018"
```

### Advanced Filtering Examples

```bash
# Find all books by Tolkien
curl -X GET "http://localhost:8000/books?author=Tolkien"

# Find books from the 1950s
curl -X GET "http://localhost:8000/books?publication_year=1954"

# Search for authors containing "Miller" (case-insensitive)
curl -X GET "http://localhost:8000/books?author=Miller"
```

### 4. Get a Specific Book

```bash
curl -X GET "http://localhost:8000/books/1"
```

### 5. Create a New Book (Requires API Key)

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

### 6. Update a Book (Requires API Key)

```bash
curl -X PUT "http://localhost:8000/books/1" \
  -H "Authorization: Bearer your-secret-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Updated description for the book"
  }'
```

### 7. Delete a Book (Requires API Key)

```bash
curl -X DELETE "http://localhost:8000/books/1" \
  -H "Authorization: Bearer your-secret-api-key-12345"
```

## Sample Data

The API comes pre-loaded with 36 sample books across various genres:

### Classic Literature
- **To Kill a Mockingbird** by Harper Lee (1960)
- **1984** by George Orwell (1949)
- **The Great Gatsby** by F. Scott Fitzgerald (1925)
- **Animal Farm** by George Orwell (1945)
- **Brave New World** by Aldous Huxley (1932)

### Fantasy & Science Fiction
- **Dune** by Frank Herbert (1965)
- **The Hobbit** by J.R.R. Tolkien (1937)
- **Foundation** by Isaac Asimov (1951)
- **Fahrenheit 451** by Ray Bradbury (1953)

### Mystery & Thriller
- **Gone Girl** by Gillian Flynn (2012)
- **The Girl with the Dragon Tattoo** by Stieg Larsson (2005)
- **The Murder of Roger Ackroyd** by Agatha Christie (1926)

### Contemporary Literature
- **The Road** by Cormac McCarthy (2006)
- **Life of Pi** by Yann Martel (2001)
- **Where the Crawdads Sing** by Delia Owens (2018)

And many more across Historical Fiction, Modern Fiction, and Literary Classics!

## Error Handling

The API returns appropriate HTTP status codes and error messages:

- `200 OK`: Successful GET/PUT requests
- `201 Created`: Successful POST requests
- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Resource not found
- `409 Conflict`: Duplicate book (same title and author)
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## Project Structure

```
api_app/
├── main.py                 # FastAPI application entry point
├── models.py               # Pydantic data models
├── database.py             # In-memory database management
├── auth.py                 # Authentication utilities
├── rate_limiter.py         # Rate limiting functionality
├── routers/
│   ├── __init__.py
│   └── books.py           # Book-related endpoints
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

## Development

### Running in Development Mode

The application runs with auto-reload enabled by default, so changes to the code will automatically restart the server.

### Testing with Different Tools

- **curl**: Command-line examples provided above
- **Postman**: Import the OpenAPI spec from http://localhost:8000/openapi.json
- **HTTPie**: `http GET localhost:8000/books`
- **Python requests**: Use the interactive documentation at `/docs`

## Security Considerations

For production deployment:

1. Use environment variables for the API key
2. Implement proper database persistence
3. Set up proper CORS origins
4. Add request logging and monitoring
5. Implement user authentication instead of a single API key
6. Use HTTPS

## License

This project is licensed under the MIT License. 
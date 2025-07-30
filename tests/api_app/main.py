from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from routers import books
import uvicorn

app = FastAPI(
    title="Books Management API",
    description="""
    A simple RESTful API for managing a collection of books with CRUD operations.
    
    ## Features
    
    * **CRUD Operations**: Create, Read, Update, and Delete books
    * **Filtering**: Search books by author or publication year
    * **Data Validation**: Comprehensive input validation using Pydantic models
    * **Authentication**: Optional API key authentication for write operations
    * **Rate Limiting**: Built-in rate limiting to handle high request volumes
    * **Error Handling**: Proper HTTP status codes and error messages
    * **Interactive Documentation**: Auto-generated Swagger UI and ReDoc
    
    ## Authentication
    
    Write operations (POST, PUT, DELETE) require API key authentication.
    Include the API key in the Authorization header:
    
    ```
    Authorization: Bearer your-secret-api-key-12345
    ```
    
    ## Rate Limiting
    
    * Read operations: 100 requests per minute
    * Write operations: 10 requests per minute
    
    ## Data Model
    
    Books contain the following fields:
    * **id**: Auto-generated unique identifier
    * **title**: Book title (1-200 characters)
    * **author**: Book author (1-100 characters)
    * **publication_year**: Year of publication (1900 to current year)
    * **description**: Optional book description (max 1000 characters)
    """,
    version="1.0.0",
    terms_of_service="http://localhost:8000/terms/",
    contact={
        "name": "API Support",
        "email": "support@booksapi.com",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)


@app.get("/", include_in_schema=False)
async def root():
    """Redirect root to documentation"""
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "message": "Books Management API is running successfully",
        "version": "1.0.0"
    }


@app.get("/info", tags=["Info"])
async def api_info():
    """API information and usage guide"""
    return {
        "api_name": "Books Management API",
        "version": "1.0.0",
        "description": "RESTful API for managing book collections",
        "endpoints": {
            "books": {
                "GET /books": "Retrieve all books with optional filtering",
                "GET /books/{id}": "Get a specific book by ID",
                "POST /books": "Create a new book (requires API key)",
                "PUT /books/{id}": "Update a book (requires API key)",
                "DELETE /books/{id}": "Delete a book (requires API key)"
            },
            "documentation": {
                "Swagger UI": "/docs",
                "ReDoc": "/redoc",
                "OpenAPI JSON": "/openapi.json"
            }
        },
        "authentication": {
            "type": "API Key",
            "header": "Authorization: Bearer your-secret-api-key-12345",
            "required_for": ["POST", "PUT", "DELETE"]
        },
        "rate_limits": {
            "read_operations": "100 requests per minute",
            "write_operations": "10 requests per minute"
        },
        "sample_book": {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "publication_year": 1925,
            "description": "A classic American novel set in the Jazz Age"
        }
    }


if __name__ == "__main__":
    print("🚀 Starting Books Management API...")
    print("📚 Access the API documentation at: http://localhost:8000/docs")
    print("🔑 API Key for protected routes: your-secret-api-key-12345")
    print("💡 Use 'Authorization: Bearer your-secret-api-key-12345' for write operations")
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 
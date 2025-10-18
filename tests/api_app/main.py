from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from routers import books
import uvicorn
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Books Management API",
    description="A RESTful API for managing books with CRUD operations, authentication, and rate limiting.",
    version="1.0.0",
    contact={"name": "API Support", "email": "support@booksapi.com"},
    license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
)

cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in cors_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books.router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "message": "Books Management API is running", "version": "1.0.0"}


@app.get("/info", tags=["Info"])
async def api_info():
    return {
        "api_name": "Books Management API",
        "version": "1.0.0",
        "endpoints": {
            "GET /books": "Retrieve all books",
            "GET /books/{id}": "Get book by ID",
            "POST /books": "Create book (requires API key)",
            "PUT /books/{id}": "Update book (requires API key)",
            "DELETE /books/{id}": "Delete book (requires API key)"
        },
        "auth_header": "Authorization: Bearer <your-api-key>",
        "rate_limits": {"read": "100/min", "write": "10/min"}
    }


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    environment = os.getenv("ENVIRONMENT", "development")
    
    print(f"Starting Books Management API on http://{host}:{port}")
    print(f"Environment: {environment}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=environment == "development",
        log_level=os.getenv("LOG_LEVEL", "info")
    ) 
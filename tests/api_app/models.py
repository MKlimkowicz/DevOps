from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Book title")
    author: str = Field(..., min_length=1, max_length=100, description="Book author")
    publication_year: int = Field(..., ge=1900, le=datetime.now().year, description="Publication year")
    description: Optional[str] = Field(None, max_length=1000, description="Book description")


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="Book title")
    author: Optional[str] = Field(None, min_length=1, max_length=100, description="Book author")
    publication_year: Optional[int] = Field(None, ge=1900, le=datetime.now().year, description="Publication year")
    description: Optional[str] = Field(None, max_length=1000, description="Book description")


class Book(BookBase):
    id: int = Field(..., description="Unique book ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "publication_year": 1925,
                "description": "A classic American novel set in the Jazz Age"
            }
        }


class BookResponse(BaseModel):
    message: str
    book: Optional[Book] = None


class BooksListResponse(BaseModel):
    books: list[Book]
    total: int
    filtered_by: Optional[dict] = None 
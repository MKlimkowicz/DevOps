from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    publication_year: int = Field(..., ge=1900, le=datetime.now().year)
    description: Optional[str] = Field(None, max_length=1000)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    author: Optional[str] = Field(None, min_length=1, max_length=100)
    publication_year: Optional[int] = Field(None, ge=1900, le=datetime.now().year)
    description: Optional[str] = Field(None, max_length=1000)


class Book(BookBase):
    id: int


class BookResponse(BaseModel):
    message: str
    book: Optional[Book] = None


class BooksListResponse(BaseModel):
    books: list[Book]
    total: int
    filtered_by: Optional[dict] = None 
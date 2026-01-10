from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import Optional, List
from models import Book, BookCreate, BookUpdate, BookResponse, BooksListResponse
from database import db
from auth import get_api_key
from rate_limiter import rate_limit_dependency, strict_rate_limit_dependency

router = APIRouter(
    tags=["books"],
    dependencies=[Depends(rate_limit_dependency)]
)


def validate_book_id(book_id: int):
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer"
        )


def ensure_book_exists(book_id: int):
    if not db.book_exists(book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )


def check_duplicate_book(title: str, author: str, exclude_id: Optional[int] = None):
    existing_books = db.get_all_books()
    for book in existing_books:
        if book.id != exclude_id and book.title.lower() == title.lower() and book.author.lower() == author.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A book with the same title and author already exists"
            )


@router.get("/books", response_model=BooksListResponse)
async def get_books(
    author: Optional[str] = Query(None),
    publication_year: Optional[int] = Query(None)
):
    books = db.get_all_books(author=author, publication_year=publication_year)
    
    filters = {}
    if author:
        filters["author"] = author
    if publication_year:
        filters["publication_year"] = publication_year
    
    return BooksListResponse(
        books=books,
        total=len(books),
        filtered_by=filters if filters else None
    )


@router.get("/books/{book_id}", response_model=Book)
async def get_book(book_id: int):
    validate_book_id(book_id)
    
    book = db.get_book(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )
    
    return book


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book_data: BookCreate,
    api_key: str = Depends(get_api_key),
    _: None = Depends(strict_rate_limit_dependency)
):
    check_duplicate_book(book_data.title, book_data.author)
    
    new_book = db.create_book(book_data)
    return BookResponse(message="Book created successfully", book=new_book)


@router.put("/books/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    api_key: str = Depends(get_api_key),
    _: None = Depends(strict_rate_limit_dependency)
):
    validate_book_id(book_id)
    ensure_book_exists(book_id)
    
    update_data = book_update.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update"
        )
    
    if "title" in update_data or "author" in update_data:
        current_book = db.get_book(book_id)
        new_title = update_data.get("title", current_book.title)
        new_author = update_data.get("author", current_book.author)
        check_duplicate_book(new_title, new_author, exclude_id=book_id)
    
    updated_book = db.update_book(book_id, book_update)
    return BookResponse(message="Book updated successfully", book=updated_book)


@router.delete("/books/{book_id}", response_model=BookResponse)
async def delete_book(
    book_id: int,
    api_key: str = Depends(get_api_key),
    _: None = Depends(strict_rate_limit_dependency)
):
    validate_book_id(book_id)
    ensure_book_exists(book_id)
    
    success = db.delete_book(book_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book"
        )
    
    return BookResponse(message=f"Book with ID {book_id} deleted successfully")

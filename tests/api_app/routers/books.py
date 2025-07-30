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


@router.get("/books", response_model=BooksListResponse, summary="Get all books")
async def get_books(
    author: Optional[str] = Query(None, description="Filter by author name (case-insensitive partial match)"),
    publication_year: Optional[int] = Query(None, description="Filter by publication year")
):
    """
    Retrieve all books with optional filtering.
    
    - **author**: Filter books by author name (partial, case-insensitive match)
    - **publication_year**: Filter books by exact publication year
    """
    try:
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
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving books: {str(e)}"
        )


@router.get("/books/{book_id}", response_model=Book, summary="Get a specific book")
async def get_book(book_id: int):
    """
    Retrieve a specific book by its ID.
    
    - **book_id**: The unique identifier of the book
    """
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer"
        )
    
    book = db.get_book(book_id)
    if not book:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )
    
    return book


@router.post("/books", response_model=BookResponse, status_code=status.HTTP_201_CREATED, summary="Create a new book")
async def create_book(
    book_data: BookCreate,
    api_key: str = Depends(get_api_key),
    _: None = Depends(strict_rate_limit_dependency)
):
    """
    Create a new book. Requires API key authentication.
    
    - **title**: Book title (required, 1-200 characters)
    - **author**: Book author (required, 1-100 characters)
    - **publication_year**: Year of publication (required, between 1900 and current year)
    - **description**: Optional book description (max 1000 characters)
    """
    try:
        existing_books = db.get_all_books()
        for existing_book in existing_books:
            if (existing_book.title.lower() == book_data.title.lower() and 
                existing_book.author.lower() == book_data.author.lower()):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A book with the same title and author already exists"
                )
        
        new_book = db.create_book(book_data)
        return BookResponse(
            message="Book created successfully",
            book=new_book
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating book: {str(e)}"
        )


@router.put("/books/{book_id}", response_model=BookResponse, summary="Update a book")
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    api_key: str = Depends(get_api_key),
    _: None = Depends(strict_rate_limit_dependency)
):
    """
    Update an existing book. Requires API key authentication.
    Allows partial updates - only provided fields will be updated.
    
    - **book_id**: The unique identifier of the book to update
    - **title**: New book title (optional, 1-200 characters)
    - **author**: New book author (optional, 1-100 characters)
    - **publication_year**: New publication year (optional, between 1900 and current year)
    - **description**: New book description (optional, max 1000 characters)
    """
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer"
        )
    
    if not db.book_exists(book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )
    
    update_data = book_update.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update"
        )
    
    try:
        if "title" in update_data or "author" in update_data:
            existing_books = db.get_all_books()
            current_book = db.get_book(book_id)
            
            new_title = update_data.get("title", current_book.title)
            new_author = update_data.get("author", current_book.author)
            
            for existing_book in existing_books:
                if (existing_book.id != book_id and 
                    existing_book.title.lower() == new_title.lower() and 
                    existing_book.author.lower() == new_author.lower()):
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="A book with the same title and author already exists"
                    )
        
        updated_book = db.update_book(book_id, book_update)
        return BookResponse(
            message="Book updated successfully",
            book=updated_book
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating book: {str(e)}"
        )


@router.delete("/books/{book_id}", response_model=BookResponse, summary="Delete a book")
async def delete_book(
    book_id: int,
    api_key: str = Depends(get_api_key),
    _: None = Depends(strict_rate_limit_dependency)
):
    """
    Delete a book by its ID. Requires API key authentication.
    
    - **book_id**: The unique identifier of the book to delete
    """
    if book_id <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Book ID must be a positive integer"
        )
    
    if not db.book_exists(book_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Book with ID {book_id} not found"
        )
    
    try:
        success = db.delete_book(book_id)
        if success:
            return BookResponse(
                message=f"Book with ID {book_id} deleted successfully"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete book"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting book: {str(e)}"
        ) 
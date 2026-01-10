import random
import sys
from typing import Dict, List, Optional

from faker import Faker
from models import Book, BookCreate, BookUpdate


class InMemoryDB:
    def __init__(self):
        self.books: Dict[int, Book] = {}
        self.next_id: int = 1
        self._populate_sample_data()
    
    def _populate_sample_data(self):
        sample_books = [
            {"title": "To Kill a Mockingbird", "author": "Harper Lee", "publication_year": 1960, 
             "description": "A classic novel about racial injustice in the American South"},
            {"title": "1984", "author": "George Orwell", "publication_year": 1949,
             "description": "A dystopian social science fiction novel"},
            {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald", "publication_year": 1925,
             "description": "A classic American novel set in the Jazz Age"},
            {"title": "The Catcher in the Rye", "author": "J.D. Salinger", "publication_year": 1951,
             "description": "A controversial novel about teenage rebellion"},
            {"title": "Animal Farm", "author": "George Orwell", "publication_year": 1945,
             "description": "An allegorical novella about farm animals who rebel against their human farmer"},
            {"title": "Brave New World", "author": "Aldous Huxley", "publication_year": 1932,
             "description": "A dystopian social science fiction novel set in a futuristic World State"},
            {"title": "The Hobbit", "author": "J.R.R. Tolkien", "publication_year": 1937,
             "description": "A fantasy adventure novel about Bilbo Baggins' unexpected journey"},
            {"title": "The Fellowship of the Ring", "author": "J.R.R. Tolkien", "publication_year": 1954,
             "description": "The first volume of The Lord of the Rings epic fantasy trilogy"},
            {"title": "Foundation", "author": "Isaac Asimov", "publication_year": 1951,
             "description": "A science fiction novel about psychohistory and the fall of a galactic empire"},
            {"title": "Gone Girl", "author": "Gillian Flynn", "publication_year": 2012,
             "description": "A psychological thriller about a marriage gone terribly wrong"},
        ]
        
        for book_data in sample_books:
            book = Book(id=self.next_id, **book_data)
            self.books[self.next_id] = book
            self.next_id += 1
    
    def create_book(self, book_data: BookCreate) -> Book:
        book = Book(id=self.next_id, **book_data.model_dump())
        self.books[self.next_id] = book
        self.next_id += 1
        return book
    
    def get_book(self, book_id: int) -> Optional[Book]:
        return self.books.get(book_id)
    
    def get_all_books(self, author: Optional[str] = None, publication_year: Optional[int] = None) -> List[Book]:
        books = list(self.books.values())
        
        if author:
            books = [book for book in books if author.lower() in book.author.lower()]
        
        if publication_year:
            books = [book for book in books if book.publication_year == publication_year]
        
        return books
    
    def update_book(self, book_id: int, book_update: BookUpdate) -> Optional[Book]:
        if book_id not in self.books:
            return None
        
        existing_book = self.books[book_id]
        update_data = book_update.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(existing_book, field, value)
        
        return existing_book
    
    def delete_book(self, book_id: int) -> bool:
        if book_id in self.books:
            del self.books[book_id]
            return True
        return False
    
    def book_exists(self, book_id: int) -> bool:
        return book_id in self.books
    
    def populate_bulk_data(self, count: int):
        fake = Faker()
        for i in range(count):
            book = Book(
                id=self.next_id,
                title=f"{fake.catch_phrase()} {self.next_id}",
                author=fake.name(),
                publication_year=random.randint(1900, 2025),
                description=fake.text(max_nb_chars=150)
            )
            self.books[self.next_id] = book
            self.next_id += 1
    
    def clear_all(self):
        self.books.clear()
        self.next_id = 1
    
    def get_stats(self) -> Dict[str, int]:
        total_size = sys.getsizeof(self.books)
        for book in self.books.values():
            total_size += sys.getsizeof(book)
        
        return {
            "total_books": len(self.books),
            "next_id": self.next_id,
            "memory_bytes": total_size
        }


db = InMemoryDB()

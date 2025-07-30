from typing import Dict, List, Optional
from models import Book, BookCreate, BookUpdate


class InMemoryDB:
    def __init__(self):
        self.books: Dict[int, Book] = {}
        self.next_id: int = 1
        self._populate_sample_data()
    
    def _populate_sample_data(self):
        """Add comprehensive sample books for demonstration"""
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
            {"title": "Of Mice and Men", "author": "John Steinbeck", "publication_year": 1937,
             "description": "A story of friendship and dreams during the Great Depression"},
            {"title": "Lord of the Flies", "author": "William Golding", "publication_year": 1954,
             "description": "A novel about British boys stranded on an uninhabited island"},
            
            {"title": "The Handmaid's Tale", "author": "Margaret Atwood", "publication_year": 1985,
             "description": "A dystopian novel set in a totalitarian society called Gilead"},
            {"title": "Beloved", "author": "Toni Morrison", "publication_year": 1987,
             "description": "A powerful novel about slavery and its lasting effects"},
            {"title": "The Color Purple", "author": "Alice Walker", "publication_year": 1982,
             "description": "An epistolary novel about African American women in the early 20th century"},
            {"title": "One Hundred Years of Solitude", "author": "Gabriel García Márquez", "publication_year": 1967,
             "description": "A landmark work of magical realism"},
            {"title": "Slaughterhouse-Five", "author": "Kurt Vonnegut", "publication_year": 1969,
             "description": "A satirical novel about World War II experiences and journeys through time"},
            
            {"title": "Dune", "author": "Frank Herbert", "publication_year": 1965,
             "description": "An epic science fiction novel set on the desert planet Arrakis"},
            {"title": "The Hobbit", "author": "J.R.R. Tolkien", "publication_year": 1937,
             "description": "A fantasy adventure novel about Bilbo Baggins' unexpected journey"},
            {"title": "The Fellowship of the Ring", "author": "J.R.R. Tolkien", "publication_year": 1954,
             "description": "The first volume of The Lord of the Rings epic fantasy trilogy"},
            {"title": "Foundation", "author": "Isaac Asimov", "publication_year": 1951,
             "description": "A science fiction novel about psychohistory and the fall of a galactic empire"},
            {"title": "Fahrenheit 451", "author": "Ray Bradbury", "publication_year": 1953,
             "description": "A dystopian novel about a society where books are burned"},
            {"title": "The Left Hand of Darkness", "author": "Ursula K. Le Guin", "publication_year": 1969,
             "description": "A groundbreaking science fiction novel exploring gender and society"},
            
            {"title": "The Murder of Roger Ackroyd", "author": "Agatha Christie", "publication_year": 1926,
             "description": "A classic mystery novel featuring detective Hercule Poirot"},
            {"title": "The Big Sleep", "author": "Raymond Chandler", "publication_year": 1939,
             "description": "A hard-boiled detective novel featuring private investigator Philip Marlowe"},
            {"title": "Gone Girl", "author": "Gillian Flynn", "publication_year": 2012,
             "description": "A psychological thriller about a marriage gone terribly wrong"},
            {"title": "The Girl with the Dragon Tattoo", "author": "Stieg Larsson", "publication_year": 2005,
             "description": "A crime thriller combining murder mystery, family saga, and financial intrigue"},
            
            {"title": "All Quiet on the Western Front", "author": "Erich Maria Remarque", "publication_year": 1929,
             "description": "A powerful anti-war novel about German soldiers in World War I"},
            {"title": "The Book Thief", "author": "Markus Zusak", "publication_year": 2005,
             "description": "A novel narrated by Death about a young girl in Nazi Germany"},
            {"title": "Cold Mountain", "author": "Charles Frazier", "publication_year": 1997,
             "description": "A Civil War novel about a Confederate soldier's journey home"},
            {"title": "The Kite Runner", "author": "Khaled Hosseini", "publication_year": 2003,
             "description": "A story of friendship and redemption set against Afghanistan's tumultuous history"},
            
            {"title": "The Road", "author": "Cormac McCarthy", "publication_year": 2006,
             "description": "A post-apocalyptic novel about a father and son's journey"},
            {"title": "Life of Pi", "author": "Yann Martel", "publication_year": 2001,
             "description": "A survival story about a boy stranded on a lifeboat with a Bengal tiger"},
            {"title": "The Curious Incident of the Dog in the Night-Time", "author": "Mark Haddon", "publication_year": 2003,
             "description": "A mystery novel narrated by a teenager with autism"},
            {"title": "Never Let Me Go", "author": "Kazuo Ishiguro", "publication_year": 2005,
             "description": "A dystopian science fiction novel about clones raised for organ donation"},
            
            {"title": "Invisible Man", "author": "Ralph Ellison", "publication_year": 1952,
             "description": "A novel about social and intellectual issues facing African Americans"},
            {"title": "Catch-22", "author": "Joseph Heller", "publication_year": 1961,
             "description": "A satirical war novel set during World War II"},
            {"title": "On the Road", "author": "Jack Kerouac", "publication_year": 1957,
             "description": "A novel based on travels across the United States"},
            {"title": "The Sound and the Fury", "author": "William Faulkner", "publication_year": 1929,
             "description": "A modernist novel employing stream of consciousness"},
            
            {"title": "Where the Crawdads Sing", "author": "Delia Owens", "publication_year": 2018,
             "description": "A mystery novel about a girl who grew up isolated in the marshes of North Carolina"},
            {"title": "The Seven Husbands of Evelyn Hugo", "author": "Taylor Jenkins Reid", "publication_year": 2017,
             "description": "A novel about a reclusive Hollywood icon who finally decides to tell her story"},
            {"title": "Educated", "author": "Tara Westover", "publication_year": 2018,
             "description": "A memoir about a woman who grows up in a survivalist family"},
            {"title": "Circe", "author": "Madeline Miller", "publication_year": 2018,
             "description": "A reimagining of the myth of Circe from Greek mythology"},
        ]
        
        for book_data in sample_books:
            book = Book(id=self.next_id, **book_data)
            self.books[self.next_id] = book
            self.next_id += 1
    
    def create_book(self, book_data: BookCreate) -> Book:
        """Create a new book"""
        book = Book(id=self.next_id, **book_data.dict())
        self.books[self.next_id] = book
        self.next_id += 1
        return book
    
    def get_book(self, book_id: int) -> Optional[Book]:
        """Get a book by ID"""
        return self.books.get(book_id)
    
    def get_all_books(self, author: Optional[str] = None, publication_year: Optional[int] = None) -> List[Book]:
        """Get all books with optional filtering"""
        books = list(self.books.values())
        
        if author:
            books = [book for book in books if author.lower() in book.author.lower()]
        
        if publication_year:
            books = [book for book in books if book.publication_year == publication_year]
        
        return books
    
    def update_book(self, book_id: int, book_update: BookUpdate) -> Optional[Book]:
        """Update a book by ID"""
        if book_id not in self.books:
            return None
        
        existing_book = self.books[book_id]
        update_data = book_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(existing_book, field, value)
        
        return existing_book
    
    def delete_book(self, book_id: int) -> bool:
        """Delete a book by ID"""
        if book_id in self.books:
            del self.books[book_id]
            return True
        return False
    
    def book_exists(self, book_id: int) -> bool:
        """Check if a book exists"""
        return book_id in self.books


db = InMemoryDB() 
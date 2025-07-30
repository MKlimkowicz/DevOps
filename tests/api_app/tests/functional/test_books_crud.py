import pytest
from fastapi import status


class TestBooksCRUD:
    """Test basic CRUD operations for the books API."""
    
    def test_retrieve_all_books(self, client):
        """
        Scenario 1: Retrieve All Books
        Send a GET request to /books without any query parameters and verify that 
        the response returns a list of exactly 39 books with the total count matching.
        """
        response = client.get("/books")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "books" in data
        assert "total" in data
        assert "filtered_by" in data
        
        assert data["total"] == 39
        assert len(data["books"]) == 39
        
        assert data["filtered_by"] is None
        
        book_ids = [book["id"] for book in data["books"]]
        assert sorted(book_ids) == list(range(1, 40))
        
        for book in data["books"]:
            assert "id" in book
            assert "title" in book
            assert "author" in book
            assert "publication_year" in book
            assert "description" in book
    
    def test_retrieve_single_book_by_valid_id_1(self, client):
        """
        Scenario 2: Retrieve Single Book by Valid ID
        Send a GET request to /books/1 and confirm the response matches 
        the details for "To Kill a Mockingbird".
        """
        response = client.get("/books/1")
        
        assert response.status_code == status.HTTP_200_OK
        book = response.json()
        
        assert book["id"] == 1
        assert book["title"] == "To Kill a Mockingbird"
        assert book["author"] == "Harper Lee"
        assert book["publication_year"] == 1960
        assert book["description"] == "A classic novel about racial injustice in the American South"
    
    def test_retrieve_single_book_by_valid_id_22(self, client):
        """
        Scenario 3: Retrieve Single Book by Another Valid ID
        Send a GET request to /books/22 and ensure the response includes 
        the correct details for "Gone Girl" by Gillian Flynn from 2012.
        """
        response = client.get("/books/22")
        
        assert response.status_code == status.HTTP_200_OK
        book = response.json()
        
        assert book["id"] == 22
        assert book["title"] == "Gone Girl"
        assert book["author"] == "Gillian Flynn"
        assert book["publication_year"] == 2012
        assert book["description"] == "A psychological thriller about a marriage gone terribly wrong"
    
    def test_filter_books_by_author_george_orwell(self, client):
        """
        Scenario 4: Filter Books by Author
        Send a GET request to /books with query parameter author="George Orwell" 
        and check that the response returns exactly two books (IDs 2 and 5).
        """
        response = client.get("/books?author=George Orwell")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["books"]) == 2
        assert data["filtered_by"] == {"author": "George Orwell"}
        
        book_ids = [book["id"] for book in data["books"]]
        assert sorted(book_ids) == [2, 5]
        
        for book in data["books"]:
            assert book["author"] == "George Orwell"
            
        titles = [book["title"] for book in data["books"]]
        assert "1984" in titles
        assert "Animal Farm" in titles
    
    def test_filter_books_by_publication_year_1951(self, client):
        """
        Scenario 5: Filter Books by Publication Year
        Send a GET request to /books with query parameter publication_year=1951 
        and verify the response includes appropriate books with total and filtered_by details.
        """
        response = client.get("/books?publication_year=1951")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 2
        assert len(data["books"]) == 2
        assert data["filtered_by"] == {"publication_year": 1951}
        
        for book in data["books"]:
            assert book["publication_year"] == 1951
            
        titles = [book["title"] for book in data["books"]]
        assert "The Catcher in the Rye" in titles
        assert "Foundation" in titles
    
    def test_filter_books_by_author_and_year_combined(self, client):
        """
        Scenario 6: Filter Books by Author and Year Combined
        Send a GET request to /books with parameters author="J.R.R. Tolkien" 
        and publication_year=1954, confirming it returns only "The Fellowship of the Ring".
        """
        response = client.get("/books?author=J.R.R. Tolkien&publication_year=1954")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 1
        assert len(data["books"]) == 1
        assert data["filtered_by"] == {"author": "J.R.R. Tolkien", "publication_year": 1954}
        
        book = data["books"][0]
        assert book["title"] == "The Fellowship of the Ring"
        assert book["author"] == "J.R.R. Tolkien"
        assert book["publication_year"] == 1954
        assert book["id"] == 16
    
    def test_filter_with_no_matches(self, client):
        """
        Scenario 7: Filter with No Matches
        Send a GET request to /books with author="NonExistentAuthor" and ensure 
        the response returns an empty books list with total=0.
        """
        response = client.get("/books?author=NonExistentAuthor")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["books"]) == 0
        assert data["filtered_by"] == {"author": "NonExistentAuthor"}
    
    def test_add_new_book_with_valid_data(self, client, auth_headers, sample_book_data):
        """
        Scenario 8: Add New Book with Valid Data
        Send a POST request to /books with complete JSON body and verify 
        the response includes the new book with an auto-generated ID.
        """
        response = client.post("/books", json=sample_book_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "message" in data
        assert "book" in data
        
        book = data["book"]
        assert book["id"] == 40
        assert book["title"] == sample_book_data["title"]
        assert book["author"] == sample_book_data["author"]
        assert book["publication_year"] == sample_book_data["publication_year"]
        assert book["description"] == sample_book_data["description"]
        
        get_response = client.get(f"/books/{book['id']}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json() == book
    
    def test_add_new_book_with_minimum_required_fields(self, client, auth_headers, minimal_book_data):
        """
        Scenario 9: Add New Book with Minimum Required Fields
        Send a POST request to /books with only required fields and confirm 
        the book is added successfully with description as null.
        """
        response = client.post("/books", json=minimal_book_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        book = data["book"]
        assert book["title"] == minimal_book_data["title"]
        assert book["author"] == minimal_book_data["author"]
        assert book["publication_year"] == minimal_book_data["publication_year"]
        assert book["description"] is None
    
    def test_update_existing_book_fully(self, client, auth_headers, update_book_data):
        """
        Scenario 10: Update Existing Book Fully
        Send a PUT request to /books/3 with a JSON body updating all fields 
        and verify the response reflects the changes.
        """
        original_response = client.get("/books/3")
        assert original_response.status_code == status.HTTP_200_OK
        
        response = client.put("/books/3", json=update_book_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "message" in data
        assert "book" in data
        
        book = data["book"]
        assert book["id"] == 3
        assert book["title"] == update_book_data["title"]
        assert book["author"] == update_book_data["author"]
        assert book["publication_year"] == update_book_data["publication_year"]
        assert book["description"] == update_book_data["description"]
        
        get_response = client.get("/books/3")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json() == book
    
    def test_partial_update_of_book(self, client, auth_headers):
        """
        Scenario 11: Partial Update of Book
        Send a PUT request to /books/10 with a JSON body updating only 
        the description field, ensuring other fields remain unchanged.
        """
        original_response = client.get("/books/10")
        assert original_response.status_code == status.HTTP_200_OK
        original_book = original_response.json()
        
        partial_update = {"description": "Updated description for partial test"}
        
        response = client.put("/books/10", json=partial_update, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        book = data["book"]
        assert book["id"] == 10
        assert book["title"] == original_book["title"]
        assert book["author"] == original_book["author"]
        assert book["publication_year"] == original_book["publication_year"]
        assert book["description"] == partial_update["description"]
    
    def test_delete_existing_book(self, client, auth_headers):
        """
        Scenario 12: Delete Existing Book
        Send a DELETE request to /books/15 and confirm proper status, 
        then verify subsequent GET shows total reduced and book is absent.
        """
        get_response = client.get("/books/15")
        assert get_response.status_code == status.HTTP_200_OK
        
        all_books_response = client.get("/books")
        initial_total = all_books_response.json()["total"]
        
        delete_response = client.delete("/books/15", headers=auth_headers)
        assert delete_response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        
        get_response = client.get("/books/15")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
        
        all_books_response = client.get("/books")
        new_total = all_books_response.json()["total"]
        assert new_total == initial_total - 1
        
        book_ids = [book["id"] for book in all_books_response.json()["books"]]
        assert 15 not in book_ids 
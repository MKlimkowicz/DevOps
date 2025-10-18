import pytest
from fastapi import status


def assert_book_fields(book):
    assert "id" in book
    assert "title" in book
    assert "author" in book
    assert "publication_year" in book
    assert "description" in book


def assert_response_structure(data, has_message=False, has_book=False):
    if has_message:
        assert "message" in data
    if has_book:
        assert "book" in data


class TestBooksCRUD:
    
    def test_retrieve_all_books(self, client):
        response = client.get("/books")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "books" in data
        assert "total" in data
        assert "filtered_by" in data
        
        assert data["total"] == 10
        assert len(data["books"]) == 10
        assert data["filtered_by"] is None
        
        book_ids = [book["id"] for book in data["books"]]
        assert sorted(book_ids) == list(range(1, 11))
        
        for book in data["books"]:
            assert_book_fields(book)
    
    def test_retrieve_single_book_by_valid_id_1(self, client):
        response = client.get("/books/1")
        
        assert response.status_code == status.HTTP_200_OK
        book = response.json()
        
        assert book["id"] == 1
        assert book["title"] == "To Kill a Mockingbird"
        assert book["author"] == "Harper Lee"
        assert book["publication_year"] == 1960
        assert book["description"] == "A classic novel about racial injustice in the American South"
    
    def test_retrieve_single_book_by_valid_id_10(self, client):
        response = client.get("/books/10")
        
        assert response.status_code == status.HTTP_200_OK
        book = response.json()
        
        assert book["id"] == 10
        assert book["title"] == "Gone Girl"
        assert book["author"] == "Gillian Flynn"
        assert book["publication_year"] == 2012
        assert book["description"] == "A psychological thriller about a marriage gone terribly wrong"
    
    def test_filter_books_by_author_george_orwell(self, client):
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
        assert book["id"] == 8
    
    def test_filter_with_no_matches(self, client):
        response = client.get("/books?author=NonExistentAuthor")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["books"]) == 0
        assert data["filtered_by"] == {"author": "NonExistentAuthor"}
    
    def test_add_new_book_with_valid_data(self, client, auth_headers, sample_book_data):
        response = client.post("/books", json=sample_book_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert_response_structure(data, has_message=True, has_book=True)
        
        book = data["book"]
        assert book["id"] == 11
        assert book["title"] == sample_book_data["title"]
        assert book["author"] == sample_book_data["author"]
        assert book["publication_year"] == sample_book_data["publication_year"]
        assert book["description"] == sample_book_data["description"]
        
        get_response = client.get(f"/books/{book['id']}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json() == book
    
    def test_add_new_book_with_minimum_required_fields(self, client, auth_headers, minimal_book_data):
        response = client.post("/books", json=minimal_book_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        book = data["book"]
        assert book["title"] == minimal_book_data["title"]
        assert book["author"] == minimal_book_data["author"]
        assert book["publication_year"] == minimal_book_data["publication_year"]
        assert book["description"] is None
    
    def test_update_existing_book_fully(self, client, auth_headers, update_book_data):
        original_response = client.get("/books/3")
        assert original_response.status_code == status.HTTP_200_OK
        
        response = client.put("/books/3", json=update_book_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert_response_structure(data, has_message=True, has_book=True)
        
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
        original_response = client.get("/books/5")
        assert original_response.status_code == status.HTTP_200_OK
        original_book = original_response.json()
        
        partial_update = {"description": "Updated description for partial test"}
        
        response = client.put("/books/5", json=partial_update, headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        book = data["book"]
        assert book["id"] == 5
        assert book["title"] == original_book["title"]
        assert book["author"] == original_book["author"]
        assert book["publication_year"] == original_book["publication_year"]
        assert book["description"] == partial_update["description"]
    
    def test_delete_existing_book(self, client, auth_headers):
        get_response = client.get("/books/7")
        assert get_response.status_code == status.HTTP_200_OK
        
        all_books_response = client.get("/books")
        initial_total = all_books_response.json()["total"]
        
        delete_response = client.delete("/books/7", headers=auth_headers)
        assert delete_response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        
        get_response = client.get("/books/7")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND
        
        all_books_response = client.get("/books")
        new_total = all_books_response.json()["total"]
        assert new_total == initial_total - 1
        
        book_ids = [book["id"] for book in all_books_response.json()["books"]]
        assert 7 not in book_ids

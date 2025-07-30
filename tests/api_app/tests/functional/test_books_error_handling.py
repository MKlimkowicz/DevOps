import pytest
from fastapi import status


class TestBooksErrorHandling:
    """Test error handling and validation for the books API."""
    
    def test_retrieve_non_existent_book(self, client):
        """
        Scenario 13: Retrieve Non-Existent Book
        Send a GET request to /books/999 and check for a 404 status code 
        with an error message indicating the resource not found.
        """
        response = client.get("/books/999")
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        
        assert "detail" in data
        assert "999" in data["detail"]
        assert "not found" in data["detail"].lower()
    
    def test_add_book_with_invalid_year_too_old(self, client, auth_headers, invalid_book_data):
        """
        Scenario 14: Add Book with Invalid Year
        Send a POST request with publication_year=1899 (below 1900) and verify 
        a 400 status with validation error message about the year range.
        """
        response = client.post("/books", json=invalid_book_data["past_year"], headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "publication_year" in error_details
    
    def test_add_book_with_future_year(self, client, auth_headers, invalid_book_data):
        """
        Scenario 15: Add Book with Future Year
        Send a POST request with publication_year=2026 (beyond current year 2025) 
        and ensure a 400 status with appropriate validation error.
        """
        response = client.post("/books", json=invalid_book_data["future_year"], headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "publication_year" in error_details
    
    def test_update_with_invalid_data_type(self, client, auth_headers, invalid_book_data):
        """
        Scenario 16: Update with Invalid Data
        Send a PUT request to /books/5 with publication_year="invalid_string" 
        and confirm a 422 status due to type mismatch in the input validation.
        """
        response = client.put("/books/5", json=invalid_book_data["invalid_year_type"], headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "publication_year" in error_details
    
    def test_delete_non_existent_book(self, client, auth_headers):
        """
        Scenario 17: Delete Non-Existent Book
        Send a DELETE request to /books/999 and verify a 404 status 
        with error indicating the book does not exist.
        """
        response = client.delete("/books/999", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        
        assert "detail" in data
        assert "999" in data["detail"]
        assert "not found" in data["detail"].lower()
    
    def test_filter_with_invalid_query_parameters(self, client):
        """
        Scenario 18: Filter with Invalid Query Parameters
        Send a GET request to /books with publication_year="not_an_integer" 
        and check for a 422 status with error on invalid input type.
        """
        response = client.get("/books?publication_year=not_an_integer")
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "publication_year" in error_details


class TestBooksValidation:
    """Test input validation for the books API."""
    
    def test_add_book_with_long_title(self, client, auth_headers, invalid_book_data):
        """
        Test adding a book with excessively long title (over 200 characters).
        """
        response = client.post("/books", json=invalid_book_data["long_title"], headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "title" in error_details
    
    def test_add_book_with_long_author(self, client, auth_headers, invalid_book_data):
        """
        Test adding a book with excessively long author name (over 100 characters).
        """
        response = client.post("/books", json=invalid_book_data["long_author"], headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "author" in error_details
    
    def test_add_book_with_long_description(self, client, auth_headers, invalid_book_data):
        """
        Test adding a book with excessively long description (over 1000 characters).
        """
        response = client.post("/books", json=invalid_book_data["long_description"], headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "description" in error_details
    
    def test_add_book_with_missing_required_fields(self, client, auth_headers):
        """
        Test adding a book with missing required fields.
        """
        incomplete_book = {"title": "Only Title"}
        
        response = client.post("/books", json=incomplete_book, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "author" in error_details or "publication_year" in error_details
    
    def test_add_book_with_empty_title(self, client, auth_headers):
        """
        Test adding a book with empty title string.
        """
        empty_title_book = {
            "title": "",
            "author": "Test Author",
            "publication_year": 2020
        }
        
        response = client.post("/books", json=empty_title_book, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "title" in error_details
    
    def test_add_book_with_empty_author(self, client, auth_headers):
        """
        Test adding a book with empty author string.
        """
        empty_author_book = {
            "title": "Test Title",
            "author": "",
            "publication_year": 2020
        }
        
        response = client.post("/books", json=empty_author_book, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "author" in error_details


class TestAuthenticationErrors:
    """Test authentication-related error scenarios."""
    
    def test_add_book_without_auth_header(self, client, sample_book_data):
        """
        Test adding a book without authentication header.
        """
        response = client.post("/books", json=sample_book_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        
        assert "detail" in data
        assert "API key required" in data["detail"]
    
    def test_add_book_with_invalid_auth_header(self, client, invalid_auth_headers, sample_book_data):
        """
        Test adding a book with invalid authentication header.
        """
        response = client.post("/books", json=sample_book_data, headers=invalid_auth_headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        
        assert "detail" in data
        assert "Invalid API key" in data["detail"]
    
    def test_update_book_without_auth_header(self, client, update_book_data):
        """
        Test updating a book without authentication header.
        """
        response = client.put("/books/1", json=update_book_data)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        
        assert "detail" in data
        assert "API key required" in data["detail"]
    
    def test_update_book_with_invalid_auth_header(self, client, invalid_auth_headers, update_book_data):
        """
        Test updating a book with invalid authentication header.
        """
        response = client.put("/books/1", json=update_book_data, headers=invalid_auth_headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        
        assert "detail" in data
        assert "Invalid API key" in data["detail"]
    
    def test_delete_book_without_auth_header(self, client):
        """
        Test deleting a book without authentication header.
        """
        response = client.delete("/books/1")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        
        assert "detail" in data
        assert "API key required" in data["detail"]
    
    def test_delete_book_with_invalid_auth_header(self, client, invalid_auth_headers):
        """
        Test deleting a book with invalid authentication header.
        """
        response = client.delete("/books/1", headers=invalid_auth_headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        
        assert "detail" in data
        assert "Invalid API key" in data["detail"] 
import pytest
from fastapi import status


def assert_not_found_error(response, resource_id):
    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data
    assert str(resource_id) in data["detail"]
    assert "not found" in data["detail"].lower()


def assert_validation_error(response, expected_field):
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    error_details = str(data["detail"])
    assert expected_field in error_details


def assert_auth_error(response, expected_message):
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    data = response.json()
    assert "detail" in data
    assert expected_message in data["detail"]


class TestBooksErrorHandling:
    
    def test_retrieve_non_existent_book(self, client):
        response = client.get("/books/999")
        assert_not_found_error(response, 999)
    
    def test_add_book_with_invalid_year_too_old(self, client, auth_headers, invalid_book_data):
        response = client.post("/books", json=invalid_book_data["past_year"], headers=auth_headers)
        assert_validation_error(response, "publication_year")
    
    def test_add_book_with_future_year(self, client, auth_headers, invalid_book_data):
        response = client.post("/books", json=invalid_book_data["future_year"], headers=auth_headers)
        assert_validation_error(response, "publication_year")
    
    def test_update_with_invalid_data_type(self, client, auth_headers, invalid_book_data):
        response = client.put("/books/5", json=invalid_book_data["invalid_year_type"], headers=auth_headers)
        assert_validation_error(response, "publication_year")
    
    def test_delete_non_existent_book(self, client, auth_headers):
        response = client.delete("/books/999", headers=auth_headers)
        assert_not_found_error(response, 999)
    
    def test_filter_with_invalid_query_parameters(self, client):
        response = client.get("/books?publication_year=not_an_integer")
        assert_validation_error(response, "publication_year")


class TestBooksValidation:
    
    def test_add_book_with_long_title(self, client, auth_headers, invalid_book_data):
        response = client.post("/books", json=invalid_book_data["long_title"], headers=auth_headers)
        assert_validation_error(response, "title")
    
    def test_add_book_with_long_author(self, client, auth_headers, invalid_book_data):
        response = client.post("/books", json=invalid_book_data["long_author"], headers=auth_headers)
        assert_validation_error(response, "author")
    
    def test_add_book_with_long_description(self, client, auth_headers, invalid_book_data):
        response = client.post("/books", json=invalid_book_data["long_description"], headers=auth_headers)
        assert_validation_error(response, "description")
    
    def test_add_book_with_missing_required_fields(self, client, auth_headers):
        incomplete_book = {"title": "Only Title"}
        
        response = client.post("/books", json=incomplete_book, headers=auth_headers)
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        
        assert "detail" in data
        error_details = str(data["detail"])
        assert "author" in error_details or "publication_year" in error_details
    
    def test_add_book_with_empty_title(self, client, auth_headers):
        empty_title_book = {
            "title": "",
            "author": "Test Author",
            "publication_year": 2020
        }
        
        response = client.post("/books", json=empty_title_book, headers=auth_headers)
        assert_validation_error(response, "title")
    
    def test_add_book_with_empty_author(self, client, auth_headers):
        empty_author_book = {
            "title": "Test Title",
            "author": "",
            "publication_year": 2020
        }
        
        response = client.post("/books", json=empty_author_book, headers=auth_headers)
        assert_validation_error(response, "author")


class TestAuthenticationErrors:
    
    def test_add_book_without_auth_header(self, client, sample_book_data):
        response = client.post("/books", json=sample_book_data)
        assert_auth_error(response, "API key required")
    
    def test_add_book_with_invalid_auth_header(self, client, invalid_auth_headers, sample_book_data):
        response = client.post("/books", json=sample_book_data, headers=invalid_auth_headers)
        assert_auth_error(response, "Invalid API key")
    
    def test_update_book_without_auth_header(self, client, update_book_data):
        response = client.put("/books/1", json=update_book_data)
        assert_auth_error(response, "API key required")
    
    def test_update_book_with_invalid_auth_header(self, client, invalid_auth_headers, update_book_data):
        response = client.put("/books/1", json=update_book_data, headers=invalid_auth_headers)
        assert_auth_error(response, "Invalid API key")
    
    def test_delete_book_without_auth_header(self, client):
        response = client.delete("/books/1")
        assert_auth_error(response, "API key required")
    
    def test_delete_book_with_invalid_auth_header(self, client, invalid_auth_headers):
        response = client.delete("/books/1", headers=invalid_auth_headers)
        assert_auth_error(response, "Invalid API key")

import pytest
from fastapi import status
import time


@pytest.mark.security
class TestAuthenticationSecurity:
    
    def test_missing_auth_header_on_post(self, client, sample_book_data):
        response = client.post("/books", json=sample_book_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "API key required" in response.json()["detail"]
    
    def test_missing_auth_header_on_put(self, client):
        response = client.put("/books/1", json={"title": "New Title"})
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_missing_auth_header_on_delete(self, client):
        response = client.delete("/books/1")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_malformed_auth_header_no_bearer(self, client, sample_book_data):
        headers = {"Authorization": "InvalidToken123"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_malformed_auth_header_empty_token(self, client, sample_book_data):
        headers = {"Authorization": "Bearer "}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_wrong_api_key(self, client, sample_book_data):
        headers = {"Authorization": "Bearer wrong-api-key"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid API key" in response.json()["detail"]
    
    def test_api_key_with_special_chars(self, client, sample_book_data):
        headers = {"Authorization": "Bearer <script>alert('xss')</script>"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_api_key_sql_injection_attempt(self, client, sample_book_data):
        headers = {"Authorization": "Bearer ' OR '1'='1"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_api_key_case_sensitivity(self, client, sample_book_data, auth_headers):
        correct_key = auth_headers["Authorization"].split(" ")[1]
        wrong_case_headers = {"Authorization": f"Bearer {correct_key.upper()}"}
        
        response = client.post("/books", json=sample_book_data, headers=wrong_case_headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_multiple_auth_headers(self, client, sample_book_data, auth_headers):
        headers = {
            "Authorization": auth_headers["Authorization"],
            "X-API-Key": "another-key"
        }
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_auth_bypass_with_different_methods(self, client):
        endpoints = [
            ("POST", "/books", {"title": "Test", "author": "Test", "publication_year": 2020}),
            ("PUT", "/books/1", {"title": "Updated"}),
            ("DELETE", "/books/1", None)
        ]
        
        for method, endpoint, data in endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data)
            elif method == "PUT":
                response = client.put(endpoint, json=data)
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_in_query_parameter(self, client, sample_book_data, auth_headers):
        api_key = auth_headers["Authorization"].split(" ")[1]
        response = client.post(f"/books?api_key={api_key}", json=sample_book_data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_token_in_request_body(self, client, sample_book_data, auth_headers):
        api_key = auth_headers["Authorization"].split(" ")[1]
        data_with_key = {**sample_book_data, "api_key": api_key}
        response = client.post("/books", json=data_with_key)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_auth_header_injection(self, client, sample_book_data):
        headers = {"Authorization": "Bearer test\r\nX-Injected: malicious"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_very_long_api_key(self, client, sample_book_data):
        headers = {"Authorization": f"Bearer {'A' * 10000}"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_null_byte_in_api_key(self, client, sample_book_data):
        headers = {"Authorization": "Bearer test\x00key"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_unicode_in_api_key(self, client, sample_book_data):
        headers = {"Authorization": "Bearer test🔑key"}
        response = client.post("/books", json=sample_book_data, headers=headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_read_endpoints_dont_require_auth(self, client):
        response = client.get("/books")
        assert response.status_code == status.HTTP_200_OK
        
        response = client.get("/books/1")
        assert response.status_code == status.HTTP_200_OK
    
    def test_valid_auth_allows_operations(self, client, auth_headers, sample_book_data):
        response = client.post("/books", json=sample_book_data, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        
        book_id = response.json()["book"]["id"]
        
        response = client.put(f"/books/{book_id}", json={"title": "Updated"}, headers=auth_headers)
        assert response.status_code == status.HTTP_200_OK
        
        response = client.delete(f"/books/{book_id}", headers=auth_headers)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]


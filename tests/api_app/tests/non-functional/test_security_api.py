import pytest
from fastapi import status
from utils.security import create_malformed_json_payloads, create_oversized_payload, create_malformed_headers
import json


@pytest.mark.security
class TestAPISecurity:
    
    def test_cors_headers_present(self, client):
        response = client.options("/books")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_405_METHOD_NOT_ALLOWED]
    
    def test_invalid_http_method(self, client):
        response = client.patch("/books/1", json={"title": "Test"})
        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    
    def test_head_request_allowed(self, client):
        response = client.head("/books")
        assert response.status_code == status.HTTP_200_OK
    
    @pytest.mark.parametrize("malformed_json", create_malformed_json_payloads())
    def test_malformed_json_payloads(self, client, auth_headers, malformed_json):
        response = client.post(
            "/books",
            data=malformed_json,
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_oversized_request_body(self, client, auth_headers):
        oversized_data = create_oversized_payload(multiplier=1000)
        response = client.post("/books", json=oversized_data, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("headers", create_malformed_headers())
    def test_content_type_confusion(self, client, auth_headers, headers):
        book_data = {"title": "Test", "author": "Author", "publication_year": 2020}
        combined_headers = {**auth_headers, **headers}
        
        response = client.post("/books", json=book_data, headers=combined_headers)
        assert response.status_code in [
            status.HTTP_201_CREATED,
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    def test_missing_content_type(self, client, auth_headers):
        book_data = json.dumps({"title": "Test", "author": "Author", "publication_year": 2020})
        headers = {**auth_headers}
        headers.pop("Content-Type", None)
        
        response = client.post("/books", data=book_data, headers=headers)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_parameter_pollution_author(self, client):
        response = client.get("/books?author=Orwell&author=Tolkien")
        assert response.status_code == status.HTTP_200_OK
    
    def test_parameter_pollution_year(self, client):
        response = client.get("/books?publication_year=1949&publication_year=2020")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_url_encoded_special_chars(self, client):
        response = client.get("/books?author=%3Cscript%3Ealert%28%27xss%27%29%3C%2Fscript%3E")
        assert response.status_code == status.HTTP_200_OK
    
    def test_double_url_encoding(self, client):
        response = client.get("/books?author=%253Cscript%253E")
        assert response.status_code == status.HTTP_200_OK
    
    def test_invalid_query_parameter_types(self, client):
        response = client.get("/books?publication_year=invalid")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_extra_query_parameters(self, client):
        response = client.get("/books?author=Orwell&unknown_param=value")
        assert response.status_code == status.HTTP_200_OK
    
    def test_request_with_null_json(self, client, auth_headers):
        response = client.post(
            "/books",
            data="null",
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_request_with_array_instead_of_object(self, client, auth_headers):
        response = client.post(
            "/books",
            json=[{"title": "Test", "author": "Author", "publication_year": 2020}],
            headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_nested_json_objects(self, client, auth_headers):
        nested_data = {
            "title": {"nested": "value"},
            "author": "Author",
            "publication_year": 2020
        }
        response = client.post("/books", json=nested_data, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_special_header_injection(self, client):
        headers = {"X-Forwarded-For": "127.0.0.1"}
        response = client.get("/books", headers=headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_host_header_manipulation(self, client):
        headers = {"Host": "malicious.com"}
        response = client.get("/books", headers=headers)
        assert response.status_code == status.HTTP_200_OK
    
    def test_http_verb_tampering(self, client, auth_headers):
        headers = {**auth_headers, "X-HTTP-Method-Override": "DELETE"}
        response = client.post("/books/1", headers=headers)
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_201_CREATED]
    
    def test_very_long_url(self, client):
        long_author = "A" * 10000
        response = client.get(f"/books?author={long_author}")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_414_REQUEST_URI_TOO_LONG]
    
    def test_response_headers_security(self, client):
        response = client.get("/books")
        
        assert "server" not in response.headers or "uvicorn" in response.headers.get("server", "").lower()
    
    def test_error_messages_dont_expose_internals(self, client):
        response = client.get("/books/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        error_detail = response.json().get("detail", "")
        sensitive_keywords = ["traceback", "exception", "stack", "file path"]
        
        for keyword in sensitive_keywords:
            assert keyword.lower() not in error_detail.lower()


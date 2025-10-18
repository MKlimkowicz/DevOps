import pytest
from fastapi import status
from utils.security import (
    SQL_INJECTION_PAYLOADS,
    XSS_PAYLOADS,
    COMMAND_INJECTION_PAYLOADS,
    PATH_TRAVERSAL_PAYLOADS,
    test_integer_overflow_values,
    create_unicode_attack_strings
)


@pytest.mark.security
class TestInputValidationSecurity:
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_title(self, client, auth_headers, payload):
        book_data = {
            "title": payload,
            "author": "Test Author",
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        
        if response.status_code == 201:
            book = response.json()["book"]
            assert book["title"] == payload
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("payload", SQL_INJECTION_PAYLOADS)
    def test_sql_injection_in_author(self, client, auth_headers, payload):
        book_data = {
            "title": "Test Book",
            "author": payload,
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        
        if response.status_code == 201:
            book = response.json()["book"]
            assert book["author"] == payload
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    def test_xss_injection_in_title(self, client, auth_headers, payload):
        book_data = {
            "title": payload,
            "author": "Test Author",
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        
        if response.status_code == 201:
            book = response.json()["book"]
            assert book["title"] == payload
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("payload", COMMAND_INJECTION_PAYLOADS)
    def test_command_injection_in_description(self, client, auth_headers, payload):
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "publication_year": 2020,
            "description": payload
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        
        if response.status_code == 201:
            book = response.json()["book"]
            assert book["description"] == payload
        else:
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
    def test_path_traversal_in_fields(self, client, auth_headers, payload):
        book_data = {
            "title": payload,
            "author": "Test Author",
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_negative_book_id(self, client):
        response = client.get("/books/-1")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_zero_book_id(self, client):
        response = client.get("/books/0")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    @pytest.mark.parametrize("value", test_integer_overflow_values())
    def test_integer_overflow_book_id(self, client, value):
        response = client.get(f"/books/{value}")
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_422_UNPROCESSABLE_ENTITY
        ]
    
    @pytest.mark.parametrize("value", test_integer_overflow_values())
    def test_integer_overflow_year(self, client, auth_headers, value):
        book_data = {
            "title": "Test Book",
            "author": "Test Author",
            "publication_year": value
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    @pytest.mark.parametrize("unicode_str", create_unicode_attack_strings())
    def test_unicode_attacks(self, client, auth_headers, unicode_str):
        book_data = {
            "title": unicode_str,
            "author": "Test Author",
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_null_byte_injection(self, client, auth_headers):
        book_data = {
            "title": "Test\x00Book",
            "author": "Test\x00Author",
            "publication_year": 2020,
            "description": "Test\x00Description"
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_ldap_injection_patterns(self, client, auth_headers):
        ldap_payloads = ["*)(uid=*))(|(uid=*", "admin)(|(password=*"]
        
        for payload in ldap_payloads:
            book_data = {
                "title": payload,
                "author": "Test Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_xml_injection_patterns(self, client, auth_headers):
        xml_payloads = [
            "<?xml version='1.0'?><!DOCTYPE foo>",
            "<![CDATA[test]]>",
            "&xxe;"
        ]
        
        for payload in xml_payloads:
            book_data = {
                "title": payload,
                "author": "Test Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_format_string_injection(self, client, auth_headers):
        format_strings = ["%s%s%s%s%s", "%x%x%x%x", "{0}{1}{2}"]
        
        for payload in format_strings:
            book_data = {
                "title": payload,
                "author": "Test Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_newline_injection(self, client, auth_headers):
        book_data = {
            "title": "Test\r\nBook",
            "author": "Test\nAuthor",
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_control_characters(self, client, auth_headers):
        control_chars = "\x01\x02\x03\x04\x05"
        book_data = {
            "title": f"Test{control_chars}Book",
            "author": "Test Author",
            "publication_year": 2020
        }
        response = client.post("/books", json=book_data, headers=auth_headers)
        assert response.status_code in [status.HTTP_201_CREATED, status.HTTP_422_UNPROCESSABLE_ENTITY]


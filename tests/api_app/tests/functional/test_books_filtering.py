import pytest
from fastapi import status


@pytest.mark.functional
class TestBooksFiltering:
    
    def test_partial_author_matching(self, client):
        response = client.get("/books?author=Orwell")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] == 2
        for book in data["books"]:
            assert "orwell" in book["author"].lower()
    
    def test_author_with_whitespace(self, client):
        response = client.get("/books?author=  George Orwell  ")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] == 2
    
    def test_empty_string_author_filter(self, client):
        response = client.get("/books?author=")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] == 0
    
    def test_special_characters_in_filter(self, client, auth_headers):
        special_book = {
            "title": "Test Book",
            "author": "O'Brien-Smith & Co.",
            "publication_year": 2020
        }
        create_response = client.post("/books", json=special_book, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        response = client.get("/books?author=O'Brien")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] >= 1
    
    def test_unicode_author_filter(self, client, auth_headers):
        unicode_book = {
            "title": "Test Book",
            "author": "José María García",
            "publication_year": 2020
        }
        create_response = client.post("/books", json=unicode_book, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        response = client.get("/books?author=José")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] >= 1
    
    def test_case_insensitive_search_lowercase(self, client):
        response = client.get("/books?author=george orwell")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 2
    
    def test_case_insensitive_search_uppercase(self, client):
        response = client.get("/books?author=GEORGE ORWELL")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 2
    
    def test_case_insensitive_search_mixed(self, client):
        response = client.get("/books?author=GeOrGe OrWeLl")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 2
    
    def test_combined_filters_no_match(self, client):
        response = client.get("/books?author=George Orwell&publication_year=2020")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] == 0
        assert data["filtered_by"] == {"author": "George Orwell", "publication_year": 2020}
    
    def test_combined_filters_with_match(self, client):
        response = client.get("/books?author=George Orwell&publication_year=1949")
        assert response.status_code == status.HTTP_200_OK
        
        data = response.json()
        assert data["total"] == 1
        assert data["books"][0]["title"] == "1984"
    
    def test_year_filter_boundary_1900(self, client, auth_headers):
        boundary_book = {
            "title": "Year 1900 Test",
            "author": "Test Author",
            "publication_year": 1900
        }
        create_response = client.post("/books", json=boundary_book, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        response = client.get("/books?publication_year=1900")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] >= 1
    
    def test_year_filter_current_year(self, client, auth_headers):
        boundary_book = {
            "title": "Current Year Test",
            "author": "Test Author",
            "publication_year": 2025
        }
        create_response = client.post("/books", json=boundary_book, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        response = client.get("/books?publication_year=2025")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] >= 1
    
    def test_nonexistent_author(self, client):
        response = client.get("/books?author=NonexistentAuthorXYZ123")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0
    
    def test_nonexistent_year(self, client):
        response = client.get("/books?publication_year=1905")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] == 0
    
    def test_filter_with_leading_trailing_spaces_year_string(self, client):
        response = client.get("/books?publication_year= 1949 ")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_multiple_spaces_in_author(self, client, auth_headers):
        spaced_book = {
            "title": "Spaced Test",
            "author": "John    Doe",
            "publication_year": 2020
        }
        create_response = client.post("/books", json=spaced_book, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        
        response = client.get("/books?author=John Doe")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["total"] >= 1


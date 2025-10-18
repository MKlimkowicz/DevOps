import pytest
from fastapi import status
from database import db


@pytest.mark.reliability
class TestErrorRecovery:
    
    def test_database_reset_recovery(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Before Reset",
            "author": "Author",
            "publication_year": 2020
        }, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
        book_id = create_response.json()["book"]["id"]
        
        db.__init__()
        
        response = client.get(f"/books/{book_id}")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        new_response = client.post("/books", json={
            "title": "After Reset",
            "author": "Author",
            "publication_year": 2020
        }, headers=auth_headers)
        assert new_response.status_code == status.HTTP_201_CREATED
    
    def test_malformed_request_recovery(self, client, auth_headers):
        malformed_data = '{"title": "Test", "author": }'
        
        response = client.post(
            "/books",
            data=malformed_data,
            headers={**auth_headers, "Content-Type": "application/json"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        valid_data = {
            "title": "Valid Book",
            "author": "Valid Author",
            "publication_year": 2020
        }
        recovery_response = client.post("/books", json=valid_data, headers=auth_headers)
        assert recovery_response.status_code == status.HTTP_201_CREATED
    
    def test_invalid_state_recovery(self, client, auth_headers):
        response = client.put("/books/99999", json={"title": "Updated"}, headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        create_response = client.post("/books", json={
            "title": "New Book",
            "author": "Author",
            "publication_year": 2020
        }, headers=auth_headers)
        assert create_response.status_code == status.HTTP_201_CREATED
    
    def test_partial_update_rollback(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Original",
            "author": "Author",
            "publication_year": 2020,
            "description": "Original description"
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        original_book = create_response.json()["book"]
        
        invalid_update = {
            "title": "Updated",
            "publication_year": 1800
        }
        update_response = client.put(f"/books/{book_id}", json=invalid_update, headers=auth_headers)
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        current_book = client.get(f"/books/{book_id}").json()
        assert current_book["title"] == original_book["title"]
        assert current_book["publication_year"] == original_book["publication_year"]
    
    def test_consistency_after_errors(self, client, auth_headers):
        initial_count = client.get("/books").json()["total"]
        
        for i in range(5):
            invalid_data = {
                "title": f"Invalid {i}",
                "author": "Author",
                "publication_year": 1800
            }
            response = client.post("/books", json=invalid_data, headers=auth_headers)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        current_count = client.get("/books").json()["total"]
        assert current_count == initial_count
    
    def test_recovery_after_concurrent_errors(self, client, auth_headers):
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def create_invalid_book(i):
            invalid_data = {
                "title": f"Invalid {i}",
                "author": "Author",
                "publication_year": 1800
            }
            return client.post("/books", json=invalid_data, headers=auth_headers)
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_invalid_book, i) for i in range(10)]
            results = [f.result() for f in as_completed(futures)]
        
        assert all(r.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY for r in results)
        
        valid_data = {
            "title": "Valid After Errors",
            "author": "Author",
            "publication_year": 2020
        }
        recovery_response = client.post("/books", json=valid_data, headers=auth_headers)
        assert recovery_response.status_code == status.HTTP_201_CREATED
    
    def test_delete_nonexistent_recovery(self, client, auth_headers):
        response = client.delete("/books/99999", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        get_response = client.get("/books")
        assert get_response.status_code == status.HTTP_200_OK
    
    def test_duplicate_detection_recovery(self, client, auth_headers):
        book_data = {
            "title": "Duplicate Test",
            "author": "Author",
            "publication_year": 2020
        }
        
        first_response = client.post("/books", json=book_data, headers=auth_headers)
        assert first_response.status_code == status.HTTP_201_CREATED
        
        duplicate_response = client.post("/books", json=book_data, headers=auth_headers)
        assert duplicate_response.status_code in [status.HTTP_409_CONFLICT, status.HTTP_201_CREATED]
        
        different_book = {
            "title": "Different Book",
            "author": "Different Author",
            "publication_year": 2020
        }
        recovery_response = client.post("/books", json=different_book, headers=auth_headers)
        assert recovery_response.status_code == status.HTTP_201_CREATED
    
    def test_empty_update_recovery(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Test",
            "author": "Author",
            "publication_year": 2020
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        empty_update = {}
        update_response = client.put(f"/books/{book_id}", json=empty_update, headers=auth_headers)
        assert update_response.status_code == status.HTTP_400_BAD_REQUEST
        
        valid_update = {"title": "Updated Title"}
        recovery_response = client.put(f"/books/{book_id}", json=valid_update, headers=auth_headers)
        assert recovery_response.status_code == status.HTTP_200_OK
    
    def test_invalid_id_recovery(self, client):
        invalid_ids = [-1, 0, "abc", 999999]
        
        for invalid_id in invalid_ids:
            response = client.get(f"/books/{invalid_id}")
            assert response.status_code in [
                status.HTTP_400_BAD_REQUEST,
                status.HTTP_404_NOT_FOUND,
                status.HTTP_422_UNPROCESSABLE_ENTITY
            ]
        
        valid_response = client.get("/books/1")
        assert valid_response.status_code == status.HTTP_200_OK


import pytest
from fastapi import status
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.functional
class TestDataIntegrity:
    
    def test_concurrent_create_operations(self, client, auth_headers):
        def create_book(i):
            book_data = {
                "title": f"Concurrent Book {i}",
                "author": f"Author {i}",
                "publication_year": 2020 + (i % 5)
            }
            return client.post("/books", json=book_data, headers=auth_headers)
        
        initial_count = client.get("/books").json()["total"]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(create_book, i) for i in range(5)]
            results = [f.result() for f in as_completed(futures)]
        
        successful_creates = sum(1 for r in results if r.status_code == 201)
        assert successful_creates == 5
        
        final_count = client.get("/books").json()["total"]
        assert final_count == initial_count + 5
    
    def test_concurrent_update_same_resource(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author",
            "publication_year": 2020
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        def update_book(i):
            update_data = {"description": f"Update {i}"}
            return client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(update_book, i) for i in range(3)]
            results = [f.result() for f in as_completed(futures)]
        
        successful_updates = sum(1 for r in results if r.status_code == 200)
        assert successful_updates == 3
        
        final_book = client.get(f"/books/{book_id}").json()
        assert final_book["description"] is not None
    
    def test_concurrent_read_during_write(self, client, auth_headers):
        def read_books():
            return client.get("/books")
        
        def create_book(i):
            return client.post("/books", json={
                "title": f"Book {i}",
                "author": "Author",
                "publication_year": 2020
            }, headers=auth_headers)
        
        with ThreadPoolExecutor(max_workers=6) as executor:
            read_futures = [executor.submit(read_books) for _ in range(3)]
            write_futures = [executor.submit(create_book, i) for i in range(3)]
            
            all_futures = read_futures + write_futures
            results = [f.result() for f in as_completed(all_futures)]
        
        assert all(r.status_code in [200, 201] for r in results)
    
    def test_idempotency_of_put_operation(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author",
            "publication_year": 2020
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        update_data = {
            "title": "Updated Title",
            "description": "Updated Description"
        }
        
        response1 = client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)
        book1 = response1.json()["book"]
        
        response2 = client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)
        book2 = response2.json()["book"]
        
        assert book1 == book2
        assert book1["title"] == "Updated Title"
        assert book1["description"] == "Updated Description"
    
    def test_id_sequence_after_bulk_operations(self, client, auth_headers):
        books_to_create = 20
        created_ids = []
        
        for i in range(books_to_create):
            response = client.post("/books", json={
                "title": f"Book {i}",
                "author": "Author",
                "publication_year": 2020
            }, headers=auth_headers)
            created_ids.append(response.json()["book"]["id"])
        
        assert len(set(created_ids)) == books_to_create
        assert all(isinstance(id, int) for id in created_ids)
        assert all(id > 0 for id in created_ids)
    
    def test_data_preservation_after_failed_update(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Original Title",
            "author": "Original Author",
            "publication_year": 2020,
            "description": "Original Description"
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        original_book = create_response.json()["book"]
        
        invalid_update = {
            "publication_year": 1800
        }
        update_response = client.put(f"/books/{book_id}", json=invalid_update, headers=auth_headers)
        assert update_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        current_book = client.get(f"/books/{book_id}").json()
        assert current_book["title"] == original_book["title"]
        assert current_book["author"] == original_book["author"]
        assert current_book["publication_year"] == original_book["publication_year"]
        assert current_book["description"] == original_book["description"]
    
    def test_consistency_after_partial_update(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Original Title",
            "author": "Original Author",
            "publication_year": 2020,
            "description": "Original Description"
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        partial_update = {"title": "Updated Title Only"}
        client.put(f"/books/{book_id}", json=partial_update, headers=auth_headers)
        
        updated_book = client.get(f"/books/{book_id}").json()
        assert updated_book["title"] == "Updated Title Only"
        assert updated_book["author"] == "Original Author"
        assert updated_book["publication_year"] == 2020
        assert updated_book["description"] == "Original Description"
    
    def test_delete_doesnt_affect_other_books(self, client, auth_headers):
        book1_response = client.post("/books", json={
            "title": "Book 1",
            "author": "Author 1",
            "publication_year": 2020
        }, headers=auth_headers)
        book1_id = book1_response.json()["book"]["id"]
        
        book2_response = client.post("/books", json={
            "title": "Book 2",
            "author": "Author 2",
            "publication_year": 2021
        }, headers=auth_headers)
        book2_id = book2_response.json()["book"]["id"]
        
        client.delete(f"/books/{book1_id}", headers=auth_headers)
        
        book1_get = client.get(f"/books/{book1_id}")
        assert book1_get.status_code == status.HTTP_404_NOT_FOUND
        
        book2_get = client.get(f"/books/{book2_id}")
        assert book2_get.status_code == status.HTTP_200_OK
        assert book2_get.json()["title"] == "Book 2"
    
    def test_race_condition_duplicate_detection(self, client, auth_headers):
        book_data = {
            "title": "Race Condition Test",
            "author": "Race Author",
            "publication_year": 2020
        }
        
        def create_same_book():
            return client.post("/books", json=book_data, headers=auth_headers)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_same_book) for _ in range(3)]
            results = [f.result() for f in as_completed(futures)]
        
        status_codes = [r.status_code for r in results]
        
        created_count = sum(1 for code in status_codes if code == 201)
        conflict_count = sum(1 for code in status_codes if code == 409)
        
        assert created_count + conflict_count == 3


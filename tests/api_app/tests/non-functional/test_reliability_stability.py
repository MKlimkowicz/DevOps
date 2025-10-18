import pytest
from fastapi import status
import random


@pytest.mark.reliability
@pytest.mark.slow
class TestStability:
    
    def test_repeated_get_operations(self, client):
        iterations = 1000
        failures = 0
        
        for i in range(iterations):
            response = client.get("/books")
            if response.status_code != status.HTTP_200_OK:
                failures += 1
        
        failure_rate = (failures / iterations) * 100
        assert failure_rate < 1.0
    
    def test_repeated_create_operations(self, client, auth_headers):
        iterations = 100
        failures = 0
        created_ids = []
        
        for i in range(iterations):
            book_data = {
                "title": f"Stability Test {i}",
                "author": f"Author {i}",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            
            if response.status_code == status.HTTP_201_CREATED:
                created_ids.append(response.json()["book"]["id"])
            else:
                failures += 1
        
        failure_rate = (failures / iterations) * 100
        assert failure_rate < 5.0
        assert len(set(created_ids)) == len(created_ids)
    
    def test_repeated_update_operations(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Stability Update Test",
            "author": "Author",
            "publication_year": 2020
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        iterations = 100
        failures = 0
        
        for i in range(iterations):
            update_data = {"description": f"Update iteration {i}"}
            response = client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)
            
            if response.status_code != status.HTTP_200_OK:
                failures += 1
        
        failure_rate = (failures / iterations) * 100
        assert failure_rate < 1.0
        
        final_book = client.get(f"/books/{book_id}").json()
        assert "Update iteration" in final_book["description"]
    
    def test_repeated_delete_create_cycle(self, client, auth_headers):
        iterations = 50
        failures = 0
        
        for i in range(iterations):
            create_response = client.post("/books", json={
                "title": f"Cycle Test {i}",
                "author": "Author",
                "publication_year": 2020
            }, headers=auth_headers)
            
            if create_response.status_code != status.HTTP_201_CREATED:
                failures += 1
                continue
            
            book_id = create_response.json()["book"]["id"]
            
            delete_response = client.delete(f"/books/{book_id}", headers=auth_headers)
            if delete_response.status_code not in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]:
                failures += 1
        
        failure_rate = (failures / (iterations * 2)) * 100
        assert failure_rate < 5.0
    
    def test_random_operation_sequence(self, client, auth_headers):
        iterations = 200
        operations = ["get_all", "get_one", "create", "update", "filter"]
        failures = 0
        created_ids = []
        
        for i in range(iterations):
            operation = random.choice(operations)
            
            try:
                if operation == "get_all":
                    response = client.get("/books")
                    assert response.status_code == status.HTTP_200_OK
                
                elif operation == "get_one":
                    book_id = random.choice(created_ids) if created_ids else 1
                    response = client.get(f"/books/{book_id}")
                    assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
                
                elif operation == "create":
                    book_data = {
                        "title": f"Random {i}",
                        "author": f"Author {i}",
                        "publication_year": random.randint(1900, 2025)
                    }
                    response = client.post("/books", json=book_data, headers=auth_headers)
                    if response.status_code == status.HTTP_201_CREATED:
                        created_ids.append(response.json()["book"]["id"])
                
                elif operation == "update":
                    if created_ids:
                        book_id = random.choice(created_ids)
                        update_data = {"description": f"Random update {i}"}
                        response = client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)
                        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]
                
                elif operation == "filter":
                    authors = ["Orwell", "Tolkien", "Flynn"]
                    author = random.choice(authors)
                    response = client.get(f"/books?author={author}")
                    assert response.status_code == status.HTTP_200_OK
            
            except AssertionError:
                failures += 1
        
        failure_rate = (failures / iterations) * 100
        assert failure_rate < 5.0
    
    def test_alternating_read_write_pattern(self, client, auth_headers):
        iterations = 100
        failures = 0
        
        for i in range(iterations):
            book_data = {
                "title": f"Alternating {i}",
                "author": "Author",
                "publication_year": 2020
            }
            write_response = client.post("/books", json=book_data, headers=auth_headers)
            
            if write_response.status_code != status.HTTP_201_CREATED:
                failures += 1
                continue
            
            book_id = write_response.json()["book"]["id"]
            
            read_response = client.get(f"/books/{book_id}")
            if read_response.status_code != status.HTTP_200_OK:
                failures += 1
        
        failure_rate = (failures / (iterations * 2)) * 100
        assert failure_rate < 1.0
    
    def test_data_consistency_verification(self, client, auth_headers):
        test_books = []
        
        for i in range(20):
            book_data = {
                "title": f"Consistency Test {i}",
                "author": f"Author {i}",
                "publication_year": 2020 + i
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            if response.status_code == status.HTTP_201_CREATED:
                test_books.append(response.json()["book"])
        
        for book in test_books:
            response = client.get(f"/books/{book['id']}")
            assert response.status_code == status.HTTP_200_OK
            
            retrieved_book = response.json()
            assert retrieved_book["title"] == book["title"]
            assert retrieved_book["author"] == book["author"]
            assert retrieved_book["publication_year"] == book["publication_year"]
    
    def test_id_sequence_stability(self, client, auth_headers):
        initial_response = client.get("/books")
        initial_count = initial_response.json()["total"]
        
        new_books_count = 50
        created_ids = []
        
        for i in range(new_books_count):
            book_data = {
                "title": f"ID Sequence {i}",
                "author": "Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            if response.status_code == status.HTTP_201_CREATED:
                created_ids.append(response.json()["book"]["id"])
        
        assert len(created_ids) == new_books_count
        assert len(set(created_ids)) == new_books_count
        assert all(isinstance(id, int) for id in created_ids)
        assert all(id > 0 for id in created_ids)
    
    def test_filter_consistency(self, client, auth_headers):
        test_author = "Consistency Author"
        test_year = 2023
        books_created = 10
        
        for i in range(books_created):
            book_data = {
                "title": f"Filter Consistency {i}",
                "author": test_author,
                "publication_year": test_year
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED
        
        for _ in range(10):
            author_response = client.get(f"/books?author={test_author}")
            assert author_response.status_code == status.HTTP_200_OK
            assert author_response.json()["total"] >= books_created
            
            year_response = client.get(f"/books?publication_year={test_year}")
            assert year_response.status_code == status.HTTP_200_OK
            assert year_response.json()["total"] >= books_created
    
    def test_long_running_stability(self, client, auth_headers):
        duration_iterations = 100
        mixed_operations = 0
        failures = 0
        
        for i in range(duration_iterations):
            operations_in_iteration = 5
            
            for j in range(operations_in_iteration):
                mixed_operations += 1
                
                if j % 3 == 0:
                    response = client.get("/books")
                elif j % 3 == 1:
                    book_data = {
                        "title": f"Long Run {i}-{j}",
                        "author": "Author",
                        "publication_year": 2020
                    }
                    response = client.post("/books", json=book_data, headers=auth_headers)
                else:
                    response = client.get("/books?author=Orwell")
                
                if response.status_code not in [200, 201]:
                    failures += 1
        
        failure_rate = (failures / mixed_operations) * 100
        assert failure_rate < 2.0


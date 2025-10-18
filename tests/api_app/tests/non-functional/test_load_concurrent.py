import pytest
from fastapi import status
from utils.performance import LoadGenerator
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.load
@pytest.mark.slow
class TestConcurrentLoad:
    
    def test_10_concurrent_users_baseline(self, client, load_test_config):
        concurrent_users = load_test_config["concurrent_users_baseline"]
        
        def get_books(iteration):
            return client.get("/books")
        
        generator = LoadGenerator(client)
        results = generator.execute_concurrent(get_books, concurrent_users)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] == concurrent_users
        assert stats["success_rate"] == 100.0
        assert stats["mean_duration_ms"] < 200
    
    def test_50_concurrent_users_normal_load(self, client, load_test_config):
        concurrent_users = load_test_config["concurrent_users_normal"]
        
        def get_books(iteration):
            return client.get("/books")
        
        generator = LoadGenerator(client)
        results = generator.execute_concurrent(get_books, concurrent_users)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] >= concurrent_users * 0.95
        assert stats["success_rate"] >= 95.0
        assert stats["mean_duration_ms"] < 500
    
    def test_100_concurrent_users_high_load(self, client, load_test_config):
        concurrent_users = load_test_config["concurrent_users_high"]
        
        def get_books(iteration):
            return client.get("/books")
        
        generator = LoadGenerator(client)
        results = generator.execute_concurrent(get_books, concurrent_users)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] >= concurrent_users * 0.90
        assert stats["success_rate"] >= 90.0
        assert stats["p95_duration_ms"] < 1000
    
    def test_concurrent_read_operations(self, client):
        operations = [
            lambda i: client.get("/books"),
            lambda i: client.get(f"/books/{(i % 10) + 1}"),
            lambda i: client.get(f"/books?author=Orwell"),
        ]
        
        def execute_random_read(iteration):
            op = operations[iteration % len(operations)]
            return op(iteration)
        
        generator = LoadGenerator(client)
        results = generator.execute_concurrent(execute_random_read, 30)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] == 30
        assert stats["success_rate"] == 100.0
    
    def test_concurrent_write_operations(self, client, auth_headers):
        def create_book(iteration):
            book_data = {
                "title": f"Concurrent Book {iteration}",
                "author": f"Author {iteration}",
                "publication_year": 2020 + (iteration % 5)
            }
            return client.post("/books", json=book_data, headers=auth_headers)
        
        generator = LoadGenerator(client, auth_headers)
        results = generator.execute_concurrent(create_book, 20)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] == 20
        assert stats["success_rate"] == 100.0
    
    def test_concurrent_same_resource_updates(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "Test Book",
            "author": "Test Author",
            "publication_year": 2020
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        def update_book(iteration):
            update_data = {"description": f"Update {iteration}"}
            return client.put(f"/books/{book_id}", json=update_data, headers=auth_headers)
        
        generator = LoadGenerator(client, auth_headers)
        results = generator.execute_concurrent(update_book, 10)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] == 10
        assert stats["success_rate"] == 100.0
    
    def test_mixed_read_write_concurrent(self, client, auth_headers):
        def mixed_operation(iteration):
            if iteration % 3 == 0:
                book_data = {
                    "title": f"Mixed Book {iteration}",
                    "author": "Author",
                    "publication_year": 2020
                }
                return client.post("/books", json=book_data, headers=auth_headers)
            elif iteration % 3 == 1:
                return client.get("/books")
            else:
                return client.get(f"/books/{(iteration % 10) + 1}")
        
        generator = LoadGenerator(client, auth_headers)
        results = generator.execute_concurrent(mixed_operation, 30)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] >= 27
        assert stats["success_rate"] >= 90.0
    
    def test_concurrent_filter_operations(self, client):
        filters = [
            "?author=Orwell",
            "?publication_year=1949",
            "?author=Tolkien",
            "?publication_year=1954"
        ]
        
        def filter_books(iteration):
            filter_param = filters[iteration % len(filters)]
            return client.get(f"/books{filter_param}")
        
        generator = LoadGenerator(client)
        results = generator.execute_concurrent(filter_books, 40)
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] == 40
        assert stats["success_rate"] == 100.0
    
    def test_concurrent_delete_operations(self, client, auth_headers):
        book_ids = []
        for i in range(15):
            response = client.post("/books", json={
                "title": f"To Delete {i}",
                "author": "Author",
                "publication_year": 2020
            }, headers=auth_headers)
            book_ids.append(response.json()["book"]["id"])
        
        def delete_book(iteration):
            if iteration < len(book_ids):
                return client.delete(f"/books/{book_ids[iteration]}", headers=auth_headers)
            return None
        
        generator = LoadGenerator(client, auth_headers)
        results = generator.execute_concurrent(delete_book, len(book_ids))
        stats = generator.get_statistics()
        
        assert stats["successful_requests"] == len(book_ids)
    
    def test_rate_limiter_behavior_under_load(self, client):
        def get_books(iteration):
            return client.get("/books")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(get_books, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]
        
        success_count = sum(1 for r in results if r.status_code == 200)
        rate_limited_count = sum(1 for r in results if r.status_code == 429)
        
        assert success_count + rate_limited_count == 20


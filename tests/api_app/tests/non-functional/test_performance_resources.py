import pytest
from fastapi import status
from utils.performance import ResourceMonitor
from database import db
import time


@pytest.mark.performance
@pytest.mark.slow
class TestResourceUsage:
    
    def test_memory_consumption_baseline(self, client):
        monitor = ResourceMonitor()
        monitor.start()
        
        for _ in range(10):
            response = client.get("/books")
            assert response.status_code == status.HTTP_200_OK
            monitor.measure()
            time.sleep(0.1)
        
        stats = monitor.get_stats()
        assert stats["memory_increase_mb"] < 50
    
    def test_memory_with_bulk_operations(self, client, auth_headers):
        monitor = ResourceMonitor()
        monitor.start()
        
        for i in range(50):
            book_data = {
                "title": f"Memory Test {i}",
                "author": "Test Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED
            
            if i % 10 == 0:
                monitor.measure()
        
        stats = monitor.get_stats()
        assert stats["memory_increase_mb"] < 100
    
    def test_memory_leak_detection(self, client):
        monitor = ResourceMonitor()
        monitor.start()
        
        initial_measurement = monitor.measure()
        
        for _ in range(100):
            response = client.get("/books")
            assert response.status_code == status.HTTP_200_OK
        
        final_measurement = monitor.measure()
        
        memory_growth = final_measurement["memory_mb"] - initial_measurement["memory_mb"]
        assert memory_growth < 20
    
    def test_database_size_tracking(self, client, auth_headers):
        initial_stats = db.get_stats()
        initial_size = initial_stats["memory_bytes"]
        
        for i in range(20):
            book_data = {
                "title": f"DB Size Test {i}",
                "author": "Test Author",
                "publication_year": 2020,
                "description": "Test description" * 10
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            assert response.status_code == status.HTTP_201_CREATED
        
        final_stats = db.get_stats()
        final_size = final_stats["memory_bytes"]
        
        size_increase = final_size - initial_size
        assert size_increase > 0
        assert final_stats["total_books"] == initial_stats["total_books"] + 20
    
    def test_response_payload_size(self, client):
        response = client.get("/books")
        assert response.status_code == status.HTTP_200_OK
        
        content_length = len(response.content)
        assert content_length < 50000
    
    def test_response_payload_size_large_dataset(self, client, db_with_bulk_data):
        response = client.get("/books")
        assert response.status_code == status.HTTP_200_OK
        
        content_length = len(response.content)
        assert content_length < 500000
    
    def test_single_book_payload_size(self, client):
        response = client.get("/books/1")
        assert response.status_code == status.HTTP_200_OK
        
        content_length = len(response.content)
        assert content_length < 1000
    
    def test_cpu_usage_normal_load(self, client):
        monitor = ResourceMonitor()
        monitor.start()
        
        for _ in range(20):
            response = client.get("/books")
            assert response.status_code == status.HTTP_200_OK
            monitor.measure()
            time.sleep(0.05)
        
        stats = monitor.get_stats()
        assert stats["avg_cpu_percent"] < 80
    
    def test_resource_cleanup_after_operations(self, client, auth_headers):
        monitor = ResourceMonitor()
        monitor.start()
        
        baseline = monitor.measure()
        
        created_ids = []
        for i in range(10):
            book_data = {
                "title": f"Cleanup Test {i}",
                "author": "Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            created_ids.append(response.json()["book"]["id"])
        
        for book_id in created_ids:
            response = client.delete(f"/books/{book_id}", headers=auth_headers)
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        
        final = monitor.measure()
        
        memory_diff = final["memory_mb"] - baseline["memory_mb"]
        assert abs(memory_diff) < 10
    
    def test_concurrent_requests_resource_usage(self, client):
        from concurrent.futures import ThreadPoolExecutor
        
        monitor = ResourceMonitor()
        monitor.start()
        
        def make_request():
            return client.get("/books")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
        
        monitor.measure()
        stats = monitor.get_stats()
        
        assert all(r.status_code == status.HTTP_200_OK for r in results)
        assert stats["memory_increase_mb"] < 50


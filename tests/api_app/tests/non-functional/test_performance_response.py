import pytest
from fastapi import status
from utils.performance import ResponseTimer, assert_performance
from database import db


@pytest.mark.performance
class TestResponseTime:
    
    def test_get_all_books_baseline(self, client):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 100, "GET /books with 10 books")
    
    def test_get_single_book(self, client):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books/1")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 50, "GET /books/{id}")
    
    def test_post_book_creation(self, client, auth_headers):
        book_data = {
            "title": "Performance Test Book",
            "author": "Performance Author",
            "publication_year": 2020
        }
        
        timer = ResponseTimer()
        timer.start()
        response = client.post("/books", json=book_data, headers=auth_headers)
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_201_CREATED
        assert_performance(duration, 200, "POST /books")
    
    def test_put_book_update(self, client, auth_headers):
        update_data = {"title": "Updated Title"}
        
        timer = ResponseTimer()
        timer.start()
        response = client.put("/books/1", json=update_data, headers=auth_headers)
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 150, "PUT /books/{id}")
    
    def test_delete_book(self, client, auth_headers):
        create_response = client.post("/books", json={
            "title": "To Delete",
            "author": "Author",
            "publication_year": 2020
        }, headers=auth_headers)
        book_id = create_response.json()["book"]["id"]
        
        timer = ResponseTimer()
        timer.start()
        response = client.delete(f"/books/{book_id}", headers=auth_headers)
        duration = timer.stop()
        
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
        assert_performance(duration, 100, "DELETE /books/{id}")
    
    def test_filter_by_author(self, client):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books?author=Orwell")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 150, "GET /books?author=")
    
    def test_filter_by_year(self, client):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books?publication_year=1949")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 150, "GET /books?publication_year=")
    
    def test_combined_filters(self, client):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books?author=Orwell&publication_year=1949")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 150, "GET /books with combined filters")


@pytest.mark.performance
@pytest.mark.slow
class TestResponseTimeWithLargeDataset:
    
    def test_get_all_books_100_records(self, client, db_with_bulk_data):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 110
        assert_performance(duration, 200, "GET /books with 100 books")
    
    def test_get_all_books_1000_records(self, client, db_with_large_dataset):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] == 1010
        assert_performance(duration, 500, "GET /books with 1000 books")
    
    def test_filter_performance_large_dataset(self, client, db_with_large_dataset):
        timer = ResponseTimer()
        timer.start()
        response = client.get("/books?publication_year=2020")
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 300, "Filter with 1000 books")
    
    def test_create_performance_with_large_dataset(self, client, auth_headers, db_with_bulk_data):
        book_data = {
            "title": "New Book",
            "author": "New Author",
            "publication_year": 2020
        }
        
        timer = ResponseTimer()
        timer.start()
        response = client.post("/books", json=book_data, headers=auth_headers)
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_201_CREATED
        assert_performance(duration, 250, "POST with large dataset")
    
    def test_update_performance_large_dataset(self, client, auth_headers, db_with_bulk_data):
        timer = ResponseTimer()
        timer.start()
        response = client.put("/books/50", json={"title": "Updated"}, headers=auth_headers)
        duration = timer.stop()
        
        assert response.status_code == status.HTTP_200_OK
        assert_performance(duration, 200, "PUT with large dataset")
    
    def test_sequential_requests_performance(self, client):
        durations = []
        
        for i in range(10):
            timer = ResponseTimer()
            timer.start()
            response = client.get("/books")
            duration = timer.stop()
            durations.append(duration)
            assert response.status_code == status.HTTP_200_OK
        
        avg_duration = sum(durations) / len(durations)
        assert_performance(avg_duration, 100, "Average of 10 sequential requests")
    
    def test_mixed_operations_performance(self, client, auth_headers):
        operations = [
            ("GET", "/books", None),
            ("GET", "/books/1", None),
            ("POST", "/books", {"title": "Test", "author": "Author", "publication_year": 2020}),
            ("PUT", "/books/2", {"title": "Updated"}),
            ("GET", "/books?author=Orwell", None)
        ]
        
        total_duration = 0
        for method, endpoint, data in operations:
            timer = ResponseTimer()
            timer.start()
            
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json=data, headers=auth_headers)
            elif method == "PUT":
                response = client.put(endpoint, json=data, headers=auth_headers)
            
            duration = timer.stop()
            total_duration += duration
            assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        
        avg_duration = total_duration / len(operations)
        assert_performance(avg_duration, 150, "Average mixed operations")


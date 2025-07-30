import pytest
import time
import asyncio
from fastapi import status
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestAdvancedFeatures:
    """Test advanced features and edge cases for the books API."""
    
    def test_add_duplicate_book_check(self, client, auth_headers):
        """
        Scenario 19: Add Duplicate Book Check
        Attempt to POST a book with identical title, author, and year as an 
        existing one and verify the API behavior for duplicates.
        """
        duplicate_book = {
            "title": "To Kill a Mockingbird",
            "author": "Harper Lee",
            "publication_year": 1960,
            "description": "A duplicate attempt"
        }
        
        response = client.post("/books", json=duplicate_book, headers=auth_headers)
        
        if response.status_code == status.HTTP_201_CREATED:
            data = response.json()
            assert data["book"]["title"] == duplicate_book["title"]
            assert data["book"]["author"] == duplicate_book["author"]
            assert data["book"]["publication_year"] == duplicate_book["publication_year"]
            assert data["book"]["id"] != 1
        elif response.status_code == status.HTTP_409_CONFLICT:
            data = response.json()
            assert "detail" in data
            assert "duplicate" in data["detail"].lower() or "already exists" in data["detail"].lower()
        else:
            pytest.fail(f"Unexpected response code {response.status_code} for duplicate book")
    
    def test_large_list_pagination_simulation(self, client):
        """
        Scenario 20: Large List Pagination Simulation
        Test retrieving books with query parameters that could simulate pagination
        and verify proper handling of large datasets.
        """
        response = client.get("/books")
        assert response.status_code == status.HTTP_200_OK
        
        all_books = response.json()["books"]
        
        assert len(all_books) == 39
        
        books_1950s = [book for book in all_books if 1950 <= book["publication_year"] < 1960]
        
        assert len(books_1950s) > 0
        
        for book in books_1950s:
            assert 1950 <= book["publication_year"] < 1960
    
    def test_rate_limiting_basic(self, client):
        """
        Scenario 21: Rate Limiting Test
        Send multiple rapid GET requests to /books and monitor response times
        and potential rate limiting behavior.
        """
        responses = []
        start_time = time.time()
        
        for i in range(10):
            response = client.get("/books")
            responses.append((response.status_code, response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0))
            time.sleep(0.1)
        
        end_time = time.time()
        
        success_count = sum(1 for status_code, _ in responses if status_code == 200)
        rate_limited_count = sum(1 for status_code, _ in responses if status_code == 429)
        
        assert success_count + rate_limited_count == len(responses)
        
        if rate_limited_count > 0:
            assert rate_limited_count >= 1
            
        total_time = end_time - start_time
        assert total_time < 30
    
    def test_case_sensitivity_in_filters(self, client):
        """
        Scenario 24: Case Sensitivity in Filters
        Send GET /books with author="george orwell" (lowercase) and verify 
        if it matches case-insensitively or requires exact case.
        """
        response_lower = client.get("/books?author=george orwell")
        assert response_lower.status_code == status.HTTP_200_OK
        
        response_exact = client.get("/books?author=George Orwell")
        assert response_exact.status_code == status.HTTP_200_OK
        
        response_mixed = client.get("/books?author=GEORGE ORWELL")
        assert response_mixed.status_code == status.HTTP_200_OK
        
        lower_data = response_lower.json()
        exact_data = response_exact.json()
        mixed_data = response_mixed.json()
        
        assert exact_data["total"] == 2
        
        if lower_data["total"] == exact_data["total"]:
            assert lower_data["total"] == 2
            assert mixed_data["total"] == 2
        else:
            assert lower_data["total"] == 0
    
    def test_concurrent_operations_simulation(self, client, auth_headers):
        """
        Scenario 26: Concurrent Operations
        Simulate adding a book while simultaneously reading books and verify 
        data consistency without conflicts.
        """
        test_books = [
            {
                "title": f"Concurrent Book {i}",
                "author": f"Concurrent Author {i}",
                "publication_year": 2020 + i,
                "description": f"Description for concurrent book {i}"
            }
            for i in range(3)
        ]
        
        def add_book(book_data):
            """Helper function to add a book"""
            response = client.post("/books", json=book_data, headers=auth_headers)
            return response.status_code, response.json() if response.status_code == 201 else None
        
        def read_books():
            """Helper function to read all books"""
            response = client.get("/books")
            return response.status_code, response.json()
        
        initial_response = client.get("/books")
        initial_count = initial_response.json()["total"]
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for book_data in test_books:
                future = executor.submit(add_book, book_data)
                futures.append(('add', future))
            
            for _ in range(2):
                future = executor.submit(read_books)
                futures.append(('read', future))
            
            results = []
            for operation_type, future in futures:
                try:
                    result = future.result(timeout=10)
                    results.append((operation_type, result))
                except Exception as e:
                    pytest.fail(f"Concurrent operation failed: {e}")
        
        add_results = [result for op_type, result in results if op_type == 'add']
        successful_adds = sum(1 for status_code, _ in add_results if status_code == 201)
        assert successful_adds == len(test_books)
        
        read_results = [result for op_type, result in results if op_type == 'read']
        successful_reads = sum(1 for status_code, _ in read_results if status_code == 200)
        assert successful_reads == 2
        
        final_response = client.get("/books")
        final_count = final_response.json()["total"]
        
        assert final_count == initial_count + successful_adds
    
    def test_input_validation_for_strings(self, client, auth_headers):
        """
        Scenario 23: Input Validation for Strings
        Send a POST with an excessively long title and check for validation errors.
        """
        test_cases = [
            {
                "name": "extremely_long_title",
                "data": {
                    "title": "A" * 500,
                    "author": "Test Author",
                    "publication_year": 2020
                },
                "expected_field": "title"
            },
            {
                "name": "extremely_long_author",
                "data": {
                    "title": "Test Title",
                    "author": "B" * 300,
                    "publication_year": 2020
                },
                "expected_field": "author"
            },
            {
                "name": "extremely_long_description",
                "data": {
                    "title": "Test Title",
                    "author": "Test Author",
                    "publication_year": 2020,
                    "description": "C" * 2000
                },
                "expected_field": "description"
            }
        ]
        
        for test_case in test_cases:
            response = client.post("/books", json=test_case["data"], headers=auth_headers)
            
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
            data = response.json()
            
            assert "detail" in data
            error_details = str(data["detail"])
            assert test_case["expected_field"] in error_details
    
    def test_empty_database_state_simulation(self, client, auth_headers):
        """
        Scenario 25: Empty Database State Simulation
        Since we can't actually empty the database due to the reset fixture,
        we'll test filtering that returns no results to simulate empty state.
        """
        response = client.get("/books?author=NonExistentAuthor&publication_year=1800")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["total"] == 0
        assert len(data["books"]) == 0
        assert data["filtered_by"] == {"author": "NonExistentAuthor", "publication_year": 1800}
        
        assert "books" in data
        assert "total" in data
        assert "filtered_by" in data
        assert isinstance(data["books"], list)
        assert isinstance(data["total"], int)
    
    def test_boundary_value_publication_years(self, client, auth_headers):
        """
        Test boundary values for publication years (1900 and current year).
        """
        current_year = 2025
        
        min_year_book = {
            "title": "Boundary Test 1900",
            "author": "Boundary Author",
            "publication_year": 1900,
            "description": "Testing minimum year boundary"
        }
        
        response = client.post("/books", json=min_year_book, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        
        max_year_book = {
            "title": "Boundary Test Current",
            "author": "Boundary Author",
            "publication_year": current_year,
            "description": "Testing maximum year boundary"
        }
        
        response = client.post("/books", json=max_year_book, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        
        below_min_book = {
            "title": "Below Min Year",
            "author": "Boundary Author",
            "publication_year": 1899,
            "description": "Testing below minimum year"
        }
        
        response = client.post("/books", json=below_min_book, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        above_max_book = {
            "title": "Above Max Year",
            "author": "Boundary Author", 
            "publication_year": current_year + 1,
            "description": "Testing above maximum year"
        }
        
        response = client.post("/books", json=above_max_book, headers=auth_headers)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSpecialCharacters:
    """Test handling of special characters and edge cases in string fields."""
    
    def test_special_characters_in_title(self, client, auth_headers):
        """Test books with special characters in title."""
        special_title_book = {
            "title": "Special: Title! With @#$%^&*()_+ Characters",
            "author": "Special Author",
            "publication_year": 2020,
            "description": "Testing special characters in title"
        }
        
        response = client.post("/books", json=special_title_book, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        
        book_id = response.json()["book"]["id"]
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == status.HTTP_200_OK
        assert get_response.json()["title"] == special_title_book["title"]
    
    def test_unicode_characters_in_fields(self, client, auth_headers):
        """Test books with Unicode characters in various fields."""
        unicode_book = {
            "title": "Título con acentos y ñoños",
            "author": "Автор на кириллице",
            "publication_year": 2020,
            "description": "Description with émojis 📚🎉 and spëcial chars"
        }
        
        response = client.post("/books", json=unicode_book, headers=auth_headers)
        assert response.status_code == status.HTTP_201_CREATED
        
        book_id = response.json()["book"]["id"]
        get_response = client.get(f"/books/{book_id}")
        assert get_response.status_code == status.HTTP_200_OK
        
        book = get_response.json()
        assert book["title"] == unicode_book["title"]
        assert book["author"] == unicode_book["author"]
        assert book["description"] == unicode_book["description"] 
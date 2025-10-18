import pytest
from fastapi import status
from concurrent.futures import ThreadPoolExecutor, as_completed
import time


@pytest.mark.load
@pytest.mark.slow
@pytest.mark.timeout(300)
class TestStressLoad:
    
    def test_find_breaking_point(self, client):
        concurrent_levels = [10, 25, 50, 75, 100]
        breaking_point = None
        
        for level in concurrent_levels:
            def make_request(i):
                return client.get("/books")
            
            with ThreadPoolExecutor(max_workers=level) as executor:
                futures = [executor.submit(make_request, i) for i in range(level)]
                results = [f.result() for f in as_completed(futures)]
            
            success_count = sum(1 for r in results if r.status_code == 200)
            success_rate = (success_count / level) * 100
            
            if success_rate < 90:
                breaking_point = level
                break
        
        assert breaking_point is None or breaking_point > 50
    
    def test_recovery_after_overload(self, client):
        overload_requests = 200
        
        with ThreadPoolExecutor(max_workers=overload_requests) as executor:
            futures = [executor.submit(lambda: client.get("/books")) for _ in range(overload_requests)]
            overload_results = [f.result() for f in as_completed(futures)]
        
        time.sleep(2)
        
        recovery_requests = 10
        recovery_results = []
        for _ in range(recovery_requests):
            response = client.get("/books")
            recovery_results.append(response)
            time.sleep(0.1)
        
        recovery_success = sum(1 for r in recovery_results if r.status_code == 200)
        recovery_rate = (recovery_success / recovery_requests) * 100
        
        assert recovery_rate >= 90.0
    
    def test_graceful_degradation(self, client):
        stress_levels = [50, 100, 150]
        response_times = []
        
        for level in stress_levels:
            durations = []
            
            with ThreadPoolExecutor(max_workers=level) as executor:
                def timed_request(i):
                    start = time.time()
                    response = client.get("/books")
                    duration = (time.time() - start) * 1000
                    return response.status_code, duration
                
                futures = [executor.submit(timed_request, i) for i in range(level)]
                results = [f.result() for f in as_completed(futures)]
            
            successful_durations = [d for status, d in results if status == 200]
            if successful_durations:
                avg_duration = sum(successful_durations) / len(successful_durations)
                response_times.append(avg_duration)
        
        if len(response_times) >= 2:
            degradation = (response_times[-1] - response_times[0]) / response_times[0] * 100
            assert degradation < 200
    
    def test_rate_limiter_at_limits(self, client):
        rapid_requests = 150
        
        with ThreadPoolExecutor(max_workers=rapid_requests) as executor:
            futures = [executor.submit(lambda: client.get("/books")) for _ in range(rapid_requests)]
            results = [f.result() for f in as_completed(futures)]
        
        success_count = sum(1 for r in results if r.status_code == 200)
        rate_limited_count = sum(1 for r in results if r.status_code == 429)
        
        assert success_count + rate_limited_count == rapid_requests
        assert rate_limited_count > 0
    
    def test_error_rate_monitoring(self, client, auth_headers):
        stress_operations = 100
        errors = []
        
        with ThreadPoolExecutor(max_workers=50) as executor:
            def stress_operation(i):
                try:
                    if i % 2 == 0:
                        response = client.get("/books")
                    else:
                        book_data = {
                            "title": f"Stress Book {i}",
                            "author": "Author",
                            "publication_year": 2020
                        }
                        response = client.post("/books", json=book_data, headers=auth_headers)
                    return response.status_code
                except Exception as e:
                    errors.append(str(e))
                    return None
            
            futures = [executor.submit(stress_operation, i) for i in range(stress_operations)]
            results = [f.result() for f in as_completed(futures)]
        
        successful = sum(1 for r in results if r in [200, 201])
        error_rate = (len(errors) / stress_operations) * 100
        
        assert error_rate < 10.0
        assert successful >= stress_operations * 0.80
    
    def test_database_stress(self, client, auth_headers):
        create_count = 100
        created_ids = []
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            def create_book(i):
                book_data = {
                    "title": f"DB Stress {i}",
                    "author": f"Author {i}",
                    "publication_year": 2020
                }
                response = client.post("/books", json=book_data, headers=auth_headers)
                if response.status_code == 201:
                    return response.json()["book"]["id"]
                return None
            
            futures = [executor.submit(create_book, i) for i in range(create_count)]
            created_ids = [f.result() for f in as_completed(futures) if f.result()]
        
        assert len(created_ids) >= create_count * 0.90
        assert len(set(created_ids)) == len(created_ids)
    
    def test_memory_under_stress(self, client):
        from utils.performance import ResourceMonitor
        
        monitor = ResourceMonitor()
        monitor.start()
        
        baseline = monitor.measure()
        
        stress_requests = 200
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(lambda: client.get("/books")) for _ in range(stress_requests)]
            results = [f.result() for f in as_completed(futures)]
        
        peak = monitor.measure()
        
        memory_increase = peak["memory_mb"] - baseline["memory_mb"]
        assert memory_increase < 100
    
    def test_response_consistency_under_stress(self, client):
        stress_requests = 100
        
        with ThreadPoolExecutor(max_workers=25) as executor:
            futures = [executor.submit(lambda: client.get("/books/1")) for _ in range(stress_requests)]
            results = [f.result() for f in as_completed(futures)]
        
        successful_results = [r for r in results if r.status_code == 200]
        
        if len(successful_results) > 1:
            first_content = successful_results[0].json()
            for result in successful_results[1:]:
                assert result.json() == first_content


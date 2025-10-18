import pytest
from fastapi import status
import time
from utils.performance import ResponseTimer


@pytest.mark.load
@pytest.mark.slow
@pytest.mark.timeout(600)
class TestSustainedLoad:
    
    def test_constant_load_1_minute(self, client):
        duration_seconds = 60
        requests_per_second = 5
        
        start_time = time.time()
        request_count = 0
        successful_requests = 0
        durations = []
        
        while time.time() - start_time < duration_seconds:
            timer = ResponseTimer()
            timer.start()
            response = client.get("/books")
            duration = timer.stop()
            
            request_count += 1
            if response.status_code == 200:
                successful_requests += 1
            durations.append(duration)
            
            time.sleep(1 / requests_per_second)
        
        success_rate = (successful_requests / request_count) * 100
        avg_duration = sum(durations) / len(durations)
        
        assert success_rate >= 95.0
        assert avg_duration < 200
        assert request_count >= duration_seconds * requests_per_second * 0.9
    
    def test_gradual_ramp_up(self, client):
        stages = [
            {"duration": 10, "requests_per_second": 1},
            {"duration": 10, "requests_per_second": 3},
            {"duration": 10, "requests_per_second": 5}
        ]
        
        total_requests = 0
        successful_requests = 0
        
        for stage in stages:
            start_time = time.time()
            
            while time.time() - start_time < stage["duration"]:
                response = client.get("/books")
                total_requests += 1
                if response.status_code == 200:
                    successful_requests += 1
                
                time.sleep(1 / stage["requests_per_second"])
        
        success_rate = (successful_requests / total_requests) * 100
        assert success_rate >= 90.0
    
    def test_spike_testing(self, client):
        normal_load_duration = 10
        spike_duration = 5
        normal_rps = 2
        spike_rps = 10
        
        requests_normal = 0
        requests_spike = 0
        successful_normal = 0
        successful_spike = 0
        
        start_time = time.time()
        while time.time() - start_time < normal_load_duration:
            response = client.get("/books")
            requests_normal += 1
            if response.status_code == 200:
                successful_normal += 1
            time.sleep(1 / normal_rps)
        
        spike_start = time.time()
        while time.time() - spike_start < spike_duration:
            response = client.get("/books")
            requests_spike += 1
            if response.status_code == 200:
                successful_spike += 1
            time.sleep(1 / spike_rps)
        
        start_time = time.time()
        while time.time() - start_time < normal_load_duration:
            response = client.get("/books")
            requests_normal += 1
            if response.status_code == 200:
                successful_normal += 1
            time.sleep(1 / normal_rps)
        
        normal_success_rate = (successful_normal / requests_normal) * 100
        spike_success_rate = (successful_spike / requests_spike) * 100
        
        assert normal_success_rate >= 95.0
        assert spike_success_rate >= 70.0
    
    def test_sustained_write_operations(self, client, auth_headers):
        duration_seconds = 30
        requests_per_second = 2
        
        start_time = time.time()
        request_count = 0
        successful_requests = 0
        
        while time.time() - start_time < duration_seconds:
            book_data = {
                "title": f"Sustained Write {request_count}",
                "author": "Test Author",
                "publication_year": 2020
            }
            response = client.post("/books", json=book_data, headers=auth_headers)
            
            request_count += 1
            if response.status_code == 201:
                successful_requests += 1
            
            time.sleep(1 / requests_per_second)
        
        success_rate = (successful_requests / request_count) * 100
        assert success_rate >= 90.0
    
    def test_sustained_mixed_operations(self, client, auth_headers):
        duration_seconds = 30
        operations_per_second = 3
        
        start_time = time.time()
        operation_count = 0
        successful_operations = 0
        
        while time.time() - start_time < duration_seconds:
            op_type = operation_count % 4
            
            if op_type == 0:
                response = client.get("/books")
            elif op_type == 1:
                response = client.get(f"/books/{(operation_count % 10) + 1}")
            elif op_type == 2:
                book_data = {
                    "title": f"Mixed Op {operation_count}",
                    "author": "Author",
                    "publication_year": 2020
                }
                response = client.post("/books", json=book_data, headers=auth_headers)
            else:
                response = client.get("/books?author=Orwell")
            
            operation_count += 1
            if response.status_code in [200, 201]:
                successful_operations += 1
            
            time.sleep(1 / operations_per_second)
        
        success_rate = (successful_operations / operation_count) * 100
        assert success_rate >= 85.0
    
    def test_sustained_filter_operations(self, client):
        duration_seconds = 30
        filters = ["Orwell", "Tolkien", "Flynn", "Asimov"]
        
        start_time = time.time()
        request_count = 0
        successful_requests = 0
        
        while time.time() - start_time < duration_seconds:
            author = filters[request_count % len(filters)]
            response = client.get(f"/books?author={author}")
            
            request_count += 1
            if response.status_code == 200:
                successful_requests += 1
            
            time.sleep(0.5)
        
        success_rate = (successful_requests / request_count) * 100
        assert success_rate >= 95.0
    
    def test_response_time_degradation(self, client):
        duration_seconds = 30
        measurement_intervals = 6
        interval_duration = duration_seconds / measurement_intervals
        
        interval_durations = []
        
        for interval in range(measurement_intervals):
            interval_start = time.time()
            durations = []
            
            while time.time() - interval_start < interval_duration:
                timer = ResponseTimer()
                timer.start()
                response = client.get("/books")
                duration = timer.stop()
                
                if response.status_code == 200:
                    durations.append(duration)
                
                time.sleep(0.5)
            
            if durations:
                avg_duration = sum(durations) / len(durations)
                interval_durations.append(avg_duration)
        
        if len(interval_durations) > 1:
            first_interval_avg = interval_durations[0]
            last_interval_avg = interval_durations[-1]
            
            degradation = ((last_interval_avg - first_interval_avg) / first_interval_avg) * 100
            assert degradation < 50


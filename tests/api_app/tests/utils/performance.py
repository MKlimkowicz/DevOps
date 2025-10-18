import time
import psutil
import statistics
from typing import List, Dict, Callable, Any
from contextlib import contextmanager


class ResponseTimer:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None
    
    def start(self):
        self.start_time = time.perf_counter()
        return self
    
    def stop(self):
        self.end_time = time.perf_counter()
        self.duration = (self.end_time - self.start_time) * 1000
        return self.duration
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, *args):
        self.stop()


class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.initial_memory = None
        self.peak_memory = None
        self.initial_cpu = None
        self.measurements = []
    
    def start(self):
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = self.initial_memory
        self.initial_cpu = self.process.cpu_percent()
        self.measurements = []
        return self
    
    def measure(self):
        current_memory = self.process.memory_info().rss / 1024 / 1024
        current_cpu = self.process.cpu_percent()
        
        if current_memory > self.peak_memory:
            self.peak_memory = current_memory
        
        measurement = {
            "memory_mb": current_memory,
            "cpu_percent": current_cpu,
            "timestamp": time.time()
        }
        self.measurements.append(measurement)
        return measurement
    
    def get_stats(self) -> Dict[str, float]:
        if not self.measurements:
            return {}
        
        memory_values = [m["memory_mb"] for m in self.measurements]
        cpu_values = [m["cpu_percent"] for m in self.measurements]
        
        return {
            "initial_memory_mb": self.initial_memory,
            "peak_memory_mb": self.peak_memory,
            "memory_increase_mb": self.peak_memory - self.initial_memory,
            "avg_memory_mb": statistics.mean(memory_values),
            "avg_cpu_percent": statistics.mean(cpu_values),
            "max_cpu_percent": max(cpu_values) if cpu_values else 0
        }


class LoadGenerator:
    def __init__(self, client, auth_headers=None):
        self.client = client
        self.auth_headers = auth_headers
        self.results = []
    
    def execute_concurrent(self, func: Callable, iterations: int) -> List[Dict[str, Any]]:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        self.results = []
        
        with ThreadPoolExecutor(max_workers=iterations) as executor:
            futures = [executor.submit(self._timed_execution, func, i) for i in range(iterations)]
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=30)
                    self.results.append(result)
                except Exception as e:
                    self.results.append({
                        "success": False,
                        "error": str(e),
                        "duration_ms": 0
                    })
        
        return self.results
    
    def _timed_execution(self, func: Callable, iteration: int) -> Dict[str, Any]:
        timer = ResponseTimer()
        timer.start()
        
        try:
            response = func(iteration)
            duration = timer.stop()
            
            return {
                "iteration": iteration,
                "success": response.status_code < 400 if hasattr(response, 'status_code') else True,
                "status_code": response.status_code if hasattr(response, 'status_code') else None,
                "duration_ms": duration
            }
        except Exception as e:
            duration = timer.stop()
            return {
                "iteration": iteration,
                "success": False,
                "error": str(e),
                "duration_ms": duration
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        if not self.results:
            return {}
        
        successful = [r for r in self.results if r.get("success", False)]
        failed = [r for r in self.results if not r.get("success", False)]
        
        durations = [r["duration_ms"] for r in self.results if "duration_ms" in r]
        
        stats = {
            "total_requests": len(self.results),
            "successful_requests": len(successful),
            "failed_requests": len(failed),
            "success_rate": len(successful) / len(self.results) * 100 if self.results else 0
        }
        
        if durations:
            sorted_durations = sorted(durations)
            stats.update({
                "min_duration_ms": min(durations),
                "max_duration_ms": max(durations),
                "mean_duration_ms": statistics.mean(durations),
                "median_duration_ms": statistics.median(durations),
                "p95_duration_ms": sorted_durations[int(len(sorted_durations) * 0.95)] if len(sorted_durations) > 0 else 0,
                "p99_duration_ms": sorted_durations[int(len(sorted_durations) * 0.99)] if len(sorted_durations) > 0 else 0
            })
        
        return stats


def calculate_percentile(values: List[float], percentile: int) -> float:
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = int(len(sorted_values) * (percentile / 100))
    return sorted_values[min(index, len(sorted_values) - 1)]


def assert_performance(duration_ms: float, threshold_ms: float, operation: str = "Operation"):
    assert duration_ms < threshold_ms, f"{operation} took {duration_ms:.2f}ms, expected < {threshold_ms}ms"


def assert_response_time_percentile(durations: List[float], percentile: int, threshold_ms: float):
    p_value = calculate_percentile(durations, percentile)
    assert p_value < threshold_ms, f"P{percentile} response time {p_value:.2f}ms exceeds threshold {threshold_ms}ms"


@contextmanager
def memory_profiler():
    monitor = ResourceMonitor()
    monitor.start()
    
    yield monitor
    
    final_stats = monitor.get_stats()
    return final_stats


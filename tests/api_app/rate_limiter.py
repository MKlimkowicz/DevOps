import time
from collections import defaultdict, deque
from fastapi import HTTPException, Request, status
from typing import Dict, Deque
import os
from dotenv import load_dotenv

load_dotenv()


class RateLimiter:
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
    
    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        
        client_requests = self.requests[client_ip]
        while client_requests and client_requests[0] <= now - self.window_seconds:
            client_requests.popleft()
        
        if len(client_requests) >= self.max_requests:
            return False
        
        client_requests.append(now)
        return True
    
    def get_reset_time(self, client_ip: str) -> int:
        client_requests = self.requests[client_ip]
        if not client_requests:
            return 0
        
        oldest_request = client_requests[0]
        reset_time = oldest_request + self.window_seconds
        return max(0, int(reset_time - time.time()))


general_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_READ_MAX", "100")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
)
strict_limiter = RateLimiter(
    max_requests=int(os.getenv("RATE_LIMIT_WRITE_MAX", "10")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
)


async def rate_limit_dependency(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    
    if not general_limiter.is_allowed(client_ip):
        reset_time = general_limiter.get_reset_time(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_time} seconds.",
            headers={"Retry-After": str(reset_time)}
        )


async def strict_rate_limit_dependency(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    
    if not strict_limiter.is_allowed(client_ip):
        reset_time = strict_limiter.get_reset_time(client_ip)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {reset_time} seconds.",
            headers={"Retry-After": str(reset_time)}
        )

import asyncio
import time
from typing import Dict
from .logger import get_logger

logger = get_logger(__name__)

class RateLimiter:
    """
    Token bucket rate limiter to respect Angel One API limits.
    For example: 3 requests per second per IP/Client.
    """
    def __init__(self, requests_per_second: int = 3):
        self.capacity = requests_per_second
        self.tokens = requests_per_second
        self.refill_rate = requests_per_second
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            while True:
                now = time.monotonic()
                time_passed = now - self.last_refill
                
                # Refill tokens
                refill_amount = time_passed * self.refill_rate
                if refill_amount > 0:
                    self.tokens = min(self.capacity, self.tokens + refill_amount)
                    self.last_refill = now
                
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                
                # Wait for next token
                wait_time = (1 - self.tokens) / self.refill_rate
                await asyncio.sleep(wait_time)

# Global rate limiter instance
limiter = RateLimiter(requests_per_second=3)

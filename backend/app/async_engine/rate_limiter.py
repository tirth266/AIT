"""
Rate Limiter
============
Async rate limiting with token bucket and sliding window algorithms.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger('rate_limiter')


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    max_requests: int
    window_seconds: float
    burst_size: Optional[int] = None


class TokenBucket:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: float, capacity: int):
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Try to acquire tokens."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class SlidingWindowCounter:
    """Sliding window rate limiter."""
    
    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = asyncio.Lock()
    
    async def is_allowed(self) -> bool:
        """Check if request is allowed."""
        async with self._lock:
            now = time.time()
            cutoff = now - self.window_seconds
            
            while self.requests and self.requests[0] < cutoff:
                self.requests.popleft()
            
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False
    
    async def get_wait_time(self) -> float:
        """Get time to wait before next request."""
        async with self._lock:
            if not self.requests:
                return 0.0
            
            oldest = self.requests[0]
            now = time.time()
            window_end = oldest + self.window_seconds
            
            if now >= window_end:
                return 0.0
            
            return window_end - now


class RateLimiter:
    """
    Async rate limiter with multiple algorithms.
    
    Features:
    - Token bucket for smooth rate limiting
    - Sliding window for accurate limiting
    - Per-user and per-strategy limits
    - Automatic cleanup of stale entries
    """

    def __init__(self):
        self._token_buckets: Dict[str, TokenBucket] = {}
        self._sliding_windows: Dict[str, SlidingWindowCounter] = {}
        
        self._default_limits: Dict[str, RateLimitConfig] = {
            'strategy_start': RateLimitConfig(max_requests=10, window_seconds=60),
            'order_submit': RateLimitConfig(max_requests=100, window_seconds=60),
            'signal_generate': RateLimitConfig(max_requests=1000, window_seconds=60),
            'data_request': RateLimitConfig(max_requests=500, window_seconds=60),
            'api_call': RateLimitConfig(max_requests=200, window_seconds=60),
        }
        
        self._user_limits: Dict[str, Dict[str, RateLimitConfig]] = defaultdict(dict)
        self._strategy_limits: Dict[str, Dict[str, RateLimitConfig]] = defaultdict(dict)
        
        self._lock = asyncio.Lock()
        self._stats: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
        
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start rate limiter background tasks."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("RateLimiter started")

    async def stop(self) -> None:
        """Stop rate limiter."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        logger.info("RateLimiter stopped")

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup of stale entries."""
        while True:
            try:
                await asyncio.sleep(300)
                await self._cleanup_stale_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

    async def _cleanup_stale_entries(self) -> None:
        """Remove stale rate limit entries."""
        now = time.time()
        cutoff = now - 3600
        
        async with self._lock:
            self._token_buckets = {
                k: v for k, v in self._token_buckets.items()
                if v.last_update > cutoff
            }
            self._sliding_windows = {
                k: v for k, v in self._sliding_windows.items()
                if v.requests and v.requests[-1] > cutoff
            }

    async def check_limit(
        self,
        limit_type: str,
        user_id: Optional[str] = None,
        strategy_id: Optional[str] = None
    ) -> bool:
        """Check if request is allowed under rate limit."""
        limit_key = self._build_limit_key(limit_type, user_id, strategy_id)
        
        config = self._get_config(limit_type, user_id, strategy_id)
        
        if config.burst_size:
            if limit_key not in self._token_buckets:
                self._token_buckets[limit_key] = TokenBucket(
                    rate=config.max_requests / config.window_seconds,
                    capacity=config.burst_size
                )
            
            allowed = await self._token_buckets[limit_key].acquire()
        else:
            if limit_key not in self._sliding_windows:
                self._sliding_windows[limit_key] = SlidingWindowCounter(
                    max_requests=config.max_requests,
                    window_seconds=config.window_seconds
                )
            
            allowed = await self._sliding_windows[limit_key].is_allowed()
        
        if allowed:
            self._stats[limit_type]['allowed'] += 1
        else:
            self._stats[limit_type]['rejected'] += 1
        
        return allowed

    async def wait_for_capacity(
        self,
        limit_type: str,
        user_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        timeout: Optional[float] = None
    ) -> bool:
        """Wait until rate limit allows request."""
        limit_key = self._build_limit_key(limit_type, user_id, strategy_id)
        
        config = self._get_config(limit_type, user_id, strategy_id)
        
        if limit_key not in self._sliding_windows:
            return True
        
        window = self._sliding_windows[limit_key]
        start_time = time.time()
        
        while True:
            if await window.is_allowed():
                return True
            
            if timeout and (time.time() - start_time) >= timeout:
                return False
            
            wait_time = await window.get_wait_time()
            if wait_time > 0:
                await asyncio.sleep(min(wait_time, 1.0))

    def _build_limit_key(self, limit_type: str, user_id: Optional[str], strategy_id: Optional[str]) -> str:
        """Build unique key for rate limit."""
        parts = [limit_type]
        if user_id:
            parts.append(user_id)
        if strategy_id:
            parts.append(strategy_id)
        return ':'.join(parts)

    def _get_config(
        self,
        limit_type: str,
        user_id: Optional[str],
        strategy_id: Optional[str]
    ) -> RateLimitConfig:
        """Get rate limit configuration."""
        if strategy_id and strategy_id in self._strategy_limits:
            if limit_type in self._strategy_limits[strategy_id]:
                return self._strategy_limits[strategy_id][limit_type]
        
        if user_id and user_id in self._user_limits:
            if limit_type in self._user_limits[user_id]:
                return self._user_limits[user_id][limit_type]
        
        return self._default_limits.get(limit_type, RateLimitConfig(max_requests=100, window_seconds=60))

    def set_user_limit(self, user_id: str, limit_type: str, config: RateLimitConfig) -> None:
        """Set custom rate limit for user."""
        self._user_limits[user_id][limit_type] = config

    def set_strategy_limit(self, strategy_id: str, limit_type: str, config: RateLimitConfig) -> None:
        """Set custom rate limit for strategy."""
        self._strategy_limits[strategy_id][limit_type] = config

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            limit_type: {
                'allowed': stats.get('allowed', 0),
                'rejected': stats.get('rejected', 0)
            }
            for limit_type, stats in self._stats.items()
        }


_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
"""
Circuit Breaker and Rate Limiter
=================================
Production-grade resilience patterns for broker API calls.
"""

import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from functools import wraps

logger = logging.getLogger('zerodha.circuit_breaker')


class CircuitState(str, Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 30
    half_open_max_calls: int = 3


class CircuitBreaker:
    """
    Circuit breaker implementation for protecting against cascading failures.
    """

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._half_open_calls = 0
        self._lock = asyncio.Lock()

        self._failure_timestamps: deque = deque(maxlen=100)
        self._call_history: deque = deque(maxlen=1000)

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def is_available(self) -> bool:
        return self._state != CircuitState.OPEN

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        await self._check_state()

        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            await self._record_success(time.time() - start_time)
            return result

        except Exception as e:
            await self._record_failure(time.time() - start_time, str(e))
            raise

    def call_sync(self, func: Callable, *args, **kwargs) -> Any:
        self._check_state_sync()

        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            self._record_success_sync(time.time() - start_time)
            return result

        except Exception as e:
            self._record_failure_sync(time.time() - start_time, str(e))
            raise

    async def _check_state(self) -> None:
        async with self._lock:
            if self._state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._state = CircuitState.HALF_OPEN
                    self._half_open_calls = 0
                    logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name} is OPEN. Retry after timeout."
                    )

            elif self._state == CircuitState.HALF_OPEN:
                if self._half_open_calls >= self.config.half_open_max_calls:
                    raise CircuitBreakerOpenError(
                        f"Circuit {self.name} half-open limit reached"
                    )
                self._half_open_calls += 1

    def _check_state_sync(self) -> None:
        if self._state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self._state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                logger.info(f"Circuit {self.name} transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit {self.name} is OPEN. Retry after timeout."
                )

        elif self._state == CircuitState.HALF_OPEN:
            if self._half_open_calls >= self.config.half_open_max_calls:
                raise CircuitBreakerOpenError(
                    f"Circuit {self.name} half-open limit reached"
                )
            self._half_open_calls += 1

    def _should_attempt_reset(self) -> bool:
        if not self._last_failure_time:
            return True

        elapsed = (datetime.now(timezone.utc) - self._last_failure_time).total_seconds()
        return elapsed >= self.config.timeout_seconds

    async def _record_success(self, duration: float) -> None:
        async with self._lock:
            self._call_history.append({"success": True, "duration": duration, "timestamp": datetime.now(timezone.utc)})

            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(f"Circuit {self.name} CLOSED after successful recovery")

            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    def _record_success_sync(self, duration: float) -> None:
        self._call_history.append({"success": True, "duration": duration, "timestamp": datetime.now(timezone.utc)})

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
                logger.info(f"Circuit {self.name} CLOSED after successful recovery")

        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)

    async def _record_failure(self, duration: float, error: str) -> None:
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = datetime.now(timezone.utc)
            self._failure_timestamps.append(self._last_failure_time)
            self._call_history.append({"success": False, "duration": duration, "error": error, "timestamp": datetime.now(timezone.utc)})

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                self._success_count = 0
                logger.warning(f"Circuit {self.name} OPEN after half-open failure")

            elif self._state == CircuitState.CLOSED:
                if self._failure_count >= self.config.failure_threshold:
                    self._state = CircuitState.OPEN
                    logger.warning(f"Circuit {self.name} OPEN after {self._failure_count} failures")

    def _record_failure_sync(self, duration: float, error: str) -> None:
        self._failure_count += 1
        self._last_failure_time = datetime.now(timezone.utc)
        self._failure_timestamps.append(self._last_failure_time)
        self._call_history.append({"success": False, "duration": duration, "error": error, "timestamp": datetime.now(timezone.utc)})

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
            logger.warning(f"Circuit {self.name} OPEN after half-open failure")

        elif self._state == CircuitState.CLOSED:
            if self._failure_count >= self.config.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(f"Circuit {self.name} OPEN after {self._failure_count} failures")

    def get_stats(self) -> Dict[str, Any]:
        recent_calls = list(self._call_history)[-100:]
        success_count = sum(1 for c in recent_calls if c.get("success"))
        avg_duration = sum(c.get("duration", 0) for c in recent_calls) / max(len(recent_calls), 1)

        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "total_calls": len(self._call_history),
            "recent_success_rate": success_count / max(len(recent_calls), 1),
            "avg_duration_ms": avg_duration * 1000,
        }

    def reset(self) -> None:
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
        self._half_open_calls = 0
        logger.info(f"Circuit {self.name} manually reset")


class CircuitBreakerOpenError(Exception):
    pass


class RateLimitType(str, Enum):
    ORDERS_PER_SECOND = "orders_per_second"
    ORDERS_PER_MINUTE = "orders_per_minute"
    ORDERS_PER_DAY = "orders_per_day"
    API_CALLS_PER_SECOND = "api_calls_per_second"


@dataclass
class RateLimitConfig:
    orders_per_second: int = 1
    orders_per_minute: int = 60
    orders_per_day: int = 1000
    api_calls_per_second: int = 5


class RateLimiter:
    """
    Token bucket rate limiter with multiple rate limit windows.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()

        self._buckets: Dict[RateLimitType, deque] = {
            RateLimitType.ORDERS_PER_SECOND: deque(maxlen=self.config.orders_per_second),
            RateLimitType.ORDERS_PER_MINUTE: deque(maxlen=self.config.orders_per_minute),
            RateLimitType.ORDERS_PER_DAY: deque(maxlen=self.config.orders_per_day),
            RateLimitType.API_CALLS_PER_SECOND: deque(maxlen=self.config.api_calls_per_second),
        }

        self._order_counts: Dict[str, int] = {}
        self._daily_order_count = 0
        self._daily_reset_time: Optional[datetime] = None

        self._lock = asyncio.Lock()

    async def acquire_order_slot(self, client_id: str) -> bool:
        now = datetime.now(timezone.utc)

        if self._daily_reset_time is None or (now - self._daily_reset_time).days >= 1:
            self._daily_order_count = 0
            self._daily_reset_time = now.replace(hour=0, minute=0, second=0, microsecond=0)

        if self._daily_order_count >= self.config.orders_per_day:
            logger.warning(f"Daily order limit reached: {self._daily_order_count}/{self.config.orders_per_day}")
            return False

        async with self._lock:
            self._cleanup_bucket(RateLimitType.ORDERS_PER_SECOND, 1)
            self._cleanup_bucket(RateLimitType.ORDERS_PER_MINUTE, 60)

            if len(self._buckets[RateLimitType.ORDERS_PER_SECOND]) >= self.config.orders_per_second:
                return False

            if len(self._buckets[RateLimitType.ORDERS_PER_MINUTE]) >= self.config.orders_per_minute:
                return False

            self._buckets[RateLimitType.ORDERS_PER_SECOND].append(now)
            self._buckets[RateLimitType.ORDERS_PER_MINUTE].append(now)
            self._daily_order_count += 1
            self._order_counts[client_id] = self._order_counts.get(client_id, 0) + 1

            return True

    async def acquire_api_call(self) -> bool:
        async with self._lock:
            self._cleanup_bucket(RateLimitType.API_CALLS_PER_SECOND, 1)

            if len(self._buckets[RateLimitType.API_CALLS_PER_SECOND]) >= self.config.api_calls_per_second:
                return False

            self._buckets[RateLimitType.API_CALLS_PER_SECOND].append(datetime.now(timezone.utc))
            return True

    def _cleanup_bucket(self, bucket_type: RateLimitType, seconds: int) -> None:
        now = datetime.now(timezone.utc)
        cutoff = now.timestamp() - seconds

        bucket = self._buckets[bucket_type]
        while bucket and bucket[0].timestamp() < cutoff:
            bucket.popleft()

    def get_remaining_quota(self) -> Dict[str, int]:
        now = datetime.now(timezone.utc)

        return {
            "orders_per_second": self.config.orders_per_second - len(self._buckets[RateLimitType.ORDERS_PER_SECOND]),
            "orders_per_minute": self.config.orders_per_minute - len(self._buckets[RateLimitType.ORDERS_PER_MINUTE]),
            "orders_per_day": self.config.orders_per_day - self._daily_order_count,
            "api_calls_per_second": self.config.api_calls_per_second - len(self._buckets[RateLimitType.API_CALLS_PER_SECOND]),
        }

    async def wait_for_slot(self, client_id: str, max_wait_seconds: float = 30) -> bool:
        start_time = time.time()

        while time.time() - start_time < max_wait_seconds:
            if await self.acquire_order_slot(client_id):
                return True

            await asyncio.sleep(0.1)

        return False


def with_circuit_breaker(circuit_breaker: CircuitBreaker):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await circuit_breaker.call(func, *args, **kwargs)

        @wraps(func)
        def wrapper_sync(*args, **kwargs):
            return circuit_breaker.call_sync(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return wrapper
        return wrapper_sync

    return decorator


def with_rate_limiter(rate_limiter: RateLimiter, client_id: str = "default"):
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not await rate_limiter.acquire_order_slot(client_id):
                raise RateLimitExceededError("Rate limit exceeded for orders")

            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return wrapper

        def wrapper_sync(*args, **kwargs):
            raise RuntimeError("Rate limiter requires async function")

        return wrapper_sync

    return decorator


class RateLimitExceededError(Exception):
    pass
"""
Socket Authentication Middleware
================================
JWT authentication, rate limiting, and security middleware for WebSocket.
"""

import os
import logging
import time
import json
import hashlib
from typing import Dict, Optional, Callable, Any, List
from functools import wraps
from dataclasses import dataclass
import threading
import jwt
import asyncio
from flask import request

from app.websocket.redis_manager import get_redis
from app.websocket.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Authentication result."""
    success: bool
    user_id: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None


class SocketAuthMiddleware:
    """
    WebSocket authentication middleware with JWT validation,
    token refresh, and connection throttling.
    """

    def __init__(
        self,
        jwt_secret: str = None,
        jwt_algorithm: str = "HS256",
        token_expiry_seconds: int = 3600,
        refresh_threshold_seconds: int = 300
    ):
        self.jwt_secret = jwt_secret or os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry = token_expiry_seconds
        self.refresh_threshold = refresh_threshold_seconds
        self._rate_limiter: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._rate_limit_window = 60
        self._max_requests_per_window = 100

    def validate_token(self, token: str) -> AuthResult:
        """Validate JWT token and return auth result."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm]
            )

            user_id = payload.get('user_id')
            if not user_id:
                return AuthResult(False, error="Missing user_id in token")

            exp = payload.get('exp', 0)
            if exp < time.time():
                return AuthResult(False, error="Token expired")

            is_blacklisted = self._is_token_blacklisted(payload.get('jti'))
            if is_blacklisted:
                return AuthResult(False, error="Token revoked")

            metadata = {
                'email': payload.get('email'),
                'role': payload.get('role'),
                'device_id': payload.get('device_id'),
                'ip': payload.get('ip')
            }

            return AuthResult(
                success=True,
                user_id=user_id,
                metadata=metadata
            )

        except jwt.ExpiredSignatureError:
            return AuthResult(False, error="Token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult(False, error=f"Invalid token: {str(e)}")

    def refresh_token(self, token: str) -> Optional[str]:
        """Generate new token from valid existing token."""
        try:
            payload = jwt.decode(
                token,
                self.jwt_secret,
                algorithms=[self.jwt_algorithm],
                options={"verify_exp": False}
            )

            new_payload = {**payload}
            new_payload['iat'] = int(time.time())
            new_payload['exp'] = int(time.time()) + self.token_expiry
            new_payload['refreshed'] = True

            return jwt.encode(new_payload, self.jwt_secret, algorithm=self.jwt_algorithm)

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")
            return None

    def _is_token_blacklisted(self, jti: str) -> bool:
        """Check if token JTI is blacklisted."""
        if not jti:
            return False
        try:
            redis = get_redis()
            return redis.exists(f"blacklist:{jti}")
        except Exception as e:
            logger.warning(f"Blacklist check failed: {e}")
            return False

    def check_rate_limit(self, identifier: str, limit: int = None) -> bool:
        """Check rate limit for identifier."""
        limit = limit or self._max_requests_per_window

        with self._lock:
            now = time.time()
            if identifier not in self._rate_limiter:
                self._rate_limiter[identifier] = []

            self._rate_limiter[identifier] = [
                t for t in self._rate_limiter[identifier]
                if now - t < self._rate_limit_window
            ]

            if len(self._rate_limiter[identifier]) >= limit:
                return False

            self._rate_limiter[identifier].append(now)
            return True


class SocketRateLimiter:
    """
    Per-user, per-event WebSocket rate limiter with Redis backend.
    """

    def __init__(
        self,
        events_per_minute: int = 60,
        events_per_second: int = 10,
        burst_limit: int = 20
    ):
        self.events_per_minute = events_per_minute
        self.events_per_second = events_per_second
        self.burst_limit = burst_limit
        self._local_cache: Dict[str, List[float]] = {}
        self._lock = threading.Lock()
        self._redis_prefix = "ws:ratelimit:"

    def check_limit(self, user_id: str, event: str) -> bool:
        """Check if user has exceeded rate limit for event."""
        key = f"{user_id}:{event}"
        now = time.time()

        with self._lock:
            if key not in self._local_cache:
                self._local_cache[key] = []

            self._local_cache[key] = [
                t for t in self._local_cache[key]
                if now - t < 60
            ]

            if len(self._local_cache[key]) >= self.events_per_minute:
                self._check_redis_fallback(user_id, event)
                return False

            self._local_cache[key].append(now)
            return True

    def _check_redis_fallback(self, user_id: str, event: str):
        """Fallback to Redis rate limiting."""
        try:
            redis = get_redis()
            key = f"{self._redis_prefix}{user_id}:{event}"
            count = redis.get(key)

            if count and int(count) >= self.events_per_minute:
                logger.warning(f"Rate limit exceeded (Redis): {user_id}:{event}")
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")


class ConnectionThrottler:
    """
    Throttle connection attempts to prevent connection storms.
    """

    def __init__(
        self,
        max_connections_per_second: int = 100,
        max_connections_per_minute: int = 1000,
        cooldown_seconds: int = 10
    ):
        self.max_per_second = max_connections_per_second
        self.max_per_minute = max_connections_per_minute
        self.cooldown = cooldown_seconds

        self._second_tracker: List[float] = []
        self._minute_tracker: List[float] = []
        self._lock = threading.Lock()
        self._blocked_ips: Dict[str, float] = {}

    def can_connect(self, ip: str = None) -> bool:
        """Check if connection should be allowed."""
        now = time.time()

        with self._lock:
            if ip in self._blocked_ips:
                if now - self._blocked_ips[ip] < self.cooldown:
                    return False
                del self._blocked_ips[ip]

            self._second_tracker = [t for t in self._second_tracker if now - t < 1]
            self._minute_tracker = [t for t in self._minute_tracker if now - t < 60]

            if len(self._second_tracker) >= self.max_per_second:
                return False

            if len(self._minute_tracker) >= self.max_per_minute:
                if ip:
                    self._blocked_ips[ip] = now
                return False

            self._second_tracker.append(now)
            self._minute_tracker.append(now)
            return True

    def get_stats(self) -> Dict:
        """Get throttle statistics."""
        with self._lock:
            return {
                'current_second': len(self._second_tracker),
                'current_minute': len(self._minute_tracker),
                'blocked_ips': len(self._blocked_ips)
            }


class SocketMiddlewareChain:
    """
    Chain of middleware for processing socket events.
    """

    def __init__(self):
        self._middleware: List[Callable] = []

    def add(self, middleware: Callable):
        """Add middleware to chain."""
        self._middleware.append(middleware)

    async def process(self, context: Dict) -> Dict:
        """Process context through middleware chain."""
        for middleware in self._middleware:
            result = await middleware(context)
            if not result.get('continue', True):
                return result
        return context


class WebSocketSecurityHeaders:
    """
    Security headers and validation for WebSocket connections.
    """

    @staticmethod
    def validate_origin(origin: str, allowed_origins: List[str] = None) -> bool:
        """Validate WebSocket origin."""
        if not allowed_origins:
            return True
        return origin in allowed_origins

    @staticmethod
    def sanitize_input(data: Any) -> Any:
        """Sanitize input data."""
        if isinstance(data, dict):
            return {k: WebSocketSecurityHeaders.sanitize_input(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [WebSocketSecurityHeaders.sanitize_input(i) for i in data]
        elif isinstance(data, str):
            if len(data) > 10000:
                return data[:10000]
            return data.replace('\x00', '').replace('\r', '').replace('\n', '')
        return data

    @staticmethod
    def generate_session_token(user_id: str) -> str:
        """Generate secure session token."""
        random_part = os.urandom(32).hex()
        timestamp = str(int(time.time()))
        return hashlib.sha256(f"{user_id}:{timestamp}:{random_part}").hexdigest()


_global_auth_middleware: Optional[SocketAuthMiddleware] = None
_global_rate_limiter: Optional[SocketRateLimiter] = None
_global_throttler: Optional[ConnectionThrottler] = None


def get_auth_middleware() -> SocketAuthMiddleware:
    """Get global auth middleware."""
    global _global_auth_middleware
    if _global_auth_middleware is None:
        _global_auth_middleware = SocketAuthMiddleware()
    return _global_auth_middleware


def get_rate_limiter() -> SocketRateLimiter:
    """Get global rate limiter."""
    global _global_rate_limiter
    if _global_rate_limiter is None:
        _global_rate_limiter = SocketRateLimiter()
    return _global_rate_limiter


def get_throttler() -> ConnectionThrottler:
    """Get global connection throttler."""
    global _global_throttler
    if _global_throttler is None:
        _global_throttler = ConnectionThrottler()
    return _global_throttler
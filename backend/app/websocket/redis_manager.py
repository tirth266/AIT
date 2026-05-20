"""
Redis Connection Manager
========================
Manages Redis connections for horizontal scaling with connection pooling,
pubsub channels, and message queue integration.
Provides graceful fallback if Redis is unavailable.
"""

import os
import logging
import json
import asyncio
from typing import Dict, List, Optional, Any, Callable, Tuple
from contextlib import asynccontextmanager
import threading
import time

import redis
from redis.asyncio import Redis as AsyncRedis
from redis.asyncio import ConnectionPool as AsyncConnectionPool

logger = logging.getLogger(__name__)


class RedisConnectionPool:
    """Thread-safe Redis connection pool with sync and async support."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: Dict = None):
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True

        config = config or {}
        self.redis_url = config.get('REDIS_URL', os.environ.get('REDIS_URL', 'redis://localhost:6379/0'))
        self.max_connections = config.get('MAX_CONNECTIONS', 50)
        self.socket_timeout = config.get('SOCKET_TIMEOUT', 5)
        self.socket_connect_timeout = config.get('SOCKET_CONNECT_TIMEOUT', 5)
        self.socket_keepalive = config.get('SOCKET_KEEPALIVE', True)
        self.retry_on_timeout = config.get('RETRY_ON_TIMEOUT', True)
        self.health_check_interval = config.get('HEALTH_CHECK_INTERVAL', 30)

        self._sync_pool: Optional[redis.ConnectionPool] = None
        self._async_pool: Optional[AsyncConnectionPool] = None
        self._client: Optional[redis.Redis] = None
        self._async_client: Optional[AsyncRedis] = None
        self._health_check_thread: Optional[threading.Thread] = None
        self._running = False
        self._redis_available = False
        self._init_error: Optional[str] = None

    def initialize(self):
        """Initialize sync and async connection pools with connection test."""
        try:
            self._sync_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=self.max_connections,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                socket_keepalive=self.socket_keepalive,
                retry_on_timeout=self.retry_on_timeout,
                decode_responses=True
            )
            self._client = redis.Redis(connection_pool=self._sync_pool)
            self._client.ping()
            self._redis_available = True
            logger.info(f"[OK] Redis connected: {self.redis_url}")

            self._async_pool = AsyncConnectionPool.from_url(
                self.redis_url.replace('/0', '/1'),
                max_connections=self.max_connections // 2,
                socket_timeout=self.socket_timeout,
                socket_connect_timeout=self.socket_connect_timeout,
                decode_responses=True
            )
            self._async_client = AsyncRedis(connection_pool=self._async_pool)

            self._start_health_check()
        except Exception as e:
            self._redis_available = False
            self._init_error = str(e)
            logger.warning(f"[WARN] Redis connection failed: {e}")
            logger.warning(f"[WARN] Continuing without Redis (local mode)")

    def is_available(self) -> bool:
        """Check if Redis is available."""
        if not self._redis_available:
            return False
        try:
            if self._client:
                self._client.ping()
                return True
        except Exception:
            self._redis_available = False
        return False

    def _start_health_check(self):
        """Start background health check."""
        if not self._redis_available:
            return
        self._running = True
        self._health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_check_thread.start()

    def _health_check_loop(self):
        """Periodic health check for Redis connections."""
        while self._running:
            try:
                if self._client:
                    self._client.ping()
            except Exception as e:
                logger.warning(f"Redis health check failed: {e}")
                self._redis_available = False
                try:
                    if self._sync_pool:
                        self._client = redis.Redis(connection_pool=self._sync_pool)
                        self._client.ping()
                        self._redis_available = True
                except Exception as reinit_error:
                    logger.warning(f"Redis reconnection failed: {reinit_error}")
            time.sleep(self.health_check_interval)

    def get_client(self) -> redis.Redis:
        """Get sync Redis client."""
        if not self._redis_available:
            raise RuntimeError("Redis is not available. Using local mode.")
        if not self._client:
            self.initialize()
        return self._client

    def get_async_client(self) -> AsyncRedis:
        """Get async Redis client."""
        if not self._redis_available:
            raise RuntimeError("Redis is not available. Using local mode.")
        if not self._async_client:
            self.initialize()
        return self._async_client

    def get_pubsub(self) -> Any:
        """Get Redis PubSub client."""
        return redis.Redis(connection_pool=self._sync_pool).pubsub()

    def get_async_pubsub(self) -> Any:
        """Get async Redis PubSub client."""
        return self.get_async_client().pubsub()

    def close(self):
        """Close all connections."""
        self._running = False
        if self._client:
            self._client.close()
        if self._sync_pool:
            self._sync_pool.disconnect()
        if self._async_client:
            asyncio.run(self._async_client.close())
        if self._async_pool:
            asyncio.run(self._async_pool.disconnect())
        logger.info("Redis connection pools closed")


_redis_pool: Optional[RedisConnectionPool] = None


def get_redis_pool() -> RedisConnectionPool:
    """Get the Redis connection pool singleton."""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = RedisConnectionPool()
        _redis_pool.initialize()
    return _redis_pool


def get_redis() -> redis.Redis:
    """Get sync Redis client."""
    return get_redis_pool().get_client()


def get_redis_async() -> AsyncRedis:
    """Get async Redis client."""
    return get_redis_pool().get_async_client()
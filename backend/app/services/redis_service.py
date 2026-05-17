"""
=============================================================================
REDIS SERVICE MODULE
=============================================================================
Production-grade Redis integration for:
- WebSocket Pub/Sub (horizontal scaling)
- Market data caching
- Rate limiting
- Session management
- Token blacklist

Author: Staff Engineer
"""

import json
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import timedelta
import redis
from redis.connection import ConnectionPool
from redis.client import PubSub
import threading
import signal
import sys

logger = logging.getLogger('trading_app')


class RedisService:
    """
    Production Redis Service with connection pooling, pub/sub, and caching.
    """

    _instance: Optional['RedisService'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._redis_client: Optional[redis.Redis] = None
        self._pubsub: Optional[PubSub] = None
        self._connection_pool: Optional[ConnectionPool] = None
        self._pub_client: Optional[redis.Redis] = None
        self._is_running = False
        self._message_handlers: Dict[str, Callable] = {}
        self._pubsub_thread: Optional[threading.Thread] = None

    @classmethod
    def get_instance(cls) -> 'RedisService':
        """Get singleton instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, redis_url: str) -> bool:
        """
        Initialize Redis connection with connection pooling.

        Args:
            redis_url: Redis connection URL

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Initializing Redis service with URL: {redis_url.split('@')[-1] if '@' in redis_url else redis_url}")

            # Create connection pool for better performance
            self._connection_pool = ConnectionPool.from_url(
                redis_url,
                max_connections=50,
                decode_responses=True,
                socket_keepalive=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )

            # Main client for operations
            self._redis_client = redis.Redis(connection_pool=self._connection_pool)

            # Separate client for publishing (high throughput)
            self._pub_client = redis.Redis(
                connection_pool=ConnectionPool.from_url(
                    redis_url,
                    max_connections=20,
                    decode_responses=True
                )
            )

            # Test connection
            self._redis_client.ping()
            logger.info("Redis service initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Redis service: {e}")
            return False

    def get_client(self) -> redis.Redis:
        """Get main Redis client."""
        if not self._redis_client:
            raise RuntimeError("Redis service not initialized")
        return self._redis_client

    # =========================================================================
    # CACHE OPERATIONS
    # =========================================================================

    def cache_set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        namespace: str = 'cache'
    ) -> bool:
        """
        Set a value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
            namespace: Key namespace prefix

        Returns:
            True if successful
        """
        try:
            full_key = f"{namespace}:{key}"
            serialized = json.dumps(value) if not isinstance(value, str) else value
            return self._redis_client.setex(full_key, ttl, serialized)
        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")
            return False

    def cache_get(self, key: str, namespace: str = 'cache') -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key
            namespace: Key namespace prefix

        Returns:
            Cached value or None
        """
        try:
            full_key = f"{namespace}:{key}"
            value = self._redis_client.get(full_key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            return None

    def cache_delete(self, key: str, namespace: str = 'cache') -> bool:
        """Delete a key from cache."""
        try:
            full_key = f"{namespace}:{key}"
            return bool(self._redis_client.delete(full_key))
        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")
            return False

    def cache_clear_pattern(self, pattern: str, namespace: str = 'cache') -> int:
        """Clear all keys matching a pattern."""
        try:
            full_pattern = f"{namespace}:{pattern}"
            keys = self._redis_client.keys(full_pattern)
            if keys:
                return self._redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache clear pattern failed for {pattern}: {e}")
            return 0

    # =========================================================================
    # MARKET DATA CACHING
    # =========================================================================

    def cache_market_data(self, symbol: str, data: Dict, ttl: int = 5) -> bool:
        """
        Cache market data with short TTL (real-time data).

        Args:
            symbol: Trading symbol
            data: Market data dictionary
            ttl: Time to live in seconds (default 5 for real-time data)

        Returns:
            True if successful
        """
        return self.cache_set(f"market:{symbol}", data, ttl=ttl, namespace='market')

    def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get cached market data for a symbol."""
        return self.cache_get(f"market:{symbol}", namespace='market')

    def cache_orderbook(self, symbol: str, orderbook: Dict, ttl: int = 2) -> bool:
        """Cache orderbook data."""
        return self.cache_set(f"orderbook:{symbol}", orderbook, ttl=ttl, namespace='market')

    def get_orderbook(self, symbol: str) -> Optional[Dict]:
        """Get cached orderbook."""
        return self.cache_get(f"orderbook:{symbol}", namespace='market')

    def cache_historical_candles(
        self,
        symbol: str,
        interval: str,
        candles: List[Dict],
        ttl: int = 60
    ) -> bool:
        """Cache historical candle data."""
        key = f"{symbol}:{interval}"
        return self.cache_set(key, candles, ttl=ttl, namespace='history')

    def get_historical_candles(
        self,
        symbol: str,
        interval: str
    ) -> Optional[List[Dict]]:
        """Get cached historical candles."""
        key = f"{symbol}:{interval}"
        return self.cache_get(key, namespace='history')

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    def create_session(
        self,
        session_id: str,
        user_data: Dict,
        ttl: int = 86400
    ) -> bool:
        """
        Create a user session.

        Args:
            session_id: Unique session identifier
            user_data: User data to store
            ttl: Session TTL in seconds (default 24 hours)

        Returns:
            True if successful
        """
        return self.cache_set(f"session:{session_id}", user_data, ttl=ttl, namespace='session')

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data."""
        return self.cache_get(f"session:{session_id}", namespace='session')

    def update_session(self, session_id: str, user_data: Dict) -> bool:
        """Update session data (refresh TTL)."""
        return self.create_session(session_id, user_data)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        return self.cache_delete(f"session:{session_id}", namespace='session')

    # =========================================================================
    # TOKEN BLACKLIST (JWT)
    # =========================================================================

    def blacklist_token(self, jti: str, ttl: int = 3600) -> bool:
        """
        Add a token to blacklist.

        Args:
            jti: JWT ID
            ttl: TTL in seconds (default 1 hour = token lifetime)

        Returns:
            True if successful
        """
        return self.cache_set(f"blacklist:{jti}", {"revoked": True}, ttl=ttl, namespace='auth')

    def is_token_blacklisted(self, jti: str) -> bool:
        """Check if a token is blacklisted."""
        result = self.cache_get(f"blacklist:{jti}", namespace='auth')
        return result is not None

    # =========================================================================
    # RATE LIMITING
    # =========================================================================

    def check_rate_limit(
        self,
        identifier: str,
        limit: int = 100,
        window: int = 60
    ) -> tuple[bool, int]:
        """
        Check rate limit for an identifier.

        Args:
            identifier: User identifier (IP, user_id, etc.)
            limit: Max requests allowed
            window: Time window in seconds

        Returns:
            Tuple of (is_allowed, remaining_requests)
        """
        try:
            key = f"ratelimit:{identifier}"
            current = self._redis_client.get(key)

            if current is None:
                self._redis_client.setex(key, window, 1)
                return True, limit - 1

            current_count = int(current)
            if current_count >= limit:
                ttl = self._redis_client.ttl(key)
                return False, 0

            self._redis_client.incr(key)
            return True, limit - current_count - 1

        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            return True, limit  # Fail open

    def reset_rate_limit(self, identifier: str) -> bool:
        """Reset rate limit for an identifier."""
        return self.cache_delete(f"ratelimit:{identifier}", namespace='')

    # =========================================================================
    # PUB/SUB FOR WEBSOCKET SCALING
    # =========================================================================

    def publish(self, channel: str, message: Dict) -> int:
        """
        Publish a message to a channel.

        Args:
            channel: Channel name
            message: Message to publish (will be JSON serialized)

        Returns:
            Number of subscribers that received the message
        """
        try:
            serialized = json.dumps(message)
            return self._pub_client.publish(channel, serialized)
        except Exception as e:
            logger.error(f"Publish failed to channel {channel}: {e}")
            return 0

    def subscribe(self, channels: List[str], handler: Callable[[str, Dict], None]):
        """
        Subscribe to channels with a message handler.

        Args:
            channels: List of channel names
            handler: Callback function (channel, message)
        """
        self._pubsub = self._redis_client.pubsub()
        self._pubsub.subscribe(*channels)
        self._message_handlers = {ch: handler for ch in channels}
        self._is_running = True

        def _listen():
            while self._is_running:
                try:
                    message = self._pubsub.get_message(timeout=1.0)
                    if message and message['type'] == 'message':
                        channel = message['channel']
                        try:
                            data = json.loads(message['data'])
                        except json.JSONDecodeError:
                            data = message['data']

                        if channel in self._message_handlers:
                            try:
                                self._message_handlers[channel](channel, data)
                            except Exception as e:
                                logger.error(f"Handler error for {channel}: {e}")
                except Exception as e:
                    if self._is_running:
                        logger.error(f"PubSub error: {e}")

        self._pubsub_thread = threading.Thread(target=_listen, daemon=True)
        self._pubsub_thread.start()
        logger.info(f"Subscribed to channels: {channels}")

    def unsubscribe(self):
        """Unsubscribe from all channels."""
        self._is_running = False
        if self._pubsub:
            self._pubsub.unsubscribe()
            self._pubsub.close()
        logger.info("Unsubscribed from all channels")

    # =========================================================================
    # WEBSOCKET CHANNELS
    # =========================================================================

    def publish_market_update(self, symbol: str, data: Dict):
        """Publish market data update."""
        self.publish(f"market:{symbol}", data)

    def publish_user_update(self, user_id: str, event: str, data: Dict):
        """Publish user-specific update."""
        self.publish(f"user:{user_id}:{event}", data)

    def publish_strategy_update(self, strategy_id: str, data: Dict):
        """Publish strategy update."""
        self.publish(f"strategy:{strategy_id}", data)

    def publish_notification(self, user_id: str, notification: Dict):
        """Publish notification to user."""
        self.publish(f"notification:{user_id}", notification)

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    def health_check(self) -> bool:
        """Check Redis connection health."""
        try:
            if self._redis_client:
                self._redis_client.ping()
                return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
        return False

    def get_info(self) -> Dict:
        """Get Redis server info."""
        try:
            if self._redis_client:
                return self._redis_client.info()
        except Exception as e:
            logger.error(f"Failed to get Redis info: {e}")
        return {}

    def shutdown(self):
        """Graceful shutdown."""
        logger.info("Shutting down Redis service...")
        self._is_running = False
        if self._pubsub:
            self._pubsub.close()
        if self._connection_pool:
            self._connection_pool.disconnect()
        logger.info("Redis service shut down")


# Global instance
redis_service = RedisService.get_instance()


def get_redis_service() -> RedisService:
    """Get the Redis service instance."""
    return redis_service
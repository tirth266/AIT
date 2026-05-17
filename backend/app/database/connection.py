"""
Database Connection Module
===========================
MongoDB and Redis connection management.
"""

from pymongo import MongoClient
from typing import Optional
import logging

logger = logging.getLogger('trading_app')

_mongo_client = None
_redis_client = None
_mongo_db = None


def init_mongo(mongo_uri: str, db_name: str = 'trading_db') -> None:
    """Initialize MongoDB connection."""
    global _mongo_client, _mongo_db
    from pymongo import MongoClient

    _mongo_client = MongoClient(
        mongo_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        maxPoolSize=50,
        minPoolSize=10
    )
    _mongo_db = _mongo_client[db_name]
    logger.info(f"MongoDB connected: {db_name}")


def init_redis(redis_url: str) -> None:
    """Initialize Redis connection."""
    global _redis_client
    import redis as redis_lib

    _redis_client = redis_lib.from_url(redis_url, decode_responses=True)
    _redis_client.ping()
    logger.info("Redis connected")


def get_mongo():
    """Get MongoDB client."""
    return _mongo_client


def get_db():
    """Get MongoDB database instance."""
    return _mongo_db


def get_redis():
    """Get Redis client instance."""
    return _redis_client


def close_connections() -> None:
    """Close all database connections."""
    global _mongo_client, _redis_client

    if _mongo_client:
        _mongo_client.close()
        logger.info("MongoDB connection closed")

    if _redis_client:
        _redis_client.close()
        logger.info("Redis connection closed")


class MongoDB:
    """MongoDB database wrapper."""

    def __init__(self):
        self.client = None
        self.db = None

    def connect(self, mongo_uri: str, db_name: str):
        self.client = _mongo_client or MongoClient(mongo_uri)
        self.db = self.client[db_name]
        return self.db

    def get_collection(self, name: str):
        return self.db[name] if self.db else None


class RedisClient:
    """Redis client wrapper."""

    def __init__(self):
        self.client = None

    def connect(self, redis_url: str):
        import redis as redis_lib
        self.client = redis_lib.from_url(redis_url, decode_responses=True)
        return self.client

    def get(self, key: str) -> Optional[str]:
        return self.client.get(key) if self.client else None

    def set(self, key: str, value: str, ex: int = None):
        if self.client:
            self.client.set(key, value, ex=ex)

    def delete(self, key: str):
        if self.client:
            self.client.delete(key)


mongo_db_instance = MongoDB()
redis_client_instance = RedisClient()
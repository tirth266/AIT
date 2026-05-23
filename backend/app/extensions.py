"""
Flask Extensions Initialization
=================================
Initialize all Flask extensions: MongoDB, Redis, Celery, CORS, Limiter.
Production-ready with proper Redis integration.
"""

import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
import redis

from .celery_app import celery_app
from .services.redis_service import get_redis_service

logger = logging.getLogger('trading_app')

# Centralized Limiter instance (initialized without app initially)
limiter = Limiter(key_func=get_remote_address)
mongo_client = None
mongo_db = None
redis_client = None
redis_service = None


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions."""
    global mongo_client, mongo_db, redis_client, redis_service

    print("[DEBUG] init_extensions() called", flush=True)
    init_mongodb(app)
    print("[DEBUG] init_mongodb() completed", flush=True)
    
    init_redis(app)
    init_redis_service(app)

    logger.info("All extensions initialized")


def init_limiter(app: Flask) -> None:
    """Initialize Flask-Limiter."""
    limiter.init_app(app)
    logger.info("Rate limiter initialized")


def init_mongodb(app: Flask) -> None:
    """Initialize MongoDB connection with validation."""
    print("[MONGO] init_mongodb() entered", flush=True)  # Must appear in logs
    global mongo_client, mongo_db
    print("\n" + "-"*50, flush=True)
    print("  MongoDB Connection", flush=True)
    print("-"*50, flush=True)

    try:
        mongo_uri = app.config.get('MONGO_URI') or os.environ.get("MONGO_URI")
        if not mongo_uri:
            print("[ERROR] MONGO_URI is not set in app.config or environment!", flush=True)
            logger.error("[MONGO] MONGO_URI is not set!")
            return None

        logger.info(f"[MONGO] Connecting to MongoDB...")
        
        # Hide password in logs
        log_uri = mongo_uri
        if "@" in mongo_uri:
            prefix = mongo_uri.split("@")[0]
            suffix = mongo_uri.split("@")[1]
            if ":" in prefix:
                protocol = prefix.split("://")[0]
                user = prefix.split("://")[1].split(":")[0]
                log_uri = f"{protocol}://{user}:****@{suffix}"
        
        print(f"[INFO] Connecting to: {log_uri}", flush=True)

        mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=10,
            retryWrites=True,
            w='majority'
        )
        
        # Force connection test
        mongo_client.admin.command('ping')
        print("[OK] MongoDB connected successfully!", flush=True)
        logger.info("[MONGO] MongoDB connected successfully!")

        db_name = app.config.get('MONGO_DB_NAME', 'trading_db')
        mongo_db = mongo_client[db_name]

        app.mongo_db = mongo_db

        from .database import connection
        connection._mongo_client = mongo_client
        connection._mongo_db = mongo_db

        logger.info(f"MongoDB database initialized: {db_name}")
    except Exception as e:
        print(f"[ERROR] MongoDB connection failed: {e}", flush=True)
        logger.error(f"[MONGO] Connection failed: {e}")
        print("[WARN] Application will run with limited functionality", flush=True)
        mongo_client = None
        mongo_db = None
    
    print("-"*50 + "\n", flush=True)


def init_redis(app: Flask) -> None:
    """Initialize Redis connection with graceful fallback."""
    global redis_client
    print("\n" + "-"*50, flush=True)
    print("  Redis Connection", flush=True)
    print("-"*50, flush=True)

    try:
        redis_url = app.config.get('REDIS_URL')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        app.redis = redis_client
        print(f"[OK] Redis connected: {redis_url}", flush=True)
        logger.info(f"Redis connected: {redis_url}")
    except Exception as e:
        print(f"[WARN] Redis connection failed: {e}", flush=True)
        print("[WARN] Continuing without Redis (local mode)", flush=True)
        logger.warning(f"Redis connection failed: {e}")
        redis_client = None

    print("-"*50 + "\n", flush=True)


def init_redis_service(app: Flask) -> None:
    """Initialize the Redis service for caching, pub/sub, and sessions."""
    global redis_service

    try:
        redis_url = app.config.get('REDIS_URL')
        redis_service = get_redis_service()
        
        if redis_service:
            initialized = redis_service.initialize(redis_url)
            if initialized:
                app.redis_service = redis_service
                logger.info("Redis service initialized (caching, pub/sub, sessions)")
            else:
                logger.warning("Redis service initialization failed, continuing without it")
        else:
            logger.error("Redis service unavailable - get_redis_service() returned None")
    except Exception as e:
        logger.error(f"Redis service initialization failed: {e}")
        redis_service = None


def get_mongo_db():
    """Get MongoDB database instance."""
    return mongo_db


def get_redis_client():
    """Get Redis client instance."""
    return redis_client


def get_redis_service():
    """Get the Redis service instance."""
    return redis_service
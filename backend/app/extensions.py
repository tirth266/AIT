"""
Flask Extensions Initialization
==============================
Initialize all Flask extensions: JWT, MongoDB, Redis, Celery, CORS, Limiter.
Production-ready with proper Redis integration.
"""

import logging
from flask import Flask
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from pymongo import MongoClient
import redis

from app.celery_app import celery_app
from app.services.redis_service import get_redis_service

logger = logging.getLogger('trading_app')

jwt_manager = JWTManager()
limiter = Limiter(key_func=get_remote_address, storage_uri="memory://")
mongo_client = None
mongo_db = None
redis_client = None
redis_service = None


def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions."""
    global mongo_client, mongo_db, redis_client, redis_service

    init_jwt(app)
    init_cors(app)
    init_limiter(app)
    init_mongodb(app)
    init_redis(app)
    init_redis_service(app)

    logger.info("All extensions initialized")


def init_jwt(app: Flask) -> None:
    """Initialize Flask-JWT-Extended."""
    jwt_manager.init_app(app)

    @jwt_manager.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload['jti']
        from app.database.connection import get_redis
        redis_conn = get_redis()
        if redis_conn:
            token_in_redis = redis_conn.get(f'blacklist:{jti}')
            return token_in_redis is not None
        return False

    @jwt_manager.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {
            'error': 'token_expired',
            'message': 'The token has expired'
        }, 401

    @jwt_manager.invalid_token_loader
    def invalid_token_callback(error):
        return {
            'error': 'invalid_token',
            'message': 'Invalid token'
        }, 401

    @jwt_manager.unauthorized_loader
    def missing_token_callback(error):
        return {
            'error': 'authorization_required',
            'message': 'Authorization required'
        }, 401

    logger.info("JWT manager initialized")


def init_cors(app: Flask) -> None:
    """Initialize Flask-CORS."""
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', '*'),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Length", "X-Total-Count"],
            "supports_credentials": True
        }
    })
    logger.info("CORS initialized")


def init_limiter(app: Flask) -> None:
    """Initialize Flask-Limiter."""
    limiter.init_app(app)
    logger.info("Rate limiter initialized")


def init_mongodb(app: Flask) -> None:
    """Initialize MongoDB connection."""
    global mongo_client, mongo_db

    try:
        mongo_uri = app.config.get('MONGO_URI')
        mongo_client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=10
        )
        mongo_client.admin.command('ping')

        db_name = app.config.get('MONGO_DB_NAME', 'trading_db')
        mongo_db = mongo_client[db_name]

        app.mongo_db = mongo_db

        from app.database import connection
        connection._mongo_client = mongo_client
        connection._mongo_db = mongo_db

        logger.info(f"MongoDB connected: {db_name}")
    except Exception as e:
        logger.error(f"MongoDB connection failed: {e}")
        mongo_client = None
        mongo_db = None


def init_redis(app: Flask) -> None:
    """Initialize Redis connection."""
    global redis_client

    try:
        redis_url = app.config.get('REDIS_URL')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
        app.redis = redis_client
        logger.info("Redis connected")
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_client = None


def init_redis_service(app: Flask) -> None:
    """Initialize the Redis service for caching, pub/sub, and sessions."""
    global redis_service

    try:
        redis_url = app.config.get('REDIS_URL')
        redis_service = get_redis_service()
        initialized = redis_service.initialize(redis_url)

        if initialized:
            app.redis_service = redis_service
            logger.info("Redis service initialized (caching, pub/sub, sessions)")
        else:
            logger.warning("Redis service initialization failed, continuing without it")
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
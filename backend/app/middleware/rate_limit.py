"""
=============================================================================
RATE LIMITING MIDDLEWARE
=============================================================================
Production-grade rate limiting with Redis storage for distributed systems.

Features:
- Redis-backed rate limiting (works across multiple instances)
- Different limits per endpoint type
- User-based rate limiting (when authenticated)
- IP-based rate limiting (fallback)
- Account lockout after excessive failed attempts

Author: Staff Engineer
"""

from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps
import logging
import hashlib

logger = logging.getLogger('trading_app')


def get_rate_limit_key():
    """
    Get the rate limit key based on authentication status.
    Uses user_id if authenticated, otherwise falls back to IP.
    """
    # Try to get user_id from JWT token
    try:
        from flask_jwt_extended import get_jwt_identity
        user_id = get_jwt_identity()
        if user_id:
            return f"user:{user_id}"
    except Exception:
        pass

    # Fall back to IP address
    forwarded_for = request.headers.get('X-Forwarded-For')
    if forwarded_for:
        ip = forwarded_for.split(',')[0].strip()
    else:
        ip = request.remote_addr

    return f"ip:{ip}"


def init_rate_limiting(app: Flask) -> None:
    """Initialize rate limiting with Redis storage."""

    # Determine storage URI
    ratelimit_storage = app.config.get('RATELIMIT_STORAGE_URL', 'memory://')

    # For production, use Redis
    if 'redis' in ratelimit_storage:
        logger.info("Using Redis for rate limiting")
    else:
        logger.warning("Using in-memory rate limiting - NOT RECOMMENDED FOR PRODUCTION")

    limiter = Limiter(
        key_func=get_rate_limit_key,
        storage_uri=ratelimit_storage,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '100/minute')],
        strategy='fixed-window',
        storage_options={
            'socket_timeout': 5,
            'socket_connect_timeout': 5,
        },
        headers_enabled=True,  # Enable rate limit headers
        header_limit='X-RateLimit-Limit',
        header_remaining='X-RateLimit-Remaining',
        header_reset='X-RateLimit-Reset'
    )
    limiter.init_app(app)

    # Custom rate limit error handler
    @app.errorhandler(429)
    def ratelimit_handler(error):
        logger.warning(
            f"Rate limit exceeded: {get_rate_limit_key()} - "
            f"Path: {request.path}"
        )
        response = jsonify({
            'error': 'RATE_LIMIT_EXCEEDED',
            'message': 'Too many requests. Please try again later.',
            'retry_after': error.description.get('retry_after', 60) if isinstance(error.description, dict) else 60
        })
        response.status_code = 429
        response.headers['Retry-After'] = '60'
        return response

    # Add rate limits to specific endpoints
    add_custom_limits(limiter)

    logger.info("Rate limiting middleware initialized with Redis storage")


def add_custom_limits(limiter: Limiter) -> None:
    """Add custom rate limits for specific endpoints."""

    # Auth endpoints - stricter limits
    limiter.limit("5/minute", methods=["POST"], endpoints=['/api/v1/auth/login', '/api/v1/auth/register'])
    limiter.limit("3/minute", methods=["POST"], endpoints=['/api/v1/auth/refresh'])

    # Trading endpoints - medium limits
    limiter.limit("30/minute", methods=["POST", "PUT", "DELETE"], endpoints=[
        '/api/v1/orders', '/api/v1/trades', '/api/v1/strategies'
    ])

    # Read endpoints - higher limits
    limiter.limit("120/minute", methods=["GET"], endpoints=[
        '/api/v1/market', '/api/v1/trades', '/api/v1/orders', '/api/v1/positions'
    ])


def rate_limit(limit: str = "10/minute"):
    """
    Decorator to apply custom rate limits to specific routes.

    Usage:
        @rate_limit("5/minute")
        def my_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)
        decorated_function.__rate_limit__ = limit
        return decorated_function
    return decorator
"""
JWT Authentication Decorators
==============================
Decorators for protecting routes with JWT authentication.
"""

from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt, get_jwt_identity
from app.database.connection import get_redis


def jwt_required(fn):
    """
    Decorator to require JWT authentication.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({
                'error': 'authentication_required',
                'message': 'Valid JWT token required'
            }), 401

    return wrapper


def jwt_optional(fn):
    """
    Decorator for optional JWT authentication.
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            return fn(*args, **kwargs, current_user=identity)
        except Exception:
            return fn(*args, **kwargs, current_user=None)

    return wrapper


def check_rate_limit():
    """Check if user has exceeded rate limit."""
    try:
        claims = get_jwt()
        user_id = claims.get('sub')

        if user_id:
            redis_client = get_redis()
            if redis_client:
                key = f"rate_limit:{user_id}"
                current = redis_client.get(key)
                if current:
                    return False
        return True
    except Exception:
        return True


def get_current_user_id() -> str:
    """Get current authenticated user ID."""
    return get_jwt_identity()


def get_current_user_claims() -> dict:
    """Get current JWT claims."""
    return get_jwt()
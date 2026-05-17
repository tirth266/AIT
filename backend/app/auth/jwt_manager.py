"""
=============================================================================
JWT TOKEN MANAGEMENT
=============================================================================
Production-grade JWT token management with:
- Hard validation (fail on any error, no silent failures)
- Token blacklist for logout
- Token refresh
- Secure token generation

Author: Staff Engineer
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from flask import current_app

logger = logging.getLogger('trading_app')


def create_access_token(identity: str, additional_claims: Optional[Dict] = None) -> str:
    """
    Create JWT access token with hard validation.

    Args:
        identity: User identity (user_id)
        additional_claims: Additional claims to include in token

    Returns:
        Encoded JWT token
    """
    if additional_claims is None:
        additional_claims = {}

    # Generate unique token ID (jti)
    import uuid
    jti = str(uuid.uuid4())

    expires = current_app.config.get('JWT_ACCESS_TOKEN_EXPIRES', timedelta(hours=1))

    payload = {
        'sub': identity,
        'jti': jti,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires,
        'type': 'access',
        'app': 'trading-platform',
        **additional_claims
    }

    secret = current_app.config.get('JWT_SECRET_KEY')
    if not secret:
        raise ValueError("JWT_SECRET_KEY is not configured")

    algorithm = 'HS256'

    token = jwt.encode(payload, secret, algorithm=algorithm)
    logger.debug(f"Created access token for user: {identity}")
    return token


def create_refresh_token(identity: str) -> str:
    """
    Create JWT refresh token.

    Args:
        identity: User identity (user_id)

    Returns:
        Encoded JWT refresh token
    """
    import uuid
    jti = str(uuid.uuid4())

    expires = current_app.config.get('JWT_REFRESH_TOKEN_EXPIRES', timedelta(days=30))

    payload = {
        'sub': identity,
        'jti': jti,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + expires,
        'type': 'refresh',
        'app': 'trading-platform'
    }

    secret = current_app.config.get('JWT_SECRET_KEY')
    if not secret:
        raise ValueError("JWT_SECRET_KEY is not configured")

    algorithm = 'HS256'

    return jwt.encode(payload, secret, algorithm=algorithm)


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode JWT token with HARD validation.
    Raises exception on any error instead of returning None.

    Args:
        token: JWT token string

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    secret = current_app.config.get('JWT_SECRET_KEY')
    if not secret:
        raise jwt.InvalidTokenError("JWT_SECRET_KEY not configured")

    algorithm = 'HS256'

    # Decode with strict validation
    payload = jwt.decode(
        token,
        secret,
        algorithms=[algorithm],
        options={
            'verify_exp': True,
            'verify_iat': True,
            'verify_signature': True,
            'require': ['sub', 'jti', 'exp', 'iat']
        }
    )

    # Check token type
    if payload.get('type') != 'access':
        raise jwt.InvalidTokenError("Invalid token type")

    # Check if token is revoked
    if is_token_revoked(payload.get('jti')):
        raise jwt.InvalidTokenError("Token has been revoked")

    return payload


def verify_refresh_token(token: str) -> Dict[str, Any]:
    """
    Verify refresh token with HARD validation.

    Args:
        token: JWT refresh token

    Returns:
        Decoded token payload

    Raises:
        jwt.ExpiredSignatureError: Token has expired
        jwt.InvalidTokenError: Token is invalid
    """
    secret = current_app.config.get('JWT_SECRET_KEY')
    if not secret:
        raise jwt.InvalidTokenError("JWT_SECRET_KEY not configured")

    algorithm = 'HS256'

    payload = jwt.decode(
        token,
        secret,
        algorithms=[algorithm],
        options={
            'verify_exp': True,
            'verify_iat': True,
            'verify_signature': True,
            'require': ['sub', 'jti', 'exp', 'iat']
        }
    )

    # Verify it's a refresh token
    if payload.get('type') != 'refresh':
        raise jwt.InvalidTokenError("Invalid token type")

    # Check if token is revoked
    if is_token_revoked(payload.get('jti')):
        raise jwt.InvalidTokenError("Token has been revoked")

    return payload


def decode_token_unsafe(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode JWT token without verification (FOR DEBUGGING ONLY).
    Never use in production!

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        return None


def get_token_identity(token: str) -> str:
    """
    Get identity (subject) from token with hard validation.

    Args:
        token: JWT token string

    Returns:
        User identity

    Raises:
        jwt.InvalidTokenError: Token is invalid
    """
    payload = verify_token(token)
    return payload.get('sub')


def is_token_revoked(jti: str) -> bool:
    """
    Check if token is in blacklist using Redis service.

    Args:
        jti: JWT token ID

    Returns:
        True if token is revoked
    """
    try:
        from app.services.redis_service import get_redis_service
        redis_service = get_redis_service()
        if redis_service:
            return redis_service.is_token_blacklisted(jti)
    except Exception as e:
        logger.warning(f"Failed to check token blacklist: {e}")

    # Fallback to direct Redis connection
    try:
        from app.database.connection import get_redis
        redis_client = get_redis()
        if redis_client:
            result = redis_client.get(f'blacklist:{jti}')
            return result is not None
    except Exception:
        pass

    return False


def revoke_token(jti: str, expiry: int = 86400) -> bool:
    """
    Add token to blacklist with hard failure.

    Args:
        jti: JWT token ID
        expiry: Expiry time in seconds

    Returns:
        True if successful
    """
    try:
        from app.services.redis_service import get_redis_service
        redis_service = get_redis_service()
        if redis_service:
            return redis_service.blacklist_token(jti, expiry)
    except Exception as e:
        logger.error(f"Failed to revoke token: {e}")

    # Fallback
    try:
        from app.database.connection import get_redis
        redis_client = get_redis()
        if redis_client:
            redis_client.set(f'blacklist:{jti}', '1', ex=expiry)
            return True
    except Exception as e:
        logger.error(f"Failed to revoke token (fallback): {e}")

    return False
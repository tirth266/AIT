"""
Authentication Module
=====================
Authentication utilities, JWT management, and password handling.
"""

from app.auth.jwt_manager import create_access_token, create_refresh_token, verify_token
from app.auth.decorators import jwt_required, jwt_optional
from app.auth.password import hash_password, verify_password

__all__ = [
    'create_access_token',
    'create_refresh_token',
    'verify_token',
    'jwt_required',
    'jwt_optional',
    'hash_password',
    'verify_password'
]
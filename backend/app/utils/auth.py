"""
Auth Utilities
==============
Helper functions for authentication and JWT handling.
"""

import logging
from flask import request
from flask_jwt_extended import get_jwt_identity

logger = logging.getLogger('trading_app')

def get_current_user_id() -> str:
    """
    Get the current user ID from the JWT token.
    Falls back to 'default_user' if no token or invalid token.
    """
    try:
        user_id = get_jwt_identity()
        if user_id:
            return str(user_id)
    except Exception as e:
        logger.debug(f"Could not get user_id from JWT: {e}")
    
    return "default_user"

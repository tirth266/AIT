"""
Authentication API
=================
Simple authentication for the trading platform.
"""

import logging
import os
import datetime
from flask import Blueprint, jsonify, request
import jwt

logger = logging.getLogger('auth_api')

bp = Blueprint('auth', __name__)


def generate_token(user_id: str = 'default_user') -> str:
    """Generate a JWT token for the user."""
    jwt_secret = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
    jwt_algorithm = 'HS256'

    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow(),
    }

    return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)


@bp.route('/token', methods=['GET', 'OPTIONS'])
def get_token():
    """
    Get authentication token for WebSocket connection.

    This is a simplified auth for the single-user trading platform.
    In production, this would validate credentials first.

    Returns:
        JWT token for WebSocket authentication
    """
    try:
        token = generate_token('default_user')

        logger.info('Generated auth token for default_user')

        return jsonify({
            'access_token': token,
            'token_type': 'Bearer',
            'expires_in': 86400
        }), 200

    except Exception as e:
        logger.error(f'Failed to generate token: {e}')
        return jsonify({
            'error': 'auth_error',
            'message': 'Failed to generate authentication token'
        }), 500


@bp.route('/verify', methods=['POST', 'OPTIONS'])
def verify_token():
    """Verify a JWT token."""
    data = request.get_json() or {}
    token = data.get('token')

    if not token:
        return jsonify({
            'valid': False,
            'message': 'No token provided'
        }), 400

    try:
        jwt_secret = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
        payload = jwt.decode(token, jwt_secret, algorithms=['HS256'])

        return jsonify({
            'valid': True,
            'user_id': payload.get('user_id')
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({
            'valid': False,
            'message': 'Token expired'
        }), 401
    except jwt.InvalidTokenError as e:
        return jsonify({
            'valid': False,
            'message': f'Invalid token: {str(e)}'
        }), 401


@bp.route('/refresh', methods=['POST', 'OPTIONS'])
def refresh_token():
    """Refresh an existing token."""
    data = request.get_json() or {}
    old_token = data.get('token')

    if not old_token:
        return jsonify({
            'error': 'auth_error',
            'message': 'No token provided'
        }), 400

    try:
        jwt_secret = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
        payload = jwt.decode(old_token, jwt_secret, algorithms=['HS256'])
        user_id = payload.get('user_id')

        new_token = generate_token(user_id)

        logger.info(f'Refreshed token for user {user_id}')

        return jsonify({
            'access_token': new_token,
            'token_type': 'Bearer',
            'expires_in': 86400
        }), 200

    except jwt.ExpiredSignatureError:
        return jsonify({
            'error': 'auth_error',
            'message': 'Token expired, please login again'
        }), 401
    except jwt.InvalidTokenError as e:
        return jsonify({
            'error': 'auth_error',
            'message': f'Invalid token: {str(e)}'
        }), 401
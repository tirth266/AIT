"""
Authentication API
=================
Simple authentication for the trading platform.
"""

import logging
import os
import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, decode_token

logger = logging.getLogger('auth_api')

bp = Blueprint('auth', __name__)


def generate_token(user_id: str = 'default_user') -> str:
    """Generate a JWT token for the user using flask_jwt_extended."""
    return create_access_token(identity=user_id, expires_delta=datetime.timedelta(hours=24))


@bp.route('/token', methods=['GET'])
def get_token():
    """
    Get authentication token for WebSocket connection.
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


@bp.route('/verify', methods=['POST'])
def verify_token():
    """Verify a JWT token using flask_jwt_extended."""
    data = request.get_json() or {}
    token = data.get('token')

    if not token:
        return jsonify({
            'valid': False,
            'message': 'No token provided'
        }), 400

    try:
        decoded = decode_token(token)
        return jsonify({
            'valid': True,
            'user_id': decoded.get('sub')
        }), 200

    except Exception as e:
        return jsonify({
            'valid': False,
            'message': f'Invalid token: {str(e)}'
        }), 401


@bp.route('/refresh', methods=['POST'])
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
        decoded = decode_token(old_token)
        user_id = decoded.get('sub')

        new_token = generate_token(user_id)

        logger.info(f'Refreshed token for user {user_id}')

        return jsonify({
            'access_token': new_token,
            'token_type': 'Bearer',
            'expires_in': 86400
        }), 200

    except Exception as e:
        return jsonify({
            'error': 'auth_error',
            'message': f'Invalid token: {str(e)}'
        }), 401
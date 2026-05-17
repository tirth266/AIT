"""
Authentication API
==================
Login, logout, token refresh, and 2FA endpoints.
"""

import os
import logging
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity,
    get_jwt
)

from app.auth.password import verify_password, hash_password
from app.auth.jwt_manager import revoke_token, is_token_revoked
from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('auth', __name__)


@bp.route('/register', methods=['POST'])
def register():
    """
    User registration endpoint.

    Request Body:
        {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "9876543210",
            "password": "password123",
            "pan_number": "ABCDE1234F",
            "broker": "zerodha"
        }

    Returns:
        JWT access token and user data
    """
    data = request.get_json() or {}

    full_name = data.get('full_name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()
    password = data.get('password', '')
    pan_number = data.get('pan_number', '').strip().upper() or None
    broker = data.get('broker', '').strip() or None

    errors = []
    if not full_name or len(full_name) < 2:
        errors.append('Full name must be at least 2 characters')
    if not email or '@' not in email:
        errors.append('Valid email is required')
    if not phone or len(phone) != 10 or not phone.isdigit():
        errors.append('10-digit mobile number is required')
    if not password or len(password) < 8:
        errors.append('Password must be at least 8 characters')

    if errors:
        return jsonify({
            'error': 'validation_error',
            'message': '; '.join(errors)
        }), 400

    db = get_db()
    if not db:
        return jsonify({
            'error': 'server_error',
            'message': 'Database not available'
        }), 500

    existing_user = db.users.find_one({'$or': [{'email': email}, {'phone': phone}]})
    if existing_user:
        return jsonify({
            'error': 'conflict',
            'message': 'User with this email or phone already exists'
        }), 409

    user_id = str(uuid.uuid4())
    user_doc = {
        '_id': user_id,
        'user_id': user_id,
        'full_name': full_name,
        'email': email,
        'phone': phone,
        'password_hash': hash_password(password),
        'role': 'trader',
        'twofa_enabled': False,
        'pan_number': pan_number,
        'broker': broker,
        'created_at': datetime.utcnow().isoformat(),
        'last_login': None,
        'is_active': True,
    }

    try:
        db.users.insert_one(user_doc)
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return jsonify({
            'error': 'server_error',
            'message': 'Failed to create account'
        }), 500

    access_token = create_access_token(identity=email)
    refresh_token = create_refresh_token(identity=email)

    logger.info(f"New user registered: {email}")

    return jsonify({
        'data': {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'Bearer',
            'expires_in': 3600,
            'user': {
                'id': user_id,
                'email': email,
                'full_name': full_name,
                'phone': phone,
                'role': 'trader',
                'twofa_enabled': False,
                'broker': broker,
            }
        }
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """
    Login endpoint.

    Request Body:
        {
            "email": "user@example.com",
            "password": "password123"
        }

    Returns:
        JWT access token and refresh token
    """
    data = request.get_json() or {}
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({
            'error': 'validation_error',
            'message': 'Email and password are required'
        }), 400

    db = get_db()

    owner_username = current_app.config.get('OWNER_USERNAME', 'owner')
    owner_password_hash = current_app.config.get('OWNER_PASSWORD_HASH')

    if email.lower() == owner_username.lower() and owner_password_hash:
        if verify_password(password, owner_password_hash):
            access_token = create_access_token(identity=owner_username)
            refresh_token = create_refresh_token(identity=owner_username)
            logger.info(f"Owner logged in successfully")
            return jsonify({
                'data': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': 3600,
                    'user': {
                        'id': 'owner',
                        'email': owner_username,
                        'full_name': 'Trading Owner',
                        'role': 'admin'
                    }
                }
            }), 200
        else:
            logger.warning(f"Failed login attempt for owner")
            return jsonify({
                'error': 'invalid_credentials',
                'message': 'Invalid credentials'
            }), 401

    if db:
        user = db.users.find_one({'email': email, 'is_active': True})
        if user and verify_password(password, user.get('password_hash', '')):
            access_token = create_access_token(identity=user['email'])
            refresh_token = create_refresh_token(identity=user['email'])

            db.users.update_one(
                {'_id': user['_id']},
                {'$set': {'last_login': datetime.utcnow().isoformat()}}
            )

            logger.info(f"User logged in: {email}")

            return jsonify({
                'data': {
                    'access_token': access_token,
                    'refresh_token': refresh_token,
                    'token_type': 'Bearer',
                    'expires_in': 3600,
                    'user': {
                        'id': user.get('user_id') or str(user['_id']),
                        'email': user['email'],
                        'full_name': user.get('full_name', ''),
                        'phone': user.get('phone'),
                        'role': user.get('role', 'trader'),
                        'twofa_enabled': user.get('twofa_enabled', False),
                        'broker': user.get('broker'),
                    }
                }
            }), 200

    logger.warning(f"Failed login attempt for: {email}")
    return jsonify({
        'error': 'invalid_credentials',
        'message': 'Invalid email or password'
    }), 401


@bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token.

    Returns:
        New access token
    """
    identity = get_jwt_identity()

    access_token = create_access_token(identity=identity)

    return jsonify({
        'access_token': access_token,
        'token_type': 'Bearer',
        'expires_in': 3600
    }), 200


@bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout and revoke current token.

    Returns:
        Success message
    """
    jti = get_jwt().get('jti')
    revoke_token(jti)

    logger.info(f"User logged out")

    return jsonify({
        'message': 'Logged out successfully'
    }), 200


@bp.route('/verify', methods=['GET'])
@jwt_required()
def verify():
    """
    Verify JWT token validity.

    Returns:
        User info if token is valid
    """
    identity = get_jwt_identity()
    db = get_db()

    user_data = {
        'email': identity,
        'role': 'admin'
    }

    if db:
        user = db.users.find_one({'email': identity})
        if user:
            user_data = {
                'id': user.get('user_id') or str(user['_id']),
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'phone': user.get('phone'),
                'role': user.get('role', 'trader'),
                'twofa_enabled': user.get('twofa_enabled', False),
                'broker': user.get('broker'),
            }
        elif identity == current_app.config.get('OWNER_USERNAME', 'owner'):
            user_data = {
                'id': 'owner',
                'email': identity,
                'full_name': 'Trading Owner',
                'role': 'admin'
            }

    return jsonify({
        'valid': True,
        'user': user_data
    }), 200


@bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get user profile.

    Returns:
        User profile data
    """
    identity = get_jwt_identity()
    db = get_db()

    user_data = {
        'email': identity,
        'role': 'admin'
    }

    if db:
        user = db.users.find_one({'email': identity})
        if user:
            user_data = {
                'id': user.get('user_id') or str(user['_id']),
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'phone': user.get('phone'),
                'role': user.get('role', 'trader'),
                'twofa_enabled': user.get('twofa_enabled', False),
                'broker': user.get('broker'),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login'),
            }
        elif identity == current_app.config.get('OWNER_USERNAME', 'owner'):
            user_data = {
                'id': 'owner',
                'email': identity,
                'full_name': 'Trading Owner',
                'role': 'admin'
            }

    return jsonify({
        'data': user_data
    }), 200


@bp.route('/2fa/setup', methods=['POST'])
@jwt_required()
def setup_2fa():
    """
    Setup 2FA for the owner account.

    Returns:
        2FA secret for authenticator app
    """
    import pyotp

    identity = get_jwt_identity()
    secret = pyotp.random_base32()

    db = get_db()
    if db:
        db.user.update_one(
            {'username': identity},
            {'$set': {'twofa_secret': secret}}
        )

    provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=identity,
        issuer_name="Trading Platform"
    )

    return jsonify({
        'secret': secret,
        'provisioning_uri': provisioning_uri
    }), 200


@bp.route('/2fa/verify', methods=['POST'])
@jwt_required()
def verify_2fa():
    """
    Verify 2FA code.

    Request Body:
        {
            "code": "123456"
        }

    Returns:
        Success message
    """
    import pyotp

    data = request.get_json() or {}
    code = data.get('code')

    if not code:
        return jsonify({
            'error': 'validation_error',
            'message': 'Code is required'
        }), 400

    identity = get_jwt_identity()
    db = get_db()

    secret = None
    if db:
        user = db.user.find_one({'username': identity})
        secret = user.get('twofa_secret') if user else None

    if not secret:
        return jsonify({
            'error': 'not_found',
            'message': '2FA not configured'
        }), 404

    totp = pyotp.TOTP(secret)
    if not totp.verify(code):
        return jsonify({
            'error': 'invalid_code',
            'message': 'Invalid 2FA code'
        }), 401

    return jsonify({
        'message': '2FA verified successfully'
    }), 200


@bp.route('/2fa/disable', methods=['POST'])
@jwt_required()
def disable_2fa():
    """
    Disable 2FA.

    Request Body:
        {
            "code": "123456"
        }

    Returns:
        Success message
    """
    import pyotp

    data = request.get_json() or {}
    code = data.get('code')

    if not code:
        return jsonify({
            'error': 'validation_error',
            'message': 'Code is required'
        }), 400

    identity = get_jwt_identity()
    db = get_db()

    secret = None
    if db:
        user = db.user.find_one({'username': identity})
        secret = user.get('twofa_secret') if user else None

    if not secret:
        return jsonify({
            'error': 'not_found',
            'message': '2FA not configured'
        }), 404

    totp = pyotp.TOTP(secret)
    if not totp.verify(code):
        return jsonify({
            'error': 'invalid_code',
            'message': 'Invalid 2FA code'
        }), 401

    if db:
        db.user.update_one(
            {'username': identity},
            {'$set': {'twofa_secret': None}}
        )

    logger.info("2FA disabled")

    return jsonify({
        'message': '2FA disabled successfully'
    }), 200
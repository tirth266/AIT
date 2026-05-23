"""
Settings API
============
User settings and preferences endpoints.
"""

import logging
from flask import Blueprint, request, jsonify

from app.database.connection import get_db
from app.utils.encryption import encrypt_value, decrypt_value

logger = logging.getLogger('trading_app')

bp = Blueprint('settings', __name__)


@bp.route('', methods=['GET'])
def get_settings():
    """
    Get all settings.

    Returns:
        List of settings
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error'}), 500

    settings = list(db.settings.find({}, {'value_encrypted': 0}))

    for setting in settings:
        setting['_id'] = str(setting['_id'])
        if 'updated_at' in setting:
            setting['updated_at'] = str(setting['updated_at'])

    return jsonify({'settings': settings}), 200


@bp.route('/<key>', methods=['GET'])
def get_setting(key):
    """
    Get a specific setting.

    Returns:
        Setting value
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error'}), 500

    setting = db.settings.find_one({'key': key})

    if not setting:
        return jsonify({
            'error': 'not_found',
            'message': f'Setting {key} not found'
        }), 404

    value = setting.get('value')
    if setting.get('value_encrypted'):
        value = decrypt_value(setting['value_encrypted'])

    return jsonify({
        'key': key,
        'value': value,
        'category': setting.get('category', 'general')
    }), 200


@bp.route('', methods=['PUT'])
def update_settings():
    """
    Update multiple settings.

    Request Body:
        {
            "key": "value",
            ...
        }

    Returns:
        Updated settings
    """
    data = request.get_json() or {}

    if not data:
        return jsonify({
            'error': 'validation_error',
            'message': 'No settings provided'
        }), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error'}), 500

    from datetime import datetime
    updated = []

    for key, value in data.items():
        encrypted_value = None
        if key in ['telegram_bot_token', 'telegram_chat_id', 'api_key', 'api_secret']:
            encrypted_value = encrypt_value(str(value))

        db.settings.update_one(
            {'key': key},
            {
                '$set': {
                    'value': str(value) if not encrypted_value else None,
                    'value_encrypted': encrypted_value,
                    'updated_at': datetime.utcnow()
                }
            },
            upsert=True
        )
        updated.append(key)

    logger.info(f"Settings updated: {updated}")

    return jsonify({
        'message': 'Settings updated successfully',
        'updated': updated
    }), 200


@bp.route('/<key>', methods=['PUT'])
def update_setting(key):
    """
    Update a specific setting.

    Request Body:
        {
            "value": "..."
        }

    Returns:
        Updated setting
    """
    data = request.get_json() or {}
    value = data.get('value')

    if value is None:
        return jsonify({
            'error': 'validation_error',
            'message': 'Value is required'
        }), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error'}), 500

    encrypted_value = None
    if key in ['telegram_bot_token', 'telegram_chat_id']:
        encrypted_value = encrypt_value(str(value))

    db.settings.update_one(
        {'key': key},
        {
            '$set': {
                'value': str(value) if not encrypted_value else None,
                'value_encrypted': encrypted_value,
                'updated_at': __import__('datetime').datetime.utcnow()
            }
        },
        upsert=True
    )

    logger.info(f"Setting updated: {key}")

    return jsonify({
        'key': key,
        'value': value,
        'message': 'Setting updated successfully'
    }), 200


@bp.route('/reset-paper-balance', methods=['POST'])
def reset_paper_balance():
    """
    Reset paper trading balance.

    Request Body:
        {
            "balance": 10000
        }

    Returns:
        Reset confirmation
    """
    data = request.get_json() or {}
    balance = data.get('balance', 10000)

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error'}), 500

    db.settings.update_one(
        {'key': 'paper_balance'},
        {'$set': {
            'value': str(balance),
            'updated_at': __import__('datetime').datetime.utcnow()
        }},
        upsert=True
    )

    logger.info(f"Paper balance reset to: {balance}")

    return jsonify({
        'message': 'Paper balance reset successfully',
        'balance': balance
    }), 200


@bp.route('/risk', methods=['GET'])
def get_risk_settings():
    """
    Get risk management settings.

    Returns:
        Risk settings
    """
    from flask import current_app

    default_settings = {
        'max_daily_loss_percent': current_app.config.get('RISK_MAX_DAILY_LOSS_PERCENT', 5.0),
        'risk_per_trade_percent': current_app.config.get('RISK_PER_TRADE_PERCENT', 1.0),
        'max_open_positions': current_app.config.get('RISK_MAX_OPEN_POSITIONS', 3),
        'max_consecutive_losses': current_app.config.get('RISK_MAX_CONSECUTIVE_LOSSES', 3),
        'max_drawdown_percent': current_app.config.get('RISK_MAX_DRAWDOWN_PERCENT', 10.0),
        'trade_cooldown_minutes': current_app.config.get('RISK_TRADE_COOLDOWN_MINUTES', 5)
    }

    db = get_db()
    if db is not None:
        settings = list(db.settings.find({'key': {'$regex': '^risk_'}}))
        for s in settings:
            key = s['key'].replace('risk_', '')
            if s.get('value'):
                try:
                    default_settings[key] = float(s['value'])
                except (ValueError, TypeError):
                    pass

    return jsonify({'risk_settings': default_settings}), 200


@bp.route('/risk', methods=['PUT'])
def update_risk_settings():
    """
    Update risk management settings.

    Request Body:
        {
            "max_daily_loss_percent": 5.0,
            "risk_per_trade_percent": 1.0,
            ...
        }

    Returns:
        Updated settings
    """
    data = request.get_json() or {}

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error'}), 500

    from datetime import datetime
    allowed_keys = [
        'max_daily_loss_percent',
        'risk_per_trade_percent',
        'max_open_positions',
        'max_consecutive_losses',
        'max_drawdown_percent',
        'trade_cooldown_minutes'
    ]

    for key in allowed_keys:
        if key in data:
            db.settings.update_one(
                {'key': f'risk_{key}'},
                {'$set': {
                    'value': str(data[key]),
                    'updated_at': datetime.utcnow()
                }},
                upsert=True
            )

    logger.info(f"Risk settings updated: {list(data.keys())}")

    return jsonify({
        'message': 'Risk settings updated successfully',
        'updated': list(data.keys())
    }), 200
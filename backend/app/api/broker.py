"""
Broker API
==========
Broker connection and management endpoints.
"""

import logging
from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.database.connection import get_db
from app.utils.encryption import encrypt_value, decrypt_value
from app.broker_integrations.factory import BrokerFactory

logger = logging.getLogger('trading_app')

bp = Blueprint('broker', __name__)


@bp.route('/connect', methods=['POST'])
@jwt_required()
def connect_broker():
    """
    Connect a broker.

    Request Body:
        {
            "broker": "binance",
            "api_key": "...",
            "api_secret": "...",
            "testnet": true
        }

    Returns:
        Connection status and balance
    """
    data = request.get_json() or {}
    broker_name = data.get('broker')
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')
    testnet = data.get('testnet', True)

    if not broker_name or not api_key or not api_secret:
        return jsonify({
            'error': 'validation_error',
            'message': 'broker, api_key, and api_secret are required'
        }), 400

    try:
        broker = BrokerFactory.get_broker(broker_name, {
            'api_key': api_key,
            'api_secret': api_secret,
            'testnet': testnet
        })
        balance = broker.get_balance()
    except Exception as e:
        logger.error(f"Broker connection failed: {e}")
        return jsonify({
            'error': 'broker_error',
            'message': f'Failed to connect to {broker_name}'
        }), 502

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    encrypted_key = encrypt_value(api_key)
    encrypted_secret = encrypt_value(api_secret)

    broker_doc = {
        'broker_name': broker_name,
        'broker_type': 'spot',
        'api_key_encrypted': encrypted_key,
        'api_secret_encrypted': encrypted_secret,
        'testnet_enabled': testnet,
        'is_connected': True,
        'last_connection_test': __import__('datetime').datetime.utcnow(),
        'created_at': __import__('datetime').datetime.utcnow()
    }

    db.brokers.update_one(
        {'broker_name': broker_name},
        {'$set': broker_doc},
        upsert=True
    )

    logger.info(f"Broker connected: {broker_name}")

    return jsonify({
        'broker': broker_name,
        'is_connected': True,
        'balance': balance,
        'testnet': testnet
    }), 200


@bp.route('/status', methods=['GET'])
@jwt_required()
def get_broker_status():
    """
    Get broker connection status.

    Returns:
        List of configured brokers
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    brokers = list(db.brokers.find({}, {
        'api_key_encrypted': 0,
        'api_secret_encrypted': 0
    }))

    for broker in brokers:
        broker['_id'] = str(broker['_id'])

    return jsonify({'brokers': brokers}), 200


@bp.route('/disconnect', methods=['DELETE'])
@jwt_required()
def disconnect_broker():
    """
    Disconnect a broker.

    Request Body:
        {
            "broker": "binance"
        }

    Returns:
        Disconnection status
    """
    data = request.get_json() or {}
    broker_name = data.get('broker')

    if not broker_name:
        return jsonify({
            'error': 'validation_error',
            'message': 'broker is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    db.brokers.update_one(
        {'broker_name': broker_name},
        {'$set': {
            'is_connected': False,
            'disconnected_at': __import__('datetime').datetime.utcnow()
        }}
    )

    logger.info(f"Broker disconnected: {broker_name}")

    return jsonify({
        'broker': broker_name,
        'is_connected': False,
        'message': f'Disconnected from {broker_name}'
    }), 200


@bp.route('/balance', methods=['GET'])
@jwt_required()
def get_balance():
    """
    Get account balance from broker.

    Query Parameters:
        - broker: broker name (optional, defaults to all)
        - mode: paper or live

    Returns:
        Balance information
    """
    broker_name = request.args.get('broker')
    mode = request.args.get('mode', 'paper')

    if mode == 'paper':
        db = get_db()
        if db:
            setting = db.settings.find_one({'key': 'paper_balance'})
            balance = float(setting['value']) if setting else 10000.0

            return jsonify({
                'mode': 'paper',
                'balance': balance,
                'available': balance,
                'equity': balance,
                'currency': 'USDT'
            }), 200

    if not broker_name:
        return jsonify({
            'error': 'validation_error',
            'message': 'broker is required for live mode'
        }), 400

    try:
        broker = BrokerFactory.get_broker(broker_name)
        balance = broker.get_balance()
    except Exception as e:
        logger.error(f"Failed to get balance: {e}")
        return jsonify({
            'error': 'broker_error',
            'message': f'Failed to get balance from {broker_name}'
        }), 502

    return jsonify({
        'mode': 'live',
        'broker': broker_name,
        'balance': balance
    }), 200


@bp.route('/test', methods=['POST'])
@jwt_required()
def test_connection():
    """
    Test broker connection.

    Request Body:
        {
            "broker": "binance",
            "api_key": "...",
            "api_secret": "..."
        }

    Returns:
        Test result
    """
    data = request.get_json() or {}
    broker_name = data.get('broker')
    api_key = data.get('api_key')
    api_secret = data.get('api_secret')

    if not broker_name or not api_key or not api_secret:
        return jsonify({
            'error': 'validation_error',
            'message': 'broker, api_key, and api_secret are required'
        }), 400

    try:
        broker = BrokerFactory.get_broker(broker_name, {
            'api_key': api_key,
            'api_secret': api_secret,
            'testnet': True
        })
        broker.get_balance()
    except Exception as e:
        logger.error(f"Broker test failed: {e}")
        return jsonify({
            'broker': broker_name,
            'is_connected': False,
            'error': str(e)
        }), 400

    return jsonify({
        'broker': broker_name,
        'is_connected': True,
        'message': 'Connection successful'
    }), 200
"""
Strategy API
============
Strategy CRUD and management endpoints.
"""

import logging
from bson import ObjectId
from flask import Blueprint, request, jsonify, current_app

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('strategies', __name__)


@bp.route('', methods=['GET'])
def list_strategies():
    """
    List all strategies.

    Query Parameters:
        - is_active: Filter by active status
        - mode: Filter by paper/live mode
        - symbol: Filter by symbol
        - limit: Number of results (default 50)
        - skip: Number to skip (default 0)

    Returns:
        List of strategies
    """
    user_id = "default_user"
    is_active = request.args.get('is_active')
    mode = request.args.get('mode')
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))

    query = {}
    if is_active is not None:
        query['is_active'] = is_active.lower() == 'true'
    if mode:
        query['mode'] = mode
    if symbol:
        query['symbol'] = symbol

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    strategies = list(db.strategies.find(query).skip(skip).limit(limit))
    total = db.strategies.count_documents(query)

    for strategy in strategies:
        strategy['_id'] = str(strategy['_id'])
        if 'created_at' in strategy:
            strategy['created_at'] = strategy['created_at'].isoformat() if hasattr(strategy['created_at'], 'isoformat') else str(strategy['created_at'])

    return jsonify({
        'strategies': strategies,
        'total': total,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('', methods=['POST'])
def create_strategy():
    """
    Create a new strategy.

    Request Body:
        {
            "strategy_name": "RSI Momentum",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "mode": "paper",
            "broker": "binance",
            "indicators": [...],
            "entry_conditions": [...],
            "exit_conditions": [...],
            "risk_settings": {...}
        }

    Returns:
        Created strategy ID
    """
    data = request.get_json() or {}

    required_fields = ['strategy_name', 'symbol', 'timeframe']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'error': 'validation_error',
                'message': f'{field} is required'
            }), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    strategy = {
        'strategy_name': data['strategy_name'],
        'symbol': data['symbol'],
        'timeframe': data['timeframe'],
        'mode': data.get('mode', 'paper'),
        'broker': data.get('broker', 'binance'),
        'indicators': data.get('indicators', []),
        'entry_conditions': data.get('entry_conditions', []),
        'exit_conditions': data.get('exit_conditions', []),
        'risk_settings': data.get('risk_settings', {
            'stop_loss_percent': 1.0,
            'take_profit_percent': 2.0,
            'trailing_stop_enabled': False,
            'position_size_type': 'fixed',
            'position_size_percent': 10.0
        }),
        'execution_settings': data.get('execution_settings', {
            'order_type': 'market',
            'allow_partial_fills': False,
            'retry_on_failure': True,
            'max_retries': 3
        }),
        'is_active': False,
        'created_at': __import__('datetime').datetime.utcnow(),
        'updated_at': __import__('datetime').datetime.utcnow()
    }

    result = db.strategies.insert_one(strategy)
    logger.info(f"Strategy created: {result.inserted_id}")

    return jsonify({
        'id': str(result.inserted_id),
        'strategy_name': strategy['strategy_name'],
        'created_at': strategy['created_at'].isoformat()
    }), 201


@bp.route('/<strategy_id>', methods=['GET'])
def get_strategy(strategy_id):
    """
    Get a specific strategy.

    Returns:
        Strategy details
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid strategy ID'
        }), 400

    if not strategy:
        return jsonify({
            'error': 'not_found',
            'message': 'Strategy not found'
        }), 404

    strategy['_id'] = str(strategy['_id'])

    return jsonify(strategy), 200


@bp.route('/<strategy_id>', methods=['PUT'])
def update_strategy(strategy_id):
    """
    Update a strategy.

    Returns:
        Updated strategy
    """
    data = request.get_json() or {}

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        result = db.strategies.update_one(
            {'_id': ObjectId(strategy_id)},
            {'$set': {
                **data,
                'updated_at': __import__('datetime').datetime.utcnow()
            }}
        )
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid strategy ID'
        }), 400

    if result.matched_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Strategy not found'
        }), 404

    logger.info(f"Strategy updated: {strategy_id}")

    return jsonify({
        'message': 'Strategy updated successfully'
    }), 200


@bp.route('/<strategy_id>', methods=['DELETE'])
def delete_strategy(strategy_id):
    """
    Delete a strategy.

    Returns:
        Success message
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        result = db.strategies.delete_one({'_id': ObjectId(strategy_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid strategy ID'
        }), 400

    if result.deleted_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Strategy not found'
        }), 404

    logger.info(f"Strategy deleted: {strategy_id}")

    return jsonify({
        'message': 'Strategy deleted successfully'
    }), 200


@bp.route('/<strategy_id>/clone', methods=['POST'])
def clone_strategy(strategy_id):
    """
    Clone a strategy.

    Returns:
        New strategy ID
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid strategy ID'
        }), 400

    if not strategy:
        return jsonify({
            'error': 'not_found',
            'message': 'Strategy not found'
        }), 404

    data = request.get_json() or {}
    new_name = data.get('strategy_name', f"{strategy['strategy_name']} (Copy)")

    new_strategy = dict(strategy)
    new_strategy.pop('_id', None)
    new_strategy['strategy_name'] = new_name
    new_strategy['is_active'] = False
    new_strategy['created_at'] = __import__('datetime').datetime.utcnow()
    new_strategy['updated_at'] = __import__('datetime').datetime.utcnow()

    result = db.strategies.insert_one(new_strategy)

    logger.info(f"Strategy cloned: {strategy_id} -> {result.inserted_id}")

    return jsonify({
        'id': str(result.inserted_id),
        'strategy_name': new_name,
        'created_at': new_strategy['created_at'].isoformat()
    }), 201


@bp.route('/<strategy_id>/toggle', methods=['POST'])
def toggle_strategy(strategy_id):
    """
    Toggle strategy active status.

    Returns:
        Updated status
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid strategy ID'
        }), 400

    if not strategy:
        return jsonify({
            'error': 'not_found',
            'message': 'Strategy not found'
        }), 404

    new_status = not strategy.get('is_active', False)

    db.strategies.update_one(
        {'_id': ObjectId(strategy_id)},
        {'$set': {
            'is_active': new_status,
            'updated_at': __import__('datetime').datetime.utcnow()
        }}
    )

    logger.info(f"Strategy {strategy_id} toggled: {new_status}")

    return jsonify({
        'is_active': new_status,
        'message': f"Strategy {'activated' if new_status else 'deactivated'}"
    }), 200
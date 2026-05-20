"""
Bot API
=======
Bot control and status endpoints.
"""

import logging
from bson import ObjectId
from flask import Blueprint, request, jsonify

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('bot', __name__)


@bp.route('/start', methods=['POST'])
def start_bot():
    """
    Start a trading bot.

    Request Body:
        {
            "strategy_id": "..."
        }

    Returns:
        Bot started status
    """
    data = request.get_json() or {}
    strategy_id = data.get('strategy_id')

    if not strategy_id:
        return jsonify({
            'error': 'validation_error',
            'message': 'strategy_id is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

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

    db.strategies.update_one(
        {'_id': ObjectId(strategy_id)},
        {'$set': {
            'is_active': True,
            'started_at': __import__('datetime').datetime.utcnow()
        }}
    )

    logger.info(f"Bot started for strategy: {strategy_id}")

    from app.celery_tasks.trading_tasks import schedule_strategy_evaluation
    schedule_strategy_evaluation.delay(strategy_id)

    return jsonify({
        'status': 'started',
        'strategy_id': strategy_id,
        'mode': strategy.get('mode', 'paper'),
        'message': f"Bot started in {strategy.get('mode', 'paper')} trading mode"
    }), 200


@bp.route('/stop', methods=['POST'])
def stop_bot():
    """
    Stop a trading bot.

    Request Body:
        {
            "strategy_id": "..."
        }

    Returns:
        Bot stopped status
    """
    data = request.get_json() or {}
    strategy_id = data.get('strategy_id')

    if not strategy_id:
        return jsonify({
            'error': 'validation_error',
            'message': 'strategy_id is required'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

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

    db.strategies.update_one(
        {'_id': ObjectId(strategy_id)},
        {'$set': {
            'is_active': False,
            'stopped_at': __import__('datetime').datetime.utcnow()
        }}
    )

    logger.info(f"Bot stopped for strategy: {strategy_id}")

    return jsonify({
        'status': 'stopped',
        'strategy_id': strategy_id,
        'message': 'Bot stopped'
    }), 200


@bp.route('/status', methods=['GET'])
def get_bot_status():
    """
    Get status of all bots.

    Returns:
        List of bot statuses
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    active_strategies = list(db.strategies.find({'is_active': True}))

    bots = []
    for strategy in active_strategies:
        trades_today = 0
        pnl_today = 0

        today_start = __import__('datetime').datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        trades = list(db.trades.find({
            'strategy_id': strategy['_id'],
            'mode': strategy.get('mode', 'paper'),
            'created_at': {'$gte': today_start}
        }))
        trades_today = len(trades)
        pnl_today = sum(t.get('pnl', 0) for t in trades)

        bots.append({
            'strategy_id': str(strategy['_id']),
            'strategy_name': strategy.get('strategy_name'),
            'symbol': strategy.get('symbol'),
            'timeframe': strategy.get('timeframe'),
            'mode': strategy.get('mode', 'paper'),
            'status': 'running',
            'trades_today': trades_today,
            'pnl_today': round(pnl_today, 2),
            'started_at': str(strategy.get('started_at', ''))
        })

    return jsonify({'bots': bots}), 200


@bp.route('/mode', methods=['POST'])
def switch_mode():
    """
    Switch between paper and live trading mode.

    Request Body:
        {
            "mode": "paper" or "live"
        }

    Returns:
        Current mode
    """
    data = request.get_json() or {}
    mode = data.get('mode')

    if mode not in ['paper', 'live']:
        return jsonify({
            'error': 'validation_error',
            'message': 'Mode must be paper or live'
        }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    db.settings.update_one(
        {'key': 'trading_mode'},
        {'$set': {'value': mode, 'updated_at': __import__('datetime').datetime.utcnow()}},
        upsert=True
    )

    logger.info(f"Trading mode switched to: {mode}")

    return jsonify({
        'current_mode': mode,
        'message': f"Switched to {mode} trading mode"
    }), 200


@bp.route('/pause', methods=['POST'])
def pause_all_bots():
    """
    Pause all running bots (circuit breaker).

    Request Body:
        {
            "reason": "manual" | "consecutive_losses" | "max_drawdown" | "daily_loss"
        }

    Returns:
        Paused bots count
    """
    data = request.get_json() or {}
    reason = data.get('reason', 'manual')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    result = db.strategies.update_many(
        {'is_active': True},
        {'$set': {
            'is_active': False,
            'paused_at': __import__('datetime').datetime.utcnow(),
            'pause_reason': reason
        }}
    )

    logger.warning(f"All bots paused: {reason}")

    return jsonify({
        'message': f'Paused {result.modified_count} bots',
        'reason': reason
    }), 200


@bp.route('/resume', methods=['POST'])
def resume_bots():
    """
    Resume paused bots.

    Request Body:
        {
            "strategy_ids": ["..."] // optional, resume specific bots
        }

    Returns:
        Resumed bots count
    """
    data = request.get_json() or {}
    strategy_ids = data.get('strategy_ids')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    query = {'pause_reason': {'$exists': True}}
    if strategy_ids:
        try:
            query['_id'] = {'$in': [ObjectId(sid) for sid in strategy_ids]}
        except Exception:
            pass

    result = db.strategies.update_many(
        query,
        {'$unset': {'paused_at': '', 'pause_reason': ''}, '$set': {'is_active': True}}
    )

    logger.info(f"Resumed {result.modified_count} bots")

    return jsonify({
        'message': f'Resumed {result.modified_count} bots'
    }), 200
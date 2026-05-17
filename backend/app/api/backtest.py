"""
Backtest API
============
Backtesting endpoints and results.
"""

import logging
from bson import ObjectId
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('backtest', __name__)


@bp.route('/run', methods=['POST'])
@jwt_required()
def run_backtest():
    """
    Start a backtest.

    Request Body:
        {
            "strategy_id": "...",
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "start_date": "2023-01-01",
            "end_date": "2023-12-31",
            "initial_capital": 10000
        }

    Returns:
        Backtest ID and status
    """
    data = request.get_json() or {}

    required_fields = ['strategy_id', 'symbol', 'timeframe', 'start_date', 'end_date']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'error': 'validation_error',
                'message': f'{field} is required'
            }), 400

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    strategy_id = data['strategy_id']
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

    backtest = {
        'strategy_id': ObjectId(strategy_id),
        'strategy_name': strategy.get('strategy_name'),
        'symbol': data['symbol'],
        'timeframe': data['timeframe'],
        'start_date': datetime.fromisoformat(data['start_date']),
        'end_date': datetime.fromisoformat(data['end_date']),
        'initial_capital': data.get('initial_capital', 10000),
        'final_capital': None,
        'total_return': None,
        'total_trades': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'win_rate': 0,
        'sharpe_ratio': None,
        'max_drawdown': None,
        'profit_factor': None,
        'status': 'queued',
        'progress': 0,
        'error_message': None,
        'created_at': datetime.utcnow()
    }

    result = db.backtests.insert_one(backtest)
    backtest_id = str(result.inserted_id)

    from app.celery_tasks.backtest_tasks import run_backtest
    run_backtest.delay(backtest_id)

    logger.info(f"Backtest started: {backtest_id}")

    return jsonify({
        'backtest_id': backtest_id,
        'status': 'queued',
        'message': 'Backtest started in background'
    }), 202


@bp.route('/<backtest_id>', methods=['GET'])
@jwt_required()
def get_backtest_status(backtest_id):
    """
    Get backtest status and progress.

    Returns:
        Backtest status
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    try:
        backtest = db.backtests.find_one({'_id': ObjectId(backtest_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid backtest ID'
        }), 400

    if not backtest:
        return jsonify({
            'error': 'not_found',
            'message': 'Backtest not found'
        }), 404

    backtest['_id'] = str(backtest['_id'])
    if 'created_at' in backtest:
        backtest['created_at'] = str(backtest['created_at'])
    if 'completed_at' in backtest:
        backtest['completed_at'] = str(backtest['completed_at'])

    if 'strategy_id' in backtest:
        backtest['strategy_id'] = str(backtest['strategy_id'])

    return jsonify({
        'id': backtest['_id'],
        'status': backtest.get('status'),
        'progress': backtest.get('progress', 0),
        'error_message': backtest.get('error_message')
    }), 200


@bp.route('/<backtest_id>/results', methods=['GET'])
@jwt_required()
def get_backtest_results(backtest_id):
    """
    Get backtest results.

    Returns:
        Detailed backtest results
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    try:
        backtest = db.backtests.find_one({'_id': ObjectId(backtest_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid backtest ID'
        }), 400

    if not backtest:
        return jsonify({
            'error': 'not_found',
            'message': 'Backtest not found'
        }), 404

    if backtest.get('status') != 'completed':
        return jsonify({
            'error': 'not_completed',
            'message': f'Backtest is {backtest.get("status")}',
            'status': backtest.get('status'),
            'progress': backtest.get('progress', 0)
        }), 400

    result = {
        'id': str(backtest['_id']),
        'strategy_id': str(backtest.get('strategy_id')),
        'strategy_name': backtest.get('strategy_name'),
        'symbol': backtest.get('symbol'),
        'timeframe': backtest.get('timeframe'),
        'start_date': str(backtest.get('start_date')),
        'end_date': str(backtest.get('end_date')),
        'initial_capital': backtest.get('initial_capital'),
        'final_capital': backtest.get('final_capital'),
        'total_return': backtest.get('total_return'),
        'total_trades': backtest.get('total_trades'),
        'winning_trades': backtest.get('winning_trades'),
        'losing_trades': backtest.get('losing_trades'),
        'win_rate': backtest.get('win_rate'),
        'sharpe_ratio': backtest.get('sharpe_ratio'),
        'max_drawdown': backtest.get('max_drawdown'),
        'profit_factor': backtest.get('profit_factor'),
        'avg_trade_duration': backtest.get('avg_trade_duration'),
        'status': backtest.get('status'),
        'completed_at': str(backtest.get('completed_at')) if backtest.get('completed_at') else None
    }

    if 'trades' in backtest:
        result['trades'] = backtest['trades'][:50]

    if 'equity_curve' in backtest:
        result['equity_curve'] = backtest['equity_curve']

    return jsonify(result), 200


@bp.route('/history', methods=['GET'])
@jwt_required()
def list_backtests():
    """
    List backtest history.

    Query Parameters:
        - limit: Number of results
        - skip: Number to skip
        - status: Filter by status

    Returns:
        List of backtests
    """
    limit = int(request.args.get('limit', 20))
    skip = int(request.args.get('skip', 0))
    status = request.args.get('status')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    query = {}
    if status:
        query['status'] = status

    backtests = list(db.backtests.find(query).sort('created_at', -1).skip(skip).limit(limit))
    total = db.backtests.count_documents(query)

    for bt in backtests:
        bt['_id'] = str(bt['_id'])
        if 'created_at' in bt:
            bt['created_at'] = str(bt['created_at'])
        if 'completed_at' in bt:
            bt['completed_at'] = str(bt['completed_at'])
        if 'strategy_id' in bt:
            bt['strategy_id'] = str(bt['strategy_id'])

    return jsonify({
        'backtests': backtests,
        'total': total,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('/<backtest_id>', methods=['DELETE'])
@jwt_required()
def delete_backtest(backtest_id):
    """
    Delete a backtest.

    Returns:
        Success message
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    try:
        result = db.backtests.delete_one({'_id': ObjectId(backtest_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid backtest ID'
        }), 400

    if result.deleted_count == 0:
        return jsonify({
            'error': 'not_found',
            'message': 'Backtest not found'
        }), 404

    return jsonify({
        'message': 'Backtest deleted successfully'
    }), 200
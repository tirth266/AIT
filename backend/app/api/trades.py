"""
Trade API
=========
Trade management and history endpoints.
"""

import logging
from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.database.connection import get_db
from app.utils.auth import get_current_user_id
from app.paper_trading.simulator import PaperTradingSimulator

logger = logging.getLogger('trading_app')

bp = Blueprint('trades', __name__)


@bp.route('', methods=['GET'])
@jwt_required(optional=True)
def list_trades():
    """
    List all trades for the user.
    """
    user_id = get_current_user_id()
    mode = request.args.get('mode')
    status = request.args.get('status')
    symbol = request.args.get('symbol')
    strategy_id = request.args.get('strategy_id')
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')

    query = {'user_id': user_id}
    if mode:
        query['mode'] = mode
    if status:
        query['status'] = status.upper()
    if symbol:
        query['symbol'] = symbol
    if strategy_id:
        try:
            query['strategy_id'] = ObjectId(strategy_id)
        except Exception:
            pass

    if start_date or end_date:
        query['entry_time'] = {}
        from datetime import datetime
        if start_date:
            query['entry_time']['$gte'] = datetime.fromisoformat(start_date)
        if end_date:
            query['entry_time']['$lte'] = datetime.fromisoformat(end_date)

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    trades = list(db.trades.find(query).sort('created_at', -1).skip(skip).limit(limit))
    total = db.trades.count_documents(query)

    for trade in trades:
        trade['_id'] = str(trade['_id'])
        if 'created_at' in trade:
            trade['created_at'] = str(trade['created_at'])
        if 'entry_time' in trade:
            trade['entry_time'] = str(trade['entry_time'])
        if 'exit_time' in trade:
            trade['exit_time'] = str(trade['exit_time'])

    return jsonify({
        'trades': trades,
        'total': total,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('/active', methods=['GET'])
@jwt_required(optional=True)
def get_active_trades():
    """
    Get active (open) trades for the user.
    """
    user_id = get_current_user_id()
    mode = request.args.get('mode', 'paper')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    positions = list(db.positions.find({'user_id': user_id, 'status': 'open', 'mode': mode}))

    for position in positions:
        position['_id'] = str(position['_id'])
        if 'created_at' in position:
            position['created_at'] = str(position['created_at'])
        if 'opened_at' in position:
            position['opened_at'] = str(position['opened_at'])

    return jsonify({'positions': positions}), 200


@bp.route('/execute', methods=['POST'])
def execute_trade():
    """
    Execute a trade (manual or signal-based).

    Request Body:
        {
            "strategy_id": "...",
            "symbol": "BTC/USDT",
            "side": "BUY",
            "quantity": 0.01,
            "order_type": "market",
            "stop_loss": 44500,
            "take_profit": 46000,
            "mode": "paper"
        }

    Returns:
        Executed trade details
    """
    data = request.get_json() or {}

    required_fields = ['symbol', 'side', 'quantity']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'error': 'validation_error',
                'message': f'{field} is required'
            }), 400

    mode = data.get('mode', 'paper')
    symbol = data['symbol']
    side = data['side']
    quantity = float(data['quantity'])

    from datetime import datetime

    if mode == 'paper':
        simulator = PaperTradingSimulator()
        result = simulator.execute_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            order_type=data.get('order_type', 'market'),
            stop_loss=data.get('stop_loss'),
            take_profit=data.get('take_profit')
        )

        db = get_db()
        if db:
            trade = {
                'strategy_id': ObjectId(data['strategy_id']) if data.get('strategy_id') else None,
                'symbol': symbol,
                'side': side.upper(),
                'entry_price': result['entry_price'],
                'quantity': quantity,
                'entry_type': data.get('order_type', 'market'),
                'pnl': 0,
                'pnl_percent': 0,
                'commission': result.get('commission', 0),
                'status': 'OPEN',
                'mode': mode,
                'stop_loss': data.get('stop_loss'),
                'take_profit': data.get('take_profit'),
                'entry_time': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }
            result['trade_id'] = str(db.trades.insert_one(trade).inserted_id)

        logger.info(f"Paper trade executed: {side} {quantity} {symbol}")

    return jsonify({
        'id': result.get('trade_id'),
        'status': 'executed',
        'mode': mode,
        'entry_price': result['entry_price'],
        'symbol': symbol,
        'side': side.upper()
    }), 201


@bp.route('/<trade_id>', methods=['GET'])
def get_trade(trade_id):
    """
    Get a specific trade.

    Returns:
        Trade details
    """
    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    try:
        trade = db.trades.find_one({'_id': ObjectId(trade_id)})
    except Exception:
        return jsonify({'error': 'validation_error', 'message': 'Invalid trade ID'}), 400

    if not trade:
        return jsonify({'error': 'not_found', 'message': 'Trade not found'}), 404

    trade['_id'] = str(trade['_id'])
    return jsonify(trade), 200


@bp.route('/<trade_id>/close', methods=['POST'])
def close_trade(trade_id):
    """
    Close an open trade/position.

    Request Body:
        {
            "reason": "manual" | "stop_loss" | "take_profit" | "signal"
        }

    Returns:
        Closed trade details
    """
    data = request.get_json() or {}
    reason = data.get('reason', 'manual')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    try:
        trade = db.trades.find_one({'_id': ObjectId(trade_id)})
    except Exception:
        return jsonify({'error': 'validation_error', 'message': 'Invalid trade ID'}), 400

    if not trade:
        return jsonify({'error': 'not_found', 'message': 'Trade not found'}), 404

    if trade.get('status') == 'CLOSED':
        return jsonify({'error': 'conflict', 'message': 'Trade already closed'}), 409

    from datetime import datetime
    from app.broker_integrations.factory import BrokerFactory

    exit_price = 0

    if trade.get('mode') == 'paper':
        simulator = PaperTradingSimulator()
        exit_result = simulator.close_position(trade['symbol'], trade['side'], trade['quantity'])
        exit_price = exit_result['exit_price']
    else:
        broker = BrokerFactory.get_broker(trade.get('broker'))
        if broker:
            ticker = broker.get_current_price(trade['symbol'])
            exit_price = ticker['last'] if isinstance(ticker, dict) else ticker

    entry_price = trade['entry_price']
    quantity = trade['quantity']
    pnl = (exit_price - entry_price) * quantity if trade['side'] == 'BUY' else (entry_price - exit_price) * quantity

    db.trades.update_one(
        {'_id': ObjectId(trade_id)},
        {'$set': {
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_percent': (pnl / (entry_price * quantity)) * 100 if entry_price * quantity > 0 else 0,
            'status': 'CLOSED',
            'exit_time': datetime.utcnow(),
            'exit_reason': reason
        }}
    )

    db.positions.delete_one({'trade_id': ObjectId(trade_id)})

    logger.info(f"Trade closed: {trade_id}, PnL: {pnl}")

    return jsonify({
        'id': trade_id,
        'status': 'closed',
        'pnl': pnl,
        'exit_price': exit_price,
        'exit_reason': reason
    }), 200


@bp.route('/stats', methods=['GET'])
def get_trade_stats():
    """
    Get trade statistics.

    Query Parameters:
        - mode: paper or live
        - period: today, week, month, all

    Returns:
        Trade statistics
    """
    mode = request.args.get('mode', 'paper')
    period = request.args.get('period', 'all')

    from datetime import datetime, timedelta

    start_date = None
    if period == 'today':
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)

    query = {'mode': mode, 'status': 'CLOSED'}
    if start_date:
        query['entry_time'] = {'$gte': start_date}

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    trades = list(db.trades.find(query))

    total_trades = len(trades)
    winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
    losing_trades = len([t for t in trades if t.get('pnl', 0) <= 0])
    total_pnl = sum(t.get('pnl', 0) for t in trades)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    return jsonify({
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': round(win_rate, 2),
        'total_pnl': round(total_pnl, 2),
        'avg_pnl': round(total_pnl / total_trades, 2) if total_trades > 0 else 0,
        'period': period
    }), 200
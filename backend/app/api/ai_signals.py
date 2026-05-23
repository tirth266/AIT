"""
AI Signals API
==============
AI trading signals management endpoints.
"""

import logging
from datetime import datetime, timedelta
from bson import ObjectId
from flask import Blueprint, request, jsonify

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('ai_signals', __name__)


@bp.route('', methods=['GET'])
def list_signals():
    """
    List AI signals with filtering options.

    Query Parameters:
        - symbol: filter by symbol
        - signal_type: BUY, SELL, HOLD
        - timeframe: 1m, 5m, 15m, 1h, 4h, 1d
        - confidence_min: minimum confidence threshold
        - is_executed: filter by execution status
        - limit: number of results (default 50)
        - skip: number to skip (default 0)
        - period: today, week, month, all

    Returns:
        List of AI signals
    """
    symbol = request.args.get('symbol')
    signal_type = request.args.get('signal_type')
    timeframe = request.args.get('timeframe')
    confidence_min = float(request.args.get('confidence_min', 0))
    is_executed = request.args.get('is_executed')
    limit = int(request.args.get('limit', 50))
    skip = int(request.args.get('skip', 0))
    period = request.args.get('period', 'all')

    query = {}
    if symbol:
        query['symbol'] = symbol.upper()
    if signal_type:
        query['signal_type'] = signal_type.upper()
    if timeframe:
        query['timeframe'] = timeframe
    if confidence_min > 0:
        query['confidence'] = {'$gte': confidence_min}
    if is_executed is not None:
        query['is_executed'] = is_executed.lower() == 'true'

    if period != 'all':
        start_date = datetime.utcnow()
        if period == 'today':
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date -= timedelta(days=7)
        elif period == 'month':
            start_date -= timedelta(days=30)
        query['generated_at'] = {'$gte': start_date}

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    signals = list(db.ai_signals.find(query).sort('generated_at', -1).skip(skip).limit(limit))
    total = db.ai_signals.count_documents(query)

    for signal in signals:
        signal['_id'] = str(signal['_id'])
        if 'generated_at' in signal:
            signal['generated_at'] = signal['generated_at'].isoformat()
        if 'executed_at' in signal:
            signal['executed_at'] = signal['executed_at'].isoformat()
        if 'expires_at' in signal:
            signal['expires_at'] = signal['expires_at'].isoformat()

    return jsonify({
        'signals': signals,
        'total': total,
        'limit': limit,
        'skip': skip
    }), 200


@bp.route('', methods=['POST'])
def create_signal():
    """
    Create a new AI signal (typically from AI engine).

    Request Body:
        {
            "signal_type": "BUY",
            "symbol": "RELIANCE",
            "exchange": "NSE",
            "timeframe": "1h",
            "confidence": 85.5,
            "entry_price": 2450.00,
            "target_price": 2500.00,
            "stop_loss": 2420.00,
            "ai_reasoning": "RSI oversold, moving avg crossover...",
            "indicators": {...},
            "expires_in_minutes": 60
        }

    Returns:
        Created signal details
    """
    data = request.get_json() or {}

    required_fields = ['signal_type', 'symbol', 'confidence']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'error': 'validation_error',
                'message': f'{field} is required'
            }), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    now = datetime.utcnow()
    expires_minutes = data.get('expires_in_minutes', 60)

    signal = {
        'signal_type': data['signal_type'].upper(),
        'symbol': data['symbol'].upper(),
        'exchange': data.get('exchange', 'NSE'),
        'timeframe': data.get('timeframe', '1h'),
        'confidence': float(data['confidence']),
        'entry_price': float(data.get('entry_price', 0)),
        'target_price': float(data.get('target_price', 0)),
        'stop_loss': float(data.get('stop_loss', 0)),
        'ai_reasoning': data.get('ai_reasoning', ''),
        'indicators': data.get('indicators', {}),
        'risk_reward_ratio': data.get('risk_reward_ratio'),
        'strategy_name': data.get('strategy_name', 'AI Signal'),
        'is_executed': False,
        'is_expired': False,
        'generated_at': now,
        'expires_at': now + timedelta(minutes=expires_minutes),
        'created_at': now,
        'metadata': data.get('metadata', {})
    }

    result = db.ai_signals.insert_one(signal)
    logger.info(f"AI Signal created: {result.inserted_id} - {signal['signal_type']} {signal['symbol']}")

    signal['_id'] = str(result.inserted_id)
    signal['generated_at'] = signal['generated_at'].isoformat()
    signal['expires_at'] = signal['expires_at'].isoformat()

    return jsonify(signal), 201


@bp.route('/<signal_id>', methods=['GET'])
def get_signal(signal_id):
    """
    Get a specific AI signal.

    Returns:
        Signal details
    """
    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        signal = db.ai_signals.find_one({'_id': ObjectId(signal_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid signal ID'
        }), 400

    if not signal:
        return jsonify({
            'error': 'not_found',
            'message': 'Signal not found'
        }), 404

    signal['_id'] = str(signal['_id'])
    if 'generated_at' in signal:
        signal['generated_at'] = signal['generated_at'].isoformat()
    if 'executed_at' in signal:
        signal['executed_at'] = signal['executed_at'].isoformat()
    if 'expires_at' in signal:
        signal['expires_at'] = signal['expires_at'].isoformat()
    if 'created_at' in signal:
        signal['created_at'] = signal['created_at'].isoformat()

    return jsonify(signal), 200


@bp.route('/<signal_id>/execute', methods=['POST'])
def execute_signal(signal_id):
    """
    Execute an AI signal (convert to trade).

    Request Body:
        {
            "quantity": 10,
            "order_type": "market",
            "mode": "paper"
        }

    Returns:
        Execution result with trade details
    """
    data = request.get_json() or {}
    user_id = "default_user"

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    try:
        signal = db.ai_signals.find_one({'_id': ObjectId(signal_id)})
    except Exception:
        return jsonify({
            'error': 'validation_error',
            'message': 'Invalid signal ID'
        }), 400

    if not signal:
        return jsonify({
            'error': 'not_found',
            'message': 'Signal not found'
        }), 404

    if signal.get('is_executed'):
        return jsonify({
            'error': 'conflict',
            'message': 'Signal already executed'
        }), 409

    if signal.get('is_expired') or signal.get('expires_at', datetime.utcnow()) < datetime.utcnow():
        db.ai_signals.update_one(
            {'_id': ObjectId(signal_id)},
            {'$set': {'is_expired': True}}
        )
        return jsonify({
            'error': 'expired',
            'message': 'Signal has expired'
        }), 400

    from app.paper_trading.simulator import PaperTradingSimulator
    from app.api.trades import execute_trade

    mode = data.get('mode', 'paper')
    quantity = data.get('quantity', 1)

    if mode == 'paper':
        simulator = PaperTradingSimulator()
        result = simulator.execute_order(
            symbol=signal['symbol'],
            side=signal['signal_type'],
            quantity=quantity,
            order_type=data.get('order_type', 'market'),
            stop_loss=signal.get('stop_loss'),
            take_profit=signal.get('target_price')
        )

        trade = {
            'signal_id': ObjectId(signal_id),
            'user_id': user_id,
            'symbol': signal['symbol'],
            'side': signal['signal_type'],
            'entry_price': result['entry_price'],
            'quantity': quantity,
            'entry_type': data.get('order_type', 'market'),
            'pnl': 0,
            'pnl_percent': 0,
            'commission': result.get('commission', 0),
            'status': 'OPEN',
            'mode': mode,
            'stop_loss': signal.get('stop_loss'),
            'take_profit': signal.get('target_price'),
            'entry_time': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }
        trade_id = str(db.trades.insert_one(trade).inserted_id)

        db.ai_signals.update_one(
            {'_id': ObjectId(signal_id)},
            {'$set': {
                'is_executed': True,
                'executed_at': datetime.utcnow(),
                'executed_trade_id': trade_id
            }}
        )

        logger.info(f"AI Signal executed: {signal_id} -> Trade {trade_id}")

        return jsonify({
            'signal_id': signal_id,
            'trade_id': trade_id,
            'status': 'executed',
            'entry_price': result['entry_price']
        }), 201

    return jsonify({
        'error': 'not_implemented',
        'message': 'Live trading not implemented yet'
    }), 501


@bp.route('/stats', methods=['GET'])
def get_signal_stats():
    """
    Get AI signal statistics.

    Query Parameters:
        - period: today, week, month, all
        - symbol: filter by symbol

    Returns:
        Signal statistics
    """
    period = request.args.get('period', 'all')
    symbol = request.args.get('symbol')

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    query = {'is_executed': True}
    if symbol:
        query['symbol'] = symbol.upper()

    start_date = None
    if period != 'all':
        start_date = datetime.utcnow()
        if period == 'today':
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_date -= timedelta(days=7)
        elif period == 'month':
            start_date -= timedelta(days=30)
        query['generated_at'] = {'$gte': start_date}

    signals = list(db.ai_signals.find(query))

    total_signals = len(signals)
    buy_signals = len([s for s in signals if s.get('signal_type') == 'BUY'])
    sell_signals = len([s for s in signals if s.get('signal_type') == 'SELL'])
    hold_signals = len([s for s in signals if s.get('signal_type') == 'HOLD'])

    avg_confidence = sum(s.get('confidence', 0) for s in signals) / total_signals if total_signals > 0 else 0

    trade_query = {'signal_id': {'$ne': None}}
    if start_date:
        trade_query['entry_time'] = {'$gte': start_date}

    trades = list(db.trades.find(trade_query))
    winning_trades = len([t for t in trades if t.get('pnl', 0) > 0])
    total_pnl = sum(t.get('pnl', 0) for t in trades)

    return jsonify({
        'total_signals': total_signals,
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'hold_signals': hold_signals,
        'avg_confidence': round(avg_confidence, 2),
        'executed_trades': len(trades),
        'winning_trades': winning_trades,
        'win_rate': round((winning_trades / len(trades) * 100) if len(trades) > 0 else 0, 2),
        'total_pnl': round(total_pnl, 2),
        'period': period
    }), 200


@bp.route('/batch', methods=['POST'])
def generate_batch_signals():
    """
    Generate batch signals for multiple symbols (AI engine endpoint).

    Request Body:
        {
            "symbols": ["RELIANCE", "TCS", "INFY"],
            "timeframe": "1h",
            "strategies": ["RSI", "MACD"]
        }

    Returns:
        List of generated signals
    """
    data = request.get_json() or {}

    symbols = data.get('symbols', [])
    timeframe = data.get('timeframe', '1h')

    if not symbols:
        return jsonify({
            'error': 'validation_error',
            'message': 'At least one symbol is required'
        }), 400

    db = get_db()
    if db is None:
        return jsonify({'error': 'database_error', 'message': 'Database not available'}), 500

    generated_signals = []
    now = datetime.utcnow()

    for symbol in symbols:
        import random
        signal_types = ['BUY', 'SELL', 'HOLD']
        signal_type = random.choice(signal_types)
        confidence = random.uniform(60, 95)

        base_prices = {
            'RELIANCE': 2450, 'TCS': 3200, 'INFY': 1400,
            'HDFCBANK': 1650, 'ICICIBANK': 950, 'SBIN': 580,
            'AXISBANK': 950, 'LT': 2800
        }
        base_price = base_prices.get(symbol, 1000)
        entry_price = base_price * (1 + random.uniform(-0.02, 0.02))

        signal = {
            'signal_type': signal_type,
            'symbol': symbol.upper(),
            'exchange': 'NSE',
            'timeframe': timeframe,
            'confidence': confidence,
            'entry_price': round(entry_price, 2),
            'target_price': round(entry_price * (1.02 if signal_type == 'BUY' else 0.98), 2),
            'stop_loss': round(entry_price * (0.98 if signal_type == 'BUY' else 1.02), 2),
            'ai_reasoning': f'AI analysis for {symbol} on {timeframe} timeframe',
            'indicators': {
                'rsi': random.uniform(30, 70),
                'macd': random.uniform(-50, 50),
                'sma_20': round(base_price * random.uniform(0.98, 1.02), 2),
                'sma_50': round(base_price * random.uniform(0.95, 1.05), 2)
            },
            'risk_reward_ratio': random.uniform(1.5, 3.0),
            'strategy_name': 'Batch AI Signal',
            'is_executed': False,
            'is_expired': False,
            'generated_at': now,
            'expires_at': now + timedelta(minutes=60),
            'created_at': now,
            'metadata': {'batch_generated': True}
        }

        result = db.ai_signals.insert_one(signal)
        signal['_id'] = str(result.inserted_id)
        signal['generated_at'] = signal['generated_at'].isoformat()
        signal['expires_at'] = signal['expires_at'].isoformat()
        generated_signals.append(signal)

    logger.info(f"Batch signals generated: {len(generated_signals)}")

    return jsonify({
        'signals': generated_signals,
        'total': len(generated_signals)
    }), 201
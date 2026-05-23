"""
Dashboard API
=============
Dashboard data and analytics endpoints.
"""

import logging
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify

from app.database.connection import get_db

logger = logging.getLogger('trading_app')

bp = Blueprint('dashboard', __name__)


@bp.route('', methods=['GET'])
def get_dashboard():
    """
    Get dashboard data.
    """
    try:
        logger.info(f"[Dashboard] Request received from {request.remote_addr}")
        mode = request.args.get('mode', 'paper')
        logger.info(f"[Dashboard] Mode: {mode}")

        db = get_db()
        if not db:
            logger.error("[Dashboard] Database connection missing")
            return jsonify({
                'success': False,
                'error': 'database_error',
                'message': 'Database not connected'
            }), 500

        try:
            setting = db.settings.find_one({'key': 'trading_mode'})
            current_mode = setting['value'] if setting else 'paper'
        except Exception as e:
            logger.warning(f"[Dashboard] Could not fetch trading_mode setting: {e}")
            current_mode = 'paper'

        balance = 10000.0
        if mode == 'paper':
            try:
                paper_balance = db.settings.find_one({'key': 'paper_balance'})
                balance = float(paper_balance['value']) if paper_balance else 10000.0
            except Exception as e:
                logger.warning(f"[Dashboard] Could not fetch paper_balance: {e}")
                balance = 10000.0
        else:
            try:
                from app.broker_integrations.factory import BrokerFactory
                brokers = list(db.brokers.find({'is_connected': True}))
                if brokers:
                    broker = BrokerFactory.get_broker(brokers[0]['broker_name'])
                    balance_data = broker.get_balance()
                    balance = balance_data.get('total', balance_data.get('free', 0))
            except Exception as e:
                logger.error(f"[Dashboard] Broker balance fetch failed: {e}")
                balance = 0.0

        try:
            open_positions = list(db.positions.find({'status': 'open', 'mode': mode}))
        except Exception as e:
            logger.error(f"[Dashboard] Positions fetch failed: {e}")
            open_positions = []

        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_trades = list(db.trades.find({
                'mode': mode,
                'created_at': {'$gte': today_start}
            }))
        except Exception as e:
            logger.error(f"[Dashboard] Today's trades fetch failed: {e}")
            today_trades = []

        pnl_today = sum(t.get('pnl', 0) for t in today_trades)
        unrealized_pnl = sum(p.get('unrealized_pnl', 0) for p in open_positions)

        try:
            active_strategies = db.strategies.count_documents({'is_active': True, 'mode': mode})
        except Exception as e:
            logger.error(f"[Dashboard] Active strategies count failed: {e}")
            active_strategies = 0

        try:
            last_7_days = datetime.utcnow() - timedelta(days=7)
            week_trades = list(db.trades.find({
                'mode': mode,
                'created_at': {'$gte': last_7_days}
            }))
            pnl_week = sum(t.get('pnl', 0) for t in week_trades)
        except Exception as e:
            logger.error(f"[Dashboard] Week trades fetch failed: {e}")
            pnl_week = 0.0

        return jsonify({
            'success': True,
            'mode': current_mode,
            'trading_mode': mode,
            'balance': balance,
            'unrealized_pnl': round(unrealized_pnl, 2),
            'pnl_today': round(pnl_today, 2),
            'pnl_week': round(pnl_week, 2),
            'open_positions': len(open_positions),
            'active_strategies': active_strategies,
            'trades_today': len(today_trades)
        }), 200

    except Exception as e:
        import traceback
        logger.error(f"[Dashboard] Critical failure: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': 'internal_error',
            'message': str(e)
        }), 500


@bp.route('/performance', methods=['GET'])
def get_performance():
    """
    Get performance metrics.

    Query Parameters:
        - mode: paper or live
        - period: today, week, month, all
        - symbol: filter by symbol (optional)

    Returns:
        Performance metrics
    """
    mode = request.args.get('mode', 'paper')
    period = request.args.get('period', 'week')
    symbol = request.args.get('symbol')

    from datetime import datetime, timedelta

    if period == 'today':
        start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'week':
        start_date = datetime.utcnow() - timedelta(days=7)
    elif period == 'month':
        start_date = datetime.utcnow() - timedelta(days=30)
    else:
        start_date = None

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    query = {'mode': mode, 'status': 'CLOSED'}
    if start_date:
        query['created_at'] = {'$gte': start_date}
    if symbol:
        query['symbol'] = symbol

    trades = list(db.trades.find(query))

    total_trades = len(trades)
    winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
    losing_trades = [t for t in trades if t.get('pnl', 0) <= 0]

    total_pnl = sum(t.get('pnl', 0) for t in trades)
    gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
    gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))

    win_rate = (len(winning_trades) / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    avg_win = gross_profit / len(winning_trades) if winning_trades else 0
    avg_loss = gross_loss / len(losing_trades) if losing_trades else 0

    return jsonify({
        'period': period,
        'total_trades': total_trades,
        'winning_trades': len(winning_trades),
        'losing_trades': len(losing_trades),
        'win_rate': round(win_rate, 2),
        'total_pnl': round(total_pnl, 2),
        'gross_profit': round(gross_profit, 2),
        'gross_loss': round(gross_loss, 2),
        'profit_factor': round(profit_factor, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2)
    }), 200


@bp.route('/equity-curve', methods=['GET'])
def get_equity_curve():
    """
    Get equity curve data.

    Query Parameters:
        - mode: paper or live
        - period: days to include (default 30)

    Returns:
        Equity curve data points
    """
    mode = request.args.get('mode', 'paper')
    days = int(request.args.get('days', 30))

    from datetime import datetime, timedelta
    start_date = datetime.utcnow() - timedelta(days=days)

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    initial_balance = 10000.0
    if mode == 'paper':
        paper_balance = db.settings.find_one({'key': 'paper_balance'})
        initial_balance = float(paper_balance['value']) if paper_balance else 10000.0

    trades = list(db.trades.find({
        'mode': mode,
        'status': 'CLOSED',
        'created_at': {'$gte': start_date}
    }).sort('created_at', 1))

    equity_points = []
    current_equity = initial_balance

    for trade in trades:
        current_equity += trade.get('pnl', 0)
        equity_points.append({
            'timestamp': trade['created_at'].isoformat() if hasattr(trade['created_at'], 'isoformat') else str(trade['created_at']),
            'equity': round(current_equity, 2)
        })

    return jsonify({
        'mode': mode,
        'initial_balance': initial_balance,
        'current_equity': round(current_equity, 2),
        'curve': equity_points
    }), 200


@bp.route('/recent-trades', methods=['GET'])
def get_recent_trades():
    """
    Get recent trades for dashboard.

    Returns:
        Recent trades list
    """
    limit = int(request.args.get('limit', 5))
    mode = request.args.get('mode', 'paper')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    trades = list(db.trades.find({'mode': mode}).sort('created_at', -1).limit(limit))

    for trade in trades:
        trade['_id'] = str(trade['_id'])
        if 'created_at' in trade:
            trade['created_at'] = str(trade['created_at'])

    return jsonify({'trades': trades}), 200


@bp.route('/positions', methods=['GET'])
def get_positions():
    """
    Get open positions for dashboard.

    Returns:
        Open positions list
    """
    mode = request.args.get('mode', 'paper')

    db = get_db()
    if not db:
        return jsonify({'error': 'database_error'}), 500

    positions = list(db.positions.find({'status': 'open', 'mode': mode}))

    for position in positions:
        position['_id'] = str(position['_id'])

    return jsonify({'positions': positions}), 200
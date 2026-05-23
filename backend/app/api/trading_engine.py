"""
Trading Engine API
===================
API endpoints for the trading engine.
"""

import logging
import uuid
from datetime import datetime, timezone
from bson import ObjectId
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from app.database.connection import get_db
from app.utils.auth import get_current_user_id
from app.trading_engine import (
    get_trading_engine,
    get_order_manager,
    get_execution_engine,
    get_position_manager,
    get_pnl_engine,
    get_margin_engine,
    get_portfolio_manager,
    get_pre_trade_risk_engine,
    get_paper_exchange,
    init_trading_engine
)

logger = logging.getLogger('trading_engine_api')

bp = Blueprint('trading_engine', __name__)


@bp.route('/engine/status', methods=['GET'])
@jwt_required(optional=True)
def get_engine_status():
    """Get trading engine status."""
    try:
        engine = get_trading_engine()
        return jsonify({
            'status': 'running' if engine._running else 'stopped',
            'orders': len(engine.orders),
            'positions': len(engine.positions),
            'trades': len(engine.trades)
        }), 200
    except Exception as e:
        logger.error(f"Error getting engine status: {e}")
        return jsonify({'error': str(e)}), 500


@bp.route('/order/create', methods=['POST'])
@jwt_required(optional=True)
async def create_order():
    """Create and submit a new order."""
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    data['user_id'] = user_id
    data['mode'] = data.get('mode', 'paper')
    
    risk_engine = get_pre_trade_risk_engine()
    margin_engine = get_margin_engine()
    
    margin_info = margin_engine.get_margin_info(user_id)
    positions = get_position_manager().get_open_positions(user_id)
    day_pnl = get_pnl_engine().calculate_day_pnl(user_id, data.get('mode', 'paper'))
    
    context = {
        'margin_info': margin_info,
        'open_positions': positions,
        'day_pnl': day_pnl.get('day_pnl', 0)
    }
    
    is_allowed, results = risk_engine.validate_order(user_id, data, context)
    
    if not is_allowed:
        blocked_checks = [r for r in results if r.action == 'BLOCK']
        return jsonify({
            'error': 'risk_validation_failed',
            'message': blocked_checks[0].message if blocked_checks else 'Order blocked by risk rules',
            'checks': [{'type': r.check_type, 'action': r.action, 'message': r.message} for r in results]
        }), 400
    
    order_manager = get_order_manager()
    order, error = order_manager.create_order(data)
    
    if error:
        return jsonify({'error': 'order_creation_failed', 'message': error}), 400
    
    execution_engine = get_execution_engine()
    await execution_engine.submit_order(order)
    
    return jsonify({
        'message': 'Order created successfully',
        'order': order.to_dict()
    }), 201


@bp.route('/order/<order_id>', methods=['GET'])
@jwt_required(optional=True)
def get_order(order_id):
    """Get order details."""
    user_id = get_current_user_id()
    
    order_manager = get_order_manager()
    order = order_manager.get_order(order_id)
    
    if not order or order.user_id != user_id:
        return jsonify({'error': 'not_found', 'message': 'Order not found'}), 404
    
    return jsonify(order.to_dict()), 200


@bp.route('/order/<order_id>/cancel', methods=['POST'])
@jwt_required(optional=True)
def cancel_order_api(order_id):
    """Cancel an order."""
    user_id = get_current_user_id()
    
    order_manager = get_order_manager()
    order = order_manager.get_order(order_id)
    
    if not order or order.user_id != user_id:
        return jsonify({'error': 'not_found', 'message': 'Order not found'}), 404
    
    reason = request.json.get('reason', 'User requested') if request.json else 'User requested'
    order, error = order_manager.cancel_order(order_id, reason)
    
    if error:
        return jsonify({'error': 'cancel_failed', 'message': error}), 400
    
    return jsonify({
        'message': 'Order cancelled',
        'order': order.to_dict()
    }), 200


@bp.route('/order/<order_id>/modify', methods=['PUT'])
@jwt_required(optional=True)
def modify_order_api(order_id):
    """Modify an order."""
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    order_manager = get_order_manager()
    order = order_manager.get_order(order_id)
    
    if not order or order.user_id != user_id:
        return jsonify({'error': 'not_found', 'message': 'Order not found'}), 404
    
    order, error = order_manager.update_order(order_id, data)
    
    if error:
        return jsonify({'error': 'modify_failed', 'message': error}), 400
    
    return jsonify({
        'message': 'Order modified',
        'order': order.to_dict()
    }), 200


@bp.route('/orders', methods=['GET'])
@jwt_required(optional=True)
def list_orders():
    """List orders with filters."""
    user_id = get_current_user_id()
    
    status = request.args.get('status')
    order_type = request.args.get('order_type')
    symbol = request.args.get('symbol')
    mode = request.args.get('mode', 'paper')
    limit = int(request.args.get('limit', 50))
    
    filters = {}
    if status:
        filters['status'] = status.upper()
    if order_type:
        filters['order_type'] = order_type.upper()
    if symbol:
        filters['symbol'] = symbol.upper()
    if mode:
        filters['mode'] = mode
    
    order_manager = get_order_manager()
    orders = order_manager.get_user_orders(user_id, filters if filters else None)
    
    orders = sorted(orders, key=lambda o: o.created_at, reverse=True)[:limit]
    
    return jsonify({
        'orders': [o.to_dict() for o in orders],
        'total': len(orders)
    }), 200


@bp.route('/positions', methods=['GET'])
@jwt_required(optional=True)
def list_positions():
    """List positions with filters."""
    user_id = get_current_user_id()
    
    status = request.args.get('status')
    symbol = request.args.get('symbol')
    mode = request.args.get('mode', 'paper')
    
    filters = {}
    if status:
        filters['status'] = status.upper()
    if symbol:
        filters['symbol'] = symbol.upper()
    if mode:
        filters['mode'] = mode
    
    position_manager = get_position_manager()
    positions = position_manager.get_user_positions(user_id, filters if filters else None)
    
    positions = sorted(positions, key=lambda p: p.opened_at or datetime.min, reverse=True)
    
    return jsonify({
        'positions': [p.to_dict() for p in positions]
    }), 200


@bp.route('/positions/open', methods=['GET'])
@jwt_required(optional=True)
def get_open_positions():
    """Get open positions."""
    try:
        user_id = get_current_user_id()
        mode = request.args.get('mode', 'paper')
        logger.info(f"[TradingEngine] Fetching open positions for {user_id}, mode={mode}")
        
        position_manager = get_position_manager()
        if not position_manager:
            logger.error("[TradingEngine] Position manager not available")
            return jsonify({'success': False, 'message': 'Position manager unavailable'}), 500
            
        positions = position_manager.get_open_positions(user_id)
        
        if mode:
            positions = [p for p in positions if p.mode == mode]
        
        return jsonify({
            'success': True,
            'positions': [p.to_dict() for p in positions]
        }), 200
        
    except Exception as e:
        import traceback
        logger.error(f"[TradingEngine] Open positions failure: {e}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/positions/<position_id>', methods=['GET'])
@jwt_required(optional=True)
def get_position(position_id):
    """Get position details."""
    user_id = get_current_user_id()
    
    position_manager = get_position_manager()
    position = position_manager.get_position(position_id)
    
    if not position or position.user_id != user_id:
        return jsonify({'error': 'not_found', 'message': 'Position not found'}), 404
    
    return jsonify(position.to_dict()), 200


@bp.route('/positions/<position_id>/exit', methods=['POST'])
@jwt_required(optional=True)
def exit_position(position_id):
    """Exit/close a position."""
    user_id = get_current_user_id()
    data = request.get_json() or {}
    
    position_manager = get_position_manager()
    position = position_manager.get_position(position_id)
    
    if not position or position.user_id != user_id:
        return jsonify({'error': 'not_found', 'message': 'Position not found'}), 404
    
    exit_price = data.get('exit_price', 0)
    if not exit_price:
        exit_price = position.current_price
    
    exit_qty = data.get('quantity', position.quantity)
    
    position, trade = position_manager.close_position(
        position_id, 
        exit_price,
        exit_qty
    )
    
    if not position:
        return jsonify({'error': 'exit_failed', 'message': 'Failed to exit position'}), 400
    
    return jsonify({
        'message': 'Position exited',
        'position': position.to_dict(),
        'trade': trade.to_dict() if trade else None
    }), 200


@bp.route('/pnl', methods=['GET'])
@jwt_required(optional=True)
def get_pnl():
    """Get P&L summary."""
    user_id = get_current_user_id()
    mode = request.args.get('mode', 'paper')
    
    pnl_engine = get_pnl_engine()
    pnl_data = pnl_engine.calculate_total_pnl(user_id, mode)
    
    return jsonify(pnl_data), 200


@bp.route('/pnl/day', methods=['GET'])
@jwt_required(optional=True)
def get_day_pnl():
    """Get day P&L."""
    user_id = get_current_user_id()
    mode = request.args.get('mode', 'paper')
    
    pnl_engine = get_pnl_engine()
    day_pnl = pnl_engine.calculate_day_pnl(user_id, mode)
    
    return jsonify(day_pnl), 200


@bp.route('/margin', methods=['GET'])
@jwt_required(optional=True)
def get_margin():
    """Get margin information."""
    user_id = get_current_user_id()
    
    margin_engine = get_margin_engine()
    margin_info = margin_engine.get_margin_info(user_id)
    
    return jsonify(margin_info.to_dict()), 200


@bp.route('/portfolio', methods=['GET'])
@jwt_required(optional=True)
def get_portfolio():
    """Get complete portfolio summary."""
    user_id = get_current_user_id()
    mode = request.args.get('mode', 'paper')
    
    margin_engine = get_margin_engine()
    cash_balance = margin_engine.get_cash_balance(user_id)
    
    portfolio_manager = get_portfolio_manager()
    portfolio = portfolio_manager.get_complete_portfolio(user_id, mode, cash_balance)
    
    return jsonify(portfolio), 200


@bp.route('/portfolio/holdings', methods=['GET'])
@jwt_required(optional=True)
def get_holdings():
    """Get holdings summary."""
    user_id = get_current_user_id()
    mode = request.args.get('mode', 'paper')
    
    portfolio_manager = get_portfolio_manager()
    holdings = portfolio_manager.get_holdings_summary(user_id, mode)
    
    return jsonify(holdings), 200


@bp.route('/trades', methods=['GET'])
@jwt_required(optional=True)
def get_trades():
    """Get trade history."""
    user_id = get_current_user_id()
    
    symbol = request.args.get('symbol')
    limit = int(request.args.get('limit', 50))
    
    filters = {}
    if symbol:
        filters['symbol'] = symbol.upper()
    
    portfolio_manager = get_portfolio_manager()
    trades = portfolio_manager.get_trade_history(user_id, filters, limit)
    
    return jsonify({'trades': trades}), 200


@bp.route('/market/quotes', methods=['GET'])
@jwt_required(optional=True)
def get_market_quotes():
    """Get market quotes."""
    symbols = request.args.get('symbols', '').split(',')
    
    if not symbols or symbols == ['']:
        paper_exchange = get_paper_exchange()
        quotes = paper_exchange.get_all_quotes()
    else:
        paper_exchange = get_paper_exchange()
        quotes = {s.strip().upper(): paper_exchange.get_quote(s.strip().upper()) 
                  for s in symbols if s.strip()}
    
    return jsonify({'quotes': quotes}), 200


@bp.route('/market/depth/<symbol>', methods=['GET'])
@jwt_required(optional=True)
def get_market_depth(symbol):
    """Get market depth for a symbol."""
    paper_exchange = get_paper_exchange()
    depth = paper_exchange.get_market_depth(symbol.upper())
    
    if not depth:
        return jsonify({'error': 'not_found', 'message': 'Symbol not found'}), 404
    
    return jsonify({
        'symbol': depth.symbol,
        'bid_prices': depth.bid_prices,
        'bid_quantities': depth.bid_quantities,
        'ask_prices': depth.ask_prices,
        'ask_quantities': depth.ask_quantities,
        'last_price': depth.last_price,
        'volume': depth.volume,
        'timestamp': depth.timestamp.isoformat()
    }), 200


@bp.route('/risk/checks', methods=['GET'])
@jwt_required(optional=True)
def get_risk_checks():
    """Get recent risk events."""
    user_id = get_current_user_id()
    limit = int(request.args.get('limit', 50))
    
    risk_engine = get_pre_trade_risk_engine()
    events = risk_engine.get_risk_events(user_id, limit)
    
    return jsonify({'events': events}), 200


@bp.route('/reconciliation', methods=['GET'])
@jwt_required(optional=True)
def run_reconciliation():
    """Run reconciliation for user."""
    user_id = get_current_user_id()
    
    from app.trading_engine.reconciliation import get_trade_reconciliation
    reconciliation = get_trade_reconciliation()
    result = reconciliation.run_full_reconciliation(user_id)
    
    return jsonify(result), 200


@bp.route('/init', methods=['POST'])
def init_engine():
    """Initialize trading engine."""
    try:
        init_trading_engine()
        return jsonify({'message': 'Trading engine initialized'}), 200
    except Exception as e:
        logger.error(f"Error initializing engine: {e}")
        return jsonify({'error': str(e)}), 500
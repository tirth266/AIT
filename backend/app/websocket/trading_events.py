"""
Trading WebSocket Events
=======================
WebSocket event handlers for trading engine updates.
"""

import logging
import asyncio
from datetime import datetime, timezone
from flask import request
from flask_socketio import emit
try:
    from flask_socketio import join_room as join, leave_room as leave
except ImportError:
    from flask_socketio import join, leave

from app.trading_engine import (
    get_trading_engine,
    get_order_manager,
    get_position_manager,
    get_pnl_engine,
    get_margin_engine,
    get_paper_exchange
)

logger = logging.getLogger('trading_ws')


def register_trading_socket_handlers(socketio, ws_manager):
    """Register trading-related WebSocket event handlers."""
    
    @socketio.on('trading_subscribe')
    def handle_trading_subscribe(data):
        """Subscribe to trading events."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        channels = data.get('channels', ['orders', 'positions', 'pnl', 'trades'])
        
        for channel in channels:
            if channel == 'orders':
                ws_manager.subscribe_strategy(request.sid, f"user:{user_id}:orders")
            elif channel == 'positions':
                ws_manager.subscribe_strategy(request.sid, f"user:{user_id}:positions")
            elif channel == 'pnl':
                ws_manager.subscribe_strategy(request.sid, f"user:{user_id}:pnl")
            elif channel == 'trades':
                ws_manager.subscribe_strategy(request.sid, f"user:{user_id}:trades")
        
        emit('subscription_success', {
            'action': 'trading_subscribe',
            'channels': channels,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        logger.info(f"User {user_id} subscribed to trading channels: {channels}")
    
    @socketio.on('trading_unsubscribe')
    def handle_trading_unsubscribe(data):
        """Unsubscribe from trading events."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        channels = data.get('channels', ['orders', 'positions', 'pnl', 'trades'])
        
        for channel in channels:
            room = f"user:{user_id}:{channel}"
            leave(room)
        
        emit('subscription_success', {
            'action': 'trading_unsubscribe',
            'channels': channels,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('place_order')
    def handle_place_order(data):
        """Handle real-time order placement via WebSocket."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        emit('order_processing', {
            'status': 'PROCESSING',
            'message': 'Processing order...',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        try:
            order_manager = get_order_manager()
            
            order_data = {
                'user_id': user_id,
                'symbol': data.get('symbol', '').upper(),
                'exchange': data.get('exchange', 'NSE'),
                'transaction_type': data.get('transaction_type', 'BUY').upper(),
                'order_type': data.get('order_type', 'MARKET').upper(),
                'quantity': int(data.get('quantity', 0)),
                'price': float(data.get('price', 0)),
                'trigger_price': float(data.get('trigger_price', 0)),
                'product_type': data.get('product_type', 'MIS').upper(),
                'validity': data.get('validity', 'DAY').upper(),
                'mode': data.get('mode', 'paper'),
                'strategy_id': data.get('strategy_id')
            }
            
            order, error = asyncio.run(order_manager.create_order(order_data))
            
            if error:
                emit('order_rejected', {
                    'error': error,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                return
            
            from app.trading_engine import get_execution_engine
            execution_engine = get_execution_engine()
            asyncio.run(execution_engine.submit_order(order))
            
            emit('order_created', {
                'order': order.to_dict(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            ws_manager.broadcast_order_update(user_id, {
                'order_id': order.order_id,
                'status': order.status,
                'message': 'Order created'
            })
            
        except Exception as e:
            logger.error(f"Order placement error: {e}")
            emit('order_error', {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
    
    @socketio.on('cancel_order_ws')
    def handle_cancel_order_ws(data):
        """Handle order cancellation via WebSocket."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        order_id = data.get('order_id')
        if not order_id:
            emit('error', {'message': 'No order_id provided'})
            return
        
        try:
            order_manager = get_order_manager()
            order, error = asyncio.run(order_manager.cancel_order(order_id, 'User cancelled via WebSocket'))
            
            if error:
                emit('cancel_error', {'error': error})
                return
            
            emit('order_cancelled', {
                'order_id': order_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            ws_manager.broadcast_order_update(user_id, {
                'order_id': order_id,
                'status': 'CANCELLED',
                'message': 'Order cancelled'
            })
            
        except Exception as e:
            logger.error(f"Order cancellation error: {e}")
            emit('cancel_error', {'error': str(e)})
    
    @socketio.on('get_quote')
    def handle_get_quote(data):
        """Get quote for a symbol."""
        symbol = data.get('symbol', '').upper()
        
        if not symbol:
            emit('error', {'message': 'No symbol provided'})
            return
        
        paper_exchange = get_paper_exchange()
        quote = paper_exchange.get_quote(symbol)
        
        emit('quote_response', {
            'symbol': symbol,
            'quote': quote,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('get_quotes')
    def handle_get_quotes(data):
        """Get quotes for multiple symbols."""
        symbols = data.get('symbols', [])
        
        paper_exchange = get_paper_exchange()
        
        if not symbols:
            quotes = paper_exchange.get_all_quotes()
        else:
            quotes = {s.upper(): paper_exchange.get_quote(s.upper()) 
                     for s in symbols if s}
        
        emit('quotes_response', {
            'quotes': quotes,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('get_user_orders')
    def handle_get_user_orders(data):
        """Get user's current orders."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        mode = data.get('mode', 'paper')
        
        order_manager = get_order_manager()
        orders = order_manager.get_user_orders(user_id, {'mode': mode})
        
        emit('user_orders', {
            'orders': [o.to_dict() for o in orders],
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('get_user_positions')
    def handle_get_user_positions(data):
        """Get user's current positions."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        mode = data.get('mode', 'paper')
        
        position_manager = get_position_manager()
        positions = position_manager.get_open_positions(user_id)
        
        if mode:
            positions = [p for p in positions if p.mode == mode]
        
        emit('user_positions', {
            'positions': [p.to_dict() for p in positions],
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('get_user_pnl')
    def handle_get_user_pnl(data):
        """Get user's P&L."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        mode = data.get('mode', 'paper')
        
        pnl_engine = get_pnl_engine()
        pnl_data = pnl_engine.calculate_total_pnl(user_id, mode)
        
        emit('user_pnl', {
            'pnl': pnl_data,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('get_user_margin')
    def handle_get_user_margin(data):
        """Get user's margin information."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        margin_engine = get_margin_engine()
        margin_info = margin_engine.get_margin_info(user_id)
        
        emit('user_margin', {
            'margin': margin_info.to_dict(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    @socketio.on('exit_position_ws')
    def handle_exit_position_ws(data):
        """Exit a position via WebSocket."""
        user_data = ws_manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')
        
        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return
        
        position_id = data.get('position_id')
        if not position_id:
            emit('error', {'message': 'No position_id provided'})
            return
        
        try:
            position_manager = get_position_manager()
            position = position_manager.get_position(position_id)
            
            if not position or position.user_id != user_id:
                emit('error', {'message': 'Position not found'})
                return
            
            exit_price = data.get('exit_price', position.current_price)
            exit_qty = data.get('quantity', position.quantity)
            
            position, trade = asyncio.run(position_manager.close_position(
                position_id, exit_price, exit_qty
            ))
            
            if not position:
                emit('error', {'message': 'Failed to exit position'})
                return
            
            emit('position_exited', {
                'position': position.to_dict(),
                'trade': trade.to_dict() if trade else None,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            ws_manager.broadcast_position_update(user_id, {
                'position_id': position_id,
                'status': position.status,
                'quantity': position.quantity,
                'message': 'Position exited'
            })
            
        except Exception as e:
            logger.error(f"Position exit error: {e}")
            emit('error', {'message': str(e)})
    
    logger.info("Trading WebSocket handlers registered")


async def broadcast_trading_update(ws_manager, user_id: str, event_type: str, data: dict):
    """Broadcast trading updates to user."""
    ws_manager.emit_to_user(user_id, event_type, {
        **data,
        'timestamp': datetime.now(timezone.utc).isoformat()
    })


async def start_trading_event_broadcasts(ws_manager):
    """Start periodic trading event broadcasts."""
    while True:
        try:
            await broadcast_all_positions(ws_manager)
            await broadcast_all_pnl(ws_manager)
        except Exception as e:
            logger.error(f"Trading broadcast error: {e}")
        
        await asyncio.sleep(5)


async def broadcast_all_positions(ws_manager):
    """Broadcast position updates for all users."""
    from collections import defaultdict
    
    user_positions = defaultdict(list)
    
    engine = get_trading_engine()
    for position in engine.positions.values():
        if position.status == "OPEN":
            user_positions[position.user_id].append(position)
    
    for user_id, positions in user_positions.items():
        pnl_engine = get_pnl_engine()
        pnl = pnl_engine.calculate_total_pnl(user_id)
        
        ws_manager.broadcast_pnl_update(user_id, {
            'total_pnl': pnl.get('total_pnl', 0),
            'unrealized_pnl': pnl.get('unrealized_pnl', 0),
            'realized_pnl': pnl.get('realized_pnl', 0),
            'day_pnl': pnl.get('day_pnl', 0)
        })


async def broadcast_all_pnl(ws_manager):
    """Broadcast P&L updates for all users."""
    from collections import defaultdict
    
    user_pnl = defaultdict(dict)
    
    engine = get_trading_engine()
    pnl_engine = get_pnl_engine()
    
    for user_id in engine.user_positions.keys():
        pnl = pnl_engine.calculate_total_pnl(user_id)
        user_pnl[user_id] = pnl
    
    for user_id, pnl in user_pnl.items():
        ws_manager.broadcast_pnl_update(user_id, pnl)
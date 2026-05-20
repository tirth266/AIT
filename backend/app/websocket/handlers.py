"""
WebSocket Event Handlers
=======================
Handle all client-server WebSocket events for the trading platform.
"""

import logging
from datetime import datetime, timezone
from flask import request
from flask_socketio import emit, disconnect
try:
    from flask_socketio import join_room as join, leave_room as leave
except ImportError:
    from flask_socketio import join, leave
from .socket_manager import get_ws_manager

logger = logging.getLogger('websocket')
logger.setLevel(logging.INFO)


def register_handlers(socketio):
    """Register all SocketIO event handlers."""
    manager = get_ws_manager()

    from app.websocket.trading_events import register_trading_socket_handlers
    register_trading_socket_handlers(socketio, manager)

    @socketio.on('connect')
    def handle_connect(auth):
        """Handle client connection with JWT validation."""
        token = auth.get('token') if auth else None

        logger.info(f"Client attempting connection: {request.sid}")

        if not token:
            logger.warning(f"Connection rejected - no token provided: {request.sid}")
            return False

        if token == 'dev_token_placeholder':
            logger.info(f"DEV mode: accepting dev token for session {request.sid}")
            user_id = 'default_user'
            manager.register_connection(request.sid, user_id, {'user_id': user_id})
            manager.join_user_room(request.sid, user_id)

            logger.info(f"Client connected (dev mode): {request.sid} -> {user_id}")

            emit('connected', {
                'status': 'connected',
                'session_id': request.sid,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

            emit('auth_success', {
                'user_id': user_id,
                'message': 'Authentication successful (dev mode)',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            return

        user_data = manager.authenticate_token(token)

        if not user_data:
            logger.warning(f"Connection rejected - invalid token: {request.sid}")
            return False

        user_id = user_data.get('user_id')
        manager.register_connection(request.sid, user_id, user_data)
        manager.join_user_room(request.sid, user_id)

        logger.info(f"Client connected and authenticated: {request.sid} -> {user_id}")

        emit('connected', {
            'status': 'connected',
            'session_id': request.sid,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        emit('auth_success', {
            'user_id': user_id,
            'message': 'Authentication successful',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        manager.unregister_connection(request.sid)
        logger.info(f"Client disconnected: {request.sid}")

    @socketio.on('authenticate')
    def handle_authenticate(data):
        """Handle JWT authentication."""
        manager = get_ws_manager()
        token = data.get('token')

        if not token:
            emit('auth_error', {
                'message': 'No token provided',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            disconnect(request.sid)
            return

        user_data = manager.authenticate_token(token)

        if not user_data:
            emit('auth_error', {
                'message': 'Invalid or expired token',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            disconnect(request.sid)
            return

        user_id = user_data.get('user_id')
        manager.register_connection(request.sid, user_id, user_data)
        manager.join_user_room(request.sid, user_id)

        emit('auth_success', {
            'user_id': user_id,
            'message': 'Authentication successful',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"User {user_id} authenticated")

    @socketio.on('refresh_auth')
    def handle_refresh_auth(data):
        """Handle token refresh."""
        manager = get_ws_manager()
        old_token = data.get('token')

        if not old_token:
            emit('auth_error', {'message': 'No token provided'})
            return

        user_data = manager.authenticate_token(old_token)
        if not user_data:
            emit('auth_error', {'message': 'Invalid token'})
            return

        user_id = user_data.get('user_id')
        emit('auth_refreshed', {
            'user_id': user_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('subscribe_market')
    def handle_subscribe_market(data):
        """Handle market data subscription."""
        from app import market_data_engine

        manager = get_ws_manager()

        user_data = manager.connected_users.get(request.sid, {})
        if not user_data.get('user_id'):
            emit('error', {'message': 'User not authenticated'})
            return

        symbols = data.get('symbols', [])
        channel = data.get('channel', 'quotes')

        if not symbols:
            emit('error', {'message': 'No symbols provided'})
            return

        symbols = [s.upper() for s in symbols]

        market_data_engine.subscribe_session(request.sid, symbols)

        for symbol in symbols:
            join(f"market:{symbol}")

        for symbol in symbols:
            tick = market_data_engine.get_tick(symbol)
            if tick:
                emit('market:tick', tick)

        emit('subscription_success', {
            'action': 'subscribe_market',
            'symbols': symbols,
            'channel': channel,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        logger.info(f"Session {request.sid} subscribed to market: {symbols}")

    @socketio.on('unsubscribe_market')
    def handle_unsubscribe_market(data):
        """Handle market data unsubscription."""
        manager = get_ws_manager()
        symbols = data.get('symbols', [])

        if not symbols:
            emit('error', {'message': 'No symbols provided'})
            return

        manager.unsubscribe_market(request.sid, symbols)

        emit('subscription_success', {
            'action': 'unsubscribe_market',
            'symbols': [s.upper() for s in symbols],
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('subscribe_watchlist')
    def handle_subscribe_watchlist(data):
        """Handle watchlist subscription."""
        manager = get_ws_manager()
        watchlist_id = data.get('watchlist_id')

        if not watchlist_id:
            emit('error', {'message': 'No watchlist_id provided'})
            return

        user_id = manager.connected_users.get(request.sid, {}).get('user_id')
        if user_id:
            manager.subscribe_strategy(request.sid, f"watchlist:{watchlist_id}")

        emit('subscription_success', {
            'action': 'subscribe_watchlist',
            'watchlist_id': watchlist_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('subscribe_user')
    def handle_subscribe_user(data):
        """Handle user-specific data subscription."""
        manager = get_ws_manager()
        channels = data.get('channels', ['orders', 'positions', 'pnl'])

        user_data = manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')

        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return

        for channel in channels:
            if channel == 'orders':
                manager.subscribe_strategy(request.sid, f"user:{user_id}:orders")
            elif channel == 'positions':
                manager.subscribe_strategy(request.sid, f"user:{user_id}:positions")
            elif channel == 'pnl':
                manager.subscribe_strategy(request.sid, f"user:{user_id}:pnl")

        emit('subscription_success', {
            'action': 'subscribe_user',
            'channels': channels,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('place_order')
    def handle_place_order(data):
        """Handle real-time order placement."""
        manager = get_ws_manager()
        user_data = manager.connected_users.get(request.sid, {})
        user_id = user_data.get('user_id')

        if not user_id:
            emit('error', {'message': 'User not authenticated'})
            return

        emit('order_received', {
            'status': 'PROCESSING',
            'message': 'Order received, processing...',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('cancel_order')
    def handle_cancel_order(data):
        """Handle order cancellation."""
        manager = get_ws_manager()
        order_id = data.get('order_id')

        if not order_id:
            emit('error', {'message': 'No order_id provided'})
            return

        user_id = manager.connected_users.get(request.sid, {}).get('user_id')

        manager.broadcast_order_update(user_id, {
            'order_id': order_id,
            'status': 'CANCELLED',
            'message': 'Order cancelled by user',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('start_strategy')
    def handle_start_strategy(data):
        """Handle strategy start."""
        manager = get_ws_manager()
        strategy_id = data.get('strategy_id')

        if not strategy_id:
            emit('error', {'message': 'No strategy_id provided'})
            return

        manager.subscribe_strategy(request.sid, strategy_id)

        manager.broadcast_strategy_signal(strategy_id, {
            'status': 'RUNNING',
            'message': 'Strategy started',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('stop_strategy')
    def handle_stop_strategy(data):
        """Handle strategy stop."""
        manager = get_ws_manager()
        strategy_id = data.get('strategy_id')

        if not strategy_id:
            emit('error', {'message': 'No strategy_id provided'})
            return

        manager.unsubscribe_strategy(request.sid, strategy_id)

        manager.broadcast_strategy_signal(strategy_id, {
            'status': 'STOPPED',
            'message': 'Strategy stopped',
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('ping')
    def handle_ping():
        """Handle heartbeat ping."""
        manager = get_ws_manager()
        manager.send_heartbeat_response(request.sid)

    @socketio.on('mark_notification_read')
    def handle_mark_notification_read(data):
        """Handle marking notification as read."""
        notification_id = data.get('notification_id')

        if not notification_id:
            emit('error', {'message': 'No notification_id provided'})
            return

        emit('notification_read', {
            'notification_id': notification_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    @socketio.on('get_market_status')
    def handle_get_market_status():
        """Handle market status request."""
        from app import market_data_engine
        
        try:
            status = market_data_engine.get_market_status()
            emit('market_status', status)
        except Exception as e:
            logger.error(f"Failed to get market status: {e}")
            emit('error', {'message': 'Failed to get market status'})

    @socketio.on('get_connection_stats')
    def handle_get_connection_stats():
        """Handle connection stats request."""
        manager = get_ws_manager()
        stats = manager.get_connection_stats()
        emit('connection_stats', stats)


def setup_error_handlers(socketio):
    """Setup error handlers."""

    @socketio.on_error()
    def error_handler(e):
        logger.error(f"SocketIO Error: {e}")

    @socketio.on_error_connect()
    def error_connect_handler(e):
        logger.error(f"SocketIO Connection Error: {e}")

    @socketio.on_error_disconnect()
    def error_disconnect_handler(e):
        logger.error(f"SocketIO Disconnect Error: {e}")

    @socketio.on_default()
    def default_handler(event, data):
        logger.warning(f"Unhandled event: {event}, data: {data}")
"""
Scalable Socket Event Handlers
==============================
Production-ready SocketIO event handlers with authentication,
rate limiting, and distributed state management.
"""

import os
import logging
import time
import asyncio
from datetime import datetime, timezone
from flask_socketio import emit, join, leave, disconnect
from flask import request

from app.websocket.scalable_socket_manager import (
    get_scalable_socket_manager,
    init_scalable_socket_manager
)
from app.websocket.connection_manager import get_connection_manager
from app.websocket.middleware import get_rate_limiter
from app.websocket.heartbeat import get_heartbeat

logger = logging.getLogger(__name__)


class SocketEventHandlers:
    """
    Scalable socket event handlers with distributed state.
    """

    def __init__(self, socketio, app=None):
        self.socketio = socketio
        self.app = app
        self._manager = None

    def register(self):
        """Register all event handlers."""
        self._manager = init_scalable_socket_manager(self.socketio, self.app)

        self._register_connect_handlers()
        self._register_auth_handlers()
        self._register_subscription_handlers()
        self._register_trading_handlers()
        self._register_heartbeat_handlers()
        self._register_monitoring_handlers()
        self._register_error_handlers()

        logger.info("Scalable socket handlers registered")

    def _register_connect_handlers(self):
        """Connection lifecycle handlers."""

        @self.socketio.on('connect')
        def handle_connect():
            """Handle new WebSocket connection."""
            sid = request.sid
            ip = request.remote_addr

            logger.info(f"New connection: {sid} from {ip}")
            emit('connected', {
                'status': 'connected',
                'session_id': sid,
                'node_id': self._manager.node_id,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        @self.socketio.on('disconnect')
        async def handle_disconnect():
            """Handle disconnection."""
            sid = request.sid
            await self._manager.unregister_connection(sid)
            logger.info(f"Disconnected: {sid}")

        @self.socketio.on('disconnect_request')
        def handle_disconnect_request():
            """Handle graceful disconnect request."""
            sid = request.sid
            asyncio.create_task(self._manager.unregister_connection(sid))
            emit('disconnected', {
                'reason': 'client_request',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

    def _register_auth_handlers(self):
        """Authentication handlers."""

        @self.socketio.on('authenticate')
        async def handle_authenticate(data):
            """Handle JWT authentication."""
            sid = request.sid
            token = data.get('token')

            if not token:
                emit('auth_error', {
                    'message': 'No token provided',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                disconnect(sid)
                return

            metadata = data.get('metadata', {})
            success = await self._manager.register_connection(sid, token, metadata)

            if success:
                user_id = self._manager._connection_manager.get_connection(sid).user_id
                emit('auth_success', {
                    'user_id': user_id,
                    'message': 'Authentication successful',
                    'heartbeat_interval': get_heartbeat().get_interval(sid),
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                logger.info(f"Authenticated: {user_id} on {sid}")
            else:
                emit('auth_error', {
                    'message': 'Authentication failed',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
                disconnect(sid)

        @self.socketio.on('refresh_token')
        def handle_refresh_token(data):
            """Handle token refresh."""
            old_token = data.get('token')

            if not old_token:
                emit('error', {'message': 'No token provided'})
                return

            from app.websocket.middleware import get_auth_middleware
            new_token = get_auth_middleware().refresh_token(old_token)

            if new_token:
                emit('token_refreshed', {
                    'token': new_token,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })
            else:
                emit('error', {'message': 'Token refresh failed'})

        @self.socketio.on('reconnect_session')
        async def handle_reconnect_session(data):
            """Handle session reconnection."""
            sid = request.sid
            session_data = data.get('session_data', {})

            session = await self._manager._session_persistence.load_session(sid)
            if session:
                user_id = session.get('user_id')
                if user_id:
                    success = await self._manager.register_connection(
                        sid,
                        session_data.get('token', ''),
                        {'reconnected': True, **session_data}
                    )
                    if success:
                        emit('reconnected', {
                            'user_id': user_id,
                            'session_restored': True,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        })
                        return

            emit('reconnect_failed', {
                'message': 'Session could not be restored',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

    def _register_subscription_handlers(self):
        """Subscription handlers."""

        @self.socketio.on('subscribe_market')
        async def handle_subscribe_market(data):
            """Handle market data subscription."""
            sid = request.sid
            symbols = data.get('symbols', [])
            channel = data.get('channel', 'quotes')

            if not symbols:
                emit('error', {'message': 'No symbols provided'})
                return

            rate_limiter = get_rate_limiter()
            conn = self._manager._connection_manager.get_connection(sid)
            if not conn:
                emit('error', {'message': 'Not authenticated'})
                return

            if not rate_limiter.check_limit(conn.user_id, 'subscribe_market'):
                emit('error', {'message': 'Rate limit exceeded'})
                return

            symbols = [s.upper() for s in symbols]
            self._manager.subscribe_market(sid, symbols, conn.user_id)

            emit('subscription_success', {
                'action': 'subscribe_market',
                'symbols': symbols,
                'channel': channel,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        @self.socketio.on('unsubscribe_market')
        async def handle_unsubscribe_market(data):
            """Handle market data unsubscription."""
            sid = request.sid
            symbols = data.get('symbols', [])

            if not symbols:
                emit('error', {'message': 'No symbols provided'})
                return

            self._manager.unsubscribe_market(sid, [s.upper() for s in symbols])

            emit('subscription_success', {
                'action': 'unsubscribe_market',
                'symbols': [s.upper() for s in symbols],
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        @self.socketio.on('subscribe_orders')
        def handle_subscribe_orders(data):
            """Subscribe to order updates."""
            sid = request.sid
            conn = self._manager._connection_manager.get_connection(sid)

            if not conn:
                emit('error', {'message': 'Not authenticated'})
                return

            room = f"user:{conn.user_id}:orders"
            join(room)

            emit('subscription_success', {
                'action': 'subscribe_orders',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        @self.socketio.on('subscribe_positions')
        def handle_subscribe_positions(data):
            """Subscribe to position updates."""
            sid = request.sid
            conn = self._manager._connection_manager.get_connection(sid)

            if not conn:
                emit('error', {'message': 'Not authenticated'})
                return

            room = f"user:{conn.user_id}:positions"
            join(room)

            emit('subscription_success', {
                'action': 'subscribe_positions',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

    def _register_trading_handlers(self):
        """Trading event handlers."""

        @self.socketio.on('place_order')
        def handle_place_order(data):
            """Handle order placement."""
            sid = request.sid
            conn = self._manager._connection_manager.get_connection(sid)

            if not conn:
                emit('error', {'message': 'Not authenticated'})
                return

            rate_limiter = get_rate_limiter()
            if not rate_limiter.check_limit(conn.user_id, 'place_order'):
                emit('error', {'message': 'Rate limit exceeded'})
                return

            emit('order_received', {
                'order_id': data.get('order_id'),
                'status': 'PROCESSING',
                'message': 'Order received',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })

        @self.socketio.on('cancel_order')
        def handle_cancel_order(data):
            """Handle order cancellation."""
            sid = request.sid
            order_id = data.get('order_id')

            if not order_id:
                emit('error', {'message': 'No order_id provided'})
                return

            conn = self._manager._connection_manager.get_connection(sid)
            if conn:
                self._manager.broadcast_order_update(conn.user_id, {
                    'order_id': order_id,
                    'status': 'CANCELLED',
                    'message': 'Order cancelled'
                })

        @self.socketio.on('modify_order')
        def handle_modify_order(data):
            """Handle order modification."""
            sid = request.sid
            order_id = data.get('order_id')

            if not order_id:
                emit('error', {'message': 'No order_id provided'})
                return

            conn = self._manager._connection_manager.get_connection(sid)
            if conn:
                emit('order_modified', {
                    'order_id': order_id,
                    'status': 'MODIFIED',
                    'timestamp': datetime.now(timezone.utc).isoformat()
                })

    def _register_heartbeat_handlers(self):
        """Heartbeat handlers."""

        @self.socketio.on('ping')
        def handle_ping(data):
            """Handle ping from client."""
            sid = request.sid
            client_time = data.get('timestamp')

            self._manager.handle_heartbeat(sid, client_time)

            emit('pong', {
                'server_time': datetime.now(timezone.utc).isoformat(),
                'latency': self._calculate_latency(sid)
            })

    def _register_monitoring_handlers(self):
        """Monitoring handlers."""

        @self.socketio.on('get_stats')
        def handle_get_stats():
            """Get connection statistics."""
            stats = self._manager.get_connection_stats()
            emit('stats', stats)

        @self.socketio.on('get_online_users')
        async def handle_get_online_users():
            """Get online users across all nodes."""
            users = await self._manager.get_online_users()
            emit('online_users', {
                'count': len(users),
                'users': list(users)
            })

        @self.socketio.on('ping_server')
        def handle_ping_server():
            """Server latency check."""
            emit('pong_server', {
                'timestamp': time.time(),
                'server_time': datetime.now(timezone.utc).isoformat()
            })

    def _register_error_handlers(self):
        """Error handlers."""

        @self.socketio.on_error()
        def error_handler(e):
            logger.error(f"SocketIO Error: {e}")

        @self.socketio.on_error_connect()
        def error_connect_handler(e):
            logger.error(f"SocketIO Connection Error: {e}")

        @self.socketio.on_error_disconnect()
        def error_disconnect_handler(e):
            logger.error(f"SocketIO Disconnect Error: {e}")

        @self.socketio.on_default()
        def default_handler(event, data):
            logger.warning(f"Unhandled event: {event}")

    def _calculate_latency(self, sid: str) -> float:
        """Calculate approximate latency for session."""
        try:
            stats = get_heartbeat().get_stats()
            return stats.get('per_connection', {}).get(sid, {}).get('latency', 0)
        except Exception:
            return 0


def register_scalable_handlers(socketio, app=None):
    """Register scalable socket handlers."""
    handlers = SocketEventHandlers(socketio, app)
    handlers.register()
    return handlers
"""
WebSocket Manager for Flask-SocketIO
=====================================
Production-grade WebSocket management system for Indian trading platform.
"""

import os
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any, Callable
from flask_socketio import emit, disconnect
try:
    from flask_socketio import join_room as join, leave_room as leave
except ImportError:
    from flask_socketio import join, leave
from flask import request
import jwt
from functools import wraps

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Central WebSocket Manager for handling connections, subscriptions, and broadcasting.
    """

    def __init__(self, socketio):
        self.socketio = socketio
        self.connected_users: Dict[str, Dict] = {}
        self.user_sessions: Dict[str, Set[str]] = {}
        self.symbol_subscriptions: Dict[str, Set[str]] = {}
        self.strategy_subscriptions: Dict[str, Set[str]] = {}
        self.active_rooms: Dict[str, Set[str]] = {}
        self._heartbeat_timers: Dict[str, Any] = {}
        self._market_data_cache: Dict[str, Dict] = {}

        self.JWT_SECRET = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
        self.JWT_ALGORITHM = 'HS256'

    def initialize_handlers(self):
        """Initialize all SocketIO event handlers."""
        from . import handlers
        handlers.register_handlers(self.socketio, self)

    def authenticate_token(self, token: str) -> Optional[Dict]:
        """Validate JWT token and return user data."""
        try:
            payload = jwt.decode(token, self.JWT_SECRET, algorithms=[self.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    def register_connection(self, sid: str, user_id: str, data: Dict = None):
        """Register a new WebSocket connection."""
        self.connected_users[sid] = {
            'user_id': user_id,
            'connected_at': datetime.now(timezone.utc).isoformat(),
            'last_heartbeat': datetime.now(timezone.utc).isoformat(),
            'subscriptions': set(),
            'metadata': data or {}
        }

        if user_id not in self.user_sessions:
            self.user_sessions[user_id] = set()
        self.user_sessions[user_id].add(sid)

        logger.info(f"User {user_id} connected with session {sid}")

    def unregister_connection(self, sid: str):
        """Unregister a WebSocket connection."""
        if sid in self.connected_users:
            user_id = self.connected_users[sid].get('user_id')
            if user_id and user_id in self.user_sessions:
                self.user_sessions[user_id].discard(sid)

            for symbol, subscribers in list(self.symbol_subscriptions.items()):
                subscribers.discard(sid)

            for strategy_id, subscribers in list(self.strategy_subscriptions.items()):
                subscribers.discard(sid)

            del self.connected_users[sid]
            logger.info(f"Session {sid} disconnected")

    def join_user_room(self, sid: str, user_id: str):
        """Join user to their personal room."""
        room = f"user:{user_id}"
        join(room)
        if room not in self.active_rooms:
            self.active_rooms[room] = set()
        self.active_rooms[room].add(sid)
        logger.info(f"Session {sid} joined room {room}")

    def leave_user_room(self, sid: str, user_id: str):
        """Leave user from their personal room."""
        room = f"user:{user_id}"
        leave(room)
        if room in self.active_rooms:
            self.active_rooms[room].discard(sid)

    def subscribe_market(self, sid: str, symbols: List[str]):
        """Subscribe to market data for symbols."""
        for symbol in symbols:
            symbol_upper = symbol.upper()
            if symbol_upper not in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol_upper] = set()
            self.symbol_subscriptions[symbol_upper].add(sid)

            if sid in self.connected_users:
                self.connected_users[sid]['subscriptions'].add(symbol_upper)

            room = f"market:{symbol_upper}"
            join(room)
            if room not in self.active_rooms:
                self.active_rooms[room] = set()
            self.active_rooms[room].add(sid)

        logger.info(f"Session {sid} subscribed to {len(symbols)} symbols")

    def unsubscribe_market(self, sid: str, symbols: List[str]):
        """Unsubscribe from market data for symbols."""
        for symbol in symbols:
            symbol_upper = symbol.upper()
            if symbol_upper in self.symbol_subscriptions:
                self.symbol_subscriptions[symbol_upper].discard(sid)
                if not self.symbol_subscriptions[symbol_upper]:
                    del self.symbol_subscriptions[symbol_upper]

            if sid in self.connected_users:
                self.connected_users[sid]['subscriptions'].discard(symbol_upper)

            room = f"market:{symbol_upper}"
            leave(room)
            if room in self.active_rooms:
                self.active_rooms[room].discard(sid)

        logger.info(f"Session {sid} unsubscribed from {len(symbols)} symbols")

    def subscribe_strategy(self, sid: str, strategy_id: str):
        """Subscribe to strategy updates."""
        if strategy_id not in self.strategy_subscriptions:
            self.strategy_subscriptions[strategy_id] = set()
        self.strategy_subscriptions[strategy_id].add(sid)

        if sid in self.connected_users:
            self.connected_users[sid]['subscriptions'].add(f"strategy:{strategy_id}")

        room = f"strategy:{strategy_id}"
        join(room)

    def unsubscribe_strategy(self, sid: str, strategy_id: str):
        """Unsubscribe from strategy updates."""
        if strategy_id in self.strategy_subscriptions:
            self.strategy_subscriptions[strategy_id].discard(sid)

        if sid in self.connected_users:
            self.connected_users[sid]['subscriptions'].discard(f"strategy:{strategy_id}")

        room = f"strategy:{strategy_id}"
        leave(room)

    def emit_to_user(self, user_id: str, event: str, data: Dict):
        """Emit event to all sessions of a user."""
        if user_id in self.user_sessions:
            for sid in self.user_sessions[user_id]:
                self.socketio.emit(event, data, room=sid)

    def emit_to_symbol(self, symbol: str, event: str, data: Dict):
        """Emit event to all subscribers of a symbol."""
        symbol_upper = symbol.upper()
        if symbol_upper in self.symbol_subscriptions:
            for sid in self.symbol_subscriptions[symbol_upper]:
                self.socketio.emit(event, data, room=sid)

    def emit_to_all(self, event: str, data: Dict):
        """Emit event to all connected clients."""
        self.socketio.emit(event, data, namespace='/')

    def broadcast_market_tick(self, symbol: str, data: Dict):
        """Broadcast market tick to symbol subscribers."""
        payload = {
            'event': 'market_tick',
            'data': {
                'symbol': symbol.upper(),
                'last_price': data.get('last_price', 0),
                'change': data.get('change', 0),
                'change_percent': data.get('change_percent', 0),
                'volume': data.get('volume', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        self.emit_to_symbol(symbol, 'market_tick', payload['data'])

    def broadcast_order_update(self, user_id: str, order_data: Dict):
        """Broadcast order update to user."""
        payload = {
            'event': 'order_update',
            'data': {
                'order_id': order_data.get('order_id'),
                'status': order_data.get('status'),
                'filled_quantity': order_data.get('filled_quantity', 0),
                'average_price': order_data.get('average_price'),
                'message': order_data.get('message', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        self.emit_to_user(user_id, 'order_update', payload['data'])

    def broadcast_position_update(self, user_id: str, position_data: Dict):
        """Broadcast position update to user."""
        payload = {
            'event': 'position_update',
            'data': {
                'position_id': position_data.get('position_id'),
                'symbol': position_data.get('symbol'),
                'quantity': position_data.get('quantity'),
                'current_price': position_data.get('current_price'),
                'unrealized_pnl': position_data.get('unrealized_pnl', 0),
                'pnl_percent': position_data.get('pnl_percent', 0),
                'day_pnl': position_data.get('day_pnl', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        self.emit_to_user(user_id, 'position_update', payload['data'])

    def broadcast_pnl_update(self, user_id: str, pnl_data: Dict):
        """Broadcast P&L update to user."""
        payload = {
            'event': 'pnl_update',
            'data': {
                'total_pnl': pnl_data.get('total_pnl', 0),
                'day_pnl': pnl_data.get('day_pnl', 0),
                'unrealized_pnl': pnl_data.get('unrealized_pnl', 0),
                'realized_pnl': pnl_data.get('realized_pnl', 0),
                'margin_used': pnl_data.get('margin_used', 0),
                'available_cash': pnl_data.get('available_cash', 0),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        self.emit_to_user(user_id, 'pnl_update', payload['data'])

    def broadcast_notification(self, user_id: str, notification_data: Dict):
        """Broadcast notification to user."""
        payload = {
            'event': 'notification',
            'data': {
                'notification_id': notification_data.get('notification_id'),
                'type': notification_data.get('type', 'SYSTEM'),
                'title': notification_data.get('title'),
                'message': notification_data.get('message'),
                'priority': notification_data.get('priority', 'MEDIUM'),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        self.emit_to_user(user_id, 'notification', payload['data'])

    def broadcast_ai_signal(self, signal_data: Dict):
        """Broadcast AI trading signal to subscribers."""
        payload = {
            'event': 'ai_signal',
            'data': {
                'signal_id': signal_data.get('signal_id'),
                'symbol': signal_data.get('symbol'),
                'action': signal_data.get('action'),
                'confidence': signal_data.get('confidence', 0),
                'target_price': signal_data.get('target_price'),
                'stop_loss': signal_data.get('stop_loss'),
                'reasoning': signal_data.get('reasoning', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        self.emit_to_all('ai_signal', payload['data'])

    def broadcast_strategy_signal(self, strategy_id: str, signal_data: Dict):
        """Broadcast strategy signal to subscribers."""
        payload = {
            'event': 'strategy_update',
            'data': {
                'strategy_id': strategy_id,
                'status': signal_data.get('status'),
                'signal': signal_data.get('signal'),
                'message': signal_data.get('message', ''),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        }
        room = f"strategy:{strategy_id}"
        self.socketio.emit('strategy_update', payload['data'], room=room)

    def send_heartbeat_response(self, sid: str):
        """Send heartbeat response to client."""
        if sid in self.connected_users:
            self.connected_users[sid]['last_heartbeat'] = datetime.now(timezone.utc).isoformat()
        self.socketio.emit('heartbeat', {'timestamp': datetime.now(timezone.utc).isoformat()}, room=sid)

    def get_connected_users_count(self) -> int:
        """Get count of connected users."""
        return len(set(u.get('user_id') for u in self.connected_users.values() if u.get('user_id')))

    def get_active_symbols_count(self) -> int:
        """Get count of actively subscribed symbols."""
        return len(self.symbol_subscriptions)

    def get_connection_stats(self) -> Dict:
        """Get connection statistics."""
        return {
            'total_connections': len(self.connected_users),
            'unique_users': self.get_connected_users_count(),
            'active_symbols': self.get_active_symbols_count(),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


ws_manager: Optional[WebSocketManager] = None


def get_ws_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global ws_manager
    if ws_manager is None:
        raise RuntimeError("WebSocket manager not initialized")
    return ws_manager


def init_websocket_manager(socketio) -> WebSocketManager:
    """Initialize the WebSocket manager."""
    global ws_manager
    ws_manager = WebSocketManager(socketio)
    return ws_manager
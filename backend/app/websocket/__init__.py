"""
WebSocket Module
===============
WebSocket handling for realtime trading.
"""

from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*", async_mode='eventlet')


def init_socketio(app):
    """Initialize SocketIO with the Flask app."""
    from .socket_manager import init_websocket_manager

    socketio.init_app(app, message_queue=None, channel='websocket')
    init_socketio_manager(socketio)
    return socketio

from app.websocket.handlers import register_handlers
from app.websocket.events import emit_price, emit_trade, emit_signal, emit_position, emit_notification

__all__ = ['register_handlers', 'emit_price', 'emit_trade', 'emit_signal', 'emit_position', 'emit_notification']
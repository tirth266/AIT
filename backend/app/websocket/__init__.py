"""
WebSocket Module
================
WebSocket handling for realtime trading.
"""

import os

frontend_origin = os.environ.get('FRONTEND_URL', 'http://localhost:5173')

from app.websocket.handlers import register_handlers

# emit helpers live in market_events.py, not events.py
try:
    from app.websocket.market_events import (
        emit_price,
        emit_trade,
        emit_signal,
        emit_position,
        emit_notification,
    )
except ImportError:
    # Provide no-op stubs so the rest of the app doesn't break
    def emit_price(*a, **kw): pass
    def emit_trade(*a, **kw): pass
    def emit_signal(*a, **kw): pass
    def emit_position(*a, **kw): pass
    def emit_notification(*a, **kw): pass

__all__ = [
    'register_handlers',
    'emit_price', 'emit_trade', 'emit_signal',
    'emit_position', 'emit_notification',
]
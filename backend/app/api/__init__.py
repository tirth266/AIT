"""
API Module
==========
API blueprints and route handlers.
"""

from . import (
    auth, strategies, trades, orders, watchlist,
    ai_signals, notifications, funds, bot, broker,
    backtest, market, settings, dashboard, health
)

__all__ = [
    'auth',
    'strategies',
    'trades',
    'orders',
    'watchlist',
    'ai_signals',
    'notifications',
    'funds',
    'bot',
    'broker',
    'backtest',
    'market',
    'settings',
    'dashboard',
    'health'
]

"""
Data Formatters
===============
Formatting utilities for display and API responses.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional


def format_price(price: float, decimals: int = 2) -> str:
    """Format price for display."""
    return f"{price:,.{decimals}f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format percentage for display."""
    return f"{value:.{decimals}f}%"


def format_currency(amount: float, currency: str = 'USD') -> str:
    """Format currency amount."""
    symbols = {'USD': '$', 'USDT': '₮', 'INR': '₹', 'EUR': '€', 'GBP': '£'}
    symbol = symbols.get(currency, currency)
    return f"{symbol}{amount:,.2f}"


def format_timeframe(timeframe: str) -> str:
    """Format timeframe for display."""
    mapping = {
        '1m': '1 Minute',
        '5m': '5 Minutes',
        '15m': '15 Minutes',
        '30m': '30 Minutes',
        '1h': '1 Hour',
        '4h': '4 Hours',
        '1d': '1 Day',
        '1w': '1 Week'
    }
    return mapping.get(timeframe, timeframe)


def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format datetime for display."""
    if isinstance(dt, str):
        return dt
    return dt.strftime(format_str)


def format_pnl(pnl: float, color: bool = True) -> str:
    """Format PnL for display."""
    sign = '+' if pnl > 0 else ''
    formatted = f"{sign}{pnl:.2f}"

    if color:
        color_code = '\033[92m' if pnl > 0 else '\033[91m' if pnl < 0 else '\033[0m'
        reset = '\033[0m'
        return f"{color_code}{formatted}{reset}"

    return formatted


def format_trade_side(side: str) -> str:
    """Format trade side."""
    return side.upper()


def format_order_type(order_type: str) -> str:
    """Format order type."""
    return order_type.lower()


def format_candle(candle: Dict) -> Dict:
    """Format candle data for API response."""
    return {
        'timestamp': candle.get('timestamp'),
        'open': float(candle.get('open', 0)),
        'high': float(candle.get('high', 0)),
        'low': float(candle.get('low', 0)),
        'close': float(candle.get('close', 0)),
        'volume': float(candle.get('volume', 0))
    }


def format_position(position: Dict) -> Dict:
    """Format position for API response."""
    return {
        'id': str(position.get('_id')),
        'symbol': position.get('symbol'),
        'side': position.get('side'),
        'quantity': float(position.get('quantity', 0)),
        'entry_price': float(position.get('entry_price', 0)),
        'current_price': float(position.get('current_price', 0)),
        'unrealized_pnl': float(position.get('unrealized_pnl', 0)),
        'unrealized_pnl_percent': float(position.get('unrealized_pnl_percent', 0)),
        'stop_loss': position.get('stop_loss'),
        'take_profit': position.get('take_profit'),
        'mode': position.get('mode'),
        'opened_at': str(position.get('opened_at')) if position.get('opened_at') else None
    }


def format_trade(trade: Dict) -> Dict:
    """Format trade for API response."""
    return {
        'id': str(trade.get('_id')),
        'symbol': trade.get('symbol'),
        'side': trade.get('side'),
        'entry_price': float(trade.get('entry_price', 0)),
        'exit_price': float(trade.get('exit_price', 0)) if trade.get('exit_price') else None,
        'quantity': float(trade.get('quantity', 0)),
        'pnl': float(trade.get('pnl', 0)),
        'pnl_percent': float(trade.get('pnl_percent', 0)),
        'status': trade.get('status'),
        'mode': trade.get('mode'),
        'entry_time': str(trade.get('entry_time')) if trade.get('entry_time') else None,
        'exit_time': str(trade.get('exit_time')) if trade.get('exit_time') else None
    }


def truncate_string(text: str, max_length: int = 50) -> str:
    """Truncate string to max length."""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + '...'


def format_error_response(error: str, code: str = 'ERROR') -> Dict:
    """Format error response."""
    return {
        'error': code,
        'message': error,
        'timestamp': datetime.utcnow().isoformat()
    }
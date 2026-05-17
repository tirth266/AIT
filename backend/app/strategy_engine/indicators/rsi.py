"""
Relative Strength Index (RSI)
==============================
"""

from typing import List, Dict
import numpy as np


def calculate_rsi(data: List[float], period: int = 14) -> List[float]:
    """
    Calculate Relative Strength Index.

    Args:
        data: List of closing prices
        period: RSI period (default 14)

    Returns:
        List of RSI values
    """
    if not data or len(data) < period + 1:
        return []

    prices = np.array(data)
    deltas = np.diff(prices)

    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    rsi_values = []

    if avg_loss == 0:
        rsi_values.append(100)
    else:
        rs = avg_gain / avg_loss
        rsi_values.append(100 - (100 / (1 + rs)))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            rsi_values.append(100)
        else:
            rs = avg_gain / avg_loss
            rsi_values.append(100 - (100 / (1 + rs)))

    return rsi_values


def get_rsi_signal(data: List[float], period: int = 14,
                   oversold: float = 30, overbought: float = 70) -> Dict[str, any]:
    """
    Get RSI-based trading signal.

    Args:
        data: List of closing prices
        period: RSI period
        oversold: Oversold threshold
        overbought: Overbought threshold

    Returns:
        Dict with signal and reasoning
    """
    rsi_values = calculate_rsi(data, period)

    if not rsi_values:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_rsi = rsi_values[-1]

    if current_rsi < oversold:
        signal = 'BUY'
        reason = f'RSI at {current_rsi:.1f} indicates oversold condition'
    elif current_rsi > overbought:
        signal = 'SELL'
        reason = f'RSI at {current_rsi:.1f} indicates overbought condition'
    else:
        signal = 'HOLD'
        reason = f'RSI at {current_r1:.1f} in neutral zone'

    return {
        'signal': signal,
        'reason': reason,
        'rsi': current_rsi,
        'oversold': oversold,
        'overbought': overbought
    }


def calculate_rsi_divergence(
    data: List[float],
    period: int = 14,
    lookback: int = 20
) -> Dict[str, any]:
    """
    Detect RSI divergence (advanced).

    Args:
        data: List of closing prices
        period: RSI period
        lookback: Number of bars to check for divergence

    Returns:
        Dict with divergence signal
    """
    rsi_values = calculate_rsi(data, period)

    if not rsi_values or len(rsi_values) < lookback:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    recent_prices = data[-lookback:]
    recent_rsi = rsi_values[-lookback:]

    price_high_idx = np.argmax(recent_prices)
    rsi_high_idx = np.argmax(recent_rsi)

    price_low_idx = np.argmin(recent_prices)
    rsi_low_idx = np.argmin(recent_rsi)

    if price_high_idx > rsi_high_idx:
        return {'signal': 'SELL', 'reason': 'Bearish divergence detected'}
    elif price_low_idx < rsi_low_idx:
        return {'signal': 'BUY', 'reason': 'Bullish divergence detected'}

    return {'signal': 'HOLD', 'reason': 'No divergence detected'}
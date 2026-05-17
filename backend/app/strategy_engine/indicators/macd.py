"""
MACD (Moving Average Convergence Divergence)
============================================
"""

from typing import List, Dict
import numpy as np


def calculate_macd(
    data: List[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, List[float]]:
    """
    Calculate MACD indicator.

    Args:
        data: List of closing prices
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period

    Returns:
        Dict with 'macd', 'signal', and 'histogram' arrays
    """
    if not data or len(data) < slow_period:
        return {'macd': [], 'signal': [], 'histogram': []}

    prices = np.array(data)

    def ema(arr, period):
        result = np.zeros(len(arr))
        result[0] = arr[0]
        multiplier = 2 / (period + 1)
        for i in range(1, len(arr)):
            result[i] = (arr[i] - result[i - 1]) * multiplier + result[i - 1]
        return result

    ema_fast = ema(prices, fast_period)
    ema_slow = ema(prices, slow_period)

    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal_period)
    histogram = macd_line - signal_line

    return {
        'macd': macd_line.tolist(),
        'signal': signal_line.tolist(),
        'histogram': histogram.tolist()
    }


def get_macd_signal(data: List[float]) -> Dict[str, any]:
    """
    Get MACD-based trading signal.

    Args:
        data: List of closing prices

    Returns:
        Dict with signal and reasoning
    """
    result = calculate_macd(data)

    if not result['macd']:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    macd = result['macd'][-1]
    signal = result['signal'][-1]
    histogram = result['histogram'][-1]

    prev_macd = result['macd'][-2] if len(result['macd']) > 1 else macd
    prev_signal = result['signal'][-2] if len(result['signal']) > 1 else signal

    if prev_macd <= prev_signal and macd > signal:
        signal = 'BUY'
        reason = 'MACD crossed above signal line'
    elif prev_macd >= prev_signal and macd < signal:
        signal = 'SELL'
        reason = 'MACD crossed below signal line'
    elif histogram > 0 and histogram > result['histogram'][-2]:
        signal = 'BUY'
        reason = 'MACD histogram expanding upward'
    elif histogram < 0 and histogram < result['histogram'][-2]:
        signal = 'SELL'
        reason = 'MACD histogram expanding downward'
    else:
        signal = 'HOLD'
        reason = 'No clear signal'

    return {
        'signal': signal,
        'reason': reason,
        'macd': macd,
        'signal_line': signal,
        'histogram': histogram
    }
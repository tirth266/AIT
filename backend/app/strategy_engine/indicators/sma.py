"""
Simple Moving Average (SMA)
===========================
"""

from typing import List
import numpy as np


def calculate_sma(data: List[float], period: int = 20) -> List[float]:
    """
    Calculate Simple Moving Average.

    Args:
        data: List of closing prices
        period: SMA period

    Returns:
        List of SMA values
    """
    if not data or len(data) < period:
        return []

    prices = np.array(data)
    sma = np.convolve(prices, np.ones(period) / period, mode='valid')
    return sma.tolist()


def calculate_sma_crossover(
    data: List[float],
    short_period: int = 20,
    long_period: int = 50
) -> Dict[str, any]:
    """
    Calculate SMA crossover signals.

    Args:
        data: List of closing prices
        short_period: Short SMA period
        long_period: Long SMA period

    Returns:
        Dict with crossover signals
    """
    sma_short = calculate_sma(data, short_period)
    sma_long = calculate_sma(data, long_period)

    if not sma_short or not sma_long:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_short = sma_short[-1]
    current_long = sma_long[-1]
    prev_short = sma_short[-2] if len(sma_short) > 1 else current_short
    prev_long = sma_long[-2] if len(sma_long) > 1 else current_long

    if prev_short <= prev_long and current_short > current_long:
        signal = 'BUY'
        reason = f'SMA {short_period} crossed above SMA {long_period}'
    elif prev_short >= prev_long and current_short < current_long:
        signal = 'SELL'
        reason = f'SMA {short_period} crossed below SMA {long_period}'
    else:
        signal = 'HOLD'
        reason = 'No crossover detected'

    return {
        'signal': signal,
        'reason': reason,
        'sma_short': current_short,
        'sma_long': current_long
    }
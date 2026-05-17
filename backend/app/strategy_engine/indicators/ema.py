"""
Exponential Moving Average (EMA)
=================================
"""

from typing import List
import numpy as np


def calculate_ema(data: List[float], period: int = 9) -> List[float]:
    """
    Calculate Exponential Moving Average.

    Args:
        data: List of closing prices
        period: EMA period

    Returns:
        List of EMA values
    """
    if not data or len(data) < period:
        return []

    prices = np.array(data)
    ema = np.zeros(len(prices))
    ema[0] = prices[0]

    multiplier = 2 / (period + 1)

    for i in range(1, len(prices)):
        ema[i] = (prices[i] - ema[i - 1]) * multiplier + ema[i - 1]

    return ema.tolist()


def calculate_ema_crossover(
    data: List[float],
    short_period: int = 9,
    long_period: int = 21
) -> Dict[str, any]:
    """
    Calculate EMA crossover signals.

    Args:
        data: List of closing prices
        short_period: Short EMA period
        long_period: Long EMA period

    Returns:
        Dict with crossover signals
    """
    ema_short = calculate_ema(data, short_period)
    ema_long = calculate_ema(data, long_period)

    if not ema_short or not ema_long:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_short = ema_short[-1]
    current_long = ema_long[-1]
    prev_short = ema_short[-2] if len(ema_short) > 1 else current_short
    prev_long = ema_long[-2] if len(ema_long) > 1 else current_long

    if prev_short <= prev_long and current_short > current_long:
        signal = 'BUY'
        reason = f'EMA {short_period} crossed above EMA {long_period}'
    elif prev_short >= prev_long and current_short < current_long:
        signal = 'SELL'
        reason = f'EMA {short_period} crossed below EMA {long_period}'
    else:
        signal = 'HOLD'
        reason = 'No crossover detected'

    return {
        'signal': signal,
        'reason': reason,
        'ema_short': current_short,
        'ema_long': current_long
    }
"""
Supertrend Indicator
====================
"""

from typing import List, Dict
import numpy as np


def calculate_supertrend(
    candles: List[Dict],
    period: int = 10,
    multiplier: float = 3.0
) -> Dict[str, List]:
    """
    Calculate Supertrend indicator.

    Args:
        candles: List of OHLCV candles
        period: ATR period
        multiplier: ATR multiplier

    Returns:
        Dict with 'value' and 'direction' arrays
    """
    if not candles or len(candles) < period + 1:
        return {'value': [], 'direction': []}

    highs = np.array([c.get('high', 0) for c in candles])
    lows = np.array([c.get('low', 0) for c in candles])
    closes = np.array([c.get('close', 0) for c in candles])

    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )

    atr = np.zeros(len(tr))
    atr[0] = np.mean(tr[:period])
    for i in range(period, len(tr)):
        atr[i] = (atr[i - 1] * (period - 1) + tr[i]) / period

    hl_avg = (highs + lows) / 2

    upper_band = hl_avg[period:] + multiplier * atr
    lower_band = hl_avg[period:] - multiplier * atr

    supertrend = np.zeros(len(closes) - period)
    direction = np.zeros(len(closes) - period)

    supertrend[0] = upper_band[0]
    direction[0] = 1

    for i in range(1, len(supertrend)):
        if closes[period + i] > supertrend[i - 1]:
            direction[i] = 1
            supertrend[i] = lower_band[i]
        else:
            direction[i] = -1
            supertrend[i] = upper_band[i]

        if direction[i] == 1:
            supertrend[i] = max(supertrend[i], lower_band[i])
        else:
            supertrend[i] = min(supertrend[i], upper_band[i])

    return {
        'value': supertrend.tolist(),
        'direction': direction.tolist()
    }


def get_supertrend_signal(candles: List[Dict]) -> Dict[str, any]:
    """
    Get Supertrend trading signal.

    Args:
        candles: List of OHLCV candles

    Returns:
        Dict with signal and reasoning
    """
    result = calculate_supertrend(candles)

    if not result['value']:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_price = candles[-1].get('close', 0)
    supertrend_value = result['value'][-1]
    direction = result['direction'][-1]

    if direction > 0:
        signal = 'BUY'
        reason = 'Supertrend in bullish phase'
    else:
        signal = 'SELL'
        reason = 'Supertrend in bearish phase'

    return {
        'signal': signal,
        'reason': reason,
        'supertrend': supertrend_value,
        'direction': 'BULLISH' if direction > 0 else 'BEARISH'
    }
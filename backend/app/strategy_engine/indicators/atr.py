"""
Average True Range (ATR)
========================
"""

from typing import List, Dict
import numpy as np


def calculate_atr(candles: List[Dict], period: int = 14) -> List[float]:
    """
    Calculate Average True Range.

    Args:
        candles: List of OHLCV candles
        period: ATR period

    Returns:
        List of ATR values
    """
    if not candles or len(candles) < period + 1:
        return []

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

    return atr.tolist()


def get_atr_signal(candles: List[Dict], multiplier: float = 2.0) -> Dict[str, any]:
    """
    Get ATR-based volatility signal.

    Args:
        candles: List of OHLCV candles
        multiplier: ATR multiplier for signals

    Returns:
        Dict with volatility analysis
    """
    atr_values = calculate_atr(candles)

    if not atr_values:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_atr = atr_values[-1]
    current_price = candles[-1].get('close', 0)

    if current_price > 0:
        atr_percent = (current_atr / current_price) * 100

        if atr_percent > 3:
            volatility = 'HIGH'
            reason = f'High volatility - ATR {atr_percent:.2f}% of price'
        elif atr_percent > 1.5:
            volatility = 'MEDIUM'
            reason = f'Medium volatility - ATR {atr_percent:.2f}% of price'
        else:
            volatility = 'LOW'
            reason = f'Low volatility - ATR {atr_percent:.2f}% of price'
    else:
        volatility = 'UNKNOWN'
        reason = 'Unable to calculate ATR percentage'

    return {
        'signal': 'HOLD',
        'reason': reason,
        'atr': current_atr,
        'volatility': volatility
    }
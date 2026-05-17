"""
Volume Weighted Average Price (VWAP)
====================================
"""

from typing import List, Dict
import numpy as np


def calculate_vwap(candles: List[Dict]) -> List[float]:
    """
    Calculate Volume Weighted Average Price.

    Args:
        candles: List of OHLCV candles

    Returns:
        List of VWAP values
    """
    if not candles:
        return []

    vwap = []
    cumulative_tpv = 0
    cumulative_volume = 0

    for candle in candles:
        high = candle.get('high', 0)
        low = candle.get('low', 0)
        close = candle.get('close', 0)
        volume = candle.get('volume', 0)

        typical_price = (high + low + close) / 3

        cumulative_tpv += typical_price * volume
        cumulative_volume += volume

        if cumulative_volume > 0:
            vwap.append(cumulative_tpv / cumulative_volume)
        else:
            vwap.append(typical_price)

    return vwap


def get_vwap_signal(candles: List[Dict]) -> Dict[str, any]:
    """
    Get VWAP-based trading signal.

    Args:
        candles: List of OHLCV candles

    Returns:
        Dict with signal and reasoning
    """
    vwap_values = calculate_vwap(candles)

    if not vwap_values:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_price = candles[-1].get('close', 0)
    current_vwap = vwap_values[-1]

    if current_price > current_vwap:
        signal = 'BUY'
        reason = f'Price above VWAP ({current_vwap:.2f}) - bullish'
    elif current_price < current_vwap:
        signal = 'SELL'
        reason = f'Price below VWAP ({current_vwap:.2f}) - bearish'
    else:
        signal = 'HOLD'
        reason = 'Price at VWAP - neutral'

    return {
        'signal': signal,
        'reason': reason,
        'price': current_price,
        'vwap': current_vwap
    }
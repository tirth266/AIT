"""
Bollinger Bands
===============
"""

from typing import List, Dict
import numpy as np


def calculate_bollinger_bands(
    data: List[float],
    period: int = 20,
    num_std: float = 2.0
) -> Dict[str, List[float]]:
    """
    Calculate Bollinger Bands.

    Args:
        data: List of closing prices
        period: Moving average period
        num_std: Number of standard deviations

    Returns:
        Dict with 'upper', 'middle', and 'lower' bands
    """
    if not data or len(data) < period:
        return {'upper': [], 'middle': [], 'lower': []}

    prices = np.array(data)

    middle = np.convolve(prices, np.ones(period) / period, mode='valid')

    upper = []
    lower = []

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1:i + 1]
        std = np.std(window)
        mid = middle[i - period + 1]
        upper.append(mid + num_std * std)
        lower.append(mid - num_std * std)

    return {
        'upper': upper,
        'middle': middle.tolist(),
        'lower': lower
    }


def get_bollinger_signal(data: List[float]) -> Dict[str, any]:
    """
    Get Bollinger Bands trading signal.

    Args:
        data: List of closing prices

    Returns:
        Dict with signal and reasoning
    """
    if not data:
        return {'signal': 'HOLD', 'reason': 'No data'}

    current_price = data[-1]

    result = calculate_bollinger_bands(data)

    if not result['upper']:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    upper = result['upper'][-1]
    middle = result['middle'][-1]
    lower = result['lower'][-1]

    if current_price <= lower:
        signal = 'BUY'
        reason = 'Price at lower Bollinger Band - oversold'
    elif current_price >= upper:
        signal = 'SELL'
        reason = 'Price at upper Bollinger Band - overbought'
    elif current_price > middle and current_price < upper:
        signal = 'BUY'
        reason = 'Price in upper half of bands - bullish momentum'
    elif current_price < middle and current_price > lower:
        signal = 'SELL'
        reason = 'Price in lower half of bands - bearish momentum'
    else:
        signal = 'HOLD'
        reason = 'Price near middle band'

    return {
        'signal': signal,
        'reason': reason,
        'price': current_price,
        'upper': upper,
        'middle': middle,
        'lower': lower
    }
"""
Stochastic Oscillator
=====================
"""

from typing import List, Dict
import numpy as np


def calculate_stochastic(
    candles: List[Dict],
    k_period: int = 14,
    d_period: int = 3
) -> Dict[str, List[float]]:
    """
    Calculate Stochastic Oscillator.

    Args:
        candles: List of OHLCV candles
        k_period: %K period
        d_period: %D period

    Returns:
        Dict with 'k' and 'd' arrays
    """
    if not candles or len(candles) < k_period:
        return {'k': [], 'd': []}

    highs = [c.get('high', 0) for c in candles]
    lows = [c.get('low', 0) for c in candles]
    closes = [c.get('close', 0) for c in candles]

    k_values = []

    for i in range(k_period - 1, len(closes)):
        highest = max(highs[i - k_period + 1:i + 1])
        lowest = min(lows[i - k_period + 1:i + 1])

        if highest != lowest:
            stoch_k = ((closes[i] - lowest) / (highest - lowest)) * 100
        else:
            stoch_k = 50

        k_values.append(stoch_k)

    if len(k_values) < d_period:
        return {'k': k_values, 'd': k_values}

    d_values = []
    for i in range(len(k_values) - d_period + 1):
        d_value = np.mean(k_values[i:i + d_period])
        d_values.append(d_value)

    k_padded = [50.0] * (k_period - 1) + k_values

    return {
        'k': k_values,
        'd': d_values
    }


def get_stochastic_signal(
    candles: List[Dict],
    oversold: float = 20,
    overbought: float = 80
) -> Dict[str, any]:
    """
    Get Stochastic-based trading signal.

    Args:
        candles: List of OHLCV candles
        oversold: Oversold threshold
        overbought: Overbought threshold

    Returns:
        Dict with signal and reasoning
    """
    result = calculate_stochastic(candles)

    if not result['k']:
        return {'signal': 'HOLD', 'reason': 'Insufficient data'}

    current_k = result['k'][-1]
    current_d = result['d'][-1] if result['d'] else current_k

    prev_k = result['k'][-2] if len(result['k']) > 1 else current_k
    prev_d = result['d'][-2] if len(result['d']) > 1 else prev_k

    if current_k < oversold and current_d < oversold:
        if prev_k < current_k:
            signal = 'BUY'
            reason = f'Stochastic oversold (%K: {current_k:.1f}) and turning up'
        else:
            signal = 'HOLD'
            reason = f'Stochastic oversold (%K: {current_k:.1f}) but still falling'
    elif current_k > overbought and current_d > overbought:
        if prev_k > current_k:
            signal = 'SELL'
            reason = f'Stochastic overbought (%K: {current_k:.1f}) and turning down'
        else:
            signal = 'HOLD'
            reason = f'Stochastic overbought (%K: {current_k:.1f}) but still rising'
    elif prev_k <= prev_d and current_k > current_d:
        signal = 'BUY'
        reason = '%K crossed above %D'
    elif prev_k >= prev_d and current_k < current_d:
        signal = 'SELL'
        reason = '%K crossed below %D'
    else:
        signal = 'HOLD'
        reason = 'No clear signal'

    return {
        'signal': signal,
        'reason': reason,
        'k': current_k,
        'd': current_d
    }
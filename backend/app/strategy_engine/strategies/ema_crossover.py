"""
EMA Crossover Strategy
=======================
Buy when faster EMA crosses above slower EMA, sell when it crosses below.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime

from .base import BaseStrategy
from ..indicators.registry import IndicatorRegistry


class EMACrossoverStrategy(BaseStrategy):
    """
    EMA Crossover Strategy

    Entry Rules:
    - BUY when fast EMA crosses above slow EMA
    - SELL when fast EMA crosses below slow EMA

    Parameters:
    - fast_period: Fast EMA period (default: 9)
    - slow_period: Slow EMA period (default: 21)
    """

    def __init__(self):
        super().__init__()
        self.indicators = IndicatorRegistry()

    async def generate(
        self,
        candles: List[Dict],
        params: Dict[str, Any],
        symbol: str
    ) -> Optional[Dict]:
        """Generate trading signal."""
        if not self.validate_candles(candles, 50):
            return None

        fast_period = params.get('fast_period', 9)
        slow_period = params.get('slow_period', 21)

        closes = [c.get('close', 0) for c in candles]

        ema_fast = self.indicators.calculate('EMA', closes, period=fast_period)
        ema_slow = self.indicators.calculate('EMA', closes, period=slow_period)

        if not ema_fast or not ema_slow:
            return None

        current_fast = ema_fast[-1]
        current_slow = ema_slow[-1]
        prev_fast = ema_fast[-2] if len(ema_fast) > 1 else current_fast
        prev_slow = ema_slow[-2] if len(ema_slow) > 1 else current_slow

        current_price = closes[-1]

        if prev_fast <= prev_slow and current_fast > current_slow:
            action = 'BUY'
            reasoning = f'EMA {fast_period} crossed above EMA {slow_period}'
            confidence = 75
        elif prev_fast >= prev_slow and current_fast < current_slow:
            action = 'SELL'
            reasoning = f'EMA {fast_period} crossed below EMA {slow_period}'
            confidence = 75
        else:
            if current_fast > current_slow:
                action = 'HOLD'
                reasoning = f'EMA {fast_period} above EMA {slow_period} - no new signal'
                confidence = 50
            else:
                action = 'HOLD'
                reasoning = f'EMA {fast_period} below EMA {slow_period} - no new signal'
                confidence = 50

        signal = self.create_signal(
            action=action,
            entry_price=current_price,
            confidence=confidence,
            reasoning=reasoning,
            indicators={
                'ema_fast': current_fast,
                'ema_slow': current_slow,
                'ema_fast_prev': prev_fast,
                'ema_slow_prev': prev_slow
            },
            timeframe='1m'
        )

        signal['symbol'] = symbol

        return signal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            'fast_period': {'type': 'int', 'default': 9, 'min': 5, 'max': 50},
            'slow_period': {'type': 'int', 'default': 21, 'min': 10, 'max': 200}
        }
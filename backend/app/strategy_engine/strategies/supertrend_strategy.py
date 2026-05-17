"""
Supertrend Strategy
==================
Trade based on Supertrend indicator direction.
"""

from typing import Dict, List, Optional, Any

from .base import BaseStrategy
from ..indicators.registry import IndicatorRegistry


class SupertrendStrategy(BaseStrategy):
    """
    Supertrend Strategy

    Entry Rules:
    - BUY when Supertrend changes from bearish to bullish
    - SELL when Supertrend changes from bullish to bearish

    Parameters:
    - period: ATR period (default: 10)
    - multiplier: ATR multiplier (default: 3)
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
        if not self.validate_candles(candles, 30):
            return None

        period = params.get('period', 10)
        multiplier = params.get('multiplier', 3.0)

        supertrend_result = self.indicators.calculate(
            'Supertrend',
            candles,
            period=period,
            multiplier=multiplier
        )

        if not supertrend_result.get('value'):
            return None

        values = supertrend_result.get('value', [])
        directions = supertrend_result.get('direction', [])

        current_value = values[-1]
        current_direction = directions[-1]
        prev_direction = directions[-2] if len(directions) > 1 else current_direction

        current_price = candles[-1].get('close', 0)

        if prev_direction < 0 and current_direction > 0:
            action = 'BUY'
            reasoning = 'Supertrend changed to bullish'
            confidence = 80

        elif prev_direction > 0 and current_direction < 0:
            action = 'SELL'
            reasoning = 'Supertrend changed to bearish'
            confidence = 80

        elif current_direction > 0:
            action = 'BUY'
            reasoning = 'Supertrend in bullish phase'
            confidence = 60

        elif current_direction < 0:
            action = 'SELL'
            reasoning = 'Supertrend in bearish phase'
            confidence = 60

        else:
            action = 'HOLD'
            reasoning = 'Supertrend direction unclear'
            confidence = 30

        signal = self.create_signal(
            action=action,
            entry_price=current_price,
            confidence=confidence,
            reasoning=reasoning,
            indicators={
                'supertrend': current_value,
                'direction': 'BULLISH' if current_direction > 0 else 'BEARISH'
            },
            timeframe='1m'
        )

        signal['symbol'] = symbol

        return signal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            'period': {'type': 'int', 'default': 10, 'min': 7, 'max': 20},
            'multiplier': {'type': 'float', 'default': 3.0, 'min': 2.0, 'max': 5.0}
        }
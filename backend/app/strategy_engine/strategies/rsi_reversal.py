"""
RSI Reversal Strategy
======================
Buy when RSI exits oversold, sell when RSI exits overbought.
"""

from typing import Dict, List, Optional, Any

from .base import BaseStrategy
from ..indicators.registry import IndicatorRegistry


class RSIReversalStrategy(BaseStrategy):
    """
    RSI Reversal Strategy

    Entry Rules:
    - BUY when RSI crosses above oversold threshold (30)
    - SELL when RSI crosses below overbought threshold (70)

    Parameters:
    - period: RSI period (default: 14)
    - oversold: Oversold threshold (default: 30)
    - overbought: Overbought threshold (default: 70)
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

        period = params.get('period', 14)
        oversold = params.get('oversold', 30)
        overbought = params.get('overbought', 70)

        closes = [c.get('close', 0) for c in candles]

        rsi_values = self.indicators.calculate('RSI', closes, period=period)

        if not rsi_values:
            return None

        current_rsi = rsi_values[-1]
        prev_rsi = rsi_values[-2] if len(rsi_values) > 1 else current_rsi

        current_price = closes[-1]

        if prev_rsi <= oversold and current_rsi > oversold:
            action = 'BUY'
            reasoning = f'RSI exited oversold zone ({current_rsi:.1f})'
            confidence = 70
        elif prev_rsi >= overbought and current_rsi < overbought:
            action = 'SELL'
            reasoning = f'RSI exited overbought zone ({current_rsi:.1f})'
            confidence = 70
        elif current_rsi < oversold:
            action = 'HOLD'
            reasoning = f'RSI at {current_rsi:.1f} in oversold zone - waiting for exit'
            confidence = 40
        elif current_rsi > overbought:
            action = 'HOLD'
            reasoning = f'RSI at {current_rsi:.1f} in overbought zone - waiting for exit'
            confidence = 40
        else:
            action = 'HOLD'
            reasoning = f'RSI at {current_rsi:.1f} in neutral zone'
            confidence = 30

        signal = self.create_signal(
            action=action,
            entry_price=current_price,
            confidence=confidence,
            reasoning=reasoning,
            indicators={
                'rsi': current_rsi,
                'rsi_prev': prev_rsi,
                'oversold': oversold,
                'overbought': overbought
            },
            timeframe='1m'
        )

        signal['symbol'] = symbol

        return signal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            'period': {'type': 'int', 'default': 14, 'min': 5, 'max': 30},
            'oversold': {'type': 'int', 'default': 30, 'min': 10, 'max': 40},
            'overbought': {'type': 'int', 'default': 70, 'min': 60, 'max': 90}
        }
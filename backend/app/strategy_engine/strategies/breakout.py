"""
Breakout Strategy
=================
Buy on bullish breakout, sell on bearish breakout.
"""

from typing import Dict, List, Optional, Any

from .base import BaseStrategy
from ..indicators.registry import IndicatorRegistry


class BreakoutStrategy(BaseStrategy):
    """
    Breakout Strategy

    Entry Rules:
    - BUY when price breaks above resistance (highest high of lookback period)
    - SELL when price breaks below support (lowest low of lookback period)

    Parameters:
    - lookback: Period to find resistance/support (default: 20)
    - confirm_bars: Number of bars to confirm breakout (default: 2)
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

        lookback = params.get('lookback', 20)
        confirm_bars = params.get('confirm_bars', 2)

        if len(candles) < lookback + confirm_bars:
            return None

        current_price = candles[-1].get('close', 0)

        recent_highs = [c.get('high', 0) for c in candles[-lookback-1:-1]]
        recent_lows = [c.get('low', 0) for c in candles[-lookback-1:-1]]

        resistance = max(recent_highs)
        support = min(recent_lows)

        breakout_threshold = 0.5

        if current_price > resistance * (1 + breakout_threshold / 100):
            action = 'BUY'
            reasoning = f'Price breakout above resistance {resistance:.2f}'
            confidence = 80

        elif current_price < support * (1 - breakout_threshold / 100):
            action = 'SELL'
            reasoning = f'Price breakdown below support {support:.2f}'
            confidence = 80

        elif current_price > resistance:
            action = 'BUY'
            reasoning = f'Price near resistance {resistance:.2f}'
            confidence = 60

        elif current_price < support:
            action = 'SELL'
            reasoning = f'Price near support {support:.2f}'
            confidence = 60

        else:
            action = 'HOLD'
            reasoning = f'Price between support ({support:.2f}) and resistance ({resistance:.2f})'
            confidence = 30

        signal = self.create_signal(
            action=action,
            entry_price=current_price,
            confidence=confidence,
            reasoning=reasoning,
            indicators={
                'resistance': resistance,
                'support': support,
                'current_price': current_price,
                'lookback': lookback
            },
            timeframe='1m'
        )

        signal['symbol'] = symbol

        return signal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            'lookback': {'type': 'int', 'default': 20, 'min': 10, 'max': 100},
            'confirm_bars': {'type': 'int', 'default': 2, 'min': 1, 'max': 5}
        }
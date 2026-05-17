"""
Scalping Strategy
=================
Fast trades on small price movements using multiple indicators.
"""

from typing import Dict, List, Optional, Any

from .base import BaseStrategy
from ..indicators.registry import IndicatorRegistry


class ScalpingStrategy(BaseStrategy):
    """
    Scalping Strategy

    Entry Rules:
    - BUY when EMA 9 > EMA 21, RSI < 70, and price above VWAP
    - SELL when EMA 9 < EMA 21, RSI > 30, and price below VWAP

    Parameters:
    - fast_ema: Fast EMA period (default: 9)
    - slow_ema: Slow EMA period (default: 21)
    - rsi_period: RSI period (default: 14)
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

        fast_ema_period = params.get('fast_ema', 9)
        slow_ema_period = params.get('slow_ema', 21)
        rsi_period = params.get('rsi_period', 14)

        closes = [c.get('close', 0) for c in candles]

        ema_fast = self.indicators.calculate('EMA', closes, period=fast_ema_period)
        ema_slow = self.indicators.calculate('EMA', closes, period=slow_ema_period)
        rsi_values = self.indicators.calculate('RSI', closes, period=rsi_period)

        if not ema_fast or not ema_slow or not rsi_values:
            return None

        current_ema_fast = ema_fast[-1]
        current_ema_slow = ema_slow[-1]
        current_rsi = rsi_values[-1]
        current_price = closes[-1]

        bullish = (
            current_ema_fast > current_ema_slow and
            current_rsi < 70 and
            current_price > current_ema_fast
        )

        bearish = (
            current_ema_fast < current_ema_slow and
            current_rsi > 30 and
            current_price < current_ema_fast
        )

        if bullish:
            action = 'BUY'
            reasoning = 'Scalping: Bullish EMA alignment, RSI not overbought'
            confidence = 75
        elif bearish:
            action = 'SELL'
            reasoning = 'Scalping: Bearish EMA alignment, RSI not oversold'
            confidence = 75
        else:
            action = 'HOLD'
            if current_ema_fast > current_ema_slow:
                reasoning = 'Scalping: EMA bullish but waiting for better RSI'
            else:
                reasoning = 'Scalping: EMA bearish but waiting for better RSI'
            confidence = 30

        signal = self.create_signal(
            action=action,
            entry_price=current_price,
            confidence=confidence,
            reasoning=reasoning,
            indicators={
                'ema_fast': current_ema_fast,
                'ema_slow': current_ema_slow,
                'rsi': current_rsi
            },
            timeframe='1m'
        )

        signal['symbol'] = symbol

        return signal

    def get_parameters(self) -> Dict[str, Any]:
        return {
            'fast_ema': {'type': 'int', 'default': 9, 'min': 5, 'max': 20},
            'slow_ema': {'type': 'int', 'default': 21, 'min': 15, 'max': 50},
            'rsi_period': {'type': 'int', 'default': 14, 'min': 7, 'max': 21}
        }
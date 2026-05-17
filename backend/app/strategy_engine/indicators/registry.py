"""
Indicator Registry
==================
Central registry for all technical indicators.
"""

import logging
from typing import Dict, List, Any, Callable, Optional

logger = logging.getLogger('indicator_registry')


class IndicatorRegistry:
    """
    Registry for technical indicators.
    """

    def __init__(self):
        self._indicators: Dict[str, Callable] = {}
        self._register_indicators()

    def _register_indicators(self) -> None:
        """Register all built-in indicators."""
        from .ema import calculate_ema
        from .sma import calculate_sma
        from .rsi import calculate_rsi
        from .macd import calculate_macd
        from .bollinger import calculate_bollinger_bands
        from .atr import calculate_atr
        from .supertrend import calculate_supertrend
        from .vwap import calculate_vwap
        from .stochastic import calculate_stochastic

        self.register('EMA', calculate_ema)
        self.register('SMA', calculate_sma)
        self.register('RSI', calculate_rsi)
        self.register('MACD', calculate_macd)
        self.register('BB', calculate_bollinger_bands)
        self.register('ATR', calculate_atr)
        self.register('Supertrend', calculate_supertrend)
        self.register('VWAP', calculate_vwap)
        self.register('STOCH', calculate_stochastic)

    def register(self, name: str, func: Callable) -> None:
        """Register an indicator."""
        self._indicators[name.upper()] = func

    def get(self, name: str) -> Optional[Callable]:
        """Get an indicator function."""
        return self._indicators.get(name.upper())

    def calculate(self, name: str, data: List, **params) -> Any:
        """Calculate an indicator."""
        func = self.get(name)
        if not func:
            raise ValueError(f"Unknown indicator: {name}")
        return func(data, **params)

    def calculate_all(self, candles: List[Dict]) -> Dict[str, Any]:
        """Calculate all indicators for given candles."""
        if not candles:
            return {}

        closes = [c.get('close', 0) for c in candles]
        highs = [c.get('high', 0) for c in candles]
        lows = [c.get('low', 0) for c in candles]
        volumes = [c.get('volume', 0) for c in candles]

        results = {}

        try:
            results['ema_9'] = self.calculate('EMA', closes, period=9)[-1] if len(closes) >= 9 else None
            results['ema_21'] = self.calculate('EMA', closes, period=21)[-1] if len(closes) >= 21 else None
            results['ema_50'] = self.calculate('EMA', closes, period=50)[-1] if len(closes) >= 50 else None
        except Exception:
            pass

        try:
            results['rsi'] = self.calculate('RSI', closes, period=14)[-1] if len(closes) >= 14 else None
        except Exception:
            pass

        try:
            macd_result = self.calculate('MACD', closes)
            results['macd'] = macd_result.get('macd')[-1] if macd_result.get('macd') else None
            results['macd_signal'] = macd_result.get('signal')[-1] if macd_result.get('signal') else None
            results['macd_histogram'] = macd_result.get('histogram')[-1] if macd_result.get('histogram') else None
        except Exception:
            pass

        try:
            bb_result = self.calculate('BB', closes)
            results['bb_upper'] = bb_result.get('upper')[-1] if bb_result.get('upper') else None
            results['bb_middle'] = bb_result.get('middle')[-1] if bb_result.get('middle') else None
            results['bb_lower'] = bb_result.get('lower')[-1] if bb_result.get('lower') else None
        except Exception:
            pass

        try:
            results['atr'] = self.calculate('ATR', candles, period=14)[-1] if len(candles) >= 14 else None
        except Exception:
            pass

        try:
            supertrend_result = self.calculate('Supertrend', candles)
            results['supertrend'] = supertrend_result.get('value')[-1] if supertrend_result.get('value') else None
            results['supertrend_direction'] = supertrend_result.get('direction')[-1] if supertrend_result.get('direction') else None
        except Exception:
            pass

        return results

    def list_indicators(self) -> List[str]:
        """List all registered indicators."""
        return list(self._indicators.keys())
"""
Indicator Stream Engine
========================
Realtime calculation of technical indicators.
"""

import logging
import math
import threading
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import deque

logger = logging.getLogger('trading_app')


@dataclass
class IndicatorData:
    """Container for technical indicator values."""
    symbol: str
    ema_9: Optional[float] = None
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    rsi_14: Optional[float] = None
    macd_line: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    vwap: Optional[float] = None
    supertrend: Optional[float] = None
    supertrend_direction: Optional[str] = None
    bb_upper: Optional[float] = None
    bb_middle: Optional[float] = None
    bb_lower: Optional[float] = None
    sma_20: Optional[float] = None
    atr_14: Optional[float] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        result = {'symbol': self.symbol, 'timestamp': self.timestamp}
        for key, value in self.__dict__.items():
            if key not in ('symbol', 'timestamp') and value is not None:
                result[key] = round(value, 2)
        return result


class TechnicalIndicators:
    """Calculate technical indicators."""

    @staticmethod
    def calculate_ema(prices: List[float], period: int) -> Optional[float]:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return None
        
        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period
        
        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema
        
        return ema

    @staticmethod
    def calculate_sma(prices: List[float], period: int) -> Optional[float]:
        """Calculate Simple Moving Average."""
        if len(prices) < period:
            return None
        return sum(prices[-period:]) / period

    @staticmethod
    def calculate_rsi(prices: List[float], period: int = 14) -> Optional[float]:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return None
        
        gains = []
        losses = []
        
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))
        
        if len(gains) < period:
            return None
        
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        
        if avg_loss == 0:
            return 100
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return rsi

    @staticmethod
    def calculate_macd(prices: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
        """Calculate MACD (Moving Average Convergence Divergence)."""
        if len(prices) < slow:
            return None, None, None
        
        ema_fast = TechnicalIndicators.calculate_ema(prices, fast)
        ema_slow = TechnicalIndicators.calculate_ema(prices, slow)
        
        if ema_fast is None or ema_slow is None:
            return None, None, None
        
        macd_line = ema_fast - ema_slow
        
        macd_values = [macd_line]
        for _ in range(slow):
            ema_fast = TechnicalIndicators.calculate_ema(prices[:slow], fast)
            ema_slow = TechnicalIndicators.calculate_ema(prices[:slow], slow)
            if ema_fast and ema_slow:
                macd_values.append(ema_fast - ema_slow)
        
        ema_signal = TechnicalIndicators.calculate_ema(macd_values, signal)
        
        if ema_signal is None:
            return macd_line, None, None
        
        histogram = macd_line - ema_signal
        
        return macd_line, ema_signal, histogram

    @staticmethod
    def calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2.0) -> tuple:
        """Calculate Bollinger Bands."""
        if len(prices) < period:
            return None, None, None
        
        sma = sum(prices[-period:]) / period
        
        variance = sum((p - sma) ** 2 for p in prices[-period:]) / period
        std = math.sqrt(variance)
        
        bb_upper = sma + (std_dev * std)
        bb_lower = sma - (std_dev * std)
        
        return bb_upper, sma, bb_lower

    @staticmethod
    def calculate_vwap(prices: List[float], volumes: List[int]) -> Optional[float]:
        """Calculate Volume Weighted Average Price."""
        if len(prices) != len(volumes) or len(prices) == 0:
            return None
        
        total_pv = sum(p * v for p, v in zip(prices, volumes))
        total_v = sum(volumes)
        
        if total_v == 0:
            return None
        
        return total_pv / total_v

    @staticmethod
    def calculate_supertrend(highs: List[float], lows: List[float], closes: List[float], period: int = 10, multiplier: float = 3.0) -> tuple:
        """Calculate Supertrend indicator."""
        if len(closes) < period:
            return None, None
        
        tr_list = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return None, None
        
        atr = sum(tr_list[:period]) / period
        
        basic_upper = (highs[-1] + lows[-1]) / 2 + multiplier * atr
        basic_lower = (highs[-1] + lows[-1]) / 2 - multiplier * atr
        
        final_upper = basic_upper
        final_lower = basic_lower
        
        for i in range(len(closes) - period, len(closes) - 1, -1):
            final_upper = max(basic_upper, final_lower) if closes[i] < final_upper else basic_upper
            final_lower = min(basic_lower, final_upper) if closes[i] > final_lower else basic_lower
        
        supertrend_value = final_upper if closes[-1] < final_upper else final_lower
        direction = 'BEARISH' if closes[-1] < final_upper else 'BULLISH'
        
        return supertrend_value, direction

    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Optional[float]:
        """Calculate Average True Range."""
        if len(closes) < period + 1:
            return None
        
        tr_list = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr = max(hl, hc, lc)
            tr_list.append(tr)
        
        if len(tr_list) < period:
            return None
        
        return sum(tr_list[:period]) / period


class IndicatorStream:
    """Realtime indicator calculation stream."""

    def __init__(self):
        self._price_history: Dict[str, deque] = {}
        self._indicators: Dict[str, IndicatorData] = {}
        self._lock = threading.RLock()
        self._subscribers: List[Callable[[IndicatorData], None]] = []
        logger.info("IndicatorStream initialized")

    def _ensure_history(self, symbol: str):
        """Ensure price history exists for a symbol."""
        if symbol not in self._price_history:
            self._price_history[symbol] = deque(maxlen=500)

    def update(self, symbol: str, price: float, high: float = None, low: float = None, volume: int = 0) -> IndicatorData:
        """Update indicators with new price data."""
        with self._lock:
            symbol = symbol.upper()
            self._ensure_history(symbol)
            
            self._price_history[symbol].append({
                'price': price,
                'high': high or price,
                'low': low or price,
                'volume': volume,
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            
            return self._calculate_indicators(symbol)

    def _calculate_indicators(self, symbol: str) -> IndicatorData:
        """Calculate all indicators for a symbol."""
        history = list(self._price_history[symbol])
        
        if len(history) < 20:
            return IndicatorData(symbol=symbol)
        
        prices = [h['price'] for h in history]
        highs = [h['high'] for h in history]
        lows = [h['low'] for h in history]
        volumes = [h['volume'] for h in history]
        
        indicators = IndicatorData(symbol=symbol)
        
        indicators.ema_9 = TechnicalIndicators.calculate_ema(prices, 9)
        indicators.ema_20 = TechnicalIndicators.calculate_ema(prices, 20)
        indicators.ema_50 = TechnicalIndicators.calculate_ema(prices, 50)
        indicators.ema_200 = TechnicalIndicators.calculate_ema(prices, 200) if len(prices) >= 200 else None
        
        indicators.sma_20 = TechnicalIndicators.calculate_sma(prices, 20)
        
        indicators.rsi_14 = TechnicalIndicators.calculate_rsi(prices, 14)
        
        macd_line, macd_signal, histogram = TechnicalIndicators.calculate_macd(prices)
        indicators.macd_line = macd_line
        indicators.macd_signal = macd_signal
        indicators.macd_histogram = histogram
        
        if len(prices) >= 20:
            bb_upper, bb_middle, bb_lower = TechnicalIndicators.calculate_bollinger_bands(prices)
            indicators.bb_upper = bb_upper
            indicators.bb_middle = bb_middle
            indicators.bb_lower = bb_lower
        
        indicators.vwap = TechnicalIndicators.calculate_vwap(prices, volumes)
        
        if len(highs) >= 10 and len(lows) >= 10 and len(prices) >= 10:
            st_value, st_direction = TechnicalIndicators.calculate_supertrend(highs, lows, prices)
            indicators.supertrend = st_value
            indicators.supertrend_direction = st_direction
        
        indicators.atr_14 = TechnicalIndicators.calculate_atr(highs, lows, prices)
        
        self._indicators[symbol] = indicators
        
        for callback in self._subscribers:
            try:
                callback(indicators)
            except Exception as e:
                logger.error(f"Error in indicator subscriber: {e}")
        
        return indicators

    def get_indicators(self, symbol: str) -> Optional[IndicatorData]:
        """Get current indicators for a symbol."""
        with self._lock:
            return self._indicators.get(symbol.upper())

    def subscribe(self, callback: Callable[[IndicatorData], None]):
        """Subscribe to indicator updates."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[IndicatorData], None]):
        """Unsubscribe from indicator updates."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)


_indicator_stream = IndicatorStream()


def get_indicator_stream() -> IndicatorStream:
    """Get the global indicator stream instance."""
    return _indicator_stream
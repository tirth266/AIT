"""
Historical Data Manager
=======================
Manages historical candle data storage and retrieval.
"""

import logging
import random
import threading
from typing import List, Optional, Dict
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass

logger = logging.getLogger('trading_app')

from app.market_data.symbol_manager import get_symbol_manager


@dataclass
class HistoricalCandle:
    """Historical candle data."""
    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    value: float = 0.0

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp,
            'open': round(self.open, 2),
            'high': round(self.high, 2),
            'low': round(self.low, 2),
            'close': round(self.close, 2),
            'volume': self.volume,
            'value': round(self.value, 2)
        }


class HistoricalDataManager:
    """Manages historical market data."""

    TIMEFRAMES = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '1d']

    def __init__(self):
        self._symbol_manager = get_symbol_manager()
        self._historical_data: Dict[str, Dict[str, List[HistoricalCandle]]] = {}
        self._lock = threading.RLock()
        logger.info("HistoricalDataManager initialized")

    def _generate_historical_candles(self, symbol: str, timeframe: str, limit: int, end_time: datetime) -> List[HistoricalCandle]:
        """Generate realistic historical candles."""
        info = self._symbol_manager.get_symbol_info(symbol)
        if not info:
            return []
        
        candles = []
        base_price = info.base_price
        current_price = base_price * (1 + random.uniform(-0.1, 0.1))
        
        timeframe_minutes = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '4h': 240, '1d': 1440
        }
        
        interval = timedelta(minutes=timeframe_minutes.get(timeframe, 1))
        
        for i in range(limit):
            candle_time = end_time - (interval * (limit - i))
            
            volatility = info.volatility * (1 + random.uniform(-0.3, 0.3))
            
            open_price = current_price
            
            change_percent = random.gauss(0, volatility)
            close_price = open_price * (1 + change_percent)
            
            high_price = max(open_price, close_price) * (1 + abs(random.gauss(0, volatility * 0.5)))
            low_price = min(open_price, close_price) * (1 - abs(random.gauss(0, volatility * 0.5)))
            
            volume = int(info.avg_volume * random.uniform(0.3, 1.5)) if not info.is_index else 0
            if timeframe == '1d':
                volume = volume * 390 if volume > 0 else 0
            
            candles.append(HistoricalCandle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=candle_time.isoformat(),
                open=round(open_price, 2),
                high=round(high_price, 2),
                low=round(low_price, 2),
                close=round(close_price, 2),
                volume=volume,
                value=round((open_price + high_price + low_price + close_price) / 4 * volume, 2) if volume > 0 else 0
            ))
            
            current_price = close_price
        
        return candles

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int = 100, end_time: datetime = None) -> List[dict]:
        """Get historical candles for a symbol and timeframe."""
        with self._lock:
            symbol = symbol.upper()
            
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            
            cache_key = f"{symbol}:{timeframe}"
            
            if cache_key not in self._historical_data:
                self._historical_data[cache_key] = self._generate_historical_candles(symbol, timeframe, limit * 2, end_time)
            
            candles = self._historical_data[cache_key]
            
            sorted_candles = sorted(candles, key=lambda c: c.timestamp, reverse=True)
            
            return [c.to_dict() for c in sorted_candles[:limit]]

    def get_candles_between(self, symbol: str, timeframe: str, start: datetime, end: datetime) -> List[dict]:
        """Get candles within a time range."""
        with self._lock:
            all_candles = self.get_historical_candles(symbol, timeframe, limit=10000, end_time=end)
            
            return [c for c in all_candles if start.isoformat() <= c['timestamp'] <= end.isoformat()]

    def preload_symbol(self, symbol: str, timeframes: List[str] = None):
        """Preload historical data for a symbol."""
        if timeframes is None:
            timeframes = self.TIMEFRAMES
        
        for tf in timeframes:
            self.get_historical_candles(symbol, tf, limit=500)
        
        logger.info(f"Preloaded historical data for {symbol}")

    def clear_cache(self, symbol: str = None):
        """Clear historical data cache."""
        with self._lock:
            if symbol:
                keys_to_remove = [k for k in self._historical_data.keys() if k.startswith(f"{symbol.upper()}")]
                for key in keys_to_remove:
                    del self._historical_data[key]
            else:
                self._historical_data.clear()


_historical_manager = HistoricalDataManager()


def get_historical_manager() -> HistoricalDataManager:
    """Get the global historical manager instance."""
    return _historical_manager
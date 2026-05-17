"""
Candle Aggregator
==================
Aggregates ticks into OHLC candles for various timeframes.
"""

import logging
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import threading

logger = logging.getLogger('trading_app')


@dataclass
class Candle:
    """OHLCV candle data structure."""
    symbol: str
    timeframe: str
    timestamp: str
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    value: float = 0.0
    trades: int = 0
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp,
            'open': round(self.open, 2),
            'high': round(self.high, 2),
            'low': round(self.low, 2),
            'close': round(self.close, 2),
            'volume': self.volume,
            'value': round(self.value, 2),
            'trades': self.trades
        }


TIMEFRAME_MINUTES = {
    '1m': 1,
    '3m': 3,
    '5m': 5,
    '15m': 15,
    '30m': 30,
    '1h': 60,
    '2h': 120,
    '4h': 240,
    '1d': 1440,
    '1w': 10080
}


class CandleAggregator:
    """Aggregates ticks into OHLC candles for various timeframes."""

    def __init__(self):
        self._candles: Dict[str, Dict[str, Candle]] = defaultdict(dict)
        self._lock = threading.RLock()
        self._subscribers: Dict[str, list] = defaultdict(list)
        logger.info("CandleAggregator initialized")

    def _get_timeframe_bucket(self, timeframe: str, timestamp: datetime = None) -> datetime:
        """Get the bucket timestamp for a given timeframe."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        minutes = TIMEFRAME_MINUTES.get(timeframe, 1)
        
        if timeframe == '1d':
            return timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
        elif timeframe == '1w':
            days_since_monday = timestamp.weekday()
            return (timestamp - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            bucket_minute = (timestamp.minute // minutes) * minutes
            return timestamp.replace(minute=bucket_minute, second=0, microsecond=0)

    def update(self, symbol: str, price: float, volume: int = 0, timeframe: str = '1m') -> Candle:
        """
        Update candle with new tick data.
        
        Args:
            symbol: Trading symbol
            price: Current price
            volume: Trade volume
            timeframe: Timeframe (1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w)
            
        Returns:
            Updated or new Candle
        """
        with self._lock:
            symbol = symbol.upper()
            now = datetime.now(timezone.utc)
            bucket_time = self._get_timeframe_bucket(timeframe, now)
            bucket_key = bucket_time.isoformat()
            
            if bucket_key not in self._candles[symbol]:
                self._candles[symbol][bucket_key] = Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=bucket_key,
                    open=price,
                    high=price,
                    low=price,
                    close=price,
                    volume=volume,
                    value=price * volume,
                    trades=1
                )
                is_new = True
            else:
                candle = self._candles[symbol][bucket_key]
                candle.high = max(candle.high, price)
                candle.low = min(candle.low, price)
                candle.close = price
                candle.volume += volume
                candle.value += price * volume
                candle.trades += 1
                is_new = False
            
            candle = self._candles[symbol][bucket_key]
            
            if not is_new:
                for callback in self._subscribers.get(symbol, []):
                    try:
                        callback(candle, timeframe)
                    except Exception as e:
                        logger.error(f"Error in candle subscriber: {e}")
            
            return candle

    def get_current_candle(self, symbol: str, timeframe: str = '1m') -> Optional[Candle]:
        """Get the current (in-progress) candle for a symbol and timeframe."""
        with self._lock:
            symbol = symbol.upper()
            now = datetime.now(timezone.utc)
            bucket_key = self._get_timeframe_bucket(timeframe, now).isoformat()
            return self._candles[symbol].get(bucket_key)

    def get_historical_candles(self, symbol: str, timeframe: str, limit: int = 100) -> List[Candle]:
        """Get historical candles (simulated)."""
        with self._lock:
            symbol = symbol.upper()
            candles = list(self._candles[symbol].values())
            candles.sort(key=lambda c: c.timestamp, reverse=True)
            return candles[:limit]

    def subscribe(self, symbol: str, callback):
        """Subscribe to candle updates for a symbol."""
        with self._lock:
            self._subscribers[symbol.upper()].append(callback)

    def unsubscribe(self, symbol: str, callback):
        """Unsubscribe from candle updates."""
        with self._lock:
            symbol = symbol.upper()
            if callback in self._subscribers.get(symbol, []):
                self._subscribers[symbol].remove(callback)

    def clear(self, symbol: str = None):
        """Clear candle data."""
        with self._lock:
            if symbol:
                self._candles[symbol.upper()].clear()
            else:
                self._candles.clear()
            logger.info(f"Candle data cleared for {symbol or 'all symbols'}")

    def get_all_current_candles(self, timeframe: str = '1m') -> List[dict]:
        """Get all current candles as list of dicts."""
        with self._lock:
            result = []
            now = datetime.now(timezone.utc)
            bucket_key = self._get_timeframe_bucket(timeframe, now).isoformat()
            
            for symbol, candles in self._candles.items():
                candle = candles.get(bucket_key)
                if candle:
                    result.append(candle.to_dict())
            
            return result


_candle_aggregator = CandleAggregator()


def get_candle_aggregator() -> CandleAggregator:
    """Get the global candle aggregator instance."""
    return _candle_aggregator
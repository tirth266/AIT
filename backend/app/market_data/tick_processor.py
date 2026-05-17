"""
Tick Processor
===============
Processes incoming market ticks and maintains tick state.
"""

import logging
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import threading

logger = logging.getLogger('trading_app')


@dataclass
class TickData:
    """Real-time tick data structure."""
    symbol: str
    exchange: str = 'NSE'
    ltp: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    bid: float = 0.0
    ask: float = 0.0
    high: float = 0.0
    low: float = 0.0
    open_price: float = 0.0
    close: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'ltp': round(self.ltp, 2),
            'change': round(self.change, 2),
            'change_percent': round(self.change_percent, 2),
            'volume': self.volume,
            'bid': round(self.bid, 2),
            'ask': round(self.ask, 2),
            'high': round(self.high, 2),
            'low': round(self.low, 2),
            'open': round(self.open_price, 2),
            'close': round(self.close, 2),
            'timestamp': self.timestamp
        }


class TickProcessor:
    """Processes and maintains real-time tick data."""

    def __init__(self):
        self._ticks: Dict[str, TickData] = {}
        self._prev_close: Dict[str, float] = {}
        self._day_open: Dict[str, float] = {}
        self._day_high: Dict[str, float] = {}
        self._day_low: Dict[str, float] = {}
        self._cumulative_volume: Dict[str, int] = {}
        self._lock = threading.RLock()
        self._subscribers: list[Callable[[TickData], None]] = []
        logger.info("TickProcessor initialized")

    def process_tick(self, symbol: str, price: float, volume: int = 0) -> TickData:
        """
        Process a new tick and update tick state.
        
        Args:
            symbol: Trading symbol
            price: Last traded price
            volume: Trading volume
            
        Returns:
            Updated TickData
        """
        with self._lock:
            symbol = symbol.upper()
            
            if symbol not in self._ticks:
                self._initialize_symbol(symbol, price)
            
            tick = self._ticks[symbol]
            
            tick.ltp = price
            tick.timestamp = datetime.now(timezone.utc).isoformat()
            
            if volume > 0:
                self._cumulative_volume[symbol] += volume
                tick.volume = self._cumulative_volume[symbol]
            
            if price > self._day_high[symbol]:
                self._day_high[symbol] = price
                tick.high = price
            
            if price < self._day_low[symbol]:
                self._day_low[symbol] = price
                tick.low = price
            
            prev_close = self._prev_close.get(symbol, price)
            if prev_close > 0:
                tick.change = round(price - prev_close, 2)
                tick.change_percent = round((tick.change / prev_close) * 100, 2)
            
            day_open = self._day_open.get(symbol, price)
            tick.open_price = day_open
            
            spread = price * 0.0002
            tick.bid = round(price - spread, 2)
            tick.ask = round(price + spread, 2)
            
            for callback in self._subscribers:
                try:
                    callback(tick)
                except Exception as e:
                    logger.error(f"Error in tick subscriber: {e}")
            
            return tick

    def _initialize_symbol(self, symbol: str, price: float):
        """Initialize a new symbol."""
        self._prev_close[symbol] = price
        self._day_open[symbol] = price
        self._day_high[symbol] = price
        self._day_low[symbol] = price
        self._cumulative_volume[symbol] = 0
        
        tick = TickData(
            symbol=symbol,
            ltp=price,
            high=price,
            low=price,
            open_price=price,
            close=price,
            volume=0
        )
        self._ticks[symbol] = tick

    def set_prev_close(self, symbol: str, prev_close: float):
        """Set previous close price for a symbol."""
        with self._lock:
            self._prev_close[symbol.upper()] = prev_close

    def get_tick(self, symbol: str) -> Optional[TickData]:
        """Get current tick for a symbol."""
        with self._lock:
            return self._ticks.get(symbol.upper())

    def get_all_ticks(self) -> Dict[str, TickData]:
        """Get all current ticks."""
        with self._lock:
            return dict(self._ticks)

    def subscribe(self, callback: Callable[[TickData], None]):
        """Subscribe to tick updates."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[TickData], None]):
        """Unsubscribe from tick updates."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def reset(self):
        """Reset all tick data."""
        with self._lock:
            self._ticks.clear()
            self._prev_close.clear()
            self._day_open.clear()
            self._day_high.clear()
            self._day_low.clear()
            self._cumulative_volume.clear()
            logger.info("TickProcessor reset")

    def get_snapshot(self) -> list:
        """Get snapshot of all ticks as list."""
        with self._lock:
            return [tick.to_dict() for tick in self._ticks.values()]


_tick_processor = TickProcessor()


def get_tick_processor() -> TickProcessor:
    """Get the global tick processor instance."""
    return _tick_processor
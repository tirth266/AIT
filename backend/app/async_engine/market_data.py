"""
Async Market Data Ingestion
============================
High-performance async market data streaming and processing.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, List, Callable, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger('market_data_ingestion')


class DataSource(Enum):
    WEBSOCKET = 'websocket'
    REST_API = 'rest_api'
    SIMULATED = 'simulated'
    KAFKA = 'kafka'


@dataclass
class MarketDataConfig:
    """Configuration for market data ingestion."""
    buffer_size: int = 1000
    batch_size: int = 100
    flush_interval_ms: int = 100
    reconnect_delay_seconds: float = 5.0
    max_reconnect_attempts: int = 10
    subscribe_batch_size: int = 50


class TickData:
    """Tick data structure."""
    def __init__(self, symbol: str, ltp: float, volume: int, timestamp: datetime):
        self.symbol = symbol
        self.ltp = ltp
        self.volume = volume
        self.timestamp = timestamp

    def to_dict(self) -> Dict:
        return {
            'symbol': self.symbol,
            'ltp': self.ltp,
            'volume': self.volume,
            'timestamp': self.timestamp.isoformat()
        }


class AsyncMarketDataIngestion:
    """
    Async market data ingestion with buffering and batching.
    
    Features:
    - Async data stream processing
    - Symbol-based subscriptions
    - Data buffering and batching
    - Automatic reconnection
    - Multiple data source support
    - Real-time tick aggregation
    """

    def __init__(self, config: Optional[MarketDataConfig] = None):
        self._config = config or MarketDataConfig()
        
        self._running = False
        self._ingestion_tasks: Dict[str, asyncio.Task] = {}
        self._buffer_tasks: Dict[str, asyncio.Task] = {}
        
        self._symbol_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._tick_buffers: Dict[str, deque] = defaultdict(lambda: deque(maxlen=self._config.buffer_size))
        self._candle_data: Dict[str, Dict[str, List[Dict]]] = defaultdict(dict)
        
        self._market_data_callbacks: List[Callable] = []
        self._tick_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        
        self._last_prices: Dict[str, float] = {}
        self._price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        self._lock = asyncio.Lock()
        self._stats = {
            'ticks_received': 0,
            'ticks_processed': 0,
            'symbols_subscribed': 0,
            'connection_errors': 0
        }

    async def start(self) -> None:
        """Start the market data ingestion."""
        if self._running:
            return
        
        self._running = True
        
        asyncio.create_task(self._aggregation_loop())
        
        logger.info("AsyncMarketDataIngestion started")

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the market data ingestion."""
        self._running = False
        
        for task in list(self._ingestion_tasks.values()):
            task.cancel()
        for task in list(self._buffer_tasks.values()):
            task.cancel()
        
        logger.info("AsyncMarketDataIngestion stopped")

    async def subscribe_symbols(
        self,
        symbols: List[str],
        timeframes: List[str] = None,
        source: DataSource = DataSource.SIMULATED
    ) -> None:
        """Subscribe to market data for symbols."""
        if timeframes is None:
            timeframes = ['1m', '5m', '15m', '1h', '1d']
        
        async with self._lock:
            for symbol in symbols:
                self._symbol_subscriptions[symbol.upper()].update(timeframes)
                
                for tf in timeframes:
                    if f"{symbol.upper()}_{tf}" not in self._candle_data:
                        self._candle_data[symbol.upper()][tf] = []
                
                if symbol.upper() not in self._ingestion_tasks:
                    task = asyncio.create_task(
                        self._ingest_symbol_data(symbol.upper(), source)
                    )
                    self._ingestion_tasks[symbol.upper()] = task
        
        self._stats['symbols_subscribed'] = len(symbols)
        logger.info(f"Subscribed to {len(symbols)} symbols")

    async def unsubscribe_symbols(self, symbols: List[str]) -> None:
        """Unsubscribe from market data."""
        async with self._lock:
            for symbol in symbols:
                symbol = symbol.upper()
                
                if symbol in self._ingestion_tasks:
                    self._ingestion_tasks[symbol].cancel()
                    del self._ingestion_tasks[symbol]
                
                self._symbol_subscriptions.pop(symbol, None)
                self._tick_buffers.pop(symbol, None)

    async def _ingest_symbol_data(self, symbol: str, source: DataSource) -> None:
        """Ingest market data for a symbol."""
        from app.market_data.engine import get_market_engine
        market_engine = get_market_engine()
        
        while self._running:
            try:
                await asyncio.sleep(0.1)
                
                tick = market_engine.get_tick(symbol)
                if tick:
                    await self._process_tick(symbol, tick)
                    
                    for tf in self._symbol_subscriptions.get(symbol, []):
                        candles = market_engine.get_candles(symbol, tf, limit=100)
                        if candles:
                            await self._update_candles(symbol, tf, candles)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Ingestion error for {symbol}: {e}")
                self._stats['connection_errors'] += 1
                await asyncio.sleep(self._config.reconnect_delay_seconds)

    async def _process_tick(self, symbol: str, tick_data: Dict) -> None:
        """Process incoming tick data."""
        tick = TickData(
            symbol=symbol,
            ltp=tick_data.get('ltp', 0),
            volume=tick_data.get('volume', 0),
            timestamp=datetime.utcnow()
        )
        
        self._tick_buffers[symbol].append(tick)
        self._last_prices[symbol] = tick.ltp
        self._price_history[symbol].append(tick.ltp)
        
        self._stats['ticks_received'] += 1
        
        for callback in self._tick_callbacks.get(symbol, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(tick)
                else:
                    callback(tick)
            except Exception as e:
                logger.error(f"Tick callback error: {e}")

    async def _update_candles(self, symbol: str, timeframe: str, candles: List[Dict]) -> None:
        """Update candle data."""
        key = f"{symbol}_{timeframe}"
        self._candle_data[symbol][timeframe] = candles
        
        self._stats['ticks_processed'] += 1

    async def _aggregation_loop(self) -> None:
        """Background loop for data aggregation."""
        while self._running:
            try:
                await asyncio.sleep(self._config.flush_interval_ms / 1000)
                
                await self._flush_buffers()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Aggregation error: {e}")

    async def _flush_buffers(self) -> None:
        """Flush tick buffers and notify subscribers."""
        for symbol, buffer in list(self._tick_buffers.items()):
            if buffer:
                latest = buffer[-1]
                
                for callback in self._market_data_callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(symbol, latest)
                        else:
                            callback(symbol, latest)
                    except Exception as e:
                        logger.error(f"Market data callback error: {e}")

    def register_market_data_callback(self, callback: Callable) -> None:
        """Register callback for all market data."""
        self._market_data_callbacks.append(callback)

    def register_tick_callback(self, symbol: str, callback: Callable) -> None:
        """Register callback for specific symbol."""
        self._tick_callbacks[symbol.upper()].append(callback)

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        return self._last_prices.get(symbol.upper())

    def get_price_history(self, symbol: str, limit: int = 100) -> List[float]:
        """Get price history for symbol."""
        history = list(self._price_history.get(symbol.upper(), []))
        return history[-limit:]

    def get_candles(self, symbol: str, timeframe: str = '1m') -> List[Dict]:
        """Get current candles for symbol."""
        return self._candle_data.get(symbol.upper(), {}).get(timeframe, [])

    def get_subscribed_symbols(self) -> List[str]:
        """Get list of subscribed symbols."""
        return list(self._symbol_subscriptions.keys())

    def get_stats(self) -> Dict:
        """Get market data ingestion statistics."""
        return {
            **self._stats,
            'subscribed_symbols': len(self._symbol_subscriptions),
            'buffer_sizes': {
                symbol: len(buffer)
                for symbol, buffer in self._tick_buffers.items()
            },
            'active_ingestion_tasks': len(self._ingestion_tasks)
        }


_market_ingestion: Optional[AsyncMarketDataIngestion] = None


def get_market_ingestion() -> AsyncMarketDataIngestion:
    """Get the global market data ingestion instance."""
    global _market_ingestion
    if _market_ingestion is None:
        _market_ingestion = AsyncMarketDataIngestion()
    return _market_ingestion
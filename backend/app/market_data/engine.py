"""
Market Data Engine
==================
Main orchestrator for the complete market data system.
"""

import logging
import threading
from typing import Optional, List, Dict, Callable
from datetime import datetime, timezone

from app.market_data.symbol_manager import get_symbol_manager
from app.market_data.tick_processor import get_tick_processor, TickData
from app.market_data.candle_aggregator import get_candle_aggregator
from app.market_data.feeds.simulated_feed import get_market_simulation, MarketSimulationEngine
from app.market_data.depth.orderbook import get_depth_manager, MarketDepth
from app.market_data.indicators.indicator_stream import get_indicator_stream, IndicatorData
from app.market_data.historical.historical_manager import get_historical_manager
from app.market_data.market_stream import get_subscription_manager, SubscriptionManager

logger = logging.getLogger('trading_app')


class MarketDataEngine:
    """
    Complete Market Data Engine
    
    Orchestrates all market data components:
    - Tick processing
    - Candle aggregation
    - Order book/depth
    - Technical indicators
    - Historical data
    - Market simulation
    - Subscription management
    """

    def __init__(self):
        self._symbol_manager = get_symbol_manager()
        self._tick_processor = get_tick_processor()
        self._candle_aggregator = get_candle_aggregator()
        self._market_simulation = get_market_simulation()
        self._depth_manager = get_depth_manager()
        self._indicator_stream = get_indicator_stream()
        self._historical_manager = get_historical_manager()
        self._subscription_manager = get_subscription_manager()
        
        self._is_running = False
        self._broadcast_callback: Optional[Callable] = None
        
        self._setup_callbacks()
        
        logger.info("MarketDataEngine initialized")

    def _setup_callbacks(self):
        """Setup internal callbacks."""
        def on_tick(tick: TickData):
            self._on_tick(tick)
        
        self._market_simulation.subscribe_to_ticks(on_tick)

    def _on_tick(self, tick: TickData):
        """Handle incoming tick data."""
        for timeframe in ['1m', '5m', '15m', '1h', '1d']:
            self._candle_aggregator.update(tick.symbol, tick.ltp, tick.volume, timeframe)
        
        depth = self._depth_manager.update_depth(tick.symbol, tick.ltp)
        if depth:
            self._broadcast_to_subscribers('market:depth', depth.to_dict(), tick.symbol)
        
        self._indicator_stream.update(tick.symbol, tick.ltp, tick.high, tick.low, tick.volume)
        
        self._broadcast_to_subscribers('market:tick', tick.to_dict(), tick.symbol)

    def _broadcast_to_subscribers(self, event: str, data: dict, symbol: str = None):
        """Broadcast data to subscribers."""
        if self._broadcast_callback:
            try:
                self._broadcast_callback(event, data, symbol)
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    def start(self):
        """Start the market data engine."""
        if self._is_running:
            logger.warning("Market data engine already running")
            return
        
        self._is_running = True
        self._market_simulation.start()
        
        for symbol in self._symbol_manager.get_all_symbols()[:10]:
            self._historical_manager.preload_symbol(symbol)
        
        logger.info("Market data engine started")

    def stop(self):
        """Stop the market data engine."""
        self._is_running = False
        self._market_simulation.stop()
        logger.info("Market data engine stopped")

    def set_broadcast_callback(self, callback: Callable[[str, dict, Optional[str]], None]):
        """Set callback for broadcasting to WebSocket."""
        self._broadcast_callback = callback

    def subscribe_session(self, session_id: str, symbols: List[str], channels: List[str] = None):
        """Subscribe a session to symbols."""
        if channels is None:
            channels = ['quotes']
        
        for symbol in symbols:
            self._subscription_manager.subscribe(session_id, symbol.upper())
        
        for symbol in symbols:
            info = self._symbol_manager.get_symbol_info(symbol.upper())
            if info:
                self._depth_manager.get_or_create_orderbook(symbol.upper(), info.base_price, info.volatility)

    def unsubscribe_session(self, session_id: str, symbols: List[str] = None):
        """Unsubscribe a session."""
        if symbols:
            for symbol in symbols:
                self._subscription_manager.unsubscribe(session_id, symbol.upper())
        else:
            self._subscription_manager.unsubscribe(session_id)

    def get_tick(self, symbol: str) -> Optional[dict]:
        """Get current tick for a symbol."""
        tick = self._tick_processor.get_tick(symbol.upper())
        return tick.to_dict() if tick else None

    def get_all_ticks(self) -> List[dict]:
        """Get all current ticks."""
        return self._tick_processor.get_snapshot()

    def get_candles(self, symbol: str, timeframe: str = '1m', limit: int = 100) -> List[dict]:
        """Get historical candles."""
        return self._historical_manager.get_historical_candles(symbol.upper(), timeframe, limit)

    def get_current_candle(self, symbol: str, timeframe: str = '1m') -> Optional[dict]:
        """Get current candle."""
        candle = self._candle_aggregator.get_current_candle(symbol.upper(), timeframe)
        return candle.to_dict() if candle else None

    def get_depth(self, symbol: str) -> Optional[dict]:
        """Get market depth for a symbol."""
        depth = self._depth_manager.get_depth(symbol.upper())
        return depth.to_dict() if depth else None

    def get_indicators(self, symbol: str) -> Optional[dict]:
        """Get technical indicators."""
        indicators = self._indicator_stream.get_indicators(symbol.upper())
        return indicators.to_dict() if indicators else None

    def get_market_status(self) -> dict:
        """Get market status."""
        status = self._market_simulation.get_market_status()
        return {
            'exchange': status.exchange,
            'status': status.status,
            'session': status.session,
            'next_session': status.next_session,
            'closes_in_seconds': status.closes_in_seconds,
            'timestamp': status.timestamp
        }

    def get_symbols(self, filter_type: str = 'all') -> List[str]:
        """Get available symbols."""
        if filter_type == 'stocks':
            return self._symbol_manager.get_stock_symbols()
        elif filter_type == 'indices':
            return self._symbol_manager.get_index_symbols()
        return self._symbol_manager.get_all_symbols()

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        """Get symbol information."""
        info = self._symbol_manager.get_symbol_info(symbol.upper())
        if info:
            return {
                'symbol': info.symbol,
                'exchange': info.exchange,
                'name': info.name,
                'sector': info.sector,
                'lot_size': info.lot_size,
                'tick_size': info.tick_size,
                'is_index': info.is_index,
                'base_price': info.base_price,
                'volatility': info.volatility
            }
        return None


_market_data_engine: Optional[MarketDataEngine] = None
_engine_lock = threading.Lock()


def get_market_engine() -> MarketDataEngine:
    """Get the global market data engine instance."""
    global _market_data_engine
    
    with _engine_lock:
        if _market_data_engine is None:
            _market_data_engine = MarketDataEngine()
        return _market_data_engine


def initialize_market_engine() -> MarketDataEngine:
    """Initialize and start the market data engine."""
    engine = get_market_engine()
    engine.start()
    return engine
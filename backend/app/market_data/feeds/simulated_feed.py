"""
Market Simulation Engine
========================
Generates realistic Indian stock market data with proper market dynamics.
"""

import logging
import random
import math
import threading
import time
from typing import Dict, Optional, Callable, List
from datetime import datetime, timezone, time as dt_time
from dataclasses import dataclass

from app.market_data.symbol_manager import get_symbol_manager
from app.market_data.tick_processor import get_tick_processor, TickData

logger = logging.getLogger('trading_app')


@dataclass
class MarketStatus:
    """Market trading status."""
    exchange: str
    status: str
    session: str
    next_session: str
    closes_in_seconds: int
    timestamp: str


class MarketSimulationEngine:
    """Generates realistic Indian market simulation with proper hours and volatility."""

    MARKET_OPEN = dt_time(9, 15)
    MARKET_CLOSE = dt_time(15, 30)
    PRE_MARKET_START = dt_time(9, 0)
    POST_MARKET_END = dt_time(16, 0)

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._tick_callbacks: List[Callable[[TickData], None]] = []
        self._status_callbacks: List[Callable[[MarketStatus], None]] = []
        
        self._symbol_manager = get_symbol_manager()
        self._tick_processor = get_tick_processor()
        
        self._current_prices: Dict[str, float] = {}
        self._price_directions: Dict[str, int] = {}
        self._volatility_multipliers: Dict[str, float] = {}
        self._base_volumes: Dict[str, int] = {}
        
        self._initialize_prices()
        self._set_intraday_volatility()
        
        logger.info("MarketSimulationEngine initialized")

    def _initialize_prices(self):
        """Initialize base prices for all symbols."""
        for symbol in self._symbol_manager.get_all_symbols():
            info = self._symbol_manager.get_symbol_info(symbol)
            if info:
                self._current_prices[symbol] = info.base_price
                self._price_directions[symbol] = random.choice([-1, 1])
                self._base_volumes[symbol] = info.avg_volume

    def _set_intraday_volatility(self):
        """Set volatility based on time of day."""
        now = datetime.now()
        current_time = now.time()
        
        if self.MARKET_OPEN <= current_time < dt_time(9, 30):
            multiplier = 1.5
        elif dt_time(9, 30) <= current_time < dt_time(11, 0):
            multiplier = 1.2
        elif dt_time(11, 0) <= current_time < dt_time(14, 0):
            multiplier = 0.8
        elif dt_time(14, 0) <= current_time <= self.MARKET_CLOSE:
            multiplier = 1.3
        else:
            multiplier = 0.5
        
        for symbol in self._symbol_manager.get_all_symbols():
            self._volatility_multipliers[symbol] = multiplier

    def _get_intraday_multiplier(self) -> float:
        """Get current intraday volatility multiplier."""
        current_time = datetime.now().time()
        
        if self.MARKET_OPEN <= current_time < dt_time(9, 30):
            return 1.5
        elif dt_time(9, 30) <= current_time < dt_time(11, 0):
            return 1.2
        elif dt_time(11, 0) <= current_time < dt_time(14, 0):
            return 0.8
        elif dt_time(14, 0) <= current_time <= self.MARKET_CLOSE:
            return 1.3
        else:
            return 0.5

    def _calculate_price_change(self, symbol: str) -> float:
        """Calculate realistic price change with momentum and mean reversion."""
        info = self._symbol_manager.get_symbol_info(symbol)
        if not info:
            return 0.0
        
        base_volatility = info.volatility
        intraday_multiplier = self._get_intraday_multiplier()
        volatility = base_volatility * intraday_multiplier
        
        current_price = self._current_prices[symbol]
        base_price = info.base_price
        
        distance_from_base = (current_price - base_price) / base_price
        
        mean_reversion = -distance_from_base * 0.002
        
        momentum = self._price_directions[symbol] * volatility * random.uniform(0.5, 1.5)
        
        noise = random.gauss(0, volatility * 0.3)
        
        if random.random() < 0.05:
            self._price_directions[symbol] *= -1
        
        price_change = momentum + noise + mean_reversion
        
        max_daily_move = 0.03
        if abs(price_change) > max_daily_move:
            price_change = math.copysign(max_daily_move, price_change)
        
        return price_change * current_price

    def _generate_volume(self, symbol: str) -> int:
        """Generate realistic trading volume."""
        info = self._symbol_manager.get_symbol_info(symbol)
        if not info:
            return 0
        
        base_vol = info.avg_volume
        if base_vol == 0:
            return random.randint(100000, 500000)
        
        intraday_mult = self._get_intraday_multiplier()
        
        volume = int(base_vol * intraday_mult * random.uniform(0.3, 1.5))
        
        volume = int(volume / 390)
        
        return max(100, volume)

    def _calculate_index_change(self, symbol: str) -> float:
        """Calculate more stable index changes."""
        info = self._symbol_manager.get_symbol_info(symbol)
        if not info:
            return 0.0
        
        volatility = info.volatility * 0.5
        
        noise = random.gauss(0, volatility * 0.5)
        
        return noise * self._current_prices[symbol]

    def start(self):
        """Start the market simulation."""
        with self._lock:
            if self._running:
                logger.warning("Market simulation already running")
                return
            
            self._running = True
            self._thread = threading.Thread(target=self._run_simulation, daemon=True)
            self._thread.start()
            logger.info("Market simulation started")

    def stop(self):
        """Stop the market simulation."""
        with self._lock:
            self._running = False
            if self._thread:
                self._thread.join(timeout=5)
            logger.info("Market simulation stopped")

    def _run_simulation(self):
        """Main simulation loop."""
        while self._running:
            try:
                current_time = datetime.now().time()
                
                if self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE:
                    for symbol in self._symbol_manager.get_all_symbols():
                        info = self._symbol_manager.get_symbol_info(symbol)
                        
                        if info.is_index:
                            price_change = self._calculate_index_change(symbol)
                        else:
                            price_change = self._calculate_price_change(symbol)
                        
                        new_price = self._current_prices[symbol] + price_change
                        new_price = max(new_price, info.base_price * 0.5)
                        new_price = min(new_price, info.base_price * 2.0)
                        
                        self._current_prices[symbol] = round(new_price, 2)
                        
                        volume = self._generate_volume(symbol)
                        
                        tick = self._tick_processor.process_tick(symbol, new_price, volume)
                        
                        for callback in self._tick_callbacks:
                            try:
                                callback(tick)
                            except Exception as e:
                                logger.error(f"Error in tick callback: {e}")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Simulation error: {e}")
                time.sleep(1)

    def subscribe_to_ticks(self, callback: Callable[[TickData], None]):
        """Subscribe to tick updates."""
        self._tick_callbacks.append(callback)

    def unsubscribe_from_ticks(self, callback: Callable[[TickData], None]):
        """Unsubscribe from tick updates."""
        if callback in self._tick_callbacks:
            self._tick_callbacks.remove(callback)

    def get_current_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
        return self._current_prices.get(symbol.upper(), 0.0)

    def get_market_status(self) -> MarketStatus:
        """Get current market status."""
        now = datetime.now()
        current_time = now.time()
        
        if self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE:
            status = 'OPEN'
            session = 'REGULAR'
            next_session = 'POST-MARKET'
        elif current_time < self.MARKET_OPEN:
            status = 'CLOSED'
            session = 'PRE-MARKET'
            next_session = 'REGULAR'
        else:
            status = 'CLOSED'
            session = 'POST-MARKET'
            next_session = 'CLOSED'
        
        if status == 'OPEN':
            market_close = datetime.combine(now.date(), self.MARKET_CLOSE)
            closes_in = int((market_close - now).total_seconds())
        else:
            market_open = datetime.combine(now.date(), self.MARKET_OPEN)
            if now.time() > self.MARKET_CLOSE:
                market_open = market_open + timedelta(days=1)
            closes_in = int((market_open - now).total_seconds())
        
        return MarketStatus(
            exchange='NSE',
            status=status,
            session=session,
            next_session=next_session,
            closes_in_seconds=max(0, closes_in),
            timestamp=datetime.now(timezone.utc).isoformat()
        )

    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        current_time = datetime.now().time()
        return self.MARKET_OPEN <= current_time <= self.MARKET_CLOSE


_market_simulation = MarketSimulationEngine()


def get_market_simulation() -> MarketSimulationEngine:
    """Get the global market simulation instance."""
    return _market_simulation
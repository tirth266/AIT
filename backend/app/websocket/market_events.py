"""
Market Data Events Generator
============================
Generate and broadcast realtime market data for Indian stocks.
"""

import logging
import random
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional
from threading import Thread

logger = logging.getLogger(__name__)


class MarketDataGenerator:
    """
    Generate simulated market data for Indian stocks.
    In production, this would connect to real market data providers.
    """

    BASE_SYMBOLS = {
        'RELIANCE': {'price': 2945.50, 'base_volume': 1500000},
        'TCS': {'price': 4215.00, 'base_volume': 800000},
        'INFY': {'price': 1750.25, 'base_volume': 1200000},
        'HDFCBANK': {'price': 1680.50, 'base_volume': 2000000},
        'ICICIBANK': {'price': 1050.75, 'base_volume': 1800000},
        'SBIN': {'price': 780.25, 'base_volume': 2500000},
        'BHARTIARTL': {'price': 1520.00, 'base_volume': 900000},
        'HINDUNILVR': {'price': 2650.00, 'base_volume': 600000},
        'KOTAKBANK': {'price': 1850.50, 'base_volume': 1100000},
        'ITC': {'price': 450.25, 'base_volume': 2200000},
    }

    def __init__(self, ws_manager):
        self.ws_manager = ws_manager
        self.prices = {k: v['price'] for k, v in self.BASE_SYMBOLS.items()}
        self.previous_prices = {k: v['price'] for k, v in self.BASE_SYMBOLS.items()}
        self.is_running = False
        self.thread: Optional[Thread] = None

    def start(self):
        """Start the market data generation."""
        if self.is_running:
            return

        self.is_running = True
        self.thread = Thread(target=self._generate_loop, daemon=True)
        self.thread.start()
        logger.info("Market data generator started")

    def stop(self):
        """Stop the market data generation."""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("Market data generator stopped")

    def _generate_loop(self):
        """Main generation loop."""
        while self.is_running:
            try:
                self._generate_tick()
                self._generate_indices()
                self._check_for_signals()
                asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error generating market data: {e}")

    def _generate_tick(self):
        """Generate tick data for subscribed symbols."""
        symbols = list(self.ws_manager.symbol_subscriptions.keys())

        if not symbols:
            return

        for symbol in symbols:
            if symbol not in self.BASE_SYMBOLS:
                continue

            self._update_price(symbol)
            tick_data = self._create_tick_data(symbol)

            self.ws_manager.broadcast_market_tick(symbol, tick_data)

    def _update_price(self, symbol: str):
        """Update price with random walk."""
        if symbol not in self.BASE_SYMBOLS:
            return

        base_price = self.BASE_SYMBOLS[symbol]['price']
        volatility = 0.002

        change_percent = random.uniform(-volatility, volatility)
        new_price = self.previous_prices.get(symbol, base_price) * (1 + change_percent)

        self.previous_prices[symbol] = self.prices.get(symbol, base_price)
        self.prices[symbol] = round(new_price, 2)

    def _create_tick_data(self, symbol: str) -> Dict:
        """Create tick data payload."""
        current_price = self.prices.get(symbol, 0)
        previous_price = self.previous_prices.get(symbol, current_price)
        change = current_price - previous_price
        change_percent = (change / previous_price * 100) if previous_price > 0 else 0

        base_volume = self.BASE_SYMBOLS.get(symbol, {}).get('base_volume', 1000000)
        volume = base_volume + random.randint(-100000, 100000)

        return {
            'symbol': symbol,
            'last_price': current_price,
            'open': round(previous_price * 0.998, 2),
            'high': round(current_price * 1.005, 2),
            'low': round(current_price * 0.995, 2),
            'prev_close': previous_price,
            'change': round(change, 2),
            'change_percent': round(change_percent, 2),
            'volume': volume,
            'value': round(current_price * volume, 2),
            'vwap': round((current_price + random.uniform(-5, 5)), 2),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def _generate_indices(self):
        """Generate index updates."""
        indices = {
            'NIFTY': {'base': 22500, 'change': random.uniform(-0.3, 0.3)},
            'SENSEX': {'base': 75000, 'change': random.uniform(-0.25, 0.25)},
            'BANKNIFTY': {'base': 48000, 'change': random.uniform(-0.4, 0.4)},
        }

        for index_name, data in indices.items():
            current = data['base'] * (1 + data['change'] / 100)
            change_val = data['base'] * data['change'] / 100

            index_data = {
                'value': round(current, 2),
                'change': round(change_val, 2),
                'change_percent': round(data['change'], 2),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

            self.ws_manager.emit_to_all(f'index:{index_name.lower()}', index_data)

    def _check_for_signals(self):
        """Randomly generate AI signals."""
        if random.random() < 0.02:
            symbol = random.choice(list(self.BASE_SYMBOLS.keys()))
            self._generate_ai_signal(symbol)

    def _generate_ai_signal(self, symbol: str):
        """Generate AI trading signal."""
        actions = ['BUY', 'SELL']
        action = random.choice(actions)

        current_price = self.prices.get(symbol, 0)
        target_price = current_price * (1.02 if action == 'BUY' else 0.98)
        stop_loss = current_price * (0.985 if action == 'BUY' else 1.015)

        signal_data = {
            'signal_id': f"sig_{datetime.now().strftime('%Y%m%d%H%M%S')}_{symbol}",
            'symbol': symbol,
            'action': action,
            'confidence': round(random.uniform(70, 95), 1),
            'target_price': round(target_price, 2),
            'stop_loss': round(stop_loss, 2),
            'reasoning': f"RSI at {random.randint(25, 75)} ({'oversold' if random.random() < 0.5 else 'overbought'}), MACD {'bullish' if action == 'BUY' else 'bearish'} crossover",
            'timeframe': random.choice(['1HOUR', '4HOUR', '1DAY']),
            'indicators': {
                'rsi': random.randint(25, 75),
                'macd': 'bullish' if action == 'BUY' else 'bearish',
                'volume_ratio': round(random.uniform(0.8, 1.5), 2)
            }
        }

        self.ws_manager.broadcast_ai_signal(signal_data)
        logger.info(f"Generated AI signal: {symbol} {action}")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for symbol."""
        return self.prices.get(symbol.upper())


market_data_generator: Optional[MarketDataGenerator] = None


def start_market_data(socketio):
    """Start the market data generator."""
    global market_data_generator
    from .socket_manager import get_ws_manager
    manager = get_ws_manager()
    market_data_generator = MarketDataGenerator(manager)
    market_data_generator.start()


def stop_market_data():
    """Stop the market data generator."""
    global market_data_generator
    if market_data_generator:
        market_data_generator.stop()


def get_market_price(symbol: str) -> Optional[float]:
    """Get current market price."""
    if market_data_generator:
        return market_data_generator.get_current_price(symbol)
    return None
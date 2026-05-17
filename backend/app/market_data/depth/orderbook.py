"""
Market Depth / Order Book
==========================
Simulated Level 2 order book for Indian stocks.
"""

import logging
import random
import threading
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger('trading_app')


@dataclass
class OrderBookEntry:
    """Single order in the order book."""
    price: float
    quantity: int
    orders: int

    def to_dict(self) -> dict:
        return {
            'price': round(self.price, 2),
            'quantity': self.quantity,
            'orders': self.orders
        }


@dataclass
class MarketDepth:
    """Full market depth / order book data."""
    symbol: str
    exchange: str = 'NSE'
    bids: List[OrderBookEntry] = field(default_factory=list)
    asks: List[OrderBookEntry] = field(default_factory=list)
    spread: float = 0.0
    spread_percent: float = 0.0
    total_bid_quantity: int = 0
    total_ask_quantity: int = 0
    timestamp: str = field(default_factory=lambda: __import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            'symbol': self.symbol,
            'exchange': self.exchange,
            'bids': [b.to_dict() for b in self.bids],
            'asks': [a.to_dict() for a in self.asks],
            'spread': round(self.spread, 2),
            'spread_percent': round(self.spread_percent, 4),
            'total_bid_quantity': self.total_bid_quantity,
            'total_ask_quantity': self.total_ask_quantity,
            'timestamp': self.timestamp
        }


class OrderBook:
    """Simulated order book for a symbol."""

    def __init__(self, symbol: str, base_price: float, volatility: float = 0.001):
        self.symbol = symbol.upper()
        self._base_price = base_price
        self._volatility = volatility
        self._lock = threading.RLock()
        self._depth_levels = 10
        self._initialize_order_book()

    def _initialize_order_book(self):
        """Initialize the order book with realistic structure."""
        self._bids: List[OrderBookEntry] = []
        self._asks: List[OrderBookEntry] = []
        
        spread = self._base_price * random.uniform(0.0001, 0.0003)
        
        mid_price = self._base_price
        
        bid_start = mid_price - spread / 2
        ask_start = mid_price + spread / 2
        
        tick_size = max(0.05, self._base_price * 0.0001)
        
        for i in range(self._depth_levels):
            bid_price = bid_start - (i * tick_size)
            ask_price = ask_start + (i * tick_size)
            
            bid_qty = int(random.uniform(100, 10000) * (1 + i * 0.1))
            ask_qty = int(random.uniform(100, 10000) * (1 + i * 0.1))
            
            self._bids.append(OrderBookEntry(
                price=round(bid_price, 2),
                quantity=bid_qty,
                orders=random.randint(1, 50)
            ))
            
            self._asks.append(OrderBookEntry(
                price=round(ask_price, 2),
                quantity=ask_qty,
                orders=random.randint(1, 50)
            ))

    def update(self, ltp: float) -> MarketDepth:
        """Update order book based on last traded price."""
        with self._lock:
            spread = ltp * random.uniform(0.0001, 0.0003)
            mid_price = ltp
            tick_size = max(0.05, ltp * 0.0001)
            
            bid_start = mid_price - spread / 2
            ask_start = mid_price + spread / 2
            
            new_bids = []
            new_asks = []
            
            for i in range(self._depth_levels):
                bid_price = bid_start - (i * tick_size)
                ask_price = ask_start + (i * tick_size)
                
                base_qty = int(random.uniform(100, 10000))
                
                bid_qty = max(100, int(base_qty * (1 + random.gauss(0, 0.3))))
                ask_qty = max(100, int(base_qty * (1 + random.gauss(0, 0.3))))
                
                if random.random() < 0.1:
                    change = random.randint(-500, 500)
                    bid_qty = max(100, bid_qty + change)
                
                if random.random() < 0.1:
                    change = random.randint(-500, 500)
                    ask_qty = max(100, ask_qty + change)
                
                new_bids.append(OrderBookEntry(
                    price=round(bid_price, 2),
                    quantity=bid_qty,
                    orders=random.randint(1, 50)
                ))
                
                new_asks.append(OrderBookEntry(
                    price=round(ask_price, 2),
                    quantity=ask_qty,
                    orders=random.randint(1, 50)
                ))
            
            self._bids = new_bids
            self._asks = new_asks
            
            return self.get_depth()

    def get_depth(self) -> MarketDepth:
        """Get current market depth."""
        with self._lock:
            total_bid = sum(b.quantity for b in self._bids)
            total_ask = sum(a.quantity for a in self._asks)
            
            best_bid = self._bids[0].price if self._bids else 0
            best_ask = self._asks[0].price if self._asks else 0
            spread = best_ask - best_bid
            spread_percent = (spread / best_ask * 100) if best_ask > 0 else 0
            
            return MarketDepth(
                symbol=self.symbol,
                exchange='NSE',
                bids=self._bids.copy(),
                asks=self._asks.copy(),
                spread=spread,
                spread_percent=spread_percent,
                total_bid_quantity=total_bid,
                total_ask_quantity=total_ask
            )


class MarketDepthManager:
    """Manages order books for multiple symbols."""

    def __init__(self):
        self._order_books: Dict[str, OrderBook] = {}
        self._lock = threading.RLock()
        logger.info("MarketDepthManager initialized")

    def get_or_create_orderbook(self, symbol: str, base_price: float, volatility: float = 0.001) -> OrderBook:
        """Get or create an order book for a symbol."""
        with self._lock:
            symbol = symbol.upper()
            if symbol not in self._order_books:
                self._order_books[symbol] = OrderBook(symbol, base_price, volatility)
            return self._order_books[symbol]

    def update_depth(self, symbol: str, ltp: float) -> Optional[MarketDepth]:
        """Update depth for a symbol."""
        with self._lock:
            symbol = symbol.upper()
            if symbol in self._order_books:
                return self._order_books[symbol].update(ltp)
            return None

    def get_depth(self, symbol: str) -> Optional[MarketDepth]:
        """Get current depth for a symbol."""
        with self._lock:
            symbol = symbol.upper()
            if symbol in self._order_books:
                return self._order_books[symbol].get_depth()
            return None

    def remove(self, symbol: str):
        """Remove order book for a symbol."""
        with self._lock:
            symbol = symbol.upper()
            if symbol in self._order_books:
                del self._order_books[symbol]


_depth_manager = MarketDepthManager()


def get_depth_manager() -> MarketDepthManager:
    """Get the global depth manager instance."""
    return _depth_manager
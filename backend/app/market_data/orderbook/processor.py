"""
L2 Order Book Processor
========================
Processes full order book depth with incremental updates.
"""

import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict
from sortedcontainers import SortedDict
import threading

from ..core.models import OrderBook, OrderBookLevel, Tick, Exchange

logger = logging.getLogger('market_data.orderbook')


@dataclass
class OrderBookConfig:
    max_depth: int = 20
    price_precision: int = 2
    quantity_multiplier: int = 1
    enable_imbalance_calculation: bool = True
    enable_vwap_calculation: bool = True
    snapshot_interval_seconds: int = 5


@dataclass
class MarketDepth:
    bid_depth: List[int] = field(default_factory=list)
    ask_depth: List[int] = field(default_factory=list)
    bid_vwap: float = 0.0
    ask_vwap: float = 0.0
    imbalance: float = 0.0
    mid_price: float = 0.0
    spread: float = 0.0
    spread_percent: float = 0.0


class OrderBookBuilder:
    """
    Maintains sorted bid/ask books with efficient price-level aggregation.
    """

    def __init__(self, max_depth: int = 20):
        self.max_depth = max_depth
        self._bids: SortedDict = SortedDict(reverse=True)
        self._asks: SortedDict = SortedDict()
        self._order_counts: Dict = defaultdict(int)

        self._last_update_time: Optional[datetime] = None
        self._total_bid_quantity: int = 0
        self._total_ask_quantity: int = 0

    def update_bids(self, price: float, quantity: int, operation: str = "UPDATE") -> None:
        if operation == "DELETE" or quantity == 0:
            if price in self._bids:
                self._total_bid_quantity -= self._bids[price]
                del self._bids[price]
        else:
            old_qty = self._bids.get(price, 0)
            self._total_bid_quantity = self._total_bid_quantity - old_qty + quantity
            self._bids[price] = quantity

        self._last_update_time = datetime.now(timezone.utc)

    def update_asks(self, price: float, quantity: int, operation: str = "UPDATE") -> None:
        if operation == "DELETE" or quantity == 0:
            if price in self._asks:
                self._total_ask_quantity -= self._asks[price]
                del self._asks[price]
        else:
            old_qty = self._asks.get(price, 0)
            self._total_ask_quantity = self._total_ask_quantity - old_qty + quantity
            self._asks[price] = quantity

        self._last_update_time = datetime.now(timezone.utc)

    def apply_tick(self, tick: Tick) -> None:
        if tick.bid_price > 0 and tick.bid_quantity > 0:
            self.update_bids(tick.bid_price, tick.bid_quantity)

        if tick.ask_price > 0 and tick.ask_quantity > 0:
            self.update_asks(tick.ask_price, tick.ask_quantity)

        if tick.last_quantity > 0:
            self.update_last_trade(tick.last_price, tick.last_quantity)

    def update_last_trade(self, price: float, quantity: int) -> None:
        side = "bid" if self._is_bid_trade(price) else "ask"
        book = self._bids if side == "bid" else self._asks

        for p in list(book.keys())[:self.max_depth]:
            if (side == "bid" and p <= price) or (side == "ask" and p >= price):
                book[p] = max(0, book[p] - quantity)
                if book[p] == 0:
                    if side == "bid":
                        self.update_bids(p, 0, "DELETE")
                    else:
                        self.update_asks(p, 0, "DELETE")
                break

    def _is_bid_trade(self, price: float) -> bool:
        if not self._bids or not self._asks:
            return True

        best_bid = self._bids.keys()[0]
        best_ask = self._asks.keys()[0]

        return price >= (best_bid + best_ask) / 2

    def get_top_levels(self, depth: int = 5) -> tuple:
        bid_levels = []
        for price in list(self._bids.keys())[:depth]:
            bid_levels.append(OrderBookLevel(
                price=price,
                quantity=self._bids[price],
            ))

        ask_levels = []
        for price in list(self._asks.keys())[:depth]:
            ask_levels.append(OrderBookLevel(
                price=price,
                quantity=self._asks[price],
            ))

        return bid_levels, ask_levels

    def get_market_depth(self, depth: int = 10) -> MarketDepth:
        bid_levels = []
        ask_levels = []
        bid_vwap = 0.0
        ask_vwap = 0.0

        cum_bid_vol = 0
        cum_ask_vol = 0

        for price in list(self._bids.keys())[:depth]:
            qty = self._bids[price]
            bid_levels.append(qty)
            cum_bid_vol += qty
            bid_vwap += price * qty

        for price in list(self._asks.keys())[:depth]:
            qty = self._asks[price]
            ask_levels.append(qty)
            cum_ask_vol += qty
            ask_vwap += price * qty

        if cum_bid_vol > 0:
            bid_vwap /= cum_bid_vol
        if cum_ask_vol > 0:
            ask_vwap /= cum_ask_vol

        spread = 0.0
        spread_percent = 0.0
        mid_price = 0.0

        if self._bids and self._asks:
            best_bid = self._bids.keys()[0]
            best_ask = self._asks.keys()[0]
            mid_price = (best_bid + best_ask) / 2
            spread = best_ask - best_bid
            if mid_price > 0:
                spread_percent = (spread / mid_price) * 100

        imbalance = 0.0
        total = self._total_bid_quantity + self._total_ask_quantity
        if total > 0:
            imbalance = (self._total_bid_quantity - self._total_ask_quantity) / total

        return MarketDepth(
            bid_depth=bid_levels,
            ask_depth=ask_levels,
            bid_vwap=bid_vwap,
            ask_vwap=ask_vwap,
            imbalance=imbalance,
            mid_price=mid_price,
            spread=spread,
            spread_percent=spread_percent,
        )

    def clear(self) -> None:
        self._bids.clear()
        self._asks.clear()
        self._order_counts.clear()
        self._total_bid_quantity = 0
        self._total_ask_quantity = 0

    @property
    def spread(self) -> float:
        if not self._bids or not self._asks:
            return 0.0
        return list(self._asks.keys())[0] - list(self._bids.keys())[0]

    @property
    def mid_price(self) -> float:
        if not self._bids or not self._asks:
            return 0.0
        return (list(self._bids.keys())[0] + list(self._asks.keys())[0]) / 2


class OrderBookProcessor:
    """
    L2 order book processor with tick processing and depth calculation.
    """

    def __init__(
        self,
        config: Optional[OrderBookConfig] = None,
    ):
        self.config = config or OrderBookConfig()

        self._symbol_books: Dict[str, OrderBookBuilder] = {}
        self._last_snapshots: Dict[str, datetime] = {}
        self._callbacks: List[Callable] = []

        self._stats = {
            "ticks_processed": 0,
            "snapshots_generated": 0,
            "symbols_tracked": 0,
        }

        self._lock = threading.RLock()

    def register_callback(self, callback: Callable[[OrderBook], None]) -> None:
        self._callbacks.append(callback)

    def process_tick(self, tick: Tick) -> Optional[OrderBook]:
        with self._lock:
            key = f"{tick.symbol}:{tick.exchange.value}"

            if key not in self._symbol_books:
                self._symbol_books[key] = OrderBookBuilder(max_depth=self.config.max_depth)
                self._stats["symbols_tracked"] += 1

            book = self._symbol_books[key]
            book.apply_tick(tick)

            self._stats["ticks_processed"] += 1

            should_snapshot = self._should_snapshot(key)
            if should_snapshot:
                return self._generate_snapshot(key, tick)
            return None

    def _should_snapshot(self, symbol_key: str) -> bool:
        last_time = self._last_snapshots.get(symbol_key)
        if not last_time:
            return True

        elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
        return elapsed >= self.config.snapshot_interval_seconds

    def _generate_snapshot(self, symbol_key: str, tick: Tick) -> OrderBook:
        book = self._symbol_books[symbol_key]
        bid_levels, ask_levels = book.get_top_levels(self.config.max_depth)

        market_depth = book.get_market_depth(self.config.max_depth)

        orderbook = OrderBook(
            symbol=tick.symbol,
            exchange=tick.exchange,
            timestamp=tick.timestamp,
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            total_bid_quantity=book._total_bid_quantity,
            total_ask_quantity=book._total_ask_quantity,
            spread=market_depth.spread,
            spread_percent=market_depth.spread_percent,
            mid_price=market_depth.mid_price,
            depth=self.config.max_depth,
        )

        self._last_snapshots[symbol_key] = datetime.now(timezone.utc)
        self._stats["snapshots_generated"] += 1

        for callback in self._callbacks:
            try:
                callback(orderbook)
            except Exception as e:
                logger.warning(f"Order book callback error: {e}")

        return orderbook

    def get_order_book(self, symbol: str, exchange: Exchange = Exchange.NSE) -> Optional[OrderBook]:
        key = f"{symbol}:{exchange.value}"
        if key not in self._symbol_books:
            return None

        book = self._symbol_books[key]
        bid_levels, ask_levels = book.get_top_levels(self.config.max_depth)

        market_depth = book.get_market_depth(self.config.max_depth)

        return OrderBook(
            symbol=symbol,
            exchange=exchange,
            timestamp=datetime.now(timezone.utc),
            bid_levels=bid_levels,
            ask_levels=ask_levels,
            total_bid_quantity=book._total_bid_quantity,
            total_ask_quantity=book._total_ask_quantity,
            spread=market_depth.spread,
            spread_percent=market_depth.spread_percent,
            mid_price=market_depth.mid_price,
            depth=self.config.max_depth,
        )

    def get_market_depth(self, symbol: str, exchange: Exchange = Exchange.NSE) -> Optional[MarketDepth]:
        key = f"{symbol}:{exchange.value}"
        if key not in self._symbol_books:
            return None
        return self._symbol_books[key].get_market_depth()

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ticks_processed": self._stats["ticks_processed"],
                "snapshots_generated": self._stats["snapshots_generated"],
                "symbols_tracked": len(self._symbol_books),
                "memory_books": len(self._symbol_books),
            }

    def reset(self) -> None:
        with self._lock:
            self._symbol_books.clear()
            self._last_snapshots.clear()
            self._stats = {
                "ticks_processed": 0,
                "snapshots_generated": 0,
                "symbols_tracked": 0,
            }


_processor: Optional[OrderBookProcessor] = None


def get_orderbook_processor() -> OrderBookProcessor:
    global _processor
    if _processor is None:
        _processor = OrderBookProcessor()
    return _processor
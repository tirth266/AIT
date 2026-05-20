"""
Paper Trading Exchange
=======================
Simulates a realistic exchange for paper trading.
"""

import logging
import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from ..engine import TradingEngine, Order, OrderStatus, OrderType, TransactionType, get_trading_engine
from ..order_manager import OrderManager, get_order_manager
from ..execution_engine import ExecutionEngine, SlippageModel, get_execution_engine

logger = logging.getLogger('paper_exchange')


class ExchangeStatus(str, Enum):
    PRE_OPEN = "PRE_OPEN"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    POST_CLOSE = "POST_CLOSE"


@dataclass
class MarketDepth:
    symbol: str
    bid_prices: List[float] = field(default_factory=list)
    bid_quantities: List[int] = field(default_factory=list)
    ask_prices: List[float] = field(default_factory=list)
    ask_quantities: List[int] = field(default_factory=list)
    last_price: float = 0.0
    volume: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OrderBookEntry:
    price: float
    quantity: int
    orders: int


class PaperExchange:
    """
    Simulated exchange for paper trading with realistic behavior.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.order_manager = get_order_manager()
        self.execution_engine = get_execution_engine()
        self.logger = logging.getLogger('paper_exchange')
        
        self._status = ExchangeStatus.PRE_OPEN
        self._orderbook: Dict[str, List] = defaultdict(list)
        self._market_depth: Dict[str, MarketDepth] = {}
        
        self._base_prices: Dict[str, float] = {
            'RELIANCE': 2945.0, 'TCS': 3850.0, 'HDFCBANK': 1680.0,
            'INFY': 1520.0, 'SBIN': 780.0, 'ICICIBANK': 1050.0,
            'KOTAKBANK': 1850.0, 'AXISBANK': 980.0, 'MARUTI': 11200.0,
            'BAJFINANCE': 7200.0, 'HINDUNILVR': 2800.0, 'NESTLEIND': 2500.0,
            'TITAN': 3500.0, 'SUNPHARMA': 1800.0, 'CIPLA': 1400.0,
        }
        
        self._simulate_market = True
        self._tick_interval = 0.5
        
        self._market_task = None
    
    async def start(self) -> None:
        """Start the market simulation loop."""
        if self._market_task is None:
            self._market_task = asyncio.create_task(
                self._market_simulation_loop()
            )
            self.logger.info("Paper exchange simulation started")
    
    async def stop(self) -> None:
        """Stop the market simulation loop."""
        if self._market_task:
            self._market_task.cancel()
            try:
                await self._market_task
            except asyncio.CancelledError:
                pass
            self._market_task = None
            self.logger.info("Paper exchange simulation stopped")
    
    async def _market_simulation_loop(self) -> None:
        while True:
            try:
                if self._simulate_market:
                    await self._update_market_prices()
                    await self._process_pending_orders()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Market simulation error: {e}")
            
            await asyncio.sleep(self._tick_interval)
    
    async def _update_market_prices(self) -> None:
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        
        if 9 <= hour < 15:
            self._status = ExchangeStatus.OPEN
        elif 9 <= hour < 9:
            self._status = ExchangeStatus.PRE_OPEN
        else:
            self._status = ExchangeStatus.CLOSED
        
        for symbol, base_price in self._base_prices.items():
            current_price = self.engine.get_market_price(symbol) or base_price
            
            volatility = 0.002
            change = current_price * random.uniform(-volatility, volatility)
            new_price = max(current_price + change, base_price * 0.9)
            new_price = min(new_price, base_price * 1.1)
            
            self.engine.update_market_price(symbol, round(new_price, 2))
            
            spread = new_price * 0.001
            bid = round(new_price - spread, 2)
            ask = round(new_price + spread, 2)
            
            self._market_depth[symbol] = MarketDepth(
                symbol=symbol,
                bid_prices=[bid, bid - 0.05, bid - 0.1],
                bid_quantities=[random.randint(100, 1000) for _ in range(3)],
                ask_prices=[ask, ask + 0.05, ask + 0.1],
                ask_quantities=[random.randint(100, 1000) for _ in range(3)],
                last_price=round(new_price, 2),
                volume=random.randint(100000, 1000000),
                timestamp=datetime.now(timezone.utc)
            )
    
    async def _process_pending_orders(self) -> None:
        if self._status != ExchangeStatus.OPEN:
            return
        
        for order in list(self.engine.orders.values()):
            if order.status not in [OrderStatus.OPEN.value, OrderStatus.VALIDATED.value]:
                continue
            
            if order.mode != "paper":
                continue
            
            current_price = self.engine.get_market_price(order.symbol)
            if not current_price:
                continue
            
            should_fill = self._check_order_fill_conditions(order, current_price)
            
            if should_fill:
                await self._execute_paper_order(order, current_price)
    
    def _check_order_fill_conditions(self, order: Order, current_price: float) -> bool:
        if order.order_type == OrderType.MARKET.value:
            return True
        
        elif order.order_type == OrderType.LIMIT.value:
            if order.transaction_type == TransactionType.BUY.value:
                return current_price <= order.price
            else:
                return current_price >= order.price
        
        elif order.order_type in [OrderType.SL.value, OrderType.SL_M.value]:
            if order.transaction_type == TransactionType.BUY.value:
                return current_price >= order.trigger_price
            else:
                return current_price <= order.trigger_price
        
        return False
    
    async def _execute_paper_order(self, order: Order, current_price: float) -> None:
        remaining_qty = order.quantity - order.filled_quantity
        if remaining_qty <= 0:
            return
        
        fill_price = SlippageModel.calculate(
            current_price, 
            order.order_type,
            order.transaction_type
        )
        
        available_qty = min(remaining_qty, random.randint(remaining_qty // 2, remaining_qty))
        
        brokerage = self._calculate_paper_brokerage(fill_price * available_qty, order.product_type)
        taxes = self._calculate_paper_taxes(fill_price * available_qty, order.transaction_type)
        
        filled_order, trade = await self.order_manager.fill_order(
            order.order_id,
            available_qty,
            fill_price,
            brokerage,
            taxes
        )
        
        if filled_order and trade:
            self.logger.info(
                f"PAPER FILLED: {order.order_id} | "
                f"{order.transaction_type} {available_qty} {order.symbol} @ {fill_price:.2f} | "
                f"Avg: {filled_order.average_price:.2f} | "
                f"P&L: {filled_order.pnl:.2f}"
            )
            
            from ..position_manager import PositionManager, get_position_manager
            position_manager = get_position_manager()
            await position_manager.process_order_fill(order, trade)
    
    def _calculate_paper_brokerage(self, value: float, product_type: str) -> float:
        rate = 0.00003
        min_brokerage = 20.0
        return max(value * rate, min_brokerage)
    
    def _calculate_paper_taxes(self, value: float, transaction_type: str) -> float:
        stt = value * 0.00025 if transaction_type == "BUY" else value * 0.00125
        exchange_fee = value * 0.00002
        sebi_charges = value * 0.0000015
        stamp_duty = value * 0.00002 if transaction_type == "BUY" else 0
        return stt + exchange_fee + sebi_charges + stamp_duty
    
    def get_market_depth(self, symbol: str) -> Optional[MarketDepth]:
        return self._market_depth.get(symbol.upper())
    
    def get_quote(self, symbol: str) -> Optional[Dict]:
        depth = self.get_market_depth(symbol)
        if not depth:
            return None
        
        return {
            'symbol': symbol.upper(),
            'last_price': depth.last_price,
            'bid': depth.bid_prices[0] if depth.bid_prices else 0,
            'ask': depth.ask_prices[0] if depth.ask_prices else 0,
            'bid_quantity': depth.bid_quantities[0] if depth.bid_quantities else 0,
            'ask_quantity': depth.ask_quantities[0] if depth.ask_quantities else 0,
            'volume': depth.volume,
            'timestamp': depth.timestamp.isoformat()
        }
    
    def get_exchange_status(self) -> str:
        return self._status.value
    
    def get_all_quotes(self) -> Dict[str, Dict]:
        return {symbol: self.get_quote(symbol) for symbol in self._base_prices.keys()}


_paper_exchange = None


def get_paper_exchange() -> PaperExchange:
    """Lazy singleton factory for PaperExchange."""
    global _paper_exchange
    
    if _paper_exchange is None:
        _paper_exchange = PaperExchange()
        
    return _paper_exchange

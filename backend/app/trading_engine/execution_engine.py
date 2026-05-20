"""
Execution Engine
================
Handles order execution, routing, fills, and execution queue.
"""

import logging
import asyncio
import random
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from .engine import TradingEngine, Order, OrderStatus, OrderType, TransactionType, get_trading_engine
from .order_manager import OrderManager, get_order_manager

logger = logging.getLogger('execution_engine')


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    ROUTED = "ROUTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass
class Fill:
    fill_id: str
    order_id: str
    quantity: int
    price: float
    timestamp: datetime
    is_nse: bool = True
    exchange_order_id: Optional[str] = None


@dataclass 
class ExecutionResult:
    success: bool
    order_id: str
    fills: List[Fill]
    error: Optional[str] = None
    execution_time_ms: float = 0


class ExecutionQueue:
    """Queue for managing order execution flow."""
    
    def __init__(self, max_size: int = 10000):
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._processing = False
        self._handlers: Dict[str, Callable] = {}
    
    async def put(self, order: Order, priority: int = 0) -> None:
        await self._queue.put((priority, order))
    
    async def get(self) -> Optional[Order]:
        try:
            priority, order = await asyncio.wait_for(self._queue.get(), timeout=0.1)
            return order
        except asyncio.TimeoutError:
            return None
    
    def size(self) -> int:
        return self._queue.qsize()
    
    def is_empty(self) -> bool:
        return self._queue.empty()


class SlippageModel:
    """Calculates simulated slippage for paper trading."""
    
    @staticmethod
    def calculate(fill_price: float, order_type: str, side: str, 
                  market_volatility: float = 0.02) -> float:
        if order_type == "MARKET":
            slippage_percent = random.uniform(0.001, 0.005) * (1 + market_volatility)
            if side == "BUY":
                return fill_price * (1 + slippage_percent)
            else:
                return fill_price * (1 - slippage_percent)
        
        elif order_type in ["SL", "SL-M"]:
            slippage_percent = random.uniform(0.0005, 0.002) * (1 + market_volatility)
            if side == "BUY":
                return fill_price * (1 - slippage_percent)
            else:
                return fill_price * (1 + slippage_percent)
        
        return fill_price
    
    @staticmethod
    def get_slippage_for_symbol(symbol: str, base_price: float) -> float:
        high_volatility_symbols = ['RELIANCE', 'TATASTEEL', 'ADANIPOWER', 'YESBANK']
        low_volatility_symbols = ['HDFCBANK', 'TCS', 'INFY']
        
        if symbol in high_volatility_symbols:
            return base_price * random.uniform(0.002, 0.008)
        elif symbol in low_volatility_symbols:
            return base_price * random.uniform(0.0005, 0.001)
        else:
            return base_price * random.uniform(0.001, 0.003)


class FillEngine:
    """Handles fill generation and partial fills."""
    
    def __init__(self):
        self.logger = logging.getLogger('fill_engine')
    
    async def generate_fills(self, order: Order, available_quantity: int, 
                           current_price: float) -> List[Fill]:
        fills = []
        
        if order.order_type == OrderType.MARKET.value:
            fill_price = SlippageModel.calculate(
                current_price, 
                order.order_type,
                order.transaction_type
            )
            
            if available_quantity >= order.quantity - order.filled_quantity:
                fill = Fill(
                    fill_id=f"FILL{random.randint(100000, 999999)}",
                    order_id=order.order_id,
                    quantity=order.quantity - order.filled_quantity,
                    price=fill_price,
                    timestamp=datetime.now(timezone.utc),
                )
                fills.append(fill)
            else:
                fill = Fill(
                    fill_id=f"FILL{random.randint(100000, 999999)}",
                    order_id=order.order_id,
                    quantity=available_quantity,
                    price=fill_price,
                    timestamp=datetime.now(timezone.utc),
                )
                fills.append(fill)
        
        elif order.order_type == OrderType.LIMIT.value:
            if order.transaction_type == TransactionType.BUY.value:
                if current_price <= order.price:
                    fill_price = min(order.price, current_price)
                else:
                    return fills
            else:
                if current_price >= order.price:
                    fill_price = max(order.price, current_price)
                else:
                    return fills
            
            fill = Fill(
                fill_id=f"FILL{random.randint(100000, 999999)}",
                order_id=order.order_id,
                quantity=min(available_quantity, order.quantity - order.filled_quantity),
                price=fill_price,
                timestamp=datetime.now(timezone.utc),
            )
            fills.append(fill)
        
        elif order.order_type in [OrderType.SL.value, OrderType.SL_M.value]:
            if order.transaction_type == TransactionType.BUY.value:
                if current_price >= order.trigger_price:
                    fill_price = order.price if order.price > 0 else current_price
                else:
                    return fills
            else:
                if current_price <= order.trigger_price:
                    fill_price = order.price if order.price > 0 else current_price
                else:
                    return fills
            
            fill = Fill(
                fill_id=f"FILL{random.randint(100000, 999999)}",
                order_id=order.order_id,
                quantity=min(available_quantity, order.quantity - order.filled_quantity),
                price=fill_price,
                timestamp=datetime.now(timezone.utc),
            )
            fills.append(fill)
        
        return fills


class RetryManager:
    """Manages retry logic for failed orders."""
    
    def __init__(self, max_retries: int = 3, backoff_seconds: int = 1):
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.retry_counts: Dict[str, int] = {}
        self.retry_queue: Dict[str, Order] = {}
        self.logger = logging.getLogger('retry_manager')
    
    def should_retry(self, order_id: str) -> bool:
        return self.retry_counts.get(order_id, 0) < self.max_retries
    
    async def retry_order(self, order: Order) -> None:
        order_id = order.order_id
        retry_count = self.retry_counts.get(order_id, 0)
        
        if retry_count >= self.max_retries:
            self.logger.warning(f"Max retries reached for order {order_id}")
            return
        
        self.retry_counts[order_id] = retry_count + 1
        self.retry_queue[order_id] = order
        
        delay = self.backoff_seconds * (2 ** retry_count)
        await asyncio.sleep(delay)
        
        self.logger.info(f"Retrying order {order_id}, attempt {retry_count + 1}")
    
    def clear_retry(self, order_id: str) -> None:
        self.retry_counts.pop(order_id, None)
        self.retry_queue.pop(order_id, None)


class ExecutionEngine:
    """
    Low-latency execution engine for order routing and fills.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.order_manager = get_order_manager()
        
        self.execution_queue = ExecutionQueue()
        self.fill_engine = FillEngine()
        self.retry_manager = RetryManager()
        
        self._execution_callbacks: List[Callable] = []
        self._market_data_callbacks: Dict[str, Callable] = {}
        
        self.logger = logging.getLogger('execution_engine')
        
        self._execution_task = None
        self._running = False
    
    async def start(self) -> None:
        """Start the execution engine loop."""
        if self._running:
            return
            
        self._running = True
        self._execution_task = asyncio.create_task(self._execution_loop())
        self.logger.info("Execution engine started")
    
    async def stop(self) -> None:
        """Stop the execution engine loop."""
        self._running = False
        
        if self._execution_task:
            self._execution_task.cancel()
            try:
                await self._execution_task
            except asyncio.CancelledError:
                pass
            self._execution_task = None
        self.logger.info("Execution engine stopped")
    
    async def _execution_loop(self) -> None:
        while self._running:
            try:
                order = await self.execution_queue.get()
                if order:
                    await self._process_order(order)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Execution loop error: {e}")
            await asyncio.sleep(0.05)
    
    async def _process_order(self, order: Order) -> None:
        start_time = datetime.now(timezone.utc)
        
        if order.status not in [OrderStatus.VALIDATED.value, OrderStatus.OPEN.value]:
            return
        
        current_price = self.engine.get_market_price(order.symbol)
        if not current_price:
            current_price = self._get_simulated_price(order.symbol)
        
        await self.order_manager._transition_status(order, OrderStatus.OPEN.value)
        
        available_qty = 100
        
        fills = await self.fill_engine.generate_fills(order, available_qty, current_price)
        
        for fill in fills:
            brokerage = self._calculate_brokerage(fill.price * fill.quantity, order.product_type)
            taxes = self._calculate_taxes(fill.price * fill.quantity, order.transaction_type)
            
            filled_order, trade = await self.order_manager.fill_order(
                order.order_id,
                fill.quantity,
                fill.price,
                brokerage,
                taxes
            )
            
            if filled_order and trade:
                self.logger.info(
                    f"Order executed: {order.order_id} | "
                    f"{order.transaction_type} {fill.quantity} {order.symbol} @ {fill.price} | "
                    f"Brokerage: {brokerage:.2f} | Taxes: {taxes:.2f}"
                )
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
        self.logger.debug(f"Order {order.order_id} execution time: {execution_time:.2f}ms")
    
    def _get_simulated_price(self, symbol: str) -> float:
        base_prices = {
            'RELIANCE': 2945.0,
            'TCS': 3850.0,
            'HDFCBANK': 1680.0,
            'INFY': 1520.0,
            'SBIN': 780.0,
            'ICICIBANK': 1050.0,
            'KOTAKBANK': 1850.0,
            'AXISBANK': 980.0,
            'MARUTI': 11200.0,
            'BAJFINANCE': 7200.0,
        }
        base = base_prices.get(symbol, 1000.0)
        return base * random.uniform(0.99, 1.01)
    
    def _calculate_brokerage(self, value: float, product_type: str) -> float:
        brokerage_rate = 0.00003 if product_type == "MIS" else 0.00002
        min_brokerage = 20.0
        return max(value * brokerage_rate, min_brokerage)
    
    def _calculate_taxes(self, value: float, transaction_type: str) -> float:
        stt = value * 0.00025
        exchange_turnover = value * 0.00002
        sebi_charges = value * 0.0000015
        stamp_duty = value * 0.00002 if transaction_type == "BUY" else 0
        
        if transaction_type == "SELL":
            stt = value * 0.00125
        
        return stt + exchange_turnover + sebi_charges + stamp_duty
    
    async def submit_order(self, order: Order) -> bool:
        try:
            await self.execution_queue.put(order)
            return True
        except Exception as e:
            self.logger.error(f"Failed to submit order: {e}")
            return False
    
    async def cancel_execution(self, order_id: str) -> bool:
        self.retry_manager.clear_retry(order_id)
        return True
    
    def register_callback(self, event: str, callback: Callable) -> None:
        self._execution_callbacks.append(callback)
    
    def get_execution_queue_size(self) -> int:
        return self.execution_queue.size()


_execution_engine = None


def get_execution_engine() -> ExecutionEngine:
    """Lazy singleton factory for ExecutionEngine."""
    global _execution_engine

    if _execution_engine is None:
        _execution_engine = ExecutionEngine()

    return _execution_engine

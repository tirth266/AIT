"""
Trading Engine Core
===================
Institutional-grade trading engine for Indian stock markets.
Provides order management, execution, position tracking, and P&L calculation.
"""

import logging
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import threading

logger = logging.getLogger('trading_engine')

class OrderStatus(str, Enum):
    NEW = "NEW"
    VALIDATED = "VALIDATED"
    OPEN = "OPEN"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"

class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"

class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"

class ProductType(str, Enum):
    MIS = "MIS"
    CNC = "CNC"
    NRML = "NRML"

class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"

class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


@dataclass
class Order:
    order_id: str
    user_id: str
    strategy_id: Optional[str] = None
    
    symbol: str = ""
    exchange: str = "NSE"
    order_type: str = "MARKET"
    product_type: str = "MIS"
    transaction_type: str = "BUY"
    
    quantity: int = 0
    filled_quantity: int = 0
    cancelled_quantity: int = 0
    
    price: float = 0.0
    trigger_price: float = 0.0
    average_price: float = 0.0
    
    status: str = "NEW"
    validity: str = "DAY"
    mode: str = "paper"
    
    brokerage: float = 0.0
    taxes: float = 0.0
    pnl: float = 0.0
    
    disclosed_quantity: int = 0
    order_tag: str = ""
    comments: str = ""
    
    source: str = "manual"
    
    parent_order_id: Optional[str] = None
    child_orders: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    filled_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    rejected_reason: Optional[str] = None
    
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            'order_id': self.order_id,
            'user_id': self.user_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'order_type': self.order_type,
            'product_type': self.product_type,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'filled_quantity': self.filled_quantity,
            'cancelled_quantity': self.cancelled_quantity,
            'price': self.price,
            'trigger_price': self.trigger_price,
            'average_price': self.average_price,
            'status': self.status,
            'validity': self.validity,
            'mode': self.mode,
            'brokerage': self.brokerage,
            'taxes': self.taxes,
            'pnl': self.pnl,
            'disclosed_quantity': self.disclosed_quantity,
            'order_tag': self.order_tag,
            'comments': self.comments,
            'source': self.source,
            'parent_order_id': self.parent_order_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'filled_at': self.filled_at.isoformat() if self.filled_at else None,
            'cancelled_at': self.cancelled_at.isoformat() if self.cancelled_at else None,
            'rejected_reason': self.rejected_reason,
        }


@dataclass
class Position:
    position_id: str
    user_id: str
    strategy_id: Optional[str] = None
    
    symbol: str = ""
    exchange: str = "NSE"
    product_type: str = "MIS"
    
    quantity: int = 0
    closed_quantity: int = 0
    
    entry_price: float = 0.0
    average_price: float = 0.0
    current_price: float = 0.0
    
    realized_pnl: float = 0.0
    unrealized_pnl: float = 0.0
    day_pnl: float = 0.0
    
    mtm_updated_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    
    mode: str = "paper"
    status: str = "OPEN"

    def to_dict(self) -> Dict:
        return {
            'position_id': self.position_id,
            'user_id': self.user_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'product_type': self.product_type,
            'quantity': self.quantity,
            'closed_quantity': self.closed_quantity,
            'entry_price': self.entry_price,
            'average_price': self.average_price,
            'current_price': self.current_price,
            'realized_pnl': self.realized_pnl,
            'unrealized_pnl': self.unrealized_pnl,
            'day_pnl': self.day_pnl,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'mode': self.mode,
            'status': self.status,
            'opened_at': self.opened_at.isoformat() if self.opened_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'mtm_updated_at': self.mtm_updated_at.isoformat() if self.mtm_updated_at else None,
        }


@dataclass
class Trade:
    trade_id: str
    user_id: str
    order_id: str
    position_id: Optional[str] = None
    strategy_id: Optional[str] = None
    
    symbol: str = ""
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    
    quantity: int = 0
    price: float = 0.0
    value: float = 0.0
    
    brokerage: float = 0.0
    stt: float = 0.0
    gst: float = 0.0
    stamp_duty: float = 0.0
    other_charges: float = 0.0
    
    pnl: float = 0.0
    pnl_percent: float = 0.0
    
    execution_time: Optional[datetime] = None
    mode: str = "paper"

    def to_dict(self) -> Dict:
        return {
            'trade_id': self.trade_id,
            'user_id': self.user_id,
            'order_id': self.order_id,
            'position_id': self.position_id,
            'strategy_id': self.strategy_id,
            'symbol': self.symbol,
            'exchange': self.exchange,
            'transaction_type': self.transaction_type,
            'quantity': self.quantity,
            'price': self.price,
            'value': self.value,
            'brokerage': self.brokerage,
            'stt': self.stt,
            'gst': self.gst,
            'stamp_duty': self.stamp_duty,
            'other_charges': self.other_charges,
            'pnl': self.pnl,
            'pnl_percent': self.pnl_percent,
            'execution_time': self.execution_time.isoformat() if self.execution_time else None,
            'mode': self.mode,
        }


class TradingEngine:
    """
    Central Trading Engine for managing orders, positions, and executions.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self.logger = logging.getLogger('trading_engine')
            
            self.orders: Dict[str, Order] = {}
            self.positions: Dict[str, Position] = {}
            self.trades: Dict[str, Trade] = {}
            
            self.user_orders: Dict[str, Dict[str, Order]] = defaultdict(dict)
            self.user_positions: Dict[str, Dict[str, Position]] = defaultdict(dict)
            self.user_trades: Dict[str, Dict[str, Trade]] = defaultdict(dict)
            
            self._execution_callbacks: List[Callable] = []
            self._order_callbacks: Dict[str, List[Callable]] = defaultdict(list)
            self._position_callbacks: List[Callable] = []
            self._pnl_callbacks: List[Callable] = []
            
            self._market_prices: Dict[str, float] = {}
            self._order_counter = 0
            
            self._order_queue: asyncio.Queue = asyncio.Queue()
            self._execution_thread: Optional[threading.Thread] = None
            self._running = False
            
            self.logger.info("Trading Engine initialized")
    
    def generate_order_id(self, prefix: str = "ORD") -> str:
        self._order_counter += 1
        timestamp = datetime.now(timezone.utc).strftime("%y%m%d")
        return f"{prefix}{timestamp}{self._order_counter:06d}"
    
    def generate_position_id(self, prefix: str = "POS") -> str:
        return f"{prefix}{uuid.uuid4().hex[:12].upper()}"
    
    def generate_trade_id(self, prefix: str = "TRD") -> str:
        return f"{prefix}{uuid.uuid4().hex[:12].upper()}"
    
    def register_order_callback(self, event: str, callback: Callable) -> None:
        self._order_callbacks[event].append(callback)
    
    def register_execution_callback(self, callback: Callable) -> None:
        self._execution_callbacks.append(callback)
    
    def register_position_callback(self, callback: Callable) -> None:
        self._position_callbacks.append(callback)
    
    def register_pnl_callback(self, callback: Callable) -> None:
        self._pnl_callbacks.append(callback)
    
    async def _notify_order_callbacks(self, event: str, order: Order) -> None:
        for callback in self._order_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(order)
                else:
                    callback(order)
            except Exception as e:
                self.logger.error(f"Order callback error: {e}")
    
    async def _notify_execution_callbacks(self, trade: Trade) -> None:
        for callback in self._execution_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(trade)
                else:
                    callback(trade)
            except Exception as e:
                self.logger.error(f"Execution callback error: {e}")
    
    async def _notify_position_callbacks(self, position: Position) -> None:
        for callback in self._position_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(position)
                else:
                    callback(position)
            except Exception as e:
                self.logger.error(f"Position callback error: {e}")
    
    async def _notify_pnl_callbacks(self, user_id: str, pnl_data: Dict) -> None:
        for callback in self._pnl_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(user_id, pnl_data)
                else:
                    callback(user_id, pnl_data)
            except Exception as e:
                self.logger.error(f"PnL callback error: {e}")
    
    def update_market_price(self, symbol: str, price: float) -> None:
        self._market_prices[symbol] = price
    
    def get_market_price(self, symbol: str) -> Optional[float]:
        return self._market_prices.get(symbol)
    
    def get_user_orders(self, user_id: str) -> List[Order]:
        return list(self.user_orders.get(user_id, {}).values())
    
    def get_user_positions(self, user_id: str) -> List[Position]:
        return list(self.user_positions.get(user_id, {}).values())
    
    def get_user_trades(self, user_id: str) -> List[Trade]:
        return list(self.user_trades.get(user_id, {}).values())
    
    def get_order(self, order_id: str) -> Optional[Order]:
        return self.orders.get(order_id)
    
    def get_position(self, position_id: str) -> Optional[Position]:
        return self.positions.get(position_id)
    
    def get_trade(self, trade_id: str) -> Optional[Trade]:
        return self.trades.get(trade_id)
    
    def get_open_position(self, user_id: str, symbol: str, product_type: str = "MIS") -> Optional[Position]:
        user_positions = self.user_positions.get(user_id, {})
        for position in user_positions.values():
            if (position.symbol == symbol and 
                position.product_type == product_type and 
                position.status == "OPEN"):
                return position
        return None
    
    def start(self) -> None:
        if not self._running:
            self._running = True
            self._execution_thread = threading.Thread(target=self._execution_loop, daemon=True)
            self._execution_thread.start()
            self.logger.info("Trading Engine started")
    
    def stop(self) -> None:
        self._running = False
        if self._execution_thread:
            self._execution_thread.join(timeout=5)
        self.logger.info("Trading Engine stopped")
    
    def _execution_loop(self) -> None:
        while self._running:
            try:
                asyncio.run(self._process_order_queue())
            except Exception as e:
                self.logger.error(f"Execution loop error: {e}")
            import time
            time.sleep(0.1)
    
    async def _process_order_queue(self) -> None:
        while not self._order_queue.empty():
            try:
                order = await self._order_queue.get()
                await self._execute_order(order)
            except Exception as e:
                self.logger.error(f"Order processing error: {e}")
    
    async def _execute_order(self, order: Order) -> None:
        pass
    
    def get_order_stats(self, user_id: str, mode: str = "paper") -> Dict:
        user_orders = self.get_user_orders(user_id)
        mode_orders = [o for o in user_orders if o.mode == mode]
        
        total = len(mode_orders)
        open_count = len([o for o in mode_orders if o.status in ["NEW", "VALIDATED", "OPEN", "PARTIALLY_FILLED"]])
        filled = len([o for o in mode_orders if o.status == "FILLED"])
        cancelled = len([o for o in mode_orders if o.status == "CANCELLED"])
        rejected = len([o for o in mode_orders if o.status == "REJECTED"])
        
        buy_orders = len([o for o in mode_orders if o.transaction_type == "BUY"])
        sell_orders = len([o for o in mode_orders if o.transaction_type == "SELL"])
        
        return {
            'total_orders': total,
            'open_orders': open_count,
            'filled_orders': filled,
            'cancelled_orders': cancelled,
            'rejected_orders': rejected,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'fill_rate': round((filled / total * 100) if total > 0 else 0, 2),
            'mode': mode
        }
    
    def get_position_stats(self, user_id: str, mode: str = "paper") -> Dict:
        user_positions = self.get_user_positions(user_id)
        mode_positions = [p for p in user_positions if p.mode == mode]
        
        open_positions = [p for p in mode_positions if p.status == "OPEN"]
        closed_positions = [p for p in mode_positions if p.status == "CLOSED"]
        
        total_realized = sum(p.realized_pnl for p in mode_positions)
        total_unrealized = sum(p.unrealized_pnl for p in open_positions)
        
        return {
            'total_positions': len(mode_positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_realized_pnl': total_realized,
            'total_unrealized_pnl': total_unrealized,
            'total_pnl': total_realized + total_unrealized,
            'mode': mode
        }


trading_engine = TradingEngine()


def get_trading_engine() -> TradingEngine:
    return trading_engine
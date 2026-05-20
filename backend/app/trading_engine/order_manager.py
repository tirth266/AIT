from __future__ import annotations

"""
Order Manager
=============
Manages order lifecycle, validation, and state transitions.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Optional, Any
from enum import Enum

from .engine import (
    TradingEngine, Order, Trade, OrderStatus, OrderType, 
    TransactionType, ProductType, Exchange, get_trading_engine
)

logger = logging.getLogger('order_manager')


class OrderValidator:
    """Validates orders before submission."""
    
    MIN_QUANTITY = 1
    MAX_QUANTITY = 1000000
    
    MIN_PRICE = 0.01
    MAX_PRICE = 1000000.0
    
    VALID_ORDER_TYPES = ["MARKET", "LIMIT", "SL", "SL-M"]
    VALID_TRANSACTION_TYPES = ["BUY", "SELL"]
    VALID_PRODUCT_TYPES = ["MIS", "CNC", "NRML"]
    VALID_EXCHANGES = ["NSE", "BSE"]
    VALID_VALIDITIES = ["DAY", "IOC", "GTD", "GTC"]
    
    @classmethod
    def validate(cls, order_data: dict) -> tuple[bool, Optional[str]]:
        if not order_data.get('symbol'):
            return False, "Symbol is required"
        
        symbol = order_data['symbol'].upper()
        if not symbol or len(symbol) < 1 or len(symbol) > 20:
            return False, "Invalid symbol"
        
        order_type = order_data.get('order_type', 'MARKET').upper()
        if order_type not in cls.VALID_ORDER_TYPES:
            return False, f"Invalid order type: {order_type}"
        
        transaction_type = order_data.get('transaction_type', 'BUY').upper()
        if transaction_type not in cls.VALID_TRANSACTION_TYPES:
            return False, f"Invalid transaction type: {transaction_type}"
        
        product_type = order_data.get('product_type', 'MIS').upper()
        if product_type not in cls.VALID_PRODUCT_TYPES:
            return False, f"Invalid product type: {product_type}"
        
        exchange = order_data.get('exchange', 'NSE').upper()
        if exchange not in cls.VALID_EXCHANGES:
            return False, f"Invalid exchange: {exchange}"
        
        quantity = order_data.get('quantity', 0)
        try:
            quantity = int(quantity)
        except (ValueError, TypeError):
            return False, "Invalid quantity"
        
        if quantity < cls.MIN_QUANTITY or quantity > cls.MAX_QUANTITY:
            return False, f"Quantity must be between {cls.MIN_QUANTITY} and {cls.MAX_QUANTITY}"
        
        price = order_data.get('price', 0)
        trigger_price = order_data.get('trigger_price', 0)
        
        if order_type == "LIMIT":
            if price <= 0:
                return False, "Limit price is required for LIMIT orders"
            if price < cls.MIN_PRICE or price > cls.MAX_PRICE:
                return False, f"Price must be between {cls.MIN_PRICE} and {cls.MAX_PRICE}"
        
        if order_type in ["SL", "SL-M"]:
            if trigger_price <= 0:
                return False, "Trigger price is required for SL/SL-M orders"
            if order_type == "SL" and price <= 0:
                return False, "Limit price is required for SL orders"
        
        if order_type == "SL-M" and trigger_price > 0:
            pass
        
        validity = order_data.get('validity', 'DAY').upper()
        if validity not in cls.VALID_VALIDITIES:
            return False, f"Invalid validity: {validity}"
        
        disclosed = order_data.get('disclosed_quantity', 0)
        if disclosed > quantity:
            return False, "Disclosed quantity cannot exceed order quantity"
        
        return True, None


class OrderManager:
    """
    Manages order creation, validation, and lifecycle.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.validator = OrderValidator()
        self.logger = logging.getLogger('order_manager')
    
    async def create_order(self, order_data: dict) -> tuple[Optional[Order], Optional[str]]:
        is_valid, error = self.validator.validate(order_data)
        if not is_valid:
            return None, error
        
        user_id = order_data.get('user_id')
        if not user_id:
            return None, "User ID is required"
        
        order_id = self.engine.generate_order_id()
        
        order = Order(
            order_id=order_id,
            user_id=user_id,
            strategy_id=order_data.get('strategy_id'),
            
            symbol=order_data['symbol'].upper(),
            exchange=order_data.get('exchange', 'NSE').upper(),
            order_type=order_data.get('order_type', 'MARKET').upper(),
            product_type=order_data.get('product_type', 'MIS').upper(),
            transaction_type=order_data.get('transaction_type', 'BUY').upper(),
            
            quantity=int(order_data['quantity']),
            price=float(order_data.get('price', 0)),
            trigger_price=float(order_data.get('trigger_price', 0)),
            
            validity=order_data.get('validity', 'DAY').upper(),
            mode=order_data.get('mode', 'paper'),
            
            disclosed_quantity=int(order_data.get('disclosed_quantity', 0)),
            order_tag=order_data.get('order_tag', ''),
            comments=order_data.get('comments', ''),
            source=order_data.get('source', 'manual'),
            
            status=OrderStatus.NEW.value,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        self.engine.orders[order_id] = order
        self.engine.user_orders[user_id][order_id] = order
        
        await self._transition_status(order, OrderStatus.VALIDATED)
        
        self.logger.info(f"Order created: {order_id} - {order.transaction_type} {order.quantity} {order.symbol} @ {order.price}")
        
        return order, None
    
    async def _transition_status(self, order: Order, new_status: str) -> None:
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.now(timezone.utc)
        
        if new_status == OrderStatus.FILLED.value:
            order.filled_at = datetime.now(timezone.utc)
        elif new_status == OrderStatus.CANCELLED.value:
            order.cancelled_at = datetime.now(timezone.utc)
        elif new_status == OrderStatus.REJECTED.value:
            order.rejected_at = datetime.now(timezone.utc)
        
        await self.engine._notify_order_callbacks(f"status_{new_status.lower()}", order)
        await self.engine._notify_order_callbacks("status_changed", order)
        
        self.logger.info(f"Order {order.order_id} status: {old_status} -> {new_status}")
    
    async def update_order(self, order_id: str, update_data: dict) -> tuple[Optional[Order], Optional[str]]:
        order = self.engine.get_order(order_id)
        if not order:
            return None, "Order not found"
        
        if order.status in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.REJECTED.value]:
            return None, f"Cannot modify order with status {order.status}"
        
        if 'price' in update_data:
            order.price = float(update_data['price'])
        if 'trigger_price' in update_data:
            order.trigger_price = float(update_data['trigger_price'])
        if 'quantity' in update_data:
            new_quantity = int(update_data['quantity'])
            if new_quantity < order.filled_quantity:
                return None, "Quantity cannot be less than filled quantity"
            order.quantity = new_quantity
        if 'validity' in update_data:
            order.validity = update_data['validity'].upper()
        
        order.updated_at = datetime.now(timezone.utc)
        
        await self.engine._notify_order_callbacks("updated", order)
        
        self.logger.info(f"Order modified: {order_id}")
        
        return order, None
    
    async def cancel_order(self, order_id: str, reason: str = "User requested") -> tuple[Optional[Order], Optional[str]]:
        order = self.engine.get_order(order_id)
        if not order:
            return None, "Order not found"
        
        if order.status not in [OrderStatus.NEW.value, OrderStatus.VALIDATED.value, OrderStatus.OPEN.value, OrderStatus.PARTIALLY_FILLED.value]:
            return None, f"Cannot cancel order with status {order.status}"
        
        if order.filled_quantity > 0:
            order.cancelled_quantity = order.quantity - order.filled_quantity
        
        await self._transition_status(order, OrderStatus.CANCELLED.value)
        
        order.rejected_reason = reason
        order.updated_at = datetime.now(timezone.utc)
        
        self.logger.info(f"Order cancelled: {order_id} - {reason}")
        
        return order, None
    
    async def fill_order(self, order_id: str, fill_quantity: int, fill_price: float, 
                        brokerage: float = 0, taxes: float = 0) -> tuple[Optional[Order], Optional[Trade]]:
        order = self.engine.get_order(order_id)
        if not order:
            return None, None
        
        if order.status == OrderStatus.FILLED.value:
            return None, None
        
        new_filled = order.filled_quantity + fill_quantity
        total_value = (order.average_price * order.filled_quantity) + (fill_price * fill_quantity)
        order.average_price = total_value / new_filled if new_filled > 0 else fill_price
        order.filled_quantity = new_filled
        order.brokerage += brokerage
        order.taxes += taxes
        
        if new_filled >= order.quantity:
            await self._transition_status(order, OrderStatus.FILLED.value)
        else:
            await self._transition_status(order, OrderStatus.PARTIALLY_FILLED.value)
        
        order.updated_at = datetime.now(timezone.utc)
        
        trade = Trade(
            trade_id=self.engine.generate_trade_id(),
            user_id=order.user_id,
            order_id=order_id,
            position_id=None,
            strategy_id=order.strategy_id,
            symbol=order.symbol,
            exchange=order.exchange,
            transaction_type=order.transaction_type,
            quantity=fill_quantity,
            price=fill_price,
            value=fill_price * fill_quantity,
            brokerage=brokerage,
            stt=taxes * 0.1,
            gst=brokerage * 0.18,
            stamp_duty=0.002,
            execution_time=datetime.now(timezone.utc),
            mode=order.mode,
        )
        
        self.engine.trades[trade.trade_id] = trade
        self.engine.user_trades[order.user_id][trade.trade_id] = trade
        
        await self.engine._notify_execution_callbacks(trade)
        
        self.logger.info(f"Order filled: {order_id} - {fill_quantity} @ {fill_price}")
        
        return order, trade
    
    async def reject_order(self, order_id: str, reason: str) -> tuple[Optional[Order], Optional[str]]:
        order = self.engine.get_order(order_id)
        if not order:
            return None, "Order not found"
        
        if order.status in [OrderStatus.FILLED.value, OrderStatus.CANCELLED.value]:
            return None, f"Cannot reject order with status {order.status}"
        
        await self._transition_status(order, OrderStatus.REJECTED.value)
        
        order.rejected_reason = reason
        order.updated_at = datetime.now(timezone.utc)
        
        self.logger.warning(f"Order rejected: {order_id} - {reason}")
        
        return order, None
    
    def get_order(self, order_id: str) -> Optional[Order]:
        return self.engine.get_order(order_id)
    
    def get_user_orders(self, user_id: str, filters: Optional[dict] = None) -> list[Order]:
        orders = self.engine.get_user_orders(user_id)
        
        if not filters:
            return orders
        
        filtered = []
        for order in orders:
            if filters.get('status') and order.status != filters['status']:
                continue
            if filters.get('order_type') and order.order_type != filters['order_type']:
                continue
            if filters.get('transaction_type') and order.transaction_type != filters['transaction_type']:
                continue
            if filters.get('symbol') and order.symbol != filters['symbol'].upper():
                continue
            if filters.get('mode') and order.mode != filters['mode']:
                continue
            filtered.append(order)
        
        return filtered


order_manager = OrderManager()


def get_order_manager() -> OrderManager:
    return order_manager
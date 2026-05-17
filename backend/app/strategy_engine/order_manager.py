"""
Order Manager
=============
Manages order placement, tracking, and execution logic.
"""

import logging
import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger('order_manager')


class OrderType(Enum):
    MARKET = 'MARKET'
    LIMIT = 'LIMIT'
    STOP_LOSS = 'SL'
    STOP_LOSS_MARKET = 'SL-M'


class OrderSide(Enum):
    BUY = 'BUY'
    SELL = 'SELL'


class OrderValidity(Enum):
    DAY = 'DAY'
    IOC = 'IOC'
    GTD = 'GTD'
    GTC = 'GTC'


@dataclass
class Order:
    order_id: str
    user_id: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    order_type: str
    price: Optional[float]
    trigger_price: Optional[float]
    status: str
    filled_quantity: int = 0
    average_price: Optional[float] = None
    created_at: Optional[datetime] = None
    filled_at: Optional[datetime] = None


class OrderManager:
    """
    Manages order lifecycle, retries, and tracking.
    """

    def __init__(self):
        self._pending_orders: Dict[str, Order] = {}
        self._order_history: List[Order] = []
        self._max_retries = 3
        self._retry_delay = 2

    async def place_order(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        order_type: str = 'MARKET',
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        validity: str = 'DAY'
    ) -> Optional[str]:
        """
        Place a new order.

        Args:
            user_id: User ID
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Order quantity
            order_type: MARKET, LIMIT, SL, or SL-M
            price: Limit price (for LIMIT orders)
            trigger_price: Trigger price (for SL orders)
            validity: Order validity

        Returns:
            Order ID or None
        """
        try:
            order_id = self._generate_order_id()

            order = Order(
                order_id=order_id,
                user_id=user_id,
                symbol=symbol,
                exchange='NSE',
                side=side.upper(),
                quantity=quantity,
                order_type=order_type.upper(),
                price=price,
                trigger_price=trigger_price,
                status='pending',
                created_at=datetime.utcnow()
            )

            self._pending_orders[order_id] = order

            executed = await self._execute_order(order)

            if executed:
                return order_id
            else:
                return None

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def _execute_order(self, order: Order) -> bool:
        """
        Execute an order (simulated for paper trading).

        Args:
            order: Order object

        Returns:
            True if executed
        """
        try:
            if order.order_type == 'MARKET':
                await asyncio.sleep(0.5)

                execution_price = self._simulate_market_price(order.symbol)

                order.filled_quantity = order.quantity
                order.average_price = execution_price
                order.status = 'executed'
                order.filled_at = datetime.utcnow()

            elif order.order_type == 'LIMIT':
                if not order.price:
                    order.status = 'rejected'
                    return False

                await asyncio.sleep(1)

                current_price = self._simulate_market_price(order.symbol)

                if (order.side == 'BUY' and current_price <= order.price) or \
                   (order.side == 'SELL' and current_price >= order.price):

                    order.filled_quantity = order.quantity
                    order.average_price = order.price
                    order.status = 'executed'
                    order.filled_at = datetime.utcnow()
                else:
                    order.status = 'cancelled'
                    return False

            self._order_history.append(order)
            if order.order_id in self._pending_orders:
                del self._pending_orders[order.order_id]

            logger.info(f"Order executed: {order.order_id} {order.side} {order.quantity} @ {order.average_price}")
            return True

        except Exception as e:
            logger.error(f"Order execution error: {e}")
            order.status = 'rejected'
            return False

    def _simulate_market_price(self, symbol: str) -> float:
        """Simulate current market price."""
        import random
        base_prices = {
            'RELIANCE': 2500,
            'TCS': 3500,
            'INFY': 1500,
            'HDFCBANK': 1600,
            'ICICIBANK': 950,
            'SBIN': 600,
            'BHARTIARTL': 800,
            'KOTAKBANK': 1800,
            'LT': 3200,
            'HINDUNILVR': 2400
        }

        base = base_prices.get(symbol.upper(), 1000)
        variation = random.uniform(-0.5, 0.5)
        return round(base * (1 + variation / 100), 2)

    def _generate_order_id(self) -> str:
        """Generate unique order ID."""
        import uuid
        return f"ORD{uuid.uuid4().hex[:12].upper()}"

    async def modify_order(
        self,
        order_id: str,
        price: Optional[float] = None,
        quantity: Optional[int] = None,
        trigger_price: Optional[float] = None
    ) -> bool:
        """Modify an existing order."""
        if order_id not in self._pending_orders:
            order = next((o for o in self._order_history if o.order_id == order_id), None)
            if not order or order.status != 'pending':
                return False
        else:
            order = self._pending_orders[order_id]

        if price is not None:
            order.price = price
        if quantity is not None:
            order.quantity = quantity
        if trigger_price is not None:
            order.trigger_price = trigger_price

        logger.info(f"Order modified: {order_id}")
        return True

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order."""
        if order_id in self._pending_orders:
            order = self._pending_orders[order_id]
            order.status = 'cancelled'
            del self._pending_orders[order_id]
            logger.info(f"Order cancelled: {order_id}")
            return True

        return False

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order details."""
        if order_id in self._pending_orders:
            return self._pending_orders[order_id]

        for order in self._order_history:
            if order.order_id == order_id:
                return order

        return None

    def get_pending_orders(self, user_id: str) -> List[Order]:
        """Get pending orders for a user."""
        return [o for o in self._pending_orders.values() if o.user_id == user_id]

    def get_order_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Order]:
        """Get order history for a user."""
        user_orders = [o for o in self._order_history if o.user_id == user_id]
        return user_orders[-limit:]

    async def retry_order(self, order_id: str) -> bool:
        """Retry a failed order."""
        order = self.get_order(order_id)
        if not order:
            return False

        order.status = 'pending'
        self._pending_orders[order_id] = order

        for attempt in range(self._max_retries):
            try:
                executed = await self._execute_order(order)
                if executed:
                    return True
            except Exception as e:
                logger.error(f"Retry attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(self._retry_delay * (attempt + 1))

        order.status = 'failed'
        return False
"""
Order Throttler & Fat Finger Protection
========================================
Institutional-grade order rate limiting, value limits, and protection against erroneous trades.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict, deque
import logging

logger = logging.getLogger('risk_engine.throttler')


class ThrottleAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    COOLDOWN = "cooldown"


@dataclass
class ThrottleResult:
    """Result of throttle check."""
    action: ThrottleAction
    reason: str
    current_value: float
    limit_value: float
    cooldown_until: Optional[datetime] = None
    remaining_window: Optional[float] = None


@dataclass
class OrderRecord:
    """Record of an order for rate limiting."""
    order_id: str
    user_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    value: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FatFingerConfig:
    """Configuration for fat finger protection."""
    max_single_order_value: float = 1000000.0
    max_single_order_quantity: int = 10000
    max_order_percent_portfolio: float = 20.0
    max_deviation_from_market: float = 10.0
    require_confirmation_above: float = 500000.0
    auto_cancel_above: float = 5000000.0


@dataclass
class ThrottleConfig:
    """Configuration for order throttling."""
    orders_per_second: int = 10
    orders_per_minute: int = 100
    orders_per_hour: int = 1000
    value_per_minute: float = 1000000.0
    value_per_hour: float = 10000000.0
    cooldown_seconds: int = 60
    max_position_orders_per_minute: int = 50


class OrderThrottler:
    """
    Order throttling and fat finger protection system.
    """

    def __init__(self):
        self.logger = logging.getLogger('order_throttler')

        self._user_configs: Dict[str, ThrottleConfig] = {}
        self._fat_finger_configs: Dict[str, FatFingerConfig] = {}

        self._order_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._value_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))

        self._cooldowns: Dict[str, datetime] = {}

        self._breach_count: Dict[str, int] = defaultdict(int)
        self._total_orders_blocked = 0

    def set_throttle_config(self, user_id: str, config: ThrottleConfig) -> None:
        """Set throttle configuration for a user."""
        self._user_configs[user_id] = config

    def get_throttle_config(self, user_id: str) -> ThrottleConfig:
        """Get throttle configuration for a user."""
        default_config = ThrottleConfig()
        return self._user_configs.get(user_id, default_config)

    def set_fat_finger_config(self, user_id: str, config: FatFingerConfig) -> None:
        """Set fat finger configuration for a user."""
        self._fat_finger_configs[user_id] = config

    def get_fat_finger_config(self, user_id: str) -> FatFingerConfig:
        """Get fat finger configuration for a user."""
        default_config = FatFingerConfig()
        return self._fat_finger_configs.get(user_id, default_config)

    async def check_order(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_id: str = None
    ) -> ThrottleResult:
        """Check if an order should be allowed."""
        config = self.get_throttle_config(user_id)
        ff_config = self.get_fat_finger_config(user_id)

        order_value = quantity * price
        now = datetime.now(timezone.utc)

        if self._is_in_cooldown(user_id):
            cooldown_until = self._cooldowns.get(user_id)
            remaining = (cooldown_until - now).total_seconds() if cooldown_until else 0
            return ThrottleResult(
                action=ThrottleAction.COOLDOWN,
                reason=f"User in cooldown period",
                current_value=0,
                limit_value=0,
                cooldown_until=cooldown_until,
                remaining_window=remaining
            )

        fat_finger_result = self._check_fat_finger(
            user_id, symbol, quantity, price, order_value, ff_config
        )
        if fat_finger_result.action != ThrottleAction.ALLOW:
            return fat_finger_result

        rate_limit_result = self._check_rate_limits(user_id, now, config)
        if rate_limit_result.action != ThrottleAction.ALLOW:
            return rate_limit_result

        position_rate_result = self._check_position_rate_limit(user_id, symbol, now, config)
        if position_rate_result.action != ThrottleAction.ALLOW:
            return position_rate_result

        self._record_order(user_id, order_id or f"ord_{time.time()}", symbol, side, quantity, price, order_value)

        return ThrottleResult(
            action=ThrottleAction.ALLOW,
            reason="Order allowed",
            current_value=order_value,
            limit_value=config.value_per_minute
        )

    def _check_fat_finger(
        self,
        user_id: str,
        symbol: str,
        quantity: int,
        price: float,
        order_value: float,
        config: FatFingerConfig
    ) -> ThrottleResult:
        """Check for fat finger violations."""
        if order_value > config.auto_cancel_above:
            self.logger.critical(f"FAT FINGER: Auto-cancel threshold exceeded: {order_value}")
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Order value {order_value} exceeds auto-cancel threshold {config.auto_cancel_above}",
                current_value=order_value,
                limit_value=config.auto_cancel_above
            )

        if order_value > config.max_single_order_value:
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Order value {order_value} exceeds max single order {config.max_single_order_value}",
                current_value=order_value,
                limit_value=config.max_single_order_value
            )

        if quantity > config.max_single_order_quantity:
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Order quantity {quantity} exceeds max {config.max_single_order_quantity}",
                current_value=quantity,
                limit_value=config.max_single_order_quantity
            )

        if order_value > config.require_confirmation_above:
            self.logger.warning(f"Order {order_value} above confirmation threshold")
            return ThrottleResult(
                action=ThrottleAction.WARN,
                reason=f"Order above confirmation threshold - manual review recommended",
                current_value=order_value,
                limit_value=config.require_confirmation_above
            )

        return ThrottleResult(
            action=ThrottleAction.ALLOW,
            reason="Fat finger check passed",
            current_value=order_value,
            limit_value=config.max_single_order_value
        )

    def _check_rate_limits(
        self,
        user_id: str,
        now: datetime,
        config: ThrottleConfig
    ) -> ThrottleResult:
        """Check rate limiting."""
        history = self._order_history[user_id]

        second_ago = now.timestamp() - 1
        minute_ago = now.timestamp() - 60
        hour_ago = now.timestamp() - 3600

        orders_last_second = sum(1 for o in history if o.timestamp.timestamp() >= second_ago)
        orders_last_minute = sum(1 for o in history if o.timestamp.timestamp() >= minute_ago)
        orders_last_hour = sum(1 for o in history if o.timestamp.timestamp() >= hour_ago)

        if orders_last_second >= config.orders_per_second:
            self._trigger_cooldown(user_id, config)
            self._breach_count[user_id] += 1
            self._total_orders_blocked += 1
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Rate limit exceeded: {orders_last_second} orders/sec (limit: {config.orders_per_second})",
                current_value=orders_last_second,
                limit_value=config.orders_per_second
            )

        if orders_last_minute >= config.orders_per_minute:
            self._trigger_cooldown(user_id, config)
            self._breach_count[user_id] += 1
            self._total_orders_blocked += 1
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Rate limit exceeded: {orders_last_minute} orders/min (limit: {config.orders_per_minute})",
                current_value=orders_last_minute,
                limit_value=config.orders_per_minute
            )

        if orders_last_hour >= config.orders_per_hour:
            self._breach_count[user_id] += 1
            return ThrottleResult(
                action=ThrottleAction.WARN,
                reason=f"Hourly order limit approaching: {orders_last_hour}/{config.orders_per_hour}",
                current_value=orders_last_hour,
                limit_value=config.orders_per_hour
            )

        value_history = self._value_history[user_id]
        value_last_minute = sum(o.value for o in value_history if o.timestamp.timestamp() >= minute_ago)
        value_last_hour = sum(o.value for o in value_history if o.timestamp.timestamp() >= hour_ago)

        if value_last_minute >= config.value_per_minute:
            self._trigger_cooldown(user_id, config)
            self._breach_count[user_id] += 1
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Value limit exceeded: {value_last_minute} (limit: {config.value_per_minute})",
                current_value=value_last_minute,
                limit_value=config.value_per_minute
            )

        return ThrottleResult(
            action=ThrottleAction.ALLOW,
            reason="Rate limits OK",
            current_value=orders_last_minute,
            limit_value=config.orders_per_minute
        )

    def _check_position_rate_limit(
        self,
        user_id: str,
        symbol: str,
        now: datetime,
        config: ThrottleConfig
    ) -> ThrottleResult:
        """Check per-symbol rate limits."""
        key = f"{user_id}:{symbol}"
        history = self._order_history.get(key, deque())

        minute_ago = now.timestamp() - 60
        orders_last_minute = sum(1 for o in history if o.timestamp.timestamp() >= minute_ago)

        if orders_last_minute >= config.max_position_orders_per_minute:
            return ThrottleResult(
                action=ThrottleAction.BLOCK,
                reason=f"Symbol {symbol}: {orders_last_minute} orders/min (limit: {config.max_position_orders_per_minute})",
                current_value=orders_last_minute,
                limit_value=config.max_position_orders_per_minute
            )

        return ThrottleResult(
            action=ThrottleAction.ALLOW,
            reason="Position rate OK",
            current_value=orders_last_minute,
            limit_value=config.max_position_orders_per_minute
        )

    def _record_order(
        self,
        user_id: str,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        value: float
    ) -> None:
        """Record order for rate limiting."""
        record = OrderRecord(
            order_id=order_id,
            user_id=user_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            value=value
        )

        self._order_history[user_id].append(record)
        self._value_history[user_id].append(record)

        symbol_key = f"{user_id}:{symbol}"
        self._order_history[symbol_key].append(record)

    def _trigger_cooldown(self, user_id: str, config: ThrottleConfig) -> None:
        """Trigger cooldown period after breach."""
        cooldown_until = datetime.now(timezone.utc) + timedelta(seconds=config.cooldown_seconds)
        self._cooldowns[user_id] = cooldown_until
        self.logger.warning(f"Cooldown triggered for user {user_id} until {cooldown_until}")

    def _is_in_cooldown(self, user_id: str) -> bool:
        """Check if user is in cooldown period."""
        if user_id not in self._cooldowns:
            return False

        if datetime.now(timezone.utc) >= self._cooldowns[user_id]:
            del self._cooldowns[user_id]
            return False

        return True

    def get_user_stats(self, user_id: str) -> Dict:
        """Get user's throttling statistics."""
        history = self._order_history.get(user_id, [])
        config = self.get_throttle_config(user_id)
        now = datetime.now(timezone.utc)

        second_ago = now.timestamp() - 1
        minute_ago = now.timestamp() - 60
        hour_ago = now.timestamp() - 3600

        return {
            'orders_last_second': sum(1 for o in history if o.timestamp.timestamp() >= second_ago),
            'orders_last_minute': sum(1 for o in history if o.timestamp.timestamp() >= minute_ago),
            'orders_last_hour': sum(1 for o in history if o.timestamp.timestamp() >= hour_ago),
            'value_last_minute': sum(o.value for o in self._value_history.get(user_id, [])
                                     if o.timestamp.timestamp() >= minute_ago),
            'breach_count': self._breach_count.get(user_id, 0),
            'in_cooldown': self._is_in_cooldown(user_id),
            'limits': {
                'orders_per_second': config.orders_per_second,
                'orders_per_minute': config.orders_per_minute,
                'value_per_minute': config.value_per_minute,
                'cooldown_seconds': config.cooldown_seconds
            }
        }

    def get_global_stats(self) -> Dict:
        """Get global throttling statistics."""
        return {
            'total_orders_blocked': self._total_orders_blocked,
            'active_users': len(self._order_history),
            'users_in_cooldown': sum(1 for u in self._cooldowns if self._is_in_cooldown(u))
        }

    def reset_user(self, user_id: str) -> None:
        """Reset throttling state for a user."""
        if user_id in self._order_history:
            self._order_history[user_id].clear()
        if user_id in self._value_history:
            self._value_history[user_id].clear()
        if user_id in self._cooldowns:
            del self._cooldowns[user_id]
        if user_id in self._breach_count:
            del self._breach_count[user_id]


order_throttler = OrderThrottler()


def get_order_throttler() -> OrderThrottler:
    return order_throttler
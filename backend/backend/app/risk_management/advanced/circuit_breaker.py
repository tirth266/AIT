"""
Circuit Breaker System
======================
Institutional-grade circuit breakers for market, loss, volume, and correlation events.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from collections import defaultdict, deque
import logging
import numpy as np

logger = logging.getLogger('risk_engine.circuit_breaker')


class CircuitBreakerType(str, Enum):
    PRICE = "price"
    LOSS = "loss"
    VOLUME = "volume"
    CORRELATION = "correlation"
    MARGIN = "margin"
    DRAWDOWN = "drawdown"


class CircuitBreakerState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerAction(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    HALT = "halt"


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    threshold: float
    window_seconds: int = 300
    reset_window_seconds: int = 3600
    trigger_count: int = 3
    action: CircuitBreakerAction = CircuitBreakerAction.BLOCK


@dataclass
class CircuitBreakerStatus:
    """Status of a circuit breaker."""
    breaker_type: CircuitBreakerType
    state: CircuitBreakerState
    current_value: float
    threshold: float
    trigger_count: int
    last_triggered: Optional[datetime]
    opened_at: Optional[datetime]
    auto_reset_at: Optional[datetime]


class CircuitBreaker:
    """
    Comprehensive circuit breaker system for multiple risk scenarios.
    """

    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('circuit_breaker')
        self.risk_engine = risk_engine

        self._breakers: Dict[str, Dict[CircuitBreakerType, CircuitBreakerStatus]] = defaultdict(dict)
        self._configs: Dict[str, Dict[CircuitBreakerType, CircuitBreakerConfig]] = defaultdict(dict)
        self._events: Dict[str, List[Dict]] = defaultdict(list)
        self._price_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

    def configure_breaker(
        self,
        user_id: str,
        breaker_type: CircuitBreakerType,
        config: CircuitBreakerConfig
    ) -> None:
        """Configure a circuit breaker for a user."""
        if user_id not in self._configs:
            self._configs[user_id] = {}

        self._configs[user_id][breaker_type] = config

        self._breakers[user_id][breaker_type] = CircuitBreakerStatus(
            breaker_type=breaker_type,
            state=CircuitBreakerState.CLOSED,
            current_value=0,
            threshold=config.threshold,
            trigger_count=0,
            last_triggered=None,
            opened_at=None,
            auto_reset_at=None
        )

        self.logger.info(f"Configured {breaker_type} breaker for {user_id}: threshold={config.threshold}")

    def get_default_configs(self, user_id: str) -> Dict[CircuitBreakerType, CircuitBreakerConfig]:
        """Get default circuit breaker configurations."""
        return {
            CircuitBreakerType.LOSS: CircuitBreakerConfig(
                threshold=5000,
                window_seconds=300,
                reset_window_seconds=3600,
                trigger_count=3,
                action=CircuitBreakerAction.BLOCK
            ),
            CircuitBreakerType.DRAWDOWN: CircuitBreakerConfig(
                threshold=10,
                window_seconds=900,
                reset_window_seconds=7200,
                trigger_count=2,
                action=CircuitBreakerAction.HALT
            ),
            CircuitBreakerType.VOLUME: CircuitBreakerConfig(
                threshold=100,
                window_seconds=60,
                reset_window_seconds=300,
                trigger_count=5,
                action=CircuitBreakerAction.WARN
            ),
            CircuitBreakerType.MARGIN: CircuitBreakerConfig(
                threshold=90,
                window_seconds=60,
                reset_window_seconds=1800,
                trigger_count=2,
                action=CircuitBreakerAction.BLOCK
            ),
            CircuitBreakerType.PRICE: CircuitBreakerConfig(
                threshold=5,
                window_seconds=60,
                reset_window_seconds=300,
                trigger_count=2,
                action=CircuitBreakerAction.HALT
            ),
            CircuitBreakerType.CORRELATION: CircuitBreakerConfig(
                threshold=0.8,
                window_seconds=300,
                reset_window_seconds=3600,
                trigger_count=1,
                action=CircuitBreakerAction.WARN
            )
        }

    def ensure_breakers(self, user_id: str) -> None:
        """Ensure all default breakers exist for a user."""
        if user_id not in self._configs or not self._configs[user_id]:
            defaults = self.get_default_configs(user_id)
            for breaker_type, config in defaults.items():
                self.configure_breaker(user_id, breaker_type, config)

    async def check_order(
        self,
        user_id: str,
        symbol: str = None,
        current_price: float = None,
        order_value: float = 0
    ) -> CircuitBreakerAction:
        """Check all circuit breakers for an order."""
        self.ensure_breakers(user_id)

        user_breakers = self._breakers.get(user_id, {})

        actions = []
        for breaker_type, status in user_breakers.items():
            if status.state == CircuitBreakerState.OPEN:
                await self._check_auto_reset(user_id, breaker_type)
                status = self._breakers[user_id].get(breaker_type)
                if status and status.state == CircuitBreakerState.OPEN:
                    actions.append((breaker_type, CircuitBreakerAction.BLOCK, f"{breaker_type.value} breaker open"))
                    continue

            result = await self._check_breaker(user_id, breaker_type, symbol, current_price, order_value)
            if result != CircuitBreakerAction.ALLOW:
                actions.append((breaker_type, result, f"{breaker_type.value} limit reached"))
            else:
                actions.append((breaker_type, CircuitBreakerAction.ALLOW, "OK"))

        final_action = max(actions, key=lambda x: self._action_priority(x[1]))[1]
        final_reason = [a[2] for a in actions if a[1] != CircuitBreakerAction.ALLOW]

        if final_action == CircuitBreakerAction.HALT or final_action == CircuitBreakerAction.BLOCK:
            self.logger.warning(f"Circuit breaker blocked order for {user_id}: {final_reason}")

        return final_action

    def _action_priority(self, action: CircuitBreakerAction) -> int:
        """Get priority of action (higher = more blocking)."""
        priorities = {
            CircuitBreakerAction.ALLOW: 0,
            CircuitBreakerAction.WARN: 1,
            CircuitBreakerAction.BLOCK: 2,
            CircuitBreakerAction.HALT: 3
        }
        return priorities.get(action, 0)

    async def _check_breaker(
        self,
        user_id: str,
        breaker_type: CircuitBreakerType,
        symbol: str = None,
        current_price: float = None,
        order_value: float = 0
    ) -> CircuitBreakerAction:
        """Check specific breaker."""
        config = self._configs[user_id].get(breaker_type)
        status = self._breakers[user_id].get(breaker_type)

        if not config or not status:
            return CircuitBreakerAction.ALLOW

        if status.state == CircuitBreakerState.OPEN:
            return CircuitBreakerAction.BLOCK

        now = datetime.now(timezone.utc)

        if breaker_type == CircuitBreakerType.PRICE and symbol and current_price:
            return await self._check_price_breaker(user_id, symbol, current_price, config, status, now)
        elif breaker_type == CircuitBreakerType.LOSS:
            return await self._check_loss_breaker(user_id, order_value, config, status, now)
        elif breaker_type == CircuitBreakerType.VOLUME:
            return await self._check_volume_breaker(user_id, order_value, config, status, now)
        elif breaker_type == CircuitBreakerType.MARGIN:
            return await self._check_margin_breaker(user_id, config, status, now)
        elif breaker_type == CircuitBreakerType.DRAWDOWN:
            return await self._check_drawdown_breaker(user_id, config, status, now)

        return CircuitBreakerAction.ALLOW

    async def _check_price_breaker(
        self,
        user_id: str,
        symbol: str,
        current_price: float,
        config: CircuitBreakerConfig,
        status: CircuitBreakerStatus,
        now: datetime
    ) -> CircuitBreakerAction:
        """Check price movement breaker."""
        if symbol not in self._price_history[user_id]:
            self._price_history[user_id][symbol] = deque(maxlen=config.window_seconds)

        history = self._price_history[user_id][symbol]

        if len(history) > 1:
            price_change = abs((current_price - history[0]) / history[0] * 100)
            status.current_value = price_change

            window_start = now.timestamp() - config.window_seconds
            recent_events = [e for e in self._events[user_id]
                           if e.get('type') == 'price' and e.get('timestamp', 0) >= window_start]

            if price_change > config.threshold:
                status.trigger_count += 1
                status.last_triggered = now

                self._events[user_id].append({
                    'type': 'price',
                    'symbol': symbol,
                    'change': price_change,
                    'threshold': config.threshold,
                    'trigger_count': status.trigger_count,
                    'timestamp': now.timestamp()
                })

                if status.trigger_count >= config.trigger_count:
                    return await self._trigger_breaker(user_id, CircuitBreakerType.PRICE, config, status, now)

                return CircuitBreakerAction.WARN

        history.append(current_price)
        return CircuitBreakerAction.ALLOW

    async def _check_loss_breaker(
        self,
        user_id: str,
        order_value: float,
        config: CircuitBreakerConfig,
        status: CircuitBreakerStatus,
        now: datetime
    ) -> CircuitBreakerAction:
        """Check daily loss breaker."""
        window_start = now.timestamp() - config.window_seconds
        recent_events = [e for e in self._events[user_id]
                        if e.get('type') == 'loss' and e.get('timestamp', 0) >= window_start]

        total_loss = sum(e.get('value', 0) for e in recent_events)
        status.current_value = total_loss

        if total_loss > config.threshold:
            status.trigger_count += 1
            status.last_triggered = now

            self._events[user_id].append({
                'type': 'loss',
                'value': order_value,
                'total': total_loss,
                'threshold': config.threshold,
                'timestamp': now.timestamp()
            })

            if status.trigger_count >= config.trigger_count:
                return await self._trigger_breaker(user_id, CircuitBreakerType.LOSS, config, status, now)

            return CircuitBreakerAction.WARN

        return CircuitBreakerAction.ALLOW

    async def _check_volume_breaker(
        self,
        user_id: str,
        order_value: float,
        config: CircuitBreakerConfig,
        status: CircuitBreakerStatus,
        now: datetime
    ) -> CircuitBreakerAction:
        """Check trading volume breaker."""
        window_start = now.timestamp() - config.window_seconds
        recent_events = [e for e in self._events[user_id]
                        if e.get('type') == 'volume' and e.get('timestamp', 0) >= window_start]

        total_volume = sum(e.get('value', 0) for e in recent_events) + order_value
        status.current_value = total_volume

        if total_volume > config.threshold:
            status.trigger_count += 1

            if status.trigger_count >= config.trigger_count:
                return await self._trigger_breaker(user_id, CircuitBreakerType.VOLUME, config, status, now)

            return CircuitBreakerAction.WARN

        self._events[user_id].append({
            'type': 'volume',
            'value': order_value,
            'total': total_volume,
            'timestamp': now.timestamp()
        })

        return CircuitBreakerAction.ALLOW

    async def _check_margin_breaker(
        self,
        user_id: str,
        config: CircuitBreakerConfig,
        status: CircuitBreakerStatus,
        now: datetime
    ) -> CircuitBreakerAction:
        """Check margin utilization breaker."""
        from app.risk_management.margin_manager import get_margin_manager

        margin_manager = get_margin_manager()
        margin_state = margin_manager.get_margin_state(user_id)

        status.current_value = margin_state.margin_utilization

        if margin_state.margin_utilization > config.threshold:
            status.trigger_count += 1

            if status.trigger_count >= config.trigger_count:
                return await self._trigger_breaker(user_id, CircuitBreakerType.MARGIN, config, status, now)

            return CircuitBreakerAction.WARN

        return CircuitBreakerAction.ALLOW

    async def _check_drawdown_breaker(
        self,
        user_id: str,
        config: CircuitBreakerConfig,
        status: CircuitBreakerStatus,
        now: datetime
    ) -> CircuitBreakerAction:
        """Check drawdown breaker."""
        from app.risk_management.drawdown_manager import get_drawdown_manager

        drawdown_manager = get_drawdown_manager()
        drawdown_pct = drawdown_manager.get_current_drawdown(user_id)

        status.current_value = abs(drawdown_pct) if drawdown_pct < 0 else 0

        if abs(drawdown_pct) > config.threshold:
            status.trigger_count += 1

            if status.trigger_count >= config.trigger_count:
                return await self._trigger_breaker(user_id, CircuitBreakerType.DRAWDOWN, config, status, now)

            return CircuitBreakerAction.WARN

        return CircuitBreakerAction.ALLOW

    async def _trigger_breaker(
        self,
        user_id: str,
        breaker_type: CircuitBreakerType,
        config: CircuitBreakerConfig,
        status: CircuitBreakerStatus,
        now: datetime
    ) -> CircuitBreakerAction:
        """Trigger circuit breaker."""
        status.state = CircuitBreakerState.OPEN
        status.opened_at = now

        reset_time = now + timedelta(seconds=config.reset_window_seconds)
        status.auto_reset_at = reset_time

        if config.action == CircuitBreakerAction.HALT:
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'circuit_breaker_halt',
                    'user_id': user_id,
                    'breaker_type': breaker_type.value,
                    'current_value': status.current_value,
                    'threshold': config.threshold,
                    'message': f"Circuit breaker {breaker_type.value} halted trading"
                })

        self.logger.critical(
            f"CIRCUIT BREAKER TRIGGERED: {breaker_type.value} for {user_id}, "
            f"value={status.current_value}, threshold={config.threshold}"
        )

        return config.action

    async def _check_auto_reset(self, user_id: str, breaker_type: CircuitBreakerType) -> None:
        """Check and auto-reset breaker if time has passed."""
        status = self._breakers[user_id].get(breaker_type)
        if not status or status.state != CircuitBreakerState.OPEN:
            return

        if status.auto_reset_at and datetime.now(timezone.utc) >= status.auto_reset_at:
            status.state = CircuitBreakerState.CLOSED
            status.trigger_count = 0
            status.opened_at = None
            status.auto_reset_at = None

            self.logger.info(f"Circuit breaker {breaker_type.value} auto-reset for {user_id}")

    async def reset_breaker(self, user_id: str, breaker_type: CircuitBreakerType = None) -> bool:
        """Manually reset circuit breaker(s)."""
        if breaker_type:
            if user_id in self._breakers and breaker_type in self._breakers[user_id]:
                self._breakers[user_id][breaker_type].state = CircuitBreakerState.CLOSED
                self._breakers[user_id][breaker_type].trigger_count = 0
                self._breakers[user_id][breaker_type].opened_at = None
                self._breakers[user_id][breaker_type].auto_reset_at = None
                return True
        else:
            if user_id in self._breakers:
                for bt in self._breakers[user_id]:
                    self._breakers[user_id][bt].state = CircuitBreakerState.CLOSED
                    self._breakers[user_id][bt].trigger_count = 0
                return True
        return False

    def get_status(self, user_id: str) -> Dict:
        """Get circuit breaker status for a user."""
        self.ensure_breakers(user_id)

        status_dict = {}
        for breaker_type, status in self._breakers.get(user_id, {}).items():
            status_dict[breaker_type.value] = {
                'state': status.state.value,
                'current_value': status.current_value,
                'threshold': status.threshold,
                'trigger_count': status.trigger_count,
                'last_triggered': status.last_triggered.isoformat() if status.last_triggered else None,
                'opened_at': status.opened_at.isoformat() if status.opened_at else None
            }

        return status_dict


circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    return circuit_breaker
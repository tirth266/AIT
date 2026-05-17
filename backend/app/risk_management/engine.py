"""
Risk Management Engine
======================
Central orchestrator for all risk management operations.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger('risk_engine')


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskEventType(str, Enum):
    ORDER_BLOCKED = "order_blocked"
    MARGIN_WARNING = "margin_warning"
    DRAWDOWN_ALERT = "drawdown_alert"
    EXPOSURE_WARNING = "exposure_warning"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    STRATEGY_DISABLED = "strategy_disabled"
    CIRCUIT_BREAKER = "circuit_breaker"
    VOLATILITY_ALERT = "volatility_alert"
    POSITION_LIMIT = "position_limit"
    DAILY_LOSS_LIMIT = "daily_loss_limit"
    BROKER_REJECTION = "broker_rejection"


@dataclass
class RiskState:
    user_id: str
    risk_level: str = RiskLevel.LOW.value
    margin_utilization: float = 0.0
    exposure_percent: float = 0.0
    day_pnl: float = 0.0
    max_drawdown: float = 0.0
    open_positions: int = 0
    active_strategies: int = 0
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RiskConfig:
    max_daily_loss: float = 5000.0
    max_position_value: float = 100000.0
    max_order_value: float = 50000.0
    max_open_positions: int = 5
    max_exposure_percent: float = 20.0
    max_leverage: float = 20.0
    margin_warning_threshold: float = 80.0
    drawdown_warning_threshold: float = 3.0
    max_consecutive_losses: int = 3
    allow_pyramiding: bool = False
    enable_kill_switch: bool = True
    enable_circuit_breaker: bool = True


class RiskEngine:
    """
    Central Risk Management Engine
    Orchestrates all risk components and provides unified interface.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('risk_engine')
        
        self._configs: Dict[str, RiskConfig] = {}
        self._states: Dict[str, RiskState] = {}
        self._subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self._risk_checks_enabled = True
        self._global_kill_switch = False
        
        self._components = {}
        
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing = False
        
        self.logger.info("Risk Engine initialized")
    
    def register_component(self, name: str, component: Any) -> None:
        self._components[name] = component
        self.logger.info(f"Registered risk component: {name}")
    
    def get_component(self, name: str) -> Optional[Any]:
        return self._components.get(name)
    
    def set_config(self, user_id: str, config: RiskConfig) -> None:
        self._configs[user_id] = config
        self.logger.info(f"Risk config updated for user {user_id}")
    
    def get_config(self, user_id: str) -> RiskConfig:
        if user_id not in self._configs:
            self._configs[user_id] = RiskConfig()
        return self._configs[user_id]
    
    def get_state(self, user_id: str) -> RiskState:
        if user_id not in self._states:
            self._states[user_id] = RiskState(user_id=user_id)
        return self._states[user_id]
    
    def update_state(self, user_id: str, **kwargs) -> None:
        if user_id not in self._states:
            self._states[user_id] = RiskState(user_id=user_id)
        
        state = self._states[user_id]
        for key, value in kwargs.items():
            if hasattr(state, key):
                setattr(state, key, value)
        state.last_updated = datetime.now(timezone.utc)
    
    def enable_risk_checks(self) -> None:
        self._risk_checks_enabled = True
        self.logger.info("Risk checks enabled")
    
    def disable_risk_checks(self) -> None:
        self._risk_checks_enabled = False
        self.logger.warning("Risk checks disabled")
    
    def trigger_global_kill_switch(self, reason: str = "Manual trigger") -> None:
        self._global_kill_switch = True
        self.logger.critical(f"GLOBAL KILL SWITCH TRIGGERED: {reason}")
        
        self._broadcast_event({
            'event_type': RiskEventType.KILL_SWITCH_TRIGGERED.value,
            'level': RiskLevel.CRITICAL.value,
            'message': f"Global kill switch activated: {reason}",
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'scope': 'global'
        })
    
    def release_global_kill_switch(self) -> None:
        self._global_kill_switch = False
        self.logger.info("Global kill switch released")
    
    def is_global_kill_switch_active(self) -> bool:
        return self._global_kill_switch
    
    def is_trading_allowed(self, user_id: str) -> tuple[bool, str]:
        if self._global_kill_switch:
            return False, "Global kill switch is active"
        
        user_state = self.get_state(user_id)
        if user_state.risk_level == RiskLevel.CRITICAL.value:
            return False, "Account risk level is CRITICAL"
        
        config = self.get_config(user_id)
        
        if user_state.day_pnl <= -config.max_daily_loss:
            return False, f"Daily loss limit ({config.max_daily_loss}) exceeded"
        
        return True, "Trading allowed"
    
    def subscribe(self, user_id: str, callback: Callable) -> None:
        self._subscribers[user_id].append(callback)
    
    def unsubscribe(self, user_id: str, callback: Callable) -> None:
        if user_id in self._subscribers:
            self._subscribers[user_id] = [cb for cb in self._subscribers[user_id] if cb != callback]
    
    async def _notify_subscribers(self, user_id: str, event: Dict) -> None:
        for callback in self._subscribers.get(user_id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                self.logger.error(f"Subscriber callback error: {e}")
    
    async def _broadcast_event(self, event: Dict) -> None:
        user_id = event.get('user_id', 'global')
        await self._notify_subscribers(user_id, event)
        
        for user in self._subscribers.get('global', []):
            try:
                if asyncio.iscoroutinefunction(user):
                    await user(event)
                else:
                    user(event)
            except Exception as e:
                self.logger.error(f"Global subscriber error: {e}")
    
    async def log_event(self, event: Dict) -> None:
        event['timestamp'] = event.get('timestamp', datetime.now(timezone.utc).isoformat())
        
        self.logger.info(f"Risk Event: {event.get('event_type')} - {event.get('message')}")
        
        await self._broadcast_event(event)
    
    async def get_risk_summary(self, user_id: str) -> Dict:
        state = self.get_state(user_id)
        config = self.get_config(user_id)
        
        return {
            'user_id': user_id,
            'risk_level': state.risk_level,
            'margin_utilization': state.margin_utilization,
            'exposure_percent': state.exposure_percent,
            'day_pnl': state.day_pnl,
            'max_drawdown': state.max_drawdown,
            'open_positions': state.open_positions,
            'max_daily_loss': config.max_daily_loss,
            'max_position_value': config.max_position_value,
            'max_open_positions': config.max_open_positions,
            'global_kill_switch': self._global_kill_switch,
            'risk_checks_enabled': self._risk_checks_enabled,
            'last_updated': state.last_updated.isoformat()
        }
    
    async def calculate_risk_score(self, user_id: str) -> float:
        state = self.get_state(user_id)
        config = self.get_config(user_id)
        
        score = 0.0
        
        if state.margin_utilization > config.margin_warning_threshold:
            score += (state.margin_utilization - config.margin_warning_threshold) * 0.5
        
        if state.exposure_percent > config.max_exposure_percent:
            score += (state.exposure_percent - config.max_exposure_percent) * 0.3
        
        daily_loss_pct = abs(state.day_pnl) / config.max_daily_loss if config.max_daily_loss > 0 else 0
        if state.day_pnl < 0:
            score += daily_loss_pct * 20
        
        score += state.max_drawdown * 5
        
        if state.open_positions >= config.max_open_positions:
            score += 20
        
        return min(score, 100)
    
    def get_all_user_states(self) -> List[Dict]:
        return [
            {
                'user_id': user_id,
                'risk_level': state.risk_level,
                'margin_utilization': state.margin_utilization,
                'day_pnl': state.day_pnl,
                'open_positions': state.open_positions,
                'last_updated': state.last_updated.isoformat()
            }
            for user_id, state in self._states.items()
        ]


risk_engine = RiskEngine()


def get_risk_engine() -> RiskEngine:
    return risk_engine
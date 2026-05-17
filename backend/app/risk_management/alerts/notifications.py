"""
Risk Alert System
=================
Realtime alerts and notifications.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    MARGIN_LOW = "margin_low"
    DRAWDOWN_EXCEEDED = "drawdown_exceeded"
    STRATEGY_DISABLED = "strategy_disabled"
    ABNORMAL_LOSS = "abnormal_loss"
    EXECUTION_FAILURE = "execution_failure"
    VOLATILITY_WARNING = "volatility_warning"
    CIRCUIT_BREAKER = "circuit_breaker"
    KILL_SWITCH = "kill_switch"
    POSITION_LIMIT = "position_limit"
    BROKER_REJECTION = "broker_rejection"
    PRICE_ALERT = "price_alert"


@dataclass
class RiskAlert:
    id: str
    user_id: str
    alert_type: str
    level: str
    message: str
    details: Dict
    read: bool
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class RiskAlertManager:
    """
    Manages risk alerts and notifications.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('risk_alerts')
        self.risk_engine = risk_engine
        
        self._alerts: Dict[str, List[RiskAlert]] = defaultdict(list)
        self._global_alerts: List[RiskAlert] = []
        
        self._handlers: Dict[AlertType, List[Callable]] = defaultdict(list)
        self._broadcast_callbacks: List[Callable] = []
        
        self._alert_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    def add_handler(self, alert_type: AlertType, handler: Callable) -> None:
        self._handlers[alert_type].append(handler)
    
    def add_broadcast_callback(self, callback: Callable) -> None:
        self._broadcast_callbacks.append(callback)
    
    async def create_alert(self, user_id: str, alert_type: AlertType,
                           level: AlertLevel, message: str,
                           details: Dict = None) -> RiskAlert:
        import uuid
        alert_id = str(uuid.uuid4())
        
        alert = RiskAlert(
            id=alert_id,
            user_id=user_id,
            alert_type=alert_type.value,
            level=level.value,
            message=message,
            details=details or {},
            read=False
        )
        
        if user_id == 'global':
            self._global_alerts.append(alert)
        else:
            self._alerts[user_id].append(alert)
        
        self._alert_counts[user_id][alert_type.value] += 1
        
        await self._handle_alert(alert)
        await self._broadcast_alert(alert)
        
        return alert
    
    async def _handle_alert(self, alert: RiskAlert) -> None:
        alert_type = AlertType(alert.alert_type)
        
        for handler in self._handlers.get(alert_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                self.logger.error(f"Alert handler error: {e}")
    
    async def _broadcast_alert(self, alert: RiskAlert) -> None:
        for callback in self._broadcast_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(alert)
                else:
                    callback(alert)
            except Exception as e:
                self.logger.error(f"Broadcast callback error: {e}")
    
    async def create_margin_alert(self, user_id: str, utilization: float) -> RiskAlert:
        level = AlertLevel.WARNING if utilization < 95 else AlertLevel.CRITICAL
        
        return await self.create_alert(
            user_id=user_id,
            alert_type=AlertType.MARGIN_LOW,
            level=level,
            message=f"Margin utilization at {utilization:.1f}%",
            details={'utilization': utilization}
        )
    
    async def create_drawdown_alert(self, user_id: str, drawdown: float,
                                     drawdown_type: str) -> RiskAlert:
        level = AlertLevel.WARNING if drawdown < 10 else AlertLevel.CRITICAL
        
        return await self.create_alert(
            user_id=user_id,
            alert_type=AlertType.DRAWDOWN_EXCEEDED,
            level=level,
            message=f"{drawdown_type} drawdown at {drawdown:.2f}%",
            details={'drawdown': drawdown, 'type': drawdown_type}
        )
    
    async def create_strategy_disabled_alert(self, user_id: str, strategy_id: str,
                                               reason: str) -> RiskAlert:
        return await self.create_alert(
            user_id=user_id,
            alert_type=AlertType.STRATEGY_DISABLED,
            level=AlertLevel.WARNING,
            message=f"Strategy {strategy_id} disabled: {reason}",
            details={'strategy_id': strategy_id, 'reason': reason}
        )
    
    async def create_volatility_alert(self, user_id: str, symbol: str,
                                       volatility: float, level: str) -> RiskAlert:
        return await self.create_alert(
            user_id=user_id,
            alert_type=AlertType.VOLATILITY_WARNING,
            level=AlertLevel.WARNING if level in ['high', 'elevated'] else AlertLevel.CRITICAL,
            message=f"Volatility {level} for {symbol}: {volatility:.2f}%",
            details={'symbol': symbol, 'volatility': volatility, 'level': level}
        )
    
    async def create_kill_switch_alert(self, user_id: str, scope: str,
                                        reason: str) -> RiskAlert:
        return await self.create_alert(
            user_id='global',
            alert_type=AlertType.KILL_SWITCH,
            level=AlertLevel.CRITICAL,
            message=f"Kill switch triggered ({scope}): {reason}",
            details={'user_id': user_id, 'scope': scope, 'reason': reason}
        )
    
    def get_alerts(self, user_id: str, unread_only: bool = False,
                   limit: int = 50) -> List[Dict]:
        alerts = self._global_alerts + self._alerts.get(user_id, [])
        
        if unread_only:
            alerts = [a for a in alerts if not a.read]
        
        alerts = sorted(alerts, key=lambda x: x.created_at, reverse=True)
        
        return [
            {
                'id': a.id,
                'user_id': a.user_id,
                'alert_type': a.alert_type,
                'level': a.level,
                'message': a.message,
                'details': a.details,
                'read': a.read,
                'created_at': a.created_at.isoformat()
            }
            for a in alerts[:limit]
        ]
    
    def mark_read(self, user_id: str, alert_id: str) -> bool:
        for alert in self._alerts.get(user_id, []):
            if alert.id == alert_id:
                alert.read = True
                return True
        
        for alert in self._global_alerts:
            if alert.id == alert_id:
                alert.read = True
                return True
        
        return False
    
    def mark_all_read(self, user_id: str) -> None:
        for alert in self._alerts.get(user_id, []):
            alert.read = True
        
        for alert in self._global_alerts:
            alert.read = True
    
    def get_unread_count(self, user_id: str) -> int:
        global_unread = sum(1 for a in self._global_alerts if not a.read)
        user_unread = sum(1 for a in self._alerts.get(user_id, []) if not a.read)
        
        return global_unread + user_unread
    
    def get_alert_counts(self, user_id: str) -> Dict[str, int]:
        counts = dict(self._alert_counts.get(user_id, {}))
        
        for alert in self._global_alerts:
            alert_type = alert.alert_type
            counts[alert_type] = counts.get(alert_type, 0) + 1
        
        return counts
    
    def clear_old_alerts(self, days: int = 7) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        self._global_alerts = [a for a in self._global_alerts if a.created_at > cutoff]
        
        for user_id in self._alerts:
            self._alerts[user_id] = [a for a in self._alerts[user_id] if a.created_at > cutoff]


from datetime import timedelta


alert_manager = RiskAlertManager()


def get_alert_manager() -> RiskAlertManager:
    return alert_manager
"""
Risk Alerting System
====================
Comprehensive alerting for risk management with multiple channels and severity levels.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from collections import defaultdict
import logging

logger = logging.getLogger('risk_engine.alerts')


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertChannel(str, Enum):
    DASHBOARD = "dashboard"
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    PAGERDUTY = "pagerduty"
    SLACK = "slack"
    WEBHOOK = "webhook"


class AlertCategory(str, Enum):
    MARGIN = "margin"
    DRAWDOWN = "drawdown"
    VAR = "var"
    LIMIT_BREACH = "limit_breach"
    CIRCUIT_BREAKER = "circuit_breaker"
    FAT_FINGER = "fat_finger"
    GREEKS = "greeks"
    STRESS_TEST = "stress_test"
    CORRELATION = "correlation"
    POSITION = "position"
    STRATEGY = "strategy"


@dataclass
class RiskAlert:
    """Risk alert definition."""
    alert_id: str
    user_id: str
    category: AlertCategory
    severity: AlertSeverity

    title: str
    message: str

    current_value: float
    limit_value: float
    threshold_percent: float

    related_entity_type: Optional[str] = None
    related_entity_id: Optional[str] = None

    channels: List[AlertChannel] = field(default_factory=lambda: [AlertChannel.DASHBOARD])

    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict = field(default_factory=dict)


class AlertRule:
    """Alert rule definition."""
    rule_id: str
    name: str
    category: AlertCategory
    condition: Callable[[Dict], bool]
    severity: AlertSeverity
    channels: List[AlertChannel]

    cooldown_seconds: int = 300
    enabled: bool = True


class RiskAlertManager:
    """
    Central risk alerting system with rule-based and threshold-based alerts.
    """

    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('risk_alerts')
        self.risk_engine = risk_engine

        self._active_alerts: Dict[str, RiskAlert] = {}
        self._alert_history: List[RiskAlert] = []
        self._alert_rules: Dict[str, AlertRule] = {}

        self._subscribers: Dict[AlertChannel, List[Callable]] = defaultdict(list)
        self._alert_counts_by_severity: Dict[AlertSeverity, int] = defaultdict(int)

        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default alert rules."""
        self.register_rule(AlertRule(
            rule_id="margin_warning",
            name="Margin Warning",
            category=AlertCategory.MARGIN,
            condition=lambda d: d.get('margin_utilization', 0) > 70,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK],
            cooldown_seconds=300
        ))

        self.register_rule(AlertRule(
            rule_id="margin_critical",
            name="Margin Critical",
            category=AlertCategory.MARGIN,
            condition=lambda d: d.get('margin_utilization', 0) > 90,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.SMS],
            cooldown_seconds=60
        ))

        self.register_rule(AlertRule(
            rule_id="var_breach",
            name="VaR Breach",
            category=AlertCategory.VAR,
            condition=lambda d: d.get('var_percent', 0) > 5,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_seconds=300
        ))

        self.register_rule(AlertRule(
            rule_id="drawdown_warning",
            name="Drawdown Warning",
            category=AlertCategory.DRAWDOWN,
            condition=lambda d: abs(d.get('drawdown_percent', 0)) > 5,
            severity=AlertSeverity.WARNING,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK],
            cooldown_seconds=600
        ))

        self.register_rule(AlertRule(
            rule_id="drawdown_critical",
            name="Drawdown Critical",
            category=AlertCategory.DRAWDOWN,
            condition=lambda d: abs(d.get('drawdown_percent', 0)) > 10,
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.PAGERDUTY],
            cooldown_seconds=60
        ))

        self.register_rule(AlertRule(
            rule_id="position_limit",
            name="Position Limit Breach",
            category=AlertCategory.LIMIT_BREACH,
            condition=lambda d: d.get('position_limit_breach', False),
            severity=AlertSeverity.CRITICAL,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK, AlertChannel.EMAIL],
            cooldown_seconds=60
        ))

        self.register_rule(AlertRule(
            rule_id="fat_finger",
            name="Fat Finger Detection",
            category=AlertCategory.FAT_FINGER,
            condition=lambda d: d.get('fat_finger_detected', False),
            severity=AlertSeverity.EMERGENCY,
            channels=[AlertChannel.DASHBOARD, AlertChannel.SLACK, AlertChannel.EMAIL, AlertChannel.SMS, AlertChannel.PAGERDUTY],
            cooldown_seconds=0
        ))

    def register_rule(self, rule: AlertRule) -> None:
        """Register an alert rule."""
        self._alert_rules[rule.rule_id] = rule
        self.logger.info(f"Registered alert rule: {rule.rule_id}")

    def subscribe(self, channel: AlertChannel, callback: Callable) -> None:
        """Subscribe to alerts on a specific channel."""
        self._subscribers[channel].append(callback)

    async def publish_alert(self, alert: RiskAlert) -> None:
        """Publish an alert to all subscribers and channels."""
        self._active_alerts[alert.alert_id] = alert
        self._alert_history.append(alert)
        self._alert_counts_by_severity[alert.severity] += 1

        for channel in alert.channels:
            for callback in self._subscribers.get(channel, []):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(alert)
                    else:
                        callback(alert)
                except Exception as e:
                    self.logger.error(f"Alert callback error for {channel}: {e}")

        await self._send_to_channels(alert)

    async def _send_to_channels(self, alert: RiskAlert) -> None:
        """Send alert to configured channels."""
        for channel in alert.channels:
            if channel == AlertChannel.DASHBOARD:
                await self._send_to_dashboard(alert)
            elif channel == AlertChannel.SLACK:
                await self._send_to_slack(alert)
            elif channel == AlertChannel.EMAIL:
                await self._send_to_email(alert)
            elif channel == AlertChannel.SMS:
                await self._send_to_sms(alert)
            elif channel == AlertChannel.TELEGRAM:
                await self._send_to_telegram(alert)
            elif channel == AlertChannel.PAGERDUTY:
                await self._send_to_pagerduty(alert)

    async def _send_to_dashboard(self, alert: RiskAlert) -> None:
        """Send alert to dashboard."""
        self.logger.info(f"Dashboard alert: [{alert.severity.value}] {alert.title} - {alert.message}")

    async def _send_to_slack(self, alert: RiskAlert) -> None:
        """Send alert to Slack."""
        webhook_url = self._get_channel_config('slack_webhook')
        if not webhook_url:
            return

        import requests
        color = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9800",
            AlertSeverity.CRITICAL: "#f44336",
            AlertSeverity.EMERGENCY: "#9c27b0"
        }.get(alert.severity, "#36a64f")

        payload = {
            "attachments": [{
                "color": color,
                "title": f"[{alert.severity.value.upper()}] {alert.title}",
                "text": alert.message,
                "fields": [
                    {"title": "User", "value": alert.user_id, "short": True},
                    {"title": "Category", "value": alert.category.value, "short": True},
                    {"title": "Current Value", "value": f"{alert.current_value:.2f}", "short": True},
                    {"title": "Limit", "value": f"{alert.limit_value:.2f}", "short": True}
                ],
                "footer": f"Risk Alert | {alert.created_at.isoformat()}"
            }]
        }

        try:
            requests.post(webhook_url, json=payload, timeout=5)
        except Exception as e:
            self.logger.error(f"Failed to send Slack alert: {e}")

    async def _send_to_email(self, alert: RiskAlert) -> None:
        """Send alert via email."""
        self.logger.info(f"Email alert to {alert.user_id}: {alert.title}")

    async def _send_to_sms(self, alert: RiskAlert) -> None:
        """Send alert via SMS."""
        self.logger.info(f"SMS alert to {alert.user_id}: {alert.title}")

    async def _send_to_telegram(self, alert: RiskAlert) -> None:
        """Send alert via Telegram."""
        self.logger.info(f"Telegram alert to {alert.user_id}: {alert.title}")

    async def _send_to_pagerduty(self, alert: RiskAlert) -> None:
        """Send alert to PagerDuty."""
        self.logger.info(f"PagerDuty alert: {alert.title}")

    def _get_channel_config(self, channel: str) -> Optional[str]:
        """Get configuration for a channel."""
        return None

    async def create_alert(
        self,
        user_id: str,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        message: str,
        current_value: float,
        limit_value: float,
        related_entity_type: str = None,
        related_entity_id: str = None,
        metadata: Dict = None
    ) -> RiskAlert:
        """Create and publish a new alert."""
        import uuid

        alert = RiskAlert(
            alert_id=str(uuid.uuid4()),
            user_id=user_id,
            category=category,
            severity=severity,
            title=title,
            message=message,
            current_value=current_value,
            limit_value=limit_value,
            threshold_percent=(current_value / limit_value * 100) if limit_value > 0 else 0,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            metadata=metadata or {}
        )

        await self.publish_alert(alert)
        return alert

    async def check_rules(self, data: Dict) -> None:
        """Check all rules against data and fire alerts."""
        for rule in self._alert_rules.values():
            if not rule.enabled:
                continue

            try:
                if rule.condition(data):
                    await self.create_alert(
                        user_id=data.get('user_id', 'system'),
                        category=rule.category,
                        severity=rule.severity,
                        title=f"{rule.name} Alert",
                        message=data.get('message', f"Alert triggered by {rule.rule_id}"),
                        current_value=data.get('current_value', 0),
                        limit_value=data.get('limit_value', 0),
                        related_entity_type=data.get('entity_type'),
                        related_entity_id=data.get('entity_id'),
                        metadata={'rule_id': rule.rule_id}
                    )
            except Exception as e:
                self.logger.error(f"Error checking rule {rule.rule_id}: {e}")

    async def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """Resolve an active alert."""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.is_resolved = True
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by = resolved_by
            return True
        return False

    def get_active_alerts(self, user_id: str = None, severity: AlertSeverity = None) -> List[Dict]:
        """Get active alerts."""
        alerts = self._active_alerts.values()

        if user_id:
            alerts = [a for a in alerts if a.user_id == user_id]

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return [
            {
                'alert_id': a.alert_id,
                'title': a.title,
                'message': a.message,
                'severity': a.severity.value,
                'category': a.category.value,
                'current_value': a.current_value,
                'limit_value': a.limit_value,
                'threshold_percent': a.threshold_percent,
                'created_at': a.created_at.isoformat()
            }
            for a in alerts if not a.is_resolved
        ]

    def get_alert_summary(self) -> Dict:
        """Get alert summary statistics."""
        return {
            'total_active': len([a for a in self._active_alerts.values() if not a.is_resolved]),
            'by_severity': {
                severity.value: sum(1 for a in self._active_alerts.values()
                                   if a.severity == severity and not a.is_resolved)
                for severity in AlertSeverity
            },
            'by_category': {
                category.value: sum(1 for a in self._active_alerts.values()
                                   if a.category == category and not a.is_resolved)
                for category in AlertCategory
            }
        }

    def get_alert_history(self, limit: int = 100) -> List[Dict]:
        """Get alert history."""
        return [
            {
                'alert_id': a.alert_id,
                'title': a.title,
                'severity': a.severity.value,
                'is_resolved': a.is_resolved,
                'created_at': a.created_at.isoformat(),
                'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None
            }
            for a in self._alert_history[-limit:]
        ]


risk_alert_manager = RiskAlertManager()


def get_risk_alert_manager() -> RiskAlertManager:
    return risk_alert_manager
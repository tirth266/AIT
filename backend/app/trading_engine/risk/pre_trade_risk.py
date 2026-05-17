"""
Pre-Trade Risk Engine
=====================
Institutional-grade risk checks before order execution.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger('risk_engine')


class RiskCheckType(str, Enum):
    MAX_POSITION_SIZE = "MAX_POSITION_SIZE"
    MAX_ORDER_VALUE = "MAX_ORDER_VALUE"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    EXPOSURE_LIMIT = "EXPOSURE_LIMIT"
    QUANTITY_VALIDATION = "QUANTITY_VALIDATION"
    COOLDOWN_PERIOD = "COOLDOWN_PERIOD"
    DUPLICATE_ORDER = "DUPLICATE_ORDER"
    MARGIN_AVAILABILITY = "MARGIN_AVAILABILITY"
    PRICE_RANGE = "PRICE_RANGE"
    CIRCUIT_BREAKER = "CIRCUIT_BREAKER"


class RiskAction(str, Enum):
    ALLOW = "ALLOW"
    WARN = "WARN"
    BLOCK = "BLOCK"


@dataclass
class RiskCheckResult:
    check_type: str
    action: str
    message: str
    details: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class RiskProfile:
    max_position_value: float = 100000.0
    max_order_value: float = 50000.0
    max_daily_loss: float = 5000.0
    max_exposure_percent: float = 20.0
    max_open_positions: int = 5
    max_orders_per_minute: int = 10
    cooldown_seconds: int = 30
    allow_pyramiding: bool = False
    max_consecutive_losses: int = 3


class RiskRule:
    """Base class for risk rules."""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
    
    async def check(self, user_id: str, order_data: Dict, context: Dict) -> RiskCheckResult:
        raise NotImplementedError


class MaxPositionSizeRule(RiskRule):
    """Check if order exceeds maximum position size."""
    
    def __init__(self, max_value: float = 100000.0):
        super().__init__("Max Position Size")
        self.max_value = max_value
    
    async def check(self, user_id: str, order_data: Dict, context: Dict) -> RiskCheckResult:
        quantity = order_data.get('quantity', 0)
        price = order_data.get('price', 0) or order_data.get('trigger_price', 0)
        
        order_value = quantity * price
        
        current_positions = context.get('open_positions', [])
        symbol = order_data.get('symbol', '').upper()
        
        for pos in current_positions:
            if pos.symbol == symbol:
                current_value = pos.quantity * pos.average_price
                total_value = current_value + order_value
                
                if total_value > self.max_value:
                    return RiskCheckResult(
                        check_type=RiskCheckType.MAX_POSITION_SIZE.value,
                        action=RiskAction.BLOCK.value,
                        message=f"Position value would exceed limit: {total_value:.2f} > {self.max_value:.2f}",
                        details={'current_value': current_value, 'order_value': order_value, 'max_value': self.max_value}
                    )
        
        if order_value > self.max_value:
            return RiskCheckResult(
                check_type=RiskCheckType.MAX_ORDER_VALUE.value,
                action=RiskAction.BLOCK.value,
                message=f"Order value {order_value:.2f} exceeds maximum {self.max_value:.2f}",
                details={'order_value': order_value}
            )
        
        return RiskCheckResult(
            check_type=RiskCheckType.MAX_POSITION_SIZE.value,
            action=RiskAction.ALLOW.value,
            message="Position size check passed"
        )


class DailyLossLimitRule(RiskRule):
    """Check if daily loss limit is exceeded."""
    
    def __init__(self, max_daily_loss: float = 5000.0):
        super().__init__("Daily Loss Limit")
        self.max_daily_loss = max_daily_loss
    
    async def check(self, user_id: str, order_data: Dict, context: Dict) -> RiskCheckResult:
        day_pnl = context.get('day_pnl', 0)
        
        if day_pnl <= -self.max_daily_loss:
            return RiskCheckResult(
                check_type=RiskCheckType.DAILY_LOSS_LIMIT.value,
                action=RiskAction.BLOCK.value,
                message=f"Daily loss limit exceeded: {day_pnl:.2f} < -{self.max_daily_loss:.2f}",
                details={'day_pnl': day_pnl, 'limit': self.max_daily_loss}
            )
        
        projected_loss = day_pnl - (order_data.get('quantity', 0) * order_data.get('price', 0))
        
        if projected_loss <= -self.max_daily_loss:
            return RiskCheckResult(
                check_type=RiskCheckType.DAILY_LOSS_LIMIT.value,
                action=RiskAction.WARN.value,
                message=f"Warning: Order may exceed daily loss limit",
                details={'projected_pnl': projected_loss, 'limit': self.max_daily_loss}
            )
        
        return RiskCheckResult(
            check_type=RiskCheckType.DAILY_LOSS_LIMIT.value,
            action=RiskAction.ALLOW.value,
            message="Daily loss check passed"
        )


class MaxOpenPositionsRule(RiskRule):
    """Check if maximum open positions limit is reached."""
    
    def __init__(self, max_positions: int = 5):
        super().__init__("Max Open Positions")
        self.max_positions = max_positions
    
    async def check(self, user_id: str, order_data: Dict, context: Dict) -> RiskCheckResult:
        open_positions = context.get('open_positions', [])
        
        if len(open_positions) >= self.max_positions:
            return RiskCheckResult(
                check_type=RiskCheckType.EXPOSURE_LIMIT.value,
                action=RiskAction.BLOCK.value,
                message=f"Maximum open positions ({self.max_positions}) reached",
                details={'current_positions': len(open_positions), 'max': self.max_positions}
            )
        
        return RiskCheckResult(
            check_type=RiskCheckType.EXPOSURE_LIMIT.value,
            action=RiskAction.ALLOW.value,
            message="Open positions check passed"
        )


class MarginAvailabilityRule(RiskRule):
    """Check if sufficient margin is available."""
    
    def __init__(self):
        super().__init__("Margin Availability")
    
    async def check(self, user_id: str, order_data: Dict, context: Dict) -> RiskCheckResult:
        margin_info = context.get('margin_info')
        
        if not margin_info:
            return RiskCheckResult(
                check_type=RiskCheckType.MARGIN_AVAILABILITY.value,
                action=RiskAction.WARN.value,
                message="Margin information not available"
            )
        
        quantity = order_data.get('quantity', 0)
        price = order_data.get('price', 0) or order_data.get('trigger_price', 0)
        product_type = order_data.get('product_type', 'MIS')
        
        required_margin = self._calculate_required_margin(quantity, price, product_type)
        
        if margin_info.available_margin < required_margin:
            return RiskCheckResult(
                check_type=RiskCheckType.MARGIN_AVAILABILITY.value,
                action=RiskAction.BLOCK.value,
                message=f"Insufficient margin: required {required_margin:.2f}, available {margin_info.available_margin:.2f}",
                details={'required': required_margin, 'available': margin_info.available_margin}
            )
        
        return RiskCheckResult(
            check_type=RiskCheckType.MARGIN_AVAILABILITY.value,
            action=RiskAction.ALLOW.value,
            message="Margin check passed"
        )
    
    def _calculate_required_margin(self, quantity: int, price: float, product_type: str) -> float:
        position_value = quantity * price
        margin_percent = 0.05 if product_type == "MIS" else 0.15
        return position_value * margin_percent


class DuplicateOrderRule(RiskRule):
    """Check for duplicate orders within cooldown period."""
    
    def __init__(self, cooldown_seconds: int = 30):
        super().__init__("Duplicate Order Check")
        self.cooldown_seconds = cooldown_seconds
        self._order_timestamps: Dict[str, datetime] = {}
    
    async def check(self, user_id: str, order_data: Dict, context: Dict) -> RiskCheckResult:
        symbol = order_data.get('symbol', '').upper()
        quantity = order_data.get('quantity', 0)
        price = order_data.get('price', 0)
        
        order_key = f"{user_id}:{symbol}:{quantity}:{price}"
        
        last_time = self._order_timestamps.get(order_key)
        if last_time:
            elapsed = (datetime.now(timezone.utc) - last_time).total_seconds()
            if elapsed < self.cooldown_seconds:
                return RiskCheckResult(
                    check_type=RiskCheckType.DUPLICATE_ORDER.value,
                    action=RiskAction.BLOCK.value,
                    message=f"Duplicate order detected. Wait {int(self.cooldown_seconds - elapsed)} seconds",
                    details={'elapsed_seconds': elapsed, 'cooldown': self.cooldown_seconds}
                )
        
        self._order_timestamps[order_key] = datetime.now(timezone.utc)
        
        return RiskCheckResult(
            check_type=RiskCheckType.DUPLICATE_ORDER.value,
            action=RiskAction.ALLOW.value,
            message="Duplicate check passed"
        )


class PreTradeRiskEngine:
    """
    Pre-trade risk validation engine.
    """
    
    def __init__(self):
        self.logger = logging.getLogger('pre_trade_risk')
        
        self.rules: List[RiskRule] = [
            MaxPositionSizeRule(max_value=100000.0),
            DailyLossLimitRule(max_daily_loss=5000.0),
            MaxOpenPositionsRule(max_positions=5),
            MarginAvailabilityRule(),
            DuplicateOrderRule(cooldown_seconds=30),
        ]
        
        self._risk_events: List[Dict] = []
    
    def add_rule(self, rule: RiskRule) -> None:
        self.rules.append(rule)
    
    def remove_rule(self, rule_name: str) -> None:
        self.rules = [r for r in self.rules if r.name != rule_name]
    
    async def validate_order(self, user_id: str, order_data: Dict, 
                             context: Dict) -> tuple[bool, List[RiskCheckResult]]:
        results = []
        blocked = False
        
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            try:
                result = await rule.check(user_id, order_data, context)
                results.append(result)
                
                if result.action == RiskAction.BLOCK.value:
                    blocked = True
                    self._log_risk_event(user_id, order_data, result)
                    
                    self.logger.warning(
                        f"Risk BLOCK: {rule.name} - {result.message} | "
                        f"User: {user_id} | Symbol: {order_data.get('symbol')} | "
                        f"Qty: {order_data.get('quantity')} @ {order_data.get('price')}"
                    )
                elif result.action == RiskAction.WARN.value:
                    self._log_risk_event(user_id, order_data, result)
                    
                    self.logger.info(
                        f"Risk WARN: {rule.name} - {result.message} | "
                        f"User: {user_id} | Symbol: {order_data.get('symbol')}"
                    )
                    
            except Exception as e:
                self.logger.error(f"Risk rule {rule.name} error: {e}")
        
        return not blocked, results
    
    def _log_risk_event(self, user_id: str, order_data: Dict, result: RiskCheckResult) -> None:
        event = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'user_id': user_id,
            'check_type': result.check_type,
            'action': result.action,
            'message': result.message,
            'order_data': {
                'symbol': order_data.get('symbol'),
                'quantity': order_data.get('quantity'),
                'price': order_data.get('price'),
                'order_type': order_data.get('order_type'),
            }
        }
        self._risk_events.append(event)
        
        if len(self._risk_events) > 1000:
            self._risk_events = self._risk_events[-500:]
    
    def get_risk_events(self, user_id: Optional[str] = None, 
                        limit: int = 100) -> List[Dict]:
        events = self._risk_events
        
        if user_id:
            events = [e for e in events if e['user_id'] == user_id]
        
        return events[-limit:]
    
    def clear_risk_events(self, user_id: Optional[str] = None) -> None:
        if user_id:
            self._risk_events = [e for e in self._risk_events if e['user_id'] != user_id]
        else:
            self._risk_events = []


pre_trade_risk_engine = PreTradeRiskEngine()


def get_pre_trade_risk_engine() -> PreTradeRiskEngine:
    return pre_trade_risk_engine
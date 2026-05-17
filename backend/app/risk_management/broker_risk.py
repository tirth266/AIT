"""
Broker Risk Integration
=======================
Integrate with broker RMS and handle broker rejections.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class BrokerRejectionReason(str, Enum):
    INSUFFICIENT_MARGIN = "insufficient_margin"
    POSITION_LIMIT = "position_limit"
    EXPOSURE_LIMIT = "exposure_limit"
    SCRIPT_NOT_ALLOWED = "script_not_allowed"
    BANNED_SYMBOL = "banned_symbol"
    SQUARE_OFF = "square_off"
    NO_AVAILABLE_MARGIN = "no_available_margin"
    BROKER_RESTRICTION = "broker_restriction"
    MARKET_CLOSED = "market_closed"
    PRICE_BREACH = "price_breach"
    UNKNOWN = "unknown"


@dataclass
class BrokerRiskStatus:
    broker_name: str
    user_id: str
    margin_available: float
    margin_used: float
    exposure_used: float
    position_count: int
    daily_loss_used: float
    is_blocked: bool
    rejection_reason: Optional[str]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BrokerOrderResponse:
    order_id: Optional[str]
    status: str
    message: str
    broker_rejection_code: Optional[str]
    broker_rejection_reason: Optional[str]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class BrokerRiskIntegration:
    """
    Integrate with broker RMS systems.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('broker_risk')
        self.risk_engine = risk_engine
        
        self._broker_statuses: Dict[str, Dict[str, BrokerRiskStatus]] = {}
        
        self._rejection_handlers: Dict[BrokerRejectionReason, callable] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self) -> None:
        self._rejection_handlers[BrokerRejectionReason.INSUFFICIENT_MARGIN] = \
            self._handle_insufficient_margin
        self._rejection_handlers[BrokerRejectionReason.POSITION_LIMIT] = \
            self._handle_position_limit
        self._rejection_handlers[BrokerRejectionReason.EXPOSURE_LIMIT] = \
            self._handle_exposure_limit
        self._rejection_handlers[BrokerRejectionReason.SCRIPT_NOT_ALLOWED] = \
            self._handle_script_not_allowed
        self._rejection_handlers[BrokerRejectionReason.BANNED_SYMBOL] = \
            self._handle_banned_symbol
    
    async def update_broker_status(self, broker: str, user_id: str, 
                                    status: Dict) -> BrokerRiskStatus:
        broker_status = BrokerRiskStatus(
            broker_name=broker,
            user_id=user_id,
            margin_available=status.get('margin_available', 0),
            margin_used=status.get('margin_used', 0),
            exposure_used=status.get('exposure_used', 0),
            position_count=status.get('position_count', 0),
            daily_loss_used=status.get('daily_loss_used', 0),
            is_blocked=status.get('is_blocked', False),
            rejection_reason=status.get('rejection_reason')
        )
        
        if broker not in self._broker_statuses:
            self._broker_statuses[broker] = {}
        
        self._broker_statuses[broker][user_id] = broker_status
        
        if broker_status.is_blocked:
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'broker_block',
                    'broker': broker,
                    'user_id': user_id,
                    'reason': broker_status.rejection_reason,
                    'level': 'critical'
                })
        
        return broker_status
    
    async def validate_order_with_broker(self, broker: str, user_id: str,
                                          order: Dict) -> BrokerOrderResponse:
        broker_statuses = self._broker_statuses.get(broker, {})
        status = broker_statuses.get(user_id)
        
        if not status:
            return BrokerOrderResponse(
                order_id=None,
                status='ERROR',
                message='Broker status not available',
                broker_rejection_code='UNKNOWN',
                broker_rejection_reason='Broker status not available'
            )
        
        if status.is_blocked:
            return BrokerOrderResponse(
                order_id=None,
                status='REJECTED',
                message=f'Account blocked by broker: {status.rejection_reason}',
                broker_rejection_code='ACCOUNT_BLOCKED',
                broker_rejection_reason=status.rejection_reason
            )
        
        order_value = order.get('quantity', 0) * order.get('price', 0)
        
        required_margin = order_value * 0.05
        if status.margin_available < required_margin:
            reason = BrokerRejectionReason.INSUFFICIENT_MARGIN.value
            return BrokerOrderResponse(
                order_id=None,
                status='REJECTED',
                message=f'Insufficient margin with broker',
                broker_rejection_code=reason,
                broker_rejection_reason=f'Available: {status.margin_available}, Required: {required_margin}'
            )
        
        return BrokerOrderResponse(
            order_id=None,
            status='ACCEPTED',
            message='Order accepted by broker',
            broker_rejection_code=None,
            broker_rejection_reason=None
        )
    
    async def handle_broker_rejection(self, user_id: str, order: Dict,
                                       rejection: Dict) -> None:
        broker_code = rejection.get('broker_rejection_code', 'UNKNOWN')
        broker_reason = rejection.get('broker_rejection_reason', 'Unknown error')
        
        reason_enum = BrokerRejectionReason.UNKNOWN
        
        for reason in BrokerRejectionReason:
            if reason.value.lower() in broker_reason.lower():
                reason_enum = reason
                break
        
        handler = self._rejection_handlers.get(reason_enum)
        
        if handler:
            await handler(user_id, order, rejection)
        
        if self.risk_engine:
            await self.risk_engine.log_event({
                'event_type': 'broker_rejection',
                'user_id': user_id,
                'order': order,
                'rejection_reason': broker_reason,
                'broker_code': broker_code,
                'level': 'warning'
            })
    
    async def _handle_insufficient_margin(self, user_id: str, order: Dict, 
                                           rejection: Dict) -> None:
        self.logger.warning(f"Insufficient margin rejection for {user_id}")
        
        margin_manager = self.risk_engine.get_component('margin_manager') if self.risk_engine else None
        if margin_manager:
            margin_manager.reset_alerts(user_id)
    
    async def _handle_position_limit(self, user_id: str, order: Dict, 
                                      rejection: Dict) -> None:
        self.logger.warning(f"Position limit reached for {user_id}")
    
    async def _handle_exposure_limit(self, user_id: str, order: Dict, 
                                       rejection: Dict) -> None:
        self.logger.warning(f"Exposure limit reached for {user_id}")
    
    async def _handle_script_not_allowed(self, user_id: str, order: Dict, 
                                           rejection: Dict) -> None:
        symbol = order.get('symbol', '')
        self.logger.warning(f"Script not allowed: {symbol} for {user_id}")
        
        pre_trade_checker = self.risk_engine.get_component('pre_trade_checker') if self.risk_engine else None
        if pre_trade_checker:
            pre_trade_checker.restrict_symbol_for_user(user_id, symbol)
    
    async def _handle_banned_symbol(self, user_id: str, order: Dict, 
                                      rejection: Dict) -> None:
        symbol = order.get('symbol', '')
        self.logger.warning(f"Symbol banned: {symbol}")
    
    def get_broker_status(self, broker: str, user_id: str) -> Optional[BrokerRiskStatus]:
        return self._broker_statuses.get(broker, {}).get(user_id)
    
    def get_all_broker_statuses(self) -> List[Dict]:
        statuses = []
        
        for broker, users in self._broker_statuses.items():
            for user_id, status in users.items():
                statuses.append({
                    'broker': status.broker_name,
                    'user_id': status.user_id,
                    'margin_available': status.margin_available,
                    'margin_used': status.margin_used,
                    'exposure_used': status.exposure_used,
                    'position_count': status.position_count,
                    'is_blocked': status.is_blocked,
                    'rejection_reason': status.rejection_reason,
                    'last_updated': status.last_updated.isoformat()
                })
        
        return statuses


broker_risk_integration = BrokerRiskIntegration()


def get_broker_risk_integration() -> BrokerRiskIntegration:
    return broker_risk_integration
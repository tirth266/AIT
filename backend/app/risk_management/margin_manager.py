"""
Margin Manager
==============
Margin calculation, validation, and monitoring.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class ProductType(str, Enum):
    MIS = "MIS"
    CNC = "CNC"
    NRML = "NRML"
    CO = "CO"


class MarginType(str, Enum):
    SPAN = "span"
    EXPOSURE = "exposure"
    PREMIUM = "premium"
    TOTAL = "total"


@dataclass
class MarginRequirement:
    product_type: str
    exchange: str
    margin_percent: float
    min_margin: float
    leverage: float


@dataclass
class PositionMargin:
    position_id: str
    symbol: str
    quantity: int
    product_type: str
    span_margin: float
    exposure_margin: float
    premium_margin: float
    total_margin: float
    blocked: bool


@dataclass
class MarginState:
    user_id: str
    cash_balance: float
    total_margin_available: float
    margin_used: float
    margin_blocked: float
    margin_available: float
    intraday_buying_power: float
    holdings_value: float
    positions_margin: Dict[str, float]
    margin_utilization: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


MARGIN_REQUIREMENTS = {
    'MIS': {
        'NSE': {'percent': 0.05, 'min': 100, 'leverage': 20},
        'BSE': {'percent': 0.05, 'min': 100, 'leverage': 20},
    },
    'CNC': {
        'NSE': {'percent': 1.0, 'min': 0, 'leverage': 1},
        'BSE': {'percent': 1.0, 'min': 0, 'leverage': 1},
    },
    'NRML': {
        'NSE': {'percent': 0.15, 'min': 100, 'leverage': 5},
        'BSE': {'percent': 0.15, 'min': 100, 'leverage': 5},
    },
    'CO': {
        'NSE': {'percent': 0.05, 'min': 100, 'leverage': 20},
    },
}


class MarginManager:
    """
    Manages margin calculations, blocking, and monitoring.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('margin_manager')
        self.risk_engine = risk_engine
        
        self._margin_states: Dict[str, MarginState] = {}
        self._margin_blocked: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._cash_balances: Dict[str, float] = defaultdict(lambda: 100000.0)
        
        self._warning_threshold = 80.0
        self._critical_threshold = 95.0
        
        self._alerts_sent: Dict[str, set] = defaultdict(set)
    
    def set_cash_balance(self, user_id: str, balance: float) -> None:
        self._cash_balances[user_id] = balance
    
    def get_cash_balance(self, user_id: str) -> float:
        return self._cash_balances.get(user_id, 100000.0)
    
    def calculate_position_margin(self, quantity: int, price: float,
                                   product_type: str, exchange: str = "NSE") -> float:
        reqs = MARGIN_REQUIREMENTS.get(product_type, {}).get(exchange, 
            {'percent': 0.1, 'min': 100, 'leverage': 1})
        
        position_value = quantity * price
        margin = position_value * reqs['percent']
        
        if product_type == 'MIS':
            margin = margin / reqs['leverage']
        
        return max(margin, reqs['min'])
    
    def calculate_order_margin(self, quantity: int, price: float,
                               order_type: str, product_type: str,
                               exchange: str = "NSE") -> float:
        if order_type == "MARKET":
            price = price * 1.01
        
        margin = self.calculate_position_margin(quantity, price, product_type, exchange)
        
        if order_type in ["SL", "SL-M"]:
            margin *= 1.1
        
        return margin
    
    def can_block_margin(self, user_id: str, amount: float) -> bool:
        state = self.get_margin_state(user_id)
        return state.margin_available >= amount
    
    def block_margin(self, user_id: str, amount: float, reason: str = "Order") -> bool:
        state = self.get_margin_state(user_id)
        
        if state.margin_available < amount:
            self.logger.warning(f"Margin block failed for {user_id}: insufficient margin")
            return False
        
        state.margin_blocked += amount
        state.margin_available -= amount
        
        self._margin_blocked[user_id][reason] = self._margin_blocked[user_id].get(reason, 0) + amount
        
        self.logger.info(f"Margin blocked: {user_id} - {amount:.2f} ({reason})")
        return True
    
    def release_margin(self, user_id: str, amount: float, reason: str = "Order filled") -> bool:
        if user_id not in self._margin_states:
            return False
        
        state = self._margin_states[user_id]
        
        state.margin_blocked = max(0, state.margin_blocked - amount)
        state.margin_available += amount
        
        if reason in self._margin_blocked[user_id]:
            self._margin_blocked[user_id][reason] = max(0, 
                self._margin_blocked[user_id][reason] - amount)
        
        self.logger.info(f"Margin released: {user_id} - {amount:.2f} ({reason})")
        return True
    
    async def calculate_margin_state(self, user_id: str, positions: List[Dict]) -> MarginState:
        cash = self.get_cash_balance(user_id)
        
        positions_margin = {}
        total_margin_used = 0
        holdings_value = 0
        
        for pos in positions:
            if pos.get('status') != 'OPEN':
                continue
            
            position_id = pos.get('position_id', '')
            quantity = pos.get('quantity', 0)
            avg_price = pos.get('average_price', 0)
            current_price = pos.get('current_price', avg_price)
            product_type = pos.get('product_type', 'MIS')
            exchange = pos.get('exchange', 'NSE')
            
            margin = self.calculate_position_margin(quantity, current_price, product_type, exchange)
            positions_margin[position_id] = margin
            total_margin_used += margin
            
            if product_type == 'CNC':
                holdings_value += quantity * current_price
        
        total_margin = cash + holdings_value
        margin_available = total_margin - total_margin_used
        
        utilization = (total_margin_used / total_margin * 100) if total_margin > 0 else 0
        
        intraday_bp = cash * 20
        
        state = MarginState(
            user_id=user_id,
            cash_balance=cash,
            total_margin_available=total_margin,
            margin_used=total_margin_used,
            margin_blocked=total_margin_used,
            margin_available=margin_available,
            intraday_buying_power=intraday_bp,
            holdings_value=holdings_value,
            positions_margin=positions_margin,
            margin_utilization=utilization
        )
        
        self._margin_states[user_id] = state
        
        await self._check_margin_alerts(user_id, state)
        
        return state
    
    async def _check_margin_alerts(self, user_id: str, state: MarginState) -> None:
        utilization = state.margin_utilization
        
        if utilization >= self._critical_threshold:
            alert_key = f"{user_id}:critical"
            if alert_key not in self._alerts_sent[user_id]:
                self._alerts_sent[user_id].add(alert_key)
                await self._send_alert(user_id, 'margin_critical',
                    f"Margin utilization CRITICAL: {utilization:.1f}%")
        
        elif utilization >= self._warning_threshold:
            alert_key = f"{user_id}:warning"
            if alert_key not in self._alerts_sent[user_id]:
                self._alerts_sent[user_id].add(alert_key)
                await self._send_alert(user_id, 'margin_warning',
                    f"Margin utilization high: {utilization:.1f}%")
    
    async def _send_alert(self, user_id: str, alert_type: str, message: str) -> None:
        if self.risk_engine:
            level = 'critical' if 'critical' in alert_type else 'warning'
            await self.risk_engine.log_event({
                'event_type': 'margin_alert',
                'user_id': user_id,
                'alert_type': alert_type,
                'message': message,
                'level': level,
                'margin_utilization': self._margin_states.get(user_id).margin_utilization if user_id in self._margin_states else 0
            })
    
    def get_margin_state(self, user_id: str) -> MarginState:
        if user_id not in self._margin_states:
            cash = self.get_cash_balance(user_id)
            self._margin_states[user_id] = MarginState(
                user_id=user_id,
                cash_balance=cash,
                total_margin_available=cash,
                margin_used=0,
                margin_blocked=0,
                margin_available=cash,
                intraday_buying_power=cash * 20,
                holdings_value=0,
                positions_margin={},
                margin_utilization=0
            )
        return self._margin_states[user_id]
    
    def set_warning_threshold(self, threshold: float) -> None:
        self._warning_threshold = threshold
    
    def set_critical_threshold(self, threshold: float) -> None:
        self._critical_threshold = threshold
    
    def get_all_margin_states(self) -> List[Dict]:
        return [
            {
                'user_id': user_id,
                'cash_balance': state.cash_balance,
                'margin_used': state.margin_used,
                'margin_available': state.margin_available,
                'margin_utilization': round(state.margin_utilization, 2),
                'intraday_buying_power': state.intraday_buying_power,
                'holdings_value': state.holdings_value,
                'position_count': len(state.positions_margin),
                'timestamp': state.timestamp.isoformat()
            }
            for user_id, state in self._margin_states.items()
        ]
    
    def reset_alerts(self, user_id: str) -> None:
        if user_id in self._alerts_sent:
            self._alerts_sent[user_id].clear()


margin_manager = MarginManager()


def get_margin_manager() -> MarginManager:
    return margin_manager
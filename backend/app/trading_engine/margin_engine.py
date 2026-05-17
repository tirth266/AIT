"""
Margin Engine
=============
Manages margin calculations, blocking, and release.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

from .engine import TradingEngine, Position, get_trading_engine
from .position_manager import PositionManager, get_position_manager

logger = logging.getLogger('margin_engine')


MARGIN_REQUIREMENTS = {
    'MIS': {
        'NSE': 0.05,
        'BSE': 0.05,
    },
    'CNC': {
        'NSE': 1.0,
        'BSE': 1.0,
    },
    'NRML': {
        'NSE': 0.15,
        'BSE': 0.15,
    }
}

BROKERAGE_RATES = {
    'MIS': {'intraday': 0.0003, 'delivery': 0.0003},
    'CNC': {'intraday': 0.0003, 'delivery': 0.001},
    'NRML': {'intraday': 0.0003, 'delivery': 0.001}
}

LEVERAGE_MULTIPLIERS = {
    'MIS': 20,
    'CNC': 1,
    'NRML': 5
}


@dataclass
class MarginInfo:
    user_id: str
    total_margin: float
    used_margin: float
    available_margin: float
    blocked_margin: float
    intraday_buying_power: float
    cash_balance: float
    holdings_value: float
    position_margins: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict:
        return {
            'user_id': self.user_id,
            'total_margin': round(self.total_margin, 2),
            'used_margin': round(self.used_margin, 2),
            'available_margin': round(self.available_margin, 2),
            'blocked_margin': round(self.blocked_margin, 2),
            'intraday_buying_power': round(self.intraday_buying_power, 2),
            'cash_balance': round(self.cash_balance, 2),
            'holdings_value': round(self.holdings_value, 2),
            'position_margins': {k: round(v, 2) for k, v in self.position_margins.items()},
            'timestamp': self.timestamp.isoformat()
        }


class MarginEngine:
    """
    Margin calculation and management engine.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.position_manager = get_position_manager()
        self.logger = logging.getLogger('margin_engine')
        
        self._margin_cache: Dict[str, MarginInfo] = {}
        self._user_balances: Dict[str, float] = defaultdict(lambda: 100000.0)
    
    def set_cash_balance(self, user_id: str, balance: float) -> None:
        self._user_balances[user_id] = balance
    
    def get_cash_balance(self, user_id: str) -> float:
        return self._user_balances.get(user_id, 100000.0)
    
    def calculate_position_margin(self, quantity: int, price: float, 
                                  product_type: str, exchange: str) -> float:
        margin_percent = MARGIN_REQUIREMENTS.get(product_type, {}).get(exchange, 0.1)
        
        position_value = quantity * price
        required_margin = position_value * margin_percent
        
        if product_type == 'MIS':
            leverage = LEVERAGE_MULTIPLIERS.get('MIS', 1)
            required_margin = required_margin / leverage
        
        min_margin = 100
        return max(required_margin, min_margin)
    
    def calculate_order_margin(self, quantity: int, price: float,
                               order_type: str, product_type: str,
                               exchange: str = "NSE") -> float:
        if order_type == "MARKET":
            estimated_price = price * 1.01
        else:
            estimated_price = price
        
        margin = self.calculate_position_margin(quantity, estimated_price, product_type, exchange)
        
        if order_type in ["SL", "SL-M"]:
            margin *= 1.1
        
        return margin
    
    def check_margin_availability(self, user_id: str, order_margin: float) -> tuple[bool, str]:
        margin_info = self.get_margin_info(user_id)
        
        if margin_info.available_margin < order_margin:
            return False, f"Insufficient margin. Required: {order_margin:.2f}, Available: {margin_info.available_margin:.2f}"
        
        return True, "Margin available"
    
    def calculate_margin_utilization(self, user_id: str) -> Dict:
        margin_info = self.get_margin_info(user_id)
        
        if margin_info.total_margin > 0:
            utilization_percent = (margin_info.used_margin / margin_info.total_margin) * 100
        else:
            utilization_percent = 0
        
        return {
            'used_margin': margin_info.used_margin,
            'available_margin': margin_info.available_margin,
            'utilization_percent': round(utilization_percent, 2),
            'cash_balance': margin_info.cash_balance,
            'total_margin': margin_info.total_margin
        }
    
    def get_margin_info(self, user_id: str) -> MarginInfo:
        if user_id in self._margin_cache:
            return self._margin_cache[user_id]
        
        cash_balance = self.get_cash_balance(user_id)
        
        open_positions = self.position_manager.get_open_positions(user_id)
        
        position_margins = {}
        used_margin = 0
        
        for pos in open_positions:
            margin = self.calculate_position_margin(
                pos.quantity,
                pos.current_price or pos.average_price,
                pos.product_type,
                pos.exchange
            )
            position_margins[pos.position_id] = margin
            used_margin += margin
        
        holdings_value = sum(
            pos.current_price * pos.quantity 
            for pos in open_positions 
            if pos.product_type == "CNC"
        )
        
        total_margin = cash_balance + holdings_value
        available_margin = total_margin - used_margin
        blocked_margin = used_margin
        
        intraday_buying_power = cash_balance * LEVERAGE_MULTIPLIERS.get('MIS', 1)
        
        margin_info = MarginInfo(
            user_id=user_id,
            total_margin=total_margin,
            used_margin=used_margin,
            available_margin=available_margin,
            blocked_margin=blocked_margin,
            intraday_buying_power=intraday_buying_power,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            position_margins=position_margins
        )
        
        self._margin_cache[user_id] = margin_info
        
        return margin_info
    
    def block_margin(self, user_id: str, amount: float, reason: str = "Order") -> bool:
        margin_info = self.get_margin_info(user_id)
        
        if margin_info.available_margin < amount:
            self.logger.warning(f"Margin blocking failed for user {user_id}: insufficient margin")
            return False
        
        margin_info.blocked_margin += amount
        margin_info.available_margin -= amount
        
        self.logger.info(f"Margin blocked: {user_id} - {amount:.2f} ({reason})")
        return True
    
    def release_margin(self, user_id: str, amount: float, reason: str = "Order filled") -> bool:
        if user_id not in self._margin_cache:
            return False
        
        margin_info = self._margin_cache[user_id]
        
        margin_info.blocked_margin = max(0, margin_info.blocked_margin - amount)
        margin_info.available_margin += amount
        
        self.logger.info(f"Margin released: {user_id} - {amount:.2f} ({reason})")
        return True
    
    async def update_margin_for_fill(self, user_id: str, quantity: int, 
                                      price: float, product_type: str) -> bool:
        margin_required = self.calculate_position_margin(
            quantity, price, product_type, "NSE"
        )
        
        if product_type == "MIS":
            self.block_margin(user_id, margin_required / 20, "Position opened (MIS)")
        else:
            self.block_margin(user_id, margin_required, "Position opened")
        
        return True
    
    async def update_margin_for_exit(self, user_id: str, position_id: str,
                                     quantity: int, product_type: str) -> bool:
        margin_released = self.calculate_position_margin(
            quantity, 0, product_type, "NSE"
        )
        
        if product_type == "MIS":
            self.release_margin(user_id, margin_released / 20, "Position closed (MIS)")
        else:
            self.release_margin(user_id, margin_released, "Position closed")
        
        return True
    
    def calculate_exposure(self, user_id: str) -> Dict:
        positions = self.position_manager.get_open_positions(user_id)
        
        total_exposure = sum(p.current_price * p.quantity for p in positions)
        single_stock_exposure = {}
        
        for pos in positions:
            if pos.symbol not in single_stock_exposure:
                single_stock_exposure[pos.symbol] = 0
            single_stock_exposure[pos.symbol] += pos.current_price * pos.quantity
        
        return {
            'total_exposure': round(total_exposure, 2),
            'single_stock_exposure': {k: round(v, 2) for k, v in single_stock_exposure.items()},
            'position_count': len(positions)
        }
    
    def get_margin_requirement_summary(self, user_id: str) -> Dict:
        positions = self.position_manager.get_open_positions(user_id)
        
        margin_by_product = defaultdict(float)
        margin_by_exchange = defaultdict(float)
        
        for pos in positions:
            margin = self.calculate_position_margin(
                pos.quantity,
                pos.current_price or pos.average_price,
                pos.product_type,
                pos.exchange
            )
            margin_by_product[pos.product_type] += margin
            margin_by_exchange[pos.exchange] += margin
        
        return {
            'margin_by_product': dict(margin_by_product),
            'margin_by_exchange': dict(margin_by_exchange),
            'total_margin_required': sum(margin_by_product.values())
        }


margin_engine = MarginEngine()


def get_margin_engine() -> MarginEngine:
    return margin_engine
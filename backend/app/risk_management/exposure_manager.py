"""
Exposure Manager
================
Real-time exposure monitoring and limits.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class ExposureType(str, Enum):
    LONG = "long"
    SHORT = "short"
    NET = "net"
    TOTAL = "total"


@dataclass
class ExposureLimit:
    max_position_value: float = 100000.0
    max_single_stock_exposure: float = 50000.0
    max_sector_exposure: float = 100000.0
    max_exposure_percent: float = 20.0
    max_sector_concentration: float = 30.0


@dataclass
class PositionExposure:
    symbol: str
    quantity: int
    average_price: float
    current_price: float
    side: str
    value: float
    unrealized_pnl: float
    sector: str = "Other"


@dataclass
class ExposureSnapshot:
    user_id: str
    total_exposure: float
    net_exposure: float
    long_exposure: float
    short_exposure: float
    cash_balance: float
    portfolio_value: float
    leverage: float
    position_count: int
    sector_exposure: Dict[str, float]
    single_stock_exposure: Dict[str, float]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


SECTOR_MAP = {
    'RELIANCE': 'Energy', 'ONGC': 'Energy', 'TATASTEEL': 'Metals',
    'HINDALCO': 'Metals', 'JSWSTEEL': 'Metals', 'VEDL': 'Metals',
    'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'TECHM': 'IT', 'HCLTECH': 'IT',
    'HDFCBANK': 'Finance', 'ICICIBANK': 'Finance', 'SBIN': 'Finance',
    'KOTAKBANK': 'Finance', 'AXISBANK': 'Finance', 'INDUSINDBK': 'Finance',
    'BHARTIARTL': 'Telecom', 'ITC': 'FMCG', 'HINDUNILVR': 'FMCG',
    'MARUTI': 'Automobile', 'TATAMOTORS': 'Automobile', 'M&M': 'Automobile',
    'TITAN': 'Consumer', 'ULTRACEMCO': 'Cement', 'LT': 'Construction',
    'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma',
    'POWERGRID': 'Utilities', 'NTPC': 'Utilities', 'COALINDIA': 'Utilities',
}


class ExposureManager:
    """
    Manages real-time exposure monitoring and limits.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('exposure_manager')
        self.risk_engine = risk_engine
        
        self._exposure_cache: Dict[str, ExposureSnapshot] = {}
        self._limits: Dict[str, ExposureLimit] = defaultdict(ExposureLimit)
        self._sector_limits: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        self._exposure_alerts_sent: Dict[str, set] = defaultdict(set)
    
    def set_limit(self, user_id: str, limit: ExposureLimit) -> None:
        self._limits[user_id] = limit
    
    def get_limit(self, user_id: str) -> ExposureLimit:
        if user_id not in self._limits:
            self._limits[user_id] = ExposureLimit()
        return self._limits[user_id]
    
    async def calculate_exposure(self, user_id: str, positions: List[Dict],
                                  cash_balance: float = 100000) -> ExposureSnapshot:
        long_exposure = 0.0
        short_exposure = 0.0
        single_stock = {}
        sector_exp = defaultdict(float)
        
        for pos in positions:
            if pos.get('status') != 'OPEN':
                continue
            
            symbol = pos.get('symbol', '').upper()
            quantity = pos.get('quantity', 0)
            avg_price = pos.get('average_price', 0)
            current_price = pos.get('current_price', avg_price)
            side = pos.get('side', 'BUY')
            
            value = quantity * current_price
            sector = SECTOR_MAP.get(symbol, 'Other')
            
            if side.upper() == 'BUY':
                long_exposure += value
            else:
                short_exposure += value
            
            single_stock[symbol] = single_stock.get(symbol, 0) + value
            sector_exp[sector] += value
        
        total_exposure = long_exposure + short_exposure
        net_exposure = long_exposure - short_exposure
        portfolio_value = cash_balance + total_exposure
        
        leverage = (total_exposure / portfolio_value) if portfolio_value > 0 else 0
        
        snapshot = ExposureSnapshot(
            user_id=user_id,
            total_exposure=total_exposure,
            net_exposure=net_exposure,
            long_exposure=long_exposure,
            short_exposure=short_exposure,
            cash_balance=cash_balance,
            portfolio_value=portfolio_value,
            leverage=leverage,
            position_count=len([p for p in positions if p.get('status') == 'OPEN']),
            sector_exposure=dict(sector_exp),
            single_stock_exposure=single_stock
        )
        
        self._exposure_cache[user_id] = snapshot
        
        await self._check_limits(user_id, snapshot)
        
        return snapshot
    
    async def _check_limits(self, user_id: str, snapshot: ExposureSnapshot) -> None:
        limit = self.get_limit(user_id)
        
        exposure_percent = (snapshot.total_exposure / snapshot.portfolio_value * 100) \
            if snapshot.portfolio_value > 0 else 0
        
        alert_key = f"{user_id}:exposure"
        if exposure_percent > limit.max_exposure_percent:
            if alert_key not in self._exposure_alerts_sent[user_id]:
                self._exposure_alerts_sent[user_id].add(alert_key)
                await self._send_alert(user_id, 'exposure_limit', 
                    f"Exposure {exposure_percent:.1f}% exceeds limit {limit.max_exposure_percent}%")
        
        for symbol, value in snapshot.single_stock_exposure.items():
            alert_key = f"{user_id}:{symbol}"
            if value > limit.max_single_stock_exposure:
                if alert_key not in self._exposure_alerts_sent[user_id]:
                    self._exposure_alerts_sent[user_id].add(alert_key)
                    await self._send_alert(user_id, 'single_stock_limit',
                        f"{symbol} exposure {value:.2f} exceeds limit")
        
        total_sector_value = sum(snapshot.sector_exposure.values())
        for sector, value in snapshot.sector_exposure.items():
            sector_pct = (value / total_sector_value * 100) if total_sector_value > 0 else 0
            if sector_pct > limit.max_sector_concentration:
                alert_key = f"{user_id}:sector:{sector}"
                if alert_key not in self._exposure_alerts_sent[user_id]:
                    self._exposure_alerts_sent[user_id].add(alert_key)
                    await self._send_alert(user_id, 'sector_concentration',
                        f"Sector {sector} concentration {sector_pct:.1f}% exceeds limit")
    
    async def _send_alert(self, user_id: str, alert_type: str, message: str) -> None:
        if self.risk_engine:
            await self.risk_engine.log_event({
                'event_type': 'exposure_warning',
                'user_id': user_id,
                'alert_type': alert_type,
                'message': message,
                'level': 'warning'
            })
    
    def get_exposure(self, user_id: str) -> Optional[ExposureSnapshot]:
        return self._exposure_cache.get(user_id)
    
    def clear_exposure(self, user_id: str) -> None:
        if user_id in self._exposure_cache:
            del self._exposure_cache[user_id]
        if user_id in self._exposure_alerts_sent:
            self._exposure_alerts_sent[user_id].clear()
    
    def get_all_exposures(self) -> List[Dict]:
        return [
            {
                'user_id': user_id,
                'total_exposure': snap.total_exposure,
                'net_exposure': snap.net_exposure,
                'long_exposure': snap.long_exposure,
                'short_exposure': snap.short_exposure,
                'leverage': round(snap.leverage, 2),
                'position_count': snap.position_count,
                'sector_exposure': snap.sector_exposure,
                'timestamp': snap.timestamp.isoformat()
            }
            for user_id, snap in self._exposure_cache.items()
        ]


exposure_manager = ExposureManager()


def get_exposure_manager() -> ExposureManager:
    return exposure_manager
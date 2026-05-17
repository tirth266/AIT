"""
Volatility Monitor
==================
Track market volatility and adjust risk parameters.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class VolatilityLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    ELEVATED = "elevated"
    HIGH = "high"
    EXTREME = "extreme"


@dataclass
class VolatilityData:
    symbol: str
    current_volatility: float
    atr: float
    avg_volatility: float
    volatility_percentile: float
    level: str
    price_change: float
    gap_percent: float
    volume_ratio: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class VolatilityConfig:
    normal_threshold: float = 2.0
    elevated_threshold: float = 3.0
    high_threshold: float = 5.0
    extreme_threshold: float = 10.0
    atr_period: int = 14
    lookback_period: int = 100


class VolatilityMonitor:
    """
    Monitors volatility and adjusts risk parameters accordingly.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('volatility_monitor')
        self.risk_engine = risk_engine
        
        self._volatility_data: Dict[str, VolatilityData] = {}
        self._configs: Dict[str, VolatilityConfig] = defaultdict(VolatilityConfig)
        
        self._price_history: Dict[str, List[float]] = defaultdict(list)
        self._high_volatility_symbols: set = set()
    
    def set_config(self, symbol: str, config: VolatilityConfig) -> None:
        self._configs[symbol] = config
    
    def get_config(self, symbol: str) -> VolatilityConfig:
        return self._configs.get(symbol, VolatilityConfig())
    
    async def update_market_data(self, symbol: str, price: float, 
                                  prev_close: float = None,
                                  high: float = None, low: float = None,
                                  volume: int = None, avg_volume: int = None) -> VolatilityData:
        self._price_history[symbol].append(price)
        
        if len(self._price_history[symbol]) > 1000:
            self._price_history[symbol] = self._price_history[symbol][-500:]
        
        config = self.get_config(symbol)
        
        volatility = self._calculate_volatility(symbol, price)
        atr = self._calculate_atr(symbol, high, low, price)
        avg_vol = self._calculate_avg_volatility(symbol)
        
        price_change = 0
        if prev_close and prev_close > 0:
            price_change = ((price - prev_close) / prev_close) * 100
        
        gap_percent = 0
        if prev_close:
            gap_percent = price_change
        
        volume_ratio = 1.0
        if volume and avg_volume and avg_volume > 0:
            volume_ratio = volume / avg_volume
        
        level = self._determine_volatility_level(volatility, config)
        
        data = VolatilityData(
            symbol=symbol,
            current_volatility=volatility,
            atr=atr,
            avg_volatility=avg_vol,
            volatility_percentile=self._calculate_percentile(symbol, volatility),
            level=level.value,
            price_change=price_change,
            gap_percent=gap_percent,
            volume_ratio=volume_ratio
        )
        
        self._volatility_data[symbol] = data
        
        await self._check_volatility_alerts(symbol, data)
        
        return data
    
    def _calculate_volatility(self, symbol: str, current_price: float) -> float:
        history = self._price_history.get(symbol, [])
        
        if len(history) < 2:
            return 0.0
        
        returns = []
        for i in range(1, len(history)):
            if history[i-1] > 0:
                ret = (history[i] - history[i-1]) / history[i-1]
                returns.append(ret)
        
        if not returns:
            return 0.0
        
        mean = sum(returns) / len(returns)
        variance = sum((r - mean) ** 2 for r in returns) / len(returns)
        
        return (variance ** 0.5) * 100
    
    def _calculate_atr(self, symbol: str, high: float, low: float, close: float) -> float:
        if not high or not low:
            return 0.0
        
        tr = high - low
        
        history = self._price_history.get(symbol, [])
        if len(history) >= 2:
            prev_close = history[-1]
            hl = high - low
            hc = abs(high - prev_close)
            lc = abs(low - prev_close)
            tr = max(hl, hc, lc)
        
        config = self.get_config(symbol)
        
        if symbol in self._volatility_data:
            prev_atr = self._volatility_data[symbol].atr
            if prev_atr > 0:
                return (prev_atr * (config.atr_period - 1) + tr) / config.atr_period
        
        return tr
    
    def _calculate_avg_volatility(self, symbol: str) -> float:
        volatilities = []
        
        history = self._price_history.get(symbol, [])
        
        if len(history) < 20:
            return 0.0
        
        for i in range(20, len(history)):
            if history[i-1] > 0:
                ret = (history[i] - history[i-1]) / history[i-1]
                volatilities.append(abs(ret) * 100)
        
        if not volatilities:
            return 0.0
        
        return sum(volatilities) / len(volatilities)
    
    def _calculate_percentile(self, symbol: str, current_vol: float) -> float:
        history = self._price_history.get(symbol, [])
        
        if len(history) < 10:
            return 50.0
        
        volatilities = []
        for i in range(1, len(history)):
            if history[i-1] > 0:
                ret = abs((history[i] - history[i-1]) / history[i-1]) * 100
                volatilities.append(ret)
        
        if not volatilities:
            return 50.0
        
        sorted_vol = sorted(volatilities)
        count_below = sum(1 for v in sorted_vol if v < current_vol)
        
        return (count_below / len(sorted_vol)) * 100
    
    def _determine_volatility_level(self, volatility: float, config: VolatilityConfig) -> VolatilityLevel:
        if volatility >= config.extreme_threshold:
            return VolatilityLevel.EXTREME
        elif volatility >= config.high_threshold:
            return VolatilityLevel.HIGH
        elif volatility >= config.elevated_threshold:
            return VolatilityLevel.ELEVATED
        elif volatility <= config.normal_threshold:
            return VolatilityLevel.LOW
        else:
            return VolatilityLevel.NORMAL
    
    async def _check_volatility_alerts(self, symbol: str, data: VolatilityData) -> None:
        if data.level == VolatilityLevel.HIGH.value or data.level == VolatilityLevel.EXTREME.value:
            if symbol not in self._high_volatility_symbols:
                self._high_volatility_symbols.add(symbol)
                
                if self.risk_engine:
                    await self.risk_engine.log_event({
                        'event_type': 'volatility_alert',
                        'symbol': symbol,
                        'level': data.level,
                        'volatility': data.current_volatility,
                        'message': f"Volatility {data.level}: {data.current_volatility:.2f}%",
                        'price_change': data.price_change,
                        'gap_percent': data.gap_percent
                    })
        
        elif symbol in self._high_volatility_symbols:
            if data.level in [VolatilityLevel.LOW.value, VolatilityLevel.NORMAL.value]:
                self._high_volatility_symbols.discard(symbol)
    
    def get_volatility_data(self, symbol: str) -> Optional[VolatilityData]:
        return self._volatility_data.get(symbol)
    
    def get_position_sizing_multiplier(self, symbol: str) -> float:
        data = self.get_volatility_data(symbol)
        
        if not data:
            return 1.0
        
        if data.level == VolatilityLevel.EXTREME.value:
            return 0.25
        elif data.level == VolatilityLevel.HIGH.value:
            return 0.5
        elif data.level == VolatilityLevel.ELEVATED.value:
            return 0.75
        elif data.level == VolatilityLevel.LOW.value:
            return 1.25
        
        return 1.0
    
    def get_leverage_recommendation(self, symbol: str) -> float:
        data = self.get_volatility_data(symbol)
        
        if not data:
            return 1.0
        
        if data.level == VolatilityLevel.EXTREME.value:
            return 0.5
        elif data.level == VolatilityLevel.HIGH.value:
            return 0.75
        elif data.level == VolatilityLevel.ELEVATED.value:
            return 0.9
        
        return 1.0
    
    def get_all_volatility(self) -> List[Dict]:
        return [
            {
                'symbol': symbol,
                'volatility': data.current_volatility,
                'atr': round(data.atr, 2),
                'level': data.level,
                'price_change': round(data.price_change, 2),
                'gap_percent': round(data.gap_percent, 2),
                'timestamp': data.timestamp.isoformat()
            }
            for symbol, data in self._volatility_data.items()
        ]


volatility_monitor = VolatilityMonitor()


def get_volatility_monitor() -> VolatilityMonitor:
    return volatility_monitor
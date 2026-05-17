"""
Circuit Breaker System
======================
Protect against extreme market movements and abnormal trading.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitReason(str, Enum):
    VOLATILITY_SPIKE = "volatility_spike"
    PRICE_MOVE = "price_move"
    TRADING_HALT = "trading_halt"
    MANUAL = "manual"
    LIQUIDITY = "liquidity"


@dataclass
class CircuitBreakerConfig:
    price_change_threshold: float = 10.0
    volatility_threshold: float = 5.0
    volume_threshold: float = 0.1
    cooldown_seconds: int = 300
    reset_minutes: int = 15


@dataclass
class CircuitStatus:
    symbol: str
    state: str
    reason: str
    triggered_at: datetime
    expires_at: datetime
    triggered_by: str


class CircuitBreaker:
    """
    Circuit breaker for trading halt on abnormal conditions.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('circuit_breaker')
        self.risk_engine = risk_engine
        
        self._circuits: Dict[str, CircuitStatus] = {}
        self._configs: Dict[str, CircuitBreakerConfig] = defaultdict(CircuitBreakerConfig)
        
        self._symbol_prices: Dict[str, float] = {}
        self._price_history: Dict[str, List[float]] = defaultdict(list)
        
        self._global_circuit: Optional[CircuitStatus] = None
    
    def set_config(self, symbol: str, config: CircuitBreakerConfig) -> None:
        self._configs[symbol] = config
    
    def get_config(self, symbol: str) -> CircuitBreakerConfig:
        return self._configs.get(symbol, CircuitBreakerConfig())
    
    async def update_price(self, symbol: str, price: float, volume: float = 0) -> None:
        old_price = self._symbol_prices.get(symbol)
        self._symbol_prices[symbol] = price
        
        self._price_history[symbol].append(price)
        if len(self._price_history[symbol]) > 100:
            self._price_history[symbol] = self._price_history[symbol][-50:]
        
        if old_price and old_price > 0:
            price_change = abs((price - old_price) / old_price * 100)
            
            config = self.get_config(symbol)
            
            if price_change >= config.price_change_threshold:
                await self._trigger_circuit(symbol, CircuitReason.PRICE_MOVE.value,
                    f"Price moved {price_change:.2f}%")
            
            await self._check_volatility(symbol)
    
    async def _check_volatility(self, symbol: str) -> None:
        history = self._price_history.get(symbol, [])
        if len(history) < 5:
            return
        
        prices = history[-10:]
        
        if len(prices) < 2:
            return
        
        mean = sum(prices) / len(prices)
        variance = sum((p - mean) ** 2 for p in prices) / len(prices)
        std_dev = variance ** 0.5
        
        volatility = (std_dev / mean * 100) if mean > 0 else 0
        
        config = self.get_config(symbol)
        
        if volatility >= config.volatility_threshold:
            await self._trigger_circuit(symbol, CircuitReason.VOLATILITY_SPIKE.value,
                f"Volatility {volatility:.2f}% exceeded threshold")
    
    async def _trigger_circuit(self, symbol: str, reason: str, triggered_by: str) -> None:
        if symbol in self._circuits and self._circuits[symbol].state == CircuitState.OPEN.value:
            return
        
        config = self.get_config(symbol)
        
        triggered_at = datetime.now(timezone.utc)
        expires_at = triggered_at + timedelta(seconds=config.cooldown_seconds)
        
        self._circuits[symbol] = CircuitStatus(
            symbol=symbol,
            state=CircuitState.OPEN.value,
            reason=reason,
            triggered_at=triggered_at,
            expires_at=expires_at,
            triggered_by=triggered_by
        )
        
        if self.risk_engine:
            await self.risk_engine.log_event({
                'event_type': 'circuit_breaker_triggered',
                'symbol': symbol,
                'reason': reason,
                'triggered_by': triggered_by,
                'level': 'warning',
                'expires_at': expires_at.isoformat()
            })
        
        self.logger.warning(f"Circuit breaker triggered for {symbol}: {reason}")
    
    async def _reset_circuit(self, symbol: str) -> None:
        if symbol in self._circuits:
            circuit = self._circuits[symbol]
            circuit.state = CircuitState.CLOSED.value
            
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'circuit_breaker_reset',
                    'symbol': symbol,
                    'level': 'info'
                })
            
            self.logger.info(f"Circuit breaker reset for {symbol}")
    
    def is_triggered(self, symbol: str) -> tuple[bool, str]:
        if self._global_circuit and self._global_circuit.state == CircuitState.OPEN.value:
            return True, f"Global circuit breaker: {self._global_circuit.reason}"
        
        if symbol in self._circuits:
            circuit = self._circuits[symbol]
            
            if circuit.state == CircuitState.OPEN.value:
                if datetime.now(timezone.utc) >= circuit.expires_at:
                    asyncio.create_task(self._reset_circuit(symbol))
                    return False, "Circuit reset"
                
                return True, circuit.reason
        
        return False, ""
    
    def trigger_global_circuit(self, reason: str, triggered_by: str = "manual") -> None:
        config = CircuitBreakerConfig()
        
        triggered_at = datetime.now(timezone.utc)
        expires_at = triggered_at + timedelta(minutes=config.reset_minutes)
        
        self._global_circuit = CircuitStatus(
            symbol="GLOBAL",
            state=CircuitState.OPEN.value,
            reason=reason,
            triggered_at=triggered_at,
            expires_at=expires_at,
            triggered_by=triggered_by
        )
        
        if self.risk_engine:
            self.risk_engine.trigger_global_kill_switch(f"Circuit breaker: {reason}")
        
        self.logger.critical(f"Global circuit breaker triggered: {reason}")
    
    def release_global_circuit(self) -> None:
        if self._global_circuit:
            self._global_circuit.state = CircuitState.CLOSED.value
            
            if self.risk_engine:
                self.risk_engine.release_global_kill_switch()
            
            self.logger.info("Global circuit breaker released")
    
    def manual_trigger(self, symbol: str, reason: str = "manual") -> bool:
        config = self.get_config(symbol)
        
        triggered_at = datetime.now(timezone.utc)
        expires_at = triggered_at + timedelta(seconds=config.cooldown_seconds)
        
        self._circuits[symbol] = CircuitStatus(
            symbol=symbol,
            state=CircuitState.OPEN.value,
            reason=reason,
            triggered_at=triggered_at,
            expires_at=expires_at,
            triggered_by="manual"
        )
        
        self.logger.warning(f"Circuit breaker manually triggered for {symbol}")
        
        return True
    
    def manual_release(self, symbol: str) -> bool:
        if symbol in self._circuits:
            self._circuits[symbol].state = CircuitState.CLOSED.value
            return True
        return False
    
    def get_status(self, symbol: str) -> Optional[Dict]:
        if symbol in self._circuits:
            circuit = self._circuits[symbol]
            return {
                'symbol': circuit.symbol,
                'state': circuit.state,
                'reason': circuit.reason,
                'triggered_at': circuit.triggered_at.isoformat(),
                'expires_at': circuit.expires_at.isoformat()
            }
        return None
    
    def get_all_circuits(self) -> List[Dict]:
        circuits = []
        
        if self._global_circuit:
            circuits.append({
                'symbol': 'GLOBAL',
                'state': self._global_circuit.state,
                'reason': self._global_circuit.reason,
                'triggered_at': self._global_circuit.triggered_at.isoformat()
            })
        
        for symbol, circuit in self._circuits.items():
            circuits.append({
                'symbol': circuit.symbol,
                'state': circuit.state,
                'reason': circuit.reason,
                'triggered_at': circuit.triggered_at.isoformat()
            })
        
        return circuits
    
    def clear_expired(self) -> None:
        now = datetime.now(timezone.utc)
        
        expired = [s for s, c in self._circuits.items() 
                   if c.state == CircuitState.OPEN.value and now >= c.expires_at]
        
        for symbol in expired:
            asyncio.create_task(self._reset_circuit(symbol))


circuit_breaker = CircuitBreaker()


def get_circuit_breaker() -> CircuitBreaker:
    return circuit_breaker
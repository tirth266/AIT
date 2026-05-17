"""
Error Recovery and Retry System
================================
Async error handling with exponential backoff and circuit breaker pattern.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable, List, Type
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from datetime import datetime, timedelta
import traceback

logger = logging.getLogger('error_recovery')


class ErrorSeverity(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class RetryStrategy(Enum):
    IMMEDIATE = 'immediate'
    LINEAR = 'linear'
    EXPONENTIAL = 'exponential'
    FIBONACCI = 'fibonacci'


class CircuitState(Enum):
    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL
    jitter: bool = True
    jitter_factor: float = 0.1


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0
    half_open_max_calls: int = 3


@dataclass
class ErrorRecord:
    """Record of an error occurrence."""
    error_id: str
    strategy_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    timestamp: datetime
    context: Dict[str, Any]
    traceback: str


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        self.name = name
        self.config = config
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._lock = asyncio.Lock()

    async def can_execute(self) -> bool:
        """Check if execution is allowed."""
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return True
            
            if self.state == CircuitState.OPEN:
                if self.last_failure_time:
                    elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                    if elapsed >= self.config.timeout_seconds:
                        self.state = CircuitState.HALF_OPEN
                        return True
                return False
            
            if self.state == CircuitState.HALF_OPEN:
                return True
            
            return False

    async def record_success(self) -> None:
        """Record successful execution."""
        async with self._lock:
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    self.success_count = 0
            elif self.state == CircuitState.CLOSED:
                self.failure_count = max(0, self.failure_count - 1)

    async def record_failure(self) -> None:
        """Record failed execution."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()
            
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.success_count = 0
            elif self.failure_count >= self.config.failure_threshold:
                self.state = CircuitState.OPEN


@dataclass
class RetryPolicy:
    """Policy for retrying failed operations."""
    max_retries: int
    initial_delay: float
    max_delay: float
    strategy: RetryStrategy
    jitter: bool
    jitter_factor: float

    @staticmethod
    def default() -> 'RetryPolicy':
        """Get default retry policy."""
        return RetryPolicy(
            max_retries=3,
            initial_delay=1.0,
            max_delay=60.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=True,
            jitter_factor=0.1
        )

    @staticmethod
    def fast() -> 'RetryPolicy':
        """Get fast retry policy."""
        return RetryPolicy(
            max_retries=2,
            initial_delay=0.5,
            max_delay=5.0,
            strategy=RetryStrategy.LINEAR,
            jitter=False,
            jitter_factor=0
        )

    @staticmethod
    def slow() -> 'RetryPolicy':
        """Get slow retry policy."""
        return RetryPolicy(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=True,
            jitter_factor=0.2
        )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt."""
        if self.strategy == RetryStrategy.IMMEDIATE:
            delay = 0
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * attempt
        elif self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (2 ** attempt)
        elif self.strategy == RetryStrategy.FIBONACCI:
            a, b = 1, 1
            for _ in range(attempt):
                a, b = b, a + b
            delay = self.initial_delay * a
        else:
            delay = self.initial_delay
        
        delay = min(delay, self.max_delay)
        
        if self.jitter:
            jitter_range = delay * self.jitter_factor
            delay += (hash(str(attempt)) % 100) / 100 * jitter_range
        
        return delay


class ErrorRecovery:
    """
    Async error recovery with retry logic and circuit breaker.
    
    Features:
    - Configurable retry policies
    - Exponential backoff with jitter
    - Circuit breaker pattern
    - Error categorization
    - Recovery strategies
    - Error history tracking
    """

    def __init__(self):
        self._retry_configs: Dict[str, RetryConfig] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        
        self._error_history: Dict[str, List[ErrorRecord]] = defaultdict(list)
        self._recovery_strategies: Dict[str, Callable] = {}
        
        self._max_history = 1000
        self._lock = asyncio.Lock()
        
        self._default_retry_config = RetryConfig()

    async def handle_error(
        self,
        strategy_id: str,
        error: Exception,
        consecutive_errors: int = 0
    ) -> bool:
        """Handle an error and determine if execution should continue."""
        error_record = self._create_error_record(strategy_id, error)
        
        async with self._lock:
            self._error_history[strategy_id].append(error_record)
            if len(self._error_history[strategy_id]) > self._max_history:
                self._error_history[strategy_id].pop(0)
        
        circuit_breaker = await self._get_circuit_breaker(strategy_id)
        
        if not await circuit_breaker.can_execute():
            logger.warning(f"Circuit breaker open for {strategy_id}, stopping execution")
            return False
        
        await circuit_breaker.record_failure()
        
        if consecutive_errors >= 10:
            logger.error(f"Too many consecutive errors for {strategy_id}, stopping")
            return False
        
        return True

    def _create_error_record(self, strategy_id: str, error: Exception) -> ErrorRecord:
        """Create error record."""
        return ErrorRecord(
            error_id=f"ERR_{time.time_ns()}",
            strategy_id=strategy_id,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=self._classify_error(error),
            timestamp=datetime.utcnow(),
            context={},
            traceback=traceback.format_exc()
        )

    def _classify_error(self, error: Exception) -> ErrorSeverity:
        """Classify error severity."""
        error_str = str(error).lower()
        
        if any(x in error_str for x in ['timeout', 'connection refused', 'unavailable']):
            return ErrorSeverity.LOW
        elif any(x in error_str for x in ['rate limit', 'quota', 'throttled']):
            return ErrorSeverity.MEDIUM
        elif any(x in error_str for x in ['permission', 'auth', 'forbidden']):
            return ErrorSeverity.HIGH
        elif any(x in error_str for x in ['fatal', 'critical', 'crash']):
            return ErrorSeverity.CRITICAL
        
        return ErrorSeverity.MEDIUM

    async def _get_circuit_breaker(self, strategy_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for strategy."""
        if strategy_id not in self._circuit_breakers:
            config = CircuitBreakerConfig()
            self._circuit_breakers[strategy_id] = CircuitBreaker(strategy_id, config)
        
        return self._circuit_breakers[strategy_id]

    async def execute_with_retry(
        self,
        strategy_id: str,
        coro: Callable,
        retry_policy: Optional[RetryPolicy] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute coroutine with retry logic."""
        policy = retry_policy or RetryPolicy.default()
        
        last_error = None
        for attempt in range(policy.max_retries + 1):
            try:
                result = await coro(*args, **kwargs)
                
                circuit_breaker = await self._get_circuit_breaker(strategy_id)
                await circuit_breaker.record_success()
                
                return result
                
            except asyncio.CancelledError:
                raise
            except Exception as e:
                last_error = e
                
                if attempt < policy.max_retries:
                    delay = policy.calculate_delay(attempt)
                    logger.warning(f"Retry {attempt + 1}/{policy.max_retries} for {strategy_id} after {delay:.2f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All retries exhausted for {strategy_id}: {e}")
        
        raise last_error

    def register_recovery_strategy(self, error_type: str, strategy: Callable) -> None:
        """Register a recovery strategy for specific error type."""
        self._recovery_strategies[error_type] = strategy

    async def recover(
        self,
        strategy_id: str,
        error: Exception,
        context: Dict[str, Any]
    ) -> bool:
        """Attempt to recover from error."""
        error_type = type(error).__name__
        
        if error_type in self._recovery_strategies:
            try:
                strategy = self._recovery_strategies[error_type]
                if asyncio.iscoroutinefunction(strategy):
                    return await strategy(strategy_id, error, context)
                return strategy(strategy_id, error, context)
            except Exception as e:
                logger.error(f"Recovery strategy failed for {error_type}: {e}")
        
        return False

    def set_retry_config(self, operation: str, config: RetryConfig) -> None:
        """Set custom retry configuration for operation."""
        self._retry_configs[operation] = config

    def get_error_history(self, strategy_id: str, limit: int = 50) -> List[Dict]:
        """Get error history for strategy."""
        errors = self._error_history.get(strategy_id, [])[-limit:]
        return [
            {
                'error_id': e.error_id,
                'error_type': e.error_type,
                'error_message': e.error_message,
                'severity': e.severity.value,
                'timestamp': e.timestamp.isoformat()
            }
            for e in errors
        ]

    def get_circuit_state(self, strategy_id: str) -> Optional[str]:
        """Get circuit breaker state for strategy."""
        if strategy_id in self._circuit_breakers:
            return self._circuit_breakers[strategy_id].state.value
        return None

    def get_metrics(self) -> Dict:
        """Get error recovery metrics."""
        return {
            'total_strategies_tracked': len(self._error_history),
            'circuit_breakers_open': sum(
                1 for cb in self._circuit_breakers.values()
                if cb.state == CircuitState.OPEN
            ),
            'total_errors': sum(len(errors) for errors in self._error_history.values())
        }


_error_recovery: Optional[ErrorRecovery] = None


def get_error_recovery() -> ErrorRecovery:
    """Get the global error recovery instance."""
    global _error_recovery
    if _error_recovery is None:
        _error_recovery = ErrorRecovery()
    return _error_recovery
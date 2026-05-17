"""
Backpressure Handler
====================
Async backpressure handling for strategy execution control.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from collections import deque
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger('backpressure')


class PressureLevel(Enum):
    NORMAL = 'normal'
    ELEVATED = 'elevated'
    HIGH = 'high'
    CRITICAL = 'critical'


@dataclass
class BackpressureConfig:
    """Configuration for backpressure handling."""
    max_queue_size: int = 1000
    max_concurrent_strategies: int = 100
    max_memory_mb: int = 512
    cpu_threshold_percent: float = 80.0
    response_time_threshold_ms: float = 1000.0
    auto_throttle: bool = True
    throttle_factor: float = 0.5


@dataclass
class PressureMetrics:
    """Current pressure metrics."""
    level: PressureLevel = PressureLevel.NORMAL
    queue_size: int = 0
    active_strategies: int = 0
    avg_response_time_ms: float = 0.0
    throttled_count: int = 0
    rejected_count: int = 0


class BackpressureHandler:
    """
    Async backpressure handler for strategy execution.
    
    Features:
    - Queue size monitoring
    - Memory pressure detection
    - Response time monitoring
    - Automatic throttling
    - Strategy prioritization
    - Graceful degradation
    """

    def __init__(self, config: Optional[BackpressureConfig] = None):
        self._config = config or BackpressureConfig()
        
        self._strategy_queue: deque = deque(maxlen=self._config.max_queue_size)
        self._active_strategies: Dict[str, asyncio.Task] = {}
        self._strategy_priorities: Dict[str, int] = {}
        
        self._response_times: deque = deque(maxlen=1000)
        self._last_response_times: Dict[str, List[float]] = {}
        
        self._pressure_level = PressureLevel.NORMAL
        self._throttle_factor = 1.0
        self._throttled_strategies: set = set()
        
        self._metrics = PressureMetrics()
        self._lock = asyncio.Lock()
        
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start backpressure monitoring."""
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("BackpressureHandler started")

    async def stop(self) -> None:
        """Stop backpressure monitoring."""
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("BackpressureHandler stopped")

    async def _monitor_loop(self) -> None:
        """Monitor system pressure."""
        while True:
            try:
                await self._calculate_pressure()
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

    async def _calculate_pressure(self) -> None:
        """Calculate current pressure level."""
        async with self._lock:
            queue_size = len(self._strategy_queue)
            active_count = len(self._active_strategies)
            
            avg_response = 0.0
            if self._response_times:
                avg_response = sum(self._response_times) / len(self._response_times)
            
            level = PressureLevel.NORMAL
            
            if active_count >= self._config.max_concurrent_strategies:
                level = PressureLevel.CRITICAL
            elif queue_size >= self._config.max_queue_size * 0.8:
                level = PressureLevel.HIGH
            elif avg_response > self._config.response_time_threshold_ms:
                level = PressureLevel.ELEVATED
            elif queue_size >= self._config.max_queue_size * 0.5:
                level = PressureLevel.ELEVATED
            
            self._pressure_level = level
            self._metrics = PressureMetrics(
                level=level,
                queue_size=queue_size,
                active_strategies=active_count,
                avg_response_time_ms=avg_response,
                throttled_count=len(self._throttled_strategies)
            )
            
            if self._config.auto_throttle and level in [PressureLevel.HIGH, PressureLevel.CRITICAL]:
                self._throttle_factor = self._config.throttle_factor
            else:
                self._throttle_factor = 1.0

    async def can_execute(self, strategy_id: str) -> bool:
        """Check if strategy can be executed."""
        async with self._lock:
            if strategy_id in self._throttled_strategies:
                return False
            
            if self._pressure_level == PressureLevel.CRITICAL:
                priority = self._strategy_priorities.get(strategy_id, 0)
                if priority < 3:
                    self._metrics.rejected_count += 1
                    return False
            
            if len(self._active_strategies) >= self._config.max_concurrent_strategies:
                self._metrics.rejected_count += 1
                return False
            
            return True

    async def execute_with_backpressure(
        self,
        strategy_id: str,
        coro: Any,
        priority: int = 0
    ) -> Any:
        """Execute coroutine with backpressure handling."""
        if not await self.can_execute(strategy_id):
            raise RuntimeError(f"Backpressure blocking execution: {strategy_id}")
        
        strategy_key = f"{strategy_id}_{time.time()}"
        self._strategy_queue.append(strategy_key)
        self._strategy_priorities[strategy_id] = priority
        
        start_time = time.perf_counter()
        
        try:
            if self._throttle_factor < 1.0:
                await asyncio.sleep(self._throttle_factor * 0.1)
            
            task = asyncio.create_task(coro)
            self._active_strategies[strategy_id] = task
            
            result = await task
            
            response_time = (time.perf_counter() - start_time) * 1000
            self._record_response_time(strategy_id, response_time)
            
            return result
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            self._metrics.rejected_count += 1
            raise
        finally:
            self._active_strategies.pop(strategy_id, None)
            self._strategy_priorities.pop(strategy_id, None)
            
            if strategy_key in self._strategy_queue:
                self._strategy_queue.remove(strategy_key)

    def _record_response_time(self, strategy_id: str, response_time: float) -> None:
        """Record response time for monitoring."""
        self._response_times.append(response_time)
        
        if strategy_id not in self._last_response_times:
            self._last_response_times[strategy_id] = []
        
        self._last_response_times[strategy_id].append(response_time)
        if len(self._last_response_times[strategy_id]) > 100:
            self._last_response_times[strategy_id].pop(0)

    async def throttle_strategy(self, strategy_id: str, duration: float = 60.0) -> None:
        """Temporarily throttle a specific strategy."""
        self._throttled_strategies.add(strategy_id)
        self._metrics.throttled_count += 1
        
        asyncio.create_task(self._unthrottle_after(strategy_id, duration))

    async def _unthrottle_after(self, strategy_id: str, duration: float) -> None:
        """Unthrottle after duration."""
        await asyncio.sleep(duration)
        self._throttled_strategies.discard(strategy_id)

    async def unthrottle_strategy(self, strategy_id: str) -> None:
        """Remove throttle from strategy."""
        self._throttled_strategies.discard(strategy_id)

    def get_throttle_factor(self) -> float:
        """Get current throttle factor."""
        return self._throttle_factor

    def get_pressure_level(self) -> PressureLevel:
        """Get current pressure level."""
        return self._pressure_level

    def get_metrics(self) -> Dict:
        """Get backpressure metrics."""
        return {
            'level': self._metrics.level.value,
            'queue_size': self._metrics.queue_size,
            'max_queue_size': self._config.max_queue_size,
            'active_strategies': self._metrics.active_strategies,
            'max_concurrent': self._config.max_concurrent_strategies,
            'avg_response_time_ms': round(self._metrics.avg_response_time_ms, 2),
            'throttled_count': self._metrics.throttled_count,
            'rejected_count': self._metrics.rejected_count,
            'throttle_factor': self._throttle_factor
        }

    def is_healthy(self) -> bool:
        """Check if system is healthy (not under pressure)."""
        return self._pressure_level == PressureLevel.NORMAL


_backpressure_handler: Optional[BackpressureHandler] = None


def get_backpressure_handler() -> BackpressureHandler:
    """Get the global backpressure handler instance."""
    global _backpressure_handler
    if _backpressure_handler is None:
        _backpressure_handler = BackpressureHandler()
    return _backpressure_handler
"""
Strategy Scheduler
=================
Async scheduler for periodic strategy execution and cron-like scheduling.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict
import uuid
import heapq

logger = logging.getLogger('strategy_scheduler')


class ScheduleType(Enum):
    INTERVAL = 'interval'
    CRON = 'cron'
    ONCE = 'once'
    CONTINUOUS = 'continuous'


@dataclass
class ScheduleEntry:
    schedule_id: str
    name: str
    coro: Callable
    schedule_type: ScheduleType
    interval_seconds: Optional[float] = None
    cron_expression: Optional[str] = None
    run_at: Optional[datetime] = None
    priority: int = 0
    enabled: bool = True
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    strategy_id: Optional[str] = None
    user_id: Optional[str] = None
    tags: Set[str] = field(default_factory=set)
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0


class StrategyScheduler:
    """
    Async scheduler for strategy execution with multiple scheduling modes.
    
    Features:
    - Interval-based scheduling
    - Cron-like scheduling
    - One-time scheduling
    - Continuous execution
    - Priority-based execution
    - Missed task handling
    """

    def __init__(self):
        self._schedules: Dict[str, ScheduleEntry] = {}
        self._schedule_heap: List[tuple] = []
        self._running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
        self._running_schedules: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()
        
        self._callbacks: Dict[str, List[Callable]] = {
            'on_schedule_start': [],
            'on_schedule_complete': [],
            'on_schedule_error': [],
            'on_missed': []
        }

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register schedule callbacks."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit_event(self, event: str, schedule: ScheduleEntry) -> None:
        """Emit schedule event."""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(schedule))
                else:
                    callback(schedule)
            except Exception as e:
                logger.error(f"Schedule callback error for {event}: {e}")

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return
        
        self._running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("StrategyScheduler started")

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the scheduler gracefully."""
        self._running = False
        
        for schedule_id, task in list(self._running_schedules.items()):
            task.cancel()
        
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await asyncio.wait_for(self._scheduler_task, timeout=timeout)
            except asyncio.CancelledError:
                pass
        
        logger.info("StrategyScheduler stopped")

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._running:
            try:
                await self._process_schedules()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(1)

    async def _process_schedules(self) -> None:
        """Process due schedules."""
        now = datetime.utcnow()
        
        async with self._lock:
            for schedule_id, schedule in list(self._schedules.items()):
                if not schedule.enabled:
                    continue
                
                if schedule.next_run and schedule.next_run <= now:
                    await self._execute_schedule(schedule)

    async def _execute_schedule(self, schedule: ScheduleEntry) -> None:
        """Execute a scheduled task."""
        schedule.last_run = datetime.utcnow()
        
        if schedule.schedule_type == ScheduleType.ONCE:
            schedule.enabled = False
        
        self._emit_event('on_schedule_start', schedule)
        
        try:
            if schedule.coro:
                await schedule.coro(*schedule.args, **schedule.kwargs)
            
            schedule.run_count += 1
            
            if schedule.schedule_type in [ScheduleType.INTERVAL, ScheduleType.CONTINUOUS]:
                schedule.next_run = datetime.utcnow() + timedelta(seconds=schedule.interval_seconds or 60)
            
            self._emit_event('on_schedule_complete', schedule)
            
        except asyncio.CancelledError:
            raise
        except Exception as e:
            schedule.error_count += 1
            logger.error(f"Schedule {schedule.schedule_id} error: {e}")
            self._emit_event('on_schedule_error', {'schedule': schedule, 'error': str(e)})
            
            if schedule.schedule_type == ScheduleType.CONTINUOUS:
                schedule.next_run = datetime.utcnow() + timedelta(seconds=30)

    def schedule_interval(
        self,
        name: str,
        coro: Callable,
        interval_seconds: float,
        priority: int = 0,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        strategy_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Schedule a task to run at fixed intervals."""
        schedule_id = str(uuid.uuid4())
        
        schedule = ScheduleEntry(
            schedule_id=schedule_id,
            name=name,
            coro=coro,
            schedule_type=ScheduleType.INTERVAL,
            interval_seconds=interval_seconds,
            priority=priority,
            args=args,
            kwargs=kwargs or {},
            strategy_id=strategy_id,
            user_id=user_id,
            tags=tags or set(),
            next_run=datetime.utcnow() + timedelta(seconds=interval_seconds)
        )
        
        self._schedules[schedule_id] = schedule
        logger.info(f"Scheduled interval task: {name} every {interval_seconds}s")
        
        return schedule_id

    def schedule_continuous(
        self,
        name: str,
        coro: Callable,
        interval_seconds: float = 5.0,
        priority: int = 0,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        strategy_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Schedule a task to run continuously."""
        schedule_id = str(uuid.uuid4())
        
        schedule = ScheduleEntry(
            schedule_id=schedule_id,
            name=name,
            coro=coro,
            schedule_type=ScheduleType.CONTINUOUS,
            interval_seconds=interval_seconds,
            priority=priority,
            args=args,
            kwargs=kwargs or {},
            strategy_id=strategy_id,
            user_id=user_id,
            tags=tags or set(),
            next_run=datetime.utcnow()
        )
        
        self._schedules[schedule_id] = schedule
        logger.info(f"Scheduled continuous task: {name}")
        
        return schedule_id

    def schedule_once(
        self,
        name: str,
        coro: Callable,
        run_at: datetime,
        priority: int = 0,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        strategy_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Schedule a one-time task."""
        schedule_id = str(uuid.uuid4())
        
        schedule = ScheduleEntry(
            schedule_id=schedule_id,
            name=name,
            coro=coro,
            schedule_type=ScheduleType.ONCE,
            run_at=run_at,
            priority=priority,
            args=args,
            kwargs=kwargs or {},
            strategy_id=strategy_id,
            user_id=user_id,
            next_run=run_at
        )
        
        self._schedules[schedule_id] = schedule
        logger.info(f"Scheduled one-time task: {name} at {run_at}")
        
        return schedule_id

    def schedule_cron(
        self,
        name: str,
        coro: Callable,
        cron_expression: str,
        priority: int = 0,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        strategy_id: Optional[str] = None,
        user_id: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> str:
        """Schedule a task using cron-like expression."""
        schedule_id = str(uuid.uuid4())
        
        next_run = self._parse_cron_next_run(cron_expression)
        
        schedule = ScheduleEntry(
            schedule_id=schedule_id,
            name=name,
            coro=coro,
            schedule_type=ScheduleType.CRON,
            cron_expression=cron_expression,
            priority=priority,
            args=args,
            kwargs=kwargs or {},
            strategy_id=strategy_id,
            user_id=user_id,
            tags=tags or set(),
            next_run=next_run
        )
        
        self._schedules[schedule_id] = schedule
        logger.info(f"Scheduled cron task: {name} with expression {cron_expression}")
        
        return schedule_id

    def _parse_cron_next_run(self, cron_expr: str) -> datetime:
        """Parse cron expression and calculate next run time."""
        parts = cron_expr.split()
        if len(parts) < 5:
            return datetime.utcnow() + timedelta(hours=1)
        
        now = datetime.utcnow()
        
        minute = int(parts[0]) if parts[0] != '*' else now.minute
        hour = int(parts[1]) if parts[1] != '*' else now.hour
        day = int(parts[2]) if parts[2] != '*' else now.day
        month = int(parts[3]) if parts[3] != '*' else now.month
        
        next_run = now.replace(minute=minute, hour=hour, day=day, month=month)
        
        if next_run <= now:
            next_run += timedelta(days=1)
        
        return next_run

    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a scheduled task."""
        if schedule_id in self._schedules:
            self._schedules[schedule_id].enabled = True
            return True
        return False

    def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a scheduled task."""
        if schedule_id in self._schedules:
            self._schedules[schedule_id].enabled = False
            return True
        return False

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a scheduled task."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False

    def get_schedule(self, schedule_id: str) -> Optional[Dict]:
        """Get schedule details."""
        if schedule_id not in self._schedules:
            return None
        
        schedule = self._schedules[schedule_id]
        return {
            'schedule_id': schedule.schedule_id,
            'name': schedule.name,
            'schedule_type': schedule.schedule_type.value,
            'enabled': schedule.enabled,
            'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
            'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
            'run_count': schedule.run_count,
            'error_count': schedule.error_count
        }

    def get_all_schedules(self) -> List[Dict]:
        """Get all schedules."""
        return [self.get_schedule(sid) for sid in self._schedules.keys()]

    def get_schedules_for_strategy(self, strategy_id: str) -> List[Dict]:
        """Get all schedules for a specific strategy."""
        return [
            self.get_schedule(sid)
            for sid, s in self._schedules.items()
            if s.strategy_id == strategy_id
        ]

    def get_metrics(self) -> Dict:
        """Get scheduler metrics."""
        return {
            'total_schedules': len(self._schedules),
            'enabled_schedules': sum(1 for s in self._schedules.values() if s.enabled),
            'total_runs': sum(s.run_count for s in self._schedules.values()),
            'total_errors': sum(s.error_count for s in self._schedules.values())
        }


_scheduler: Optional[StrategyScheduler] = None


def get_scheduler() -> StrategyScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = StrategyScheduler()
    return _scheduler
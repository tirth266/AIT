"""
Task Manager
============
Async task management with priority queues, monitoring, and cancellation.
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
from datetime import datetime
import uuid

logger = logging.getLogger('task_manager')


class TaskStatus(Enum):
    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'


class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    task_id: str
    name: str
    coro: Callable
    priority: TaskPriority = TaskPriority.NORMAL
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    timeout: Optional[float] = None
    retries: int = 0
    max_retries: int = 3
    tags: Set[str] = field(default_factory=set)
    strategy_id: Optional[str] = None
    user_id: Optional[str] = None


@dataclass
class TaskMetrics:
    total_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    avg_execution_time: float = 0.0
    tasks_per_minute: float = 0.0


class TaskManager:
    """
    Async task manager with priority scheduling and monitoring.
    
    Features:
    - Priority queue for task execution
    - Task timeout handling
    - Automatic retry with backoff
    - Task metrics and monitoring
    - Task cancellation
    - Task tagging and filtering
    """

    def __init__(self, max_concurrent: int = 200, default_timeout: float = 60.0):
        self._max_concurrent = max_concurrent
        self._default_timeout = default_timeout
        
        self._pending_tasks: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._completed_tasks: Dict[str, Task] = {}
        self._task_metadata: Dict[str, Task] = {}
        
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._active_count = 0
        
        self._metrics = TaskMetrics()
        self._start_time = time.time()
        
        self._running = False
        self._worker_tasks: Set[asyncio.Task] = set()
        
        self._callbacks: Dict[str, List[Callable]] = {
            'on_task_start': [],
            'on_task_complete': [],
            'on_task_fail': [],
            'on_task_cancel': []
        }

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register task lifecycle callbacks."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit_event(self, event: str, task: Task) -> None:
        """Emit task event."""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(task))
                else:
                    callback(task)
            except Exception as e:
                logger.error(f"Task callback error for {event}: {e}")

    async def start(self) -> None:
        """Start the task manager workers."""
        if self._running:
            return
        
        self._running = True
        self._start_time = time.time()
        
        for i in range(min(10, self._max_concurrent // 20 + 1)):
            worker = asyncio.create_task(self._worker_loop(i))
            self._worker_tasks.add(worker)
        
        logger.info(f"TaskManager started with {len(self._worker_tasks)} workers")

    async def stop(self, timeout: float = 10.0) -> None:
        """Stop the task manager."""
        self._running = False
        
        for worker in self._worker_tasks:
            worker.cancel()
        
        await asyncio.gather(*self._worker_tasks, return_exceptions=True)
        
        for task in self._running_tasks.values():
            task.cancel()
        
        logger.info("TaskManager stopped")

    async def _worker_loop(self, worker_id: int) -> None:
        """Worker loop for processing tasks."""
        while self._running:
            try:
                task = await asyncio.wait_for(
                    self._pending_tasks.get(),
                    timeout=1.0
                )
                
                asyncio.create_task(self._execute_task(task))
                
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

    async def _execute_task(self, task: Task) -> None:
        """Execute a single task with proper resource management."""
        async with self._semaphore:
            if task.status == TaskStatus.CANCELLED:
                return
            
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            self._running_tasks[task.task_id] = asyncio.current_task()
            self._metrics.running_tasks += 1
            
            self._emit_event('on_task_start', task)
            
            try:
                if task.timeout:
                    result = await asyncio.wait_for(
                        task.coro(*task.args, **task.kwargs),
                        timeout=task.timeout
                    )
                else:
                    result = await task.coro(*task.args, **task.kwargs)
                
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.utcnow()
                task.result = result
                
                self._metrics.completed_tasks += 1
                self._emit_event('on_task_complete', task)
                
            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                self._metrics.cancelled_tasks += 1
                self._emit_event('on_task_cancel', task)
                
            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = "Task timeout"
                self._metrics.failed_tasks += 1
                self._emit_event('on_task_fail', task)
                
                if task.retries < task.max_retries:
                    task.retries += 1
                    await self._retry_task(task)
                    
            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                self._metrics.failed_tasks += 1
                self._emit_event('on_task_fail', task)
                
                if task.retries < task.max_retries:
                    task.retries += 1
                    await self._retry_task(task)
            
            finally:
                self._running_tasks.pop(task.task_id, None)
                self._active_count = len(self._running_tasks)
                self._completed_tasks[task.task_id] = task
                self._task_metadata[task.task_id] = task
                
                self._update_metrics()

    async def _retry_task(self, task: Task) -> None:
        """Retry a failed task with exponential backoff."""
        delay = min(2 ** task.retries, 30)
        await asyncio.sleep(delay)
        
        await self.submit(
            name=task.name,
            coro=task.coro,
            priority=task.priority,
            args=task.args,
            kwargs=task.kwargs,
            timeout=task.timeout,
            max_retries=task.max_retries - task.retries,
            tags=task.tags,
            strategy_id=task.strategy_id,
            user_id=task.user_id
        )

    def _update_metrics(self) -> None:
        """Update task metrics."""
        self._metrics.total_tasks += 1
        
        if self._metrics.total_tasks > 1:
            elapsed = time.time() - self._start_time
            self._metrics.tasks_per_minute = self._metrics.total_tasks / elapsed * 60

    async def submit(
        self,
        name: str,
        coro: Callable,
        priority: TaskPriority = TaskPriority.NORMAL,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
        timeout: Optional[float] = None,
        max_retries: int = 3,
        tags: Optional[Set[str]] = None,
        strategy_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Submit a task for execution."""
        task_id = str(uuid.uuid4())
        
        task = Task(
            task_id=task_id,
            name=name,
            coro=coro,
            priority=priority,
            args=args,
            kwargs=kwargs or {},
            timeout=timeout or self._default_timeout,
            max_retries=max_retries,
            tags=tags or set(),
            strategy_id=strategy_id,
            user_id=user_id
        )
        
        priority_value = (4 - priority.value, time.time(), task_id)
        await self._pending_tasks.put(priority_value)
        
        logger.debug(f"Task submitted: {name} ({task_id})")
        return task_id

    async def submit_strategy(
        self,
        strategy_id: str,
        user_id: str,
        coro: Callable,
        priority: TaskPriority = TaskPriority.NORMAL
    ) -> str:
        """Submit a strategy-specific task."""
        return await self.submit(
            name=f"strategy_{strategy_id}",
            coro=coro,
            priority=priority,
            strategy_id=strategy_id,
            user_id=user_id,
            tags={'strategy', strategy_id}
        )

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending or running task."""
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.cancel()
            return True
        
        logger.warning(f"Cannot cancel task {task_id}: not found")
        return False

    async def cancel_strategy_tasks(self, strategy_id: str) -> int:
        """Cancel all tasks for a specific strategy."""
        cancelled = 0
        
        for task_id, task in list(self._running_tasks.items()):
            if task_id in self._task_metadata:
                meta = self._task_metadata[task_id]
                if meta.strategy_id == strategy_id:
                    task.cancel()
                    cancelled += 1
        
        return cancelled

    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get status of a task."""
        if task_id in self._task_metadata:
            return self._task_metadata[task_id].status
        return None

    def get_task_result(self, task_id: str) -> Any:
        """Get result of a completed task."""
        if task_id in self._completed_tasks:
            return self._completed_tasks[task_id].result
        return None

    def get_pending_count(self) -> int:
        """Get number of pending tasks."""
        return self._pending_tasks.qsize()

    def get_running_count(self) -> int:
        """Get number of running tasks."""
        return len(self._running_tasks)

    def get_metrics(self) -> Dict:
        """Get task metrics."""
        return {
            'total_tasks': self._metrics.total_tasks,
            'running_tasks': self._metrics.running_tasks,
            'completed_tasks': self._metrics.completed_tasks,
            'failed_tasks': self._metrics.failed_tasks,
            'cancelled_tasks': self._metrics.cancelled_tasks,
            'pending_tasks': self.get_pending_count(),
            'tasks_per_minute': round(self._metrics.tasks_per_minute, 2),
            'max_concurrent': self._max_concurrent
        }


_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get the global task manager instance."""
    global _task_manager
    if _task_manager is None:
        _task_manager = TaskManager(max_concurrent=200)
    return _task_manager
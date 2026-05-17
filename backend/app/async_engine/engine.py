"""
Async Strategy Engine
=====================
Core async orchestrator for strategy execution with proper event loop management.
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager
import weakref

from .task_manager import get_task_manager, TaskManager
from .scheduler import get_scheduler, StrategyScheduler
from .rate_limiter import get_rate_limiter, RateLimiter
from .backpressure import get_backpressure_handler, BackpressureHandler
from .recovery import get_error_recovery, ErrorRecovery
from .event_bus import get_event_bus, EventBus
from .market_data import get_market_ingestion, AsyncMarketDataIngestion

logger = logging.getLogger('async_strategy_engine')


class EngineStatus(Enum):
    STOPPED = 'stopped'
    STARTING = 'starting'
    RUNNING = 'running'
    PAUSED = 'paused'
    SHUTTING_DOWN = 'shutting_down'
    ERROR = 'error'


class StrategyState(Enum):
    CREATED = 'created'
    INITIALIZING = 'initializing'
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPED = 'stopped'
    ERROR = 'error'
    RECOVERING = 'recovering'


@dataclass
class AsyncStrategyInstance:
    strategy_id: str
    user_id: str
    name: str
    symbol: str
    exchange: str
    timeframe: str
    mode: str
    config: Dict[str, Any]
    state: StrategyState = StrategyState.CREATED
    task: Optional[asyncio.Task] = None
    last_signal_time: Optional[datetime] = None
    last_error: Optional[str] = None
    execution_count: int = 0
    consecutive_errors: int = 0
    trades_count: int = 0
    started_at: Optional[datetime] = None
    execution_interval: float = 5.0
    priority: int = 0


@dataclass
class EngineMetrics:
    total_strategies: int = 0
    active_strategies: int = 0
    signals_generated: int = 0
    signals_executed: int = 0
    total_pnl: float = 0.0
    uptime_seconds: float = 0.0
    errors_count: int = 0
    tasks_scheduled: int = 0
    tasks_completed: int = 0
    backpressure_events: int = 0
    rate_limited: int = 0
    avg_execution_time_ms: float = 0.0


class AsyncStrategyEngine:
    """
    Fully async strategy engine with single global event loop.
    
    Features:
    - Single event loop for all async operations
    - Task-based strategy execution
    - Built-in rate limiting and backpressure
    - Error recovery with retry logic
    - Event-driven architecture
    - Graceful shutdown handling
    """

    _instance: Optional['AsyncStrategyEngine'] = None
    _loop: Optional[asyncio.AbstractEventLoop] = None

    def __init__(self):
        self.status = EngineStatus.STOPPED
        self.strategies: Dict[str, AsyncStrategyInstance] = {}
        self.metrics = EngineMetrics()
        self._running = False
        self._shutdown_event = asyncio.Event()
        self._start_time: Optional[datetime] = None
        
        self.task_manager: Optional[TaskManager] = None
        self.scheduler: Optional[StrategyScheduler] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.backpressure: Optional[BackpressureHandler] = None
        self.error_recovery: Optional[ErrorRecovery] = None
        self.event_bus: Optional[EventBus] = None
        self.market_ingestion: Optional[AsyncMarketDataIngestion] = None

        self._strategy_tasks: Set[asyncio.Task] = set()
        self._background_tasks: Set[asyncio.Task] = set()
        
        self._market_data_cache: Dict[str, List[Dict]] = {}
        
        self._callbacks: Dict[str, List[Callable]] = {
            'on_signal': [],
            'on_trade': [],
            'on_error': [],
            'on_status_change': [],
            'on_metric': []
        }

    @classmethod
    def get_instance(cls) -> 'AsyncStrategyEngine':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = AsyncStrategyEngine()
        return cls._instance

    @classmethod
    async def create_loop(cls) -> asyncio.AbstractEventLoop:
        """Create and set the global event loop."""
        if cls._loop is None or cls._loop.is_closed():
            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
            logger.info("Created new global event loop")
        return cls._loop

    @classmethod
    def get_loop(cls) -> Optional[asyncio.AbstractEventLoop]:
        """Get the global event loop."""
        return cls._loop

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register event callbacks."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit_event(self, event: str, data: Any) -> None:
        """Emit event to registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(data))
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    async def initialize(self) -> bool:
        """Initialize all async components."""
        try:
            logger.info("Initializing Async Strategy Engine...")
            
            self.task_manager = get_task_manager()
            self.scheduler = get_scheduler()
            self.rate_limiter = get_rate_limiter()
            self.backpressure = get_backpressure_handler()
            self.error_recovery = get_error_recovery()
            self.event_bus = get_event_bus()
            self.market_ingestion = get_market_ingestion()

            await self.task_manager.start()
            await self.scheduler.start()
            await self.market_ingestion.start()
            
            await self._setup_event_handlers()
            
            logger.info("Async Strategy Engine initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize engine: {e}")
            return False

    async def _setup_event_handlers(self) -> None:
        """Setup internal event handlers."""
        if self.event_bus:
            self.event_bus.subscribe('market_data', self._on_market_data)
            self.event_bus.subscribe('signal_generated', self._on_signal)
            self.event_bus.subscribe('trade_executed', self._on_trade)
            self.event_bus.subscribe('error', self._on_error)

    async def _on_market_data(self, data: Dict) -> None:
        """Handle incoming market data."""
        symbol = data.get('symbol')
        timeframe = data.get('timeframe')
        candles = data.get('candles', [])
        
        if symbol and timeframe:
            cache_key = f"{symbol}:{timeframe}"
            self._market_data_cache[cache_key] = candles

    async def _on_signal(self, data: Dict) -> None:
        """Handle generated signal."""
        self.metrics.signals_generated += 1
        self._emit_event('on_signal', data)

    async def _on_trade(self, data: Dict) -> None:
        """Handle executed trade."""
        self.metrics.signals_executed += 1
        self._emit_event('on_trade', data)

    async def _on_error(self, data: Dict) -> None:
        """Handle error event."""
        self.metrics.errors_count += 1
        strategy_id = data.get('strategy_id')
        if strategy_id and strategy_id in self.strategies:
            self.strategies[strategy_id].consecutive_errors += 1
        self._emit_event('on_error', data)

    async def start(self) -> bool:
        """Start the async strategy engine."""
        if self._running:
            logger.warning("Engine already running")
            return True

        try:
            self.status = EngineStatus.STARTING
            logger.info("Starting Async Strategy Engine...")

            await self.create_loop()
            
            if not await self.initialize():
                raise RuntimeError("Failed to initialize components")

            self._running = True
            self._start_time = datetime.utcnow()
            self.status = EngineStatus.RUNNING

            await self._start_background_tasks()
            await self._load_active_strategies()

            logger.info("Async Strategy Engine started successfully")
            self._emit_event('on_status_change', {'status': 'running'})
            return True

        except Exception as e:
            logger.error(f"Failed to start engine: {e}")
            self.status = EngineStatus.ERROR
            self._running = False
            return False

    async def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        monitor_task = asyncio.create_task(self._monitor_loop())
        self._background_tasks.add(monitor_task)
        monitor_task.add_done_callback(self._background_tasks.discard)

        metrics_task = asyncio.create_task(self._metrics_loop())
        self._background_tasks.add(metrics_task)
        metrics_task.add_done_callback(self._background_tasks.discard)

    async def _monitor_loop(self) -> None:
        """Background task monitoring."""
        while self._running:
            try:
                await self._check_strategy_health()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

    async def _check_strategy_health(self) -> None:
        """Check health of running strategies."""
        for instance in self.strategies.values():
            if instance.state == StrategyState.RUNNING:
                if instance.consecutive_errors >= 5:
                    logger.warning(f"Strategy {instance.strategy_id} has too many errors, pausing")
                    await self.pause_strategy(instance.strategy_id)

    async def _metrics_loop(self) -> None:
        """Background metrics collection."""
        while self._running:
            try:
                if self._start_time:
                    self.metrics.uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()
                self._emit_event('on_metric', self.get_metrics())
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Metrics loop error: {e}")

    async def _load_active_strategies(self) -> None:
        """Load active strategies from database."""
        from app.database.connection import get_db
        db = get_db()
        if not db:
            logger.error("Database not available")
            return

        try:
            active_strategies = list(db.strategies.find({
                'is_active': True,
                'mode': 'paper'
            }))

            for strategy in active_strategies:
                strategy_id = str(strategy['_id'])
                instance = AsyncStrategyInstance(
                    strategy_id=strategy_id,
                    user_id=strategy.get('user_id', ''),
                    name=strategy.get('strategy_name', 'Unnamed'),
                    symbol=strategy.get('symbol', ''),
                    exchange=strategy.get('exchange', 'NSE'),
                    timeframe=strategy.get('timeframe', '1m'),
                    mode=strategy.get('mode', 'paper'),
                    config=strategy,
                    state=StrategyState.PAUSED,
                    execution_interval=strategy.get('execution_interval', 5.0)
                )
                self.strategies[strategy_id] = instance

            logger.info(f"Loaded {len(active_strategies)} active strategies")

        except Exception as e:
            logger.error(f"Failed to load active strategies: {e}")

    async def stop(self, timeout: float = 30.0) -> bool:
        """Gracefully stop the engine."""
        if not self._running:
            return True

        try:
            self.status = EngineStatus.SHUTTING_DOWN
            logger.info("Stopping Async Strategy Engine...")

            self._running = False
            
            for instance in self.strategies.values():
                if instance.task and not instance.task.done():
                    instance.task.cancel()

            for task in list(self._background_tasks):
                task.cancel()

            await asyncio.gather(*self._background_tasks, return_exceptions=True)

            if self.scheduler:
                await self.scheduler.stop()
            if self.task_manager:
                await self.task_manager.stop()
            if self.market_ingestion:
                await self.market_ingestion.stop()

            if self._loop and self._loop.is_running():
                self._shutdown_event.set()

            self.status = EngineStatus.STOPPED
            logger.info("Async Strategy Engine stopped")
            self._emit_event('on_status_change', {'status': 'stopped'})
            return True

        except Exception as e:
            logger.error(f"Error stopping engine: {e}")
            self.status = EngineStatus.ERROR
            return False

    async def add_strategy(self, strategy_config: Dict) -> str:
        """Add a new strategy to the engine."""
        from bson import ObjectId
        strategy_id = str(ObjectId())

        instance = AsyncStrategyInstance(
            strategy_id=strategy_id,
            user_id=strategy_config.get('user_id', ''),
            name=strategy_config.get('strategy_name', 'Unnamed'),
            symbol=strategy_config.get('symbol', ''),
            exchange=strategy_config.get('exchange', 'NSE'),
            timeframe=strategy_config.get('timeframe', '1m'),
            mode=strategy_config.get('mode', 'paper'),
            config=strategy_config,
            state=StrategyState.CREATED,
            execution_interval=strategy_config.get('execution_interval', 5.0),
            priority=strategy_config.get('priority', 0)
        )

        self.strategies[strategy_id] = instance
        self.metrics.total_strategies += 1

        logger.info(f"Strategy added: {strategy_id}")
        return strategy_id

    async def start_strategy(self, strategy_id: str) -> bool:
        """Start a specific strategy as an async task."""
        if strategy_id not in self.strategies:
            logger.error(f"Strategy {strategy_id} not found")
            return False

        instance = self.strategies[strategy_id]
        
        if self.rate_limiter:
            allowed = await self.rate_limiter.check_limit('strategy_start', instance.user_id)
            if not allowed:
                logger.warning(f"Rate limited for strategy start: {strategy_id}")
                self.metrics.rate_limited += 1
                return False

        if self.backpressure:
            can_proceed = await self.backpressure.can_execute(strategy_id)
            if not can_proceed:
                logger.warning(f"Backpressure blocking strategy start: {strategy_id}")
                self.metrics.backpressure_events += 1
                return False

        try:
            instance.state = StrategyState.INITIALIZING
            instance.started_at = datetime.utcnow()
            
            task = asyncio.create_task(
                self._strategy_execution_loop(instance),
                name=f"strategy_{strategy_id}"
            )
            instance.task = task
            self._strategy_tasks.add(task)
            
            instance.state = StrategyState.RUNNING
            self.metrics.active_strategies += 1
            
            logger.info(f"Strategy {strategy_id} started")
            return True

        except Exception as e:
            logger.error(f"Failed to start strategy {strategy_id}: {e}")
            instance.state = StrategyState.ERROR
            instance.last_error = str(e)
            return False

    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop a specific strategy."""
        if strategy_id not in self.strategies:
            return False

        instance = self.strategies[strategy_id]
        
        if instance.task and not instance.task.done():
            instance.task.cancel()
            try:
                await asyncio.wait_for(instance.task, timeout=5.0)
            except asyncio.CancelledError:
                pass

        instance.state = StrategyState.STOPPED
        if self.metrics.active_strategies > 0:
            self.metrics.active_strategies -= 1

        logger.info(f"Strategy {strategy_id} stopped")
        return True

    async def pause_strategy(self, strategy_id: str) -> bool:
        """Pause a specific strategy."""
        if strategy_id not in self.strategies:
            return False

        instance = self.strategies[strategy_id]
        instance.state = StrategyState.PAUSED
        logger.info(f"Strategy {strategy_id} paused")
        return True

    async def _strategy_execution_loop(self, instance: AsyncStrategyInstance) -> None:
        """Main async execution loop for a single strategy."""
        while self._running and instance.state == StrategyState.RUNNING:
            try:
                start_time = time.perf_counter()
                
                await self._execute_strategy(instance)
                
                execution_time = (time.perf_counter() - start_time) * 1000
                self._update_avg_execution_time(execution_time)
                
                instance.execution_count += 1
                
                await asyncio.sleep(instance.execution_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Strategy execution error {instance.strategy_id}: {e}")
                instance.consecutive_errors += 1
                instance.last_error = str(e)
                
                if self.error_recovery:
                    should_continue = await self.error_recovery.handle_error(
                        instance.strategy_id,
                        e,
                        instance.consecutive_errors
                    )
                    if not should_continue:
                        instance.state = StrategyState.ERROR
                        break
                
                await asyncio.sleep(5)

    async def _execute_strategy(self, instance: AsyncStrategyInstance) -> None:
        """Execute a single strategy iteration."""
        try:
            candles = self._get_market_data(instance.symbol, instance.timeframe)
            if not candles or len(candles) < 50:
                return

            from app.strategy_engine.signal_generator import SignalGenerator
            generator = SignalGenerator()
            
            signal = await generator.generate(
                instance.config,
                candles,
                instance.symbol
            )

            if signal:
                instance.last_signal_time = datetime.utcnow()
                instance.consecutive_errors = 0
                
                await self._process_signal(instance, signal)

                self._emit_event('on_signal', {
                    'strategy_id': instance.strategy_id,
                    'signal': signal
                })

        except Exception as e:
            logger.error(f"Strategy execution error {instance.strategy_id}: {e}")
            raise

    def _get_market_data(self, symbol: str, timeframe: str) -> List[Dict]:
        """Get market data for a symbol."""
        cache_key = f"{symbol}:{timeframe}"
        return self._market_data_cache.get(cache_key, [])

    def _update_avg_execution_time(self, execution_time_ms: float) -> None:
        """Update running average of execution time."""
        count = self.metrics.tasks_completed
        if count == 0:
            self.metrics.avg_execution_time_ms = execution_time_ms
        else:
            self.metrics.avg_execution_time_ms = (
                (self.metrics.avg_execution_time_ms * count + execution_time_ms) / (count + 1)
            )
        self.metrics.tasks_completed += 1

    async def _process_signal(self, instance: AsyncStrategyInstance, signal: Dict) -> None:
        """Process a trading signal."""
        if not signal or signal.get('action') == 'HOLD':
            return

        risk_check = await self._check_risk(instance, signal)
        if not risk_check['allowed']:
            logger.warning(f"Signal rejected by risk manager: {risk_check['reason']}")
            return

        if instance.mode == 'paper':
            from app.strategy_engine.paper_trading import get_paper_engine
            paper_engine = get_paper_engine()
            trade = await paper_engine.execute_trade(instance.strategy_id, instance.user_id, signal)
        else:
            from app.trading_engine.execution_engine import get_execution_engine
            exec_engine = get_execution_engine()
            trade = await exec_engine.execute_live_trade(instance.strategy_id, instance.user_id, signal)

        if trade:
            instance.trades_count += 1
            
            self._emit_event('on_trade', trade)

    async def _check_risk(self, instance: AsyncStrategyInstance, signal: Dict) -> Dict:
        """Check risk for signal."""
        from app.strategy_engine.risk_manager import RiskManager
        risk_manager = RiskManager()
        
        return await risk_manager.check_signal(
            instance.user_id,
            signal,
            instance.config.get('risk_settings', {})
        )

    def get_strategy_status(self, strategy_id: str) -> Optional[Dict]:
        """Get status of a strategy."""
        if strategy_id not in self.strategies:
            return None

        instance = self.strategies[strategy_id]
        return {
            'strategy_id': instance.strategy_id,
            'name': instance.name,
            'state': instance.state.value,
            'symbol': instance.symbol,
            'timeframe': instance.timeframe,
            'trades_count': instance.trades_count,
            'execution_count': instance.execution_count,
            'last_signal_time': instance.last_signal_time.isoformat() if instance.last_signal_time else None,
            'last_error': instance.last_error,
            'consecutive_errors': instance.consecutive_errors
        }

    def get_all_strategies(self) -> List[Dict]:
        """Get all strategy statuses."""
        return [self.get_strategy_status(sid) for sid in self.strategies.keys()]

    def get_metrics(self) -> Dict:
        """Get engine metrics."""
        return {
            'status': self.status.value,
            'total_strategies': self.metrics.total_strategies,
            'active_strategies': self.metrics.active_strategies,
            'signals_generated': self.metrics.signals_generated,
            'signals_executed': self.metrics.signals_executed,
            'total_pnl': self.metrics.total_pnl,
            'uptime_seconds': self.metrics.uptime_seconds,
            'errors_count': self.metrics.errors_count,
            'tasks_scheduled': self.metrics.tasks_scheduled,
            'tasks_completed': self.metrics.tasks_completed,
            'backpressure_events': self.metrics.backpressure_events,
            'rate_limited': self.metrics.rate_limited,
            'avg_execution_time_ms': round(self.metrics.avg_execution_time_ms, 2)
        }


_async_engine: Optional[AsyncStrategyEngine] = None


def get_async_engine() -> AsyncStrategyEngine:
    """Get the global async strategy engine instance."""
    global _async_engine
    if _async_engine is None:
        _async_engine = AsyncStrategyEngine.get_instance()
    return _async_engine


async def initialize_async_engine() -> AsyncStrategyEngine:
    """Initialize and start the async engine."""
    engine = get_async_engine()
    await engine.start()
    return engine
"""
Strategy Engine Core
====================
Main orchestrator for strategy execution, signal processing, and lifecycle management.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading

from bson import ObjectId

from app.database.connection import get_db
from app.websocket.socket_manager import SocketManager
from .signal_generator import SignalGenerator
from .execution_engine import ExecutionEngine
from .strategy_manager import StrategyManager
from .risk_manager import RiskManager
from .position_manager import PositionManager
from .indicators import IndicatorRegistry

logger = logging.getLogger('strategy_engine')


class EngineStatus(Enum):
    STOPPED = 'stopped'
    STARTING = 'starting'
    RUNNING = 'running'
    PAUSED = 'paused'
    ERROR = 'error'


class StrategyStatus(Enum):
    CREATED = 'created'
    RUNNING = 'running'
    PAUSED = 'paused'
    STOPPED = 'stopped'
    ERROR = 'error'


@dataclass
class StrategyInstance:
    strategy_id: str
    user_id: str
    name: str
    symbol: str
    exchange: str
    timeframe: str
    mode: str
    config: Dict[str, Any]
    status: StrategyStatus = StrategyStatus.CREATED
    last_signal_time: Optional[datetime] = None
    trades_count: int = 0
    started_at: Optional[datetime] = None


@dataclass
class EngineMetrics:
    total_strategies: int = 0
    active_strategies: int = 0
    signals_generated: int = 0
    signals_executed: int = 0
    total_pnl: float = 0.0
    uptime_seconds: float = 0.0
    errors_count: int = 0


class StrategyEngine:
    """
    Core strategy execution engine.

    Manages strategy lifecycle, signal generation, execution, and monitoring.
    """

    def __init__(self, socket_manager: Optional[SocketManager] = None):
        self.status = EngineStatus.STOPPED
        self.socket_manager = socket_manager
        self.strategies: Dict[str, StrategyInstance] = {}
        self.metrics = EngineMetrics()
        self.running = False
        self._lock = threading.RLock()
        self._execution_thread: Optional[threading.Thread] = None
        self._market_data_cache: Dict[str, List[Dict]] = {}

        self.signal_generator = SignalGenerator()
        self.execution_engine = ExecutionEngine(socket_manager)
        self.strategy_manager = StrategyManager()
        self.risk_manager = RiskManager()
        self.position_manager = PositionManager()

        self._callbacks: Dict[str, List[Callable]] = {
            'on_signal': [],
            'on_trade': [],
            'on_error': [],
            'on_status_change': []
        }

        self._execution_interval = 5
        self._start_time: Optional[datetime] = None

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register event callbacks."""
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def _emit_event(self, event: str, data: Any) -> None:
        """Emit event to registered callbacks."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(data)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")

    async def start(self) -> bool:
        """Start the strategy engine."""
        with self._lock:
            if self.running:
                logger.warning("Engine already running")
                return True

            try:
                self.status = EngineStatus.STARTING
                logger.info("Starting Strategy Engine...")

                self.running = True
                self._start_time = datetime.utcnow()
                self.status = EngineStatus.RUNNING

                self._execution_thread = threading.Thread(
                    target=self._execution_loop,
                    daemon=True,
                    name="StrategyEngine-Execution"
                )
                self._execution_thread.start()

                await self._load_active_strategies()

                logger.info("Strategy Engine started successfully")
                self._emit_event('on_status_change', {'status': 'running'})
                return True

            except Exception as e:
                logger.error(f"Failed to start engine: {e}")
                self.status = EngineStatus.ERROR
                self.running = False
                return False

    async def stop(self) -> bool:
        """Stop the strategy engine."""
        with self._lock:
            if not self.running:
                return True

            try:
                logger.info("Stopping Strategy Engine...")
                self.running = False
                self.status = EngineStatus.STOPPED

                for strategy_id in list(self.strategies.keys()):
                    await self.stop_strategy(strategy_id)

                if self._execution_thread and self._execution_thread.is_alive():
                    self._execution_thread.join(timeout=5)

                self.status = EngineStatus.STOPPED
                logger.info("Strategy Engine stopped")
                self._emit_event('on_status_change', {'status': 'stopped'})
                return True

            except Exception as e:
                logger.error(f"Error stopping engine: {e}")
                return False

    async def _load_active_strategies(self) -> None:
        """Load active strategies from database."""
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
                instance = StrategyInstance(
                    strategy_id=strategy_id,
                    user_id=strategy.get('user_id', ''),
                    name=strategy.get('strategy_name', 'Unnamed'),
                    symbol=strategy.get('symbol', ''),
                    exchange=strategy.get('exchange', 'NSE'),
                    timeframe=strategy.get('timeframe', '1m'),
                    mode=strategy.get('mode', 'paper'),
                    config=strategy,
                    status=StrategyStatus.PAUSED
                )
                self.strategies[strategy_id] = instance

            logger.info(f"Loaded {len(active_strategies)} active strategies")

        except Exception as e:
            logger.error(f"Failed to load active strategies: {e}")

    def _execution_loop(self) -> None:
        """Main execution loop running strategies."""
        while self.running:
            try:
                loop_start = time.time()

                for strategy_id, instance in list(self.strategies.items()):
                    if instance.status == StrategyStatus.RUNNING:
                        asyncio.run(self._execute_strategy(instance))

                elapsed = time.time() - loop_start
                sleep_time = max(0, self._execution_interval - elapsed)
                time.sleep(sleep_time)

            except Exception as e:
                logger.error(f"Execution loop error: {e}")
                self.metrics.errors_count += 1
                time.sleep(5)

    async def _execute_strategy(self, instance: StrategyInstance) -> None:
        """Execute a single strategy iteration."""
        try:
            candles = await self._get_market_data(instance.symbol, instance.timeframe)
            if not candles or len(candles) < 50:
                return

            signal = await self.signal_generator.generate(
                instance.config,
                candles,
                instance.symbol
            )

            if signal:
                instance.last_signal_time = datetime.utcnow()
                self.metrics.signals_generated += 1

                await self._process_signal(instance, signal, candles)

                self._emit_event('on_signal', {
                    'strategy_id': instance.strategy_id,
                    'signal': signal
                })

                if self.socket_manager:
                    self.socket_manager.emit_to_user(
                        instance.user_id,
                        'strategy_signal',
                        {
                            'strategy_id': instance.strategy_id,
                            'strategy_name': instance.name,
                            'signal': signal
                        }
                    )

        except Exception as e:
            logger.error(f"Strategy execution error {instance.strategy_id}: {e}")
            instance.status = StrategyStatus.ERROR

    async def _get_market_data(self, symbol: str, timeframe: str) -> List[Dict]:
        """Get market data for a symbol."""
        cache_key = f"{symbol}:{timeframe}"
        return self._market_data_cache.get(cache_key, [])

    def _update_market_data(self, symbol: str, timeframe: str, candles: List[Dict]) -> None:
        """Update market data cache."""
        cache_key = f"{symbol}:{timeframe}"
        self._market_data_cache[cache_key] = candles

    async def _process_signal(self, instance: StrategyInstance, signal: Dict, candles: List[Dict]) -> None:
        """Process a trading signal."""
        if not signal or signal.get('action') == 'HOLD':
            return

        risk_check = await self.risk_manager.check_signal(
            instance.user_id,
            signal,
            instance.config.get('risk_settings', {})
        )

        if not risk_check['allowed']:
            logger.warning(f"Signal rejected by risk manager: {risk_check['reason']}")
            return

        if instance.mode == 'paper':
            trade = await self.execution_engine.execute_paper_trade(
                instance.strategy_id,
                instance.user_id,
                signal,
                instance.config.get('risk_settings', {})
            )
        else:
            trade = await self.execution_engine.execute_live_trade(
                instance.strategy_id,
                instance.user_id,
                signal,
                instance.config.get('execution_settings', {})
            )

        if trade:
            instance.trades_count += 1
            self.metrics.signals_executed += 1

            self._emit_event('on_trade', trade)

            if self.socket_manager:
                self.socket_manager.emit_to_user(
                    instance.user_id,
                    'strategy_trade',
                    {
                        'strategy_id': instance.strategy_id,
                        'trade': trade
                    }
                )

    async def start_strategy(self, strategy_id: str) -> bool:
        """Start a specific strategy."""
        with self._lock:
            if strategy_id in self.strategies:
                self.strategies[strategy_id].status = StrategyStatus.RUNNING
                self.strategies[strategy_id].started_at = datetime.utcnow()
                self.metrics.active_strategies += 1
                logger.info(f"Strategy {strategy_id} started")
                return True

            return False

    async def stop_strategy(self, strategy_id: str) -> bool:
        """Stop a specific strategy."""
        with self._lock:
            if strategy_id in self.strategies:
                self.strategies[strategy_id].status = StrategyStatus.STOPPED
                self.metrics.active_strategies = max(0, self.metrics.active_strategies - 1)
                logger.info(f"Strategy {strategy_id} stopped")
                return True
            return False

    async def pause_strategy(self, strategy_id: str) -> bool:
        """Pause a specific strategy."""
        with self._lock:
            if strategy_id in self.strategies:
                self.strategies[strategy_id].status = StrategyStatus.PAUSED
                logger.info(f"Strategy {strategy_id} paused")
                return True
            return False

    async def add_strategy(self, strategy_config: Dict) -> str:
        """Add a new strategy to the engine."""
        strategy_id = str(ObjectId())

        instance = StrategyInstance(
            strategy_id=strategy_id,
            user_id=strategy_config.get('user_id', ''),
            name=strategy_config.get('strategy_name', 'Unnamed'),
            symbol=strategy_config.get('symbol', ''),
            exchange=strategy_config.get('exchange', 'NSE'),
            timeframe=strategy_config.get('timeframe', '1m'),
            mode=strategy_config.get('mode', 'paper'),
            config=strategy_config,
            status=StrategyStatus.CREATED
        )

        with self._lock:
            self.strategies[strategy_id] = instance
            self.metrics.total_strategies += 1

        logger.info(f"Strategy added: {strategy_id}")
        return strategy_id

    def remove_strategy(self, strategy_id: str) -> bool:
        """Remove a strategy from the engine."""
        with self._lock:
            if strategy_id in self.strategies:
                instance = self.strategies[strategy_id]
                if instance.status == StrategyStatus.RUNNING:
                    self.metrics.active_strategies -= 1

                del self.strategies[strategy_id]
                logger.info(f"Strategy removed: {strategy_id}")
                return True
        return False

    def get_strategy_status(self, strategy_id: str) -> Optional[Dict]:
        """Get status of a strategy."""
        if strategy_id in self.strategies:
            instance = self.strategies[strategy_id]
            return {
                'strategy_id': instance.strategy_id,
                'name': instance.name,
                'status': instance.status.value,
                'symbol': instance.symbol,
                'timeframe': instance.timeframe,
                'trades_count': instance.trades_count,
                'last_signal_time': instance.last_signal_time.isoformat() if instance.last_signal_time else None
            }
        return None

    def get_all_strategies(self) -> List[Dict]:
        """Get all strategy statuses."""
        return [self.get_strategy_status(sid) for sid in self.strategies.keys()]

    def get_metrics(self) -> Dict:
        """Get engine metrics."""
        if self._start_time:
            self.metrics.uptime_seconds = (datetime.utcnow() - self._start_time).total_seconds()

        return {
            'status': self.status.value,
            'total_strategies': self.metrics.total_strategies,
            'active_strategies': self.metrics.active_strategies,
            'signals_generated': self.metrics.signals_generated,
            'signals_executed': self.metrics.signals_executed,
            'total_pnl': self.metrics.total_pnl,
            'uptime_seconds': self.metrics.uptime_seconds,
            'errors_count': self.metrics.errors_count
        }

    def update_market_feed(self, symbol: str, timeframe: str, candles: List[Dict]) -> None:
        """Update market data feed for strategies."""
        self._update_market_data(symbol, timeframe, candles)


_engine_instance: Optional[StrategyEngine] = None


def get_strategy_engine() -> StrategyEngine:
    """Get the global strategy engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = StrategyEngine()
    return _engine_instance


def initialize_engine(socket_manager: Optional[SocketManager] = None) -> StrategyEngine:
    """Initialize the strategy engine with dependencies."""
    global _engine_instance
    _engine_instance = StrategyEngine(socket_manager)
    return _engine_instance
"""
Tick Ingestion Pipeline
=======================
High-throughput tick ingestion with parallel processing stages.
"""

import logging
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import threading

from .normalization import TickNormalizer, get_tick_normalizer
from .deduplication import TickDeduplicator, get_tick_deduplicator
from ..core.models import Tick, Exchange

logger = logging.getLogger('market_data.ingestion')


class PipelineStage(str, Enum):
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    DEDUPLICATED = "DEDUPLICATED"
    VALIDATED = "VALIDATED"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"


class PipelineStatus(str, Enum):
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    ERROR = "ERROR"


@dataclass
class PipelineConfig:
    max_queue_size: int = 10000
    worker_count: int = 4
    enable_normalization: bool = True
    enable_deduplication: bool = True
    enable_validation: bool = True
    batch_size: int = 100
    flush_interval_ms: int = 100


@dataclass
class PipelineMetrics:
    stage: PipelineStage
    timestamp: datetime
    ticks_processed: int = 0
    processing_time_ms: float = 0.0
    queue_depth: int = 0


@dataclass
class IngestionResult:
    success: bool
    tick: Optional[Tick] = None
    stage_reached: PipelineStage = PipelineStage.RECEIVED
    error: Optional[str] = None
    processing_time_ms: float = 0.0


class TickIngestionPipeline:
    """
    High-throughput tick ingestion pipeline with:
    - Parallel normalization
    - Deduplication
    - Quality validation
    - Batch processing
    - Backpressure handling
    """

    def __init__(
        self,
        config: Optional[PipelineConfig] = None,
        normalizer: Optional[TickNormalizer] = None,
        deduplicator: Optional[TickDeduplicator] = None,
    ):
        self.config = config or PipelineConfig()
        self._normalizer = normalizer or get_tick_normalizer()
        self._deduplicator = deduplicator or get_tick_deduplicator()

        self._status = PipelineStatus.STOPPED

        self._input_queue: deque = deque(maxlen=self.config.max_queue_size)
        self._output_queue: deque = deque(maxlen=self.config.max_queue_size)

        self._batch_buffer: List[Tick] = []
        self._last_flush = time.perf_counter()

        self._worker_tasks: List[asyncio.Task] = []
        self._executor = ThreadPoolExecutor(max_workers=self.config.worker_count)

        self._callbacks: Dict[PipelineStage, List[Callable]] = {
            stage: [] for stage in PipelineStage
        }

        self._metrics_history: deque = deque(maxlen=1000)
        self._current_metrics = {
            PipelineStage.RECEIVED: 0,
            PipelineStage.NORMALIZED: 0,
            PipelineStage.DEDUPLICATED: 0,
            PipelineStage.VALIDATED: 0,
            PipelineStage.PUBLISHED: 0,
            PipelineStage.FAILED: 0,
        }

        self._lock = threading.Lock()
        self._processing = False

    def register_callback(self, stage: PipelineStage, callback: Callable[[Tick], None]) -> None:
        self._callbacks[stage].append(callback)

    def start(self) -> None:
        if self._status == PipelineStatus.RUNNING:
            return

        self._status = PipelineStatus.RUNNING
        self._processing = True

        for _ in range(self.config.worker_count):
            task = asyncio.create_task(self._worker_loop())
            self._worker_tasks.append(task)

        logger.info(f"Tick ingestion pipeline started with {self.config.worker_count} workers")

    def stop(self) -> None:
        self._status = PipelineStatus.STOPPED
        self._processing = False

        for task in self._worker_tasks:
            task.cancel()

        self._worker_tasks.clear()
        logger.info("Tick ingestion pipeline stopped")

    def pause(self) -> None:
        self._status = PipelineStatus.PAUSED

    def resume(self) -> None:
        self._status = PipelineStatus.RUNNING

    async def ingest(self, raw_data: Dict[str, Any], source: str = "simulated") -> IngestionResult:
        start_time = time.perf_counter()

        try:
            self._current_metrics[PipelineStage.RECEIVED] += 1
            self._input_queue.append((raw_data, source))

            self._trigger_callbacks(PipelineStage.RECEIVED, None)

            return IngestionResult(
                success=True,
                stage_reached=PipelineStage.RECEIVED,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Ingestion error: {e}")
            self._current_metrics[PipelineStage.FAILED] += 1

            return IngestionResult(
                success=False,
                stage_reached=PipelineStage.FAILED,
                error=str(e),
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    async def ingest_batch(self, raw_data_list: List[Dict[str, Any]], source: str = "simulated") -> List[IngestionResult]:
        results = []
        for raw_data in raw_data_list:
            result = await self.ingest(raw_data, source)
            results.append(result)
        return results

    async def _worker_loop(self) -> None:
        while self._processing and self._status == PipelineStatus.RUNNING:
            try:
                await self._process_batch()
                await asyncio.sleep(0.001)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker error: {e}")

    async def _process_batch(self) -> None:
        batch = []
        current_time = time.perf_counter()
        time_since_flush = (current_time - self._last_flush) * 1000

        while len(batch) < self.config.batch_size and self._input_queue:
            try:
                item = self._input_queue.popleft()
                batch.append(item)
            except IndexError:
                break

        if not batch:
            return

        if time_since_flush >= self.config.flush_interval_ms:
            await self._flush_output()
            self._last_flush = current_time

        for raw_data, source in batch:
            result = await self._process_single(raw_data, source)
            if result.success and result.tick:
                self._output_queue.append(result.tick)

    async def _process_single(self, raw_data: Dict[str, Any], source: str) -> IngestionResult:
        start_time = time.perf_counter()

        try:
            if self.config.enable_normalization:
                norm_result = self._normalizer.normalize(raw_data, source)
                self._current_metrics[PipelineStage.NORMALIZED] += 1
                self._trigger_callbacks(PipelineStage.NORMALIZED, None)

                if norm_result.status.value != "SUCCESS" or not norm_result.tick:
                    return IngestionResult(
                        success=False,
                        stage_reached=PipelineStage.NORMALIZED,
                        error=norm_result.error,
                        processing_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

                tick = norm_result.tick
            else:
                tick = self._create_tick_from_raw(raw_data)

            if self.config.enable_deduplication:
                dedup_result = self._deduplicator.check_and_add(tick)
                self._current_metrics[PipelineStage.DEDUPLICATED] += 1

                if dedup_result.is_duplicate:
                    return IngestionResult(
                        success=True,
                        tick=tick,
                        stage_reached=PipelineStage.DEDUPLICATED,
                        processing_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

            if self.config.enable_validation:
                if not self._validate_tick(tick):
                    self._current_metrics[PipelineStage.FAILED] += 1
                    return IngestionResult(
                        success=False,
                        stage_reached=PipelineStage.VALIDATED,
                        error="Validation failed",
                        processing_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

                self._current_metrics[PipelineStage.VALIDATED] += 1

            self._current_metrics[PipelineStage.PUBLISHED] += 1

            return IngestionResult(
                success=True,
                tick=tick,
                stage_reached=PipelineStage.PUBLISHED,
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Processing error: {e}")
            return IngestionResult(
                success=False,
                stage_reached=PipelineStage.FAILED,
                error=str(e),
                processing_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _create_tick_from_raw(self, raw_data: Dict[str, Any]) -> Tick:
        return Tick(
            symbol=raw_data.get("symbol", ""),
            exchange=Exchange(raw_data.get("exchange", "NSE").upper()),
            timestamp=datetime.now(timezone.utc),
            last_price=float(raw_data.get("last_price", 0)),
            last_quantity=int(raw_data.get("last_quantity", 0)),
            volume=int(raw_data.get("volume", 0)),
            open=float(raw_data.get("open", 0)),
            high=float(raw_data.get("high", 0)),
            low=float(raw_data.get("low", 0)),
            close=float(raw_data.get("prev_close", 0)),
            source=raw_data.get("source", "UNKNOWN"),
        )

    def _validate_tick(self, tick: Tick) -> bool:
        if not tick.symbol:
            return False
        if tick.last_price <= 0:
            return False
        if tick.high < tick.low:
            return False
        if tick.high < tick.last_price or tick.low > tick.last_price:
            pass
        return True

    def _trigger_callbacks(self, stage: PipelineStage, tick: Optional[Tick]) -> None:
        for callback in self._callbacks[stage]:
            try:
                if tick:
                    callback(tick)
                else:
                    callback()
            except Exception as e:
                logger.warning(f"Callback error for stage {stage}: {e}")

    async def _flush_output(self) -> None:
        for tick in self._output_queue:
            self._trigger_callbacks(PipelineStage.PUBLISHED, tick)

        self._output_queue.clear()

    def get_output_tick(self) -> Optional[Tick]:
        try:
            return self._output_queue.popleft()
        except IndexError:
            return None

    def get_output_ticks(self, count: int = 100) -> List[Tick]:
        ticks = []
        for _ in range(min(count, len(self._output_queue))):
            tick = self.get_output_tick()
            if tick:
                ticks.append(tick)
        return ticks

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "status": self._status.value,
            "input_queue_size": len(self._input_queue),
            "output_queue_size": len(self._output_queue),
            "stage_metrics": self._current_metrics.copy(),
            "config": {
                "worker_count": self.config.worker_count,
                "batch_size": self.config.batch_size,
                "max_queue_size": self.config.max_queue_size,
            },
        }

    @property
    def status(self) -> PipelineStatus:
        return self._status

    @property
    def input_queue_size(self) -> int:
        return len(self._input_queue)

    @property
    def output_queue_size(self) -> int:
        return len(self._output_queue)


_pipeline: Optional[TickIngestionPipeline] = None


def get_ingestion_pipeline() -> TickIngestionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TickIngestionPipeline()
    return _pipeline
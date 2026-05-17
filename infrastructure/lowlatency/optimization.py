"""
Low Latency Optimization Module
===============================
Performance optimizations targeting <5ms internal processing latency.

Key optimizations:
- orjson for fast JSON serialization
- Redis connection pooling and pipeline batching
- Async batching for database writes
- Object pooling for reducing allocations
- WebSocket message batching
"""

import logging
import time
import asyncio
import json
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from collections import deque
from contextlib import asynccontextmanager
import threading
import weakref
import sys

logger = logging.getLogger('lowlatency')


try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    ORJSON_AVAILABLE = False
    logger.warning("orjson not installed. Install for 3-5x faster JSON: pip install orjson")


@dataclass
class LatencyMetrics:
    """Latency tracking metrics."""
    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float('inf')
    max_ms: float = 0.0
    p50_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    _values: List[float] = field(default_factory=list)

    def record(self, latency_ms: float):
        self.count += 1
        self.total_ms += latency_ms
        self.min_ms = min(self.min_ms, latency_ms)
        self.max_ms = max(self.max_ms, latency_ms)
        self._values.append(latency_ms)

        if len(self._values) > 10000:
            self._values = self._values[-5000:]

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0

    def calculate_percentiles(self):
        if not self._values:
            return
        sorted_vals = sorted(self._values)
        self.p50_ms = sorted_vals[int(len(sorted_vals) * 0.50)]
        self.p95_ms = sorted_vals[int(len(sorted_vals) * 0.95)]
        self.p99_ms = sorted_vals[int(len(sorted_vals) * 0.99)]

    def to_dict(self) -> Dict:
        self.calculate_percentiles()
        return {
            'count': self.count,
            'avg_ms': round(self.avg_ms, 3),
            'min_ms': round(self.min_ms, 3),
            'max_ms': round(self.max_ms, 3),
            'p50_ms': round(self.p50_ms, 3),
            'p95_ms': round(self.p95_ms, 3),
            'p99_ms': round(self.p99_ms, 3)
        }


class FastJSONSerializer:
    """
    Fast JSON serialization using orjson when available.
    Falls back to standard json for compatibility.
    """

    @staticmethod
    def dumps(obj: Any) -> bytes:
        """Serialize object to JSON bytes."""
        if ORJSON_AVAILABLE:
            return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY)
        return json.dumps(obj).encode('utf-8')

    @staticmethod
    def dumps_str(obj: Any) -> str:
        """Serialize object to JSON string."""
        if ORJSON_AVAILABLE:
            return orjson.dumps(obj, option=orjson.OPT_SERIALIZE_NUMPY).decode('utf-8')
        return json.dumps(obj)

    @staticmethod
    def loads(data: bytes) -> Any:
        """Deserialize JSON bytes to object."""
        if ORJSON_AVAILABLE:
            return orjson.loads(data)
        return json.loads(data.decode('utf-8'))


class ObjectPool:
    """
    Pre-allocated object pool to reduce GC pressure.
    """

    def __init__(self, factory: Callable, initial_size: int = 100):
        self._factory = factory
        self._pool: List = []
        self._lock = threading.Lock()
        self._stats = {'acquired': 0, 'released': 0}

        for _ in range(initial_size):
            self._pool.append(factory())

    def acquire(self):
        """Acquire an object from the pool."""
        with self._lock:
            if self._pool:
                self._stats['acquired'] += 1
                return self._pool.pop()
        self._stats['acquired'] += 1
        return self._factory()

    def release(self, obj):
        """Return an object to the pool."""
        with self._lock:
            if len(self._pool) < 1000:
                self._stats['released'] += 1
                self._pool.append(obj)

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            'pool_size': len(self._pool)
        }


@dataclass
class BatchItem:
    """Item for batch processing."""
    key: str
    data: Any
    callback: Optional[Callable] = None


class AsyncBatcher:
    """
    Async batcher for aggregating operations.
    Reduces DB roundtrips by batching multiple operations.
    """

    def __init__(
        self,
        max_batch_size: int = 100,
        max_wait_ms: int = 5,
        batch_handler: Callable[[List[BatchItem]], Any] = None
    ):
        self._max_batch_size = max_batch_size
        self._max_wait_ms = max_wait_ms
        self._batch_handler = batch_handler

        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: Optional[asyncio.Task] = None

        self._metrics = LatencyMetrics()

    async def start(self):
        """Start the batch processor."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._process_loop())
        logger.info("AsyncBatcher started")

    async def stop(self):
        """Stop the batch processor."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("AsyncBatcher stopped")

    async def add(self, key: str, data: Any, callback: Optional[Callable] = None):
        """Add an item to the batch."""
        await self._queue.put(BatchItem(key, data, callback))

    async def _process_loop(self):
        """Process batches."""
        while self._running:
            try:
                batch = await self._collect_batch()

                if batch:
                    start = time.perf_counter()
                    try:
                        if asyncio.iscoroutinefunction(self._batch_handler):
                            await self._batch_handler(batch)
                        else:
                            self._batch_handler(batch)
                    except Exception as e:
                        logger.error(f"Batch handler error: {e}")

                    latency_ms = (time.perf_counter() - start) * 1000
                    self._metrics.record(latency_ms)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Batch processing error: {e}")

    async def _collect_batch(self) -> List[BatchItem]:
        """Collect items for a batch."""
        batch = []
        deadline = time.perf_counter() + (self._max_wait_ms / 1000)

        try:
            item = await asyncio.wait_for(self._queue.get(), timeout=0.001)
            batch.append(item)
        except asyncio.TimeoutError:
            return batch

        while len(batch) < self._max_batch_size:
            remaining = deadline - time.perf_counter()
            if remaining <= 0:
                break

            try:
                item = await asyncio.wait_for(self._queue.get(), timeout=min(remaining, 0.001))
                batch.append(item)
            except asyncio.TimeoutError:
                break

        return batch

    def get_metrics(self) -> Dict:
        return self._metrics.to_dict()


class RedisPool:
    """
    Optimized Redis connection pool with pipeline support.
    """

    def __init__(self, redis_url: str, pool_size: int = 50):
        self._redis_url = redis_url
        self._pool_size = pool_size
        self._pool: Optional[Any] = None
        self._client = None

        self._init_pool()

    def _init_pool(self):
        """Initialize Redis connection pool."""
        try:
            import redis
            self._pool = redis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._pool_size,
                decode_responses=False,
                socket_keepalive=True,
                socket_connect_timeout=5
            )
            self._client = redis.Redis(connection_pool=self._pool)
            logger.info(f"Redis pool initialized: {self._pool_size} connections")
        except ImportError:
            logger.error("redis-py not installed")
            self._client = None

    def get_client(self):
        """Get a Redis client from the pool."""
        return redis.Redis(connection_pool=self._pool) if self._pool else None

    @asynccontextmanager
    async def pipeline(self):
        """Execute Redis commands in a pipeline."""
        if not self._pool:
            raise RuntimeError("Redis pool not initialized")

        client = self.get_client()
        pipe = client.pipeline()

        try:
            yield pipe
            pipe.execute()
        finally:
            pipe.reset()
            client.close()

    def get_stats(self) -> Dict:
        if self._pool:
            return {
                'max_connections': self._pool.max_connections,
                'connection_class': str(type(self._pool.connection_class))
            }
        return {}


class WebSocketBatcher:
    """
    Batches WebSocket messages for reduced network overhead.
    Target: <20ms end-to-end latency.
    """

    def __init__(
        self,
        flush_interval_ms: int = 5,
        max_batch_size: int = 50,
        max_latency_ms: int = 10
    ):
        self._flush_interval_ms = flush_interval_ms
        self._max_batch_size = max_batch_size
        self._max_latency_ms = max_latency_ms

        self._buffers: Dict[str, List] = defaultdict(list)
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start the WebSocket batcher."""
        self._running = True
        self._task = asyncio.create_task(self._flush_loop())
        logger.info("WebSocketBatcher started")

    async def stop(self):
        """Stop the batcher and flush remaining messages."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        async with self._lock:
            for room, messages in self._buffers.items():
                if messages:
                    await self._send_batch(room, messages)
        logger.info("WebSocketBatcher stopped")

    async def add_message(self, room: str, event: str, data: Any):
        """Add a message to the batch buffer."""
        async with self._lock:
            self._buffers[room].append({'event': event, 'data': data, 'timestamp': time.time()})

            if len(self._buffers[room]) >= self._max_batch_size:
                messages = self._buffers[room]
                self._buffers[room] = []
                await self._send_batch(room, messages)

    async def _flush_loop(self):
        """Periodically flush buffers."""
        while self._running:
            try:
                await asyncio.sleep(self._flush_interval_ms / 1000)

                async with self._lock:
                    for room, messages in list(self._buffers.items()):
                        if not messages:
                            continue

                        oldest = messages[0]['timestamp']
                        age_ms = (time.time() - oldest) * 1000

                        if age_ms >= self._max_latency_ms or len(messages) >= self._max_batch_size:
                            await self._send_batch(room, messages)
                            self._buffers[room] = []

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"WebSocket batcher error: {e}")

    async def _send_batch(self, room: str, messages: List[Dict]):
        """Send a batch of messages. Override in implementation."""
        pass


class LatencyTracker:
    """
    Tracks latency across the system.
    """

    def __init__(self):
        self._trackers: Dict[str, LatencyMetrics] = {}
        self._lock = threading.Lock()

    def track(self, operation: str, latency_ms: float):
        """Track latency for an operation."""
        with self._lock:
            if operation not in self._trackers:
                self._trackers[operation] = LatencyMetrics()
            self._trackers[operation].record(latency_ms)

    def get_metrics(self, operation: str) -> Optional[Dict]:
        with self._lock:
            tracker = self._trackers.get(operation)
            return tracker.to_dict() if tracker else None

    def get_all_metrics(self) -> Dict[str, Dict]:
        with self._lock:
            return {op: tracker.to_dict() for op, tracker in self._trackers.items()}


class TickProcessor:
    """
    Optimized tick processor targeting <2ms tick processing latency.
    """

    def __init__(self):
        self._last_prices: Dict[str, float] = {}
        self._last_volumes: Dict[str, int] = {}
        self._tick_handlers: List[Callable] = []
        self._metrics = LatencyMetrics()

    def register_handler(self, handler: Callable):
        self._tick_handlers.append(handler)

    def process_tick(self, tick: Dict) -> Dict:
        """Process a tick with sub-millisecond latency."""
        start = time.perf_counter()

        symbol = tick.get('symbol')
        if not symbol:
            return {}

        processed = {
            'symbol': symbol,
            'last_price': tick.get('last_price', 0),
            'bid': tick.get('bid_price', 0),
            'ask': tick.get('ask_price', 0),
            'volume': tick.get('volume', 0),
            'timestamp': tick.get('timestamp', 0),
            'change': 0,
            'change_percent': 0,
            'vwap': 0
        }

        if symbol in self._last_prices:
            prev_price = self._last_prices[symbol]
            current_price = processed['last_price']
            processed['change'] = current_price - prev_price
            processed['change_percent'] = (processed['change'] / prev_price * 100) if prev_price > 0 else 0

        self._last_prices[symbol] = processed['last_price']
        self._last_volumes[symbol] = processed['volume']

        volume = processed['volume']
        prev_volume = self._last_volumes.get(symbol, 0)
        if volume > prev_volume and prev_volume > 0:
            turnover = processed['last_price'] * (volume - prev_volume)
            processed['vwap'] = processed['last_price']

        for handler in self._tick_handlers:
            try:
                handler(processed)
            except Exception as e:
                logger.error(f"Tick handler error: {e}")

        latency_ms = (time.perf_counter() - start) * 1000
        self._metrics.record(latency_ms)

        return processed

    def get_metrics(self) -> Dict:
        return self._metrics.to_dict()


_global_latency_tracker: Optional[LatencyTracker] = None
_tick_processor: Optional[TickProcessor] = None


def get_latency_tracker() -> LatencyTracker:
    """Get global latency tracker."""
    global _global_latency_tracker
    if _global_latency_tracker is None:
        _global_latency_tracker = LatencyTracker()
    return _global_latency_tracker


def get_tick_processor() -> TickProcessor:
    """Get global tick processor."""
    global _tick_processor
    if _tick_processor is None:
        _tick_processor = TickProcessor()
    return _tick_processor


def create_optimized_json_serializer() -> FastJSONSerializer:
    """Create optimized JSON serializer."""
    return FastJSONSerializer()
"""
Event Batching System
======================
High-performance event batching for reducing WebSocket overhead.
Batches multiple events together to minimize network round-trips.
"""

import os
import logging
import time
import asyncio
import threading
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum
import json
import zlib

logger = logging.getLogger(__name__)


class CompressionLevel(Enum):
    NONE = 0
    FAST = 1
    BALANCED = 6
    MAXIMUM = 9


@dataclass
class BatchedEvent:
    """Single event for batching."""
    event: str
    data: Dict
    timestamp: float
    priority: int = 0
    namespace: str = "/"


@dataclass
class Batch:
    """Batch of events."""
    events: List[BatchedEvent]
    created_at: float
    target_sids: List[str] = field(default_factory=list)
    target_room: Optional[str] = None
    compression: CompressionLevel = CompressionLevel.NONE


class EventBatcher:
    """
    Batches WebSocket events for efficient delivery.
    Reduces network overhead by combining multiple events.
    """

    def __init__(
        self,
        batch_interval: float = 0.05,
        max_batch_size: int = 50,
        max_queue_size: int = 10000,
        compression_enabled: bool = False,
        compression_threshold: int = 500
    ):
        self.batch_interval = batch_interval
        self.max_batch_size = max_batch_size
        self.max_queue_size = max_queue_size
        self.compression_enabled = compression_enabled
        self.compression_threshold = compression_threshold
        self.compression_level = CompressionLevel.BALANCED

        self._queues: Dict[str, List[BatchedEvent]] = defaultdict(list)
        self._lock = threading.Lock()
        self._flush_interval = batch_interval
        self._running = False
        self._worker_thread: Optional[threading.Thread] = None

        self._batch_callback: Optional[Callable] = None
        self._event_counts: Dict[str, int] = defaultdict(int)
        self._dropped_events: int = 0

    def set_batch_callback(self, callback: Callable):
        """Set callback for batch delivery."""
        self._batch_callback = callback

    def start(self):
        """Start the batcher."""
        if self._running:
            return
        self._running = True
        self._worker_thread = threading.Thread(target=self._flush_loop, daemon=True)
        self._worker_thread.start()
        logger.info("Event batcher started")

    def stop(self):
        """Stop the batcher."""
        self._running = False
        if self._worker_thread:
            self._worker_thread.join(timeout=2)
        logger.info("Event batcher stopped")

    def add_event(
        self,
        event: str,
        data: Dict,
        target_sids: List[str] = None,
        target_room: str = None,
        priority: int = 0
    ):
        """Add event to batch queue."""
        batched_event = BatchedEvent(
            event=event,
            data=data,
            timestamp=time.time(),
            priority=priority
        )

        queue_key = self._get_queue_key(target_sids, target_room)

        with self._lock:
            if len(self._queues[queue_key]) >= self.max_queue_size:
                self._dropped_events += 1
                logger.warning(f"Queue full, dropping event: {event}")
                return

            self._queues[queue_key].append(batched_event)
            self._event_counts[event] += 1

            if len(self._queues[queue_key]) >= self.max_batch_size:
                self._flush_queue(queue_key)

    def _get_queue_key(self, sids: List[str] = None, room: str = None) -> str:
        """Generate queue key from targets."""
        if room:
            return f"room:{room}"
        elif sids:
            return f"sids:{','.join(sorted(sids[:3]))}"
        return "broadcast"

    def _flush_queue(self, queue_key: str):
        """Flush a specific queue."""
        with self._lock:
            events = self._queues.pop(queue_key, [])
            if not events:
                return

        self._deliver_batch(queue_key, events)

    def _flush_loop(self):
        """Periodic flush loop."""
        while self._running:
            time.sleep(self._flush_interval)

            with self._lock:
                queue_keys = list(self._queues.keys())

            for key in queue_keys:
                self._flush_queue(key)

    def _deliver_batch(self, queue_key: str, events: List[BatchedEvent]):
        """Deliver batched events."""
        if not events or not self._batch_callback:
            return

        batch_data = self._prepare_batch_data(events)

        if self.compression_enabled and len(batch_data) > self.compression_threshold:
            batch_data = self._compress(batch_data)

        self._batch_callback(queue_key, batch_data)

    def _prepare_batch_data(self, events: List[BatchedEvent]) -> Dict:
        """Prepare batch data for delivery."""
        return {
            'batch': True,
            'count': len(events),
            'timestamp': time.time(),
            'events': [
                {
                    'event': e.event,
                    'data': e.data,
                    'ts': e.timestamp,
                    'priority': e.priority
                }
                for e in sorted(events, key=lambda x: x.priority, reverse=True)
            ]
        }

    def _compress(self, data: Dict) -> Dict:
        """Compress batch data."""
        try:
            json_str = json.dumps(data)
            compressed = zlib.compress(
                json_str.encode('utf-8'),
                level=self.compression_level.value
            )
            return {
                'compressed': True,
                'data': compressed.hex(),
                'original_size': len(json_str),
                'compressed_size': len(compressed)
            }
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            return data

    def get_stats(self) -> Dict:
        """Get batcher statistics."""
        with self._lock:
            return {
                'queue_count': len(self._queues),
                'total_queued': sum(len(q) for q in self._queues.values()),
                'event_counts': dict(self._event_counts),
                'dropped_events': self._dropped_events,
                'running': self._running
            }


class AdaptiveBatcher(EventBatcher):
    """
    Adaptive batching that adjusts intervals based on load.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_throughput = 0
        self._target_latency_ms = kwargs.get('target_latency_ms', 20)
        self._min_interval = 0.01
        self._max_interval = 0.2
        self._adjustment_factor = 0.1

    def _adjust_interval(self):
        """Adjust batch interval based on throughput."""
        current_throughput = sum(self._event_counts.values())

        if current_throughput > 0:
            if current_throughput > self._last_throughput * 1.5:
                self._flush_interval = max(self._min_interval, self._flush_interval * (1 - self._adjustment_factor))
            elif current_throughput < self._last_throughput * 0.5:
                self._flush_interval = min(self._max_interval, self._flush_interval * (1 + self._adjustment_factor))

        self._last_throughput = current_throughput


class StreamBatcher:
    """
    Specialized batcher for high-frequency streaming data (market data).
    Uses time-window batching for tick data.
    """

    def __init__(
        self,
        window_ms: int = 100,
        max_events_per_window: int = 100,
        flush_callback: Callable = None
    ):
        self.window_ms = window_ms / 1000.0
        self.max_events_per_window = max_events_per_window
        self.flush_callback = flush_callback

        self._symbol_buffers: Dict[str, List[Dict]] = defaultdict(list)
        self._lock = threading.Lock()
        self._running = False
        self._worker: Optional[threading.Thread] = None
        self._last_flush: Dict[str, float] = defaultdict(float)

    def start(self):
        """Start the stream batcher."""
        if self._running:
            return
        self._running = True
        self._worker = threading.Thread(target=self._window_loop, daemon=True)
        self._worker.start()
        logger.info("Stream batcher started")

    def stop(self):
        """Stop the stream batcher."""
        self._running = False
        if self._worker:
            self._worker.join(timeout=2)

    def add_market_tick(self, symbol: str, tick_data: Dict):
        """Add market tick to buffer."""
        with self._lock:
            buffer = self._symbol_buffers[symbol]
            buffer.append({
                **tick_data,
                'received_at': time.time()
            })

            if len(buffer) >= self.max_events_per_window:
                self._flush_symbol(symbol)

    def _window_loop(self):
        """Window-based flush loop."""
        while self._running:
            time.sleep(self.window_ms / 2)

            with self._lock:
                symbols = list(self._symbol_buffers.keys())

            for symbol in symbols:
                self._maybe_flush(symbol)

    def _maybe_flush(self, symbol: str):
        """Check if symbol buffer should be flushed."""
        with self._lock:
            buffer = self._symbol_buffers.get(symbol, [])
            if not buffer:
                return

            now = time.time()
            if now - self._last_flush[symbol] >= self.window_ms:
                self._flush_symbol(symbol)

    def _flush_symbol(self, symbol: str):
        """Flush symbol buffer."""
        with self._lock:
            buffer = self._symbol_buffers.pop(symbol, [])
            if not buffer:
                return
            self._last_flush[symbol] = time.time()

        if self.flush_callback:
            self.flush_callback(symbol, buffer)

    def get_buffer_stats(self) -> Dict:
        """Get buffer statistics."""
        with self._lock:
            return {
                'symbols_tracked': len(self._symbol_buffers),
                'total_buffered': sum(len(b) for b in self._symbol_buffers.values()),
                'per_symbol': {s: len(b) for s, b in self._symbol_buffers.items()}
            }


_global_batcher: Optional[EventBatcher] = None
_global_stream_batcher: Optional[StreamBatcher] = None


def get_event_batcher() -> EventBatcher:
    """Get global event batcher."""
    global _global_batcher
    if _global_batcher is None:
        _global_batcher = EventBatcher()
        _global_batcher.start()
    return _global_batcher


def get_stream_batcher() -> StreamBatcher:
    """Get global stream batcher."""
    global _global_stream_batcher
    if _global_stream_batcher is None:
        _global_stream_batcher = StreamBatcher()
        _global_stream_batcher.start()
    return _global_stream_batcher
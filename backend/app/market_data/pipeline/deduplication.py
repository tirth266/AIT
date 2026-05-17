"""
Tick Deduplication
===================
Ensures each tick is processed exactly once using sliding window + bloom filter.
"""

import logging
import time
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from collections import OrderedDict
import hashlib
import threading

from ..core.models import Tick, TickStats

logger = logging.getLogger('market_data.deduplication')


@dataclass
class DeduplicationResult:
    is_duplicate: bool
    tick: Optional[Tick]
    deduplication_time_ms: float = 0.0


class TickDeduplicator:
    """
    High-performance tick deduplication using sliding window + probabilistic filtering.
    """

    def __init__(
        self,
        window_seconds: int = 300,
        max_ticks_in_memory: int = 100000,
        enable_bloom_filter: bool = True,
    ):
        self._window_seconds = window_seconds
        self._max_ticks = max_ticks_in_memory

        self._recent_ticks: OrderedDict[str, datetime] = OrderedDict()
        self._tick_stats: Dict[str, TickStats] = {}

        self._bloom_filter: Optional[BloomFilter] = None
        if enable_bloom_filter:
            self._bloom_filter = BloomFilter(max_items=max_ticks_in_memory)

        self._lock = threading.RLock()

        self._stats = {
            "total_checked": 0,
            "duplicates_found": 0,
            "unique_ticks": 0,
        }

    def check_and_add(self, tick: Tick) -> DeduplicationResult:
        start_time = time.perf_counter()

        key = self._generate_key(tick)

        with self._lock:
            self._stats["total_checked"] += 1

            if key in self._recent_ticks:
                self._stats["duplicates_found"] += 1
                self._update_tick_stats(tick.symbol, tick.exchange, duplicate=True)

                return DeduplicationResult(
                    is_duplicate=True,
                    tick=tick,
                    deduplication_time_ms=(time.perf_counter() - start_time) * 1000,
                )

            if self._bloom_filter and self._bloom_filter.might_contain(key):
                if key in self._recent_ticks:
                    self._stats["duplicates_found"] += 1
                    return DeduplicationResult(
                        is_duplicate=True,
                        tick=tick,
                        deduplication_time_ms=(time.perf_counter() - start_time) * 1000,
                    )

            self._recent_ticks[key] = tick.timestamp

            if self._bloom_filter:
                self._bloom_filter.add(key)

            self._cleanup_old_ticks()

            self._stats["unique_ticks"] += 1
            self._update_tick_stats(tick.symbol, tick.exchange, duplicate=False)

            return DeduplicationResult(
                is_duplicate=False,
                tick=tick,
                deduplication_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _generate_key(self, tick: Tick) -> str:
        if tick.sequence_number > 0:
            return f"{tick.symbol}:{tick.exchange.value}:{tick.sequence_number}"
        return f"{tick.symbol}:{tick.exchange.value}:{tick.timestamp.timestamp()}"

    def _cleanup_old_ticks(self) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=self._window_seconds)

        while self._recent_ticks:
            _, timestamp = next(iter(self._recent_ticks.items()))
            if timestamp < cutoff:
                self._recent_ticks.popitem(last=False)
            else:
                break

        while len(self._recent_ticks) > self._max_ticks:
            self._recent_ticks.popitem(last=False)

    def _update_tick_stats(
        self,
        symbol: str,
        exchange: str,
        duplicate: bool = False,
    ) -> None:
        key = f"{symbol}:{exchange}"

        if key not in self._tick_stats:
            self._tick_stats[key] = TickStats(
                symbol=symbol,
                exchange=exchange,
            )

        stats = self._tick_stats[key]
        stats.ticks_received += 1

        if duplicate:
            stats.ticks_deduplicated += 1
        else:
            stats.last_tick_time = datetime.now(timezone.utc)

    def is_duplicate(self, tick: Tick) -> bool:
        key = self._generate_key(tick)
        with self._lock:
            return key in self._recent_ticks

    def get_stats(self, symbol: Optional[str] = None) -> Dict:
        with self._lock:
            if symbol:
                key = f"{symbol}:NSE"
                return {
                    "symbol": symbol,
                    "ticks_received": self._tick_stats.get(key, TickStats(symbol=symbol, exchange=exchange)).ticks_received,
                    "ticks_deduplicated": self._tick_stats.get(key, TickStats(symbol=symbol, exchange=exchange)).ticks_deduplicated,
                    "ticks_invalid": self._tick_stats.get(key, TickStats(symbol=symbol, exchange=exchange)).ticks_invalid,
                }

            return {
                "total_checked": self._stats["total_checked"],
                "duplicates_found": self._stats["duplicates_found"],
                "unique_ticks": self._stats["unique_ticks"],
                "cache_size": len(self._recent_ticks),
                "bloom_filter_size": self._bloom_filter.size if self._bloom_filter else 0,
            }

    def reset(self) -> None:
        with self._lock:
            self._recent_ticks.clear()
            if self._bloom_filter:
                self._bloom_filter.clear()
            self._tick_stats.clear()
            self._stats = {
                "total_checked": 0,
                "duplicates_found": 0,
                "unique_ticks": 0,
            }


class BloomFilter:
    """
    Space-efficient probabilistic filter for duplicate detection.
    """

    def __init__(self, max_items: int, error_rate: float = 0.01):
        self._size = self._optimal_size(max_items, error_rate)
        self._hash_count = self._optimal_hash_count(self._size, max_items)
        self._bit_array = bytearray((self._size + 7) // 8)

    @staticmethod
    def _optimal_size(n: int, p: float) -> int:
        import math
        return int(-n * math.log(p) / (math.log(2) ** 2))

    @staticmethod
    def _optimal_hash_count(m: int, n: int) -> int:
        import math
        return int((m / n) * math.log(2))

    def _hashes(self, item: str) -> tuple:
        result = []
        h = hashlib.md5(item.encode()).digest()

        for i in range(self._hash_count):
            hi = int.from_bytes(h, 'big')
            result.append((hi + i * h) % self._size)

        return tuple(result)

    def add(self, item: str) -> None:
        for h in self._hashes(item):
            self._bit_array[h // 8] |= 1 << (h % 8)

    def might_contain(self, item: str) -> bool:
        for h in self._hashes(item):
            if not (self._bit_array[h // 8] & (1 << (h % 8))):
                return False
        return True

    def clear(self) -> None:
        self._bit_array = bytearray((self._size + 7) // 8)

    @property
    def size(self) -> int:
        return self._size


class AsyncTickDeduplicator:
    """
    Async wrapper for tick deduplicator.
    """

    def __init__(self, deduplicator: Optional[TickDeduplicator] = None):
        self._deduplicator = deduplicator or TickDeduplicator()
        self._lock = asyncio.Lock()

    async def check_and_add(self, tick: Tick) -> DeduplicationResult:
        async with self._lock:
            return self._deduplicator.check_and_add(tick)

    def get_stats(self) -> Dict:
        return self._deduplicator.get_stats()


_deduplicator: Optional[TickDeduplicator] = None


def get_tick_deduplicator() -> TickDeduplicator:
    global _deduplicator
    if _deduplicator is None:
        _deduplicator = TickDeduplicator()
    return _deduplicator
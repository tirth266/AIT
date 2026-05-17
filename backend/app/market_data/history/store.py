"""
Historical Data Storage
=======================
Efficient tick and candle storage with time-series optimization.
"""

import logging
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import threading
import os
import struct

from ..core.models import Tick, Candle, Exchange, CandleInterval

logger = logging.getLogger('market_data.history')


class StorageFormat(str, Enum):
    JSON = "JSON"
    BINARY = "BINARY"
    PARQUET = "PARQUET"


@dataclass
class StorageConfig:
    data_dir: str = "./market_data"
    tick_retention_days: int = 30
    candle_retention_days: int = 365
    compression_enabled: bool = True
    use_binary_format: bool = True
    flush_interval_seconds: int = 60
    max_file_size_mb: int = 100


class HistoricalDataStore:
    """
    Time-series storage for ticks and candles with automatic retention management.
    """

    def __init__(
        self,
        config: Optional[StorageConfig] = None,
    ):
        self.config = config or StorageConfig()

        self._tick_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=10000))
        self._candle_cache: Dict[str, deque] = defaultdict(lambda: deque(maxlen=5000))

        self._stats = {
            "ticks_stored": 0,
            "candles_stored": 0,
            "reads": 0,
            "writes": 0,
            "errors": 0,
        }

        self._lock = threading.RLock()

        os.makedirs(self.config.data_dir, exist_ok=True)

    def store_tick(self, tick: Tick) -> bool:
        try:
            with self._lock:
                key = f"{tick.symbol}:{tick.exchange.value}"
                self._tick_cache[key].append(tick)

                self._stats["ticks_stored"] += 1
                self._stats["writes"] += 1

            return True

        except Exception as e:
            logger.error(f"Store tick error: {e}")
            self._stats["errors"] += 1
            return False

    def store_ticks(self, ticks: List[Tick]) -> int:
        stored = 0
        for tick in ticks:
            if self.store_tick(tick):
                stored += 1
        return stored

    def store_candle(self, candle: Candle) -> bool:
        try:
            with self._lock:
                key = f"{candle.symbol}:{candle.exchange.value}:{candle.interval.value}"
                self._candle_cache[key].append(candle)

                self._stats["candles_stored"] += 1
                self._stats["writes"] += 1

            return True

        except Exception as e:
            logger.error(f"Store candle error: {e}")
            self._stats["errors"] += 1
            return False

    def get_ticks(
        self,
        symbol: str,
        exchange: Exchange,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Tick]:
        with self._lock:
            key = f"{symbol}:{exchange.value}"
            ticks = list(self._tick_cache.get(key, []))

            if start_time:
                ticks = [t for t in ticks if t.timestamp >= start_time]

            if end_time:
                ticks = [t for t in ticks if t.timestamp <= end_time]

            self._stats["reads"] += 1

            return ticks[-limit:]

    def get_candles(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[Candle]:
        with self._lock:
            key = f"{symbol}:{exchange.value}:{interval.value}"
            candles = list(self._candle_cache.get(key, []))

            if start_time:
                candles = [c for c in candles if c.timestamp >= start_time]

            if end_time:
                candles = [c for c in candles if c.timestamp <= end_time]

            self._stats["reads"] += 1

            return candles[-limit:]

    def get_latest_tick(
        self,
        symbol: str,
        exchange: Exchange,
    ) -> Optional[Tick]:
        with self._lock:
            key = f"{symbol}:{exchange.value}"
            ticks = self._tick_cache.get(key)

            if ticks:
                return ticks[-1]

        return None

    def get_latest_candle(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
    ) -> Optional[Candle]:
        with self._lock:
            key = f"{symbol}:{exchange.value}:{interval.value}"
            candles = self._candle_cache.get(key)

            if candles:
                return candles[-1]

        return None

    def get_tick_range(
        self,
        symbol: str,
        exchange: Exchange,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        ticks = self.get_ticks(symbol, exchange, start_time, end_time, limit=100000)
        return len(ticks)

    def get_candle_range(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        candles = self.get_candles(symbol, exchange, interval, start_time, end_time, limit=100000)
        return len(candles)

    def export_to_file(
        self,
        symbol: str,
        exchange: Exchange,
        start_time: datetime,
        end_time: datetime,
        format: StorageFormat = StorageFormat.JSON,
    ) -> str:
        filename = f"{symbol}_{exchange.value}_{start_time.strftime('%Y%m%d')}_{end_time.strftime('%Y%m%d')}"

        if format == StorageFormat.JSON:
            return self._export_json(symbol, exchange, start_time, end_time, filename)
        elif format == StorageFormat.BINARY:
            return self._export_binary(symbol, exchange, start_time, end_time, filename)

        return ""

    def _export_json(
        self,
        symbol: str,
        exchange: Exchange,
        start_time: datetime,
        end_time: datetime,
        filename: str,
    ) -> str:
        ticks = self.get_ticks(symbol, exchange, start_time, end_time, limit=100000)

        filepath = os.path.join(self.config.data_dir, f"{filename}.json")

        with open(filepath, "w") as f:
            json.dump([t.to_dict() for t in ticks], f)

        return filepath

    def _export_binary(
        self,
        symbol: str,
        exchange: Exchange,
        start_time: datetime,
        end_time: datetime,
        filename: str,
    ) -> str:
        ticks = self.get_ticks(symbol, exchange, start_time, end_time, limit=100000)

        filepath = os.path.join(self.config.data_dir, f"{filename}.bin")

        with open(filepath, "wb") as f:
            for tick in ticks:
                f.write(tick.to_binary())

        return filepath

    def cleanup_old_data(self) -> Dict[str, int]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=self.config.tick_retention_days)

        cleaned_ticks = 0
        cleaned_candles = 0

        with self._lock:
            for key, ticks in self._tick_cache.items():
                original_len = len(ticks)
                while ticks and ticks[0].timestamp < cutoff:
                    ticks.popleft()
                cleaned_ticks += original_len - len(ticks)

            cutoff_candle = now - timedelta(days=self.config.candle_retention_days)
            for key, candles in self._candle_cache.items():
                original_len = len(candles)
                while candles and candles[0].timestamp < cutoff_candle:
                    candles.popleft()
                cleaned_candles += original_len - len(candles)

        return {
            "ticks_cleaned": cleaned_ticks,
            "candles_cleaned": cleaned_candles,
        }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ticks_stored": self._stats["ticks_stored"],
                "candles_stored": self._stats["candles_stored"],
                "reads": self._stats["reads"],
                "writes": self._stats["writes"],
                "errors": self._stats["errors"],
                "unique_symbols": len(self._tick_cache),
                "unique_candle_keys": len(self._candle_cache),
                "memory_ticks": sum(len(v) for v in self._tick_cache.values()),
                "memory_candles": sum(len(v) for v in self._candle_cache.values()),
            }


_store: Optional[HistoricalDataStore] = None


def get_historical_store() -> HistoricalDataStore:
    global _store
    if _store is None:
        _store = HistoricalDataStore()
    return _store
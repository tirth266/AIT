"""
Real-time Candle Aggregation
==============================
Aggregates ticks into OHLCV candles with multiple timeframe support.
"""

import logging
import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from collections import defaultdict
import threading

from ..core.models import Candle, Tick, Exchange, CandleInterval

logger = logging.getLogger('market_data.candles')


@dataclass
class CandleConfig:
    intervals: List[CandleInterval] = None
    enable_vwap: bool = True
    enable_oi_tracking: bool = True
    flush_interval_seconds: int = 1

    def __post_init__(self):
        if self.intervals is None:
            self.intervals = [
                CandleInterval.MINUTE_1,
                CandleInterval.MINUTE_5,
                CandleInterval.MINUTE_15,
                CandleInterval.MINUTE_30,
                CandleInterval.HOUR_1,
                CandleInterval.DAY_1,
            ]


@dataclass
class CandleKey:
    symbol: str
    exchange: Exchange
    interval: CandleInterval

    def to_string(self) -> str:
        return f"{self.symbol}:{self.exchange.value}:{self.interval.value}"

    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
            "interval": self.interval.value,
        }


class OHLCVCalculator:
    """
    Accumulates ticks into OHLCV candles.
    """

    def __init__(self):
        self._current_candle: Optional[Candle] = None
        self._tick_count = 0
        self._total_volume = 0
        self._vwap_sum = 0.0

    def update(self, tick: Tick) -> Optional[Candle]:
        if not self._current_candle:
            return None

        self._tick_count += 1
        self._total_volume += tick.last_quantity
        self._vwap_sum += tick.last_price * tick.last_quantity

        self._current_candle.close = tick.last_price
        self._current_candle.volume += tick.last_quantity

        if tick.last_price > self._current_candle.high:
            self._current_candle.high = tick.last_price
        if tick.last_price < self._current_candle.low or self._current_candle.low == 0:
            self._current_candle.low = tick.last_price

        if tick.oi > 0:
            self._current_candle.oi = tick.oi

        self._current_candle.tick_count = self._tick_count

        if self._total_volume > 0:
            self._current_candle.vwap = self._vwap_sum / self._total_volume

        self._current_candle.trades += 1

        return self._current_candle

    def start_new_candle(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
        timestamp: datetime,
    ) -> Candle:
        self._current_candle = Candle(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            timestamp=self._get_candle_start_time(timestamp, interval),
            open=tick.last_price if (tick := self.get_current_tick()) else 0,
            high=tick.last_price if tick else 0,
            low=tick.last_price if tick else 0,
            close=0,
            volume=0,
            vwap=0,
            oi=0,
            trades=0,
            tick_count=0,
        )
        self._tick_count = 0
        self._total_volume = 0
        self._vwap_sum = 0.0

        return self._current_candle

    def get_current_tick(self) -> Optional[Tick]:
        return None

    @staticmethod
    def _get_candle_start_time(timestamp: datetime, interval: CandleInterval) -> datetime:
        ts = timestamp.timestamp()
        seconds = interval.seconds

        if seconds == 0:
            return timestamp.replace(microsecond=0)

        start_ts = (ts // seconds) * seconds
        return datetime.fromtimestamp(start_ts, tz=timezone.utc)

    def get_current_candle(self) -> Optional[Candle]:
        return self._current_candle

    def is_candle_closed(self, current_time: datetime, interval: CandleInterval) -> bool:
        if not self._current_candle:
            return True

        candle_end_ts = self._current_candle.timestamp.timestamp() + interval.seconds
        return current_time.timestamp() >= candle_end_ts


class CandleAggregator:
    """
    Real-time multi-timeframe candle aggregator.
    """

    def __init__(
        self,
        config: Optional[CandleConfig] = None,
    ):
        self.config = config or CandleConfig()

        self._calculators: Dict[CandleKey, OHLCVCalculator] = {}
        self._completed_candles: Dict[CandleKey, List[Candle]] = defaultdict(list)

        self._callbacks: Dict[CandleInterval, List[Callable]] = defaultdict(list)
        self._symbol_callbacks: Dict[str, List[Callable]] = defaultdict(list)

        self._stats = {
            "ticks_processed": 0,
            "candles_generated": 0,
            "intervals_tracked": 0,
        }

        self._lock = threading.RLock()

    def register_interval_callback(
        self,
        interval: CandleInterval,
        callback: Callable[[Candle], None],
    ) -> None:
        self._callbacks[interval].append(callback)

    def register_symbol_callback(
        self,
        symbol: str,
        callback: Callable[[Dict], None],
    ) -> None:
        self._symbol_callbacks[symbol.upper()].append(callback)

    def process_tick(self, tick: Tick) -> List[Candle]:
        completed_candles = []

        with self._lock:
            self._stats["ticks_processed"] += 1

            for interval in self.config.intervals:
                key = CandleKey(tick.symbol, tick.exchange, interval)

                if key not in self._calculators:
                    self._calculators[key] = OHLCVCalculator()
                    self._calculators[key].start_new_candle(
                        tick.symbol, tick.exchange, interval, tick.timestamp
                    )
                    self._stats["intervals_tracked"] += 1

                calculator = self._calculators[key]

                if calculator.is_candle_closed(tick.timestamp, interval):
                    completed = calculator.get_current_candle()
                    if completed:
                        completed_candles.append(completed)
                        self._completed_candles[key].append(completed)

                        if len(self._completed_candles[key]) > 100:
                            self._completed_candles[key] = self._completed_candles[key][-100:]

                    calculator.start_new_candle(tick.symbol, tick.exchange, interval, tick.timestamp)

                calculator.update(tick)

        for candle in completed_candles:
            self._trigger_callbacks(candle)

        return completed_candles

    def _trigger_callbacks(self, candle: Candle) -> None:
        self._stats["candles_generated"] += 1

        for callback in self._callbacks.get(candle.interval, []):
            try:
                callback(candle)
            except Exception as e:
                logger.warning(f"Candle callback error: {e}")

        for callback in self._symbol_callbacks.get(candle.symbol, []):
            try:
                callback(candle.to_dict())
            except Exception as e:
                logger.warning(f"Symbol callback error: {e}")

    def get_current_candle(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
    ) -> Optional[Candle]:
        key = CandleKey(symbol, exchange, interval)
        if key in self._calculators:
            return self._calculators[key].get_current_candle()
        return None

    def get_completed_candles(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
        count: int = 100,
    ) -> List[Candle]:
        key = CandleKey(symbol, exchange, interval)
        candles = self._completed_candles.get(key, [])
        return candles[-count:]

    def get_historical_candle(
        self,
        symbol: str,
        exchange: Exchange,
        interval: CandleInterval,
        timestamp: datetime,
    ) -> Optional[Candle]:
        key = CandleKey(symbol, exchange, interval)
        candles = self._completed_candles.get(key, [])

        target_start = self._get_candle_start_time(timestamp, interval)

        for candle in candles:
            if candle.timestamp == target_start:
                return candle

        return None

    @staticmethod
    def _get_candle_start_time(timestamp: datetime, interval: CandleInterval) -> datetime:
        ts = timestamp.timestamp()
        seconds = interval.seconds

        if seconds == 0:
            return timestamp.replace(microsecond=0)

        start_ts = (ts // seconds) * seconds
        return datetime.fromtimestamp(start_ts, tz=timezone.utc)

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "ticks_processed": self._stats["ticks_processed"],
                "candles_generated": self._stats["candles_generated"],
                "intervals_tracked": self._stats["intervals_tracked"],
                "unique_keys": len(self._calculators),
                "intervals": [i.value for i in self.config.intervals],
            }

    def reset(self) -> None:
        with self._lock:
            self._calculators.clear()
            self._completed_candles.clear()
            self._stats = {
                "ticks_processed": 0,
                "candles_generated": 0,
                "intervals_tracked": 0,
            }


_aggregator: Optional[CandleAggregator] = None


def get_candle_aggregator() -> CandleAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = CandleAggregator()
    return _aggregator
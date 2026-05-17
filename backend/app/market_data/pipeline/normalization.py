"""
Tick Normalization
===================
Transforms raw exchange ticks into standardized internal format.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import hashlib

from ..core.models import Tick, Exchange
from ..core.types import InstrumentType

logger = logging.getLogger('market_data.normalization')


class NormalizationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


@dataclass
class NormalizationResult:
    status: NormalizationStatus
    tick: Optional[Tick] = None
    error: Optional[str] = None
    transformation_time_ms: float = 0.0


class TickNormalizer:
    """
    Normalizes ticks from various sources into a standardized format.
    """

    def __init__(self):
        self._symbol_cache: Dict[str, Dict] = {}
        self._normalization_rules: Dict[str, Callable] = {}
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
        }

        self._register_default_rules()

    def _register_default_rules(self) -> None:
        self._normalization_rules["zerodha"] = self._normalize_zerodha_tick
        self._normalization_rules["upstox"] = self._normalize_upstox_tick
        self._normalization_rules["simulated"] = self._normalize_simulated_tick

    def register_rule(self, source: str, handler: Callable) -> None:
        self._normalization_rules[source.lower()] = handler

    def normalize(self, raw_data: Dict[str, Any], source: str = "simulated") -> NormalizationResult:
        import time
        start_time = time.perf_counter()

        try:
            handler = self._normalization_rules.get(source.lower())

            if handler:
                tick = handler(raw_data)
            else:
                tick = self._normalize_generic_tick(raw_data)

            if tick:
                self._stats["successful"] += 1
                self._stats["total_processed"] += 1

                return NormalizationResult(
                    status=NormalizationStatus.SUCCESS,
                    tick=tick,
                    transformation_time_ms=(time.perf_counter() - start_time) * 1000,
                )

            self._stats["skipped"] += 1
            self._stats["total_processed"] += 1

            return NormalizationResult(
                status=NormalizationStatus.SKIPPED,
                error="No handler available",
                transformation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Normalization failed: {e}")
            self._stats["failed"] += 1
            self._stats["total_processed"] += 1

            return NormalizationResult(
                status=NormalizationStatus.FAILED,
                error=str(e),
                transformation_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def _normalize_zerodha_tick(self, raw_data: Dict) -> Optional[Tick]:
        if not raw_data:
            return None

        instrument_token = raw_data.get("instrument_token", 0)
        timestamp = raw_data.get("last_trade_time")

        if isinstance(timestamp, (int, float)):
            tick_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, str):
            tick_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            tick_time = datetime.now(timezone.utc)

        last_price = float(raw_data.get("last_price", 0))
        prev_close = float(raw_data.get("close", 0))
        change = last_price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0

        return Tick(
            symbol=raw_data.get("tradingsymbol", ""),
            exchange=Exchange.NSE,
            timestamp=tick_time,
            last_price=last_price,
            last_quantity=int(raw_data.get("last_quantity", 0)),
            last_trade_time=tick_time,
            average_price=float(raw_data.get("average_price", 0)),
            volume=int(raw_data.get("volume", 0)),
            oi=int(raw_data.get("oi", 0)),
            oi_day_high=int(raw_data.get("oi_day_high", 0)),
            oi_day_low=int(raw_data.get("oi_day_low", 0)),
            open=float(raw_data.get("open", 0)),
            high=float(raw_data.get("high", 0)),
            low=float(raw_data.get("low", 0)),
            close=float(raw_data.get("close", 0)),
            vwap=float(raw_data.get("vwap", 0)),
            change=change,
            change_percent=change_percent,
            bid_price=float(raw_data.get("buy_qty", 0)),
            bid_quantity=int(raw_data.get("buy_qty", 0)),
            ask_price=float(raw_data.get("sell_qty", 0)),
            ask_quantity=int(raw_data.get("sell_qty", 0)),
            source="ZERODHA_KITE",
            sequence_number=instrument_token,
        )

    def _normalize_upstox_tick(self, raw_data: Dict) -> Optional[Tick]:
        if not raw_data:
            return None

        instrument_token = raw_data.get("instrument_token", 0)
        timestamp = raw_data.get("timestamp")

        if isinstance(timestamp, (int, float)):
            tick_time = datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc)
        else:
            tick_time = datetime.now(timezone.utc)

        last_price = float(raw_data.get("last_price", 0))
        prev_close = float(raw_data.get("previous_close", 0))
        change = last_price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0

        return Tick(
            symbol=raw_data.get("symbol", ""),
            exchange=Exchange.NSE,
            timestamp=tick_time,
            last_price=last_price,
            last_quantity=int(raw_data.get("last_quantity", 0)),
            last_trade_time=tick_time,
            average_price=float(raw_data.get("average_price", 0)),
            volume=int(raw_data.get("volume", 0)),
            open=float(raw_data.get("open", 0)),
            high=float(raw_data.get("high", 0)),
            low=float(raw_data.get("low", 0)),
            close=prev_close,
            change=change,
            change_percent=change_percent,
            source="UPSTOX",
            sequence_number=instrument_token,
        )

    def _normalize_simulated_tick(self, raw_data: Dict) -> Optional[Tick]:
        if not raw_data:
            return None

        symbol = raw_data.get("symbol", "")
        if not symbol:
            return None

        last_price = float(raw_data.get("last_price", 0))
        prev_close = float(raw_data.get("prev_close", 0))
        change = last_price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0

        timestamp_str = raw_data.get("timestamp")
        if timestamp_str:
            try:
                tick_time = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception:
                tick_time = datetime.now(timezone.utc)
        else:
            tick_time = datetime.now(timezone.utc)

        return Tick(
            symbol=symbol,
            exchange=Exchange.NSE,
            timestamp=tick_time,
            last_price=last_price,
            last_quantity=int(raw_data.get("last_quantity", 0)),
            last_trade_time=tick_time,
            volume=int(raw_data.get("volume", 0)),
            open=float(raw_data.get("open", 0)),
            high=float(raw_data.get("high", 0)),
            low=float(raw_data.get("low", 0)),
            close=prev_close,
            change=change,
            change_percent=change_percent,
            source="SIMULATED",
        )

    def _normalize_generic_tick(self, raw_data: Dict) -> Optional[Tick]:
        symbol = raw_data.get("symbol") or raw_data.get("tradingsymbol") or raw_data.get("scrip_code", "")
        if not symbol:
            return None

        last_price = float(raw_data.get("last_price", raw_data.get("ltp", 0)))
        prev_close = float(raw_data.get("prev_close", raw_data.get("close", raw_data.get("previous_close", 0))))
        change = last_price - prev_close
        change_percent = (change / prev_close * 100) if prev_close > 0 else 0

        timestamp = raw_data.get("timestamp") or raw_data.get("time")
        if isinstance(timestamp, (int, float)):
            tick_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        elif isinstance(timestamp, str):
            try:
                tick_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            except Exception:
                tick_time = datetime.now(timezone.utc)
        else:
            tick_time = datetime.now(timezone.utc)

        return Tick(
            symbol=str(symbol),
            exchange=Exchange(raw_data.get("exchange", "NSE").upper()),
            timestamp=tick_time,
            last_price=last_price,
            last_quantity=int(raw_data.get("last_quantity", raw_data.get("quantity", 0))),
            volume=int(raw_data.get("volume", 0)),
            open=float(raw_data.get("open", 0)),
            high=float(raw_data.get("high", 0)),
            low=float(raw_data.get("low", 0)),
            close=prev_close,
            change=change,
            change_percent=change_percent,
            source=raw_data.get("source", "UNKNOWN"),
        )

    def update_symbol_cache(self, symbol_info: Dict) -> None:
        symbol = symbol_info.get("symbol") or symbol_info.get("tradingsymbol")
        if symbol:
            self._symbol_cache[symbol.upper()] = symbol_info

    def get_symbol_info(self, symbol: str) -> Optional[Dict]:
        return self._symbol_cache.get(symbol.upper())

    def get_stats(self) -> Dict[str, Any]:
        success_rate = (self._stats["successful"] / max(self._stats["total_processed"], 1)) * 100
        return {
            "total_processed": self._stats["total_processed"],
            "successful": self._stats["successful"],
            "failed": self._stats["failed"],
            "skipped": self._stats["skipped"],
            "success_rate_percent": round(success_rate, 2),
        }

    def reset_stats(self) -> None:
        self._stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
        }


_normalizer: Optional[TickNormalizer] = None


def get_tick_normalizer() -> TickNormalizer:
    global _normalizer
    if _normalizer is None:
        _normalizer = TickNormalizer()
    return _normalizer
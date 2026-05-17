"""
Market Session Engine
=====================
Manages market open/close states and trading phases for Indian exchanges.
"""

import logging
import asyncio
from datetime import datetime, timezone, time, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
import pytz

from ..core.models import MarketStatus, Exchange

logger = logging.getLogger('market_data.session')


class MarketPhase(str, Enum):
    PRE_MARKET_OPEN = "PRE_MARKET_OPEN"
    PRE_MARKET_CLOSED = "PRE_MARKET_CLOSED"
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_CLOSE = "MARKET_CLOSE"
    POST_MARKET = "POST_MARKET"
    CLOSED = "CLOSED"
    HALTED = "HALTED"
    AUCTION = "AUCTION"


@dataclass
class SessionConfig:
    exchange: Exchange
    pre_market_start: time
    pre_market_end: time
    market_open: time
    market_close: time
    post_market_start: time
    post_market_end: time
    timezone: str = "Asia/Kolkata"


NSE_CONFIG = SessionConfig(
    exchange=Exchange.NSE,
    pre_market_start=time(9, 0),
    pre_market_end=time(9, 15),
    market_open=time(9, 15),
    market_close=time(15, 30),
    post_market_start=time(15, 30),
    post_market_end=time(16, 0),
)

BSE_CONFIG = SessionConfig(
    exchange=Exchange.BSE,
    pre_market_start=time(9, 0),
    pre_market_end=time(9, 15),
    market_open=time(9, 15),
    market_close=time(15, 30),
    post_market_start=time(15, 30),
    post_market_end=time(16, 0),
)

MCX_CONFIG = SessionConfig(
    exchange=Exchange.MCX,
    pre_market_start=time(9, 0),
    pre_market_end=time(9, 0),
    market_open=time(9, 0),
    market_close=time(23, 30),
    post_market_start=time(23, 30),
    post_market_end=time(23, 55),
)


class MarketSessionEngine:
    """
    Manages market session states for NSE/BSE/MCX with real-time phase detection.
    """

    def __init__(self):
        self._configs: Dict[Exchange, SessionConfig] = {
            Exchange.NSE: NSE_CONFIG,
            Exchange.BSE: BSE_CONFIG,
            Exchange.MCX: MCX_CONFIG,
        }

        self._current_sessions: Dict[Exchange, MarketPhase] = {}
        self._callbacks: Dict[MarketPhase, List[Callable]] = defaultdict(list)
        self._last_phase_change: Dict[Exchange, datetime] = {}

        self._tz = pytz.timezone("Asia/Kolkata")

        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None

        self._initialize_sessions()

    def _initialize_sessions(self) -> None:
        for exchange in Exchange:
            phase = self._get_current_phase(exchange)
            self._current_sessions[exchange] = phase
            self._last_phase_change[exchange] = datetime.now(timezone.utc)

    async def start_monitoring(self, interval_seconds: int = 5) -> None:
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval_seconds))
        logger.info("Market session monitoring started")

    async def stop_monitoring(self) -> None:
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
        logger.info("Market session monitoring stopped")

    async def _monitor_loop(self, interval: int) -> None:
        while self._running:
            try:
                for exchange in Exchange:
                    new_phase = self._get_current_phase(exchange)
                    old_phase = self._current_sessions.get(exchange)

                    if new_phase != old_phase:
                        self._current_sessions[exchange] = new_phase
                        self._last_phase_change[exchange] = datetime.now(timezone.utc)

                        logger.info(f"Market phase change {exchange.value}: {old_phase} -> {new_phase}")

                        await self._trigger_phase_callbacks(exchange, new_phase)

                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")

    async def _trigger_phase_callbacks(self, exchange: Exchange, phase: MarketPhase) -> None:
        for callback in self._callbacks.get(phase, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(exchange, phase)
                else:
                    callback(exchange, phase)
            except Exception as e:
                logger.warning(f"Phase callback error: {e}")

    def _get_current_phase(self, exchange: Exchange) -> MarketPhase:
        config = self._configs.get(exchange)
        if not config:
            return MarketPhase.CLOSED

        now = datetime.now(self._tz)
        current_time = now.time()
        current_date = now.date()

        if self._is_holiday(exchange, current_date):
            return MarketPhase.CLOSED

        if config.pre_market_start <= current_time < config.pre_market_end:
            return MarketPhase.PRE_MARKET_OPEN
        elif config.pre_market_end <= current_time < config.market_open:
            return MarketPhase.PRE_MARKET_CLOSED
        elif config.market_open <= current_time < config.market_close:
            return MarketPhase.MARKET_OPEN
        elif config.market_close <= current_time < config.post_market_end:
            return MarketPhase.POST_MARKET
        else:
            return MarketPhase.CLOSED

    def _is_holiday(self, exchange: Exchange, date) -> bool:
        weekday = date.weekday()
        if weekday >= 5:
            return True

        return False

    def register_phase_callback(self, phase: MarketPhase, callback: Callable) -> None:
        self._callbacks[phase].append(callback)

    def get_current_phase(self, exchange: Exchange = Exchange.NSE) -> MarketPhase:
        return self._current_sessions.get(exchange, MarketPhase.CLOSED)

    def is_market_open(self, exchange: Exchange = Exchange.NSE) -> bool:
        phase = self.get_current_phase(exchange)
        return phase in [MarketPhase.MARKET_OPEN, MarketPhase.PRE_MARKET_OPEN]

    def get_next_open_time(self, exchange: Exchange = Exchange.NSE) -> Optional[datetime]:
        config = self._configs.get(exchange)
        if not config:
            return None

        now = datetime.now(self._tz)
        current_time = now.time()

        if current_time < config.pre_market_start:
            next_open = now.replace(
                hour=config.pre_market_start.hour,
                minute=config.pre_market_start.minute,
                second=0,
            )
        elif current_time < config.market_open:
            next_open = now.replace(
                hour=config.market_open.hour,
                minute=config.market_open.minute,
                second=0,
            )
        else:
            next_day = now + timedelta(days=1)
            while next_day.weekday() >= 5 or self._is_holiday(exchange, next_day.date()):
                next_day += timedelta(days=1)

            next_open = next_day.replace(
                hour=config.pre_market_start.hour,
                minute=config.pre_market_start.minute,
                second=0,
            )

        return next_open.astimezone(timezone.utc)

    def get_next_close_time(self, exchange: Exchange = Exchange.NSE) -> Optional[datetime]:
        config = self._configs.get(exchange)
        if not config:
            return None

        now = datetime.now(self._tz)
        current_time = now.time()

        if current_time < config.market_close:
            close_time = config.market_close
        elif current_time < config.post_market_end:
            close_time = config.post_market_end
        else:
            return None

        return now.replace(
            hour=close_time.hour,
            minute=close_time.minute,
            second=0,
        ).astimezone(timezone.utc)

    def get_time_until_open(self, exchange: Exchange = Exchange.NSE) -> Optional[timedelta]:
        next_open = self.get_next_open_time(exchange)
        if not next_open:
            return None

        now = datetime.now(timezone.utc)
        delta = next_open - now

        if delta.total_seconds() < 0:
            return None

        return delta

    def get_session_duration(self, exchange: Exchange = Exchange.NSE) -> Optional[timedelta]:
        config = self._configs.get(exchange)
        if not config:
            return None

        open_time = datetime.combine(datetime.now().date(), config.market_open)
        close_time = datetime.combine(datetime.now().date(), config.market_close)

        return close_time - open_time

    def get_status(self) -> Dict[str, Any]:
        return {
            "sessions": {
                exchange.value: {
                    "phase": phase.value,
                    "last_change": self._last_phase_change.get(exchange, datetime.now(timezone.utc)).isoformat(),
                }
                for exchange, phase in self._current_sessions.items()
            },
            "next_open": {
                ex.value: self.get_next_open_time(ex).isoformat()
                for ex in Exchange
            },
        }


_session_engine: Optional[MarketSessionEngine] = None


def get_market_session_engine() -> MarketSessionEngine:
    global _session_engine
    if _session_engine is None:
        _session_engine = MarketSessionEngine()
    return _session_engine
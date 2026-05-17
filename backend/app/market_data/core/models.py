"""
Core Data Models
================
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
import struct
import hashlib


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NCDEX = "NCDEX"
    NFO = "NFO"
    CDS = "CDS"


class InstrumentType(str, Enum):
    EQUITY = "EQ"
    INDEX = "INDEX"
    FUTURES = "FUT"
    OPTIONS = "OPT"
    COMMODITY = "COM"
    CURRENCY = "CUR"


class CandleInterval(str, Enum):
    TICK = "TICK"
    SECOND_1 = "1S"
    SECOND_5 = "5S"
    MINUTE_1 = "1M"
    MINUTE_5 = "5M"
    MINUTE_15 = "15M"
    MINUTE_30 = "30M"
    HOUR_1 = "1H"
    DAY_1 = "1D"


class MarketStatus(str, Enum):
    PRE_MARKET = "PRE_MARKET"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    POST_MARKET = "POST_MARKET"
    HALTED = "HALTED"
    AUCTION = "AUCTION"


class CorporateActionType(str, Enum):
    SPLIT = "SPLIT"
    BONUS = "BONUS"
    RIGHTS = "RIGHTS"
    DIVIDEND = "DIVIDEND"
    MERGER = "MERGER"
    DELISTING = "DELISTING"
    NAME_CHANGE = "NAME_CHANGE"
    FACTOR_CHANGE = "FACTOR_CHANGE"


@dataclass
class Tick:
    symbol: str
    exchange: Exchange
    timestamp: datetime
    last_price: float = 0.0
    last_quantity: int = 0
    last_trade_time: Optional[datetime] = None
    average_price: float = 0.0
    volume: int = 0
    oi: int = 0
    oi_day_high: int = 0
    oi_day_low: int = 0
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    vwap: float = 0.0
    change: float = 0.0
    change_percent: float = 0.0
    bid_price: float = 0.0
    bid_quantity: int = 0
    ask_price: float = 0.0
    ask_quantity: int = 0
    tick_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sequence_number: int = 0
    source: str = "UNKNOWN"

    def to_binary(self) -> bytes:
        return struct.pack(
            '>qifqiqqqqfffffffqq',
            self.timestamp.timestamp(),
            self.sequence_number,
            self.last_price,
            self.last_quantity,
            self.last_trade_time.timestamp() if self.last_trade_time else 0,
            self.volume,
            self.oi,
            int(self.open * 10000),
            int(self.high * 10000),
            int(self.low * 10000),
            int(self.close * 10000),
            int(self.vwap * 10000),
            int(self.bid_price * 10000),
            self.bid_quantity,
            int(self.ask_price * 10000),
            self.ask_quantity,
            self.tick_id.encode()[:16].ljust(16, b'\x00'),
        )

    @classmethod
    def from_binary(cls, data: bytes) -> 'Tick':
        (
            ts, seq, lprice, lqty, ltt,
            vol, oi, opn, high, low, close, vwap,
            bidp, bidq, askp, askq, tick_id
        ) = struct.unpack('>qifqiqqqqfffffffqq', data)

        return cls(
            symbol="",
            exchange=Exchange.NSE,
            timestamp=datetime.fromtimestamp(ts, tz=timezone.utc),
            last_price=lprice,
            last_quantity=lqty,
            last_trade_time=datetime.fromtimestamp(ltt, tz=timezone.utc) if ltt else None,
            volume=vol,
            oi=oi,
            open=opn / 10000,
            high=high / 10000,
            low=low / 10000,
            close=close / 10000,
            vwap=vwap / 10000,
            bid_price=bidp / 10000,
            bid_quantity=bidq,
            ask_price=askp / 10000,
            ask_quantity=askq,
            tick_id=tick_id.to_bytes(16, 'big').hex()[:36],
            sequence_number=seq,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
            "timestamp": self.timestamp.isoformat(),
            "last_price": self.last_price,
            "last_quantity": self.last_quantity,
            "volume": self.volume,
            "oi": self.oi,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "change": self.change,
            "change_percent": self.change_percent,
        }

    def get_idempotency_key(self) -> str:
        return f"{self.symbol}:{self.exchange.value}:{self.sequence_number}"


@dataclass
class OrderBookLevel:
    price: float
    quantity: int
    orders: int = 0


@dataclass
class OrderBook:
    symbol: str
    exchange: Exchange
    timestamp: datetime
    bid_levels: List[OrderBookLevel] = field(default_factory=list)
    ask_levels: List[OrderBookLevel] = field(default_factory=list)
    total_bid_quantity: int = 0
    total_ask_quantity: int = 0
    spread: float = 0.0
    spread_percent: float = 0.0
    mid_price: float = 0.0
    depth: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
            "timestamp": self.timestamp.isoformat(),
            "bids": [{"price": b.price, "quantity": b.quantity} for b in self.bid_levels[:self.depth]],
            "asks": [{"price": a.price, "quantity": a.quantity} for a in self.ask_levels[:self.depth]],
            "spread": self.spread,
            "mid_price": self.mid_price,
            "total_bid_quantity": self.total_bid_quantity,
            "total_ask_quantity": self.total_ask_quantity,
        }


@dataclass
class Candle:
    symbol: str
    exchange: Exchange
    interval: CandleInterval
    timestamp: datetime
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: int = 0
    vwap: float = 0.0
    oi: int = 0
    trades: int = 0
    tick_count: int = 0

    def is_complete(self) -> bool:
        return self.volume > 0 and self.close > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
            "interval": self.interval.value,
            "timestamp": self.timestamp.isoformat(),
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "vwap": self.vwap,
            "oi": self.oi,
            "trades": self.trades,
        }


@dataclass
class SymbolMaster:
    symbol: str
    exchange: Exchange
    instrument_token: int
    tradingsymbol: str
    name: str
    instrument_type: InstrumentType
    lot_size: int
    tick_size: float
    expiry_date: Optional[datetime] = None
    strike_price: Optional[float] = None
    option_type: Optional[str] = None
    underlying_symbol: Optional[str] = None
    is_tradeable: bool = True
    is_listed: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange.value,
            "instrument_token": self.instrument_token,
            "tradingsymbol": self.tradingsymbol,
            "name": self.name,
            "instrument_type": self.instrument_type.value,
            "lot_size": self.lot_size,
            "tick_size": self.tick_size,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "strike_price": self.strike_price,
            "option_type": self.option_type,
            "underlying_symbol": self.underlying_symbol,
        }


@dataclass
class CorporateAction:
    symbol: str
    exchange: Exchange
    action_type: CorporateActionType
    announcement_date: datetime
    record_date: Optional[datetime] = None
    ex_date: Optional[datetime] = None
    execution_date: Optional[datetime] = None
    ratio: Optional[float] = None
    price: Optional[float] = None
    old_symbol: Optional[str] = None
    new_symbol: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class TradingSession:
    exchange: Exchange
    session_type: MarketStatus
    start_time: datetime
    end_time: datetime
    is_trading_day: bool = True


@dataclass
class DataQualityIssue:
    symbol: str
    exchange: Exchange
    issue_type: str
    severity: str
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TickStats:
    symbol: str
    exchange: Exchange
    ticks_received: int = 0
    ticks_deduplicated: int = 0
    ticks_invalid: int = 0
    avg_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    last_tick_time: Optional[datetime] = None
    last_update: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StreamMetadata:
    stream_name: str
    topic: str
    partition: int = 0
    offset: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
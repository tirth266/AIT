"""
Core Types for Market Data System
===================================
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional
from datetime import datetime


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
    DEBT = "DR"
    MF = "MF"
    GOVT = "GOVT"


class CandleInterval(str, Enum):
    TICK = "TICK"
    SECOND_1 = "1S"
    SECOND_5 = "5S"
    SECOND_15 = "15S"
    MINUTE_1 = "1M"
    MINUTE_3 = "3M"
    MINUTE_5 = "5M"
    MINUTE_15 = "15M"
    MINUTE_30 = "30M"
    HOUR_1 = "1H"
    HOUR_4 = "4H"
    DAY_1 = "1D"
    WEEK_1 = "1W"
    MONTH_1 = "1M"

    @property
    def seconds(self) -> int:
        if self == CandleInterval.TICK:
            return 0
        elif self == CandleInterval.SECOND_1:
            return 1
        elif self == CandleInterval.SECOND_5:
            return 5
        elif self == CandleInterval.SECOND_15:
            return 15
        elif self == CandleInterval.MINUTE_1:
            return 60
        elif self == CandleInterval.MINUTE_3:
            return 180
        elif self == CandleInterval.MINUTE_5:
            return 300
        elif self == CandleInterval.MINUTE_15:
            return 900
        elif self == CandleInterval.MINUTE_30:
            return 1800
        elif self == CandleInterval.HOUR_1:
            return 3600
        elif self == CandleInterval.HOUR_4:
            return 14400
        elif self == CandleInterval.DAY_1:
            return 86400
        elif self == CandleInterval.WEEK_1:
            return 604800
        elif self == CandleInterval.MONTH_1:
            return 2592000
        return 0

    def is_intraday(self) -> bool:
        return self not in [CandleInterval.DAY_1, CandleInterval.WEEK_1, CandleInterval.MONTH_1]


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "SL"
    STOP_LIMIT = "SL-M"


class TickSource(str, Enum):
    ZERODHA_KITE = "ZERODHA_KITE"
    UPSTOX = "UPSTOX"
    ANGEL_ONE = "ANGEL_ONE"
    FIVESTOCKS = "FIVESTOCKS"
    NASDAQ = "NASDAQ"
    SIMULATED = "SIMULATED"


@dataclass
class MarketConfig:
    exchange: Exchange
    instrument_type: InstrumentType
    lot_size: int = 1
    tick_size: float = 0.05
    min_quantity: int = 1
    max_quantity: int = 1000000
    allowed_order_types: list = None

    def __post_init__(self):
        if self.allowed_order_types is None:
            self.allowed_order_types = [OrderType.LIMIT, OrderType.MARKET]


EXCHANGE_CONFIG = {
    Exchange.NSE: MarketConfig(
        exchange=Exchange.NSE,
        instrument_type=InstrumentType.EQUITY,
        lot_size=1,
        tick_size=0.05,
    ),
    Exchange.BSE: MarketConfig(
        exchange=Exchange.BSE,
        instrument_type=InstrumentType.EQUITY,
        lot_size=1,
        tick_size=0.05,
    ),
    Exchange.NFO: MarketConfig(
        exchange=Exchange.NFO,
        instrument_type=InstrumentType.FUTURES,
        tick_size=0.05,
    ),
    Exchange.MCX: MarketConfig(
        exchange=Exchange.MCX,
        instrument_type=InstrumentType.COMMODITY,
        tick_size=0.05,
    ),
}
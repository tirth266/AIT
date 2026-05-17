"""
Data Models for Zerodha Kite Connect
====================================
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
import uuid


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"
    MCX = "MCX"
    NCDEX = "NCDEX"


class ProductType(str, Enum):
    CNC = "CNC"
    MIS = "MIS"
    NRML = "NRML"
    CO = "CO"
    BO = "BO"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    SL = "SL"
    SL_M = "SL-M"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    OPEN = "OPEN"
    COMPLETE = "COMPLETE"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    TRIGGER_PENDING = "TRIGGER PENDING"


class VALIDITY(str, Enum):
    DAY = "DAY"
    IOC = "IOC"
    GTT = "GTT"


@dataclass
class OrderParams:
    symbol: str
    exchange: Exchange
    transaction_type: TransactionType
    quantity: int
    product: ProductType
    order_type: OrderType = OrderType.LIMIT
    price: float = 0.0
    trigger_price: float = 0.0
    validity: VALIDITY = VALIDITY.DAY
    disclosed_quantity: int = 0
    squareoff: float = 0.0
    stoploss: float = 0.0
    trailing_stoploss: float = 0.0
    tag: Optional[str] = None

    def to_zerodha_params(self) -> Dict[str, Any]:
        params = {
            "exchange": self.exchange.value,
            "transaction_type": self.transaction_type.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "product": self.product.value,
            "validity": self.validity.value,
        }

        if self.order_type in [OrderType.LIMIT, OrderType.SL]:
            if self.price > 0:
                params["price"] = self.price

        if self.order_type in [OrderType.SL, OrderType.SL_M]:
            if self.trigger_price > 0:
                params["trigger_price"] = self.trigger_price

        if self.disclosed_quantity > 0:
            params["disclosed_quantity"] = self.disclosed_quantity

        if self.tag:
            params["tag"] = self.tag

        return params


@dataclass
class ZerodhaOrder:
    order_id: str
    internal_order_id: str
    symbol: str
    exchange: str
    transaction_type: str
    quantity: int
    filled_quantity: int = 0
    pending_quantity: int = 0
    price: float = 0.0
    trigger_price: float = 0.0
    order_type: str = "LIMIT"
    product: str = "MIS"
    status: str = "OPEN"
    validity: str = "DAY"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    exchange_order_id: Optional[str] = None
    placed_by: Optional[str] = None
    variety: str = "regular"
    tradingsymbol: Optional[str] = None
    instrument_token: Optional[int] = None
    average_price: float = 0.0
    cancelled_quantity: int = 0
    market_protection: float = 0.0
    after_market_order: bool = False
    _raw_data: Optional[Dict] = field(default_factory=dict)
    idempotency_key: Optional[str] = None
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None

    @classmethod
    def from_zerodha_response(
        cls,
        data: Dict[str, Any],
        internal_order_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> "ZerodhaOrder":
        internal_id = internal_order_id or str(uuid.uuid4())

        return cls(
            order_id=data.get("order_id", ""),
            internal_order_id=internal_id,
            symbol=data.get("tradingsymbol", ""),
            exchange=data.get("exchange", ""),
            transaction_type=data.get("transaction_type", ""),
            quantity=data.get("quantity", 0),
            filled_quantity=data.get("filled_quantity", 0),
            pending_quantity=data.get("pending_quantity", 0),
            price=data.get("price", 0.0),
            trigger_price=data.get("trigger_price", 0.0),
            order_type=data.get("order_type", "LIMIT"),
            product=data.get("product", "MIS"),
            status=data.get("status", "OPEN"),
            validity=data.get("validity", "DAY"),
            created_at=cls._parse_datetime(data.get("created_at")),
            updated_at=cls._parse_datetime(data.get("updated_at")),
            exchange_order_id=data.get("exchange_order_id"),
            placed_by=data.get("placed_by"),
            variety=data.get("variety", "regular"),
            tradingsymbol=data.get("tradingsymbol"),
            instrument_token=data.get("instrument_token"),
            average_price=data.get("average_price", 0.0),
            cancelled_quantity=data.get("cancelled_quantity", 0),
            market_protection=data.get("market_protection", 0.0),
            after_market_order=data.get("after_market_order", False),
            _raw_data=data,
            idempotency_key=idempotency_key,
        )

    @staticmethod
    def _parse_datetime(dt_str: Optional[str]) -> Optional[datetime]:
        if not dt_str:
            return None
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except Exception:
            return None

    def is_complete(self) -> bool:
        return self.status in ["COMPLETE", "CANCELLED", "REJECTED"]

    def is_pending(self) -> bool:
        return self.status in ["OPEN", "TRIGGER PENDING"]

    def is_filled(self) -> bool:
        return self.status == "COMPLETE" and self.filled_quantity > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "order_id": self.order_id,
            "internal_order_id": self.internal_order_id,
            "symbol": self.symbol,
            "exchange": self.exchange,
            "transaction_type": self.transaction_type,
            "quantity": self.quantity,
            "filled_quantity": self.filled_quantity,
            "pending_quantity": self.pending_quantity,
            "price": self.price,
            "trigger_price": self.trigger_price,
            "order_type": self.order_type,
            "product": self.product,
            "status": self.status,
            "validity": self.validity,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "exchange_order_id": self.exchange_order_id,
            "average_price": self.average_price,
        }


@dataclass
class ZerodhaPosition:
    symbol: str
    exchange: str
    product: str
    quantity: int = 0
    overnight_quantity: int = 0
    covered_quantity: int = 0
    previous_quantity: int = 0
    average_price: float = 0.0
    last_price: float = 0.0
    close_price: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    realised_pnl: float = 0.0
    unrealised_pnl: float = 0.0
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_value: float = 0.0
    sell_value: float = 0.0
    buy_average: float = 0.0
    sell_average: float = 0.0
    trading_symbol: str = ""
    instrument_token: Optional[int] = None
    last_updated: Optional[datetime] = None
    _raw_data: Optional[Dict] = field(default_factory=dict)

    @classmethod
    def from_zerodha_response(cls, data: Dict[str, Any]) -> "ZerodhaPosition":
        return cls(
            symbol=data.get("tradingsymbol", ""),
            exchange=data.get("exchange", ""),
            product=data.get("product", ""),
            quantity=int(data.get("quantity", 0)),
            overnight_quantity=int(data.get("overnight_quantity", 0)),
            covered_quantity=int(data.get("covered_quantity", 0)),
            previous_quantity=int(data.get("previous_quantity", 0)),
            average_price=float(data.get("average_price", 0.0)),
            last_price=float(data.get("last_price", 0.0)),
            close_price=float(data.get("close_price", 0.0)),
            pnl=float(data.get("pnl", 0.0)),
            pnl_percent=float(data.get("pnl_percent", 0.0)),
            realised_pnl=float(data.get("realised_pnl", 0.0)),
            unrealised_pnl=float(data.get("unrealised_pnl", 0.0)),
            buy_quantity=int(data.get("buy_quantity", 0)),
            sell_quantity=int(data.get("sell_quantity", 0)),
            buy_value=float(data.get("buy_value", 0.0)),
            sell_value=float(data.get("sell_value", 0.0)),
            buy_average=float(data.get("buy_average", 0.0)),
            sell_average=float(data.get("sell_average", 0.0)),
            trading_symbol=data.get("tradingsymbol", ""),
            instrument_token=data.get("instrument_token"),
            last_updated=datetime.now(timezone.utc),
            _raw_data=data,
        )

    @property
    def is_long(self) -> bool:
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        return self.quantity < 0

    @property
    def is_flat(self) -> bool:
        return self.quantity == 0

    @property
    def market_value(self) -> float:
        return abs(self.quantity) * self.last_price

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "product": self.product,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "last_price": self.last_price,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
            "realised_pnl": self.realised_pnl,
            "unrealised_pnl": self.unrealised_pnl,
            "market_value": self.market_value,
        }


@dataclass
class ZerodhaPortfolio:
    instrument_token: int
    tradingsymbol: str
    exchange: str
    product: str
    quantity: int = 0
    average_price: float = 0.0
    last_price: float = 0.0
    current_value: float = 0.0
    pnl: float = 0.0
    pnl_percent: float = 0.0
    day_pnl: float = 0.0
    day_pnl_percent: float = 0.0
    _raw_data: Optional[Dict] = field(default_factory=dict)

    @classmethod
    def from_zerodha_response(cls, data: Dict[str, Any]) -> "ZerodhaPortfolio":
        return cls(
            instrument_token=data.get("instrument_token", 0),
            tradingsymbol=data.get("tradingsymbol", ""),
            exchange=data.get("exchange", ""),
            product=data.get("product", ""),
            quantity=data.get("quantity", 0),
            average_price=float(data.get("average_price", 0.0)),
            last_price=float(data.get("last_price", 0.0)),
            current_value=float(data.get("current_value", 0.0)),
            pnl=float(data.get("pnl", 0.0)),
            pnl_percent=float(data.get("pnl_percent", 0.0)),
            day_pnl=float(data.get("day_pnl", 0.0)),
            day_pnl_percent=float(data.get("day_pnl_percent", 0.0)),
            _raw_data=data,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.tradingsymbol,
            "exchange": self.exchange,
            "quantity": self.quantity,
            "average_price": self.average_price,
            "last_price": self.last_price,
            "current_value": self.current_value,
            "pnl": self.pnl,
            "day_pnl": self.day_pnl,
        }


@dataclass
class ZerodhaTick:
    instrument_token: int
    tradingsymbol: str
    exchange: str
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
    tick_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_zerodha_ticker(cls, data: List) -> Optional["ZerodhaTick"]:
        try:
            return cls(
                instrument_token=int(data[0]),
                last_price=float(data[1]) if data[1] else 0.0,
                last_quantity=int(data[2]) if data[2] else 0,
                last_trade_time=datetime.fromtimestamp(data[3]) if data[3] else None,
                average_price=float(data[4]) if data[4] else 0.0,
                volume=int(data[5]) if data[5] else 0,
                oi=int(data[6]) if data[6] else 0,
                oi_day_high=int(data[7]) if data[7] else 0,
                oi_day_low=int(data[8]) if data[8] else 0,
                open=float(data[9]) if data[9] else 0.0,
                high=float(data[10]) if data[10] else 0.0,
                low=float(data[11]) if data[11] else 0.0,
                close=float(data[12]) if data[12] else 0.0,
            )
        except (IndexError, TypeError, ValueError):
            return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instrument_token": self.instrument_token,
            "tradingsymbol": self.tradingsymbol,
            "exchange": self.exchange,
            "last_price": self.last_price,
            "volume": self.volume,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "tick_timestamp": self.tick_timestamp.isoformat(),
        }


@dataclass
class ZerodhaMargin:
    equity: float = 0.0
    commodity: float = 0.0
    currency: float = 0.0
    total: float = 0.0
    available_cash: float = 0.0
    available_margin: float = 0.0
    used_margin: float = 0.0
    net: float = 0.0

    @classmethod
    def from_zerodha_response(cls, data: Dict[str, Any]) -> "ZerodhaMargin":
        return cls(
            equity=float(data.get("equity", 0.0)),
            commodity=float(data.get("commodity", 0.0)),
            currency=float(data.get("currency", 0.0)),
            total=float(data.get("total", 0.0)),
            available_cash=float(data.get("available", {}).get("cash", 0.0)) if isinstance(data.get("available"), dict) else 0.0,
            available_margin=float(data.get("available", {}).get("margin", 0.0)) if isinstance(data.get("available"), dict) else 0.0,
            used_margin=float(data.get("used", {}).get("margin", 0.0)) if isinstance(data.get("used"), dict) else 0.0,
            net=float(data.get("net", 0.0)),
        )


@dataclass
class ZerodhaInstrument:
    instrument_token: int
    exchange_token: str
    tradingsymbol: str
    name: str
    exchange: str
    instrument_type: str
    segment: str
    tick_size: float
    lot_size: int

    @classmethod
    def from_zerodha_response(cls, data: List) -> "ZerodhaInstrument":
        return cls(
            instrument_token=int(data[0]),
            exchange_token=str(data[1]),
            tradingsymbol=str(data[2]),
            name=str(data[3]),
            exchange=str(data[4]),
            instrument_type=str(data[5]),
            segment=str(data[6]),
            tick_size=float(data[7]),
            lot_size=int(data[8]),
        )


@dataclass
class OrderModificationParams:
    order_id: str
    quantity: Optional[int] = None
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    validity: Optional[VALIDITY] = None


@dataclass
class OrderCancellationParams:
    order_id: str
    variety: str = "regular"


@dataclass
class OrderPlacementResult:
    success: bool
    order: Optional[ZerodhaOrder] = None
    error: Optional[str] = None
    retryable: bool = False
    exchange_rejection: bool = False
    duplicate_order: bool = False
    idempotency_key: Optional[str] = None
    placed_at: Optional[datetime] = None


@dataclass
class MarketSession:
    is_open: bool
    session_type: str
    next_open: Optional[datetime] = None
    next_close: Optional[datetime] = None

    @classmethod
    def from_exchange(cls) -> "MarketSession":
        now = datetime.now(timezone.utc)
        ist_now = now.astimezone()

        hour = ist_now.hour
        weekday = ist_now.weekday()

        if weekday >= 5:
            return cls(is_open=False, session_type="CLOSED", next_open=None, next_close=None)

        if 9 * 60 + 15 <= hour * 60 + ist_now.minute < 15 * 60 + 30:
            return cls(is_open=True, session_type="MARKET", next_open=None, next_close=None)
        elif 9 * 60 <= hour * 60 + ist_now.minute < 15 * 60 + 35:
            return cls(is_open=True, session_type="PRE_MARKET", next_open=None, next_close=None)
        else:
            return cls(is_open=False, session_type="CLOSED", next_open=None, next_close=None)
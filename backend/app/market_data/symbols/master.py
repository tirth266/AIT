"""
Symbol Master Management
========================
Maintains master data for all tradable symbols with real-time updates.
"""

import logging
import asyncio
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from collections import defaultdict
import json

from ..core.models import SymbolMaster, Exchange, InstrumentType

logger = logging.getLogger('market_data.symbols')


DEFAULT_NSE_EQUITY = {
    "RELIANCE": {
        "instrument_token": 288974,
        "tradingsymbol": "RELIANCE",
        "name": "Reliance Industries Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "TCS": {
        "instrument_token": 295321,
        "tradingsymbol": "TCS",
        "name": "Tata Consultancy Services Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "HDFCBANK": {
        "instrument_token": 341249,
        "tradingsymbol": "HDFCBANK",
        "name": "HDFC Bank Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "INFY": {
        "instrument_token": 408065,
        "tradingsymbol": "INFY",
        "name": "Infosys Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "ICICIBANK": {
        "instrument_token": 2700673,
        "tradingsymbol": "ICICIBANK",
        "name": "ICICI Bank Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "SBIN": {
        "instrument_token": 2753139,
        "tradingsymbol": "SBIN",
        "name": "State Bank of India",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "KOTAKBANK": {
        "instrument_token": 3779617,
        "tradingsymbol": "KOTAKBANK",
        "name": "Kotak Mahindra Bank Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "ITC": {
        "instrument_token": 959873,
        "tradingsymbol": "ITC",
        "name": "ITC Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "BHARTIARTL": {
        "instrument_token": 2716369,
        "tradingsymbol": "BHARTIARTL",
        "name": "Bharti Airtel Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "HINDUNILVR": {
        "instrument_token": 1121299,
        "tradingsymbol": "HINDUNILVR",
        "name": "Hindustan Unilever Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "LT": {
        "instrument_token": 3712049,
        "tradingsymbol": "LT",
        "name": "Larsen & Toubro Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "ASIANPAINT": {
        "instrument_token": 2610993,
        "tradingsymbol": "ASIANPAINT",
        "name": "Asian Paints Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "MARUTI": {
        "instrument_token": 2818050,
        "tradingsymbol": "MARUTI",
        "name": "Maruti Suzuki India Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
    "AXISBANK": {
        "instrument_token": 2454017,
        "tradingsymbol": "AXISBANK",
        "name": "Axis Bank Ltd",
        "instrument_type": InstrumentType.EQUITY,
        "lot_size": 1,
        "tick_size": 0.05,
    },
}


@dataclass
class SymbolUpdate:
    symbol: str
    exchange: Exchange
    update_type: str
    timestamp: datetime
    data: Dict[str, Any]


class SymbolMasterManager:
    """
    Centralized symbol master management with caching and lookup optimization.
    """

    def __init__(self):
        self._symbols: Dict[str, SymbolMaster] = {}
        self._tokens: Dict[int, SymbolMaster] = {}
        self._exchange_symbols: Dict[Exchange, Dict[str, SymbolMaster]] = defaultdict(dict)
        self._tradable_symbols: Dict[Exchange, List[str]] = defaultdict(list)

        self._callbacks: List[Callable] = []
        self._update_history: List[SymbolUpdate] = []

        self._lock = threading.RLock()

        self._load_default_symbols()

    def _load_default_symbols(self) -> None:
        for symbol, info in DEFAULT_NSE_EQUITY.items():
            master = SymbolMaster(
                symbol=symbol,
                exchange=Exchange.NSE,
                instrument_token=info["instrument_token"],
                tradingsymbol=info["tradingsymbol"],
                name=info["name"],
                instrument_type=info["instrument_type"],
                lot_size=info["lot_size"],
                tick_size=info["tick_size"],
                is_tradeable=True,
                is_listed=True,
            )

            self._add_symbol(master)

    def _add_symbol(self, master: SymbolMaster) -> None:
        key = self._get_key(master.symbol, master.exchange)
        self._symbols[key] = master

        if master.instrument_token:
            self._tokens[master.instrument_token] = master

        self._exchange_symbols[master.exchange][master.symbol] = master

        if master.is_tradeable:
            self._tradable_symbols[master.exchange].append(master.symbol)

    def _get_key(self, symbol: str, exchange: Exchange) -> str:
        return f"{symbol}:{exchange.value}"

    def register_symbol(self, master: SymbolMaster) -> None:
        with self._lock:
            self._add_symbol(master)

            update = SymbolUpdate(
                symbol=master.symbol,
                exchange=master.exchange,
                update_type="REGISTER",
                timestamp=datetime.now(timezone.utc),
                data=master.to_dict(),
            )
            self._update_history.append(update)

            for callback in self._callbacks:
                try:
                    callback(update)
                except Exception as e:
                    logger.warning(f"Symbol update callback error: {e}")

    def register_symbols(self, masters: List[SymbolMaster]) -> None:
        with self._lock:
            for master in masters:
                self._add_symbol(master)

    def get_symbol(
        self,
        symbol: str,
        exchange: Exchange = Exchange.NSE,
    ) -> Optional[SymbolMaster]:
        key = self._get_key(symbol, exchange)
        return self._symbols.get(key)

    def get_by_token(self, instrument_token: int) -> Optional[SymbolMaster]:
        return self._tokens.get(instrument_token)

    def get_by_tradingsymbol(
        self,
        tradingsymbol: str,
        exchange: Exchange = Exchange.NSE,
    ) -> Optional[SymbolMaster]:
        for master in self._exchange_symbols.get(exchange, {}).values():
            if master.tradingsymbol == tradingsymbol:
                return master
        return None

    def get_all_symbols(self, exchange: Optional[Exchange] = None) -> List[SymbolMaster]:
        with self._lock:
            if exchange:
                return list(self._exchange_symbols.get(exchange, {}).values())
            return list(self._symbols.values())

    def get_tradable_symbols(
        self,
        exchange: Exchange = Exchange.NSE,
    ) -> List[str]:
        return self._tradable_symbols.get(exchange, [])

    def is_tradable(
        self,
        symbol: str,
        exchange: Exchange = Exchange.NSE,
    ) -> bool:
        master = self.get_symbol(symbol, exchange)
        return master.is_tradeable if master else False

    def get_symbol_count(self, exchange: Optional[Exchange] = None) -> int:
        if exchange:
            return len(self._exchange_symbols.get(exchange, {}))
        return len(self._symbols)

    def search_symbols(
        self,
        query: str,
        exchange: Optional[Exchange] = None,
        limit: int = 10,
    ) -> List[SymbolMaster]:
        query_upper = query.upper()
        results = []

        symbols = self.get_all_symbols(exchange)

        for master in symbols:
            if query_upper in master.symbol.upper():
                results.append(master)
            elif query_upper in master.name.upper():
                results.append(master)
            elif query_upper in master.tradingsymbol.upper():
                results.append(master)

            if len(results) >= limit:
                break

        return results

    def register_callback(self, callback: Callable[[SymbolUpdate], None]) -> None:
        self._callbacks.append(callback)

    def get_update_history(
        self,
        count: int = 100,
    ) -> List[SymbolUpdate]:
        return self._update_history[-count:]

    def export_to_dict(self) -> Dict[str, Any]:
        return {
            "symbols": [m.to_dict() for m in self._symbols.values()],
            "total_count": len(self._symbols),
            "exchange_counts": {
                ex.value: len(symbols)
                for ex, symbols in self._exchange_symbols.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_symbols": len(self._symbols),
            "by_exchange": {
                ex.value: len(symbols)
                for ex, symbols in self._exchange_symbols.items()
            },
            "tradable_by_exchange": {
                ex.value: len(symbols)
                for ex, symbols in self._tradable_symbols.items()
            },
            "total_tokens": len(self._tokens),
        }


_master_manager: Optional[SymbolMasterManager] = None


def get_symbol_master() -> SymbolMasterManager:
    global _master_manager
    if _master_manager is None:
        _master_manager = SymbolMasterManager()
    return _master_manager
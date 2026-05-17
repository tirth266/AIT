"""
Symbol Manager
==============
Manages Indian stock market symbols and their metadata.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """Information about a trading symbol."""
    symbol: str
    exchange: str
    name: str
    sector: str
    lot_size: int
    tick_size: float
    is_index: bool = False
    base_price: float = 0.0
    volatility: float = 0.01
    avg_volume: int = 0


class SymbolManager:
    """Manages trading symbols for Indian markets."""

    NSE_STOCKS = {
        'RELIANCE': {'name': 'Reliance Industries', 'sector': 'Energy', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 2950, 'volatility': 0.012, 'avg_volume': 5000000},
        'TCS': {'name': 'Tata Consultancy Services', 'sector': 'IT', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 4200, 'volatility': 0.01, 'avg_volume': 3000000},
        'INFY': {'name': 'Infosys', 'sector': 'IT', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1750, 'volatility': 0.011, 'avg_volume': 4000000},
        'HDFCBANK': {'name': 'HDFC Bank', 'sector': 'Banking', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1680, 'volatility': 0.013, 'avg_volume': 6000000},
        'ICICIBANK': {'name': 'ICICI Bank', 'sector': 'Banking', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1050, 'volatility': 0.014, 'avg_volume': 5500000},
        'SBIN': {'name': 'State Bank of India', 'sector': 'Banking', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 780, 'volatility': 0.015, 'avg_volume': 8000000},
        'AXISBANK': {'name': 'Axis Bank', 'sector': 'Banking', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1050, 'volatility': 0.014, 'avg_volume': 4000000},
        'LT': {'name': 'Larsen & Toubro', 'sector': 'Infrastructure', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 3500, 'volatility': 0.012, 'avg_volume': 2500000},
        'ITC': {'name': 'ITC Limited', 'sector': 'FMCG', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 450, 'volatility': 0.008, 'avg_volume': 7000000},
        'BHARTIARTL': {'name': 'Bharti Airtel', 'sector': 'Telecom', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1550, 'volatility': 0.013, 'avg_volume': 3500000},
        'KOTAKBANK': {'name': 'Kotak Mahindra Bank', 'sector': 'Banking', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1900, 'volatility': 0.012, 'avg_volume': 3000000},
        'HINDUNILVR': {'name': 'Hindustan Unilever', 'sector': 'FMCG', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 2800, 'volatility': 0.007, 'avg_volume': 2000000},
        'ASIANPAINT': {'name': 'Asian Paints', 'sector': 'Chemicals', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 3200, 'volatility': 0.011, 'avg_volume': 1500000},
        'MARUTI': {'name': 'Maruti Suzuki', 'sector': 'Auto', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 12000, 'volatility': 0.013, 'avg_volume': 800000},
        'SUNPHARMA': {'name': 'Sun Pharmaceutical', 'sector': 'Pharma', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1800, 'volatility': 0.014, 'avg_volume': 2500000},
        'TITAN': {'name': 'Titan Company', 'sector': 'Consumer', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 3500, 'volatility': 0.012, 'avg_volume': 1200000},
        'BAJFINANCE': {'name': 'Bajaj Finance', 'sector': 'Finance', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 7200, 'volatility': 0.016, 'avg_volume': 1800000},
        'ADANIPORTS': {'name': 'Adani Ports', 'sector': 'Logistics', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1400, 'volatility': 0.018, 'avg_volume': 3000000},
        'WIPRO': {'name': 'Wipro', 'sector': 'IT', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 580, 'volatility': 0.011, 'avg_volume': 4500000},
        'HCLTECH': {'name': 'HCL Technologies', 'sector': 'IT', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 1900, 'volatility': 0.01, 'avg_volume': 2000000},
    }

    NSE_INDICES = {
        'NIFTY50': {'name': 'Nifty 50', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 22500, 'volatility': 0.008, 'avg_volume': 0},
        'NIFTYBANK': {'name': 'Nifty Bank', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 48000, 'volatility': 0.01, 'avg_volume': 0},
        'NIFTYIT': {'name': 'Nifty IT', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 42000, 'volatility': 0.012, 'avg_volume': 0},
        'NIFTYAUTO': {'name': 'Nifty Auto', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 25000, 'volatility': 0.011, 'avg_volume': 0},
        'NIFTYPHARMA': {'name': 'Nifty Pharma', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 19000, 'volatility': 0.01, 'avg_volume': 0},
        'NIFTYMETAL': {'name': 'Nifty Metal', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 9000, 'volatility': 0.015, 'avg_volume': 0},
        'NIFTYFINSERVICE': {'name': 'Nifty Financial Services', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 22000, 'volatility': 0.012, 'avg_volume': 0},
        'NIFTYMEDIA': {'name': 'Nifty Media', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 2200, 'volatility': 0.014, 'avg_volume': 0},
        'NIFTYREALTY': {'name': 'Nifty Realty', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 800, 'volatility': 0.018, 'avg_volume': 0},
        'NIFTYCP': {'name': 'Nifty Consumer Durable', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 38000, 'volatility': 0.01, 'avg_volume': 0},
        'SENSEX': {'name': 'Sensex', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 75000, 'volatility': 0.008, 'avg_volume': 0},
        'BANKNIFTY': {'name': 'Bank Nifty', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 48000, 'volatility': 0.01, 'avg_volume': 0},
        'FINNIFTY': {'name': 'Nifty Financial Services', 'sector': 'Index', 'lot_size': 1, 'tick_size': 0.05, 'base_price': 22000, 'volatility': 0.012, 'avg_volume': 0},
    }

    def __init__(self):
        self._symbols: Dict[str, SymbolInfo] = {}
        self._initialize_symbols()
        logger.info(f"SymbolManager initialized with {len(self._symbols)} symbols")

    def _initialize_symbols(self):
        """Initialize all available symbols."""
        for symbol, data in self.NSE_STOCKS.items():
            self._symbols[symbol] = SymbolInfo(
                symbol=symbol,
                exchange='NSE',
                name=data['name'],
                sector=data['sector'],
                lot_size=data['lot_size'],
                tick_size=data['tick_size'],
                is_index=False,
                base_price=data['base_price'],
                volatility=data['volatility'],
                avg_volume=data['avg_volume']
            )

        for symbol, data in self.NSE_INDICES.items():
            self._symbols[symbol] = SymbolInfo(
                symbol=symbol,
                exchange='NSE',
                name=data['name'],
                sector=data['sector'],
                lot_size=data['lot_size'],
                tick_size=data['tick_size'],
                is_index=True,
                base_price=data['base_price'],
                volatility=data['volatility'],
                avg_volume=data['avg_volume']
            )

    def get_symbol_info(self, symbol: str) -> Optional[SymbolInfo]:
        """Get information about a symbol."""
        return self._symbols.get(symbol.upper())

    def get_all_symbols(self) -> List[str]:
        """Get list of all available symbols."""
        return list(self._symbols.keys())

    def get_stock_symbols(self) -> List[str]:
        """Get list of stock symbols."""
        return [s for s, info in self._symbols.items() if not info.is_index]

    def get_index_symbols(self) -> List[str]:
        """Get list of index symbols."""
        return [s for s, info in self._symbols.items() if info.is_index]

    def get_sector_symbols(self, sector: str) -> List[str]:
        """Get symbols by sector."""
        return [s for s, info in self._symbols.items() if info.sector == sector]

    def get_sectors(self) -> List[str]:
        """Get list of all sectors."""
        return list(set(info.sector for info in self._symbols.values()))

    def is_valid_symbol(self, symbol: str) -> bool:
        """Check if symbol is valid."""
        return symbol.upper() in self._symbols

    def get_base_price(self, symbol: str) -> float:
        """Get base price for symbol."""
        info = self._symbols.get(symbol.upper())
        return info.base_price if info else 0.0

    def get_volatility(self, symbol: str) -> float:
        """Get volatility for symbol."""
        info = self._symbols.get(symbol.upper())
        return info.volatility if info else 0.01


_symbol_manager = SymbolManager()


def get_symbol_manager() -> SymbolManager:
    """Get the global symbol manager instance."""
    return _symbol_manager
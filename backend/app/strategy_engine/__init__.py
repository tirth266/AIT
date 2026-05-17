"""
Strategy Engine Module
=======================
Core components for algorithmic trading.
"""

from .engine import StrategyEngine
from .signal_generator import SignalGenerator
from .execution_engine import ExecutionEngine
from .strategy_manager import StrategyManager
from .order_manager import OrderManager
from .risk_manager import RiskManager
from .position_manager import PositionManager
from .paper_trading import PaperTradingEngine

__all__ = [
    'StrategyEngine',
    'SignalGenerator',
    'ExecutionEngine',
    'StrategyManager',
    'OrderManager',
    'RiskManager',
    'PositionManager',
    'PaperTradingEngine',
]

__version__ = '1.0.0'
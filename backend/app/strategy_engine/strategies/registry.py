"""
Strategy Registry
=================
Central registry for all trading strategies.
"""

import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger('strategy_registry')


class StrategyRegistry:
    """
    Registry for trading strategies.
    """

    def __init__(self):
        self._strategies: Dict[str, Any] = {}
        self._register_strategies()

    def _register_strategies(self) -> None:
        """Register all built-in strategies."""
        from .ema_crossover import EMACrossoverStrategy
        from .rsi_reversal import RSIReversalStrategy
        from .breakout import BreakoutStrategy
        from .scalping import ScalpingStrategy
        from .supertrend_strategy import SupertrendStrategy
        from .ai_strategy import AIStrategy

        self.register('ema_crossover', EMACrossoverStrategy())
        self.register('rsi_reversal', RSIReversalStrategy())
        self.register('breakout', BreakoutStrategy())
        self.register('scalping', ScalpingStrategy())
        self.register('supertrend', SupertrendStrategy())
        self.register('ai_strategy', AIStrategy())

    def register(self, name: str, strategy: Any) -> None:
        """Register a strategy."""
        self._strategies[name.lower()] = strategy

    def get(self, name: str) -> Optional[Any]:
        """Get a strategy by name."""
        return self._strategies.get(name.lower())

    def list_strategies(self) -> List[str]:
        """List all registered strategies."""
        return list(self._strategies.keys())

    def get_strategy_info(self, name: str) -> Optional[Dict]:
        """Get strategy information."""
        strategy = self.get(name)
        if strategy:
            return {
                'name': name,
                'description': strategy.get_description() if hasattr(strategy, 'get_description') else '',
                'parameters': strategy.get_parameters() if hasattr(strategy, 'get_parameters') else {}
            }
        return None
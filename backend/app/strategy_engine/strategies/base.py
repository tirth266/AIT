"""
Base Strategy Class
===================
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies.
    """

    def __init__(self):
        self.name = self.__class__.__name__
        self.strategy_type = self.__class__.__name__.lower().replace('strategy', '')

    @abstractmethod
    async def generate(
        self,
        candles: List[Dict],
        params: Dict[str, Any],
        symbol: str
    ) -> Optional[Dict]:
        """
        Generate a trading signal.

        Args:
            candles: List of OHLCV candles
            params: Strategy parameters
            symbol: Trading symbol

        Returns:
            Signal dict or None
        """
        pass

    def get_description(self) -> str:
        """Get strategy description."""
        return self.__doc__ or "Trading strategy"

    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters schema."""
        return {}

    def create_signal(
        self,
        action: str,
        entry_price: float,
        confidence: float,
        reasoning: str,
        indicators: Dict[str, Any],
        timeframe: str
    ) -> Dict:
        """
        Create a standardized signal dict.

        Args:
            action: BUY, SELL, or HOLD
            entry_price: Entry price
            confidence: Confidence score (0-100)
            reasoning: Human-readable reasoning
            indicators: Indicator values used
            timeframe: Timeframe used

        Returns:
            Signal dict
        """
        return {
            'signal_id': str(uuid.uuid4()),
            'symbol': '',
            'action': action,
            'entry_price': entry_price,
            'confidence': confidence,
            'reasoning': reasoning,
            'indicators': indicators,
            'timeframe': timeframe,
            'timestamp': datetime.utcnow().isoformat()
        }

    def validate_candles(self, candles: List[Dict], min_count: int = 30) -> bool:
        """Validate candle data."""
        if not candles or len(candles) < min_count:
            return False

        for candle in candles[-5:]:
            if not all(k in candle for k in ['open', 'high', 'low', 'close']):
                return False

        return True
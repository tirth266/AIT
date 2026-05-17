"""
Signal Generator
=================
Generates trading signals based on strategy configurations and market data.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from .indicators import IndicatorRegistry
from .strategies import StrategyRegistry

logger = logging.getLogger('signal_generator')


@dataclass
class TradingSignal:
    signal_id: str
    strategy_id: str
    symbol: str
    action: str
    entry_price: float
    stop_loss: float
    target_price: float
    quantity: int
    confidence: float
    reasoning: str
    indicators: Dict[str, Any]
    timestamp: datetime
    timeframe: str


class SignalGenerator:
    """
    Generates trading signals from strategy configurations and candle data.
    """

    def __init__(self):
        self.indicator_registry = IndicatorRegistry()
        self.strategy_registry = StrategyRegistry()

    async def generate(
        self,
        strategy_config: Dict,
        candles: List[Dict],
        symbol: str
    ) -> Optional[Dict]:
        """
        Generate a trading signal based on strategy configuration.

        Args:
            strategy_config: Strategy configuration dict
            candles: List of OHLCV candles
            symbol: Trading symbol

        Returns:
            Signal dict or None
        """
        try:
            strategy_type = strategy_config.get('strategy_type', 'ema_crossover')
            strategy_params = strategy_config.get('parameters', {})

            strategy = self.strategy_registry.get_strategy(strategy_type)
            if not strategy:
                logger.warning(f"Unknown strategy type: {strategy_type}")
                return None

            signal = await strategy.generate(candles, strategy_params, symbol)

            if signal:
                signal['strategy_id'] = str(strategy_config.get('_id', 'unknown'))
                signal['strategy_name'] = strategy_config.get('strategy_name', 'Unknown')

            return signal

        except Exception as e:
            logger.error(f"Signal generation error: {e}")
            return None

    def calculate_confidence(
        self,
        action: str,
        indicator_values: Dict[str, float],
        strategy_params: Dict
    ) -> float:
        """
        Calculate confidence score for a signal.

        Args:
            action: BUY, SELL, or HOLD
            indicator_values: Calculated indicator values
            strategy_params: Strategy parameters

        Returns:
            Confidence score (0-100)
        """
        confidence = 50.0

        if action == 'BUY':
            if indicator_values.get('rsi', 50) < 35:
                confidence += 15
            if indicator_values.get('rsi', 50) < 25:
                confidence += 10

            if indicator_values.get('macd_histogram', 0) > 0:
                confidence += 10

            if indicator_values.get('ema_9', 0) > indicator_values.get('ema_21', 0):
                confidence += 10

        elif action == 'SELL':
            if indicator_values.get('rsi', 50) > 65:
                confidence += 15
            if indicator_values.get('rsi', 50) > 75:
                confidence += 10

            if indicator_values.get('macd_histogram', 0) < 0:
                confidence += 10

            if indicator_values.get('ema_9', 0) < indicator_values.get('ema_21', 0):
                confidence += 10

        min_confidence = strategy_params.get('min_confidence', 30)
        confidence = max(confidence, min_confidence)
        confidence = min(confidence, 95)

        return confidence

    def generate_reasoning(
        self,
        action: str,
        indicator_values: Dict[str, float],
        strategy_name: str
    ) -> str:
        """Generate human-readable reasoning for the signal."""
        reasons = []

        if action == 'BUY':
            if indicator_values.get('rsi', 50) < 30:
                reasons.append(f"RSI at {indicator_values['rsi']:.1f} indicates oversold")
            if indicator_values.get('macd_histogram', 0) > 0:
                reasons.append("MACD histogram positive - momentum bullish")
            if indicator_values.get('ema_9', 0) > indicator_values.get('ema_21', 0):
                reasons.append("EMA 9 above EMA 21 - bullish trend")

        elif action == 'SELL':
            if indicator_values.get('rsi', 50) > 70:
                reasons.append(f"RSI at {indicator_values['rsi']:.1f} indicates overbought")
            if indicator_values.get('macd_histogram', 0) < 0:
                reasons.append("MACD histogram negative - momentum bearish")
            if indicator_values.get('ema_9', 0) < indicator_values.get('ema_21', 0):
                reasons.append("EMA 9 below EMA 21 - bearish trend")

        if not reasons:
            reasons.append("No strong signals detected")

        return f"{strategy_name}: {' | '.join(reasons)}"

    def calculate_levels(
        self,
        entry_price: float,
        action: str,
        risk_settings: Dict
    ) -> Tuple[float, float]:
        """
        Calculate stop loss and target levels.

        Args:
            entry_price: Entry price
            action: BUY or SELL
            risk_settings: Risk management settings

        Returns:
            (stop_loss, target) tuple
        """
        stop_loss_percent = risk_settings.get('stop_loss_percent', 1.0)
        target_percent = risk_settings.get('target_percent', 2.0)

        if action == 'BUY':
            stop_loss = entry_price * (1 - stop_loss_percent / 100)
            target = entry_price * (1 + target_percent / 100)
        else:
            stop_loss = entry_price * (1 + stop_loss_percent / 100)
            target = entry_price * (1 - target_percent / 100)

        return round(stop_loss, 2), round(target, 2)

    def validate_signal(self, signal: Dict, risk_settings: Dict) -> bool:
        """
        Validate a generated signal.

        Args:
            signal: Signal dict
            risk_settings: Risk settings

        Returns:
            True if valid
        """
        if not signal or signal.get('action') == 'HOLD':
            return False

        confidence = signal.get('confidence', 0)
        min_confidence = risk_settings.get('min_confidence', 30)

        if confidence < min_confidence:
            return False

        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)

        if entry_price <= 0 or stop_loss <= 0:
            return False

        return True
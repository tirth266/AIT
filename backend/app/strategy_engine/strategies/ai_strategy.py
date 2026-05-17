"""
AI Hybrid Strategy
==================
Combines multiple indicators with weighted scoring for signal generation.
"""

from typing import Dict, List, Optional, Any

from .base import BaseStrategy
from ..indicators.registry import IndicatorRegistry


class AIStrategy(BaseStrategy):
    """
    AI Hybrid Strategy

    Combines multiple indicators with weighted scoring:
    - EMA Crossover
    - RSI
    - MACD
    - Bollinger Bands
    - Supertrend

    Each indicator votes BUY, SELL, or HOLD with confidence.
    Final signal based on weighted average.
    """

    def __init__(self):
        super().__init__()
        self.indicators = IndicatorRegistry()

    async def generate(
        self,
        candles: List[Dict],
        params: Dict[str, Any],
        symbol: str
    ) -> Optional[Dict]:
        """Generate trading signal using AI-style voting."""
        if not self.validate_candles(candles, 50):
            return None

        closes = [c.get('close', 0) for c in candles]
        current_price = closes[-1]

        votes = []
        indicators_used = {}

        ema_vote = self._get_ema_vote(closes)
        if ema_vote:
            votes.append(ema_vote)
            indicators_used['ema'] = ema_vote['indicator']

        rsi_vote = self._get_rsi_vote(closes)
        if rsi_vote:
            votes.append(rsi_vote)
            indicators_used['rsi'] = rsi_vote['indicator']

        macd_vote = self._get_macd_vote(closes)
        if macd_vote:
            votes.append(macd_vote)
            indicators_used['macd'] = macd_vote['indicator']

        bb_vote = self._get_bb_vote(closes)
        if bb_vote:
            votes.append(bb_vote)
            indicators_used['bb'] = bb_vote['indicator']

        supertrend_vote = self._get_supertrend_vote(candles)
        if supertrend_vote:
            votes.append(supertrend_vote)
            indicators_used['supertrend'] = supertrend_vote['indicator']

        if not votes:
            return None

        buy_score = sum(v['confidence'] for v in votes if v['action'] == 'BUY')
        sell_score = sum(v['confidence'] for v in votes if v['action'] == 'SELL')
        hold_score = sum(v['confidence'] for v in votes if v['action'] == 'HOLD')

        total_score = buy_score + sell_score + hold_score

        if total_score > 0:
            buy_ratio = buy_score / total_score
            sell_ratio = sell_score / total_score
        else:
            buy_ratio = 0
            sell_ratio = 0

        threshold = 0.35

        if buy_ratio > threshold and buy_ratio > sell_ratio:
            action = 'BUY'
            confidence = int(buy_ratio * 100)
            reasoning = f"AI: {len([v for v in votes if v['action'] == 'BUY'])} indicators bullish"
        elif sell_ratio > threshold and sell_ratio > buy_ratio:
            action = 'SELL'
            confidence = int(sell_ratio * 100)
            reasoning = f"AI: {len([v for v in votes if v['action'] == 'SELL'])} indicators bearish"
        else:
            action = 'HOLD'
            confidence = 40
            reasoning = "AI: Mixed signals - no clear direction"

        signal = self.create_signal(
            action=action,
            entry_price=current_price,
            confidence=confidence,
            reasoning=reasoning,
            indicators={
                'votes': votes,
                'buy_score': buy_score,
                'sell_score': sell_score,
                'indicators_used': list(indicators_used.values())
            },
            timeframe='1m'
        )

        signal['symbol'] = symbol
        signal['strategy'] = 'AI Hybrid'

        return signal

    def _get_ema_vote(self, closes: List[float]) -> Optional[Dict]:
        """Get EMA indicator vote."""
        ema_9 = self.indicators.calculate('EMA', closes, period=9)
        ema_21 = self.indicators.calculate('EMA', closes, period=21)

        if not ema_9 or not ema_21:
            return None

        current_9 = ema_9[-1]
        current_21 = ema_21[-1]

        if current_9 > current_21:
            return {'action': 'BUY', 'confidence': 70, 'indicator': 'EMA bullish'}
        elif current_9 < current_21:
            return {'action': 'SELL', 'confidence': 70, 'indicator': 'EMA bearish'}
        return {'action': 'HOLD', 'confidence': 30, 'indicator': 'EMA neutral'}

    def _get_rsi_vote(self, closes: List[float]) -> Optional[Dict]:
        """Get RSI indicator vote."""
        rsi = self.indicators.calculate('RSI', closes, period=14)
        if not rsi:
            return None

        current_rsi = rsi[-1]

        if current_rsi < 30:
            return {'action': 'BUY', 'confidence': 80, 'indicator': f'RSI oversold ({current_rsi:.1f})'}
        elif current_rsi > 70:
            return {'action': 'SELL', 'confidence': 80, 'indicator': f'RSI overbought ({current_rsi:.1f})'}
        elif current_rsi < 40:
            return {'action': 'BUY', 'confidence': 40, 'indicator': f'RSI mildly oversold ({current_rsi:.1f})'}
        elif current_rsi > 60:
            return {'action': 'SELL', 'confidence': 40, 'indicator': f'RSI mildly overbought ({current_rsi:.1f})'}
        return {'action': 'HOLD', 'confidence': 30, 'indicator': f'RSI neutral ({current_rsi:.1f})'}

    def _get_macd_vote(self, closes: List[float]) -> Optional[Dict]:
        """Get MACD indicator vote."""
        macd_result = self.indicators.calculate('MACD', closes)
        if not macd_result.get('histogram'):
            return None

        histogram = macd_result['histogram'][-1]

        if histogram > 0:
            return {'action': 'BUY', 'confidence': 70, 'indicator': 'MACD bullish'}
        elif histogram < 0:
            return {'action': 'SELL', 'confidence': 70, 'indicator': 'MACD bearish'}
        return {'action': 'HOLD', 'confidence': 30, 'indicator': 'MACD neutral'}

    def _get_bb_vote(self, closes: List[float]) -> Optional[Dict]:
        """Get Bollinger Bands vote."""
        bb = self.indicators.calculate('BB', closes)
        if not bb.get('upper') or not bb.get('lower'):
            return None

        current_price = closes[-1]
        upper = bb['upper'][-1]
        lower = bb['lower'][-1]

        if current_price <= lower:
            return {'action': 'BUY', 'confidence': 80, 'indicator': 'Price at lower BB'}
        elif current_price >= upper:
            return {'action': 'SELL', 'confidence': 80, 'indicator': 'Price at upper BB'}
        return {'action': 'HOLD', 'confidence': 30, 'indicator': 'Price in BB range'}

    def _get_supertrend_vote(self, candles: List[Dict]) -> Optional[Dict]:
        """Get Supertrend vote."""
        st = self.indicators.calculate('Supertrend', candles)
        if not st.get('direction'):
            return None

        direction = st['direction'][-1]

        if direction > 0:
            return {'action': 'BUY', 'confidence': 75, 'indicator': 'Supertrend bullish'}
        else:
            return {'action': 'SELL', 'confidence': 75, 'indicator': 'Supertrend bearish'}

    def get_parameters(self) -> Dict[str, Any]:
        return {
            'use_ema': {'type': 'bool', 'default': True},
            'use_rsi': {'type': 'bool', 'default': True},
            'use_macd': {'type': 'bool', 'default': True},
            'use_bb': {'type': 'bool', 'default': True},
            'use_supertrend': {'type': 'bool', 'default': True}
        }
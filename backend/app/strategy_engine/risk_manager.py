"""
Risk Manager
============
Handles risk management, position sizing, and trading limits.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from app.database.connection import get_db

logger = logging.getLogger('risk_manager')


@dataclass
class RiskLimits:
    max_daily_loss: float
    max_position_size: float
    max_positions: int
    max_trades_per_day: int
    min_trade_amount: float
    max_trade_amount: float


class RiskManager:
    """
    Manages risk controls for trading strategies.
    """

    def __init__(self):
        self._daily_loss_cache: Dict[str, Dict] = {}

    async def check_signal(
        self,
        user_id: str,
        signal: Dict,
        risk_settings: Dict
    ) -> Dict:
        """
        Check if a signal passes risk validation.

        Args:
            user_id: User ID
            signal: Trading signal
            risk_settings: Risk settings

        Returns:
            Validation result dict
        """
        result = {'allowed': True, 'reason': ''}

        max_daily_loss = risk_settings.get('max_daily_loss', 5000)
        daily_loss = await self._get_daily_loss(user_id)

        if daily_loss <= -max_daily_loss:
            result['allowed'] = False
            result['reason'] = 'Daily loss limit reached'
            return result

        max_positions = risk_settings.get('max_positions', 5)
        open_positions = await self._get_open_positions_count(user_id)

        if open_positions >= max_positions:
            result['allowed'] = False
            result['reason'] = 'Max positions reached'
            return result

        trades_today = await self._get_trades_today(user_id)
        max_trades_per_day = risk_settings.get('max_trades_per_day', 20)

        if trades_today >= max_trades_per_day:
            result['allowed'] = False
            result['reason'] = 'Max trades per day reached'
            return result

        entry_price = signal.get('entry_price', 0)
        stop_loss = signal.get('stop_loss', 0)

        if entry_price <= 0 or stop_loss <= 0:
            result['allowed'] = False
            result['reason'] = 'Invalid price levels'
            return result

        risk_reward_ratio = abs(entry_price - signal.get('target_price', 0)) / abs(entry_price - stop_loss)

        min_rr = risk_settings.get('min_risk_reward_ratio', 1.5)
        if risk_reward_ratio < min_rr:
            result['allowed'] = False
            result['reason'] = f'Risk/Reward ratio {risk_reward_ratio:.2f} below minimum {min_rr}'
            return result

        return result

    async def calculate_position_size(
        self,
        user_id: str,
        entry_price: float,
        stop_loss: float,
        risk_percent: float,
        account_balance: float
    ) -> int:
        """
        Calculate position size based on risk parameters.

        Args:
            user_id: User ID
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_percent: Risk percentage of account
            account_balance: Total account balance

        Returns:
            Position quantity
        """
        risk_amount = account_balance * (risk_percent / 100)

        risk_per_share = abs(entry_price - stop_loss)
        if risk_per_share <= 0:
            return 1

        quantity = int(risk_amount / risk_per_share)
        max_quantity = int(account_balance * 0.2 / entry_price)

        return max(1, min(quantity, max_quantity))

    async def _get_daily_loss(self, user_id: str) -> float:
        """Get current daily P&L."""
        db = get_db()
        if db is None:
            return 0.0

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            pipeline = [
                {
                    '$match': {
                        'user_id': user_id,
                        'executed_at': {'$gte': today}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'total_pnl': {'$sum': '$pnl'}
                    }
                }
            ]

            result = list(db.paper_trades.aggregate(pipeline))
            if result:
                return result[0].get('total_pnl', 0.0)

        except Exception as e:
            logger.error(f"Error getting daily loss: {e}")

        return 0.0

    async def _get_open_positions_count(self, user_id: str) -> int:
        """Get count of open positions."""
        db = get_db()
        if db is None:
            return 0

        try:
            return db.paper_positions.count_documents({
                'user_id': user_id,
                'status': 'open'
            })
        except Exception:
            return 0

    async def _get_trades_today(self, user_id: str) -> int:
        """Get number of trades executed today."""
        db = get_db()
        if db is None:
            return 0

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            return db.paper_trades.count_documents({
                'user_id': user_id,
                'executed_at': {'$gte': today}
            })
        except Exception:
            return 0

    async def check_stop_loss(
        self,
        position: Dict,
        current_price: float
    ) -> Dict:
        """
        Check if stop loss is triggered.

        Args:
            position: Position dict
            current_price: Current market price

        Returns:
            Result dict with triggered status
        """
        result = {'triggered': False, 'action': 'hold', 'exit_price': 0}

        side = position.get('side', 'BUY')
        entry_price = position.get('entry_price', 0)
        stop_loss = position.get('stop_loss', 0)

        if side == 'BUY' and current_price <= stop_loss:
            result['triggered'] = True
            result['action'] = 'sell'
            result['exit_price'] = stop_loss
            result['reason'] = 'Stop loss hit'
        elif side == 'SELL' and current_price >= stop_loss:
            result['triggered'] = True
            result['action'] = 'buy'
            result['exit_price'] = stop_loss
            result['reason'] = 'Stop loss hit'

        return result

    async def check_take_profit(
        self,
        position: Dict,
        current_price: float
    ) -> Dict:
        """
        Check if take profit target is reached.

        Args:
            position: Position dict
            current_price: Current market price

        Returns:
            Result dict with triggered status
        """
        result = {'triggered': False, 'action': 'hold', 'exit_price': 0}

        side = position.get('side', 'BUY')
        entry_price = position.get('entry_price', 0)
        target = position.get('target', 0)

        if target <= 0:
            return result

        if side == 'BUY' and current_price >= target:
            result['triggered'] = True
            result['action'] = 'sell'
            result['exit_price'] = target
            result['reason'] = 'Take profit target reached'
        elif side == 'SELL' and current_price <= target:
            result['triggered'] = True
            result['action'] = 'buy'
            result['exit_price'] = target
            result['reason'] = 'Take profit target reached'

        return result

    async def check_trailing_stop(
        self,
        position: Dict,
        current_price: float,
        trailing_percent: float
    ) -> Dict:
        """
        Check if trailing stop is triggered.

        Args:
            position: Position dict
            current_price: Current market price
            trailing_percent: Trailing stop percentage

        Returns:
            Result dict
        """
        result = {'triggered': False, 'action': 'hold', 'exit_price': 0}

        if trailing_percent <= 0:
            return result

        side = position.get('side', 'BUY')
        highest_price = position.get('highest_price', 0)
        entry_price = position.get('entry_price', 0)

        if side == 'BUY':
            new_high = max(highest_price, current_price)
            trailing_stop = new_high * (1 - trailing_percent / 100)

            if current_price <= trailing_stop and highest_price > entry_price:
                result['triggered'] = True
                result['action'] = 'sell'
                result['exit_price'] = round(trailing_stop, 2)
                result['reason'] = 'Trailing stop triggered'

        return result

    async def log_risk_event(
        self,
        user_id: str,
        event_type: str,
        details: Dict
    ) -> None:
        """Log risk management events."""
        db = get_db()
        if db is None:
            return

        try:
            log_entry = {
                'user_id': user_id,
                'event_type': event_type,
                'details': details,
                'timestamp': datetime.utcnow()
            }

            db.risk_logs.insert_one(log_entry)

        except Exception as e:
            logger.error(f"Error logging risk event: {e}")

    async def get_risk_summary(self, user_id: str) -> Dict:
        """Get risk management summary for user."""
        db = get_db()
        if db is None:
            return {}

        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        try:
            daily_pnl = 0.0
            pipeline = [
                {'$match': {'user_id': user_id, 'executed_at': {'$gte': today}}},
                {'$group': {'_id': None, 'total_pnl': {'$sum': '$pnl'}}}
            ]
            result = list(db.paper_trades.aggregate(pipeline))
            if result:
                daily_pnl = result[0].get('total_pnl', 0.0)

            open_positions = db.paper_positions.count_documents({
                'user_id': user_id,
                'status': 'open'
            })

            trades_today = db.paper_trades.count_documents({
                'user_id': user_id,
                'executed_at': {'$gte': today}
            })

            return {
                'daily_pnl': daily_pnl,
                'open_positions': open_positions,
                'trades_today': trades_today,
                'risk_status': 'normal' if daily_pnl > -5000 else 'danger'
            }

        except Exception as e:
            logger.error(f"Error getting risk summary: {e}")
            return {}
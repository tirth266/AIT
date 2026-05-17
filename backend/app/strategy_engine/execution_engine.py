"""
Execution Engine
================
Handles order execution for both paper and live trading.
"""

import logging
import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import random

from bson import ObjectId
from app.database.connection import get_db
from .order_manager import OrderManager

logger = logging.getLogger('execution_engine')


class OrderStatus(Enum):
    PENDING = 'pending'
    EXECUTED = 'executed'
    CANCELLED = 'cancelled'
    REJECTED = 'rejected'
    PARTIAL = 'partial'


class ExecutionMode(Enum):
    PAPER = 'paper'
    LIVE = 'live'


@dataclass
class TradeExecution:
    execution_id: str
    strategy_id: str
    user_id: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    price: float
    order_type: str
    status: OrderStatus
    executed_at: datetime
    execution_price: Optional[float] = None


class ExecutionEngine:
    """
    Handles order execution for strategies.
    """

    def __init__(self, socket_manager=None):
        self.socket_manager = socket_manager
        self.order_manager = OrderManager()
        self._execution_queue: List[Dict] = []
        self._is_processing = False

    async def execute_paper_trade(
        self,
        strategy_id: str,
        user_id: str,
        signal: Dict,
        risk_settings: Dict
    ) -> Optional[Dict]:
        """
        Execute a paper trade (simulated).

        Args:
            strategy_id: Strategy ID
            user_id: User ID
            signal: Trading signal
            risk_settings: Risk settings

        Returns:
            Trade execution dict
        """
        try:
            db = get_db()
            if not db:
                logger.error("Database not available for paper trade")
                return None

            quantity = self._calculate_quantity(
                signal.get('entry_price', 0),
                risk_settings.get('position_size_percent', 10),
                risk_settings.get('max_position_size', 100000)
            )

            execution_price = signal.get('entry_price')

            slippage = random.uniform(-0.05, 0.05)
            execution_price = execution_price * (1 + slippage / 100)

            trade = {
                '_id': ObjectId(),
                'strategy_id': strategy_id,
                'user_id': user_id,
                'symbol': signal.get('symbol'),
                'exchange': signal.get('exchange', 'NSE'),
                'side': signal.get('action'),
                'quantity': quantity,
                'order_type': 'MARKET',
                'status': 'executed',
                'entry_price': signal.get('entry_price'),
                'execution_price': round(execution_price, 2),
                'stop_loss': signal.get('stop_loss'),
                'target': signal.get('target_price'),
                'mode': 'paper',
                'executed_at': datetime.utcnow(),
                'created_at': datetime.utcnow()
            }

            db.paper_trades.insert_one(self._to_dict(trade))

            await self._update_paper_portfolio(user_id, trade)

            logger.info(f"Paper trade executed: {signal.get('action')} {quantity} {signal.get('symbol')}")

            return self._to_dict(trade)

        except Exception as e:
            logger.error(f"Paper trade execution error: {e}")
            return None

    async def execute_live_trade(
        self,
        strategy_id: str,
        user_id: str,
        signal: Dict,
        execution_settings: Dict
    ) -> Optional[Dict]:
        """
        Execute a live trade (via broker API).

        Args:
            strategy_id: Strategy ID
            user_id: User ID
            signal: Trading signal
            execution_settings: Execution settings

        Returns:
            Trade execution dict
        """
        try:
            db = get_db()
            if not db:
                logger.error("Database not available for live trade")
                return None

            order_id = await self.order_manager.place_order(
                user_id=user_id,
                symbol=signal.get('symbol'),
                side=signal.get('action'),
                quantity=signal.get('quantity', 1),
                order_type=execution_settings.get('order_type', 'MARKET'),
                price=signal.get('entry_price')
            )

            if not order_id:
                logger.error("Failed to place live order")
                return None

            trade = {
                '_id': ObjectId(),
                'strategy_id': strategy_id,
                'user_id': user_id,
                'symbol': signal.get('symbol'),
                'exchange': signal.get('exchange', 'NSE'),
                'side': signal.get('action'),
                'quantity': signal.get('quantity', 1),
                'order_type': execution_settings.get('order_type', 'MARKET'),
                'order_id': order_id,
                'status': 'pending',
                'entry_price': signal.get('entry_price'),
                'stop_loss': signal.get('stop_loss'),
                'target': signal.get('target_price'),
                'mode': 'live',
                'created_at': datetime.utcnow()
            }

            db.strategy_executions.insert_one(self._to_dict(trade))

            logger.info(f"Live order placed: {order_id} {signal.get('action')} {signal.get('symbol')}")

            return self._to_dict(trade)

        except Exception as e:
            logger.error(f"Live trade execution error: {e}")
            return None

    def _calculate_quantity(
        self,
        price: float,
        position_size_percent: float,
        max_position_size: float
    ) -> int:
        """Calculate position quantity based on risk settings."""
        if price <= 0:
            return 1

        max_amount = max_position_size * (position_size_percent / 100)
        quantity = int(max_amount / price)

        return max(1, quantity)

    async def _update_paper_portfolio(self, user_id: str, trade: Dict) -> None:
        """Update paper trading portfolio."""
        db = get_db()
        if not db:
            return

        portfolio = db.paper_portfolios.find_one({'user_id': user_id})

        if not portfolio:
            portfolio = {
                'user_id': user_id,
                'cash': 100000.0,
                'positions': [],
                'created_at': datetime.utcnow()
            }
            db.paper_portfolios.insert_one(portfolio)

        side = trade.get('side')
        symbol = trade.get('symbol')
        quantity = trade.get('quantity', 0)
        price = trade.get('execution_price', 0)

        current_cash = portfolio.get('cash', 100000)

        if side == 'BUY':
            new_cash = current_cash - (quantity * price)
            db.paper_portfolios.update_one(
                {'user_id': user_id},
                {
                    '$set': {'cash': new_cash},
                    '$push': {
                        'positions': {
                            'symbol': symbol,
                            'quantity': quantity,
                            'entry_price': price,
                            'opened_at': datetime.utcnow()
                        }
                    }
                }
            )
        else:
            new_cash = current_cash + (quantity * price)
            db.paper_portfolios.update_one(
                {'user_id': user_id},
                {'$set': {'cash': new_cash}}
            )

    async def close_paper_position(
        self,
        user_id: str,
        symbol: str,
        quantity: int,
        exit_price: float
    ) -> Optional[Dict]:
        """Close a paper trading position."""
        try:
            db = get_db()
            if not db:
                return None

            portfolio = db.paper_portfolios.find_one({'user_id': user_id})
            if not portfolio:
                return None

            pnl = 0
            positions = portfolio.get('positions', [])

            for pos in positions:
                if pos.get('symbol') == symbol and pos.get('quantity') >= quantity:
                    entry_price = pos.get('entry_price', 0)
                    pnl = (exit_price - entry_price) * quantity
                    break

            current_cash = portfolio.get('cash', 100000)
            new_cash = current_cash + (quantity * exit_price) + pnl

            db.paper_portfolios.update_one(
                {'user_id': user_id},
                {'$set': {'cash': new_cash}}
            )

            closed_trade = {
                'user_id': user_id,
                'symbol': symbol,
                'quantity': quantity,
                'exit_price': exit_price,
                'pnl': pnl,
                'closed_at': datetime.utcnow()
            }

            db.paper_closed_trades.insert_one(closed_trade)

            return closed_trade

        except Exception as e:
            logger.error(f"Error closing paper position: {e}")
            return None

    def _to_dict(self, obj: Any) -> Dict:
        """Convert object to dict for MongoDB."""
        if hasattr(obj, '__dict__'):
            result = {}
            for key, value in obj.__dict__.items():
                if key.startswith('_'):
                    continue
                if isinstance(value, datetime):
                    result[key] = value
                elif isinstance(value, (str, int, float, bool, list, dict)):
                    result[key] = value
            return result
        elif isinstance(obj, dict):
            return {k: self._to_dict(v) for k, v in obj.items() if not k.startswith('_')}
        return obj

    async def validate_execution(
        self,
        user_id: str,
        signal: Dict,
        risk_settings: Dict
    ) -> Dict:
        """
        Validate if a trade can be executed.

        Args:
            user_id: User ID
            signal: Trading signal
            risk_settings: Risk settings

        Returns:
            Validation result dict
        """
        result = {'allowed': True, 'reason': ''}

        max_positions = risk_settings.get('max_positions', 5)
        db = get_db()

        if db:
            open_positions = db.paper_positions.count_documents({
                'user_id': user_id,
                'status': 'open'
            })

            if open_positions >= max_positions:
                result['allowed'] = False
                result['reason'] = 'Max positions reached'
                return result

        return result
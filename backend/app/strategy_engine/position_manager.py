"""
Position Manager
================
Manages trading positions and tracks P&L.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId

from app.database.connection import get_db

logger = logging.getLogger('position_manager')


class PositionManager:
    """
    Manages open positions and calculates P&L.
    """

    def __init__(self):
        pass

    async def open_position(
        self,
        user_id: str,
        trade: Dict
    ) -> Optional[str]:
        """Open a new position."""
        db = get_db()
        if not db:
            return None

        try:
            position = {
                'user_id': user_id,
                'strategy_id': trade.get('strategy_id'),
                'symbol': trade.get('symbol'),
                'exchange': trade.get('exchange', 'NSE'),
                'side': trade.get('side'),
                'quantity': trade.get('quantity'),
                'entry_price': trade.get('execution_price') or trade.get('entry_price'),
                'stop_loss': trade.get('stop_loss'),
                'target': trade.get('target'),
                'status': 'open',
                'opened_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'highest_price': trade.get('execution_price') or trade.get('entry_price'),
                'lowest_price': trade.get('execution_price') or trade.get('entry_price')
            }

            result = db.paper_positions.insert_one(position)
            logger.info(f"Position opened: {result.inserted_id}")

            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error opening position: {e}")
            return None

    async def close_position(
        self,
        position_id: str,
        exit_price: float,
        exit_reason: str
    ) -> Optional[Dict]:
        """Close an existing position."""
        db = get_db()
        if not db:
            return None

        try:
            position = db.paper_positions.find_one({'_id': ObjectId(position_id)})
            if not position:
                return None

            entry_price = position.get('entry_price', 0)
            quantity = position.get('quantity', 0)
            side = position.get('side', 'BUY')

            if side == 'BUY':
                pnl = (exit_price - entry_price) * quantity
            else:
                pnl = (entry_price - exit_price) * quantity

            db.paper_positions.update_one(
                {'_id': ObjectId(position_id)},
                {
                    '$set': {
                        'status': 'closed',
                        'exit_price': exit_price,
                        'exit_reason': exit_reason,
                        'pnl': pnl,
                        'closed_at': datetime.utcnow(),
                        'updated_at': datetime.utcnow()
                    }
                }
            )

            logger.info(f"Position closed: {position_id}, P&L: {pnl}")

            return {
                'position_id': position_id,
                'pnl': pnl,
                'exit_price': exit_price,
                'exit_reason': exit_reason
            }

        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return None

    async def get_open_positions(self, user_id: str) -> List[Dict]:
        """Get all open positions for a user."""
        db = get_db()
        if not db:
            return []

        try:
            positions = list(db.paper_positions.find({
                'user_id': user_id,
                'status': 'open'
            }))

            for pos in positions:
                pos['_id'] = str(pos['_id'])

            return positions

        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []

    async def get_position(self, position_id: str) -> Optional[Dict]:
        """Get a specific position."""
        db = get_db()
        if not db:
            return None

        try:
            position = db.paper_positions.find_one({'_id': ObjectId(position_id)})
            if position:
                position['_id'] = str(position['_id'])
            return position

        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None

    async def update_position_prices(
        self,
        position_id: str,
        current_price: float
    ) -> None:
        """Update position with current market price."""
        db = get_db()
        if not db:
            return

        try:
            position = db.paper_positions.find_one({'_id': ObjectId(position_id)})
            if not position:
                return

            highest = position.get('highest_price', 0)
            lowest = position.get('lowest_price', float('inf'))

            if current_price > highest:
                highest = current_price
            if current_price < lowest:
                lowest = current_price

            side = position.get('side', 'BUY')
            entry_price = position.get('entry_price', 0)
            quantity = position.get('quantity', 0)

            if side == 'BUY':
                unrealized_pnl = (current_price - entry_price) * quantity
            else:
                unrealized_pnl = (entry_price - current_price) * quantity

            db.paper_positions.update_one(
                {'_id': ObjectId(position_id)},
                {
                    '$set': {
                        'current_price': current_price,
                        'unrealized_pnl': unrealized_pnl,
                        'highest_price': highest,
                        'lowest_price': lowest,
                        'updated_at': datetime.utcnow()
                    }
                }
            )

        except Exception as e:
            logger.error(f"Error updating position prices: {e}")

    async def get_position_pnl(self, position_id: str) -> Optional[Dict]:
        """Calculate P&L for a position."""
        position = await self.get_position(position_id)
        if not position:
            return None

        entry_price = position.get('entry_price', 0)
        current_price = position.get('current_price', entry_price)
        quantity = position.get('quantity', 0)
        side = position.get('side', 'BUY')

        if side == 'BUY':
            pnl = (current_price - entry_price) * quantity
            pnl_percent = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
        else:
            pnl = (entry_price - current_price) * quantity
            pnl_percent = ((entry_price - current_price) / entry_price * 100) if entry_price > 0 else 0

        return {
            'pnl': pnl,
            'pnl_percent': round(pnl_percent, 2),
            'entry_price': entry_price,
            'current_price': current_price,
            'quantity': quantity
        }

    async def get_portfolio_summary(self, user_id: str) -> Dict:
        """Get portfolio summary with total P&L."""
        db = get_db()
        if not db:
            return {}

        try:
            positions = list(db.paper_positions.find({
                'user_id': user_id,
                'status': 'open'
            }))

            total_pnl = 0.0
            total_value = 0.0

            for pos in positions:
                pnl = pos.get('unrealized_pnl', 0)
                total_pnl += pnl

                entry_price = pos.get('entry_price', 0)
                quantity = pos.get('quantity', 0)
                total_value += entry_price * quantity

            portfolio = db.paper_portfolios.find_one({'user_id': user_id})
            cash = portfolio.get('cash', 100000) if portfolio else 100000

            return {
                'cash': cash,
                'total_value': total_value,
                'total_pnl': total_pnl,
                'open_positions': len(positions)
            }

        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            return {}

    async def get_closed_positions(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get closed positions history."""
        db = get_db()
        if not db:
            return []

        try:
            positions = list(db.paper_positions.find({
                'user_id': user_id,
                'status': 'closed'
            }).sort('closed_at', -1).limit(limit))

            for pos in positions:
                pos['_id'] = str(pos['_id'])

            return positions

        except Exception as e:
            logger.error(f"Error getting closed positions: {e}")
            return []
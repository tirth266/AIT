"""
Paper Trading Engine
====================
Simulates trading without real money.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from app.database.connection import get_db

logger = logging.getLogger('paper_trading')


@dataclass
class PaperPortfolio:
    user_id: str
    cash: float
    initial_capital: float
    positions: List[Dict] = field(default_factory=list)
    closed_trades: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PaperTrade:
    trade_id: str
    user_id: str
    strategy_id: str
    symbol: str
    exchange: str
    side: str
    quantity: int
    entry_price: float
    exit_price: Optional[float] = None
    pnl: float = 0.0
    status: str = 'open'
    opened_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None


class PaperTradingEngine:
    """
    Paper trading simulation engine.
    """

    def __init__(self):
        self._portfolios: Dict[str, PaperPortfolio] = {}
        self._default_capital = 100000.0

    async def initialize_portfolio(
        self,
        user_id: str,
        initial_capital: Optional[float] = None
    ) -> Dict:
        """
        Initialize a paper trading portfolio.

        Args:
            user_id: User ID
            initial_capital: Starting capital (default: 100000)

        Returns:
            Portfolio dict
        """
        db = get_db()
        if not db:
            return {}

        capital = initial_capital or self._default_capital

        existing = db.paper_portfolios.find_one({'user_id': user_id})
        if existing:
            return existing

        portfolio = {
            'user_id': user_id,
            'cash': capital,
            'initial_capital': capital,
            'positions': [],
            'closed_trades': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }

        db.paper_portfolios.insert_one(portfolio)
        logger.info(f"Paper portfolio initialized for {user_id} with {capital}")

        return portfolio

    async def get_portfolio(self, user_id: str) -> Optional[Dict]:
        """Get paper trading portfolio."""
        db = get_db()
        if not db:
            return None

        return db.paper_portfolios.find_one({'user_id': user_id})

    async def execute_entry(
        self,
        user_id: str,
        strategy_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        stop_loss: Optional[float] = None,
        target: Optional[float] = None
    ) -> Optional[Dict]:
        """
        Execute a paper trade entry.

        Args:
            user_id: User ID
            strategy_id: Strategy ID
            symbol: Trading symbol
            side: BUY or SELL
            quantity: Quantity
            price: Entry price
            stop_loss: Stop loss price
            target: Target price

        Returns:
            Trade dict
        """
        db = get_db()
        if not db:
            return None

        portfolio = await self.get_portfolio(user_id)
        if not portfolio:
            portfolio = await self.initialize_portfolio(user_id)

        cash = portfolio.get('cash', 0)
        total_cost = price * quantity

        if side == 'BUY' and total_cost > cash:
            logger.warning(f"Insufficient cash for paper trade: {cash} < {total_cost}")
            return None

        trade = {
            'user_id': user_id,
            'strategy_id': strategy_id,
            'symbol': symbol,
            'exchange': 'NSE',
            'side': side,
            'quantity': quantity,
            'entry_price': price,
            'stop_loss': stop_loss,
            'target': target,
            'status': 'open',
            'pnl': 0.0,
            'opened_at': datetime.utcnow(),
            'created_at': datetime.utcnow()
        }

        result = db.paper_trades.insert_one(trade)
        trade['_id'] = str(result.inserted_id)

        new_cash = cash - total_cost if side == 'BUY' else cash + total_cost

        db.paper_portfolios.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'cash': new_cash,
                    'updated_at': datetime.utcnow()
                },
                '$push': {
                    'positions': {
                        'trade_id': trade['_id'],
                        'symbol': symbol,
                        'side': side,
                        'quantity': quantity,
                        'entry_price': price,
                        'stop_loss': stop_loss,
                        'target': target,
                        'opened_at': datetime.utcnow()
                    }
                }
            }
        )

        logger.info(f"Paper entry: {side} {quantity} {symbol} @ {price}")

        return trade

    async def execute_exit(
        self,
        trade_id: str,
        exit_price: float,
        exit_reason: str = 'manual'
    ) -> Optional[Dict]:
        """
        Close a paper trade.

        Args:
            trade_id: Trade ID
            exit_price: Exit price
            exit_reason: Reason for exit

        Returns:
            Trade dict with P&L
        """
        db = get_db()
        if not db:
            return None

        trade = db.paper_trades.find_one({'_id': trade_id})
        if not trade or trade.get('status') == 'closed':
            return None

        side = trade.get('side', 'BUY')
        entry_price = trade.get('entry_price', 0)
        quantity = trade.get('quantity', 0)

        if side == 'BUY':
            pnl = (exit_price - entry_price) * quantity
        else:
            pnl = (entry_price - exit_price) * quantity

        db.paper_trades.update_one(
            {'_id': trade_id},
            {
                '$set': {
                    'exit_price': exit_price,
                    'exit_reason': exit_reason,
                    'pnl': pnl,
                    'status': 'closed',
                    'closed_at': datetime.utcnow()
                }
            }
        )

        user_id = trade.get('user_id')
        portfolio = await self.get_portfolio(user_id)
        if portfolio:
            cash = portfolio.get('cash', 0)
            new_cash = cash + (exit_price * quantity) + pnl

            db.paper_portfolios.update_one(
                {'user_id': user_id},
                {
                    '$set': {
                        'cash': new_cash,
                        'updated_at': datetime.utcnow()
                    },
                    '$pull': {
                        'positions': {'trade_id': trade_id}
                    }
                }
            )

        trade['exit_price'] = exit_price
        trade['pnl'] = pnl
        trade['exit_reason'] = exit_reason

        logger.info(f"Paper exit: {trade_id} @ {exit_price}, P&L: {pnl}")

        return trade

    async def get_open_trades(self, user_id: str) -> List[Dict]:
        """Get open paper trades."""
        db = get_db()
        if not db:
            return []

        try:
            trades = list(db.paper_trades.find({
                'user_id': user_id,
                'status': 'open'
            }))

            for trade in trades:
                trade['_id'] = str(trade['_id'])

            return trades

        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []

    async def get_trade_history(
        self,
        user_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Get trade history."""
        db = get_db()
        if not db:
            return []

        try:
            trades = list(db.paper_trades.find({
                'user_id': user_id,
                'status': 'closed'
            }).sort('closed_at', -1).limit(limit))

            for trade in trades:
                trade['_id'] = str(trade['_id'])

            return trades

        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []

    async def calculate_performance(
        self,
        user_id: str,
        days: int = 30
    ) -> Dict:
        """
        Calculate performance metrics.

        Args:
            user_id: User ID
            days: Number of days to analyze

        Returns:
            Performance metrics
        """
        db = get_db()
        if not db:
            return {}

        start_date = datetime.utcnow() - timedelta(days=days)

        try:
            trades = list(db.paper_trades.find({
                'user_id': user_id,
                'status': 'closed',
                'closed_at': {'$gte': start_date}
            }))

            portfolio = await self.get_portfolio(user_id)
            current_capital = portfolio.get('cash', 0) if portfolio else 0
            initial_capital = portfolio.get('initial_capital', self._default_capital) if portfolio else self._default_capital

            total_trades = len(trades)
            winning = sum(1 for t in trades if t.get('pnl', 0) > 0)
            losing = total_trades - winning
            total_pnl = sum(t.get('pnl', 0) for t in trades)

            return {
                'total_trades': total_trades,
                'winning_trades': winning,
                'losing_trades': losing,
                'win_rate': (winning / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'current_capital': current_capital,
                'return_percent': ((current_capital - initial_capital) / initial_capital * 100) if initial_capital > 0 else 0,
                'avg_pnl': total_pnl / total_trades if total_trades > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error calculating performance: {e}")
            return {}

    async def reset_portfolio(self, user_id: str) -> bool:
        """Reset paper portfolio to initial capital."""
        db = get_db()
        if not db:
            return False

        portfolio = await self.get_portfolio(user_id)
        if not portfolio:
            return False

        initial_capital = portfolio.get('initial_capital', self._default_capital)

        db.paper_portfolios.update_one(
            {'user_id': user_id},
            {
                '$set': {
                    'cash': initial_capital,
                    'positions': [],
                    'updated_at': datetime.utcnow()
                },
                '$set': {
                    'closed_trades': []
                }
            }
        )

        db.paper_trades.delete_many({'user_id': user_id})

        logger.info(f"Portfolio reset for {user_id}")
        return True


_paper_engine: Optional[PaperTradingEngine] = None


def get_paper_engine() -> PaperTradingEngine:
    """Get the global paper trading engine instance."""
    global _paper_engine
    if _paper_engine is None:
        _paper_engine = PaperTradingEngine()
    return _paper_engine
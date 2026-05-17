"""
Strategy Manager
================
Manages strategy CRUD operations and lifecycle.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from bson import ObjectId

from app.database.connection import get_db

logger = logging.getLogger('strategy_manager')


class StrategyManager:
    """
    Manages strategy lifecycle, persistence, and configuration.
    """

    def __init__(self):
        pass

    async def create_strategy(
        self,
        user_id: str,
        strategy_data: Dict
    ) -> Optional[str]:
        """Create a new strategy."""
        db = get_db()
        if not db:
            logger.error("Database not available")
            return None

        try:
            strategy = {
                'user_id': user_id,
                'strategy_name': strategy_data.get('strategy_name'),
                'description': strategy_data.get('description', ''),
                'strategy_type': strategy_data.get('strategy_type', 'ema_crossover'),
                'symbol': strategy_data.get('symbol'),
                'exchange': strategy_data.get('exchange', 'NSE'),
                'timeframe': strategy_data.get('timeframe', '1m'),
                'mode': strategy_data.get('mode', 'paper'),
                'status': 'created',
                'parameters': strategy_data.get('parameters', {}),
                'indicators': strategy_data.get('indicators', []),
                'entry_conditions': strategy_data.get('entry_conditions', []),
                'exit_conditions': strategy_data.get('exit_conditions', []),
                'risk_settings': strategy_data.get('risk_settings', {
                    'stop_loss_percent': 1.0,
                    'target_percent': 2.0,
                    'position_size_percent': 10,
                    'max_positions': 5,
                    'max_daily_loss': 5000
                }),
                'execution_settings': strategy_data.get('execution_settings', {
                    'order_type': 'MARKET',
                    'allow_partial_fills': False,
                    'retry_on_failure': True,
                    'max_retries': 3
                }),
                'statistics': {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0
                },
                'is_active': False,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }

            result = db.strategies.insert_one(strategy)
            logger.info(f"Strategy created: {result.inserted_id}")

            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error creating strategy: {e}")
            return None

    async def get_strategy(self, strategy_id: str) -> Optional[Dict]:
        """Get strategy by ID."""
        db = get_db()
        if not db:
            return None

        try:
            strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
            if strategy:
                strategy['_id'] = str(strategy['_id'])
            return strategy
        except Exception as e:
            logger.error(f"Error getting strategy: {e}")
            return None

    async def update_strategy(
        self,
        strategy_id: str,
        updates: Dict
    ) -> bool:
        """Update strategy configuration."""
        db = get_db()
        if not db:
            return False

        try:
            updates['updated_at'] = datetime.utcnow()
            result = db.strategies.update_one(
                {'_id': ObjectId(strategy_id)},
                {'$set': updates}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating strategy: {e}")
            return False

    async def delete_strategy(self, strategy_id: str) -> bool:
        """Delete a strategy."""
        db = get_db()
        if not db:
            return False

        try:
            result = db.strategies.delete_one({'_id': ObjectId(strategy_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error deleting strategy: {e}")
            return False

    async def list_strategies(
        self,
        user_id: str,
        filters: Optional[Dict] = None
    ) -> List[Dict]:
        """List strategies for a user."""
        db = get_db()
        if not db:
            return []

        query = {'user_id': user_id}
        if filters:
            if filters.get('is_active') is not None:
                query['is_active'] = filters['is_active']
            if filters.get('mode'):
                query['mode'] = filters['mode']
            if filters.get('strategy_type'):
                query['strategy_type'] = filters['strategy_type']

        try:
            strategies = list(db.strategies.find(query).sort('created_at', -1))
            for strategy in strategies:
                strategy['_id'] = str(strategy['_id'])
            return strategies
        except Exception as e:
            logger.error(f"Error listing strategies: {e}")
            return []

    async def update_statistics(
        self,
        strategy_id: str,
        trade_result: Dict
    ) -> bool:
        """Update strategy statistics after a trade."""
        db = get_db()
        if not db:
            return False

        try:
            strategy = db.strategies.find_one({'_id': ObjectId(strategy_id)})
            if not strategy:
                return False

            stats = strategy.get('statistics', {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0
            })

            stats['total_trades'] += 1

            pnl = trade_result.get('pnl', 0)
            stats['total_pnl'] += pnl

            if pnl > 0:
                stats['winning_trades'] += 1
            else:
                stats['losing_trades'] += 1

            if stats['total_trades'] > 0:
                stats['win_rate'] = (stats['winning_trades'] / stats['total_trades']) * 100

            db.strategies.update_one(
                {'_id': ObjectId(strategy_id)},
                {
                    '$set': {
                        'statistics': stats,
                        'updated_at': datetime.utcnow()
                    }
                }
            )

            return True

        except Exception as e:
            logger.error(f"Error updating statistics: {e}")
            return False

    async def clone_strategy(
        self,
        strategy_id: str,
        new_name: Optional[str] = None
    ) -> Optional[str]:
        """Clone an existing strategy."""
        original = await self.get_strategy(strategy_id)
        if not original:
            return None

        original.pop('_id', None)
        original['strategy_name'] = new_name or f"{original['strategy_name']} (Copy)"
        original['is_active'] = False
        original['status'] = 'created'
        original['created_at'] = datetime.utcnow()
        original['updated_at'] = datetime.utcnow()

        if 'statistics' in original:
            original['statistics'] = {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0
            }

        db = get_db()
        if db:
            result = db.strategies.insert_one(original)
            return str(result.inserted_id)

        return None

    async def get_strategy_performance(
        self,
        strategy_id: str,
        period: str = 'all'
    ) -> Optional[Dict]:
        """Get strategy performance metrics."""
        db = get_db()
        if not db:
            return None

        try:
            query = {'strategy_id': strategy_id}
            if period != 'all':
                from datetime import timedelta
                start_date = datetime.utcnow() - timedelta(days=int(period))
                query['executed_at'] = {'$gte': start_date}

            trades = list(db.paper_trades.find(query))

            if not trades:
                return None

            total_trades = len(trades)
            winning = sum(1 for t in trades if t.get('pnl', 0) > 0)
            losing = total_trades - winning

            total_pnl = sum(t.get('pnl', 0) for t in trades)
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0

            wins = [t.get('pnl', 0) for t in trades if t.get('pnl', 0) > 0]
            losses = [abs(t.get('pnl', 0)) for t in trades if t.get('pnl', 0) < 0]

            avg_win = sum(wins) / len(wins) if wins else 0
            avg_loss = sum(losses) / len(losses) if losses else 0

            return {
                'total_trades': total_trades,
                'winning_trades': winning,
                'losing_trades': losing,
                'win_rate': (winning / total_trades * 100) if total_trades > 0 else 0,
                'total_pnl': total_pnl,
                'avg_pnl': avg_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': (avg_win / avg_loss) if avg_loss > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting performance: {e}")
            return None
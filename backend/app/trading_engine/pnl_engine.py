"""
P&L Engine
==========
Calculates realized P&L, unrealized P&L, day P&L, and portfolio metrics.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .engine import TradingEngine, Position, Trade, get_trading_engine
from .position_manager import PositionManager, get_position_manager

logger = logging.getLogger('pnl_engine')


class PnLEngine:
    """
    Real-time P&L calculation engine.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.position_manager = get_position_manager()
        self.logger = logging.getLogger('pnl_engine')
        
        self._pnl_callbacks: Dict[str, List[callable]] = defaultdict(list)
        self._last_pnl_cache: Dict[str, Dict] = {}
    
    def register_pnl_callback(self, user_id: str, callback: callable) -> None:
        self._pnl_callbacks[user_id].append(callback)
    
    async def _notify_pnl_update(self, user_id: str, pnl_data: Dict) -> None:
        for callback in self._pnl_callbacks.get(user_id, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(user_id, pnl_data)
                else:
                    callback(user_id, pnl_data)
            except Exception as e:
                self.logger.error(f"PnL callback error: {e}")
    
    def calculate_day_pnl(self, user_id: str, mode: str = "paper") -> Dict:
        trades = self.engine.get_user_trades(user_id)
        mode_trades = [t for t in trades if t.mode == mode]
        
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        day_trades = [t for t in mode_trades if t.execution_time and t.execution_time >= today_start]
        
        buy_value = sum(t.value for t in day_trades if t.transaction_type == "BUY")
        sell_value = sum(t.value for t in day_trades if t.transaction_type == "SELL")
        
        total_brokerage = sum(t.brokerage for t in day_trades)
        total_taxes = t.stt + t.gst + t.stamp_duty for t in day_trades
        
        day_pnl = (sell_value - buy_value) - total_brokerage - total_taxes
        
        day_trades_count = len(day_trades)
        winning_trades = len([t for t in day_trades if t.pnl and t.pnl > 0])
        losing_trades = len([t for t in day_trades if t.pnl and t.pnl < 0])
        
        return {
            'day_pnl': round(day_pnl, 2),
            'buy_value': round(buy_value, 2),
            'sell_value': round(sell_value, 2),
            'brokerage': round(total_brokerage, 2),
            'taxes': round(sum(t.stt + t.gst + t.stamp_duty for t in day_trades), 2),
            'trades_count': day_trades_count,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round((winning_trades / day_trades_count * 100) if day_trades_count > 0 else 0, 2),
        }
    
    def calculate_realized_pnl(self, user_id: str, mode: str = "paper", 
                               from_date: Optional[datetime] = None,
                               to_date: Optional[datetime] = None) -> Dict:
        positions = self.engine.get_user_positions(user_id)
        mode_positions = [p for p in positions if p.mode == mode]
        
        if from_date:
            mode_positions = [p for p in mode_positions if p.closed_at and p.closed_at >= from_date]
        if to_date:
            mode_positions = [p for p in mode_positions if p.closed_at and p.closed_at <= to_date]
        
        total_realized = sum(p.realized_pnl for p in mode_positions)
        
        closed_positions_count = len([p for p in mode_positions if p.status == "CLOSED"])
        winning_positions = len([p for p in mode_positions if p.realized_pnl > 0])
        losing_positions = len([p for p in mode_positions if p.realized_pnl < 0])
        
        return {
            'total_realized_pnl': round(total_realized, 2),
            'closed_positions': closed_positions_count,
            'winning_positions': winning_positions,
            'losing_positions': losing_positions,
            'win_rate': round((winning_positions / closed_positions_count * 100) if closed_positions_count > 0 else 0, 2),
        }
    
    def calculate_unrealized_pnl(self, user_id: str, mode: str = "paper") -> Dict:
        positions = self.engine.get_user_positions(user_id)
        open_positions = [p for p in positions if p.mode == mode and p.status == "OPEN"]
        
        total_unrealized = sum(p.unrealized_pnl for p in open_positions)
        
        profitable_positions = len([p for p in open_positions if p.unrealized_pnl > 0])
        loss_positions = len([p for p in open_positions if p.unrealized_pnl < 0])
        
        return {
            'total_unrealized_pnl': round(total_unrealized, 2),
            'open_positions': len(open_positions),
            'profitable_positions': profitable_positions,
            'loss_positions': loss_positions,
        }
    
    def calculate_total_pnl(self, user_id: str, mode: str = "paper") -> Dict:
        realized = self.calculate_realized_pnl(user_id, mode)
        unrealized = self.calculate_unrealized_pnl(user_id, mode)
        day_pnl = self.calculate_day_pnl(user_id, mode)
        
        total_pnl = realized['total_realized_pnl'] + unrealized['total_unrealized_pnl']
        
        return {
            'total_pnl': round(total_pnl, 2),
            'realized_pnl': realized['total_realized_pnl'],
            'unrealized_pnl': unrealized['total_unrealized_pnl'],
            'day_pnl': day_pnl['day_pnl'],
            'mode': mode,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def calculate_strategy_pnl(self, user_id: str, strategy_id: str, mode: str = "paper") -> Dict:
        positions = [p for p in self.engine.get_user_positions(user_id) 
                     if p.mode == mode and p.strategy_id == strategy_id]
        
        open_positions = [p for p in positions if p.status == "OPEN"]
        closed_positions = [p for p in positions if p.status == "CLOSED"]
        
        realized = sum(p.realized_pnl for p in closed_positions)
        unrealized = sum(p.unrealized_pnl for p in open_positions)
        
        return {
            'strategy_id': strategy_id,
            'total_pnl': round(realized + unrealized, 2),
            'realized_pnl': round(realized, 2),
            'unrealized_pnl': round(unrealized, 2),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
        }
    
    def calculate_portfolio_value(self, user_id: str, mode: str = "paper",
                                   cash_balance: float = 0) -> Dict:
        positions = self.engine.get_user_positions(user_id)
        open_positions = [p for p in positions if p.mode == mode and p.status == "OPEN"]
        
        position_value = sum(p.current_price * p.quantity for p in open_positions)
        position_cost = sum(p.average_price * p.quantity for p in open_positions)
        
        unrealized_pnl = sum(p.unrealized_pnl for p in open_positions)
        
        return {
            'cash_balance': round(cash_balance, 2),
            'position_value': round(position_value, 2),
            'position_cost': round(position_cost, 2),
            'unrealized_pnl': round(unrealized_pnl, 2),
            'portfolio_value': round(cash_balance + position_value, 2),
            'total_invested': round(position_cost, 2),
            'pnl_percent': round(((position_value - position_cost) / position_cost * 100) if position_cost > 0 else 0, 2),
        }
    
    async def update_pnl_realtime(self, user_id: str, mode: str = "paper", 
                                  cash_balance: float = 100000) -> Dict:
        total_pnl = self.calculate_total_pnl(user_id, mode)
        portfolio = self.calculate_portfolio_value(user_id, mode, cash_balance)
        day_pnl = self.calculate_day_pnl(user_id, mode)
        
        pnl_data = {
            'user_id': user_id,
            'mode': mode,
            'total_pnl': total_pnl['total_pnl'],
            'realized_pnl': total_pnl['realized_pnl'],
            'unrealized_pnl': total_pnl['unrealized_pnl'],
            'day_pnl': day_pnl['day_pnl'],
            'portfolio_value': portfolio['portfolio_value'],
            'cash_balance': portfolio['cash_balance'],
            'position_value': portfolio['position_value'],
            'margin_used': 0,
            'available_cash': cash_balance,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        self._last_pnl_cache[user_id] = pnl_data
        
        await self._notify_pnl_update(user_id, pnl_data)
        
        return pnl_data
    
    def get_last_pnl(self, user_id: str) -> Optional[Dict]:
        return self._last_pnl_cache.get(user_id)
    
    def calculate_sector_exposure(self, user_id: str, mode: str = "paper") -> Dict:
        positions = self.engine.get_user_positions(user_id)
        open_positions = [p for p in positions if p.mode == mode and p.status == "OPEN"]
        
        sector_map = {
            'RELIANCE': 'Energy', 'ONGC': 'Energy', 'TATASTEEL': 'Metals',
            'HINDALCO': 'Metals', 'JSWSTEEL': 'Metals',
            'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'TECHM': 'IT',
            'HDFCBANK': 'Finance', 'ICICIBANK': 'Finance', 'SBIN': 'Finance',
            'KOTAKBANK': 'Finance', 'AXISBANK': 'Finance',
            'BHARTIARTL': 'Telecom', 'ITC': 'FMCG',
            'MARUTI': 'Automobile', 'TATAMOTORS': 'Automobile',
        }
        
        sector_values = defaultdict(float)
        for pos in open_positions:
            sector = sector_map.get(pos.symbol, 'Other')
            sector_values[sector] += pos.current_price * pos.quantity
        
        total_value = sum(sector_values.values())
        
        sector_exposure = {}
        for sector, value in sector_values.items():
            sector_exposure[sector] = {
                'value': round(value, 2),
                'percent': round((value / total_value * 100) if total_value > 0 else 0, 2)
            }
        
        return sector_exposure


pnl_engine = PnLEngine()


def get_pnl_engine() -> PnLEngine:
    return pnl_engine
"""
Portfolio Manager
=================
Manages portfolio summary, holdings, and performance tracking.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .engine import TradingEngine, Position, Trade, get_trading_engine
from .position_manager import PositionManager, get_position_manager
from .pnl_engine import PnLEngine, get_pnl_engine
from .margin_engine import MarginEngine, get_margin_engine

logger = logging.getLogger('portfolio_manager')


class PortfolioManager:
    """
    Manages portfolio holdings, summary, and performance metrics.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.position_manager = get_position_manager()
        self.pnl_engine = get_pnl_engine()
        self.margin_engine = get_margin_engine()
        self.logger = logging.getLogger('portfolio_manager')
    
    def get_holdings_summary(self, user_id: str, mode: str = "paper") -> Dict:
        positions = self.engine.get_user_positions(user_id)
        cnc_positions = [p for p in positions if p.mode == mode and p.product_type == "CNC"]
        
        holdings = []
        total_value = 0
        total_cost = 0
        
        for pos in cnc_positions:
            current_value = pos.current_price * pos.quantity
            cost_value = pos.average_price * pos.quantity
            pnl = current_value - cost_value
            pnl_percent = (pnl / cost_value * 100) if cost_value > 0 else 0
            
            holdings.append({
                'symbol': pos.symbol,
                'quantity': pos.quantity,
                'average_price': round(pos.average_price, 2),
                'current_price': round(pos.current_price, 2),
                'value': round(current_value, 2),
                'cost': round(cost_value, 2),
                'pnl': round(pnl, 2),
                'pnl_percent': round(pnl_percent, 2),
            })
            
            total_value += current_value
            total_cost += cost_value
        
        return {
            'holdings': holdings,
            'total_value': round(total_value, 2),
            'total_cost': round(total_cost, 2),
            'total_pnl': round(total_value - total_cost, 2),
            'pnl_percent': round(((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0, 2),
            'count': len(holdings)
        }
    
    def get_intraday_summary(self, user_id: str, mode: str = "paper") -> Dict:
        trades = self.engine.get_user_trades(user_id)
        mode_trades = [t for t in trades if t.mode == mode]
        
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        day_trades = [t for t in mode_trades if t.execution_time and t.execution_time >= today_start]
        
        buy_trades = [t for t in day_trades if t.transaction_type == "BUY"]
        sell_trades = [t for t in day_trades if t.transaction_type == "SELL"]
        
        total_buy_value = sum(t.value for t in buy_trades)
        total_sell_value = sum(t.value for t in sell_trades)
        
        total_brokerage = sum(t.brokerage for t in day_trades)
        total_taxes = sum(t.stt + t.gst + t.stamp_duty for t in day_trades)
        
        day_pnl = (total_sell_value - total_buy_value) - total_brokerage - total_taxes
        
        symbols_traded = list(set(t.symbol for t in day_trades))
        
        return {
            'trades_count': len(day_trades),
            'buy_trades': len(buy_trades),
            'sell_trades': len(sell_trades),
            'total_buy_value': round(total_buy_value, 2),
            'total_sell_value': round(total_sell_value, 2),
            'brokerage': round(total_brokerage, 2),
            'taxes': round(total_taxes, 2),
            'day_pnl': round(day_pnl, 2),
            'symbols_traded': symbols_traded,
            'unique_symbols': len(symbols_traded)
        }
    
    def get_strategy_performance(self, user_id: str, mode: str = "paper") -> Dict:
        positions = self.engine.get_user_positions(user_id)
        mode_positions = [p for p in positions if p.mode == mode]
        
        strategy_performance = defaultdict(lambda: {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'realized_pnl': 0,
            'unrealized_pnl': 0,
            'total_pnl': 0
        })
        
        for pos in mode_positions:
            strategy_id = pos.strategy_id or "manual"
            perf = strategy_performance[strategy_id]
            
            perf['total_trades'] += 1
            
            if pos.status == "CLOSED":
                if pos.realized_pnl > 0:
                    perf['winning_trades'] += 1
                else:
                    perf['losing_trades'] += 1
                perf['realized_pnl'] += pos.realized_pnl
            else:
                perf['unrealized_pnl'] += pos.unrealized_pnl
            
            perf['total_pnl'] = perf['realized_pnl'] + perf['unrealized_pnl']
        
        result = {}
        for strategy_id, perf in strategy_performance.items():
            total = perf['winning_trades'] + perf['losing_trades']
            result[strategy_id] = {
                'total_trades': perf['total_trades'],
                'winning_trades': perf['winning_trades'],
                'losing_trades': perf['losing_trades'],
                'win_rate': round((perf['winning_trades'] / total * 100) if total > 0 else 0, 2),
                'realized_pnl': round(perf['realized_pnl'], 2),
                'unrealized_pnl': round(perf['unrealized_pnl'], 2),
                'total_pnl': round(perf['total_pnl'], 2)
            }
        
        return result
    
    def get_complete_portfolio(self, user_id: str, mode: str = "paper",
                              cash_balance: float = 100000) -> Dict:
        holdings = self.get_holdings_summary(user_id, mode)
        intraday = self.get_intraday_summary(user_id, mode)
        pnl = self.pnl_engine.calculate_total_pnl(user_id, mode)
        margin = self.margin_engine.get_margin_info(user_id)
        exposure = self.margin_engine.calculate_exposure(user_id)
        
        return {
            'mode': mode,
            'cash_balance': cash_balance,
            'holdings': holdings,
            'intraday': intraday,
            'pnl': pnl,
            'margin': margin.to_dict(),
            'exposure': exposure,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    
    def get_performance_metrics(self, user_id: str, mode: str = "paper",
                               period: str = "day") -> Dict:
        positions = self.engine.get_user_positions(user_id)
        mode_positions = [p for p in positions if p.mode == mode]
        
        if period == "day":
            start_date = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
        elif period == "week":
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        elif period == "month":
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        else:
            start_date = None
        
        if start_date:
            period_positions = [
                p for p in mode_positions 
                if p.opened_at and p.opened_at >= start_date
            ]
        else:
            period_positions = mode_positions
        
        if not period_positions:
            return {
                'period': period,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_pnl_per_trade': 0,
                'max_drawdown': 0
            }
        
        closed_positions = [p for p in period_positions if p.status == "CLOSED"]
        
        winning = [p for p in closed_positions if p.realized_pnl > 0]
        losing = [p for p in closed_positions if p.realized_pnl < 0]
        
        total_pnl = sum(p.realized_pnl for p in closed_positions)
        
        return {
            'period': period,
            'total_trades': len(closed_positions),
            'winning_trades': len(winning),
            'losing_trades': len(losing),
            'win_rate': round((len(winning) / len(closed_positions) * 100) if closed_positions else 0, 2),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl_per_trade': round(total_pnl / len(closed_positions), 2) if closed_positions else 0,
            'max_win': round(max(p.realized_pnl for p in winning), 2) if winning else 0,
            'max_loss': round(min(p.realized_pnl for p in losing), 2) if losing else 0,
            'avg_win': round(sum(p.realized_pnl for p in winning) / len(winning), 2) if winning else 0,
            'avg_loss': round(sum(p.realized_pnl for p in losing) / len(losing), 2) if losing else 0,
        }
    
    def get_trade_history(self, user_id: str, filters: Optional[Dict] = None,
                         limit: int = 50) -> List[Dict]:
        trades = self.engine.get_user_trades(user_id)
        
        if filters:
            if filters.get('symbol'):
                trades = [t for t in trades if t.symbol == filters['symbol'].upper()]
            if filters.get('from_date'):
                from_date = datetime.fromisoformat(filters['from_date'])
                trades = [t for t in trades if t.execution_time and t.execution_time >= from_date]
            if filters.get('to_date'):
                to_date = datetime.fromisoformat(filters['to_date'])
                trades = [t for t in trades if t.execution_time and t.execution_time <= to_date]
        
        trades = sorted(trades, key=lambda t: t.execution_time or datetime.min, reverse=True)
        
        return [t.to_dict() for t in trades[:limit]]


portfolio_manager = PortfolioManager()


def get_portfolio_manager() -> PortfolioManager:
    return portfolio_manager
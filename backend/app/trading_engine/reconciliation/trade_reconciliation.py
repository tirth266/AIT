"""
Reconciliation Engine
=====================
Trade and P&L reconciliation for consistency checks.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict

from ..engine import TradingEngine, Order, Position, Trade, get_trading_engine
from ..position_manager import PositionManager, get_position_manager
from ..pnl_engine import PnLEngine, get_pnl_engine
from ..margin_engine import MarginEngine, get_margin_engine

logger = logging.getLogger('reconciliation')


class ReconciliationResult:
    def __init__(self, is_balanced: bool, discrepancies: List[Dict], timestamp: datetime):
        self.is_balanced = is_balanced
        self.discrepancies = discrepancies
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict:
        return {
            'is_balanced': self.is_balanced,
            'discrepancies': self.discrepancies,
            'timestamp': self.timestamp.isoformat()
        }


class TradeReconciliation:
    """Reconciles trades and positions for consistency."""
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.position_manager = get_position_manager()
        self.pnl_engine = get_pnl_engine()
        self.margin_engine = get_margin_engine()
        self.logger = logging.getLogger('trade_reconciliation')
    
    def reconcile_user(self, user_id: str) -> ReconciliationResult:
        discrepancies = []
        
        orders = self.engine.get_user_orders(user_id)
        positions = self.engine.get_user_positions(user_id)
        trades = self.engine.get_user_trades(user_id)
        
        order_filled_qty = sum(o.filled_quantity for o in orders)
        trade_qty = sum(t.quantity for t in trades)
        
        if abs(order_filled_qty - trade_qty) > 0.01:
            discrepancies.append({
                'type': 'order_trade_mismatch',
                'order_filled_qty': order_filled_qty,
                'trade_qty': trade_qty,
                'difference': order_filled_qty - trade_qty
            })
        
        for trade in trades:
            if trade.position_id:
                position = self.engine.get_position(trade.position_id)
                if not position:
                    discrepancies.append({
                        'type': 'orphan_trade',
                        'trade_id': trade.trade_id,
                        'position_id': trade.position_id,
                        'message': 'Trade references non-existent position'
                    })
        
        position_qty = sum(p.quantity for p in positions if p.status == "OPEN")
        trades_in_positions = sum(
            t.quantity for t in trades 
            if t.position_id and any(p.position_id == t.position_id and p.status == "OPEN" for p in positions)
        )
        
        return ReconciliationResult(
            is_balanced=len(discrepancies) == 0,
            discrepancies=discrepancies,
            timestamp=datetime.now(timezone.utc)
        )
    
    def reconcile_pnl(self, user_id: str) -> ReconciliationResult:
        discrepancies = []
        
        positions = self.position_manager.get_open_positions(user_id)
        
        calculated_unrealized = sum(
            (p.current_price - p.average_price) * p.quantity 
            for p in positions if p.quantity > 0
        )
        
        stored_unrealized = sum(p.unrealized_pnl for p in positions)
        
        if abs(calculated_unrealized - stored_unrealized) > 0.01:
            discrepancies.append({
                'type': 'unrealized_pnl_mismatch',
                'calculated': calculated_unrealized,
                'stored': stored_unrealized,
                'difference': calculated_unrealized - stored_unrealized
            })
        
        realized_pnl = sum(p.realized_pnl for p in positions)
        
        trades = self.engine.get_user_trades(user_id)
        trade_pnl_sum = sum(t.pnl for t in trades if t.pnl is not None)
        
        if abs(realized_pnl - trade_pnl_sum) > 0.01:
            discrepancies.append({
                'type': 'realized_pnl_mismatch',
                'positions_pnl': realized_pnl,
                'trades_pnl': trade_pnl_sum,
                'difference': realized_pnl - trade_pnl_sum
            })
        
        return ReconciliationResult(
            is_balanced=len(discrepancies) == 0,
            discrepancies=discrepancies,
            timestamp=datetime.now(timezone.utc)
        )
    
    def reconcile_margin(self, user_id: str) -> ReconciliationResult:
        discrepancies = []
        
        margin_info = self.margin_engine.get_margin_info(user_id)
        
        positions = self.position_manager.get_open_positions(user_id)
        
        calculated_margin = sum(
            self.margin_engine.calculate_position_margin(
                p.quantity, p.current_price or p.average_price, p.product_type, p.exchange
            )
            for p in positions
        )
        
        if abs(calculated_margin - margin_info.used_margin) > 0.01:
            discrepancies.append({
                'type': 'margin_mismatch',
                'calculated': calculated_margin,
                'stored': margin_info.used_margin,
                'difference': calculated_margin - margin_info.used_margin
            })
        
        available_cash = margin_info.cash_balance - margin_info.used_margin
        if available_cash != margin_info.available_margin:
            discrepancies.append({
                'type': 'available_margin_mismatch',
                'calculated': available_cash,
                'stored': margin_info.available_margin
            })
        
        return ReconciliationResult(
            is_balanced=len(discrepancies) == 0,
            discrepancies=discrepancies,
            timestamp=datetime.now(timezone.utc)
        )
    
    def run_full_reconciliation(self, user_id: str) -> Dict:
        trade_result = self.reconcile_user(user_id)
        pnl_result = self.reconcile_pnl(user_id)
        margin_result = self.reconcile_margin(user_id)
        
        all_discrepancies = (
            trade_result.discrepancies + 
            pnl_result.discrepancies + 
            margin_result.discrepancies
        )
        
        return {
            'user_id': user_id,
            'is_balanced': len(all_discrepancies) == 0,
            'trade_reconciliation': trade_result.to_dict(),
            'pnl_reconciliation': pnl_result.to_dict(),
            'margin_reconciliation': margin_result.to_dict(),
            'total_discrepancies': len(all_discrepancies),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


class ExecutionLog:
    """Logs execution events for audit trail."""
    
    def __init__(self):
        self._logs: List[Dict] = []
        self.logger = logging.getLogger('execution_log')
    
    def log_order_submit(self, order: Order) -> None:
        self._logs.append({
            'event': 'order_submit',
            'order_id': order.order_id,
            'user_id': order.user_id,
            'symbol': order.symbol,
            'quantity': order.quantity,
            'price': order.price,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def log_order_fill(self, order: Order, trade: Trade) -> None:
        self._logs.append({
            'event': 'order_fill',
            'order_id': order.order_id,
            'trade_id': trade.trade_id,
            'user_id': order.user_id,
            'symbol': order.symbol,
            'filled_quantity': trade.quantity,
            'fill_price': trade.price,
            'brokerage': trade.brokerage,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def log_position_update(self, position: Position) -> None:
        self._logs.append({
            'event': 'position_update',
            'position_id': position.position_id,
            'user_id': position.user_id,
            'symbol': position.symbol,
            'quantity': position.quantity,
            'current_price': position.current_price,
            'pnl': position.unrealized_pnl,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def log_margin_update(self, user_id: str, margin_info: Dict) -> None:
        self._logs.append({
            'event': 'margin_update',
            'user_id': user_id,
            'available_margin': margin_info.get('available_margin'),
            'used_margin': margin_info.get('used_margin'),
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
    
    def get_logs(self, user_id: Optional[str] = None, 
                event_type: Optional[str] = None, 
                limit: int = 100) -> List[Dict]:
        logs = self._logs
        
        if user_id:
            logs = [l for l in logs if l.get('user_id') == user_id]
        if event_type:
            logs = [l for l in logs if l.get('event') == event_type]
        
        return logs[-limit:]


trade_reconciliation = TradeReconciliation()
execution_log = ExecutionLog()


def get_trade_reconciliation() -> TradeReconciliation:
    return trade_reconciliation


def get_execution_log() -> ExecutionLog:
    return execution_log
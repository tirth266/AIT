"""
Position Manager
================
Manages open positions, updates, and lifecycle.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .engine import (
    TradingEngine, Position, Order, Trade, 
    TransactionType, get_trading_engine
)
from .order_manager import OrderManager, get_order_manager
from .execution_engine import ExecutionEngine, get_execution_engine

logger = logging.getLogger('position_manager')


class PositionManager:
    """
    Manages positions - creation, updates, MTM, and closing.
    """
    
    def __init__(self, engine: Optional[TradingEngine] = None):
        self.engine = engine or get_trading_engine()
        self.order_manager = get_order_manager()
        self.execution_engine = get_execution_engine()
        self.logger = logging.getLogger('position_manager')
        
        self._position_update_callbacks: List[callable] = []
    
    def register_position_callback(self, callback: callable) -> None:
        self._position_update_callbacks.append(callback)
    
    async def _notify_position_update(self, position: Position) -> None:
        for callback in self._position_update_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(position)
                else:
                    callback(position)
            except Exception as e:
                self.logger.error(f"Position callback error: {e}")
    
    async def process_order_fill(self, order: Order, trade: Trade) -> Optional[Position]:
        user_id = order.user_id
        symbol = order.symbol
        product_type = order.product_type
        
        existing_position = self.engine.get_open_position(user_id, symbol, product_type)
        
        if order.transaction_type == TransactionType.BUY.value:
            position = await self._handle_buy_order(order, trade, existing_position)
        else:
            position = await self._handle_sell_order(order, trade, existing_position)
        
        return position
    
    async def _handle_buy_order(self, order: Order, trade: Trade, 
                                existing: Optional[Position]) -> Position:
        if existing:
            new_quantity = existing.quantity + trade.quantity
            new_value = (existing.average_price * existing.quantity) + (trade.price * trade.quantity)
            existing.average_price = new_value / new_quantity if new_quantity > 0 else 0
            existing.quantity = new_quantity
            existing.updated_at = datetime.now(timezone.utc)
            
            position = existing
            self.logger.info(f"Position updated: {position.position_id} - Qty: {new_quantity}")
        else:
            position_id = self.engine.generate_position_id()
            
            position = Position(
                position_id=position_id,
                user_id=order.user_id,
                strategy_id=order.strategy_id,
                symbol=order.symbol,
                exchange=order.exchange,
                product_type=order.product_type,
                quantity=trade.quantity,
                average_price=trade.price,
                current_price=trade.price,
                entry_price=trade.price,
                opened_at=datetime.now(timezone.utc),
                mode=order.mode,
                status="OPEN",
            )
            
            self.engine.positions[position_id] = position
            self.engine.user_positions[order.user_id][position_id] = position
            
            self.logger.info(f"Position created: {position_id} - BUY {trade.quantity} {order.symbol} @ {trade.price}")
        
        await self._notify_position_update(position)
        return position
    
    async def _handle_sell_order(self, order: Order, trade: Trade,
                                  existing: Optional[Position]) -> Optional[Position]:
        if not existing:
            return None
        
        if order.product_type != "CNC" and trade.quantity > existing.quantity:
            trade_quantity = existing.quantity
        else:
            trade_quantity = trade.quantity
        
        closed_value = trade.price * trade_quantity
        cost_basis = existing.average_price * trade_quantity
        realized_pnl = closed_value - cost_basis - trade.brokerage - trade.stt
        
        existing.quantity -= trade_quantity
        existing.realized_pnl += realized_pnl
        existing.closed_quantity += trade_quantity
        
        if existing.quantity <= 0:
            existing.status = "CLOSED"
            existing.closed_at = datetime.now(timezone.utc)
            self.logger.info(f"Position closed: {existing.position_id} - PnL: {realized_pnl:.2f}")
        else:
            self.logger.info(f"Position partially closed: {existing.position_id} - Remaining: {existing.quantity}")
        
        existing.updated_at = datetime.now(timezone.utc)
        
        await self._notify_position_update(existing)
        
        return existing
    
    async def close_position(self, position_id: str, exit_price: float, 
                            exit_quantity: Optional[int] = None) -> tuple[Optional[Position], Optional[Trade]]:
        position = self.engine.get_position(position_id)
        if not position:
            return None, None
        
        if position.status != "OPEN":
            return None, None
        
        exit_qty = exit_quantity or position.quantity
        
        trade = Trade(
            trade_id=self.engine.generate_trade_id(),
            user_id=position.user_id,
            order_id="",
            position_id=position_id,
            strategy_id=position.strategy_id,
            symbol=position.symbol,
            exchange=position.exchange,
            transaction_type="SELL",
            quantity=exit_qty,
            price=exit_price,
            value=exit_price * exit_qty,
            execution_time=datetime.now(timezone.utc),
            mode=position.mode,
        )
        
        cost_basis = position.average_price * exit_qty
        trade.pnl = exit_price * exit_qty - cost_basis - trade.brokerage - trade.stt
        trade.pnl_percent = (trade.pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        position.quantity -= exit_qty
        position.realized_pnl += trade.pnl
        position.closed_quantity += exit_qty
        
        if position.quantity <= 0:
            position.status = "CLOSED"
            position.closed_at = datetime.now(timezone.utc)
        else:
            position.current_price = exit_price
        
        position.updated_at = datetime.now(timezone.utc)
        
        self.engine.trades[trade.trade_id] = trade
        self.engine.user_positions[position.user_id][trade.trade_id] = trade
        
        await self._notify_position_update(position)
        
        self.logger.info(f"Position exited: {position_id} - Exit: {exit_price}, PnL: {trade.pnl:.2f}")
        
        return position, trade
    
    async def update_mtm(self, symbol: str, current_price: float) -> List[Position]:
        updated_positions = []
        
        for position in self.engine.positions.values():
            if position.symbol == symbol and position.status == "OPEN":
                position.current_price = current_price
                position.mtm_updated_at = datetime.now(timezone.utc)
                
                if position.average_price > 0:
                    position.unrealized_pnl = (current_price - position.average_price) * position.quantity
                    
                    if position.transaction_type == "SELL":
                        position.unrealized_pnl *= -1
                    
                    position.unrealized_pnl -= position.brokerage
                
                updated_positions.append(position)
                
                await self._notify_position_update(position)
        
        return updated_positions
    
    async def update_all_positions_mtm(self) -> Dict[str, List[Position]]:
        all_updates = defaultdict(list)
        
        symbols = set(p.symbol for p in self.engine.positions.values() if p.status == "OPEN")
        
        for symbol in symbols:
            market_price = self.engine.get_market_price(symbol)
            if market_price:
                updates = await self.update_mtm(symbol, market_price)
                all_updates[symbol] = updates
        
        return all_updates
    
    def get_user_positions(self, user_id: str, filters: Optional[Dict] = None) -> List[Position]:
        positions = self.engine.get_user_positions(user_id)
        
        if not filters:
            return positions
        
        filtered = []
        for pos in positions:
            if filters.get('status') and pos.status != filters['status']:
                continue
            if filters.get('symbol') and pos.symbol != filters['symbol'].upper():
                continue
            if filters.get('product_type') and pos.product_type != filters['product_type']:
                continue
            if filters.get('mode') and pos.mode != filters['mode']:
                continue
            filtered.append(pos)
        
        return filtered
    
    def get_position(self, position_id: str) -> Optional[Position]:
        return self.engine.get_position(position_id)
    
    def get_open_positions(self, user_id: str) -> List[Position]:
        return [p for p in self.engine.get_user_positions(user_id) if p.status == "OPEN"]
    
    def get_closed_positions(self, user_id: str) -> List[Position]:
        return [p for p in self.engine.get_user_positions(user_id) if p.status == "CLOSED"]
    
    def get_position_summary(self, user_id: str, mode: str = "paper") -> Dict:
        positions = [p for p in self.engine.get_user_positions(user_id) if p.mode == mode]
        
        open_positions = [p for p in positions if p.status == "OPEN"]
        closed_positions = [p for p in positions if p.status == "CLOSED"]
        
        total_realized = sum(p.realized_pnl for p in positions)
        total_unrealized = sum(p.unrealized_pnl for p in open_positions)
        
        total_value = sum(p.current_price * p.quantity for p in open_positions)
        total_cost = sum(p.average_price * p.quantity for p in open_positions)
        
        return {
            'total_positions': len(positions),
            'open_positions': len(open_positions),
            'closed_positions': len(closed_positions),
            'total_realized_pnl': round(total_realized, 2),
            'total_unrealized_pnl': round(total_unrealized, 2),
            'total_pnl': round(total_realized + total_unrealized, 2),
            'total_value': round(total_value, 2),
            'total_cost': round(total_cost, 2),
            'pnl_percent': round(((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0, 2),
            'mode': mode
        }


position_manager = PositionManager()


def get_position_manager() -> PositionManager:
    return position_manager
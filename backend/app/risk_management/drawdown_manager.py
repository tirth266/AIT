"""
Drawdown Manager
================
Track and protect against drawdowns.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class DrawdownType(str, Enum):
    DAILY = "daily"
    TRAILING = "trailing"
    PEAK_TO_TROUGH = "peak_to_trough"


class DrawdownAction(str, Enum):
    WARN = "warn"
    STOP_STRATEGY = "stop_strategy"
    CLOSE_POSITIONS = "close_positions"
    DISABLE_TRADING = "disable_trading"


@dataclass
class DrawdownState:
    user_id: str
    peak_equity: float
    current_equity: float
    drawdown_amount: float
    drawdown_percent: float
    daily_pnl: float
    daily_peak: float
    daily_trough: float
    trailing_peak: float
    trailing_drawdown_percent: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DrawdownLimit:
    max_daily_loss: float = 5000.0
    max_daily_loss_percent: float = 5.0
    max_trailing_drawdown: float = 10.0
    max_equity_drawdown: float = 15.0


class DrawdownManager:
    """
    Manages drawdown tracking and protection.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('drawdown_manager')
        self.risk_engine = risk_engine
        
        self._drawdown_states: Dict[str, DrawdownState] = {}
        self._limits: Dict[str, DrawdownLimit] = defaultdict(DrawdownLimit)
        
        self._daily_reset_time = datetime.now(timezone.utc).replace(
            hour=15, minute=30, second=0, microsecond=0
        )
        
        self._last_equity: Dict[str, float] = {}
        self._equity_history: Dict[str, List[float]] = defaultdict(list)
        
        self._actions_triggered: Dict[str, set] = defaultdict(set)
    
    def set_limit(self, user_id: str, limit: DrawdownLimit) -> None:
        self._limits[user_id] = limit
    
    def get_limit(self, user_id: str) -> DrawdownLimit:
        if user_id not in self._limits:
            self._limits[user_id] = DrawdownLimit()
        return self._limits[user_id]
    
    async def update_equity(self, user_id: str, equity: float, pnl: float = 0,
                           positions: List[Dict] = None) -> DrawdownState:
        if user_id not in self._drawdown_states:
            self._initialize_drawdown(user_id, equity)
        
        state = self._drawdown_states[user_id]
        
        state.current_equity = equity
        state.daily_pnl = pnl
        
        if equity > state.daily_peak:
            state.daily_peak = equity
        
        if pnl < state.daily_trough:
            state.daily_trough = pnl
        
        if equity > state.peak_equity:
            state.peak_equity = equity
            state.trailing_peak = equity
        
        state.drawdown_amount = state.peak_equity - equity
        
        if state.peak_equity > 0:
            state.drawdown_percent = (state.drawdown_amount / state.peak_equity) * 100
        
        if state.trailing_peak > 0:
            state.trailing_drawdown_percent = (
                (state.trailing_peak - equity) / state.trailing_peak * 100
            )
        
        state.timestamp = datetime.now(timezone.utc)
        
        self._equity_history[user_id].append(equity)
        if len(self._equity_history[user_id]) > 1000:
            self._equity_history[user_id] = self._equity_history[user_id][-500:]
        
        self._last_equity[user_id] = equity
        
        await self._check_drawdown_limits(user_id, state, positions)
        
        return state
    
    def _initialize_drawdown(self, user_id: str, equity: float) -> None:
        self._drawdown_states[user_id] = DrawdownState(
            user_id=user_id,
            peak_equity=equity,
            current_equity=equity,
            drawdown_amount=0,
            drawdown_percent=0,
            daily_pnl=0,
            daily_peak=equity,
            daily_trough=0,
            trailing_peak=equity,
            trailing_drawdown_percent=0
        )
    
    async def _check_drawdown_limits(self, user_id: str, state: DrawdownState,
                                     positions: List[Dict] = None) -> None:
        limit = self.get_limit(user_id)
        
        action_key = f"{user_id}:daily_loss"
        if abs(state.daily_pnl) >= limit.max_daily_loss:
            if action_key not in self._actions_triggered[user_id]:
                self._actions_triggered[user_id].add(action_key)
                await self._trigger_action(user_id, DrawdownAction.STOP_STRATEGY,
                    f"Daily loss {state.daily_pnl:.2f} exceeds limit {limit.max_daily_loss}")
                await self._trigger_action(user_id, DrawdownAction.WARN,
                    f"Daily loss limit hit: {state.daily_pnl:.2f}")
        
        action_key = f"{user_id}:daily_loss_pct"
        if state.daily_peak > 0:
            daily_loss_pct = abs(state.daily_pnl) / state.daily_peak * 100
            if daily_loss_pct >= limit.max_daily_loss_percent:
                if action_key not in self._actions_triggered[user_id]:
                    self._actions_triggered[user_id].add(action_key)
                    await self._trigger_action(user_id, DrawdownAction.WARN,
                        f"Daily loss {daily_loss_pct:.1f}% exceeds {limit.max_daily_loss_percent}%")
        
        action_key = f"{user_id}:trailing"
        if state.trailing_drawdown_percent >= limit.max_trailing_drawdown:
            if action_key not in self._actions_triggered[user_id]:
                self._actions_triggered[user_id].add(action_key)
                await self._trigger_action(user_id, DrawdownAction.STOP_STRATEGY,
                    f"Trailing drawdown {state.trailing_drawdown_percent:.1f}% exceeds limit")
                await self._trigger_action(user_id, DrawdownAction.WARN,
                    f"Trailing drawdown CRITICAL: {state.trailing_drawdown_percent:.1f}%")
        
        action_key = f"{user_id}:equity_drawdown"
        if state.drawdown_percent >= limit.max_equity_drawdown:
            if action_key not in self._actions_triggered[user_id]:
                self._actions_triggered[user_id].add(action_key)
                await self._trigger_action(user_id, DrawdownAction.CLOSE_POSITIONS,
                    f"Equity drawdown {state.drawdown_percent:.1f}% exceeds limit")
                await self._trigger_action(user_id, DrawdownAction.DISABLE_TRADING,
                    f"Max drawdown exceeded: {state.drawdown_percent:.1f}%")
    
    async def _trigger_action(self, user_id: str, action: DrawdownAction, message: str) -> None:
        self.logger.warning(f"Drawdown action for {user_id}: {action.value} - {message}")
        
        if self.risk_engine:
            await self.risk_engine.log_event({
                'event_type': 'drawdown_action',
                'user_id': user_id,
                'action': action.value,
                'message': message,
                'level': 'warning' if action == DrawdownAction.WARN else 'critical'
            })
        
        if action == DrawdownAction.WARN:
            pass
        elif action == DrawdownAction.STOP_STRATEGY:
            self._notify_strategy_manager(user_id, 'stop_all', message)
        elif action == DrawdownAction.CLOSE_POSITIONS:
            self._notify_trading_engine(user_id, 'close_all', message)
        elif action == DrawdownAction.DISABLE_TRADING:
            if self.risk_engine:
                self.risk_engine.update_state(user_id, risk_level='critical')
    
    def _notify_strategy_manager(self, user_id: str, action: str, reason: str) -> None:
        self.logger.info(f"Notifying strategy manager: {user_id} - {action}")
    
    def _notify_trading_engine(self, user_id: str, action: str, reason: str) -> None:
        self.logger.info(f"Notifying trading engine: {user_id} - {action}")
    
    def get_drawdown_state(self, user_id: str) -> Optional[DrawdownState]:
        return self._drawdown_states.get(user_id)
    
    def reset_drawdown_state(self, user_id: str) -> None:
        if user_id in self._drawdown_states:
            equity = self._drawdown_states[user_id].current_equity
            self._initialize_drawdown(user_id, equity)
        
        if user_id in self._actions_triggered:
            self._actions_triggered[user_id].clear()
    
    def reset_all_daily(self) -> None:
        for user_id in self._drawdown_states:
            equity = self._drawdown_states[user_id].current_equity
            self._initialize_drawdown(user_id, equity)
        
        self._actions_triggered.clear()
        self.logger.info("All daily drawdown states reset")
    
    def get_equity_history(self, user_id: str, limit: int = 100) -> List[float]:
        history = self._equity_history.get(user_id, [])
        return history[-limit:]
    
    def get_all_drawdown_states(self) -> List[Dict]:
        return [
            {
                'user_id': user_id,
                'peak_equity': state.peak_equity,
                'current_equity': state.current_equity,
                'drawdown_amount': round(state.drawdown_amount, 2),
                'drawdown_percent': round(state.drawdown_percent, 2),
                'daily_pnl': round(state.daily_pnl, 2),
                'daily_peak': state.daily_peak,
                'daily_trough': state.daily_trough,
                'trailing_drawdown_percent': round(state.trailing_drawdown_percent, 2),
                'timestamp': state.timestamp.isoformat()
            }
            for user_id, state in self._drawdown_states.items()
        ]


drawdown_manager = DrawdownManager()


def get_drawdown_manager() -> DrawdownManager:
    return drawdown_manager
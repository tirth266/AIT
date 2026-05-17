"""
Strategy Risk Engine
====================
Monitor and control strategy risk.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class StrategyRiskProfile:
    strategy_id: str
    user_id: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_win: float
    avg_loss: float
    largest_win: float
    largest_loss: float
    consecutive_wins: int
    consecutive_losses: int
    max_consecutive_losses: int
    avg_holding_time: float
    risk_score: float
    status: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StrategyLimits:
    max_concurrent_trades: int = 5
    max_capital_allocation: float = 50000.0
    max_loss_per_day: float = 2000.0
    max_trades_per_day: int = 20
    min_win_rate: float = 40.0
    max_consecutive_losses: int = 5


class StrategyRiskEngine:
    """
    Monitors and controls strategy risk.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('strategy_risk')
        self.risk_engine = risk_engine
        
        self._profiles: Dict[str, StrategyRiskProfile] = {}
        self._limits: Dict[str, StrategyLimits] = defaultdict(StrategyLimits)
        
        self._trade_history: Dict[str, List[Dict]] = defaultdict(list)
        self._active_trades: Dict[str, int] = defaultdict(int)
        
        self._disabled_strategies: set = set()
    
    def set_limits(self, strategy_id: str, limits: StrategyLimits) -> None:
        self._limits[strategy_id] = limits
    
    def get_limits(self, strategy_id: str) -> StrategyLimits:
        return self._limits.get(strategy_id, StrategyLimits())
    
    async def record_trade(self, strategy_id: str, user_id: str, trade: Dict) -> None:
        self._trade_history[strategy_id].append({
            **trade,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        if len(self._trade_history[strategy_id]) > 1000:
            self._trade_history[strategy_id] = self._trade_history[strategy_id][-500:]
    
    async def update_position(self, strategy_id: str, count: int) -> None:
        self._active_trades[strategy_id] = count
    
    async def calculate_risk_profile(self, strategy_id: str, user_id: str) -> StrategyRiskProfile:
        trades = self._trade_history.get(strategy_id, [])
        
        if not trades:
            return StrategyRiskProfile(
                strategy_id=strategy_id,
                user_id=user_id,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0,
                avg_win=0,
                avg_loss=0,
                largest_win=0,
                largest_loss=0,
                consecutive_wins=0,
                consecutive_losses=0,
                max_consecutive_losses=0,
                avg_holding_time=0,
                risk_score=50,
                status='active'
            )
        
        closed_trades = [t for t in trades if t.get('status') in ['closed', 'exited']]
        
        winning = [t for t in closed_trades if t.get('pnl', 0) > 0]
        losing = [t for t in closed_trades if t.get('pnl', 0) < 0]
        
        total_trades = len(closed_trades)
        win_rate = (len(winning) / total_trades * 100) if total_trades > 0 else 0
        
        avg_win = sum(t.get('pnl', 0) for t in winning) / len(winning) if winning else 0
        avg_loss = abs(sum(t.get('pnl', 0) for t in losing) / len(losing)) if losing else 0
        
        largest_win = max((t.get('pnl', 0) for t in winning), default=0)
        largest_loss = min((t.get('pnl', 0) for t in losing), default=0)
        
        consecutive_wins, consecutive_losses, max_consecutive = self._calculate_consecutive(closed_trades)
        
        avg_holding = 0
        if closed_trades:
            holding_times = []
            for t in closed_trades:
                entry = t.get('entry_time')
                exit = t.get('exit_time')
                if entry and exit:
                    try:
                        if isinstance(entry, str):
                            entry = datetime.fromisoformat(entry)
                        if isinstance(exit, str):
                            exit = datetime.fromisoformat(exit)
                        holding_times.append((exit - entry).total_seconds() / 60)
                    except:
                        pass
            if holding_times:
                avg_holding = sum(holding_times) / len(holding_times)
        
        risk_score = self._calculate_risk_score(win_rate, avg_win, avg_loss, 
                                                  max_consecutive, len(winning), len(losing))
        
        status = 'active'
        if strategy_id in self._disabled_strategies:
            status = 'disabled'
        
        profile = StrategyRiskProfile(
            strategy_id=strategy_id,
            user_id=user_id,
            total_trades=total_trades,
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=win_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            consecutive_wins=consecutive_wins,
            consecutive_losses=consecutive_losses,
            max_consecutive_losses=max_consecutive,
            avg_holding_time=avg_holding,
            risk_score=risk_score,
            status=status
        )
        
        self._profiles[strategy_id] = profile
        
        await self._check_strategy_limits(strategy_id, profile)
        
        return profile
    
    def _calculate_consecutive(self, trades: List[Dict]) -> tuple[int, int, int]:
        if not trades:
            return 0, 0, 0
        
        current_streak = 0
        max_streak = 0
        streak_type = None
        
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive = 0
        
        for trade in trades:
            pnl = trade.get('pnl', 0)
            
            if pnl > 0:
                if streak_type == 'win':
                    consecutive_wins += 1
                else:
                    consecutive_wins = 1
                    streak_type = 'win'
            elif pnl < 0:
                if streak_type == 'loss':
                    consecutive_losses += 1
                else:
                    consecutive_losses = 1
                    streak_type = 'loss'
            else:
                streak_type = None
            
            if streak_type == 'win':
                max_consecutive = max(max_consecutive, consecutive_wins)
            elif streak_type == 'loss':
                max_consecutive = max(max_consecutive, consecutive_losses)
        
        return consecutive_wins, consecutive_losses, max_consecutive
    
    def _calculate_risk_score(self, win_rate: float, avg_win: float, avg_loss: float,
                              max_consecutive: int, wins: int, losses: int) -> float:
        score = 50.0
        
        if win_rate < 30:
            score += 20
        elif win_rate < 40:
            score += 10
        
        if avg_loss > 0 and avg_win > 0:
            rr = avg_win / avg_loss if avg_loss > 0 else 0
            if rr < 1:
                score += 15
            elif rr < 1.5:
                score += 5
        
        if max_consecutive >= 5:
            score += 20
        elif max_consecutive >= 3:
            score += 10
        
        if losses > wins and losses > 5:
            score += 10
        
        return min(score, 100)
    
    async def _check_strategy_limits(self, strategy_id: str, profile: StrategyRiskProfile) -> None:
        limits = self.get_limits(strategy_id)
        
        if profile.max_consecutive_losses >= limits.max_consecutive_losses:
            await self.disable_strategy(strategy_id, "Max consecutive losses exceeded")
        
        elif profile.win_rate < limits.min_win_rate and profile.total_trades >= 10:
            await self.disable_strategy(strategy_id, f"Win rate {profile.win_rate:.1f}% below minimum")
        
        active_count = self._active_trades.get(strategy_id, 0)
        if active_count >= limits.max_concurrent_trades:
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'strategy_limit',
                    'strategy_id': strategy_id,
                    'message': f"Max concurrent trades reached: {active_count}",
                    'level': 'warning'
                })
    
    async def disable_strategy(self, strategy_id: str, reason: str) -> None:
        self._disabled_strategies.add(strategy_id)
        
        if strategy_id in self._profiles:
            self._profiles[strategy_id].status = 'disabled'
        
        if self.risk_engine:
            await self.risk_engine.log_event({
                'event_type': 'strategy_disabled',
                'strategy_id': strategy_id,
                'reason': reason,
                'level': 'warning'
            })
        
        self.logger.warning(f"Strategy {strategy_id} disabled: {reason}")
    
    async def enable_strategy(self, strategy_id: str) -> None:
        self._disabled_strategies.discard(strategy_id)
        
        if strategy_id in self._profiles:
            self._profiles[strategy_id].status = 'active'
        
        if self.risk_engine:
            await self.risk_engine.log_event({
                'event_type': 'strategy_enabled',
                'strategy_id': strategy_id,
                'level': 'info'
            })
    
    def is_strategy_allowed(self, strategy_id: str) -> bool:
        return strategy_id not in self._disabled_strategies
    
    def get_profile(self, strategy_id: str) -> Optional[StrategyRiskProfile]:
        return self._profiles.get(strategy_id)
    
    def get_all_profiles(self) -> List[Dict]:
        return [
            {
                'strategy_id': p.strategy_id,
                'user_id': p.user_id,
                'total_trades': p.total_trades,
                'win_rate': round(p.win_rate, 2),
                'avg_win': round(p.avg_win, 2),
                'avg_loss': round(p.avg_loss, 2),
                'consecutive_losses': p.consecutive_losses,
                'risk_score': round(p.risk_score, 2),
                'status': p.status,
                'timestamp': p.timestamp.isoformat()
            }
            for p in self._profiles.values()
        ]


strategy_risk_engine = StrategyRiskEngine()


def get_strategy_risk_engine() -> StrategyRiskEngine:
    return strategy_risk_engine
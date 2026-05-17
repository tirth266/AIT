"""
Portfolio Risk Aggregator
=========================
Real-time portfolio-wide risk aggregation across positions, strategies, and users.
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import logging

logger = logging.getLogger('risk_engine.portfolio')

from app.risk_management.analytics.var_engine import get_var_engine, VaRResult
from app.risk_management.analytics.stress_engine import get_stress_engine, StressResult
from app.risk_management.exposure_manager import get_exposure_manager, ExposureSnapshot


@dataclass
class StrategyRisk:
    """Risk metrics for a single strategy."""
    strategy_id: str
    strategy_name: str

    total_value: float
    pnl: float
    pnl_percent: float

    var_95: float
    var_99: float

    positions_count: int
    active_orders: int

    exposure_percent: float
    concentration_percent: float

    risk_score: float
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class UserRisk:
    """Comprehensive risk metrics for a user."""
    user_id: str

    total_portfolio_value: float
    cash_balance: float
    invested_value: float

    gross_exposure: float
    net_exposure: float
    leverage: float

    var_95: float
    var_99: float
    expected_shortfall: float

    daily_pnl: float
    weekly_pnl: float
    monthly_pnl: float

    margin_utilization: float
    margin_available: float

    open_positions: int
    active_strategies: int

    risk_level: str

    strategies: List[StrategyRisk]
    sector_exposure: Dict[str, float]
    position_exposure: Dict[str, float]

    heatmap_data: List[Dict]
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class PortfolioAggregator:
    """
    Aggregates portfolio-level risk across all positions and strategies.
    """

    def __init__(self):
        self.logger = logging.getLogger('portfolio_aggregator')

        self._var_engine = get_var_engine()
        self._stress_engine = get_stress_engine()
        self._exposure_manager = get_exposure_manager()

        self._user_risk: Dict[str, UserRisk] = {}
        self._strategy_risk: Dict[str, Dict[str, StrategyRisk]] = defaultdict(dict)

        self._price_cache: Dict[str, float] = {}
        self._correlation_matrix: Dict[str, Dict[str, float]] = {}

    async def calculate_portfolio_risk(
        self,
        user_id: str,
        positions: List[Dict],
        strategies: List[Dict],
        market_data: Dict[str, Dict],
        cash_balance: float,
        margin_state: Dict
    ) -> UserRisk:
        """Calculate complete portfolio risk for a user."""
        portfolio_value = cash_balance + sum(pos.get('value', 0) for pos in positions)

        positions_dict = {}
        for pos in positions:
            symbol = pos.get('symbol', '')
            positions_dict[symbol] = {
                'value': pos.get('value', 0),
                'quantity': pos.get('quantity', 0),
                'side': pos.get('side', 'BUY'),
                'sector': pos.get('sector', 'OTHER'),
                'beta': market_data.get(symbol, {}).get('beta', 1.0)
            }

        self._update_correlation_matrix(market_data)

        var_result = self._var_engine.calculate_historical_var(
            positions_dict,
            portfolio_value
        )

        strategy_risks = await self._calculate_strategy_risks(
            user_id, strategies, positions, market_data
        )

        sector_exposure = defaultdict(float)
        position_exposure = {}

        for pos in positions:
            symbol = pos.get('symbol', '')
            sector = pos.get('sector', 'OTHER')
            value = pos.get('value', 0)

            sector_exposure[sector] += value
            position_exposure[symbol] = value

        risk_level = self._calculate_risk_level(
            var_result.var_95,
            portfolio_value,
            margin_state.get('margin_utilization', 0),
            strategy_risks
        )

        heatmap_data = self._generate_heatmap_data(position_exposure, sector_exposure, portfolio_value)

        user_risk = UserRisk(
            user_id=user_id,
            total_portfolio_value=portfolio_value,
            cash_balance=cash_balance,
            invested_value=sum(pos.get('value', 0) for pos in positions),
            gross_exposure=sum(abs(pos.get('value', 0)) for pos in positions),
            net_exposure=sum(pos.get('value', 0) for pos in positions),
            leverage=(sum(abs(pos.get('value', 0)) for pos in positions) / portfolio_value) if portfolio_value > 0 else 0,
            var_95=var_result.var_95,
            var_99=var_result.var_99,
            expected_shortfall=var_result.expected_shortfall_95,
            daily_pnl=margin_state.get('daily_pnl', 0),
            weekly_pnl=margin_state.get('weekly_pnl', 0),
            monthly_pnl=margin_state.get('monthly_pnl', 0),
            margin_utilization=margin_state.get('margin_utilization', 0),
            margin_available=margin_state.get('margin_available', cash_balance),
            open_positions=len([p for p in positions if p.get('status') == 'OPEN']),
            active_strategies=len([s for s in strategies if s.get('status') == 'ACTIVE']),
            risk_level=risk_level,
            strategies=strategy_risks,
            sector_exposure=dict(sector_exposure),
            position_exposure=position_exposure,
            heatmap_data=heatmap_data
        )

        self._user_risk[user_id] = user_risk

        return user_risk

    async def _calculate_strategy_risks(
        self,
        user_id: str,
        strategies: List[Dict],
        positions: List[Dict],
        market_data: Dict[str, Dict]
    ) -> List[StrategyRisk]:
        """Calculate risk metrics for each strategy."""
        strategy_risks = []

        for strategy in strategies:
            strategy_id = strategy.get('strategy_id')
            strategy_positions = [p for p in positions if p.get('strategy_id') == strategy_id]

            strategy_value = sum(p.get('value', 0) for p in strategy_positions)
            strategy_pnl = sum(p.get('unrealized_pnl', 0) for p in strategy_positions)

            strategy_positions_dict = {
                p.get('symbol', ''): {
                    'value': p.get('value', 0),
                    'quantity': p.get('quantity', 0),
                    'side': p.get('side', 'BUY'),
                    'sector': p.get('sector', 'OTHER'),
                    'beta': market_data.get(p.get('symbol', ''), {}).get('beta', 1.0)
                }
                for p in strategy_positions
            }

            strategy_var = self._var_engine.calculate_historical_var(
                strategy_positions_dict,
                strategy_value
            )

            total_portfolio_value = sum(p.get('value', 0) for p in positions)
            exposure_percent = (strategy_value / total_portfolio_value * 100) if total_portfolio_value > 0 else 0

            sector_exp = defaultdict(float)
            for pos in strategy_positions:
                sector_exp[pos.get('sector', 'OTHER')] += pos.get('value', 0)
            concentration = max(sector_exp.values()) / strategy_value * 100 if strategy_value > 0 else 0

            risk_score = self._calculate_strategy_risk_score(
                strategy_var.var_95,
                strategy_value,
                strategy_pnl,
                exposure_percent
            )

            strategy_risk = StrategyRisk(
                strategy_id=strategy_id,
                strategy_name=strategy.get('strategy_name', strategy_id),
                total_value=strategy_value,
                pnl=strategy_pnl,
                pnl_percent=(strategy_pnl / strategy_value * 100) if strategy_value > 0 else 0,
                var_95=strategy_var.var_95,
                var_99=strategy_var.var_99,
                positions_count=len(strategy_positions),
                active_orders=strategy.get('active_orders', 0),
                exposure_percent=exposure_percent,
                concentration_percent=concentration,
                risk_score=risk_score
            )

            strategy_risks.append(strategy_risk)
            self._strategy_risk[user_id][strategy_id] = strategy_risk

        return strategy_risks

    def _calculate_risk_level(
        self,
        var_95: float,
        portfolio_value: float,
        margin_utilization: float,
        strategy_risks: List[StrategyRisk]
    ) -> str:
        """Calculate overall risk level."""
        var_percent = (var_95 / portfolio_value * 100) if portfolio_value > 0 else 0

        score = 0

        if var_percent > 5:
            score += 30
        elif var_percent > 2:
            score += 15

        if margin_utilization > 80:
            score += 25
        elif margin_utilization > 60:
            score += 10

        high_risk_strategies = sum(1 for s in strategy_risks if s.risk_score > 70)
        score += high_risk_strategies * 10

        if score >= 60:
            return 'critical'
        elif score >= 40:
            return 'high'
        elif score >= 20:
            return 'medium'
        else:
            return 'low'

    def _calculate_strategy_risk_score(
        self,
        var: float,
        strategy_value: float,
        pnl: float,
        exposure_percent: float
    ) -> float:
        """Calculate risk score for a strategy."""
        score = 0

        if strategy_value > 0:
            var_percent = (var / strategy_value * 100)
            score += min(var_percent * 3, 40)

            if pnl < 0:
                loss_percent = abs(pnl / strategy_value * 100)
                score += min(loss_percent * 2, 30)

            score += min(exposure_percent * 0.5, 30)

        return min(score, 100)

    def _generate_heatmap_data(
        self,
        position_exposure: Dict[str, float],
        sector_exposure: Dict[str, float],
        portfolio_value: float
    ) -> List[Dict]:
        """Generate heatmap data for visualization."""
        heatmap = []

        for sector, sector_value in sector_exposure.items():
            sector_pct = (sector_value / portfolio_value * 100) if portfolio_value > 0 else 0
            heatmap.append({
                'category': sector,
                'value': sector_value,
                'percent': sector_pct,
                'risk': 'high' if sector_pct > 30 else 'medium' if sector_pct > 15 else 'low'
            })

        sorted_positions = sorted(position_exposure.items(), key=lambda x: x[1], reverse=True)[:10]
        for symbol, value in sorted_positions:
            pct = (value / portfolio_value * 100) if portfolio_value > 0 else 0
            heatmap.append({
                'category': symbol,
                'value': value,
                'percent': pct,
                'type': 'position',
                'risk': 'high' if pct > 20 else 'medium' if pct > 10 else 'low'
            })

        return heatmap

    def _update_correlation_matrix(self, market_data: Dict[str, Dict]) -> None:
        """Update correlation matrix from market data."""
        symbols = list(market_data.keys())
        self._correlation_matrix = {}

        for s1 in symbols:
            self._correlation_matrix[s1] = {}
            for s2 in symbols:
                if s1 == s2:
                    self._correlation_matrix[s1][s2] = 1.0
                else:
                    default_corr = market_data.get(s1, {}).get('correlation', {}).get(s2, 0.3)
                    self._correlation_matrix[s1][s2] = default_corr

        self._var_engine.update_correlation_matrix(self._correlation_matrix)

    async def calculate_cross_strategy_risk(
        self,
        user_id: str,
        strategies: List[Dict],
        positions: List[Dict]
    ) -> Dict:
        """Calculate cross-strategy risk and correlations."""
        if user_id not in self._strategy_risk:
            return {}

        strategy_returns = {}
        for strategy in strategies:
            strategy_id = strategy.get('strategy_id')
            strategy_positions = [p for p in positions if p.get('strategy_id') == strategy_id]

            if not strategy_positions:
                continue

            total_value = sum(p.get('value', 0) for p in strategy_positions)
            pnl = sum(p.get('unrealized_pnl', 0) for p in strategy_positions)

            daily_return = (pnl / total_value * 100) if total_value > 0 else 0
            strategy_returns[strategy_id] = [daily_return]

        correlation_matrix = {}
        strategy_ids = list(strategy_returns.keys())

        for s1 in strategy_ids:
            correlation_matrix[s1] = {}
            for s2 in strategy_ids:
                if s1 == s2:
                    correlation_matrix[s1][s2] = 1.0
                else:
                    correlation_matrix[s1][s2] = 0.5

        portfolio_concentration = max(
            (s.total_value for s in self._strategy_risk[user_id].values()),
            default=0
        )

        return {
            'correlation_matrix': correlation_matrix,
            'highest_concentration_strategy': max(
                ((s.strategy_id, s.exposure_percent) for s in self._strategy_risk[user_id].values()),
                key=lambda x: x[1],
                default=('', 0)
            )[0],
            'strategy_count': len(strategy_returns)
        }

    def get_user_risk(self, user_id: str) -> Optional[UserRisk]:
        """Get current risk metrics for a user."""
        return self._user_risk.get(user_id)

    def get_all_user_risks(self) -> List[Dict]:
        """Get risk metrics for all users."""
        return [
            {
                'user_id': user_id,
                'portfolio_value': risk.total_portfolio_value,
                'var_95': risk.var_95,
                'risk_level': risk.risk_level,
                'margin_utilization': risk.margin_utilization,
                'open_positions': risk.open_positions,
                'last_updated': risk.last_updated.isoformat()
            }
            for user_id, risk in self._user_risk.items()
        ]

    def get_risk_summary(self) -> Dict:
        """Get aggregate risk summary across all users."""
        if not self._user_risk:
            return {}

        total_value = sum(r.total_portfolio_value for r in self._user_risk.values())
        total_var = sum(r.var_95 for r in self._user_risk.values())
        avg_margin = sum(r.margin_utilization for r in self._user_risk.values()) / len(self._user_risk)

        risk_distribution = {
            'low': sum(1 for r in self._user_risk.values() if r.risk_level == 'low'),
            'medium': sum(1 for r in self._user_risk.values() if r.risk_level == 'medium'),
            'high': sum(1 for r in self._user_risk.values() if r.risk_level == 'high'),
            'critical': sum(1 for r in self._user_risk.values() if r.risk_level == 'critical')
        }

        return {
            'total_portfolio_value': total_value,
            'aggregate_var_95': total_var,
            'average_margin_utilization': avg_margin,
            'risk_distribution': risk_distribution,
            'user_count': len(self._user_risk)
        }


portfolio_aggregator = PortfolioAggregator()


def get_portfolio_aggregator() -> PortfolioAggregator:
    return portfolio_aggregator
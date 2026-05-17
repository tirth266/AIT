"""
Portfolio Risk Analytics
========================
Calculate portfolio-level risk metrics.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
import math

logger = logging.getLogger(__name__)


@dataclass
class PortfolioMetrics:
    user_id: str
    total_value: float
    cash: float
    invested: float
    leverage: float
    beta: float
    var_95: float
    expected_drawdown: float
    sharpe_ratio: float
    sector_concentration: Dict[str, float]
    correlation_risk: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


SECTOR_BETA = {
    'Energy': 1.1, 'Metals': 1.2, 'IT': 1.0, 'Finance': 1.15,
    'Telecom': 0.9, 'FMCG': 0.7, 'Automobile': 1.05, 'Consumer': 0.85,
    'Cement': 0.95, 'Construction': 1.0, 'Pharma': 0.9, 'Utilities': 0.8,
    'Other': 1.0
}


SECTOR_CORRELATION = {
    ('Energy', 'Metals'): 0.7,
    ('IT', 'Finance'): 0.5,
    ('FMCG', 'Consumer'): 0.6,
    ('Automobile', 'Metals'): 0.4,
}


class PortfolioRiskAnalytics:
    """
    Calculate portfolio-level risk metrics.
    """
    
    def __init__(self, risk_engine=None):
        self.logger = logging.getLogger('portfolio_risk')
        self.risk_engine = risk_engine
        
        self._metrics: Dict[str, PortfolioMetrics] = {}
        self._price_cache: Dict[str, float] = {}
        
        self._historical_returns: Dict[str, List[float]] = defaultdict(list)
    
    async def calculate_metrics(self, user_id: str, positions: List[Dict],
                                 cash: float = 100000) -> PortfolioMetrics:
        open_positions = [p for p in positions if p.get('status') == 'OPEN']
        
        invested = sum(
            p.get('quantity', 0) * p.get('current_price', p.get('average_price', 0))
            for p in open_positions
        )
        
        total_value = cash + invested
        leverage = invested / total_value if total_value > 0 else 0
        
        sector_values = defaultdict(float)
        symbol_exposure = {}
        
        for pos in open_positions:
            symbol = pos.get('symbol', '').upper()
            quantity = pos.get('quantity', 0)
            price = pos.get('current_price', pos.get('average_price', 0))
            
            value = quantity * price
            sector = self._get_sector(symbol)
            
            sector_values[sector] += value
            symbol_exposure[symbol] = value
        
        sector_concentration = {}
        if invested > 0:
            for sector, value in sector_values.items():
                sector_concentration[sector] = round((value / invested) * 100, 2)
        
        beta = self._calculate_portfolio_beta(sector_values, invested)
        
        var_95 = self._calculate_var(total_value, beta)
        
        expected_dd = self._calculate_expected_drawdown(var_95)
        
        sharpe = self._calculate_sharpe_ratio(user_id)
        
        corr_risk = self._calculate_correlation_risk(sector_values)
        
        metrics = PortfolioMetrics(
            user_id=user_id,
            total_value=total_value,
            cash=cash,
            invested=invested,
            leverage=leverage,
            beta=beta,
            var_95=var_95,
            expected_drawdown=expected_dd,
            sharpe_ratio=sharpe,
            sector_concentration=sector_concentration,
            correlation_risk=corr_risk
        )
        
        self._metrics[user_id] = metrics
        
        await self._check_risk_warnings(user_id, metrics)
        
        return metrics
    
    def _get_sector(self, symbol: str) -> str:
        sector_map = {
            'RELIANCE': 'Energy', 'ONGC': 'Energy', 'TATASTEEL': 'Metals',
            'HINDALCO': 'Metals', 'JSWSTEEL': 'Metals',
            'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'TECHM': 'IT',
            'HDFCBANK': 'Finance', 'ICICIBANK': 'Finance', 'SBIN': 'Finance',
            'KOTAKBANK': 'Finance', 'AXISBANK': 'Finance',
            'BHARTIARTL': 'Telecom', 'ITC': 'FMCG', 'HINDUNILVR': 'FMCG',
            'MARUTI': 'Automobile', 'TATAMOTORS': 'Automobile', 'M&M': 'Automobile',
            'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma',
            'POWERGRID': 'Utilities', 'NTPC': 'Utilities', 'COALINDIA': 'Utilities',
        }
        return sector_map.get(symbol, 'Other')
    
    def _calculate_portfolio_beta(self, sector_values: Dict[str, float], 
                                   invested: float) -> float:
        if invested <= 0:
            return 1.0
        
        weighted_beta = 0.0
        
        for sector, value in sector_values.items():
            weight = value / invested
            beta = SECTOR_BETA.get(sector, 1.0)
            weighted_beta += weight * beta
        
        return round(weighted_beta, 2)
    
    def _calculate_var(self, portfolio_value: float, beta: float, 
                       confidence: float = 0.95) -> float:
        daily_volatility = 0.015
        z_score = 1.65
        
        portfolio_var = portfolio_value * beta * daily_volatility * z_score
        
        return round(portfolio_var, 2)
    
    def _calculate_expected_drawdown(self, var: float) -> float:
        expected_dd = var * 1.5
        
        return round(expected_dd, 2)
    
    def _calculate_sharpe_ratio(self, user_id: str) -> float:
        returns = self._historical_returns.get(user_id, [])
        
        if len(returns) < 5:
            return 0.0
        
        avg_return = sum(returns) / len(returns)
        
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        std_dev = variance ** 0.5
        
        if std_dev == 0:
            return 0.0
        
        sharpe = (avg_return / std_dev) * math.sqrt(252)
        
        return round(sharpe, 2)
    
    def _calculate_correlation_risk(self, sector_values: Dict[str, float]) -> float:
        if len(sector_values) < 2:
            return 0.0
        
        total_value = sum(sector_values.values())
        if total_value <= 0:
            return 0.0
        
        risk_score = 0.0
        
        sectors = list(sector_values.keys())
        
        for i, s1 in enumerate(sectors):
            for s2 in sectors[i+1:]:
                weight1 = sector_values[s1] / total_value
                weight2 = sector_values[s2] / total_value
                
                correlation = SECTOR_CORRELATION.get((s1, s2), 
                    SECTOR_CORRELATION.get((s2, s1), 0.3))
                
                risk_score += weight1 * weight2 * correlation
        
        return round(risk_score * 100, 2)
    
    async def _check_risk_warnings(self, user_id: str, metrics: PortfolioMetrics) -> None:
        if metrics.leverage > 2.0:
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'portfolio_warning',
                    'user_id': user_id,
                    'warning': 'high_leverage',
                    'message': f"Portfolio leverage {metrics.leverage:.2f}x is high",
                    'level': 'warning'
                })
        
        max_concentration = max(metrics.sector_concentration.values()) if metrics.sector_concentration else 0
        if max_concentration > 40:
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'portfolio_warning',
                    'user_id': user_id,
                    'warning': 'sector_concentration',
                    'message': f"Sector concentration {max_concentration}% is high",
                    'level': 'warning'
                })
        
        if metrics.beta > 1.3:
            if self.risk_engine:
                await self.risk_engine.log_event({
                    'event_type': 'portfolio_warning',
                    'user_id': user_id,
                    'warning': 'high_beta',
                    'message': f"Portfolio beta {metrics.beta} is high",
                    'level': 'warning'
                })
    
    def add_return_data(self, user_id: str, return_pct: float) -> None:
        self._historical_returns[user_id].append(return_pct)
        
        if len(self._historical_returns[user_id]) > 252:
            self._historical_returns[user_id] = self._historical_returns[user_id][-252:]
    
    def get_metrics(self, user_id: str) -> Optional[PortfolioMetrics]:
        return self._metrics.get(user_id)
    
    def get_all_metrics(self) -> List[Dict]:
        return [
            {
                'user_id': m.user_id,
                'total_value': m.total_value,
                'cash': m.cash,
                'invested': m.invested,
                'leverage': round(m.leverage, 2),
                'beta': m.beta,
                'var_95': m.var_95,
                'expected_drawdown': m.expected_drawdown,
                'sharpe_ratio': m.sharpe_ratio,
                'sector_concentration': m.sector_concentration,
                'correlation_risk': m.correlation_risk,
                'timestamp': m.timestamp.isoformat()
            }
            for m in self._metrics.values()
        ]


portfolio_risk_analytics = PortfolioRiskAnalytics()


def get_portfolio_risk_analytics() -> PortfolioRiskAnalytics:
    return portfolio_risk_analytics
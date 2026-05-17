"""
Value at Risk (VaR) Engine
==========================
Institutional-grade VaR calculation with multiple methodologies:
- Historical Simulation
- Parametric (Variance-Covariance)
- Monte Carlo Simulation
- Expected Shortfall (CVaR)
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import logging
import asyncio

logger = logging.getLogger('risk_engine.var')


@dataclass
class VaRResult:
    """VaR calculation result."""
    var_95: float
    var_99: float
    expected_shortfall_95: float
    expected_shortfall_99: float
    component_var: Dict[str, float]
    marginal_var: Dict[str, float]
    confidence_level_95: float
    confidence_level_99: float
    calculation_time: float
    method: str
    lookback_days: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PositionRisk:
    """Risk metrics for a single position."""
    symbol: str
    quantity: int
    side: str
    current_value: float
    beta: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    var_contribution: float
    marginal_var: float


@dataclass
class PortfolioRisk:
    """Complete portfolio risk metrics."""
    total_value: float
    cash: float
    invested: float
    gross_exposure: float
    net_exposure: float
    leverage: float
    var_result: VaRResult
    positions: List[PositionRisk]
    sector_exposure: Dict[str, float]
    correlation_matrix: Dict[str, Dict[str, float]]


class VaREngine:
    """
    Value at Risk Engine with multiple calculation methods.
    """

    def __init__(
        self,
        lookback_days: int = 252,
        risk_free_rate: float = 0.07,
        confidence_levels: List[float] = None
    ):
        self.lookback_days = lookback_days
        self.risk_free_rate = risk_free_rate
        self.confidence_levels = confidence_levels or [0.95, 0.99]

        self._historical_returns: Dict[str, pd.DataFrame] = {}
        self._correlation_matrix: Optional[pd.DataFrame] = None
        self._volatility_cache: Dict[str, float] = {}

        self._calculation_history: List[VaRResult] = []

    def set_historical_prices(self, symbol: str, prices: List[float], dates: List[datetime] = None):
        """Set historical price data for a symbol."""
        if dates is None:
            dates = [datetime.now(timezone.utc) - timedelta(days=i) for i in range(len(prices))]

        df = pd.DataFrame({
            'date': dates,
            'price': prices
        }).sort_values('date')

        df['returns'] = df['price'].pct_change().fillna(0)
        self._historical_returns[symbol] = df

    def update_correlation_matrix(self, correlation_matrix: Dict[str, Dict[str, float]]):
        """Update the correlation matrix."""
        symbols = list(correlation_matrix.keys())
        self._correlation_matrix = pd.DataFrame(index=symbols, columns=symbols)

        for s1 in symbols:
            for s2 in symbols:
                self._correlation_matrix.loc[s1, s2] = correlation_matrix[s1].get(s2, 0)

    def calculate_historical_var(
        self,
        positions: Dict[str, Dict],
        portfolio_value: float,
        horizon_days: int = 1
    ) -> VaRResult:
        """Calculate VaR using historical simulation method."""
        start_time = datetime.now(timezone.utc)

        if not positions or portfolio_value <= 0:
            return self._empty_var_result(start_time, "historical")

        returns_by_symbol = {}

        for symbol, pos in positions.items():
            if symbol in self._historical_returns:
                returns = self._historical_returns[symbol]['returns'].values
            else:
                default_vol = self._volatility_cache.get(symbol, 0.02)
                returns = np.random.normal(0, default_vol, self.lookback_days)

            returns_by_symbol[symbol] = returns

        portfolio_returns = self._simulate_portfolio_returns(positions, returns_by_symbol, portfolio_value)

        var_95 = self._calculate_var(portfolio_returns, 0.95) * np.sqrt(horizon_days)
        var_99 = self._calculate_var(portfolio_returns, 0.99) * np.sqrt(horizon_days)
        es_95 = self._calculate_expected_shortfall(portfolio_returns, 0.95) * np.sqrt(horizon_days)
        es_99 = self._calculate_expected_shortfall(portfolio_returns, 0.99) * np.sqrt(horizon_days)

        component_var = self._calculate_component_var(portfolio_returns, positions, portfolio_value)
        marginal_var = self._calculate_marginal_var(portfolio_returns, positions, portfolio_value)

        calculation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = VaRResult(
            var_95=abs(var_95 * portfolio_value),
            var_99=abs(var_99 * portfolio_value),
            expected_shortfall_95=abs(es_95 * portfolio_value),
            expected_shortfall_99=abs(es_99 * portfolio_value),
            component_var=component_var,
            marginal_var=marginal_var,
            confidence_level_95=var_95,
            confidence_level_99=var_99,
            calculation_time=calculation_time,
            method='historical',
            lookback_days=self.lookback_days
        )

        self._calculation_history.append(result)
        return result

    def calculate_parametric_var(
        self,
        positions: Dict[str, Dict],
        portfolio_value: float,
        horizon_days: int = 1
    ) -> VaRResult:
        """Calculate VaR using parametric (variance-covariance) method."""
        start_time = datetime.now(timezone.utc)

        if not positions or portfolio_value <= 0:
            return self._empty_var_result(start_time, "parametric")

        weights = {}
        volatilities = {}

        total_value = sum(pos['value'] for pos in positions.values())

        for symbol, pos in positions.items():
            weights[symbol] = pos['value'] / total_value if total_value > 0 else 0
            volatilities[symbol] = self._get_volatility(symbol)

        portfolio_volatility = self._calculate_portfolio_volatility(weights, volatilities)

        z_95 = 1.645
        z_99 = 2.326

        var_95 = z_95 * portfolio_volatility * np.sqrt(horizon_days)
        var_99 = z_99 * portfolio_volatility * np.sqrt(horizon_days)

        es_95 = (portfolio_volatility * np.sqrt(horizon_days)) * (
            (np.exp(-z_95**2/2) / (np.sqrt(2 * np.pi) * (1 - 0.95))) * 0.5
        )
        es_99 = (portfolio_volatility * np.sqrt(horizon_days)) * (
            (np.exp(-z_99**2/2) / (np.sqrt(2 * np.pi) * (1 - 0.99))) * 0.5
        )

        component_var = {
            symbol: var_95 * weight * portfolio_value
            for symbol, weight in weights.items()
        }
        marginal_var = component_var.copy()

        calculation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = VaRResult(
            var_95=abs(var_95 * portfolio_value),
            var_99=abs(var_99 * portfolio_value),
            expected_shortfall_95=abs(es_95 * portfolio_value),
            expected_shortfall_99=abs(es_99 * portfolio_value),
            component_var=component_var,
            marginal_var=marginal_var,
            confidence_level_95=var_95,
            confidence_level_99=var_99,
            calculation_time=calculation_time,
            method='parametric',
            lookback_days=self.lookback_days
        )

        self._calculation_history.append(result)
        return result

    def calculate_monte_carlo_var(
        self,
        positions: Dict[str, Dict],
        portfolio_value: float,
        n_simulations: int = 10000,
        horizon_days: int = 1
    ) -> VaRResult:
        """Calculate VaR using Monte Carlo simulation."""
        start_time = datetime.now(timezone.utc)

        if not positions or portfolio_value <= 0:
            return self._empty_var_result(start_time, "monte_carlo")

        total_value = sum(pos['value'] for pos in positions.values())

        weights = {}
        volatilities = {}

        for symbol, pos in positions.items():
            weights[symbol] = pos['value'] / total_value if total_value > 0 else 0
            volatilities[symbol] = self._get_volatility(symbol)

        portfolio_volatility = self._calculate_portfolio_volatility(weights, volatilities)

        simulated_returns = np.random.normal(
            self.risk_free_rate / 252,
            portfolio_volatility,
            (n_simulations, horizon_days)
        ).mean(axis=1)

        var_95 = -np.percentile(simulated_returns, 5) * portfolio_value
        var_99 = -np.percentile(simulated_returns, 1) * portfolio_value

        tail_5 = simulated_returns[simulated_returns <= np.percentile(simulated_returns, 5)]
        tail_1 = simulated_returns[simulated_returns <= np.percentile(simulated_returns, 1)]

        es_95 = -np.mean(tail_5) * portfolio_value if len(tail_5) > 0 else var_95
        es_99 = -np.mean(tail_1) * portfolio_value if len(tail_1) > 0 else var_99

        component_var = {
            symbol: var_95 * weight * portfolio_value
            for symbol, weight in weights.items()
        }
        marginal_var = component_var.copy()

        calculation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = VaRResult(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall_95=es_95,
            expected_shortfall_99=es_99,
            component_var=component_var,
            marginal_var=marginal_var,
            confidence_level_95=var_95 / portfolio_value,
            confidence_level_99=var_99 / portfolio_value,
            calculation_time=calculation_time,
            method='monte_carlo',
            lookback_days=n_simulations
        )

        self._calculation_history.append(result)
        return result

    def calculate_all_methods(
        self,
        positions: Dict[str, Dict],
        portfolio_value: float
    ) -> Dict[str, VaRResult]:
        """Calculate VaR using all methods."""
        return {
            'historical': self.calculate_historical_var(positions, portfolio_value),
            'parametric': self.calculate_parametric_var(positions, portfolio_value),
            'monte_carlo': self.calculate_monte_carlo_var(positions, portfolio_value)
        }

    def _simulate_portfolio_returns(
        self,
        positions: Dict[str, Dict],
        returns_by_symbol: Dict[str, np.ndarray],
        portfolio_value: float
    ) -> np.ndarray:
        """Simulate portfolio returns using correlation structure."""
        if not returns_by_symbol:
            return np.zeros(self.lookback_days)

        symbols = list(positions.keys())
        n_assets = len(symbols)
        n_days = self.lookback_days

        if n_assets == 1:
            symbol = symbols[0]
            return returns_by_symbol.get(symbol, np.zeros(n_days))

        returns_matrix = np.zeros((n_days, n_assets))
        for i, symbol in enumerate(symbols):
            returns_matrix[:, i] = returns_by_symbol.get(symbol, np.zeros(n_days))

        if self._correlation_matrix is not None:
            try:
                corr_subset = self._correlation_matrix.loc[symbols, symbols].values
                if not np.isnan(corr_subset).any():
                    L = np.linalg.cholesky(corr_subset)
                    returns_matrix = returns_matrix @ L.T
            except Exception:
                pass

        weights = np.array([positions[s].get('value', 0) / portfolio_value for s in symbols])
        portfolio_returns = returns_matrix @ weights

        return portfolio_returns

    def _calculate_var(self, returns: np.ndarray, confidence: float) -> float:
        """Calculate Value at Risk."""
        if len(returns) == 0:
            return 0.0
        return -np.percentile(returns, (1 - confidence) * 100)

    def _calculate_expected_shortfall(self, returns: np.ndarray, confidence: float) -> float:
        """Calculate Expected Shortfall (CVaR)."""
        if len(returns) == 0:
            return 0.0

        var_threshold = np.percentile(returns, (1 - confidence) * 100)
        tail_returns = returns[returns <= var_threshold]

        if len(tail_returns) == 0:
            return abs(var_threshold)

        return -np.mean(tail_returns)

    def _calculate_portfolio_volatility(
        self,
        weights: Dict[str, float],
        volatilities: Dict[str, float]
    ) -> float:
        """Calculate portfolio volatility."""
        if self._correlation_matrix is not None:
            symbols = list(weights.keys())
            if all(s in self._correlation_matrix.index for s in symbols):
                try:
                    w = np.array([weights[s] for s in symbols])
                    v = np.array([volatilities.get(s, 0.02) for s in symbols])
                    cov_matrix = np.outer(v, v) * self._correlation_matrix.loc[symbols, symbols].values
                    return np.sqrt(w @ cov_matrix @ w)
                except Exception:
                    pass

        w_arr = np.array(list(weights.values()))
        v_arr = np.array(list(volatilities.values()))
        return np.sqrt(np.sum(w_arr ** 2 * v_arr ** 2))

    def _calculate_component_var(
        self,
        returns: np.ndarray,
        positions: Dict[str, Dict],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Calculate component VaR (contribution to portfolio VaR)."""
        total_var = np.var(returns) if len(returns) > 0 else 0

        if total_var == 0:
            return {symbol: 0 for symbol in positions.keys()}

        component_var = {}
        total_value = sum(pos['value'] for pos in positions.values())

        for symbol, pos in positions.items():
            weight = pos['value'] / total_value if total_value > 0 else 0
            component_var[symbol] = weight * total_var * portfolio_value

        return component_var

    def _calculate_marginal_var(
        self,
        returns: np.ndarray,
        positions: Dict[str, Dict],
        portfolio_value: float
    ) -> Dict[str, float]:
        """Calculate marginal VaR (change in VaR from adding 1% of position)."""
        if len(returns) == 0:
            return {symbol: 0 for symbol in positions.keys()}

        base_var = abs(np.percentile(returns, 5)) * portfolio_value

        if base_var == 0:
            return {symbol: 0 for symbol in positions.keys()}

        total_value = sum(pos['value'] for pos in positions.values())
        marginal_var = {}

        for symbol, pos in positions.items():
            weight = pos['value'] / total_value if total_value > 0 else 0
            marginal_var[symbol] = base_var * weight

        return marginal_var

    def _get_volatility(self, symbol: str) -> float:
        """Get or calculate volatility for a symbol."""
        if symbol in self._volatility_cache:
            return self._volatility_cache[symbol]

        if symbol in self._historical_returns:
            returns = self._historical_returns[symbol]['returns']
            vol = returns.std()
            self._volatility_cache[symbol] = vol
            return vol

        default_vol = 0.02
        self._volatility_cache[symbol] = default_vol
        return default_vol

    def _empty_var_result(self, start_time: datetime, method: str) -> VaRResult:
        """Return empty VaR result."""
        return VaRResult(
            var_95=0,
            var_99=0,
            expected_shortfall_95=0,
            expected_shortfall_99=0,
            component_var={},
            marginal_var={},
            confidence_level_95=0,
            confidence_level_99=0,
            calculation_time=0,
            method=method,
            lookback_days=self.lookback_days
        )

    def get_calculation_history(self, limit: int = 100) -> List[Dict]:
        """Get VaR calculation history."""
        return [
            {
                'var_95': r.var_95,
                'var_99': r.var_99,
                'expected_shortfall_95': r.expected_shortfall_95,
                'expected_shortfall_99': r.expected_shortfall_99,
                'method': r.method,
                'timestamp': r.timestamp.isoformat()
            }
            for r in self._calculation_history[-limit:]
        ]


var_engine = VaREngine()


def get_var_engine() -> VaREngine:
    return var_engine
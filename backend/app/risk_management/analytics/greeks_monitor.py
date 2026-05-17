"""
Greeks Monitor
==============
Options Greeks calculation and portfolio-level Greeks aggregation.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import logging
from math import exp, sqrt, log

logger = logging.getLogger('risk_engine.greeks')


class OptionType(str, Enum):
    CALL = "call"
    PUT = "put"


class GreeksLimitType(str, Enum):
    DELTA = "delta"
    GAMMA = "gamma"
    THETA = "theta"
    VEGA = "vega"
    RHO = "rho"
    TOTAL_EXPOSURE = "total_exposure"


@dataclass
class OptionGreeks:
    """Greeks for a single option position."""
    symbol: str
    option_type: OptionType
    strike_price: float
    expiration_days: int

    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float

    position_value: float
    quantity: int
    side: str


@dataclass
class PortfolioGreeks:
    """Aggregated portfolio Greeks."""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    total_rho: float

    delta_exposure_value: float
    gamma_exposure_value: float
    theta_exposure_value: float
    vega_exposure_value: float
    rho_exposure_value: float

    net_delta: float
    net_gamma: float

    position_count: int
    option_count: int

    delta_limit: float
    gamma_limit: float
    theta_limit: float
    vega_limit: float

    delta_utilization: float
    gamma_utilization: float
    theta_utilization: float
    vega_utilization: float


@dataclass
class GreeksAlert:
    """Greeks limit breach alert."""
    user_id: str
    limit_type: GreeksLimitType
    current_value: float
    limit_value: float
    utilization_percent: float
    severity: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class GreeksCalculator:
    """
    Black-Scholes Greeks calculator.
    """

    def __init__(self, risk_free_rate: float = 0.07):
        self.risk_free_rate = risk_free_rate

    def _d1(self, S: float, K: float, T: float, r: float, sigma: float) -> float:
        """Calculate d1 parameter."""
        if T <= 0 or sigma <= 0:
            return 0
        return (log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * sqrt(T))

    def _d2(self, d1: float, sigma: float, T: float) -> float:
        """Calculate d2 parameter."""
        if T <= 0 or sigma <= 0:
            return 0
        return d1 - sigma * sqrt(T)

    def calculate_greeks(
        self,
        spot_price: float,
        strike_price: float,
        time_to_expiry_days: int,
        volatility: float,
        option_type: OptionType,
        risk_free_rate: float = None
    ) -> Dict[str, float]:
        """Calculate all Greeks for an option."""
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate

        T = time_to_expiry_days / 365.0
        r = risk_free_rate
        sigma = volatility

        if T <= 0 or sigma <= 0:
            return {
                'delta': 0,
                'gamma': 0,
                'theta': 0,
                'vega': 0,
                'rho': 0
            }

        d1 = self._d1(spot_price, strike_price, T, r, sigma)
        d2 = self._d2(d1, sigma, T)

        sqrt_T = sqrt(T)

        if option_type == OptionType.CALL:
            delta = self._norm_cdf(d1)
            rho = strike_price * T * self._norm_cdf(d2) * exp(-r * T)
            theta = (-(spot_price * sigma * self._norm_pdf(d1)) / (2 * sqrt_T)
                     - r * strike_price * self._norm_cdf(d2) * exp(-r * T)) / 365
        else:
            delta = self._norm_cdf(d1) - 1
            rho = -strike_price * T * self._norm_cdf(-d2) * exp(-r * T)
            theta = (-(spot_price * sigma * self._norm_pdf(d1)) / (2 * sqrt_T)
                     + r * strike_price * self._norm_cdf(-d2) * exp(-r * T)) / 365

        gamma = self._norm_pdf(d1) / (spot_price * sigma * sqrt_T)
        vega = spot_price * sqrt_T * self._norm_pdf(d1) / 100

        return {
            'delta': delta,
            'gamma': gamma,
            'theta': theta,
            'vega': vega,
            'rho': rho
        }

    def _norm_cdf(self, x: float) -> float:
        """Standard normal cumulative distribution function."""
        return 0.5 * (1 + self._erf(x / sqrt(2)))

    def _norm_pdf(self, x: float) -> float:
        """Standard normal probability density function."""
        return exp(-0.5 * x ** 2) / sqrt(2 * np.pi)

    def _erf(self, x: float) -> float:
        """Error function approximation."""
        a1 = 0.254829592
        a2 = -0.284496736
        a3 = 1.421413741
        a4 = -1.453152027
        a5 = 1.061405429
        p = 0.3275911

        sign = 1 if x >= 0 else -1
        x = abs(x)

        t = 1.0 / (1.0 + p * x)
        y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * exp(-x * x)

        return sign * y


class GreeksMonitor:
    """
    Monitors and aggregates portfolio Greeks with limit checking.
    """

    def __init__(self):
        self.logger = logging.getLogger('greeks_monitor')
        self._calculator = GreeksCalculator()

        self._portfolio_greeks: Dict[str, PortfolioGreeks] = {}
        self._option_greeks: Dict[str, Dict[str, OptionGreeks]] = {}

        self._limits: Dict[str, Dict[GreeksLimitType, float]] = {}
        self._alerts: Dict[str, List[GreeksAlert]] = {}

    def set_limits(self, user_id: str, limits: Dict[GreeksLimitType, float]) -> None:
        """Set Greeks limits for a user."""
        self._limits[user_id] = limits

    def get_limits(self, user_id: str) -> Dict[GreeksLimitType, float]:
        """Get Greeks limits for a user."""
        default_limits = {
            GreeksLimitType.DELTA: 100000,
            GreeksLimitType.GAMMA: 50000,
            GreeksLimitType.THETA: 10000,
            GreeksLimitType.VEGA: 50000,
            GreeksLimitType.TOTAL_EXPOSURE: 200000
        }
        return self._limits.get(user_id, default_limits)

    async def calculate_position_greeks(
        self,
        symbol: str,
        option_type: OptionType,
        strike_price: float,
        time_to_expiry_days: int,
        volatility: float,
        spot_price: float,
        quantity: int,
        side: str
    ) -> OptionGreeks:
        """Calculate Greeks for a single option position."""
        greeks = self._calculator.calculate_greeks(
            spot_price,
            strike_price,
            time_to_expiry_days,
            volatility,
            option_type
        )

        position_value = quantity * spot_price
        multiplier = 1 if side.upper() == 'BUY' else -1

        return OptionGreeks(
            symbol=symbol,
            option_type=option_type,
            strike_price=strike_price,
            expiration_days=time_to_expiry_days,
            delta=greeks['delta'] * multiplier,
            gamma=greeks['gamma'] * multiplier,
            theta=greeks['theta'] * multiplier * position_value,
            vega=greeks['vega'] * multiplier,
            rho=greeks['rho'] * multiplier * position_value,
            position_value=position_value,
            quantity=quantity,
            side=side
        )

    async def calculate_equity_delta(
        self,
        symbol: str,
        beta: float,
        position_value: float,
        side: str
    ) -> float:
        """Calculate delta for equity position (beta-weighted)."""
        multiplier = 1 if side.upper() == 'BUY' else -1
        return beta * position_value * multiplier

    async def calculate_portfolio_greeks(
        self,
        user_id: str,
        positions: List[Dict],
        market_data: Dict[str, Dict]
    ) -> PortfolioGreeks:
        """Calculate aggregated portfolio Greeks."""
        total_delta = 0.0
        total_gamma = 0.0
        total_theta = 0.0
        total_vega = 0.0
        total_rho = 0.0

        option_count = 0

        for pos in positions:
            symbol = pos.get('symbol', '')
            position_type = pos.get('position_type', 'EQUITY')
            side = pos.get('side', 'BUY')
            value = pos.get('value', 0)
            quantity = pos.get('quantity', 0)

            if position_type == 'OPTIONS':
                option_data = market_data.get(symbol, {})
                spot_price = option_data.get('spot_price', value)
                strike = option_data.get('strike_price', value)
                expiry = option_data.get('expiry_days', 30)
                vol = option_data.get('volatility', 0.20)
                opt_type = OptionType(option_data.get('option_type', 'call'))

                option_greeks = await self.calculate_position_greeks(
                    symbol, opt_type, strike, expiry, vol, spot_price, quantity, side
                )

                total_delta += option_greeks.delta * value
                total_gamma += option_greeks.gamma * value
                total_theta += option_greeks.theta
                total_vega += option_greeks.vega * value
                total_rho += option_greeks.rho
                option_count += 1

            else:
                beta = market_data.get(symbol, {}).get('beta', 1.0)
                equity_delta = await self.calculate_equity_delta(symbol, beta, value, side)
                total_delta += equity_delta

        limits = self.get_limits(user_id)

        portfolio_greeks = PortfolioGreeks(
            total_delta=total_delta,
            total_gamma=total_gamma,
            total_theta=total_theta,
            total_vega=total_vega,
            total_rho=total_rho,
            delta_exposure_value=abs(total_delta),
            gamma_exposure_value=abs(total_gamma),
            theta_exposure_value=abs(total_theta),
            vega_exposure_value=abs(total_vega),
            rho_exposure_value=abs(total_rho),
            net_delta=total_delta,
            net_gamma=total_gamma,
            position_count=len(positions),
            option_count=option_count,
            delta_limit=limits.get(GreeksLimitType.DELTA, 100000),
            gamma_limit=limits.get(GreeksLimitType.GAMMA, 50000),
            theta_limit=limits.get(GreeksLimitType.THETA, 10000),
            vega_limit=limits.get(GreeksLimitType.VEGA, 50000),
            delta_utilization=(abs(total_delta) / limits.get(GreeksLimitType.DELTA, 100000) * 100) if limits.get(GreeksLimitType.DELTA) else 0,
            gamma_utilization=(abs(total_gamma) / limits.get(GreeksLimitType.GAMMA, 50000) * 100) if limits.get(GreeksLimitType.GAMMA) else 0,
            theta_utilization=(abs(total_theta) / limits.get(GreeksLimitType.THETA, 10000) * 100) if limits.get(GreeksLimitType.THETA) else 0,
            vega_utilization=(abs(total_vega) / limits.get(GreeksLimitType.VEGA, 50000) * 100) if limits.get(GreeksLimitType.VEGA) else 0
        )

        self._portfolio_greeks[user_id] = portfolio_greeks

        await self._check_limits(user_id, portfolio_greeks)

        return portfolio_greeks

    async def _check_limits(self, user_id: str, greeks: PortfolioGreeks) -> None:
        """Check Greeks limits and generate alerts."""
        alerts = []

        if greeks.delta_utilization > 80:
            alerts.append(GreeksAlert(
                user_id=user_id,
                limit_type=GreeksLimitType.DELTA,
                current_value=abs(greeks.total_delta),
                limit_value=greeks.delta_limit,
                utilization_percent=greeks.delta_utilization,
                severity='warning'
            ))

        if greeks.delta_utilization > 100:
            alerts[-1].severity = 'critical'

        if greeks.gamma_utilization > 80:
            alerts.append(GreeksAlert(
                user_id=user_id,
                limit_type=GreeksLimitType.GAMMA,
                current_value=abs(greeks.total_gamma),
                limit_value=greeks.gamma_limit,
                utilization_percent=greeks.gamma_utilization,
                severity='warning'
            ))

        if greeks.theta_utilization > 80:
            alerts.append(GreeksAlert(
                user_id=user_id,
                limit_type=GreeksLimitType.THETA,
                current_value=abs(greeks.total_theta),
                limit_value=greeks.theta_limit,
                utilization_percent=greeks.theta_utilization,
                severity='warning'
            ))

        if greeks.vega_utilization > 80:
            alerts.append(GreeksAlert(
                user_id=user_id,
                limit_type=GreeksLimitType.VEGA,
                current_value=abs(greeks.total_vega),
                limit_value=greeks.vega_limit,
                utilization_percent=greeks.vega_utilization,
                severity='warning'
            ))

        self._alerts[user_id] = alerts

    def get_portfolio_greeks(self, user_id: str) -> Optional[PortfolioGreeks]:
        """Get current portfolio Greeks."""
        return self._portfolio_greeks.get(user_id)

    def get_greeks_summary(self, user_id: str) -> Dict:
        """Get Greeks summary."""
        greeks = self._portfolio_greeks.get(user_id)
        if not greeks:
            return {}

        return {
            'delta': {
                'value': greeks.total_delta,
                'limit': greeks.delta_limit,
                'utilization': greeks.delta_utilization
            },
            'gamma': {
                'value': greeks.total_gamma,
                'limit': greeks.gamma_limit,
                'utilization': greeks.gamma_utilization
            },
            'theta': {
                'value': greeks.total_theta,
                'limit': greeks.theta_limit,
                'utilization': greeks.theta_utilization
            },
            'vega': {
                'value': greeks.total_vega,
                'limit': greeks.vega_limit,
                'utilization': greeks.vega_utilization
            },
            'position_count': greeks.position_count,
            'option_count': greeks.option_count
        }


greeks_monitor = GreeksMonitor()


def get_greeks_monitor() -> GreeksMonitor:
    return greeks_monitor
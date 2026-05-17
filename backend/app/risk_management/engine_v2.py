"""
Institutional Risk Engine
=========================
Unified risk management engine integrating all advanced risk components.
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field

from app.risk_management.engine import risk_engine as BaseRiskEngine
from app.risk_management.exposure_manager import get_exposure_manager
from app.risk_management.margin_manager import get_margin_manager

from app.risk_management.analytics.var_engine import get_var_engine
from app.risk_management.analytics.stress_engine import get_stress_engine
from app.risk_management.analytics.greeks_monitor import get_greeks_monitor
from app.risk_management.analytics.portfolio_aggregator import get_portfolio_aggregator

from app.risk_management.advanced.order_throttler import get_order_throttler
from app.risk_management.advanced.circuit_breaker import get_circuit_breaker
from app.risk_management.advanced.risk_alerts import get_risk_alert_manager, AlertCategory, AlertSeverity


logger = logging.getLogger('risk_engine.institutional')


@dataclass
class RiskCheckResult:
    """Complete risk check result."""
    allowed: bool
    order_value: float
    risk_checks: Dict[str, Any]
    throttle_result: Optional[Dict]
    circuit_breaker_result: Optional[Dict]
    fat_finger_result: Optional[Dict]
    block_reason: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class InstitutionalRiskEngine:
    """
    Institutional-grade risk engine combining all advanced components.
    """

    def __init__(self):
        self.logger = logging.getLogger('institutional_risk')

        self.base_engine = BaseRiskEngine

        self.var_engine = get_var_engine()
        self.stress_engine = get_stress_engine()
        self.greeks_monitor = get_greeks_monitor()
        self.portfolio_aggregator = get_portfolio_aggregator()

        self.order_throttler = get_order_throttler()
        self.circuit_breaker = get_circuit_breaker()
        self.alert_manager = get_risk_alert_manager()

        self.exposure_manager = get_exposure_manager()
        self.margin_manager = get_margin_manager()

        self._running = False

    async def start(self):
        """Start the risk engine."""
        self._running = True
        logger.info("Institutional Risk Engine started")

    async def stop(self):
        """Stop the risk engine."""
        self._running = False
        logger.info("Institutional Risk Engine stopped")

    async def check_order(
        self,
        user_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        order_id: str = None
    ) -> RiskCheckResult:
        """
        Comprehensive order risk check.
        """
        order_value = quantity * price

        throttle_result = await self.order_throttler.check_order(
            user_id, symbol, side, quantity, price, order_id
        )

        circuit_breaker_result = await self.circuit_breaker.check_order(
            user_id, symbol, price, order_value
        )

        risk_checks = await self._run_risk_checks(user_id, order_value)

        warnings = []
        if throttle_result.action.value == 'warn':
            warnings.append(f"Throttle: {throttle_result.reason}")
        if circuit_breaker_result.value == 'warn':
            warnings.append(f"Circuit: {circuit_breaker_result.reason}")

        allowed = (
            throttle_result.action.value == 'allow' and
            circuit_breaker_result.value in ['allow', 'warn'] and
            risk_checks['allowed']
        )

        block_reason = None
        if not allowed:
            if throttle_result.action.value == 'block':
                block_reason = f"Throttle: {throttle_result.reason}"
            elif throttle_result.action.value == 'cooldown':
                block_reason = f"Cooldown: {throttle_result.reason}"
            elif circuit_breaker_result.value == 'block':
                block_reason = f"Circuit Breaker: {circuit_breaker_result.reason}"
            elif not risk_checks['allowed']:
                block_reason = risk_checks.get('reason', 'Risk check failed')

            await self.alert_manager.create_alert(
                user_id=user_id,
                category=AlertCategory.LIMIT_BREACH,
                severity=AlertSeverity.CRITICAL,
                title="Order Blocked",
                message=block_reason,
                current_value=order_value,
                limit_value=risk_checks.get('limit_value', order_value),
                related_entity_type='order',
                related_entity_id=order_id
            )

        return RiskCheckResult(
            allowed=allowed,
            order_value=order_value,
            risk_checks=risk_checks,
            throttle_result={'action': throttle_result.action.value, 'reason': throttle_result.reason},
            circuit_breaker_result={'action': circuit_breaker_result.value, 'reason': circuit_breaker_result.reason} if hasattr(circuit_breaker_result, 'value') else circuit_breaker_result,
            fat_finger_result={'status': 'pass'} if throttle_result.action.value != 'block' else {'status': 'blocked', 'reason': throttle_result.reason},
            block_reason=block_reason,
            warnings=warnings
        )

    async def _run_risk_checks(self, user_id: str, order_value: float) -> Dict:
        """Run basic risk checks."""
        trading_allowed, reason = self.base_engine.is_trading_allowed(user_id)

        if not trading_allowed:
            return {'allowed': False, 'reason': reason, 'limit_value': 0}

        state = self.base_engine.get_state(user_id)
        config = self.base_engine.get_config(user_id)

        margin_state = self.margin_manager.get_margin_state(user_id)
        if margin_state.margin_available < order_value:
            return {
                'allowed': False,
                'reason': f"Insufficient margin: need {order_value}, have {margin_state.margin_available}",
                'limit_value': margin_state.margin_available
            }

        if state.open_positions >= config.max_open_positions:
            return {
                'allowed': False,
                'reason': f"Max positions reached: {state.open_positions}",
                'limit_value': config.max_open_positions
            }

        return {'allowed': True, 'reason': 'OK', 'limit_value': config.max_position_value}

    async def calculate_portfolio_risk(
        self,
        user_id: str,
        positions: List[Dict],
        strategies: List[Dict],
        market_data: Dict[str, Dict],
        cash_balance: float
    ) -> Dict:
        """Calculate complete portfolio risk."""
        margin_state_dict = {
            'margin_utilization': self.margin_manager.get_margin_state(user_id).margin_utilization,
            'margin_available': self.margin_manager.get_margin_state(user_id).margin_available,
            'daily_pnl': 0,
            'weekly_pnl': 0,
            'monthly_pnl': 0
        }

        portfolio_risk = await self.portfolio_aggregator.calculate_portfolio_risk(
            user_id=user_id,
            positions=positions,
            strategies=strategies,
            market_data=market_data,
            cash_balance=cash_balance,
            margin_state=margin_state_dict
        )

        stress_results = await self.stress_engine.run_all_scenarios(
            positions={p.get('symbol', ''): {'value': p.get('value', 0), 'sector': p.get('sector', 'OTHER')}
                      for p in positions},
            portfolio_value=portfolio_risk.total_portfolio_value,
            cash_balance=cash_balance,
            margin_available=margin_state_dict.get('margin_available', cash_balance)
        )

        return {
            'user_id': user_id,
            'portfolio': {
                'total_value': portfolio_risk.total_portfolio_value,
                'cash': portfolio_risk.cash_balance,
                'invested': portfolio_risk.invested_value,
                'gross_exposure': portfolio_risk.gross_exposure,
                'net_exposure': portfolio_risk.net_exposure,
                'leverage': portfolio_risk.leverage
            },
            'var': {
                'var_95': portfolio_risk.var_95,
                'var_99': portfolio_risk.var_99,
                'expected_shortfall': portfolio_risk.expected_shortfall
            },
            'margin': {
                'utilization': portfolio_risk.margin_utilization,
                'available': portfolio_risk.margin_available
            },
            'risk_level': portfolio_risk.risk_level,
            'strategies': [
                {
                    'strategy_id': s.strategy_id,
                    'name': s.strategy_name,
                    'value': s.total_value,
                    'pnl': s.pnl,
                    'var_95': s.var_95,
                    'risk_score': s.risk_score
                }
                for s in portfolio_risk.strategies
            ],
            'sectors': portfolio_risk.sector_exposure,
            'heatmap': portfolio_risk.heatmap_data,
            'stress_tests': [
                {
                    'scenario': r.scenario_name,
                    'loss_percent': r.portfolio_loss_percent,
                    'severity': r.severity.value
                }
                for r in stress_results[:5]
            ],
            'greeks': self.greeks_monitor.get_greeks_summary(user_id),
            'alerts': self.alert_manager.get_active_alerts(user_id),
            'circuit_breakers': self.circuit_breaker.get_status(user_id),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

    async def get_dashboard_summary(self) -> Dict:
        """Get summary for risk dashboard."""
        user_risks = self.portfolio_aggregator.get_all_user_risks()
        alert_summary = self.alert_manager.get_alert_summary()

        return {
            'total_users': len(user_risks),
            'total_portfolio_value': sum(r.get('portfolio_value', 0) for r in user_risks),
            'aggregate_var_95': sum(r.get('var_95', 0) for r in user_risks),
            'risk_distribution': {
                'low': sum(1 for r in user_risks if r.get('risk_level') == 'low'),
                'medium': sum(1 for r in user_risks if r.get('risk_level') == 'medium'),
                'high': sum(1 for r in user_risks if r.get('risk_level') == 'high'),
                'critical': sum(1 for r in user_risks if r.get('risk_level') == 'critical')
            },
            'alerts': alert_summary,
            'throttling_stats': self.order_throttler.get_global_stats()
        }


institutional_risk_engine = InstitutionalRiskEngine()


def get_institutional_risk_engine() -> InstitutionalRiskEngine:
    return institutional_risk_engine
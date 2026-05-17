"""
Stress Testing Engine
=====================
Institutional-grade stress testing with historical, hypothetical, and custom scenarios.
"""

import numpy as np
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
import logging

logger = logging.getLogger('risk_engine.stress')


class ScenarioType(str, Enum):
    HISTORICAL = "historical"
    HYPOTHETICAL = "hypothetical"
    CUSTOM = "custom"
    REVERSE = "reverse"


class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"
    EXTREME = "extreme"


@dataclass
class StressScenario:
    """Stress test scenario definition."""
    scenario_id: str
    name: str
    description: str
    scenario_type: ScenarioType
    severity: SeverityLevel

    price_changes: Dict[str, float] = field(default_factory=dict)
    volatility_multiplier: float = 1.0
    correlation_breakdown: float = 0.0
    liquidity_shock: float = 0.0

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StressResult:
    """Stress test result."""
    scenario_id: str
    scenario_name: str
    scenario_type: ScenarioType
    severity: SeverityLevel

    portfolio_value_before: float
    portfolio_value_after: float
    portfolio_loss: float
    portfolio_loss_percent: float

    position_impacts: Dict[str, Dict]
    sector_impacts: Dict[str, Dict]

    var_before: float
    var_after: float
    var_change_percent: float

    margin_requirement: float
    margin_available: float
    margin_utilization_after: float

    calculation_time: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class StressTestingEngine:
    """
    Comprehensive stress testing engine with multiple scenario types.
    """

    def __init__(self, var_engine=None):
        self.var_engine = var_engine
        self.logger = logging.getLogger('stress_engine')

        self._scenarios: Dict[str, StressScenario] = {}
        self._results: List[StressResult] = []

        self._register_default_scenarios()

    def _register_default_scenarios(self):
        """Register default stress scenarios."""
        self.register_scenario(StressScenario(
            scenario_id="2008_crisis",
            name="2008 Financial Crisis",
            description="Simulates the 2008 financial crisis scenario",
            scenario_type=ScenarioType.HISTORICAL,
            severity=SeverityLevel.EXTREME,
            price_changes={
                'FINANCE': -0.50,
                'IT': -0.35,
                'ENERGY': -0.40,
                'FMCG': -0.15,
                'AUTOMOBILE': -0.45,
            },
            volatility_multiplier=3.0,
            correlation_breakdown=0.3,
            start_date=datetime(2008, 9, 1, tzinfo=timezone.utc),
            end_date=datetime(2009, 3, 31, tzinfo=timezone.utc)
        ))

        self.register_scenario(StressScenario(
            scenario_id="2020_crash",
            name="2020 COVID Crash",
            description="Simulates the March 2020 market crash",
            scenario_type=ScenarioType.HISTORICAL,
            severity=SeverityLevel.EXTREME,
            price_changes={
                'AUTOMOBILE': -0.35,
                'IT': -0.25,
                'FINANCE': -0.40,
                'METALS': -0.45,
                'PHARMA': -0.10,
            },
            volatility_multiplier=2.5,
            correlation_breakdown=0.2,
            start_date=datetime(2020, 2, 20, tzinfo=timezone.utc),
            end_date=datetime(2020, 3, 23, tzinfo=timezone.utc)
        ))

        self.register_scenario(StressScenario(
            scenario_id="flash_crash",
            name="Flash Crash",
            description="Simulates a sudden flash crash scenario",
            scenario_type=ScenarioType.HISTORICAL,
            severity=SeverityLevel.HIGH,
            price_changes={
                'IT': -0.15,
                'FINANCE': -0.12,
                'ENERGY': -0.18,
            },
            volatility_multiplier=5.0,
            correlation_breakdown=0.5,
            start_date=datetime(2010, 5, 6, tzinfo=timezone.utc),
            end_date=datetime(2010, 5, 6, tzinfo=timezone.utc)
        ))

        self.register_scenario(StressScenario(
            scenario_id="parallel_shift_down",
            name="Parallel Market Shift",
            description="10% downward parallel shift in all markets",
            scenario_type=ScenarioType.HYPOTHETICAL,
            severity=SeverityLevel.HIGH,
            price_changes={
                'IT': -0.10,
                'FINANCE': -0.10,
                'ENERGY': -0.10,
                'FMCG': -0.10,
                'AUTOMOBILE': -0.10,
                'METALS': -0.10,
                'PHARMA': -0.10,
            },
            volatility_multiplier=1.5
        ))

        self.register_scenario(StressScenario(
            scenario_id="steepening_yield",
            name="Yield Curve Steepening",
            description="Interest rates rise, yield curve steepens",
            scenario_type=ScenarioType.HYPOTHETICAL,
            severity=SeverityLevel.MEDIUM,
            price_changes={
                'FINANCE': 0.05,
                'REAL_ESTATE': -0.08,
                'UTILITIES': -0.05,
            },
            volatility_multiplier=1.2
        ))

        self.register_scenario(StressScenario(
            scenario_id="volatility_spike",
            name="Volatility Spike",
            description="Market volatility increases by 200%",
            scenario_type=ScenarioType.HYPOTHETICAL,
            severity=SeverityLevel.HIGH,
            price_changes={},
            volatility_multiplier=3.0
        ))

    def register_scenario(self, scenario: StressScenario) -> None:
        """Register a new stress scenario."""
        self._scenarios[scenario.scenario_id] = scenario
        self.logger.info(f"Registered stress scenario: {scenario.scenario_id} - {scenario.name}")

    def get_scenario(self, scenario_id: str) -> Optional[StressScenario]:
        """Get a scenario by ID."""
        return self._scenarios.get(scenario_id)

    def get_all_scenarios(self) -> List[Dict]:
        """Get all registered scenarios."""
        return [
            {
                'scenario_id': s.scenario_id,
                'name': s.name,
                'description': s.description,
                'type': s.scenario_type.value,
                'severity': s.severity.value,
                'created_at': s.created_at.isoformat()
            }
            for s in self._scenarios.values()
        ]

    async def run_stress_test(
        self,
        scenario_id: str,
        positions: Dict[str, Dict],
        portfolio_value: float,
        cash_balance: float,
        margin_available: float
    ) -> Optional[StressResult]:
        """Run a stress test for a specific scenario."""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            self.logger.error(f"Scenario not found: {scenario_id}")
            return None

        start_time = datetime.now(timezone.utc)

        scenario_positions = self._apply_scenario(positions, scenario)

        scenario_value = sum(
            pos['value'] * (1 + scenario.price_changes.get(pos.get('sector', 'OTHER'), 0))
            for pos in scenario_positions.values()
        )

        loss = portfolio_value - scenario_value
        loss_percent = (loss / portfolio_value * 100) if portfolio_value > 0 else 0

        position_impacts = {}
        sector_impacts = defaultdict(lambda: {'before': 0, 'after': 0, 'change': 0})

        for symbol, pos in positions.items():
            sector = pos.get('sector', 'OTHER')
            original_value = pos['value']
            stressed_value = original_value * (1 + scenario.price_changes.get(sector, 0))

            position_impacts[symbol] = {
                'original_value': original_value,
                'stressed_value': stressed_value,
                'loss': original_value - stressed_value,
                'loss_percent': ((original_value - stressed_value) / original_value * 100) if original_value > 0 else 0
            }

            sector_impacts[sector]['before'] += original_value
            sector_impacts[sector]['after'] += stressed_value

        for sector in sector_impacts:
            before = sector_impacts[sector]['before']
            after = sector_impacts[sector]['after']
            sector_impacts[sector]['change'] = before - after
            sector_impacts[sector]['change_percent'] = ((before - after) / before * 100) if before > 0 else 0

        margin_required = scenario_value * 0.15
        margin_utilization = (margin_required / (cash_balance + margin_available) * 100) if (cash_balance + margin_available) > 0 else 0

        var_before = 0
        var_after = 0
        if self.var_engine:
            var_before_result = self.var_engine.calculate_historical_var(positions, portfolio_value)
            var_before = var_before_result.var_95
            var_after_result = self.var_engine.calculate_historical_var(scenario_positions, scenario_value)
            var_after = var_after_result.var_95

        var_change = ((var_after - var_before) / var_before * 100) if var_before > 0 else 0

        calculation_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        result = StressResult(
            scenario_id=scenario.scenario_id,
            scenario_name=scenario.name,
            scenario_type=scenario.scenario_type,
            severity=scenario.severity,
            portfolio_value_before=portfolio_value,
            portfolio_value_after=scenario_value,
            portfolio_loss=loss,
            portfolio_loss_percent=loss_percent,
            position_impacts=position_impacts,
            sector_impacts=dict(sector_impacts),
            var_before=var_before,
            var_after=var_after,
            var_change_percent=var_change,
            margin_requirement=margin_required,
            margin_available=cash_balance + margin_available,
            margin_utilization_after=margin_utilization,
            calculation_time=calculation_time
        )

        self._results.append(result)
        return result

    def _apply_scenario(
        self,
        positions: Dict[str, Dict],
        scenario: StressScenario
    ) -> Dict[str, Dict]:
        """Apply scenario effects to positions."""
        stressed_positions = {}

        for symbol, pos in positions.items():
            sector = pos.get('sector', 'OTHER')

            price_change = scenario.price_changes.get(sector, 0)

            new_value = pos['value'] * (1 + price_change)
            new_quantity = pos.get('quantity', 0)
            if pos.get('current_price'):
                new_quantity = new_value / pos.get('current_price', pos.get('average_price', 1))

            stressed_positions[symbol] = {
                **pos,
                'value': new_value,
                'quantity': int(new_quantity),
                'stressed': True
            }

        return stressed_positions

    async def run_all_scenarios(
        self,
        positions: Dict[str, Dict],
        portfolio_value: float,
        cash_balance: float,
        margin_available: float
    ) -> List[StressResult]:
        """Run all registered stress scenarios."""
        results = []

        for scenario_id in self._scenarios.keys():
            result = await self.run_stress_test(
                scenario_id,
                positions,
                portfolio_value,
                cash_balance,
                margin_available
            )
            if result:
                results.append(result)

        return results

    def create_custom_scenario(
        self,
        scenario_id: str,
        name: str,
        description: str,
        price_changes: Dict[str, float],
        volatility_multiplier: float = 1.0,
        severity: SeverityLevel = SeverityLevel.MEDIUM
    ) -> StressScenario:
        """Create a custom stress scenario."""
        scenario = StressScenario(
            scenario_id=scenario_id,
            name=name,
            description=description,
            scenario_type=ScenarioType.CUSTOM,
            severity=severity,
            price_changes=price_changes,
            volatility_multiplier=volatility_multiplier
        )

        self.register_scenario(scenario)
        return scenario

    def get_results(self, limit: int = 100) -> List[Dict]:
        """Get stress test results."""
        return [
            {
                'scenario_id': r.scenario_id,
                'scenario_name': r.scenario_name,
                'severity': r.severity.value,
                'portfolio_loss': r.portfolio_loss,
                'portfolio_loss_percent': r.portfolio_loss_percent,
                'var_before': r.var_before,
                'var_after': r.var_after,
                'timestamp': r.timestamp.isoformat()
            }
            for r in self._results[-limit:]
        ]

    def get_worst_case(self, limit: int = 5) -> List[Dict]:
        """Get worst-case scenarios by loss."""
        sorted_results = sorted(self._results, key=lambda x: x.portfolio_loss_percent, reverse=True)
        return [
            {
                'scenario_id': r.scenario_id,
                'scenario_name': r.scenario_name,
                'severity': r.severity.value,
                'portfolio_loss_percent': r.portfolio_loss_percent,
                'timestamp': r.timestamp.isoformat()
            }
            for r in sorted_results[:limit]
        ]


stress_engine = StressTestingEngine()


def get_stress_engine() -> StressTestingEngine:
    return stress_engine
"""
Testing Framework and Sandbox Sync
=====================================
"""

import logging
import asyncio
import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .models import (
    ZerodhaOrder,
    ZerodhaPosition,
    ZerodhaPortfolio,
    ZerodhaTick,
    OrderParams,
    Exchange,
    ProductType,
    OrderType,
    TransactionType,
    VALIDITY,
    MarketSession,
)
from .client import BrokerError, OrderRejectedError
from .orders import OrderService, get_order_service

logger = logging.getLogger('zerodha.testing')


class TestMode(str, Enum):
    SANDBOX = "SANDBOX"
    LIVE_SIMULATION = "LIVE_SIMULATION"
    FAILURE_SIMULATION = "FAILURE_SIMULATION"


@dataclass
class TestScenario:
    name: str
    description: str
    setup: Optional[Callable] = None
    execute: Optional[Callable] = None
    verify: Optional[Callable] = None
    cleanup: Optional[Callable] = None


@dataclass
class TestResult:
    scenario_name: str
    passed: bool
    duration_ms: float = 0.0
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


class MockExchange:
    """
    Simulates exchange behavior for testing.
    """

    def __init__(self):
        self._orders: Dict[str, Dict] = {}
        self._positions: Dict[str, Dict] = {}
        self._instruments: Dict[str, Dict] = {}
        self._quotes: Dict[str, Dict] = {}
        self._failure_mode: Optional[str] = None
        self._delay_ms: int = 0

        self._initialize_mock_data()

    def _initialize_mock_data(self) -> None:
        self._instruments = {
            "RELIANCE": {
                "instrument_token": 288974,
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "name": "Reliance Industries",
                "lot_size": 1,
                "tick_size": 0.05,
            },
            "TCS": {
                "instrument_token": 295321,
                "tradingsymbol": "TCS",
                "exchange": "NSE",
                "name": "Tata Consultancy Services",
                "lot_size": 1,
                "tick_size": 0.05,
            },
            "HDFCBANK": {
                "instrument_token": 341249,
                "tradingsymbol": "HDFCBANK",
                "exchange": "NSE",
                "name": "HDFC Bank",
                "lot_size": 1,
                "tick_size": 0.05,
            },
            "INFY": {
                "instrument_token": 408065,
                "tradingsymbol": "INFY",
                "exchange": "NSE",
                "name": "Infosys",
                "lot_size": 1,
                "tick_size": 0.05,
            },
        }

        self._quotes = {
            token: {
                "last_price": round(random.uniform(100, 5000), 2),
                "open": round(random.uniform(100, 5000), 2),
                "high": round(random.uniform(100, 5000), 2),
                "low": round(random.uniform(100, 5000), 2),
                "close": round(random.uniform(100, 5000), 2),
                "volume": random.randint(100000, 10000000),
                "oi": random.randint(100000, 5000000),
            }
            for token in self._instruments.keys()
        }

    def set_failure_mode(self, mode: Optional[str]) -> None:
        self._failure_mode = mode

    def set_delay(self, delay_ms: int) -> None:
        self._delay_ms = delay_ms

    def place_order(self, params: Dict) -> Dict:
        if self._failure_mode == "rejection":
            raise OrderRejectedError("Mock exchange rejection", exchange_code="ME101")

        if self._failure_mode == "timeout":
            raise BrokerError("Mock timeout", retryable=True)

        if self._delay_ms > 0:
            import time
            time.sleep(self._delay_ms / 1000)

        order_id = f"MOCK{uuid.uuid4().hex[:10].upper()}"

        order = {
            "order_id": order_id,
            "tradingsymbol": params.get("tradingsymbol", ""),
            "exchange": params.get("exchange", "NSE"),
            "transaction_type": params.get("transaction_type", "BUY"),
            "quantity": params.get("quantity", 0),
            "filled_quantity": 0,
            "pending_quantity": params.get("quantity", 0),
            "price": params.get("price", 0),
            "trigger_price": params.get("trigger_price", 0),
            "order_type": params.get("order_type", "LIMIT"),
            "product": params.get("product", "MIS"),
            "status": "OPEN",
            "validity": params.get("validity", "DAY"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        self._orders[order_id] = order

        symbol = params.get("tradingsymbol", "")
        if symbol in self._positions:
            pos = self._positions[symbol]
            if params.get("transaction_type") == "BUY":
                pos["quantity"] += params.get("quantity", 0)
            else:
                pos["quantity"] -= params.get("quantity", 0)
        else:
            qty = params.get("quantity", 0) if params.get("transaction_type") == "BUY" else -params.get("quantity", 0)
            self._positions[symbol] = {
                "tradingsymbol": symbol,
                "exchange": params.get("exchange", "NSE"),
                "product": params.get("product", "MIS"),
                "quantity": qty,
                "average_price": params.get("price", 0),
                "last_price": params.get("price", 0),
                "pnl": 0,
            }

        return order

    def modify_order(self, order_id: str, params: Dict) -> Dict:
        if order_id not in self._orders:
            raise BrokerError(f"Order not found: {order_id}")

        order = self._orders[order_id]

        if "price" in params:
            order["price"] = params["price"]
        if "quantity" in params:
            order["quantity"] = params["quantity"]
        if "trigger_price" in params:
            order["trigger_price"] = params["trigger_price"]

        order["updated_at"] = datetime.now(timezone.utc).isoformat()

        return order

    def cancel_order(self, order_id: str) -> Dict:
        if order_id not in self._orders:
            raise BrokerError(f"Order not found: {order_id}")

        order = self._orders[order_id]
        order["status"] = "CANCELLED"
        order["cancelled_quantity"] = order.get("quantity", 0)
        order["updated_at"] = datetime.now(timezone.utc).isoformat()

        return order

    def get_order(self, order_id: str) -> Dict:
        if order_id not in self._orders:
            raise BrokerError(f"Order not found: {order_id}")
        return self._orders[order_id]

    def get_orders(self) -> List[Dict]:
        return list(self._orders.values())

    def get_positions(self) -> List[Dict]:
        return list(self._positions.values())

    def get_quote(self, symbol: str) -> Dict:
        return self._quotes.get(symbol, {})


class SandboxBroker:
    """
    Paper trading broker that simulates live broker behavior.
    """

    def __init__(
        self,
        initial_balance: float = 100000.0,
        mock_exchange: Optional[MockExchange] = None,
    ):
        self.mock_exchange = mock_exchange or MockExchange()

        self._balance = initial_balance
        self._initial_balance = initial_balance
        self._orders: Dict[str, ZerodhaOrder] = {}
        self._positions: Dict[str, ZerodhaPosition] = {}
        self._order_history: List[ZerodhaOrder] = []

    def reset(self) -> None:
        self._balance = self._initial_balance
        self._orders.clear()
        self._positions.clear()
        self._order_history.clear()

    def place_order(self, params: OrderParams) -> ZerodhaOrder:
        result = self.mock_exchange.place_order(params.to_zerodha_params())

        order = ZerodhaOrder.from_zerodha_response(
            result,
            internal_order_id=f"SBOX{uuid.uuid4().hex[:12].upper()}",
        )

        self._orders[order.internal_order_id] = order
        self._order_history.append(order)

        logger.info(f"[SANDBOX] Order placed: {order.order_id} - {params.symbol} {params.quantity} @ {params.price}")

        return order

    def modify_order(self, order_id: str, params: Dict) -> ZerodhaOrder:
        result = self.mock_exchange.modify_order(order_id, params)
        return ZerodhaOrder.from_zerodha_response(result)

    def cancel_order(self, order_id: str) -> ZerodhaOrder:
        result = self.mock_exchange.cancel_order(order_id)
        return ZerodhaOrder.from_zerodha_response(result)

    def get_order(self, order_id: str) -> Optional[ZerodhaOrder]:
        for order in self._orders.values():
            if order.order_id == order_id:
                return order
        return None

    def get_orders(self) -> List[ZerodhaOrder]:
        return list(self._orders.values())

    def get_positions(self) -> List[ZerodhaPosition]:
        return list(self._positions.values())

    def get_balance(self) -> float:
        return self._balance

    def get_pnl(self) -> float:
        return self._balance - self._initial_balance


class BrokerTestSuite:
    """
    Comprehensive test suite for broker integration.
    """

    def __init__(self, broker: SandboxBroker):
        self.broker = broker
        self.results: List[TestResult] = []

    async def run_all_tests(self) -> Dict[str, Any]:
        scenarios = [
            self._test_order_placement,
            self._test_order_modification,
            self._test_order_cancellation,
            self._test_idempotency,
            self._test_failure_recovery,
        ]

        total_passed = 0
        total_failed = 0

        for scenario in scenarios:
            result = await scenario()
            self.results.append(result)

            if result.passed:
                total_passed += 1
            else:
                total_failed += 1

        return {
            "total_tests": len(scenarios),
            "passed": total_passed,
            "failed": total_failed,
            "results": [r.to_dict() for r in self.results],
        }

    async def _test_order_placement(self) -> TestResult:
        start_time = datetime.now(timezone.utc)

        try:
            params = OrderParams(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                transaction_type=TransactionType.BUY,
                quantity=10,
                product=ProductType.MIS,
                order_type=OrderType.LIMIT,
                price=2500.0,
            )

            order = self.broker.place_order(params)

            passed = order is not None and order.order_id is not None

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return TestResult(
                scenario_name="test_order_placement",
                passed=passed,
                duration_ms=duration,
                details={"order_id": order.order_id if order else None},
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TestResult(
                scenario_name="test_order_placement",
                passed=False,
                duration_ms=duration,
                error=str(e),
            )

    async def _test_order_modification(self) -> TestResult:
        start_time = datetime.now(timezone.utc)

        try:
            params = OrderParams(
                symbol="TCS",
                exchange=Exchange.NSE,
                transaction_type=TransactionType.BUY,
                quantity=5,
                product=ProductType.MIS,
                order_type=OrderType.LIMIT,
                price=3500.0,
            )

            order = self.broker.place_order(params)

            modified = self.broker.modify_order(order.order_id, {"price": 3600.0})

            passed = modified is not None and modified.price == 3600.0

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return TestResult(
                scenario_name="test_order_modification",
                passed=passed,
                duration_ms=duration,
                details={"modified_price": modified.price if modified else None},
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TestResult(
                scenario_name="test_order_modification",
                passed=False,
                duration_ms=duration,
                error=str(e),
            )

    async def _test_order_cancellation(self) -> TestResult:
        start_time = datetime.now(timezone.utc)

        try:
            params = OrderParams(
                symbol="HDFCBANK",
                exchange=Exchange.NSE,
                transaction_type=TransactionType.BUY,
                quantity=20,
                product=ProductType.MIS,
                order_type=OrderType.LIMIT,
                price=1600.0,
            )

            order = self.broker.place_order(params)
            cancelled = self.broker.cancel_order(order.order_id)

            passed = cancelled is not None and cancelled.status == "CANCELLED"

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return TestResult(
                scenario_name="test_order_cancellation",
                passed=passed,
                duration_ms=duration,
                details={"status": cancelled.status if cancelled else None},
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TestResult(
                scenario_name="test_order_cancellation",
                passed=False,
                duration_ms=duration,
                error=str(e),
            )

    async def _test_idempotency(self) -> TestResult:
        start_time = datetime.now(timezone.utc)

        try:
            params = OrderParams(
                symbol="INFY",
                exchange=Exchange.NSE,
                transaction_type=TransactionType.BUY,
                quantity=15,
                product=ProductType.MIS,
                order_type=OrderType.LIMIT,
                price=1500.0,
            )

            key = "IDEM_TEST123"

            order1 = self.broker.place_order(params)
            order2 = self.broker.place_order(params)

            passed = order1.order_id == order2.order_id

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return TestResult(
                scenario_name="test_idempotency",
                passed=passed,
                duration_ms=duration,
                details={"order1": order1.order_id, "order2": order2.order_id},
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TestResult(
                scenario_name="test_idempotency",
                passed=False,
                duration_ms=duration,
                error=str(e),
            )

    async def _test_failure_recovery(self) -> TestResult:
        start_time = datetime.now(timezone.utc)

        try:
            self.broker.mock_exchange.set_failure_mode("timeout")

            params = OrderParams(
                symbol="RELIANCE",
                exchange=Exchange.NSE,
                transaction_type=TransactionType.BUY,
                quantity=10,
                product=ProductType.MIS,
                order_type=OrderType.LIMIT,
                price=2500.0,
            )

            try:
                order = self.broker.place_order(params)
                passed = False
            except BrokerError as e:
                passed = e.retryable

            self.broker.mock_exchange.set_failure_mode(None)

            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return TestResult(
                scenario_name="test_failure_recovery",
                passed=passed,
                duration_ms=duration,
                details={"retryable_error": passed},
            )

        except Exception as e:
            duration = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            return TestResult(
                scenario_name="test_failure_recovery",
                passed=False,
                duration_ms=duration,
                error=str(e),
            )


@dataclass
class SandboxSyncConfig:
    initial_balance: float = 100000.0
    sync_interval_seconds: int = 60
    enable_position_sync: bool = True
    enable_order_sync: bool = True


class PaperTradingSync:
    """
    Synchronizes paper trading state with live broker for parallel operation.
    """

    def __init__(
        self,
        live_client: Any,
        sandbox_broker: SandboxBroker,
        config: Optional[SandboxSyncConfig] = None,
    ):
        self.live_client = live_client
        self.sandbox_broker = sandbox_broker
        self.config = config or SandboxSyncConfig()

        self._running = False
        self._last_sync: Optional[datetime] = None

    async def start_sync(self) -> None:
        self._running = True
        logger.info("Starting paper trading sync")

        while self._running:
            try:
                await self._sync_positions()
                await self._sync_orders()

                self._last_sync = datetime.now(timezone.utc)

            except Exception as e:
                logger.error(f"Sync error: {e}")

            await asyncio.sleep(self.config.sync_interval_seconds)

    def stop_sync(self) -> None:
        self._running = False
        logger.info("Stopped paper trading sync")

    async def _sync_positions(self) -> None:
        if not self.config.enable_position_sync:
            return

        live_positions = await self.live_client.get_positions()

        for live_pos in live_positions:
            self.sandbox_broker._positions[live_pos.symbol] = live_pos

    async def _sync_orders(self) -> None:
        if not self.config.enable_order_sync:
            return

        live_orders = await self.live_client.get_orders()

        for live_order in live_orders:
            self.sandbox_broker._orders[live_order.internal_order_id] = live_order

    def get_sync_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "sandbox_balance": self.sandbox_broker.get_balance(),
            "sandbox_orders": len(self.sandbox_broker._orders),
            "sandbox_positions": len(self.sandbox_broker._positions),
        }


_sandbox_broker: Optional[SandboxBroker] = None


def get_sandbox_broker(initial_balance: float = 100000.0) -> SandboxBroker:
    global _sandbox_broker
    if _sandbox_broker is None:
        _sandbox_broker = SandboxBroker(initial_balance=initial_balance)
    return _sandbox_broker
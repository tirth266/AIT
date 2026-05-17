"""
Order Reconciliation for Zerodha Broker
========================================
Ensures consistency between internal order state and broker order state.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from .client import ZerodhaClient, get_zerodha_client
from .models import ZerodhaOrder, ZerodhaPosition
from .audit import AuditLogger, AuditEvent, get_audit_logger

logger = logging.getLogger('zerodha.reconciliation')


class ReconciliationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"
    PENDING = "PENDING"


class DiscrepancyType(str, Enum):
    MISSING_IN_BROKER = "MISSING_IN_BROKER"
    MISSING_IN_INTERNAL = "MISSING_IN_INTERNAL"
    QUANTITY_MISMATCH = "QUANTITY_MISMATCH"
    STATUS_MISMATCH = "STATUS_MISMATCH"
    PRICE_MISMATCH = "PRICE_MISMATCH"


@dataclass
class OrderDiscrepancy:
    internal_order_id: str
    exchange_order_id: Optional[str]
    discrepancy_type: DiscrepancyType
    internal_value: Any = None
    broker_value: Any = None
    severity: str = "HIGH"
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class PositionDiscrepancy:
    symbol: str
    discrepancy_type: DiscrepancyType
    internal_quantity: int = 0
    broker_quantity: int = 0
    severity: str = "HIGH"
    detected_at: datetime = field(default_factory=datetime.now)


@dataclass
class ReconciliationResult:
    status: ReconciliationStatus
    order_discrepancies: List[OrderDiscrepancy]
    position_discrepancies: List[PositionDiscrepancy]
    reconciled_at: datetime
    internal_order_count: int
    broker_order_count: int
    internal_position_count: int
    broker_position_count: int
    execution_time_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class OrderReconciler:
    """
    Reconciles internal order state with broker order state.
    """

    def __init__(
        self,
        client: Optional[ZerodhaClient] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.client = client or get_zerodha_client()
        self.audit_logger = audit_logger or get_audit_logger()

        self._internal_orders: Dict[str, ZerodhaOrder] = {}
        self._internal_positions: Dict[str, ZerodhaPosition] = {}

        self._last_reconciliation: Optional[datetime] = None
        self._reconciliation_count = 0

        self._auto_reconcile_enabled = False
        self._auto_reconcile_interval = 60

    def set_internal_orders(self, orders: Dict[str, ZerodhaOrder]) -> None:
        self._internal_orders = orders

    def set_internal_positions(self, positions: Dict[str, ZerodhaPosition]) -> None:
        self._internal_positions = positions

    async def reconcile_orders(self) -> List[OrderDiscrepancy]:
        discrepancies: List[OrderDiscrepancy] = []

        internal_order_ids = set(self._internal_orders.keys())
        exchange_order_ids = {o.order_id for o in self._internal_orders.values() if o.order_id}

        broker_orders = await self.client.get_orders()
        broker_order_ids = {o.order_id for o in broker_orders}
        broker_orders_map = {o.order_id: o for o in broker_orders}

        for internal_id, internal_order in self._internal_orders.items():
            if not internal_order.order_id:
                continue

            if internal_order.order_id not in broker_order_ids:
                discrepancies.append(OrderDiscrepancy(
                    internal_order_id=internal_id,
                    exchange_order_id=internal_order.order_id,
                    discrepancy_type=DiscrepancyType.MISSING_IN_BROKER,
                    internal_value=internal_order.status,
                    broker_value=None,
                    severity="HIGH" if internal_order.is_pending() else "LOW",
                ))
            else:
                broker_order = broker_orders_map[internal_order.order_id]

                if broker_order.filled_quantity != internal_order.filled_quantity:
                    discrepancies.append(OrderDiscrepancy(
                        internal_order_id=internal_id,
                        exchange_order_id=internal_order.order_id,
                        discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                        internal_value=internal_order.filled_quantity,
                        broker_value=broker_order.filled_quantity,
                    ))

                if broker_order.status != internal_order.status:
                    if internal_order.is_pending() and broker_order.is_complete():
                        discrepancies.append(OrderDiscrepancy(
                            internal_order_id=internal_id,
                            exchange_order_id=internal_order.order_id,
                            discrepancy_type=DiscrepancyType.STATUS_MISMATCH,
                            internal_value=internal_order.status,
                            broker_value=broker_order.status,
                            severity="HIGH",
                        ))

        for broker_order in broker_orders:
            if broker_order.order_id not in exchange_order_ids:
                if broker_order.status in ["OPEN", "TRIGGER PENDING"]:
                    logger.warning(f"Found order in broker not tracked internally: {broker_order.order_id}")

        return discrepancies

    async def reconcile_positions(self) -> List[PositionDiscrepancy]:
        discrepancies: List[PositionDiscrepancy] = []

        internal_symbols = set(self._internal_positions.keys())

        broker_positions = await self.client.get_positions()
        broker_symbols = {p.symbol for p in broker_positions}
        broker_positions_map = {p.symbol: p for p in broker_positions}

        for symbol in internal_symbols:
            internal_pos = self._internal_positions[symbol]

            if symbol not in broker_symbols:
                if internal_pos.quantity != 0:
                    discrepancies.append(PositionDiscrepancy(
                        symbol=symbol,
                        discrepancy_type=DiscrepancyType.MISSING_IN_BROKER,
                        internal_quantity=internal_pos.quantity,
                        broker_quantity=0,
                        severity="HIGH" if internal_pos.quantity != 0 else "LOW",
                    ))
            else:
                broker_pos = broker_positions_map[symbol]

                if broker_pos.quantity != internal_pos.quantity:
                    discrepancies.append(PositionDiscrepancy(
                        symbol=symbol,
                        discrepancy_type=DiscrepancyType.QUANTITY_MISMATCH,
                        internal_quantity=internal_pos.quantity,
                        broker_quantity=broker_pos.quantity,
                    ))

        return discrepancies

    async def full_reconciliation(self) -> ReconciliationResult:
        start_time = datetime.now(timezone.utc)

        self.audit_logger.log(
            AuditEvent.RECONCILIATION_STARTED,
            {"internal_orders": len(self._internal_orders), "internal_positions": len(self._internal_positions)},
        )

        order_discrepancies = await self.reconcile_orders()
        position_discrepancies = await self.reconcile_positions()

        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

        if not order_discrepancies and not position_discrepancies:
            status = ReconciliationStatus.PASSED
        elif not order_discrepancies and position_discrepancies:
            status = ReconciliationStatus.PARTIAL
        else:
            status = ReconciliationStatus.FAILED

        result = ReconciliationResult(
            status=status,
            order_discrepancies=order_discrepancies,
            position_discrepancies=position_discrepancies,
            reconciled_at=datetime.now(timezone.utc),
            internal_order_count=len(self._internal_orders),
            broker_order_count=len(await self.client.get_orders()),
            internal_position_count=len(self._internal_positions),
            broker_position_count=len(await self.client.get_positions()),
            execution_time_ms=execution_time,
        )

        self._last_reconciliation = datetime.now(timezone.utc)
        self._reconciliation_count += 1

        self.audit_logger.log(
            AuditEvent.RECONCILIATION_COMPLETED,
            {
                "status": status.value,
                "order_discrepancies": len(order_discrepancies),
                "position_discrepancies": len(position_discrepancies),
                "execution_time_ms": execution_time,
            },
            severity="ERROR" if status == ReconciliationStatus.FAILED else "INFO",
        )

        if order_discrepancies:
            for disc in order_discrepancies:
                self.audit_logger.log(
                    AuditEvent.RECONCILIATION_MISMATCH,
                    asdict(disc),
                    severity="ERROR",
                )

        return result

    def enable_auto_reconciliation(self, interval_seconds: int = 60) -> None:
        self._auto_reconcile_enabled = True
        self._auto_reconcile_interval = interval_seconds

    def disable_auto_reconciliation(self) -> None:
        self._auto_reconcile_enabled = False

    async def start_auto_reconciliation(self) -> None:
        if not self._auto_reconcile_enabled:
            return

        while self._auto_reconcile_enabled:
            try:
                await self.full_reconciliation()
            except Exception as e:
                logger.error(f"Auto reconciliation error: {e}")

                self.audit_logger.log(
                    AuditEvent.RECONCILIATION_FAILED,
                    {"error": str(e)},
                    severity="ERROR",
                )

            await asyncio.sleep(self._auto_reconcile_interval)

    def get_reconciliation_history(self, count: int = 10) -> List[Dict[str, Any]]:
        entries = self.audit_logger.get_entries_by_event(AuditEvent.RECONCILIATION_COMPLETED, count)
        return [e.to_dict() for e in entries]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "last_reconciliation": self._last_reconciliation.isoformat() if self._last_reconciliation else None,
            "reconciliation_count": self._reconciliation_count,
            "internal_orders_tracked": len(self._internal_orders),
            "internal_positions_tracked": len(self._internal_positions),
            "auto_reconcile_enabled": self._auto_reconcile_enabled,
            "auto_reconcile_interval": self._auto_reconcile_interval,
        }


def asdict(obj):
    if hasattr(obj, '__dataclass_fields__'):
        return {f: getattr(obj, f) for f in obj.__dataclass_fields__}
    return {}


_reconciler: Optional[OrderReconciler] = None


def get_order_reconciler(client: Optional[ZerodhaClient] = None) -> OrderReconciler:
    global _reconciler
    if _reconciler is None:
        _reconciler = OrderReconciler(client=client)
    return _reconciler
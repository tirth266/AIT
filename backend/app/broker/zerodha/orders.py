"""
Order Service with Idempotency and Duplicate Prevention
========================================================
"""

import logging
import asyncio
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import threading

from .client import (
    ZerodhaClient,
    get_zerodha_client,
    BrokerError,
    OrderRejectedError,
    RateLimitError,
)
from .models import (
    ZerodhaOrder,
    OrderParams,
    OrderPlacementResult,
    OrderModificationParams,
    OrderCancellationParams,
    MarketSession,
    Exchange,
    ProductType,
    OrderType,
    TransactionType,
    VALIDITY,
)
from .audit import AuditLogger, AuditEvent, get_audit_logger

logger = logging.getLogger('zerodha.orders')


class OrderSource(str, Enum):
    SYSTEM = "SYSTEM"
    MANUAL = "MANUAL"
    STRATEGY = "STRATEGY"
    API = "API"


@dataclass
class PendingOrder:
    order_params: OrderParams
    idempotency_key: str
    source: OrderSource
    created_at: datetime
    retry_count: int = 0
    last_retry_at: Optional[datetime] = None


class OrderService:
    """
    Production-grade order service with idempotency, duplicate prevention, and audit logging.
    """

    def __init__(
        self,
        client: Optional[ZerodhaClient] = None,
        audit_logger: Optional[AuditLogger] = None,
    ):
        self.client = client or get_zerodha_client()
        self.audit_logger = audit_logger or get_audit_logger()

        self._pending_orders: Dict[str, PendingOrder] = {}
        self._order_cache: Dict[str, ZerodhaOrder] = {}
        self._idempotency_map: Dict[str, str] = {}

        self._order_placed_callbacks: List[Callable] = []
        self._order_updated_callbacks: List[Callable] = []
        self._order_rejected_callbacks: List[Callable] = []

        self._lock = threading.RLock()

        self._order_id_counter = 0

    def register_order_placed_callback(self, callback: Callable[[ZerodhaOrder], None]) -> None:
        self._order_placed_callbacks.append(callback)

    def register_order_updated_callback(self, callback: Callable[[ZerodhaOrder], None]) -> None:
        self._order_updated_callbacks.append(callback)

    def register_order_rejected_callback(self, callback: Callable[[str, str], None]) -> None:
        self._order_rejected_callbacks.append(callback)

    def _generate_order_id(self) -> str:
        with self._lock:
            self._order_id_counter += 1
            return f"ORD{int(datetime.now(timezone.utc).timestamp() * 1000)}{self._order_id_counter:04d}"

    def _generate_idempotency_key(
        self,
        symbol: str,
        exchange: Exchange,
        transaction_type: TransactionType,
        quantity: int,
        order_type: OrderType,
        price: float,
    ) -> str:
        key_parts = [
            str(symbol),
            str(exchange.value),
            str(transaction_type.value),
            str(quantity),
            str(order_type.value),
            str(round(price, 2)),
        ]

        key_string = "|".join(key_parts)
        return f"IDEM_{hashlib.sha256(key_string.encode()).hexdigest()[:16].upper()}"

    def _is_market_open(self) -> bool:
        return self.client.get_market_session().is_open

    async def place_order(
        self,
        params: OrderParams,
        source: OrderSource = OrderSource.SYSTEM,
        idempotency_key: Optional[str] = None,
    ) -> OrderPlacementResult:
        start_time = datetime.now(timezone.utc)

        market_session = self.client.get_market_session()
        if not market_session.is_open and params.product not in [ProductType.CNC, ProductType.NRML]:
            logger.warning(f"Attempting to place order when market is closed: {market_session.session_type}")

        if not idempotency_key:
            idempotency_key = self._generate_idempotency_key(
                params.symbol,
                params.exchange,
                params.transaction_type,
                params.quantity,
                params.order_type,
                params.price,
            )

        with self._lock:
            existing_internal_id = self._idempotency_map.get(idempotency_key)
            if existing_internal_id:
                cached_order = self._order_cache.get(existing_internal_id)
                if cached_order and not cached_order.is_complete():
                    logger.info(f"Duplicate order detected for idempotency key: {idempotency_key}")
                    return OrderPlacementResult(
                        success=False,
                        error="Duplicate order already in progress",
                        duplicate_order=True,
                        idempotency_key=idempotency_key,
                    )

        internal_order_id = self._generate_order_id()

        self.audit_logger.log(
            AuditEvent.ORDER_PLACEMENT_REQUESTED,
            {
                "internal_order_id": internal_order_id,
                "idempotency_key": idempotency_key,
                "symbol": params.symbol,
                "exchange": params.exchange.value,
                "transaction_type": params.transaction_type.value,
                "quantity": params.quantity,
                "order_type": params.order_type.value,
                "price": params.price,
                "product": params.product.value,
                "source": source.value,
            },
        )

        try:
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None,
                lambda: self.client.place_order_sync(params.to_zerodha_params())
            )

            order.internal_order_id = internal_order_id
            order.idempotency_key = idempotency_key

            with self._lock:
                self._order_cache[internal_order_id] = order
                self._idempotency_map[idempotency_key] = internal_order_id
                self._pending_orders.pop(idempotency_key, None)

            self.audit_logger.log(
                AuditEvent.ORDER_PLACED,
                {
                    "internal_order_id": internal_order_id,
                    "exchange_order_id": order.order_id,
                    "idempotency_key": idempotency_key,
                    "symbol": order.symbol,
                    "quantity": order.quantity,
                    "price": order.price,
                },
            )

            for callback in self._order_placed_callbacks:
                try:
                    callback(order)
                except Exception as e:
                    logger.error(f"Order placed callback error: {e}")

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            return OrderPlacementResult(
                success=True,
                order=order,
                idempotency_key=idempotency_key,
                placed_at=start_time,
            )

        except OrderRejectedError as e:
            self.audit_logger.log(
                AuditEvent.ORDER_REJECTED,
                {
                    "internal_order_id": internal_order_id,
                    "idempotency_key": idempotency_key,
                    "error": e.message,
                    "exchange_code": e.exchange_code,
                },
            )

            for callback in self._order_rejected_callbacks:
                try:
                    callback(internal_order_id, e.message)
                except Exception as e:
                    logger.error(f"Order rejected callback error: {e}")

            return OrderPlacementResult(
                success=False,
                error=e.message,
                exchange_rejection=True,
                idempotency_key=idempotency_key,
            )

        except RateLimitError as e:
            self.audit_logger.log(
                AuditEvent.RATE_LIMIT_EXCEEDED,
                {
                    "internal_order_id": internal_order_id,
                    "idempotency_key": idempotency_key,
                    "error": str(e),
                },
            )

            return OrderPlacementResult(
                success=False,
                error=str(e),
                retryable=True,
                idempotency_key=idempotency_key,
            )

        except BrokerError as e:
            self.audit_logger.log(
                AuditEvent.ORDER_PLACEMENT_FAILED,
                {
                    "internal_order_id": internal_order_id,
                    "idempotency_key": idempotency_key,
                    "error": str(e),
                    "retryable": e.retryable,
                },
            )

            if e.retryable:
                pending_order = PendingOrder(
                    order_params=params,
                    idempotency_key=idempotency_key,
                    source=source,
                    created_at=datetime.now(timezone.utc),
                )

                with self._lock:
                    self._pending_orders[idempotency_key] = pending_order

            return OrderPlacementResult(
                success=False,
                error=str(e),
                retryable=e.retryable,
                idempotency_key=idempotency_key,
            )

        except Exception as e:
            logger.error(f"Unexpected order placement error: {e}")

            self.audit_logger.log(
                AuditEvent.ORDER_PLACEMENT_FAILED,
                {
                    "internal_order_id": internal_order_id,
                    "idempotency_key": idempotency_key,
                    "error": str(e),
                    "retryable": True,
                },
            )

            return OrderPlacementResult(
                success=False,
                error=f"Internal error: {str(e)}",
                retryable=True,
                idempotency_key=idempotency_key,
            )

    async def modify_order(self, params: OrderModificationParams) -> ZerodhaOrder:
        internal_order_id = getattr(params, "internal_order_id", None)

        self.audit_logger.log(
            AuditEvent.ORDER_MODIFICATION_REQUESTED,
            {
                "order_id": params.order_id,
                "internal_order_id": internal_order_id,
                "quantity": params.quantity,
                "price": params.price,
                "trigger_price": params.trigger_price,
            },
        )

        try:
            loop = asyncio.get_event_loop()
            modify_params = {}

            if params.quantity is not None:
                modify_params["quantity"] = params.quantity

            if params.price is not None:
                modify_params["price"] = params.price

            if params.trigger_price is not None:
                modify_params["trigger_price"] = params.trigger_price

            if params.validity:
                modify_params["validity"] = params.validity.value

            order = await loop.run_in_executor(
                None,
                lambda: self.client.modify_order_sync(params.order_id, modify_params)
            )

            if internal_order_id and internal_order_id in self._order_cache:
                self._order_cache[internal_order_id].order_id = order.order_id
                self._order_cache[internal_order_id].price = order.price
                self._order_cache[internal_order_id].quantity = order.quantity
                self._order_cache[internal_order_id].trigger_price = order.trigger_price
                self._order_cache[internal_order_id].updated_at = datetime.now(timezone.utc)

            self.audit_logger.log(
                AuditEvent.ORDER_MODIFIED,
                {
                    "order_id": params.order_id,
                    "internal_order_id": internal_order_id,
                    "new_order_id": order.order_id,
                },
            )

            return order

        except BrokerError as e:
            self.audit_logger.log(
                AuditEvent.ORDER_MODIFICATION_FAILED,
                {
                    "order_id": params.order_id,
                    "internal_order_id": internal_order_id,
                    "error": str(e),
                },
            )
            raise

    async def cancel_order(self, params: OrderCancellationParams) -> ZerodhaOrder:
        internal_order_id = getattr(params, "internal_order_id", None)

        self.audit_logger.log(
            AuditEvent.ORDER_CANCELLATION_REQUESTED,
            {
                "order_id": params.order_id,
                "internal_order_id": internal_order_id,
                "variety": params.variety,
            },
        )

        try:
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None,
                lambda: self.client.cancel_order_sync(params.order_id, params.variety)
            )

            if internal_order_id and internal_order_id in self._order_cache:
                self._order_cache[internal_order_id].status = "CANCELLED"
                self._order_cache[internal_order_id].updated_at = datetime.now(timezone.utc)

            self.audit_logger.log(
                AuditEvent.ORDER_CANCELLED,
                {
                    "order_id": params.order_id,
                    "internal_order_id": internal_order_id,
                },
            )

            return order

        except BrokerError as e:
            self.audit_logger.log(
                AuditEvent.ORDER_CANCELLATION_FAILED,
                {
                    "order_id": params.order_id,
                    "internal_order_id": internal_order_id,
                    "error": str(e),
                },
            )
            raise

    async def get_order(self, order_id: str) -> Optional[ZerodhaOrder]:
        try:
            loop = asyncio.get_event_loop()
            order = await loop.run_in_executor(
                None,
                lambda: self.client.get_order_info_sync(order_id)
            )

            return order

        except BrokerError as e:
            logger.error(f"Failed to get order {order_id}: {e}")
            return None

    async def get_orders(self) -> List[ZerodhaOrder]:
        return await self.client.get_orders()

    async def get_positions(self) -> List[ZerodhaPosition]:
        return await self.client.get_positions()

    async def get_portfolio(self) -> List[ZerodhaPortfolio]:
        return await self.client.get_portfolio()

    async def get_margins(self) -> ZerodhaMargin:
        return await self.client.get_margins()

    def get_order_by_internal_id(self, internal_order_id: str) -> Optional[ZerodhaOrder]:
        return self._order_cache.get(internal_order_id)

    def get_order_by_idempotency_key(self, idempotency_key: str) -> Optional[ZerodhaOrder]:
        internal_id = self._idempotency_map.get(idempotency_key)
        if internal_id:
            return self._order_cache.get(internal_id)
        return None

    async def retry_pending_orders(self) -> Dict[str, Any]:
        results = {"success": 0, "failed": 0, "duplicates": 0}

        with self._lock:
            pending_items = list(self._pending_orders.items())

        for idempotency_key, pending in pending_items:
            if pending.retry_count >= 3:
                logger.warning(f"Max retries reached for pending order: {idempotency_key}")
                continue

            pending.retry_count += 1
            pending.last_retry_at = datetime.now(timezone.utc)

            result = await self.place_order(
                params=pending.order_params,
                source=pending.source,
                idempotency_key=idempotency_key,
            )

            if result.success:
                results["success"] += 1
            elif result.duplicate_order:
                results["duplicates"] += 1
            else:
                results["failed"] += 1

        return results

    def get_pending_orders_count(self) -> int:
        return len(self._pending_orders)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "cached_orders": len(self._order_cache),
            "pending_orders": len(self._pending_orders),
            "idempotency_mappings": len(self._idempotency_map),
        }


_order_service: Optional[OrderService] = None


def get_order_service(client: Optional[ZerodhaClient] = None) -> OrderService:
    global _order_service
    if _order_service is None:
        _order_service = OrderService(client=client)
    return _order_service
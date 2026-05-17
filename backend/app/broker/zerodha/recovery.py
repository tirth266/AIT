"""
Connection Recovery Logic
=========================
Handles reconnection, state recovery, and failover for broker connections.
"""

import logging
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from .auth import TokenManager, get_token_manager
from .client import ZerodhaClient, get_zerodha_client
from .orders import OrderService, get_order_service
from .websocket import KiteWebSocket, get_kite_websocket, WebSocketState
from .models import ZerodhaOrder, MarketSession

logger = logging.getLogger('zerodha.recovery')


class RecoveryState(str, Enum):
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    RECOVERING_ORDERS = "RECOVERING_ORDERS"
    RECOVERING_POSITIONS = "RECOVERING_POSITIONS"
    SYNCING_STATE = "SYNCING_STATE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class RecoveryResult:
    success: bool
    state: RecoveryState
    recovered_orders: int = 0
    recovered_positions: int = 0
    failed_operations: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class ConnectionRecovery:
    """
    Manages connection recovery, state synchronization, and failover.
    """

    def __init__(
        self,
        token_manager: Optional[TokenManager] = None,
        client: Optional[ZerodhaClient] = None,
        order_service: Optional[OrderService] = None,
        websocket: Optional[KiteWebSocket] = None,
    ):
        self.token_manager = token_manager or get_token_manager()
        self.client = client or get_zerodha_client()
        self.order_service = order_service or get_order_service(self.client)
        self.websocket = websocket

        self._state = RecoveryState.IDLE
        self._last_recovery: Optional[datetime] = None
        self._recovery_count = 0

        self._order_state_cache: Dict[str, ZerodhaOrder] = {}
        self._last_known_positions: Dict[str, int] = {}

        self._on_recovery_started: Optional[Callable] = None
        self._on_recovery_completed: Optional[Callable[[RecoveryResult], None]] = None

    def set_websocket(self, ws: KiteWebSocket) -> None:
        self.websocket = ws

    def set_recovery_started_callback(self, callback: Callable) -> None:
        self._on_recovery_started = callback

    def set_recovery_completed_callback(self, callback: Callable[[RecoveryResult], None]) -> None:
        self._on_recovery_completed = callback

    def _update_state(self, new_state: RecoveryState) -> None:
        self._state = new_state
        logger.info(f"Recovery state: {new_state.value}")

    async def perform_recovery(self) -> RecoveryResult:
        start_time = datetime.now(timezone.utc)

        logger.info("Starting connection recovery")
        self._update_state(RecoveryState.CONNECTING)
        self._recovery_count += 1

        if self._on_recovery_started:
            self._on_recovery_started()

        failed_operations: List[str] = []

        try:
            await self._ensure_token_valid()

            self._update_state(RecoveryState.RECOVERING_ORDERS)
            orders = await self.order_service.get_orders()
            self._order_state_cache = {o.order_id: o for o in orders if o.order_id}
            logger.info(f"Recovered {len(self._order_state_cache)} orders from broker")

            self._update_state(RecoveryState.RECOVERING_POSITIONS)
            positions = await self.order_service.get_positions()
            self._last_known_positions = {
                p.symbol: p.quantity for p in positions
            }
            logger.info(f"Recovered {len(self._last_known_positions)} positions from broker")

            self._update_state(RecoveryState.SYNCING_STATE)
            await self._sync_order_state()

            if self.websocket and not self.websocket.is_connected:
                logger.info("Reconnecting WebSocket")
                self.websocket.connect()

            self._update_state(RecoveryState.COMPLETED)

            self._last_recovery = datetime.now(timezone.utc)

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            result = RecoveryResult(
                success=True,
                state=RecoveryState.COMPLETED,
                recovered_orders=len(self._order_state_cache),
                recovered_positions=len(self._last_known_positions),
                execution_time_ms=execution_time,
            )

            if self._on_recovery_completed:
                self._on_recovery_completed(result)

            return result

        except Exception as e:
            logger.error(f"Recovery failed: {e}")
            self._update_state(RecoveryState.FAILED)

            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000

            result = RecoveryResult(
                success=False,
                state=RecoveryState.FAILED,
                failed_operations=failed_operations,
                execution_time_ms=execution_time,
                error=str(e),
            )

            if self._on_recovery_completed:
                self._on_recovery_completed(result)

            return result

    async def _ensure_token_valid(self) -> None:
        if not self.token_manager.is_valid:
            logger.warning("Token invalid, attempting refresh")
            await self.token_manager.refresh_token()

    async def _sync_order_state(self) -> None:
        pending_orders = [o for o in self._order_state_cache.values() if o.is_pending()]

        if not pending_orders:
            return

        logger.info(f"Syncing {len(pending_orders)} pending orders")

        for order in pending_orders:
            try:
                updated_order = await self.order_service.get_order(order.order_id)
                if updated_order:
                    self._order_state_cache[order.order_id] = updated_order
            except Exception as e:
                logger.warning(f"Failed to sync order {order.order_id}: {e}")

    async def check_and_recover_if_needed(self) -> Optional[RecoveryResult]:
        if self._should_recover():
            return await self.perform_recovery()
        return None

    def _should_recover(self) -> bool:
        if self._state in [RecoveryState.RECOVERING_ORDERS, RecoveryState.RECOVERING_POSITIONS]:
            return False

        if not self._last_recovery:
            return True

        time_since_recovery = datetime.now(timezone.utc) - self._last_recovery

        if time_since_recovery > timedelta(minutes=5):
            return True

        return False

    async def reconnect_websocket(self, max_retries: int = 3) -> bool:
        if not self.websocket:
            logger.warning("No WebSocket configured")
            return False

        for attempt in range(max_retries):
            try:
                self.websocket.connect(use_thread=False)

                if self.websocket.is_connected:
                    logger.info(f"WebSocket reconnected on attempt {attempt + 1}")
                    return True

            except Exception as e:
                logger.warning(f"WebSocket reconnect attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2 ** attempt)

        logger.error(f"WebSocket failed to reconnect after {max_retries} attempts")
        return False

    def get_pending_orders_from_cache(self) -> List[ZerodhaOrder]:
        return [o for o in self._order_state_cache.values() if o.is_pending()]

    def get_cached_positions(self) -> Dict[str, int]:
        return self._last_known_positions.copy()

    @property
    def state(self) -> RecoveryState:
        return self._state

    @property
    def last_recovery_time(self) -> Optional[datetime]:
        return self._last_recovery

    @property
    def recovery_count(self) -> int:
        return self._recovery_count

    def get_stats(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "last_recovery": self._last_recovery.isoformat() if self._last_recovery else None,
            "recovery_count": self._recovery_count,
            "cached_orders": len(self._order_state_cache),
            "cached_positions": len(self._last_known_positions),
        }


class BrokerFailoverManager:
    """
    Manages failover between multiple brokers (preparation for multi-broker support).
    """

    def __init__(self):
        self._brokers: Dict[str, Dict[str, Any]] = {}
        self._active_broker: Optional[str] = None

        self._failover_callbacks: List[Callable] = []

    def register_broker(
        self,
        broker_id: str,
        token_manager: TokenManager,
        client: ZerodhaClient,
        priority: int = 0,
    ) -> None:
        self._brokers[broker_id] = {
            "token_manager": token_manager,
            "client": client,
            "priority": priority,
            "available": True,
            "last_used": None,
        }

        if self._active_broker is None:
            self._active_broker = broker_id

    def set_active_broker(self, broker_id: str) -> bool:
        if broker_id not in self._brokers:
            return False

        self._active_broker = broker_id
        self._brokers[broker_id]["last_used"] = datetime.now(timezone.utc)

        for callback in self._failover_callbacks:
            callback(broker_id)

        return True

    def mark_broker_unavailable(self, broker_id: str) -> None:
        if broker_id in self._brokers:
            self._brokers[broker_id]["available"] = False
            logger.warning(f"Broker {broker_id} marked unavailable")

            self._attempt_failover()

    def mark_broker_available(self, broker_id: str) -> None:
        if broker_id in self._brokers:
            self._brokers[broker_id]["available"] = True
            logger.info(f"Broker {broker_id} marked available")

    def _attempt_failover(self) -> None:
        if self._active_broker is None:
            return

        available_brokers = [
            (bid, info) for bid, info in self._brokers.items()
            if info["available"] and bid != self._active_broker
        ]

        if not available_brokers:
            logger.error("No available brokers for failover")
            return

        available_brokers.sort(key=lambda x: x[1]["priority"], reverse=True)

        new_broker = available_brokers[0][0]
        self.set_active_broker(new_broker)

        logger.info(f"Failed over to broker: {new_broker}")

    def get_active_client(self) -> Optional[ZerodhaClient]:
        if self._active_broker and self._active_broker in self._brokers:
            return self._brokers[self._active_broker]["client"]
        return None

    def register_failover_callback(self, callback: Callable) -> None:
        self._failover_callbacks.append(callback)

    def get_broker_status(self) -> Dict[str, Any]:
        return {
            broker_id: {
                "available": info["available"],
                "priority": info["priority"],
                "last_used": info["last_used"].isoformat() if info["last_used"] else None,
            }
            for broker_id, info in self._brokers.items()
        }


_recovery_instance: Optional[ConnectionRecovery] = None


def get_connection_recovery(
    token_manager: Optional[TokenManager] = None,
    client: Optional[ZerodhaClient] = None,
) -> ConnectionRecovery:
    global _recovery_instance
    if _recovery_instance is None:
        _recovery_instance = ConnectionRecovery(
            token_manager=token_manager,
            client=client,
        )
    return _recovery_instance
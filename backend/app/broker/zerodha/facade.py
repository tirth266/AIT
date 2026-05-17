"""
Zerodha Broker Facade
=====================
Main entry point that ties all broker components together.
"""

import logging
import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List, Callable

from .client import (
    ZerodhaClient,
    get_zerodha_client,
    initialize_zerodha_client,
)
from .auth import TokenManager, get_token_manager
from .orders import OrderService, get_order_service
from .websocket import KiteWebSocket, get_kite_websocket, WebSocketState
from .reconciliation import OrderReconciler, get_order_reconciler
from .recovery import ConnectionRecovery, get_connection_recovery
from .audit import AuditLogger, get_audit_logger
from .testing import SandboxBroker, get_sandbox_broker, PaperTradingSync
from .models import (
    OrderParams,
    OrderPlacementResult,
    OrderModificationParams,
    OrderCancellationParams,
    ZerodhaOrder,
    ZerodhaPosition,
    ZerodhaPortfolio,
    ZerodhaTick,
    MarketSession,
)

logger = logging.getLogger('zerodha.facade')


class TradingMode(str, Enum):
    PAPER = "PAPER"
    LIVE = "LIVE"


class ZerodhaBroker:
    """
    Unified broker facade providing access to all broker operations.
    """

    def __init__(
        self,
        token_manager: Optional[TokenManager] = None,
        client: Optional[ZerodhaClient] = None,
        sandbox_broker: Optional[SandboxBroker] = None,
    ):
        self._token_manager = token_manager or get_token_manager()
        self._client = client or get_zerodha_client()
        self._order_service = get_order_service(self._client)
        self._websocket = get_kite_websocket(self._token_manager, self._client.token_manager.config.api_key)
        self._reconciler = get_order_reconciler(self._client)
        self._recovery = get_connection_recovery(self._token_manager, self._client)
        self._audit_logger = get_audit_logger()

        self._sandbox_broker = sandbox_broker
        self._trading_mode = TradingMode.PAPER

        self._initialized = False

    def initialize(
        self,
        enable_live: bool = False,
        sandbox_balance: float = 100000.0,
    ) -> None:
        if self._initialized:
            logger.warning("Broker already initialized")
            return

        if enable_live:
            self._trading_mode = TradingMode.LIVE

            if self._token_manager.access_token:
                self._recovery.set_websocket(self._websocket)
                self._websocket.connect()

                logger.info("Live trading enabled")
            else:
                logger.warning("No access token - falling back to paper trading")
                self._trading_mode = TradingMode.PAPER
                self._sandbox_broker = get_sandbox_broker(sandbox_balance)
        else:
            self._trading_mode = TradingMode.PAPER
            self._sandbox_broker = get_sandbox_broker(sandbox_balance)

        self._initialized = True
        logger.info(f"Broker initialized in {self._trading_mode.value} mode")

    async def place_order(
        self,
        params: OrderParams,
        source: str = "SYSTEM",
    ) -> OrderPlacementResult:
        if self._trading_mode == TradingMode.PAPER:
            return await self._place_paper_order(params)

        return await self._order_service.place_order(params, source=source)

    async def _place_paper_order(self, params: OrderParams) -> OrderPlacementResult:
        if not self._sandbox_broker:
            return OrderPlacementResult(
                success=False,
                error="Sandbox broker not initialized",
            )

        try:
            order = self._sandbox_broker.place_order(params)

            return OrderPlacementResult(
                success=True,
                order=order,
            )

        except Exception as e:
            return OrderPlacementResult(
                success=False,
                error=str(e),
            )

    async def modify_order(self, params: OrderModificationParams) -> ZerodhaOrder:
        if self._trading_mode == TradingMode.PAPER:
            raise NotImplementedError("Order modification not supported in paper mode")

        return await self._order_service.modify_order(params)

    async def cancel_order(self, params: OrderCancellationParams) -> ZerodhaOrder:
        if self._trading_mode == TradingMode.PAPER:
            raise NotImplementedError("Order cancellation not supported in paper mode")

        return await self._order_service.cancel_order(params)

    async def get_orders(self) -> List[ZerodhaOrder]:
        if self._trading_mode == TradingMode.PAPER:
            return self._sandbox_broker.get_orders() if self._sandbox_broker else []

        return await self._order_service.get_orders()

    async def get_positions(self) -> List[ZerodhaPosition]:
        if self._trading_mode == TradingMode.PAPER:
            return self._sandbox_broker.get_positions() if self._sandbox_broker else []

        return await self._order_service.get_positions()

    async def get_portfolio(self) -> List[ZerodhaPortfolio]:
        if self._trading_mode == TradingMode.PAPER:
            return []

        return await self._order_service.get_portfolio()

    async def get_margins(self) -> Dict[str, Any]:
        if self._trading_mode == TradingMode.PAPER:
            return {
                "equity": self._sandbox_broker.get_balance() if self._sandbox_broker else 0,
                "available": self._sandbox_broker.get_balance() if self._sandbox_broker else 0,
                "used": 0,
            }

        margins = await self._client.get_margins()
        return {
            "equity": margins.equity,
            "available": margins.available_cash,
            "used": margins.used_margin,
        }

    def subscribe_ticks(self, instrument_tokens: List[int]) -> bool:
        return self._websocket.subscribe(instrument_tokens)

    def unsubscribe_ticks(self, instrument_tokens: List[int]) -> bool:
        return self._websocket.unsubscribe(instrument_tokens)

    def add_tick_listener(self, instrument_token: int, callback: Callable[[ZerodhaTick], None]) -> None:
        self._websocket.add_tick_listener(instrument_token, callback)

    def set_ticks_callback(self, callback: Callable[[List[ZerodhaTick]], None]) -> None:
        self._websocket.set_ticks_callback(callback)

    def set_order_update_callback(self, callback: Callable[[Dict], None]) -> None:
        self._websocket.set_order_update_callback(callback)

    async def reconcile(self) -> Dict[str, Any]:
        if self._trading_mode == TradingMode.PAPER:
            return {"status": "N/A", "message": "Reconciliation not needed for paper trading"}

        orders = await self.get_orders()
        positions = await self.get_positions()

        self._reconciler.set_internal_orders({o.internal_order_id: o for o in orders})
        self._reconciler.set_internal_positions({p.symbol: p for p in positions})

        result = await self._reconciler.full_reconciliation()

        return {
            "status": result.status.value,
            "order_discrepancies": len(result.order_discrepancies),
            "position_discrepancies": len(result.position_discrepancies),
            "execution_time_ms": result.execution_time_ms,
        }

    async def recover_connection(self) -> bool:
        if self._trading_mode == TradingMode.PAPER:
            return True

        result = await self._recovery.perform_recovery()
        return result.success

    def get_market_session(self) -> MarketSession:
        return self._client.get_market_session()

    def get_status(self) -> Dict[str, Any]:
        return {
            "trading_mode": self._trading_mode.value,
            "initialized": self._initialized,
            "websocket_state": self._websocket.state.value if self._websocket else "N/A",
            "websocket_connected": self._websocket.is_connected if self._websocket else False,
            "circuit_breaker": self._client.get_circuit_breaker_stats() if self._client else {},
            "rate_limits": self._client.get_rate_limit_stats() if self._client else {},
            "recovery": self._recovery.get_stats() if self._recovery else {},
            "audit": self._audit_logger.get_stats() if self._audit_logger else {},
            "paper_balance": self._sandbox_broker.get_balance() if self._sandbox_broker else 0,
        }

    def disconnect(self) -> None:
        if self._websocket:
            self._websocket.disconnect()

        logger.info("Broker disconnected")

    @property
    def trading_mode(self) -> TradingMode:
        return self._trading_mode

    @property
    def is_live(self) -> bool:
        return self._trading_mode == TradingMode.LIVE

    @property
    def is_connected(self) -> bool:
        return self._websocket.is_connected if self._websocket else False


_broker_instance: Optional[ZerodhaBroker] = None


def get_zerodha_broker() -> ZerodhaBroker:
    global _broker_instance
    if _broker_instance is None:
        _broker_instance = ZerodhaBroker()
    return _broker_instance


def initialize_broker(
    enable_live: bool = False,
    access_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    sandbox_balance: float = 100000.0,
) -> ZerodhaBroker:
    global _broker_instance

    token_manager = get_token_manager()

    if access_token and refresh_token:
        token_manager._tokens = token_manager._tokens or type(token_manager._tokens)(
            access_token=access_token,
            refresh_token=refresh_token,
            api_key=token_manager.config.api_key,
            expires_at=datetime.now(timezone.utc),
        )
        token_manager._status = "VALID"

    from .client import initialize_zerodha_client
    client = initialize_zerodha_client(token_manager)

    broker = ZerodhaBroker(
        token_manager=token_manager,
        client=client,
    )

    broker.initialize(enable_live=enable_live, sandbox_balance=sandbox_balance)

    _broker_instance = broker

    return broker
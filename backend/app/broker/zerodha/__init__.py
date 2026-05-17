"""
Zerodha Kite Connect Broker Integration
=======================================
Production-grade live trading infrastructure for Zerodha Kite Connect API.
"""

from .client import ZerodhaClient, get_zerodha_client, initialize_zerodha_client
from .auth import TokenManager, get_token_manager
from .orders import OrderService, get_order_service
from .websocket import KiteWebSocket, get_kite_websocket
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
    OrderStatus,
    VALIDITY,
)
from .circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerOpenError
from .rate_limiter import RateLimiter, RateLimitType, RateLimitExceededError
from .recovery import ConnectionRecovery, RecoveryState, BrokerFailoverManager
from .reconciliation import OrderReconciler, ReconciliationResult, DiscrepancyType
from .audit import AuditLogger, AuditEvent
from .testing import SandboxBroker, get_sandbox_broker, BrokerTestSuite, PaperTradingSync
from .facade import ZerodhaBroker, get_zerodha_broker, initialize_broker, TradingMode

__all__ = [
    "ZerodhaClient",
    "get_zerodha_client",
    "initialize_zerodha_client",
    "TokenManager",
    "get_token_manager",
    "OrderService",
    "get_order_service",
    "KiteWebSocket",
    "get_kite_websocket",
    "ZerodhaOrder",
    "ZerodhaPosition",
    "ZerodhaPortfolio",
    "ZerodhaTick",
    "OrderParams",
    "Exchange",
    "ProductType",
    "OrderType",
    "TransactionType",
    "OrderStatus",
    "VALIDITY",
    "CircuitBreaker",
    "CircuitState",
    "CircuitBreakerOpenError",
    "RateLimiter",
    "RateLimitType",
    "RateLimitExceededError",
    "ConnectionRecovery",
    "RecoveryState",
    "BrokerFailoverManager",
    "OrderReconciler",
    "ReconciliationResult",
    "DiscrepancyType",
    "AuditLogger",
    "AuditEvent",
    "SandboxBroker",
    "get_sandbox_broker",
    "BrokerTestSuite",
    "PaperTradingSync",
    "ZerodhaBroker",
    "get_zerodha_broker",
    "initialize_broker",
    "TradingMode",
]
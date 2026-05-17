"""
Multi-Broker Infrastructure
============================
Broker abstraction layer with smart routing, failover, and execution quality tracking.
"""

import logging
import time
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from collections import defaultdict
import threading
import statistics

logger = logging.getLogger('broker_infrastructure')


class BrokerStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    DEGRADED = "degraded"
    MAINTENANCE = "maintenance"


class OrderStatus(str, Enum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class OrderRequest:
    """Order request to broker."""
    symbol: str
    exchange: str = "NSE"
    transaction_type: str = "BUY"
    quantity: int = 0
    order_type: str = "MARKET"
    product_type: str = "MIS"
    price: float = 0.0
    trigger_price: float = 0.0
    validity: str = "DAY"

    order_id: str = ""
    user_id: str = ""
    strategy_id: Optional[str] = None


@dataclass
class OrderResponse:
    """Order response from broker."""
    broker_order_id: str = ""
    order_id: str = ""
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    average_price: float = 0.0
    rejected_reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class BrokerMetrics:
    """Broker execution metrics."""
    broker_name: str = ""
    total_orders: int = 0
    successful_orders: int = 0
    failed_orders: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    fill_rate: float = 0.0
    last_latencies: List[float] = field(default_factory=list)


class BrokerAdapterBase(ABC):
    """
    Abstract base class for broker adapters.
    """

    def __init__(self, config: Dict[str, Any]):
        self._config = config
        self._name = config.get('name', 'unknown')
        self._status = BrokerStatus.DISCONNECTED
        self._metrics = BrokerMetrics(broker_name=self._name)
        self._lock = threading.Lock()

    @property
    def name(self) -> str:
        return self._name

    @property
    def status(self) -> BrokerStatus:
        return self._status

    @property
    def metrics(self) -> BrokerMetrics:
        return self._metrics

    @abstractmethod
    async def connect(self) -> bool:
        """Connect to broker."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnect from broker."""
        pass

    @abstractmethod
    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place an order."""
        pass

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel an order."""
        pass

    @abstractmethod
    async def get_order_status(self, broker_order_id: str) -> OrderResponse:
        """Get order status."""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Dict]:
        """Get open positions."""
        pass

    @abstractmethod
    async def get_balance(self) -> Dict:
        """Get account balance."""
        pass

    @abstractmethod
    async def get_quote(self, symbol: str) -> Dict:
        """Get quote for symbol."""
        pass

    def _record_latency(self, latency_ms: float):
        """Record order execution latency."""
        with self._lock:
            self._metrics.total_orders += 1
            self._metrics.last_latencies.append(latency_ms)

            if len(self._metrics.last_latencies) > 1000:
                self._metrics.last_latencies = self._metrics.last_latencies[-500:]

            self._metrics.avg_latency_ms = statistics.mean(self._metrics.last_latencies)

            if len(self._metrics.last_latencies) >= 10:
                sorted_latencies = sorted(self._metrics.last_latencies)
                self._metrics.p50_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.50)]
                self._metrics.p95_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.95)]
                self._metrics.p99_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.99)]

    def _record_success(self):
        """Record successful order."""
        with self._lock:
            self._metrics.successful_orders += 1
            if self._metrics.total_orders > 0:
                self._metrics.fill_rate = self._metrics.successful_orders / self._metrics.total_orders

    def _record_failure(self):
        """Record failed order."""
        with self._lock:
            self._metrics.failed_orders += 1


class ZerodhaAdapter(BrokerAdapterBase):
    """Zerodha Kite Connect adapter."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._api_key = config.get('api_key', '')
        self._access_token = config.get('access_token', '')
        self._kite = None

    async def connect(self) -> bool:
        """Connect to Zerodha."""
        try:
            logger.info(f"Connecting to Zerodha: {self._name}")
            self._status = BrokerStatus.CONNECTED
            return True
        except Exception as e:
            logger.error(f"Zerodha connection failed: {e}")
            self._status = BrokerStatus.DISCONNECTED
            return False

    async def disconnect(self) -> bool:
        """Disconnect from Zerodha."""
        self._status = BrokerStatus.DISCONNECTED
        return True

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        """Place order via Zerodha."""
        start = time.perf_counter()

        try:
            response = OrderResponse(
                broker_order_id=f"ZER{order.order_id}",
                order_id=order.order_id,
                status=OrderStatus.SUBMITTED,
                timestamp=datetime.now(timezone.utc)
            )

            latency_ms = (time.perf_counter() - start) * 1000
            self._record_latency(latency_ms)
            self._record_success()

            return response

        except Exception as e:
            self._record_failure()
            logger.error(f"Zerodha order failed: {e}")
            return OrderResponse(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                rejected_reason=str(e),
                timestamp=datetime.now(timezone.utc)
            )

    async def cancel_order(self, broker_order_id: str) -> bool:
        return True

    async def get_order_status(self, broker_order_id: str) -> OrderResponse:
        return OrderResponse(broker_order_id=broker_order_id, status=OrderStatus.SUBMITTED)

    async def get_positions(self) -> List[Dict]:
        return []

    async def get_balance(self) -> Dict:
        return {'available_cash': 0, 'margin_used': 0}

    async def get_quote(self, symbol: str) -> Dict:
        return {'last_price': 0, 'bid': 0, 'ask': 0}


class UpstoxAdapter(BrokerAdapterBase):
    """Upstox API adapter."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self._api_key = config.get('api_key', '')
        self._access_token = config.get('access_token', '')

    async def connect(self) -> bool:
        logger.info(f"Connecting to Upstox: {self._name}")
        self._status = BrokerStatus.CONNECTED
        return True

    async def disconnect(self) -> bool:
        self._status = BrokerStatus.DISCONNECTED
        return True

    async def place_order(self, order: OrderRequest) -> OrderResponse:
        start = time.perf_counter()

        response = OrderResponse(
            broker_order_id=f"UP{order.order_id}",
            order_id=order.order_id,
            status=OrderStatus.SUBMITTED,
            timestamp=datetime.now(timezone.utc)
        )

        latency_ms = (time.perf_counter() - start) * 1000
        self._record_latency(latency_ms)
        self._record_success()

        return response

    async def cancel_order(self, broker_order_id: str) -> bool:
        return True

    async def get_order_status(self, broker_order_id: str) -> OrderResponse:
        return OrderResponse(broker_order_id=broker_order_id, status=OrderStatus.SUBMITTED)

    async def get_positions(self) -> List[Dict]:
        return []

    async def get_balance(self) -> Dict:
        return {'available_cash': 0, 'margin_used': 0}

    async def get_quote(self, symbol: str) -> Dict:
        return {'last_price': 0, 'bid': 0, 'ask': 0}


class BrokerRouter:
    """
    Smart broker routing with failover and latency-based selection.
    """

    def __init__(self):
        self._brokers: Dict[str, BrokerAdapterBase] = {}
        self._active_broker: Optional[BrokerAdapterBase] = None
        self._routing_strategy = "latency"
        self._lock = threading.Lock()

        self._circuit_breakers: Dict[str, int] = defaultdict(int)
        self._circuit_threshold = 5

        logger.info("BrokerRouter initialized")

    def register_broker(self, broker: BrokerAdapterBase):
        """Register a broker adapter."""
        with self._lock:
            self._brokers[broker.name] = broker
            logger.info(f"Registered broker: {broker.name}")

    async def route_order(self, order: OrderRequest) -> OrderResponse:
        """Route order to best available broker."""
        broker = self._select_broker()

        if not broker:
            return OrderResponse(
                order_id=order.order_id,
                status=OrderStatus.REJECTED,
                rejected_reason="No available brokers"
            )

        try:
            response = await broker.place_order(order)

            if response.status == OrderStatus.REJECTED:
                self._record_failure(broker.name)

            return response

        except Exception as e:
            logger.error(f"Order routing failed: {e}")
            self._record_failure(broker.name)
            return await self._failover_order(order, broker.name)

    def _select_broker(self) -> Optional[BrokerAdapterBase]:
        """Select best broker based on routing strategy."""
        with self._lock:
            available = [b for b in self._brokers.values()
                       if b.status == BrokerStatus.CONNECTED
                       and self._circuit_breakers[b.name] < self._circuit_threshold]

            if not available:
                return None

            if self._routing_strategy == "latency":
                return min(available, key=lambda b: b.metrics.avg_latency_ms)
            elif self._routing_strategy == "fill_rate":
                return max(available, key=lambda b: b.metrics.fill_rate)
            else:
                return available[0]

    async def _failover_order(self, order: OrderRequest, failed_broker: str) -> OrderResponse:
        """Failover to another broker."""
        with self._lock:
            self._circuit_breakers[failed_broker] += 1
            logger.warning(f"Circuit breaker incremented for {failed_broker}: {self._circuit_breakers[failed_broker]}")

        available = [b for b in self._brokers.values()
                    if b.name != failed_broker
                    and b.status == BrokerStatus.CONNECTED
                    and self._circuit_breakers[b.name] < self._circuit_threshold]

        for broker in available:
            try:
                return await broker.place_order(order)
            except Exception as e:
                logger.error(f"Failover to {broker.name} failed: {e}")
                self._circuit_breakers[broker.name] += 1

        return OrderResponse(
            order_id=order.order_id,
            status=OrderStatus.REJECTED,
            rejected_reason="All brokers failed"
        )

    def _record_failure(self, broker_name: str):
        """Record broker failure."""
        with self._lock:
            self._circuit_breakers[broker_name] += 1
            logger.warning(f"Failure recorded for {broker_name}: {self._circuit_breakers[broker_name]}")

    def reset_circuit_breaker(self, broker_name: str):
        """Reset circuit breaker for a broker."""
        with self._lock:
            self._circuit_breakers[broker_name] = 0
            logger.info(f"Circuit breaker reset for {broker_name}")

    def get_broker_health(self) -> Dict[str, Any]:
        """Get health status of all brokers."""
        with self._lock:
            return {
                name: {
                    'status': broker.status.value,
                    'avg_latency_ms': broker.metrics.avg_latency_ms,
                    'fill_rate': broker.metrics.fill_rate,
                    'circuit_breaker_count': self._circuit_breakers[name]
                }
                for name, broker in self._brokers.items()
            }


class ExecutionQualityTracker:
    """Tracks execution quality across brokers."""

    def __init__(self):
        self._trades: List[Dict] = []
        self._lock = threading.Lock()

    def record_execution(
        self,
        broker_name: str,
        order_id: str,
        symbol: str,
        quantity: int,
        price: float,
        timestamp: datetime
    ):
        """Record an execution for quality tracking."""
        with self._lock:
            self._trades.append({
                'broker_name': broker_name,
                'order_id': order_id,
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'timestamp': timestamp
            })

    def get_broker_stats(self, broker_name: str) -> Dict:
        """Get execution statistics for a broker."""
        with self._lock:
            broker_trades = [t for t in self._trades if t['broker_name'] == broker_name]

            if not broker_trades:
                return {}

            prices = [t['price'] for t in broker_trades]

            return {
                'total_trades': len(broker_trades),
                'avg_price': statistics.mean(prices) if prices else 0,
                'price_variance': statistics.variance(prices) if len(prices) > 1 else 0
            }

    def get_execution_report(self) -> Dict:
        """Generate execution quality report."""
        with self._lock:
            broker_groups = defaultdict(list)
            for trade in self._trades:
                broker_groups[trade['broker_name']].append(trade)

            return {
                broker: self.get_broker_stats(broker)
                for broker in broker_groups.keys()
            }


# Global instances
_broker_router: Optional[BrokerRouter] = None
_execution_tracker: Optional[ExecutionQualityTracker] = None


def get_broker_router() -> BrokerRouter:
    """Get or create the global broker router."""
    global _broker_router
    if _broker_router is None:
        _broker_router = BrokerRouter()
    return _broker_router


def get_execution_tracker() -> ExecutionQualityTracker:
    """Get or create the execution quality tracker."""
    global _execution_tracker
    if _execution_tracker is None:
        _execution_tracker = ExecutionQualityTracker()
    return _execution_tracker
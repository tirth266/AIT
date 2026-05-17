"""
Prometheus Metrics Export
=========================
Production-grade Prometheus metrics for trading platform.
"""

import logging
import time
import os
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from functools import wraps
import threading

logger = logging.getLogger('prometheus_metrics')

try:
    from prometheus_client import Counter, Histogram, Gauge, Summary, Info, CollectorRegistry
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.warning("prometheus_client not installed")


@dataclass
class MetricLabels:
    """Standard labels for trading metrics."""
    service: str = "trading-platform"
    environment: str = "production"


class TradingMetrics:
    """
    Trading platform metrics.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._setup_metrics()

    def _setup_metrics(self):
        """Setup all Prometheus metrics."""
        if not PROMETHEUS_AVAILABLE:
            return

        prefix = "trading_"

        # Order metrics
        self.orders_placed = Counter(
            f'{prefix}orders_placed_total',
            'Total orders placed',
            ['mode', 'order_type', 'status']
        )

        self.orders_latency = Histogram(
            f'{prefix}orders_latency_seconds',
            'Order placement latency',
            ['mode', 'operation'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )

        # Trade metrics
        self.trades_executed = Counter(
            f'{prefix}trades_executed_total',
            'Total trades executed',
            ['mode', 'transaction_type', 'symbol']
        )

        self.trade_value = Histogram(
            f'{prefix}trade_value',
            'Trade value in INR',
            ['mode'],
            buckets=[1000, 5000, 10000, 50000, 100000, 500000, 1000000, 5000000]
        )

        # Position metrics
        self.positions_open = Gauge(
            f'{prefix}positions_open',
            'Number of open positions',
            ['mode', 'user_id']
        )

        self.position_pnl = Gauge(
            f'{prefix}position_pnl',
            'Position P&L in INR',
            ['position_id', 'mode']
        )

        # P&L metrics
        self.daily_pnl = Gauge(
            f'{prefix}daily_pnl',
            'Daily P&L in INR',
            ['mode', 'user_id']
        )

        # Signal metrics
        self.signals_generated = Counter(
            f'{prefix}signals_generated_total',
            'Total signals generated',
            ['strategy_id', 'signal_type', 'source']
        )

        self.signal_execution_rate = Gauge(
            f'{prefix}signal_execution_rate',
            'Signal execution rate',
            ['strategy_id']
        )

        # Tick processing metrics
        self.ticks_processed = Counter(
            f'{prefix}ticks_processed_total',
            'Total ticks processed',
            ['symbol']
        )

        self.tick_processing_latency = Histogram(
            f'{prefix}tick_processing_latency_ms',
            'Tick processing latency in milliseconds',
            ['symbol'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 25.0, 50.0]
        )

        # WebSocket metrics
        self.ws_connections = Gauge(
            f'{prefix}ws_connections',
            'Active WebSocket connections'
        )

        self.ws_messages_sent = Counter(
            f'{prefix}ws_messages_sent_total',
            'Total WebSocket messages sent',
            ['event_type']
        )

        self.ws_latency = Histogram(
            f'{prefix}ws_latency_ms',
            'WebSocket message latency',
            ['event_type'],
            buckets=[1, 5, 10, 25, 50, 100, 250, 500]
        )

        # Risk metrics
        self.risk_checks = Counter(
            f'{prefix}risk_checks_total',
            'Total risk checks performed',
            ['check_type', 'result']
        )

        self.margin_utilization = Gauge(
            f'{prefix}margin_utilization_percent',
            'Margin utilization percentage',
            ['user_id']
        )

        # System metrics
        self.request_duration = Histogram(
            f'{prefix}request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint', 'status'],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
        )

        self.active_users = Gauge(
            f'{prefix}active_users',
            'Number of active users'
        )

        # Kafka metrics
        self.kafka_produced = Counter(
            f'{prefix}kafka_produced_total',
            'Messages produced to Kafka',
            ['topic']
        )

        self.kafka_consumed = Counter(
            f'{prefix}kafka_consumed_total',
            'Messages consumed from Kafka',
            ['topic', 'group']
        )

        self.kafka_consumer_lag = Gauge(
            f'{prefix}kafka_consumer_lag',
            'Kafka consumer lag',
            ['topic', 'group', 'partition']
        )

        # Database metrics
        self.db_query_duration = Histogram(
            f'{prefix}db_query_duration_seconds',
            'Database query duration',
            ['operation', 'collection'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
        )

        self.redis_operations = Counter(
            f'{prefix}redis_operations_total',
            'Redis operations',
            ['operation', 'status']
        )

        # Error metrics
        self.errors = Counter(
            f'{prefix}errors_total',
            'Total errors',
            ['error_type', 'component']
        )

        self.order_rejections = Counter(
            f'{prefix}order_rejections_total',
            'Order rejections',
            ['reason']
        )

    def record_order(self, mode: str, order_type: str, status: str):
        """Record order placement."""
        if PROMETHEUS_AVAILABLE:
            self.orders_placed.labels(mode=mode, order_type=order_type, status=status).inc()

    def record_order_latency(self, mode: str, operation: str, latency_seconds: float):
        """Record order operation latency."""
        if PROMETHEUS_AVAILABLE:
            self.orders_latency.labels(mode=mode, operation=operation).observe(latency_seconds)

    def record_trade(self, mode: str, transaction_type: str, symbol: str, value: float):
        """Record trade execution."""
        if PROMETHEUS_AVAILABLE:
            self.trades_executed.labels(
                mode=mode,
                transaction_type=transaction_type,
                symbol=symbol
            ).inc()
            self.trade_value.labels(mode=mode).observe(value)

    def update_position(self, position_id: str, mode: str, pnl: float):
        """Update position P&L."""
        if PROMETHEUS_AVAILABLE:
            self.position_pnl.labels(position_id=position_id, mode=mode).set(pnl)

    def set_open_positions(self, mode: str, user_id: str, count: int):
        """Set open position count."""
        if PROMETHEUS_AVAILABLE:
            self.positions_open.labels(mode=mode, user_id=user_id).set(count)

    def set_daily_pnl(self, mode: str, user_id: str, pnl: float):
        """Set daily P&L."""
        if PROMETHEUS_AVAILABLE:
            self.daily_pnl.labels(mode=mode, user_id=user_id).set(pnl)

    def record_signal(self, strategy_id: str, signal_type: str, source: str):
        """Record generated signal."""
        if PROMETHEUS_AVAILABLE:
            self.signals_generated.labels(
                strategy_id=strategy_id,
                signal_type=signal_type,
                source=source
            ).inc()

    def set_signal_execution_rate(self, strategy_id: str, rate: float):
        """Set signal execution rate."""
        if PROMETHEUS_AVAILABLE:
            self.signal_execution_rate.labels(strategy_id=strategy_id).set(rate)

    def record_tick(self, symbol: str, latency_ms: float):
        """Record tick processing."""
        if PROMETHEUS_AVAILABLE:
            self.ticks_processed.labels(symbol=symbol).inc()
            self.tick_processing_latency.labels(symbol=symbol).observe(latency_ms)

    def set_ws_connections(self, count: int):
        """Set active WebSocket connections."""
        if PROMETHEUS_AVAILABLE:
            self.ws_connections.set(count)

    def record_ws_message(self, event_type: str, latency_ms: float):
        """Record WebSocket message."""
        if PROMETHEUS_AVAILABLE:
            self.ws_messages_sent.labels(event_type=event_type).inc()
            self.ws_latency.labels(event_type=event_type).observe(latency_ms)

    def record_risk_check(self, check_type: str, result: str):
        """Record risk check."""
        if PROMETHEUS_AVAILABLE:
            self.risk_checks.labels(check_type=check_type, result=result).inc()

    def set_margin_utilization(self, user_id: str, utilization: float):
        """Set margin utilization."""
        if PROMETHEUS_AVAILABLE:
            self.margin_utilization.labels(user_id=user_id).set(utilization)

    def record_request(self, method: str, endpoint: str, status: int, duration: float):
        """Record HTTP request."""
        if PROMETHEUS_AVAILABLE:
            self.request_duration.labels(
                method=method,
                endpoint=endpoint,
                status=str(status)
            ).observe(duration)

    def set_active_users(self, count: int):
        """Set active user count."""
        if PROMETHEUS_AVAILABLE:
            self.active_users.set(count)

    def record_kafka_produced(self, topic: str):
        """Record Kafka message produced."""
        if PROMETHEUS_AVAILABLE:
            self.kafka_produced.labels(topic=topic).inc()

    def record_kafka_consumed(self, topic: str, group: str):
        """Record Kafka message consumed."""
        if PROMETHEUS_AVAILABLE:
            self.kafka_consumed.labels(topic=topic, group=group).inc()

    def set_kafka_lag(self, topic: str, group: str, partition: int, lag: int):
        """Set Kafka consumer lag."""
        if PROMETHEUS_AVAILABLE:
            self.kafka_consumer_lag.labels(
                topic=topic,
                group=group,
                partition=partition
            ).set(lag)

    def record_db_query(self, operation: str, collection: str, duration: float):
        """Record database query."""
        if PROMETHEUS_AVAILABLE:
            self.db_query_duration.labels(
                operation=operation,
                collection=collection
            ).observe(duration)

    def record_redis_operation(self, operation: str, status: str):
        """Record Redis operation."""
        if PROMETHEUS_AVAILABLE:
            self.redis_operations.labels(operation=operation, status=status).inc()

    def record_error(self, error_type: str, component: str):
        """Record error."""
        if PROMETHEUS_AVAILABLE:
            self.errors.labels(error_type=error_type, component=component).inc()

    def record_order_rejection(self, reason: str):
        """Record order rejection."""
        if PROMETHEUS_AVAILABLE:
            self.order_rejections.labels(reason=reason).inc()


def timed(metric_name: str, **labels):
    """Decorator to time function execution."""
    def decorator(func):
        if not PROMETHEUS_AVAILABLE:
            return func

        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                metrics = TradingMetrics()
                if hasattr(metrics, metric_name):
                    getattr(metrics, metric_name).labels(**labels).observe(duration)

        return wrapper
    return decorator


def get_metrics() -> Dict[str, Any]:
    """Get current metrics."""
    metrics = TradingMetrics()
    return {
        'orders_placed': metrics.orders_placed._value._value,
        'trades_executed': metrics.trades_executed._value._value,
    }


_trading_metrics = TradingMetrics()


def get_trading_metrics() -> TradingMetrics:
    """Get global trading metrics instance."""
    return _trading_metrics


def generate_prometheus_output() -> bytes:
    """Generate Prometheus metrics output."""
    if PROMETHEUS_AVAILABLE:
        return generate_latest()
    return b''


def get_prometheus_content_type() -> str:
    """Get Prometheus content type."""
    return CONTENT_TYPE_LATEST if PROMETHEUS_AVAILABLE else 'text/plain'
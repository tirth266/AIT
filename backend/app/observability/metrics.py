"""
Metrics Collection Module
=========================
Prometheus metrics for trading platform with custom metrics for:
- HTTP API requests
- WebSocket connections and messages
- Order execution
- Strategy execution
- Database operations
- System resources
"""

import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from flask import Flask, g, request
from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client import REGISTRY
import logging

logger = logging.getLogger('trading_app.metrics')

DEFAULT_BUCKETS = (
    0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0
)

LATENCY_BUCKETS = (
    0.001, 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0
)

TRADING_LATENCY_BUCKETS = (
    0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 10.0, 30.0
)


class MetricsCollector:
    """Central metrics collector for all trading platform metrics."""

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or REGISTRY
        self._setup_http_metrics()
        self._setup_websocket_metrics()
        self._setup_trading_metrics()
        self._setup_database_metrics()
        self._setup_system_metrics()
        self._setup_business_metrics()

    def _setup_http_metrics(self):
        """HTTP API metrics."""
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status', 'service'],
            registry=self.registry
        )

        self.http_request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency in seconds',
            ['method', 'endpoint', 'service'],
            buckets=LATENCY_BUCKETS,
            registry=self.registry
        )

        self.http_request_size = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000),
            registry=self.registry
        )

        self.http_response_size = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            buckets=(100, 500, 1000, 5000, 10000, 50000, 100000, 500000),
            registry=self.registry
        )

        self.http_requests_in_progress = Gauge(
            'http_requests_in_progress',
            'HTTP requests currently being processed',
            ['method', 'endpoint', 'service'],
            registry=self.registry
        )

        self.rate_limit_hits = Counter(
            'http_rate_limit_hits_total',
            'Total rate limit hits',
            ['endpoint', 'service'],
            registry=self.registry
        )

    def _setup_websocket_metrics(self):
        """WebSocket metrics."""
        self.websocket_connections_active = Gauge(
            'websocket_active_connections',
            'Number of active WebSocket connections',
            ['service'],
            registry=self.registry
        )

        self.websocket_connections_total = Counter(
            'websocket_connections_total',
            'Total WebSocket connections',
            ['event', 'service'],
            registry=self.registry
        )

        self.websocket_messages_total = Counter(
            'websocket_messages_total',
            'Total WebSocket messages',
            ['direction', 'message_type', 'service'],
            registry=self.registry
        )

        self.websocket_message_duration = Histogram(
            'websocket_message_latency_seconds',
            'WebSocket message processing latency',
            ['message_type', 'service'],
            buckets=LATENCY_BUCKETS,
            registry=self.registry
        )

        self.websocket_messages_in_progress = Gauge(
            'websocket_messages_in_progress',
            'WebSocket messages currently being processed',
            ['service'],
            registry=self.registry
        )

    def _setup_trading_metrics(self):
        """Trading-specific metrics."""
        self.orders_total = Counter(
            'trading_orders_total',
            'Total orders placed',
            ['type', 'status', 'side', 'symbol'],
            registry=self.registry
        )

        self.order_latency = Histogram(
            'trading_order_latency_seconds',
            'Order execution latency in seconds',
            ['type', 'symbol'],
            buckets=TRADING_LATENCY_BUCKETS,
            registry=self.registry
        )

        self.orders_in_progress = Gauge(
            'trading_orders_in_progress',
            'Orders currently being processed',
            registry=self.registry
        )

        self.strategy_executions_total = Counter(
            'trading_strategy_executions_total',
            'Total strategy executions',
            ['strategy', 'status'],
            registry=self.registry
        )

        self.strategy_execution_time = Histogram(
            'trading_strategy_execution_time_seconds',
            'Strategy execution time in seconds',
            ['strategy'],
            buckets=TRADING_LATENCY_BUCKETS,
            registry=self.registry
        )

        self.strategy_executions_in_progress = Gauge(
            'trading_strategy_executions_in_progress',
            'Strategies currently being executed',
            registry=self.registry
        )

        self.ticks_processed_total = Counter(
            'trading_ticks_processed_total',
            'Total ticks processed',
            ['symbol', 'source'],
            registry=self.registry
        )

        self.tick_processing_time = Histogram(
            'trading_tick_processing_time_seconds',
            'Tick processing time in seconds',
            ['symbol'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )

        self.market_data_latency = Histogram(
            'trading_market_data_latency_seconds',
            'Market data latency (time from tick to processing)',
            ['symbol'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry
        )

    def _setup_database_metrics(self):
        """Database operation metrics."""
        self.mongodb_operations = Counter(
            'mongodb_operations_total',
            'MongoDB operations',
            ['operation', 'collection', 'status'],
            registry=self.registry
        )

        self.mongodb_query_duration = Histogram(
            'mongodb_query_duration_seconds',
            'MongoDB query duration in seconds',
            ['operation', 'collection'],
            buckets=LATENCY_BUCKETS,
            registry=self.registry
        )

        self.mongodb_connections = Gauge(
            'mongodb_connections_active',
            'Active MongoDB connections',
            registry=self.registry
        )

        self.redis_operations = Counter(
            'redis_operations_total',
            'Redis operations',
            ['operation', 'key_type', 'status'],
            registry=self.registry
        )

        self.redis_operation_duration = Histogram(
            'redis_operation_duration_seconds',
            'Redis operation duration in seconds',
            ['operation'],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5),
            registry=self.registry
        )

        self.redis_memory = Gauge(
            'redis_memory_bytes',
            'Redis memory usage in bytes',
            registry=self.registry
        )

        self.redis_keys = Gauge(
            'redis_keys_total',
            'Total Redis keys by database',
            ['db'],
            registry=self.registry
        )

    def _setup_system_metrics(self):
        """System resource metrics."""
        self.process_cpu_seconds = Counter(
            'process_cpu_seconds_total',
            'Process CPU time in seconds',
            registry=self.registry
        )

        self.process_memory_bytes = Gauge(
            'process_memory_bytes',
            'Process memory usage in bytes',
            registry=self.registry
        )

        self.process_threads = Gauge(
            'process_threads',
            'Number of process threads',
            registry=self.registry
        )

        self.process_open_files = Gauge(
            'process_open_files',
            'Number of open file descriptors',
            registry=self.registry
        )

    def _setup_business_metrics(self):
        """Business-level metrics."""
        self.active_users = Gauge(
            'active_users',
            'Number of active users',
            ['service'],
            registry=self.registry
        )

        self.trading_volume = Counter(
            'trading_volume_usd_total',
            'Total trading volume in USD',
            ['symbol', 'side'],
            registry=self.registry
        )

        self.positions_active = Gauge(
            'trading_positions_active',
            'Number of active positions',
            registry=self.registry
        )

    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        request_size: int,
        response_size: int,
        service: str = 'trading-backend'
    ):
        """Record an HTTP request."""
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status),
            service=service
        ).inc()

        self.http_request_duration.labels(
            method=method,
            endpoint=endpoint,
            service=service
        ).observe(duration)

        if request_size > 0:
            self.http_request_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)

        if response_size > 0:
            self.http_response_size.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)

    def record_websocket_connection(self, event: str, service: str = 'trading-websocket'):
        """Record a WebSocket connection event."""
        self.websocket_connections_total.labels(
            event=event,
            service=service
        ).inc()

    def set_websocket_connections(self, count: int, service: str = 'trading-websocket'):
        """Set the number of active WebSocket connections."""
        self.websocket_connections_active.labels(service=service).set(count)

    def record_websocket_message(
        self,
        direction: str,
        message_type: str,
        duration: float,
        service: str = 'trading-websocket'
    ):
        """Record a WebSocket message."""
        self.websocket_messages_total.labels(
            direction=direction,
            message_type=message_type,
            service=service
        ).inc()

        self.websocket_message_duration.labels(
            message_type=message_type,
            service=service
        ).observe(duration)

    def record_order(
        self,
        order_type: str,
        status: str,
        side: str,
        symbol: str,
        latency: float
    ):
        """Record an order execution."""
        self.orders_total.labels(
            type=order_type,
            status=status,
            side=side,
            symbol=symbol
        ).inc()

        if latency > 0:
            self.order_latency.labels(
                type=order_type,
                symbol=symbol
            ).observe(latency)

    def record_strategy_execution(
        self,
        strategy: str,
        status: str,
        execution_time: float
    ):
        """Record a strategy execution."""
        self.strategy_executions_total.labels(
            strategy=strategy,
            status=status
        ).inc()

        if execution_time > 0:
            self.strategy_execution_time.labels(strategy=strategy).observe(execution_time)

    def record_tick_processing(
        self,
        symbol: str,
        source: str,
        processing_time: float
    ):
        """Record tick processing."""
        self.ticks_processed_total.labels(
            symbol=symbol,
            source=source
        ).inc()

        if processing_time > 0:
            self.tick_processing_time.labels(symbol=symbol).observe(processing_time)

    def record_mongodb_operation(
        self,
        operation: str,
        collection: str,
        status: str,
        duration: float
    ):
        """Record a MongoDB operation."""
        self.mongodb_operations.labels(
            operation=operation,
            collection=collection,
            status=status
        ).inc()

        if duration > 0:
            self.mongodb_query_duration.labels(
                operation=operation,
                collection=collection
            ).observe(duration)

    def record_redis_operation(
        self,
        operation: str,
        key_type: str,
        status: str,
        duration: float
    ):
        """Record a Redis operation."""
        self.redis_operations.labels(
            operation=operation,
            key_type=key_type,
            status=status
        ).inc()

        if duration > 0:
            self.redis_operation_duration.labels(operation=operation).observe(duration)


metrics_collector = MetricsCollector()


def setup_metrics(app: Flask) -> None:
    """Initialize metrics collection with Flask app."""
    app.config.setdefault('METRICS_ENABLED', True)

    @app.route('/metrics')
    def metrics_endpoint():
        """Prometheus metrics endpoint."""
        if not app.config.get('METRICS_ENABLED', True):
            return 'Service Unavailable', 503
        return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    @app.route('/metrics/detailed')
    def detailed_metrics():
        """Detailed metrics endpoint with additional labels."""
        return generate_latest(REGISTRY), 200, {'Content-Type': CONTENT_TYPE_LATEST}

    logger.info("Metrics endpoint registered at /metrics")


def track_request(f: Callable) -> Callable:
    """Decorator to track HTTP request metrics."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()

        method = request.method
        path = request.path
        content_length = request.content_length or 0

        g.request_start_time = start_time
        g.request_method = method
        g.request_path = path

        try:
            response = f(*args, **kwargs)

            duration = time.perf_counter() - start_time
            status = 200
            response_size = 0

            if hasattr(response, 'content_length'):
                response_size = response.content_length or 0
            elif isinstance(response, tuple) and len(response) > 1:
                response_size = response[1] if isinstance(response[1], int) else 0

            metrics_collector.record_http_request(
                method=method,
                endpoint=path,
                status=status,
                duration=duration,
                request_size=content_length,
                response_size=response_size
            )

            return response
        except Exception as e:
            duration = time.perf_counter() - start_time
            status = 500

            metrics_collector.record_http_request(
                method=method,
                endpoint=path,
                status=status,
                duration=duration,
                request_size=content_length,
                response_size=0
            )

            raise

    return wrapper


def track_websocket_message(message_type: str):
    """Decorator to track WebSocket message processing time."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            try:
                result = f(*args, **kwargs)
                duration = time.perf_counter() - start_time

                metrics_collector.record_websocket_message(
                    direction='inbound',
                    message_type=message_type,
                    duration=duration
                )

                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                metrics_collector.record_websocket_message(
                    direction='inbound',
                    message_type=message_type,
                    duration=duration
                )
                raise

        return wrapper
    return decorator


def track_order_execution(order_type: str, symbol: str):
    """Decorator to track order execution time."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            metrics_collector.orders_in_progress.inc()

            try:
                result = f(*args, **kwargs)
                duration = time.perf_counter() - start_time

                metrics_collector.record_order(
                    order_type=order_type,
                    status='success',
                    side=args[0].get('side', 'buy') if args and isinstance(args[0], dict) else 'buy',
                    symbol=symbol,
                    latency=duration
                )

                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                metrics_collector.record_order(
                    order_type=order_type,
                    status='failed',
                    side='buy',
                    symbol=symbol,
                    latency=duration
                )
                raise
            finally:
                metrics_collector.orders_in_progress.dec()

        return wrapper
    return decorator


def track_strategy_execution(strategy: str):
    """Decorator to track strategy execution time."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            metrics_collector.strategy_executions_in_progress.inc()

            try:
                result = f(*args, **kwargs)
                duration = time.perf_counter() - start_time

                metrics_collector.record_strategy_execution(
                    strategy=strategy,
                    status='success',
                    execution_time=duration
                )

                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                metrics_collector.record_strategy_execution(
                    strategy=strategy,
                    status='failed',
                    execution_time=duration
                )
                raise
            finally:
                metrics_collector.strategy_executions_in_progress.dec()

        return wrapper
    return decorator


def track_tick_processing(symbol: str, source: str = 'websocket'):
    """Decorator to track tick processing time."""
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            try:
                result = f(*args, **kwargs)
                duration = time.perf_counter() - start_time

                metrics_collector.record_tick_processing(
                    symbol=symbol,
                    source=source,
                    processing_time=duration
                )

                return result
            except Exception as e:
                duration = time.perf_counter() - start_time
                metrics_collector.record_tick_processing(
                    symbol=symbol,
                    source=source,
                    processing_time=duration
                )
                raise

        return wrapper
    return decorator


def increment_counter(name: str, **labels):
    """Increment a counter metric."""
    counter = getattr(metrics_collector, name, None)
    if counter:
        counter.labels(**labels).inc()


def gauge_value(name: str, value: float, **labels):
    """Set a gauge metric value."""
    gauge = getattr(metrics_collector, name, None)
    if gauge:
        gauge.labels(**labels).set(value)


def histogram_time(name: str, duration: float, **labels):
    """Observe a duration in a histogram."""
    histogram = getattr(metrics_collector, name, None)
    if histogram:
        histogram.labels(**labels).observe(duration)


class PrometheusExporter:
    """Prometheus metrics exporter for Flask."""

    def __init__(self, app: Flask = None):
        if app:
            self.init_app(app)

    def init_app(self, app: Flask):
        """Initialize with Flask app."""
        setup_metrics(app)
        logger.info("Prometheus exporter initialized")


from flask import Flask


class MetricsMiddleware:
    """WSGI middleware for metrics collection."""

    def __init__(self, app: Flask):
        self.app = app

    def __call__(self, environ, start_response):
        start_time = time.perf_counter()

        def metrics_start_response(status, headers, exc_info=None):
            duration = time.perf_counter() - start_time
            method = environ.get('REQUEST_METHOD', 'GET')
            path = environ.get('PATH_INFO', '/')
            status_code = int(status.split()[0])

            metrics_collector.record_http_request(
                method=method,
                endpoint=path,
                status=status_code,
                duration=duration,
                request_size=int(environ.get('CONTENT_LENGTH', 0)),
                response_size=0
            )

            return start_response(status, headers, exc_info)

        return self.app(environ, metrics_start_response)
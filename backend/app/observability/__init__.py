"""
Observability Module
====================
Complete observability implementation for trading platform:
- Prometheus metrics collection
- Structured logging with correlation IDs
- Distributed tracing
- Health checks
- Alerting hooks
"""

from app.observability.metrics import (
    MetricsCollector,
    metrics_collector,
    setup_metrics,
    track_request,
    track_websocket_message,
    track_order_execution,
    track_strategy_execution,
    track_tick_processing,
    increment_counter,
    gauge_value,
    histogram_time,
)
from app.observability.logging import (
    StructuredLogger,
    setup_structured_logging,
    get_logger,
    bind_context,
    clear_context,
)
from app.observability.tracing import (
    TracingContext,
    setup_tracing,
    trace_operation,
    get_trace_id,
    span,
)
from app.observability.health import (
    HealthCheck,
    health_check_registry,
    register_health_check,
    get_health_status,
    setup_health_checks,
)
from app.observability.export import (
    PrometheusExporter,
    metrics_endpoint,
)

__all__ = [
    "MetricsCollector",
    "metrics_collector",
    "setup_metrics",
    "track_request",
    "track_websocket_message",
    "track_order_execution",
    "track_strategy_execution",
    "track_tick_processing",
    "increment_counter",
    "gauge_value",
    "histogram_time",
    "StructuredLogger",
    "setup_structured_logging",
    "get_logger",
    "bind_context",
    "clear_context",
    "TracingContext",
    "setup_tracing",
    "trace_operation",
    "get_trace_id",
    "span",
    "HealthCheck",
    "health_check_registry",
    "register_health_check",
    "get_health_status",
    "setup_health_checks",
    "PrometheusExporter",
    "metrics_endpoint",
]
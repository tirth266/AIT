"""
Distributed Tracing Module
==========================
Distributed tracing implementation using OpenTelemetry:
- Trace context propagation
- Span creation and management
- Sampling configuration
- Integration with Tempo
"""

import os
import time
import uuid
import logging
from typing import Optional, Dict, Any, Callable, List
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
import threading

logger = logging.getLogger('trading_app.tracing')

trace_id_context: ContextVar[Optional[str]] = ContextVar('trace_id', default=None)
span_stack_context: ContextVar[List['Span']] = ContextVar('span_stack', default=[])


class SpanKind(Enum):
    """Span kind enumeration."""
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"


class SpanStatus(Enum):
    """Span status enumeration."""
    OK = "ok"
    ERROR = "error"
    UNSET = "unset"


@dataclass
class Span:
    """Represents a trace span."""
    name: str
    trace_id: str
    span_id: str
    parent_id: Optional[str] = None
    kind: SpanKind = SpanKind.INTERNAL
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    status: SpanStatus = SpanStatus.UNSET
    status_message: Optional[str] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.end_time is None:
            self.end_time = time.time()
        if exc_type is not None:
            self.status = SpanStatus.ERROR
            self.status_message = str(exc_val)
            self.record_exception(exc_val, exc_tb)
        return False

    def set_attribute(self, key: str, value: Any) -> None:
        """Set a span attribute."""
        self.attributes[key] = value

    def set_attributes(self, attributes: Dict[str, Any]) -> None:
        """Set multiple span attributes."""
        self.attributes.update(attributes)

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """Add an event to the span."""
        event = {
            'name': name,
            'timestamp': datetime.utcnow().isoformat(),
            'attributes': attributes or {}
        }
        self.events.append(event)

    def record_exception(self, exception: Exception, tb: Any = None) -> None:
        """Record an exception in the span."""
        self.add_event(
            'exception',
            {
                'exception.type': type(exception).__name__,
                'exception.message': str(exception),
                'exception.stacktrace': traceback.format_exc() if tb else None
            }
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert span to dictionary."""
        return {
            'name': self.name,
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_id': self.parent_id,
            'kind': self.kind.value,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.end_time - self.start_time if self.end_time else None,
            'status': self.status.value,
            'status_message': self.status_message,
            'attributes': self.attributes,
            'events': self.events
        }


class TracingContext:
    """Manages trace context and span creation."""

    def __init__(
        self,
        service_name: str = 'trading-backend',
        sample_rate: float = 0.1,
        exporter_endpoint: Optional[str] = None
    ):
        self.service_name = service_name
        self.sample_rate = sample_rate
        self.exporter_endpoint = exporter_endpoint
        self._spans: List[Span] = []
        self._lock = threading.Lock()

    def generate_trace_id(self) -> str:
        """Generate a new trace ID."""
        return f"trace-{uuid.uuid4().hex[:16]}"

    def generate_span_id(self) -> str:
        """Generate a new span ID."""
        return f"span-{uuid.uuid4().hex[:8]}"

    def should_sample(self) -> bool:
        """Determine if trace should be sampled."""
        import random
        return random.random() < self.sample_rate

    @contextmanager
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None
    ):
        """Start a new span context."""
        trace_id = trace_id_context.get()
        if not trace_id:
            trace_id = self.generate_trace_id()
            trace_id_context.set(trace_id)

        span_id = self.generate_span_id()

        span_stack = span_stack_context.get()
        if span_stack:
            parent_span = span_stack[-1]
            parent_id = parent_span.span_id

        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            kind=kind,
            attributes=attributes or {}
        )

        span_stack.append(span)
        span_stack_context.set(span_stack)

        try:
            yield span
        finally:
            span.end_time = time.time()
            span_stack.pop()
            span_stack_context.set(span_stack)

            with self._lock:
                self._spans.append(span)

            self._export_span(span)

    def get_current_trace_id(self) -> Optional[str]:
        """Get current trace ID."""
        return trace_id_context.get()

    def get_current_span(self) -> Optional[Span]:
        """Get current span."""
        span_stack = span_stack_context.get()
        return span_stack[-1] if span_stack else None

    def _export_span(self, span: Span) -> None:
        """Export span to configured backend."""
        if not self.exporter_endpoint:
            return

        try:
            import requests
            payload = span.to_dict()
            payload['service_name'] = self.service_name

            requests.post(
                f"{self.exporter_endpoint}/api/traces",
                json=payload,
                timeout=1.0
            )
        except Exception as e:
            logger.debug(f"Failed to export span: {e}")

    def get_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent traces."""
        with self._lock:
            return [span.to_dict() for span in self._spans[-limit:]]

    def clear_traces(self) -> None:
        """Clear stored traces."""
        with self._lock:
            self._spans.clear()


tracing_context = TracingContext(
    service_name=os.environ.get('OTEL_SERVICE_NAME', 'trading-backend'),
    sample_rate=float(os.environ.get('OTEL_SAMPLE_RATE', '0.1')),
    exporter_endpoint=os.environ.get('OTEL_EXPORTER_ENDPOINT', None)
)


def setup_tracing(app, service_name: Optional[str] = None) -> TracingContext:
    """Setup tracing for Flask app."""
    global tracing_context

    service_name = service_name or app.config.get('SERVICE_NAME', 'trading-backend')

    tracing_context = TracingContext(
        service_name=service_name,
        sample_rate=float(os.environ.get('OTEL_SAMPLE_RATE', '0.1')),
        exporter_endpoint=os.environ.get('OTEL_EXPORTER_ENDPOINT')
    )

    @app.before_request
    def inject_trace_context():
        incoming_trace = request.headers.get('X-Trace-ID')
        if incoming_trace:
            trace_id_context.set(incoming_trace)
        elif tracing_context.should_sample():
            trace_id_context.set(tracing_context.generate_trace_id())

    @app.after_request
    def propagate_trace_context(response):
        trace_id = trace_id_context.get()
        if trace_id:
            response.headers['X-Trace-ID'] = trace_id
        return response

    @app.route('/debug/traces')
    def debug_traces():
        """Debug endpoint to view recent traces."""
        return {
            'traces': tracing_context.get_traces(),
            'current_trace_id': tracing_context.get_current_trace_id()
        }

    logger.info(f"Distributed tracing initialized for {service_name}")
    return tracing_context


def trace_operation(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """Decorator to trace a function."""
    def decorator(f: Callable) -> Callable:
        def wrapper(*args, **kwargs):
            with tracing_context.start_span(
                name=name,
                kind=kind,
                attributes={
                    'function': f.__name__,
                    **(attributes or {})
                }
            ) as span:
                try:
                    result = f(*args, **kwargs)
                    span.status = SpanStatus.OK
                    return result
                except Exception as e:
                    span.status = SpanStatus.ERROR
                    span.status_message = str(e)
                    raise

        return wrapper
    return decorator


def get_trace_id() -> Optional[str]:
    """Get current trace ID."""
    return tracing_context.get_current_trace_id()


@contextmanager
def span(name: str, **attributes):
    """Context manager for creating spans."""
    with tracing_context.start_span(name, attributes=attributes) as s:
        yield s


import traceback
from flask import Flask, request
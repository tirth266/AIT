"""
Structured Logging Module
=========================
JSON-formatted structured logging with:
- Correlation IDs for request tracing
- Standardized field formats
- Sensitive data masking
- Multiple output handlers
"""

import os
import sys
import json
import logging
import uuid
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler, SocketHandler
from pythonjsonlogger import jsonlogger
from flask import Flask, g, request
import threading

correlation_id_context: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
user_id_context: ContextVar[Optional[str]] = ContextVar('user_id', default=None)
request_context: ContextVar[Optional[Dict]] = ContextVar('request_context', default=None)


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record: Dict, record: logging.LogRecord, message_dict: Dict):
        super().add_fields(log_record, record, message_dict)

        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['thread'] = record.threadName
        log_record['process'] = record.process

        correlation_id = correlation_id_context.get()
        if correlation_id:
            log_record['correlation_id'] = correlation_id

        user_id = user_id_context.get()
        if user_id:
            log_record['user_id'] = user_id

        request_ctx = request_context.get()
        if request_ctx:
            log_record['request'] = request_ctx

        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)

    def format(self, record: logging.LogRecord) -> str:
        log_record = {}
        self.add_fields(log_record, record, {})
        return self.dumps(log_record)


class SensitiveDataFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""

    SENSITIVE_FIELDS = {
        'password', 'secret', 'token', 'api_key', 'api_secret',
        'private_key', 'access_token', 'refresh_token', 'jwt',
        'authorization', 'credit_card', 'ssn', 'pin'
    }

    SENSITIVE_PATTERNS = [
        r'sk-[a-zA-Z0-9]{20,}',
        r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if hasattr(record, 'msg') and isinstance(record.msg, dict):
            record.msg = self._mask_sensitive_data(record.msg)
        return True

    def _mask_sensitive_data(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: self._mask_value(k, v)
                for k, v in data.items()
            }
        elif isinstance(data, (list, tuple)):
            return [self._mask_sensitive_data(item) for item in data]
        return data

    def _mask_value(self, key: str, value: Any) -> Any:
        key_lower = key.lower()
        if key_lower in self.SENSITIVE_FIELDS:
            return '***REDACTED***'
        if isinstance(value, str):
            import re
            for pattern in self.SENSITIVE_PATTERNS:
                if re.search(pattern, value):
                    return '***REDACTED***'
        return self._mask_sensitive_data(value)


class CorrelationIdFilter(logging.Filter):
    """Filter to add correlation ID to all log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, 'correlation_id'):
            record.correlation_id = correlation_id_context.get() or str(uuid.uuid4())
        return True


def setup_structured_logging(
    app: Flask,
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_to_console: bool = True,
    log_to_file: bool = True,
    log_to_syslog: bool = False,
    max_bytes: int = 10485760,
    backup_count: int = 10,
    json_format: bool = True
) -> logging.Logger:
    """Setup structured logging for the application."""

    level = log_level or app.config.get('LOG_LEVEL', 'INFO')
    logger = logging.getLogger('trading_app')
    logger.setLevel(getattr(logging, level.upper()))

    logger.handlers.clear()

    sensitive_filter = SensitiveDataFilter()
    correlation_filter = CorrelationIdFilter()

    if json_format:
        formatter = StructuredFormatter(
            fmt='%(timestamp)s %(level)s %(name)s %(message)s',
            rename_fields={'message': 'msg'}
        )
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, level.upper()))
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)
        console_handler.addFilter(correlation_filter)
        logger.addHandler(console_handler)

    if log_to_file or log_file:
        log_dir = log_file or os.path.join(os.path.dirname(__file__), '../../logs')
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'trading_app.log'),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        file_handler.setLevel(getattr(logging, level.upper()))
        file_handler.setFormatter(formatter)
        file_handler.addFilter(sensitive_filter)
        file_handler.addFilter(correlation_filter)
        logger.addHandler(file_handler)

        error_file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'trading_app_error.log'),
            maxBytes=max_bytes,
            backupCount=backup_count
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(formatter)
        error_file_handler.addFilter(sensitive_filter)
        error_file_handler.addFilter(correlation_filter)
        logger.addHandler(error_file_handler)

    if log_to_syslog:
        syslog_handler = SocketHandler('localhost', 514)
        syslog_handler.setLevel(getattr(logging, level.upper()))
        syslog_handler.addFilter(sensitive_filter)
        syslog_handler.addFilter(correlation_filter)
        logger.addHandler(syslog_handler)

    logger.info("Structured logging initialized")
    return logger


class StructuredLogger:
    """Structured logger with convenience methods."""

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _log(self, level: int, message: str, extra: Optional[Dict] = None, **kwargs):
        extra = extra or {}
        extra.update(kwargs)

        if correlation_id := correlation_id_context.get():
            extra['correlation_id'] = correlation_id

        if user_id := user_id_context.get():
            extra['user_id'] = user_id

        self.logger.log(level, message, extra=extra, stacklevel=2)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            kwargs['traceback'] = traceback.format_exc()
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        if error:
            kwargs['error_type'] = type(error).__name__
            kwargs['error_message'] = str(error)
            kwargs['traceback'] = traceback.format_exc()
        self._log(logging.CRITICAL, message, **kwargs)

    def log_request(self, method: str, path: str, status: int, duration: float, **kwargs):
        self.info(
            f"{method} {path} {status}",
            event='request',
            method=method,
            path=path,
            status=status,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )

    def log_websocket_event(self, event: str, connection_id: str, **kwargs):
        self.info(
            f"WebSocket {event}",
            event='websocket',
            websocket_event=event,
            connection_id=connection_id[:8] if connection_id else None,
            **kwargs
        )

    def log_order(self, order_id: str, symbol: str, side: str, quantity: float, price: float, **kwargs):
        self.info(
            f"Order {order_id}: {side} {quantity} {symbol} @ {price}",
            event='order',
            order_id=order_id,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            **kwargs
        )

    def log_strategy(self, strategy: str, event: str, **kwargs):
        self.info(
            f"Strategy {strategy}: {event}",
            event='strategy',
            strategy=strategy,
            strategy_event=event,
            **kwargs
        )

    def log_market_data(self, symbol: str, data_type: str, **kwargs):
        self.debug(
            f"Market data: {symbol} {data_type}",
            event='market_data',
            symbol=symbol,
            data_type=data_type,
            **kwargs
        )

    def log_database_operation(self, operation: str, collection: str, duration: float, **kwargs):
        self.debug(
            f"Database {operation} on {collection}",
            event='database',
            operation=operation,
            collection=collection,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )

    def log_redis_operation(self, operation: str, key: str, duration: float, **kwargs):
        self.debug(
            f"Redis {operation} on {key}",
            event='redis',
            operation=operation,
            key=key[:50] if key else None,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )


_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger."""
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return f"corr-{uuid.uuid4().hex[:16]}"


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_context.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Get correlation ID from current context."""
    return correlation_id_context.get()


def set_user_id(user_id: str) -> None:
    """Set user ID for current context."""
    user_id_context.set(user_id)


def get_user_id() -> Optional[str]:
    """Get user ID from current context."""
    return user_id_context.get()


def bind_context(**kwargs) -> None:
    """Bind additional context to logs."""
    ctx = request_context.get() or {}
    ctx.update(kwargs)
    request_context.set(ctx)


def clear_context() -> None:
    """Clear all context."""
    correlation_id_context.set(None)
    user_id_context.set(None)
    request_context.set(None)


class RequestLoggingMiddleware:
    """Middleware to log all HTTP requests."""

    def __init__(self, app: Flask):
        self.app = app
        self.logger = get_logger('trading_app.request')

    def __call__(self, environ, start_response):
        correlation_id = generate_correlation_id()
        correlation_id_context.set(correlation_id)

        def logging_start_response(status, headers, exc_info=None):
            duration = time.time() - start_time
            status_code = int(status.split()[0])

            self.logger.log_request(
                method=environ.get('REQUEST_METHOD', 'GET'),
                path=environ.get('PATH_INFO', '/'),
                status=status_code,
                duration=duration,
                correlation_id=correlation_id
            )

            return start_response(status, headers, exc_info)

        start_time = time.time()
        return self.app(environ, logging_start_response)


import time


def init_request_logging(app: Flask) -> None:
    """Initialize request logging middleware."""

    @app.before_request
    def before_request():
        correlation_id = request.headers.get('X-Correlation-ID') or generate_correlation_id()
        correlation_id_context.set(correlation_id)
        g.correlation_id = correlation_id

        if request.authorization:
            user_id_context.set(request.authorization.get('username', 'anonymous'))

        request_context.set({
            'method': request.method,
            'path': request.path,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', ''),
        })

    @app.after_request
    def after_request(response):
        correlation_id = correlation_id_context.get()
        if correlation_id:
            response.headers['X-Correlation-ID'] = correlation_id

        clear_context()
        return response

    @app.teardown_request
    def teardown_request(exception=None):
        clear_context()

    app.logger.info("Request logging middleware initialized")
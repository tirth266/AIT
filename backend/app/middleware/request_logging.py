"""
Request Logging Middleware
==========================
Log incoming requests and responses.
"""

from flask import Flask, request
import logging
import time
import uuid

logger = logging.getLogger('trading_app')


def init_request_logging(app: Flask) -> None:
    """Initialize request logging middleware."""

    @app.before_request
    def before_request():
        request.id = str(uuid.uuid4())[:8]
        request.start_time = time.time()

        logger.debug(
            f"Request started: {request.method} {request.path}",
            extra={
                'request_id': request.id,
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr
            }
        )

    @app.after_request
    def after_request(response):
        # Use getattr to avoid AttributeError if before_request was skipped
        request_id = getattr(request, 'id', 'unknown')
        start_time = getattr(request, 'start_time', None)
        
        if start_time:
            elapsed = time.time() - start_time
            logger.info(
                f"Request completed: {request.method} {request.path} - {response.status_code} ({elapsed:.3f}s)",
                extra={
                    'request_id': request_id,
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'elapsed_ms': round(elapsed * 1000, 2)
                }
            )

        return response

    logger.info("Request logging middleware initialized")
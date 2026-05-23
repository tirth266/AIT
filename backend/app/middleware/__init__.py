"""
=============================================================================
MIDDLEWARE MODULE
=============================================================================
Flask middleware for request processing, security, and monitoring.
"""

from flask import Flask
from .rate_limit import init_rate_limiting
from .request_logging import init_request_logging
from .security import init_security


def register_middleware(app: Flask) -> None:
    """Register all middleware with the Flask app."""
    init_security(app)  # Security headers and request validation
    init_rate_limiting(app)
    init_request_logging(app)
    print("[OK] All middleware registered")
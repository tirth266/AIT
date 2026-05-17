"""
Broker Errors
=============
Custom exceptions for broker-related errors.
"""

from app.errors.base import AppError, ErrorCode


class BrokerError(AppError):
    """Base broker error."""

    def __init__(self, message: str, broker_name: str = None, details: dict = None):
        error_details = details or {}
        if broker_name:
            error_details['broker'] = broker_name
        super().__init__(
            message,
            ErrorCode.BROKER_ERROR,
            status_code=502,
            details=error_details
        )


class BrokerConnectionError(BrokerError):
    """Broker connection error."""

    def __init__(self, broker_name: str, message: str = "Failed to connect to broker"):
        super().__init__(message, broker_name)


class BrokerAPIError(BrokerError):
    """Broker API error."""

    def __init__(self, broker_name: str, message: str, api_error: str = None):
        details = {'api_error': api_error} if api_error else {}
        super().__init__(message, broker_name, details)


class BrokerAuthenticationError(BrokerError):
    """Broker authentication error."""

    def __init__(self, broker_name: str, message: str = "Invalid broker credentials"):
        super().__init__(
            message,
            broker_name,
            details={'error': 'authentication_failed'}
        )


class BrokerRateLimitError(BrokerError):
    """Broker rate limit error."""

    def __init__(self, broker_name: str, retry_after: int = None):
        message = f"Broker rate limit exceeded"
        details = {'retry_after': retry_after} if retry_after else {}
        super().__init__(message, broker_name, details)
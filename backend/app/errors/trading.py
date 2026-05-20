"""
Trading Errors
==============
Custom exceptions for trading-related errors.
"""

from app.errors.base import TradingError as BaseTradingError, ErrorCode

# Alias so that `from app.errors.trading import TradingError` works
TradingError = BaseTradingError


class InsufficientBalanceError(BaseTradingError):
    """Insufficient balance error."""

    def __init__(self, message: str = "Insufficient balance"):
        super().__init__(
            message,
            ErrorCode.TRADING_ERROR,
            status_code=400
        )


class RiskLimitExceededError(BaseTradingError):
    """Risk limit exceeded error."""

    def __init__(self, message: str, limit_type: str = None):
        details = {'limit_type': limit_type} if limit_type else {}
        super().__init__(
            message,
            ErrorCode.RISK_LIMIT_ERROR,
            status_code=400,
            details=details
        )


class InvalidSignalError(BaseTradingError):
    """Invalid trading signal error."""

    def __init__(self, message: str = "Invalid trading signal"):
        super().__init__(
            message,
            ErrorCode.TRADING_ERROR,
            status_code=400
        )


class PositionNotFoundError(BaseTradingError):
    """Position not found error."""

    def __init__(self, position_id: str = None):
        message = f"Position not found: {position_id}" if position_id else "Position not found"
        super().__init__(
            message,
            ErrorCode.TRADING_ERROR,
            status_code=404
        )


class OrderExecutionError(BaseTradingError):
    """Order execution error."""

    def __init__(self, message: str, order_id: str = None):
        details = {'order_id': order_id} if order_id else {}
        super().__init__(
            message,
            ErrorCode.TRADING_ERROR,
            status_code=500,
            details=details
        )


class CircuitBreakerError(BaseTradingError):
    """Circuit breaker triggered error."""

    def __init__(self, reason: str):
        super().__init__(
            f"Circuit breaker triggered: {reason}",
            ErrorCode.RISK_LIMIT_ERROR,
            status_code=503,
            details={'reason': reason, 'action': 'pause_trading'}
        )
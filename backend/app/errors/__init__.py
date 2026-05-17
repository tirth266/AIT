"""
Error Handling Module
=====================
Custom exceptions and error handlers for the application.
"""

from app.errors.base import (
    TradingError,
    AppError,
    ErrorCode
)
from app.errors.auth import (
    AuthenticationError,
    InvalidCredentialsError,
    TokenExpiredError,
    TokenInvalidError
)
from app.errors.trading import (
    TradingError as TradingErrorEx,
    InsufficientBalanceError,
    RiskLimitExceededError,
    InvalidSignalError,
    PositionNotFoundError
)
from app.errors.broker import (
    BrokerError,
    BrokerConnectionError,
    BrokerAPIError
)
from app.errors.validation import (
    ValidationError,
    InvalidParameterError
)

__all__ = [
    'TradingError',
    'AppError',
    'ErrorCode',
    'AuthenticationError',
    'InvalidCredentialsError',
    'TokenExpiredError',
    'TokenInvalidError',
    'InsufficientBalanceError',
    'RiskLimitExceededError',
    'InvalidSignalError',
    'PositionNotFoundError',
    'BrokerConnectionError',
    'BrokerAPIError',
    'ValidationError',
    'InvalidParameterError'
]
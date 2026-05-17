"""
Base Error Classes
==================
Base exceptions and error codes for the application.
"""

from enum import Enum
from typing import Optional, Dict, Any


class ErrorCode(Enum):
    """Error codes for the application."""
    GENERAL_ERROR = 'GENERAL_ERROR'
    VALIDATION_ERROR = 'VALIDATION_ERROR'
    AUTHENTICATION_ERROR = 'AUTHENTICATION_ERROR'
    AUTHORIZATION_ERROR = 'AUTHORIZATION_ERROR'
    NOT_FOUND = 'NOT_FOUND'
    CONFLICT = 'CONFLICT'
    RATE_LIMIT_EXCEEDED = 'RATE_LIMIT_EXCEEDED'
    BROKER_ERROR = 'BROKER_ERROR'
    TRADING_ERROR = 'TRADING_ERROR'
    RISK_LIMIT_ERROR = 'RISK_LIMIT_ERROR'


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.GENERAL_ERROR,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        result = {
            'error': self.code.value,
            'message': self.message
        }
        if self.details:
            result['details'] = self.details
        return result


class TradingError(AppError):
    """Base trading error."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.TRADING_ERROR,
        status_code: int = 400,
        details: Optional[Dict] = None
    ):
        super().__init__(message, code, status_code, details)


class ValidationError(AppError):
    """Validation error."""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict] = None
    ):
        details = details or {}
        if field:
            details['field'] = field
        super().__init__(
            message,
            ErrorCode.VALIDATION_ERROR,
            status_code=400,
            details=details
        )


class NotFoundError(AppError):
    """Resource not found error."""

    def __init__(self, message: str, resource: Optional[str] = None):
        details = {'resource': resource} if resource else {}
        super().__init__(
            message,
            ErrorCode.NOT_FOUND,
            status_code=404,
            details=details
        )


class ConflictError(AppError):
    """Conflict error."""

    def __init__(self, message: str, details: Optional[Dict] = None):
        super().__init__(
            message,
            ErrorCode.CONFLICT,
            status_code=409,
            details=details
        )
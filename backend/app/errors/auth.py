"""
Authentication Errors
=====================
Custom exceptions for authentication-related errors.
"""

from app.errors.base import AppError, ErrorCode


class AuthenticationError(AppError):
    """Base authentication error."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(
            message,
            ErrorCode.AUTHENTICATION_ERROR,
            status_code=401,
            details=details
        )


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials error."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Token expired error."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            message,
            details={'error': 'token_expired'}
        )


class TokenInvalidError(AuthenticationError):
    """Token invalid error."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(
            message,
            details={'error': 'invalid_token'}
        )


class AuthorizationError(AuthenticationError):
    """Authorization error."""

    def __init__(self, message: str = "Not authorized"):
        super().__init__(
            message,
            details={'error': 'not_authorized'},
            status_code=403
        )
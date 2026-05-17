"""
Validation Errors
=================
Custom exceptions for validation errors.
"""

from app.errors.base import ValidationError as BaseValidationError


class ValidationError(BaseValidationError):
    """Validation error."""

    def __init__(self, message: str, field: str = None, details: dict = None):
        super().__init__(message, field, details)


class InvalidParameterError(ValidationError):
    """Invalid parameter error."""

    def __init__(self, parameter: str, message: str = None):
        msg = message or f"Invalid parameter: {parameter}"
        super().__init__(msg, field=parameter)


class SchemaValidationError(ValidationError):
    """Schema validation error."""

    def __init__(self, errors: list):
        super().__init__(
            "Validation failed",
            details={'errors': errors}
        )
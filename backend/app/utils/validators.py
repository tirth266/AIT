"""
Input Validators
================
Validation functions for API inputs.
"""

import re
from typing import Any, List, Optional


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_symbol(symbol: str) -> bool:
    """Validate trading symbol format."""
    if not symbol:
        raise ValidationError("Symbol is required")

    pattern = r'^[A-Z]{2,10}/[A-Z]{2,10}$'
    if not re.match(pattern, symbol):
        raise ValidationError("Invalid symbol format (e.g., BTC/USDT)")

    return True


def validate_timeframe(timeframe: str) -> bool:
    """Validate timeframe value."""
    valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w']

    if timeframe not in valid_timeframes:
        raise ValidationError(f"Invalid timeframe. Must be one of: {', '.join(valid_timeframes)}")

    return True


def validate_side(side: str) -> bool:
    """Validate trade side."""
    if side.upper() not in ['BUY', 'SELL']:
        raise ValidationError("Side must be BUY or SELL")

    return True


def validate_quantity(quantity: float) -> bool:
    """Validate trade quantity."""
    if quantity <= 0:
        raise ValidationError("Quantity must be greater than 0")

    if quantity > 1000000:
        raise ValidationError("Quantity exceeds maximum allowed")

    return True


def validate_price(price: float) -> bool:
    """Validate price value."""
    if price <= 0:
        raise ValidationError("Price must be greater than 0")

    return True


def validate_percentage(value: float, field_name: str = "value") -> bool:
    """Validate percentage value."""
    if value < 0 or value > 100:
        raise ValidationError(f"{field_name} must be between 0 and 100")

    return True


def validate_strategy_conditions(conditions: List[dict]) -> bool:
    """Validate strategy conditions."""
    if not conditions:
        raise ValidationError("At least one condition is required")

    required_fields = ['indicator', 'operator', 'value']
    valid_operators = [
        'greater_than', 'less_than', 'equals', 'not_equals',
        'crosses_above', 'crosses_below', 'greater_or_equal', 'less_or_equal'
    ]

    for condition in conditions:
        for field in required_fields:
            if field not in condition:
                raise ValidationError(f"Condition missing required field: {field}")

        if condition['operator'] not in valid_operators:
            raise ValidationError(f"Invalid operator: {condition['operator']}")

    return True


def validate_indicator(indicator: dict) -> bool:
    """Validate indicator configuration."""
    valid_indicators = ['RSI', 'EMA', 'SMA', 'MACD', 'BB', 'VWAP', 'Supertrend', 'ATR', 'Stochastic']

    if indicator.get('name') not in valid_indicators:
        raise ValidationError(f"Invalid indicator. Must be one of: {', '.join(valid_indicators)}")

    if 'params' not in indicator:
        raise ValidationError("Indicator must have params")

    return True


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError("Invalid email format")

    return True


def validate_password(password: str) -> bool:
    """Validate password strength."""
    if len(password) < 8:
        raise ValidationError("Password must be at least 8 characters")

    return True


def sanitize_input(value: Any) -> Any:
    """Sanitize user input."""
    if isinstance(value, str):
        value = value.strip()
        value = re.sub(r'[<>]', '', value)

    return value
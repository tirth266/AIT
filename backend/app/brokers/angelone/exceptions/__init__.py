class AngelOneException(Exception):
    """Base exception for Angel One broker."""
    pass

class AuthException(AngelOneException):
    """Raised when authentication fails."""
    pass

class OrderException(AngelOneException):
    """Raised when an order placement or modification fails."""
    pass

class RateLimitException(AngelOneException):
    """Raised when API rate limits are exceeded."""
    pass

class WebSocketException(AngelOneException):
    """Raised when websocket connection or parsing fails."""
    pass

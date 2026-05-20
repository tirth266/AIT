import asyncio
from functools import wraps
from typing import Callable, Any
from .logger import get_logger

logger = get_logger(__name__)

def async_retry(retries: int = 3, delay: float = 1.0, backoff: float = 2.0, exceptions: tuple = (Exception,)):
    """
    Decorator for async function retries with exponential backoff.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            current_delay = delay
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        logger.error(f"Function {func.__name__} failed after {retries} attempts: {str(e)}")
                        raise
                    logger.warning(f"Attempt {attempt + 1} for {func.__name__} failed: {str(e)}. Retrying in {current_delay}s...")
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator

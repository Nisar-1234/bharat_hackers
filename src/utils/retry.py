"""Retry utilities with exponential backoff."""
import time
import functools
from typing import Callable, Type, Tuple
from botocore.exceptions import ClientError


RETRY_CONFIG = {
    "max_retries": 3,
    "base_delay_seconds": 1,
    "max_delay_seconds": 30,
    "exponential_base": 2,
    "retryable_exceptions": [
        "ThrottlingException",
        "ServiceUnavailableException",
        "InternalServerException"
    ]
}


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable."""
    if isinstance(error, ClientError):
        error_code = error.response.get('Error', {}).get('Code', '')
        return error_code in RETRY_CONFIG["retryable_exceptions"]
    return False


def retry_with_backoff(
    max_retries: int = RETRY_CONFIG["max_retries"],
    base_delay: float = RETRY_CONFIG["base_delay_seconds"],
    max_delay: float = RETRY_CONFIG["max_delay_seconds"],
    exponential_base: float = RETRY_CONFIG["exponential_base"]
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            
            while retries <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if not is_retryable_error(e) or retries >= max_retries:
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** retries), max_delay)
                    
                    print(f"Retry {retries + 1}/{max_retries} after {delay}s due to: {str(e)}")
                    time.sleep(delay)
                    retries += 1
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def async_retry_with_backoff(
    max_retries: int = RETRY_CONFIG["max_retries"],
    base_delay: float = RETRY_CONFIG["base_delay_seconds"],
    max_delay: float = RETRY_CONFIG["max_delay_seconds"],
    exponential_base: float = RETRY_CONFIG["exponential_base"]
):
    """
    Decorator for retrying async functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
    """
    def decorator(func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            retries = 0
            
            while retries <= max_retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if not is_retryable_error(e) or retries >= max_retries:
                        raise
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (exponential_base ** retries), max_delay)
                    
                    print(f"Retry {retries + 1}/{max_retries} after {delay}s due to: {str(e)}")
                    await asyncio.sleep(delay)
                    retries += 1
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

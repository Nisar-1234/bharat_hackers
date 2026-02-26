"""Circuit breaker pattern implementation."""
import time
from enum import Enum
from typing import Callable
import functools


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker for AWS service calls.
    
    Configuration:
    - Failure threshold: 5 failures in 60 seconds
    - Recovery timeout: 30 seconds
    - Half-open state: Allow 1 request to test recovery
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        window_size: float = 60.0
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.window_size = window_size
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.opened_at = None
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.state == CircuitState.OPEN and self.opened_at:
            return time.time() - self.opened_at >= self.recovery_timeout
        return False
    
    def _reset_failure_count_if_needed(self):
        """Reset failure count if window has passed."""
        if self.last_failure_time:
            if time.time() - self.last_failure_time > self.window_size:
                self.failure_count = 0
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        # Check if we should attempt reset
        if self._should_attempt_reset():
            self.state = CircuitState.HALF_OPEN
        
        # Reject if circuit is open
        if self.state == CircuitState.OPEN:
            raise Exception("Circuit breaker is OPEN. Service unavailable.")
        
        try:
            result = func(*args, **kwargs)
            
            # Success - reset if in half-open state
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
            
            return result
            
        except Exception as e:
            # Record failure
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            # Reset count if window expired
            self._reset_failure_count_if_needed()
            
            # Open circuit if threshold exceeded
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
            
            # If in half-open, go back to open
            if self.state == CircuitState.HALF_OPEN:
                self.state = CircuitState.OPEN
                self.opened_at = time.time()
            
            raise


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    window_size: float = 60.0
):
    """
    Decorator for applying circuit breaker pattern.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Seconds to wait before attempting recovery
        window_size: Time window for counting failures
    """
    breaker = CircuitBreaker(failure_threshold, recovery_timeout, window_size)
    
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return breaker.call(func, *args, **kwargs)
        return wrapper
    return decorator

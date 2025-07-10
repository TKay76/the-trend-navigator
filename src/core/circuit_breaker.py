"""Circuit Breaker pattern implementation for fault tolerance"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional, Dict, Type
from dataclasses import dataclass, field
from functools import wraps
import asyncio

from .settings import get_settings

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, calls blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker monitoring"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    last_failure_time: Optional[float] = None
    state_changes: Dict[CircuitState, int] = field(default_factory=lambda: {
        CircuitState.CLOSED: 0,
        CircuitState.OPEN: 0,
        CircuitState.HALF_OPEN: 0
    })
    
    @property
    def failure_rate(self) -> float:
        """Calculate failure rate"""
        if self.total_calls == 0:
            return 0.0
        return self.failed_calls / self.total_calls
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        return 1.0 - self.failure_rate


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class CircuitBreaker:
    """
    Circuit Breaker implementation for fault tolerance.
    
    Prevents cascading failures by monitoring error rates and
    temporarily blocking calls to failing services.
    """
    
    def __init__(
        self,
        name: str,
        failure_threshold: Optional[int] = None,
        recovery_timeout: Optional[int] = None,
        expected_exception: Type[Exception] = Exception,
        fallback_function: Optional[Callable] = None
    ):
        """
        Initialize circuit breaker.
        
        Args:
            name: Unique name for this circuit breaker
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again
            expected_exception: Exception type that counts as failure
            fallback_function: Function to call when circuit is open
        """
        settings = get_settings()
        
        self.name = name
        self.failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
        self.recovery_timeout = recovery_timeout or settings.circuit_breaker_recovery_timeout
        self.expected_exception = expected_exception
        self.fallback_function = fallback_function
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._last_state_change = time.time()
        
        logger.info(f"Circuit breaker '{name}' initialized with threshold={self.failure_threshold}, timeout={self.recovery_timeout}")
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        return self._stats
    
    def _can_attempt_call(self) -> bool:
        """Check if we can attempt a call"""
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            # Check if enough time has passed for recovery attempt
            if time.time() - self._last_state_change >= self.recovery_timeout:
                self._transition_to_half_open()
                return True
            return False
        
        if self._state == CircuitState.HALF_OPEN:
            return True
        
        return False
    
    def _transition_to_half_open(self):
        """Transition to half-open state"""
        self._state = CircuitState.HALF_OPEN
        self._stats.state_changes[CircuitState.HALF_OPEN] += 1
        self._last_state_change = time.time()
        logger.info(f"Circuit breaker '{self.name}' transitioned to HALF_OPEN")
    
    def _transition_to_open(self):
        """Transition to open state"""
        self._state = CircuitState.OPEN
        self._stats.state_changes[CircuitState.OPEN] += 1
        self._stats.last_failure_time = time.time()
        self._last_state_change = time.time()
        logger.warning(f"Circuit breaker '{self.name}' OPENED after {self._stats.failed_calls} failures")
    
    def _transition_to_closed(self):
        """Transition to closed state"""
        self._state = CircuitState.CLOSED
        self._stats.state_changes[CircuitState.CLOSED] += 1
        self._last_state_change = time.time()
        logger.info(f"Circuit breaker '{self.name}' CLOSED - service recovered")
    
    def _record_success(self):
        """Record successful call"""
        self._stats.total_calls += 1
        self._stats.successful_calls += 1
        
        # If we're in half-open state and call succeeded, close the circuit
        if self._state == CircuitState.HALF_OPEN:
            self._transition_to_closed()
    
    def _record_failure(self):
        """Record failed call"""
        self._stats.total_calls += 1
        self._stats.failed_calls += 1
        
        # Check if we should open the circuit
        if self._state == CircuitState.CLOSED:
            if self._stats.failed_calls >= self.failure_threshold:
                self._transition_to_open()
        elif self._state == CircuitState.HALF_OPEN:
            # If half-open call fails, go back to open
            self._transition_to_open()
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
            
        Raises:
            CircuitBreakerError: If circuit is open and no fallback
        """
        if not self._can_attempt_call():
            if self.fallback_function:
                logger.debug(f"Circuit breaker '{self.name}' is open, using fallback")
                return self.fallback_function(*args, **kwargs)
            else:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            logger.warning(f"Circuit breaker '{self.name}' recorded failure: {e}")
            raise
        except Exception as e:
            # Unexpected exceptions don't count as failures
            logger.error(f"Circuit breaker '{self.name}' unexpected error: {e}")
            raise
    
    async def acall(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
            
        Returns:
            Function result or fallback result
            
        Raises:
            CircuitBreakerError: If circuit is open and no fallback
        """
        if not self._can_attempt_call():
            if self.fallback_function:
                logger.debug(f"Circuit breaker '{self.name}' is open, using fallback")
                if asyncio.iscoroutinefunction(self.fallback_function):
                    return await self.fallback_function(*args, **kwargs)
                else:
                    return self.fallback_function(*args, **kwargs)
            else:
                raise CircuitBreakerError(f"Circuit breaker '{self.name}' is open")
        
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except self.expected_exception as e:
            self._record_failure()
            logger.warning(f"Circuit breaker '{self.name}' recorded failure: {e}")
            raise
        except Exception as e:
            # Unexpected exceptions don't count as failures
            logger.error(f"Circuit breaker '{self.name}' unexpected error: {e}")
            raise
    
    def reset(self):
        """Reset circuit breaker to initial state"""
        self._state = CircuitState.CLOSED
        self._stats = CircuitBreakerStats()
        self._last_state_change = time.time()
        logger.info(f"Circuit breaker '{self.name}' reset")


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    failure_threshold: Optional[int] = None,
    recovery_timeout: Optional[int] = None,
    expected_exception: Type[Exception] = Exception,
    fallback_function: Optional[Callable] = None
) -> CircuitBreaker:
    """
    Get or create a circuit breaker instance.
    
    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before recovery attempt
        expected_exception: Exception type that counts as failure
        fallback_function: Function to call when circuit is open
        
    Returns:
        CircuitBreaker instance
    """
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            fallback_function=fallback_function
        )
    
    return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    failure_threshold: Optional[int] = None,
    recovery_timeout: Optional[int] = None,
    expected_exception: Type[Exception] = Exception,
    fallback_function: Optional[Callable] = None
):
    """
    Decorator to apply circuit breaker pattern to functions.
    
    Args:
        name: Unique name for the circuit breaker
        failure_threshold: Number of failures before opening
        recovery_timeout: Seconds to wait before recovery attempt
        expected_exception: Exception type that counts as failure
        fallback_function: Function to call when circuit is open
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(
            name=name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            expected_exception=expected_exception,
            fallback_function=fallback_function
        )
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await breaker.acall(func, *args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return breaker.call(func, *args, **kwargs)
            return sync_wrapper
    
    return decorator


def get_all_circuit_breakers() -> Dict[str, CircuitBreaker]:
    """Get all registered circuit breakers"""
    return _circuit_breakers.copy()


def reset_all_circuit_breakers():
    """Reset all circuit breakers"""
    for breaker in _circuit_breakers.values():
        breaker.reset()
    logger.info("All circuit breakers reset")
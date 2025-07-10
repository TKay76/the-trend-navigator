"""Enhanced retry logic with exponential backoff and jitter"""

import asyncio
import random
import time
import logging
from typing import Callable, Any, Type, Union, List, Optional, Tuple
from functools import wraps
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    exceptions: Tuple[Type[Exception], ...] = (Exception,)


class RetryError(Exception):
    """Exception raised when all retry attempts are exhausted"""
    
    def __init__(self, attempts: int, last_exception: Exception):
        self.attempts = attempts
        self.last_exception = last_exception
        super().__init__(f"Failed after {attempts} attempts. Last error: {last_exception}")


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculate delay for retry attempt with exponential backoff and jitter.
    
    Args:
        attempt: Current attempt number (starting from 1)
        config: Retry configuration
        
    Returns:
        Delay in seconds
    """
    # Exponential backoff
    delay = config.base_delay * (config.exponential_base ** (attempt - 1))
    
    # Cap at max_delay
    delay = min(delay, config.max_delay)
    
    # Add jitter to prevent thundering herd
    if config.jitter:
        # Random jitter between 50% and 100% of calculated delay
        jitter_range = delay * 0.5
        delay = delay - jitter_range + (random.random() * jitter_range * 2)
    
    return max(0, delay)


async def retry_async(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute async function with retry logic.
    
    Args:
        func: Async function to execute
        *args: Function arguments
        config: Retry configuration
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryError: If all attempts fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.debug(f"Attempt {attempt}/{config.max_attempts} for {func.__name__}")
            result = await func(*args, **kwargs)
            
            if attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
            
            return result
            
        except config.exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(f"Function {func.__name__} failed after {attempt} attempts: {e}")
                break
            
            delay = calculate_delay(attempt, config)
            logger.warning(f"Function {func.__name__} failed on attempt {attempt}: {e}. Retrying in {delay:.2f}s")
            
            await asyncio.sleep(delay)
        
        except Exception as e:
            # Non-retryable exception
            logger.error(f"Function {func.__name__} failed with non-retryable exception: {e}")
            raise
    
    raise RetryError(config.max_attempts, last_exception)


def retry_sync(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute function with retry logic.
    
    Args:
        func: Function to execute
        *args: Function arguments
        config: Retry configuration
        **kwargs: Function keyword arguments
        
    Returns:
        Function result
        
    Raises:
        RetryError: If all attempts fail
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.debug(f"Attempt {attempt}/{config.max_attempts} for {func.__name__}")
            result = func(*args, **kwargs)
            
            if attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")
            
            return result
            
        except config.exceptions as e:
            last_exception = e
            
            if attempt == config.max_attempts:
                logger.error(f"Function {func.__name__} failed after {attempt} attempts: {e}")
                break
            
            delay = calculate_delay(attempt, config)
            logger.warning(f"Function {func.__name__} failed on attempt {attempt}: {e}. Retrying in {delay:.2f}s")
            
            time.sleep(delay)
        
        except Exception as e:
            # Non-retryable exception
            logger.error(f"Function {func.__name__} failed with non-retryable exception: {e}")
            raise
    
    raise RetryError(config.max_attempts, last_exception)


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    exceptions: Union[Type[Exception], Tuple[Type[Exception], ...]] = Exception
):
    """
    Decorator to add retry logic to functions.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        jitter: Whether to add random jitter
        exceptions: Exception types to retry on
    """
    if isinstance(exceptions, type):
        exceptions = (exceptions,)
    
    config = RetryConfig(
        max_attempts=max_attempts,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        exceptions=exceptions
    )
    
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_async(func, *args, config=config, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_sync(func, *args, config=config, **kwargs)
            return sync_wrapper
    
    return decorator


class RetryManager:
    """
    Context manager for retry operations with custom configurations.
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_exception = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type and issubclass(exc_type, self.config.exceptions):
            self.last_exception = exc_val
            self.attempt += 1
            
            if self.attempt < self.config.max_attempts:
                delay = calculate_delay(self.attempt, self.config)
                logger.warning(f"Attempt {self.attempt} failed: {exc_val}. Retrying in {delay:.2f}s")
                time.sleep(delay)
                return True  # Suppress the exception
            else:
                logger.error(f"All {self.config.max_attempts} attempts failed")
                return False  # Let the exception propagate
        
        return False  # Don't suppress other exceptions


# Pre-configured retry decorators for common scenarios
api_retry = retry(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    exceptions=(ConnectionError, TimeoutError)
)

database_retry = retry(
    max_attempts=5,
    base_delay=0.5,
    max_delay=10.0,
    exceptions=(ConnectionError,)
)

network_retry = retry(
    max_attempts=3,
    base_delay=2.0,
    max_delay=60.0,
    exceptions=(ConnectionError, TimeoutError)
)
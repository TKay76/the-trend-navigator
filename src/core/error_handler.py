"""Global error handling and recovery mechanisms"""

import logging
import traceback
from typing import Optional, Callable, Any, Dict, Type
from functools import wraps
import asyncio

from .exceptions import (
    YouTubeTrendAnalysisError, YouTubeAPIError, QuotaExceededError,
    LLMProviderError, ClassificationError, RateLimitError
)
from .circuit_breaker import get_circuit_breaker, CircuitBreakerError
from .retry import retry_async, retry_sync, RetryConfig, RetryError
from .settings import get_settings

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy:
    """Base class for error recovery strategies"""
    
    def can_handle(self, error: Exception) -> bool:
        """Check if this strategy can handle the given error"""
        raise NotImplementedError
    
    def handle(self, error: Exception, context: Dict[str, Any]) -> Any:
        """Handle the error and return a recovery result"""
        raise NotImplementedError


class MockFallbackStrategy(ErrorRecoveryStrategy):
    """Fallback to mock providers when real APIs fail"""
    
    def can_handle(self, error: Exception) -> bool:
        return isinstance(error, (YouTubeAPIError, LLMProviderError, QuotaExceededError))
    
    def handle(self, error: Exception, context: Dict[str, Any]) -> Any:
        logger.warning(f"Falling back to mock provider due to: {error}")
        
        # Switch to mock mode temporarily
        settings = get_settings()
        if not settings.use_mock_llm:
            logger.info("Enabling mock LLM provider for error recovery")
            # Note: In a real implementation, you'd want to create a new settings instance
            # or use a configuration manager that can switch providers dynamically
        
        # Return a mock response based on context
        if 'operation' in context:
            operation = context['operation']
            if operation == 'classify_video':
                return {
                    'category': 'Challenge',
                    'confidence': 0.3,
                    'reasoning': 'Fallback classification due to API error'
                }
            elif operation == 'collect_videos':
                return []  # Empty list as fallback
        
        return None


class GracefulDegradationStrategy(ErrorRecoveryStrategy):
    """Provide degraded functionality when full service unavailable"""
    
    def can_handle(self, error: Exception) -> bool:
        return isinstance(error, (CircuitBreakerError, RetryError))
    
    def handle(self, error: Exception, context: Dict[str, Any]) -> Any:
        logger.warning(f"Applying graceful degradation due to: {error}")
        
        operation = context.get('operation', 'unknown')
        
        if operation == 'classify_video':
            # Return a safe default classification
            return {
                'category': 'Unknown',
                'confidence': 0.1,
                'reasoning': 'Service unavailable - using default classification'
            }
        elif operation == 'collect_videos':
            # Return cached results if available, otherwise empty
            cached_result = context.get('cached_result', [])
            logger.info(f"Using cached result with {len(cached_result)} items")
            return cached_result
        
        return None


class ErrorHandler:
    """
    Centralized error handling and recovery system.
    
    Manages error recovery strategies, circuit breakers, and fallback mechanisms.
    """
    
    def __init__(self):
        self.strategies = [
            MockFallbackStrategy(),
            GracefulDegradationStrategy()
        ]
        self.error_counts: Dict[str, int] = {}
    
    def add_strategy(self, strategy: ErrorRecoveryStrategy):
        """Add a new error recovery strategy"""
        self.strategies.append(strategy)
    
    def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True
    ) -> Any:
        """
        Handle an error using available recovery strategies.
        
        Args:
            error: The exception that occurred
            context: Additional context for recovery
            reraise: Whether to reraise if no recovery possible
            
        Returns:
            Recovery result if successful, None otherwise
            
        Raises:
            Original exception if no recovery possible and reraise=True
        """
        if context is None:
            context = {}
        
        # Log the error
        error_type = type(error).__name__
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
        
        logger.error(f"Handling error ({self.error_counts[error_type]} occurrences): {error}")
        logger.debug(f"Error context: {context}")
        logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Try recovery strategies
        for strategy in self.strategies:
            if strategy.can_handle(error):
                try:
                    result = strategy.handle(error, context)
                    logger.info(f"Error recovered using {strategy.__class__.__name__}")
                    return result
                except Exception as recovery_error:
                    logger.warning(f"Recovery strategy {strategy.__class__.__name__} failed: {recovery_error}")
        
        # No recovery possible
        logger.error(f"No recovery strategy available for {error_type}")
        
        if reraise:
            raise error
        
        return None
    
    async def handle_error_async(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        reraise: bool = True
    ) -> Any:
        """Async version of handle_error"""
        # For now, use sync version since recovery strategies are sync
        # In a real implementation, you might have async recovery strategies
        return self.handle_error(error, context, reraise)
    
    def get_error_stats(self) -> Dict[str, int]:
        """Get error occurrence statistics"""
        return self.error_counts.copy()
    
    def reset_stats(self):
        """Reset error statistics"""
        self.error_counts.clear()


# Global error handler instance
error_handler = ErrorHandler()


def handle_errors(
    operation: str,
    fallback_result: Any = None,
    reraise: bool = False
):
    """
    Decorator to add error handling to functions.
    
    Args:
        operation: Name of the operation for context
        fallback_result: Result to return if error handling fails
        reraise: Whether to reraise exceptions after handling
    """
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    context = {
                        'operation': operation,
                        'function': func.__name__,
                        'args': args[:2],  # Limit for privacy
                        'fallback_result': fallback_result
                    }
                    
                    result = await error_handler.handle_error_async(e, context, reraise)
                    return result if result is not None else fallback_result
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    context = {
                        'operation': operation,
                        'function': func.__name__,
                        'args': args[:2],  # Limit for privacy
                        'fallback_result': fallback_result
                    }
                    
                    result = error_handler.handle_error(e, context, reraise)
                    return result if result is not None else fallback_result
            
            return sync_wrapper
    
    return decorator


def robust_api_call(
    name: str,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple = (Exception,)
):
    """
    Decorator combining circuit breaker, retry logic, and error handling.
    
    Args:
        name: Unique name for the circuit breaker
        max_attempts: Maximum retry attempts
        base_delay: Base delay for retries
        exceptions: Exception types to handle
    """
    def decorator(func: Callable) -> Callable:
        # Get circuit breaker for this API call
        breaker = get_circuit_breaker(
            name=name,
            expected_exception=exceptions[0] if exceptions else Exception
        )
        
        # Create retry config
        retry_config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            exceptions=exceptions
        )
        
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                try:
                    # Use circuit breaker with retry logic
                    async def protected_call():
                        return await retry_async(func, *args, config=retry_config, **kwargs)
                    
                    return await breaker.acall(protected_call)
                    
                except Exception as e:
                    context = {
                        'operation': name,
                        'function': func.__name__,
                        'circuit_breaker_state': breaker.state.value,
                        'circuit_breaker_stats': breaker.stats
                    }
                    
                    return await error_handler.handle_error_async(e, context, reraise=False)
            
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                try:
                    # Use circuit breaker with retry logic
                    def protected_call():
                        return retry_sync(func, *args, config=retry_config, **kwargs)
                    
                    return breaker.call(protected_call)
                    
                except Exception as e:
                    context = {
                        'operation': name,
                        'function': func.__name__,
                        'circuit_breaker_state': breaker.state.value,
                        'circuit_breaker_stats': breaker.stats
                    }
                    
                    return error_handler.handle_error(e, context, reraise=False)
            
            return sync_wrapper
    
    return decorator


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance"""
    return error_handler
"""Advanced logging system with structured logging and performance metrics"""

import json
import logging
import logging.handlers
import time
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
from functools import wraps
import threading
import os

from .settings import get_settings


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter for structured JSON logging.
    
    Outputs logs in JSON format for better parsing and analysis.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON"""
        
        # Base log data
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'thread': record.thread,
            'thread_name': record.threadName,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add extra fields from log record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in {
                'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                'filename', 'module', 'exc_info', 'exc_text', 'stack_info',
                'lineno', 'funcName', 'created', 'msecs', 'relativeCreated',
                'thread', 'threadName', 'processName', 'process', 'getMessage'
            }:
                extra_fields[key] = value
        
        if extra_fields:
            log_data['extra'] = extra_fields
        
        return json.dumps(log_data, default=str, ensure_ascii=False)


class PerformanceMetrics:
    """Track performance metrics for operations"""
    
    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def record_operation(
        self,
        operation: str,
        duration: float,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Record performance metrics for an operation"""
        with self._lock:
            if operation not in self._metrics:
                self._metrics[operation] = {
                    'total_calls': 0,
                    'successful_calls': 0,
                    'failed_calls': 0,
                    'total_duration': 0.0,
                    'min_duration': float('inf'),
                    'max_duration': 0.0,
                    'last_call': None
                }
            
            metrics = self._metrics[operation]
            metrics['total_calls'] += 1
            metrics['total_duration'] += duration
            metrics['min_duration'] = min(metrics['min_duration'], duration)
            metrics['max_duration'] = max(metrics['max_duration'], duration)
            metrics['last_call'] = datetime.now().isoformat()
            
            if success:
                metrics['successful_calls'] += 1
            else:
                metrics['failed_calls'] += 1
    
    def get_metrics(self, operation: Optional[str] = None) -> Dict[str, Any]:
        """Get performance metrics"""
        with self._lock:
            if operation:
                metrics = self._metrics.get(operation, {})
                if metrics and metrics['total_calls'] > 0:
                    metrics = metrics.copy()
                    metrics['avg_duration'] = metrics['total_duration'] / metrics['total_calls']
                    metrics['success_rate'] = metrics['successful_calls'] / metrics['total_calls']
                return metrics
            else:
                result = {}
                for op, metrics in self._metrics.items():
                    if metrics['total_calls'] > 0:
                        op_metrics = metrics.copy()
                        op_metrics['avg_duration'] = metrics['total_duration'] / metrics['total_calls']
                        op_metrics['success_rate'] = metrics['successful_calls'] / metrics['total_calls']
                        result[op] = op_metrics
                return result
    
    def reset(self, operation: Optional[str] = None):
        """Reset metrics"""
        with self._lock:
            if operation:
                self._metrics.pop(operation, None)
            else:
                self._metrics.clear()


# Global performance metrics instance
performance_metrics = PerformanceMetrics()


class LoggingManager:
    """
    Centralized logging configuration and management.
    
    Handles structured logging, log rotation, and performance tracking.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.configured = False
        self.loggers = {}
    
    def setup_logging(self):
        """Configure logging system"""
        if self.configured:
            return
        
        # Create logs directory
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.settings.log_level))
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, self.settings.log_level))
        
        if self.settings.is_production:
            # Structured JSON logging for production
            console_handler.setFormatter(StructuredFormatter())
        else:
            # Human-readable logging for development
            console_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            console_handler.setFormatter(logging.Formatter(console_format))
        
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "application.log",
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=5
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)
        
        # Error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "errors.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)
        
        # Performance metrics file handler
        metrics_handler = logging.handlers.RotatingFileHandler(
            log_dir / "metrics.log",
            maxBytes=20 * 1024 * 1024,  # 20MB
            backupCount=3
        )
        metrics_handler.setLevel(logging.INFO)
        metrics_handler.setFormatter(StructuredFormatter())
        
        # Create metrics logger
        metrics_logger = logging.getLogger('metrics')
        metrics_logger.addHandler(metrics_handler)
        metrics_logger.setLevel(logging.INFO)
        metrics_logger.propagate = False
        
        self.configured = True
        
        # Log startup
        logger = logging.getLogger(__name__)
        logger.info(
            "Logging system initialized",
            extra={
                'environment': self.settings.environment,
                'log_level': self.settings.log_level,
                'structured_logging': self.settings.is_production
            }
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a configured logger instance"""
        if not self.configured:
            self.setup_logging()
        
        if name not in self.loggers:
            logger = logging.getLogger(name)
            self.loggers[name] = logger
        
        return self.loggers[name]


# Global logging manager
logging_manager = LoggingManager()


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance"""
    return logging_manager.get_logger(name)


def log_performance(operation: str, include_args: bool = False):
    """
    Decorator to log performance metrics for functions.
    
    Args:
        operation: Name of the operation for metrics
        include_args: Whether to include function arguments in logs
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            success = True
            result = None
            
            # Log function start
            log_data = {
                'operation': operation,
                'function': func.__name__,
                'start_time': datetime.now().isoformat()
            }
            
            if include_args:
                log_data['args'] = str(args[:2])  # Limit for privacy
                log_data['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}  # Truncate
            
            logger.info(f"Starting {operation}", extra=log_data)
            
            try:
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                logger.error(
                    f"Operation {operation} failed: {e}",
                    extra={
                        'operation': operation,
                        'function': func.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                raise
                
            finally:
                duration = time.time() - start_time
                
                # Record metrics
                performance_metrics.record_operation(
                    operation=operation,
                    duration=duration,
                    success=success
                )
                
                # Log completion
                logger.info(
                    f"Completed {operation}",
                    extra={
                        'operation': operation,
                        'function': func.__name__,
                        'duration': duration,
                        'success': success,
                        'end_time': datetime.now().isoformat()
                    }
                )
                
                # Log to metrics logger
                metrics_logger = logging.getLogger('metrics')
                metrics_logger.info(
                    f"Performance: {operation}",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)
            start_time = time.time()
            success = True
            result = None
            
            # Log function start
            log_data = {
                'operation': operation,
                'function': func.__name__,
                'start_time': datetime.now().isoformat()
            }
            
            if include_args:
                log_data['args'] = str(args[:2])  # Limit for privacy
                log_data['kwargs'] = {k: str(v)[:100] for k, v in kwargs.items()}  # Truncate
            
            logger.info(f"Starting {operation}", extra=log_data)
            
            try:
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                logger.error(
                    f"Operation {operation} failed: {e}",
                    extra={
                        'operation': operation,
                        'function': func.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                raise
                
            finally:
                duration = time.time() - start_time
                
                # Record metrics
                performance_metrics.record_operation(
                    operation=operation,
                    duration=duration,
                    success=success
                )
                
                # Log completion
                logger.info(
                    f"Completed {operation}",
                    extra={
                        'operation': operation,
                        'function': func.__name__,
                        'duration': duration,
                        'success': success,
                        'end_time': datetime.now().isoformat()
                    }
                )
                
                # Log to metrics logger
                metrics_logger = logging.getLogger('metrics')
                metrics_logger.info(
                    f"Performance: {operation}",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'success': success,
                        'timestamp': datetime.now().isoformat()
                    }
                )
        
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:  # CO_COROUTINE
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def setup_logging():
    """Initialize the logging system"""
    logging_manager.setup_logging()


def get_performance_metrics(operation: Optional[str] = None) -> Dict[str, Any]:
    """Get performance metrics"""
    return performance_metrics.get_metrics(operation)


def reset_performance_metrics(operation: Optional[str] = None):
    """Reset performance metrics"""
    performance_metrics.reset(operation)
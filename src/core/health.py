"""Health check and monitoring system"""

import asyncio
import time
import psutil
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import json

from .settings import get_settings
from .circuit_breaker import get_all_circuit_breakers
from .logging import get_performance_metrics

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheck:
    """Individual health check result"""
    name: str
    status: HealthStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    response_time: Optional[float] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class HealthChecker:
    """
    System health monitoring and checks.
    
    Monitors various aspects of the application including:
    - System resources (CPU, memory, disk)
    - Circuit breaker states
    - API connectivity
    - Performance metrics
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.checks: Dict[str, Callable] = {}
        self.last_check_time: Optional[datetime] = None
        self.last_results: List[HealthCheck] = []
        
        # Register default checks
        self._register_default_checks()
    
    def _register_default_checks(self):
        """Register default health checks"""
        self.register_check("system_resources", self._check_system_resources)
        self.register_check("circuit_breakers", self._check_circuit_breakers)
        self.register_check("performance_metrics", self._check_performance_metrics)
        self.register_check("configuration", self._check_configuration)
    
    def register_check(self, name: str, check_func: Callable):
        """Register a new health check"""
        self.checks[name] = check_func
        logger.debug(f"Registered health check: {name}")
    
    async def run_all_checks(self) -> List[HealthCheck]:
        """Run all registered health checks"""
        results = []
        start_time = time.time()
        
        logger.info("Starting health checks")
        
        for name, check_func in self.checks.items():
            try:
                check_start = time.time()
                
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()
                
                result.response_time = time.time() - check_start
                results.append(result)
                
                logger.debug(f"Health check '{name}' completed: {result.status.value}")
                
            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                results.append(HealthCheck(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {e}",
                    response_time=time.time() - check_start
                ))
        
        total_time = time.time() - start_time
        self.last_check_time = datetime.now()
        self.last_results = results
        
        logger.info(f"Health checks completed in {total_time:.2f}s")
        return results
    
    def get_overall_status(self, results: Optional[List[HealthCheck]] = None) -> HealthStatus:
        """Determine overall system health status"""
        if results is None:
            results = self.last_results
        
        if not results:
            return HealthStatus.UNHEALTHY
        
        # If any check is unhealthy, system is unhealthy
        if any(check.status == HealthStatus.UNHEALTHY for check in results):
            return HealthStatus.UNHEALTHY
        
        # If any check is degraded, system is degraded
        if any(check.status == HealthStatus.DEGRADED for check in results):
            return HealthStatus.DEGRADED
        
        # All checks healthy
        return HealthStatus.HEALTHY
    
    def _check_system_resources(self) -> HealthCheck:
        """Check system resource usage"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            
            details = {
                'cpu_percent': cpu_percent,
                'memory_percent': memory_percent,
                'disk_percent': disk_percent,
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3)
            }
            
            # Determine status based on thresholds
            if cpu_percent > 90 or memory_percent > 90 or disk_percent > 90:
                status = HealthStatus.UNHEALTHY
                message = "Critical resource usage"
            elif cpu_percent > 70 or memory_percent > 70 or disk_percent > 80:
                status = HealthStatus.DEGRADED
                message = "High resource usage"
            else:
                status = HealthStatus.HEALTHY
                message = "Resource usage normal"
            
            return HealthCheck(
                name="system_resources",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheck(
                name="system_resources",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {e}"
            )
    
    def _check_circuit_breakers(self) -> HealthCheck:
        """Check circuit breaker states"""
        try:
            breakers = get_all_circuit_breakers()
            
            if not breakers:
                return HealthCheck(
                    name="circuit_breakers",
                    status=HealthStatus.HEALTHY,
                    message="No circuit breakers configured"
                )
            
            open_breakers = []
            degraded_breakers = []
            
            details = {}
            
            for name, breaker in breakers.items():
                breaker_info = {
                    'state': breaker.state.value,
                    'failure_rate': breaker.stats.failure_rate,
                    'total_calls': breaker.stats.total_calls,
                    'failed_calls': breaker.stats.failed_calls
                }
                details[name] = breaker_info
                
                if breaker.state.value == 'open':
                    open_breakers.append(name)
                elif breaker.state.value == 'half_open' or breaker.stats.failure_rate > 0.5:
                    degraded_breakers.append(name)
            
            # Determine status
            if open_breakers:
                status = HealthStatus.UNHEALTHY
                message = f"Circuit breakers open: {', '.join(open_breakers)}"
            elif degraded_breakers:
                status = HealthStatus.DEGRADED
                message = f"Circuit breakers degraded: {', '.join(degraded_breakers)}"
            else:
                status = HealthStatus.HEALTHY
                message = f"All {len(breakers)} circuit breakers healthy"
            
            return HealthCheck(
                name="circuit_breakers",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheck(
                name="circuit_breakers",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check circuit breakers: {e}"
            )
    
    def _check_performance_metrics(self) -> HealthCheck:
        """Check performance metrics for anomalies"""
        try:
            metrics = get_performance_metrics()
            
            if not metrics:
                return HealthCheck(
                    name="performance_metrics",
                    status=HealthStatus.HEALTHY,
                    message="No performance data available"
                )
            
            slow_operations = []
            failing_operations = []
            
            details = {}
            
            for operation, stats in metrics.items():
                details[operation] = {
                    'avg_duration': stats.get('avg_duration', 0),
                    'success_rate': stats.get('success_rate', 1.0),
                    'total_calls': stats.get('total_calls', 0)
                }
                
                # Check for slow operations (>30s average)
                if stats.get('avg_duration', 0) > 30:
                    slow_operations.append(operation)
                
                # Check for failing operations (<70% success rate)
                if stats.get('success_rate', 1.0) < 0.7:
                    failing_operations.append(operation)
            
            # Determine status
            if failing_operations:
                status = HealthStatus.UNHEALTHY
                message = f"Operations with low success rate: {', '.join(failing_operations)}"
            elif slow_operations:
                status = HealthStatus.DEGRADED
                message = f"Slow operations detected: {', '.join(slow_operations)}"
            else:
                status = HealthStatus.HEALTHY
                message = f"Performance metrics normal for {len(metrics)} operations"
            
            return HealthCheck(
                name="performance_metrics",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheck(
                name="performance_metrics",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check performance metrics: {e}"
            )
    
    def _check_configuration(self) -> HealthCheck:
        """Check configuration validity"""
        try:
            # Check required settings
            required_settings = ['youtube_api_key', 'llm_api_key']
            missing_settings = []
            
            for setting in required_settings:
                value = getattr(self.settings, setting, None)
                if not value or value == 'your_api_key_here':
                    missing_settings.append(setting)
            
            details = {
                'environment': self.settings.environment,
                'debug': self.settings.debug,
                'use_mock_llm': self.settings.use_mock_llm,
                'log_level': self.settings.log_level
            }
            
            if missing_settings:
                status = HealthStatus.UNHEALTHY
                message = f"Missing required configuration: {', '.join(missing_settings)}"
            elif self.settings.use_mock_llm and self.settings.is_production:
                status = HealthStatus.DEGRADED
                message = "Using mock LLM in production environment"
            else:
                status = HealthStatus.HEALTHY
                message = "Configuration valid"
            
            return HealthCheck(
                name="configuration",
                status=status,
                message=message,
                details=details
            )
            
        except Exception as e:
            return HealthCheck(
                name="configuration",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check configuration: {e}"
            )


# Global health checker instance
health_checker = HealthChecker()


async def check_health() -> Dict[str, Any]:
    """
    Run health checks and return status.
    
    Returns:
        Health status dictionary
    """
    results = await health_checker.run_all_checks()
    overall_status = health_checker.get_overall_status(results)
    
    return {
        'status': overall_status.value,
        'timestamp': datetime.now().isoformat(),
        'checks': [asdict(check) for check in results],
        'summary': {
            'total_checks': len(results),
            'healthy': sum(1 for c in results if c.status == HealthStatus.HEALTHY),
            'degraded': sum(1 for c in results if c.status == HealthStatus.DEGRADED),
            'unhealthy': sum(1 for c in results if c.status == HealthStatus.UNHEALTHY)
        }
    }


def get_health_checker() -> HealthChecker:
    """Get the global health checker instance"""
    return health_checker


async def monitor_health(interval: int = 60):
    """
    Continuous health monitoring.
    
    Args:
        interval: Check interval in seconds
    """
    logger.info(f"Starting health monitoring with {interval}s interval")
    
    while True:
        try:
            health_status = await check_health()
            
            # Log health status
            if health_status['status'] == 'healthy':
                logger.info("System health check: HEALTHY")
            elif health_status['status'] == 'degraded':
                logger.warning("System health check: DEGRADED")
            else:
                logger.error("System health check: UNHEALTHY")
            
            # Log detailed status for non-healthy states
            if health_status['status'] != 'healthy':
                logger.info(f"Health details: {json.dumps(health_status, indent=2)}")
            
        except Exception as e:
            logger.error(f"Health monitoring error: {e}")
        
        await asyncio.sleep(interval)


if __name__ == "__main__":
    # CLI interface for health checks
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "monitor":
        # Run continuous monitoring
        asyncio.run(monitor_health())
    else:
        # Run single health check
        result = asyncio.run(check_health())
        print(json.dumps(result, indent=2))
        
        # Exit with error code if unhealthy
        if result['status'] == 'unhealthy':
            sys.exit(1)
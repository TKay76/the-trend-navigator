"""Real-time monitoring scheduler system"""

import asyncio
import logging
from typing import Optional, Callable, Dict, Any
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .settings import get_settings
from .logging import get_logger

logger = get_logger(__name__)


class MonitoringScheduler:
    """
    Real-time monitoring scheduler for YouTube Shorts trend analysis.
    
    Manages periodic data collection, trend detection, and notification tasks.
    """
    
    def __init__(self):
        """Initialize monitoring scheduler"""
        self.settings = get_settings()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.tasks = {}
        
        # Monitoring statistics
        self.stats = {
            "scheduler_started": None,
            "total_jobs_executed": 0,
            "failed_jobs": 0,
            "last_execution": None,
            "next_execution": None,
            "chart_collections": 0,
            "last_chart_collection": None
        }
        
        logger.info("Monitoring scheduler initialized")
    
    async def start(self):
        """Start the monitoring scheduler"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
        
        try:
            # Configure default monitoring job
            if self.settings.monitoring_enabled:
                await self.setup_monitoring_jobs()
            
            self.scheduler.start()
            self.is_running = True
            self.stats["scheduler_started"] = datetime.now()
            
            logger.info("Monitoring scheduler started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start monitoring scheduler: {e}")
            raise
    
    async def stop(self):
        """Stop the monitoring scheduler"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=True)
            self.is_running = False
            
            logger.info("Monitoring scheduler stopped")
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring scheduler: {e}")
            raise
    
    async def setup_monitoring_jobs(self):
        """Setup default monitoring jobs"""
        # Main trend monitoring job
        self.add_periodic_job(
            func=self._run_trend_monitoring,
            job_id="trend_monitoring",
            minutes=self.settings.monitoring_interval_minutes,
            description="Main trend monitoring task"
        )
        
        # Daily cleanup job
        self.add_cron_job(
            func=self._run_daily_cleanup,
            job_id="daily_cleanup",
            hour=2,
            minute=0,
            description="Daily data cleanup task"
        )
        
        # Weekly trend analysis job
        self.add_cron_job(
            func=self._run_weekly_analysis,
            job_id="weekly_analysis",
            day_of_week="mon",
            hour=9,
            minute=0,
            description="Weekly trend analysis task"
        )
        
        # Add chart collection job
        self.add_cron_job(
            func=self._run_chart_collection,
            job_id="daily_chart_collection",
            hour=10,
            minute=0,
            description="Daily chart data collection"
        )
        
        logger.info("Default monitoring jobs configured")
    
    def add_periodic_job(
        self,
        func: Callable,
        job_id: str,
        minutes: int,
        description: str = "",
        max_instances: int = 1
    ):
        """
        Add a periodic job to the scheduler.
        
        Args:
            func: Function to execute
            job_id: Unique job identifier
            minutes: Interval in minutes
            description: Job description
            max_instances: Maximum concurrent instances
        """
        trigger = IntervalTrigger(minutes=minutes)
        
        job = self.scheduler.add_job(
            func=self._job_wrapper(func, job_id),
            trigger=trigger,
            id=job_id,
            max_instances=max_instances,
            replace_existing=True
        )
        
        self.tasks[job_id] = {
            "job": job,
            "description": description,
            "type": "periodic",
            "interval_minutes": minutes,
            "added_at": datetime.now(),
            "last_run": None,
            "run_count": 0,
            "error_count": 0
        }
        
        logger.info(f"Added periodic job '{job_id}': {description} (every {minutes} minutes)")
    
    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        hour: int,
        minute: int = 0,
        day_of_week: Optional[str] = None,
        description: str = "",
        max_instances: int = 1
    ):
        """
        Add a cron-style job to the scheduler.
        
        Args:
            func: Function to execute
            job_id: Unique job identifier
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            day_of_week: Day of week (optional)
            description: Job description
            max_instances: Maximum concurrent instances
        """
        trigger = CronTrigger(
            hour=hour,
            minute=minute,
            day_of_week=day_of_week
        )
        
        job = self.scheduler.add_job(
            func=self._job_wrapper(func, job_id),
            trigger=trigger,
            id=job_id,
            max_instances=max_instances,
            replace_existing=True
        )
        
        self.tasks[job_id] = {
            "job": job,
            "description": description,
            "type": "cron",
            "schedule": f"{hour:02d}:{minute:02d}" + (f" ({day_of_week})" if day_of_week else ""),
            "added_at": datetime.now(),
            "last_run": None,
            "run_count": 0,
            "error_count": 0
        }
        
        logger.info(f"Added cron job '{job_id}': {description} ({trigger})")
    
    def remove_job(self, job_id: str):
        """Remove a job from the scheduler"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self.tasks:
                del self.tasks[job_id]
            logger.info(f"Removed job '{job_id}'")
        except Exception as e:
            logger.error(f"Failed to remove job '{job_id}': {e}")
    
    def _job_wrapper(self, func: Callable, job_id: str):
        """Wrapper for job execution with error handling and statistics"""
        async def wrapper():
            start_time = datetime.now()
            
            try:
                logger.info(f"Starting job '{job_id}'")
                
                # Execute the job function
                if asyncio.iscoroutinefunction(func):
                    await func()
                else:
                    func()
                
                # Update statistics
                self.stats["total_jobs_executed"] += 1
                self.stats["last_execution"] = start_time
                
                if job_id in self.tasks:
                    self.tasks[job_id]["last_run"] = start_time
                    self.tasks[job_id]["run_count"] += 1
                
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.info(f"Job '{job_id}' completed in {execution_time:.2f} seconds")
                
            except Exception as e:
                logger.error(f"Job '{job_id}' failed: {e}")
                
                # Update error statistics
                self.stats["failed_jobs"] += 1
                if job_id in self.tasks:
                    self.tasks[job_id]["error_count"] += 1
                
                # Don't re-raise to prevent scheduler from stopping
        
        return wrapper
    
    async def _run_trend_monitoring(self):
        """Main trend monitoring task"""
        logger.info("Running trend monitoring task")
        
        try:
            # Import here to avoid circular imports
            from ..services.trend_detector import TrendDetector
            from ..services.notification_service import NotificationService
            
            # Initialize services
            trend_detector = TrendDetector()
            notification_service = NotificationService()
            
            # Run trend detection
            trends = await trend_detector.detect_trends()
            
            # Send notifications if trends found
            if trends:
                await notification_service.send_trend_alerts(trends)
            
            logger.info(f"Trend monitoring completed: {len(trends)} trends detected")
            
        except Exception as e:
            logger.error(f"Trend monitoring failed: {e}")
            raise
    
    async def _run_daily_cleanup(self):
        """Daily cleanup task"""
        logger.info("Running daily cleanup task")
        
        try:
            # Import here to avoid circular imports
            from ..services.trend_storage import TrendStorage
            
            storage = TrendStorage()
            await storage.cleanup_old_data()
            
            logger.info("Daily cleanup completed")
            
        except Exception as e:
            logger.error(f"Daily cleanup failed: {e}")
            raise
    
    async def _run_chart_collection(self):
        """Daily chart data collection task"""
        logger.info("Running daily chart collection task")
        
        try:
            # Import here to avoid circular imports
            from ..agents.collector_agent import CollectorAgent
            from ..models.video_models import ChartHistoryRequest
            
            # Initialize collector agent
            collector = CollectorAgent()
            
            # Collect Korean daily charts
            chart_request = ChartHistoryRequest(
                region="kr",
                chart_type="daily",
                days=1
            )
            
            chart_data = await collector.collect_chart_data(
                region=chart_request.region,
                chart_type=chart_request.chart_type,
                days=chart_request.days
            )
            
            # Update statistics
            self.stats["chart_collections"] += 1
            self.stats["last_chart_collection"] = datetime.now()
            
            logger.info(f"Chart collection completed: {chart_data.total_songs} songs collected")
            
        except Exception as e:
            logger.error(f"Chart collection failed: {e}")
            raise
    
    async def _run_weekly_analysis(self):
        """Weekly trend analysis task"""
        logger.info("Running weekly trend analysis task")
        
        try:
            # Import here to avoid circular imports
            from ..services.trend_detector import TrendDetector
            from ..services.notification_service import NotificationService
            
            trend_detector = TrendDetector()
            notification_service = NotificationService()
            
            # Generate weekly report
            report = await trend_detector.generate_weekly_report()
            
            # Send weekly report
            await notification_service.send_weekly_report(report)
            
            logger.info("Weekly trend analysis completed")
            
        except Exception as e:
            logger.error(f"Weekly trend analysis failed: {e}")
            raise
    
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific job"""
        if job_id not in self.tasks:
            return None
        
        task = self.tasks[job_id]
        job = task["job"]
        
        return {
            "job_id": job_id,
            "description": task["description"],
            "type": task["type"],
            "schedule": task.get("schedule", f"Every {task.get('interval_minutes', 0)} minutes"),
            "added_at": task["added_at"],
            "last_run": task["last_run"],
            "next_run": job.next_run_time,
            "run_count": task["run_count"],
            "error_count": task["error_count"],
            "is_running": self.is_running
        }
    
    def get_all_jobs_status(self) -> Dict[str, Any]:
        """Get status of all jobs"""
        return {
            "scheduler_running": self.is_running,
            "total_jobs": len(self.tasks),
            "statistics": self.stats,
            "jobs": {
                job_id: self.get_job_status(job_id)
                for job_id in self.tasks
            }
        }


# Global scheduler instance
_scheduler = None


def get_scheduler() -> MonitoringScheduler:
    """Get the global monitoring scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = MonitoringScheduler()
    return _scheduler


async def start_monitoring():
    """Start the monitoring scheduler"""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_monitoring():
    """Stop the monitoring scheduler"""
    scheduler = get_scheduler()
    await scheduler.stop()
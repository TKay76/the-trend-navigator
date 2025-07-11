"""API routes for real-time monitoring and trend management"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from ..core.scheduler import get_scheduler
from ..services.trend_detector import TrendDetector
from ..services.trend_storage import get_trend_storage
from ..services.notification_service import get_notification_service
from ..core.settings import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# Pydantic models for API responses
class MonitoringStatus(BaseModel):
    """Monitoring system status"""
    monitoring_enabled: bool
    scheduler_running: bool
    last_detection: Optional[datetime]
    next_scheduled_run: Optional[datetime]
    total_trends_detected: int
    total_alerts_sent: int
    
    
class TrendAlertResponse(BaseModel):
    """Trend alert response model"""
    alert_id: str
    alert_type: str
    title: str
    description: str
    video_id: str
    channel_title: str
    confidence_score: float
    detected_at: datetime
    category: str
    keywords: List[str]
    youtube_url: str
    

class MonitoringConfig(BaseModel):
    """Monitoring configuration model"""
    monitoring_enabled: bool = Field(description="Enable/disable monitoring")
    interval_minutes: int = Field(ge=5, le=1440, description="Monitoring interval (5-1440 minutes)")
    trend_threshold: float = Field(ge=1.0, le=20.0, description="Trend detection threshold")
    viral_threshold: int = Field(ge=1000, description="Viral content threshold")
    email_notifications: bool = Field(description="Enable email notifications")
    slack_notifications: bool = Field(description="Enable Slack notifications")
    discord_notifications: bool = Field(description="Enable Discord notifications")


class KeywordTrend(BaseModel):
    """Keyword trend model"""
    keyword: str
    category: str
    frequency: int
    peak_frequency: int
    first_seen: datetime
    last_seen: datetime
    trend_score: float


class CategoryAnalytics(BaseModel):
    """Category analytics model"""
    category: str
    total_alerts: int
    alert_types: Dict[str, int]
    average_confidence: float
    trend_momentum: float


@router.get("/status", response_model=MonitoringStatus)
async def get_monitoring_status():
    """Get current monitoring system status"""
    try:
        settings = get_settings()
        scheduler = get_scheduler()
        trend_detector = TrendDetector()
        notification_service = get_notification_service()
        
        # Get scheduler status
        scheduler_status = scheduler.get_all_jobs_status()
        
        # Get trend detector stats
        detector_stats = trend_detector.get_stats()
        
        # Get notification stats
        notification_stats = await notification_service.get_notification_stats()
        
        return MonitoringStatus(
            monitoring_enabled=settings.monitoring_enabled,
            scheduler_running=scheduler_status["scheduler_running"],
            last_detection=detector_stats["detector_stats"]["last_detection"],
            next_scheduled_run=scheduler_status["statistics"]["next_execution"],
            total_trends_detected=detector_stats["detector_stats"]["trends_detected"],
            total_alerts_sent=notification_stats["total_notifications_sent"]
        )
        
    except Exception as e:
        logger.error(f"Failed to get monitoring status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get monitoring status")


@router.post("/start")
async def start_monitoring(background_tasks: BackgroundTasks):
    """Start the monitoring system"""
    try:
        settings = get_settings()
        
        if not settings.monitoring_enabled:
            raise HTTPException(
                status_code=400, 
                detail="Monitoring is disabled in settings. Set MONITORING_ENABLED=true to enable."
            )
        
        scheduler = get_scheduler()
        
        # Start scheduler in background
        background_tasks.add_task(scheduler.start)
        
        logger.info("Monitoring system start initiated")
        
        return {"message": "Monitoring system started successfully", "status": "starting"}
        
    except Exception as e:
        logger.error(f"Failed to start monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start monitoring: {e}")


@router.post("/stop")
async def stop_monitoring():
    """Stop the monitoring system"""
    try:
        scheduler = get_scheduler()
        await scheduler.stop()
        
        logger.info("Monitoring system stopped")
        
        return {"message": "Monitoring system stopped successfully", "status": "stopped"}
        
    except Exception as e:
        logger.error(f"Failed to stop monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to stop monitoring: {e}")


@router.post("/trigger")
async def trigger_trend_detection(background_tasks: BackgroundTasks):
    """Manually trigger trend detection"""
    try:
        async def run_detection():
            trend_detector = TrendDetector()
            notification_service = get_notification_service()
            storage = await get_trend_storage()
            
            # Run trend detection
            alerts = await trend_detector.detect_trends()
            
            # Store alerts
            if alerts:
                await storage.store_trend_alerts(alerts)
                
                # Send notifications
                await notification_service.send_trend_alerts(alerts)
            
            logger.info(f"Manual trend detection completed: {len(alerts)} alerts generated")
        
        background_tasks.add_task(run_detection)
        
        return {"message": "Trend detection triggered", "status": "running"}
        
    except Exception as e:
        logger.error(f"Failed to trigger trend detection: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger trend detection: {e}")


@router.get("/alerts", response_model=List[TrendAlertResponse])
async def get_recent_alerts(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to look back (1-168)"),
    alert_type: Optional[str] = Query(default=None, description="Filter by alert type"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum number of alerts to return")
):
    """Get recent trend alerts"""
    try:
        storage = await get_trend_storage()
        
        # Get alerts from storage
        alerts = await storage.get_recent_alerts(hours=hours, alert_type=alert_type)
        
        # Limit results
        alerts = alerts[:limit]
        
        # Convert to response format
        response_alerts = []
        for alert in alerts:
            response_alerts.append(TrendAlertResponse(
                alert_id=alert["alert_id"],
                alert_type=alert["alert_type"],
                title=alert["title"],
                description=alert["description"],
                video_id=alert["video_id"],
                channel_title=alert["channel_title"],
                confidence_score=alert["confidence_score"],
                detected_at=alert["detected_at"],
                category=alert["category"],
                keywords=alert["keywords"],
                youtube_url=alert["youtube_url"]
            ))
        
        return response_alerts
        
    except Exception as e:
        logger.error(f"Failed to get recent alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to get recent alerts")


@router.get("/keywords", response_model=List[KeywordTrend])
async def get_trending_keywords(
    days: int = Query(default=7, ge=1, le=30, description="Days to analyze (1-30)"),
    limit: int = Query(default=20, ge=1, le=100, description="Maximum number of keywords to return")
):
    """Get trending keywords"""
    try:
        storage = await get_trend_storage()
        
        # Get keyword trends
        keywords = await storage.get_trending_keywords(days=days, limit=limit)
        
        # Convert to response format
        response_keywords = []
        for keyword in keywords:
            # Calculate trend score (simple frequency-based scoring)
            trend_score = min(1.0, keyword["frequency"] / 10.0)  # Normalize to 0-1
            
            response_keywords.append(KeywordTrend(
                keyword=keyword["keyword"],
                category=keyword["category"],
                frequency=keyword["frequency"],
                peak_frequency=keyword["peak_frequency"],
                first_seen=keyword["first_seen"],
                last_seen=keyword["last_seen"],
                trend_score=trend_score
            ))
        
        return response_keywords
        
    except Exception as e:
        logger.error(f"Failed to get trending keywords: {e}")
        raise HTTPException(status_code=500, detail="Failed to get trending keywords")


@router.get("/analytics", response_model=List[CategoryAnalytics])
async def get_category_analytics(
    days: int = Query(default=30, ge=1, le=90, description="Days to analyze (1-90)")
):
    """Get category analytics"""
    try:
        storage = await get_trend_storage()
        
        # Get category analytics
        analytics = await storage.get_category_analytics(days=days)
        
        # Convert to response format
        response_analytics = []
        for category, data in analytics.items():
            # Calculate trend momentum (simple metric based on activity)
            trend_momentum = min(1.0, data["total_alerts"] / 20.0)  # Normalize to 0-1
            
            response_analytics.append(CategoryAnalytics(
                category=category,
                total_alerts=data["total_alerts"],
                alert_types=data["alert_types"],
                average_confidence=data["average_confidence"],
                trend_momentum=trend_momentum
            ))
        
        return response_analytics
        
    except Exception as e:
        logger.error(f"Failed to get category analytics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get category analytics")


@router.get("/jobs")
async def get_scheduled_jobs():
    """Get status of all scheduled jobs"""
    try:
        scheduler = get_scheduler()
        return scheduler.get_all_jobs_status()
        
    except Exception as e:
        logger.error(f"Failed to get scheduled jobs: {e}")
        raise HTTPException(status_code=500, detail="Failed to get scheduled jobs")


@router.get("/storage/stats")
async def get_storage_stats():
    """Get storage statistics"""
    try:
        storage = await get_trend_storage()
        return await storage.get_storage_stats()
        
    except Exception as e:
        logger.error(f"Failed to get storage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage stats")


@router.post("/storage/cleanup")
async def cleanup_storage(
    days_to_keep: int = Query(default=30, ge=7, le=365, description="Days of data to keep (7-365)")
):
    """Clean up old data from storage"""
    try:
        storage = await get_trend_storage()
        await storage.cleanup_old_data(days_to_keep=days_to_keep)
        
        return {"message": f"Storage cleanup completed, kept {days_to_keep} days of data"}
        
    except Exception as e:
        logger.error(f"Failed to cleanup storage: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup storage")


@router.post("/storage/export")
async def export_data(
    days: int = Query(default=30, ge=1, le=365, description="Days of data to export (1-365)")
):
    """Export trend data to JSON file"""
    try:
        storage = await get_trend_storage()
        
        # Generate export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"data/trends_export_{timestamp}.json"
        
        # Export data
        success = await storage.export_data(export_path, days=days)
        
        if success:
            return {"message": f"Data exported successfully to {export_path}", "file_path": export_path}
        else:
            raise HTTPException(status_code=500, detail="Failed to export data")
            
    except Exception as e:
        logger.error(f"Failed to export data: {e}")
        raise HTTPException(status_code=500, detail="Failed to export data")


@router.post("/notifications/test")
async def test_notifications():
    """Test notification channels"""
    try:
        notification_service = get_notification_service()
        results = await notification_service.test_notifications()
        
        return {
            "message": "Notification test completed",
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Failed to test notifications: {e}")
        raise HTTPException(status_code=500, detail="Failed to test notifications")


@router.get("/notifications/stats")
async def get_notification_stats():
    """Get notification statistics"""
    try:
        notification_service = get_notification_service()
        return await notification_service.get_notification_stats()
        
    except Exception as e:
        logger.error(f"Failed to get notification stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get notification stats")


@router.get("/dashboard/data")
async def get_dashboard_data():
    """Get comprehensive dashboard data"""
    try:
        # Get data from all services
        storage = await get_trend_storage()
        notification_service = get_notification_service()
        trend_detector = TrendDetector()
        scheduler = get_scheduler()
        
        # Collect dashboard data
        dashboard_data = {
            "timestamp": datetime.now(),
            "monitoring_status": {
                "enabled": get_settings().monitoring_enabled,
                "scheduler_running": scheduler.is_running,
                "last_detection": None
            },
            "recent_alerts": await storage.get_recent_alerts(hours=24),
            "trending_keywords": await storage.get_trending_keywords(days=7, limit=10),
            "category_analytics": await storage.get_category_analytics(days=30),
            "storage_stats": await storage.get_storage_stats(),
            "notification_stats": await notification_service.get_notification_stats(),
            "detector_stats": trend_detector.get_stats()
        }
        
        return dashboard_data
        
    except Exception as e:
        logger.error(f"Failed to get dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Failed to get dashboard data")


@router.get("/health")
async def monitoring_health_check():
    """Health check for monitoring system"""
    try:
        settings = get_settings()
        scheduler = get_scheduler()
        
        # Check if monitoring is enabled
        if not settings.monitoring_enabled:
            return {
                "status": "disabled",
                "message": "Monitoring is disabled in settings"
            }
        
        # Check scheduler status
        if not scheduler.is_running:
            return {
                "status": "stopped",
                "message": "Monitoring scheduler is not running"
            }
        
        # Check database connectivity
        try:
            storage = await get_trend_storage()
            await storage.get_storage_stats()
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connectivity issue: {e}"
            }
        
        return {
            "status": "healthy",
            "message": "Monitoring system is running normally"
        }
        
    except Exception as e:
        logger.error(f"Monitoring health check failed: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {e}"
        }
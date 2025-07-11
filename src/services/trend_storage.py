"""Trend data storage and management system"""

import asyncio
import logging
import json
import aiosqlite
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path

from .trend_detector import TrendAlert
from ..core.settings import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class TrendStorage:
    """
    Lightweight SQLite-based storage system for trend data.
    
    Manages trend alerts, historical data, and analytics storage.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize trend storage.
        
        Args:
            db_path: Path to SQLite database file (optional)
        """
        self.settings = get_settings()
        
        # Set database path
        if db_path:
            self.db_path = db_path
        else:
            # Create data directory if it doesn't exist
            data_dir = Path("data")
            data_dir.mkdir(exist_ok=True)
            self.db_path = data_dir / "trends.db"
        
        # Storage statistics
        self.stats = {
            "total_alerts_stored": 0,
            "database_size_mb": 0,
            "last_cleanup": None,
            "oldest_record": None,
            "newest_record": None
        }
        
        logger.info(f"Trend storage initialized with database: {self.db_path}")
    
    async def initialize(self):
        """Initialize database tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await self._create_tables(db)
            
            # Update statistics
            await self._update_stats()
            
            logger.info("Trend storage database initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize trend storage: {e}")
            raise
    
    async def _create_tables(self, db: aiosqlite.Connection):
        """Create database tables"""
        # Trend alerts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trend_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id TEXT UNIQUE NOT NULL,
                alert_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                video_id TEXT NOT NULL,
                channel_title TEXT,
                current_stats TEXT,  -- JSON
                growth_metrics TEXT,  -- JSON
                confidence_score REAL,
                detected_at TIMESTAMP,
                category TEXT,
                keywords TEXT,  -- JSON array
                youtube_url TEXT,
                thumbnail_url TEXT,
                processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Trend history table for tracking performance over time
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trend_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                engagement_rate REAL,
                growth_rate REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Keyword trends table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS keyword_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                category TEXT,
                frequency INTEGER DEFAULT 1,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                peak_frequency INTEGER DEFAULT 1,
                peak_date TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Monitoring metrics table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitoring_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_type TEXT NOT NULL,
                metric_value REAL,
                metric_data TEXT,  -- JSON
                recorded_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_detected_at ON trend_alerts(detected_at)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_video_id ON trend_alerts(video_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON trend_alerts(alert_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_history_video_id ON trend_history(video_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_history_timestamp ON trend_history(timestamp)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_keywords_keyword ON keyword_trends(keyword)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_type ON monitoring_metrics(metric_type)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_metrics_recorded_at ON monitoring_metrics(recorded_at)")
        
        await db.commit()
    
    async def store_trend_alert(self, alert: TrendAlert) -> bool:
        """
        Store a trend alert in the database.
        
        Args:
            alert: TrendAlert object to store
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO trend_alerts (
                        alert_id, alert_type, title, description, video_id, channel_title,
                        current_stats, growth_metrics, confidence_score, detected_at,
                        category, keywords, youtube_url, thumbnail_url
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    alert.alert_id,
                    alert.alert_type,
                    alert.title,
                    alert.description,
                    alert.video_id,
                    alert.channel_title,
                    json.dumps(alert.current_stats),
                    json.dumps(alert.growth_metrics),
                    alert.confidence_score,
                    alert.detected_at,
                    alert.category,
                    json.dumps(alert.keywords),
                    alert.youtube_url,
                    alert.thumbnail_url
                ))
                
                await db.commit()
                
                # Update keyword trends
                await self._update_keyword_trends(db, alert.keywords, alert.category)
                
                self.stats["total_alerts_stored"] += 1
                logger.info(f"Stored trend alert: {alert.alert_id}")
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to store trend alert {alert.alert_id}: {e}")
            return False
    
    async def store_trend_alerts(self, alerts: List[TrendAlert]) -> int:
        """
        Store multiple trend alerts.
        
        Args:
            alerts: List of TrendAlert objects
            
        Returns:
            int: Number of alerts stored successfully
        """
        stored_count = 0
        
        for alert in alerts:
            if await self.store_trend_alert(alert):
                stored_count += 1
        
        logger.info(f"Stored {stored_count}/{len(alerts)} trend alerts")
        return stored_count
    
    async def _update_keyword_trends(self, db: aiosqlite.Connection, keywords: List[str], category: str):
        """Update keyword trends tracking"""
        current_time = datetime.now()
        
        for keyword in keywords:
            # Check if keyword exists
            cursor = await db.execute(
                "SELECT id, frequency, peak_frequency FROM keyword_trends WHERE keyword = ? AND category = ?",
                (keyword, category)
            )
            row = await cursor.fetchone()
            
            if row:
                # Update existing keyword
                keyword_id, frequency, peak_frequency = row
                new_frequency = frequency + 1
                new_peak = max(peak_frequency, new_frequency)
                
                await db.execute("""
                    UPDATE keyword_trends 
                    SET frequency = ?, last_seen = ?, peak_frequency = ?, peak_date = ?
                    WHERE id = ?
                """, (new_frequency, current_time, new_peak, current_time, keyword_id))
            else:
                # Insert new keyword
                await db.execute("""
                    INSERT INTO keyword_trends (keyword, category, frequency, first_seen, last_seen, peak_frequency, peak_date)
                    VALUES (?, ?, 1, ?, ?, 1, ?)
                """, (keyword, category, current_time, current_time, current_time))
    
    async def get_recent_alerts(self, hours: int = 24, alert_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get recent trend alerts.
        
        Args:
            hours: Number of hours to look back
            alert_type: Filter by alert type (optional)
            
        Returns:
            List of alert dictionaries
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                query = """
                    SELECT * FROM trend_alerts 
                    WHERE detected_at > ? 
                """
                params = [cutoff_time]
                
                if alert_type:
                    query += " AND alert_type = ?"
                    params.append(alert_type)
                
                query += " ORDER BY detected_at DESC"
                
                cursor = await db.execute(query, params)
                rows = await cursor.fetchall()
                
                alerts = []
                for row in rows:
                    alert = dict(row)
                    # Parse JSON fields
                    alert['current_stats'] = json.loads(alert['current_stats'] or '{}')
                    alert['growth_metrics'] = json.loads(alert['growth_metrics'] or '{}')
                    alert['keywords'] = json.loads(alert['keywords'] or '[]')
                    alerts.append(alert)
                
                logger.info(f"Retrieved {len(alerts)} recent alerts (last {hours} hours)")
                return alerts
                
        except Exception as e:
            logger.error(f"Failed to get recent alerts: {e}")
            return []
    
    async def get_trending_keywords(self, days: int = 7, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get trending keywords from the past period.
        
        Args:
            days: Number of days to analyze
            limit: Maximum number of keywords to return
            
        Returns:
            List of keyword trend data
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                cursor = await db.execute("""
                    SELECT keyword, category, frequency, peak_frequency, first_seen, last_seen, peak_date
                    FROM keyword_trends 
                    WHERE last_seen > ? 
                    ORDER BY frequency DESC 
                    LIMIT ?
                """, (cutoff_time, limit))
                
                rows = await cursor.fetchall()
                
                keywords = [dict(row) for row in rows]
                
                logger.info(f"Retrieved {len(keywords)} trending keywords (last {days} days)")
                return keywords
                
        except Exception as e:
            logger.error(f"Failed to get trending keywords: {e}")
            return []
    
    async def get_category_analytics(self, days: int = 30) -> Dict[str, Any]:
        """
        Get analytics by category.
        
        Args:
            days: Number of days to analyze
            
        Returns:
            Category analytics data
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Get alerts by category
                cursor = await db.execute("""
                    SELECT category, alert_type, COUNT(*) as count, AVG(confidence_score) as avg_confidence
                    FROM trend_alerts 
                    WHERE detected_at > ? 
                    GROUP BY category, alert_type
                    ORDER BY count DESC
                """, (cutoff_time,))
                
                rows = await cursor.fetchall()
                
                analytics = {}
                for row in rows:
                    category = row['category']
                    if category not in analytics:
                        analytics[category] = {
                            'total_alerts': 0,
                            'alert_types': {},
                            'average_confidence': 0.0
                        }
                    
                    analytics[category]['total_alerts'] += row['count']
                    analytics[category]['alert_types'][row['alert_type']] = row['count']
                    analytics[category]['average_confidence'] = row['avg_confidence']
                
                logger.info(f"Retrieved analytics for {len(analytics)} categories (last {days} days)")
                return analytics
                
        except Exception as e:
            logger.error(f"Failed to get category analytics: {e}")
            return {}
    
    async def store_monitoring_metric(self, metric_type: str, value: float, data: Optional[Dict[str, Any]] = None):
        """
        Store a monitoring metric.
        
        Args:
            metric_type: Type of metric
            value: Metric value
            data: Additional metric data (optional)
        """
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO monitoring_metrics (metric_type, metric_value, metric_data, recorded_at)
                    VALUES (?, ?, ?, ?)
                """, (metric_type, value, json.dumps(data or {}), datetime.now()))
                
                await db.commit()
                
        except Exception as e:
            logger.error(f"Failed to store monitoring metric: {e}")
    
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """
        Clean up old data from the database.
        
        Args:
            days_to_keep: Number of days of data to keep
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days_to_keep)
            
            async with aiosqlite.connect(self.db_path) as db:
                # Clean up old alerts
                cursor = await db.execute(
                    "DELETE FROM trend_alerts WHERE detected_at < ?", 
                    (cutoff_time,)
                )
                alerts_deleted = cursor.rowcount
                
                # Clean up old history
                cursor = await db.execute(
                    "DELETE FROM trend_history WHERE timestamp < ?", 
                    (cutoff_time,)
                )
                history_deleted = cursor.rowcount
                
                # Clean up old metrics
                cursor = await db.execute(
                    "DELETE FROM monitoring_metrics WHERE recorded_at < ?", 
                    (cutoff_time,)
                )
                metrics_deleted = cursor.rowcount
                
                await db.commit()
                
                # Vacuum database to reclaim space
                await db.execute("VACUUM")
                
                self.stats["last_cleanup"] = datetime.now()
                
                logger.info(f"Cleanup completed: {alerts_deleted} alerts, {history_deleted} history, {metrics_deleted} metrics deleted")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    async def _update_stats(self):
        """Update storage statistics"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Count total alerts
                cursor = await db.execute("SELECT COUNT(*) as count FROM trend_alerts")
                row = await cursor.fetchone()
                self.stats["total_alerts_stored"] = row['count']
                
                # Get date range
                cursor = await db.execute("""
                    SELECT MIN(detected_at) as oldest, MAX(detected_at) as newest 
                    FROM trend_alerts
                """)
                row = await cursor.fetchone()
                self.stats["oldest_record"] = row['oldest']
                self.stats["newest_record"] = row['newest']
                
                # Get database size
                db_size_bytes = Path(self.db_path).stat().st_size
                self.stats["database_size_mb"] = db_size_bytes / (1024 * 1024)
                
        except Exception as e:
            logger.error(f"Failed to update stats: {e}")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        await self._update_stats()
        return self.stats
    
    async def export_data(self, output_path: str, days: int = 30) -> bool:
        """
        Export trend data to JSON file.
        
        Args:
            output_path: Path to output JSON file
            days: Number of days to export
            
        Returns:
            bool: True if exported successfully
        """
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                # Export alerts
                cursor = await db.execute("""
                    SELECT * FROM trend_alerts WHERE detected_at > ?
                    ORDER BY detected_at DESC
                """, (cutoff_time,))
                
                alerts = []
                async for row in cursor:
                    alert = dict(row)
                    alert['current_stats'] = json.loads(alert['current_stats'] or '{}')
                    alert['growth_metrics'] = json.loads(alert['growth_metrics'] or '{}')
                    alert['keywords'] = json.loads(alert['keywords'] or '[]')
                    alerts.append(alert)
                
                # Export keywords
                cursor = await db.execute("""
                    SELECT * FROM keyword_trends WHERE last_seen > ?
                    ORDER BY frequency DESC
                """, (cutoff_time,))
                
                keywords = [dict(row) async for row in cursor]
                
                # Create export data
                export_data = {
                    "exported_at": datetime.now().isoformat(),
                    "period_days": days,
                    "statistics": await self.get_storage_stats(),
                    "alerts": alerts,
                    "keywords": keywords
                }
                
                # Write to file
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, default=str)
                
                logger.info(f"Exported {len(alerts)} alerts and {len(keywords)} keywords to {output_path}")
                return True
                
        except Exception as e:
            logger.error(f"Failed to export data: {e}")
            return False


# Global storage instance
_storage = None


async def get_trend_storage() -> TrendStorage:
    """Get the global trend storage instance"""
    global _storage
    if _storage is None:
        _storage = TrendStorage()
        await _storage.initialize()
    return _storage
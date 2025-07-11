"""Trend detection engine for YouTube Shorts analysis"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass

from ..agents.collector_agent import create_collector_agent
from ..agents.analyzer_agent import create_analyzer_agent
from ..models.video_models import YouTubeVideoRaw, ClassifiedVideo
from ..core.settings import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TrendAlert:
    """Trend alert data structure"""
    alert_id: str
    alert_type: str  # 'viral', 'rising', 'new_trend', 'category_spike'
    title: str
    description: str
    video_id: str
    channel_title: str
    current_stats: Dict[str, Any]
    growth_metrics: Dict[str, Any]
    confidence_score: float
    detected_at: datetime
    category: str
    keywords: List[str]
    youtube_url: str
    thumbnail_url: str


class TrendDetector:
    """
    Intelligent trend detection engine for YouTube Shorts.
    
    Analyzes video performance metrics, growth patterns, and content patterns
    to identify viral content, rising trends, and emerging topics.
    """
    
    def __init__(self):
        """Initialize trend detector"""
        self.settings = get_settings()
        self.collector_agent = None
        self.analyzer_agent = None
        
        # Detection parameters
        self.viral_threshold = self.settings.viral_threshold
        self.growth_threshold = self.settings.trend_detection_threshold
        
        # Trend detection statistics
        self.stats = {
            "trends_detected": 0,
            "alerts_sent": 0,
            "last_detection": None,
            "detection_accuracy": 0.0
        }
        
        logger.info("Trend detector initialized")
    
    async def detect_trends(self) -> List[TrendAlert]:
        """
        Main trend detection method.
        
        Returns:
            List of trend alerts detected
        """
        logger.info("Starting trend detection analysis")
        
        try:
            # Initialize agents
            if not self.collector_agent:
                self.collector_agent = create_collector_agent()
            if not self.analyzer_agent:
                self.analyzer_agent = create_analyzer_agent()
            
            # Collect recent trending videos
            trending_videos = await self._collect_trending_videos()
            
            if not trending_videos:
                logger.warning("No trending videos collected")
                return []
            
            # Analyze videos for classification
            classified_videos = await self._classify_videos(trending_videos)
            
            # Detect different types of trends
            alerts = []
            
            # Viral content detection
            viral_alerts = await self._detect_viral_content(classified_videos)
            alerts.extend(viral_alerts)
            
            # Rising trends detection
            rising_alerts = await self._detect_rising_trends(classified_videos)
            alerts.extend(rising_alerts)
            
            # New trend detection
            new_trend_alerts = await self._detect_new_trends(classified_videos)
            alerts.extend(new_trend_alerts)
            
            # Category spikes detection
            category_spike_alerts = await self._detect_category_spikes(classified_videos)
            alerts.extend(category_spike_alerts)
            
            # Update statistics
            self.stats["trends_detected"] += len(alerts)
            self.stats["last_detection"] = datetime.now()
            
            logger.info(f"Trend detection completed: {len(alerts)} alerts generated")
            
            return alerts
            
        except Exception as e:
            logger.error(f"Trend detection failed: {e}")
            raise
    
    async def _collect_trending_videos(self) -> List[YouTubeVideoRaw]:
        """Collect recent trending videos"""
        logger.info("Collecting trending videos")
        
        try:
            # Define search queries for different categories
            search_queries = [
                "shorts trending",
                "viral shorts",
                "dance challenge",
                "fitness shorts",
                "cooking shorts",
                "comedy shorts",
                "tutorial shorts"
            ]
            
            # Collect videos from the last 24 hours
            videos = await self.collector_agent.collect_top_videos(
                search_queries=search_queries,
                max_results_per_query=50,
                max_daily_quota=self.settings.max_daily_quota // 2,  # Reserve half quota for monitoring
                published_after_days=1  # Last 24 hours
            )
            
            logger.info(f"Collected {len(videos)} trending videos")
            return videos
            
        except Exception as e:
            logger.error(f"Failed to collect trending videos: {e}")
            raise
    
    async def _classify_videos(self, videos: List[YouTubeVideoRaw]) -> List[ClassifiedVideo]:
        """Classify collected videos"""
        logger.info(f"Classifying {len(videos)} videos")
        
        try:
            classified_videos = await self.analyzer_agent.classify_videos(videos)
            logger.info(f"Classified {len(classified_videos)} videos")
            return classified_videos
            
        except Exception as e:
            logger.error(f"Failed to classify videos: {e}")
            raise
    
    async def _detect_viral_content(self, videos: List[ClassifiedVideo]) -> List[TrendAlert]:
        """Detect viral content based on view count and engagement"""
        alerts = []
        
        for video in videos:
            # Check if video meets viral criteria
            if video.view_count >= self.viral_threshold:
                # Calculate engagement rate
                engagement_rate = self._calculate_engagement_rate(video)
                
                # Check if video is relatively new (published within last 7 days)
                days_since_published = (datetime.now() - video.published_at).days
                
                if days_since_published <= 7 and engagement_rate > 0.05:  # 5% engagement rate
                    alert = TrendAlert(
                        alert_id=f"viral_{video.video_id}_{int(datetime.now().timestamp())}",
                        alert_type="viral",
                        title=f"🚀 Viral Content Alert: {video.title[:50]}...",
                        description=f"Video has reached {video.view_count:,} views with {engagement_rate:.2%} engagement rate in {days_since_published} days",
                        video_id=video.video_id,
                        channel_title=video.channel_title,
                        current_stats={
                            "view_count": video.view_count,
                            "like_count": video.like_count,
                            "comment_count": video.comment_count,
                            "engagement_rate": engagement_rate
                        },
                        growth_metrics={
                            "days_since_published": days_since_published,
                            "daily_view_rate": video.view_count / max(days_since_published, 1)
                        },
                        confidence_score=min(0.95, engagement_rate * 10),  # Cap at 95%
                        detected_at=datetime.now(),
                        category=video.category,
                        keywords=self._extract_keywords(video.title + " " + video.description),
                        youtube_url=f"https://youtube.com/watch?v={video.video_id}",
                        thumbnail_url=video.thumbnail_url
                    )
                    alerts.append(alert)
        
        logger.info(f"Detected {len(alerts)} viral content alerts")
        return alerts
    
    async def _detect_rising_trends(self, videos: List[ClassifiedVideo]) -> List[TrendAlert]:
        """Detect rising trends based on growth patterns"""
        alerts = []
        
        # Group videos by keywords to identify trending topics
        keyword_groups = self._group_by_keywords(videos)
        
        for keywords, group_videos in keyword_groups.items():
            if len(group_videos) >= 3:  # At least 3 videos with similar keywords
                # Calculate average growth metrics
                avg_views = sum(v.view_count for v in group_videos) / len(group_videos)
                total_engagement = sum(self._calculate_engagement_rate(v) for v in group_videos)
                
                # Check if this represents a rising trend
                if avg_views > 50000 and total_engagement > 0.1:  # Threshold for rising trend
                    # Pick the best performing video as representative
                    best_video = max(group_videos, key=lambda v: v.view_count)
                    
                    alert = TrendAlert(
                        alert_id=f"rising_{hash(keywords)}_{int(datetime.now().timestamp())}",
                        alert_type="rising",
                        title=f"📈 Rising Trend: {keywords}",
                        description=f"Trending topic with {len(group_videos)} videos, avg {avg_views:,.0f} views",
                        video_id=best_video.video_id,
                        channel_title=best_video.channel_title,
                        current_stats={
                            "related_videos": len(group_videos),
                            "average_views": avg_views,
                            "total_engagement": total_engagement,
                            "best_video_views": best_video.view_count
                        },
                        growth_metrics={
                            "trend_strength": len(group_videos) * (avg_views / 100000),
                            "engagement_momentum": total_engagement
                        },
                        confidence_score=min(0.9, len(group_videos) * 0.15),  # Based on video count
                        detected_at=datetime.now(),
                        category=best_video.category,
                        keywords=keywords.split(),
                        youtube_url=f"https://youtube.com/watch?v={best_video.video_id}",
                        thumbnail_url=best_video.thumbnail_url
                    )
                    alerts.append(alert)
        
        logger.info(f"Detected {len(alerts)} rising trend alerts")
        return alerts
    
    async def _detect_new_trends(self, videos: List[ClassifiedVideo]) -> List[TrendAlert]:
        """Detect completely new trends or formats"""
        alerts = []
        
        # Look for videos with unique patterns or unusual success
        for video in videos:
            # Check for videos with unusually high engagement relative to subscriber count
            # This could indicate a new trend or format breaking through
            
            engagement_rate = self._calculate_engagement_rate(video)
            days_since_published = (datetime.now() - video.published_at).days
            
            # New trend criteria: very high engagement on relatively new video
            if (days_since_published <= 3 and 
                engagement_rate > 0.15 and  # 15% engagement rate
                video.view_count > 10000):   # Minimum view threshold
                
                # Check if keywords are unusual or emerging
                keywords = self._extract_keywords(video.title + " " + video.description)
                novelty_score = self._calculate_novelty_score(keywords)
                
                if novelty_score > 0.7:  # High novelty score
                    alert = TrendAlert(
                        alert_id=f"new_trend_{video.video_id}_{int(datetime.now().timestamp())}",
                        alert_type="new_trend",
                        title=f"🆕 New Trend Alert: {video.title[:50]}...",
                        description=f"Emerging trend with {engagement_rate:.2%} engagement in {days_since_published} days",
                        video_id=video.video_id,
                        channel_title=video.channel_title,
                        current_stats={
                            "view_count": video.view_count,
                            "engagement_rate": engagement_rate,
                            "novelty_score": novelty_score
                        },
                        growth_metrics={
                            "days_since_published": days_since_published,
                            "rapid_growth_rate": video.view_count / max(days_since_published, 1)
                        },
                        confidence_score=min(0.85, novelty_score * engagement_rate * 5),
                        detected_at=datetime.now(),
                        category=video.category,
                        keywords=keywords,
                        youtube_url=f"https://youtube.com/watch?v={video.video_id}",
                        thumbnail_url=video.thumbnail_url
                    )
                    alerts.append(alert)
        
        logger.info(f"Detected {len(alerts)} new trend alerts")
        return alerts
    
    async def _detect_category_spikes(self, videos: List[ClassifiedVideo]) -> List[TrendAlert]:
        """Detect unusual activity spikes in specific categories"""
        alerts = []
        
        # Group videos by category
        category_groups = {}
        for video in videos:
            category = video.category
            if category not in category_groups:
                category_groups[category] = []
            category_groups[category].append(video)
        
        # Analyze each category for spikes
        for category, category_videos in category_groups.items():
            if len(category_videos) >= 5:  # Minimum videos to detect a spike
                # Calculate category metrics
                total_views = sum(v.view_count for v in category_videos)
                avg_engagement = sum(self._calculate_engagement_rate(v) for v in category_videos) / len(category_videos)
                
                # Check if this represents a category spike
                if total_views > 500000 and avg_engagement > 0.08:  # Threshold for category spike
                    # Pick the best performing video as representative
                    best_video = max(category_videos, key=lambda v: v.view_count)
                    
                    alert = TrendAlert(
                        alert_id=f"category_spike_{category}_{int(datetime.now().timestamp())}",
                        alert_type="category_spike",
                        title=f"📊 Category Spike: {category}",
                        description=f"Unusual activity in {category} with {len(category_videos)} videos, {total_views:,} total views",
                        video_id=best_video.video_id,
                        channel_title=best_video.channel_title,
                        current_stats={
                            "category_video_count": len(category_videos),
                            "total_category_views": total_views,
                            "average_engagement": avg_engagement,
                            "best_video_views": best_video.view_count
                        },
                        growth_metrics={
                            "category_momentum": len(category_videos) * (total_views / 1000000),
                            "engagement_consistency": avg_engagement
                        },
                        confidence_score=min(0.8, len(category_videos) * 0.1),
                        detected_at=datetime.now(),
                        category=category,
                        keywords=[category.lower().replace(" ", "_")],
                        youtube_url=f"https://youtube.com/watch?v={best_video.video_id}",
                        thumbnail_url=best_video.thumbnail_url
                    )
                    alerts.append(alert)
        
        logger.info(f"Detected {len(alerts)} category spike alerts")
        return alerts
    
    def _calculate_engagement_rate(self, video: ClassifiedVideo) -> float:
        """Calculate engagement rate for a video"""
        if video.view_count == 0:
            return 0.0
        
        total_engagement = video.like_count + video.comment_count
        return total_engagement / video.view_count
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Simple keyword extraction - can be enhanced with NLP
        import re
        
        # Clean and normalize text
        text = text.lower()
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.split()
        
        # Filter out common words and extract meaningful keywords
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must',
            'shorts', 'video', 'youtube', 'watch', 'like', 'subscribe', 'comment'
        }
        
        keywords = [word for word in words if len(word) > 2 and word not in stop_words]
        
        # Return top keywords by frequency
        from collections import Counter
        keyword_counts = Counter(keywords)
        return [keyword for keyword, count in keyword_counts.most_common(10)]
    
    def _group_by_keywords(self, videos: List[ClassifiedVideo]) -> Dict[str, List[ClassifiedVideo]]:
        """Group videos by similar keywords"""
        keyword_groups = {}
        
        for video in videos:
            keywords = self._extract_keywords(video.title + " " + video.description)
            
            # Create keyword signature (top 3 keywords)
            keyword_signature = " ".join(sorted(keywords[:3]))
            
            if keyword_signature:
                if keyword_signature not in keyword_groups:
                    keyword_groups[keyword_signature] = []
                keyword_groups[keyword_signature].append(video)
        
        # Filter out groups with less than 2 videos
        return {k: v for k, v in keyword_groups.items() if len(v) >= 2}
    
    def _calculate_novelty_score(self, keywords: List[str]) -> float:
        """Calculate novelty score for keywords"""
        # Simple novelty calculation - can be enhanced with historical data
        # For now, we'll use keyword uniqueness and combination patterns
        
        if not keywords:
            return 0.0
        
        # Common trending keywords (lower novelty)
        common_keywords = {
            'challenge', 'viral', 'trend', 'dance', 'tutorial', 'funny', 'comedy',
            'reaction', 'review', 'tips', 'hack', 'diy', 'food', 'recipe',
            'workout', 'fitness', 'makeup', 'fashion', 'music', 'cover'
        }
        
        # Calculate novelty based on uncommon keywords
        novel_keywords = [k for k in keywords if k not in common_keywords]
        novelty_score = len(novel_keywords) / len(keywords)
        
        # Boost score for unique combinations
        if len(set(keywords)) == len(keywords):  # All unique keywords
            novelty_score += 0.2
        
        return min(1.0, novelty_score)
    
    async def generate_weekly_report(self) -> Dict[str, Any]:
        """Generate weekly trend analysis report"""
        logger.info("Generating weekly trend report")
        
        try:
            # This would typically analyze data from the past week
            # For now, we'll create a summary report structure
            
            report = {
                "report_type": "weekly_trends",
                "generated_at": datetime.now(),
                "period": {
                    "start": datetime.now() - timedelta(days=7),
                    "end": datetime.now()
                },
                "summary": {
                    "total_trends_detected": self.stats["trends_detected"],
                    "viral_content_count": 0,  # Would be calculated from stored data
                    "rising_trends_count": 0,
                    "new_trends_count": 0,
                    "category_spikes_count": 0
                },
                "top_trending_keywords": [],
                "category_analysis": {},
                "growth_patterns": {},
                "recommendations": []
            }
            
            logger.info("Weekly trend report generated")
            return report
            
        except Exception as e:
            logger.error(f"Failed to generate weekly report: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get trend detection statistics"""
        return {
            "detector_stats": self.stats,
            "configuration": {
                "viral_threshold": self.viral_threshold,
                "growth_threshold": self.growth_threshold,
                "monitoring_enabled": self.settings.monitoring_enabled
            }
        }
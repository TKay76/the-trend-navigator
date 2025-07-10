"""Data collection agent for YouTube Shorts video gathering"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..clients.youtube_client import YouTubeClient
from ..models.video_models import YouTubeVideoRaw, CollectionRequest
from ..core.settings import get_settings
from ..core.exceptions import YouTubeAPIError, QuotaExceededError

# Setup logging
logger = logging.getLogger(__name__)


class CollectorAgent:
    """
    Data collection agent for YouTube Shorts.
    
    STRICT ROLE: Only data collection, no analysis or transformation.
    This agent is responsible solely for gathering video data from YouTube API.
    """
    
    def __init__(self, youtube_client: Optional[YouTubeClient] = None):
        """
        Initialize collector agent.
        
        Args:
            youtube_client: YouTube API client (if None, creates new instance)
        """
        self.agent_name = "CollectorAgent"
        self.settings = get_settings()
        
        # Use dependency injection for testability
        self.youtube_client = youtube_client
        
        # Collection statistics
        self.collection_stats = {
            "videos_collected": 0,
            "api_calls_made": 0,
            "quota_used": 0,
            "last_collection": None
        }
        
        logger.info(f"[{self.agent_name}] Agent initialized")
    
    async def collect_top_videos(
        self, 
        search_queries: List[str],
        max_results_per_query: int = 50,
        days: int = 7,
        top_n: int = 10,
        region_code: str = "US"
    ) -> List[YouTubeVideoRaw]:
        """
        Collects top N trending videos for multiple search queries based on 
        view count, like count, and comment count.

        Args:
            search_queries: List of search terms.
            max_results_per_query: Max videos to fetch per query for analysis.
            days: The number of past days to search within.
            top_n: The number of top videos to select for each metric.
            region_code: Region code for localized results.

        Returns:
            A consolidated list of unique top videos.
        """
        logger.info(f"[{self.agent_name}] Starting top video collection for {len(search_queries)} queries.")
        
        if self.youtube_client is None:
            self.youtube_client = YouTubeClient()

        all_videos = []
        collected_video_ids = set()

        for i, query in enumerate(search_queries):
            try:
                logger.info(f"[{self.agent_name}] Query {i+1}/{len(search_queries)}: '{query}'")
                
                # Check quota before making expensive search call
                current_quota = self.youtube_client.get_quota_usage()
                if current_quota + 100 > self.settings.max_daily_quota:
                    logger.warning(f"[{self.agent_name}] Quota limit approaching, stopping collection")
                    break
                
                videos = await self.youtube_client.search_trending_shorts(
                    query=query,
                    max_results=max_results_per_query,
                    days=days,
                    order="viewCount",
                    region_code=region_code
                )
                
                for video in videos:
                    if video.video_id not in collected_video_ids:
                        all_videos.append(video)
                        collected_video_ids.add(video.video_id)

            except QuotaExceededError as e:
                logger.error(f"[{self.agent_name}] Quota exceeded: {e}. Stopping collection.")
                break
            except YouTubeAPIError as e:
                logger.error(f"[{self.agent_name}] API error for query '{query}': {e}")
                continue

        if not all_videos:
            logger.warning(f"[{self.agent_name}] No videos found for any query.")
            return []

        # --- Sorting and Filtering Logic ---
        logger.info(f"[{self.agent_name}] Sorting {len(all_videos)} videos to find top {top_n} for each metric.")

        # Sort by view count
        top_by_views = sorted(
            [v for v in all_videos if v.statistics],
            key=lambda v: v.statistics.view_count, 
            reverse=True
        )[:top_n]

        # Sort by like count
        top_by_likes = sorted(
            [v for v in all_videos if v.statistics],
            key=lambda v: v.statistics.like_count, 
            reverse=True
        )[:top_n]

        # Sort by comment count
        top_by_comments = sorted(
            [v for v in all_videos if v.statistics],
            key=lambda v: v.statistics.comment_count, 
            reverse=True
        )[:top_n]

        # Consolidate and remove duplicates
        final_top_videos = {}
        for video in top_by_views + top_by_likes + top_by_comments:
            final_top_videos[video.video_id] = video
        
        final_list = list(final_top_videos.values())
        logger.info(f"[{self.agent_name}] Collection complete. Found {len(final_list)} unique top videos.")
        
        self.collection_stats["videos_collected"] = len(final_list)
        self.collection_stats["quota_used"] = self.youtube_client.get_quota_usage()
        self.collection_stats["last_collection"] = datetime.now()

        return final_list
    
    async def collect_by_request(self, request: CollectionRequest) -> List[YouTubeVideoRaw]:
        """
        Collect videos based on a structured collection request.
        
        Args:
            request: Collection request with search parameters
            
        Returns:
            List of collected video data
        """
        logger.info(f"[{self.agent_name}] Processing collection request with {len(request.search_queries)} queries")
        
        return await self.collect_top_videos(
            search_queries=request.search_queries,
            max_results_per_query=request.max_results_per_query,
            region_code=request.region_code or "US"
        )
    
    async def collect_by_category_keywords(
        self, 
        categories: List[str],
        max_results_per_category: int = 50,
        days: int = 7,
        top_n: int = 10,
        region_code: str = "US"
    ) -> List[YouTubeVideoRaw]:
        """
        Collects top videos by generating search queries for each category.

        Args:
            categories: List of category names to search for.
            max_results_per_category: Max videos to fetch per category for analysis.
            days: The number of past days to search within.
            top_n: The number of top videos to select for each metric.
            region_code: Region code for search.

        Returns:
            A list of top collected video data.
        """
        logger.info(f"[{self.agent_name}] Collecting top videos for categories: {categories}")
        
        search_queries = [f"{category} shorts" for category in categories]
        
        return await self.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=max_results_per_category,
            days=days,
            top_n=top_n,
            region_code=region_code
        )
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics for this session.
        
        Returns:
            Dictionary with collection statistics
        """
        stats = self.collection_stats.copy()
        
        # Add current quota usage if client exists
        if self.youtube_client:
            stats["current_quota_usage"] = self.youtube_client.get_quota_usage()
            stats["quota_remaining"] = self.settings.max_daily_quota - (stats["current_quota_usage"] or 0)
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset collection statistics"""
        self.collection_stats = {
            "videos_collected": 0,
            "api_calls_made": 0,
            "quota_used": 0,
            "last_collection": None
        }
        
        # Reset YouTube client quota tracking if exists
        if self.youtube_client:
            self.youtube_client.reset_quota_tracking()
        
        logger.info(f"[{self.agent_name}] Statistics reset")
    
    async def __aenter__(self):
        """Async context manager entry"""
        if self.youtube_client is None:
            self.youtube_client = YouTubeClient()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.youtube_client and hasattr(self.youtube_client, 'client'):
            await self.youtube_client.client.aclose()


# Factory function for easy instantiation
def create_collector_agent(youtube_client: Optional[YouTubeClient] = None) -> CollectorAgent:
    """
    Factory function to create collector agent.
    
    Args:
        youtube_client: Optional YouTube client for dependency injection
        
    Returns:
        Configured collector agent
    """
    return CollectorAgent(youtube_client=youtube_client)
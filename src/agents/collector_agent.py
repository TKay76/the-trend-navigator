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
    
    async def collect_trending_shorts(
        self, 
        search_queries: List[str],
        max_results_per_query: int = 20,
        region_code: str = "US"
    ) -> List[YouTubeVideoRaw]:
        """
        Collect trending YouTube Shorts based on search queries.
        
        STRICT ROLE: Only collection, no analysis or categorization.
        
        Args:
            search_queries: List of search terms for video discovery
            max_results_per_query: Maximum results per search query
            region_code: Region code for localized results
            
        Returns:
            List of raw YouTube video data
            
        Raises:
            YouTubeAPIError: If API calls fail
            QuotaExceededError: If quota limits are exceeded
        """
        logger.info(f"[{self.agent_name}] Starting collection for {len(search_queries)} queries")
        
        # Initialize YouTube client if needed
        if self.youtube_client is None:
            self.youtube_client = YouTubeClient()
        
        all_videos = []
        collected_video_ids = set()  # Prevent duplicates
        
        # Collect videos for each search query
        for i, query in enumerate(search_queries):
            try:
                logger.info(f"[{self.agent_name}] Processing query {i+1}/{len(search_queries)}: '{query}'")
                
                # Check quota before making expensive search call
                current_quota = self.youtube_client.get_quota_usage()
                if current_quota + 100 > self.settings.max_daily_quota:
                    logger.warning(f"[{self.agent_name}] Quota limit approaching, stopping collection")
                    break
                
                # Search for videos
                videos = await self.youtube_client.search_shorts(
                    query=query,
                    max_results=max_results_per_query,
                    region_code=region_code
                )
                
                # Filter out duplicates
                unique_videos = []
                for video in videos:
                    if video.video_id not in collected_video_ids:
                        unique_videos.append(video)
                        collected_video_ids.add(video.video_id)
                
                all_videos.extend(unique_videos)
                
                # Update statistics
                self.collection_stats["videos_collected"] = (self.collection_stats["videos_collected"] or 0) + len(unique_videos)
                self.collection_stats["api_calls_made"] = (self.collection_stats["api_calls_made"] or 0) + 1
                
                logger.info(f"[{self.agent_name}] Collected {len(unique_videos)} unique videos from query '{query}'")
                
                # Rate limiting: delay between requests to be respectful
                if i < len(search_queries) - 1:  # Don't delay after the last query
                    delay = max(1, 60 / self.settings.rate_limit_per_second)
                    logger.debug(f"[{self.agent_name}] Waiting {delay} seconds before next query")
                    await asyncio.sleep(delay)
                
            except QuotaExceededError as e:
                logger.error(f"[{self.agent_name}] Quota exceeded: {e}")
                break
                
            except YouTubeAPIError as e:
                logger.error(f"[{self.agent_name}] API error for query '{query}': {e}")
                continue  # Continue with next query
        
        # Update final statistics
        self.collection_stats["quota_used"] = self.youtube_client.get_quota_usage()
        self.collection_stats["last_collection"] = datetime.now()
        
        logger.info(f"[{self.agent_name}] Collection complete: {len(all_videos)} total videos collected")
        return all_videos
    
    async def collect_by_request(self, request: CollectionRequest) -> List[YouTubeVideoRaw]:
        """
        Collect videos based on a structured collection request.
        
        Args:
            request: Collection request with search parameters
            
        Returns:
            List of collected video data
        """
        logger.info(f"[{self.agent_name}] Processing collection request with {len(request.search_queries)} queries")
        
        return await self.collect_trending_shorts(
            search_queries=request.search_queries,
            max_results_per_query=request.max_results_per_query,
            region_code=request.region_code or "US"
        )
    
    async def collect_by_category_keywords(
        self, 
        categories: List[str],
        max_results_per_category: int = 20,
        region_code: str = "US"
    ) -> List[YouTubeVideoRaw]:
        """
        Collect videos by generating search queries for each category.
        
        Args:
            categories: List of category names to search for
            max_results_per_category: Maximum results per category
            region_code: Region code for search
            
        Returns:
            List of collected video data
        """
        logger.info(f"[{self.agent_name}] Collecting videos for categories: {categories}")
        
        # Generate search queries for each category
        search_queries = []
        for category in categories:
            # Create multiple search variations for better coverage
            queries = [
                f"{category} shorts trending",
                f"{category} viral",
                f"popular {category}",
                f"best {category} 2024"
            ]
            search_queries.extend(queries)
        
        logger.debug(f"[{self.agent_name}] Generated {len(search_queries)} search queries")
        
        return await self.collect_trending_shorts(
            search_queries=search_queries,
            max_results_per_query=max_results_per_category // 4,  # Divide by 4 queries per category
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
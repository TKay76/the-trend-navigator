"""YouTube Data API client for shorts video collection"""

import httpx
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..core.settings import get_settings
from ..core.exceptions import QuotaExceededError, YouTubeAPIError
from ..models.video_models import YouTubeVideoRaw, VideoSnippet, VideoStatistics

# Setup logging
logger = logging.getLogger(__name__)

# YouTube API constants
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"


class YouTubeClient:
    """
    YouTube Data API client for collecting shorts video data.
    Follows async patterns with proper error handling and quota management.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API key (if None, loads from settings)
        """
        self.settings = get_settings()
        self.api_key = api_key or self.settings.youtube_api_key
        
        if not self.api_key or self.api_key == "":
            raise ValueError("YouTube API key is required")
        
        # Configure HTTP client with limits and timeout
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5
            ),
            timeout=30.0
        )
        
        self.base_url = YOUTUBE_API_BASE_URL
        self.quota_used = 0  # Track quota usage
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.client.aclose()
    
    async def search_trending_shorts(
        self, 
        query: str, 
        max_results: int = 50,
        days: int = 7,
        order: str = "viewCount",
        region_code: str = "US"
    ) -> List[YouTubeVideoRaw]:
        """
        Search for trending YouTube Shorts videos within a specific period.

        Args:
            query: Search query string
            max_results: Maximum number of results (1-50)
            days: Number of past days to search within (e.g., 7 for the last week)
            order: Sort order ('viewCount', 'relevance', 'date')
            region_code: Region code for search (ISO 3166-1 alpha-2)
            
        Returns:
            List of raw YouTube video data, filtered to be actual shorts.
        """
        logger.info(f"Searching for trending shorts: '{query}' (last {days} days, order by {order})")

        if self.quota_used + 100 > self.settings.max_daily_quota:
            raise QuotaExceededError(f"Would exceed daily quota limit ({self.settings.max_daily_quota})")

        # Calculate the 'publishedAfter' timestamp
        published_after = (datetime.utcnow() - timedelta(days=days)).isoformat("T") + "Z"

        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "short",
            "maxResults": min(max_results, 50),
            "regionCode": region_code,
            "order": order,
            "publishedAfter": published_after,
            "key": self.api_key
        }
        
        video_ids = await self._make_search_request(params)
        if not video_ids:
            return []
        
        # Get detailed video information to verify duration
        videos = await self.get_video_details(video_ids)
        
        # Filter to only include actual shorts (duration <= 60 seconds)
        shorts = self._filter_shorts(videos)
        
        logger.info(f"Found {len(shorts)} actual shorts from {len(videos)} videos fetched.")
        return shorts
    
    async def get_video_details(self, video_ids: List[str]) -> List[YouTubeVideoRaw]:
        """
        Get detailed information for specific video IDs.
        
        Args:
            video_ids: List of YouTube video IDs
            
        Returns:
            List of detailed video data
            
        Raises:
            QuotaExceededError: When API quota is exceeded
            YouTubeAPIError: For other API errors
        """
        if not video_ids:
            return []
        
        # Quota Cost: 1 (cheap for details)
        logger.debug(f"Getting details for {len(video_ids)} videos")
        
        # Check quota
        if self.quota_used + 1 > self.settings.max_daily_quota:
            raise QuotaExceededError(f"Would exceed daily quota limit ({self.settings.max_daily_quota})")
        
        # YouTube API supports up to 50 IDs per request
        video_ids_str = ",".join(video_ids[:50])
        
        params = {
            "part": "snippet,contentDetails,statistics",
            "id": video_ids_str,
            "key": self.api_key
        }
        
        return await self._make_videos_request(params)
    
    async def _make_search_request(self, params: Dict[str, Any]) -> List[str]:
        """Make search API request with retry logic"""
        for attempt in range(3):
            try:
                response = await self.client.get(f"{self.base_url}/search", params=params)
                
                if response.status_code == 429:
                    # Handle rate limiting
                    retry_after = int(response.headers.get('retry-after', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Update quota usage
                self.quota_used += 100
                logger.debug(f"Quota used: {self.quota_used}/{self.settings.max_daily_quota}")
                
                # Extract video IDs from search results
                video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
                return video_ids
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    error_data = e.response.json() if e.response.content else {}
                    error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                    
                    if "quotaExceeded" in error_reason:
                        raise QuotaExceededError("YouTube API daily quota exceeded")
                    else:
                        raise YouTubeAPIError(f"YouTube API access forbidden: {error_reason}")
                        
                elif attempt == 2:
                    raise YouTubeAPIError(f"YouTube API error: {e.response.status_code}")
                    
                # Exponential backoff for retries
                await asyncio.sleep(2 ** attempt)
                
            except httpx.RequestError as e:
                if attempt == 2:
                    raise YouTubeAPIError(f"Network error: {str(e)}")
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    async def _make_videos_request(self, params: Dict[str, Any]) -> List[YouTubeVideoRaw]:
        """Make videos API request with retry logic"""
        for attempt in range(3):
            try:
                response = await self.client.get(f"{self.base_url}/videos", params=params)
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('retry-after', 60))
                    logger.warning(f"Rate limited. Waiting {retry_after} seconds...")
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # Update quota usage
                self.quota_used += 1
                logger.debug(f"Quota used: {self.quota_used}/{self.settings.max_daily_quota}")
                
                # Convert to Pydantic models
                videos = []
                for item in data.get("items", []):
                    try:
                        video = self._parse_video_item(item)
                        videos.append(video)
                    except Exception as e:
                        logger.warning(f"Failed to parse video {item.get('id', 'unknown')}: {e}")
                        continue
                
                return videos
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    error_data = e.response.json() if e.response.content else {}
                    error_reason = error_data.get("error", {}).get("errors", [{}])[0].get("reason", "")
                    
                    if "quotaExceeded" in error_reason:
                        raise QuotaExceededError("YouTube API daily quota exceeded")
                    else:
                        raise YouTubeAPIError(f"YouTube API access forbidden: {error_reason}")
                        
                elif attempt == 2:
                    raise YouTubeAPIError(f"YouTube API error: {e.response.status_code}")
                    
                await asyncio.sleep(2 ** attempt)
                
            except httpx.RequestError as e:
                if attempt == 2:
                    raise YouTubeAPIError(f"Network error: {str(e)}")
                await asyncio.sleep(2 ** attempt)
        
        return []
    
    def _parse_video_item(self, item: Dict[str, Any]) -> YouTubeVideoRaw:
        """Parse YouTube API video item into Pydantic model"""
        snippet_data = item["snippet"]
        
        # Parse thumbnail URL
        thumbnails = snippet_data.get("thumbnails", {})
        thumbnail_url = (
            thumbnails.get("medium", {}).get("url") or
            thumbnails.get("default", {}).get("url") or
            "https://example.com/default.jpg"
        )
        
        # Parse published date
        published_at = datetime.fromisoformat(
            snippet_data["publishedAt"].replace('Z', '+00:00')
        )
        
        # Create snippet model
        snippet = VideoSnippet(
            title=snippet_data["title"],
            description=snippet_data.get("description", ""),
            published_at=published_at,
            channel_title=snippet_data.get("channelTitle", ""),
            thumbnail_url=thumbnail_url,
            duration=item.get("contentDetails", {}).get("duration")
        )
        
        # Create statistics model if available
        statistics = None
        if "statistics" in item:
            stats_data = item["statistics"]
            statistics = VideoStatistics(
                view_count=int(stats_data.get("viewCount", 0)),
                like_count=int(stats_data.get("likeCount", 0)),
                comment_count=int(stats_data.get("commentCount", 0))
            )
        
        return YouTubeVideoRaw(
            video_id=item["id"],
            snippet=snippet,
            statistics=statistics
        )
    
    def _parse_duration_to_seconds(self, duration: str) -> Optional[int]:
        """Parse ISO 8601 duration string to seconds."""
        if not duration or not duration.startswith('PT'):
            return None

        # Regex to parse ISO 8601 duration format (e.g., PT1M5S)
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
        if not match or not any(match.groups()): # Ensure at least one group has a value
            return None

        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds

    def _filter_shorts(self, videos: List[YouTubeVideoRaw]) -> List[YouTubeVideoRaw]:
        """
        Filter videos to only include actual shorts (duration <= 60 seconds).
        YouTube's 'videoDuration=short' parameter can include videos up to 4 minutes.
        """
        actual_shorts = []
        for video in videos:
            duration_seconds = self._parse_duration_to_seconds(video.snippet.duration)
            
            # We only want videos that are 60 seconds or less
            if duration_seconds is not None and duration_seconds <= 60:
                actual_shorts.append(video)
            elif duration_seconds is None:
                # If duration is unknown, we can choose to include it as a fallback.
                # For now, we will be strict and exclude it.
                logger.debug(f"Excluding video {video.video_id} with unknown duration.")

        return actual_shorts
    
    def get_quota_usage(self) -> int:
        """Get current quota usage for this session"""
        return self.quota_used
    
    def reset_quota_tracking(self) -> None:
        """Reset quota tracking (call at start of new day)"""
        self.quota_used = 0
        logger.info("Quota tracking reset")
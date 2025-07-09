"""YouTube Data API client for shorts video collection"""

import httpx
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

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
        
        if not self.api_key:
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
    
    async def search_shorts(
        self, 
        query: str, 
        max_results: int = 20,
        region_code: str = "US"
    ) -> List[YouTubeVideoRaw]:
        """
        Search for YouTube Shorts videos.
        
        Args:
            query: Search query string
            max_results: Maximum number of results (1-50)
            region_code: Region code for search (ISO 3166-1 alpha-2)
            
        Returns:
            List of raw YouTube video data
            
        Raises:
            QuotaExceededError: When API quota is exceeded
            YouTubeAPIError: For other API errors
        """
        # Quota Cost: 100 (expensive - use sparingly)
        logger.info(f"Searching for shorts: '{query}' (max_results={max_results})")
        
        # Check quota before making expensive search call
        if self.quota_used + 100 > self.settings.max_daily_quota:
            raise QuotaExceededError(f"Would exceed daily quota limit ({self.settings.max_daily_quota})")
        
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "short",  # Filter for shorts (<= 4 minutes)
            "maxResults": min(max_results, 50),  # API limit
            "regionCode": region_code,
            "order": "relevance",  # Most relevant first
            "key": self.api_key
        }
        
        video_ids = await self._make_search_request(params)
        if not video_ids:
            return []
        
        # Get detailed video information (cheaper API call)
        videos = await self.get_video_details(video_ids)
        
        # Filter to only include actual shorts (duration <= 60 seconds)
        shorts = self._filter_shorts(videos)
        
        logger.info(f"Found {len(shorts)} shorts out of {len(videos)} videos")
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
    
    def _filter_shorts(self, videos: List[YouTubeVideoRaw]) -> List[YouTubeVideoRaw]:
        """
        Filter videos to only include actual shorts (duration <= 60 seconds).
        YouTube's videoDuration=short parameter can include videos up to 4 minutes.
        """
        shorts = []
        
        for video in videos:
            if not video.snippet.duration:
                # If no duration info, assume it might be a short
                shorts.append(video)
                continue
            
            # Parse ISO 8601 duration (e.g., "PT1M5S" = 1 minute 5 seconds)
            duration_str = video.snippet.duration
            try:
                if duration_str.startswith("PT"):
                    # Simple parsing for shorts - looking for seconds only or < 1 minute
                    if "H" not in duration_str and (
                        "M" not in duration_str or 
                        (duration_str.count("M") == 1 and int(duration_str.split("M")[0].split("T")[1]) == 0)
                    ):
                        shorts.append(video)
                    elif "M" in duration_str:
                        minutes_part = duration_str.split("M")[0].split("T")[1]
                        if minutes_part.isdigit() and int(minutes_part) <= 1:
                            shorts.append(video)
            except (ValueError, IndexError) as e:
                logger.debug(f"Could not parse duration '{duration_str}': {e}")
                # Include if we can't parse (better to include than exclude)
                shorts.append(video)
        
        return shorts
    
    def get_quota_usage(self) -> int:
        """Get current quota usage for this session"""
        return self.quota_used
    
    def reset_quota_tracking(self) -> None:
        """Reset quota tracking (call at start of new day)"""
        self.quota_used = 0
        logger.info("Quota tracking reset")
"""Tests for YouTube API client"""

import pytest
import httpx
from unittest.mock import Mock, AsyncMock, patch

from src.clients.youtube_client import YouTubeClient
from src.core.exceptions import YouTubeAPIError, QuotaExceededError
from src.models.video_models import YouTubeVideoRaw


class TestYouTubeClient:
    """Test YouTube API client functionality"""
    
    @pytest.fixture
    def youtube_client(self):
        """Create YouTube client for testing"""
        return YouTubeClient(api_key="test_api_key")
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, monkeypatch):
        """Test YouTube client initialization"""
        # Mock get_settings to return a Settings object with an empty youtube_api_key
        mock_settings = Mock()
        mock_settings.youtube_api_key = ""
        monkeypatch.setattr('src.clients.youtube_client.get_settings', lambda: mock_settings)

        client = YouTubeClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.base_url == "https://www.googleapis.com/youtube/v3"
        assert client.quota_used == 0
        
        # Test initialization without API key
        with pytest.raises(ValueError, match="YouTube API key is required"):
            YouTubeClient(api_key="")
    
    @pytest.mark.asyncio
    async def test_search_trending_shorts_success(self, youtube_client, mock_youtube_api_response, mock_youtube_videos_response):
        """Test successful trending shorts search"""
        mock_client = AsyncMock()
        
        search_response = Mock(status_code=200, json=lambda: mock_youtube_api_response)
        videos_response = Mock(status_code=200, json=lambda: mock_youtube_videos_response)

        async def mock_get(url, params=None):
            if "/search" in url:
                # Check that publishedAfter is set correctly
                assert "publishedAfter" in params
                return search_response
            elif "/videos" in url:
                return videos_response
            return Mock()

        mock_client.get = mock_get
        youtube_client.client = mock_client
        
        videos = await youtube_client.search_trending_shorts("dance challenge", days=7)
        
        assert len(videos) == 1
        assert isinstance(videos[0], YouTubeVideoRaw)
        assert videos[0].video_id == "abc123"
        assert youtube_client.quota_used == 101
    
    @pytest.mark.asyncio
    async def test_search_shorts_quota_check(self, youtube_client):
        """Test quota checking before expensive search"""
        # Set quota near limit
        youtube_client.quota_used = 9950
        youtube_client.settings.max_daily_quota = 10000
        
        with pytest.raises(QuotaExceededError, match="Would exceed daily quota limit"):
            await youtube_client.search_trending_shorts("test query")
    
    @pytest.mark.asyncio
    async def test_search_shorts_rate_limiting(self, youtube_client):
        """Test rate limiting handling"""
        mock_client = AsyncMock()
        
        # First call returns 429, second call succeeds
        responses = [
            Mock(status_code=429, headers={"retry-after": "1"}),
            Mock(status_code=200, json=lambda: {"items": []})
        ]
        
        call_count = 0
        async def mock_get(url, params=None):
            nonlocal call_count
            if "/search" in url:
                response = responses[min(call_count, len(responses) - 1)]
                call_count += 1
                return response
            # Mock videos endpoint
            return Mock(status_code=200, json=lambda: {"items": []})
        
        mock_client.get = mock_get
        youtube_client.client = mock_client
        
        # Mock asyncio.sleep to avoid actual delay in tests
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await youtube_client.search_trending_shorts("test")
            mock_sleep.assert_called_once_with(1)  # retry-after value
    
    @pytest.mark.asyncio
    async def test_search_shorts_quota_exceeded_error(self, youtube_client):
        """Test handling of quota exceeded error"""
        mock_client = AsyncMock()
        
        # Mock 403 response with quotaExceeded error
        error_response = Mock()
        error_response.status_code = 403
        error_response.json.return_value = {
            "error": {
                "errors": [{"reason": "quotaExceeded"}]
            }
        }
        
        http_error = httpx.HTTPStatusError(
            message="Forbidden",
            request=Mock(),
            response=error_response
        )
        
        mock_client.get.side_effect = http_error
        youtube_client.client = mock_client
        
        with pytest.raises(QuotaExceededError, match="YouTube API daily quota exceeded"):
            await youtube_client.search_trending_shorts("test")
    
    @pytest.mark.asyncio
    async def test_search_shorts_api_error(self, youtube_client):
        """Test handling of general API errors"""
        mock_client = AsyncMock()
        
        # Mock 403 response with other error
        error_response = Mock()
        error_response.status_code = 403
        error_response.json.return_value = {
            "error": {
                "errors": [{"reason": "forbidden"}]
            }
        }
        
        http_error = httpx.HTTPStatusError(
            message="Forbidden",
            request=Mock(),
            response=error_response
        )
        
        mock_client.get.side_effect = http_error
        youtube_client.client = mock_client
        
        with pytest.raises(YouTubeAPIError, match="YouTube API access forbidden"):
            await youtube_client.search_trending_shorts("test")
    
    @pytest.mark.asyncio
    async def test_search_shorts_network_error(self, youtube_client):
        """Test handling of network errors"""
        mock_client = AsyncMock()
        
        # Mock network error
        network_error = httpx.RequestError("Network error")
        mock_client.get.side_effect = network_error
        youtube_client.client = mock_client
        
        with pytest.raises(YouTubeAPIError, match="Network error"):
            await youtube_client.search_trending_shorts("test")
    
    @pytest.mark.asyncio
    async def test_get_video_details_success(self, youtube_client, mock_youtube_videos_response):
        """Test successful video details retrieval"""
        mock_client = AsyncMock()
        
        videos_response = Mock()
        videos_response.status_code = 200
        videos_response.json.return_value = mock_youtube_videos_response
        
        mock_client.get.return_value = videos_response
        youtube_client.client = mock_client
        
        videos = await youtube_client.get_video_details(["abc123"])
        
        assert len(videos) == 1
        assert videos[0].video_id == "abc123"
        assert youtube_client.quota_used == 1
    
    @pytest.mark.asyncio
    async def test_get_video_details_empty_list(self, youtube_client):
        """Test video details with empty input"""
        videos = await youtube_client.get_video_details([])
        assert videos == []
    
    @pytest.mark.asyncio
    async def test_get_video_details_quota_check(self, youtube_client):
        """Test quota checking for video details"""
        youtube_client.quota_used = 10000
        youtube_client.settings.max_daily_quota = 10000
        
        with pytest.raises(QuotaExceededError):
            await youtube_client.get_video_details(["test"])
    
    def test_parse_video_item_success(self, youtube_client):
        """Test parsing of YouTube API video item"""
        item = {
            "id": "test123",
            "snippet": {
                "title": "Test Video",
                "description": "Test description",
                "publishedAt": "2024-01-15T10:00:00Z",
                "channelTitle": "Test Channel",
                "thumbnails": {
                    "default": {"url": "https://example.com/test.jpg"}
                }
            },
            "contentDetails": {
                "duration": "PT45S"
            },
            "statistics": {
                "viewCount": "1000",
                "likeCount": "50",
                "commentCount": "10"
            }
        }
        
        video = youtube_client._parse_video_item(item)
        
        assert video.video_id == "test123"
        assert video.snippet.title == "Test Video"
        assert video.snippet.description == "Test description"
        assert video.snippet.channel_title == "Test Channel"
        assert video.snippet.duration == "PT45S"
        assert video.statistics.view_count == 1000
        assert video.statistics.like_count == 50
        assert video.statistics.comment_count == 10
    
    def test_parse_video_item_minimal(self, youtube_client):
        """Test parsing with minimal required data"""
        item = {
            "id": "test123",
            "snippet": {
                "title": "Test Video",
                "publishedAt": "2024-01-15T10:00:00Z",
                "thumbnails": {
                    "default": {"url": "https://example.com/test.jpg"}
                }
            }
        }
        
        video = youtube_client._parse_video_item(item)
        
        assert video.video_id == "test123"
        assert video.snippet.title == "Test Video"
        assert video.snippet.description == ""
        assert video.snippet.channel_title == ""
        assert video.statistics is None
    
    def test_filter_shorts_by_duration(self, youtube_client, sample_youtube_videos):
        """Test filtering videos to only include shorts"""
        # Create test videos with different durations
        videos = sample_youtube_videos.copy()
        
        # Modify durations to test filtering
        videos[0].snippet.duration = "PT30S"  # 30 seconds - should be included
        videos[1].snippet.duration = "PT58S"  # 58 seconds - should be included  
        videos[2].snippet.duration = "PT5M"   # 5 minutes - should be excluded
        
        shorts = youtube_client._filter_shorts(videos)
        
        # Should only include the first two videos (shorts)
        assert len(shorts) == 2
        assert shorts[0].video_id == videos[0].video_id
        assert shorts[1].video_id == videos[1].video_id
    
    def test_filter_shorts_no_duration(self, youtube_client, sample_youtube_videos):
        """Test filtering when duration information is missing"""
        videos = sample_youtube_videos.copy()
        
        # Remove duration information
        for video in videos:
            video.snippet.duration = None
        
        shorts = youtube_client._filter_shorts(videos)
        
        # Should be empty as videos with unknown duration are now excluded
        assert len(shorts) == 0
    
    def test_filter_shorts_invalid_duration(self, youtube_client, sample_youtube_videos):
        """Test filtering with invalid duration format"""
        videos = sample_youtube_videos.copy()
        
        # Set invalid duration formats
        videos[0].snippet.duration = "INVALID"
        videos[1].snippet.duration = "PT"
        videos[2].snippet.duration = None
        
        shorts = youtube_client._filter_shorts(videos)
        
        # Should be empty as videos with invalid duration are now excluded
        assert len(shorts) == 0
    
    def test_quota_tracking(self, youtube_client):
        """Test quota usage tracking"""
        assert youtube_client.get_quota_usage() == 0
        
        # Simulate quota usage
        youtube_client.quota_used = 150
        assert youtube_client.get_quota_usage() == 150
        
        # Test reset
        youtube_client.reset_quota_tracking()
        assert youtube_client.get_quota_usage() == 0
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test YouTube client as async context manager"""
        async with YouTubeClient(api_key="test_key") as client:
            assert isinstance(client, YouTubeClient)
            assert client.api_key == "test_key"
        
        # Client should be properly closed after context
        # (In real implementation, this would close the HTTP client)
    
    @pytest.mark.asyncio
    async def test_search_parameters(self, youtube_client):
        """Test search parameters are correctly formatted"""
        mock_client = AsyncMock()
        
        # Capture the parameters passed to the API
        captured_params = {}
        
        async def capture_params(url, params=None):
            if "/search" in url:
                captured_params.update(params or {})
                return Mock(status_code=200, json=lambda: {"items": []})
            return Mock(status_code=200, json=lambda: {"items": []})
        
        mock_client.get = capture_params
        youtube_client.client = mock_client
        
        await youtube_client.search_trending_shorts(
            query="test query",
            max_results=25,
            region_code="KR",
            days=1, # Add days parameter
            order="viewCount" # Add order parameter
        )
        
        # Verify parameters
        assert captured_params["part"] == "snippet"
        assert captured_params["q"] == "test query"
        assert captured_params["type"] == "video"
        assert captured_params["videoDuration"] == "short"
        assert captured_params["maxResults"] == 25
        assert captured_params["regionCode"] == "KR"
        assert captured_params["order"] == "viewCount"
        assert "publishedAfter" in captured_params # Verify publishedAfter is present
        assert captured_params["key"] == "test_api_key"
    
    @pytest.mark.asyncio
    async def test_max_results_limit(self, youtube_client):
        """Test max results is limited to API constraints"""
        mock_client = AsyncMock()
        
        captured_params = {}
        
        async def capture_params(url, params=None):
            if "/search" in url:
                captured_params.update(params or {})
                return Mock(status_code=200, json=lambda: {"items": []})
            return Mock(status_code=200, json=lambda: {"items": []})
        
        mock_client.get = capture_params
        youtube_client.client = mock_client
        
        # Request more than API limit
        await youtube_client.search_trending_shorts("test", max_results=100, days=1, order="viewCount")
        
        # Should be limited to 50 (API maximum)
        assert captured_params["maxResults"] == 50
    
    @pytest.mark.asyncio
    async def test_retry_logic_exponential_backoff(self, youtube_client):
        """Test exponential backoff retry logic"""
        mock_client = AsyncMock()
        
        # Simulate failures then success
        call_count = 0
        async def mock_get_with_failures(url, params=None):
            nonlocal call_count
            call_count += 1
            
            if "/search" in url:
                if call_count <= 2:  # First two calls fail
                    raise httpx.HTTPStatusError(
                        message="Server Error",
                        request=Mock(),
                        response=Mock(status_code=500)
                    )
                else:  # Third call succeeds
                    return Mock(status_code=200, json=lambda: {"items": []})
            return Mock(status_code=200, json=lambda: {"items": []})
        
        mock_client.get = mock_get_with_failures
        youtube_client.client = mock_client
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            await youtube_client.search_trending_shorts("test")
            
            # Should have called sleep for exponential backoff
            assert mock_sleep.call_count == 2
            # Check exponential backoff: 2^0=1, 2^1=2
            mock_sleep.assert_any_call(1)  # First retry
            mock_sleep.assert_any_call(2)  # Second retry
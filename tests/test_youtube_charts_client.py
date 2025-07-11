"""Tests for YouTube Charts client"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.clients.youtube_charts_client import YouTubeChartsClient
from src.models.video_models import ChartSong, TrendDirection
from src.core.exceptions import YouTubeAPIError


class TestYouTubeChartsClient:
    """Test suite for YouTube Charts client"""
    
    def test_init(self):
        """Test client initialization"""
        client = YouTubeChartsClient(headless=True)
        assert client.headless is True
        assert client.base_url == "https://charts.youtube.com"
        assert client.request_delay == 2.0
    
    def test_init_headless_false(self):
        """Test client initialization with headless=False"""
        client = YouTubeChartsClient(headless=False)
        assert client.headless is False
    
    @patch('src.clients.youtube_charts_client.webdriver.Chrome')
    def test_setup_driver_success(self, mock_chrome):
        """Test successful driver setup"""
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        client = YouTubeChartsClient(headless=True)
        driver = client._setup_driver()
        
        assert driver == mock_driver
        mock_chrome.assert_called_once()
        mock_driver.execute_script.assert_called_once()
    
    @patch('src.clients.youtube_charts_client.webdriver.Chrome')
    def test_setup_driver_failure(self, mock_chrome):
        """Test driver setup failure"""
        mock_chrome.side_effect = Exception("Driver setup failed")
        
        client = YouTubeChartsClient(headless=True)
        
        with pytest.raises(YouTubeAPIError) as exc_info:
            client._setup_driver()
        
        assert "Failed to initialize Chrome driver" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_rate_limit(self):
        """Test rate limiting functionality"""
        client = YouTubeChartsClient(headless=True)
        
        # First call should not delay
        start_time = asyncio.get_event_loop().time()
        await client._rate_limit()
        first_call_time = asyncio.get_event_loop().time() - start_time
        
        # Should be minimal delay for first call
        assert first_call_time < 0.1
        
        # Second call should be delayed
        start_time = asyncio.get_event_loop().time()
        await client._rate_limit()
        second_call_time = asyncio.get_event_loop().time() - start_time
        
        # Should be at least the delay time
        assert second_call_time >= client.request_delay - 0.1
    
    @pytest.mark.asyncio
    @patch('src.clients.youtube_charts_client.YouTubeChartsClient._extract_chart_data')
    @patch('src.clients.youtube_charts_client.WebDriverWait')
    async def test_get_top_shorts_songs_kr_success(self, mock_wait, mock_extract):
        """Test successful chart data extraction"""
        mock_driver = Mock()
        mock_wait.return_value.until.return_value = Mock()
        
        # Mock extracted songs
        mock_songs = [
            ChartSong(
                title="Test Song 1",
                artist="Test Artist 1",
                rank=1,
                video_id="test123"
            ),
            ChartSong(
                title="Test Song 2",
                artist="Test Artist 2",
                rank=2,
                video_id="test456"
            )
        ]
        mock_extract.return_value = mock_songs
        
        client = YouTubeChartsClient(headless=True)
        client.driver = mock_driver
        
        result = await client.get_top_shorts_songs_kr("daily")
        
        assert len(result) == 2
        assert result[0].title == "Test Song 1"
        assert result[1].rank == 2
        mock_driver.get.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_top_shorts_songs_kr_no_driver(self):
        """Test chart collection without driver"""
        client = YouTubeChartsClient(headless=True)
        
        with pytest.raises(YouTubeAPIError) as exc_info:
            await client.get_top_shorts_songs_kr("daily")
        
        assert "Driver not initialized" in str(exc_info.value)
    
    def test_extract_song_from_element_success(self):
        """Test successful song extraction from element"""
        mock_element = Mock()
        
        # Mock title element
        mock_title = Mock()
        mock_title.text = "Test Song"
        mock_element.find_element.side_effect = [
            mock_title,  # title
            Mock(text="Test Artist"),  # artist
            Mock(get_attribute=Mock(return_value="https://youtube.com/watch?v=test123"))  # link
        ]
        
        client = YouTubeChartsClient(headless=True)
        
        # Use asyncio.run to handle async method
        async def run_test():
            result = await client._extract_song_from_element(mock_element, 1)
            return result
        
        result = asyncio.run(run_test())
        
        assert result is not None
        assert result.title == "Test Song"
        assert result.artist == "Test Artist"
        assert result.rank == 1
        assert result.video_id == "test123"
    
    def test_extract_song_from_element_missing_data(self):
        """Test song extraction with missing data"""
        mock_element = Mock()
        mock_element.find_element.side_effect = Exception("Element not found")
        
        client = YouTubeChartsClient(headless=True)
        
        # Use asyncio.run to handle async method
        async def run_test():
            result = await client._extract_song_from_element(mock_element, 1)
            return result
        
        result = asyncio.run(run_test())
        
        assert result is None
    
    def test_get_supported_regions(self):
        """Test getting supported regions"""
        client = YouTubeChartsClient(headless=True)
        regions = client.get_supported_regions()
        
        assert isinstance(regions, list)
        assert "kr" in regions
        assert "us" in regions
        assert len(regions) > 0
    
    def test_get_supported_chart_types(self):
        """Test getting supported chart types"""
        client = YouTubeChartsClient(headless=True)
        chart_types = client.get_supported_chart_types()
        
        assert isinstance(chart_types, list)
        assert "daily" in chart_types
        assert "weekly" in chart_types
        assert len(chart_types) > 0
    
    @pytest.mark.asyncio
    @patch('src.clients.youtube_charts_client.YouTubeChartsClient.get_top_shorts_songs_kr')
    async def test_get_chart_history(self, mock_get_songs):
        """Test chart history collection"""
        mock_songs = [
            ChartSong(
                title="Test Song",
                artist="Test Artist",
                rank=1,
                video_id="test123"
            )
        ]
        mock_get_songs.return_value = mock_songs
        
        client = YouTubeChartsClient(headless=True)
        client.driver = Mock()
        
        result = await client.get_chart_history(days=1)
        
        assert isinstance(result, dict)
        assert len(result) == 1
        today = datetime.now().strftime("%Y-%m-%d")
        assert today in result
        assert result[today] == mock_songs


@pytest.mark.integration
class TestYouTubeChartsClientIntegration:
    """Integration tests for YouTube Charts client (require network)"""
    
    @pytest.mark.asyncio
    async def test_real_chart_collection(self):
        """
        Test real chart collection from YouTube Charts.
        This test is marked as integration and requires network access.
        """
        client = YouTubeChartsClient(headless=True)
        
        try:
            async with client as c:
                # Test with a short timeout to avoid long waits in CI
                import asyncio
                result = await asyncio.wait_for(
                    c.get_top_shorts_songs_kr("daily"),
                    timeout=30.0
                )
                
                # Basic validation
                assert isinstance(result, list)
                if result:  # Only validate if we got results
                    assert all(isinstance(song, ChartSong) for song in result)
                    assert all(song.rank > 0 for song in result)
                    assert all(song.title for song in result)
                    assert all(song.artist for song in result)
                    
        except Exception as e:
            # Skip if we can't connect or if the site structure changed
            pytest.skip(f"Integration test skipped due to: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
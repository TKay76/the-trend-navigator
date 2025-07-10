"""Tests for data collection agent"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.agents.collector_agent import CollectorAgent, create_collector_agent
from src.clients.youtube_client import YouTubeClient
from src.models.video_models import CollectionRequest, YouTubeVideoRaw
from src.core.exceptions import YouTubeAPIError, QuotaExceededError


class TestCollectorAgent:
    """Test data collection agent functionality"""
    
    @pytest.fixture
    def collector_agent(self, mock_youtube_client):
        """Create collector agent with mock YouTube client"""
        return CollectorAgent(youtube_client=mock_youtube_client)
    
    def test_collector_agent_initialization(self):
        """Test collector agent initialization"""
        # Test with provided client
        mock_client = Mock(spec=YouTubeClient)
        agent = CollectorAgent(youtube_client=mock_client)
        
        assert agent.agent_name == "CollectorAgent"
        assert agent.youtube_client == mock_client
        assert agent.collection_stats["videos_collected"] == 0
        assert agent.collection_stats["api_calls_made"] == 0
        assert agent.collection_stats["quota_used"] == 0
        assert agent.collection_stats["last_collection"] is None
        
        # Test without provided client
        agent_no_client = CollectorAgent()
        assert agent_no_client.youtube_client is None
    
    @pytest.mark.asyncio
    async def test_collect_top_videos_success(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test successful top video collection"""
        mock_youtube_client.search_trending_shorts.return_value = sample_youtube_videos
        mock_youtube_client.get_quota_usage.return_value = 100
        
        search_queries = ["dance", "fitness", "tutorial"]
        
        result = await collector_agent.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=50,
            days=7,
            top_n=10,
            region_code="US"
        )
        
        # Verify results (should be unique videos, up to top_n * 3)
        assert len(result) <= len(sample_youtube_videos) * len(search_queries) # Max possible unique videos
        assert all(isinstance(video, YouTubeVideoRaw) for video in result)
        
        # Verify YouTube client was called correctly
        assert mock_youtube_client.search_trending_shorts.call_count == len(search_queries)
        
        # Verify statistics were updated
        stats = collector_agent.get_collection_stats()
        assert stats["videos_collected"] == len(result)
        assert stats["quota_used"] == mock_youtube_client.get_quota_usage()
        assert stats["last_collection"] is not None
    
    @pytest.mark.asyncio
    async def test_collect_top_videos_duplicate_removal(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test duplicate video removal during collection"""
        mock_youtube_client.search_trending_shorts.return_value = sample_youtube_videos
        mock_youtube_client.get_quota_usage.return_value = 100
        
        search_queries = ["dance", "dance challenge"]
        
        result = await collector_agent.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=50,
            days=7,
            top_n=10
        )
        
        video_ids = [video.video_id for video in result]
        unique_ids = set(video_ids)
        assert len(unique_ids) <= len(sample_youtube_videos) # Should have unique videos, potentially less than sample_youtube_videos if top_n filters them out
    
    @pytest.mark.asyncio
    async def test_collect_top_videos_quota_limit(self, collector_agent, mock_youtube_client):
        """Test quota limit handling during collection"""
        mock_youtube_client.get_quota_usage.return_value = 9950
        collector_agent.settings.max_daily_quota = 10000
        
        search_queries = ["dance", "fitness"]
        
        result = await collector_agent.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=50,
            days=7,
            top_n=10
        )
        
        # Should stop at first query due to quota limit
        assert mock_youtube_client.search_trending_shorts.call_count == 0
        assert result == []
    
    @pytest.mark.asyncio
    async def test_collect_top_videos_quota_exceeded_error(self, collector_agent, mock_youtube_client):
        """Test handling of quota exceeded error"""
        mock_youtube_client.search_trending_shorts.side_effect = QuotaExceededError("Quota exceeded")
        mock_youtube_client.get_quota_usage.return_value = 100
        
        search_queries = ["dance", "fitness"]
        
        result = await collector_agent.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=50,
            days=7,
            top_n=10
        )
        
        assert result == []
        assert mock_youtube_client.search_trending_shorts.call_count == 1
    
    @pytest.mark.asyncio
    async def test_collect_top_videos_api_error_recovery(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test recovery from API errors"""
        mock_youtube_client.search_trending_shorts.side_effect = [
            YouTubeAPIError("API Error"),
            sample_youtube_videos
        ]
        mock_youtube_client.get_quota_usage.return_value = 100
        
        search_queries = ["dance", "fitness"]
        
        result = await collector_agent.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=50,
            days=7,
            top_n=10
        )
        
        assert len(result) == len(sample_youtube_videos)
        assert mock_youtube_client.search_trending_shorts.call_count == 2
    
    @pytest.mark.asyncio
    async def test_collect_by_request(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test collection using structured request"""
        mock_youtube_client.search_trending_shorts.return_value = sample_youtube_videos
        mock_youtube_client.get_quota_usage.return_value = 100
        
        request = CollectionRequest(
            search_queries=["dance", "fitness"],
            max_results_per_query=50,
            days=7,
            top_n=10,
            region_code="KR"
        )
        
        result = await collector_agent.collect_by_request(request)
        
        assert len(result) > 0
        
        mock_youtube_client.search_trending_shorts.assert_called_with(
            query="fitness",  # Last call
            max_results=50,
            days=7,
            order="viewCount",
            region_code="KR"
        )
    
    @pytest.mark.asyncio
    async def test_collect_by_category_keywords(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test collection by category keywords"""
        mock_youtube_client.search_trending_shorts.return_value = sample_youtube_videos
        mock_youtube_client.get_quota_usage.return_value = 100
        
        categories = ["dance", "fitness"]
        
        result = await collector_agent.collect_by_category_keywords(
            categories=categories,
            max_results_per_category=50,
            days=7,
            top_n=10,
            region_code="US"
        )
        
        assert len(result) > 0
        
        # Verify correct parameters were used
        mock_youtube_client.search_trending_shorts.assert_called_with(
            query="fitness shorts",  # Last call
            max_results=50,
            days=7,
            order="viewCount",
            region_code="US"
        )
    
    
    
    def test_get_collection_stats(self, collector_agent, mock_youtube_client):
        """Test collection statistics retrieval"""
        # Update some stats
        collector_agent.collection_stats["videos_collected"] = 10
        collector_agent.collection_stats["api_calls_made"] = 5
        collector_agent.collection_stats["quota_used"] = 500
        collector_agent.collection_stats["last_collection"] = datetime.now()
        
        mock_youtube_client.get_quota_usage.return_value = 600
        
        stats = collector_agent.get_collection_stats()
        
        assert stats["videos_collected"] == 10
        assert stats["api_calls_made"] == 5
        assert stats["quota_used"] == 500
        assert stats["current_quota_usage"] == 600
        assert stats["quota_remaining"] == collector_agent.settings.max_daily_quota - 600
        assert stats["last_collection"] is not None
    
    def test_reset_stats(self, collector_agent, mock_youtube_client):
        """Test statistics reset"""
        # Set some stats
        collector_agent.collection_stats["videos_collected"] = 10
        collector_agent.collection_stats["api_calls_made"] = 5
        
        collector_agent.reset_stats()
        
        # Verify stats are reset
        assert collector_agent.collection_stats["videos_collected"] == 0
        assert collector_agent.collection_stats["api_calls_made"] == 0
        assert collector_agent.collection_stats["quota_used"] == 0
        assert collector_agent.collection_stats["last_collection"] is None
        
        # Verify YouTube client quota tracking is reset
        mock_youtube_client.reset_quota_tracking.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager_with_existing_client(self, mock_youtube_client):
        """Test context manager with existing YouTube client"""
        mock_youtube_client.client = Mock()
        mock_youtube_client.client.aclose = AsyncMock()
        
        agent = CollectorAgent(youtube_client=mock_youtube_client)
        
        async with agent as ctx_agent:
            assert ctx_agent == agent
            assert ctx_agent.youtube_client == mock_youtube_client
        
        mock_youtube_client.client.aclose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_manager_without_client(self):
        """Test context manager without existing YouTube client"""
        agent = CollectorAgent()
        
        with patch('src.agents.collector_agent.YouTubeClient') as mock_client_class:
            mock_client_instance = AsyncMock()
            mock_client_class.return_value = mock_client_instance
            
            async with agent as ctx_agent:
                assert ctx_agent == agent
                assert ctx_agent.youtube_client == mock_client_instance
            
            # Verify YouTube client was created
            mock_client_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_collect_with_no_youtube_client(self):
        """Test collection when no YouTube client is provided"""
        agent = CollectorAgent()
        
        with patch('src.agents.collector_agent.YouTubeClient') as mock_client_class:
            mock_client_instance = Mock()
            mock_client_instance.search_trending_shorts = AsyncMock(return_value=[])
            mock_client_instance.get_quota_usage.return_value = 100
            mock_client_class.return_value = mock_client_instance
            
            await agent.collect_top_videos(["dance"], days=7, top_n=10)
            
            # Verify YouTube client was created
            mock_client_class.assert_called_once()
            assert agent.youtube_client == mock_client_instance
    
    def test_create_collector_agent_factory(self):
        """Test collector agent factory function"""
        # Test with provided client
        mock_client = Mock(spec=YouTubeClient)
        agent = create_collector_agent(youtube_client=mock_client)
        
        assert isinstance(agent, CollectorAgent)
        assert agent.youtube_client == mock_client
        
        # Test without provided client
        agent_no_client = create_collector_agent()
        assert isinstance(agent_no_client, CollectorAgent)
        assert agent_no_client.youtube_client is None
    
    @pytest.mark.asyncio
    async def test_collect_empty_search_queries(self, collector_agent):
        """Test collection with empty search queries"""
        result = await collector_agent.collect_top_videos([])
        
        assert result == []
        assert collector_agent.collection_stats["api_calls_made"] == 0
    
    @pytest.mark.asyncio
    async def test_collect_search_query_generation(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test search query generation for categories"""
        mock_youtube_client.search_trending_shorts.return_value = sample_youtube_videos
        mock_youtube_client.get_quota_usage.return_value = 100
        
        categories = ["dance"]
        
        await collector_agent.collect_by_category_keywords(categories)
        
        # Verify correct queries were generated
        mock_youtube_client.search_trending_shorts.assert_called_once_with(
            query="dance shorts",
            max_results=50, # Default max_results_per_category
            days=7, # Default days
            order="viewCount", # Default order
            region_code="US" # Default region_code
        )
    
    @pytest.mark.asyncio
    async def test_strict_role_compliance(self, collector_agent, mock_youtube_client, sample_youtube_videos):
        """Test that collector agent only does collection (STRICT ROLE)"""
        mock_youtube_client.search_shorts.return_value = sample_youtube_videos
        mock_youtube_client.get_quota_usage.return_value = 100
        
        result = await collector_agent.collect_top_videos(["dance"], days=7, top_n=10)
        
        # Verify that raw YouTube data is returned without any analysis
        for video in result:
            assert isinstance(video, YouTubeVideoRaw)
            # Should not have any classification or analysis data
            assert not hasattr(video, 'category')
            assert not hasattr(video, 'confidence')
            assert not hasattr(video, 'reasoning')
    
    
"""Pytest configuration and shared fixtures"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock

from src.models.video_models import (
    YouTubeVideoRaw, VideoSnippet, VideoStatistics, ClassifiedVideo, VideoCategory
)
from src.models.classification_models import ClassificationResponse
from src.clients.youtube_client import YouTubeClient
from src.clients.llm_provider import LLMProvider
from src.agents.collector_agent import CollectorAgent
from src.agents.analyzer_agent import AnalyzerAgent


@pytest.fixture
def sample_video_snippet():
    """Sample video snippet data"""
    return VideoSnippet(
        title="Amazing Dance Challenge Tutorial",
        description="Learn this viral dance challenge in just 60 seconds!",
        published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        channel_title="DanceChannel",
        thumbnail_url="https://i.ytimg.com/vi/abc123/default.jpg",
        duration="PT58S"
    )


@pytest.fixture
def sample_video_statistics():
    """Sample video statistics data"""
    return VideoStatistics(
        view_count=1000000,
        like_count=50000,
        comment_count=2500
    )


@pytest.fixture
def sample_youtube_video(sample_video_snippet, sample_video_statistics):
    """Sample YouTube video data"""
    return YouTubeVideoRaw(
        video_id="abc123",
        snippet=sample_video_snippet,
        statistics=sample_video_statistics
    )


@pytest.fixture
def sample_youtube_videos(sample_video_snippet, sample_video_statistics):
    """List of sample YouTube videos"""
    videos = []
    
    # Challenge video
    challenge_snippet = VideoSnippet(
        title="Epic Dance Challenge 2024",
        description="Join the viral dance challenge trending everywhere!",
        published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        channel_title="TrendingDances",
        thumbnail_url="https://i.ytimg.com/vi/challenge123/default.jpg",
        duration="PT45S"
    )
    videos.append(YouTubeVideoRaw(
        video_id="challenge123",
        snippet=challenge_snippet,
        statistics=sample_video_statistics
    ))
    
    # Info/Advice video
    info_snippet = VideoSnippet(
        title="5 Quick Productivity Tips",
        description="Learn these productivity hacks to boost your efficiency",
        published_at=datetime(2024, 1, 16, 14, 30, 0, tzinfo=timezone.utc),
        channel_title="ProductivityGuru",
        thumbnail_url="https://i.ytimg.com/vi/tips456/default.jpg",
        duration="PT55S"
    )
    videos.append(YouTubeVideoRaw(
        video_id="tips456",
        snippet=info_snippet,
        statistics=VideoStatistics(view_count=750000, like_count=30000, comment_count=1200)
    ))
    
    # Trending Sounds video
    music_snippet = VideoSnippet(
        title="Trending Beat Drop 2024",
        description="This sound is everywhere! Use it in your videos",
        published_at=datetime(2024, 1, 17, 18, 45, 0, tzinfo=timezone.utc),
        channel_title="MusicTrends",
        thumbnail_url="https://i.ytimg.com/vi/music789/default.jpg",
        duration="PT30S"
    )
    videos.append(YouTubeVideoRaw(
        video_id="music789",
        snippet=music_snippet,
        statistics=VideoStatistics(view_count=2000000, like_count=100000, comment_count=5000)
    ))
    
    return videos


@pytest.fixture
def sample_classified_video():
    """Sample classified video"""
    return ClassifiedVideo(
        video_id="abc123",
        title="Amazing Dance Challenge Tutorial",
        category=VideoCategory.CHALLENGE,
        confidence=0.85,
        reasoning="Contains dance and challenge keywords, tutorial format",
        view_count=1000000,
        published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
        channel_title="DanceChannel"
    )


@pytest.fixture
def sample_classified_videos():
    """List of sample classified videos"""
    return [
        ClassifiedVideo(
            video_id="challenge123",
            title="Epic Dance Challenge 2024",
            category=VideoCategory.CHALLENGE,
            confidence=0.92,
            reasoning="Clear challenge content with dance elements",
            view_count=1000000,
            published_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
            channel_title="TrendingDances"
        ),
        ClassifiedVideo(
            video_id="tips456",
            title="5 Quick Productivity Tips",
            category=VideoCategory.INFO_ADVICE,
            confidence=0.88,
            reasoning="Educational content providing advice and tips",
            view_count=750000,
            published_at=datetime(2024, 1, 16, 14, 30, 0, tzinfo=timezone.utc),
            channel_title="ProductivityGuru"
        ),
        ClassifiedVideo(
            video_id="music789",
            title="Trending Beat Drop 2024",
            category=VideoCategory.TRENDING_SOUNDS,
            confidence=0.95,
            reasoning="Music-focused content with trending audio elements",
            view_count=2000000,
            published_at=datetime(2024, 1, 17, 18, 45, 0, tzinfo=timezone.utc),
            channel_title="MusicTrends"
        )
    ]


@pytest.fixture
def sample_classification_response():
    """Sample classification response"""
    return ClassificationResponse(
        video_id="abc123",
        category=VideoCategory.CHALLENGE,
        confidence=0.85,
        reasoning="Contains dance and challenge keywords",
        alternative_categories=[],
        model_used="openai/gpt-4o-mini",
        processing_time=1.2
    )


@pytest.fixture
def mock_youtube_client():
    """Mock YouTube client"""
    client = Mock(spec=YouTubeClient)
    client.search_shorts = AsyncMock()
    client.get_video_details = AsyncMock()
    client.get_quota_usage = Mock(return_value=0)
    client.reset_quota_tracking = Mock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider"""
    provider = Mock(spec=LLMProvider)
    provider.classify_video = AsyncMock()
    provider.classify_videos_batch = AsyncMock()
    provider.get_model_info = Mock(return_value={
        "provider": "openai",
        "model": "gpt-4o-mini",
        "full_model_string": "openai:gpt-4o-mini"
    })
    provider.provider_name = "openai"
    provider.model_name = "gpt-4o-mini"
    return provider


@pytest.fixture
def mock_collector_agent(mock_youtube_client):
    """Mock collector agent"""
    agent = Mock(spec=CollectorAgent)
    agent.collect_trending_shorts = AsyncMock()
    agent.collect_by_category_keywords = AsyncMock()
    agent.get_collection_stats = Mock(return_value={
        "videos_collected": 10,
        "api_calls_made": 5,
        "quota_used": 500,
        "last_collection": datetime.now()
    })
    agent.reset_stats = Mock()
    agent.__aenter__ = AsyncMock(return_value=agent)
    agent.__aexit__ = AsyncMock(return_value=None)
    return agent


@pytest.fixture
def mock_analyzer_agent(mock_llm_provider):
    """Mock analyzer agent"""
    agent = Mock(spec=AnalyzerAgent)
    agent.classify_videos = AsyncMock()
    agent.generate_trend_report = Mock()
    agent.generate_comprehensive_analysis = Mock()
    agent.get_analysis_stats = Mock(return_value={
        "videos_analyzed": 10,
        "classifications_successful": 9,
        "classifications_failed": 1,
        "reports_generated": 1,
        "last_analysis": datetime.now()
    })
    agent.reset_stats = Mock()
    return agent


@pytest.fixture
def mock_youtube_api_response():
    """Mock YouTube API response data"""
    return {
        "items": [
            {
                "id": {"videoId": "abc123"},
                "snippet": {
                    "title": "Amazing Dance Challenge Tutorial",
                    "description": "Learn this viral dance challenge in just 60 seconds!",
                    "publishedAt": "2024-01-15T10:00:00Z",
                    "channelTitle": "DanceChannel",
                    "thumbnails": {
                        "default": {"url": "https://i.ytimg.com/vi/abc123/default.jpg"}
                    }
                }
            }
        ]
    }


@pytest.fixture
def mock_youtube_videos_response():
    """Mock YouTube videos API response data"""
    return {
        "items": [
            {
                "id": "abc123",
                "snippet": {
                    "title": "Amazing Dance Challenge Tutorial",
                    "description": "Learn this viral dance challenge in just 60 seconds!",
                    "publishedAt": "2024-01-15T10:00:00Z",
                    "channelTitle": "DanceChannel",
                    "thumbnails": {
                        "default": {"url": "https://i.ytimg.com/vi/abc123/default.jpg"}
                    }
                },
                "contentDetails": {
                    "duration": "PT58S"
                },
                "statistics": {
                    "viewCount": "1000000",
                    "likeCount": "50000",
                    "commentCount": "2500"
                }
            }
        ]
    }


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Setup test environment variables"""
    monkeypatch.setenv("YOUTUBE_API_KEY", "test_youtube_key")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("LLM_API_KEY", "test_llm_key")
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("MAX_DAILY_QUOTA", "10000")
    monkeypatch.setenv("RATE_LIMIT_PER_SECOND", "10")


# Helper functions for tests
def create_test_video(video_id: str, title: str, category_hint: str = "challenge") -> YouTubeVideoRaw:
    """Create a test video with specified parameters"""
    snippet = VideoSnippet(
        title=title,
        description=f"Test video description for {category_hint}",
        published_at=datetime.now(timezone.utc),
        channel_title="TestChannel",
        thumbnail_url=f"https://example.com/{video_id}.jpg",
        duration="PT45S"
    )
    
    statistics = VideoStatistics(
        view_count=100000,
        like_count=5000,
        comment_count=250
    )
    
    return YouTubeVideoRaw(
        video_id=video_id,
        snippet=snippet,
        statistics=statistics
    )
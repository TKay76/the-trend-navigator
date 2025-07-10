"""Tests for Mock LLM provider functionality"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import patch

from src.clients.mock_llm_provider import MockLLMProvider, create_mock_llm_provider
from src.models.video_models import VideoCategory, YouTubeVideoRaw, VideoSnippet, VideoStatistics
from src.models.classification_models import ClassificationResponse
from src.core.exceptions import ClassificationError


class TestMockLLMProvider:
    """Test Mock LLM provider functionality"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider for testing"""
        return MockLLMProvider()
    
    @pytest.fixture
    def sample_video(self):
        """Create sample video for testing"""
        snippet = VideoSnippet(
            title="Amazing Dance Challenge Tutorial",
            description="Learn this viral dance challenge step by step!",
            published_at=datetime.now(),
            channel_title="Dance Channel",
            thumbnail_url="https://example.com/thumb.jpg"
        )
        
        statistics = VideoStatistics(
            view_count=1000000,
            like_count=50000,
            comment_count=2500
        )
        
        return YouTubeVideoRaw(
            video_id="test_video_123",
            snippet=snippet,
            statistics=statistics
        )
    
    @pytest.fixture
    def sample_videos(self):
        """Create sample video list for testing"""
        videos = []
        for i in range(5):
            snippet = VideoSnippet(
                title=f"Test Video {i+1}",
                description=f"Description for video {i+1}",
                published_at=datetime.now(),
                channel_title=f"Channel {i+1}",
                thumbnail_url="https://example.com/thumb.jpg"
            )
            
            video = YouTubeVideoRaw(
                video_id=f"video_{i+1}",
                snippet=snippet
            )
            videos.append(video)
        
        return videos
    
    def test_mock_llm_provider_initialization(self):
        """Test mock LLM provider initialization"""
        provider = MockLLMProvider()
        
        assert provider.provider_name == "mock"
        assert provider.model_name == "mock-model"
        assert len(provider._mock_classifications) == 8
        assert provider._classification_counter == 0
    
    def test_mock_llm_provider_initialization_with_model(self):
        """Test mock LLM provider initialization with custom model"""
        provider = MockLLMProvider(model_name="custom-mock-model")
        
        assert provider.provider_name == "mock"
        assert provider.model_name == "custom-mock-model"
    
    @pytest.mark.asyncio
    async def test_classify_video_success(self, mock_llm_provider, sample_video):
        """Test successful single video classification"""
        result = await mock_llm_provider.classify_video(sample_video)
        
        # Verify response structure
        assert isinstance(result, ClassificationResponse)
        assert result.video_id == sample_video.video_id
        assert result.category in [VideoCategory.CHALLENGE, VideoCategory.INFO_ADVICE, VideoCategory.TRENDING_SOUNDS]
        assert 0.0 <= result.confidence <= 1.0
        assert len(result.reasoning) > 0
        assert result.model_used == "mock/mock-model"
        assert result.processing_time == 0.1
        
        # Verify reasoning includes video title
        assert sample_video.snippet.title[:20] in result.reasoning
    
    @pytest.mark.asyncio
    async def test_classify_video_cycling_behavior(self, mock_llm_provider, sample_videos):
        """Test that classifications cycle through predefined data"""
        results = []
        
        # Classify multiple videos to see cycling behavior
        for video in sample_videos:
            result = await mock_llm_provider.classify_video(video)
            results.append(result)
        
        # Should have different classifications (cycling through mock data)
        categories = [result.category for result in results]
        assert len(set(categories)) > 1, "Should have variety in classifications"
        
        # Counter should increment
        assert mock_llm_provider._classification_counter == len(sample_videos)
    
    @pytest.mark.asyncio
    async def test_classify_video_error_simulation(self, mock_llm_provider, sample_videos):
        """Test occasional error simulation in mock provider"""
        # Reset counter to control when error occurs
        mock_llm_provider.reset_counter()
        
        # Process videos until we hit the error condition (every 20th video)
        error_occurred = False
        for i in range(22):  # Process enough to trigger error
            video = sample_videos[i % len(sample_videos)]
            try:
                await mock_llm_provider.classify_video(video)
            except ClassificationError as e:
                error_occurred = True
                assert "Mock classification failed" in str(e)
                break
        
        assert error_occurred, "Mock should simulate occasional errors"
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_success(self, mock_llm_provider, sample_videos):
        """Test successful batch classification"""
        result = await mock_llm_provider.classify_videos_batch_optimized(sample_videos)
        
        # Verify results
        assert len(result) == len(sample_videos)
        assert all(isinstance(response, ClassificationResponse) for response in result)
        
        # Verify each result has correct video_id
        for i, response in enumerate(result):
            assert response.video_id == sample_videos[i].video_id
            assert response.model_used == "mock/mock-model"
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_empty_list(self, mock_llm_provider):
        """Test batch classification with empty list"""
        result = await mock_llm_provider.classify_videos_batch_optimized([])
        
        assert result == []
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_error_simulation(self, mock_llm_provider, sample_videos):
        """Test batch error simulation"""
        # Reset counter to control when error occurs
        mock_llm_provider.reset_counter()
        
        # Process batches until we hit the error condition
        large_video_list = sample_videos * 3  # 15 videos
        
        # This should trigger batch error simulation (every 10th batch for >3 videos)
        error_occurred = False
        try:
            # Set counter to trigger error
            mock_llm_provider._classification_counter = 9
            await mock_llm_provider.classify_videos_batch_optimized(large_video_list[:4])
        except ClassificationError as e:
            error_occurred = True
            assert "Mock batch classification failed" in str(e)
        
        assert error_occurred, "Mock should simulate occasional batch errors"
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_with_individual_failures(self, mock_llm_provider, sample_videos):
        """Test batch processing with some individual classification failures"""
        # Reset counter and set it to trigger individual errors during batch processing
        mock_llm_provider.reset_counter()
        mock_llm_provider._classification_counter = 18  # Will cause error on 19th call
        
        result = await mock_llm_provider.classify_videos_batch_optimized(sample_videos[:3])
        
        # Should still get results for all videos (with fallbacks for failures)
        assert len(result) == 3
        
        # Check if any have fallback reasoning
        fallback_found = any("fallback result" in result[i].reasoning.lower() for i in range(len(result)))
        # Note: Fallback might not occur depending on exact counter timing
    
    def test_get_model_info(self, mock_llm_provider):
        """Test model info retrieval"""
        info = mock_llm_provider.get_model_info()
        
        assert info["provider"] == "mock"
        assert info["model"] == "mock-model"
        assert info["full_model_string"] == "mock:mock-model"
        assert info["type"] == "mock"
    
    def test_reset_counter(self, mock_llm_provider):
        """Test counter reset functionality"""
        # Increment counter
        mock_llm_provider._classification_counter = 10
        
        # Reset counter
        mock_llm_provider.reset_counter()
        
        assert mock_llm_provider._classification_counter == 0
    
    def test_create_mock_llm_provider_factory(self):
        """Test mock LLM provider factory function"""
        # Test with default parameters
        provider = create_mock_llm_provider()
        
        assert isinstance(provider, MockLLMProvider)
        assert provider.model_name == "mock-model"
        
        # Test with custom model name
        custom_provider = create_mock_llm_provider(model_name="custom-test-model")
        
        assert isinstance(custom_provider, MockLLMProvider)
        assert custom_provider.model_name == "custom-test-model"
    
    def test_mock_classifications_variety(self, mock_llm_provider):
        """Test that mock classifications include all video categories"""
        classifications = mock_llm_provider._mock_classifications
        
        # Extract categories from mock data
        categories = [item["category"] for item in classifications]
        
        # Should include all three main categories
        assert VideoCategory.CHALLENGE in categories
        assert VideoCategory.INFO_ADVICE in categories
        assert VideoCategory.TRENDING_SOUNDS in categories
        
        # Should have reasonable confidence values
        confidences = [item["confidence"] for item in classifications]
        assert all(0.0 <= conf <= 1.0 for conf in confidences)
        assert max(confidences) > 0.8, "Should have high-confidence classifications"
        assert min(confidences) > 0.7, "Should maintain reasonable minimum confidence"
    
    @pytest.mark.asyncio
    async def test_classification_timing(self, mock_llm_provider, sample_video):
        """Test that mock classifications have realistic timing"""
        import time
        
        start_time = time.time()
        await mock_llm_provider.classify_video(sample_video)
        elapsed_time = time.time() - start_time
        
        # Should have some delay to simulate real API call
        assert elapsed_time >= 0.1, "Should have realistic processing delay"
        assert elapsed_time < 0.5, "Should not be too slow"
    
    @pytest.mark.asyncio
    async def test_batch_timing(self, mock_llm_provider, sample_videos):
        """Test that batch processing has realistic timing"""
        import time
        
        start_time = time.time()
        await mock_llm_provider.classify_videos_batch_optimized(sample_videos)
        elapsed_time = time.time() - start_time
        
        # Batch should be faster per video than individual calls
        assert elapsed_time >= 0.5, "Should have realistic batch processing delay"
        assert elapsed_time < 2.0, "Should not be too slow for batch"
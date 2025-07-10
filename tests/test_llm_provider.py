"""Comprehensive tests for LLM provider with batch processing and retry logic"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.clients.llm_provider import LLMProvider, ClassificationResult
from src.models.video_models import VideoCategory, YouTubeVideoRaw, VideoSnippet, VideoStatistics
from src.models.classification_models import ClassificationResponse
from src.core.exceptions import ClassificationError


class TestLLMProviderBatching:
    """Test LLM provider batch processing functionality"""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create mock LLM provider for testing"""
        with patch('src.clients.llm_provider.get_settings') as mock_settings:
            mock_settings.return_value.llm_model = "gemini-1.5-flash"
            mock_settings.return_value.llm_provider = "gemini"
            
            provider = LLMProvider()
            provider.classification_agent = AsyncMock()
            return provider
    
    @pytest.fixture
    def sample_videos(self):
        """Create sample video data for testing"""
        videos = []
        for i in range(3):
            snippet = VideoSnippet(
                title=f"Test Video {i+1}",
                description=f"Description for video {i+1}",
                published_at=datetime.now(),
                channel_title=f"Channel {i+1}",
                thumbnail_url="https://example.com/thumb.jpg"
            )
            
            statistics = VideoStatistics(
                view_count=1000 * (i + 1),
                like_count=100 * (i + 1),
                comment_count=10 * (i + 1)
            )
            
            video = YouTubeVideoRaw(
                video_id=f"video_{i+1}",
                snippet=snippet,
                statistics=statistics
            )
            videos.append(video)
        
        return videos
    
    @pytest.fixture
    def sample_batch_response(self):
        """Create sample batch response JSON"""
        return ClassificationResult(
            category=VideoCategory.CHALLENGE,
            confidence=0.85,
            reasoning="""{
  "video_1": {"category": "Challenge", "confidence": 0.95, "reasoning": "Dance challenge video"},
  "video_2": {"category": "Info/Advice", "confidence": 0.87, "reasoning": "Educational content"},
  "video_3": {"category": "Trending Sounds/BGM", "confidence": 0.78, "reasoning": "Music-focused content"}
}""",
            keywords=[]
        )
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_success(self, mock_llm_provider, sample_videos, sample_batch_response):
        """Test successful batch classification"""
        # Mock successful agent response
        mock_result = Mock()
        mock_result.data = sample_batch_response
        mock_llm_provider.classification_agent.run.return_value = mock_result
        
        # Execute batch classification
        result = await mock_llm_provider.classify_videos_batch_optimized(sample_videos, batch_size=3)
        
        # Verify results
        assert len(result) == 3
        assert all(isinstance(response, ClassificationResponse) for response in result)
        
        # Verify specific classifications
        assert result[0].video_id == "video_1"
        assert result[0].category == VideoCategory.CHALLENGE
        assert result[0].confidence == 0.95
        assert result[0].reasoning == "Dance challenge video"
        
        assert result[1].video_id == "video_2"
        assert result[1].category == VideoCategory.INFO_ADVICE
        assert result[1].confidence == 0.87
        
        assert result[2].video_id == "video_3"
        assert result[2].category == VideoCategory.TRENDING_SOUNDS
        assert result[2].confidence == 0.78
        
        # Verify agent was called only once (batch optimization)
        assert mock_llm_provider.classification_agent.run.call_count == 1
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_retry_logic(self, mock_llm_provider, sample_videos, sample_batch_response):
        """Test retry logic with 503 errors"""
        # Mock agent to fail first two attempts with 503, succeed on third
        mock_result = Mock()
        mock_result.data = sample_batch_response
        
        mock_llm_provider.classification_agent.run.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("Service Unavailable - rate limited"),
            mock_result
        ]
        
        # Execute with retry logic
        with patch('asyncio.sleep') as mock_sleep:  # Speed up test by mocking sleep
            result = await mock_llm_provider.classify_videos_batch_optimized(sample_videos, batch_size=3)
        
        # Verify successful result after retries
        assert len(result) == 3
        assert result[0].category == VideoCategory.CHALLENGE
        
        # Verify retry behavior
        assert mock_llm_provider.classification_agent.run.call_count == 3
        assert mock_sleep.call_count == 2  # Called for first two failures
        mock_sleep.assert_any_call(1)  # First retry: 2^0 = 1
        mock_sleep.assert_any_call(2)  # Second retry: 2^1 = 2
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_permanent_failure(self, mock_llm_provider, sample_videos):
        """Test behavior when all retry attempts fail"""
        # Mock agent to always fail with 503
        mock_llm_provider.classification_agent.run.side_effect = Exception("503 Service Unavailable")
        
        # Should raise ClassificationError after all retries
        with pytest.raises(ClassificationError) as exc_info:
            with patch('asyncio.sleep'):  # Speed up test
                await mock_llm_provider.classify_videos_batch_optimized(sample_videos, batch_size=3)
        
        assert "Service unavailable after retries" in str(exc_info.value)
        assert mock_llm_provider.classification_agent.run.call_count == 3  # All retry attempts
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_non_retryable_error(self, mock_llm_provider, sample_videos):
        """Test behavior with non-retryable errors"""
        # Mock agent to fail with non-retryable error
        mock_llm_provider.classification_agent.run.side_effect = Exception("Invalid API key")
        
        # Should raise ClassificationError immediately (no retries)
        with pytest.raises(ClassificationError) as exc_info:
            await mock_llm_provider.classify_videos_batch_optimized(sample_videos, batch_size=3)
        
        assert "Failed to classify batch" in str(exc_info.value)
        assert mock_llm_provider.classification_agent.run.call_count == 1  # No retries
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_empty_list(self, mock_llm_provider):
        """Test batch classification with empty video list"""
        result = await mock_llm_provider.classify_videos_batch_optimized([], batch_size=3)
        
        assert result == []
        assert mock_llm_provider.classification_agent.run.call_count == 0
    
    @pytest.mark.asyncio
    async def test_batch_prompt_creation(self, mock_llm_provider, sample_videos):
        """Test batch prompt formatting"""
        prompt = mock_llm_provider._create_batch_classification_prompt(sample_videos)
        
        # Verify prompt structure
        assert "Classify the following YouTube Shorts videos:" in prompt
        assert "VIDEO 1:" in prompt
        assert "VIDEO 2:" in prompt
        assert "VIDEO 3:" in prompt
        
        # Verify video data is included
        assert sample_videos[0].snippet.title in prompt
        assert sample_videos[1].snippet.title in prompt
        assert sample_videos[2].snippet.title in prompt
        
        # Verify JSON format specification
        assert "video_1" in prompt
        assert "video_2" in prompt
        assert "..." in prompt  # Template shows ... for additional videos
        assert "Challenge" in prompt
        assert "Info/Advice" in prompt
        assert "Trending Sounds/BGM" in prompt
    
    @pytest.mark.asyncio
    async def test_batch_result_parsing_success(self, mock_llm_provider, sample_videos, sample_batch_response):
        """Test parsing batch JSON response"""
        result = mock_llm_provider._parse_batch_classification_result(sample_batch_response, sample_videos)
        
        # Verify parsing results
        assert len(result) == 3
        assert all(isinstance(response, ClassificationResponse) for response in result)
        
        # Verify category mapping
        assert result[0].category == VideoCategory.CHALLENGE
        assert result[1].category == VideoCategory.INFO_ADVICE
        assert result[2].category == VideoCategory.TRENDING_SOUNDS
        
        # Verify confidence scores
        assert result[0].confidence == 0.95
        assert result[1].confidence == 0.87
        assert result[2].confidence == 0.78
    
    @pytest.mark.asyncio 
    async def test_batch_result_parsing_malformed_json(self, mock_llm_provider, sample_videos):
        """Test parsing with malformed JSON response"""
        malformed_response = ClassificationResult(
            category=VideoCategory.CHALLENGE,
            confidence=0.85,
            reasoning="This is not valid JSON at all",
            keywords=[]
        )
        
        # Mock the fallback response creation
        with patch.object(mock_llm_provider, '_create_fallback_responses') as mock_fallback:
            mock_fallback.return_value = [
                ClassificationResponse(
                    video_id="video_1",
                    category=VideoCategory.CHALLENGE,
                    confidence=0.3,
                    reasoning="Fallback classification due to parsing error",
                    alternative_categories=[],
                    model_used="test/model",
                    processing_time=0.0
                )
            ]
            
            result = mock_llm_provider._parse_batch_classification_result(malformed_response, sample_videos[:1])
            
            # Should use fallback
            assert len(result) == 1
            assert result[0].reasoning == "Fallback classification due to parsing error"
            mock_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fallback_individual_classification(self, mock_llm_provider, sample_videos):
        """Test fallback to individual classification"""
        # Mock individual classification responses
        individual_responses = [
            ClassificationResponse(
                video_id=f"video_{i+1}",
                category=VideoCategory.CHALLENGE,
                confidence=0.8,
                reasoning=f"Individual classification {i+1}",
                alternative_categories=[],
                model_used="test/model",
                processing_time=0.0
            )
            for i in range(len(sample_videos))
        ]
        
        with patch.object(mock_llm_provider, 'classify_video') as mock_classify:
            mock_classify.side_effect = individual_responses
            
            result = await mock_llm_provider._fallback_individual_classification(sample_videos)
            
            # Verify fallback results
            assert len(result) == 3
            assert mock_classify.call_count == 3
            assert all(response.reasoning.startswith("Individual classification") for response in result)
    
    @pytest.mark.asyncio
    async def test_fallback_with_partial_failures(self, mock_llm_provider, sample_videos):
        """Test fallback when some individual classifications fail"""
        # Mock individual classification with some failures
        responses_and_errors = [
            ClassificationResponse(
                video_id="video_1",
                category=VideoCategory.CHALLENGE,
                confidence=0.8,
                reasoning="Success",
                alternative_categories=[],
                model_used="test/model",
                processing_time=0.0
            ),
            ClassificationError("Classification failed"),
            ClassificationResponse(
                video_id="video_3",
                category=VideoCategory.INFO_ADVICE,
                confidence=0.7,
                reasoning="Success",
                alternative_categories=[],
                model_used="test/model",
                processing_time=0.0
            )
        ]
        
        with patch.object(mock_llm_provider, 'classify_video') as mock_classify:
            mock_classify.side_effect = responses_and_errors
            
            result = await mock_llm_provider._fallback_individual_classification(sample_videos)
            
            # Should have 3 results (2 successful + 1 fallback for failed)
            assert len(result) == 3
            assert result[0].reasoning == "Success"
            assert "Classification failed" in result[1].reasoning  # Fallback for failed classification
            assert result[2].reasoning == "Success"
    
    @pytest.mark.asyncio
    async def test_classify_video_retry_logic(self, mock_llm_provider):
        """Test retry logic in individual classify_video method"""
        # Create sample video
        video = YouTubeVideoRaw(
            video_id="test_video",
            snippet=VideoSnippet(
                title="Test Video",
                description="Test description",
                published_at=datetime.now(),
                channel_title="Test Channel",
                thumbnail_url="https://example.com/thumb.jpg"
            )
        )
        
        # Mock successful response after retries
        successful_result = ClassificationResult(
            category=VideoCategory.CHALLENGE,
            confidence=0.85,
            reasoning="Test classification",
            keywords=[]
        )
        
        mock_result = Mock()
        mock_result.data = successful_result
        
        # Fail first two attempts with 503, succeed on third
        mock_llm_provider.classification_agent.run.side_effect = [
            Exception("503 Service Unavailable"),
            Exception("429 Rate Limit Exceeded"),
            mock_result
        ]
        
        # Execute with retry logic
        with patch('asyncio.sleep') as mock_sleep:
            result = await mock_llm_provider.classify_video(video)
        
        # Verify successful result
        assert isinstance(result, ClassificationResponse)
        assert result.category == VideoCategory.CHALLENGE
        assert result.confidence == 0.85
        
        # Verify retry behavior
        assert mock_llm_provider.classification_agent.run.call_count == 3
        assert mock_sleep.call_count == 2
    
    @pytest.mark.asyncio
    async def test_classify_video_non_retryable_error(self, mock_llm_provider):
        """Test individual classification with non-retryable error"""
        # Create sample video  
        video = YouTubeVideoRaw(
            video_id="test_video",
            snippet=VideoSnippet(
                title="Test Video",
                description="Test description", 
                published_at=datetime.now(),
                channel_title="Test Channel",
                thumbnail_url="https://example.com/thumb.jpg"
            )
        )
        
        # Mock non-retryable error
        mock_llm_provider.classification_agent.run.side_effect = Exception("Invalid API key")
        
        # Should raise ClassificationError immediately
        with pytest.raises(ClassificationError) as exc_info:
            await mock_llm_provider.classify_video(video)
        
        assert "Failed to classify video" in str(exc_info.value)
        assert mock_llm_provider.classification_agent.run.call_count == 1  # No retries
    
    def test_batch_size_calculation(self, mock_llm_provider, sample_videos):
        """Test batch processing with different batch sizes"""
        # Test batch size larger than video count
        prompt = mock_llm_provider._create_batch_classification_prompt(sample_videos[:2])
        assert "VIDEO 1:" in prompt
        assert "VIDEO 2:" in prompt
        assert "VIDEO 3:" not in prompt
        
        # Test single video batch
        prompt_single = mock_llm_provider._create_batch_classification_prompt(sample_videos[:1])
        assert "VIDEO 1:" in prompt_single
        assert "VIDEO 2:" not in prompt_single
    
    def test_description_truncation(self, mock_llm_provider):
        """Test that long descriptions are properly truncated"""
        # Create video with very long description
        long_description = "A" * 500  # Longer than 200 char limit
        
        video = YouTubeVideoRaw(
            video_id="test_video",
            snippet=VideoSnippet(
                title="Test Video",
                description=long_description,
                published_at=datetime.now(),
                channel_title="Test Channel",
                thumbnail_url="https://example.com/thumb.jpg"
            )
        )
        
        prompt = mock_llm_provider._create_batch_classification_prompt([video])
        
        # Should be truncated with ellipsis
        assert "A" * 200 + "..." in prompt
        assert len([line for line in prompt.split('\n') if 'Description:' in line][0]) < 250
"""Tests for analysis agent"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.agents.analyzer_agent import AnalyzerAgent, create_analyzer_agent
from src.models.video_models import VideoCategory, ClassifiedVideo, TrendReport, YouTubeVideoRaw, VideoSnippet
from src.models.classification_models import TrendAnalysisResult, ClassificationResponse
from src.core.exceptions import ClassificationError


class TestAnalyzerAgent:
    """Test analysis agent functionality"""
    
    @pytest.fixture
    def analyzer_agent(self, mock_llm_provider):
        """Create analyzer agent with mock LLM provider"""
        return AnalyzerAgent(llm_provider=mock_llm_provider)
    
    def test_analyzer_agent_initialization(self, mock_llm_provider):
        """Test analyzer agent initialization"""
        agent = AnalyzerAgent(llm_provider=mock_llm_provider)
        
        assert agent.agent_name == "AnalyzerAgent"
        assert agent.llm_provider == mock_llm_provider
        assert agent.analysis_stats["videos_analyzed"] == 0
        assert agent.analysis_stats["classifications_successful"] == 0
        assert agent.analysis_stats["classifications_failed"] == 0
        assert agent.analysis_stats["reports_generated"] == 0
        assert agent.analysis_stats["last_analysis"] is None
    
    def test_analyzer_agent_initialization_without_provider(self):
        """Test analyzer agent initialization without LLM provider"""
        with patch('src.agents.analyzer_agent.create_llm_provider') as mock_create:
            mock_provider = Mock()
            mock_create.return_value = mock_provider
            
            agent = AnalyzerAgent()
            
            assert agent.llm_provider == mock_provider
            mock_create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_classify_videos_success(self, analyzer_agent, mock_llm_provider, sample_youtube_videos, sample_classification_response):
        """Test successful video classification with batch processing"""
        # Create batch responses with matching video IDs
        def create_matching_responses(videos, batch_size):
            return [
                ClassificationResponse(
                    video_id=video.video_id,
                    category=sample_classification_response.category,
                    confidence=sample_classification_response.confidence,
                    reasoning=sample_classification_response.reasoning,
                    alternative_categories=[],
                    model_used=sample_classification_response.model_used,
                    processing_time=sample_classification_response.processing_time
                )
                for video in videos
            ]
        
        mock_llm_provider.classify_videos_batch_optimized.side_effect = create_matching_responses
        
        result = await analyzer_agent.classify_videos(sample_youtube_videos)
        
        # Verify results
        assert len(result) == len(sample_youtube_videos)
        assert all(isinstance(video, ClassifiedVideo) for video in result)
        
        # Verify batch LLM provider was called
        mock_llm_provider.classify_videos_batch_optimized.assert_called()
        
        # Verify statistics were updated
        stats = analyzer_agent.get_analysis_stats()
        assert stats["videos_analyzed"] == len(sample_youtube_videos)
        assert stats["classifications_successful"] == len(sample_youtube_videos)
        assert stats["classifications_failed"] == 0
        assert stats["last_analysis"] is not None
    
    @pytest.mark.asyncio
    async def test_classify_videos_with_failures(self, analyzer_agent, mock_llm_provider, sample_youtube_videos, sample_classification_response):
        """Test video classification with batch failures and individual fallback"""
        # Configure mock batch to fail, then individual fallback to succeed for some
        mock_llm_provider.classify_videos_batch_optimized.side_effect = ClassificationError("Batch classification failed")
        mock_llm_provider.classify_video.side_effect = [
            sample_classification_response,  # First video succeeds
            ClassificationError("Individual classification failed"),  # Second video fails
            sample_classification_response   # Third video succeeds
        ]
        
        result = await analyzer_agent.classify_videos(sample_youtube_videos)
        
        # Should have 2 successful classifications (batch failed, 2 individual successes)
        assert len(result) == 2
        
        # Verify batch was attempted first
        mock_llm_provider.classify_videos_batch_optimized.assert_called()
        
        # Verify individual fallback was used
        assert mock_llm_provider.classify_video.call_count == len(sample_youtube_videos)
        
        # Verify statistics
        stats = analyzer_agent.get_analysis_stats()
        assert stats["videos_analyzed"] == len(sample_youtube_videos)
        assert stats["classifications_successful"] == 2
    
    @pytest.mark.asyncio
    async def test_classify_videos_empty_list(self, analyzer_agent):
        """Test classification with empty video list"""
        result = await analyzer_agent.classify_videos([])
        
        assert result == []
        
        stats = analyzer_agent.get_analysis_stats()
        assert stats["videos_analyzed"] == 0
        assert stats["classifications_successful"] == 0
        assert stats["classifications_failed"] == 0
    
    def test_generate_trend_report_single_category(self, analyzer_agent, sample_classified_videos):
        """Test trend report generation for single category"""
        # Filter to only challenge videos
        challenge_videos = [v for v in sample_classified_videos if v.category == VideoCategory.CHALLENGE]
        
        report = analyzer_agent.generate_trend_report(challenge_videos, VideoCategory.CHALLENGE)
        
        assert isinstance(report, TrendReport)
        assert report.category == VideoCategory.CHALLENGE
        assert len(report.key_insights) > 0
        assert len(report.recommended_actions) > 0
        assert len(report.top_videos) > 0
        assert report.total_videos_analyzed == len(challenge_videos)
        assert "Challenge" in report.trend_summary
        
        # Verify statistics updated
        stats = analyzer_agent.get_analysis_stats()
        assert stats["reports_generated"] == 1
    
    def test_generate_trend_report_all_categories(self, analyzer_agent, sample_classified_videos):
        """Test trend report generation for all categories"""
        report = analyzer_agent.generate_trend_report(sample_classified_videos)
        
        assert isinstance(report, TrendReport)
        # Should default to dominant category (Challenge in sample data)
        assert report.category == VideoCategory.CHALLENGE
        assert report.total_videos_analyzed > 0
    
    def test_generate_trend_report_empty_videos(self, analyzer_agent):
        """Test trend report generation with empty video list"""
        report = analyzer_agent.generate_trend_report([], VideoCategory.CHALLENGE)
        
        assert report.category == VideoCategory.CHALLENGE
        assert report.total_videos_analyzed == 0
        assert "No videos found" in report.trend_summary
        assert "No data available" in report.key_insights[0]
        assert "Collect more videos" in report.recommended_actions[0]
        assert len(report.top_videos) == 0
    
    def test_generate_comprehensive_analysis(self, analyzer_agent, sample_classified_videos):
        """Test comprehensive analysis generation"""
        analysis = analyzer_agent.generate_comprehensive_analysis(sample_classified_videos)
        
        assert isinstance(analysis, TrendAnalysisResult)
        assert analysis.total_videos_analyzed == len(sample_classified_videos)
        assert len(analysis.category_insights) > 0
        assert analysis.dominant_category in [VideoCategory.CHALLENGE, VideoCategory.INFO_ADVICE, VideoCategory.TRENDING_SOUNDS]
        assert len(analysis.emerging_trends) > 0
        assert len(analysis.recommended_content_strategy) > 0
        assert f"{analyzer_agent.llm_provider.provider_name}/{analyzer_agent.llm_provider.model_name}" in analysis.model_version
    
    def test_get_dominant_category(self, analyzer_agent, sample_classified_videos):
        """Test dominant category identification"""
        # Add more challenge videos to make it dominant
        challenge_videos = [v for v in sample_classified_videos if v.category == VideoCategory.CHALLENGE]
        challenge_videos.extend(challenge_videos)  # Duplicate to make dominant
        
        all_videos = sample_classified_videos + challenge_videos
        dominant = analyzer_agent._get_dominant_category(all_videos)
        
        assert dominant == VideoCategory.CHALLENGE
    
    def test_get_dominant_category_empty_list(self, analyzer_agent):
        """Test dominant category with empty list"""
        dominant = analyzer_agent._get_dominant_category([])
        assert dominant == VideoCategory.CHALLENGE  # Default fallback
    
    def test_analyze_category_trends(self, analyzer_agent, sample_classified_videos):
        """Test category trend analysis"""
        challenge_videos = [v for v in sample_classified_videos if v.category == VideoCategory.CHALLENGE]
        
        insights = analyzer_agent._analyze_category_trends(challenge_videos)
        
        assert len(insights) > 0
        assert any("confidence" in insight.lower() for insight in insights)
        
        # Should include view analysis if videos have view counts
        if any(v.view_count for v in challenge_videos):
            assert any("views" in insight.lower() for insight in insights)
    
    def test_analyze_category_trends_empty_list(self, analyzer_agent):
        """Test category trend analysis with empty list"""
        insights = analyzer_agent._analyze_category_trends([])
        
        assert insights == ["No videos to analyze"]
    
    def test_generate_recommendations_by_category(self, analyzer_agent, sample_classified_videos):
        """Test recommendation generation for different categories"""
        # Test Challenge category
        challenge_recs = analyzer_agent._generate_recommendations(VideoCategory.CHALLENGE, sample_classified_videos)
        assert any("viral" in rec.lower() or "challenge" in rec.lower() for rec in challenge_recs)
        
        # Test Info/Advice category
        info_recs = analyzer_agent._generate_recommendations(VideoCategory.INFO_ADVICE, sample_classified_videos)
        assert any("tips" in rec.lower() or "actionable" in rec.lower() for rec in info_recs)
        
        # Test Trending Sounds category
        sounds_recs = analyzer_agent._generate_recommendations(VideoCategory.TRENDING_SOUNDS, sample_classified_videos)
        assert any("sound" in rec.lower() or "music" in rec.lower() for rec in sounds_recs)
    
    def test_get_top_videos(self, analyzer_agent, sample_classified_videos):
        """Test top video selection"""
        top_videos = analyzer_agent._get_top_videos(sample_classified_videos, limit=2)
        
        assert len(top_videos) <= 2
        assert len(top_videos) <= len(sample_classified_videos)
        
        # Should be sorted by view count and confidence
        if len(top_videos) > 1:
            first_video = top_videos[0]
            second_video = top_videos[1]
            
            # First video should have >= views than second
            first_views = first_video.view_count or 0
            second_views = second_video.view_count or 0
            assert first_views >= second_views
    
    def test_get_top_videos_empty_list(self, analyzer_agent):
        """Test top video selection with empty list"""
        top_videos = analyzer_agent._get_top_videos([])
        assert top_videos == []
    
    def test_create_trend_summary(self, analyzer_agent, sample_classified_videos):
        """Test trend summary creation"""
        challenge_videos = [v for v in sample_classified_videos if v.category == VideoCategory.CHALLENGE]
        
        summary = analyzer_agent._create_trend_summary(VideoCategory.CHALLENGE, challenge_videos)
        
        assert len(summary) > 0
        assert str(len(challenge_videos)) in summary
        assert "Challenge" in summary
        assert "confidence" in summary.lower()
    
    def test_create_trend_summary_empty_videos(self, analyzer_agent):
        """Test trend summary creation with empty video list"""
        summary = analyzer_agent._create_trend_summary(VideoCategory.CHALLENGE, [])
        assert summary == "No trend data available"
    
    def test_create_category_insights(self, analyzer_agent, sample_classified_videos):
        """Test category insights creation"""
        challenge_videos = [v for v in sample_classified_videos if v.category == VideoCategory.CHALLENGE]
        
        insights = analyzer_agent._create_category_insights(VideoCategory.CHALLENGE, challenge_videos)
        
        assert insights.category == VideoCategory.CHALLENGE
        assert insights.video_count == len(challenge_videos)
        assert 0.0 <= insights.average_confidence <= 1.0
        assert len(insights.common_keywords) <= 10
        assert len(insights.trending_themes) <= 5
    
    def test_extract_common_keywords(self, analyzer_agent):
        """Test keyword extraction from text"""
        texts = [
            "Amazing dance challenge tutorial",
            "Best dance moves 2024",
            "Viral dance trends"
        ]
        
        keywords = analyzer_agent._extract_common_keywords(texts)
        
        assert "dance" in keywords
        assert len(keywords) <= 10
        
        # Test with empty list
        empty_keywords = analyzer_agent._extract_common_keywords([])
        assert empty_keywords == []
    
    def test_identify_themes_by_category(self, analyzer_agent):
        """Test theme identification for different categories"""
        # Challenge themes
        challenge_titles = ["Dance challenge tutorial", "Fitness workout challenge"]
        challenge_themes = analyzer_agent._identify_themes(VideoCategory.CHALLENGE, challenge_titles)
        assert any(theme in ["dance", "fitness", "challenge"] for theme in challenge_themes)
        
        # Info/Advice themes
        advice_titles = ["How to improve productivity", "Tips for better sleep"]
        advice_themes = analyzer_agent._identify_themes(VideoCategory.INFO_ADVICE, advice_titles)
        assert any(theme in ["how", "tips"] for theme in advice_themes)
        
        # Trending Sounds themes
        sound_titles = ["New trending music beat", "Popular song remix"]
        sound_themes = analyzer_agent._identify_themes(VideoCategory.TRENDING_SOUNDS, sound_titles)
        assert any(theme in ["music", "song"] for theme in sound_themes)
    
    def test_identify_emerging_trends(self, analyzer_agent, sample_classified_videos):
        """Test emerging trend identification"""
        trends = analyzer_agent._identify_emerging_trends(sample_classified_videos)
        
        assert len(trends) > 0
        assert all(isinstance(trend, str) for trend in trends)
    
    def test_generate_content_strategy(self, analyzer_agent, sample_classified_videos):
        """Test content strategy generation"""
        strategy = analyzer_agent._generate_content_strategy(sample_classified_videos)
        
        assert len(strategy) > 0
        assert all(isinstance(item, str) for item in strategy)
        
        # Should include category-specific strategies
        categories_mentioned = any(
            category.value in " ".join(strategy) 
            for category in VideoCategory
        )
        assert categories_mentioned
    
    def test_get_analysis_stats(self, analyzer_agent):
        """Test analysis statistics retrieval"""
        # Update some stats
        analyzer_agent.analysis_stats["videos_analyzed"] = 10
        analyzer_agent.analysis_stats["classifications_successful"] = 8
        analyzer_agent.analysis_stats["classifications_failed"] = 2
        analyzer_agent.analysis_stats["reports_generated"] = 1
        analyzer_agent.analysis_stats["last_analysis"] = datetime.now()
        
        stats = analyzer_agent.get_analysis_stats()
        
        assert stats["videos_analyzed"] == 10
        assert stats["classifications_successful"] == 8
        assert stats["classifications_failed"] == 2
        assert stats["reports_generated"] == 1
        assert stats["last_analysis"] is not None
    
    def test_reset_stats(self, analyzer_agent):
        """Test statistics reset"""
        # Set some stats
        analyzer_agent.analysis_stats["videos_analyzed"] = 10
        analyzer_agent.analysis_stats["classifications_successful"] = 8
        
        analyzer_agent.reset_stats()
        
        # Verify stats are reset
        assert analyzer_agent.analysis_stats["videos_analyzed"] == 0
        assert analyzer_agent.analysis_stats["classifications_successful"] == 0
        assert analyzer_agent.analysis_stats["classifications_failed"] == 0
        assert analyzer_agent.analysis_stats["reports_generated"] == 0
        assert analyzer_agent.analysis_stats["last_analysis"] is None
    
    def test_create_analyzer_agent_factory(self, mock_llm_provider):
        """Test analyzer agent factory function"""
        # Test with provided provider
        agent = create_analyzer_agent(llm_provider=mock_llm_provider)
        
        assert isinstance(agent, AnalyzerAgent)
        assert agent.llm_provider == mock_llm_provider
        
        # Test without provided provider
        with patch('src.agents.analyzer_agent.create_llm_provider') as mock_create:
            mock_provider = Mock()
            mock_create.return_value = mock_provider
            
            agent_no_provider = create_analyzer_agent()
            assert isinstance(agent_no_provider, AnalyzerAgent)
            assert agent_no_provider.llm_provider == mock_provider
    
    @pytest.mark.asyncio
    async def test_strict_role_compliance(self, analyzer_agent, mock_llm_provider, sample_youtube_videos, sample_classification_response):
        """Test that analyzer agent only does analysis (STRICT ROLE)"""
        # Configure batch processing mock
        batch_responses = [sample_classification_response for _ in sample_youtube_videos]
        mock_llm_provider.classify_videos_batch_optimized.return_value = batch_responses
        
        # Analyzer should not make external API calls
        # It should only receive data and perform analysis
        result = await analyzer_agent.classify_videos(sample_youtube_videos)
        
        # Verify only LLM provider was used (no YouTube API calls)
        assert mock_llm_provider.classify_videos_batch_optimized.called
        
        # Result should be analyzed/classified data
        for video in result:
            assert isinstance(video, ClassifiedVideo)
            assert hasattr(video, 'category')
            assert hasattr(video, 'confidence')
            assert hasattr(video, 'reasoning')
    
    def test_category_specific_recommendations(self, analyzer_agent):
        """Test that recommendations are appropriate for each category"""
        sample_videos = []  # Empty for this test
        
        # Test Challenge recommendations
        challenge_recs = analyzer_agent._generate_recommendations(VideoCategory.CHALLENGE, sample_videos)
        challenge_text = " ".join(challenge_recs).lower()
        assert "challenge" in challenge_text or "viral" in challenge_text or "dance" in challenge_text
        
        # Test Info/Advice recommendations  
        info_recs = analyzer_agent._generate_recommendations(VideoCategory.INFO_ADVICE, sample_videos)
        info_text = " ".join(info_recs).lower()
        assert "tips" in info_text or "advice" in info_text or "value" in info_text
        
        # Test Trending Sounds recommendations
        sounds_recs = analyzer_agent._generate_recommendations(VideoCategory.TRENDING_SOUNDS, sample_videos)
        sounds_text = " ".join(sounds_recs).lower()
        assert "sound" in sounds_text or "music" in sounds_text or "audio" in sounds_text
    
    @pytest.mark.asyncio 
    async def test_classification_data_conversion(self, analyzer_agent, mock_llm_provider, sample_youtube_video, sample_classification_response):
        """Test conversion from classification response to classified video"""
        # Configure batch processing mock
        mock_llm_provider.classify_videos_batch_optimized.return_value = [sample_classification_response]
        
        result = await analyzer_agent.classify_videos([sample_youtube_video])
        
        assert len(result) == 1
        classified_video = result[0]
        
        # Verify data was correctly converted
        assert classified_video.video_id == sample_classification_response.video_id
        assert classified_video.category == sample_classification_response.category
        assert classified_video.confidence == sample_classification_response.confidence
        assert classified_video.reasoning == sample_classification_response.reasoning
        
        # Verify original video data was preserved
        assert classified_video.title == sample_youtube_video.snippet.title
        assert classified_video.published_at == sample_youtube_video.snippet.published_at
        assert classified_video.channel_title == sample_youtube_video.snippet.channel_title
        
        if sample_youtube_video.statistics:
            assert classified_video.view_count == sample_youtube_video.statistics.view_count
    
    @pytest.mark.asyncio
    async def test_classify_videos_with_batching(self, analyzer_agent, mock_llm_provider, sample_youtube_videos, sample_classification_response):
        """Test video classification using batch processing"""
        # Create batch responses with matching video IDs
        def create_matching_batch_responses(videos, batch_size):
            return [
                ClassificationResponse(
                    video_id=video.video_id,
                    category=sample_classification_response.category,
                    confidence=sample_classification_response.confidence,
                    reasoning=sample_classification_response.reasoning,
                    alternative_categories=[],
                    model_used=sample_classification_response.model_used,
                    processing_time=sample_classification_response.processing_time
                )
                for video in videos
            ]
        
        mock_llm_provider.classify_videos_batch_optimized.side_effect = create_matching_batch_responses
        
        result = await analyzer_agent.classify_videos(sample_youtube_videos)
        
        # Verify results
        assert len(result) == len(sample_youtube_videos)
        assert all(isinstance(video, ClassifiedVideo) for video in result)
        
        # Verify batch method was called instead of individual calls
        mock_llm_provider.classify_videos_batch_optimized.assert_called()
        
        # Individual classify_video should not be called for successful batch
        assert not mock_llm_provider.classify_video.called
        
        # Verify statistics were updated
        stats = analyzer_agent.get_analysis_stats()
        assert stats["videos_analyzed"] == len(sample_youtube_videos)
        assert stats["classifications_successful"] == len(sample_youtube_videos)
        assert stats["classifications_failed"] == 0
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_failure_recovery(self, analyzer_agent, mock_llm_provider, sample_youtube_videos, sample_classification_response):
        """Test recovery when some batches fail"""
        # Mock batch classification to fail, then individual fallback to succeed
        mock_llm_provider.classify_videos_batch_optimized.side_effect = ClassificationError("Batch failed")
        mock_llm_provider.classify_video.return_value = sample_classification_response
        
        result = await analyzer_agent.classify_videos(sample_youtube_videos)
        
        # Should have successful results from individual fallback
        assert len(result) == len(sample_youtube_videos)
        
        # Verify batch method was attempted
        mock_llm_provider.classify_videos_batch_optimized.assert_called()
        
        # Verify individual fallback was used
        assert mock_llm_provider.classify_video.call_count == len(sample_youtube_videos)
        
        # Verify statistics account for both batch failure and individual successes
        stats = analyzer_agent.get_analysis_stats()
        assert stats["videos_analyzed"] == len(sample_youtube_videos)
        assert stats["classifications_successful"] == len(sample_youtube_videos)
        # Note: batch failure is counted but then individual successes recover
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_partial_failure(self, analyzer_agent, mock_llm_provider, sample_youtube_videos, sample_classification_response):
        """Test handling when batch returns partial results"""
        # Mock batch to return only partial responses (simulating some videos not found in results)
        def partial_batch_response(videos, batch_size):
            # Return response for only the first video
            return [
                ClassificationResponse(
                    video_id=videos[0].video_id,
                    category=VideoCategory.CHALLENGE,
                    confidence=0.85,
                    reasoning="Partial batch classification",
                    alternative_categories=[],
                    model_used="test/model",
                    processing_time=0.0
                )
            ]
        
        mock_llm_provider.classify_videos_batch_optimized.side_effect = partial_batch_response
        mock_llm_provider.classify_video.return_value = sample_classification_response
        
        result = await analyzer_agent.classify_videos(sample_youtube_videos)
        
        # Should get at least one result
        assert len(result) >= 1
        
        # Verify batch was attempted
        mock_llm_provider.classify_videos_batch_optimized.assert_called()
    
    @pytest.mark.asyncio
    async def test_classify_videos_batch_size_behavior(self, analyzer_agent, mock_llm_provider, sample_classification_response):
        """Test batch processing with different video counts"""
        # Create larger video list to test batching
        large_video_list = []
        for i in range(12):  # More than default batch size of 5
            snippet = VideoSnippet(
                title=f"Test Video {i+1}",
                description=f"Description {i+1}",
                published_at=datetime.now(),
                channel_title=f"Channel {i+1}",
                thumbnail_url="https://example.com/thumb.jpg"
            )
            video = YouTubeVideoRaw(
                video_id=f"video_{i+1}",
                snippet=snippet
            )
            large_video_list.append(video)
        
        # Create responses that match the video IDs being processed
        def mock_batch_response(videos, batch_size):
            return [
                ClassificationResponse(
                    video_id=video.video_id,
                    category=VideoCategory.CHALLENGE,
                    confidence=0.85,
                    reasoning="Batch classification",
                    alternative_categories=[],
                    model_used="test/model",
                    processing_time=0.0
                )
                for video in videos  # Return response for all videos in the batch
            ]
        
        mock_llm_provider.classify_videos_batch_optimized.side_effect = mock_batch_response
        
        result = await analyzer_agent.classify_videos(large_video_list)
        
        # Should process all videos in multiple batches
        assert len(result) >= 10  # At least most videos should be processed
        
        # Verify batch method was called multiple times (once per batch)
        assert mock_llm_provider.classify_videos_batch_optimized.call_count >= 2  # At least 2 batches for 12 videos
    
    @pytest.mark.asyncio
    async def test_classify_videos_empty_batch_optimization(self, analyzer_agent, mock_llm_provider):
        """Test batch processing with empty video list"""
        result = await analyzer_agent.classify_videos([])
        
        assert result == []
        # No API calls should be made for empty list
        assert not mock_llm_provider.classify_videos_batch_optimized.called
        assert not mock_llm_provider.classify_video.called
        
        # Statistics should reflect no processing
        stats = analyzer_agent.get_analysis_stats()
        assert stats["videos_analyzed"] == 0
        assert stats["classifications_successful"] == 0
        assert stats["classifications_failed"] == 0
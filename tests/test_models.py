"""Tests for data models validation and serialization"""

import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from src.models.video_models import (
    VideoCategory, VideoStatistics, VideoSnippet, YouTubeVideoRaw,
    ClassifiedVideo, TrendReport, CollectionRequest
)
from src.models.classification_models import (
    ClassificationRequest, BatchClassificationRequest,
    BatchClassificationResponse, CategoryInsights, TrendAnalysisResult
)


class TestVideoModels:
    """Test video data models"""
    
    def test_video_category_enum(self):
        """Test VideoCategory enum values"""
        assert VideoCategory.CHALLENGE == "Challenge"
        assert VideoCategory.INFO_ADVICE == "Info/Advice"
        assert VideoCategory.TRENDING_SOUNDS == "Trending Sounds/BGM"
        
        # Test enum creation
        category = VideoCategory("Challenge")
        assert category == VideoCategory.CHALLENGE
    
    def test_video_statistics_model(self):
        """Test VideoStatistics model validation"""
        # Valid statistics
        stats = VideoStatistics(
            view_count=1000000,
            like_count=50000,
            comment_count=2500
        )
        assert stats.view_count == 1000000
        assert stats.like_count == 50000
        assert stats.comment_count == 2500
        
        # Default values
        stats_default = VideoStatistics()
        assert stats_default.view_count == 0
        assert stats_default.like_count == 0
        assert stats_default.comment_count == 0
        
        # Invalid values (negative numbers should be allowed for real API data)
        stats_negative = VideoStatistics(view_count=-1)
        assert stats_negative.view_count == -1
    
    def test_video_snippet_model(self, sample_video_snippet):
        """Test VideoSnippet model validation"""
        snippet = sample_video_snippet
        
        assert snippet.title == "Amazing Dance Challenge Tutorial"
        assert snippet.description == "Learn this viral dance challenge in just 60 seconds!"
        assert snippet.channel_title == "DanceChannel"
        assert str(snippet.thumbnail_url) == "https://i.ytimg.com/vi/abc123/default.jpg"
        assert snippet.duration == "PT58S"
        
        # Test required fields
        with pytest.raises(ValidationError):
            VideoSnippet()  # Missing required title
        
        # Test with minimal required data
        minimal_snippet = VideoSnippet(
            title="Test Title",
            published_at=datetime.now(timezone.utc),
            thumbnail_url="https://example.com/test.jpg"
        )
        assert minimal_snippet.description == ""
        assert minimal_snippet.channel_title == ""
    
    def test_youtube_video_raw_model(self, sample_youtube_video):
        """Test YouTubeVideoRaw model validation"""
        video = sample_youtube_video
        
        assert video.video_id == "abc123"
        assert video.snippet.title == "Amazing Dance Challenge Tutorial"
        assert video.statistics.view_count == 1000000
        
        # Test without statistics
        video_no_stats = YouTubeVideoRaw(
            video_id="test123",
            snippet=video.snippet
        )
        assert video_no_stats.statistics is None
        
        # Test model dump and load
        video_dict = video.model_dump()
        assert video_dict["video_id"] == "abc123"
        
        # Test reconstruction from dict
        video_reconstructed = YouTubeVideoRaw(**video_dict)
        assert video_reconstructed.video_id == video.video_id
    
    def test_classified_video_model(self, sample_classified_video):
        """Test ClassifiedVideo model validation"""
        classified = sample_classified_video
        
        assert classified.video_id == "abc123"
        assert classified.category == VideoCategory.CHALLENGE
        assert 0.0 <= classified.confidence <= 1.0
        assert len(classified.reasoning) > 0
        
        # Test confidence bounds
        with pytest.raises(ValidationError):
            ClassifiedVideo(
                video_id="test",
                title="Test",
                category=VideoCategory.CHALLENGE,
                confidence=1.5,  # Invalid: > 1.0
                reasoning="Test"
            )
        
        with pytest.raises(ValidationError):
            ClassifiedVideo(
                video_id="test",
                title="Test",
                category=VideoCategory.CHALLENGE,
                confidence=-0.1,  # Invalid: < 0.0
                reasoning="Test"
            )
    
    def test_trend_report_model(self, sample_classified_videos):
        """Test TrendReport model validation"""
        report = TrendReport(
            category=VideoCategory.CHALLENGE,
            trend_summary="Test summary",
            key_insights=["Insight 1", "Insight 2"],
            recommended_actions=["Action 1", "Action 2"],
            top_videos=sample_classified_videos[:2],
            total_videos_analyzed=len(sample_classified_videos),
            analysis_period="Test period"
        )
        
        assert report.category == VideoCategory.CHALLENGE
        assert len(report.key_insights) == 2
        assert len(report.recommended_actions) == 2
        assert len(report.top_videos) == 2
        assert report.total_videos_analyzed == 3
        
        # Test default timestamp
        assert isinstance(report.generated_at, datetime)
    
    def test_collection_request_model(self):
        """Test CollectionRequest model validation"""
        request = CollectionRequest(
            search_queries=["dance", "fitness", "tutorial"],
            max_results_per_query=25,
            region_code="KR"
        )
        
        assert len(request.search_queries) == 3
        assert request.max_results_per_query == 25
        assert request.region_code == "KR"
        
        # Test validation bounds
        with pytest.raises(ValidationError):
            CollectionRequest(
                search_queries=["dance"],
                max_results_per_query=0  # Invalid: < 1
            )
        
        with pytest.raises(ValidationError):
            CollectionRequest(
                search_queries=["dance"],
                max_results_per_query=51  # Invalid: > 50
            )
        
        # Test empty queries list
        with pytest.raises(ValidationError):
            CollectionRequest(search_queries=[])


class TestClassificationModels:
    """Test classification-related models"""
    
    def test_classification_request_model(self, sample_youtube_video):
        """Test ClassificationRequest model"""
        request = ClassificationRequest(
            video=sample_youtube_video,
            context_data={"additional": "context"}
        )
        
        assert request.video.video_id == "abc123"
        assert request.context_data["additional"] == "context"
        
        # Test without context data
        request_minimal = ClassificationRequest(video=sample_youtube_video)
        assert request_minimal.context_data is None
    
    def test_classification_response_model(self, sample_classification_response):
        """Test ClassificationResponse model"""
        response = sample_classification_response
        
        assert response.video_id == "abc123"
        assert response.category == VideoCategory.CHALLENGE
        assert 0.0 <= response.confidence <= 1.0
        assert len(response.reasoning) > 0
        assert response.model_used == "openai/gpt-4o-mini"
        assert response.processing_time >= 0
        
        # Test default values
        assert response.alternative_categories == []
        assert isinstance(response.classified_at, datetime)
    
    def test_batch_classification_request_model(self, sample_youtube_videos):
        """Test BatchClassificationRequest model"""
        request = BatchClassificationRequest(
            videos=sample_youtube_videos,
            classification_settings={"confidence_threshold": 0.7}
        )
        
        assert len(request.videos) == 3
        assert request.classification_settings["confidence_threshold"] == 0.7
        
        # Test empty videos list
        with pytest.raises(ValidationError):
            BatchClassificationRequest(videos=[])
    
    def test_batch_classification_response_model(self, sample_classification_response):
        """Test BatchClassificationResponse model"""
        classifications = [sample_classification_response] * 3
        
        response = BatchClassificationResponse(
            classifications=classifications,
            batch_summary={"total_processed": 3},
            total_videos=3,
            successful_classifications=3,
            failed_classifications=0,
            processing_time=3.6
        )
        
        assert len(response.classifications) == 3
        assert response.total_videos == 3
        assert response.successful_classifications == 3
        assert response.failed_classifications == 0
        assert response.processing_time == 3.6
        assert isinstance(response.processed_at, datetime)
    
    def test_category_insights_model(self):
        """Test CategoryInsights model"""
        insights = CategoryInsights(
            category=VideoCategory.CHALLENGE,
            video_count=10,
            average_confidence=0.85,
            common_keywords=["dance", "challenge", "viral"],
            trending_themes=["dance", "fitness"],
            average_views=500000.0,
            engagement_score=0.7
        )
        
        assert insights.category == VideoCategory.CHALLENGE
        assert insights.video_count == 10
        assert insights.average_confidence == 0.85
        assert len(insights.common_keywords) == 3
        assert len(insights.trending_themes) == 2
        assert insights.average_views == 500000.0
        assert insights.engagement_score == 0.7
    
    def test_trend_analysis_result_model(self):
        """Test TrendAnalysisResult model"""
        category_insights = [
            CategoryInsights(
                category=VideoCategory.CHALLENGE,
                video_count=5,
                average_confidence=0.85,
                common_keywords=["dance"],
                trending_themes=["dance"]
            ),
            CategoryInsights(
                category=VideoCategory.INFO_ADVICE,
                video_count=3,
                average_confidence=0.80,
                common_keywords=["tips"],
                trending_themes=["advice"]
            )
        ]
        
        analysis = TrendAnalysisResult(
            analysis_period="January 2024",
            total_videos_analyzed=8,
            category_insights=category_insights,
            dominant_category=VideoCategory.CHALLENGE,
            emerging_trends=["Short-form tutorials", "Dance challenges"],
            recommended_content_strategy=["Focus on challenges", "Include tutorials"],
            model_version="openai/gpt-4o-mini"
        )
        
        assert analysis.total_videos_analyzed == 8
        assert len(analysis.category_insights) == 2
        assert analysis.dominant_category == VideoCategory.CHALLENGE
        assert len(analysis.emerging_trends) == 2
        assert len(analysis.recommended_content_strategy) == 2
        assert isinstance(analysis.analyzed_at, datetime)


class TestModelSerialization:
    """Test model serialization and deserialization"""
    
    def test_youtube_video_serialization(self, sample_youtube_video):
        """Test YouTube video model serialization"""
        video = sample_youtube_video
        
        # Test model_dump
        video_dict = video.model_dump()
        assert isinstance(video_dict, dict)
        assert video_dict["video_id"] == "abc123"
        assert "snippet" in video_dict
        assert "statistics" in video_dict
        
        # Test JSON serialization
        video_json = video.model_dump_json()
        assert isinstance(video_json, str)
        assert "abc123" in video_json
        
        # Test reconstruction
        video_reconstructed = YouTubeVideoRaw.model_validate(video_dict)
        assert video_reconstructed.video_id == video.video_id
        assert video_reconstructed.snippet.title == video.snippet.title
    
    def test_classified_video_serialization(self, sample_classified_video):
        """Test classified video model serialization"""
        classified = sample_classified_video
        
        # Test serialization with datetime handling
        classified_dict = classified.model_dump()
        assert isinstance(classified_dict, dict)
        assert classified_dict["category"] == "Challenge"
        
        # Test reconstruction
        classified_reconstructed = ClassifiedVideo.model_validate(classified_dict)
        assert classified_reconstructed.video_id == classified.video_id
        assert classified_reconstructed.category == classified.category
    
    def test_trend_report_serialization(self, sample_classified_videos):
        """Test trend report model serialization"""
        report = TrendReport(
            category=VideoCategory.CHALLENGE,
            trend_summary="Test summary",
            key_insights=["Insight 1"],
            recommended_actions=["Action 1"],
            top_videos=sample_classified_videos[:1],
            total_videos_analyzed=1,
            analysis_period="Test"
        )
        
        # Test serialization
        report_dict = report.model_dump()
        assert isinstance(report_dict, dict)
        assert report_dict["category"] == "Challenge"
        assert len(report_dict["top_videos"]) == 1
        
        # Test reconstruction
        report_reconstructed = TrendReport.model_validate(report_dict)
        assert report_reconstructed.category == report.category
        assert len(report_reconstructed.top_videos) == 1


class TestModelValidationEdgeCases:
    """Test edge cases and validation scenarios"""
    
    def test_empty_string_handling(self):
        """Test handling of empty strings in models"""
        # VideoSnippet with empty description should be valid
        snippet = VideoSnippet(
            title="Test",
            description="",  # Empty string should be allowed
            published_at=datetime.now(timezone.utc),
            channel_title="",  # Empty string should be allowed
            thumbnail_url="https://example.com/test.jpg"
        )
        assert snippet.description == ""
        assert snippet.channel_title == ""
    
    def test_url_validation(self):
        """Test URL validation in models"""
        # Valid URL
        snippet = VideoSnippet(
            title="Test",
            published_at=datetime.now(timezone.utc),
            thumbnail_url="https://example.com/test.jpg"
        )
        assert str(snippet.thumbnail_url) == "https://example.com/test.jpg"
        
        # Invalid URL should raise ValidationError
        with pytest.raises(ValidationError):
            VideoSnippet(
                title="Test",
                published_at=datetime.now(timezone.utc),
                thumbnail_url="not-a-url"
            )
    
    def test_datetime_handling(self):
        """Test datetime handling in models"""
        now = datetime.now(timezone.utc)
        
        snippet = VideoSnippet(
            title="Test",
            published_at=now,
            thumbnail_url="https://example.com/test.jpg"
        )
        assert snippet.published_at == now
        
        # Test timezone-naive datetime (should still work)
        naive_datetime = datetime(2024, 1, 15, 10, 0, 0)
        snippet_naive = VideoSnippet(
            title="Test",
            published_at=naive_datetime,
            thumbnail_url="https://example.com/test.jpg"
        )
        assert snippet_naive.published_at == naive_datetime
    
    def test_long_text_handling(self):
        """Test handling of long text fields"""
        long_title = "A" * 1000  # Very long title
        long_description = "B" * 5000  # Very long description
        
        snippet = VideoSnippet(
            title=long_title,
            description=long_description,
            published_at=datetime.now(timezone.utc),
            thumbnail_url="https://example.com/test.jpg"
        )
        
        assert len(snippet.title) == 1000
        assert len(snippet.description) == 5000
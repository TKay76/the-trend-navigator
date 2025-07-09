"""Classification models for AI-powered video categorization"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from .video_models import VideoCategory, YouTubeVideoRaw


class ClassificationRequest(BaseModel):
    """Request model for video classification"""
    video: YouTubeVideoRaw = Field(..., description="Video to be classified")
    context_data: Optional[Dict[str, Any]] = Field(None, description="Additional context for classification")
    
    class Config:
        schema_extra = {
            "example": {
                "video": {
                    "video_id": "abc123",
                    "snippet": {
                        "title": "10-Minute Morning Dance Workout",
                        "description": "Quick dance routine to start your day...",
                        "published_at": "2024-01-15T10:00:00Z",
                        "channel_title": "FitnessGuru",
                        "thumbnail_url": "https://i.ytimg.com/vi/abc123/default.jpg"
                    }
                }
            }
        }


class ClassificationResponse(BaseModel):
    """Response model for video classification"""
    video_id: str = Field(..., description="YouTube video ID")
    category: VideoCategory = Field(..., description="Classified category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score")
    reasoning: str = Field(..., description="Detailed reasoning for classification")
    
    # Alternative categories with scores
    alternative_categories: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Alternative classification options with scores"
    )
    
    # Processing metadata
    model_used: str = Field(..., description="LLM model used for classification")
    processing_time: float = Field(..., description="Time taken for classification in seconds")
    classified_at: datetime = Field(default_factory=datetime.now, description="Classification timestamp")


class BatchClassificationRequest(BaseModel):
    """Request model for batch video classification"""
    videos: List[YouTubeVideoRaw] = Field(..., min_items=1, description="Videos to be classified")
    classification_settings: Optional[Dict[str, Any]] = Field(None, description="Classification configuration")
    
    class Config:
        schema_extra = {
            "example": {
                "videos": [
                    {
                        "video_id": "abc123",
                        "snippet": {
                            "title": "Dance Challenge Tutorial",
                            "description": "Learn this viral dance...",
                            "published_at": "2024-01-15T10:00:00Z",
                            "channel_title": "DanceChannel",
                            "thumbnail_url": "https://i.ytimg.com/vi/abc123/default.jpg"
                        }
                    }
                ],
                "classification_settings": {
                    "confidence_threshold": 0.7,
                    "include_alternatives": True
                }
            }
        }


class BatchClassificationResponse(BaseModel):
    """Response model for batch video classification"""
    classifications: List[ClassificationResponse] = Field(..., description="Individual classification results")
    batch_summary: Dict[str, Any] = Field(..., description="Summary of batch processing")
    
    # Batch metadata
    total_videos: int = Field(..., description="Total number of videos processed")
    successful_classifications: int = Field(..., description="Number of successful classifications")
    failed_classifications: int = Field(..., description="Number of failed classifications")
    processing_time: float = Field(..., description="Total batch processing time in seconds")
    processed_at: datetime = Field(default_factory=datetime.now, description="Batch processing timestamp")


class CategoryInsights(BaseModel):
    """Insights for a specific video category"""
    category: VideoCategory = Field(..., description="Video category")
    video_count: int = Field(..., description="Number of videos in this category")
    average_confidence: float = Field(..., description="Average classification confidence")
    common_keywords: List[str] = Field(..., description="Most common keywords in titles/descriptions")
    trending_themes: List[str] = Field(..., description="Trending themes within this category")
    
    # Performance metrics
    average_views: Optional[float] = Field(None, description="Average view count for videos in this category")
    engagement_score: Optional[float] = Field(None, description="Engagement score (likes/comments ratio)")


class TrendAnalysisResult(BaseModel):
    """Complete trend analysis result across all categories"""
    analysis_period: str = Field(..., description="Time period analyzed")
    total_videos_analyzed: int = Field(..., description="Total number of videos analyzed")
    category_insights: List[CategoryInsights] = Field(..., description="Insights per category")
    
    # Overall trends
    dominant_category: VideoCategory = Field(..., description="Most prevalent category")
    emerging_trends: List[str] = Field(..., description="Emerging trends across all categories")
    recommended_content_strategy: List[str] = Field(..., description="Strategic recommendations for creators")
    
    # Analysis metadata
    analyzed_at: datetime = Field(default_factory=datetime.now, description="Analysis completion timestamp")
    model_version: str = Field(..., description="Version of the analysis model used")
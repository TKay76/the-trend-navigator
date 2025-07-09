"""Video data models for YouTube API responses and internal structures"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum


class VideoCategory(str, Enum):
    """Video classification categories for YouTube Shorts"""
    CHALLENGE = "Challenge"
    INFO_ADVICE = "Info/Advice"
    TRENDING_SOUNDS = "Trending Sounds/BGM"


class VideoStatistics(BaseModel):
    """Video statistics information model"""
    view_count: int = Field(0, description="Number of views")
    like_count: int = Field(0, description="Number of likes")
    comment_count: int = Field(0, description="Number of comments")


class VideoSnippet(BaseModel):
    """Video basic information model"""
    title: str = Field(..., description="Video title")
    description: str = Field("", description="Video description")
    published_at: datetime = Field(..., description="Publication date")
    channel_title: str = Field("", description="Channel name")
    thumbnail_url: HttpUrl = Field(..., description="Thumbnail URL")
    duration: Optional[str] = Field(None, description="Video duration in ISO 8601 format")


class YouTubeVideoRaw(BaseModel):
    """
    Raw YouTube API response structure.
    This model represents data as received from YouTube Data API
    before any processing or transformation.
    """
    video_id: str = Field(..., description="YouTube video ID")
    snippet: VideoSnippet
    statistics: Optional[VideoStatistics] = None
    
    class Config:
        populate_by_name = True


class ClassifiedVideo(BaseModel):
    """Video with AI classification results"""
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    category: VideoCategory = Field(..., description="AI-classified category")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence score")
    reasoning: str = Field(..., description="AI reasoning for classification")
    
    # Optional metadata
    view_count: Optional[int] = Field(None, description="Number of views")
    published_at: Optional[datetime] = Field(None, description="Publication date")
    channel_title: Optional[str] = Field(None, description="Channel name")


class TrendReport(BaseModel):
    """Generated trend analysis report for a specific category"""
    category: VideoCategory = Field(..., description="Report category")
    trend_summary: str = Field(..., description="Overall trend summary")
    key_insights: List[str] = Field(..., description="Key insights from analysis")
    recommended_actions: List[str] = Field(..., description="Actionable recommendations")
    top_videos: List[ClassifiedVideo] = Field(..., description="Top performing videos in category")
    generated_at: datetime = Field(default_factory=datetime.now, description="Report generation timestamp")
    
    # Analysis metadata
    total_videos_analyzed: int = Field(..., description="Total number of videos analyzed")
    analysis_period: str = Field(..., description="Time period of analysis")


class CollectionRequest(BaseModel):
    """Request model for video collection operations"""
    search_queries: List[str] = Field(..., min_items=1, description="Search terms for video collection")
    max_results_per_query: int = Field(20, ge=1, le=50, description="Maximum results per search query")
    region_code: Optional[str] = Field("US", description="Region code for search")
    
    class Config:
        schema_extra = {
            "example": {
                "search_queries": ["dance challenge", "fitness tips", "trending music"],
                "max_results_per_query": 20,
                "region_code": "US"
            }
        }
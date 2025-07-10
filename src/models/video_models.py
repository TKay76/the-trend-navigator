"""Video data models for YouTube API responses and internal structures"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict, Any
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


# Enhanced video analysis models for YouTube content analysis

class ChallengeType(str, Enum):
    """Detailed challenge type classifications"""
    DANCE = "Dance"
    FOOD = "Food"
    GAME = "Game"
    FITNESS = "Fitness"
    CREATIVE = "Creative"
    REACTION = "Reaction"
    SKILL = "Skill"
    TREND = "Trend"
    OTHER = "Other"


class DifficultyLevel(str, Enum):
    """Challenge difficulty levels"""
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"
    EXPERT = "Expert"


class SafetyLevel(str, Enum):
    """Safety assessment levels"""
    SAFE = "Safe"
    CAUTION = "Caution"
    RISKY = "Risky"
    DANGEROUS = "Dangerous"


class MusicAnalysis(BaseModel):
    """Music and sound analysis results"""
    genre: Optional[str] = Field(None, description="Detected music genre")
    viral_sounds: List[str] = Field(default=[], description="Identified viral sounds or tracks")
    audio_elements: List[str] = Field(default=[], description="Audio elements (voice, effects, music)")
    background_music: Optional[str] = Field(None, description="Background music description")


class ChallengeAnalysis(BaseModel):
    """Challenge-specific analysis results"""
    challenge_type: ChallengeType = Field(..., description="Specific challenge category")
    mechanics: str = Field(..., description="How the challenge works")
    rules: Optional[str] = Field(None, description="Challenge rules if apparent")
    target_audience: str = Field(..., description="Intended audience")


class AccessibilityAnalysis(BaseModel):
    """Accessibility and difficulty analysis"""
    difficulty_level: DifficultyLevel = Field(..., description="Overall difficulty")
    required_tools: List[str] = Field(default=[], description="Required tools or materials")
    required_space: str = Field(..., description="Space requirements")
    required_skills: List[str] = Field(default=[], description="Required skills")
    easy_to_follow: bool = Field(..., description="Can average person follow along")
    safety_level: SafetyLevel = Field(..., description="Safety assessment")
    safety_notes: Optional[str] = Field(None, description="Safety considerations")


class ContentDetails(BaseModel):
    """Detailed content analysis"""
    participants_count: int = Field(..., description="Number of participants")
    setting: str = Field(..., description="Environment/setting description")
    key_visual_elements: List[str] = Field(default=[], description="Important visual elements")
    estimated_duration: str = Field(..., description="Estimated time to complete challenge")
    props_used: List[str] = Field(default=[], description="Props or objects used")


class TrendAnalysis(BaseModel):
    """Trend and viral potential analysis"""
    viral_potential: str = Field(..., description="Assessment of viral potential")
    cultural_relevance: str = Field(..., description="Cultural context and relevance")
    appeal_factors: List[str] = Field(default=[], description="What makes this appealing")
    trend_indicators: List[str] = Field(default=[], description="Indicators of trending potential")


class EnhancedVideoAnalysis(BaseModel):
    """Comprehensive video analysis results from AI"""
    video_id: str = Field(..., description="YouTube video ID")
    analysis_timestamp: datetime = Field(default_factory=datetime.now, description="When analysis was performed")
    
    # Core analysis components
    music_analysis: MusicAnalysis = Field(..., description="Music and sound analysis")
    challenge_analysis: ChallengeAnalysis = Field(..., description="Challenge-specific analysis")
    accessibility_analysis: AccessibilityAnalysis = Field(..., description="Accessibility and difficulty")
    content_details: ContentDetails = Field(..., description="Detailed content information")
    trend_analysis: TrendAnalysis = Field(..., description="Trend and viral analysis")
    
    # Analysis metadata
    analysis_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall analysis confidence")
    analysis_notes: Optional[str] = Field(None, description="Additional analysis notes")
    raw_analysis_text: str = Field(..., description="Raw AI analysis response")


class EnhancedClassifiedVideo(ClassifiedVideo):
    """ClassifiedVideo with enhanced analysis data"""
    enhanced_analysis: Optional[EnhancedVideoAnalysis] = Field(None, description="Enhanced video analysis")
    analysis_source: str = Field(default="text", description="Source of analysis: 'text' or 'video'")
    
    @property
    def has_video_analysis(self) -> bool:
        """Check if video has been analyzed with video content"""
        return self.enhanced_analysis is not None and self.analysis_source == "video"
    
    @property
    def challenge_type_detailed(self) -> Optional[ChallengeType]:
        """Get detailed challenge type if available"""
        if self.enhanced_analysis:
            return self.enhanced_analysis.challenge_analysis.challenge_type
        return None
    
    @property
    def difficulty_level(self) -> Optional[DifficultyLevel]:
        """Get difficulty level if available"""
        if self.enhanced_analysis:
            return self.enhanced_analysis.accessibility_analysis.difficulty_level
        return None
    
    @property
    def viral_sounds(self) -> List[str]:
        """Get viral sounds if available"""
        if self.enhanced_analysis:
            return self.enhanced_analysis.music_analysis.viral_sounds
        return []


class VideoAnalysisRequest(BaseModel):
    """Request model for video analysis operations"""
    video_ids: List[str] = Field(..., min_items=1, description="YouTube video IDs to analyze")
    analysis_type: str = Field(default="comprehensive", description="Type of analysis to perform")
    include_video_content: bool = Field(default=False, description="Whether to analyze actual video content")
    
    class Config:
        schema_extra = {
            "example": {
                "video_ids": ["dWFASBOoh2w", "5I7dRmkXWY4"],
                "analysis_type": "challenge",
                "include_video_content": True
            }
        }
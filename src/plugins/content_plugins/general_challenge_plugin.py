"""General challenge content analysis plugin - Universal fallback"""

import logging
from datetime import datetime
from typing import List, Dict, Any

from ..base_plugin import (
    BaseContentPlugin, PluginMetadata, AnalysisContext, PluginResult,
    PluginCapability
)
from ...models.video_models import (
    YouTubeVideoRaw, EnhancedClassifiedVideo, VideoCategory, ChallengeType,
    DifficultyLevel
)
from ...models.prompt_models import ContentType, ParsedUserRequest
from ...agents.analyzer_agent import create_analyzer_agent

logger = logging.getLogger(__name__)


class GeneralChallengePlugin(BaseContentPlugin):
    """
    Universal plugin for analyzing any type of challenge content
    
    This plugin serves as a fallback for content types that don't have
    specialized plugins, and can handle general analysis for:
    - Any challenge type
    - General content classification
    - Basic trend analysis
    - Universal recommendations
    """
    
    def __init__(self):
        super().__init__()
        self.analyzer_agent = None
    
    def _define_metadata(self) -> PluginMetadata:
        """Define metadata for general challenge plugin"""
        return PluginMetadata(
            name="general_challenge_analyzer",
            version="1.0.0",
            description="Universal analyzer for all types of challenge and general content",
            content_types=[
                ContentType.GENERAL_CHALLENGE,
                ContentType.ANY_VIDEO,
                ContentType.CREATIVE_CHALLENGE,
                ContentType.GAME_CHALLENGE,
                # Can also handle specialized types as fallback
                ContentType.DANCE_CHALLENGE,
                ContentType.FOOD_CHALLENGE,
                ContentType.FITNESS_CHALLENGE
            ],
            capabilities=[
                PluginCapability.CONTENT_CLASSIFICATION,
                PluginCapability.VIDEO_ANALYSIS,
                PluginCapability.TREND_ANALYSIS,
                PluginCapability.RECOMMENDATION,
                PluginCapability.SEARCH_OPTIMIZATION
            ],
            supported_languages=["korean", "english"],
            author="YouTube Trends Analysis Team",
            min_confidence_threshold=0.4,  # Lower threshold as fallback
            max_videos_per_batch=50
        )
    
    async def _setup(self) -> None:
        """Initialize the analyzer agent"""
        logger.info("Setting up General Challenge Plugin...")
        self.analyzer_agent = create_analyzer_agent()
        logger.info("General Challenge Plugin setup completed")
    
    def _calculate_handling_confidence(self, user_request: ParsedUserRequest) -> float:
        """Calculate confidence for handling any content"""
        # This is a fallback plugin, so confidence should be lower than specialized plugins
        base_confidence = 0.5
        
        # Boost confidence for general keywords
        general_keywords = ["챌린지", "challenge", "트렌드", "trend", "인기", "popular"]
        request_text = user_request.original_input.lower()
        
        for keyword in general_keywords:
            if keyword in request_text:
                base_confidence = min(base_confidence + 0.1, 0.8)  # Max 0.8 to stay below specialized plugins
                break
        
        # If this is explicitly a general challenge request
        if user_request.content_filter.content_type == ContentType.GENERAL_CHALLENGE:
            base_confidence = 0.9
        elif user_request.content_filter.content_type == ContentType.ANY_VIDEO:
            base_confidence = 0.95
        
        return base_confidence
    
    async def analyze_videos(
        self, 
        videos: List[YouTubeVideoRaw], 
        context: AnalysisContext
    ) -> PluginResult:
        """Analyze any type of challenge videos"""
        start_time = datetime.now()
        
        try:
            logger.info(f"General plugin analyzing {len(videos)} videos")
            
            # Use the analyzer agent for video classification
            include_video_analysis = (
                context.analysis_depth == "detailed" or 
                len(videos) <= 15  # Slightly more conservative than specialized plugins
            )
            
            analyzed_videos = await self.analyzer_agent.classify_videos_with_enhanced_analysis(
                videos,
                include_video_content=include_video_analysis
            )
            
            # Apply general enhancements
            enhanced_videos = []
            for video in analyzed_videos:
                enhanced_video = await self._enhance_general_analysis(video, context)
                enhanced_videos.append(enhanced_video)
            
            # Sort by general criteria
            sorted_videos = self._sort_general_videos(enhanced_videos, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate confidence score
            confidence_score = self._calculate_analysis_confidence(sorted_videos)
            
            logger.info(f"General analysis completed: {len(sorted_videos)} videos analyzed")
            
            return PluginResult(
                success=True,
                analyzed_videos=sorted_videos,
                insights={},  # Will be filled by generate_insights
                processing_time=processing_time,
                confidence_score=confidence_score,
                warnings=[],
                metadata={
                    "plugin_name": self.metadata.name,
                    "original_video_count": len(videos),
                    "analyzed_video_count": len(sorted_videos),
                    "analysis_depth": context.analysis_depth,
                    "content_type": context.user_request.content_filter.content_type.value
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"General video analysis failed: {e}")
            
            return PluginResult(
                success=False,
                analyzed_videos=[],
                insights={},
                processing_time=processing_time,
                confidence_score=0.0,
                error_message=str(e),
                warnings=[],
                metadata={"plugin_name": self.metadata.name}
            )
    
    async def _enhance_general_analysis(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> EnhancedClassifiedVideo:
        """Apply general enhancements to video analysis"""
        # Add general scoring
        general_score = self._calculate_general_score(video, context)
        
        # Update metadata with general information
        if not hasattr(video, 'plugin_metadata'):
            video.plugin_metadata = {}
        
        video.plugin_metadata['general_score'] = general_score
        video.plugin_metadata['plugin_name'] = self.metadata.name
        video.plugin_metadata['content_category'] = self._categorize_content(video)
        video.plugin_metadata['engagement_level'] = self._assess_engagement_level(video)
        
        # Enhance difficulty assessment for any content
        if video.has_video_analysis and hasattr(video.enhanced_analysis, 'accessibility_analysis'):
            difficulty = self._assess_general_difficulty(video, context)
            video.enhanced_analysis.accessibility_analysis.difficulty_level = difficulty
        
        return video
    
    def _calculate_general_score(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> float:
        """Calculate general relevance score"""
        score = 0.0
        
        # Base score from video classification confidence
        score += video.confidence * 0.3
        
        # Title relevance to user request
        user_keywords = context.search_keywords + [context.user_request.original_input]
        title_lower = video.title.lower()
        keyword_matches = sum(1 for keyword in user_keywords if keyword.lower() in title_lower)
        if user_keywords:
            score += (keyword_matches / len(user_keywords)) * 0.3
        
        # View count factor (normalized)
        if video.view_count > 1000000:  # 1M+ views
            score += 0.2
        elif video.view_count > 100000:  # 100K+ views
            score += 0.15
        elif video.view_count > 10000:  # 10K+ views
            score += 0.1
        
        # Recency factor
        days_old = (datetime.now() - video.published_at).days
        if days_old <= 3:
            score += 0.1
        elif days_old <= 7:
            score += 0.08
        elif days_old <= 30:
            score += 0.05
        
        # Engagement ratio (likes vs views) if available
        if hasattr(video, 'like_count') and video.like_count and video.view_count:
            engagement_ratio = video.like_count / video.view_count
            if engagement_ratio > 0.05:  # Good engagement
                score += 0.05
        
        return min(score, 1.0)
    
    def _categorize_content(self, video: EnhancedClassifiedVideo) -> str:
        """Categorize content into general categories"""
        title_lower = video.title.lower()
        
        # Define general content categories
        categories = {
            "entertainment": ["재미있는", "웃긴", "funny", "comedy", "entertainment"],
            "educational": ["배우기", "how to", "tutorial", "guide", "learn"],
            "challenge": ["챌린지", "challenge", "시도", "try"],
            "review": ["리뷰", "review", "평가", "rating"],
            "lifestyle": ["일상", "daily", "lifestyle", "vlog"],
            "creative": ["만들기", "창작", "creative", "diy", "craft"],
            "gaming": ["게임", "gaming", "play", "게임플레이"],
            "beauty": ["뷰티", "메이크업", "beauty", "makeup", "skincare"],
            "technology": ["기술", "tech", "review", "unboxing"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in title_lower for keyword in keywords):
                return category
        
        return "general"
    
    def _assess_engagement_level(self, video: EnhancedClassifiedVideo) -> str:
        """Assess engagement level based on metrics"""
        if not video.view_count:
            return "unknown"
        
        # Simple heuristic based on view count and recency
        days_old = (datetime.now() - video.published_at).days
        views_per_day = video.view_count / max(days_old, 1)
        
        if views_per_day > 50000:
            return "viral"
        elif views_per_day > 10000:
            return "high"
        elif views_per_day > 1000:
            return "medium"
        else:
            return "low"
    
    def _assess_general_difficulty(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> DifficultyLevel:
        """Assess general difficulty based on content analysis"""
        title_lower = video.title.lower()
        
        # Check for difficulty indicators in title
        if any(word in title_lower for word in ["쉬운", "간단", "초보", "easy", "simple", "beginner"]):
            return DifficultyLevel.EASY
        elif any(word in title_lower for word in ["어려운", "복잡", "고급", "hard", "complex", "advanced"]):
            return DifficultyLevel.HARD
        elif any(word in title_lower for word in ["전문가", "마스터", "expert", "master", "pro"]):
            return DifficultyLevel.EXPERT
        else:
            return DifficultyLevel.MEDIUM
    
    def _sort_general_videos(self, videos: List[EnhancedClassifiedVideo], context: AnalysisContext) -> List[EnhancedClassifiedVideo]:
        """Sort videos by general criteria"""
        user_request = context.user_request
        
        # Determine sort criteria from user request
        if user_request.quantity_filter.sort_order.value == "view_count_desc":
            return sorted(videos, key=lambda v: v.view_count, reverse=True)
        elif user_request.quantity_filter.sort_order.value == "recent_first":
            return sorted(videos, key=lambda v: v.published_at, reverse=True)
        elif user_request.quantity_filter.sort_order.value == "difficulty_asc":
            return sorted(videos, key=lambda v: self._get_difficulty_score(v))
        elif user_request.quantity_filter.sort_order.value == "difficulty_desc":
            return sorted(videos, key=lambda v: self._get_difficulty_score(v), reverse=True)
        else:
            # Default: sort by general relevance score
            return sorted(videos, key=lambda v: v.plugin_metadata.get('general_score', 0), reverse=True)
    
    def _get_difficulty_score(self, video: EnhancedClassifiedVideo) -> int:
        """Get numeric difficulty score for sorting"""
        if not video.has_video_analysis:
            return 2  # Default to medium
        
        difficulty = video.enhanced_analysis.accessibility_analysis.difficulty_level
        difficulty_scores = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.MEDIUM: 2,
            DifficultyLevel.HARD: 3,
            DifficultyLevel.EXPERT: 4
        }
        return difficulty_scores.get(difficulty, 2)
    
    def _calculate_analysis_confidence(self, videos: List[EnhancedClassifiedVideo]) -> float:
        """Calculate overall analysis confidence"""
        if not videos:
            return 0.0
        
        # Average confidence of analyzed videos
        avg_confidence = sum(v.confidence for v in videos) / len(videos)
        
        # Average general score
        avg_general_score = sum(v.plugin_metadata.get('general_score', 0) for v in videos) / len(videos)
        
        # Combine both scores with slight penalty for being general plugin
        combined_score = (avg_confidence * 0.6 + avg_general_score * 0.4) * 0.9
        
        return combined_score
    
    async def generate_insights(
        self, 
        analyzed_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """Generate general insights"""
        if not analyzed_videos:
            return {}
        
        insights = {}
        
        # Content category distribution
        category_counts = {}
        for video in analyzed_videos:
            category = video.plugin_metadata.get('content_category', 'general')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        insights["content_category_distribution"] = category_counts
        
        # Engagement level distribution
        engagement_counts = {}
        for video in analyzed_videos:
            engagement = video.plugin_metadata.get('engagement_level', 'unknown')
            engagement_counts[engagement] = engagement_counts.get(engagement, 0) + 1
        
        insights["engagement_distribution"] = engagement_counts
        
        # Channel diversity
        channels = set(video.channel_title for video in analyzed_videos)
        insights["channel_diversity"] = {
            "unique_channels": len(channels),
            "videos_per_channel": len(analyzed_videos) / len(channels) if channels else 0
        }
        
        # View count analytics
        total_views = sum(v.view_count for v in analyzed_videos)
        avg_views = total_views // len(analyzed_videos)
        median_views = sorted([v.view_count for v in analyzed_videos])[len(analyzed_videos) // 2]
        
        insights["view_analytics"] = {
            "total_views": total_views,
            "average_views": avg_views,
            "median_views": median_views,
            "top_performer": max(analyzed_videos, key=lambda v: v.view_count) if analyzed_videos else None
        }
        
        # Time-based trends
        recent_videos = [v for v in analyzed_videos if (datetime.now() - v.published_at).days <= 7]
        this_month_videos = [v for v in analyzed_videos if (datetime.now() - v.published_at).days <= 30]
        
        insights["temporal_trends"] = {
            "recent_uploads": len(recent_videos),
            "recent_ratio": len(recent_videos) / len(analyzed_videos) if analyzed_videos else 0,
            "this_month_uploads": len(this_month_videos),
            "content_freshness": "high" if len(recent_videos) / len(analyzed_videos) > 0.3 else "medium" if len(recent_videos) / len(analyzed_videos) > 0.1 else "low"
        }
        
        # Viral content indicators
        viral_videos = [v for v in analyzed_videos if v.plugin_metadata.get('engagement_level') == 'viral']
        insights["viral_indicators"] = {
            "viral_count": len(viral_videos),
            "viral_ratio": len(viral_videos) / len(analyzed_videos) if analyzed_videos else 0
        }
        
        logger.info(f"Generated general insights for {len(analyzed_videos)} videos")
        return insights
    
    async def optimize_search_keywords(
        self, 
        original_keywords: List[str], 
        context: AnalysisContext
    ) -> List[str]:
        """Optimize search keywords for general content"""
        optimized = original_keywords.copy()
        
        # Add general enhancers based on content type
        content_type = context.user_request.content_filter.content_type
        
        if content_type == ContentType.GENERAL_CHALLENGE:
            general_enhancers = ["challenge", "trend", "popular"]
        elif content_type == ContentType.CREATIVE_CHALLENGE:
            general_enhancers = ["creative", "diy", "tutorial"]
        elif content_type == ContentType.GAME_CHALLENGE:
            general_enhancers = ["gaming", "play", "fun"]
        else:
            general_enhancers = ["popular", "trending", "2024"]
        
        for enhancer in general_enhancers:
            if enhancer not in [k.lower() for k in optimized]:
                optimized.append(enhancer)
        
        # Add recency keywords if not present
        recency_keywords = ["latest", "new", "recent"]
        if not any(keyword in [k.lower() for k in optimized] for keyword in recency_keywords):
            optimized.append("latest")
        
        logger.info(f"Optimized general keywords: {original_keywords} -> {optimized}")
        return optimized
    
    async def recommend_related_content(
        self, 
        base_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend related general content"""
        if not base_videos:
            return []
        
        recommendations = []
        
        # Analyze base videos to understand user preferences
        popular_categories = self._get_popular_categories(base_videos)
        avg_engagement = self._get_average_engagement(base_videos)
        
        # Generate recommendations based on analysis
        if popular_categories:
            top_category = list(popular_categories.keys())[0]
            recommendations.append({
                "type": "same_category",
                "title": f"더 많은 {top_category} 콘텐츠",
                "description": f"{top_category} 카테고리의 인기 영상들",
                "search_keywords": [top_category, "popular", "trending"]
            })
        
        # Trending content recommendation
        recommendations.append({
            "type": "trending",
            "title": "지금 뜨는 콘텐츠",
            "description": "최근 인기를 끌고 있는 다양한 콘텐츠",
            "search_keywords": ["viral", "trending", "popular", "2024"]
        })
        
        # Similar engagement level content
        if avg_engagement == "high" or avg_engagement == "viral":
            recommendations.append({
                "type": "high_engagement",
                "title": "화제의 영상들",
                "description": "높은 참여도를 보이는 인기 영상들",
                "search_keywords": ["viral", "popular", "trending"]
            })
        
        # Creative content suggestion
        recommendations.append({
            "type": "creative",
            "title": "창의적인 콘텐츠",
            "description": "독창적이고 재미있는 아이디어 영상들",
            "search_keywords": ["creative", "unique", "interesting"]
        })
        
        # Educational content suggestion
        recommendations.append({
            "type": "educational",
            "title": "유용한 정보 영상",
            "description": "배울 점이 있는 교육적인 콘텐츠",
            "search_keywords": ["tutorial", "how to", "educational"]
        })
        
        return recommendations[:max_recommendations]
    
    def _get_popular_categories(self, videos: List[EnhancedClassifiedVideo]) -> Dict[str, int]:
        """Get popular content categories from videos"""
        category_counts = {}
        for video in videos:
            category = video.plugin_metadata.get('content_category', 'general')
            if category != 'general':
                category_counts[category] = category_counts.get(category, 0) + 1
        
        return dict(sorted(category_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _get_average_engagement(self, videos: List[EnhancedClassifiedVideo]) -> str:
        """Get average engagement level from videos"""
        engagement_levels = {"viral": 4, "high": 3, "medium": 2, "low": 1, "unknown": 0}
        
        total_score = 0
        count = 0
        
        for video in videos:
            engagement = video.plugin_metadata.get('engagement_level', 'unknown')
            if engagement in engagement_levels:
                total_score += engagement_levels[engagement]
                count += 1
        
        if count == 0:
            return "medium"
        
        avg_score = total_score / count
        
        if avg_score >= 3.5:
            return "viral"
        elif avg_score >= 2.5:
            return "high"
        elif avg_score >= 1.5:
            return "medium"
        else:
            return "low"
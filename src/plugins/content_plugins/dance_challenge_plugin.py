"""Dance challenge content analysis plugin"""

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


class DanceChallengePlugin(BaseContentPlugin):
    """
    Specialized plugin for analyzing dance challenge content
    
    This plugin focuses on dance-related content with specific analysis for:
    - Dance difficulty assessment
    - Choreography style identification
    - Music genre detection
    - Participant count and demographics
    - Safety and accessibility evaluation
    """
    
    def __init__(self):
        super().__init__()
        self.analyzer_agent = None
    
    def _define_metadata(self) -> PluginMetadata:
        """Define metadata for dance challenge plugin"""
        return PluginMetadata(
            name="dance_challenge_analyzer",
            version="1.0.0",
            description="Specialized analyzer for dance challenges and choreography content",
            content_types=[
                ContentType.DANCE_CHALLENGE,
                ContentType.GENERAL_CHALLENGE  # Can also handle general challenges
            ],
            capabilities=[
                PluginCapability.CONTENT_CLASSIFICATION,
                PluginCapability.VIDEO_ANALYSIS,
                PluginCapability.TREND_ANALYSIS,
                PluginCapability.RECOMMENDATION
            ],
            supported_languages=["korean", "english"],
            author="YouTube Trends Analysis Team",
            min_confidence_threshold=0.6,
            max_videos_per_batch=30
        )
    
    async def _setup(self) -> None:
        """Initialize the analyzer agent"""
        logger.info("Setting up Dance Challenge Plugin...")
        self.analyzer_agent = create_analyzer_agent()
        logger.info("Dance Challenge Plugin setup completed")
    
    def _calculate_handling_confidence(self, user_request: ParsedUserRequest) -> float:
        """Calculate confidence for handling dance-related requests"""
        base_confidence = 0.9  # High confidence for dance content
        
        # Boost confidence for dance-specific keywords
        dance_keywords = ["댄스", "춤", "dance", "choreography", "안무", "kpop", "k-pop"]
        request_text = user_request.original_input.lower()
        
        for keyword in dance_keywords:
            if keyword in request_text:
                base_confidence = min(base_confidence + 0.1, 1.0)
                break
        
        # Additional boosts for specific dance criteria
        if user_request.content_filter.difficulty:
            base_confidence = min(base_confidence + 0.05, 1.0)
        
        if user_request.content_filter.genre and "k-pop" in user_request.content_filter.genre.lower():
            base_confidence = min(base_confidence + 0.05, 1.0)
        
        return base_confidence
    
    async def analyze_videos(
        self, 
        videos: List[YouTubeVideoRaw], 
        context: AnalysisContext
    ) -> PluginResult:
        """Analyze dance challenge videos"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Dance plugin analyzing {len(videos)} videos")
            
            # Use the analyzer agent for video classification
            include_video_analysis = (
                context.analysis_depth == "detailed" or 
                len(videos) <= 10
            )
            
            analyzed_videos = await self.analyzer_agent.classify_videos_with_enhanced_analysis(
                videos,
                include_video_content=include_video_analysis
            )
            
            # Filter for dance-related content
            dance_videos = []
            for video in analyzed_videos:
                if self._is_dance_related(video, context):
                    dance_videos.append(video)
            
            # Apply dance-specific enhancements
            enhanced_videos = []
            for video in dance_videos:
                enhanced_video = await self._enhance_dance_analysis(video, context)
                enhanced_videos.append(enhanced_video)
            
            # Sort by dance-specific criteria
            sorted_videos = self._sort_dance_videos(enhanced_videos, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate confidence score based on dance relevance
            confidence_score = self._calculate_analysis_confidence(sorted_videos)
            
            logger.info(f"Dance analysis completed: {len(sorted_videos)} dance videos identified")
            
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
                    "dance_video_count": len(sorted_videos),
                    "analysis_depth": context.analysis_depth
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Dance video analysis failed: {e}")
            
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
    
    def _is_dance_related(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> bool:
        """Check if video is dance-related"""
        # Check video category
        if video.category == VideoCategory.CHALLENGE and video.challenge_type == ChallengeType.DANCE:
            return True
        
        # Check title and description for dance keywords
        dance_keywords = ["댄스", "춤", "dance", "choreography", "안무", "challenge"]
        video_text = f"{video.title} {getattr(video, 'description', '')}".lower()
        
        return any(keyword in video_text for keyword in dance_keywords)
    
    async def _enhance_dance_analysis(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> EnhancedClassifiedVideo:
        """Apply dance-specific enhancements to video analysis"""
        # Add dance-specific scoring
        dance_score = self._calculate_dance_score(video, context)
        
        # Update metadata with dance-specific information
        if not hasattr(video, 'plugin_metadata'):
            video.plugin_metadata = {}
        
        video.plugin_metadata['dance_score'] = dance_score
        video.plugin_metadata['plugin_name'] = self.metadata.name
        
        # Enhance difficulty assessment for dance content
        if video.has_video_analysis and hasattr(video.enhanced_analysis, 'accessibility_analysis'):
            difficulty = self._assess_dance_difficulty(video, context)
            video.enhanced_analysis.accessibility_analysis.difficulty_level = difficulty
        
        return video
    
    def _calculate_dance_score(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> float:
        """Calculate dance-specific relevance score"""
        score = 0.0
        
        # Base score from video classification confidence
        score += video.confidence * 0.4
        
        # Title relevance
        title_keywords = ["댄스", "춤", "dance", "challenge", "choreography"]
        title_lower = video.title.lower()
        title_matches = sum(1 for keyword in title_keywords if keyword in title_lower)
        score += (title_matches / len(title_keywords)) * 0.3
        
        # View count factor (popular content gets higher score)
        if video.view_count > 1000000:  # 1M+ views
            score += 0.2
        elif video.view_count > 100000:  # 100K+ views
            score += 0.1
        
        # Recency factor (newer content gets slight boost)
        days_old = (datetime.now() - video.published_at).days
        if days_old <= 7:
            score += 0.1
        elif days_old <= 30:
            score += 0.05
        
        return min(score, 1.0)
    
    def _assess_dance_difficulty(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> DifficultyLevel:
        """Assess dance difficulty based on content analysis"""
        # Default difficulty assessment logic
        title_lower = video.title.lower()
        
        # Check for difficulty indicators in title
        if any(word in title_lower for word in ["초보", "쉬운", "easy", "beginner", "simple"]):
            return DifficultyLevel.EASY
        elif any(word in title_lower for word in ["고급", "어려운", "hard", "advanced", "complex"]):
            return DifficultyLevel.HARD
        elif any(word in title_lower for word in ["전문", "프로", "professional", "expert"]):
            return DifficultyLevel.EXPERT
        else:
            return DifficultyLevel.MEDIUM
    
    def _sort_dance_videos(self, videos: List[EnhancedClassifiedVideo], context: AnalysisContext) -> List[EnhancedClassifiedVideo]:
        """Sort videos by dance-specific criteria"""
        user_request = context.user_request
        
        # Determine sort criteria from user request
        if user_request.quantity_filter.sort_order.value == "difficulty_asc":
            # Sort by difficulty (easy first)
            return sorted(videos, key=lambda v: self._get_difficulty_score(v))
        elif user_request.quantity_filter.sort_order.value == "difficulty_desc":
            # Sort by difficulty (hard first)
            return sorted(videos, key=lambda v: self._get_difficulty_score(v), reverse=True)
        elif user_request.quantity_filter.sort_order.value == "view_count_desc":
            # Sort by view count (high first)
            return sorted(videos, key=lambda v: v.view_count, reverse=True)
        else:
            # Default: sort by dance relevance score
            return sorted(videos, key=lambda v: v.plugin_metadata.get('dance_score', 0), reverse=True)
    
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
        
        # Average dance score
        avg_dance_score = sum(v.plugin_metadata.get('dance_score', 0) for v in videos) / len(videos)
        
        # Combine both scores
        return (avg_confidence * 0.6 + avg_dance_score * 0.4)
    
    async def generate_insights(
        self, 
        analyzed_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """Generate dance-specific insights"""
        if not analyzed_videos:
            return {}
        
        insights = {}
        
        # Difficulty distribution
        difficulty_counts = {}
        for video in analyzed_videos:
            if video.has_video_analysis:
                difficulty = video.enhanced_analysis.accessibility_analysis.difficulty_level.value
                difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        insights["difficulty_distribution"] = difficulty_counts
        
        # Popular dance styles (extracted from titles)
        dance_styles = self._extract_dance_styles(analyzed_videos)
        insights["popular_dance_styles"] = dance_styles
        
        # K-pop vs other genres
        kpop_count = sum(1 for v in analyzed_videos if "k-pop" in v.title.lower() or "kpop" in v.title.lower())
        insights["kpop_ratio"] = kpop_count / len(analyzed_videos) if analyzed_videos else 0
        
        # View count analytics
        total_views = sum(v.view_count for v in analyzed_videos)
        avg_views = total_views // len(analyzed_videos)
        insights["view_analytics"] = {
            "total_views": total_views,
            "average_views": avg_views,
            "top_performer": max(analyzed_videos, key=lambda v: v.view_count) if analyzed_videos else None
        }
        
        # Trend indicators
        recent_videos = [v for v in analyzed_videos if (datetime.now() - v.published_at).days <= 7]
        insights["trend_indicators"] = {
            "recent_uploads": len(recent_videos),
            "recent_ratio": len(recent_videos) / len(analyzed_videos) if analyzed_videos else 0
        }
        
        logger.info(f"Generated dance insights for {len(analyzed_videos)} videos")
        return insights
    
    def _extract_dance_styles(self, videos: List[EnhancedClassifiedVideo]) -> Dict[str, int]:
        """Extract and count dance styles from video titles"""
        style_keywords = {
            "k-pop": ["k-pop", "kpop", "케이팝"],
            "hip-hop": ["hip-hop", "hiphop", "힙합"],
            "street": ["street", "스트릿"],
            "contemporary": ["contemporary", "컨템포러리"],
            "jazz": ["jazz", "재즈"],
            "ballet": ["ballet", "발레"],
            "latin": ["latin", "라틴"],
            "ballroom": ["ballroom", "볼룸"]
        }
        
        style_counts = {}
        
        for video in videos:
            title_lower = video.title.lower()
            for style, keywords in style_keywords.items():
                if any(keyword in title_lower for keyword in keywords):
                    style_counts[style] = style_counts.get(style, 0) + 1
        
        # Sort by popularity
        return dict(sorted(style_counts.items(), key=lambda x: x[1], reverse=True))
    
    async def optimize_search_keywords(
        self, 
        original_keywords: List[str], 
        context: AnalysisContext
    ) -> List[str]:
        """Optimize search keywords for dance content"""
        optimized = original_keywords.copy()
        
        # Add dance-specific keywords if not present
        dance_enhancers = ["challenge", "choreography", "tutorial"]
        for enhancer in dance_enhancers:
            if enhancer not in [k.lower() for k in optimized]:
                optimized.append(enhancer)
        
        # Add K-pop specific terms if relevant
        if any("k-pop" in k.lower() or "kpop" in k.lower() for k in original_keywords):
            kpop_enhancers = ["idol", "cover", "dance practice"]
            for enhancer in kpop_enhancers:
                if enhancer not in [k.lower() for k in optimized]:
                    optimized.append(enhancer)
        
        logger.info(f"Optimized dance keywords: {original_keywords} -> {optimized}")
        return optimized
    
    async def recommend_related_content(
        self, 
        base_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend related dance content"""
        if not base_videos:
            return []
        
        recommendations = []
        
        # Analyze base videos to understand user preferences
        preferred_difficulty = self._get_preferred_difficulty(base_videos)
        popular_styles = self._extract_dance_styles(base_videos)
        
        # Generate recommendations based on analysis
        recommendations.append({
            "type": "difficulty_progression",
            "title": f"다음 단계 난이도 댄스 챌린지",
            "description": f"{preferred_difficulty} 다음 단계의 댄스를 시도해보세요",
            "search_keywords": ["dance", "challenge", self._get_next_difficulty(preferred_difficulty)]
        })
        
        if popular_styles:
            top_style = list(popular_styles.keys())[0]
            recommendations.append({
                "type": "same_style",
                "title": f"더 많은 {top_style} 댄스",
                "description": f"{top_style} 스타일의 인기 댄스 챌린지를 더 찾아보세요",
                "search_keywords": ["dance", top_style, "popular"]
            })
        
        # Add trending recommendations
        recommendations.append({
            "type": "trending",
            "title": "지금 뜨는 댄스 챌린지",
            "description": "최근 인기를 끌고 있는 새로운 댄스 트렌드",
            "search_keywords": ["viral dance", "trending", "2024"]
        })
        
        return recommendations[:max_recommendations]
    
    def _get_preferred_difficulty(self, videos: List[EnhancedClassifiedVideo]) -> str:
        """Get most common difficulty level from videos"""
        difficulty_counts = {}
        for video in videos:
            if video.has_video_analysis:
                difficulty = video.enhanced_analysis.accessibility_analysis.difficulty_level.value
                difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        if difficulty_counts:
            return max(difficulty_counts.items(), key=lambda x: x[1])[0]
        return "medium"
    
    def _get_next_difficulty(self, current_difficulty: str) -> str:
        """Get next difficulty level for progression"""
        progression = {
            "easy": "medium",
            "medium": "hard", 
            "hard": "expert",
            "expert": "expert"  # Stay at expert
        }
        return progression.get(current_difficulty, "medium")
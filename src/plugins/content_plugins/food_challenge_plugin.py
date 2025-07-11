"""Food challenge content analysis plugin"""

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


class FoodChallengePlugin(BaseContentPlugin):
    """
    Specialized plugin for analyzing food challenge and cooking content
    
    This plugin focuses on food-related content with specific analysis for:
    - Cooking difficulty assessment
    - Recipe complexity evaluation
    - Cuisine type identification
    - Ingredient accessibility
    - Safety and dietary considerations
    """
    
    def __init__(self):
        super().__init__()
        self.analyzer_agent = None
    
    def _define_metadata(self) -> PluginMetadata:
        """Define metadata for food challenge plugin"""
        return PluginMetadata(
            name="food_challenge_analyzer",
            version="1.0.0",
            description="Specialized analyzer for food challenges, cooking tutorials, and culinary content",
            content_types=[
                ContentType.FOOD_CHALLENGE,
                ContentType.GENERAL_CHALLENGE
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
            max_videos_per_batch=25
        )
    
    async def _setup(self) -> None:
        """Initialize the analyzer agent"""
        logger.info("Setting up Food Challenge Plugin...")
        self.analyzer_agent = create_analyzer_agent()
        logger.info("Food Challenge Plugin setup completed")
    
    def _calculate_handling_confidence(self, user_request: ParsedUserRequest) -> float:
        """Calculate confidence for handling food-related requests"""
        base_confidence = 0.85  # High confidence for food content
        
        # Boost confidence for food-specific keywords
        food_keywords = ["음식", "요리", "레시피", "food", "cooking", "recipe", "먹방", "쿡방"]
        request_text = user_request.original_input.lower()
        
        for keyword in food_keywords:
            if keyword in request_text:
                base_confidence = min(base_confidence + 0.1, 1.0)
                break
        
        # Additional boosts for specific food criteria
        if user_request.content_filter.difficulty:
            base_confidence = min(base_confidence + 0.05, 1.0)
        
        return base_confidence
    
    async def analyze_videos(
        self, 
        videos: List[YouTubeVideoRaw], 
        context: AnalysisContext
    ) -> PluginResult:
        """Analyze food challenge videos"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Food plugin analyzing {len(videos)} videos")
            
            # Use the analyzer agent for video classification
            include_video_analysis = (
                context.analysis_depth == "detailed" or 
                len(videos) <= 10
            )
            
            analyzed_videos = await self.analyzer_agent.classify_videos_with_enhanced_analysis(
                videos,
                include_video_content=include_video_analysis
            )
            
            # Filter for food-related content
            food_videos = []
            for video in analyzed_videos:
                if self._is_food_related(video, context):
                    food_videos.append(video)
            
            # Apply food-specific enhancements
            enhanced_videos = []
            for video in food_videos:
                enhanced_video = await self._enhance_food_analysis(video, context)
                enhanced_videos.append(enhanced_video)
            
            # Sort by food-specific criteria
            sorted_videos = self._sort_food_videos(enhanced_videos, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate confidence score based on food relevance
            confidence_score = self._calculate_analysis_confidence(sorted_videos)
            
            logger.info(f"Food analysis completed: {len(sorted_videos)} food videos identified")
            
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
                    "food_video_count": len(sorted_videos),
                    "analysis_depth": context.analysis_depth
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Food video analysis failed: {e}")
            
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
    
    def _is_food_related(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> bool:
        """Check if video is food-related"""
        # Check video category
        if video.category == VideoCategory.CHALLENGE and video.challenge_type == ChallengeType.FOOD:
            return True
        
        # Check title and description for food keywords
        food_keywords = [
            "음식", "요리", "레시피", "food", "cooking", "recipe", "먹방", "쿡방",
            "베이킹", "baking", "디저트", "dessert", "간식", "snack"
        ]
        video_text = f"{video.title} {getattr(video, 'description', '')}".lower()
        
        return any(keyword in video_text for keyword in food_keywords)
    
    async def _enhance_food_analysis(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> EnhancedClassifiedVideo:
        """Apply food-specific enhancements to video analysis"""
        # Add food-specific scoring
        food_score = self._calculate_food_score(video, context)
        
        # Update metadata with food-specific information
        if not hasattr(video, 'plugin_metadata'):
            video.plugin_metadata = {}
        
        video.plugin_metadata['food_score'] = food_score
        video.plugin_metadata['plugin_name'] = self.metadata.name
        video.plugin_metadata['cuisine_type'] = self._identify_cuisine_type(video)
        video.plugin_metadata['cooking_method'] = self._identify_cooking_method(video)
        
        # Enhance difficulty assessment for food content
        if video.has_video_analysis and hasattr(video.enhanced_analysis, 'accessibility_analysis'):
            difficulty = self._assess_cooking_difficulty(video, context)
            video.enhanced_analysis.accessibility_analysis.difficulty_level = difficulty
        
        return video
    
    def _calculate_food_score(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> float:
        """Calculate food-specific relevance score"""
        score = 0.0
        
        # Base score from video classification confidence
        score += video.confidence * 0.4
        
        # Title relevance
        title_keywords = ["음식", "요리", "레시피", "food", "cooking", "recipe", "challenge"]
        title_lower = video.title.lower()
        title_matches = sum(1 for keyword in title_keywords if keyword in title_lower)
        score += (title_matches / len(title_keywords)) * 0.3
        
        # View count factor (popular content gets higher score)
        if video.view_count > 500000:  # 500K+ views
            score += 0.2
        elif video.view_count > 50000:  # 50K+ views
            score += 0.1
        
        # Recency factor (newer content gets slight boost)
        days_old = (datetime.now() - video.published_at).days
        if days_old <= 7:
            score += 0.1
        elif days_old <= 30:
            score += 0.05
        
        return min(score, 1.0)
    
    def _identify_cuisine_type(self, video: EnhancedClassifiedVideo) -> str:
        """Identify cuisine type from video content"""
        title_lower = video.title.lower()
        
        cuisine_indicators = {
            "korean": ["한식", "김치", "떡볶이", "korean", "k-food"],
            "japanese": ["일식", "라멘", "스시", "japanese", "ramen", "sushi"],
            "chinese": ["중식", "짜장면", "chinese", "dumpling"],
            "western": ["파스타", "pizza", "burger", "western", "pasta"],
            "italian": ["이탈리안", "italian", "pasta", "pizza"],
            "dessert": ["디저트", "케이크", "dessert", "cake", "cookie"],
            "baking": ["베이킹", "baking", "bread", "빵"]
        }
        
        for cuisine, keywords in cuisine_indicators.items():
            if any(keyword in title_lower for keyword in keywords):
                return cuisine
        
        return "general"
    
    def _identify_cooking_method(self, video: EnhancedClassifiedVideo) -> str:
        """Identify cooking method from video content"""
        title_lower = video.title.lower()
        
        method_indicators = {
            "no_cook": ["노쿡", "no cook", "간단", "5분"],
            "frying": ["튀김", "후라이", "fry", "fried"],
            "baking": ["베이킹", "오븐", "baking", "oven"],
            "grilling": ["그릴", "구이", "grill", "bbq"],
            "boiling": ["끓이기", "삶기", "boil"],
            "steaming": ["찜", "steam"]
        }
        
        for method, keywords in method_indicators.items():
            if any(keyword in title_lower for keyword in keywords):
                return method
        
        return "general_cooking"
    
    def _assess_cooking_difficulty(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> DifficultyLevel:
        """Assess cooking difficulty based on content analysis"""
        title_lower = video.title.lower()
        
        # Check for difficulty indicators in title
        if any(word in title_lower for word in ["초보", "쉬운", "간단", "easy", "simple", "5분", "노쿡"]):
            return DifficultyLevel.EASY
        elif any(word in title_lower for word in ["어려운", "복잡한", "hard", "complex", "professional"]):
            return DifficultyLevel.HARD
        elif any(word in title_lower for word in ["마스터", "전문가", "expert", "advanced"]):
            return DifficultyLevel.EXPERT
        else:
            return DifficultyLevel.MEDIUM
    
    def _sort_food_videos(self, videos: List[EnhancedClassifiedVideo], context: AnalysisContext) -> List[EnhancedClassifiedVideo]:
        """Sort videos by food-specific criteria"""
        user_request = context.user_request
        
        # Determine sort criteria from user request
        if user_request.quantity_filter.sort_order.value == "difficulty_asc":
            return sorted(videos, key=lambda v: self._get_difficulty_score(v))
        elif user_request.quantity_filter.sort_order.value == "difficulty_desc":
            return sorted(videos, key=lambda v: self._get_difficulty_score(v), reverse=True)
        elif user_request.quantity_filter.sort_order.value == "view_count_desc":
            return sorted(videos, key=lambda v: v.view_count, reverse=True)
        else:
            # Default: sort by food relevance score
            return sorted(videos, key=lambda v: v.plugin_metadata.get('food_score', 0), reverse=True)
    
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
        
        # Average food score
        avg_food_score = sum(v.plugin_metadata.get('food_score', 0) for v in videos) / len(videos)
        
        # Combine both scores
        return (avg_confidence * 0.6 + avg_food_score * 0.4)
    
    async def generate_insights(
        self, 
        analyzed_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """Generate food-specific insights"""
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
        
        # Cuisine type distribution
        cuisine_counts = {}
        for video in analyzed_videos:
            cuisine = video.plugin_metadata.get('cuisine_type', 'general')
            cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
        
        insights["cuisine_distribution"] = cuisine_counts
        
        # Cooking method distribution
        method_counts = {}
        for video in analyzed_videos:
            method = video.plugin_metadata.get('cooking_method', 'general_cooking')
            method_counts[method] = method_counts.get(method, 0) + 1
        
        insights["cooking_method_distribution"] = method_counts
        
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
        no_cook_count = sum(1 for v in analyzed_videos if v.plugin_metadata.get('cooking_method') == 'no_cook')
        
        insights["trend_indicators"] = {
            "recent_uploads": len(recent_videos),
            "recent_ratio": len(recent_videos) / len(analyzed_videos) if analyzed_videos else 0,
            "no_cook_popularity": no_cook_count / len(analyzed_videos) if analyzed_videos else 0
        }
        
        logger.info(f"Generated food insights for {len(analyzed_videos)} videos")
        return insights
    
    async def optimize_search_keywords(
        self, 
        original_keywords: List[str], 
        context: AnalysisContext
    ) -> List[str]:
        """Optimize search keywords for food content"""
        optimized = original_keywords.copy()
        
        # Add food-specific keywords if not present
        food_enhancers = ["recipe", "cooking", "tutorial", "how to make"]
        for enhancer in food_enhancers:
            if enhancer not in [k.lower() for k in optimized]:
                optimized.append(enhancer)
        
        # Add difficulty-specific terms if relevant
        if context.user_request.content_filter.difficulty == DifficultyLevel.EASY:
            easy_enhancers = ["easy", "simple", "quick", "5 minute"]
            for enhancer in easy_enhancers:
                if enhancer not in [k.lower() for k in optimized]:
                    optimized.append(enhancer)
        
        logger.info(f"Optimized food keywords: {original_keywords} -> {optimized}")
        return optimized
    
    async def recommend_related_content(
        self, 
        base_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend related food content"""
        if not base_videos:
            return []
        
        recommendations = []
        
        # Analyze base videos to understand user preferences
        preferred_difficulty = self._get_preferred_difficulty(base_videos)
        popular_cuisines = self._get_popular_cuisines(base_videos)
        popular_methods = self._get_popular_methods(base_videos)
        
        # Generate recommendations based on analysis
        if popular_cuisines:
            top_cuisine = list(popular_cuisines.keys())[0]
            recommendations.append({
                "type": "same_cuisine",
                "title": f"더 많은 {top_cuisine} 요리",
                "description": f"{top_cuisine} 스타일의 인기 레시피를 더 찾아보세요",
                "search_keywords": ["cooking", top_cuisine, "recipe"]
            })
        
        if popular_methods:
            top_method = list(popular_methods.keys())[0]
            if top_method == "no_cook":
                recommendations.append({
                    "type": "similar_method",
                    "title": "더 많은 노쿡 레시피",
                    "description": "요리 없이 만들 수 있는 간편한 음식들",
                    "search_keywords": ["no cook", "easy", "quick snack"]
                })
        
        recommendations.append({
            "type": "difficulty_progression",
            "title": f"다음 단계 난이도 요리",
            "description": f"{preferred_difficulty} 다음 단계의 요리를 시도해보세요",
            "search_keywords": ["cooking", self._get_next_difficulty(preferred_difficulty)]
        })
        
        # Add trending recommendations
        recommendations.append({
            "type": "trending",
            "title": "지금 뜨는 음식 트렌드",
            "description": "최근 인기를 끌고 있는 새로운 음식 트렌드",
            "search_keywords": ["viral food", "trending recipe", "2024"]
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
    
    def _get_popular_cuisines(self, videos: List[EnhancedClassifiedVideo]) -> Dict[str, int]:
        """Get popular cuisine types from videos"""
        cuisine_counts = {}
        for video in videos:
            cuisine = video.plugin_metadata.get('cuisine_type', 'general')
            if cuisine != 'general':
                cuisine_counts[cuisine] = cuisine_counts.get(cuisine, 0) + 1
        
        return dict(sorted(cuisine_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _get_popular_methods(self, videos: List[EnhancedClassifiedVideo]) -> Dict[str, int]:
        """Get popular cooking methods from videos"""
        method_counts = {}
        for video in videos:
            method = video.plugin_metadata.get('cooking_method', 'general_cooking')
            if method != 'general_cooking':
                method_counts[method] = method_counts.get(method, 0) + 1
        
        return dict(sorted(method_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _get_next_difficulty(self, current_difficulty: str) -> str:
        """Get next difficulty level for progression"""
        progression = {
            "easy": "medium",
            "medium": "hard", 
            "hard": "expert",
            "expert": "expert"  # Stay at expert
        }
        return progression.get(current_difficulty, "medium")
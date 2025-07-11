"""Fitness challenge content analysis plugin"""

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


class FitnessChallengePlugin(BaseContentPlugin):
    """
    Specialized plugin for analyzing fitness challenge and workout content
    
    This plugin focuses on fitness-related content with specific analysis for:
    - Workout intensity assessment
    - Exercise type identification
    - Equipment requirements
    - Target muscle groups
    - Safety and accessibility evaluation
    """
    
    def __init__(self):
        super().__init__()
        self.analyzer_agent = None
    
    def _define_metadata(self) -> PluginMetadata:
        """Define metadata for fitness challenge plugin"""
        return PluginMetadata(
            name="fitness_challenge_analyzer",
            version="1.0.0",
            description="Specialized analyzer for fitness challenges, workout tutorials, and health content",
            content_types=[
                ContentType.FITNESS_CHALLENGE,
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
        logger.info("Setting up Fitness Challenge Plugin...")
        self.analyzer_agent = create_analyzer_agent()
        logger.info("Fitness Challenge Plugin setup completed")
    
    def _calculate_handling_confidence(self, user_request: ParsedUserRequest) -> float:
        """Calculate confidence for handling fitness-related requests"""
        base_confidence = 0.85  # High confidence for fitness content
        
        # Boost confidence for fitness-specific keywords
        fitness_keywords = ["운동", "헬스", "피트니스", "다이어트", "fitness", "workout", "exercise"]
        request_text = user_request.original_input.lower()
        
        for keyword in fitness_keywords:
            if keyword in request_text:
                base_confidence = min(base_confidence + 0.1, 1.0)
                break
        
        # Additional boosts for specific fitness criteria
        if user_request.content_filter.difficulty:
            base_confidence = min(base_confidence + 0.05, 1.0)
        
        return base_confidence
    
    async def analyze_videos(
        self, 
        videos: List[YouTubeVideoRaw], 
        context: AnalysisContext
    ) -> PluginResult:
        """Analyze fitness challenge videos"""
        start_time = datetime.now()
        
        try:
            logger.info(f"Fitness plugin analyzing {len(videos)} videos")
            
            # Use the analyzer agent for video classification
            include_video_analysis = (
                context.analysis_depth == "detailed" or 
                len(videos) <= 10
            )
            
            analyzed_videos = await self.analyzer_agent.classify_videos_with_enhanced_analysis(
                videos,
                include_video_content=include_video_analysis
            )
            
            # Filter for fitness-related content
            fitness_videos = []
            for video in analyzed_videos:
                if self._is_fitness_related(video, context):
                    fitness_videos.append(video)
            
            # Apply fitness-specific enhancements
            enhanced_videos = []
            for video in fitness_videos:
                enhanced_video = await self._enhance_fitness_analysis(video, context)
                enhanced_videos.append(enhanced_video)
            
            # Sort by fitness-specific criteria
            sorted_videos = self._sort_fitness_videos(enhanced_videos, context)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Calculate confidence score based on fitness relevance
            confidence_score = self._calculate_analysis_confidence(sorted_videos)
            
            logger.info(f"Fitness analysis completed: {len(sorted_videos)} fitness videos identified")
            
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
                    "fitness_video_count": len(sorted_videos),
                    "analysis_depth": context.analysis_depth
                }
            )
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Fitness video analysis failed: {e}")
            
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
    
    def _is_fitness_related(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> bool:
        """Check if video is fitness-related"""
        # Check video category
        if video.category == VideoCategory.CHALLENGE and video.challenge_type == ChallengeType.FITNESS:
            return True
        
        # Check title and description for fitness keywords
        fitness_keywords = [
            "운동", "헬스", "피트니스", "다이어트", "fitness", "workout", "exercise",
            "홈트", "홈트레이닝", "요가", "yoga", "필라테스", "pilates", "스트레칭", "stretching"
        ]
        video_text = f"{video.title} {getattr(video, 'description', '')}".lower()
        
        return any(keyword in video_text for keyword in fitness_keywords)
    
    async def _enhance_fitness_analysis(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> EnhancedClassifiedVideo:
        """Apply fitness-specific enhancements to video analysis"""
        # Add fitness-specific scoring
        fitness_score = self._calculate_fitness_score(video, context)
        
        # Update metadata with fitness-specific information
        if not hasattr(video, 'plugin_metadata'):
            video.plugin_metadata = {}
        
        video.plugin_metadata['fitness_score'] = fitness_score
        video.plugin_metadata['plugin_name'] = self.metadata.name
        video.plugin_metadata['workout_type'] = self._identify_workout_type(video)
        video.plugin_metadata['equipment_needed'] = self._identify_equipment_requirements(video)
        video.plugin_metadata['target_area'] = self._identify_target_areas(video)
        
        # Enhance difficulty assessment for fitness content
        if video.has_video_analysis and hasattr(video.enhanced_analysis, 'accessibility_analysis'):
            difficulty = self._assess_workout_difficulty(video, context)
            video.enhanced_analysis.accessibility_analysis.difficulty_level = difficulty
        
        return video
    
    def _calculate_fitness_score(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> float:
        """Calculate fitness-specific relevance score"""
        score = 0.0
        
        # Base score from video classification confidence
        score += video.confidence * 0.4
        
        # Title relevance
        title_keywords = ["운동", "헬스", "피트니스", "workout", "fitness", "exercise", "challenge"]
        title_lower = video.title.lower()
        title_matches = sum(1 for keyword in title_keywords if keyword in title_lower)
        score += (title_matches / len(title_keywords)) * 0.3
        
        # View count factor (popular content gets higher score)
        if video.view_count > 300000:  # 300K+ views
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
    
    def _identify_workout_type(self, video: EnhancedClassifiedVideo) -> str:
        """Identify workout type from video content"""
        title_lower = video.title.lower()
        
        workout_indicators = {
            "cardio": ["유산소", "cardio", "hiit", "달리기", "running"],
            "strength": ["근력", "웨이트", "strength", "weight", "muscle"],
            "yoga": ["요가", "yoga"],
            "pilates": ["필라테스", "pilates"],
            "stretching": ["스트레칭", "stretching", "flexibility"],
            "dance_fitness": ["댄스핏", "dance fitness", "zumba"],
            "home_workout": ["홈트", "홈트레이닝", "home workout", "집에서"],
            "abs": ["복근", "abs", "core", "뱃살"],
            "legs": ["하체", "다리", "legs", "squat"],
            "arms": ["팔", "상체", "arms", "upper body"]
        }
        
        for workout_type, keywords in workout_indicators.items():
            if any(keyword in title_lower for keyword in keywords):
                return workout_type
        
        return "general_fitness"
    
    def _identify_equipment_requirements(self, video: EnhancedClassifiedVideo) -> str:
        """Identify equipment requirements from video content"""
        title_lower = video.title.lower()
        
        equipment_indicators = {
            "no_equipment": ["맨몸", "홈트", "집에서", "no equipment", "bodyweight"],
            "dumbbells": ["덤벨", "아령", "dumbbell"],
            "resistance_bands": ["밴드", "저항밴드", "resistance band"],
            "mat": ["매트", "요가매트", "mat", "yoga mat"],
            "weights": ["웨이트", "바벨", "weight", "barbell"],
            "gym": ["헬스장", "gym", "fitness center"]
        }
        
        for equipment, keywords in equipment_indicators.items():
            if any(keyword in title_lower for keyword in keywords):
                return equipment
        
        return "unknown"
    
    def _identify_target_areas(self, video: EnhancedClassifiedVideo) -> List[str]:
        """Identify target muscle groups/areas from video content"""
        title_lower = video.title.lower()
        target_areas = []
        
        area_indicators = {
            "abs": ["복근", "abs", "core", "뱃살"],
            "legs": ["하체", "다리", "legs", "허벅지", "종아리"],
            "arms": ["팔", "상체", "arms", "어깨", "shoulder"],
            "back": ["등", "back"],
            "chest": ["가슴", "chest"],
            "glutes": ["엉덩이", "glutes", "힙"],
            "full_body": ["전신", "full body", "온몸"]
        }
        
        for area, keywords in area_indicators.items():
            if any(keyword in title_lower for keyword in keywords):
                target_areas.append(area)
        
        return target_areas if target_areas else ["general"]
    
    def _assess_workout_difficulty(self, video: EnhancedClassifiedVideo, context: AnalysisContext) -> DifficultyLevel:
        """Assess workout difficulty based on content analysis"""
        title_lower = video.title.lower()
        
        # Check for difficulty indicators in title
        if any(word in title_lower for word in ["초보", "쉬운", "가벼운", "easy", "beginner", "gentle"]):
            return DifficultyLevel.EASY
        elif any(word in title_lower for word in ["어려운", "고강도", "intense", "hard", "advanced"]):
            return DifficultyLevel.HARD
        elif any(word in title_lower for word in ["전문가", "프로", "expert", "extreme"]):
            return DifficultyLevel.EXPERT
        else:
            return DifficultyLevel.MEDIUM
    
    def _sort_fitness_videos(self, videos: List[EnhancedClassifiedVideo], context: AnalysisContext) -> List[EnhancedClassifiedVideo]:
        """Sort videos by fitness-specific criteria"""
        user_request = context.user_request
        
        # Determine sort criteria from user request
        if user_request.quantity_filter.sort_order.value == "difficulty_asc":
            return sorted(videos, key=lambda v: self._get_difficulty_score(v))
        elif user_request.quantity_filter.sort_order.value == "difficulty_desc":
            return sorted(videos, key=lambda v: self._get_difficulty_score(v), reverse=True)
        elif user_request.quantity_filter.sort_order.value == "view_count_desc":
            return sorted(videos, key=lambda v: v.view_count, reverse=True)
        else:
            # Default: sort by fitness relevance score
            return sorted(videos, key=lambda v: v.plugin_metadata.get('fitness_score', 0), reverse=True)
    
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
        
        # Average fitness score
        avg_fitness_score = sum(v.plugin_metadata.get('fitness_score', 0) for v in videos) / len(videos)
        
        # Combine both scores
        return (avg_confidence * 0.6 + avg_fitness_score * 0.4)
    
    async def generate_insights(
        self, 
        analyzed_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext
    ) -> Dict[str, Any]:
        """Generate fitness-specific insights"""
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
        
        # Workout type distribution
        workout_counts = {}
        for video in analyzed_videos:
            workout_type = video.plugin_metadata.get('workout_type', 'general_fitness')
            workout_counts[workout_type] = workout_counts.get(workout_type, 0) + 1
        
        insights["workout_type_distribution"] = workout_counts
        
        # Equipment requirements distribution
        equipment_counts = {}
        for video in analyzed_videos:
            equipment = video.plugin_metadata.get('equipment_needed', 'unknown')
            equipment_counts[equipment] = equipment_counts.get(equipment, 0) + 1
        
        insights["equipment_distribution"] = equipment_counts
        
        # Target area analysis
        target_area_counts = {}
        for video in analyzed_videos:
            target_areas = video.plugin_metadata.get('target_area', ['general'])
            for area in target_areas:
                target_area_counts[area] = target_area_counts.get(area, 0) + 1
        
        insights["target_area_distribution"] = target_area_counts
        
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
        home_workout_count = sum(1 for v in analyzed_videos if v.plugin_metadata.get('workout_type') == 'home_workout')
        no_equipment_count = sum(1 for v in analyzed_videos if v.plugin_metadata.get('equipment_needed') == 'no_equipment')
        
        insights["trend_indicators"] = {
            "recent_uploads": len(recent_videos),
            "recent_ratio": len(recent_videos) / len(analyzed_videos) if analyzed_videos else 0,
            "home_workout_popularity": home_workout_count / len(analyzed_videos) if analyzed_videos else 0,
            "no_equipment_popularity": no_equipment_count / len(analyzed_videos) if analyzed_videos else 0
        }
        
        logger.info(f"Generated fitness insights for {len(analyzed_videos)} videos")
        return insights
    
    async def optimize_search_keywords(
        self, 
        original_keywords: List[str], 
        context: AnalysisContext
    ) -> List[str]:
        """Optimize search keywords for fitness content"""
        optimized = original_keywords.copy()
        
        # Add fitness-specific keywords if not present
        fitness_enhancers = ["workout", "exercise", "fitness", "challenge"]
        for enhancer in fitness_enhancers:
            if enhancer not in [k.lower() for k in optimized]:
                optimized.append(enhancer)
        
        # Add equipment-specific terms if relevant
        if context.user_request.content_filter.participants.value == "individual":
            home_enhancers = ["home workout", "no equipment", "bodyweight"]
            for enhancer in home_enhancers:
                if enhancer not in [k.lower() for k in optimized]:
                    optimized.append(enhancer)
        
        logger.info(f"Optimized fitness keywords: {original_keywords} -> {optimized}")
        return optimized
    
    async def recommend_related_content(
        self, 
        base_videos: List[EnhancedClassifiedVideo],
        context: AnalysisContext,
        max_recommendations: int = 5
    ) -> List[Dict[str, Any]]:
        """Recommend related fitness content"""
        if not base_videos:
            return []
        
        recommendations = []
        
        # Analyze base videos to understand user preferences
        preferred_difficulty = self._get_preferred_difficulty(base_videos)
        popular_workout_types = self._get_popular_workout_types(base_videos)
        popular_equipment = self._get_popular_equipment(base_videos)
        
        # Generate recommendations based on analysis
        if popular_workout_types:
            top_workout = list(popular_workout_types.keys())[0]
            recommendations.append({
                "type": "same_workout_type",
                "title": f"더 많은 {top_workout} 운동",
                "description": f"{top_workout} 운동의 다양한 루틴을 찾아보세요",
                "search_keywords": ["workout", top_workout, "exercise"]
            })
        
        if popular_equipment:
            top_equipment = list(popular_equipment.keys())[0]
            if top_equipment == "no_equipment":
                recommendations.append({
                    "type": "similar_equipment",
                    "title": "더 많은 맨몸 운동",
                    "description": "장비 없이 할 수 있는 홈트레이닝",
                    "search_keywords": ["home workout", "bodyweight", "no equipment"]
                })
        
        recommendations.append({
            "type": "difficulty_progression",
            "title": f"다음 단계 난이도 운동",
            "description": f"{preferred_difficulty} 다음 단계의 운동을 시도해보세요",
            "search_keywords": ["workout", self._get_next_difficulty(preferred_difficulty)]
        })
        
        # Add recovery/stretching recommendations
        recommendations.append({
            "type": "recovery",
            "title": "운동 후 스트레칭",
            "description": "운동 후 회복을 위한 스트레칭 루틴",
            "search_keywords": ["stretching", "cool down", "recovery"]
        })
        
        # Add trending recommendations
        recommendations.append({
            "type": "trending",
            "title": "지금 뜨는 피트니스 트렌드",
            "description": "최근 인기를 끌고 있는 새로운 운동 트렌드",
            "search_keywords": ["viral workout", "trending fitness", "2024"]
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
    
    def _get_popular_workout_types(self, videos: List[EnhancedClassifiedVideo]) -> Dict[str, int]:
        """Get popular workout types from videos"""
        workout_counts = {}
        for video in videos:
            workout_type = video.plugin_metadata.get('workout_type', 'general_fitness')
            if workout_type != 'general_fitness':
                workout_counts[workout_type] = workout_counts.get(workout_type, 0) + 1
        
        return dict(sorted(workout_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _get_popular_equipment(self, videos: List[EnhancedClassifiedVideo]) -> Dict[str, int]:
        """Get popular equipment requirements from videos"""
        equipment_counts = {}
        for video in videos:
            equipment = video.plugin_metadata.get('equipment_needed', 'unknown')
            if equipment != 'unknown':
                equipment_counts[equipment] = equipment_counts.get(equipment, 0) + 1
        
        return dict(sorted(equipment_counts.items(), key=lambda x: x[1], reverse=True))
    
    def _get_next_difficulty(self, current_difficulty: str) -> str:
        """Get next difficulty level for progression"""
        progression = {
            "easy": "medium",
            "medium": "hard", 
            "hard": "expert",
            "expert": "expert"  # Stay at expert
        }
        return progression.get(current_difficulty, "medium")
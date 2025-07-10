"""Analysis agent for video classification and trend reporting"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import Counter

from ..clients.llm_provider import LLMProvider, create_llm_provider
from ..models.video_models import (
    YouTubeVideoRaw, ClassifiedVideo, TrendReport, VideoCategory
)
from ..models.classification_models import (
    TrendAnalysisResult, CategoryInsights
)
from ..core.exceptions import ClassificationError
from ..core.settings import get_settings

# Setup logging
logger = logging.getLogger(__name__)


class AnalyzerAgent:
    """
    Analysis agent for video classification and trend reporting.
    
    STRICT ROLE: Analysis and reporting only, no external API calls.
    This agent receives data from CollectorAgent and performs AI-powered analysis.
    """
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        """
        Initialize analyzer agent.
        
        Args:
            llm_provider: LLM provider for classification (if None, creates new instance)
        """
        self.agent_name = "AnalyzerAgent"
        self.settings = get_settings()
        
        # Use dependency injection for testability
        self.llm_provider = llm_provider or create_llm_provider()
        
        # Analysis statistics
        self.analysis_stats = {
            "videos_analyzed": 0,
            "classifications_successful": 0,
            "classifications_failed": 0,
            "reports_generated": 0,
            "last_analysis": None
        }
        
        logger.info(f"[{self.agent_name}] Agent initialized with LLM: {self.llm_provider.get_model_info()}")
    
    async def classify_videos(self, videos: List[YouTubeVideoRaw]) -> List[ClassifiedVideo]:
        """
        Classify videos into categories using AI with optimized batch processing.
        
        STRICT ROLE: Analysis only, no external API calls.
        
        Args:
            videos: List of raw video data to classify
            
        Returns:
            List of classified videos with AI categorization
        """
        logger.info(f"[{self.agent_name}] Starting batch classification of {len(videos)} videos")
        
        if not videos:
            return []
        
        classified_videos = []
        batch_size = 5  # Start conservative, can tune up to 10
        
        # Process videos in batches
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(videos) + batch_size - 1) // batch_size
            
            logger.debug(f"[{self.agent_name}] Processing batch {batch_num}/{total_batches}: {len(batch)} videos")
            
            try:
                # Use new batch classification
                batch_responses = await self.llm_provider.classify_videos_batch_optimized(batch, batch_size)
                
                # Convert to ClassifiedVideo objects
                for response in batch_responses:
                    # Find the corresponding video by ID
                    video = next((v for v in batch if v.video_id == response.video_id), None)
                    if video:
                        classified_video = ClassifiedVideo(
                            video_id=video.video_id,
                            title=video.snippet.title,
                            category=response.category,
                            confidence=response.confidence,
                            reasoning=response.reasoning,
                            view_count=video.statistics.view_count if video.statistics else None,
                            published_at=video.snippet.published_at,
                            channel_title=video.snippet.channel_title
                        )
                        classified_videos.append(classified_video)
                        
                        logger.debug(f"[{self.agent_name}] Classified {video.video_id} as {response.category} "
                                    f"(confidence: {response.confidence:.2f})")
                
                self.analysis_stats["classifications_successful"] = (self.analysis_stats["classifications_successful"] or 0) + len(batch_responses)
                
            except ClassificationError as e:
                logger.warning(f"[{self.agent_name}] Batch classification failed for batch {batch_num}: {e}")
                self.analysis_stats["classifications_failed"] = (self.analysis_stats["classifications_failed"] or 0) + len(batch)
                
                # Try fallback individual classification for this batch
                logger.info(f"[{self.agent_name}] Attempting individual classification fallback for batch {batch_num}")
                for video in batch:
                    try:
                        classification_response = await self.llm_provider.classify_video(video)
                        
                        classified_video = ClassifiedVideo(
                            video_id=video.video_id,
                            title=video.snippet.title,
                            category=classification_response.category,
                            confidence=classification_response.confidence,
                            reasoning=classification_response.reasoning,
                            view_count=video.statistics.view_count if video.statistics else None,
                            published_at=video.snippet.published_at,
                            channel_title=video.snippet.channel_title
                        )
                        
                        classified_videos.append(classified_video)
                        self.analysis_stats["classifications_successful"] = (self.analysis_stats["classifications_successful"] or 0) + 1
                        
                        logger.debug(f"[{self.agent_name}] Individual fallback classified {video.video_id} as {classification_response.category}")
                        
                    except ClassificationError as fallback_error:
                        logger.warning(f"[{self.agent_name}] Individual fallback also failed for video {video.video_id}: {fallback_error}")
                        continue
        
        # Update statistics
        self.analysis_stats["videos_analyzed"] = (self.analysis_stats["videos_analyzed"] or 0) + len(videos)
        self.analysis_stats["last_analysis"] = datetime.now()
        
        logger.info(f"[{self.agent_name}] Batch classification complete: "
                   f"{len(classified_videos)}/{len(videos)} successful")
        
        return classified_videos
    
    def generate_trend_report(
        self, 
        classified_videos: List[ClassifiedVideo],
        category: Optional[VideoCategory] = None
    ) -> TrendReport:
        """
        Generate trend analysis report for classified videos.
        
        Args:
            classified_videos: List of classified videos to analyze
            category: Specific category to analyze (if None, analyzes all)
            
        Returns:
            Comprehensive trend report
        """
        logger.info(f"[{self.agent_name}] Generating trend report for {len(classified_videos)} videos")
        
        # Filter by category if specified
        videos_to_analyze = classified_videos
        if category:
            videos_to_analyze = [v for v in classified_videos if v.category == category]
            logger.info(f"[{self.agent_name}] Filtered to {len(videos_to_analyze)} videos for category {category}")
        
        if not videos_to_analyze:
            # Return empty report for the category
            return TrendReport(
                category=category or VideoCategory.CHALLENGE,
                trend_summary="No videos found for analysis",
                key_insights=["No data available for trend analysis"],
                recommended_actions=["Collect more videos for this category"],
                top_videos=[],
                total_videos_analyzed=0,
                analysis_period="Current session"
            )
        
        # Determine target category for report
        target_category = category or self._get_dominant_category(videos_to_analyze)
        
        # Filter to target category only
        category_videos = [v for v in videos_to_analyze if v.category == target_category]
        
        # Generate insights
        insights = self._analyze_category_trends(category_videos)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(target_category, category_videos)
        
        # Get top performing videos
        top_videos = self._get_top_videos(category_videos, limit=5)
        
        # Create trend summary
        trend_summary = self._create_trend_summary(target_category, category_videos)
        
        report = TrendReport(
            category=target_category,
            trend_summary=trend_summary,
            key_insights=insights,
            recommended_actions=recommendations,
            top_videos=top_videos,
            total_videos_analyzed=len(category_videos),
            analysis_period="Current session"
        )
        
        self.analysis_stats["reports_generated"] = (self.analysis_stats["reports_generated"] or 0) + 1
        logger.info(f"[{self.agent_name}] Trend report generated for {target_category}")
        
        return report
    
    def generate_comprehensive_analysis(
        self, 
        classified_videos: List[ClassifiedVideo]
    ) -> TrendAnalysisResult:
        """
        Generate comprehensive analysis across all categories.
        
        Args:
            classified_videos: List of all classified videos
            
        Returns:
            Complete trend analysis result
        """
        logger.info(f"[{self.agent_name}] Generating comprehensive analysis for {len(classified_videos)} videos")
        
        # Analyze each category
        category_insights = []
        for category in VideoCategory:
            category_videos = [v for v in classified_videos if v.category == category]
            if category_videos:
                insights = self._create_category_insights(category, category_videos)
                category_insights.append(insights)
        
        # Determine dominant category
        dominant_category = self._get_dominant_category(classified_videos)
        
        # Generate emerging trends
        emerging_trends = self._identify_emerging_trends(classified_videos)
        
        # Generate strategic recommendations
        content_strategy = self._generate_content_strategy(classified_videos)
        
        analysis_result = TrendAnalysisResult(
            analysis_period="Current session",
            total_videos_analyzed=len(classified_videos),
            category_insights=category_insights,
            dominant_category=dominant_category,
            emerging_trends=emerging_trends,
            recommended_content_strategy=content_strategy,
            model_version=f"{self.llm_provider.provider_name}/{self.llm_provider.model_name}"
        )
        
        logger.info(f"[{self.agent_name}] Comprehensive analysis complete")
        return analysis_result
    
    def _get_dominant_category(self, videos: List[ClassifiedVideo]) -> VideoCategory:
        """Get the most prevalent category"""
        if not videos:
            return VideoCategory.CHALLENGE
        
        category_counts = Counter(v.category for v in videos)
        return category_counts.most_common(1)[0][0]
    
    def _analyze_category_trends(self, videos: List[ClassifiedVideo]) -> List[str]:
        """Analyze trends within a specific category"""
        if not videos:
            return ["No videos to analyze"]
        
        insights = []
        
        # Analyze confidence levels
        avg_confidence = sum(v.confidence for v in videos) / len(videos)
        insights.append(f"Average classification confidence: {avg_confidence:.1%}")
        
        # Analyze view performance if available
        videos_with_views = [v for v in videos if v.view_count is not None]
        if videos_with_views:
            avg_views = sum(v.view_count or 0 for v in videos_with_views) / len(videos_with_views)
            insights.append(f"Average views: {avg_views:,.0f}")
            
            # Find high-performing videos
            high_performers = [v for v in videos_with_views if (v.view_count or 0) > avg_views * 1.5]
            if high_performers:
                insights.append(f"{len(high_performers)} high-performing videos (>50% above average)")
        
        # Analyze title patterns
        common_words = self._extract_common_keywords([v.title for v in videos])
        if common_words:
            insights.append(f"Common keywords: {', '.join(common_words[:5])}")
        
        return insights
    
    def _generate_recommendations(self, category: VideoCategory, videos: List[ClassifiedVideo]) -> List[str]:
        """Generate actionable recommendations for the category"""
        recommendations = []
        
        if category == VideoCategory.CHALLENGE:
            recommendations.extend([
                "Focus on viral dance challenges and fitness routines",
                "Create content that encourages user participation",
                "Use trending music and hashtags for maximum reach"
            ])
        elif category == VideoCategory.INFO_ADVICE:
            recommendations.extend([
                "Provide clear, actionable tips in short format",
                "Use eye-catching titles that promise value",
                "Include quick demonstrations or visual examples"
            ])
        elif category == VideoCategory.TRENDING_SOUNDS:
            recommendations.extend([
                "Stay updated with trending audio clips",
                "Create content that showcases musical talent",
                "Experiment with popular sound effects and remixes"
            ])
        
        # Add performance-based recommendations
        if videos:
            high_confidence_videos = [v for v in videos if v.confidence > 0.8]
            if high_confidence_videos:
                recommendations.append(f"Replicate patterns from {len(high_confidence_videos)} clearly categorized videos")
        
        return recommendations
    
    def _get_top_videos(self, videos: List[ClassifiedVideo], limit: int = 5) -> List[ClassifiedVideo]:
        """Get top performing videos based on views and confidence"""
        if not videos:
            return []
        
        # Sort by view count (if available) and confidence
        sorted_videos = sorted(
            videos,
            key=lambda v: (v.view_count or 0, v.confidence),
            reverse=True
        )
        
        return sorted_videos[:limit]
    
    def _create_trend_summary(self, category: VideoCategory, videos: List[ClassifiedVideo]) -> str:
        """Create a summary of trends for the category"""
        if not videos:
            return "No trend data available"
        
        total_videos = len(videos)
        avg_confidence = sum(v.confidence for v in videos) / total_videos
        
        summary = f"Analysis of {total_videos} {category.value} videos with {avg_confidence:.1%} average confidence. "
        
        if category == VideoCategory.CHALLENGE:
            summary += "Challenge content shows strong engagement potential with viral elements."
        elif category == VideoCategory.INFO_ADVICE:
            summary += "Educational content demonstrates consistent value delivery patterns."
        elif category == VideoCategory.TRENDING_SOUNDS:
            summary += "Music-focused content shows audio-driven engagement trends."
        
        return summary
    
    def _create_category_insights(self, category: VideoCategory, videos: List[ClassifiedVideo]) -> CategoryInsights:
        """Create detailed insights for a category"""
        avg_confidence = sum(v.confidence for v in videos) / len(videos)
        
        # Extract keywords from titles
        titles = [v.title for v in videos]
        common_keywords = self._extract_common_keywords(titles)
        
        # Calculate average views if available
        videos_with_views = [v for v in videos if v.view_count is not None]
        avg_views = None
        if videos_with_views:
            avg_views = sum(v.view_count or 0 for v in videos_with_views) / len(videos_with_views)
        
        return CategoryInsights(
            category=category,
            video_count=len(videos),
            average_confidence=avg_confidence,
            common_keywords=common_keywords[:10],
            trending_themes=self._identify_themes(category, titles),
            average_views=avg_views,
            engagement_score=avg_confidence  # Simplified engagement score
        )
    
    def _extract_common_keywords(self, texts: List[str]) -> List[str]:
        """Extract common keywords from text list"""
        if not texts:
            return []
        
        # Simple keyword extraction (could be enhanced with NLP)
        all_words = []
        for text in texts:
            words = text.lower().split()
            # Filter out common stop words
            filtered_words = [w for w in words if len(w) > 3 and w not in ['this', 'that', 'with', 'from', 'they']]
            all_words.extend(filtered_words)
        
        # Count and return most common
        word_counts = Counter(all_words)
        return [word for word, _ in word_counts.most_common(10)]
    
    def _identify_themes(self, category: VideoCategory, titles: List[str]) -> List[str]:
        """Identify trending themes within a category"""
        themes = []
        
        if category == VideoCategory.CHALLENGE:
            challenge_themes = ["dance", "fitness", "viral", "workout", "trend"]
            themes = [theme for theme in challenge_themes if any(theme in title.lower() for title in titles)]
        elif category == VideoCategory.INFO_ADVICE:
            advice_themes = ["tips", "how", "tutorial", "guide", "learn"]
            themes = [theme for theme in advice_themes if any(theme in title.lower() for title in titles)]
        elif category == VideoCategory.TRENDING_SOUNDS:
            sound_themes = ["music", "song", "sound", "audio", "remix"]
            themes = [theme for theme in sound_themes if any(theme in title.lower() for title in titles)]
        
        return themes[:5]
    
    def _identify_emerging_trends(self, videos: List[ClassifiedVideo]) -> List[str]:
        """Identify emerging trends across all categories"""
        # Simple implementation - could be enhanced with more sophisticated analysis
        all_titles = [v.title for v in videos]
        common_keywords = self._extract_common_keywords(all_titles)
        
        # Look for trend indicators
        trend_indicators = ["new", "viral", "trending", "popular", "latest", "2024"]
        emerging_trends = []
        
        for keyword in common_keywords[:5]:
            if any(indicator in keyword.lower() for indicator in trend_indicators):
                emerging_trends.append(f"Growing interest in {keyword}")
        
        if not emerging_trends:
            emerging_trends = ["Short-form content continues to drive engagement"]
        
        return emerging_trends
    
    def _generate_content_strategy(self, videos: List[ClassifiedVideo]) -> List[str]:
        """Generate strategic recommendations for content creators"""
        category_distribution = Counter(v.category for v in videos)
        total_videos = len(videos)
        
        strategies = []
        
        for category, count in category_distribution.most_common():
            percentage = (count / total_videos) * 100
            if percentage > 40:
                strategies.append(f"Focus heavily on {category.value} content ({percentage:.0f}% of current trends)")
            elif percentage > 20:
                strategies.append(f"Include {category.value} content in your strategy ({percentage:.0f}% representation)")
        
        # Add general strategies
        strategies.extend([
            "Maintain consistent posting schedule for shorts",
            "Engage with trending hashtags and sounds",
            "Monitor performance metrics for optimization"
        ])
        
        return strategies
    
    def get_analysis_stats(self) -> Dict[str, Any]:
        """Get analysis statistics for this session"""
        return self.analysis_stats.copy()
    
    def reset_stats(self) -> None:
        """Reset analysis statistics"""
        self.analysis_stats = {
            "videos_analyzed": 0,
            "classifications_successful": 0,
            "classifications_failed": 0,
            "reports_generated": 0,
            "last_analysis": None
        }
        logger.info(f"[{self.agent_name}] Statistics reset")


# Factory function for easy instantiation
def create_analyzer_agent(llm_provider: Optional[LLMProvider] = None) -> AnalyzerAgent:
    """
    Factory function to create analyzer agent.
    
    Args:
        llm_provider: Optional LLM provider for dependency injection
        
    Returns:
        Configured analyzer agent
    """
    return AnalyzerAgent(llm_provider=llm_provider)
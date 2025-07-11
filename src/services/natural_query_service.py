"""Natural language query processing service"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from ..core.prompt_parser import create_prompt_parser, PromptParser
from ..agents.collector_agent import create_collector_agent
from ..plugins.plugin_manager import create_plugin_manager
from ..plugins.base_plugin import AnalysisContext
from ..models.prompt_models import (
    ParsedUserRequest, ParsingResult, ActionType, ContentType, 
    ParticipantType, TimeRange, SortOrder, DifficultyLevel
)
from ..models.video_models import (
    YouTubeVideoRaw, EnhancedClassifiedVideo, VideoCategory, ChallengeType
)
from ..core.exceptions import YouTubeAPIError, ClassificationError

logger = logging.getLogger(__name__)


class QueryResponse:
    """Response from natural language query processing"""
    
    def __init__(self):
        self.success: bool = False
        self.parsed_request: Optional[ParsedUserRequest] = None
        self.results: List[EnhancedClassifiedVideo] = []
        self.total_found: int = 0
        self.processing_time: float = 0.0
        self.summary: str = ""
        self.detailed_report: str = ""
        self.error_message: Optional[str] = None
        self.warnings: List[str] = []
        self.metadata: Dict[str, Any] = {}


class NaturalQueryService:
    """
    Service for processing natural language queries and returning 
    structured analysis results
    """
    
    def __init__(self):
        """Initialize the natural query service"""
        self.prompt_parser = create_prompt_parser()
        self.collector_agent = None
        self.plugin_manager = None
        self._plugins_initialized = False
        
        # Query processing statistics
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0,
            "failed_queries": 0,
            "avg_processing_time": 0.0,
            "last_query_time": None
        }
        
        logger.info("NaturalQueryService initialized")
    
    async def _ensure_agents(self):
        """Ensure collector agent and plugin manager are available"""
        if self.collector_agent is None:
            self.collector_agent = create_collector_agent()
        
        if self.plugin_manager is None:
            self.plugin_manager = create_plugin_manager()
        
        # Initialize plugins if not done yet
        if not self._plugins_initialized:
            logger.info("Discovering and initializing plugins...")
            plugin_results = await self.plugin_manager.discover_and_load_plugins()
            self._plugins_initialized = True
            logger.info(f"Plugin initialization completed: {plugin_results['summary']}")
    
    async def process_query(self, user_input: str) -> QueryResponse:
        """
        Process a natural language query and return structured results
        
        Args:
            user_input: Natural language input from user
            
        Returns:
            QueryResponse with results or error information
        """
        start_time = datetime.now()
        response = QueryResponse()
        
        try:
            self.stats["total_queries"] += 1
            logger.info(f"Processing query: '{user_input}'")
            
            # Step 1: Parse the natural language input
            parsing_result = await self.prompt_parser.parse(user_input)
            
            if not parsing_result.success:
                response.error_message = f"파싱 실패: {parsing_result.error_message}"
                self.stats["failed_queries"] += 1
                return response
            
            response.parsed_request = parsing_result.parsed_request
            
            # Step 2: Convert parsed request to search parameters
            search_params = self._convert_to_search_params(parsing_result.parsed_request)
            
            # Step 3: Collect videos based on parsed parameters
            await self._ensure_agents()
            
            collected_videos = await self._collect_videos(search_params)
            logger.info(f"Collected {len(collected_videos)} videos")
            
            if not collected_videos:
                response.warning = ["검색 조건에 맞는 비디오를 찾을 수 없습니다."]
                response.summary = "검색 결과가 없습니다."
                response.success = True
                return response
            
            # Step 4: Analyze and classify videos
            analyzed_videos = await self._analyze_videos(
                collected_videos, 
                parsing_result.parsed_request
            )
            
            # Step 5: Limit results to requested count (plugins handle filtering/sorting)
            requested_count = parsing_result.parsed_request.quantity_filter.count
            final_results = analyzed_videos[:requested_count] if len(analyzed_videos) > requested_count else analyzed_videos
            
            # Step 6: Generate response and recommendations
            response.results = final_results
            response.total_found = len(final_results)
            
            # Get content recommendations if available
            if final_results:
                try:
                    recommendations = await self.plugin_manager.get_recommendations(
                        final_results, 
                        parsing_result.parsed_request,
                        max_recommendations=3
                    )
                    response.metadata['recommendations'] = recommendations
                except Exception as e:
                    logger.warning(f"Failed to get recommendations: {e}")
            response.success = True
            
            # Generate summary and detailed report
            response.summary = self._generate_summary(parsing_result.parsed_request, final_results)
            response.detailed_report = self._generate_detailed_report(
                parsing_result.parsed_request, 
                final_results
            )
            
            # Update statistics
            processing_time = (datetime.now() - start_time).total_seconds()
            response.processing_time = processing_time
            self.stats["successful_queries"] += 1
            self.stats["last_query_time"] = datetime.now()
            self._update_avg_processing_time(processing_time)
            
            logger.info(f"Query processed successfully: {len(final_results)} results in {processing_time:.2f}s")
            
        except Exception as e:
            logger.error(f"Query processing failed: {e}")
            response.error_message = str(e)
            response.success = False
            self.stats["failed_queries"] += 1
        
        return response
    
    def _convert_to_search_params(self, parsed_request: ParsedUserRequest) -> Dict[str, Any]:
        """Convert parsed request to search parameters for collector agent"""
        params = {
            "days": 7,  # Default
            "top_n": parsed_request.quantity_filter.count,
            "max_results_per_query": parsed_request.quantity_filter.count * 3,  # Buffer for filtering
            "region_code": "US"
        }
        
        # Convert content type to search categories
        content_filter = parsed_request.content_filter
        categories = []
        
        if content_filter.content_type == ContentType.DANCE_CHALLENGE:
            categories = ["dance challenge", "dance", "choreography"]
            if content_filter.genre:
                categories.append(f"{content_filter.genre} dance")
        elif content_filter.content_type == ContentType.FOOD_CHALLENGE:
            categories = ["food challenge", "cooking", "food"]
        elif content_filter.content_type == ContentType.FITNESS_CHALLENGE:
            categories = ["fitness challenge", "workout", "exercise"]
        else:
            categories = ["challenge"]
        
        # Add keywords to categories
        for keyword in content_filter.keywords:
            categories.append(keyword)
        
        params["categories"] = categories
        
        # Convert time filter
        time_filter = parsed_request.time_filter
        if time_filter.time_range == TimeRange.TODAY:
            params["days"] = 1
        elif time_filter.time_range == TimeRange.THIS_WEEK:
            params["days"] = 7
        elif time_filter.time_range == TimeRange.THIS_MONTH:
            params["days"] = 30
        elif time_filter.time_range == TimeRange.RECENT:
            params["days"] = 7
        elif time_filter.time_range == TimeRange.LAST_WEEK:
            params["days"] = 14  # Include last week
        elif time_filter.time_range == TimeRange.LAST_MONTH:
            params["days"] = 60  # Include last month
        elif time_filter.time_range == TimeRange.CUSTOM and time_filter.custom_days:
            params["days"] = time_filter.custom_days
        
        return params
    
    async def _collect_videos(self, search_params: Dict[str, Any]) -> List[YouTubeVideoRaw]:
        """Collect videos using the collector agent"""
        try:
            videos = await self.collector_agent.collect_by_category_keywords(
                categories=search_params["categories"],
                max_results_per_category=search_params["max_results_per_query"],
                days=search_params["days"],
                top_n=search_params["top_n"],
                region_code=search_params["region_code"]
            )
            return videos
            
        except YouTubeAPIError as e:
            logger.error(f"YouTube API error during collection: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during collection: {e}")
            raise
    
    async def _analyze_videos(self, videos: List[YouTubeVideoRaw], parsed_request: ParsedUserRequest) -> List[EnhancedClassifiedVideo]:
        """Analyze videos using the plugin manager"""
        try:
            # Use plugin manager for content analysis
            plugin_result = await self.plugin_manager.analyze_content(videos, parsed_request)
            
            if not plugin_result.success:
                raise ClassificationError(f"Plugin analysis failed: {plugin_result.error_message}")
            
            logger.info(f"Plugin analysis completed with confidence: {plugin_result.confidence_score:.2f}")
            
            # Log any warnings from plugin analysis
            for warning in plugin_result.warnings:
                logger.warning(f"Plugin warning: {warning}")
            
            return plugin_result.analyzed_videos
            
        except ClassificationError as e:
            logger.error(f"Classification error during analysis: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during analysis: {e}")
            raise
    
    def _filter_and_sort_results(self, videos: List[EnhancedClassifiedVideo], parsed_request: ParsedUserRequest) -> List[EnhancedClassifiedVideo]:
        """Filter and sort results based on parsed request criteria"""
        filtered_videos = []
        content_filter = parsed_request.content_filter
        quantity_filter = parsed_request.quantity_filter
        
        for video in videos:
            # Apply content filters
            if not self._passes_content_filter(video, content_filter):
                continue
            
            # Apply quantity filters
            if not self._passes_quantity_filter(video, quantity_filter):
                continue
            
            filtered_videos.append(video)
        
        # Sort results
        sorted_videos = self._sort_results(filtered_videos, quantity_filter.sort_order)
        
        # Limit to requested count
        return sorted_videos[:parsed_request.quantity_filter.count]
    
    def _passes_content_filter(self, video: EnhancedClassifiedVideo, content_filter) -> bool:
        """Check if video passes content filters"""
        # Check video category
        if content_filter.video_category and video.category != content_filter.video_category:
            return False
        
        # Check challenge type if available
        if (content_filter.challenge_type and 
            hasattr(video, 'challenge_type_detailed') and 
            video.challenge_type_detailed != content_filter.challenge_type):
            return False
        
        # Check difficulty if video has analysis
        if (content_filter.difficulty and 
            video.has_video_analysis and 
            video.enhanced_analysis.accessibility_analysis.difficulty_level != content_filter.difficulty):
            return False
        
        # Check participant type
        if content_filter.participants != ParticipantType.ANY:
            if not self._matches_participant_type(video, content_filter.participants):
                return False
        
        # Check must-include keywords
        video_text = f"{video.title} {getattr(video, 'description', '')}".lower()
        for keyword in content_filter.must_include:
            if keyword.lower() not in video_text:
                return False
        
        # Check must-exclude keywords
        for keyword in content_filter.must_exclude:
            if keyword.lower() in video_text:
                return False
        
        return True
    
    def _passes_quantity_filter(self, video: EnhancedClassifiedVideo, quantity_filter) -> bool:
        """Check if video passes quantity filters"""
        # Check minimum views
        if quantity_filter.min_views and video.view_count < quantity_filter.min_views:
            return False
        
        # Check maximum views
        if quantity_filter.max_views and video.view_count > quantity_filter.max_views:
            return False
        
        return True
    
    def _matches_participant_type(self, video: EnhancedClassifiedVideo, participant_type: ParticipantType) -> bool:
        """Check if video matches participant type requirements"""
        if not video.has_video_analysis:
            # Fallback to title/description analysis
            video_text = f"{video.title} {getattr(video, 'description', '')}".lower()
            
            if participant_type == ParticipantType.COUPLE:
                return any(word in video_text for word in ['couple', 'duo', '커플', '둘이서'])
            elif participant_type == ParticipantType.GROUP:
                return any(word in video_text for word in ['group', 'team', '그룹', '단체'])
            elif participant_type == ParticipantType.KIDS:
                return any(word in video_text for word in ['kids', 'children', '아이들', '어린이'])
            elif participant_type == ParticipantType.FAMILY:
                return any(word in video_text for word in ['family', '가족'])
            
        return True  # Default to allowing if unclear
    
    def _sort_results(self, videos: List[EnhancedClassifiedVideo], sort_order: SortOrder) -> List[EnhancedClassifiedVideo]:
        """Sort videos according to requested order"""
        if sort_order == SortOrder.VIEW_COUNT_DESC:
            return sorted(videos, key=lambda v: v.view_count, reverse=True)
        elif sort_order == SortOrder.VIEW_COUNT_ASC:
            return sorted(videos, key=lambda v: v.view_count)
        elif sort_order == SortOrder.LIKE_COUNT_DESC:
            return sorted(videos, key=lambda v: getattr(v, 'like_count', 0), reverse=True)
        elif sort_order == SortOrder.RECENT_FIRST:
            return sorted(videos, key=lambda v: v.published_at, reverse=True)
        elif sort_order == SortOrder.OLDEST_FIRST:
            return sorted(videos, key=lambda v: v.published_at)
        elif sort_order == SortOrder.DIFFICULTY_ASC:
            return sorted(videos, key=lambda v: self._get_difficulty_score(v))
        elif sort_order == SortOrder.DIFFICULTY_DESC:
            return sorted(videos, key=lambda v: self._get_difficulty_score(v), reverse=True)
        else:  # RELEVANCE or default
            return sorted(videos, key=lambda v: v.confidence, reverse=True)
    
    def _get_difficulty_score(self, video: EnhancedClassifiedVideo) -> int:
        """Get numeric difficulty score for sorting"""
        if not video.has_video_analysis:
            return 1  # Default to easy
        
        difficulty = video.enhanced_analysis.accessibility_analysis.difficulty_level
        difficulty_scores = {
            DifficultyLevel.EASY: 1,
            DifficultyLevel.MEDIUM: 2,
            DifficultyLevel.HARD: 3,
            DifficultyLevel.EXPERT: 4
        }
        return difficulty_scores.get(difficulty, 1)
    
    def _generate_summary(self, parsed_request: ParsedUserRequest, results: List[EnhancedClassifiedVideo]) -> str:
        """Generate a concise summary of results"""
        if not results:
            return "검색 조건에 맞는 결과를 찾지 못했습니다."
        
        action_map = {
            ActionType.FIND: "찾았습니다",
            ActionType.RECOMMEND: "추천드립니다",
            ActionType.ANALYZE: "분석했습니다",
            ActionType.COMPARE: "비교했습니다",
            ActionType.EXPLAIN: "설명드립니다"
        }
        
        action_text = action_map.get(parsed_request.action_type, "찾았습니다")
        content_type = parsed_request.content_filter.content_type.value.replace('_', ' ')
        
        total_views = sum(video.view_count for video in results)
        avg_views = total_views // len(results) if results else 0
        
        summary = f"""
{content_type} {len(results)}개를 {action_text}.

📊 **요약 통계:**
- 총 영상 수: {len(results)}개
- 총 조회수: {total_views:,}회
- 평균 조회수: {avg_views:,}회
- 분석 신뢰도: {sum(v.confidence for v in results) / len(results):.2f}

🏆 **TOP 3:**
"""
        
        for i, video in enumerate(results[:3], 1):
            summary += f"\n{i}. {video.title} ({video.view_count:,}회)"
        
        return summary.strip()
    
    def _generate_detailed_report(self, parsed_request: ParsedUserRequest, results: List[EnhancedClassifiedVideo]) -> str:
        """Generate detailed markdown report"""
        if not results:
            return "# 검색 결과 없음\n\n검색 조건에 맞는 결과를 찾지 못했습니다."
        
        content_type = parsed_request.content_filter.content_type.value.replace('_', ' ')
        action_text = parsed_request.action_type.value
        
        report = f"""# {content_type.title()} 분석 결과

## 📊 검색 정보
- **사용자 요청**: "{parsed_request.original_input}"
- **검색 액션**: {action_text}
- **검색된 결과**: {len(results)}개
- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 🏆 결과 목록

"""
        
        for i, video in enumerate(results, 1):
            report += f"""### {i}. {video.title}

- **채널**: {video.channel_title}
- **조회수**: {video.view_count:,}회
- **신뢰도**: {video.confidence:.2f}
- **발행일**: {video.published_at.strftime('%Y-%m-%d')}
- **YouTube 링크**: https://www.youtube.com/watch?v={video.video_id}

"""
            
            # Add enhanced analysis if available
            if video.has_video_analysis:
                analysis = video.enhanced_analysis
                report += f"""#### 📋 상세 분석:
- **난이도**: {analysis.accessibility_analysis.difficulty_level.value}
- **안전도**: {analysis.accessibility_analysis.safety_level.value}
- **음악 장르**: {analysis.music_analysis.genre or 'Unknown'}
- **따라하기 용이성**: {'쉬움' if analysis.accessibility_analysis.easy_to_follow else '어려움'}

"""
            
            report += "---\n\n"
        
        # Add trend analysis
        report += self._generate_trend_section(results)
        
        return report
    
    def _generate_trend_section(self, results: List[EnhancedClassifiedVideo]) -> str:
        """Generate trend analysis section"""
        if not results:
            return ""
        
        # Analyze trends from results
        total_views = sum(video.view_count for video in results)
        avg_views = total_views // len(results)
        
        # Most popular
        most_popular = max(results, key=lambda v: v.view_count)
        
        # Recent vs older content
        recent_count = len([v for v in results if (datetime.now() - v.published_at).days <= 7])
        
        trend_section = f"""## 📈 트렌드 분석

### 🔥 인기도 분석
- **가장 인기있는 영상**: {most_popular.title} ({most_popular.view_count:,}회)
- **평균 조회수**: {avg_views:,}회
- **최근 7일 내 영상**: {recent_count}개 ({recent_count/len(results)*100:.1f}%)

### 💡 인사이트
- 총 {len(results)}개 영상 중 평균 조회수는 {avg_views:,}회입니다.
- 최근 업로드된 콘텐츠가 {recent_count/len(results)*100:.1f}%를 차지합니다.
"""
        
        if len(results) >= 3:
            top_channels = {}
            for video in results:
                top_channels[video.channel_title] = top_channels.get(video.channel_title, 0) + 1
            
            if top_channels:
                most_active_channel = max(top_channels.items(), key=lambda x: x[1])
                trend_section += f"- 가장 활발한 채널: {most_active_channel[0]} ({most_active_channel[1]}개 영상)\n"
        
        return trend_section
    
    def _update_avg_processing_time(self, processing_time: float):
        """Update average processing time statistics"""
        current_avg = self.stats["avg_processing_time"]
        total_successful = self.stats["successful_queries"]
        
        if total_successful == 1:
            self.stats["avg_processing_time"] = processing_time
        else:
            # Calculate rolling average
            self.stats["avg_processing_time"] = (
                (current_avg * (total_successful - 1) + processing_time) / total_successful
            )
    
    def get_service_stats(self) -> Dict[str, Any]:
        """Get service statistics"""
        return self.stats.copy()


# Factory function
def create_natural_query_service() -> NaturalQueryService:
    """Create a new natural query service instance"""
    return NaturalQueryService()
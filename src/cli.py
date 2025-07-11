"""Command-line interface for YouTube Shorts trend analysis"""

import asyncio
import argparse
import json
import sys
import signal
import logging
from datetime import datetime
from typing import Dict
import atexit

from .agents.collector_agent import create_collector_agent
from .agents.analyzer_agent import create_analyzer_agent
from .services.natural_query_service import create_natural_query_service
from .models.video_models import VideoCategory, ChallengeType
from .core.settings import get_settings
from .core.exceptions import (
    YouTubeAPIError, QuotaExceededError, ClassificationError
)
from .core.logging import setup_logging, get_logger
from .core.error_handler import get_error_handler
from .core.health import check_health

# Setup logging system
setup_logging()
logger = get_logger(__name__)


class YouTubeTrendsCLI:
    """Command-line interface for YouTube Shorts trend analysis"""
    
    def __init__(self):
        """Initialize CLI"""
        self.shutdown_requested = False
        self.current_tasks = set()
        
        # Setup graceful shutdown
        self._setup_signal_handlers()
        atexit.register(self._cleanup)
        
        try:
            self.settings = get_settings()
            logger.info(f"CLI initialized - Environment: {self.settings.environment}")
        except Exception as e:
            logger.error(f"Configuration error: {e}")
            print(f"❌ Configuration error: {e}")
            print("💡 Please check your .env file and ensure all required variables are set.")
            sys.exit(1)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            signal_name = signal.Signals(signum).name
            logger.info(f"Received {signal_name}, initiating graceful shutdown...")
            self.shutdown_requested = True
            
            # Cancel current tasks
            for task in self.current_tasks:
                if not task.done():
                    task.cancel()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _cleanup(self):
        """Cleanup resources on exit"""
        logger.info("Performing cleanup...")
        # Any cleanup tasks can be added here
    
    async def _handle_task_with_tracking(self, coro):
        """Execute a coroutine with task tracking for graceful shutdown"""
        task = asyncio.create_task(coro)
        self.current_tasks.add(task)
        
        try:
            result = await task
            return result
        except asyncio.CancelledError:
            logger.info("Task cancelled due to shutdown request")
            raise
        finally:
            self.current_tasks.discard(task)
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser"""
        parser = argparse.ArgumentParser(
            description="YouTube Shorts Trend Analysis MVP",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        subparsers = parser.add_subparsers(dest='command', help='Available commands')
        
        # Collect command
        collect_parser = subparsers.add_parser(
            'collect', 
            help='Collect YouTube Shorts video data'
        )
        collect_parser.add_argument(
            '--categories',
            type=str,
            default="dance,fitness,tutorial",
            help='Comma-separated list of categories to search'
        )
        collect_parser.add_argument(
            '--max-per-category',
            type=int,
            default=50,
            help='Maximum videos to fetch per category for analysis (default: 50)'
        )
        collect_parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of past days to search within (default: 7)'
        )
        collect_parser.add_argument(
            '--top-n',
            type=int,
            default=10,
            help='Number of top videos to select for each metric (default: 10)'
        )
        collect_parser.add_argument(
            '--region',
            type=str,
            default="US",
            help='Region code for search (default: US)'
        )
        collect_parser.add_argument(
            '--output',
            type=str,
            default="collected_videos.json",
            help='Output file for collected data (default: collected_videos.json)'
        )
        
        # Analyze command
        analyze_parser = subparsers.add_parser(
            'analyze',
            help='Analyze collected videos using AI classification'
        )
        analyze_parser.add_argument(
            '--input',
            type=str,
            default="collected_videos.json",
            help='Input file with collected videos (default: collected_videos.json)'
        )
        analyze_parser.add_argument(
            '--output',
            type=str,
            default="classified_videos.json",
            help='Output file for classified videos (default: classified_videos.json)'
        )
        
        # Report command
        report_parser = subparsers.add_parser(
            'report',
            help='Generate trend analysis report'
        )
        report_parser.add_argument(
            '--input',
            type=str,
            default="classified_videos.json",
            help='Input file with classified videos (default: classified_videos.json)'
        )
        report_parser.add_argument(
            '--category',
            type=str,
            choices=['Challenge', 'Info/Advice', 'Trending Sounds/BGM'],
            help='Specific category to analyze (default: all categories)'
        )
        report_parser.add_argument(
            '--output',
            type=str,
            default="trend_report.json",
            help='Output file for trend report (default: trend_report.json)'
        )
        report_parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'text'],
            default='text',
            help='Output format (default: text)'
        )
        
        # Full pipeline command
        pipeline_parser = subparsers.add_parser(
            'pipeline',
            help='Run complete analysis pipeline (collect -> analyze -> report)'
        )
        pipeline_parser.add_argument(
            '--categories',
            type=str,
            default="dance,fitness,tutorial",
            help='Comma-separated list of categories to search'
        )
        pipeline_parser.add_argument(
            '--max-per-category',
            type=int,
            default=50,
            help='Maximum videos to fetch per category for analysis (default: 50)'
        )
        pipeline_parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of past days to search within (default: 7)'
        )
        pipeline_parser.add_argument(
            '--top-n',
            type=int,
            default=10,
            help='Number of top videos to select for each metric (default: 10)'
        )
        pipeline_parser.add_argument(
            '--region',
            type=str,
            default="US",
            help='Region code for search'
        )
        pipeline_parser.add_argument(
            '--include-video-content',
            action='store_true',
            help='Enable video content analysis using Gemini (more detailed but slower)'
        )
        
        # Health check command
        health_parser = subparsers.add_parser(
            'health',
            help='Check system health and status'
        )
        health_parser.add_argument(
            '--format',
            type=str,
            choices=['json', 'text'],
            default='text',
            help='Output format (default: text)'
        )
        health_parser.add_argument(
            '--monitor',
            action='store_true',
            help='Run continuous health monitoring'
        )
        health_parser.add_argument(
            '--interval',
            type=int,
            default=60,
            help='Monitoring interval in seconds (default: 60)'
        )
        
        # Chat command for natural language queries
        chat_parser = subparsers.add_parser(
            'chat',
            help='Process natural language queries for video analysis'
        )
        chat_parser.add_argument(
            'query',
            type=str,
            nargs='?',
            help='Natural language query (e.g., "댄스 챌린지 TOP 10 찾아줘")'
        )
        chat_parser.add_argument(
            '--interactive',
            action='store_true',
            help='Start interactive chat mode'
        )
        chat_parser.add_argument(
            '--output-format',
            type=str,
            choices=['markdown', 'json', 'text'],
            default='markdown',
            help='Output format for results (default: markdown)'
        )
        chat_parser.add_argument(
            '--save-results',
            type=str,
            help='Save results to specified file'
        )
        chat_parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed processing information'
        )
        
        return parser
    
    async def collect_command(self, args) -> None:
        """Execute collect command"""
        print(f"🚀 Starting Top {args.top_n} YouTube Shorts data collection from the last {args.days} days...")
        
        categories = [cat.strip() for cat in args.categories.split(',')]
        print(f"📋 Target categories: {', '.join(categories)}")
        
        try:
            async with create_collector_agent() as collector:
                print(f"📊 Fetching up to {args.max_per_category} videos per category for analysis...")
                
                videos = await collector.collect_by_category_keywords(
                    categories=categories,
                    max_results_per_category=args.max_per_category,
                    days=args.days,
                    top_n=args.top_n,
                    region_code=args.region
                )
                
                stats = collector.get_collection_stats()
                self._save_videos_to_file(videos, args.output)
                
                print("\n✅ Collection complete!")
                print("📈 Statistics:")
                print(f"   • Unique top videos collected: {len(videos)}")
                print(f"   • Quota used: {stats.get('quota_used', 0)}")
                print(f"   • Output saved to: {args.output}")
                
        except QuotaExceededError as e:
            print(f"⚠️  Quota exceeded: {e}")
            print("💡 Try reducing max-results or wait for quota reset.")
        except YouTubeAPIError as e:
            print(f"❌ YouTube API error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logger.exception("Collection command failed")
    
    async def analyze_command(self, args) -> None:
        """Execute analyze command"""
        print("🤖 Starting AI-powered video classification...")
        
        try:
            # Load collected videos
            videos = self._load_videos_from_file(args.input)
            print(f"📂 Loaded {len(videos)} videos from {args.input}")
            
            # Create analyzer agent
            analyzer = create_analyzer_agent()
            
            print("🔍 Classifying videos...")
            self._show_progress("Classification", 0, len(videos))
            
            # Classify videos
            classified_videos = await analyzer.classify_videos_with_enhanced_analysis(
                videos,
                include_video_content=getattr(args, 'include_video_content', False)
            )
            
            # Get analysis statistics
            stats = analyzer.get_analysis_stats()
            
            # Show classification results
            category_counts: Dict[str, int] = {}
            for video in classified_videos:
                category_counts[video.category.value] = category_counts.get(video.category.value, 0) + 1
            
            # Save results
            self._save_classified_videos_to_file(classified_videos, args.output)
            
            print("\n✅ Analysis complete!")
            print("📊 Classification results:")
            for category, count in category_counts.items():
                percentage = (count / len(classified_videos)) * 100
                print(f"   • {category}: {count} videos ({percentage:.1f}%)")
            
            print("📈 Statistics:")
            print(f"   • Videos analyzed: {stats.get('videos_analyzed', 0)}")
            print(f"   • Successful classifications: {stats.get('classifications_successful', 0)}")
            print(f"   • Failed classifications: {stats.get('classifications_failed', 0)}")
            print(f"   • Output saved to: {args.output}")
            
        except FileNotFoundError:
            print(f"❌ Input file not found: {args.input}")
            print("💡 Run 'collect' command first or specify correct input file.")
        except ClassificationError as e:
            print(f"❌ Classification error: {e}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logger.exception("Analysis command failed")
    
    async def report_command(self, args) -> None:
        """Execute report command"""
        print("📈 Generating trend analysis report...")
        
        try:
            # Load classified videos
            classified_videos = self._load_classified_videos_from_file(args.input)
            print(f"📂 Loaded {len(classified_videos)} classified videos from {args.input}")
            
            # Create analyzer agent
            analyzer = create_analyzer_agent()
            
            # Parse category if specified
            target_category = None
            if args.category:
                target_category = VideoCategory(args.category)
                print(f"🎯 Focusing on category: {target_category.value}")
            
            if target_category:
                # Generate category-specific report
                report = analyzer.generate_trend_report(classified_videos, target_category)
                
                if args.format == 'text':
                    self._display_trend_report(report)
                else:
                    self._save_report_to_file(report, args.output)
            else:
                # Generate comprehensive analysis
                comprehensive_analysis = analyzer.generate_comprehensive_analysis(classified_videos)
                
                if args.format == 'text':
                    self._display_comprehensive_analysis(comprehensive_analysis)
                else:
                    self._save_comprehensive_analysis_to_file(comprehensive_analysis, args.output)
            
            print("✅ Report generation complete!")
            if args.format == 'json':
                print(f"📄 Report saved to: {args.output}")
            
        except FileNotFoundError:
            print(f"❌ Input file not found: {args.input}")
            print("💡 Run 'analyze' command first or specify correct input file.")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logger.exception("Report command failed")
    
    async def pipeline_command(self, args) -> None:
        """Execute complete pipeline with iterative collection and analysis"""
        logger.info("🔄 Running iterative YouTube Shorts trend analysis pipeline...")

        MAX_COLLECTION_ATTEMPTS = 5  # 최대 수집 시도 횟수
        VIDEOS_PER_ATTEMPT = 50    # 각 시도마다 수집할 영상 수 (max_per_category)
        
        # "사람들이 쉽게 따라할 수 있는 댄스 챌린지"를 위한 타겟 설정
        target_category = VideoCategory.CHALLENGE
        target_challenge_type = ChallengeType.DANCE
        
        collected_video_ids = set()
        final_classified_videos = []
        
        print("\n" + "="*50)
        print("STEP 1 & 2: ITERATIVE DATA COLLECTION & AI CLASSIFICATION")
        print("="*50)

        async with create_collector_agent() as collector:
            analyzer = create_analyzer_agent() # AnalyzerAgent는 컨텍스트 매니저가 아님

            for attempt in range(MAX_COLLECTION_ATTEMPTS):
                if self.shutdown_requested:
                    logger.info("Shutdown requested, stopping pipeline.")
                    break

                print(f"\n🚀 수집 및 분석 시도 {attempt + 1}/{MAX_COLLECTION_ATTEMPTS} (현재 {len(final_classified_videos)}/{args.top_n}개 확보)")
                
                # 1. 데이터 수집
                print(f"📊 '댄스 챌린지' 관련 최신 영상 {VIDEOS_PER_ATTEMPT}개 수집 중 (지난 {args.days}일)...")
                new_raw_videos = await self._handle_task_with_tracking(
                    collector.collect_by_category_keywords(
                        categories=["dance challenge"], # 고정된 카테고리
                        max_results_per_category=VIDEOS_PER_ATTEMPT,
                        days=args.days,
                        top_n=VIDEOS_PER_ATTEMPT, # 수집 단계에서는 최대한 많이 가져와서 분석 단계에서 필터링
                        region_code=args.region
                    )
                )
                
                # 이미 처리된 영상 제외
                videos_to_analyze = []
                for video in new_raw_videos:
                    if video.video_id not in collected_video_ids:
                        videos_to_analyze.append(video)
                        collected_video_ids.add(video.video_id)
                
                if not videos_to_analyze:
                    print("ℹ️ 새로운 수집 영상이 없습니다. 다음 시도로 넘어갑니다.")
                    continue

                print(f"🔍 새로운 영상 {len(videos_to_analyze)}개 AI 분류 및 비디오 콘텐츠 분석 중...")
                
                # 2. AI 분류 및 비디오 콘텐츠 분석
                classified_batch = await self._handle_task_with_tracking(
                    analyzer.classify_videos_with_enhanced_analysis(
                        videos_to_analyze,
                        include_video_content=args.include_video_content
                    )
                )
                
                # 3. 조건에 맞는 영상 필터링 및 추가
                for video in classified_batch:
                    if len(final_classified_videos) >= args.top_n:
                        break # 목표 개수 달성 시 중단
                    
                    # '댄스 챌린지' 카테고리이면서, 비디오 분석이 수행되었고,
                    # 챌린지 타입이 'DANCE'이며, 'easy_to_follow'가 True인 영상만 선택
                    if (video.category == target_category and
                        video.has_video_analysis and
                        video.challenge_type_detailed == target_challenge_type and
                        video.enhanced_analysis.accessibility_analysis.easy_to_follow):
                        
                        final_classified_videos.append(video)
                        print(f"✅ 조건에 맞는 영상 발견: {video.title} (현재 {len(final_classified_videos)}/{args.top_n}개)")
                
                if len(final_classified_videos) >= args.top_n:
                    print(f"🎉 목표 개수 ({args.top_n}개) 달성! 수집 및 분석을 중단합니다.")
                    break
                else:
                    print(f"➡️ 목표 개수 ({args.top_n}개) 미달. 다음 수집 시도를 진행합니다.")
            
            if not final_classified_videos:
                print("❌ 조건에 맞는 영상을 찾지 못했습니다. 파이프라인을 종료합니다.")
                return

            # 최종 분류된 영상 저장
            classified_output_file = "classified_videos.json"
            self._save_classified_videos_to_file(final_classified_videos, classified_output_file)
            print(f"✅ 최종 분류된 영상 {len(final_classified_videos)}개 저장 완료: {classified_output_file}")

        # Step 3: Report
        print("\n" + "="*50)
        print("STEP 3: TREND REPORTING")
        print("="*50)
        # Create args object for report command
        report_args = argparse.Namespace(
            input="classified_videos.json",
            category=target_category.value, # 댄스 챌린지 카테고리로 리포트 생성
            output="trend_report.json",
            format="text"
        )
        await self.report_command(report_args)
        
        print("\n🎉 파이프라인 완료! 모든 분석 단계가 성공적으로 완료되었습니다.")
    
    async def health_command(self, args) -> None:
        """Execute health check command"""
        from .core.health import monitor_health
        
        if args.monitor:
            print(f"🔍 Starting health monitoring (checking every {args.interval}s)")
            print("Press Ctrl+C to stop monitoring")
            try:
                await monitor_health(args.interval)
            except KeyboardInterrupt:
                print("\n⏹️ Health monitoring stopped")
        else:
            print("🔍 Running system health check...")
            health_status = await check_health()
            
            if args.format == 'json':
                print(json.dumps(health_status, indent=2))
            else:
                self._display_health_status(health_status)
            
            # Exit with error code if unhealthy
            if health_status['status'] == 'unhealthy':
                sys.exit(1)
    
    async def chat_command(self, args) -> None:
        """Execute natural language chat command"""
        if args.interactive:
            await self._interactive_chat_mode(args)
        elif args.query:
            await self._process_single_query(args.query, args)
        else:
            print("❌ 자연어 쿼리를 입력하거나 --interactive 모드를 사용하세요.")
            print("💡 예시: python cli.py chat \"댄스 챌린지 TOP 10 찾아줘\"")
            sys.exit(1)
    
    async def _interactive_chat_mode(self, args) -> None:
        """Run interactive chat mode"""
        print("🤖 자연어 비디오 분석 채팅 모드")
        print("=" * 50)
        print("💬 자연어로 원하는 분석을 요청해보세요!")
        print("📝 예시:")
        print("   - '댄스 챌린지 TOP 10 찾아줘'")
        print("   - '초보자용 쉬운 K-pop 댄스 추천해줘'")
        print("   - '커플이 할 수 있는 로맨틱한 댄스 보여줘'")
        print("\n🔚 종료하려면 'quit', 'exit', '종료' 입력")
        print("-" * 50)
        
        query_service = create_natural_query_service()
        
        while True:
            try:
                # Get user input
                user_input = input("\n💭 질문: ").strip()
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                    print("👋 채팅을 종료합니다.")
                    break
                
                if not user_input:
                    print("❓ 질문을 입력해주세요.")
                    continue
                
                # Process query
                await self._process_single_query(user_input, args, query_service)
                
            except KeyboardInterrupt:
                print("\n\n👋 채팅을 종료합니다.")
                break
            except Exception as e:
                print(f"❌ 오류가 발생했습니다: {e}")
                logger.exception("Interactive chat error")
    
    async def _process_single_query(self, query: str, args, query_service=None) -> None:
        """Process a single natural language query"""
        if query_service is None:
            query_service = create_natural_query_service()
        
        try:
            if args.verbose:
                print(f"🔍 쿼리 처리 중: '{query}'")
            
            # Show progress indicator
            print("⏳ 자연어 분석 및 비디오 검색 중...")
            
            # Process the query
            response = await query_service.process_query(query)
            
            if not response.success:
                print(f"❌ 쿼리 처리 실패: {response.error_message}")
                return
            
            # Display results based on format
            if args.output_format == 'json':
                await self._display_json_results(response, args)
            elif args.output_format == 'text':
                await self._display_text_results(response, args)
            else:  # markdown (default)
                await self._display_markdown_results(response, args)
            
            # Save results if requested
            if args.save_results:
                await self._save_query_results(response, args.save_results, args.output_format)
                print(f"💾 결과가 저장되었습니다: {args.save_results}")
            
        except Exception as e:
            print(f"❌ 쿼리 처리 중 오류 발생: {e}")
            logger.exception("Query processing error")
    
    async def _display_json_results(self, response, args) -> None:
        """Display results in JSON format"""
        result_data = {
            "query": response.parsed_request.original_input if response.parsed_request else "",
            "success": response.success,
            "total_found": response.total_found,
            "processing_time": response.processing_time,
            "results": []
        }
        
        for video in response.results:
            video_data = {
                "rank": len(result_data["results"]) + 1,
                "video_id": video.video_id,
                "title": video.title,
                "channel": video.channel_title,
                "view_count": video.view_count,
                "confidence": video.confidence,
                "youtube_url": f"https://www.youtube.com/watch?v={video.video_id}",
                "published_at": video.published_at.isoformat()
            }
            
            if video.has_video_analysis:
                video_data["analysis"] = {
                    "difficulty": video.enhanced_analysis.accessibility_analysis.difficulty_level.value,
                    "safety": video.enhanced_analysis.accessibility_analysis.safety_level.value,
                    "music_genre": video.enhanced_analysis.music_analysis.genre,
                    "easy_to_follow": video.enhanced_analysis.accessibility_analysis.easy_to_follow
                }
            
            result_data["results"].append(video_data)
        
        print(json.dumps(result_data, ensure_ascii=False, indent=2))
    
    async def _display_text_results(self, response, args) -> None:
        """Display results in simple text format"""
        print("\n" + "="*60)
        print("🎯 자연어 쿼리 결과")
        print("="*60)
        
        if response.parsed_request:
            print(f"📝 원본 질문: {response.parsed_request.original_input}")
            print(f"🔍 분석된 액션: {response.parsed_request.action_type.value}")
            print(f"📊 요청 개수: {response.parsed_request.quantity_filter.count}개")
        
        print(f"✅ 찾은 결과: {response.total_found}개")
        print(f"⏱️ 처리 시간: {response.processing_time:.2f}초")
        
        if response.summary:
            print(f"\n📋 요약:")
            print(response.summary)
        
        print(f"\n🏆 상위 결과:")
        print("-" * 60)
        
        for i, video in enumerate(response.results[:5], 1):  # Show top 5 in text mode
            print(f"{i}. {video.title}")
            print(f"   📺 채널: {video.channel_title}")
            print(f"   👀 조회수: {video.view_count:,}회")
            print(f"   🎯 신뢰도: {video.confidence:.2f}")
            print(f"   🔗 https://www.youtube.com/watch?v={video.video_id}")
            
            if video.has_video_analysis:
                analysis = video.enhanced_analysis
                print(f"   ⭐ 난이도: {analysis.accessibility_analysis.difficulty_level.value}")
                print(f"   🎵 음악: {analysis.music_analysis.genre or 'Unknown'}")
            
            print()
    
    async def _display_markdown_results(self, response, args) -> None:
        """Display results in markdown format"""
        print("\n" + response.detailed_report)
        
        if args.verbose:
            print("\n" + "="*50)
            print("🔍 상세 처리 정보")
            print("="*50)
            
            if response.parsed_request:
                print(f"📊 파싱 신뢰도: {response.parsed_request.confidence:.2f}")
                print(f"🏷️ 추출된 키워드: {', '.join(response.parsed_request.content_filter.keywords)}")
                if response.parsed_request.content_filter.difficulty:
                    print(f"⭐ 요청 난이도: {response.parsed_request.content_filter.difficulty.value}")
            
            print(f"⏱️ 총 처리 시간: {response.processing_time:.2f}초")
            
            if response.warnings:
                print(f"⚠️ 경고사항:")
                for warning in response.warnings:
                    print(f"   - {warning}")
    
    async def _save_query_results(self, response, filename: str, format_type: str) -> None:
        """Save query results to file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                if format_type == 'json':
                    result_data = {
                        "query": response.parsed_request.original_input if response.parsed_request else "",
                        "success": response.success,
                        "total_found": response.total_found,
                        "processing_time": response.processing_time,
                        "timestamp": datetime.now().isoformat(),
                        "results": [
                            {
                                "rank": i + 1,
                                "video_id": video.video_id,
                                "title": video.title,
                                "channel": video.channel_title,
                                "view_count": video.view_count,
                                "confidence": video.confidence,
                                "youtube_url": f"https://www.youtube.com/watch?v={video.video_id}",
                                "published_at": video.published_at.isoformat()
                            }
                            for i, video in enumerate(response.results)
                        ]
                    }
                    json.dump(result_data, f, ensure_ascii=False, indent=2)
                else:  # markdown or text
                    f.write(response.detailed_report)
                    
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            raise
    
    def _display_health_status(self, health_status: Dict) -> None:
        """Display health status in human-readable format"""
        status = health_status['status']
        
        # Status indicator
        if status == 'healthy':
            print("✅ System Status: HEALTHY")
        elif status == 'degraded':
            print("⚠️  System Status: DEGRADED")
        else:
            print("❌ System Status: UNHEALTHY")
        
        print(f"📅 Check Time: {health_status['timestamp']}")
        
        # Summary
        summary = health_status['summary']
        print(f"\n📊 Check Summary:")
        print(f"   • Total checks: {summary['total_checks']}")
        print(f"   • Healthy: {summary['healthy']}")
        print(f"   • Degraded: {summary['degraded']}")
        print(f"   • Unhealthy: {summary['unhealthy']}")
        
        # Individual checks
        print(f"\n🔍 Individual Checks:")
        for check in health_status['checks']:
            status_icon = {
                'healthy': '✅',
                'degraded': '⚠️ ',
                'unhealthy': '❌'
            }.get(check['status'], '❓')
            
            print(f"   {status_icon} {check['name']}: {check['message']}")
            if check.get('response_time'):
                print(f"      Response time: {check['response_time']:.2f}s")
    
    def _save_videos_to_file(self, videos, filename: str) -> None:
        """Save videos to JSON file"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_videos": len(videos),
            "videos": [video.model_dump() for video in videos]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def _load_videos_from_file(self, filename: str):
        """Load videos from JSON file"""
        from .models.video_models import YouTubeVideoRaw
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        videos = []
        for video_data in data.get('videos', []):
            try:
                video = YouTubeVideoRaw(**video_data)
                videos.append(video)
            except Exception as e:
                logger.warning(f"Failed to parse video data: {e}")
                continue
        
        return videos
    
    def _save_classified_videos_to_file(self, videos, filename: str) -> None:
        """Save classified videos to JSON file"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "total_videos": len(videos),
            "classified_videos": [video.model_dump() for video in videos]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    
    def _load_classified_videos_from_file(self, filename: str):
        """Load classified videos from JSON file"""
        from .models.video_models import ClassifiedVideo
        
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        videos = []
        for video_data in data.get('classified_videos', []):
            try:
                video = ClassifiedVideo(**video_data)
                videos.append(video)
            except Exception as e:
                logger.warning(f"Failed to parse classified video data: {e}")
                continue
        
        return videos
    
    def _save_report_to_file(self, report, filename: str) -> None:
        """Save trend report to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report.model_dump(), f, indent=2, ensure_ascii=False, default=str)
    
    def _save_comprehensive_analysis_to_file(self, analysis, filename: str) -> None:
        """Save comprehensive analysis to JSON file"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(analysis.model_dump(), f, indent=2, ensure_ascii=False, default=str)
    
    def _display_trend_report(self, report) -> None:
        """Display trend report in readable format"""
        print(f"\n📈 TREND REPORT: {report.category.value.upper()}")
        print("="*60)
        
        print("\n📋 Summary:")
        print(f"   {report.trend_summary}")
        
        print("\n🔥 Key Insights:")
        for insight in report.key_insights:
            print(f"   • {insight}")
        
        print("\n💡 Recommended Actions:")
        for action in report.recommended_actions:
            print(f"   • {action}")
        
        if report.top_videos:
            print("\n🏆 Top Performing Videos:")
            for i, video in enumerate(report.top_videos[:3], 1):
                views_text = f" ({video.view_count:,} views)" if video.view_count else ""
                print(f"   {i}. {video.title}{views_text}")
                print(f"      Confidence: {video.confidence:.1%}")
        
        print("\n📊 Analysis Details:")
        print(f"   • Videos analyzed: {report.total_videos_analyzed}")
        print(f"   • Analysis period: {report.analysis_period}")
        print(f"   • Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _display_comprehensive_analysis(self, analysis) -> None:
        """Display comprehensive analysis in readable format"""
        print("\n📊 COMPREHENSIVE TREND ANALYSIS")
        print("="*60)
        
        print("\n🎯 Overview:")
        print(f"   • Total videos analyzed: {analysis.total_videos_analyzed}")
        print(f"   • Analysis period: {analysis.analysis_period}")
        print(f"   • Dominant category: {analysis.dominant_category.value}")
        
        print("\n📈 Category Breakdown:")
        for insights in analysis.category_insights:
            percentage = (insights.video_count / analysis.total_videos_analyzed) * 100
            print(f"   • {insights.category.value}: {insights.video_count} videos ({percentage:.1f}%)")
            print(f"     Average confidence: {insights.average_confidence:.1%}")
            if insights.common_keywords:
                print(f"     Keywords: {', '.join(insights.common_keywords[:3])}")
        
        print("\n🚀 Emerging Trends:")
        for trend in analysis.emerging_trends:
            print(f"   • {trend}")
        
        print("\n💡 Content Strategy Recommendations:")
        for strategy in analysis.recommended_content_strategy:
            print(f"   • {strategy}")
        
        print("\n🔧 Analysis Info:")
        print(f"   • Model version: {analysis.model_version}")
        print(f"   • Generated: {analysis.analyzed_at.strftime('%Y-%m-%d %H:%M:%S')}")
    
    def _show_progress(self, task: str, current: int, total: int) -> None:
        """Show progress indicator"""
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 30
        filled_length = int(bar_length * current // total) if total > 0 else 0
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        print(f'\r{task}: |{bar}| {percentage:.1f}% ({current}/{total})', end='', flush=True)


async def main():
    """Main CLI entry point"""
    cli = YouTubeTrendsCLI()
    parser = cli.create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == 'collect':
            await cli.collect_command(args)
        elif args.command == 'analyze':
            await cli.analyze_command(args)
        elif args.command == 'report':
            await cli.report_command(args)
        elif args.command == 'pipeline':
            await cli.pipeline_command(args)
        elif args.command == 'health':
            await cli.health_command(args)
        elif args.command == 'chat':
            await cli.chat_command(args)
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("CLI command failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
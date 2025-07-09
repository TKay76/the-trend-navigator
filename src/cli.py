"""Command-line interface for YouTube Shorts trend analysis"""

import asyncio
import argparse
import json
import sys
import logging
from datetime import datetime
from typing import Dict

from .agents.collector_agent import create_collector_agent
from .agents.analyzer_agent import create_analyzer_agent
from .models.video_models import VideoCategory
from .core.settings import get_settings
from .core.exceptions import (
    YouTubeAPIError, QuotaExceededError, ClassificationError
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeTrendsCLI:
    """Command-line interface for YouTube Shorts trend analysis"""
    
    def __init__(self):
        """Initialize CLI"""
        try:
            self.settings = get_settings()
        except Exception as e:
            print(f"❌ Configuration error: {e}")
            print("💡 Please check your .env file and ensure all required variables are set.")
            sys.exit(1)
    
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
            help='Comma-separated list of categories to search (default: dance,fitness,tutorial)'
        )
        collect_parser.add_argument(
            '--max-results',
            type=int,
            default=20,
            help='Maximum results per category (default: 20)'
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
            '--max-results',
            type=int,
            default=20,
            help='Maximum results per category'
        )
        pipeline_parser.add_argument(
            '--region',
            type=str,
            default="US",
            help='Region code for search'
        )
        
        return parser
    
    async def collect_command(self, args) -> None:
        """Execute collect command"""
        print("🚀 Starting YouTube Shorts data collection...")
        
        # Parse categories
        categories = [cat.strip() for cat in args.categories.split(',')]
        print(f"📋 Target categories: {', '.join(categories)}")
        
        try:
            # Create collector agent
            async with create_collector_agent() as collector:
                print(f"📊 Collecting up to {args.max_results} videos per category...")
                
                # Collect videos
                videos = await collector.collect_by_category_keywords(
                    categories=categories,
                    max_results_per_category=args.max_results,
                    region_code=args.region
                )
                
                # Get collection statistics
                stats = collector.get_collection_stats()
                
                # Save results
                self._save_videos_to_file(videos, args.output)
                
                print("✅ Collection complete!")
                print("📈 Statistics:")
                print(f"   • Videos collected: {len(videos)}")
                print(f"   • API calls made: {stats.get('api_calls_made', 0)}")
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
            classified_videos = await analyzer.classify_videos(videos)
            
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
        """Execute complete pipeline"""
        print("🔄 Running complete YouTube Shorts trend analysis pipeline...")
        
        # Step 1: Collect
        print("\n" + "="*50)
        print("STEP 1: DATA COLLECTION")
        print("="*50)
        # Create args object for collect command
        collect_args = argparse.Namespace(
            categories=args.categories,
            max_results=args.max_results,
            region=args.region,
            output="collected_videos.json"
        )
        await self.collect_command(collect_args)
        
        # Step 2: Analyze
        print("\n" + "="*50)
        print("STEP 2: AI CLASSIFICATION")
        print("="*50)
        # Create args object for analyze command
        analyze_args = argparse.Namespace(
            input="collected_videos.json",
            output="classified_videos.json"
        )
        await self.analyze_command(analyze_args)
        
        # Step 3: Report
        print("\n" + "="*50)
        print("STEP 3: TREND REPORTING")
        print("="*50)
        # Create args object for report command
        report_args = argparse.Namespace(
            input="classified_videos.json",
            category=None,
            output="trend_report.json",
            format="text"
        )
        await self.report_command(report_args)
        
        print("\n🎉 Pipeline complete! All analysis steps finished successfully.")
    
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
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("CLI command failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
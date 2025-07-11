"""
YouTube Charts Data Collection Example
=====================================

This example demonstrates how to collect music chart data from YouTube Charts
using the implemented YouTube Charts client and collector agent.
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, List

from src.clients.youtube_charts_client import YouTubeChartsClient
from src.agents.collector_agent import CollectorAgent
from src.models.video_models import ChartHistoryRequest, ChartData, ChartSong
from src.core.logging import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def example_basic_chart_collection():
    """
    Basic example: Collect current Korean daily charts
    """
    print("=== Basic Chart Collection Example ===")
    
    async with YouTubeChartsClient(headless=True) as client:
        try:
            # Get current Korean daily charts
            songs = await client.get_top_shorts_songs_kr("daily")
            
            print(f"Found {len(songs)} songs in Korean daily charts:")
            for i, song in enumerate(songs[:10], 1):  # Show top 10
                print(f"{i:2d}. {song.title} - {song.artist} (Rank: {song.rank})")
                if song.video_id:
                    print(f"     Video ID: {song.video_id}")
            
            return songs
            
        except Exception as e:
            logger.error(f"Chart collection failed: {e}")
            return []


async def example_collector_agent_usage():
    """
    Example using the CollectorAgent for chart data collection
    """
    print("\n=== CollectorAgent Chart Collection Example ===")
    
    collector = CollectorAgent()
    
    try:
        # Collect chart data using the agent
        chart_data = await collector.collect_chart_data(
            region="kr",
            chart_type="daily",
            days=1
        )
        
        print(f"Chart Data Summary:")
        print(f"  Region: {chart_data.region}")
        print(f"  Chart Type: {chart_data.chart_type}")
        print(f"  Date: {chart_data.date.strftime('%Y-%m-%d')}")
        print(f"  Total Songs: {chart_data.total_songs}")
        
        # Show top 5 songs
        print(f"\nTop 5 Songs:")
        for song in chart_data.songs[:5]:
            print(f"  #{song.rank}: {song.title} - {song.artist}")
            if song.video_id:
                print(f"           Video: https://youtube.com/watch?v={song.video_id}")
        
        return chart_data
        
    except Exception as e:
        logger.error(f"Agent chart collection failed: {e}")
        return None


async def example_chart_history_collection():
    """
    Example: Collect chart history for multiple days
    """
    print("\n=== Chart History Collection Example ===")
    
    collector = CollectorAgent()
    
    try:
        # Create chart history request
        request = ChartHistoryRequest(
            region="kr",
            chart_type="daily",
            days=3  # Collect 3 days of history
        )
        
        # Collect chart history
        chart_history = await collector.collect_chart_history(request)
        
        print(f"Chart History Summary:")
        print(f"  Collected {len(chart_history)} days of chart data")
        
        for date_str, chart_data in chart_history.items():
            print(f"\n  {date_str}:")
            print(f"    Total Songs: {chart_data.total_songs}")
            if chart_data.songs:
                top_song = chart_data.songs[0]
                print(f"    #1 Song: {top_song.title} - {top_song.artist}")
        
        return chart_history
        
    except Exception as e:
        logger.error(f"Chart history collection failed: {e}")
        return {}


async def example_api_usage():
    """
    Example: How to use the chart data in your application
    """
    print("\n=== API Usage Example ===")
    
    # This demonstrates how you might use the chart data in your application
    collector = CollectorAgent()
    
    try:
        # Get current chart data
        chart_data = await collector.collect_chart_data("kr", "daily")
        
        # Process the data for your application
        processed_data = {
            "chart_info": {
                "region": chart_data.region,
                "type": chart_data.chart_type,
                "date": chart_data.date.isoformat(),
                "total_songs": chart_data.total_songs
            },
            "top_10": []
        }
        
        # Extract top 10 songs with relevant metadata
        for song in chart_data.songs[:10]:
            song_data = {
                "rank": song.rank,
                "title": song.title,
                "artist": song.artist,
                "video_id": song.video_id,
                "youtube_url": f"https://youtube.com/watch?v={song.video_id}" if song.video_id else None,
                "trend_direction": song.trend_direction.value if song.trend_direction else None
            }
            processed_data["top_10"].append(song_data)
        
        # Display as JSON
        print("Processed Chart Data (JSON):")
        print(json.dumps(processed_data, indent=2, ensure_ascii=False))
        
        return processed_data
        
    except Exception as e:
        logger.error(f"API usage example failed: {e}")
        return None


async def example_trend_analysis():
    """
    Example: Basic trend analysis using chart data
    """
    print("\n=== Trend Analysis Example ===")
    
    collector = CollectorAgent()
    
    try:
        # Collect multiple days for trend analysis
        request = ChartHistoryRequest(region="kr", chart_type="daily", days=3)
        chart_history = await collector.collect_chart_history(request)
        
        if len(chart_history) < 2:
            print("Need at least 2 days of data for trend analysis")
            return
        
        # Simple trend analysis
        dates = sorted(chart_history.keys())
        latest_date = dates[-1]
        previous_date = dates[-2]
        
        latest_chart = chart_history[latest_date]
        previous_chart = chart_history[previous_date]
        
        print(f"Trend Analysis ({previous_date} → {latest_date}):")
        
        # Create ranking maps
        latest_rankings = {song.title: song.rank for song in latest_chart.songs}
        previous_rankings = {song.title: song.rank for song in previous_chart.songs}
        
        # Find trends
        rising_songs = []
        falling_songs = []
        new_entries = []
        
        for song in latest_chart.songs[:10]:  # Analyze top 10
            title = song.title
            current_rank = song.rank
            
            if title in previous_rankings:
                previous_rank = previous_rankings[title]
                if current_rank < previous_rank:
                    rising_songs.append((title, previous_rank, current_rank))
                elif current_rank > previous_rank:
                    falling_songs.append((title, previous_rank, current_rank))
            else:
                new_entries.append((title, current_rank))
        
        # Display trends
        if rising_songs:
            print("\n  📈 Rising Songs:")
            for title, prev_rank, curr_rank in rising_songs:
                print(f"    {title}: #{prev_rank} → #{curr_rank} (↑{prev_rank - curr_rank})")
        
        if falling_songs:
            print("\n  📉 Falling Songs:")
            for title, prev_rank, curr_rank in falling_songs:
                print(f"    {title}: #{prev_rank} → #{curr_rank} (↓{curr_rank - prev_rank})")
        
        if new_entries:
            print("\n  ⭐ New Entries:")
            for title, rank in new_entries:
                print(f"    {title}: New at #{rank}")
        
    except Exception as e:
        logger.error(f"Trend analysis failed: {e}")


async def main():
    """
    Main function demonstrating all examples
    """
    print("YouTube Charts Data Collection Examples")
    print("=" * 50)
    
    # Run all examples
    await example_basic_chart_collection()
    await example_collector_agent_usage()
    await example_chart_history_collection()
    await example_api_usage()
    await example_trend_analysis()
    
    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
"""YouTube Charts API endpoints"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Dict, Optional
from datetime import datetime

from ..agents.collector_agent import CollectorAgent
from ..models.video_models import ChartData, ChartHistoryRequest, ChartSong
from ..core.logging import get_logger
from ..core.exceptions import YouTubeAPIError

logger = get_logger(__name__)

router = APIRouter(prefix="/charts", tags=["charts"])


async def get_collector_agent() -> CollectorAgent:
    """Dependency to get collector agent instance"""
    return CollectorAgent()


@router.get("/current/{region}", response_model=ChartData)
async def get_current_chart(
    region: str = "kr",
    chart_type: str = Query("daily", description="Chart type (daily, weekly)"),
    collector: CollectorAgent = Depends(get_collector_agent)
):
    """
    Get current chart data for a specific region.
    
    Args:
        region: Region code (kr, us, jp, etc.)
        chart_type: Type of chart (daily, weekly)
        collector: Collector agent dependency
        
    Returns:
        Current chart data with song rankings
    """
    try:
        logger.info(f"Getting current {chart_type} chart for region: {region}")
        
        chart_data = await collector.collect_chart_data(
            region=region,
            chart_type=chart_type,
            days=1
        )
        
        return chart_data
        
    except YouTubeAPIError as e:
        logger.error(f"YouTube API error: {e}")
        raise HTTPException(status_code=503, detail=f"Chart data unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history/{region}", response_model=Dict[str, ChartData])
async def get_chart_history(
    region: str = "kr",
    chart_type: str = Query("daily", description="Chart type (daily, weekly)"),
    days: int = Query(7, ge=1, le=30, description="Number of days to fetch"),
    collector: CollectorAgent = Depends(get_collector_agent)
):
    """
    Get chart history for a specific region.
    
    Args:
        region: Region code (kr, us, jp, etc.)
        chart_type: Type of chart (daily, weekly)
        days: Number of days to fetch (1-30)
        collector: Collector agent dependency
        
    Returns:
        Dictionary mapping dates to chart data
    """
    try:
        logger.info(f"Getting chart history for region: {region}, days: {days}")
        
        request = ChartHistoryRequest(
            region=region,
            chart_type=chart_type,
            days=days
        )
        
        chart_history = await collector.collect_chart_history(request)
        
        return chart_history
        
    except YouTubeAPIError as e:
        logger.error(f"YouTube API error: {e}")
        raise HTTPException(status_code=503, detail=f"Chart history unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/top-songs/{region}", response_model=List[ChartSong])
async def get_top_songs(
    region: str = "kr",
    chart_type: str = Query("daily", description="Chart type (daily, weekly)"),
    limit: int = Query(10, ge=1, le=100, description="Number of top songs to return"),
    collector: CollectorAgent = Depends(get_collector_agent)
):
    """
    Get top songs from current chart.
    
    Args:
        region: Region code (kr, us, jp, etc.)
        chart_type: Type of chart (daily, weekly)
        limit: Number of top songs to return (1-100)
        collector: Collector agent dependency
        
    Returns:
        List of top songs with metadata
    """
    try:
        logger.info(f"Getting top {limit} songs for region: {region}")
        
        chart_data = await collector.collect_chart_data(
            region=region,
            chart_type=chart_type,
            days=1
        )
        
        # Return top N songs
        top_songs = chart_data.songs[:limit]
        
        return top_songs
        
    except YouTubeAPIError as e:
        logger.error(f"YouTube API error: {e}")
        raise HTTPException(status_code=503, detail=f"Top songs unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/song/{region}/{rank}", response_model=ChartSong)
async def get_song_by_rank(
    region: str = "kr",
    rank: int = 1,
    chart_type: str = Query("daily", description="Chart type (daily, weekly)"),
    collector: CollectorAgent = Depends(get_collector_agent)
):
    """
    Get specific song by chart rank.
    
    Args:
        region: Region code (kr, us, jp, etc.)
        rank: Chart rank (1-based)
        chart_type: Type of chart (daily, weekly)
        collector: Collector agent dependency
        
    Returns:
        Song at specified rank
    """
    try:
        logger.info(f"Getting song at rank {rank} for region: {region}")
        
        chart_data = await collector.collect_chart_data(
            region=region,
            chart_type=chart_type,
            days=1
        )
        
        # Find song at specified rank
        for song in chart_data.songs:
            if song.rank == rank:
                return song
        
        raise HTTPException(status_code=404, detail=f"Song at rank {rank} not found")
        
    except YouTubeAPIError as e:
        logger.error(f"YouTube API error: {e}")
        raise HTTPException(status_code=503, detail=f"Song data unavailable: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/supported-regions", response_model=List[str])
async def get_supported_regions():
    """
    Get list of supported region codes.
    
    Returns:
        List of supported region codes
    """
    # This would be populated based on actual chart availability
    supported_regions = ["kr", "us", "jp", "gb", "de", "fr", "br", "in"]
    return supported_regions


@router.get("/supported-chart-types", response_model=List[str])
async def get_supported_chart_types():
    """
    Get list of supported chart types.
    
    Returns:
        List of supported chart types
    """
    supported_types = ["daily", "weekly"]
    return supported_types


@router.get("/stats", response_model=Dict[str, int])
async def get_chart_stats(
    collector: CollectorAgent = Depends(get_collector_agent)
):
    """
    Get chart collection statistics.
    
    Returns:
        Chart collection statistics
    """
    try:
        stats = collector.get_collection_stats()
        
        # Filter to chart-related stats
        chart_stats = {
            "chart_collections": stats.get("chart_collections", 0),
            "last_chart_collection": stats.get("last_chart_collection"),
            "total_collections": stats.get("videos_collected", 0)
        }
        
        return chart_stats
        
    except Exception as e:
        logger.error(f"Error getting chart stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
"""FastAPI web server for YouTube Trends Analysis service"""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from .middleware import RequestLoggingMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from .cache import get_cache_manager, cache_result

from ..services.natural_query_service import create_natural_query_service, QueryResponse
from ..plugins.plugin_manager import create_plugin_manager
from ..core.settings import get_settings
from ..core.logging import setup_logging, get_logger
from ..core.health import check_health

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Global service instances
natural_query_service = None
plugin_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global natural_query_service, plugin_manager
    
    logger.info("Starting YouTube Trends Analysis Web Service...")
    
    try:
        # Initialize services
        natural_query_service = create_natural_query_service()
        plugin_manager = create_plugin_manager()
        
        # Initialize plugins
        plugin_results = await plugin_manager.discover_and_load_plugins()
        logger.info(f"Plugin initialization completed: {plugin_results['summary']}")
        
        logger.info("Web service startup completed successfully")
        yield
        
    except Exception as e:
        logger.error(f"Failed to start web service: {e}")
        raise
    finally:
        logger.info("Shutting down YouTube Trends Analysis Web Service...")


# FastAPI app instance
app = FastAPI(
    title="YouTube Trends Analysis API",
    description="Universal content analysis system with natural language processing",
    version="1.0.0",
    lifespan=lifespan
)

# Add custom middleware (order matters!)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, calls_per_minute=100)  # Allow 100 requests per minute

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
class AnalyzeRequest(BaseModel):
    """Request model for content analysis"""
    query: str = Field(..., description="Natural language query", min_length=1, max_length=500)
    output_format: str = Field("json", description="Output format: json, markdown, or summary")
    include_recommendations: bool = Field(True, description="Include content recommendations")


class AnalyzeResponse(BaseModel):
    """Response model for content analysis"""
    success: bool
    query: str
    processing_time: float
    results_count: int
    results: List[Dict[str, Any]]
    summary: str
    detailed_report: Optional[str] = None
    recommendations: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any]
    error_message: Optional[str] = None
    warnings: List[str] = []


class PluginInfo(BaseModel):
    """Plugin information model"""
    name: str
    version: str
    description: str
    content_types: List[str]
    capabilities: List[str]
    initialized: bool


class HealthResponse(BaseModel):
    """Health check response model"""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    plugins_status: Dict[str, Any]
    system_info: Dict[str, Any]


class StatsResponse(BaseModel):
    """Service statistics response model"""
    total_queries: int
    successful_queries: int
    failed_queries: int
    avg_processing_time: float
    last_query_time: Optional[str]
    plugin_stats: Dict[str, Any]


# Global variables for tracking
startup_time = datetime.now()
request_count = 0


# Middleware to track requests
@app.middleware("http")
async def track_requests(request: Request, call_next):
    global request_count
    request_count += 1
    
    start_time = datetime.now()
    response = await call_next(request)
    processing_time = (datetime.now() - start_time).total_seconds()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {processing_time:.3f}s"
    )
    
    return response


# API Routes

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main web interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube Trends Analyzer</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 30px; }
            .header h1 { color: #333; margin-bottom: 10px; }
            .header p { color: #666; font-size: 18px; }
            .query-form { margin-bottom: 30px; }
            .query-input { width: 100%; padding: 15px; font-size: 16px; border: 2px solid #ddd; border-radius: 5px; margin-bottom: 15px; }
            .query-button { background: #007bff; color: white; padding: 15px 30px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; }
            .query-button:hover { background: #0056b3; }
            .examples { margin-bottom: 30px; }
            .examples h3 { color: #333; margin-bottom: 15px; }
            .example-tag { display: inline-block; background: #e9ecef; padding: 8px 12px; margin: 5px; border-radius: 20px; cursor: pointer; font-size: 14px; }
            .example-tag:hover { background: #007bff; color: white; }
            .results { margin-top: 30px; }
            .loading { text-align: center; padding: 20px; display: none; }
            .error { background: #f8d7da; color: #721c24; padding: 15px; border-radius: 5px; margin: 10px 0; }
            .success { background: #d4edda; color: #155724; padding: 15px; border-radius: 5px; margin: 10px 0; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎯 YouTube Trends Analyzer</h1>
                <p>자연어로 YouTube 콘텐츠를 분석하고 트렌드를 발견하세요</p>
            </div>
            
            <div class="query-form">
                <input type="text" id="queryInput" class="query-input" placeholder="예: 댄스 챌린지 TOP 10 찾아줘">
                <button onclick="analyzeQuery()" class="query-button">분석하기</button>
            </div>
            
            <div class="examples">
                <h3>💡 예시 쿼리:</h3>
                <span class="example-tag" onclick="setQuery('댄스 챌린지 TOP 10 찾아줘')">댄스 챌린지 TOP 10</span>
                <span class="example-tag" onclick="setQuery('요리 레시피 5개 추천해줘')">요리 레시피 추천</span>
                <span class="example-tag" onclick="setQuery('피트니스 운동 분석해줘')">피트니스 운동 분석</span>
                <span class="example-tag" onclick="setQuery('쉬운 홈트레이닝 찾아줘')">홈트레이닝</span>
                <span class="example-tag" onclick="setQuery('간단한 베이킹 레시피')">베이킹 레시피</span>
            </div>
            
            <div class="loading" id="loading">
                <p>🔍 분석 중... 잠시만 기다려주세요.</p>
            </div>
            
            <div class="results" id="results"></div>
        </div>
        
        <script>
            function setQuery(query) {
                document.getElementById('queryInput').value = query;
            }
            
            async function analyzeQuery() {
                const query = document.getElementById('queryInput').value.trim();
                if (!query) {
                    alert('쿼리를 입력해주세요.');
                    return;
                }
                
                const loadingEl = document.getElementById('loading');
                const resultsEl = document.getElementById('results');
                
                loadingEl.style.display = 'block';
                resultsEl.innerHTML = '';
                
                try {
                    const response = await fetch('/api/analyze', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            query: query,
                            output_format: 'json',
                            include_recommendations: true
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.success) {
                        displayResults(data);
                    } else {
                        displayError(data.error_message || 'Unknown error occurred');
                    }
                    
                } catch (error) {
                    displayError('네트워크 오류가 발생했습니다: ' + error.message);
                } finally {
                    loadingEl.style.display = 'none';
                }
            }
            
            function displayResults(data) {
                const resultsEl = document.getElementById('results');
                
                let html = `
                    <div class="success">
                        ✅ 분석 완료! ${data.results_count}개 결과를 찾았습니다. (처리 시간: ${data.processing_time.toFixed(2)}초)
                    </div>
                    
                    <h3>📊 분석 요약</h3>
                    <p>${data.summary}</p>
                `;
                
                if (data.results && data.results.length > 0) {
                    html += '<h3>🏆 결과 목록</h3>';
                    data.results.forEach((result, index) => {
                        html += `
                            <div style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
                                <h4>${index + 1}. ${result.title}</h4>
                                <p><strong>채널:</strong> ${result.channel_title}</p>
                                <p><strong>조회수:</strong> ${result.view_count?.toLocaleString() || 'N/A'}회</p>
                                <p><strong>신뢰도:</strong> ${(result.confidence * 100).toFixed(1)}%</p>
                                ${result.youtube_url ? `<p><a href="${result.youtube_url}" target="_blank">YouTube에서 보기</a></p>` : ''}
                            </div>
                        `;
                    });
                }
                
                if (data.recommendations && data.recommendations.length > 0) {
                    html += '<h3>💡 추천 콘텐츠</h3>';
                    data.recommendations.forEach(rec => {
                        html += `
                            <div style="background: #f8f9fa; padding: 10px; margin: 5px 0; border-radius: 5px;">
                                <strong>${rec.title}</strong><br>
                                <small>${rec.description}</small>
                            </div>
                        `;
                    });
                }
                
                resultsEl.innerHTML = html;
            }
            
            function displayError(message) {
                const resultsEl = document.getElementById('results');
                resultsEl.innerHTML = `<div class="error">❌ 오류: ${message}</div>`;
            }
            
            // Allow Enter key to trigger analysis
            document.getElementById('queryInput').addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    analyzeQuery();
                }
            });
        </script>
    </body>
    </html>
    """


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze_content(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """Analyze content based on natural language query"""
    global natural_query_service
    
    if not natural_query_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        logger.info(f"Processing analysis request: '{request.query}'")
        
        # Check cache first
        cache = get_cache_manager()
        cache_key = cache._generate_cache_key("analyze", {
            "query": request.query,
            "output_format": request.output_format,
            "include_recommendations": request.include_recommendations
        })
        
        cached_result = await cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached result for query: '{request.query}'")
            return AnalyzeResponse(**cached_result)
        
        # Process the query
        query_response = await natural_query_service.process_query(request.query)
        
        if not query_response.success:
            raise HTTPException(
                status_code=400, 
                detail=query_response.error_message or "Query processing failed"
            )
        
        # Convert results to serializable format
        results = []
        for video in query_response.results:
            video_dict = {
                "video_id": video.video_id,
                "title": video.title,
                "channel_title": video.channel_title,
                "view_count": video.view_count,
                "confidence": video.confidence,
                "published_at": video.published_at.isoformat(),
                "youtube_url": f"https://www.youtube.com/watch?v={video.video_id}",
                "thumbnail_url": getattr(video, 'thumbnail_url', None)
            }
            
            # Add enhanced analysis if available
            if video.has_video_analysis and hasattr(video, 'enhanced_analysis'):
                analysis = video.enhanced_analysis
                video_dict["enhanced_analysis"] = {
                    "difficulty_level": analysis.accessibility_analysis.difficulty_level.value if hasattr(analysis, 'accessibility_analysis') else None,
                    "safety_level": getattr(analysis.accessibility_analysis, 'safety_level', {}).value if hasattr(analysis, 'accessibility_analysis') else None
                }
            
            # Add plugin metadata if available
            if hasattr(video, 'plugin_metadata'):
                video_dict["plugin_metadata"] = video.plugin_metadata
            
            results.append(video_dict)
        
        # Extract recommendations from metadata
        recommendations = query_response.metadata.get('recommendations', [])
        
        # Create response
        response = AnalyzeResponse(
            success=True,
            query=request.query,
            processing_time=query_response.processing_time,
            results_count=len(results),
            results=results,
            summary=query_response.summary,
            detailed_report=query_response.detailed_report if request.output_format == "markdown" else None,
            recommendations=recommendations if request.include_recommendations else None,
            metadata={
                "parsed_request": {
                    "action_type": query_response.parsed_request.action_type.value,
                    "content_type": query_response.parsed_request.content_filter.content_type.value,
                    "confidence": query_response.parsed_request.confidence
                } if query_response.parsed_request else None,
                "total_found": query_response.total_found
            },
            warnings=query_response.warnings
        )
        
        # Cache the response for future requests (30 minutes TTL)
        response_dict = response.dict()
        await cache.set(cache_key, response_dict, ttl=1800)
        
        logger.info(f"Analysis completed successfully: {len(results)} results")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Analysis request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/plugins", response_model=List[PluginInfo])
async def get_plugins():
    """Get list of available plugins"""
    global plugin_manager
    
    if not plugin_manager:
        raise HTTPException(status_code=503, detail="Plugin manager not initialized")
    
    try:
        plugins_info = plugin_manager.registry.list_plugins()
        return [
            PluginInfo(
                name=plugin["name"],
                version=plugin["version"],
                description=plugin["description"],
                content_types=plugin["content_types"],
                capabilities=plugin["capabilities"],
                initialized=plugin["initialized"]
            )
            for plugin in plugins_info
        ]
    except Exception as e:
        logger.error(f"Failed to get plugins info: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    global plugin_manager, startup_time
    
    try:
        # Basic system health check
        system_health = await check_health()
        
        # Plugin health check
        plugins_status = {}
        if plugin_manager:
            plugins_status = await plugin_manager.health_check_all_plugins()
        
        uptime_seconds = (datetime.now() - startup_time).total_seconds()
        
        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            version="1.0.0",
            uptime_seconds=uptime_seconds,
            plugins_status=plugins_status,
            system_info=system_health
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get service statistics"""
    global natural_query_service, plugin_manager, request_count
    
    try:
        service_stats = {}
        if natural_query_service:
            service_stats = natural_query_service.get_service_stats()
        
        plugin_stats = {}
        if plugin_manager:
            plugin_stats = plugin_manager.get_plugin_stats()
        
        return StatsResponse(
            total_queries=service_stats.get("total_queries", 0),
            successful_queries=service_stats.get("successful_queries", 0),
            failed_queries=service_stats.get("failed_queries", 0),
            avg_processing_time=service_stats.get("avg_processing_time", 0.0),
            last_query_time=service_stats.get("last_query_time").isoformat() if service_stats.get("last_query_time") else None,
            plugin_stats=plugin_stats
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get cache statistics"""
    try:
        cache = get_cache_manager()
        stats = await cache.get_cache_stats()
        return stats
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/cache/clear")
async def clear_cache():
    """Clear all cache entries (admin endpoint)"""
    try:
        cache = get_cache_manager()
        # This is a simple implementation - in production you'd want proper cache clearing
        if hasattr(cache, 'memory_cache'):
            cache.memory_cache.clear()
        
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "path": str(request.url.path)}
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    logger.error(f"Internal server error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)}
    )


if __name__ == "__main__":
    import uvicorn
    
    settings = get_settings()
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False,
        log_level="info"
    )
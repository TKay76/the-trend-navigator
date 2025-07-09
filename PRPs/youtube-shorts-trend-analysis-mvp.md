name: "YouTube Shorts Trend Analysis & AI Report MVP"
description: |

## Purpose
Build a comprehensive YouTube Shorts trend analysis system that automatically collects data, classifies videos using AI, and generates actionable insights reports. This MVP focuses on creating a robust, scalable foundation for trend analysis.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Create a production-ready YouTube Shorts trend analysis system that automatically collects trending short-form content, classifies videos into categories (Challenge, Info/Advice, Trending Sounds/BGM), and generates comprehensive AI-powered reports for content creators.

## Why
- **Business value**: Helps content creators identify trending topics and optimize their content strategy
- **Integration**: Provides actionable insights for YouTube Shorts creators
- **Problems solved**: Automates the time-consuming process of trend analysis and content research
- **Market need**: Addresses the growing demand for short-form content optimization tools

## What
A web-based application that:
- Periodically collects YouTube Shorts video data using YouTube Data API
- Classifies videos using AI into predefined categories 
- Generates detailed trend reports with actionable insights
- Provides efficient API quota management and error handling
- Supports scalable category expansion for future growth

### Success Criteria
- [ ] Successfully collects YouTube Shorts data via YouTube Data API
- [ ] AI classification achieves consistent categorization into 3 main categories
- [ ] Generates comprehensive trend reports with actionable insights
- [ ] Implements efficient API quota management (stays within 10,000 units/day)
- [ ] Includes robust error handling for all API interactions
- [ ] All tests pass and code meets quality standards per CLAUDE.md
- [ ] System is designed for easy category expansion

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://ai.pydantic.dev/agents/
  why: Core agent creation patterns, async usage, dependency injection
  
- url: https://ai.pydantic.dev/api/agent/
  why: Agent API reference for initialization, tools, and validation
  
- url: https://developers.google.com/youtube/v3/docs/search/list
  why: YouTube Data API search.list method for finding shorts
  
- url: https://developers.google.com/youtube/v3/docs/videos/list
  why: YouTube Data API videos.list method for video details
  
- url: https://developers.google.com/youtube/v3/determine_quota_cost
  why: API quota calculation - search.list=100 units, videos.list=1 unit
  
- file: examples/youtube_api_client_example.py
  why: Async API client pattern, error handling, constant management
  
- file: examples/data_model_example.py
  why: Pydantic model structure and validation patterns
  
- file: examples/simple_processing_agent_example.py
  why: Agent structure, data flow, and processing patterns
  
- doc: https://www.python-httpx.org/async/
  why: HTTPX async patterns for API rate limiting and error handling
  
- doc: https://ai.pydantic.dev/models/
  why: LLM provider configuration and cost optimization strategies
```

### Current Codebase tree
```bash
/mnt/e/_Unity Project/challenge-platform-claude/Context-Engineering-Intro/
├── CLAUDE.md                    # Global rules and conventions
├── INITIAL.md                   # Feature requirements
├── README.md                    # Project documentation
├── examples/                    # Code patterns to follow
│   ├── data_model_example.py   # Pydantic model patterns
│   ├── simple_processing_agent_example.py  # Agent structure
│   └── youtube_api_client_example.py       # API client patterns
├── PRPs/                       # Product Requirements Prompts
│   ├── templates/
│   │   └── prp_base.md
│   └── EXAMPLE_multi_agent_prp.md
```

### Desired Codebase tree with files to be added
```bash
/mnt/e/_Unity Project/challenge-platform-claude/Context-Engineering-Intro/
├── src/
│   ├── __init__.py                    # Package initialization
│   ├── models/
│   │   ├── __init__.py               # Models package init
│   │   ├── video_models.py           # Video data models (Pydantic)
│   │   └── classification_models.py  # Classification result models
│   ├── clients/
│   │   ├── __init__.py               # Clients package init
│   │   ├── youtube_client.py         # YouTube API client
│   │   └── llm_provider.py           # LLM provider interface
│   ├── agents/
│   │   ├── __init__.py               # Agents package init
│   │   ├── collector_agent.py        # Data collection agent
│   │   └── analyzer_agent.py         # Analysis and reporting agent
│   ├── core/
│   │   ├── __init__.py               # Core package init
│   │   ├── settings.py               # Environment and configuration
│   │   └── exceptions.py             # Custom exceptions
│   └── cli.py                        # Command-line interface
├── tests/
│   ├── __init__.py                   # Tests package init
│   ├── test_youtube_client.py        # YouTube client tests
│   ├── test_collector_agent.py       # Collector agent tests
│   ├── test_analyzer_agent.py        # Analyzer agent tests
│   ├── test_models.py                # Model validation tests
│   └── conftest.py                   # Pytest configuration
├── .env.example                      # Environment variables template
├── requirements.txt                  # Python dependencies
└── README.md                         # Updated project documentation
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: YouTube Data API quota management
# - search.list costs 100 units (expensive!)
# - videos.list costs 1 unit (cheap for details)
# - Default quota: 10,000 units/day
# - Must include quota cost comments: # Quota Cost: X

# CRITICAL: YouTube Shorts identification
# - No direct "shorts" filter in search.list
# - Must use videoDuration parameter or check duration in videos.list
# - Shorts are <= 60 seconds in duration

# CRITICAL: Pydantic AI requirements
# - Always use async throughout - no sync functions in async context
# - Agent deps_type must be passed to run() method
# - Use structured output models for LLM responses
# - Include proper error handling with ModelRetry

# CRITICAL: Project-specific rules from CLAUDE.md
# - Never create files longer than 500 lines
# - Always use venv_linux for Python commands
# - Use python_dotenv and load_env() for environment variables
# - Follow strict agent role separation (collector vs analyzer)
# - Model-first principle: always use Pydantic models, never raw dict/json

# CRITICAL: API rate limiting with httpx
# - Use exponential backoff for 429 responses
# - Implement circuit breaker pattern for resilience
# - Monitor API usage to prevent quota exhaustion
# - Use aiometer for request rate limiting
```

## Implementation Blueprint

### Data models and structure

Create comprehensive data models ensuring type safety and API compatibility:

```python
# models/video_models.py - Core video data structures
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List
from datetime import datetime
from enum import Enum

class VideoCategory(str, Enum):
    CHALLENGE = "Challenge"
    INFO_ADVICE = "Info/Advice"
    TRENDING_SOUNDS = "Trending Sounds/BGM"

class VideoStatistics(BaseModel):
    view_count: int = Field(0, description="Number of views")
    like_count: int = Field(0, description="Number of likes")
    comment_count: int = Field(0, description="Number of comments")
    
class VideoSnippet(BaseModel):
    title: str = Field(..., description="Video title")
    description: str = Field("", description="Video description")
    published_at: datetime = Field(..., description="Publication date")
    channel_title: str = Field("", description="Channel name")
    thumbnail_url: HttpUrl = Field(..., description="Thumbnail URL")
    duration: str = Field(..., description="Video duration in ISO 8601 format")
    
class YouTubeVideoRaw(BaseModel):
    """Raw YouTube API response structure"""
    video_id: str = Field(..., description="YouTube video ID")
    snippet: VideoSnippet
    statistics: Optional[VideoStatistics] = None
    
class ClassifiedVideo(BaseModel):
    """Video with AI classification results"""
    video_id: str
    title: str
    category: VideoCategory
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="AI reasoning for classification")
    
class TrendReport(BaseModel):
    """Generated trend analysis report"""
    category: VideoCategory
    trend_summary: str
    key_insights: List[str]
    recommended_actions: List[str]
    top_videos: List[ClassifiedVideo]
    generated_at: datetime
```

### List of tasks to be completed in order

```yaml
Task 1: Setup Project Structure and Configuration
CREATE src/core/settings.py:
  - PATTERN: Use pydantic-settings like examples use os.getenv
  - Load environment variables with validation
  - Include YouTube API key and LLM provider configuration
  - Follow CLAUDE.md rules for environment variable management

CREATE .env.example:
  - Include all required environment variables with descriptions
  - YouTube API key configuration
  - LLM provider settings

Task 2: Implement Core Data Models
CREATE src/models/video_models.py:
  - PATTERN: Follow examples/data_model_example.py structure
  - Define comprehensive video data models
  - Include validation for YouTube API response structure
  - Add classification result models

CREATE src/models/classification_models.py:
  - Define classification request/response models
  - Include confidence scoring and reasoning
  - Support for category expansion

Task 3: Build YouTube API Client
CREATE src/clients/youtube_client.py:
  - PATTERN: Follow examples/youtube_api_client_example.py exactly
  - Implement async API client with proper error handling
  - Add quota cost comments for all API calls
  - Include rate limiting and retry logic
  - Methods: search_shorts(), get_video_details(), get_video_statistics()

Task 4: Implement LLM Provider Interface
CREATE src/clients/llm_provider.py:
  - PATTERN: Use Pydantic AI agent patterns from documentation
  - Create cost-effective LLM provider with model selection
  - Implement structured classification responses
  - Support for multiple LLM providers (OpenAI, Anthropic, etc.)

Task 5: Create Data Collection Agent
CREATE src/agents/collector_agent.py:
  - PATTERN: Follow examples/simple_processing_agent_example.py structure
  - STRICT ROLE: Only data collection, no analysis or transformation
  - Use YouTube client to fetch shorts data
  - Implement efficient quota management
  - Return structured video data using Pydantic models

Task 6: Create Analysis Agent
CREATE src/agents/analyzer_agent.py:
  - PATTERN: Follow Pydantic AI agent creation patterns
  - STRICT ROLE: Analysis and reporting only, no external API calls
  - Classify videos using LLM provider
  - Generate trend reports with actionable insights
  - Use structured output validation

Task 7: Build CLI Interface
CREATE src/cli.py:
  - PATTERN: Follow async command structure
  - Commands: collect, analyze, report
  - Include progress indicators and error handling
  - Support for different output formats

Task 8: Add Core Infrastructure
CREATE src/core/exceptions.py:
  - Custom exceptions for API errors, quota exceeded, etc.
  - Consistent error handling patterns

Task 9: Comprehensive Testing
CREATE tests/ directory:
  - PATTERN: Follow pytest patterns with async support
  - Mock external API calls (YouTube, LLM)
  - Test quota management logic
  - Include edge cases and error scenarios
  - Ensure 80%+ test coverage

Task 10: Documentation and Examples
UPDATE README.md:
  - Installation and setup instructions
  - Usage examples and API documentation
  - Architecture overview
  - Configuration guide
```

### Per task pseudocode

```python
# Task 3: YouTube API Client Implementation
class YouTubeClient:
    def __init__(self, api_key: str):
        # PATTERN: Follow examples/youtube_api_client_example.py
        self.api_key = api_key
        self.base_url = "https://www.googleapis.com/youtube/v3"
        self.client = httpx.AsyncClient(
            limits=httpx.Limits(max_connections=10),
            timeout=30.0
        )
    
    async def search_shorts(self, query: str, max_results: int = 50) -> List[YouTubeVideoRaw]:
        # Quota Cost: 100 (expensive - use sparingly)
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "videoDuration": "short",  # Filter for shorts
            "maxResults": max_results,
            "key": self.api_key
        }
        
        # PATTERN: Error handling with retry logic
        for attempt in range(3):
            try:
                response = await self.client.get(f"{self.base_url}/search", params=params)
                
                if response.status_code == 429:
                    # CRITICAL: Handle rate limiting
                    retry_after = int(response.headers.get('retry-after', 60))
                    await asyncio.sleep(retry_after)
                    continue
                
                response.raise_for_status()
                data = response.json()
                
                # PATTERN: Return structured data using Pydantic models
                return [YouTubeVideoRaw(**item) for item in data.get('items', [])]
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 403:
                    raise QuotaExceededError("YouTube API quota exceeded")
                if attempt == 2:
                    raise
                await asyncio.sleep(2 ** attempt)

# Task 5: Data Collection Agent
class CollectorAgent:
    def __init__(self, youtube_client: YouTubeClient):
        # PATTERN: Dependency injection for testability
        self.youtube_client = youtube_client
        self.agent_name = "CollectorAgent"
    
    async def collect_trending_shorts(self, categories: List[str]) -> List[YouTubeVideoRaw]:
        # STRICT ROLE: Only collection, no analysis
        all_videos = []
        
        for category in categories:
            # QUOTA MANAGEMENT: Spread searches across categories
            videos = await self.youtube_client.search_shorts(
                query=f"{category} shorts trending",
                max_results=20  # Limit to manage quota
            )
            all_videos.extend(videos)
            
            # PATTERN: Add delay between requests
            await asyncio.sleep(1)
        
        return all_videos

# Task 6: Analysis Agent with Pydantic AI
classification_agent = Agent(
    'openai:gpt-4o-mini',  # Cost-effective model for classification
    deps_type=ClassificationDeps,
    output_type=ClassifiedVideo,
    instructions="""
    You are a YouTube Shorts content classifier. Analyze the video title, description, 
    and metadata to classify it into one of three categories:
    - Challenge: Dance challenges, fitness challenges, viral challenges
    - Info/Advice: Educational content, tutorials, tips, how-to videos
    - Trending Sounds/BGM: Music-focused content, sound trends, audio-centric videos
    
    Provide high confidence scoring and clear reasoning for your classification.
    """
)

@classification_agent.tool
async def get_video_context(ctx: RunContext[ClassificationDeps], video_id: str) -> str:
    """Get additional context about the video for classification"""
    # PATTERN: Use dependency injection to access services
    video_details = await ctx.deps.youtube_client.get_video_details(video_id)
    return f"Additional context: {video_details}"

class AnalyzerAgent:
    def __init__(self, llm_provider: LLMProvider):
        self.llm_provider = llm_provider
        self.agent_name = "AnalyzerAgent"
    
    async def classify_videos(self, videos: List[YouTubeVideoRaw]) -> List[ClassifiedVideo]:
        # STRICT ROLE: Analysis only, no external API calls
        classified_videos = []
        
        for video in videos:
            # PATTERN: Use structured LLM responses
            classification = await classification_agent.run(
                f"Classify this video: {video.snippet.title} - {video.snippet.description}",
                deps=ClassificationDeps(video=video)
            )
            classified_videos.append(classification.data)
        
        return classified_videos
```

### Integration Points
```yaml
ENVIRONMENT:
  - add to: .env
  - vars: |
      # YouTube Data API
      YOUTUBE_API_KEY=your_api_key_here
      
      # LLM Configuration
      LLM_PROVIDER=openai
      LLM_API_KEY=your_llm_api_key
      LLM_MODEL=gpt-4o-mini
      
      # Application Settings
      MAX_DAILY_QUOTA=8000
      RATE_LIMIT_PER_SECOND=10
      
DEPENDENCIES:
  - Update requirements.txt with:
    - pydantic-ai[anthropic,openai,gemini]
    - httpx
    - python-dotenv
    - pydantic-settings
    - aiometer
    - pytest
    - pytest-asyncio
    
TESTING:
  - Use pytest with async support
  - Mock external API calls
  - Test quota management logic
  - Include error handling tests
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
source venv_linux/bin/activate  # CRITICAL: Use venv_linux per CLAUDE.md
ruff check src/ tests/ --fix     # Auto-fix style issues
mypy src/ tests/                 # Type checking

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# test_youtube_client.py
@pytest.mark.asyncio
async def test_search_shorts_success():
    """Test successful shorts search"""
    client = YouTubeClient("test_api_key")
    videos = await client.search_shorts("dance challenge", max_results=10)
    assert len(videos) > 0
    assert all(isinstance(v, YouTubeVideoRaw) for v in videos)

@pytest.mark.asyncio
async def test_quota_exceeded_handling():
    """Test quota exceeded error handling"""
    client = YouTubeClient("test_api_key")
    with pytest.raises(QuotaExceededError):
        await client.search_shorts("test", max_results=1000)

# test_collector_agent.py
@pytest.mark.asyncio
async def test_collector_agent_data_collection():
    """Test collector agent collects data correctly"""
    mock_client = Mock(spec=YouTubeClient)
    agent = CollectorAgent(mock_client)
    
    videos = await agent.collect_trending_shorts(["dance", "fitness"])
    assert len(videos) > 0
    assert all(isinstance(v, YouTubeVideoRaw) for v in videos)

# test_analyzer_agent.py
@pytest.mark.asyncio
async def test_analyzer_classification():
    """Test analyzer agent classifies videos correctly"""
    mock_llm = Mock(spec=LLMProvider)
    agent = AnalyzerAgent(mock_llm)
    
    test_videos = [create_test_video("dance challenge")]
    classified = await agent.classify_videos(test_videos)
    
    assert len(classified) == 1
    assert classified[0].category == VideoCategory.CHALLENGE
    assert classified[0].confidence > 0.7
```

```bash
# Run tests iteratively until passing:
source venv_linux/bin/activate  # CRITICAL: Use venv_linux
uv run pytest tests/ -v --cov=src --cov-report=term-missing

# If failing: Debug specific test, fix code, re-run
```

### Level 3: Integration Test
```bash
# Test CLI functionality
source venv_linux/bin/activate  # CRITICAL: Use venv_linux
python -m src.cli collect --categories "dance,fitness" --max-results 10

# Expected output:
# 🚀 Starting data collection...
# 📊 Collected 20 videos across 2 categories
# ✅ Collection complete!

python -m src.cli analyze --input-file collected_videos.json

# Expected output:
# 🤖 Starting AI classification...
# 📋 Classified 20 videos:
#   - Challenge: 12 videos
#   - Info/Advice: 5 videos
#   - Trending Sounds/BGM: 3 videos
# ✅ Analysis complete!

python -m src.cli report --category Challenge

# Expected output:
# 📈 Trend Report for Challenge Category
# 🔥 Key Insights:
#   - Dance challenges dominate with 67% of content
#   - Fitness challenges showing 23% growth
# 💡 Recommended Actions:
#   - Focus on dance trends for maximum reach
#   - Consider fitness crossover content
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `ruff check src/ tests/`
- [ ] No type errors: `mypy src/ tests/`
- [ ] YouTube API client handles rate limiting correctly
- [ ] LLM classification produces structured, consistent results
- [ ] CLI provides clear, actionable outputs
- [ ] API quota management prevents exhaustion
- [ ] Error cases handled gracefully with proper logging
- [ ] File size limits respected (max 500 lines per file)
- [ ] All environment variables documented in .env.example
- [ ] README includes comprehensive setup and usage instructions

---

## Anti-Patterns to Avoid
- ❌ Don't exceed 500 lines per file - refactor into modules
- ❌ Don't use raw dict/json - always use Pydantic models
- ❌ Don't mix collection and analysis logic in same agent
- ❌ Don't ignore API quota costs - always include comments
- ❌ Don't skip error handling for external API calls
- ❌ Don't use sync functions in async context
- ❌ Don't hardcode API keys - use environment variables
- ❌ Don't forget to use venv_linux for Python commands

## Confidence Score: 9/10

High confidence due to:
- Clear examples to follow in the codebase
- Comprehensive API documentation for YouTube Data API
- Well-established patterns for Pydantic AI agents
- Detailed validation gates and testing requirements
- Strong context engineering with all necessary references

Minor uncertainty on YouTube Shorts detection accuracy, but multiple filtering approaches are documented and can be iterated upon.
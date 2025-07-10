# PRP: Improve Stability and Efficiency of AI AnalyzerAgent

## Project Context

**YouTube Shorts Trend Analysis MVP** - A comprehensive platform for collecting, classifying, and analyzing YouTube Shorts trends using AI-powered video classification.

## Objective

Resolve rate limiting (429) and server overload (503) errors during LLM API calls when classifying numerous videos, making the AI analysis pipeline stable and scalable by implementing batch processing and retry logic.

## Problem Statement

Current implementation performs 1 LLM API call per video (`src/agents/analyzer_agent.py:classify_videos()` lines 70-98), causing:
- Quota exhaustion with large video datasets (observed: 52 videos collected, only 10 classified before timeout)
- 503 Service Unavailable errors from Gemini API overload
- Inefficient resource usage and slow processing

## Core Requirements

### 1. Batch Processing Implementation
**Target File:** `src/agents/analyzer_agent.py`
- **Current Pattern:** Line 75: `await self.llm_provider.classify_video(video)` in sequential loop
- **New Pattern:** Batch 5-10 videos per API call to reduce total requests by 80-90%
- **Model Support:** Utilize existing `BatchClassificationRequest` from `src/models/classification_models.py:50-76`

### 2. Retry Logic with Exponential Backoff
**Target File:** `src/clients/llm_provider.py`
- **Reference Pattern:** `src/clients/youtube_client.py:148-191` (`_make_search_request` method)
- **Pattern to Copy:** `for attempt in range(3):` and `await asyncio.sleep(2 ** attempt)`
- **Handle Errors:** 503 Service Unavailable, 429 Rate Limiting

## Implementation Blueprint

### Phase 1: Enhanced LLM Provider with Retry Logic

```python
# src/clients/llm_provider.py - Add new method
async def classify_videos_batch_optimized(self, videos: List[YouTubeVideoRaw], batch_size: int = 5) -> List[ClassificationResponse]:
    """
    Classify multiple videos using true batching with retry logic.
    Reduces API calls by sending multiple videos in single prompt.
    """
    for attempt in range(3):
        try:
            # Create batch prompt with multiple videos
            batch_prompt = self._create_batch_classification_prompt(videos)
            
            # Single API call for entire batch
            result = await self.classification_agent.run(batch_prompt, deps=...)
            
            # Parse batch response back to individual classifications
            return self._parse_batch_classification_result(result, videos)
            
        except Exception as e:
            if "503" in str(e) or "Service Unavailable" in str(e):
                if attempt < 2:
                    await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
                    continue
                raise ClassificationError(f"Service unavailable after retries: {e}")
            raise ClassificationError(f"Classification failed: {e}")
```

### Phase 2: Batch Prompt Engineering

```python
def _create_batch_classification_prompt(self, videos: List[YouTubeVideoRaw]) -> str:
    """Create optimized prompt for batch classification"""
    batch_text = "Classify the following YouTube Shorts videos:\n\n"
    
    for i, video in enumerate(videos, 1):
        batch_text += f"VIDEO {i}:\n"
        batch_text += f"Title: {video.snippet.title}\n"
        batch_text += f"Channel: {video.snippet.channel_title}\n"
        batch_text += f"Description: {video.snippet.description[:200]}...\n\n"
    
    batch_text += """
For each video, respond with JSON format:
{
  "video_1": {"category": "Challenge", "confidence": 0.95, "reasoning": "..."},
  "video_2": {"category": "Info/Advice", "confidence": 0.87, "reasoning": "..."},
  ...
}"""
    return batch_text
```

### Phase 3: AnalyzerAgent Integration

```python
# src/agents/analyzer_agent.py - Replace classify_videos method
async def classify_videos(self, videos: List[YouTubeVideoRaw]) -> List[ClassifiedVideo]:
    """Enhanced video classification with batching"""
    logger.info(f"[{self.agent_name}] Starting batch classification of {len(videos)} videos")
    
    classified_videos = []
    batch_size = 5  # Start conservative, can tune up to 10
    
    # Process videos in batches
    for i in range(0, len(videos), batch_size):
        batch = videos[i:i + batch_size]
        logger.debug(f"Processing batch {i//batch_size + 1}: {len(batch)} videos")
        
        try:
            # Use new batch classification
            batch_responses = await self.llm_provider.classify_videos_batch_optimized(batch)
            
            # Convert to ClassifiedVideo objects
            for response in batch_responses:
                video = next(v for v in batch if v.video_id == response.video_id)
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
            
            self.analysis_stats["classifications_successful"] += len(batch_responses)
            
        except ClassificationError as e:
            logger.warning(f"Batch classification failed: {e}")
            self.analysis_stats["classifications_failed"] += len(batch)
            continue
    
    return classified_videos
```

## Implementation Tasks (Sequential Order)

1. **[LLM Provider]** Add retry wrapper to `src/clients/llm_provider.py:classify_video()`
2. **[LLM Provider]** Implement `_create_batch_classification_prompt()` method
3. **[LLM Provider]** Implement `_parse_batch_classification_result()` method  
4. **[LLM Provider]** Implement `classify_videos_batch_optimized()` method
5. **[AnalyzerAgent]** Refactor `classify_videos()` to use batching
6. **[Testing]** Create `tests/test_llm_provider.py` with comprehensive tests
7. **[Testing]** Update `tests/test_analyzer_agent.py` for batch scenarios
8. **[Integration]** Test end-to-end pipeline with various batch sizes

## Code References

### Existing Retry Pattern (Copy This)
```python
# src/clients/youtube_client.py:148-191
async def _make_search_request(self, params: Dict[str, Any]) -> List[str]:
    for attempt in range(3):
        try:
            response = await self.client.get(f"{self.base_url}/search", params=params)
            # ... handle response
        except httpx.HTTPStatusError as e:
            if attempt == 2:
                raise YouTubeAPIError(f"YouTube API error: {e.response.status_code}")
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Existing Batch Models (Use These)
```python
# src/models/classification_models.py:50-89
class BatchClassificationRequest(BaseModel):
    videos: List[YouTubeVideoRaw] = Field(..., min_items=1)
    classification_settings: Optional[Dict[str, Any]] = None

class BatchClassificationResponse(BaseModel):
    classifications: List[ClassificationResponse] = Field(...)
    batch_summary: Dict[str, Any] = Field(...)
    total_videos: int = Field(...)
    successful_classifications: int = Field(...)
    failed_classifications: int = Field(...)
```

### Current Sequential Pattern (Replace This)
```python
# src/agents/analyzer_agent.py:70-98 - CURRENT INEFFICIENT PATTERN
for i, video in enumerate(videos):
    try:
        classification_response = await self.llm_provider.classify_video(video)  # 1 API call each
        # ... process individual result
```

## Testing Strategy

### Unit Tests Required
```python
# tests/test_llm_provider.py - NEW FILE
class TestLLMProviderBatching:
    @pytest.mark.asyncio
    async def test_classify_videos_batch_optimized_success(self):
        """Test successful batch classification"""
        
    @pytest.mark.asyncio  
    async def test_classify_videos_batch_optimized_retry_logic(self):
        """Test retry logic with 503 errors"""
        
    @pytest.mark.asyncio
    async def test_batch_prompt_creation(self):
        """Test batch prompt formatting"""
        
    @pytest.mark.asyncio
    async def test_batch_result_parsing(self):
        """Test parsing batch JSON response"""
```

### Updated Tests Required
```python
# tests/test_analyzer_agent.py - UPDATE EXISTING
@pytest.mark.asyncio
async def test_classify_videos_with_batching(self):
    """Test video classification using batching"""
    
@pytest.mark.asyncio
async def test_classify_videos_batch_failure_recovery(self):
    """Test recovery when some batches fail"""
```

## Validation Gates (Executable Commands)

```bash
# Syntax/Style Check
ruff check --fix src/ tests/
mypy src/

# Unit Tests (must pass)
YOUTUBE_API_KEY=test_key LLM_API_KEY=test_key python -m pytest tests/test_llm_provider.py -v
YOUTUBE_API_KEY=test_key LLM_API_KEY=test_key python -m pytest tests/test_analyzer_agent.py -v

# Integration Test (verify pipeline works)
YOUTUBE_API_KEY=test_key LLM_API_KEY=test_key python -m pytest tests/ -k "batch" -v

# CLI Functionality Test
YOUTUBE_API_KEY=test_key LLM_API_KEY=test_key python -m src.cli analyze --input tests/fixtures/sample_videos.json
```

## Performance Targets

- **API Call Reduction:** 80-90% fewer LLM API calls (52 videos: 52 calls → 6-11 calls)
- **Error Resilience:** 100% recovery from transient 503 errors via retry logic
- **Processing Speed:** 50% faster processing due to reduced network round-trips
- **Cost Optimization:** Proportional cost reduction from fewer API calls

## Risk Mitigation

### Context Length Limits
- **Solution:** Start with batch_size=5, tune up gradually
- **Fallback:** If batch fails due to context length, split into smaller batches

### Parsing Complexity  
- **Solution:** Use structured JSON output with clear delimiters
- **Fallback:** Individual classification if batch parsing fails

### Model Accuracy
- **Validation:** Compare batch vs individual classification accuracy
- **Monitoring:** Track confidence scores across batch sizes

## Architectural Constraints

- **No Breaking Changes:** Maintain existing public API of `AnalyzerAgent.classify_videos()`
- **Dependency Injection:** Preserve testability with mock LLM providers  
- **Error Handling:** Maintain existing exception types (`ClassificationError`)
- **Logging:** Enhance existing logging with batch-specific messages

## Documentation Requirements

### Code Comments
```python
# Quota Cost: 1 (was 10 with individual calls) - 90% reduction
async def classify_videos_batch_optimized(self, videos: List[YouTubeVideoRaw], batch_size: int = 5):
    """
    Classify multiple videos in single API call with retry logic.
    
    Reduces API quota usage by ~90% compared to individual classification.
    Implements exponential backoff for transient 503/429 errors.
    """
```

### Update CLAUDE.md
```markdown
## Batch Processing Performance
- **Video Classification:** Processes 5-10 videos per API call
- **Error Recovery:** Automatic retry with exponential backoff
- **Cost Optimization:** 90% reduction in LLM API calls
```

## Implementation Confidence Score: 9/10

**High confidence rationale:**
- ✅ Clear reference patterns exist in codebase (`youtube_client.py` retry logic)
- ✅ Data models already defined (`BatchClassificationRequest`/`Response`)  
- ✅ Isolated refactoring with clear boundaries
- ✅ Comprehensive test strategy defined
- ✅ Executable validation gates provided
- ✅ Specific line numbers and code examples referenced
- ⚠️ Minor risk: LLM batch parsing complexity (mitigated with structured JSON)

**Success factors:**
1. Existing retry pattern provides exact template to follow
2. Batch models eliminate data structure design work
3. Clear performance targets enable validation
4. Incremental approach reduces implementation risk
5. Comprehensive error handling strategy defined
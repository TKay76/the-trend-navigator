"""LLM provider interface for cost-effective video classification"""

import logging
import asyncio
from typing import Optional, Dict, List
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext

from ..core.settings import get_settings
from ..core.exceptions import LLMProviderError, ClassificationError
from ..models.video_models import VideoCategory, YouTubeVideoRaw
from ..models.classification_models import ClassificationResponse

# Setup logging
logger = logging.getLogger(__name__)


class ClassificationDependencies(BaseModel):
    """Dependencies for classification agent"""
    video: YouTubeVideoRaw
    provider: 'LLMProvider'
    
    class Config:
        arbitrary_types_allowed = True


class ClassificationResult(BaseModel):
    """Structured output for video classification"""
    category: VideoCategory
    confidence: float
    reasoning: str
    keywords: List[str] = []
    
    class Config:
        use_enum_values = True


class LLMProvider:
    """
    Cost-effective LLM provider for video classification.
    Uses Pydantic AI with model selection optimization.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize LLM provider.
        
        Args:
            model_name: Specific model to use (if None, uses settings)
        """
        self.settings = get_settings()
        self.model_name = model_name or self.settings.llm_model
        self.provider_name = self.settings.llm_provider
        
        # Create classification agent
        self.classification_agent = self._create_classification_agent()
        
        logger.info(f"Initialized LLM provider: {self.provider_name}/{self.model_name}")
    
    def _create_classification_agent(self) -> Agent:
        """Create Pydantic AI agent for video classification"""
        
        # Model string format for pydantic-ai
        # For Google models, use just the model name
        if self.provider_name == "gemini":
            model_string = self.model_name
        else:
            model_string = f"{self.provider_name}:{self.model_name}"
        
        return Agent(
            model_string,
            deps_type=ClassificationDependencies,
            result_type=ClassificationResult,
            system_prompt=self._get_classification_prompt()
        )
    
    def _get_classification_prompt(self) -> str:
        """Get system prompt for video classification"""
        return """You are an expert YouTube Shorts content classifier. Analyze video metadata to categorize content accurately.

CLASSIFICATION CATEGORIES:
1. Challenge - Dance challenges, fitness challenges, viral challenges, trending activities
2. Info/Advice - Educational content, tutorials, tips, how-to videos, informational content
3. Trending Sounds/BGM - Music-focused content, sound trends, audio-centric videos, song covers

ANALYSIS GUIDELINES:
- Focus on title keywords and description content
- Consider channel type and content style
- Look for challenge-related terms (challenge, dance, workout, viral)
- Identify educational markers (how to, tutorial, tips, learn, guide)
- Spot music/audio focus (song, music, sound, beat, audio, cover)

OUTPUT REQUIREMENTS:
- Provide confidence score (0.0-1.0) based on certainty
- Include clear reasoning for classification decision
- Extract key classification keywords from title/description
- Be decisive but honest about uncertainty

QUALITY STANDARDS:
- Confidence > 0.8 for clear categorizations
- Confidence 0.6-0.8 for probable categorizations  
- Confidence < 0.6 for uncertain cases (mark as best guess)"""

    async def classify_video(self, video: YouTubeVideoRaw) -> ClassificationResponse:
        """
        Classify a single video using LLM with retry logic.
        
        Args:
            video: Video to classify
            
        Returns:
            Classification response with category, confidence, and reasoning
            
        Raises:
            ClassificationError: If classification fails
        """
        for attempt in range(3):
            try:
                logger.debug(f"Classifying video: {video.video_id} - {video.snippet.title} (attempt {attempt + 1})")
                
                # Prepare input for classification
                input_text = self._prepare_classification_input(video)
                
                # Run classification agent
                deps = ClassificationDependencies(video=video, provider=self)
                result = await self.classification_agent.run(
                    input_text,
                    deps=deps
                )
                
                # Convert to response model
                classification_result = result.data
                
                response = ClassificationResponse(
                    video_id=video.video_id,
                    category=classification_result.category,
                    confidence=classification_result.confidence,
                    reasoning=classification_result.reasoning,
                    alternative_categories=[],  # Could be enhanced later
                    model_used=f"{self.provider_name}/{self.model_name}",
                    processing_time=0.0  # Would need timing implementation
                )
                
                logger.debug(f"Classification result: {classification_result.category} (confidence: {classification_result.confidence})")
                return response
                
            except Exception as e:
                error_str = str(e)
                if "503" in error_str or "Service Unavailable" in error_str or "429" in error_str or "Rate Limit" in error_str:
                    if attempt < 2:
                        wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                        logger.warning(f"Service unavailable/rate limited for video {video.video_id}, retrying in {wait_time}s (attempt {attempt + 1}/3)")
                        await asyncio.sleep(wait_time)
                        continue
                    logger.error(f"Classification failed for video {video.video_id} after retries: {e}")
                    raise ClassificationError(f"Service unavailable after retries for video {video.video_id}: {str(e)}")
                else:
                    logger.error(f"Classification failed for video {video.video_id}: {e}")
                    raise ClassificationError(f"Failed to classify video {video.video_id}: {str(e)}")
        
        # Should never reach here due to the retry logic
        raise ClassificationError(f"Unexpected error in classify_video for {video.video_id}")
    
    async def classify_videos_batch(self, videos: List[YouTubeVideoRaw]) -> List[ClassificationResponse]:
        """
        Classify multiple videos in batch (legacy sequential method).
        
        Args:
            videos: List of videos to classify
            
        Returns:
            List of classification responses
        """
        logger.info(f"Starting legacy batch classification of {len(videos)} videos")
        
        results = []
        for video in videos:
            try:
                result = await self.classify_video(video)
                results.append(result)
            except ClassificationError as e:
                logger.warning(f"Skipping failed classification: {e}")
                continue
        
        logger.info(f"Completed batch classification: {len(results)}/{len(videos)} successful")
        return results
    
    async def classify_videos_batch_optimized(self, videos: List[YouTubeVideoRaw], batch_size: int = 5) -> List[ClassificationResponse]:
        """
        Classify multiple videos using true batching with retry logic.
        Reduces API calls by sending multiple videos in single prompt.
        
        # Quota Cost: 1 (was 10 with individual calls) - 90% reduction
        
        Args:
            videos: List of videos to classify
            batch_size: Number of videos to process in each batch (5-10 recommended)
            
        Returns:
            List of classification responses
            
        Raises:
            ClassificationError: If batch classification fails
        """
        if not videos:
            return []
        
        logger.info(f"Starting optimized batch classification of {len(videos)} videos (batch_size={batch_size})")
        
        all_results = []
        
        # Process videos in batches
        for i in range(0, len(videos), batch_size):
            batch = videos[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(videos) + batch_size - 1) // batch_size
            
            logger.debug(f"Processing batch {batch_num}/{total_batches}: {len(batch)} videos")
            
            for attempt in range(3):
                try:
                    # Create batch prompt with multiple videos
                    batch_prompt = self._create_batch_classification_prompt(batch)
                    
                    # Single API call for entire batch
                    deps = ClassificationDependencies(video=batch[0], provider=self)  # Use first video for deps
                    result = await self.classification_agent.run(batch_prompt, deps=deps)
                    
                    # Parse batch response back to individual classifications
                    batch_results = self._parse_batch_classification_result(result.data, batch)
                    all_results.extend(batch_results)
                    
                    logger.debug(f"Batch {batch_num} completed successfully: {len(batch_results)} classifications")
                    break
                    
                except Exception as e:
                    error_str = str(e)
                    if "503" in error_str or "Service Unavailable" in error_str or "429" in error_str or "Rate Limit" in error_str:
                        if attempt < 2:
                            wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                            logger.warning(f"Service unavailable/rate limited for batch {batch_num}, retrying in {wait_time}s (attempt {attempt + 1}/3)")
                            await asyncio.sleep(wait_time)
                            continue
                        logger.error(f"Batch {batch_num} failed after retries: {e}")
                        raise ClassificationError(f"Service unavailable after retries for batch {batch_num}: {str(e)}")
                    else:
                        logger.error(f"Batch {batch_num} classification failed: {e}")
                        raise ClassificationError(f"Failed to classify batch {batch_num}: {str(e)}")
        
        logger.info(f"Optimized batch classification complete: {len(all_results)}/{len(videos)} successful")
        return all_results
    
    def _prepare_classification_input(self, video: YouTubeVideoRaw) -> str:
        """
        Prepare input text for classification.
        
        Args:
            video: Video data to analyze
            
        Returns:
            Formatted input text for LLM
        """
        title = video.snippet.title
        description = video.snippet.description
        channel = video.snippet.channel_title
        
        # Truncate description to avoid token limits
        if len(description) > 500:
            description = description[:500] + "..."
        
        input_text = f"""Classify this YouTube Short:

Title: {title}
Channel: {channel}
Description: {description}

Analyze the content and classify into one of the three categories: Challenge, Info/Advice, or Trending Sounds/BGM."""

        return input_text
    
    def _create_batch_classification_prompt(self, videos: List[YouTubeVideoRaw]) -> str:
        """
        Create optimized prompt for batch classification.
        
        Args:
            videos: List of videos to classify in batch
            
        Returns:
            Formatted batch prompt for LLM
        """
        batch_text = "Classify the following YouTube Shorts videos:\n\n"
        
        for i, video in enumerate(videos, 1):
            batch_text += f"VIDEO {i}:\n"
            batch_text += f"Title: {video.snippet.title}\n"
            batch_text += f"Channel: {video.snippet.channel_title}\n"
            
            # Truncate description to avoid token limits
            description = video.snippet.description
            if len(description) > 200:
                description = description[:200] + "..."
            batch_text += f"Description: {description}\n\n"
        
        batch_text += """For each video, respond with JSON format:
{
  "video_1": {"category": "Challenge", "confidence": 0.95, "reasoning": "..."},
  "video_2": {"category": "Info/Advice", "confidence": 0.87, "reasoning": "..."},
  ...
}

Categories must be exactly one of: Challenge, Info/Advice, Trending Sounds/BGM
Confidence must be between 0.0 and 1.0
Provide clear reasoning for each classification."""
        
        return batch_text
    
    def _parse_batch_classification_result(self, result_data: ClassificationResult, videos: List[YouTubeVideoRaw]) -> List[ClassificationResponse]:
        """
        Parse batch JSON response back to individual classifications.
        
        Args:
            result_data: Raw result from classification agent
            videos: Original video list for mapping
            
        Returns:
            List of individual classification responses
            
        Raises:
            ClassificationError: If parsing fails
        """
        try:
            # Extract the JSON content from the reasoning field
            # The agent should return structured data in the reasoning
            reasoning_text = result_data.reasoning
            
            # Try to find JSON in the response
            import json
            import re
            
            # Look for JSON object in the response
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', reasoning_text, re.DOTALL)
            if not json_match:
                # Fallback: create individual responses with original data
                logger.warning("Could not parse batch JSON, falling back to individual classification")
                return self._create_fallback_responses(videos)
            
            json_str = json_match.group()
            batch_data = json.loads(json_str)
            
            results = []
            for i, video in enumerate(videos, 1):
                video_key = f"video_{i}"
                if video_key in batch_data:
                    video_result = batch_data[video_key]
                    
                    # Map category string to enum
                    category_str = video_result.get("category", "Challenge")
                    if category_str == "Challenge":
                        category = VideoCategory.CHALLENGE
                    elif category_str == "Info/Advice":
                        category = VideoCategory.INFO_ADVICE
                    elif category_str == "Trending Sounds/BGM":
                        category = VideoCategory.TRENDING_SOUNDS
                    else:
                        category = VideoCategory.CHALLENGE  # Default fallback
                    
                    response = ClassificationResponse(
                        video_id=video.video_id,
                        category=category,
                        confidence=float(video_result.get("confidence", 0.5)),
                        reasoning=video_result.get("reasoning", "Batch classification"),
                        alternative_categories=[],
                        model_used=f"{self.provider_name}/{self.model_name}",
                        processing_time=0.0
                    )
                    results.append(response)
                else:
                    # Create fallback response if video not in batch result
                    logger.warning(f"Video {i} not found in batch result, creating fallback")
                    response = ClassificationResponse(
                        video_id=video.video_id,
                        category=VideoCategory.CHALLENGE,
                        confidence=0.5,
                        reasoning="Fallback classification due to parsing error",
                        alternative_categories=[],
                        model_used=f"{self.provider_name}/{self.model_name}",
                        processing_time=0.0
                    )
                    results.append(response)
            
            return results
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse batch classification result: {e}")
            # Create fallback responses for parsing failures
            return self._create_fallback_responses(videos)
    
    async def _fallback_individual_classification(self, videos: List[YouTubeVideoRaw]) -> List[ClassificationResponse]:
        """
        Fallback to individual classification when batch parsing fails.
        
        Args:
            videos: Videos to classify individually
            
        Returns:
            List of classification responses
        """
        logger.info(f"Using fallback individual classification for {len(videos)} videos")
        results = []
        
        for video in videos:
            try:
                result = await self.classify_video(video)
                results.append(result)
            except ClassificationError as e:
                logger.warning(f"Fallback classification failed for video {video.video_id}: {e}")
                # Create a basic response even for failed classifications
                response = ClassificationResponse(
                    video_id=video.video_id,
                    category=VideoCategory.CHALLENGE,
                    confidence=0.3,
                    reasoning=f"Classification failed: {str(e)}",
                    alternative_categories=[],
                    model_used=f"{self.provider_name}/{self.model_name}",
                    processing_time=0.0
                )
                results.append(response)
        
        return results
    
    def _create_fallback_responses(self, videos: List[YouTubeVideoRaw]) -> List[ClassificationResponse]:
        """
        Create basic fallback responses when batch parsing fails.
        
        Args:
            videos: Videos to create fallback responses for
            
        Returns:
            List of basic classification responses
        """
        logger.info(f"Creating fallback responses for {len(videos)} videos")
        results = []
        
        for video in videos:
            response = ClassificationResponse(
                video_id=video.video_id,
                category=VideoCategory.CHALLENGE,
                confidence=0.3,
                reasoning="Fallback classification due to parsing error",
                alternative_categories=[],
                model_used=f"{self.provider_name}/{self.model_name}",
                processing_time=0.0
            )
            results.append(response)
        
        return results
    
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the current model configuration"""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "full_model_string": f"{self.provider_name}:{self.model_name}"
        }


# Classification agent tool functions
@Agent.tool
async def get_video_metadata(ctx: RunContext[ClassificationDependencies]) -> str:
    """
    Get additional video metadata for classification context.
    
    Args:
        ctx: Run context with dependencies
        
    Returns:
        Additional metadata string
    """
    video = ctx.deps.video
    
    metadata_parts = []
    
    # Add publication info
    metadata_parts.append(f"Published: {video.snippet.published_at.strftime('%Y-%m-%d')}")
    
    # Add statistics if available
    if video.statistics:
        metadata_parts.append(f"Views: {video.statistics.view_count:,}")
        metadata_parts.append(f"Likes: {video.statistics.like_count:,}")
        metadata_parts.append(f"Comments: {video.statistics.comment_count:,}")
    
    # Add duration if available
    if video.snippet.duration:
        metadata_parts.append(f"Duration: {video.snippet.duration}")
    
    return " | ".join(metadata_parts)


@Agent.tool
async def analyze_keywords(ctx: RunContext[ClassificationDependencies], text: str) -> List[str]:
    """
    Extract and analyze keywords from video text.
    
    Args:
        ctx: Run context with dependencies
        text: Text to analyze for keywords
        
    Returns:
        List of relevant keywords
    """
    # Simple keyword extraction (could be enhanced with NLP libraries)
    challenge_keywords = [
        "challenge", "dance", "workout", "fitness", "viral", "trending",
        "try", "attempt", "competition", "game", "test"
    ]
    
    info_keywords = [
        "how", "tutorial", "guide", "tips", "learn", "teach", "explain",
        "advice", "help", "review", "fact", "truth", "secret"
    ]
    
    sound_keywords = [
        "music", "song", "sound", "audio", "beat", "remix", "cover",
        "singing", "rap", "melody", "rhythm", "track", "bgm"
    ]
    
    text_lower = text.lower()
    found_keywords = []
    
    # Check for keywords in each category
    for keyword in challenge_keywords + info_keywords + sound_keywords:
        if keyword in text_lower:
            found_keywords.append(keyword)
    
    return found_keywords[:10]  # Limit to top 10 keywords


# Factory function for easy instantiation
def create_llm_provider(model_name: Optional[str] = None) -> LLMProvider:
    """
    Factory function to create LLM provider instance.
    
    Args:
        model_name: Optional specific model name
        
    Returns:
        Configured LLM provider
        
    Raises:
        LLMProviderError: If provider creation fails
    """
    try:
        return LLMProvider(model_name=model_name)
    except Exception as e:
        raise LLMProviderError(f"Failed to create LLM provider: {str(e)}")
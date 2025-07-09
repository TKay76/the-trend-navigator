"""LLM provider interface for cost-effective video classification"""

import logging
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
        Classify a single video using LLM.
        
        Args:
            video: Video to classify
            
        Returns:
            Classification response with category, confidence, and reasoning
            
        Raises:
            ClassificationError: If classification fails
        """
        try:
            logger.debug(f"Classifying video: {video.video_id} - {video.snippet.title}")
            
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
            logger.error(f"Classification failed for video {video.video_id}: {e}")
            raise ClassificationError(f"Failed to classify video {video.video_id}: {str(e)}")
    
    async def classify_videos_batch(self, videos: List[YouTubeVideoRaw]) -> List[ClassificationResponse]:
        """
        Classify multiple videos in batch.
        
        Args:
            videos: List of videos to classify
            
        Returns:
            List of classification responses
        """
        logger.info(f"Starting batch classification of {len(videos)} videos")
        
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
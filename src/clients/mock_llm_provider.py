"""Mock LLM provider for testing and development without real API calls"""

import logging
import asyncio
import json
from typing import List, Dict, Optional
from datetime import datetime

from ..models.video_models import VideoCategory, YouTubeVideoRaw
from ..models.classification_models import ClassificationResponse
from ..core.exceptions import ClassificationError

# Setup logging
logger = logging.getLogger(__name__)


class MockLLMProvider:
    """
    Mock LLM provider that returns predefined classification results.
    Mimics the interface of LLMProvider but doesn't make real API calls.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize mock LLM provider.
        
        Args:
            model_name: Model name (for compatibility, not used in mock)
        """
        self.provider_name = "mock"
        self.model_name = model_name or "mock-model"
        
        # Predefined mock classification data
        self._mock_classifications = self._get_mock_classifications()
        self._classification_counter = 0
        
        logger.info(f"Initialized Mock LLM provider: {self.provider_name}/{self.model_name}")
    
    def _get_mock_classifications(self) -> List[Dict]:
        """
        Get predefined mock classification data similar to collected_videos.json.
        
        Returns:
            List of mock classification results
        """
        return [
            {
                "category": VideoCategory.CHALLENGE,
                "confidence": 0.95,
                "reasoning": "Dance challenge video with viral hashtags and trending choreography",
                "keywords": ["dance", "challenge", "viral", "trending"]
            },
            {
                "category": VideoCategory.INFO_ADVICE,
                "confidence": 0.87,
                "reasoning": "Educational content providing tips and actionable advice",
                "keywords": ["tips", "advice", "how-to", "tutorial"]
            },
            {
                "category": VideoCategory.TRENDING_SOUNDS,
                "confidence": 0.78,
                "reasoning": "Music-focused content featuring trending audio and sound effects",
                "keywords": ["music", "sound", "trending", "audio"]
            },
            {
                "category": VideoCategory.CHALLENGE,
                "confidence": 0.92,
                "reasoning": "Fitness workout challenge encouraging participation",
                "keywords": ["fitness", "workout", "challenge", "exercise"]
            },
            {
                "category": VideoCategory.INFO_ADVICE,
                "confidence": 0.83,
                "reasoning": "Life hack video providing practical solutions",
                "keywords": ["hack", "tips", "solution", "practical"]
            },
            {
                "category": VideoCategory.TRENDING_SOUNDS,
                "confidence": 0.89,
                "reasoning": "Popular song cover with unique vocal interpretation",
                "keywords": ["cover", "song", "music", "vocal"]
            },
            {
                "category": VideoCategory.CHALLENGE,
                "confidence": 0.88,
                "reasoning": "Comedy challenge video with humor and entertainment",
                "keywords": ["comedy", "funny", "challenge", "entertainment"]
            },
            {
                "category": VideoCategory.INFO_ADVICE,
                "confidence": 0.91,
                "reasoning": "Educational tutorial explaining complex concepts simply",
                "keywords": ["tutorial", "education", "explain", "learn"]
            }
        ]
    
    async def classify_video(self, video: YouTubeVideoRaw) -> ClassificationResponse:
        """
        Mock classify a single video.
        
        Args:
            video: Video to classify
            
        Returns:
            Mock classification response
            
        Raises:
            ClassificationError: Occasionally for testing error handling
        """
        # Add small delay to simulate real API call
        await asyncio.sleep(0.1)
        
        logger.debug(f"Mock classifying video: {video.video_id} - {video.snippet.title}")
        
        # Occasionally simulate classification errors (5% chance)
        if self._classification_counter % 20 == 19:
            raise ClassificationError(f"Mock classification failed for video {video.video_id}")
        
        # Get mock classification data (rotate through predefined list)
        mock_data = self._mock_classifications[
            self._classification_counter % len(self._mock_classifications)
        ]
        self._classification_counter += 1
        
        # Enhance reasoning with actual video title for more realistic results
        enhanced_reasoning = f"{mock_data['reasoning']} (Video: '{video.snippet.title[:50]}...')"
        
        response = ClassificationResponse(
            video_id=video.video_id,
            category=mock_data["category"],
            confidence=mock_data["confidence"],
            reasoning=enhanced_reasoning,
            alternative_categories=[],
            model_used=f"{self.provider_name}/{self.model_name}",
            processing_time=0.1
        )
        
        logger.debug(f"Mock classification result: {mock_data['category']} (confidence: {mock_data['confidence']})")
        return response
    
    async def classify_videos_batch_optimized(
        self, 
        videos: List[YouTubeVideoRaw], 
        batch_size: int = 5
    ) -> List[ClassificationResponse]:
        """
        Mock batch classification of videos.
        
        Args:
            videos: List of videos to classify
            batch_size: Batch size for processing (ignored in mock)
            
        Returns:
            List of mock classification responses
            
        Raises:
            ClassificationError: Occasionally for testing error handling
        """
        if not videos:
            return []
        
        logger.info(f"Mock batch classifying {len(videos)} videos")
        
        # Add delay to simulate batch processing
        await asyncio.sleep(0.5)
        
        # Occasionally simulate batch failure (10% chance for batches > 3 videos)
        if len(videos) > 3 and self._classification_counter % 10 == 9:
            self._classification_counter += 1
            raise ClassificationError("Mock batch classification failed - simulating service unavailable")
        
        # Process all videos in the batch
        results = []
        for video in videos:
            try:
                response = await self.classify_video(video)
                results.append(response)
            except ClassificationError:
                # Even for mock, include fallback response for failed individual classifications
                fallback_response = ClassificationResponse(
                    video_id=video.video_id,
                    category=VideoCategory.CHALLENGE,
                    confidence=0.3,
                    reasoning="Mock classification failed - fallback result",
                    alternative_categories=[],
                    model_used=f"{self.provider_name}/{self.model_name}",
                    processing_time=0.1
                )
                results.append(fallback_response)
        
        logger.info(f"Mock batch classification completed: {len(results)} results")
        return results
    
    def get_model_info(self) -> Dict[str, str]:
        """Get information about the mock model configuration"""
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "full_model_string": f"{self.provider_name}:{self.model_name}",
            "type": "mock"
        }
    
    def reset_counter(self) -> None:
        """Reset the classification counter (useful for testing)"""
        self._classification_counter = 0
        logger.debug("Mock LLM provider counter reset")


# Factory function for easy instantiation
def create_mock_llm_provider(model_name: Optional[str] = None) -> MockLLMProvider:
    """
    Factory function to create mock LLM provider instance.
    
    Args:
        model_name: Optional specific model name
        
    Returns:
        Configured mock LLM provider
    """
    return MockLLMProvider(model_name=model_name)
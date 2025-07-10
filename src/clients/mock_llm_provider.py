"""Mock LLM provider for testing and development without real API calls"""

import logging
import asyncio
import json
from typing import List, Dict, Optional, Any
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
    
    async def analyze_youtube_video(self, video_id: str, analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Mock YouTube video analysis that returns sample enhanced analysis data.
        
        Args:
            video_id: YouTube video ID
            analysis_type: Type of analysis ("comprehensive", "challenge", "quick")
            
        Returns:
            Mock analysis response with enhanced data
        """
        # Add small delay to simulate real API call
        await asyncio.sleep(0.2)
        
        logger.debug(f"Mock analyzing YouTube video: {video_id} (type: {analysis_type})")
        
        # Sample mock analysis data based on known video IDs
        mock_analyses = {
            # 댄스 챌린지 관련 Mock 데이터들
            "mock_dance_01": {
                "comprehensive": """
                **Music/Sound Analysis:**
                - Background music: K-pop upbeat track with catchy hooks
                - Viral sounds: "Attention attention" vocal hooks, electronic beats
                - Audio elements: Clear vocals, electronic music, clap sounds
                
                **Challenge Type Classification:**
                - Challenge category: Dance challenge
                - Challenge mechanics: Simple 4-count dance moves, hand gestures and body movements
                - Target audience: K-pop fans, dance beginners, teens and young adults
                
                **Accessibility & Difficulty:**
                - Difficulty level: Easy
                - Required tools: None - just your body and space to move
                - Required space: Small indoor space (2x2 meters)
                - Average person follow along: Yes - designed for beginners
                - Safety considerations: Safe (basic movements)
                
                **Content Details:**
                - Participants: 1 dancer demonstrating
                - Setting: Clean dance studio with mirrors
                - Key visual elements: Clear step-by-step breakdown, slow motion sections
                - Estimated duration: 5-10 minutes to learn
                
                **Trend Analysis:**
                - Viral potential: High (K-pop + easy choreography)
                - Cultural relevance: Current K-pop trend
                - Appeal factors: Catchy music, simple moves, trending artist
                """,
                "challenge": """
                This is an Easy K-pop Dance Challenge.
                Difficulty: Easy - basic moves anyone can follow.
                Requirements: Just your body and small space to dance.
                Music: NewJeans "Attention" - very catchy and trending.
                Accessibility: Perfect for beginners - step by step tutorial.
                Safety: Very safe (simple arm and body movements).
                """
            },
            "mock_dance_02": {
                "comprehensive": """
                **Music/Sound Analysis:**
                - Background music: Trending TikTok audio with electronic beats
                - Viral sounds: Popular TikTok sound bite, rhythmic claps
                - Audio elements: Electronic music, voice instructions, beat drops
                
                **Challenge Type Classification:**
                - Challenge category: Dance challenge
                - Challenge mechanics: Simple TikTok-style dance with 3 main moves
                - Target audience: Social media users, teenagers, beginners
                
                **Accessibility & Difficulty:**
                - Difficulty level: Easy
                - Required tools: Smartphone for recording (optional)
                - Required space: Small room space
                - Average person follow along: Yes - very beginner friendly
                - Safety considerations: Safe (low impact movements)
                
                **Content Details:**
                - Participants: 1 person teaching the dance
                - Setting: Bedroom/home environment
                - Key visual elements: Clear instruction, multiple angles shown
                - Estimated duration: 3-5 minutes to master
                
                **Trend Analysis:**
                - Viral potential: Very high (TikTok algorithm friendly)
                - Cultural relevance: Current social media trends
                - Appeal factors: Quick to learn, shareable, trending audio
                """
            },
            "dWFASBOoh2w": {
                "comprehensive": """
                **Music/Sound Analysis:**
                - Background music: Upbeat electronic music with gaming elements
                - Viral sounds: "tong tong tong" sound effects, repetitive beats
                - Audio elements: Sound effects, electronic music, no vocals
                
                **Challenge Type Classification:**
                - Challenge category: Creative/Animation challenge
                - Challenge mechanics: Create 2D animated ninja battle sequences with fire and ice effects
                - Target audience: Animation enthusiasts, gamers, digital artists
                
                **Accessibility & Difficulty:**
                - Difficulty level: Hard to Expert
                - Required tools: Animation software (After Effects, Adobe Animate), drawing skills
                - Required space: Digital workspace with computer
                - Average person follow along: No - requires specialized animation skills
                - Safety considerations: Safe (digital only)
                
                **Content Details:**
                - Participants: 1 (animator)
                - Setting: Digital animated environment with ninja characters
                - Key visual elements: Fire and ice effects, ninja characters, dynamic battle scenes
                - Estimated duration: Hours to days depending on complexity
                
                **Trend Analysis:**
                - Viral potential: Medium (niche audience but high quality content)
                - Cultural relevance: Gaming and animation communities
                - Appeal factors: Visual effects, gaming aesthetic, short format
                """,
                "challenge": """
                This is a Creative/Animation challenge requiring advanced skills.
                Difficulty: Hard - requires animation software and digital art skills.
                Requirements: Animation software, drawing/design skills, computer setup.
                Music: Electronic gaming music with "tong tong" sound effects.
                Accessibility: Not easily followable for average person - specialized skills needed.
                Safety: Safe (digital creation only).
                """,
                "quick": """
                1. Creative animation challenge featuring ninja battle sequences
                2. Electronic gaming music with repetitive "tong" sound effects  
                3. Very difficult - requires animation software and skills
                4. Animation software, digital art skills, computer setup
                """
            },
            "default": {
                "comprehensive": """
                **Music/Sound Analysis:**
                - Background music: Popular trending audio
                - Viral sounds: Catchy music hooks
                - Audio elements: Music, voice, occasional effects
                
                **Challenge Type Classification:**
                - Challenge category: General challenge content
                - Challenge mechanics: Follow along activity
                - Target audience: General social media users
                
                **Accessibility & Difficulty:**
                - Difficulty level: Medium
                - Required tools: Minimal equipment needed
                - Required space: Small indoor space
                - Average person follow along: Yes
                - Safety considerations: Generally safe
                
                **Content Details:**
                - Participants: 1-2 people
                - Setting: Indoor casual environment
                - Key visual elements: Person demonstrating activity
                - Estimated duration: Few minutes to complete
                
                **Trend Analysis:**
                - Viral potential: High (accessible content)
                - Cultural relevance: Broad appeal
                - Appeal factors: Easy to follow, entertaining
                """
            }
        }
        
        # Get appropriate mock data
        video_data = mock_analyses.get(video_id, mock_analyses["default"])
        analysis_content = video_data.get(analysis_type, video_data.get("comprehensive", "Mock analysis content"))
        
        result = {
            "video_id": video_id,
            "analysis_type": analysis_type,
            "content": analysis_content,
            "success": True
        }
        
        logger.debug(f"Mock video analysis completed for {video_id}")
        return result


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
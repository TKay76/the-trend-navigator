#!/usr/bin/env python3
"""
Test enhanced video analysis with new models
"""

import asyncio
import json
from src.clients.llm_provider import create_llm_provider
from src.models.video_models import (
    ChallengeType, DifficultyLevel, SafetyLevel,
    MusicAnalysis, ChallengeAnalysis, AccessibilityAnalysis,
    ContentDetails, TrendAnalysis, EnhancedVideoAnalysis
)

async def test_enhanced_analysis():
    """Test the enhanced YouTube video analysis"""
    
    print("🚀 Testing Enhanced YouTube Video Analysis")
    print("="*60)
    
    # Create LLM provider
    llm_provider = create_llm_provider()
    
    # Test video from our previous collection
    video_id = "dWFASBOoh2w"  # Build a Queen Run Challenge
    
    try:
        print(f"🎥 Analyzing video: {video_id}")
        print("🤖 Running enhanced analysis...")
        
        # Analyze video with challenge-focused prompt
        result = await llm_provider.analyze_youtube_video(
            video_id=video_id,
            analysis_type="challenge"
        )
        
        print("✅ Analysis completed!")
        print(f"📄 Raw result:\n{result['content']}")
        
        # Test the new models by creating sample data
        print("\n🧪 Testing new data models...")
        
        # Sample enhanced analysis
        sample_music = MusicAnalysis(
            genre="Electronic/Game",
            viral_sounds=["tong tong tong"],
            audio_elements=["sound effects", "repetitive beats"],
            background_music="Upbeat electronic music"
        )
        
        sample_challenge = ChallengeAnalysis(
            challenge_type=ChallengeType.CREATIVE,
            mechanics="Animation creation challenge",
            target_audience="Animation enthusiasts and gamers"
        )
        
        sample_accessibility = AccessibilityAnalysis(
            difficulty_level=DifficultyLevel.HARD,
            required_tools=["Animation software", "Drawing skills"],
            required_space="Digital workspace",
            required_skills=["Animation", "Digital art"],
            easy_to_follow=False,
            safety_level=SafetyLevel.SAFE
        )
        
        sample_content = ContentDetails(
            participants_count=1,
            setting="Digital animated environment",
            key_visual_elements=["Ninja characters", "Fire and ice effects"],
            estimated_duration="Hours to days",
            props_used=["Animation software"]
        )
        
        sample_trend = TrendAnalysis(
            viral_potential="Medium",
            cultural_relevance="Gaming and animation communities",
            appeal_factors=["Visual effects", "Gaming aesthetic"],
            trend_indicators=["Short format", "Gaming theme"]
        )
        
        enhanced_analysis = EnhancedVideoAnalysis(
            video_id=video_id,
            music_analysis=sample_music,
            challenge_analysis=sample_challenge,
            accessibility_analysis=sample_accessibility,
            content_details=sample_content,
            trend_analysis=sample_trend,
            analysis_confidence=0.85,
            raw_analysis_text=result['content']
        )
        
        print("✅ Enhanced analysis model created successfully!")
        print(f"📊 Challenge Type: {enhanced_analysis.challenge_analysis.challenge_type}")
        print(f"⚡ Difficulty: {enhanced_analysis.accessibility_analysis.difficulty_level}")
        print(f"🎵 Viral Sounds: {enhanced_analysis.music_analysis.viral_sounds}")
        print(f"🔒 Safety Level: {enhanced_analysis.accessibility_analysis.safety_level}")
        
        # Convert to JSON to test serialization (serialize datetime fields)
        json_data = enhanced_analysis.model_dump(mode='json')
        print(f"\n📄 JSON serialization successful: {len(json.dumps(json_data))} characters")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_analysis())
    if success:
        print("\n🎉 Enhanced analysis test completed successfully!")
    else:
        print("\n❌ Enhanced analysis test failed!")
        exit(1)
#!/usr/bin/env python3
"""
Test script for YouTube video analysis with Gemini 1.5 Flash
"""

import asyncio
import json
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
google_api_key = os.getenv('GOOGLE_API_KEY')
if not google_api_key:
    print("❌ GOOGLE_API_KEY not found in environment variables")
    print("💡 Please set GOOGLE_API_KEY in your .env file")
    exit(1)

genai.configure(api_key=google_api_key)


def test_youtube_video_analysis():
    """Test YouTube video analysis with Gemini 1.5 Flash"""
    
    # Test with some Korean challenge videos from our previous collection
    test_videos = [
        {
            "video_id": "dWFASBOoh2w",
            "title": "Build a Queen Run Challenge with Tung Tung Tung Sahur",
            "expected": "Animation challenge with viral sound"
        },
        {
            "video_id": "5I7dRmkXWY4", 
            "title": "WHO CAN GET THE COIN CHALLENGE!",
            "expected": "Simple coin-based game challenge"
        },
        {
            "video_id": "P2fnXovqm0A",
            "title": "Try Not to Laugh Challenge 1258 🤣",
            "expected": "Reaction-based entertainment challenge"
        }
    ]
    
    # Initialize Gemini model
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    print("🎥 Testing YouTube Video Analysis with Gemini 1.5 Flash")
    print("="*60)
    
    for i, video in enumerate(test_videos, 1):
        print(f"\n📹 Test {i}: {video['title']}")
        print(f"🔗 Video ID: {video['video_id']}")
        print(f"📝 Expected: {video['expected']}")
        print("-" * 40)
        
        try:
            # Create YouTube URL
            youtube_url = f"https://youtube.com/watch?v={video['video_id']}"
            
            # Enhanced analysis prompt
            prompt = """
            Analyze this YouTube Shorts video and provide detailed information about:

            1. **Music/Sound Analysis:**
               - Background music genre or style
               - Any viral sounds or specific tracks
               - Audio elements (voice, effects, music)

            2. **Challenge Type Classification:**
               - Specific challenge category (dance, food, game, fitness, creative, etc.)
               - Challenge mechanics and rules
               - Target audience

            3. **Accessibility & Difficulty:**
               - Difficulty level (Easy/Medium/Hard)
               - Required tools, materials, or space
               - Can average person easily follow along?
               - Safety considerations

            4. **Content Details:**
               - Number of participants
               - Setting/environment
               - Key visual elements
               - Estimated duration to complete

            5. **Trend Analysis:**
               - Viral potential assessment
               - Cultural relevance
               - Appeal factors

            Please provide a structured JSON response with these categories.
            """
            
            print("🤖 Analyzing video content...")
            
            # Generate content with video
            response = model.generate_content([
                prompt,
                {
                    "mime_type": "video/mp4",
                    "data": youtube_url
                }
            ])
            
            print("✅ Analysis completed!")
            print(f"📊 Response length: {len(response.text)} characters")
            print(f"📄 Analysis result:\n{response.text}")
            
        except Exception as e:
            print(f"❌ Error analyzing video: {e}")
            print(f"🔍 Error type: {type(e).__name__}")
            
            # Try alternative approach with file_data
            try:
                print("🔄 Trying alternative approach...")
                
                response = model.generate_content([
                    genai.protos.Part(
                        file_data=genai.protos.FileData(
                            file_uri=youtube_url
                        )
                    ),
                    genai.protos.Part(text=prompt)
                ])
                
                print("✅ Alternative approach successful!")
                print(f"📄 Analysis result:\n{response.text}")
                
            except Exception as e2:
                print(f"❌ Alternative approach also failed: {e2}")
                continue
        
        print("\n" + "="*60)
        
        # Add delay between requests to respect rate limits
        print("⏳ Waiting 3 seconds before next request...")
        import time
        time.sleep(3)


def test_simple_video_prompt():
    """Test with a simpler prompt first"""
    
    print("\n🧪 Testing Simple Video Analysis")
    print("="*40)
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    video_id = "dWFASBOoh2w"  # Build a Queen Run Challenge
    youtube_url = f"https://youtube.com/watch?v={video_id}"
    
    simple_prompt = "Please describe what you see in this video in 3 sentences."
    
    try:
        print(f"🔗 Analyzing: {youtube_url}")
        print("🤖 Running simple analysis...")
        
        response = model.generate_content([
            simple_prompt,
            youtube_url
        ])
        
        print("✅ Simple analysis successful!")
        print(f"📄 Result: {response.text}")
        
    except Exception as e:
        print(f"❌ Simple analysis failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    print("🚀 Starting YouTube Video Analysis Tests")
    print(f"🔑 Using Google API Key: {google_api_key[:10]}...")
    
    # First try simple test
    if test_simple_video_prompt():
        print("\n" + "="*60)
        print("✅ Simple test passed! Proceeding with detailed analysis...")
        test_youtube_video_analysis()
    else:
        print("❌ Simple test failed. Please check your API key and configuration.")
    
    print("\n🎉 Test completed!")
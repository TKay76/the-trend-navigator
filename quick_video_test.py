#!/usr/bin/env python3
"""
Quick test for YouTube video analysis with Gemini 1.5 Flash
"""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini
google_api_key = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=google_api_key)

def quick_test():
    """Quick test with one video"""
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Test with the Build a Queen Run Challenge video
    video_id = "dWFASBOoh2w"
    youtube_url = f"https://youtube.com/watch?v={video_id}"
    
    prompt = """
    Analyze this YouTube Shorts video and tell me:
    1. What type of challenge is this?
    2. What music/sounds do you hear?
    3. How difficult would this be for a regular person to recreate?
    4. What tools or materials would someone need?
    
    Keep the response concise and practical.
    """
    
    try:
        print(f"🔗 Analyzing: {youtube_url}")
        print("🤖 Running analysis...")
        
        # Try the method that worked in the previous test
        response = model.generate_content([
            genai.protos.Part(
                file_data=genai.protos.FileData(
                    file_uri=youtube_url
                )
            ),
            genai.protos.Part(text=prompt)
        ])
        
        print("✅ Analysis successful!")
        print(f"📄 Result:\n{response.text}")
        return True
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Quick YouTube Video Analysis Test")
    print("="*50)
    quick_test()
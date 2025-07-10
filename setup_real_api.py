#!/usr/bin/env python3
"""
실제 API 설정 도우미
"""

import os
from pathlib import Path

def setup_real_api():
    """실제 API 사용을 위한 설정"""
    
    print("🔧 실제 YouTube API 설정")
    print("=" * 50)
    
    # .env 파일 체크
    env_file = Path(".env")
    if not env_file.exists():
        print("📝 .env 파일이 없습니다. .env.example을 복사해서 생성하겠습니다.")
        
        # .env.example 복사
        with open(".env.example", "r") as f:
            content = f.read()
        
        with open(".env", "w") as f:
            f.write(content)
        
        print("✅ .env 파일 생성 완료!")
    else:
        print("✅ .env 파일이 이미 존재합니다.")
    
    print("\n🔑 API 키 설정이 필요합니다:")
    print("\n1. **YouTube Data API v3 키**")
    print("   📌 https://console.developers.google.com/")
    print("   - Google Cloud Console에서 프로젝트 생성")
    print("   - YouTube Data API v3 활성화")
    print("   - API 키 생성 (IP 제한 권장)")
    
    print("\n2. **Google Generative AI API 키** (비디오 분석용)")
    print("   📌 https://ai.google.dev/")
    print("   - Google AI Studio에서 API 키 생성")
    print("   - Gemini 1.5 Flash 모델 사용")
    
    print("\n3. **.env 파일 수정**")
    print("   다음 항목들을 실제 값으로 변경하세요:")
    print("   ```")
    print("   YOUTUBE_API_KEY=실제_유튜브_API_키")
    print("   LLM_PROVIDER=gemini")
    print("   LLM_API_KEY=실제_구글_AI_API_키")
    print("   LLM_MODEL=gemini-1.5-flash")
    print("   USE_MOCK_LLM=false")
    print("   GOOGLE_API_KEY=실제_구글_AI_API_키")
    print("   ```")
    
    # 현재 .env 상태 확인
    print("\n📋 현재 .env 파일 상태:")
    print("-" * 30)
    
    try:
        with open(".env", "r") as f:
            lines = f.readlines()
        
        key_status = {
            "YOUTUBE_API_KEY": "❌ 미설정",
            "LLM_PROVIDER": "❌ 미설정", 
            "LLM_API_KEY": "❌ 미설정",
            "USE_MOCK_LLM": "❌ 미설정",
            "GOOGLE_API_KEY": "❌ 미설정"
        }
        
        for line in lines:
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                if key in key_status:
                    if value and value != "your_youtube_api_key_here" and value != "your_llm_api_key_here":
                        key_status[key] = "✅ 설정됨"
                    else:
                        key_status[key] = "❌ 기본값"
        
        for key, status in key_status.items():
            print(f"   {key}: {status}")
            
    except Exception as e:
        print(f"   ❌ .env 파일 읽기 오류: {e}")
    
    print("\n⚠️  주의사항:")
    print("   - API 키는 절대 공개하지 마세요!")
    print("   - YouTube API는 일일 할당량이 있습니다 (기본 10,000 단위)")
    print("   - Google AI API도 사용량에 따른 요금이 발생할 수 있습니다")
    
    print("\n🚀 설정 완료 후 실행:")
    print("   python dance_challenge_analyzer.py")
    
    return True

if __name__ == "__main__":
    setup_real_api()
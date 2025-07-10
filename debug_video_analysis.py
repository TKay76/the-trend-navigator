#!/usr/bin/env python3
"""
영상 분석 디버깅 스크립트
"""

import asyncio
import logging
from src.clients.llm_provider import create_llm_provider
import google.generativeai as genai

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def debug_video_analysis():
    """영상 분석 디버깅"""
    
    print("🔍 영상 분석 디버깅")
    print("=" * 50)
    
    # 테스트 비디오
    video_id = "Bq_znt--GTU"
    youtube_url = f"https://youtube.com/watch?v={video_id}"
    
    print(f"🎥 테스트 비디오: {video_id}")
    print(f"🔗 YouTube URL: {youtube_url}")
    
    try:
        # LLM Provider 생성
        llm_provider = create_llm_provider()
        print(f"✅ LLM Provider: {llm_provider.provider_name}")
        
        # Google API 키 확인
        settings = llm_provider.settings
        print(f"🔑 Google API Key 설정됨: {bool(settings.google_api_key and settings.google_api_key != '')}")
        print(f"🔑 API Key 앞 10자: {settings.google_api_key[:10] if settings.google_api_key else 'None'}...")
        
        # 영상 분석 모델 확인
        if hasattr(llm_provider, 'video_analysis_model'):
            print(f"✅ 영상 분석 모델 있음: {type(llm_provider.video_analysis_model)}")
        else:
            print("❌ 영상 분석 모델 없음")
            return
        
        # 직접 Gemini API 테스트
        print("\n🧪 직접 Gemini API 테스트...")
        
        try:
            # 간단한 프롬프트로 테스트
            simple_prompt = "이 YouTube 비디오에 대해 간단히 설명해주세요."
            
            print(f"📝 프롬프트: {simple_prompt}")
            print("⏳ Gemini API 호출 중...")
            
            response = llm_provider.video_analysis_model.generate_content([
                genai.protos.Part(
                    file_data=genai.protos.FileData(
                        file_uri=youtube_url
                    )
                ),
                genai.protos.Part(text=simple_prompt)
            ])
            
            print("✅ Gemini API 응답 받음!")
            
            if hasattr(response, 'text') and response.text:
                print(f"📄 응답 텍스트 길이: {len(response.text)} 문자")
                print(f"📄 응답 내용 (처음 200자):")
                print("-" * 40)
                print(response.text[:200])
                if len(response.text) > 200:
                    print("...")
                print("-" * 40)
            else:
                print("⚠️ 응답 텍스트가 비어있거나 없음")
                print(f"📊 응답 객체: {response}")
                
                # 응답 객체의 속성들 확인
                print("🔍 응답 객체 속성들:")
                for attr in dir(response):
                    if not attr.startswith('_'):
                        try:
                            value = getattr(response, attr)
                            print(f"   {attr}: {type(value)} = {value}")
                        except:
                            print(f"   {attr}: (접근 불가)")
            
        except Exception as e:
            print(f"❌ 직접 API 호출 실패: {e}")
            print(f"❌ 에러 타입: {type(e)}")
            logger.exception("Direct API call failed")
        
        # LLM Provider 메서드 테스트
        print("\n🧪 LLM Provider 메서드 테스트...")
        try:
            result = await llm_provider.analyze_youtube_video(video_id, "quick")
            print(f"📊 LLM Provider 결과: {result}")
        except Exception as e:
            print(f"❌ LLM Provider 메서드 실패: {e}")
            logger.exception("LLM Provider method failed")
            
    except Exception as e:
        print(f"❌ 전체 테스트 실패: {e}")
        logger.exception("Overall test failed")

if __name__ == "__main__":
    asyncio.run(debug_video_analysis())
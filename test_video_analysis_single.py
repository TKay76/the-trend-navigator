#!/usr/bin/env python3
"""
단일 비디오 영상 분석 테스트
"""

import asyncio
import logging
from src.clients.llm_provider import create_llm_provider
from src.core.settings import get_settings

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_single_video_analysis():
    """단일 비디오 영상 분석 테스트"""
    
    print("🎬 단일 비디오 영상 분석 테스트")
    print("=" * 50)
    
    # 테스트할 비디오 ID (최신 리포트에서 가져온 인기 댄스 챌린지)
    test_videos = [
        {
            "video_id": "Bq_znt--GTU",
            "title": "Cha Cha Slide con @LeylaStar ❤️🎉 #trend #tutorial #dance #challenge",
            "channel": "Los Meñiques De La Casa",
            "views": "217,205,732"
        },
        {
            "video_id": "k0rPuyIPXCQ", 
            "title": "Laal Pari #laalpari #ytshorts #shorts #dancetutorial #tutorial #stepbystepdance #housefull5",
            "channel": "3D DANCE ACADEMY JAIPUR",
            "views": "23,160,263"
        }
    ]
    
    try:
        # LLM Provider 생성
        print("🔧 LLM Provider 초기화 중...")
        llm_provider = create_llm_provider()
        print(f"✅ LLM Provider 초기화 완료: {llm_provider.provider_name}/{llm_provider.model_name}")
        
        # 영상 분석 모델 확인
        if hasattr(llm_provider, 'video_analysis_model') and llm_provider.video_analysis_model:
            print("✅ 영상 분석 모델 사용 가능")
        else:
            print("❌ 영상 분석 모델 사용 불가")
            return
        
        # 각 비디오 분석
        for i, video in enumerate(test_videos, 1):
            print(f"\n🎥 비디오 {i}/2 분석 중...")
            print(f"제목: {video['title'][:50]}...")
            print(f"채널: {video['channel']}")
            print(f"조회수: {video['views']}")
            print(f"비디오 ID: {video['video_id']}")
            
            try:
                # 빠른 분석 모드로 테스트
                print("📊 영상 콘텐츠 분석 시작...")
                
                result = await llm_provider.analyze_youtube_video(
                    video_id=video['video_id'],
                    analysis_type="quick"  # 빠른 분석
                )
                
                print("✅ 영상 분석 완료!")
                print(f"📝 분석 결과:")
                print(f"   - 분석 타입: {result.get('analysis_type', 'unknown')}")
                print(f"   - 분석 시간: {result.get('timestamp', 'unknown')}")
                print(f"   - 응답 길이: {len(result.get('raw_response', ''))} 문자")
                
                # 분석 결과 출력 (처음 500자만)
                raw_response = result.get('raw_response', '')
                if raw_response:
                    response_preview = raw_response[:500]
                    print(f"\n📋 분석 내용 (처음 500자):")
                    print("-" * 40)
                    print(response_preview)
                    if len(raw_response) > 500:
                        print("...")
                    print("-" * 40)
                else:
                    print("\n⚠️ 분석 응답이 비어있습니다.")
                
            except Exception as e:
                print(f"❌ 비디오 {video['video_id']} 분석 실패: {e}")
                logger.error(f"Video analysis failed: {e}")
                continue
            
            # 잠시 대기 (API 제한 고려)
            if i < len(test_videos):
                print("⏳ 잠시 대기 중...")
                await asyncio.sleep(2)
        
        print("\n🎉 영상 분석 테스트 완료!")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        logger.error(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_single_video_analysis())
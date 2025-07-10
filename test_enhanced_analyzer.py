#!/usr/bin/env python3
"""
향상된 AnalyzerAgent 비디오 분석 기능 테스트
"""

import asyncio
import json
from datetime import datetime

from src.agents.analyzer_agent import create_analyzer_agent
from src.models.video_models import YouTubeVideoRaw, VideoSnippet, VideoStatistics

async def test_enhanced_analyzer():
    """향상된 AnalyzerAgent 테스트"""
    
    print("🚀 향상된 AnalyzerAgent 테스트 시작")
    print("=" * 60)
    
    # AnalyzerAgent 생성
    analyzer = create_analyzer_agent()
    
    # 테스트용 비디오 데이터 생성 (실제 YouTube 비디오들)
    test_videos = [
        YouTubeVideoRaw(
            video_id="dWFASBOoh2w",
            snippet=VideoSnippet(
                title="Build a Queen Run Challenge",
                description="Amazing ninja battle animation challenge",
                published_at=datetime.now(),
                channel_title="Animation Channel",
                thumbnail_url="https://example.com/thumb1.jpg"
            ),
            statistics=VideoStatistics(
                view_count=12000,
                like_count=800,
                comment_count=150
            )
        ),
        YouTubeVideoRaw(
            video_id="example_tanghulu",
            snippet=VideoSnippet(
                title="탕후루챌린지 따라하기 #탕후루 #challenge",
                description="쉽고 맛있는 탕후루 만들기 챌린지",
                published_at=datetime.now(),
                channel_title="Food Challenge",
                thumbnail_url="https://example.com/thumb2.jpg"
            ),
            statistics=VideoStatistics(
                view_count=45000,
                like_count=2100,
                comment_count=320
            )
        )
    ]
    
    print(f"📊 테스트 데이터: {len(test_videos)}개 비디오")
    
    # 1. 텍스트 기반 분석만 (기존 방식)
    print("\n🔤 텍스트 기반 분석 테스트...")
    text_based_results = await analyzer.classify_videos_with_enhanced_analysis(
        videos=test_videos,
        include_video_content=False
    )
    
    print("✅ 텍스트 기반 분석 완료!")
    for video in text_based_results:
        print(f"  📹 {video.title[:30]}...")
        print(f"     카테고리: {video.category}")
        print(f"     분석 소스: {video.analysis_source}")
        print(f"     비디오 분석 여부: {video.has_video_analysis}")
    
    # 2. 비디오 콘텐츠 분석 포함 (새로운 방식)
    print("\n🎥 비디오 콘텐츠 분석 테스트...")
    video_based_results = await analyzer.classify_videos_with_enhanced_analysis(
        videos=test_videos,
        include_video_content=True
    )
    
    print("✅ 비디오 콘텐츠 분석 완료!")
    for video in video_based_results:
        print(f"\n📹 {video.title}")
        print(f"   카테고리: {video.category}")
        print(f"   분석 소스: {video.analysis_source}")
        print(f"   비디오 분석 여부: {video.has_video_analysis}")
        
        if video.enhanced_analysis:
            ea = video.enhanced_analysis
            print(f"   🎵 음악 장르: {ea.music_analysis.genre}")
            print(f"   🎯 챌린지 타입: {ea.challenge_analysis.challenge_type}")
            print(f"   ⚡ 난이도: {ea.accessibility_analysis.difficulty_level}")
            print(f"   🔒 안전성: {ea.accessibility_analysis.safety_level}")
            print(f"   👥 따라하기 쉬운가: {'예' if ea.accessibility_analysis.easy_to_follow else '아니오'}")
            
            if ea.music_analysis.viral_sounds:
                print(f"   🎶 바이럴 사운드: {ea.music_analysis.viral_sounds}")
            if ea.accessibility_analysis.required_tools:
                print(f"   🛠️  필요한 도구: {ea.accessibility_analysis.required_tools}")
    
    # 3. 분석 통계 확인
    print(f"\n📈 분석 통계:")
    stats = analyzer.get_analysis_stats()
    for key, value in stats.items():
        print(f"   {key}: {value}")
    
    # 4. JSON 직렬화 테스트
    print(f"\n💾 JSON 직렬화 테스트...")
    try:
        for video in video_based_results:
            json_data = video.model_dump(mode='json')
            json_size = len(json.dumps(json_data))
            print(f"   📄 {video.video_id}: {json_size} 문자")
        print("✅ JSON 직렬화 성공!")
    except Exception as e:
        print(f"❌ JSON 직렬화 실패: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_enhanced_analyzer())
    if success:
        print("\n🎉 향상된 AnalyzerAgent 테스트 성공!")
    else:
        print("\n❌ 향상된 AnalyzerAgent 테스트 실패!")
        exit(1)
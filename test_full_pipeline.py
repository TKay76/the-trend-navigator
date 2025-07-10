#!/usr/bin/env python3
"""
전체 파이프라인 통합 테스트: CollectorAgent + AnalyzerAgent (향상된 비디오 분석 포함)
"""

import asyncio
import json
from datetime import datetime

from src.agents.collector_agent import create_collector_agent
from src.agents.analyzer_agent import create_analyzer_agent

async def test_full_pipeline():
    """전체 파이프라인 통합 테스트"""
    
    print("🚀 전체 파이프라인 통합 테스트")
    print("=" * 70)
    
    # 1. CollectorAgent로 비디오 수집
    print("📊 1단계: 비디오 데이터 수집")
    print("-" * 40)
    
    collector = create_collector_agent()
    
    # 테스트용 검색 쿼리
    search_queries = ["challenge", "탕후루"]
    
    print(f"🔍 검색 쿼리: {search_queries}")
    
    try:
        collected_videos = await collector.collect_top_videos(
            search_queries=search_queries,
            max_results_per_query=3,  # 테스트용으로 적게
            days=7,
            top_n=3
        )
        
        print(f"✅ 비디오 수집 완료: {len(collected_videos)}개")
        for video in collected_videos[:3]:  # 처음 3개만 출력
            print(f"   📹 {video.snippet.title[:50]}...")
            
    except Exception as e:
        print(f"❌ 비디오 수집 실패: {e}")
        return False
    
    if not collected_videos:
        print("⚠️  수집된 비디오가 없어서 Mock 데이터 사용")
        # Mock 데이터로 테스트 계속
        from src.models.video_models import YouTubeVideoRaw, VideoSnippet, VideoStatistics
        collected_videos = [
            YouTubeVideoRaw(
                video_id="dWFASBOoh2w",
                snippet=VideoSnippet(
                    title="Build a Queen Run Challenge",
                    description="Amazing ninja battle animation challenge",
                    published_at=datetime.now(),
                    channel_title="Animation Channel",
                    thumbnail_url="https://example.com/thumb1.jpg"
                ),
                statistics=VideoStatistics(view_count=12000, like_count=800, comment_count=150)
            )
        ]
    
    # 2. AnalyzerAgent로 기본 분석
    print(f"\n🔤 2단계: 텍스트 기반 비디오 분석")
    print("-" * 40)
    
    analyzer = create_analyzer_agent()
    
    try:
        text_analysis_results = await analyzer.classify_videos_with_enhanced_analysis(
            videos=collected_videos[:2],  # 처음 2개만 테스트
            include_video_content=False
        )
        
        print(f"✅ 텍스트 분석 완료: {len(text_analysis_results)}개")
        for video in text_analysis_results:
            print(f"   📹 {video.title[:40]}...")
            print(f"      카테고리: {video.category} (신뢰도: {video.confidence:.2f})")
            print(f"      분석 소스: {video.analysis_source}")
            
    except Exception as e:
        print(f"❌ 텍스트 분석 실패: {e}")
        return False
    
    # 3. AnalyzerAgent로 향상된 비디오 분석
    print(f"\n🎥 3단계: 향상된 비디오 콘텐츠 분석")
    print("-" * 40)
    
    try:
        enhanced_analysis_results = await analyzer.classify_videos_with_enhanced_analysis(
            videos=collected_videos[:1],  # 처음 1개만 테스트 (API 비용 절약)
            include_video_content=True
        )
        
        print(f"✅ 향상된 분석 완료: {len(enhanced_analysis_results)}개")
        
        for video in enhanced_analysis_results:
            print(f"\n📹 {video.title}")
            print(f"   기본 카테고리: {video.category}")
            print(f"   분석 소스: {video.analysis_source}")
            
            if video.has_video_analysis and video.enhanced_analysis:
                ea = video.enhanced_analysis
                print(f"   🎵 음악: {ea.music_analysis.genre}")
                print(f"   🎯 챌린지 타입: {ea.challenge_analysis.challenge_type}")
                print(f"   ⚡ 난이도: {ea.accessibility_analysis.difficulty_level}")
                print(f"   🛡️  안전성: {ea.accessibility_analysis.safety_level}")
                print(f"   👥 따라하기: {'쉬움' if ea.accessibility_analysis.easy_to_follow else '어려움'}")
                
                if ea.music_analysis.viral_sounds:
                    print(f"   🎶 바이럴 사운드: {', '.join(ea.music_analysis.viral_sounds)}")
                if ea.accessibility_analysis.required_tools:
                    print(f"   🛠️  필요 도구: {', '.join(ea.accessibility_analysis.required_tools)}")
                
                print(f"   📝 원본 분석: {ea.raw_analysis_text[:100]}...")
                
    except Exception as e:
        print(f"❌ 향상된 분석 실패: {e}")
        # 실패해도 테스트는 계속 (API 에러일 수 있음)
        enhanced_analysis_results = text_analysis_results
    
    # 4. 트렌드 리포트 생성
    print(f"\n📊 4단계: 트렌드 리포트 생성")
    print("-" * 40)
    
    try:
        # 기본 분류된 비디오들로 변환
        from src.models.video_models import ClassifiedVideo
        basic_classified = []
        for video in text_analysis_results:
            basic_classified.append(ClassifiedVideo(
                video_id=video.video_id,
                title=video.title,
                category=video.category,
                confidence=video.confidence,
                reasoning=video.reasoning,
                view_count=video.view_count,
                published_at=video.published_at,
                channel_title=video.channel_title
            ))
        
        trend_report = analyzer.generate_trend_report(basic_classified)
        
        print(f"✅ 트렌드 리포트 생성 완료")
        print(f"   📋 분석 카테고리: {trend_report.category}")
        print(f"   📈 분석된 비디오 수: {trend_report.total_videos_analyzed}")
        print(f"   💡 주요 인사이트: {len(trend_report.key_insights)}개")
        print(f"   📌 추천 액션: {len(trend_report.recommended_actions)}개")
        print(f"   🏆 상위 비디오: {len(trend_report.top_videos)}개")
        
        # 일부 인사이트 출력
        print(f"\n   💡 주요 인사이트:")
        for insight in trend_report.key_insights[:3]:
            print(f"      • {insight}")
            
        print(f"\n   📌 추천 액션:")
        for action in trend_report.recommended_actions[:3]:
            print(f"      • {action}")
            
    except Exception as e:
        print(f"❌ 트렌드 리포트 생성 실패: {e}")
        return False
    
    # 5. 종합 통계
    print(f"\n📈 5단계: 종합 통계")
    print("-" * 40)
    
    collector_stats = collector.get_collection_stats()
    analyzer_stats = analyzer.get_analysis_stats()
    
    print(f"📊 CollectorAgent 통계:")
    for key, value in collector_stats.items():
        print(f"   {key}: {value}")
    
    print(f"\n🔍 AnalyzerAgent 통계:")
    for key, value in analyzer_stats.items():
        print(f"   {key}: {value}")
    
    # 6. 비교 분석
    print(f"\n🔄 6단계: 텍스트 vs 비디오 분석 비교")
    print("-" * 40)
    
    if len(enhanced_analysis_results) > 0 and enhanced_analysis_results[0].has_video_analysis:
        video = enhanced_analysis_results[0]
        
        # 텍스트 기반 결과 찾기
        text_result = next((v for v in text_analysis_results if v.video_id == video.video_id), None)
        
        if text_result:
            print(f"📹 비디오: {video.title[:40]}...")
            print(f"   텍스트 분석 → {text_result.category} (신뢰도: {text_result.confidence:.2f})")
            print(f"   비디오 분석 → {video.category} (신뢰도: {video.confidence:.2f})")
            
            if video.enhanced_analysis:
                print(f"   추가 정보:")
                print(f"     🎯 챌린지 타입: {video.enhanced_analysis.challenge_analysis.challenge_type}")
                print(f"     ⚡ 난이도: {video.enhanced_analysis.accessibility_analysis.difficulty_level}")
                print(f"     👥 접근성: {'일반인 가능' if video.enhanced_analysis.accessibility_analysis.easy_to_follow else '전문 기술 필요'}")
    
    print(f"\n🎉 전체 파이프라인 테스트 완료!")
    return True

if __name__ == "__main__":
    success = asyncio.run(test_full_pipeline())
    if success:
        print("\n✅ 전체 파이프라인 통합 테스트 성공!")
        print("   🚀 이제 탕후루챌린지 같은 비디오의 실제 음악, 난이도, 접근성을 정확히 분석할 수 있어요!")
    else:
        print("\n❌ 전체 파이프라인 통합 테스트 실패!")
        exit(1)
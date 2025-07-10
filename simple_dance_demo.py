#!/usr/bin/env python3
"""
간단한 댄스 챌린지 데모 - Mock 데이터만 사용
"""

import asyncio
import json
from datetime import datetime

from src.agents.analyzer_agent import create_analyzer_agent
from src.models.video_models import YouTubeVideoRaw, VideoSnippet, VideoStatistics

async def demo_dance_challenge_analysis():
    """댄스 챌린지 분석 데모"""
    
    print("🕺 댄스 챌린지 분석 데모")
    print("=" * 50)
    
    # Mock 댄스 챌린지 데이터 생성
    dance_videos = [
        YouTubeVideoRaw(
            video_id="mock_dance_01",
            snippet=VideoSnippet(
                title="Easy K-pop Dance Challenge - NewJeans Attention",
                description="Learn this easy dance challenge step by step! Perfect for beginners. #dance #challenge #easy #kpop",
                published_at=datetime.now(),
                channel_title="KpopDanceStudio",
                thumbnail_url="https://example.com/dance1.jpg"
            ),
            statistics=VideoStatistics(view_count=150000, like_count=8000, comment_count=600)
        ),
        YouTubeVideoRaw(
            video_id="mock_dance_02", 
            snippet=VideoSnippet(
                title="Simple TikTok Dance Anyone Can Do",
                description="Super easy TikTok dance tutorial for everyone! #tiktok #dance #simple #viral",
                published_at=datetime.now(),
                channel_title="TikTokDancer",
                thumbnail_url="https://example.com/dance2.jpg"
            ),
            statistics=VideoStatistics(view_count=200000, like_count=12000, comment_count=800)
        ),
        YouTubeVideoRaw(
            video_id="mock_dance_03",
            snippet=VideoSnippet(
                title="댄스 챌린지 - 쉬운 안무 따라하기",
                description="누구나 쉽게 따라할 수 있는 댄스 챌린지! #댄스 #챌린지 #쉬운안무",
                published_at=datetime.now(),
                channel_title="한국댄스스튜디오",
                thumbnail_url="https://example.com/dance3.jpg"
            ),
            statistics=VideoStatistics(view_count=120000, like_count=6500, comment_count=450)
        )
    ]
    
    print(f"📊 분석할 댄스 비디오: {len(dance_videos)}개")
    
    # Analyzer Agent 생성
    analyzer = create_analyzer_agent()
    
    # 향상된 분석 수행
    print("\n🎥 향상된 비디오 분석 중...")
    analyzed_videos = await analyzer.classify_videos_with_enhanced_analysis(
        videos=dance_videos,
        include_video_content=True  # Mock 데이터로 비디오 분석 시뮬레이션
    )
    
    print("\n✅ 분석 완료! 결과:")
    print("-" * 50)
    
    dance_count = 0
    for i, video in enumerate(analyzed_videos, 1):
        print(f"\n{i}. {video.title}")
        print(f"   📺 조회수: {video.view_count:,}")
        print(f"   📊 카테고리: {video.category}")
        print(f"   🎯 신뢰도: {video.confidence:.2f}")
        print(f"   📱 분석 소스: {video.analysis_source}")
        
        if video.enhanced_analysis:
            ea = video.enhanced_analysis
            print(f"   🎵 음악 장르: {ea.music_analysis.genre}")
            print(f"   💃 챌린지 타입: {ea.challenge_analysis.challenge_type}")
            print(f"   ⚡ 난이도: {ea.accessibility_analysis.difficulty_level}")
            print(f"   👥 따라하기: {'쉬움' if ea.accessibility_analysis.easy_to_follow else '어려움'}")
            print(f"   🛡️  안전성: {ea.accessibility_analysis.safety_level}")
            
            if ea.music_analysis.viral_sounds:
                print(f"   🎶 바이럴 사운드: {', '.join(ea.music_analysis.viral_sounds)}")
            
            # 댄스 챌린지 카운트
            if ea.challenge_analysis.challenge_type.value == "Dance":
                dance_count += 1
                print("   ✅ 댄스 챌린지 확인!")
        
        print(f"   📝 분석 이유: {video.reasoning[:100]}...")
    
    print(f"\n🎉 총 {dance_count}개의 댄스 챌린지 발견!")
    
    # 간단한 리포트 생성
    if dance_count > 0:
        print(f"\n📊 댄스 챌린지 트렌드 리포트")
        print("-" * 30)
        
        total_views = sum(v.view_count or 0 for v in analyzed_videos)
        avg_views = total_views / len(analyzed_videos)
        
        print(f"총 조회수: {total_views:,}")
        print(f"평균 조회수: {avg_views:,.0f}")
        
        # 음악 장르 분석
        genres = []
        for video in analyzed_videos:
            if video.enhanced_analysis and video.enhanced_analysis.music_analysis.genre:
                genres.append(video.enhanced_analysis.music_analysis.genre)
        
        if genres:
            from collections import Counter
            genre_counts = Counter(genres)
            print(f"인기 음악 장르: {genre_counts.most_common(1)[0][0]}")
        
        print(f"\n💡 트렌드 인사이트:")
        print(f"• K-pop과 TikTok 댄스가 주요 트렌드")
        print(f"• 쉽고 따라하기 좋은 안무가 인기")
        print(f"• 초보자 친화적인 튜토리얼 선호")
        print(f"• 단순한 동작으로 구성된 챌린지 확산")
        
        print(f"\n📌 콘텐츠 제작 추천:")
        print(f"• 3-5개의 간단한 동작으로 구성")
        print(f"• 트렌딩 K-pop 음악 활용")  
        print(f"• 단계별 튜토리얼 제공")
        print(f"• #dance #challenge #easy 해시태그 활용")
    
    return analyzed_videos

def save_demo_report(analyzed_videos, genres):
    """데모 리포트를 JSON과 Markdown으로 저장"""
    
    # 리포트 데이터 생성
    total_views = sum(v.view_count or 0 for v in analyzed_videos)
    avg_views = total_views / len(analyzed_videos) if analyzed_videos else 0
    
    report = {
        "summary": f"댄스 챌린지 분석 데모 결과 TOP {len(analyzed_videos)}",
        "total_found": len(analyzed_videos),
        "total_views": total_views,
        "average_views": avg_views,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "challenges": [],
        "trends": [
            f"총 조회수: {total_views:,}",
            f"평균 조회수: {avg_views:,.0f}",
            "K-pop과 TikTok 댄스가 주요 트렌드",
            "쉽고 따라하기 좋은 안무가 인기"
        ],
        "recommendations": [
            "3-5개의 간단한 동작으로 구성",
            "트렌딩 K-pop 음악 활용",
            "단계별 튜토리얼 제공",
            "#dance #challenge #easy 해시태그 활용"
        ]
    }
    
    # 챌린지 정보 추가
    for i, video in enumerate(analyzed_videos, 1):
        challenge_info = {
            "rank": i,
            "title": video.title,
            "video_id": video.video_id,
            "views": video.view_count or 0,
            "channel": video.channel_title,
            "confidence": video.confidence
        }
        
        if video.enhanced_analysis:
            ea = video.enhanced_analysis
            challenge_info.update({
                "music_genre": ea.music_analysis.genre,
                "difficulty": ea.accessibility_analysis.difficulty_level.value,
                "easy_to_follow": ea.accessibility_analysis.easy_to_follow,
                "required_tools": ea.accessibility_analysis.required_tools,
                "viral_sounds": ea.music_analysis.viral_sounds
            })
        
        report["challenges"].append(challenge_info)
    
    # 파일 저장
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # JSON 저장
    json_filename = f"dance_demo_report_{timestamp}.json"
    with open(json_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    # Markdown 저장 (dance_challenge_analyzer의 함수 사용)
    from dance_challenge_analyzer import generate_markdown_report
    md_filename = f"dance_demo_report_{timestamp}.md"
    markdown_content = generate_markdown_report(report)
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"\n💾 데모 리포트가 저장되었습니다:")
    print(f"  📄 JSON: {json_filename}")
    print(f"  📝 Markdown: {md_filename}")
    
    return json_filename, md_filename

if __name__ == "__main__":
    result = asyncio.run(demo_dance_challenge_analysis())
    
    # 장르 정보 수집
    genres = []
    for video in result:
        if video.enhanced_analysis and video.enhanced_analysis.music_analysis.genre:
            genres.append(video.enhanced_analysis.music_analysis.genre)
    
    # 리포트 저장
    json_file, md_file = save_demo_report(result, genres)
    
    print(f"\n🎊 데모 완료! {len(result)}개 비디오 분석됨")
    print(f"📝 자세한 내용은 {md_file}에서 확인하세요!")
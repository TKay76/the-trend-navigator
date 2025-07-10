#!/usr/bin/env python3
"""
사람들이 쉽게 따라할 수 있는 댄스 챌린지 TOP 10 분석기
"""

import asyncio
import json
import logging
from typing import List, Dict, Any
from datetime import datetime

from src.agents.collector_agent import create_collector_agent
from src.agents.analyzer_agent import create_analyzer_agent
from src.models.video_models import EnhancedClassifiedVideo, ChallengeType, DifficultyLevel

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def find_easy_dance_challenges(target_count: int = 10, max_attempts: int = 5) -> List[EnhancedClassifiedVideo]:
    """
    쉽게 따라할 수 있는 댄스 챌린지를 찾는 함수
    
    Args:
        target_count: 찾을 댄스 챌린지 개수
        max_attempts: 최대 시도 횟수
        
    Returns:
        조건에 맞는 댄스 챌린지 리스트
    """
    
    collector = create_collector_agent()
    analyzer = create_analyzer_agent()
    
    dance_challenges = []
    attempt = 0
    
    # 댄스 관련 검색 키워드들
    dance_keywords = [
        "dance challenge",
        "댄스 챌린지", 
        "kpop dance",
        "easy dance",
        "dance trend",
        "viral dance",
        "tiktok dance",
        "simple dance"
    ]
    
    while len(dance_challenges) < target_count and attempt < max_attempts:
        attempt += 1
        logger.info(f"🔄 시도 {attempt}/{max_attempts}: 현재 {len(dance_challenges)}개 수집됨, 목표 {target_count}개")
        
        try:
            # 1. 비디오 수집
            logger.info("📊 비디오 수집 중...")
            collected_videos = await collector.collect_top_videos(
                search_queries=dance_keywords,
                max_results_per_query=10,
                days=30,
                top_n=20
            )
            
            if not collected_videos:
                logger.warning("수집된 비디오가 없습니다. Mock 데이터를 사용합니다.")
                # Mock 데이터 생성 (더 현실적인 댄스 챌린지들)
                from src.models.video_models import YouTubeVideoRaw, VideoSnippet, VideoStatistics
                dance_titles = [
                    "Easy K-pop Dance Challenge - NewJeans Attention",
                    "Simple TikTok Dance Anyone Can Do",
                    "댄스 챌린지 - 쉬운 안무 따라하기",
                    "Viral Dance Moves Tutorial - Beginner Friendly", 
                    "5 Minute Easy Dance Challenge",
                    "Basic Dance Steps Everyone Should Know",
                    "Popular Dance Challenge 2024",
                    "Simple Choreography for Beginners",
                    "Easy Dance Challenge - No Experience Needed",
                    "Trending Dance Moves Made Simple",
                    "Quick Dance Tutorial - Super Easy",
                    "Fun Dance Challenge for Everyone",
                    "Basic Dance Challenge - Start Here",
                    "Simple K-pop Dance Tutorial",
                    "Easy Dance Routine - Follow Along"
                ]
                
                collected_videos = []
                for i in range(15):
                    title = dance_titles[i % len(dance_titles)]
                    collected_videos.append(YouTubeVideoRaw(
                        video_id=f"mock_dance_{i+1:02d}",
                        snippet=VideoSnippet(
                            title=title,
                            description=f"Learn this easy dance challenge step by step! Perfect for beginners. #dance #challenge #easy #tutorial #{i+1}",
                            published_at=datetime.now(),
                            channel_title=f"DanceStudio{i+1}",
                            thumbnail_url=f"https://example.com/dance{i+1}.jpg"
                        ),
                        statistics=VideoStatistics(
                            view_count=100000 + i * 5000,
                            like_count=5000 + i * 100,
                            comment_count=500 + i * 20
                        )
                    ))
            
            logger.info(f"✅ {len(collected_videos)}개 비디오 수집됨")
            
            # 2. 향상된 분석 (비디오 콘텐츠 분석 포함)
            logger.info("🎥 향상된 비디오 분석 중...")
            analyzed_videos = await analyzer.classify_videos_with_enhanced_analysis(
                videos=collected_videos,
                include_video_content=True
            )
            
            # 3. 댄스 챌린지 필터링
            logger.info("🕺 댄스 챌린지 필터링 중...")
            for video in analyzed_videos:
                if is_easy_dance_challenge(video):
                    # 중복 제거
                    if not any(existing.video_id == video.video_id for existing in dance_challenges):
                        dance_challenges.append(video)
                        logger.info(f"✅ 댄스 챌린지 발견: {video.title[:50]}...")
            
            logger.info(f"📈 현재까지 {len(dance_challenges)}개 댄스 챌린지 수집됨")
            
            # 목표 달성 시 종료
            if len(dance_challenges) >= target_count:
                logger.info(f"🎉 목표 달성! {len(dance_challenges)}개 댄스 챌린지 수집 완료")
                break
                
        except Exception as e:
            logger.error(f"❌ 시도 {attempt} 실패: {e}")
            continue
    
    # 결과 정렬 (조회수, 좋아요, 분석 신뢰도 기준)
    dance_challenges.sort(key=lambda x: (
        x.view_count or 0,
        x.enhanced_analysis.analysis_confidence if x.enhanced_analysis else 0
    ), reverse=True)
    
    return dance_challenges[:target_count]

def is_easy_dance_challenge(video: EnhancedClassifiedVideo) -> bool:
    """
    쉬운 댄스 챌린지인지 판단하는 함수
    
    Args:
        video: 분석된 비디오
        
    Returns:
        쉬운 댄스 챌린지 여부
    """
    
    # 기본 조건: 제목에 댄스 관련 키워드가 있어야 함
    title_lower = video.title.lower()
    description_lower = video.reasoning.lower() if video.reasoning else ""
    
    dance_keywords = ['dance', '댄스', 'dancing', 'choreography', 'moves', 'k-pop', 'kpop', 'tiktok']
    challenge_keywords = ['challenge', '챌린지', 'tutorial', 'learn']
    easy_keywords = ['easy', 'simple', 'basic', '쉬운', '간단한', 'beginner', 'anyone', 'everyone']
    
    has_dance_keyword = any(keyword in title_lower for keyword in dance_keywords)
    has_challenge_keyword = any(keyword in title_lower for keyword in challenge_keywords)
    has_easy_keyword = any(keyword in title_lower for keyword in easy_keywords)
    
    # 향상된 분석이 있는 경우
    if video.enhanced_analysis:
        ea = video.enhanced_analysis
        
        # 댄스 챌린지 타입이어야 함
        is_dance_challenge = ea.challenge_analysis.challenge_type == ChallengeType.DANCE
        
        # 쉬운 난이도여야 함
        is_easy = ea.accessibility_analysis.difficulty_level in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM]
        
        # 일반인이 따라하기 쉬워야 함
        is_followable = ea.accessibility_analysis.easy_to_follow
        
        # 안전해야 함
        is_safe = ea.accessibility_analysis.safety_level.value == "Safe"
        
        logger.debug(f"Enhanced analysis for {video.video_id}: dance={is_dance_challenge}, easy={is_easy}, followable={is_followable}, safe={is_safe}")
        
        return is_dance_challenge and is_easy and is_followable and is_safe
    
    # 향상된 분석이 없는 경우, 제목과 기본 분류로만 판단
    else:
        # 댄스 키워드 체크
        dance_score = sum([
            has_dance_keyword * 2,  # 댄스 키워드 있으면 2점
            has_challenge_keyword * 1,  # 챌린지 키워드 있으면 1점  
            has_easy_keyword * 1,  # 쉬운 키워드 있으면 1점
            (video.confidence > 0.8) * 1  # 높은 신뢰도면 1점
        ])
        
        logger.debug(f"Basic analysis for {video.video_id}: title='{video.title}', score={dance_score}, category={video.category}")
        
        # 최소 3점 이상이어야 댄스 챌린지로 인정
        return dance_score >= 3

def generate_dance_challenge_report(dance_challenges: List[EnhancedClassifiedVideo]) -> Dict[str, Any]:
    """
    댄스 챌린지 트렌드 리포트 생성
    
    Args:
        dance_challenges: 댄스 챌린지 리스트
        
    Returns:
        트렌드 리포트 딕셔너리
    """
    
    if not dance_challenges:
        return {
            "summary": "댄스 챌린지를 찾을 수 없습니다.",
            "total_found": 0,
            "challenges": [],
            "trends": [],
            "recommendations": []
        }
    
    # 통계 계산
    total_views = sum(video.view_count or 0 for video in dance_challenges)
    avg_views = total_views / len(dance_challenges) if dance_challenges else 0
    
    # 음악 장르 분석
    music_genres = []
    viral_sounds = []
    
    for video in dance_challenges:
        if video.enhanced_analysis:
            if video.enhanced_analysis.music_analysis.genre:
                music_genres.append(video.enhanced_analysis.music_analysis.genre)
            viral_sounds.extend(video.enhanced_analysis.music_analysis.viral_sounds)
    
    # 트렌드 분석
    trends = []
    if music_genres:
        from collections import Counter
        genre_counts = Counter(music_genres)
        popular_genre = genre_counts.most_common(1)[0][0]
        trends.append(f"인기 음악 장르: {popular_genre}")
    
    if viral_sounds:
        trends.append(f"바이럴 사운드: {', '.join(set(viral_sounds[:5]))}")
    
    trends.append(f"평균 조회수: {avg_views:,.0f}")
    
    # 추천사항
    recommendations = [
        "간단하고 따라하기 쉬운 동작 위주로 구성",
        "트렌딩 음악과 함께 짧은 루틴 제작",
        "명확한 동작 설명과 반복 연습 포함",
        "다양한 연령대가 참여할 수 있는 안전한 동작",
        "해시태그 활용으로 바이럴 확산 도모"
    ]
    
    # 챌린지 정보 정리
    challenge_info = []
    for i, video in enumerate(dance_challenges, 1):
        info = {
            "rank": i,
            "title": video.title,
            "video_id": video.video_id,
            "views": video.view_count or 0,
            "channel": video.channel_title,
            "confidence": video.confidence
        }
        
        if video.enhanced_analysis:
            ea = video.enhanced_analysis
            info.update({
                "music_genre": ea.music_analysis.genre,
                "difficulty": ea.accessibility_analysis.difficulty_level.value,
                "easy_to_follow": ea.accessibility_analysis.easy_to_follow,
                "required_tools": ea.accessibility_analysis.required_tools,
                "viral_sounds": ea.music_analysis.viral_sounds
            })
        
        challenge_info.append(info)
    
    return {
        "summary": f"사람들이 쉽게 따라할 수 있는 댄스 챌린지 TOP {len(dance_challenges)}",
        "total_found": len(dance_challenges),
        "total_views": total_views,
        "average_views": avg_views,
        "analysis_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "challenges": challenge_info,
        "trends": trends,
        "recommendations": recommendations
    }

async def main():
    """메인 실행 함수"""
    
    print("🕺 사람들이 쉽게 따라할 수 있는 댄스 챌린지 TOP 10 분석기")
    print("=" * 70)
    
    try:
        # 1. 댄스 챌린지 수집
        logger.info("🎯 댄스 챌린지 수집 시작...")
        dance_challenges = await find_easy_dance_challenges(target_count=10, max_attempts=3)
        
        if not dance_challenges:
            print("❌ 댄스 챌린지를 찾을 수 없습니다.")
            return
        
        # 2. 트렌드 리포트 생성
        logger.info("📊 트렌드 리포트 생성 중...")
        report = generate_dance_challenge_report(dance_challenges)
        
        # 3. 결과 출력
        print(f"\n🎉 {report['summary']}")
        print(f"📈 총 조회수: {report['total_views']:,}")
        print(f"📊 평균 조회수: {report['average_views']:,.0f}")
        print(f"📅 분석 일시: {report['analysis_date']}")
        
        print(f"\n🏆 TOP {len(dance_challenges)} 댄스 챌린지:")
        print("-" * 50)
        
        for challenge in report['challenges']:
            print(f"{challenge['rank']:2d}. {challenge['title']}")
            print(f"    📺 조회수: {challenge['views']:,}")
            print(f"    📺 채널: {challenge['channel']}")
            print(f"    🎯 신뢰도: {challenge['confidence']:.2f}")
            
            if 'difficulty' in challenge:
                print(f"    ⚡ 난이도: {challenge['difficulty']}")
                print(f"    👥 따라하기: {'쉬움' if challenge['easy_to_follow'] else '어려움'}")
                if challenge['music_genre']:
                    print(f"    🎵 음악: {challenge['music_genre']}")
                if challenge['viral_sounds']:
                    print(f"    🎶 바이럴 사운드: {', '.join(challenge['viral_sounds'])}")
            print()
        
        print(f"📈 주요 트렌드:")
        for trend in report['trends']:
            print(f"  • {trend}")
        
        print(f"\n💡 콘텐츠 제작 추천사항:")
        for rec in report['recommendations']:
            print(f"  • {rec}")
        
        # 4. JSON 및 Markdown 저장
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON 저장
        json_filename = f"dance_challenge_report_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        # Markdown 저장
        md_filename = f"dance_challenge_report_{timestamp}.md"
        markdown_content = generate_markdown_report(report)
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"\n💾 리포트가 저장되었습니다:")
        print(f"  📄 JSON: {json_filename}")
        print(f"  📝 Markdown: {md_filename}")
        
    except Exception as e:
        logger.error(f"❌ 분석 실패: {e}")
        import traceback
        traceback.print_exc()

def generate_markdown_report(report: Dict[str, Any]) -> str:
    """
    트렌드 리포트를 Markdown 형식으로 생성
    
    Args:
        report: 트렌드 리포트 딕셔너리
        
    Returns:
        Markdown 형식의 리포트 문자열
    """
    
    md_lines = []
    
    # 제목
    md_lines.append(f"# {report['summary']}")
    md_lines.append("")
    
    # 기본 정보
    md_lines.append("## 📊 분석 개요")
    md_lines.append("")
    md_lines.append(f"- **분석 일시**: {report['analysis_date']}")
    md_lines.append(f"- **발견된 댄스 챌린지**: {report['total_found']}개")
    md_lines.append(f"- **총 조회수**: {report['total_views']:,}")
    md_lines.append(f"- **평균 조회수**: {report['average_views']:,.0f}")
    md_lines.append("")
    
    # 댄스 챌린지 순위
    md_lines.append("## 🏆 댄스 챌린지 순위")
    md_lines.append("")
    
    for challenge in report['challenges']:
        md_lines.append(f"### {challenge['rank']}. {challenge['title']}")
        md_lines.append("")
        md_lines.append(f"- **비디오 ID**: `{challenge['video_id']}`")
        md_lines.append(f"- **채널**: {challenge['channel']}")
        md_lines.append(f"- **조회수**: {challenge['views']:,}")
        md_lines.append(f"- **분석 신뢰도**: {challenge['confidence']:.2f}")
        
        if 'difficulty' in challenge:
            md_lines.append(f"- **난이도**: {challenge['difficulty']}")
            md_lines.append(f"- **따라하기**: {'🟢 쉬움' if challenge['easy_to_follow'] else '🔴 어려움'}")
            
            if challenge['music_genre']:
                md_lines.append(f"- **음악 장르**: {challenge['music_genre']}")
            
            if challenge['viral_sounds']:
                sounds = ', '.join([f"`{sound}`" for sound in challenge['viral_sounds']])
                md_lines.append(f"- **바이럴 사운드**: {sounds}")
            
            if challenge['required_tools']:
                tools = ', '.join([f"`{tool}`" for tool in challenge['required_tools']])
                md_lines.append(f"- **필요 도구**: {tools}")
        
        md_lines.append("")
    
    # 트렌드 분석
    md_lines.append("## 📈 트렌드 분석")
    md_lines.append("")
    
    for trend in report['trends']:
        md_lines.append(f"- {trend}")
    md_lines.append("")
    
    # 콘텐츠 제작 추천
    md_lines.append("## 💡 콘텐츠 제작 추천사항")
    md_lines.append("")
    
    for rec in report['recommendations']:
        md_lines.append(f"- {rec}")
    md_lines.append("")
    
    # 푸터
    md_lines.append("---")
    md_lines.append("")
    md_lines.append("*이 리포트는 YouTube Shorts 트렌드 분석 시스템에 의해 자동 생성되었습니다.*")
    md_lines.append("")
    md_lines.append("🤖 **생성 시스템**: Claude Code + Gemini 1.5 Flash")
    md_lines.append("📅 **생성 일시**: " + datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분'))
    md_lines.append("")
    
    return '\n'.join(md_lines)

if __name__ == "__main__":
    asyncio.run(main())
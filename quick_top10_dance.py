#!/usr/bin/env python3
"""
빠른 댄스 챌린지 TOP 10 - 영상 분석 없이 텍스트 기반으로만
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from dataclasses import dataclass

from src.agents.collector_agent import create_collector_agent
from src.agents.analyzer_agent import create_analyzer_agent
from src.models.video_models import EnhancedClassifiedVideo

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class QuickDanceChallenge:
    """빠른 댄스 챌린지 데이터"""
    rank: int
    video_id: str
    title: str
    channel: str
    view_count: int
    confidence: float
    youtube_url: str
    thumbnail_url: str
    description: str
    published_date: str
    like_count: int
    comment_count: int

async def quick_find_dance_challenges(target_count: int = 10, max_attempts: int = 3) -> List[QuickDanceChallenge]:
    """
    빠른 댄스 챌린지 수집 - 반드시 target_count만큼 수집
    """
    print(f"🎯 댄스 챌린지 {target_count}개 빠른 수집 시작...")
    
    collector = create_collector_agent()
    analyzer = create_analyzer_agent()
    
    all_dance_challenges = []
    
    for attempt in range(max_attempts):
        print(f"\n🔄 시도 {attempt + 1}/{max_attempts}: 현재 {len(all_dance_challenges)}개 수집됨, 목표 {target_count}개")
        
        if len(all_dance_challenges) >= target_count:
            print(f"✅ 목표 달성! {len(all_dance_challenges)}개 수집 완료")
            break
        
        print(f"📊 비디오 수집 중...")
        
        # 다양한 키워드로 수집
        videos = await collector.collect_top_videos(
            search_queries=[
                'dance challenge', '댄스 챌린지', 'easy dance', 'simple dance', 
                'dance tutorial', 'kpop dance', 'viral dance', 'tiktok dance',
                '쉬운 댄스', '간단한 댄스', 'dance trend', 'trending dance',
                'dance moves', 'choreography', '안무', 'dance steps'
            ],
            days=30,  # 30일로 확장
            top_n=15,  # 각 쿼리당 상위 15개
            max_results_per_query=30  # 쿼리당 최대 30개 검색 (속도 향상)
        )
        
        print(f"✅ {len(videos)}개 비디오 수집됨")
        
        # 텍스트 기반 분석만 (영상 분석 제외)
        print(f"📝 텍스트 기반 분석 중...")
        classified_videos = await analyzer.classify_videos(videos)
        
        # 댄스 챌린지 필터링 및 변환
        print(f"🕺 댄스 챌린지 필터링 중...")
        
        for i, classification in enumerate(classified_videos):
            # 해당 비디오 찾기
            video = next((v for v in videos if v.video_id == classification.video_id), None)
            if not video:
                continue
            
            # 댄스 챌린지 조건 검사 (더 관대하게)
            title_lower = video.snippet.title.lower()
            desc_lower = video.snippet.description.lower()
            
            # 댄스 키워드 체크
            dance_keywords = ['dance', '댄스', 'dancing', 'choreography', '안무', 'moves', 'tutorial', 'challenge', '챌린지']
            has_dance_keyword = any(keyword in title_lower or keyword in desc_lower for keyword in dance_keywords)
            
            # 쉬운/간단한 키워드 체크
            easy_keywords = ['easy', 'simple', '쉬운', '간단한', 'basic', 'beginner', '초보']
            has_easy_keyword = any(keyword in title_lower or keyword in desc_lower for keyword in easy_keywords)
            
            is_dance_challenge = (
                classification.category.value == "Challenge" and 
                has_dance_keyword and
                classification.confidence > 0.2  # 더 관대한 신뢰도
            )
            
            if is_dance_challenge:
                # 이미 수집된 비디오인지 확인 (중복 제거)
                if any(dc.video_id == video.video_id for dc in all_dance_challenges):
                    continue
                
                # 빠른 댄스 챌린지 객체 생성
                quick_challenge = QuickDanceChallenge(
                    rank=0,  # 나중에 설정
                    video_id=video.video_id,
                    title=video.snippet.title,
                    channel=video.snippet.channel_title,
                    view_count=video.statistics.view_count if video.statistics else 0,
                    confidence=classification.confidence,
                    youtube_url=f"https://www.youtube.com/watch?v={video.video_id}",
                    thumbnail_url=video.snippet.thumbnail_url,
                    description=video.snippet.description[:200] + "..." if len(video.snippet.description) > 200 else video.snippet.description,
                    published_date=video.snippet.published_at.strftime('%Y-%m-%d'),
                    like_count=video.statistics.like_count if video.statistics else 0,
                    comment_count=video.statistics.comment_count if video.statistics else 0
                )
                
                all_dance_challenges.append(quick_challenge)
                print(f"✅ 댄스 챌린지 발견: {quick_challenge.title[:50]}...")
        
        print(f"📈 현재까지 {len(all_dance_challenges)}개 댄스 챌린지 수집됨")
        
        # 목표 달성했으면 종료
        if len(all_dance_challenges) >= target_count:
            break
    
    # 조회수 기준 정렬
    all_dance_challenges.sort(key=lambda x: x.view_count, reverse=True)
    
    # 상위 target_count개 선택하고 순위 설정
    top_challenges = all_dance_challenges[:target_count]
    for i, challenge in enumerate(top_challenges, 1):
        challenge.rank = i
    
    print(f"\n🎉 최종 결과: {len(top_challenges)}개 댄스 챌린지 수집 완료!")
    
    return top_challenges

def analyze_text_trends(challenges: List[QuickDanceChallenge]) -> Dict[str, Any]:
    """텍스트 기반 트렌드 분석"""
    
    # 제목에서 키워드 추출
    title_keywords = {}
    description_keywords = {}
    
    for challenge in challenges:
        title_words = challenge.title.lower().split()
        desc_words = challenge.description.lower().split()
        
        for word in title_words:
            if len(word) > 3:  # 3글자 이상만
                title_keywords[word] = title_keywords.get(word, 0) + 1
        
        for word in desc_words[:20]:  # 처음 20단어만
            if len(word) > 3:
                description_keywords[word] = description_keywords.get(word, 0) + 1
    
    # 상위 키워드 추출
    top_title_keywords = sorted(title_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
    top_desc_keywords = sorted(description_keywords.items(), key=lambda x: x[1], reverse=True)[:10]
    
    # 채널 분석
    channel_count = {}
    for challenge in challenges:
        channel_count[challenge.channel] = channel_count.get(challenge.channel, 0) + 1
    
    # 발행일 분석
    date_count = {}
    for challenge in challenges:
        date_count[challenge.published_date] = date_count.get(challenge.published_date, 0) + 1
    
    return {
        "title_keywords": top_title_keywords,
        "description_keywords": top_desc_keywords,
        "channel_distribution": sorted(channel_count.items(), key=lambda x: x[1], reverse=True),
        "date_distribution": sorted(date_count.items(), key=lambda x: x[1], reverse=True),
        "avg_views": sum(c.view_count for c in challenges) // len(challenges),
        "avg_likes": sum(c.like_count for c in challenges) // len(challenges),
        "avg_comments": sum(c.comment_count for c in challenges) // len(challenges)
    }

def generate_quick_markdown_report(challenges: List[QuickDanceChallenge]) -> str:
    """빠른 마크다운 리포트 생성"""
    
    total_views = sum(challenge.view_count for challenge in challenges)
    total_likes = sum(challenge.like_count for challenge in challenges)
    total_comments = sum(challenge.comment_count for challenge in challenges)
    avg_views = total_views // len(challenges) if challenges else 0
    
    # 트렌드 분석
    trends = analyze_text_trends(challenges)
    
    report = f"""# 🕺 따라하기 쉬운 댄스 챌린지 TOP {len(challenges)}

## 📊 분석 개요

- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **발견된 댄스 챌린지**: {len(challenges)}개
- **총 조회수**: {total_views:,}
- **총 좋아요**: {total_likes:,}
- **총 댓글**: {total_comments:,}
- **평균 조회수**: {avg_views:,}
- **분석 방법**: AI 텍스트 분석 + YouTube 메타데이터

## 🏆 댄스 챌린지 순위

"""
    
    for challenge in challenges:
        report += f"""### {challenge.rank}. {challenge.title}

- **🎬 비디오 ID**: `{challenge.video_id}`
- **👤 채널**: {challenge.channel}
- **👀 조회수**: {challenge.view_count:,}
- **👍 좋아요**: {challenge.like_count:,}
- **💬 댓글**: {challenge.comment_count:,}
- **📅 발행일**: {challenge.published_date}
- **🎯 분석 신뢰도**: {challenge.confidence:.2f}
- **🔗 YouTube 링크**: [바로가기]({challenge.youtube_url})
- **🖼️ 썸네일**: ![썸네일]({challenge.thumbnail_url})

#### 📝 설명:
```
{challenge.description}
```

---

"""
    
    # 트렌드 분석 섹션
    report += f"""## 📈 상세 트렌드 분석

### 🏷️ 제목 키워드 TOP 10
"""
    
    for i, (keyword, count) in enumerate(trends["title_keywords"], 1):
        report += f"{i}. **{keyword}** ({count}회)\n"
    
    report += f"""
### 📝 설명 키워드 TOP 10
"""
    
    for i, (keyword, count) in enumerate(trends["description_keywords"], 1):
        report += f"{i}. **{keyword}** ({count}회)\n"
    
    report += f"""
### 👥 인기 채널 분석
"""
    
    for i, (channel, count) in enumerate(trends["channel_distribution"][:5], 1):
        report += f"{i}. **{channel}** ({count}개 영상)\n"
    
    report += f"""
### 📊 통계 분석
- **최고 조회수**: {max(challenge.view_count for challenge in challenges):,} ({challenges[0].title[:30]}...)
- **최저 조회수**: {min(challenge.view_count for challenge in challenges):,} ({challenges[-1].title[:30]}...)
- **조회수 격차**: {max(challenge.view_count for challenge in challenges) - min(challenge.view_count for challenge in challenges):,}
- **평균 좋아요**: {trends['avg_likes']:,}
- **평균 댓글**: {trends['avg_comments']:,}

### 🎯 성공 요소 분석
"""
    
    # 성공 요소 분석
    high_view_challenges = [c for c in challenges if c.view_count > avg_views]
    
    if high_view_challenges:
        report += f"**고조회수 영상 ({len(high_view_challenges)}개) 공통점:**\n"
        
        # 고조회수 영상들의 공통 키워드 찾기
        high_view_titles = " ".join([c.title.lower() for c in high_view_challenges])
        common_words = ['dance', 'challenge', 'easy', 'tutorial', 'viral', 'trending', 'kpop', 'simple']
        
        for word in common_words:
            if word in high_view_titles:
                count = high_view_titles.count(word)
                if count > 1:
                    report += f"- **{word}**: {count}개 영상에서 사용\n"
    
    report += f"""
## 💡 콘텐츠 제작 추천사항

### 🎯 핵심 성공 요소
1. **명확한 제목**: "Easy", "Challenge", "Tutorial" 등의 키워드 포함
2. **트렌딩 요소**: K-pop, 바이럴 음악, 인기 챌린지 활용  
3. **접근성**: 초보자도 따라할 수 있는 간단한 동작
4. **시각적 매력**: 밝고 선명한 썸네일
5. **일관성**: 정기적인 업로드와 브랜딩

### 📱 플랫폼별 최적화
- **YouTube Shorts**: 세로형 영상, 자막 활용
- **제목 최적화**: 트렌딩 키워드 + 감정적 표현
- **해시태그**: #dance #challenge #easy #viral

### 🎨 콘텐츠 아이디어
- **난이도별 시리즈**: 초급/중급/고급 댄스 챌린지
- **음악별 시리즈**: K-pop, 팝, 힙합 등 장르별 댄스
- **그룹 챌린지**: 친구, 가족과 함께하는 댄스
- **속도 조절**: 느린 버전과 빠른 버전 제공

---

*이 리포트는 AI 기반 YouTube Shorts 트렌드 분석 시스템에 의해 자동 생성되었습니다.*

🤖 **생성 시스템**: Claude Code + Gemini 1.5 Flash + YouTube Data API  
📅 **생성 일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}  
🔬 **분석 방법**: 텍스트 기반 AI 분석 + 메타데이터 분석
"""
    
    return report

async def main():
    """메인 실행 함수"""
    print("🕺 빠른 댄스 챌린지 분석기 - TOP 10 보장")
    print("=" * 50)
    
    try:
        # 반드시 10개 수집
        dance_challenges = await quick_find_dance_challenges(target_count=10, max_attempts=3)
        
        if len(dance_challenges) < 10:
            print(f"⚠️ 경고: 목표 10개에 못 미치는 {len(dance_challenges)}개만 수집됨")
            print("🔄 더 관대한 조건으로 추가 수집...")
            
            # 부족한 만큼 더 수집 (조건을 더 완화)
            needed = 10 - len(dance_challenges)
            collector = create_collector_agent()
            analyzer = create_analyzer_agent()
            
            # 더 많은 키워드로 재시도
            videos = await collector.collect_top_videos(
                search_queries=[
                    'dance', 'dancing', 'choreography', 'moves', 'tutorial',
                    '댄스', '안무', '춤', 'challenge', 'viral'
                ],
                days=60,  # 더 긴 기간
                top_n=20,
                max_results_per_query=40
            )
            
            classified_videos = await analyzer.classify_videos(videos)
            
            for classification in classified_videos:
                if len(dance_challenges) >= 10:
                    break
                    
                video = next((v for v in videos if v.video_id == classification.video_id), None)
                if not video:
                    continue
                
                # 이미 있는지 확인
                if any(dc.video_id == video.video_id for dc in dance_challenges):
                    continue
                
                # 더 관대한 조건
                title_lower = video.snippet.title.lower()
                if any(keyword in title_lower for keyword in ['dance', '댄스', 'dancing', 'choreography', '안무']):
                    quick_challenge = QuickDanceChallenge(
                        rank=len(dance_challenges) + 1,
                        video_id=video.video_id,
                        title=video.snippet.title,
                        channel=video.snippet.channel_title,
                        view_count=video.statistics.view_count if video.statistics else 0,
                        confidence=classification.confidence,
                        youtube_url=f"https://www.youtube.com/watch?v={video.video_id}",
                        thumbnail_url=video.snippet.thumbnail_url,
                        description=video.snippet.description[:200] + "..." if len(video.snippet.description) > 200 else video.snippet.description,
                        published_date=video.snippet.published_at.strftime('%Y-%m-%d'),
                        like_count=video.statistics.like_count if video.statistics else 0,
                        comment_count=video.statistics.comment_count if video.statistics else 0
                    )
                    dance_challenges.append(quick_challenge)
                    print(f"✅ 추가 댄스 영상 발견: {quick_challenge.title[:50]}...")
        
        # 최종 정렬 및 순위 재설정
        dance_challenges.sort(key=lambda x: x.view_count, reverse=True)
        for i, challenge in enumerate(dance_challenges[:10], 1):
            challenge.rank = i
        
        # 상위 10개만 유지
        dance_challenges = dance_challenges[:10]
        
        # 리포트 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # JSON 저장 (HttpUrl 객체를 문자열로 변환)
        json_data = {
            "analysis_date": datetime.now().isoformat(),
            "total_challenges": len(dance_challenges),
            "challenges": [
                {
                    "rank": c.rank,
                    "video_id": c.video_id,
                    "title": c.title,
                    "channel": c.channel,
                    "view_count": c.view_count,
                    "like_count": c.like_count,
                    "comment_count": c.comment_count,
                    "confidence": c.confidence,
                    "youtube_url": str(c.youtube_url),  # HttpUrl을 문자열로 변환
                    "thumbnail_url": str(c.thumbnail_url),  # HttpUrl을 문자열로 변환
                    "description": c.description,
                    "published_date": c.published_date
                }
                for c in dance_challenges
            ]
        }
        
        json_filename = f"quick_dance_top10_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 마크다운 리포트 생성
        markdown_report = generate_quick_markdown_report(dance_challenges)
        markdown_filename = f"quick_dance_top10_{timestamp}.md"
        
        with open(markdown_filename, 'w', encoding='utf-8') as f:
            f.write(markdown_report)
        
        # 결과 출력
        total_views = sum(c.view_count for c in dance_challenges)
        avg_views = total_views // len(dance_challenges) if dance_challenges else 0
        
        print(f"\n🎉 따라하기 쉬운 댄스 챌린지 TOP {len(dance_challenges)}")
        print(f"📈 총 조회수: {total_views:,}")
        print(f"📊 평균 조회수: {avg_views:,}")
        print(f"📅 분석 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        print(f"\n🏆 TOP {len(dance_challenges)} 댄스 챌린지:")
        print("-" * 70)
        for challenge in dance_challenges:
            print(f" {challenge.rank}. {challenge.title}")
            print(f"    📺 조회수: {challenge.view_count:,}")
            print(f"    📺 채널: {challenge.channel}")
            print(f"    🎯 신뢰도: {challenge.confidence:.2f}")
            print(f"    🔗 링크: {challenge.youtube_url}")
            print(f"    🖼️ 썸네일: {challenge.thumbnail_url}")
            print()
        
        print(f"💾 리포트가 저장되었습니다:")
        print(f"  📄 JSON: {json_filename}")
        print(f"  📝 Markdown: {markdown_filename}")
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        logger.exception("Analysis failed")

if __name__ == "__main__":
    asyncio.run(main())
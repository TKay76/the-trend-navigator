#!/usr/bin/env python3
"""
향상된 댄스 챌린지 분석기 - 탑 10 보장 + 영상 링크 + 썸네일 + 상세 분석
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
class EnhancedDanceChallenge:
    """향상된 댄스 챌린지 데이터"""
    rank: int
    video_id: str
    title: str
    channel: str
    view_count: int
    confidence: float
    youtube_url: str
    thumbnail_url: str
    video_analysis: Dict[str, Any] = None
    music_analysis: str = ""
    difficulty_level: str = ""
    participants: str = ""
    followability: str = ""
    viral_potential: str = ""

async def enhanced_find_dance_challenges(target_count: int = 10, max_attempts: int = 5) -> List[EnhancedDanceChallenge]:
    """
    향상된 댄스 챌린지 수집 - 반드시 target_count만큼 수집
    """
    print(f"🎯 댄스 챌린지 {target_count}개 수집 시작...")
    
    collector = create_collector_agent()
    analyzer = create_analyzer_agent()
    
    all_dance_challenges = []
    
    for attempt in range(max_attempts):
        print(f"\n🔄 시도 {attempt + 1}/{max_attempts}: 현재 {len(all_dance_challenges)}개 수집됨, 목표 {target_count}개")
        
        if len(all_dance_challenges) >= target_count:
            print(f"✅ 목표 달성! {len(all_dance_challenges)}개 수집 완료")
            break
        
        # 더 많은 비디오 수집 (부족한 만큼 더 수집)
        needed = target_count - len(all_dance_challenges)
        collect_count = max(50, needed * 3)  # 3배수로 수집해서 충분히 확보
        
        print(f"📊 {collect_count}개 비디오 수집 중...")
        
        # 다양한 키워드로 수집
        videos = await collector.collect_top_videos(
            search_queries=[
                'dance challenge', '댄스 챌린지', 'easy dance', 'simple dance', 
                'dance tutorial', 'kpop dance', 'viral dance', 'tiktok dance',
                '쉬운 댄스', '간단한 댄스', 'dance trend', 'trending dance',
                'dance moves', 'choreography', '안무', 'dance steps'
            ],
            days=30,  # 30일로 확장
            top_n=20,  # 각 쿼리당 상위 20개
            max_results_per_query=50  # 쿼리당 최대 50개 검색
        )
        
        print(f"✅ {len(videos)}개 비디오 수집됨")
        
        # 향상된 분석 (영상 콘텐츠 포함)
        print(f"🎥 향상된 비디오 분석 중...")
        enhanced_videos = await analyzer.classify_videos_with_enhanced_analysis(
            videos, 
            include_video_content=True
        )
        
        # 댄스 챌린지 필터링 및 변환
        print(f"🕺 댄스 챌린지 필터링 중...")
        
        for video in enhanced_videos:
            # 댄스 챌린지 조건 검사
            is_dance_challenge = (
                video.category.value == "Challenge" and 
                any(keyword in video.video.snippet.title.lower() for keyword in 
                    ['dance', '댄스', 'dancing', 'choreography', '안무', 'moves', 'tutorial']) and
                video.confidence > 0.3  # 신뢰도 낮춤
            )
            
            if is_dance_challenge:
                # 이미 수집된 비디오인지 확인 (중복 제거)
                if any(dc.video_id == video.video.video_id for dc in all_dance_challenges):
                    continue
                
                # 향상된 댄스 챌린지 객체 생성
                enhanced_challenge = EnhancedDanceChallenge(
                    rank=0,  # 나중에 설정
                    video_id=video.video.video_id,
                    title=video.video.snippet.title,
                    channel=video.video.snippet.channel_title,
                    view_count=video.video.statistics.view_count if video.video.statistics else 0,
                    confidence=video.confidence,
                    youtube_url=f"https://www.youtube.com/watch?v={video.video.video_id}",
                    thumbnail_url=video.video.snippet.thumbnail_url,
                    video_analysis=video.enhanced_analysis if hasattr(video, 'enhanced_analysis') else None
                )
                
                # 영상 분석 결과에서 상세 정보 추출
                if enhanced_challenge.video_analysis and enhanced_challenge.video_analysis.get('content'):
                    content = enhanced_challenge.video_analysis['content']
                    enhanced_challenge.music_analysis = extract_music_info(content)
                    enhanced_challenge.difficulty_level = extract_difficulty(content)
                    enhanced_challenge.participants = extract_participants(content)
                    enhanced_challenge.followability = extract_followability(content)
                    enhanced_challenge.viral_potential = extract_viral_potential(content)
                
                all_dance_challenges.append(enhanced_challenge)
                print(f"✅ 댄스 챌린지 발견: {enhanced_challenge.title[:50]}...")
        
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

def extract_music_info(content: str) -> str:
    """영상 분석에서 음악 정보 추출"""
    keywords = ['music', 'song', 'audio', 'sound', '음악', '곡', '사운드']
    lines = content.split('\n')
    
    for line in lines:
        if any(keyword in line.lower() for keyword in keywords):
            return line.strip()
    
    return "음악 정보 없음"

def extract_difficulty(content: str) -> str:
    """난이도 정보 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['easy', 'simple', '쉬운', '간단한', 'basic']):
        return "쉬움"
    elif any(word in content_lower for word in ['medium', 'moderate', '보통', '중간']):
        return "보통"
    elif any(word in content_lower for word in ['hard', 'difficult', '어려운', '복잡한']):
        return "어려움"
    
    return "알 수 없음"

def extract_participants(content: str) -> str:
    """참가자 정보 추출"""
    content_lower = content.lower()
    
    if 'group' in content_lower or '그룹' in content_lower:
        return "그룹"
    elif 'solo' in content_lower or '솔로' in content_lower or 'individual' in content_lower:
        return "개인"
    elif 'couple' in content_lower or '커플' in content_lower:
        return "커플"
    
    return "개인"

def extract_followability(content: str) -> str:
    """따라하기 쉬운 정도 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['easy to follow', 'beginner', '초보자', '따라하기 쉬운']):
        return "매우 쉬움"
    elif any(word in content_lower for word in ['moderate', '보통']):
        return "보통"
    
    return "쉬움"

def extract_viral_potential(content: str) -> str:
    """바이럴 가능성 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['viral', 'trending', '바이럴', '트렌딩']):
        return "높음"
    elif any(word in content_lower for word in ['popular', '인기']):
        return "보통"
    
    return "보통"

def generate_enhanced_markdown_report(challenges: List[EnhancedDanceChallenge]) -> str:
    """향상된 마크다운 리포트 생성"""
    
    total_views = sum(challenge.view_count for challenge in challenges)
    avg_views = total_views // len(challenges) if challenges else 0
    
    # 트렌드 분석
    music_trends = analyze_music_trends(challenges)
    difficulty_trends = analyze_difficulty_trends(challenges)
    participant_trends = analyze_participant_trends(challenges)
    
    report = f"""# 🕺 따라하기 쉬운 댄스 챌린지 TOP {len(challenges)}

## 📊 분석 개요

- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **발견된 댄스 챌린지**: {len(challenges)}개
- **총 조회수**: {total_views:,}
- **평균 조회수**: {avg_views:,}
- **분석 방법**: AI 영상 콘텐츠 분석 + 메타데이터 분석

## 🏆 댄스 챌린지 순위

"""
    
    for challenge in challenges:
        report += f"""### {challenge.rank}. {challenge.title}

- **🎬 비디오 ID**: `{challenge.video_id}`
- **👤 채널**: {challenge.channel}
- **👀 조회수**: {challenge.view_count:,}
- **🎯 분석 신뢰도**: {challenge.confidence:.2f}
- **🔗 YouTube 링크**: [{challenge.youtube_url}]({challenge.youtube_url})
- **🖼️ 썸네일**: ![썸네일]({challenge.thumbnail_url})

#### 📋 상세 분석 결과:
- **🎵 음악 분석**: {challenge.music_analysis}
- **⭐ 댄스 난이도**: {challenge.difficulty_level}
- **👥 구성원**: {challenge.participants}
- **🎯 따라하기 용이성**: {challenge.followability}
- **🚀 바이럴 가능성**: {challenge.viral_potential}

"""
        
        if challenge.video_analysis and challenge.video_analysis.get('content'):
            content_preview = challenge.video_analysis['content'][:200]
            report += f"""#### 🎥 AI 영상 분석:
```
{content_preview}...
```

"""
    
    # 트렌드 분석 섹션
    report += f"""## 📈 상세 트렌드 분석

### 🎵 음악 트렌드
{music_trends}

### ⭐ 난이도 분포
{difficulty_trends}

### 👥 참가자 유형
{participant_trends}

### 📊 조회수 분석
- **최고 조회수**: {max(challenge.view_count for challenge in challenges):,} ({challenges[0].title[:30]}...)
- **최저 조회수**: {min(challenge.view_count for challenge in challenges):,} ({challenges[-1].title[:30]}...)
- **조회수 격차**: {max(challenge.view_count for challenge in challenges) - min(challenge.view_count for challenge in challenges):,}

### 🚀 바이럴 요소 분석
- **쉬운 난이도**: {len([c for c in challenges if c.difficulty_level == '쉬움'])}개 ({len([c for c in challenges if c.difficulty_level == '쉬움'])/len(challenges)*100:.1f}%)
- **개인 참여 가능**: {len([c for c in challenges if c.participants in ['개인', '솔로']])}개
- **높은 따라하기 용이성**: {len([c for c in challenges if c.followability in ['매우 쉬움', '쉬움']])}개

## 💡 콘텐츠 제작 추천사항

### 🎯 핵심 성공 요소
1. **간단한 안무**: 3-5개의 기본 동작으로 구성
2. **명확한 지시**: 화면 가이드나 음성 지시 포함
3. **트렌딩 음악**: 현재 인기 있는 음악 활용
4. **짧은 길이**: 15-30초 내외의 짧은 영상
5. **반복 학습**: 같은 동작을 여러 번 보여주기

### 📱 플랫폼별 최적화
- **YouTube Shorts**: 세로형 영상, 해시태그 활용
- **TikTok**: 트렌딩 사운드 사용, 챌린지 해시태그
- **Instagram Reels**: 고화질 영상, 스토리 연동

### 🎨 시각적 요소
- **밝고 선명한 색상**: 눈에 띄는 의상과 배경
- **좋은 조명**: 실내외 모두 밝은 환경
- **클린한 배경**: 집중도를 높이는 깔끔한 배경

---

*이 리포트는 AI 기반 YouTube Shorts 트렌드 분석 시스템에 의해 자동 생성되었습니다.*

🤖 **생성 시스템**: Claude Code + Gemini 1.5 Flash + YouTube Data API  
📅 **생성 일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}  
🔬 **분석 방법**: 실시간 영상 콘텐츠 AI 분석
"""
    
    return report

def analyze_music_trends(challenges: List[EnhancedDanceChallenge]) -> str:
    """음악 트렌드 분석"""
    music_keywords = {}
    
    for challenge in challenges:
        music = challenge.music_analysis.lower()
        if 'kpop' in music or 'k-pop' in music:
            music_keywords['K-pop'] = music_keywords.get('K-pop', 0) + 1
        if 'pop' in music:
            music_keywords['Pop'] = music_keywords.get('Pop', 0) + 1
        if 'hip hop' in music or 'hiphop' in music:
            music_keywords['Hip-hop'] = music_keywords.get('Hip-hop', 0) + 1
        if 'electronic' in music:
            music_keywords['Electronic'] = music_keywords.get('Electronic', 0) + 1
    
    if not music_keywords:
        return "- 다양한 장르의 음악이 사용되고 있음"
    
    trend_text = ""
    for genre, count in sorted(music_keywords.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(challenges)) * 100
        trend_text += f"- **{genre}**: {count}개 ({percentage:.1f}%)\n"
    
    return trend_text

def analyze_difficulty_trends(challenges: List[EnhancedDanceChallenge]) -> str:
    """난이도 트렌드 분석"""
    difficulty_count = {}
    
    for challenge in challenges:
        diff = challenge.difficulty_level
        difficulty_count[diff] = difficulty_count.get(diff, 0) + 1
    
    trend_text = ""
    for diff, count in sorted(difficulty_count.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(challenges)) * 100
        trend_text += f"- **{diff}**: {count}개 ({percentage:.1f}%)\n"
    
    return trend_text

def analyze_participant_trends(challenges: List[EnhancedDanceChallenge]) -> str:
    """참가자 유형 트렌드 분석"""
    participant_count = {}
    
    for challenge in challenges:
        part = challenge.participants
        participant_count[part] = participant_count.get(part, 0) + 1
    
    trend_text = ""
    for part, count in sorted(participant_count.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(challenges)) * 100
        trend_text += f"- **{part}**: {count}개 ({percentage:.1f}%)\n"
    
    return trend_text

async def main():
    """메인 실행 함수"""
    print("🕺 향상된 댄스 챌린지 분석기 - TOP 10 보장")
    print("=" * 70)
    
    try:
        # 반드시 10개 수집
        dance_challenges = await enhanced_find_dance_challenges(target_count=10, max_attempts=5)
        
        if len(dance_challenges) < 10:
            print(f"⚠️ 경고: 목표 10개에 못 미치는 {len(dance_challenges)}개만 수집됨")
            print("🔄 추가 수집 시도...")
            
            # 더 관대한 조건으로 재시도
            additional_challenges = await enhanced_find_dance_challenges(target_count=10-len(dance_challenges), max_attempts=3)
            dance_challenges.extend(additional_challenges)
        
        if len(dance_challenges) < 10:
            print(f"❌ 최종적으로 {len(dance_challenges)}개만 수집됨. 그래도 리포트 생성합니다.")
        
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
                    "confidence": c.confidence,
                    "youtube_url": str(c.youtube_url),  # HttpUrl을 문자열로 변환
                    "thumbnail_url": str(c.thumbnail_url),  # HttpUrl을 문자열로 변환
                    "music_analysis": c.music_analysis,
                    "difficulty_level": c.difficulty_level,
                    "participants": c.participants,
                    "followability": c.followability,
                    "viral_potential": c.viral_potential,
                    "video_analysis": c.video_analysis
                }
                for c in dance_challenges
            ]
        }
        
        json_filename = f"enhanced_dance_report_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # 마크다운 리포트 생성
        markdown_report = generate_enhanced_markdown_report(dance_challenges)
        markdown_filename = f"enhanced_dance_report_{timestamp}.md"
        
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
        print("-" * 50)
        for challenge in dance_challenges:
            print(f" {challenge.rank}. {challenge.title[:40]}...")
            print(f"    📺 조회수: {challenge.view_count:,}")
            print(f"    📺 채널: {challenge.channel}")
            print(f"    🎯 신뢰도: {challenge.confidence:.2f}")
            print(f"    🔗 링크: {challenge.youtube_url}")
            print()
        
        print(f"💾 리포트가 저장되었습니다:")
        print(f"  📄 JSON: {json_filename}")
        print(f"  📝 Markdown: {markdown_filename}")
        
    except Exception as e:
        print(f"❌ 분석 실패: {e}")
        logger.exception("Analysis failed")

if __name__ == "__main__":
    asyncio.run(main())
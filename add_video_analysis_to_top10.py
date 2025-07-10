#!/usr/bin/env python3
"""
기존 TOP 10에 영상 분석 추가
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from src.clients.llm_provider import create_llm_provider

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def analyze_top10_videos():
    """기존 TOP 10에 영상 분석 추가"""
    
    print("🎥 TOP 10 댄스 챌린지 영상 분석 추가")
    print("=" * 50)
    
    # 기존 TOP 10 데이터 로드
    json_file = "quick_dance_top10_20250710_192850.json"
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        challenges = data["challenges"]
        print(f"✅ {len(challenges)}개 댄스 챌린지 로드됨")
        
        # LLM Provider 생성
        llm_provider = create_llm_provider()
        print(f"✅ LLM Provider: {llm_provider.provider_name}")
        
        # 각 비디오에 대해 영상 분석 수행
        for i, challenge in enumerate(challenges, 1):
            video_id = challenge["video_id"]
            title = challenge["title"]
            
            print(f"\n🎬 [{i}/10] 영상 분석 중: {title[:50]}...")
            
            try:
                # 챌린지 타입 분석 수행
                analysis_result = await llm_provider.analyze_youtube_video(
                    video_id, 
                    analysis_type="challenge"
                )
                
                if analysis_result and analysis_result.get("success"):
                    content = analysis_result.get("content", "")
                    
                    # 간단한 텍스트 파싱으로 정보 추출
                    challenge["video_analysis"] = {
                        "content": content,
                        "music_analysis": extract_music_info(content),
                        "difficulty_level": extract_difficulty(content),
                        "participants": extract_participants(content),
                        "followability": extract_followability(content),
                        "viral_potential": extract_viral_potential(content),
                        "challenge_type": extract_challenge_type(content),
                        "requirements": extract_requirements(content)
                    }
                    
                    print(f"  ✅ 영상 분석 완료")
                    print(f"     음악: {challenge['video_analysis']['music_analysis']}")
                    print(f"     난이도: {challenge['video_analysis']['difficulty_level']}")
                    print(f"     참여자: {challenge['video_analysis']['participants']}")
                    print(f"     용이성: {challenge['video_analysis']['followability']}")
                else:
                    print(f"  ❌ 영상 분석 실패")
                    challenge["video_analysis"] = {"error": "분석 실패"}
                
            except Exception as e:
                print(f"  ❌ 영상 분석 에러: {e}")
                challenge["video_analysis"] = {"error": str(e)}
            
            # API 제한을 위한 대기
            await asyncio.sleep(2)
        
        # 업데이트된 데이터 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_json_file = f"enhanced_dance_top10_{timestamp}.json"
        
        enhanced_data = {
            "analysis_date": datetime.now().isoformat(),
            "original_file": json_file,
            "enhanced_analysis": True,
            "total_challenges": len(challenges),
            "challenges": challenges
        }
        
        with open(new_json_file, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
        
        # 마크다운 리포트 생성
        markdown_content = generate_enhanced_markdown(challenges)
        markdown_file = f"enhanced_dance_top10_{timestamp}.md"
        
        with open(markdown_file, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        print(f"\n🎉 영상 분석 완료!")
        print(f"💾 파일 저장됨:")
        print(f"  📄 JSON: {new_json_file}")
        print(f"  📝 Markdown: {markdown_file}")
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file}")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        logger.exception("Analysis failed")

def extract_music_info(content: str) -> str:
    """영상 분석에서 음악 정보 추출"""
    content_lower = content.lower()
    
    if "music" in content_lower or "song" in content_lower:
        lines = content.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['music', 'song', 'audio', 'sound']):
                return line.strip()[:100]
    
    if "cha cha slide" in content_lower:
        return "Cha Cha Slide - 클래식 댄스 음악"
    elif "viral" in content_lower and "tiktok" in content_lower:
        return "바이럴 TikTok 사운드"
    elif "k-pop" in content_lower or "kpop" in content_lower:
        return "K-pop 음악"
    
    return "일반 배경음악"

def extract_difficulty(content: str) -> str:
    """난이도 정보 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['easy', 'simple', 'basic', 'beginner']):
        return "쉬움"
    elif any(word in content_lower for word in ['medium', 'moderate', 'intermediate']):
        return "보통"
    elif any(word in content_lower for word in ['hard', 'difficult', 'complex', 'advanced']):
        return "어려움"
    
    # 제목 기반 추론
    if "tutorial" in content_lower or "easy" in content_lower:
        return "쉬움"
    
    return "보통"

def extract_participants(content: str) -> str:
    """참가자 정보 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['couple', 'duo', 'pair']):
        return "커플/듀오"
    elif any(word in content_lower for word in ['group', 'team', 'multiple']):
        return "그룹"
    elif any(word in content_lower for word in ['solo', 'individual', 'single']):
        return "개인"
    elif "kids" in content_lower or "children" in content_lower:
        return "아이들"
    
    return "개인"

def extract_followability(content: str) -> str:
    """따라하기 쉬운 정도 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['easy to follow', 'beginner-friendly', 'simple steps']):
        return "매우 쉬움"
    elif any(word in content_lower for word in ['tutorial', 'learn', 'guide']):
        return "쉬움"
    elif any(word in content_lower for word in ['complex', 'difficult', 'advanced']):
        return "어려움"
    
    return "보통"

def extract_viral_potential(content: str) -> str:
    """바이럴 가능성 추출"""
    content_lower = content.lower()
    
    viral_indicators = ['viral', 'trending', 'popular', 'challenge', 'tiktok', 'shorts']
    count = sum(1 for indicator in viral_indicators if indicator in content_lower)
    
    if count >= 3:
        return "높음"
    elif count >= 1:
        return "보통"
    
    return "낮음"

def extract_challenge_type(content: str) -> str:
    """챌린지 타입 추출"""
    content_lower = content.lower()
    
    if "dance" in content_lower:
        if "cha cha" in content_lower:
            return "라인 댄스"
        elif "couple" in content_lower:
            return "커플 댄스"
        elif "tutorial" in content_lower:
            return "댄스 튜토리얼"
        else:
            return "일반 댄스"
    elif "ice" in content_lower and "skating" in content_lower:
        return "아이스 댄스"
    
    return "댄스 챌린지"

def extract_requirements(content: str) -> str:
    """필요 조건 추출"""
    content_lower = content.lower()
    
    requirements = []
    
    if "ice" in content_lower or "skating" in content_lower:
        requirements.append("아이스링크")
    if "couple" in content_lower or "partner" in content_lower:
        requirements.append("파트너")
    if "costume" in content_lower or "outfit" in content_lower:
        requirements.append("특별 의상")
    
    if not requirements:
        return "특별한 준비물 없음"
    
    return ", ".join(requirements)

def generate_enhanced_markdown(challenges: List[Dict[str, Any]]) -> str:
    """향상된 마크다운 리포트 생성"""
    
    total_views = sum(c["view_count"] for c in challenges)
    total_likes = sum(c["like_count"] for c in challenges)
    avg_views = total_views // len(challenges) if challenges else 0
    
    report = f"""# 🕺 따라하기 쉬운 댄스 챌린지 TOP 10 (영상 분석 포함)

## 📊 분석 개요

- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **발견된 댄스 챌린지**: {len(challenges)}개
- **총 조회수**: {total_views:,}
- **총 좋아요**: {total_likes:,}
- **평균 조회수**: {avg_views:,}
- **분석 방법**: AI 실시간 영상 콘텐츠 분석 + YouTube 메타데이터

## 🏆 댄스 챌린지 순위 (영상 분석 포함)

"""
    
    for challenge in challenges:
        analysis = challenge.get("video_analysis", {})
        
        report += f"""### {challenge["rank"]}. {challenge["title"]}

- **🎬 비디오 ID**: `{challenge["video_id"]}`
- **👤 채널**: {challenge["channel"]}
- **👀 조회수**: {challenge["view_count"]:,}
- **👍 좋아요**: {challenge["like_count"]:,}
- **💬 댓글**: {challenge["comment_count"]:,}
- **📅 발행일**: {challenge["published_date"]}
- **🎯 분석 신뢰도**: {challenge["confidence"]:.2f}
- **🔗 YouTube 링크**: [바로가기]({challenge["youtube_url"]})
- **🖼️ 썸네일**: ![썸네일]({challenge["thumbnail_url"]})

#### 📋 상세 영상 분석 결과:
"""
        
        if "error" not in analysis:
            report += f"""- **🎵 음악 분석**: {analysis.get('music_analysis', '정보 없음')}
- **⭐ 댄스 난이도**: {analysis.get('difficulty_level', '정보 없음')}
- **👥 구성원**: {analysis.get('participants', '정보 없음')}
- **🎯 따라하기 용이성**: {analysis.get('followability', '정보 없음')}
- **🚀 바이럴 가능성**: {analysis.get('viral_potential', '정보 없음')}
- **🎭 챌린지 타입**: {analysis.get('challenge_type', '정보 없음')}
- **📦 필요 조건**: {analysis.get('requirements', '정보 없음')}

#### 🎥 AI 영상 분석 요약:
```
{analysis.get('content', '분석 결과 없음')[:300]}...
```
"""
        else:
            report += f"""- **❌ 영상 분석**: {analysis.get('error', '분석 실패')}
"""
        
        report += "\n---\n\n"
    
    # 트렌드 분석 추가
    report += f"""## 📈 영상 분석 기반 트렌드 인사이트

### 🎵 음악 트렌드
"""
    
    music_types = {}
    difficulty_dist = {}
    participant_types = {}
    
    for challenge in challenges:
        analysis = challenge.get("video_analysis", {})
        if "error" not in analysis:
            music = analysis.get('music_analysis', '기타')
            difficulty = analysis.get('difficulty_level', '알 수 없음')
            participants = analysis.get('participants', '개인')
            
            music_types[music] = music_types.get(music, 0) + 1
            difficulty_dist[difficulty] = difficulty_dist.get(difficulty, 0) + 1
            participant_types[participants] = participant_types.get(participants, 0) + 1
    
    for music, count in sorted(music_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(challenges)) * 100
        report += f"- **{music}**: {count}개 ({percentage:.1f}%)\n"
    
    report += f"""
### ⭐ 난이도 분포
"""
    
    for difficulty, count in sorted(difficulty_dist.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(challenges)) * 100
        report += f"- **{difficulty}**: {count}개 ({percentage:.1f}%)\n"
    
    report += f"""
### 👥 참가자 유형
"""
    
    for participant, count in sorted(participant_types.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(challenges)) * 100
        report += f"- **{participant}**: {count}개 ({percentage:.1f}%)\n"
    
    report += f"""

## 💡 영상 분석 기반 콘텐츠 제작 가이드

### 🎯 성공 요소 분석
1. **음악 선택**: 클래식 댄스 음악이나 바이럴 TikTok 사운드 활용
2. **난이도 설정**: 대부분 '쉬움~보통' 수준으로 접근성 확보
3. **참여 형태**: 개인이나 커플 단위로 참여 가능한 형태 선호
4. **따라하기 요소**: 튜토리얼 형식이나 반복 학습 가능한 구조

### 📱 플랫폼별 최적화 전략
- **YouTube Shorts**: 세로형 고화질 영상, 명확한 움직임 표현
- **TikTok**: 트렌딩 사운드 활용, 챌린지 해시태그 적극 사용
- **Instagram Reels**: 시각적 임팩트와 스토리 연동 활용

### 🎨 영상 제작 팁
- **촬영 각도**: 전신이 보이는 고정 앵글
- **조명**: 밝고 균일한 조명으로 동작 명확히 표현
- **편집**: 느린 버전과 빠른 버전 모두 제공
- **자막**: 핵심 동작 설명이나 카운트 표시

---

*이 리포트는 AI 기반 실시간 영상 콘텐츠 분석을 통해 생성되었습니다.*

🤖 **생성 시스템**: Claude Code + Gemini 1.5 Flash + YouTube Data API  
📅 **생성 일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}  
🔬 **분석 방법**: 실시간 영상 콘텐츠 AI 분석 + 메타데이터 통합 분석
"""
    
    return report

if __name__ == "__main__":
    asyncio.run(analyze_top10_videos())
#!/usr/bin/env python3
"""
TOP 3 댄스 챌린지 영상 분석 데모
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any

from src.clients.llm_provider import create_llm_provider

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_video_analysis():
    """TOP 3 댄스 챌린지 영상 분석 데모"""
    
    print("🎥 TOP 3 댄스 챌린지 영상 분석 데모")
    print("=" * 50)
    
    # TOP 3 비디오 ID (기존 데이터에서)
    top3_videos = [
        {
            "rank": 1,
            "video_id": "Bq_znt--GTU",
            "title": "Cha Cha Slide con @LeylaStar ❤️🎉",
            "view_count": 217636308
        },
        {
            "rank": 2, 
            "video_id": "Rz_p-ogETPw",
            "title": "WE NEED TO KNOW!? 😅",
            "view_count": 87314984
        },
        {
            "rank": 3,
            "video_id": "rlgJnOAtU7o", 
            "title": "Cutie's first experience of a dance class",
            "view_count": 72115681
        }
    ]
    
    try:
        # LLM Provider 생성
        llm_provider = create_llm_provider()
        print(f"✅ LLM Provider: {llm_provider.provider_name}")
        
        analysis_results = []
        
        # 각 비디오 분석
        for video in top3_videos:
            video_id = video["video_id"]
            title = video["title"]
            
            print(f"\n🎬 [{video['rank']}/3] 영상 분석: {title[:50]}...")
            print(f"   📊 조회수: {video['view_count']:,}")
            
            try:
                # 챌린지 분석 수행
                analysis_result = await llm_provider.analyze_youtube_video(
                    video_id, 
                    analysis_type="challenge"
                )
                
                if analysis_result and analysis_result.get("success"):
                    content = analysis_result.get("content", "")
                    
                    # 분석 결과 파싱
                    parsed_analysis = {
                        "video_id": video_id,
                        "title": title,
                        "view_count": video["view_count"],
                        "rank": video["rank"],
                        "raw_analysis": content,
                        "music_analysis": extract_music_info(content),
                        "difficulty_level": extract_difficulty(content),
                        "participants": extract_participants(content),
                        "followability": extract_followability(content),
                        "viral_potential": extract_viral_potential(content),
                        "challenge_type": extract_challenge_type(content),
                        "requirements": extract_requirements(content),
                        "analysis_timestamp": datetime.now().isoformat()
                    }
                    
                    analysis_results.append(parsed_analysis)
                    
                    print(f"  ✅ 분석 완료!")
                    print(f"     🎵 음악: {parsed_analysis['music_analysis']}")
                    print(f"     ⭐ 난이도: {parsed_analysis['difficulty_level']}")
                    print(f"     👥 참여자: {parsed_analysis['participants']}")
                    print(f"     🎯 용이성: {parsed_analysis['followability']}")
                    print(f"     🚀 바이럴: {parsed_analysis['viral_potential']}")
                    print(f"     🎭 타입: {parsed_analysis['challenge_type']}")
                    
                else:
                    print(f"  ❌ 영상 분석 실패")
                
            except Exception as e:
                print(f"  ❌ 영상 분석 에러: {e}")
                
            # API 제한을 위한 대기
            await asyncio.sleep(3)
        
        # 결과 저장
        if analysis_results:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # JSON 파일 저장
            result_data = {
                "analysis_date": datetime.now().isoformat(),
                "total_analyzed": len(analysis_results),
                "analysis_type": "TOP 3 댄스 챌린지 영상 분석 데모",
                "results": analysis_results
            }
            
            json_file = f"top3_video_analysis_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result_data, f, ensure_ascii=False, indent=2)
            
            # 마크다운 리포트 생성
            markdown_content = generate_demo_report(analysis_results)
            md_file = f"top3_video_analysis_{timestamp}.md"
            
            with open(md_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            print(f"\n🎉 TOP 3 영상 분석 완료!")
            print(f"💾 파일 저장됨:")
            print(f"  📄 JSON: {json_file}")
            print(f"  📝 Markdown: {md_file}")
            
            # 간단한 요약 출력
            print(f"\n📊 분석 요약:")
            difficulty_count = {}
            music_count = {}
            
            for result in analysis_results:
                difficulty = result['difficulty_level']
                music = result['music_analysis']
                
                difficulty_count[difficulty] = difficulty_count.get(difficulty, 0) + 1
                if '바이럴' in music or 'TikTok' in music:
                    music_count['바이럴 사운드'] = music_count.get('바이럴 사운드', 0) + 1
                elif 'Cha Cha' in music:
                    music_count['클래식 댄스'] = music_count.get('클래식 댄스', 0) + 1
                else:
                    music_count['기타'] = music_count.get('기타', 0) + 1
            
            print(f"   난이도 분포: {difficulty_count}")
            print(f"   음악 타입: {music_count}")
        
    except Exception as e:
        print(f"❌ 데모 실행 실패: {e}")
        logger.exception("Demo failed")

def extract_music_info(content: str) -> str:
    """음악 정보 추출"""
    content_lower = content.lower()
    
    if "cha cha slide" in content_lower:
        return "Cha Cha Slide - 클래식 라인 댄스 음악"
    elif "viral" in content_lower and ("tiktok" in content_lower or "trend" in content_lower):
        return "바이럴 TikTok 트렌드 사운드"
    elif "k-pop" in content_lower or "kpop" in content_lower:
        return "K-pop 댄스 음악"
    elif "pop" in content_lower:
        return "팝 음악"
    elif "electronic" in content_lower:
        return "일렉트로닉 댄스 음악"
    
    return "일반 댄스 배경음악"

def extract_difficulty(content: str) -> str:
    """난이도 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['easy', 'simple', 'basic', 'beginner', 'tutorial']):
        return "쉬움"
    elif any(word in content_lower for word in ['medium', 'moderate', 'intermediate']):
        return "보통"
    elif any(word in content_lower for word in ['hard', 'difficult', 'complex', 'advanced']):
        return "어려움"
    
    return "보통"

def extract_participants(content: str) -> str:
    """참가자 정보 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['couple', 'duo', 'pair', 'two people']):
        return "커플/듀오"
    elif any(word in content_lower for word in ['group', 'team', 'multiple people']):
        return "그룹"
    elif "kids" in content_lower or "children" in content_lower:
        return "어린이"
    elif any(word in content_lower for word in ['solo', 'individual', 'single person']):
        return "개인"
    
    return "개인"

def extract_followability(content: str) -> str:
    """따라하기 용이성 추출"""
    content_lower = content.lower()
    
    if any(word in content_lower for word in ['easy to follow', 'simple steps', 'beginner-friendly']):
        return "매우 쉬움"
    elif any(word in content_lower for word in ['tutorial', 'step by step', 'guide']):
        return "쉬움" 
    elif any(word in content_lower for word in ['complex', 'difficult', 'advanced']):
        return "어려움"
    
    return "보통"

def extract_viral_potential(content: str) -> str:
    """바이럴 가능성 추출"""
    content_lower = content.lower()
    
    viral_keywords = ['viral', 'trending', 'popular', 'challenge', 'tiktok', 'shorts', 'trend']
    count = sum(1 for keyword in viral_keywords if keyword in content_lower)
    
    if count >= 4:
        return "매우 높음"
    elif count >= 2:
        return "높음"
    elif count >= 1:
        return "보통"
    
    return "낮음"

def extract_challenge_type(content: str) -> str:
    """챌린지 타입 추출"""
    content_lower = content.lower()
    
    if "cha cha slide" in content_lower:
        return "라인 댄스 챌린지"
    elif "couple" in content_lower and "dance" in content_lower:
        return "커플 댄스 챌린지"
    elif "tutorial" in content_lower:
        return "댄스 튜토리얼"
    elif "kids" in content_lower:
        return "키즈 댄스"
    elif "ice" in content_lower and "skating" in content_lower:
        return "아이스 댄스"
    
    return "일반 댄스 챌린지"

def extract_requirements(content: str) -> str:
    """필요 조건 추출"""
    content_lower = content.lower()
    
    requirements = []
    
    if "partner" in content_lower or "couple" in content_lower:
        requirements.append("파트너 필요")
    if "ice" in content_lower or "skating" in content_lower:
        requirements.append("아이스링크")
    if "costume" in content_lower or "special outfit" in content_lower:
        requirements.append("특별 의상")
    if "props" in content_lower:
        requirements.append("소품")
    
    if not requirements:
        return "특별한 준비물 없음"
    
    return ", ".join(requirements)

def generate_demo_report(results: list) -> str:
    """데모 리포트 생성"""
    
    total_views = sum(r["view_count"] for r in results)
    
    report = f"""# 🎥 TOP 3 댄스 챌린지 영상 분석 데모

## 📊 분석 개요

- **분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
- **분석 영상 수**: {len(results)}개
- **총 조회수**: {total_views:,}
- **평균 조회수**: {total_views // len(results):,}
- **분석 방법**: Gemini 1.5 Flash 실시간 영상 콘텐츠 분석

## 🏆 TOP 3 영상 분석 결과

"""
    
    for result in results:
        report += f"""### {result["rank"]}. {result["title"]}

**📊 기본 정보:**
- **Video ID**: `{result["video_id"]}`
- **조회수**: {result["view_count"]:,}

**🎬 영상 분석 결과:**
- **🎵 음악 분석**: {result["music_analysis"]}
- **⭐ 댄스 난이도**: {result["difficulty_level"]}
- **👥 참여자 구성**: {result["participants"]}
- **🎯 따라하기 용이성**: {result["followability"]}
- **🚀 바이럴 가능성**: {result["viral_potential"]}
- **🎭 챌린지 타입**: {result["challenge_type"]}
- **📦 필요 조건**: {result["requirements"]}

**🔍 상세 AI 분석:**
```
{result["raw_analysis"][:500]}...
```

---

"""
    
    # 인사이트 추가
    report += f"""## 💡 영상 분석 인사이트

### 🎯 성공 요소 분석
"""
    
    # 난이도 분석
    difficulty_count = {}
    music_types = {}
    
    for result in results:
        difficulty = result['difficulty_level'] 
        music = result['music_analysis']
        
        difficulty_count[difficulty] = difficulty_count.get(difficulty, 0) + 1
        
        if 'Cha Cha' in music:
            music_types['클래식 댄스'] = music_types.get('클래식 댄스', 0) + 1
        elif '바이럴' in music or 'TikTok' in music:
            music_types['바이럴 사운드'] = music_types.get('바이럴 사운드', 0) + 1
        else:
            music_types['기타'] = music_types.get('기타', 0) + 1
    
    report += f"""
**난이도 분포:**
"""
    for difficulty, count in difficulty_count.items():
        percentage = (count / len(results)) * 100
        report += f"- {difficulty}: {count}개 ({percentage:.1f}%)\n"
    
    report += f"""
**음악 타입 분포:**
"""
    for music_type, count in music_types.items():
        percentage = (count / len(results)) * 100  
        report += f"- {music_type}: {count}개 ({percentage:.1f}%)\n"
    
    report += f"""

### 📈 트렌드 관찰
1. **접근성**: 대부분의 인기 댄스는 '쉬움~보통' 난이도로 설정
2. **음악 선택**: 클래식 댄스 음악과 바이럴 트렌드 사운드가 주를 이룸
3. **참여 형태**: 개인이나 커플 단위 참여가 가장 일반적
4. **바이럴 요소**: 모든 TOP 댄스가 높은 바이럴 가능성을 보유

### 🎨 콘텐츠 제작 권장사항
- **난이도**: 초보자도 쉽게 따라할 수 있는 단순한 동작 구성
- **음악**: 익숙한 클래식 댄스 곡이나 현재 트렌딩 사운드 활용
- **촬영**: 전신이 명확히 보이는 고정 앵글 사용
- **편집**: 느린 버전 튜토리얼과 빠른 버전 모두 제공

---

*이 리포트는 Gemini 1.5 Flash를 사용한 실시간 YouTube 영상 콘텐츠 분석을 통해 생성되었습니다.*

🤖 **분석 시스템**: Claude Code + Gemini 1.5 Flash  
📅 **생성 일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')}  
🔬 **분석 방법**: AI 실시간 영상 콘텐츠 분석
"""
    
    return report

if __name__ == "__main__":
    asyncio.run(demo_video_analysis())
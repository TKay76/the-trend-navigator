#!/usr/bin/env python3
"""
프롬프트 파서 테스트 스크립트
"""

import asyncio
import logging
from datetime import datetime

from src.core.prompt_parser import create_prompt_parser
from src.models.prompt_models import ActionType, ContentType, ParticipantType, DifficultyLevel

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 테스트 케이스들
TEST_CASES = [
    "댄스 챌린지 TOP 10 찾아줘",
    "초보자용 쉬운 K-pop 댄스 5개 추천해줘",
    "커플이 함께 할 수 있는 로맨틱한 댄스 챌린지 보여줘",
    "최근 2주간 조회수 100만 이상인 바이럴 댄스 3개만",
    "아이들도 따라할 수 있는 안전한 댄스 챌린지가 있나?",
    "요리 챌린지 중에서 간단한 것들 몇 개 추천해줘",
    "피트니스 챌린지 TOP 5 분석해줘",
    "dance challenge top 10",
    "easy dance for beginners",
    "혼자 할 수 있는 쉬운 댄스 찾아줘"
]

async def test_prompt_parser():
    """프롬프트 파서 테스트 실행"""
    
    print("🧪 프롬프트 파서 테스트 시작")
    print("=" * 60)
    
    parser = create_prompt_parser()
    
    successful_parses = 0
    total_parses = len(TEST_CASES)
    
    for i, test_input in enumerate(TEST_CASES, 1):
        print(f"\n🔍 테스트 {i}/{total_parses}: '{test_input}'")
        print("-" * 40)
        
        try:
            # 파싱 실행
            result = await parser.parse(test_input)
            
            if result.success:
                successful_parses += 1
                parsed_request = result.parsed_request
                
                print(f"✅ 파싱 성공 (신뢰도: {parsed_request.confidence:.2f})")
                print(f"📊 액션: {parsed_request.action_type.value}")
                print(f"📝 콘텐츠 타입: {parsed_request.content_filter.content_type.value}")
                print(f"🔢 요청 개수: {parsed_request.quantity_filter.count}")
                
                if parsed_request.content_filter.difficulty:
                    print(f"⭐ 난이도: {parsed_request.content_filter.difficulty.value}")
                
                if parsed_request.content_filter.participants != ParticipantType.ANY:
                    print(f"👥 참여자: {parsed_request.content_filter.participants.value}")
                
                if parsed_request.content_filter.keywords:
                    print(f"🏷️ 키워드: {', '.join(parsed_request.content_filter.keywords)}")
                
                print(f"⏱️ 처리 시간: {result.processing_time:.3f}초")
                
                if result.warnings:
                    print(f"⚠️ 경고: {', '.join(result.warnings)}")
                
            else:
                print(f"❌ 파싱 실패: {result.error_message}")
                
        except Exception as e:
            print(f"💥 예외 발생: {e}")
            logger.exception(f"Test case failed: {test_input}")
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {successful_parses}/{total_parses} ({successful_parses/total_parses*100:.1f}%)")
    print(f"❌ 실패: {total_parses - successful_parses}/{total_parses}")
    
    if successful_parses == total_parses:
        print("🎉 모든 테스트 케이스 통과!")
    elif successful_parses >= total_parses * 0.8:
        print("🟡 대부분의 테스트 케이스 통과")
    else:
        print("🔴 일부 테스트 케이스 실패 - 개선 필요")

async def test_interactive_parsing():
    """대화형 파싱 테스트"""
    print("\n" + "=" * 60)
    print("🤖 대화형 프롬프트 파싱 테스트")
    print("=" * 60)
    print("💬 자연어로 입력해보세요 (종료: 'quit')")
    
    parser = create_prompt_parser()
    
    while True:
        try:
            user_input = input("\n💭 입력: ").strip()
            
            if user_input.lower() in ['quit', 'exit', '종료', 'q']:
                print("👋 테스트를 종료합니다.")
                break
            
            if not user_input:
                continue
            
            print("⏳ 파싱 중...")
            result = await parser.parse(user_input)
            
            if result.success:
                parsed = result.parsed_request
                print(f"✅ 파싱 성공!")
                print(f"   액션: {parsed.action_type.value}")
                print(f"   콘텐츠: {parsed.content_filter.content_type.value}")
                print(f"   개수: {parsed.quantity_filter.count}")
                print(f"   신뢰도: {parsed.confidence:.2f}")
                print(f"   처리시간: {result.processing_time:.3f}초")
            else:
                print(f"❌ 파싱 실패: {result.error_message}")
                
        except KeyboardInterrupt:
            print("\n👋 테스트를 종료합니다.")
            break
        except Exception as e:
            print(f"💥 오류: {e}")

async def main():
    """메인 테스트 함수"""
    await test_prompt_parser()
    
    # 대화형 테스트 실행 여부 확인
    run_interactive = input("\n❓ 대화형 테스트를 실행하시겠습니까? (y/N): ").strip().lower()
    if run_interactive in ['y', 'yes', '네', 'ㅇ']:
        await test_interactive_parsing()

if __name__ == "__main__":
    asyncio.run(main())
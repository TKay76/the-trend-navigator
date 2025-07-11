#!/usr/bin/env python3
"""
범용 콘텐츠 분석 시스템 테스트
"""

import asyncio
import logging
import sys
import os

# Add src directory to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.prompt_parser import create_prompt_parser
from src.plugins.plugin_manager import create_plugin_manager
from src.plugins.base_plugin import AnalysisContext

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 다양한 콘텐츠 타입 테스트 케이스들
UNIVERSAL_TEST_CASES = [
    "댄스 챌린지 TOP 10 찾아줘",
    "요리 레시피 3개 추천해줘",
    "피트니스 운동 5개 분석해줘",
    "뷰티 메이크업 챌린지 찾아줘",
    "게임 플레이 영상 추천해줘",
    "DIY 만들기 튜토리얼 보여줘",
    "기술 리뷰 영상 분석해줘",
    "일상 브이로그 추천해줘",
    "쉬운 홈트레이닝 찾아줘",
    "간단한 베이킹 레시피 3개"
]

async def test_universal_content_analysis():
    """범용 콘텐츠 분석 시스템 테스트"""
    
    print("🚀 범용 콘텐츠 분석 시스템 테스트 시작")
    print("=" * 60)
    
    # 프롬프트 파서와 플러그인 매니저 초기화
    parser = create_prompt_parser()
    plugin_manager = create_plugin_manager()
    
    # 플러그인 발견 및 로딩
    print("🔧 플러그인 시스템 초기화 중...")
    plugin_results = await plugin_manager.discover_and_load_plugins()
    print(f"✅ 플러그인 로딩 완료: {plugin_results['summary']}")
    
    # 등록된 플러그인 목록 출력
    plugins = plugin_manager.registry.list_plugins()
    print(f"\n📦 등록된 플러그인 ({len(plugins)}개):")
    for plugin in plugins:
        status = "✅ Ready" if plugin["initialized"] else "❌ Not Ready"
        print(f"  • {plugin['name']} v{plugin['version']} - {status}")
        print(f"    지원 콘텐츠: {', '.join(plugin['content_types'])}")
    
    print("\n" + "=" * 60)
    print("🧪 콘텐츠 타입 감지 테스트")
    print("=" * 60)
    
    successful_parses = 0
    
    for i, test_input in enumerate(UNIVERSAL_TEST_CASES, 1):
        print(f"\n🔍 테스트 {i}/{len(UNIVERSAL_TEST_CASES)}: '{test_input}'")
        print("-" * 40)
        
        try:
            # 1. 프롬프트 파싱
            parsing_result = await parser.parse(test_input)
            
            if parsing_result.success:
                parsed_request = parsing_result.parsed_request
                content_type = parsed_request.content_filter.content_type
                
                print(f"✅ 파싱 성공 (신뢰도: {parsed_request.confidence:.2f})")
                print(f"📝 감지된 콘텐츠 타입: {content_type.value}")
                print(f"🎯 액션: {parsed_request.action_type.value}")
                
                # 2. 적합한 플러그인 찾기
                best_plugin = plugin_manager.registry.find_best_plugin(content_type, parsed_request)
                
                if best_plugin:
                    confidence = best_plugin.can_handle(content_type, parsed_request)
                    print(f"🔌 선택된 플러그인: {best_plugin.metadata.name}")
                    print(f"🎯 플러그인 신뢰도: {confidence:.2f}")
                    
                    # 3. 키워드 최적화 테스트
                    original_keywords = parsed_request.content_filter.keywords
                    optimized_keywords = await best_plugin.optimize_search_keywords(
                        original_keywords,
                        AnalysisContext(
                            user_request=parsed_request,
                            search_keywords=original_keywords
                        )
                    )
                    
                    if optimized_keywords != original_keywords:
                        print(f"🔍 키워드 최적화:")
                        print(f"  원본: {original_keywords}")
                        print(f"  최적화: {optimized_keywords}")
                
                else:
                    print("❌ 적합한 플러그인을 찾을 수 없음")
                
                successful_parses += 1
            else:
                print(f"❌ 파싱 실패: {parsing_result.error_message}")
                
        except Exception as e:
            print(f"💥 예외 발생: {e}")
            logger.exception(f"Test case failed: {test_input}")
    
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"✅ 성공: {successful_parses}/{len(UNIVERSAL_TEST_CASES)} ({successful_parses/len(UNIVERSAL_TEST_CASES)*100:.1f}%)")
    print(f"❌ 실패: {len(UNIVERSAL_TEST_CASES) - successful_parses}/{len(UNIVERSAL_TEST_CASES)}")
    
    if successful_parses == len(UNIVERSAL_TEST_CASES):
        print("🎉 모든 콘텐츠 타입 테스트 통과!")
    elif successful_parses >= len(UNIVERSAL_TEST_CASES) * 0.8:
        print("🟡 대부분의 콘텐츠 타입 테스트 통과")
    else:
        print("🔴 일부 콘텐츠 타입 테스트 실패 - 개선 필요")
    
    # 플러그인 헬스 체크
    print("\n" + "=" * 60)
    print("🏥 플러그인 헬스 체크")
    print("=" * 60)
    
    health_results = await plugin_manager.health_check_all_plugins()
    for plugin_name, health_info in health_results["plugins"].items():
        status = health_info.get("status", "unknown")
        if status == "healthy":
            print(f"✅ {plugin_name}: 정상")
        else:
            print(f"❌ {plugin_name}: {status}")
            if "error" in health_info:
                print(f"   오류: {health_info['error']}")

async def main():
    """메인 테스트 함수"""
    await test_universal_content_analysis()

if __name__ == "__main__":
    asyncio.run(main())
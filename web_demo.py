#!/usr/bin/env python3
"""
YouTube Trends Analysis Web Service Demo
실행: python3 web_demo.py
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Add src directory to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.services.natural_query_service import create_natural_query_service
from src.plugins.plugin_manager import create_plugin_manager

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_web_service():
    """웹 서비스 데모"""
    print("🌐 YouTube Trends Analysis Web Service Demo")
    print("=" * 60)
    
    # 서비스 초기화
    print("🔧 서비스 초기화 중...")
    natural_query_service = create_natural_query_service()
    plugin_manager = create_plugin_manager()
    
    # 플러그인 초기화
    plugin_results = await plugin_manager.discover_and_load_plugins()
    print(f"✅ 플러그인 초기화 완료: {plugin_results['summary']}")
    
    # 플러그인 목록 출력
    plugins = plugin_manager.registry.list_plugins()
    print(f"\n📦 등록된 플러그인 ({len(plugins)}개):")
    for plugin in plugins:
        status = "✅" if plugin["initialized"] else "❌"
        print(f"  {status} {plugin['name']} v{plugin['version']}")
        print(f"     지원 콘텐츠: {', '.join(plugin['content_types'])}")
    
    # 데모 쿼리들
    demo_queries = [
        "댄스 챌린지 TOP 3 찾아줘",
        "쉬운 요리 레시피 2개 추천해줘",
        "홈트레이닝 운동 추천해줘",
    ]
    
    print(f"\n🧪 데모 쿼리 테스트")
    print("=" * 60)
    
    for i, query in enumerate(demo_queries, 1):
        print(f"\n🔍 쿼리 {i}: '{query}'")
        print("-" * 40)
        
        start_time = datetime.now()
        
        try:
            # 쿼리 처리
            response = await natural_query_service.process_query(query)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            if response.success:
                print(f"✅ 처리 성공 (시간: {processing_time:.2f}초)")
                print(f"📊 결과 수: {len(response.results)}")
                print(f"🎯 요약: {response.summary[:100]}...")
                
                if response.metadata.get('recommendations'):
                    rec_count = len(response.metadata['recommendations'])
                    print(f"💡 추천 콘텐츠: {rec_count}개")
                
            else:
                print(f"❌ 처리 실패: {response.error_message}")
                
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            print(f"💥 오류 발생: {e}")
    
    print(f"\n📊 서비스 통계")
    print("=" * 60)
    stats = natural_query_service.get_service_stats()
    print(f"총 쿼리: {stats.get('total_queries', 0)}")
    print(f"성공: {stats.get('successful_queries', 0)}")
    print(f"실패: {stats.get('failed_queries', 0)}")
    print(f"평균 처리 시간: {stats.get('avg_processing_time', 0):.2f}초")
    
    # 플러그인 헬스 체크
    print(f"\n🏥 플러그인 헬스 체크")
    print("=" * 60)
    health_results = await plugin_manager.health_check_all_plugins()
    
    for plugin_name, health in health_results["plugins"].items():
        status = health.get("status", "unknown")
        if status == "healthy":
            print(f"✅ {plugin_name}: 정상")
        else:
            print(f"❌ {plugin_name}: {status}")
    
    print(f"\n🎉 데모 완료!")
    print("실제 웹 서버를 시작하려면: python3 web_server.py")
    print("브라우저에서 http://localhost:8000 방문")

async def main():
    """메인 함수"""
    await demo_web_service()

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
YouTube Trends Analysis Web Server
실행: python3 web_server.py
"""

import sys
import os
import uvicorn

# Add src directory to Python path for proper imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.settings import get_settings

def main():
    """웹 서버 실행"""
    settings = get_settings()
    
    print("🚀 YouTube Trends Analysis Web Server 시작")
    print("=" * 50)
    print(f"환경: {settings.environment}")
    print(f"주소: http://localhost:8000")
    print(f"WSL 주소: http://172.21.190.87:8000")
    print(f"API 문서: http://localhost:8000/docs")
    print("=" * 50)
    print("서버를 중지하려면 Ctrl+C를 누르세요.")
    print()
    
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False,
        log_level="info",
        access_log=True
    )

if __name__ == "__main__":
    main()
# 🎯 YouTube Shorts Trend Analysis - Project Planning

## 📋 Project Overview
YouTube Shorts 트렌드 분석 시스템 - AI 기반 비디오 분류 및 트렌드 분석 플랫폼

## 🏗️ Architecture
- **Collector Agent**: YouTube API를 통한 데이터 수집
- **Analyzer Agent**: AI 기반 비디오 분류 및 분석
- **Web API**: FastAPI 기반 RESTful API
- **Plugin System**: 확장 가능한 콘텐츠 분석 플러그인

## 📁 Core Structure
```
src/
├── agents/          # 데이터 수집 및 분석 에이전트
├── api/            # FastAPI 웹 서버
├── clients/        # 외부 API 클라이언트 (YouTube, LLM)
├── core/           # 핵심 유틸리티 및 설정
├── models/         # Pydantic 데이터 모델
├── plugins/        # 콘텐츠 분석 플러그인
└── services/       # 비즈니스 로직 서비스
```

## 🎨 Code Style
- Python 3.12+ with type hints
- Pydantic models for data validation
- FastAPI for web services
- Async/await patterns
- PEP8 formatting with black
- Google-style docstrings

## 🧪 Testing Strategy
- Pytest for unit tests
- 80%+ code coverage
- Test files in `/tests` directory
- Mock external APIs (YouTube, LLM)
- Integration tests for full pipeline

## 🔧 Key Constraints
- YouTube API quota: 10,000 units/day
- File size limit: 500 lines max
- Model-first approach with Pydantic
- Separate collector/analyzer responsibilities
- Use venv_linux for Python execution
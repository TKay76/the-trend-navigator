# examples/models/data_model_example.py

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from datetime import datetime

class VideoStatistics(BaseModel):
    """영상 통계 정보 모델"""
    view_count: int = Field(0, description="조회수")
    like_count: int = Field(0, description="좋아요 수")
    comment_count: int = Field(0, description="댓글 수")

class VideoSnippet(BaseModel):
    """영상 기본 정보 모델"""
    title: str = Field(..., description="영상 제목")
    description: str = Field("", description="영상 설명")
    published_at: datetime = Field(..., description="게시일")
    channel_title: str = Field("", description="채널명")
    thumbnail_url: HttpUrl = Field(..., alias="thumbnails.default.url")

class RawYouTubeVideo(BaseModel):
    """
    YouTube API로부터 받은 원본 데이터 구조.
    향후 우리 시스템에 맞게 한 번 더 가공될 예정입니다.
    """
    video_id: str = Field(..., alias="id", description="유튜브 영상 ID")
    snippet: VideoSnippet
    statistics: Optional[VideoStatistics] = None

    class Config:
        populate_by_name = True # alias 사용을 위함

# 예제 사용법:
# 이 모델은 API 응답 데이터를 검증하고 객체로 변환하는 데 사용됩니다.
# 실제로는 youtube_client에서 이 모델을 사용하여 반환 타입을 지정합니다.
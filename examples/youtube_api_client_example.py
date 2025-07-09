# examples/clients/youtube_api_client_example.py

import httpx
import os
from typing import List, Dict, Any, Optional

# --- 환경 변수에서 API 키를 안전하게 불러옵니다. ---
# 실제 프로젝트에서는 core/settings.py에서 이 로직을 관리합니다.
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY_EXAMPLE")

# --- API의 기본 URL을 상수로 정의합니다. ---
YOUTUBE_API_BASE_URL = "https://www.googleapis.com/youtube/v3"

class YouTubeAPIClient:
    """
    YouTube Data API와 통신하기 위한 비동기 클라이언트 예제.
    """
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("YouTube API 키가 필요합니다.")
        self.api_key = api_key
        self.client = httpx.AsyncClient()

    async def fetch_popular_videos(
        self, region_code: str = "US", max_results: int = 10
    ) -> Optional[List[Dict[str, Any]]]:
        """
        특정 지역의 인기 동영상 목록을 가져옵니다.

        Args:
            region_code (str): 국가 코드 (ISO 3166-1 alpha-2).
            max_results (int): 가져올 결과의 최대 개수.

        Returns:
            Optional[List[Dict[str, Any]]]: 동영상 데이터 목록 또는 실패 시 None.
        """
        # Quota Cost: 1 (API 할당량 비용을 주석으로 명시하는 습관)
        params = {
            "part": "snippet,contentDetails,statistics",
            "chart": "mostPopular",
            "regionCode": region_code,
            "maxResults": max_results,
            "videoCategoryId": "17",  # "Sports" 카테고리 예시 (실제로는 더 동적으로)
            "key": self.api_key,
        }
        try:
            response = await self.client.get(f"{YOUTUBE_API_BASE_URL}/videos", params=params)
            response.raise_for_status()  # 2xx 이외의 상태 코드에 대해 예외 발생
            return response.json().get("items", [])
        except httpx.HTTPStatusError as e:
            print(f"API 오류 발생: {e.response.status_code} - {e.response.text}")
            return None
        except httpx.RequestError as e:
            print(f"네트워크 오류 발생: {e}")
            return None

# 예제 사용법 (실제 프로젝트에서는 cli.py나 agent에서 호출)
async def main():
    if not YOUTUBE_API_KEY:
        print("환경변수에서 YOUTUBE_API_KEY_EXAMPLE을 설정해주세요.")
        return

    client = YouTubeAPIClient(api_key=YOUTUBE_API_KEY)
    videos = await client.fetch_popular_videos(region_code="KR", max_results=5)

    if videos:
        print(f"한국 인기 동영상 {len(videos)}개 수집 성공!")
        for video in videos:
            print(f"- 제목: {video['snippet']['title']}")
    else:
        print("동영상 수집 실패.")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
# examples/agents/simple_processing_agent_example.py

from pydantic import BaseModel, Field
from typing import List

# --- 입력 데이터 모델 정의 (예: Data Collector Agent의 출력) ---
class InputData(BaseModel):
    source: str
    content: str

# --- 출력 데이터 모델 정의 ---
class ProcessedData(BaseModel):
    source: str
    content_length: int = Field(..., description="입력된 컨텐츠의 길이")
    processed_by: str = Field("SimpleProcessingAgentExample", description="처리한 에이전트 이름")

class SimpleProcessingAgent:
    """
    입력 데이터를 받아 간단한 처리를 수행하는 에이전트 예제.
    """
    def __init__(self, agent_name: str = "Processor"):
        self.agent_name = agent_name
        print(f"[{self.agent_name}] 에이전트가 준비되었습니다.")

    def run(self, data: List[InputData]) -> List[ProcessedData]:
        """
        입력된 데이터 목록을 처리하여 결과 목록을 반환합니다.
        (실제 Pydantic AI 에이전트는 비동기로 작동하지만, 여기서는 기본 구조를 보여주기 위해 동기 함수로 작성)
        """
        print(f"[{self.agent_name}] {len(data)}개의 데이터 처리 시작...")
        results = []
        for item in data:
            processed_item = ProcessedData(
                source=item.source,
                content_length=len(item.content)
            )
            results.append(processed_item)
        print(f"[{self.agent_name}] 처리 완료!")
        return results

# 예제 사용법
def main():
    # 1. 가짜 입력 데이터 생성 (마치 Collector Agent가 수집한 것처럼)
    dummy_inputs = [
        InputData(source="youtube", content="첫 번째 유튜브 영상 설명입니다."),
        InputData(source="tiktok", content="틱톡 영상 설명입니다. 이것은 조금 더 깁니다."),
    ]

    # 2. 에이전트 생성 및 실행
    agent = SimpleProcessingAgent()
    processed_results = agent.run(dummy_inputs)

    # 3. 결과 확인
    for result in processed_results:
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
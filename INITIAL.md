### **FEATURE:**

- **Improve Stability and Efficiency of AI AnalyzerAgent**
- **Objective:** To resolve the rate limiting (429) and server overload (503) errors that occurred during LLM API calls when classifying numerous videos, making the AI analysis pipeline stable and scalable.

### **CORE FUNCTIONS:**

1. **Introduce Batch Processing:**
    - **Target File:** `src/agents/analyzer_agent.py`
    - **Requirement:** Change the current '1 LLM API call per video' approach to a '1 LLM API call per batch of videos (e.g., 10 videos)' approach. This will drastically reduce the number of API calls to solve the quota exhaustion problem.
2. **Add Retry Logic:**
    - **Target File:** `src/clients/llm_provider.py`
    - **Requirement:** Similar to the implementation in `youtube_client.py`, add logic to automatically retry with **exponential backoff** when transient server errors like `503 Service Unavailable` occur during LLM API calls (e.g., retry 3 times after a short delay).

### **EXAMPLES:**

- **Reference for Retry Logic:** When implementing in `llm_provider.py`, refer to the `for attempt in range(3):` loop and `asyncio.sleep(2 ** attempt)` pattern from the `_make_search_request` function in `src/clients/youtube_client.py`.
- **Data Model Utilization:** When batching information for multiple videos into a single request, utilize models like `BatchClassificationRequest` from `src/models/classification_models.py` or define new Pydantic models as needed to maintain data structure integrity.

### **DOCUMENTATION:**

- **pydantic-ai Batching/Streaming:** (Reference if needed) https://ai.pydantic.dev/ (Check if the pydantic-ai library directly supports batching, and if so, prioritize using that feature.)
- **HTTPX Retry/Backoff:** https://www.python-httpx.org/async/ (Reference for implementing retry and delay logic in an async environment.)

### **OTHER CONSIDERATIONS:**

- **Maintain Existing Structure:** This task is a **refactoring** effort to improve the internal logic of `AnalyzerAgent` and `LLMProvider`, not to add new features. The overall project structure and data flow should not be altered.
- **Cost-Effectiveness:** When batching, sending too many videos in a single request could hit the LLM's context length limit or cause costs to spike. Design the system to start with a baseline of processing 5-10 videos per request to find the optimal batch size.
- **Update Test Code:** Test code in `tests/test_analyzer_agent.py` and a new `tests/test_llm_provider.py` must be updated or added to verify the changed logic.
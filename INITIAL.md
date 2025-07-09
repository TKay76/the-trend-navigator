### **FEATURE:**

- **YouTube Shorts Trend Analysis & AI Report MVP (Minimum Viable Product) Development**
- **Objective:** To develop an initial web-based version that automatically analyzes trending short-form content on YouTube and provides actionable insights to creators.

### **CORE FUNCTIONS:**

1. **Automated Data Collection:** Periodically collect YouTube Shorts video data that meets specific criteria using the YouTube Data API.
2. **AI-Powered Classification:** Automatically classify the collected videos into broad categories (Challenge, Info/Advice, Trending Sounds/BGM) using an LLM.
3. **AI Trend Report Generation:** Automatically generate in-depth reports for each trend based on the analyzed data.

### **EXAMPLES:**

- **Prioritize referencing the new examples in the `examples/` folder:**
    - **`examples/youtube_api_client_example.py`**: Follow the patterns in this file (async, error handling, constant management) when implementing the YouTube API client.
    - **`examples/data_model_example.py`**: Follow the Pydantic model structure in this file when defining data models.
    - **`examples/simple_processing_agent_example.py`**: Follow the basic structure and data flow in this file when implementing data processing agents.

### **DOCUMENTATION:**

- **Pydantic AI Documentation:** https://ai.pydantic.dev/
- **YouTube Data API v3 Docs:** https://developers.google.com/youtube/v3/docs

### **OTHER CONSIDERATIONS:**

- **API Quota Management:** Logic to call the YouTube Data API efficiently without exceeding its daily quota must be implemented.
- **Environment Variables:** All sensitive information must be managed via a `.env` file.
- **MVP Focus:** Do not consider TikTok or Instagram integration; focus solely on the core pipeline with YouTube data.
- **Error Handling:** Robust error handling logic for all possible exceptions must be included.
- **Category Scalability:** While the MVP will focus on the three main categories, the design must be flexible to easily accommodate more granular sub-categories in the future.
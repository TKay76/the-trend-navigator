---

### **`CLAUDE.md` (Final English Version)**

### 🔄 Project Awareness & Context

- **Always read `PLANNING.md`** at the start of a new conversation to understand the project's architecture, goals, style, and constraints.
- **Check `TASK.md`** before starting a new task. If the task isn’t listed, add it with a brief description and today's date.
- **Use consistent naming conventions, file structure, and architecture patterns** as described in `PLANNING.md`.
- **Use venv_linux** (the virtual environment) whenever executing Python commands, including for unit tests.

### 🧱 Code Structure & Modularity

- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- Organize code into clearly separated modules, grouped by feature or responsibility.
    
    For agents this looks like:
    
    - `agent.py` - Main agent definition and execution logic
    - `tools.py` - Tool functions used by the agent
    - `prompts.py` - System prompts
- **Use clear, consistent imports** (prefer relative imports within packages).
- **Use python_dotenv and load_env()** for environment variables.

### 🧪 Testing & Reliability

- **Always create Pytest unit tests for new features** (functions, classes, routes, etc).
- **After updating any logic**, check whether existing unit tests need to be updated. If so, do it.
- **Tests should live in a `/tests` folder** mirroring the main app structure.
    - Include at least:
        - 1 test for expected use
        - 1 edge case
        - 1 failure case

### ✅ Task Completion

- **Mark completed tasks in `TASK.md`** immediately after finishing them.
- Add new sub-tasks or TODOs discovered during development to `TASK.md` under a “Discovered During Work” section.

### 📎 Style & Conventions

- **Use Python** as the primary language.
- **Follow PEP8**, use type hints, and format with `black`.
- **Use `pydantic` for data validation**.
- Use `FastAPI` for APIs and `SQLAlchemy` or `SQLModel` for ORM if applicable.
- Write **docstrings for every function** using the Google style:Python
    
    # 
    
    `def example():
        """
        Brief summary.
    
        Args:
            param1 (type): Description.
    
        Returns:
            type: Description.
        """`
    

### 📚 Documentation & Explainability

- **Update `README.md`** when new features are added, dependencies change, or setup steps are modified.
- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

### 🧠 AI Behavior Rules

- **Never assume missing context. Ask questions if uncertain.**
- **Never hallucinate libraries or functions** – only use known, verified Python packages.
- **Always confirm file paths and module names** exist before referencing them in code or tests.
- **Never delete or overwrite existing code** unless explicitly instructed to or if part of a task from `TASK.md`.

### 🎥 YouTube Trend Analyzer Project-Specific Rules

- **Respect API Quotas:** In any function that calls the YouTube Data API, include a comment `# Quota Cost: [cost]` to clearly indicate the quota consumption. For example, `videos.list` with `part=snippet,contentDetails` has a cost of 3, so it should be commented as `# Quota Cost: 3`.
- **Model-First Principle:** When fetching data from an external API (YouTube) or requesting analysis from an AI (LLM), always use a Pydantic model defined in `models/video_models.py` to enforce the input and output data structure. Never use raw `dict` or `json` directly.
- **Strict Agent Roles:**
    - `collector_agent.py` must only focus on data 'collection'. It should not contain any data transformation or analysis logic.
    - `analyzer_agent.py` is solely responsible for 'analysis' and 'reporting'. It must not call external APIs directly and should always receive data collected by the `collector_agent` as input.
- **Cost-Effective LLM Usage:** Design the `LLMProvider` to prioritize using faster, lower-cost LLM models for simpler tasks like text classification. Use high-performance models only for tasks requiring more creativity, such as report generation.
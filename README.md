# YouTube Shorts Trend Analysis MVP

A comprehensive system for analyzing YouTube Shorts trends using AI-powered classification and automated data collection. This MVP automatically collects YouTube Shorts data, classifies videos into categories, and generates actionable insights for content creators.

> **Built using Context Engineering principles for reliable AI agent development.**

## 🚀 Quick Start

```bash
# 1. Clone this repository
git clone https://github.com/coleam00/Context-Engineering-Intro.git
cd Context-Engineering-Intro

# 2. Set up virtual environment
python3 -m venv venv_linux
source venv_linux/bin/activate  # On Windows: venv_linux\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Edit .env with your API keys:
# - YOUTUBE_API_KEY: Get from Google Cloud Console
# - LLM_API_KEY: Get from your LLM provider (OpenAI, Anthropic, etc.)

# 5. Run the complete analysis pipeline
python -m src.cli pipeline --categories "dance,fitness,tutorial"

# 6. Or run individual commands
python -m src.cli collect --categories "dance,fitness" --max-results 20
python -m src.cli analyze --input collected_videos.json
python -m src.cli report --input classified_videos.json
```

## 📚 Table of Contents

- [Features](#features)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Contributing](#contributing)

## ✨ Features

### Core Functionality
- **🎯 Automated Data Collection**: Efficiently collects YouTube Shorts data using YouTube Data API v3
- **🤖 AI-Powered Classification**: Classifies videos into three main categories:
  - **Challenge**: Dance challenges, fitness challenges, viral challenges
  - **Info/Advice**: Educational content, tutorials, tips, how-to videos
  - **Trending Sounds/BGM**: Music-focused content, sound trends, audio-centric videos
- **📊 Trend Analysis**: Generates comprehensive reports with actionable insights
- **⚡ Quota Management**: Efficient API usage within YouTube's 10,000 units/day limit
- **🔄 Scalable Architecture**: Easy to extend with additional categories and features

### Technical Features
- **Async Processing**: High-performance async implementation throughout
- **Type Safety**: Full Pydantic model validation for all data structures
- **Error Handling**: Robust error handling with exponential backoff and retry logic
- **Rate Limiting**: Respectful API usage with built-in rate limiting
- **Comprehensive Testing**: 80%+ test coverage with unit and integration tests
- **CLI Interface**: User-friendly command-line interface for all operations

## 🏗️ System Architecture

### Project Structure
```
youtube-shorts-trend-analysis/
├── src/
│   ├── models/
│   │   ├── video_models.py           # Video data models
│   │   └── classification_models.py  # Classification models
│   ├── clients/
│   │   ├── youtube_client.py         # YouTube API client
│   │   └── llm_provider.py           # LLM provider interface
│   ├── agents/
│   │   ├── collector_agent.py        # Data collection agent
│   │   └── analyzer_agent.py         # Analysis and reporting agent
│   ├── core/
│   │   ├── settings.py               # Configuration management
│   │   └── exceptions.py             # Custom exceptions
│   └── cli.py                        # Command-line interface
├── tests/                            # Comprehensive test suite
├── examples/                         # Code examples and patterns
├── PRPs/                            # Product Requirements Prompts
├── .env.example                     # Environment variables template
├── requirements.txt                 # Python dependencies
└── README.md                        # This file
```

### Agent Architecture
The system follows a strict separation of concerns with two main agents:

1. **🗂️ Collector Agent**: 
   - **Role**: Data collection only
   - **Responsibility**: Fetch YouTube Shorts data via API
   - **Output**: Raw video data with metadata

2. **🔍 Analyzer Agent**:
   - **Role**: Analysis and reporting only
   - **Responsibility**: AI classification and trend analysis
   - **Input**: Raw video data from Collector Agent
   - **Output**: Classified videos and trend reports

### Data Flow
```
YouTube API → CollectorAgent → Raw Video Data → AnalyzerAgent → Classified Data → Reports
```

## Step-by-Step Guide

### 1. Set Up Global Rules (CLAUDE.md)

The `CLAUDE.md` file contains project-wide rules that the AI assistant will follow in every conversation. The template includes:

- **Project awareness**: Reading planning docs, checking tasks
- **Code structure**: File size limits, module organization
- **Testing requirements**: Unit test patterns, coverage expectations
- **Style conventions**: Language preferences, formatting rules
- **Documentation standards**: Docstring formats, commenting practices

**You can use the provided template as-is or customize it for your project.**

### 2. Create Your Initial Feature Request

Edit `INITIAL.md` to describe what you want to build:

```markdown
## FEATURE:
[Describe what you want to build - be specific about functionality and requirements]

## EXAMPLES:
[List any example files in the examples/ folder and explain how they should be used]

## DOCUMENTATION:
[Include links to relevant documentation, APIs, or MCP server resources]

## OTHER CONSIDERATIONS:
[Mention any gotchas, specific requirements, or things AI assistants commonly miss]
```

**See `INITIAL_EXAMPLE.md` for a complete example.**

### 3. Generate the PRP

PRPs (Product Requirements Prompts) are comprehensive implementation blueprints that include:

- Complete context and documentation
- Implementation steps with validation
- Error handling patterns
- Test requirements

They are similar to PRDs (Product Requirements Documents) but are crafted more specifically to instruct an AI coding assistant.

Run in Claude Code:
```bash
/generate-prp INITIAL.md
```

**Note:** The slash commands are custom commands defined in `.claude/commands/`. You can view their implementation:
- `.claude/commands/generate-prp.md` - See how it researches and creates PRPs
- `.claude/commands/execute-prp.md` - See how it implements features from PRPs

The `$ARGUMENTS` variable in these commands receives whatever you pass after the command name (e.g., `INITIAL.md` or `PRPs/your-feature.md`).

This command will:
1. Read your feature request
2. Research the codebase for patterns
3. Search for relevant documentation
4. Create a comprehensive PRP in `PRPs/your-feature-name.md`

### 4. Execute the PRP

Once generated, execute the PRP to implement your feature:

```bash
/execute-prp PRPs/your-feature-name.md
```

The AI coding assistant will:
1. Read all context from the PRP
2. Create a detailed implementation plan
3. Execute each step with validation
4. Run tests and fix any issues
5. Ensure all success criteria are met

## Writing Effective INITIAL.md Files

### Key Sections Explained

**FEATURE**: Be specific and comprehensive
- ❌ "Build a web scraper"
- ✅ "Build an async web scraper using BeautifulSoup that extracts product data from e-commerce sites, handles rate limiting, and stores results in PostgreSQL"

**EXAMPLES**: Leverage the examples/ folder
- Place relevant code patterns in `examples/`
- Reference specific files and patterns to follow
- Explain what aspects should be mimicked

**DOCUMENTATION**: Include all relevant resources
- API documentation URLs
- Library guides
- MCP server documentation
- Database schemas

**OTHER CONSIDERATIONS**: Capture important details
- Authentication requirements
- Rate limits or quotas
- Common pitfalls
- Performance requirements

## The PRP Workflow

### How /generate-prp Works

The command follows this process:

1. **Research Phase**
   - Analyzes your codebase for patterns
   - Searches for similar implementations
   - Identifies conventions to follow

2. **Documentation Gathering**
   - Fetches relevant API docs
   - Includes library documentation
   - Adds gotchas and quirks

3. **Blueprint Creation**
   - Creates step-by-step implementation plan
   - Includes validation gates
   - Adds test requirements

4. **Quality Check**
   - Scores confidence level (1-10)
   - Ensures all context is included

### How /execute-prp Works

1. **Load Context**: Reads the entire PRP
2. **Plan**: Creates detailed task list using TodoWrite
3. **Execute**: Implements each component
4. **Validate**: Runs tests and linting
5. **Iterate**: Fixes any issues found
6. **Complete**: Ensures all requirements met

See `PRPs/EXAMPLE_multi_agent_prp.md` for a complete example of what gets generated.

## Using Examples Effectively

The `examples/` folder is **critical** for success. AI coding assistants perform much better when they can see patterns to follow.

### What to Include in Examples

1. **Code Structure Patterns**
   - How you organize modules
   - Import conventions
   - Class/function patterns

2. **Testing Patterns**
   - Test file structure
   - Mocking approaches
   - Assertion styles

3. **Integration Patterns**
   - API client implementations
   - Database connections
   - Authentication flows

4. **CLI Patterns**
   - Argument parsing
   - Output formatting
   - Error handling

### Example Structure

```
examples/
├── README.md           # Explains what each example demonstrates
├── cli.py             # CLI implementation pattern
├── agent/             # Agent architecture patterns
│   ├── agent.py      # Agent creation pattern
│   ├── tools.py      # Tool implementation pattern
│   └── providers.py  # Multi-provider pattern
└── tests/            # Testing patterns
    ├── test_agent.py # Unit test patterns
    └── conftest.py   # Pytest configuration
```

## Best Practices

### 1. Be Explicit in INITIAL.md
- Don't assume the AI knows your preferences
- Include specific requirements and constraints
- Reference examples liberally

### 2. Provide Comprehensive Examples
- More examples = better implementations
- Show both what to do AND what not to do
- Include error handling patterns

### 3. Use Validation Gates
- PRPs include test commands that must pass
- AI will iterate until all validations succeed
- This ensures working code on first try

### 4. Leverage Documentation
- Include official API docs
- Add MCP server resources
- Reference specific documentation sections

### 5. Customize CLAUDE.md
- Add your conventions
- Include project-specific rules
- Define coding standards

## Resources

- [Claude Code Documentation](https://docs.anthropic.com/en/docs/claude-code)
- [Context Engineering Best Practices](https://www.philschmid.de/context-engineering)
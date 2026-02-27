# News Bot - Mexico CRE Sector

An autonomous LangGraph-powered AI agent for retrieving and analyzing news related to Mexico's Commercial Real Estate (CRE) sector.

## Overview

This agent autonomously:
1. **Explores** current news to understand what's happening
2. **Plans** specific searches based on real data (not guessing)
3. **Searches** deeply on selected topics
4. **Extracts** full content from sources
5. **Evaluates** coverage and loops if needed
6. **Generates** a structured news digest

## Architecture

```
                    +-------------+
                    |   START     |
                    +------+------+
                           |
                           v
                    +-------------+
                    | explorador  |  Broad, fast search
                    +------+------+  to see what's out there
                           |
                           v
                    +-------------+
                    | planificador|  Analyzes real headlines
                    +------+------+  and picks topics to investigate
                           |
                           v
                    +-------------+
                    |  buscador   |  Deep, targeted searches
                    +------+------+  on selected topics
                           |
                           v
                    +-------------+
                    |  extractor  |  Extracts full article
                    +------+------+  content from URLs
                           |
                           v
                    +-------------+
              +---->|  evaluador  |  Evaluates coverage quality
              |     +------+------+
              |            |
              |     +------+------+
              |     |  sufficient?|
              |     +--+-------+--+
              |        |       |
              |       NO      YES
              |        |       |
              +--------+       v
                        +-------------+
                        |  analista   |  Generates final
                        +------+------+  news digest
                               |
                               v
                        +-------------+
                        |    END      |
                        +-------------+
```

## Features

- **Autonomous topic selection** - AI decides what to search based on actual news
- **Multi-topic search** - Query multiple topics in a single run
- **Date-filtered results** - Retrieve news within specific date ranges
- **Content extraction** - Get full article content, not just snippets
- **Coverage evaluation** - Loops back if more information is needed
- **Structured output** - Pydantic models for consistent data
- **Markdown reports** - Auto-generated reports with sources

## Installation

### 1. Create and activate virtual environment

```powershell
# Create venv
python -m venv news_bot

# Activate (PowerShell)
.\news_bot\Scripts\Activate.ps1

# Activate (Command Prompt)
.\news_bot\Scripts\activate.bat
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
OPENAI_MODEL=gpt-4o  # Optional, defaults to gpt-4o
```

## Usage

### Run the agent

```bash
python agent.py
```

### Customize your search

Edit the `__main__` block in `agent.py`:

```python
digest = run_agent(
    objective="Noticias del sector inmobiliario comercial en México: parques industriales, oficinas corporativas",
    start_date="2026-01-20",
    end_date="2026-02-03"
)
```

### Use as a module

```python
from agent import run_agent, save_report

digest = run_agent(
    objective="Nearshoring y parques industriales en el Bajío",
    start_date="2026-01-01",
    end_date="2026-02-01"
)

if digest:
    save_report(digest, "mi_reporte.md")
```

## Project Structure

```
news_bot/
├── agent.py              # Main agent with graph definition
├── models.py             # Pydantic models and GraphState
├── nodes/                # Individual node functions
│   ├── __init__.py
│   ├── explorer.py       # Broad news exploration
│   ├── planner.py        # Topic planning from real data
│   ├── searcher.py       # Deep targeted searches
│   ├── extractor.py      # Content extraction
│   ├── evaluator.py      # Coverage evaluation
│   └── analyst.py        # Report generation
├── tests/                # Test suite
│   ├── conftest.py       # Shared fixtures
│   ├── unit/             # Unit tests for each node
│   └── integration/      # Full flow tests
├── requirements.txt
├── .env                  # Environment variables (not tracked)
├── .gitignore
└── README.md
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=nodes --cov=agent
```

## Node Descriptions

| Node | Purpose | Input | Output |
|------|---------|-------|--------|
| `explorador` | Broad search to see what's happening | objective, dates | exploration_results |
| `planificador` | Analyze headlines, pick topics | exploration_results | topics, reasoning |
| `buscador` | Deep search on selected topics | topics, dates | raw_content |
| `extractor` | Get full article content | raw_content URLs | enriched raw_content |
| `evaluador` | Check if coverage is sufficient | raw_content, objective | evaluation |
| `analista` | Generate structured digest | raw_content | NewsDigest |

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Required |
| `TAVILY_API_KEY` | Tavily API key | Required |
| `OPENAI_MODEL` | Model to use | gpt-4o |
| `MAX_SEARCH_ITERATIONS` | Max re-search loops | 2 |

## API Keys

- **OpenAI API Key**: [platform.openai.com](https://platform.openai.com/)
- **Tavily API Key**: [tavily.com](https://tavily.com/)

## License

MIT

---

Built with LangGraph for Mexico's CRE sector

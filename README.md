# 🔄 Newsloop — Autonomous News Research Agent

> **Research smarter. Publish faster.**

Newsloop is an autonomous, multimodal AI agent that researches any topic across text and video sources, synthesizes findings, and generates structured news digests — all in one run.

Built for the [Autonomous Agents Hackathon](https://devpost.com/) — *"We've stacked real infra and real AI so your hack ships as a product, not a slide."*

---

## What It Does

Give Newsloop a research objective and a date range. It autonomously:

1. **Explores** the news landscape to understand what's happening
2. **Plans** targeted searches based on real headlines (not guessing)
3. **Searches** text articles and YouTube videos in parallel
4. **Extracts** full article content from source URLs
5. **Analyzes** video content using Reka Vision AI (upload → index → Q&A)
6. **Enriches** extracted content with Pioneer AI entity recognition (GLiNER)
7. **Evaluates** coverage quality and loops back if gaps are found
8. **Generates** a structured, source-cited news digest with text and video insights

The entire pipeline is autonomous — no human intervention between start and finish.

---

## Architecture

Newsloop uses a **parallel fan-out/fan-in** architecture built on LangGraph. The text and video branches run simultaneously, merge at the evaluator, and produce a unified report.

```
                         ┌─────────────┐
                         │   START     │
                         └──────┬──────┘
                                │
                                ▼
                         ┌─────────────┐
                         │ explorador  │  Broad search — what's out there?
                         └──────┬──────┘
                                │
                                ▼
                         ┌──────────────┐
                         │ planificador │  Pick 3-5 topics from real data
                         └──┬────────┬──┘
                            │        │
                   ─────────┘        └──────────
                  │ TEXT BRANCH            │ VIDEO BRANCH
                  ▼                        ▼
           ┌───────────┐           ┌────────────────┐
           │ buscador   │           │ buscador_video  │  Tavily → YouTube URLs
           └─────┬─────┘           └───────┬────────┘
                 │                          │
                 ▼                          ▼
           ┌───────────┐           ┌──────────────────┐
           │ extractor  │           │ analizador_visual │  Reka Vision Q&A
           └─────┬─────┘           └───────┬──────────┘
                 │                          │
                 ▼                          │
           ┌──────────────┐                │
           │ enriquecedor │  Pioneer AI     │
           └──────┬───────┘                │
                  │                         │
                  └────────┬───────────────┘
                           │  FAN-IN (waits for both)
                           ▼
                    ┌─────────────┐
              ┌────►│  evaluador  │  Coverage sufficient?
              │     └──────┬──────┘
              │            │
              │     ┌──────┴──────┐
              │     NO           YES
              │     │              │
              └─────┘              ▼
                            ┌───────────┐
                            │  analista  │  Generate final digest
                            └─────┬─────┘
                                  │
                                  ▼
                            ┌───────────┐
                            │    END    │
                            └───────────┘
```

The `Annotated[list[dict], operator.add]` reducer on shared state fields is what makes the parallel merge work — when both branches complete, their outputs are concatenated instead of one overwriting the other.

---

## Sponsor Integrations

| Sponsor | Integration | What It Does |
|---------|------------|--------------|
| **Reka AI** | Vision API | Uploads YouTube videos, indexes them, runs Spanish/English Q&A to extract insights, then cleans up |
| **Pioneer AI** | GLiNER Entity Extraction | Enriches extracted articles with named entities (people, organizations, locations, events) |
| **OpenAI** | GPT models | Powers the LLM reasoning across all nodes (exploration, planning, evaluation, report generation) |
| **Tavily** | Search API | Web search with date filtering for both text articles and YouTube video discovery |

---

## Demo — Newsloop Web Interface

Newsloop ships with a local web interface for demos and presentations.

**Features:**
- Neo-brutalist design with dark terminal log panel
- Real-time SSE streaming of agent logs (color-coded by node status)
- Visual pipeline progress bar showing parallel execution
- Rendered report with clickable sources and video insights
- One-click download as JSON or Markdown

**Run it:**

```bash
uvicorn app:app --reload
```

Then open **http://localhost:8000**.

---

## Quick Start

### 1. Clone and set up

```bash
git clone https://github.com/AlejandroSpot2/Hackaton-news.git
cd Hackaton-news
python -m venv venv
```

Activate the virtual environment:

```powershell
# PowerShell
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure API keys

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
REKA_API_KEY=your_reka_api_key
PIONEER_API_KEY=your_pioneer_api_key
OPENAI_MODEL=gpt-4o
MAX_VIDEOS=5
MAX_VIDEOS_PER_TOPIC=2
```

### 4. Run

**CLI mode (interactive):**

```bash
python agent.py
```

The agent will prompt you for an objective, date range, and optional context.

**Web interface:**

```bash
uvicorn app:app --reload
# → http://localhost:8000
```

**As a Python module:**

```python
from agent import run_agent, save_report

digest = run_agent(
    objective="Latest developments in renewable energy in Europe",
    start_date="2026-02-01",
    end_date="2026-02-27",
)

if digest:
    save_report(digest, objective, start_date, end_date)
```

---

## Project Structure

```
Hackaton-news/
├── agent.py                  # LangGraph workflow, CLI entry point
├── app.py                    # FastAPI web server (SSE streaming)
├── models.py                 # Pydantic models, GraphState, constants
├── converter.py              # JSON → Markdown / TXT / DOCX report converter
├── templates/
│   └── index.html            # Neo-brutalist web UI
├── nodes/
│   ├── __init__.py           # Node exports
│   ├── explorer.py           # Broad news exploration (explorador)
│   ├── planner.py            # Topic planning from real data (planificador)
│   ├── searcher.py           # Deep targeted text search (buscador)
│   ├── extractor.py          # Full article content extraction (extractor)
│   ├── enricher.py           # Pioneer AI entity enrichment (enriquecedor)
│   ├── evaluator.py          # Coverage evaluation + retry logic (evaluador)
│   ├── analyst.py            # Final digest generation (analista)
│   ├── video_searcher.py     # YouTube video discovery (buscador_video)
│   ├── visual_analyzer.py    # Reka Vision video analysis (analizador_visual)
│   └── pioneer_client.py     # Pioneer REST API client with retries
├── tests/
│   ├── conftest.py           # Shared fixtures and mocks
│   ├── unit/                 # Unit tests per node
│   └── integration/          # Full pipeline tests
├── reportes/                 # Generated reports output directory
├── requirements.txt
├── .env                      # API keys (not tracked)
├── .gitignore
├── AGENTS.md                 # Repository guidelines for AI tools
└── README.md
```

---

## Node Reference

| Node | Spanish Name | Purpose | Key Tech |
|------|-------------|---------|----------|
| Explorer | `explorador` | Broad search to map the news landscape | Tavily |
| Planner | `planificador` | Analyze headlines, select 3-5 topics | OpenAI |
| Text Searcher | `buscador` | Deep, date-filtered article search | Tavily |
| Video Searcher | `buscador_video` | Find YouTube URLs (topic + broad fallback) | Tavily |
| Extractor | `extractor` | Fetch full article content from URLs | BeautifulSoup |
| Visual Analyzer | `analizador_visual` | Upload → index → Q&A → delete on Reka Vision | Reka Vision API |
| Enricher | `enriquecedor` | Entity extraction on article content | Pioneer AI (GLiNER) |
| Evaluator | `evaluador` | Assess coverage, trigger retry if needed | OpenAI |
| Analyst | `analista` | Generate structured digest from all sources | OpenAI |

---

## Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | OpenAI API key | Yes | — |
| `TAVILY_API_KEY` | Tavily search API key | Yes | — |
| `REKA_API_KEY` | Reka Vision API key | Yes | — |
| `PIONEER_API_KEY` | Pioneer AI API key | Yes | — |
| `OPENAI_MODEL` | LLM model to use | No | `gpt-4o` |
| `MAX_VIDEOS` | Max total videos per run | No | `5` |
| `MAX_VIDEOS_PER_TOPIC` | Max videos per topic search | No | `2` |
| `MAX_SEARCH_ITERATIONS` | Max evaluator retry loops | No | `2` |

---

## Report Converter

Convert the JSON output to other formats:

```bash
# Default: JSON → Markdown
python converter.py reporte.json

# Specific format
python converter.py reporte.json --format docx

# All formats at once
python converter.py reporte.json --all

# Custom output path
python converter.py reporte.json -o my_report.md
```

Supported formats: `.md`, `.txt`, `.docx`, `.json`

---

## Running Tests

```bash
# Full suite
pytest

# Verbose
pytest -v

# Unit tests only
pytest tests/unit/

# Integration tests only
pytest tests/integration/

# With coverage
pytest --cov=nodes --cov=agent
```

---

## API Keys

| Service | Get Your Key |
|---------|-------------|
| OpenAI | [platform.openai.com](https://platform.openai.com/) |
| Tavily | [tavily.com](https://tavily.com/) |
| Reka AI | [reka.ai](https://www.reka.ai/) |
| Pioneer AI | [pioneerai.com](https://www.pioneerai.com/) |

---

## Tech Stack

- **Python 3.11+**
- **LangGraph** — stateful agent orchestration with parallel execution
- **LangChain + OpenAI** — LLM integration
- **Tavily** — web search with date filtering
- **Reka Vision API** — video understanding (upload, index, Q&A)
- **Pioneer AI** — GLiNER entity extraction
- **FastAPI + Uvicorn** — web interface backend with SSE streaming
- **Pydantic** — structured data models and validation
- **BeautifulSoup** — article content extraction

---

## Team
Built by the Hackaton-news team at the Autonomous Agents Hackathon. Argentina, Peru, Mexico is KEY.

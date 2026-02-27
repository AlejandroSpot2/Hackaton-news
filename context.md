# News Research Agent — Project Context

## What is this?

An **autonomous news research agent** built with [LangGraph](https://github.com/langchain-ai/langgraph) that takes a user-defined objective, time period, and optional context, then autonomously explores, plans, searches, extracts, evaluates, and generates a structured news digest.

## Tech Stack

- **Orchestration:** LangGraph (StateGraph with conditional edges)
- **Search & Extraction:** [Tavily API](https://tavily.com/) (news search + full-content extraction)
- **LLM:** OpenAI (`gpt-5-mini` for planning/evaluation, `gpt-5` for final analysis) via `langchain-openai`
- **Data Models:** Pydantic v2 (structured LLM output, JSON serialization)
- **Report Export:** Markdown, plain text, and Word (.docx) via `python-docx`
- **Testing:** pytest with full mock coverage (Tavily + OpenAI)

## Agent Pipeline

```
User input (interactive CLI)
  │
  ▼
Explorer ──► Planner ──► Searcher ──► Extractor ──► Evaluator ──┐
                                                                 │
                              ┌──────────────────────────────────┘
                              │
                              ▼
                     coverage sufficient? ──yes──► Analyst ──► END
                              │
                             no (+ iterations remain)
                              │
                              ▼
                          Searcher (loop back with missing topics)
```

1. **Explorer** — Broad Tavily search to discover what's happening
2. **Planner** — LLM analyzes headlines and picks 3-5 targeted search queries
3. **Searcher** — Deep Tavily searches per topic (advanced depth, date-filtered)
4. **Extractor** — Pulls full article content from discovered URLs
5. **Evaluator** — LLM judges coverage quality; loops back if insufficient (max 2 iterations)
6. **Analyst** — LLM generates the final structured digest (title + 100-150 word article + sources per topic)

## How to Run

```bash
python agent.py
```

Interactive prompts:
```
What are we researching today? > Soccer news in europe regarding racism
What time period? (e.g. 2026-02-01 to 2026-02-27) > 2026-02-01 to 2026-02-27
(Optional) Any specific context? (e.g. sector, region, focus) >
```

Output: `reporte.json` with the structured digest.

To convert to other formats:
```bash
python converter.py reporte.json --format md
python converter.py reporte.json --all          # md + txt + docx
```

## How to Test

```bash
python -m pytest tests/unit/ -v       # 49 unit tests
python -m pytest tests/ -v            # unit + integration
```

All external APIs (Tavily, OpenAI) are fully mocked in tests.

## Project Structure

```
├── agent.py              # Graph definition, run_agent(), interactive CLI
├── models.py             # Pydantic models + GraphState + constants
├── converter.py          # JSON → Markdown / plaintext / Word export
├── nodes/
│   ├── explorer.py       # Broad news discovery
│   ├── planner.py        # LLM-powered search planning
│   ├── searcher.py       # Deep targeted searches
│   ├── extractor.py      # Full content extraction
│   ├── evaluator.py      # Coverage quality assessment + loop control
│   └── analyst.py        # Final digest generation
├── tests/
│   ├── conftest.py       # Shared fixtures and mocks
│   ├── unit/             # Per-node unit tests
│   └── integration/      # Full pipeline tests
└── reportes/             # Generated report output directory
```

## What We Did (Hackathon Changes)

The agent was originally hardcoded for Mexico's commercial real estate (CRE) sector — with Spanish prompts, a domain whitelist (`MEXICO_DOMAINS`), and sector-specific LLM instructions. We generalized it into a **topic-agnostic news research agent**:

- **Interactive CLI prompts** — user provides objective, time period, and optional context at runtime
- **Removed `MEXICO_DOMAINS`** — no more domain filtering; searches the entire web
- **Generalized all LLM prompts** — from CRE-specific Spanish to generic English news analyst roles
- **Added `context` field** — optional parameter that flows through the entire pipeline (planner, evaluator, analyst) for domain-specific focus without hardcoding
- **Switched all UI/prints to English**
- **Updated all tests** — new generic fixtures, updated assertions, all 49 passing

## Environment Variables

```
TAVILY_API_KEY=...
OPENAI_API_KEY=...
```

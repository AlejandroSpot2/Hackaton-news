# Repository Guidelines

## Project Structure & Module Organization
`agent.py` orchestrates the LangGraph workflow and CLI entry point. `models.py` holds Pydantic models and GraphState. `nodes/` contains the node implementations (explorer, planner, searcher, extractor, evaluator, analyst). `tests/` is split into `unit/` and `integration/` with shared fixtures in `tests/conftest.py`. Generated reports are written to `reporte_detallado.md`. A local virtualenv may exist in `news_bot/`; treat it as tooling, not source.

## Build, Test, and Development Commands
```powershell
python -m venv news_bot
.\news_bot\Scripts\Activate.ps1
pip install -r requirements.txt
python agent.py
pytest
pytest --cov=nodes --cov=agent
```
The first two commands create and activate a local virtualenv. Install dependencies before running `python agent.py` to generate a report. Use `pytest` for the full suite and the coverage command for quick signal on node and agent coverage.

## Coding Style & Naming Conventions
Use 4-space indentation, type hints, and docstrings for public functions. Keep modules lowercase and functions and variables in snake_case. Node identifiers in `agent.py` are Spanish (for example, `explorador` and `planificador`); keep new nodes aligned with that naming and update graph edges accordingly.

## Testing Guidelines
Pytest is the test runner. Unit tests live in `tests/unit/` and should mirror node modules (for example, `tests/unit/test_explorer.py`). Integration coverage is in `tests/integration/test_full_flow.py`. Add tests for new behavior and prefer mocks for external calls.

## Commit & Pull Request Guidelines
Recent commits use short, typed prefixes such as `Feature:` and `Enhancement:` followed by an imperative summary. Keep subject lines concise. For PRs, include a clear summary, tests run, and linked issues. If the report format changes, attach a short sample of `reporte_detallado.md` or a log excerpt.

## Security & Configuration Tips
Store API keys in `.env` and do not commit the file. Required variables are `OPENAI_API_KEY` and `TAVILY_API_KEY`; optional tuning uses `OPENAI_MODEL` and `MAX_SEARCH_ITERATIONS`. Avoid logging secrets in test output.

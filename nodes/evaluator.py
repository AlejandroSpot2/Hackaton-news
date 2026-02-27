"""
Evaluator node - assesses coverage quality and decides if more search is needed.
"""
import os
from datetime import datetime
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, Evaluation, MAX_SEARCH_ITERATIONS

load_dotenv()

# Initialize model
model = ChatOpenAI(model="gpt-5-mini-2025-08-07", temperature=0.0)


def _is_within_range(pub_date_str: str, start: str, end: str) -> bool:
    """Check if a published_date falls within [start, end]."""
    if not pub_date_str:
        return True  # no date = benefit of the doubt
    try:
        pub = parsedate_to_datetime(pub_date_str).date()
        return (
            datetime.strptime(start, "%Y-%m-%d").date()
            <= pub
            <= datetime.strptime(end, "%Y-%m-%d").date()
        )
    except (ValueError, TypeError):
        return True  # unparseable = keep


def evaluator_node(state: GraphState) -> dict:
    """
    Evaluate if the search results provide sufficient coverage.

    This node analyzes the collected content and determines if:
    - The objective is adequately covered
    - There's enough concrete data (numbers, companies, dates)
    - Important angles are missing
    - Sources fall within the required date range

    Args:
        state: Current graph state containing raw_content and objective

    Returns:
        Dictionary with Evaluation result
    """
    print("--- EVALUATING COVERAGE ---")

    objective = state.get("objective", "general news")
    context = state.get("context", "")
    raw_content = state.get("raw_content", [])
    current_iterations = state.get("search_iterations", 0)
    start_date = state.get("start_date", "")
    end_date = state.get("end_date", "")

    # Summarize what we have
    topics_covered = [item["topic"] for item in raw_content]

    # Count sources and flag out-of-range ones
    total_sources = 0
    out_of_range = 0
    for item in raw_content:
        for source in item.get("sources", []):
            total_sources += 1
            pub = source.get("published_date", "")
            if pub and not _is_within_range(pub, start_date, end_date):
                out_of_range += 1

    if out_of_range:
        print(f"  -> Sources out of range: {out_of_range}/{total_sources}")

    # Build content summary for evaluation (include dates)
    content_summary = []
    for item in raw_content:
        sources_text = "\n".join([
            f"  - [{s.get('published_date', 'no date')}] {s['title'][:100]}"
            for s in item["sources"][:3]
        ])
        content_summary.append(f"Topic: {item['topic']}\nSources:\n{sources_text}")

    content_text = "\n\n".join(content_summary)

    context_block = f"\nResearch context/focus: {context}\n" if context else ""

    prompt = f"""You are a senior news editor evaluating coverage quality.

REPORT OBJECTIVE: {objective}
{context_block}REQUIRED PERIOD: {start_date} to {end_date}
SEARCH ITERATIONS: {current_iterations} of {MAX_SEARCH_ITERATIONS} max

COLLECTED CONTENT:
{content_text}

TOTAL: {len(topics_covered)} topics, {total_sources} sources
SOURCES OUT OF DATE RANGE: {out_of_range} of {total_sources}

EVALUATE RIGOROUSLY:
1. TOPIC COVERAGE: Do the topics cover the sub-topics of the objective? (e.g., if the objective mentions multiple areas, there should be at least one topic per area)
2. DATA QUALITY: Are there concrete figures (amounts, percentages, specific companies)? A topic without hard data is weak.
3. SOURCE DIVERSITY: Are there at least 2 distinct sources per topic? A topic with only 1 source is weak.
4. TIMELINESS: If there are sources outside the date range, that reduces quality. Penalize proportionally.

SUFFICIENCY CRITERIA:
- SUFFICIENT: >= 3 solid topics (with concrete data + >= 2 sources each) covering the objective's sub-areas
- INSUFFICIENT: < 3 solid topics, OR a sub-area of the objective without coverage, OR majority of sources out of range

If coverage is insufficient AND iterations remain, suggest 1-2 additional focused searches for what's missing.
If max iterations reached, mark is_sufficient=True.
"""

    evaluation = model.with_structured_output(Evaluation).invoke(prompt)

    status = "SUFFICIENT" if evaluation.is_sufficient else "NEEDS MORE"
    print(f"  -> Evaluation: {status}")
    if not evaluation.is_sufficient and evaluation.missing_topics:
        topics_str = str(evaluation.missing_topics).encode("ascii", "replace").decode()
        print(f"  -> Missing topics: {topics_str}")

    return {"evaluation": evaluation}


def should_search_more(state: GraphState) -> str:
    """
    Conditional edge function to decide next step after evaluation.

    Args:
        state: Current graph state with evaluation result

    Returns:
        "buscador" to search more, or "analista" to generate report
    """
    evaluation = state.get("evaluation")
    current_iterations = state.get("search_iterations", 0)

    # No evaluation? Go to analyst
    if not evaluation:
        return "analista"

    # Coverage is sufficient? Go to analyst
    if evaluation.is_sufficient:
        return "analista"

    # Hit max iterations? Go to analyst anyway
    if current_iterations >= MAX_SEARCH_ITERATIONS:
        print(f"  -> Iteration limit reached ({MAX_SEARCH_ITERATIONS})")
        return "analista"

    # Need more search - update topics with missing ones
    if evaluation.missing_topics:
        print(f"  -> Searching {len(evaluation.missing_topics)} additional topics")

    return "buscador"

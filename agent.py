"""
News Research Agent - LangGraph-powered autonomous news research

An autonomous agent that:
1. Explores current news to understand what's happening
2. Plans specific searches based on real data
3. Performs deep searches on selected topics
4. Extracts full content from sources
5. Enriches articles with Pioneer AI entity extraction
6. Evaluates coverage and loops if needed
7. Generates a structured news digest
"""
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", message="Pydantic serializer warnings")

from langgraph.graph import StateGraph, END

from models import GraphState, NewsDigest, ReportOutput
from nodes import (
    explorer_node,
    planner_node,
    search_news_node,
    extract_content_node,
    enrich_content_node,
    evaluator_node,
    should_search_more,
    analyze_news_node,
)


def update_topics_for_retry(state: GraphState) -> dict:
    """
    Helper node to update topics from evaluator's missing_topics.
    Called when evaluator decides more search is needed.
    """
    evaluation = state.get("evaluation")
    if evaluation and evaluation.missing_topics:
        return {"topics": evaluation.missing_topics}
    return {}


# =============================================================================
# Build the Graph
# =============================================================================

workflow = StateGraph(GraphState)

# Add all nodes
workflow.add_node("explorador", explorer_node)
workflow.add_node("planificador", planner_node)
workflow.add_node("buscador", search_news_node)
workflow.add_node("extractor", extract_content_node)
workflow.add_node("enriquecedor", enrich_content_node)
workflow.add_node("evaluador", evaluator_node)
workflow.add_node("actualizador_topics", update_topics_for_retry)
workflow.add_node("analista", analyze_news_node)

# Set entry point
workflow.set_entry_point("explorador")

# Define edges
workflow.add_edge("explorador", "planificador")
workflow.add_edge("planificador", "buscador")
workflow.add_edge("buscador", "extractor")
workflow.add_edge("extractor", "enriquecedor")
workflow.add_edge("enriquecedor", "evaluador")

# Conditional edge from evaluator
workflow.add_conditional_edges(
    "evaluador",
    should_search_more,
    {
        "buscador": "actualizador_topics",
        "analista": "analista",
    }
)

workflow.add_edge("actualizador_topics", "buscador")
workflow.add_edge("analista", END)

# Compile the graph
app = workflow.compile()


# =============================================================================
# Public API
# =============================================================================

def run_agent(
    objective: str,
    start_date: str,
    end_date: str,
    context: str = "",
) -> NewsDigest | None:
    """
    Run the news agent with a high-level objective.

    The agent will autonomously:
    1. Explore current news
    2. Plan what to search
    3. Search and extract content
    4. Enrich with Pioneer AI entities
    5. Evaluate and possibly iterate
    6. Generate the final digest

    Args:
        objective: High-level description of what news to find
        start_date: Start date for news search (YYYY-MM-DD)
        end_date: End date for news search (YYYY-MM-DD)
        context: Optional research context (sector, region, focus)

    Returns:
        NewsDigest with the structured report, or None if failed
    """
    inputs: GraphState = {
        "objective": objective,
        "context": context,
        "start_date": start_date,
        "end_date": end_date,
        "exploration_results": [],
        "topics": [],
        "planning_reasoning": "",
        "raw_content": [],
        "evaluation": None,
        "search_iterations": 0,
        "digest": None,
    }

    print(f"\n{'='*60}")
    print(f"NEWS RESEARCH AGENT")
    print(f"{'='*60}")
    print(f"Objective: {objective}")
    if context:
        print(f"Context: {context}")
    print(f"Period: {start_date} to {end_date}")
    print(f"{'='*60}\n")

    final_state = None
    for output in app.stream(inputs):
        for key, value in output.items():
            print(f"[OK] Node completed: {key}")
            if key == "analista":
                final_state = value

    return final_state.get("digest") if final_state else None


def save_report(
    digest: NewsDigest,
    objective: str,
    start_date: str,
    end_date: str,
    filename: str = "reporte.json",
) -> ReportOutput:
    """
    Save the digest as a JSON report using Pydantic serialization.

    Args:
        digest: The NewsDigest to save
        objective: The search objective used for this run
        start_date: Start of the news search window
        end_date: End of the news search window
        filename: Output filename (default: reporte.json)

    Returns:
        The ReportOutput model that was saved
    """
    report = ReportOutput(
        generated_at=datetime.now().isoformat(),
        objective=objective,
        period_start=start_date,
        period_end=end_date,
        digest=digest,
    )

    with open(filename, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))

    print(f"[SAVE] Saved to: {filename}")
    return report


# =============================================================================
# Main Entry Point
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("  NEWS RESEARCH AGENT")
    print("=" * 60)

    objective = input("\nWhat are we researching today? > ").strip()
    if not objective:
        print("No objective provided. Exiting.")
        raise SystemExit(1)

    period = input("What time period? (e.g. 2026-02-01 to 2026-02-27) > ").strip()
    parts = period.replace(" to ", " ").replace(" - ", " ").split()
    if len(parts) < 2:
        print("Invalid period. Please provide start and end dates.")
        raise SystemExit(1)
    start_date, end_date = parts[0], parts[1]

    context = input("(Optional) Any specific context? (e.g. sector, region, focus) > ").strip()

    digest = run_agent(
        objective=objective,
        start_date=start_date,
        end_date=end_date,
        context=context,
    )

    if digest:
        print(f"\n{'='*60}")
        print("REPORT GENERATED")
        print(f"{'='*60}\n")

        for section in digest.sections:
            print(f">> {section.title}")
            print(f"   {section.article[:150]}...")
            print(f"   External sources: {len(section.sources)}")
            print()

        save_report(digest, objective, start_date, end_date)

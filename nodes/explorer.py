"""
Explorer node - performs broad, fast searches to discover what's happening.
"""
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from models import GraphState

load_dotenv()

# Initialize Tavily client
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def explorer_node(state: GraphState) -> dict:
    """
    Perform a broad, fast search to see what's happening in the sector.

    This node does a shallow but wide search to give the planner
    real data about current news, which it uses to decide what
    topics to investigate further.

    Args:
        state: Current graph state containing objective and date range

    Returns:
        Dictionary with exploration_results (headlines and snippets)
    """
    print("--- EXPLORING NEWS ---")

    objective = state.get("objective", "general news")
    start_date = state["start_date"]
    end_date = state["end_date"]

    # Build exploration query from objective; include date range so Tavily prioritizes the period
    exploration_query = f"{objective} news {start_date} to {end_date}"
    print(f"  -> Exploring: {exploration_query}")

    response = tavily.search(
        query=exploration_query,
        search_depth="advanced",
        start_date=state["start_date"],
        end_date=state["end_date"],
        max_results=10,
        topic="news",
    )

    # Extract headlines and snippets for the planner
    exploration_results = [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": result.get("content", "")[:500],
        }
        for result in response.get("results", [])
    ]

    print(f"  -> Found {len(exploration_results)} articles to analyze")

    return {"exploration_results": exploration_results}

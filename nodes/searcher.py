"""
Searcher node - performs deep, targeted news searches.
"""
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from models import GraphState

load_dotenv()

# Initialize Tavily client
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def search_news_node(state: GraphState) -> dict:
    """
    Search news for all topics with deep, targeted queries.

    Args:
        state: Current graph state containing topics and date range

    Returns:
        Dictionary with raw_content and incremented search_iterations
    """
    print("--- SEARCHING NEWS ---")

    raw_content = state.get("raw_content", [])
    current_iterations = state.get("search_iterations", 0)
    start_date = state["start_date"]
    end_date = state["end_date"]

    for topic in state["topics"]:
        enhanced_query = f"{topic} news {start_date} {end_date}"
        print(f"  -> Searching: {enhanced_query}")

        response = tavily.search(
            query=enhanced_query,
            search_depth="advanced",
            start_date=start_date,
            end_date=end_date,
            max_results=5,
            topic="news",
        )

        sources = [
            {
                "url": result["url"],
                "title": result["title"],
                "content": result["content"],
                "published_date": result.get("published_date", ""),
            }
            for result in response.get("results", [])
        ]

        raw_content.append({"topic": topic, "sources": sources})

    return {
        "raw_content": raw_content,
        "search_iterations": current_iterations + 1
    }

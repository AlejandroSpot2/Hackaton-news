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
    print("--- EXPLORANDO NOTICIAS ---")
    
    objective = state.get("objective", "noticias inmobiliarias comerciales México")
    start_date = state["start_date"]
    end_date = state["end_date"]

    # Build exploration query from objective; include date range so Tavily prioritizes the period
    exploration_query = f"{objective} noticias entre {start_date} y {end_date}"
    print(f"  -> Explorando: {exploration_query}")
    
    response = tavily.search(
        query=exploration_query,
        search_depth="advanced",  # Fast, shallow search
        start_date=state["start_date"],
        end_date=state["end_date"],
        max_results=10,  # Get many results for variety
        topic="news",
        # NO include_domains here - explorer casts a wide net
        # The searcher will filter by Mexican domains later
    )
    
    # Extract headlines and snippets for the planner
    exploration_results = [
        {
            "title": result.get("title", ""),
            "url": result.get("url", ""),
            "snippet": result.get("content", "")[:500],  # Short snippets only
        }
        for result in response.get("results", [])
    ]
    
    print(f"  -> Encontradas {len(exploration_results)} noticias para analizar")
    
    return {"exploration_results": exploration_results}

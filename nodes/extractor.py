"""
Extractor node - extracts full content from discovered URLs.
"""
import os

from dotenv import load_dotenv
from tavily import TavilyClient

from models import GraphState

load_dotenv()

# Initialize Tavily client
tavily = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))


def extract_content_node(state: GraphState) -> dict:
    """
    Extract full content from URLs discovered during search.

    Args:
        state: Current graph state containing raw_content with URLs

    Returns:
        Dictionary with enriched raw_content
    """
    print("--- EXTRACTING CONTENT ---")

    enriched_content = []

    for topic_data in state["raw_content"]:
        urls = [source["url"] for source in topic_data["sources"]]

        if not urls:
            enriched_content.append(topic_data)
            continue

        try:
            extract_response = tavily.extract(urls)

            # Enrich sources with extracted content
            for source in topic_data["sources"]:
                for extracted in extract_response.get("results", []):
                    if source["url"] == extracted["url"]:
                        source["content"] = extracted.get("raw_content", source["content"])[:3000]

            # Remove failed extractions
            failed_urls = [f["url"] for f in extract_response.get("failed_results", [])]
            topic_data["sources"] = [s for s in topic_data["sources"] if s["url"] not in failed_urls]

        except Exception as e:
            print(f"  ! Extraction error: {e}")

        enriched_content.append(topic_data)

    return {"raw_content": enriched_content}

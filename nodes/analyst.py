"""
Analyst node - generates the final news digest report.

Leverages Pioneer AI entity data (when available) to provide the LLM
with structured facts (companies, people, figures) for richer output.
"""
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, NewsDigest

load_dotenv()

model = ChatOpenAI(model="gpt-5-2025-08-07", temperature=0.0)


def _build_entity_summary(raw_content: list[dict]) -> str:
    """
    Compile a concise entity summary from Pioneer-enriched articles.

    Returns a text block listing key entities by type, or an empty
    string if no entities were found.
    """
    all_entities: dict[str, set[str]] = {}

    for topic_data in raw_content:
        for source in topic_data.get("sources", []):
            entities = source.get("entities", {})
            for label, values in entities.items():
                if label not in all_entities:
                    all_entities[label] = set()
                for v in values:
                    all_entities[label].add(v)

    if not all_entities:
        return ""

    lines = ["KEY ENTITIES EXTRACTED (via Pioneer AI NER):"]
    for label, values in sorted(all_entities.items()):
        joined = ", ".join(sorted(values)[:15])
        lines.append(f"  {label}: {joined}")

    return "\n".join(lines)


def analyze_news_node(state: GraphState) -> dict:
    """
    Generate a structured news digest from collected and enriched content.

    When Pioneer entity data is present, it is appended to the prompt so
    the LLM can reference concrete names, figures, and locations.

    Args:
        state: Current graph state containing raw_content and objective

    Returns:
        Dictionary with the final NewsDigest
    """
    print("--- GENERATING REPORT ---")

    date = datetime.now().strftime("%Y-%m-%d")
    objective = state.get("objective", "News summary")
    context = state.get("context", "")
    raw_content = state.get("raw_content", [])

    # Video branch: build video analysis context block
    visual_analysis = state.get("visual_analysis", [])
    video_context = ""
    if visual_analysis:
        video_context = "\n\nANALYZED VIDEO CONTENT:\n"
        for va in visual_analysis:
            video_context += f"\nVideo: {va['video_title']}\nURL: {va['video_url']}\nAnalysis: {va['analysis']}\n"

    context_block = f"\nResearch context: {context}\n" if context else ""
    entity_block = _build_entity_summary(raw_content)
    entity_section = f"\n\n{entity_block}\n" if entity_block else ""

    prompt = f"""You are a professional news analyst.
Today's date is {date}.

Report objective: {objective}
{context_block}
Your task is to generate a structured news summary.
For each relevant topic, write:
1. A descriptive title
2. An article of 100 to 150 words summarizing the key points with concrete data (figures, companies, locations)
3. List the URLs of the external sources used (field "sources"); include video URLs where relevant
{entity_section}
Use the entity data above (if present) to ensure your report references
specific people, organisations, monetary amounts, and locations by name.

If video analysis is provided below, integrate its insights into the relevant sections and include the video URLs in the "sources" field.

Collected news data:
{raw_content}{video_context}
"""

    digest = model.with_structured_output(NewsDigest).invoke(prompt)

    return {"digest": digest}

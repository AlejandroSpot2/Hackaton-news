"""
Analyst node - generates the final news digest report.
"""
import os
from datetime import datetime

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, NewsDigest

load_dotenv()

# Initialize model
model = ChatOpenAI(model="gpt-5-2025-08-07", temperature=0.0)


def analyze_news_node(state: GraphState) -> dict:
    """
    Generate a structured news digest from the collected content.

    Args:
        state: Current graph state containing raw_content and objective

    Returns:
        Dictionary with the final NewsDigest
    """
    print("--- GENERATING REPORT ---")

    date = datetime.now().strftime("%Y-%m-%d")
    objective = state.get("objective", "News summary")
    context = state.get("context", "")

    # Video branch: build video analysis context block
    visual_analysis = state.get("visual_analysis", [])
    video_context = ""
    if visual_analysis:
        video_context = "\n\nANALYZED VIDEO CONTENT:\n"
        for va in visual_analysis:
            video_context += f"\nVideo: {va['video_title']}\nURL: {va['video_url']}\nAnalysis: {va['analysis']}\n"

    context_block = f"\nResearch context: {context}\n" if context else ""

    prompt = f"""You are a professional news analyst.
Today's date is {date}.

Report objective: {objective}
{context_block}
Your task is to generate a structured news summary.
For each relevant topic, write:
1. A descriptive title
2. An article of 100 to 150 words summarizing the key points with concrete data (figures, companies, locations)
3. List the URLs of the external sources used (field "sources"); include video URLs where relevant

If video analysis is provided below, integrate its insights into the relevant sections and include the video URLs in the "sources" field.

Collected news data:
{state["raw_content"]}{video_context}
"""

    digest = model.with_structured_output(NewsDigest).invoke(prompt)

    return {"digest": digest}

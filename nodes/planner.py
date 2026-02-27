"""
Planner node - analyzes exploration results and decides what to search deeper.
"""
import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from models import GraphState, SearchPlan

load_dotenv()

# Initialize model
model = ChatOpenAI(model="gpt-5-mini-2025-08-07", temperature=0.0)


def planner_node(state: GraphState) -> dict:
    """
    Analyze exploration results and generate specific search topics.

    This node receives real news data from the explorer and decides
    which topics deserve deeper investigation based on relevance,
    data richness, and alignment with the objective.

    Args:
        state: Current graph state containing exploration_results and objective

    Returns:
        Dictionary with topics list and planning_reasoning
    """
    print("--- PLANNING SEARCHES ---")

    exploration_data = state.get("exploration_results", [])
    objective = state.get("objective", "general news")
    context = state.get("context", "")

    # Format exploration results for the prompt
    headlines_text = "\n".join([
        f"- {item['title']}: {item['snippet'][:200]}..."
        for item in exploration_data
    ])

    context_block = f"\nContext/focus: {context}\n" if context else ""

    prompt = f"""You are a professional news research analyst.

REPORT OBJECTIVE: {objective}
{context_block}
HEADLINES AND NEWS FOUND:
{headlines_text}

TASK:
Based on the REAL headlines above, generate 3-5 specific search queries to investigate further.

CRITICAL RULES FOR TOPICS:
- Each topic must be A SHORT SEARCH QUERY (max 50-60 characters)
- Do NOT include explanations or reasoning in the topics
- Reasoning goes ONLY in the "reasoning" field, NOT in the topics
- Topics are ONLY the search phrases

CORRECT topic examples:
- "AI regulation updates 2026"
- "Tesla factory expansion Germany"
- "Federal Reserve interest rate decision"
- "Climate summit agreements COP31"

INCORRECT topic examples (DO NOT do this):
- "1) AI regulation as a driver... Reasoning: the headline indicates..." (TOO LONG)
- "Search about investments in renewable energy considering that..." (TOO LONG)

Prioritize news with concrete data (figures, companies, specific locations).
"""

    plan = model.with_structured_output(SearchPlan).invoke(prompt)

    print(f"  -> Topics selected: {len(plan.topics)}")
    for i, topic in enumerate(plan.topics, 1):
        print(f"     {i}. {topic}")

    return {
        "topics": plan.topics,
        "planning_reasoning": plan.reasoning
    }

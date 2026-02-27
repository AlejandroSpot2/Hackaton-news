"""
Pydantic models for the News Bot agent.
"""
import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel, Field


# =============================================================================
# Pydantic Models for Structured LLM Output
# =============================================================================

class VisualInsight(BaseModel):
    """Analysis of a video from Reka Vision."""
    video_url: str
    video_title: str
    analysis: str
    source_topic: str = ""


class TopicSection(BaseModel):
    """A section of the news digest for a single topic."""
    title: str
    article: str
    sources: list[str] = Field(description="URLs de fuentes externas (noticias y videos)")
    visual_insights: list[VisualInsight] = Field(default_factory=list, description="Análisis de contenido de video relacionado")


class NewsDigest(BaseModel):
    """Complete news digest with multiple topic sections."""
    sections: list[TopicSection]


class ReportOutput(BaseModel):
    """
    Full report output with metadata and the news digest.
    
    This is the primary JSON output of the agent. It wraps the
    NewsDigest with contextual metadata so the file is self-describing.
    """
    generated_at: str = Field(description="ISO timestamp of report generation")
    objective: str = Field(description="The search objective used for this run")
    period_start: str = Field(description="Start of the news search window (YYYY-MM-DD)")
    period_end: str = Field(description="End of the news search window (YYYY-MM-DD)")
    digest: NewsDigest = Field(description="The structured news digest")


class SearchPlan(BaseModel):
    """Output from the planner node - topics to search."""
    topics: list[str]  # 3-5 specific search queries
    reasoning: str     # Why these topics were chosen


class Evaluation(BaseModel):
    """Output from the evaluator node - coverage assessment."""
    is_sufficient: bool        # True if coverage is good
    missing_topics: list[str]  # Topics to search if not sufficient
    reasoning: str             # Explanation of the decision


# =============================================================================
# Graph State
# =============================================================================

class GraphState(TypedDict):
    """State that flows through the LangGraph agent."""
    # High-level objective (input)
    objective: str
    
    # Date range for searches (controlled externally, not by AI)
    start_date: str
    end_date: str
    
    # Results from broad exploration (explorer node output)
    exploration_results: list[dict]
    
    # Planning output
    topics: list[str]
    planning_reasoning: str
    
    # Search and extraction results
    raw_content: list[dict]
    
    # Evaluation output
    evaluation: Evaluation | None
    search_iterations: int
    
    # Final output
    digest: NewsDigest | None

    # Video branch fields (Annotated with operator.add for parallel fan-in merge)
    video_sources: Annotated[list[dict], operator.add]
    visual_analysis: Annotated[list[dict], operator.add]


# =============================================================================
# Constants
# =============================================================================

MAX_SEARCH_ITERATIONS = 2  # Safety limit for search loops

MEXICO_DOMAINS = [
    "eleconomista.com.mx",
    "elfinanciero.com.mx",
    "expansion.mx",
    "forbes.com.mx",
    "inmobiliare.com",
    "realestatemarket.com.mx",
    "obrasweb.mx",
    "centrourbano.com",
    "mexicoindustry.com",
    "solili.mx",
    "oem.com.mx/elsoldemexico"
]

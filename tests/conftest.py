"""
Shared pytest fixtures for the News Bot test suite.
"""
import pytest
from unittest.mock import MagicMock, patch

from models import (
    GraphState,
    NewsDigest,
    TopicSection,
    SearchPlan,
    Evaluation,
    ReportOutput,
)


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_exploration_results():
    """Sample exploration data as returned by explorer_node."""
    return [
        {
            "title": "AI regulation bill advances in EU parliament",
            "url": "https://reuters.com/tech/ai-regulation-eu-2026",
            "snippet": "The European Parliament approved new AI safety requirements affecting major tech companies...",
        },
        {
            "title": "Tesla announces new Gigafactory in Southeast Asia",
            "url": "https://bloomberg.com/auto/tesla-gigafactory-sea",
            "snippet": "Tesla plans to invest $4.2 billion in a new manufacturing facility in Indonesia...",
        },
        {
            "title": "Federal Reserve holds rates steady amid inflation concerns",
            "url": "https://wsj.com/economy/fed-rates-2026",
            "snippet": "The Fed maintained its benchmark rate at 4.5% citing persistent inflation in services sector...",
        },
    ]


@pytest.fixture
def sample_raw_content():
    """Sample search results as returned by search_news_node."""
    return [
        {
            "topic": "AI regulation EU 2026",
            "sources": [
                {
                    "url": "https://reuters.com/tech/ai-regulation",
                    "title": "EU AI Act enforcement begins",
                    "content": "The European Union's AI Act enters its enforcement phase..."
                },
                {
                    "url": "https://bbc.com/tech/ai-rules",
                    "title": "New AI safety requirements take effect",
                    "content": "Companies must now comply with strict AI transparency rules..."
                }
            ]
        },
        {
            "topic": "Tesla Gigafactory Southeast Asia",
            "sources": [
                {
                    "url": "https://bloomberg.com/auto/tesla-sea",
                    "title": "Tesla expands manufacturing footprint",
                    "content": "Tesla's new $4.2B facility in Indonesia will produce 500,000 vehicles annually..."
                }
            ]
        }
    ]


@pytest.fixture
def sample_enriched_raw_content():
    """Sample raw_content after enrichment with Pioneer entities."""
    return [
        {
            "topic": "AI regulation EU 2026",
            "sources": [
                {
                    "url": "https://reuters.com/tech/ai-regulation",
                    "title": "EU AI Act enforcement begins",
                    "content": "The European Union's AI Act enters its enforcement phase...",
                    "entities": {
                        "ORGANIZATION": ["European Union", "European Parliament"],
                        "LOCATION": ["EU"],
                    },
                },
                {
                    "url": "https://bbc.com/tech/ai-rules",
                    "title": "New AI safety requirements take effect",
                    "content": "Companies must now comply with strict AI transparency rules...",
                    "entities": {},
                }
            ]
        },
        {
            "topic": "Tesla Gigafactory Southeast Asia",
            "sources": [
                {
                    "url": "https://bloomberg.com/auto/tesla-sea",
                    "title": "Tesla expands manufacturing footprint",
                    "content": "Tesla's new $4.2B facility in Indonesia will produce 500,000 vehicles annually...",
                    "entities": {
                        "ORGANIZATION": ["Tesla"],
                        "LOCATION": ["Indonesia", "Southeast Asia"],
                        "MONEY": ["$4.2B"],
                    },
                }
            ]
        }
    ]


@pytest.fixture
def sample_state(sample_exploration_results, sample_raw_content):
    """Complete GraphState for integration tests."""
    return GraphState(
        objective="Latest developments in AI regulation and electric vehicle manufacturing",
        context="",
        start_date="2026-01-20",
        end_date="2026-02-03",
        exploration_results=sample_exploration_results,
        topics=["AI regulation EU", "Tesla Gigafactory"],
        planning_reasoning="Selected based on concrete investment data",
        raw_content=sample_raw_content,
        evaluation=None,
        search_iterations=0,
        digest=None,
    )


@pytest.fixture
def sample_digest():
    """Sample NewsDigest output."""
    return NewsDigest(
        sections=[
            TopicSection(
                title="EU AI Act Enforcement Begins",
                article="The European Union's AI Act enters enforcement with new safety requirements for tech companies.",
                sources=["https://reuters.com/tech/ai-regulation"]
            ),
            TopicSection(
                title="Tesla Expands Manufacturing in Southeast Asia",
                article="Tesla plans a $4.2 billion Gigafactory in Indonesia targeting 500,000 vehicles annually.",
                sources=["https://bloomberg.com/auto/tesla-sea"]
            )
        ]
    )


@pytest.fixture
def sample_report_output(sample_digest):
    """Sample ReportOutput wrapping a digest with metadata."""
    return ReportOutput(
        generated_at="2026-02-05T10:30:00",
        objective="Latest developments in AI regulation and electric vehicle manufacturing",
        period_start="2026-01-20",
        period_end="2026-02-03",
        digest=sample_digest,
    )


@pytest.fixture
def sample_search_plan():
    """Sample SearchPlan from planner."""
    return SearchPlan(
        topics=[
            "AI regulation EU 2026",
            "Tesla Gigafactory Southeast Asia",
            "Federal Reserve interest rate decision"
        ],
        reasoning="Selected topics with concrete data and specific developments"
    )


@pytest.fixture
def sample_evaluation_sufficient():
    """Sample Evaluation marking coverage as sufficient."""
    return Evaluation(
        is_sufficient=True,
        missing_topics=[],
        reasoning="Coverage is adequate with 3 topics and 5 sources with concrete data"
    )


@pytest.fixture
def sample_evaluation_insufficient():
    """Sample Evaluation marking coverage as insufficient."""
    return Evaluation(
        is_sufficient=False,
        missing_topics=["Federal Reserve rate decision impact"],
        reasoning="Missing coverage on monetary policy which is mentioned in objective"
    )


@pytest.fixture
def sample_pioneer_enricher_entities():
    """Mock Pioneer entity extraction response for the enricher."""
    return [
        {"label": "ORGANIZATION", "text": "Tesla"},
        {"label": "LOCATION", "text": "Indonesia"},
        {"label": "MONEY", "text": "$4.2 billion"},
        {"label": "PERSON", "text": "Elon Musk"},
    ]


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_tavily_search_response():
    """Mock response from Tavily search API."""
    return {
        "results": [
            {
                "url": "https://reuters.com/test",
                "title": "Test Article Title",
                "content": "Test article content with relevant information..."
            },
            {
                "url": "https://bloomberg.com/test",
                "title": "Another Test Article",
                "content": "More test content for the search results..."
            }
        ]
    }


@pytest.fixture
def mock_tavily_extract_response():
    """Mock response from Tavily extract API."""
    return {
        "results": [
            {
                "url": "https://reuters.com/test",
                "raw_content": "Full extracted content from the article..."
            }
        ],
        "failed_results": []
    }


@pytest.fixture
def mock_tavily(monkeypatch, mock_tavily_search_response, mock_tavily_extract_response):
    """
    Mock Tavily client to avoid real API calls.

    Usage:
        def test_something(mock_tavily):
            # Tavily calls are now mocked
            result = explorer_node(state)
    """
    mock_client = MagicMock()
    mock_client.search.return_value = mock_tavily_search_response
    mock_client.extract.return_value = mock_tavily_extract_response

    monkeypatch.setattr("nodes.explorer.tavily", mock_client)
    monkeypatch.setattr("nodes.searcher.tavily", mock_client)
    monkeypatch.setattr("nodes.extractor.tavily", mock_client)

    return mock_client


def _make_openai_mock(
    search_plan,
    evaluation,
    digest,
    pioneer_entities,
):
    """
    Build mocks for OpenAI (planner, evaluator, analyst) and Pioneer (enricher).

    Returns a dict with 'openai_planner', 'openai_evaluator', 'openai_analyst',
    and 'pioneer_enricher' mocks.
    """
    def _build_model(return_map):
        mock_model = MagicMock()

        def _with_structured_output(output_type):
            mock_chain = MagicMock()
            mock_chain.invoke.return_value = return_map.get(output_type)
            return mock_chain

        mock_model.with_structured_output = _with_structured_output
        return mock_model

    planner_model = _build_model({SearchPlan: search_plan})
    evaluator_model = _build_model({Evaluation: evaluation})
    analyst_model = _build_model({NewsDigest: digest})

    pioneer_mock = MagicMock(return_value=pioneer_entities)

    return {
        "planner": planner_model,
        "evaluator": evaluator_model,
        "analyst": analyst_model,
        "pioneer_enricher": pioneer_mock,
    }


@pytest.fixture
def mock_openai(
    monkeypatch,
    sample_search_plan,
    sample_evaluation_sufficient,
    sample_digest,
    sample_pioneer_enricher_entities,
):
    """
    Mock OpenAI for planner, evaluator, analyst + Pioneer for enricher.

    This is the standard fixture used by most tests.
    """
    mocks = _make_openai_mock(
        sample_search_plan,
        sample_evaluation_sufficient,
        sample_digest,
        sample_pioneer_enricher_entities,
    )

    monkeypatch.setattr("nodes.planner.model", mocks["planner"])
    monkeypatch.setattr("nodes.evaluator.model", mocks["evaluator"])
    monkeypatch.setattr("nodes.analyst.model", mocks["analyst"])
    monkeypatch.setattr("nodes.enricher.pioneer_extract", mocks["pioneer_enricher"])

    return mocks["planner"]


@pytest.fixture
def mock_openai_insufficient(
    monkeypatch,
    sample_search_plan,
    sample_evaluation_insufficient,
    sample_digest,
    sample_pioneer_enricher_entities,
):
    """
    Mock that returns insufficient evaluation (triggers re-search loop).
    """
    mocks = _make_openai_mock(
        sample_search_plan,
        sample_evaluation_insufficient,
        sample_digest,
        sample_pioneer_enricher_entities,
    )

    monkeypatch.setattr("nodes.planner.model", mocks["planner"])
    monkeypatch.setattr("nodes.evaluator.model", mocks["evaluator"])
    monkeypatch.setattr("nodes.analyst.model", mocks["analyst"])
    monkeypatch.setattr("nodes.enricher.pioneer_extract", mocks["pioneer_enricher"])

    return mocks["planner"]

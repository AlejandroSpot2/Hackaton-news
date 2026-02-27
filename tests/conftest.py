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
            "title": "Inversión en parques industriales crece 37% en 2026",
            "url": "https://elfinanciero.com.mx/empresas/parques-industriales-2026",
            "snippet": "La AMPIP proyecta inversiones por 5,831 millones de dólares en el sector industrial...",
        },
        {
            "title": "Vacancia de oficinas en CDMX baja a 17.6%",
            "url": "https://realestatemarket.com.mx/oficinas-cdmx-2026",
            "snippet": "El mercado de oficinas muestra signos de recuperación con absorción neta de 247,000 m²...",
        },
        {
            "title": "Amazon anuncia nuevo centro de distribución en Guadalajara",
            "url": "https://expansion.mx/empresas/amazon-guadalajara",
            "snippet": "La empresa invertirá 200 millones de dólares en un centro logístico de 150,000 m²...",
        },
    ]


@pytest.fixture
def sample_raw_content():
    """Sample search results as returned by search_news_node."""
    return [
        {
            "topic": "Parques industriales nearshoring México 2026",
            "sources": [
                {
                    "url": "https://elfinanciero.com.mx/parques-industriales",
                    "title": "Inversión en parques industriales crece 37%",
                    "content": "La Asociación Mexicana de Parques Industriales (AMPIP) proyecta..."
                },
                {
                    "url": "https://mexicoindustry.com/nearshoring",
                    "title": "Nearshoring impulsa desarrollo industrial",
                    "content": "El fenómeno del nearshoring continúa atrayendo inversiones..."
                }
            ]
        },
        {
            "topic": "Oficinas corporativas CDMX vacancia 2026",
            "sources": [
                {
                    "url": "https://realestatemarket.com.mx/oficinas",
                    "title": "Mercado de oficinas se estabiliza",
                    "content": "La vacancia en el mercado de oficinas de CDMX bajó a 17.6%..."
                }
            ]
        }
    ]


@pytest.fixture
def sample_state(sample_exploration_results, sample_raw_content):
    """Complete GraphState for integration tests."""
    return GraphState(
        objective="Noticias del sector inmobiliario comercial en México",
        start_date="2026-01-20",
        end_date="2026-02-03",
        exploration_results=sample_exploration_results,
        topics=["Parques industriales", "Oficinas CDMX"],
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
                title="Inversión récord en parques industriales",
                article="La AMPIP proyecta crecimiento del 37% con inversiones de 5,831 MDD.",
                sources=["https://elfinanciero.com.mx/parques"]
            ),
            TopicSection(
                title="Recuperación del mercado de oficinas en CDMX",
                article="La vacancia bajó a 17.6% con absorción neta de 247,000 m².",
                sources=["https://realestatemarket.com.mx/oficinas"]
            )
        ]
    )


@pytest.fixture
def sample_report_output(sample_digest):
    """Sample ReportOutput wrapping a digest with metadata."""
    return ReportOutput(
        generated_at="2026-02-05T10:30:00",
        objective="Noticias del sector inmobiliario comercial en México",
        period_start="2026-01-20",
        period_end="2026-02-03",
        digest=sample_digest,
    )


@pytest.fixture
def sample_search_plan():
    """Sample SearchPlan from planner."""
    return SearchPlan(
        topics=[
            "Parques industriales nearshoring México 2026",
            "Oficinas corporativas CDMX vacancia",
            "Centro distribución Amazon Guadalajara"
        ],
        reasoning="Selected topics with concrete investment data and specific projects"
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
        missing_topics=["Desarrollos logísticos Bajío"],
        reasoning="Missing coverage on logistics sector which is mentioned in objective"
    )


# =============================================================================
# Mock Fixtures
# =============================================================================

@pytest.fixture
def mock_tavily_search_response():
    """Mock response from Tavily search API."""
    return {
        "results": [
            {
                "url": "https://elfinanciero.com.mx/test",
                "title": "Test Article Title",
                "content": "Test article content with relevant information..."
            },
            {
                "url": "https://expansion.mx/test",
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
                "url": "https://elfinanciero.com.mx/test",
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
    
    # Patch in all node modules that use Tavily
    monkeypatch.setattr("nodes.explorer.tavily", mock_client)
    monkeypatch.setattr("nodes.searcher.tavily", mock_client)
    monkeypatch.setattr("nodes.extractor.tavily", mock_client)
    
    return mock_client


@pytest.fixture
def mock_openai(monkeypatch, sample_search_plan, sample_evaluation_sufficient, sample_digest):
    """
    Mock ChatOpenAI to return predictable responses.
    
    Usage:
        def test_something(mock_openai):
            # OpenAI calls are now mocked
            result = planner_node(state)
    """
    mock_model = MagicMock()
    
    # Create a mock that returns different values based on structured output type
    def mock_with_structured_output(output_type):
        mock_chain = MagicMock()
        if output_type == SearchPlan:
            mock_chain.invoke.return_value = sample_search_plan
        elif output_type == Evaluation:
            mock_chain.invoke.return_value = sample_evaluation_sufficient
        elif output_type == NewsDigest:
            mock_chain.invoke.return_value = sample_digest
        return mock_chain
    
    mock_model.with_structured_output = mock_with_structured_output
    
    # Patch in all node modules that use OpenAI
    monkeypatch.setattr("nodes.planner.model", mock_model)
    monkeypatch.setattr("nodes.evaluator.model", mock_model)
    monkeypatch.setattr("nodes.analyst.model", mock_model)
    
    return mock_model


@pytest.fixture
def mock_openai_insufficient(monkeypatch, sample_search_plan, sample_evaluation_insufficient, sample_digest):
    """
    Mock ChatOpenAI that returns insufficient evaluation (triggers re-search).
    """
    mock_model = MagicMock()
    
    def mock_with_structured_output(output_type):
        mock_chain = MagicMock()
        if output_type == SearchPlan:
            mock_chain.invoke.return_value = sample_search_plan
        elif output_type == Evaluation:
            mock_chain.invoke.return_value = sample_evaluation_insufficient
        elif output_type == NewsDigest:
            mock_chain.invoke.return_value = sample_digest
        return mock_chain
    
    mock_model.with_structured_output = mock_with_structured_output
    
    monkeypatch.setattr("nodes.planner.model", mock_model)
    monkeypatch.setattr("nodes.evaluator.model", mock_model)
    monkeypatch.setattr("nodes.analyst.model", mock_model)
    
    return mock_model

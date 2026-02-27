"""
Unit tests for the evaluator node.
"""
import pytest

from nodes.evaluator import evaluator_node, should_search_more
from models import Evaluation, MAX_SEARCH_ITERATIONS


class TestEvaluatorNode:
    """Tests for evaluator_node function."""

    def test_returns_evaluation(self, mock_openai, sample_raw_content):
        """Evaluator should return an Evaluation object."""
        state = {
            "objective": "AI regulation news",
            "raw_content": sample_raw_content,
            "search_iterations": 1,
        }

        result = evaluator_node(state)

        assert "evaluation" in result
        assert isinstance(result["evaluation"], Evaluation)

    def test_evaluation_has_required_fields(self, mock_openai, sample_raw_content):
        """Evaluation should have is_sufficient, missing_topics, and reasoning."""
        state = {
            "objective": "AI regulation news",
            "raw_content": sample_raw_content,
            "search_iterations": 1,
        }

        result = evaluator_node(state)

        evaluation = result["evaluation"]
        assert hasattr(evaluation, "is_sufficient")
        assert hasattr(evaluation, "missing_topics")
        assert hasattr(evaluation, "reasoning")

    def test_handles_empty_raw_content(self, mock_openai):
        """Evaluator should handle case with no content."""
        state = {
            "objective": "AI regulation news",
            "raw_content": [],
            "search_iterations": 1,
        }

        result = evaluator_node(state)

        assert "evaluation" in result


class TestShouldSearchMore:
    """Tests for should_search_more conditional edge function."""

    def test_returns_analista_when_sufficient(self, sample_evaluation_sufficient):
        """Should route to analista when coverage is sufficient."""
        state = {
            "evaluation": sample_evaluation_sufficient,
            "search_iterations": 1,
        }

        result = should_search_more(state)

        assert result == "analista"

    def test_returns_buscador_when_insufficient(self, sample_evaluation_insufficient):
        """Should route to buscador when coverage is insufficient."""
        state = {
            "evaluation": sample_evaluation_insufficient,
            "search_iterations": 1,
        }

        result = should_search_more(state)

        assert result == "buscador"

    def test_returns_analista_when_max_iterations_reached(self, sample_evaluation_insufficient):
        """Should route to analista when max iterations reached, even if insufficient."""
        state = {
            "evaluation": sample_evaluation_insufficient,
            "search_iterations": MAX_SEARCH_ITERATIONS,
        }

        result = should_search_more(state)

        assert result == "analista"

    def test_returns_analista_when_no_evaluation(self):
        """Should route to analista when evaluation is missing."""
        state = {
            "evaluation": None,
            "search_iterations": 1,
        }

        result = should_search_more(state)

        assert result == "analista"

    def test_respects_iteration_limit(self, sample_evaluation_insufficient):
        """Should not exceed MAX_SEARCH_ITERATIONS."""
        state = {
            "evaluation": sample_evaluation_insufficient,
            "search_iterations": MAX_SEARCH_ITERATIONS + 1,
        }

        result = should_search_more(state)

        assert result == "analista"

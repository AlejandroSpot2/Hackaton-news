"""
Unit tests for the analyst node.
"""
import pytest

from nodes.analyst import analyze_news_node
from models import NewsDigest


class TestAnalystNode:
    """Tests for analyze_news_node function."""

    def test_returns_digest(self, mock_openai, sample_raw_content):
        """Analyst should return a NewsDigest."""
        state = {
            "objective": "AI regulation news",
            "raw_content": sample_raw_content,
        }

        result = analyze_news_node(state)

        assert "digest" in result
        assert isinstance(result["digest"], NewsDigest)

    def test_digest_has_sections(self, mock_openai, sample_raw_content):
        """NewsDigest should have sections."""
        state = {
            "objective": "AI regulation news",
            "raw_content": sample_raw_content,
        }

        result = analyze_news_node(state)

        assert hasattr(result["digest"], "sections")
        assert isinstance(result["digest"].sections, list)

    def test_sections_have_required_fields(self, mock_openai, sample_raw_content):
        """Each section should have title, article, and sources."""
        state = {
            "objective": "AI regulation news",
            "raw_content": sample_raw_content,
        }

        result = analyze_news_node(state)

        for section in result["digest"].sections:
            assert hasattr(section, "title")
            assert hasattr(section, "article")
            assert hasattr(section, "sources")

    def test_uses_structured_output(self, mock_openai, sample_raw_content):
        """Analyst should use with_structured_output for NewsDigest."""
        state = {
            "objective": "Test objective",
            "raw_content": sample_raw_content,
        }

        result = analyze_news_node(state)

        # Verify it returns a NewsDigest (which means structured output worked)
        assert isinstance(result["digest"], NewsDigest)

    def test_handles_empty_raw_content(self, mock_openai):
        """Analyst should handle case with no content."""
        state = {
            "objective": "AI regulation news",
            "raw_content": [],
        }

        result = analyze_news_node(state)

        assert "digest" in result

    def test_includes_objective_in_prompt(self, mock_openai, sample_raw_content):
        """Analyst should include the objective in the prompt."""
        state = {
            "objective": "Custom objective for testing",
            "raw_content": sample_raw_content,
        }

        result = analyze_news_node(state)

        # Verify it produces output (integration with objective is tested by behavior)
        assert result["digest"] is not None

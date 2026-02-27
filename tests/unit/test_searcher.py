"""
Unit tests for the searcher node.
"""
import pytest

from nodes.searcher import search_news_node


class TestSearcherNode:
    """Tests for search_news_node function."""

    def test_returns_raw_content(self, mock_tavily):
        """Searcher should return raw_content with search results."""
        state = {
            "topics": ["AI regulation EU"],
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "raw_content": [],
            "search_iterations": 0,
        }

        result = search_news_node(state)

        assert "raw_content" in result
        assert isinstance(result["raw_content"], list)

    def test_increments_search_iterations(self, mock_tavily):
        """Searcher should increment the iteration counter."""
        state = {
            "topics": ["Test topic"],
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "raw_content": [],
            "search_iterations": 0,
        }

        result = search_news_node(state)

        assert result["search_iterations"] == 1

    def test_accumulates_results_across_iterations(self, mock_tavily):
        """Searcher should append to existing raw_content."""
        existing_content = [{"topic": "Previous", "sources": []}]
        state = {
            "topics": ["New topic"],
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "raw_content": existing_content.copy(),
            "search_iterations": 1,
        }

        result = search_news_node(state)

        # Should have both old and new content
        assert len(result["raw_content"]) == 2
        assert result["search_iterations"] == 2

    def test_searches_each_topic(self, mock_tavily):
        """Searcher should call Tavily for each topic."""
        state = {
            "topics": ["Topic 1", "Topic 2", "Topic 3"],
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "raw_content": [],
            "search_iterations": 0,
        }

        search_news_node(state)

        assert mock_tavily.search.call_count == 3

    def test_uses_advanced_search_depth(self, mock_tavily):
        """Searcher should use advanced search depth for deep results."""
        state = {
            "topics": ["Test topic"],
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "raw_content": [],
            "search_iterations": 0,
        }

        search_news_node(state)

        call_kwargs = mock_tavily.search.call_args.kwargs
        assert call_kwargs["search_depth"] == "advanced"

    def test_raw_content_has_required_structure(self, mock_tavily):
        """Each raw_content item should have topic and sources."""
        state = {
            "topics": ["Test topic"],
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "raw_content": [],
            "search_iterations": 0,
        }

        result = search_news_node(state)

        for item in result["raw_content"]:
            assert "topic" in item
            assert "sources" in item
            assert isinstance(item["sources"], list)

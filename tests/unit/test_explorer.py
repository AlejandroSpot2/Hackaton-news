"""
Unit tests for the explorer node.
"""
import pytest

from nodes.explorer import explorer_node


class TestExplorerNode:
    """Tests for explorer_node function."""
    
    def test_returns_exploration_results(self, mock_tavily):
        """Explorer should return exploration_results in output."""
        state = {
            "objective": "Noticias inmobiliarias México",
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
        }
        
        result = explorer_node(state)
        
        assert "exploration_results" in result
        assert isinstance(result["exploration_results"], list)
    
    def test_exploration_results_have_required_fields(self, mock_tavily):
        """Each exploration result should have title, url, and snippet."""
        state = {
            "objective": "Noticias inmobiliarias México",
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
        }
        
        result = explorer_node(state)
        
        for item in result["exploration_results"]:
            assert "title" in item
            assert "url" in item
            assert "snippet" in item
    
    def test_calls_tavily_with_correct_parameters(self, mock_tavily):
        """Explorer should call Tavily with basic search depth."""
        state = {
            "objective": "Test objective",
            "start_date": "2026-01-01",
            "end_date": "2026-01-31",
        }
        
        explorer_node(state)
        
        mock_tavily.search.assert_called_once()
        call_kwargs = mock_tavily.search.call_args.kwargs
        
        assert call_kwargs["search_depth"] == "advanced"
        assert call_kwargs["max_results"] == 10
        assert call_kwargs["start_date"] == "2026-01-01"
        assert call_kwargs["end_date"] == "2026-01-31"
    
    def test_handles_empty_results(self, mock_tavily):
        """Explorer should handle empty search results gracefully."""
        mock_tavily.search.return_value = {"results": []}
        
        state = {
            "objective": "Noticias inmobiliarias México",
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
        }
        
        result = explorer_node(state)
        
        assert result["exploration_results"] == []
    
    def test_uses_default_objective_when_missing(self, mock_tavily):
        """Explorer should use default objective if not provided."""
        state = {
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
        }
        
        result = explorer_node(state)
        
        # Should not raise and should return results
        assert "exploration_results" in result

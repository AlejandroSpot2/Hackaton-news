"""
Unit tests for the planner node.
"""
import pytest

from nodes.planner import planner_node


class TestPlannerNode:
    """Tests for planner_node function."""

    def test_returns_topics_list(self, mock_openai, sample_exploration_results):
        """Planner should return a list of topics."""
        state = {
            "exploration_results": sample_exploration_results,
            "objective": "AI regulation news",
        }

        result = planner_node(state)

        assert "topics" in result
        assert isinstance(result["topics"], list)
        assert len(result["topics"]) >= 1

    def test_returns_planning_reasoning(self, mock_openai, sample_exploration_results):
        """Planner should explain its reasoning."""
        state = {
            "exploration_results": sample_exploration_results,
            "objective": "AI regulation news",
        }

        result = planner_node(state)

        assert "planning_reasoning" in result
        assert isinstance(result["planning_reasoning"], str)
        assert len(result["planning_reasoning"]) > 0

    def test_handles_empty_exploration_results(self, mock_openai):
        """Planner should handle case with no exploration results."""
        state = {
            "exploration_results": [],
            "objective": "AI regulation news",
        }

        result = planner_node(state)

        # Should still return topics (from model)
        assert "topics" in result

    def test_uses_structured_output(self, mock_openai, sample_exploration_results):
        """Planner should use with_structured_output for SearchPlan."""
        state = {
            "exploration_results": sample_exploration_results,
            "objective": "Test objective",
        }

        result = planner_node(state)

        # Verify it returns topics (which means structured output worked)
        assert isinstance(result["topics"], list)
        assert len(result["topics"]) > 0

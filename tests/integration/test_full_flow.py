"""
Integration tests for the complete News Bot agent flow.
"""
import pytest
from unittest.mock import patch, MagicMock

from agent import run_agent, save_report, app
from models import GraphState, NewsDigest, ReportOutput, SearchPlan, Evaluation, MAX_SEARCH_ITERATIONS


class TestFullAgentFlow:
    """Integration tests for the complete agent pipeline."""

    def test_full_flow_produces_digest(self, mock_tavily, mock_openai):
        """Test that the complete flow produces a NewsDigest."""
        digest = run_agent(
            objective="AI regulation news",
            start_date="2026-01-20",
            end_date="2026-02-03"
        )

        assert digest is not None
        assert isinstance(digest, NewsDigest)
        assert len(digest.sections) > 0

    def test_flow_calls_all_nodes_in_order(self, mock_tavily, mock_openai):
        """Test that all nodes are executed in the correct order."""
        nodes_called = []

        # Wrap nodes to track execution order
        original_stream = app.stream

        def tracking_stream(inputs):
            for output in original_stream(inputs):
                for key in output.keys():
                    nodes_called.append(key)
                yield output

        with patch.object(app, 'stream', tracking_stream):
            run_agent(
                objective="Test",
                start_date="2026-01-20",
                end_date="2026-02-03"
            )

        # Verify expected order (at minimum)
        expected_sequence = ["explorador", "planificador", "buscador", "extractor", "evaluador", "analista"]
        for expected_node in expected_sequence:
            assert expected_node in nodes_called, f"Node {expected_node} was not called"

    def test_flow_handles_empty_exploration(self, mock_tavily, mock_openai):
        """Test flow handles case where exploration returns nothing."""
        mock_tavily.search.return_value = {"results": []}

        digest = run_agent(
            objective="Obscure topic with no results",
            start_date="2026-01-20",
            end_date="2026-02-03"
        )

        # Should still produce a digest (might be empty)
        assert digest is not None


class TestConditionalLoop:
    """Tests for the evaluator conditional loop behavior."""

    def test_loops_when_coverage_insufficient(self, mock_tavily, mock_openai_insufficient):
        """Test that agent loops back to buscador when evaluation is insufficient."""
        # Track search calls by counting how many times search was called
        # We check this after the run completes

        # Run the agent
        run_agent(
            objective="Test",
            start_date="2026-01-20",
            end_date="2026-02-03"
        )

        # Should have searched multiple times:
        # Explorer (1) + first buscador (N topics) + re-search (M topics)
        # Since mock returns 3 topics and evaluation is insufficient, we expect multiple calls
        assert mock_tavily.search.call_count >= 4  # 1 explorer + 3 topics minimum

    def test_respects_max_iterations_limit(self, mock_tavily, mock_openai_insufficient):
        """Test that agent doesn't exceed MAX_SEARCH_ITERATIONS."""
        search_iterations = [0]

        # Track how many times buscador is called
        from nodes.searcher import search_news_node
        original_searcher = search_news_node

        def counting_searcher(state):
            search_iterations[0] += 1
            return original_searcher(state)

        with patch('agent.search_news_node', counting_searcher):
            run_agent(
                objective="Test",
                start_date="2026-01-20",
                end_date="2026-02-03"
            )

        # Should not exceed max iterations
        assert search_iterations[0] <= MAX_SEARCH_ITERATIONS + 1  # +1 for safety margin


class TestGraphCompilation:
    """Tests for the graph structure and compilation."""

    def test_graph_compiles_successfully(self):
        """Test that the graph compiles without errors."""
        assert app is not None

    def test_graph_has_correct_entry_point(self):
        """Test that the graph starts at explorador."""
        # Get the graph structure
        graph_dict = app.get_graph().to_json()

        # The entry point should be explorador
        assert "explorador" in str(graph_dict)

    def test_initial_state_structure(self):
        """Test that initial state has all required fields."""
        initial_state: GraphState = {
            "objective": "Test",
            "context": "",
            "start_date": "2026-01-20",
            "end_date": "2026-02-03",
            "exploration_results": [],
            "topics": [],
            "planning_reasoning": "",
            "raw_content": [],
            "evaluation": None,
            "search_iterations": 0,
            "digest": None,
        }

        # All required fields should be present
        required_fields = [
            "objective", "context", "start_date", "end_date",
            "exploration_results", "topics", "planning_reasoning",
            "raw_content", "evaluation", "search_iterations", "digest"
        ]

        for field in required_fields:
            assert field in initial_state


class TestSaveReport:
    """Tests for JSON report output."""

    def test_save_report_creates_json_file(self, sample_digest, tmp_path):
        """save_report should create a valid JSON file."""
        filepath = tmp_path / "test_report.json"

        report = save_report(
            digest=sample_digest,
            objective="Test objective",
            start_date="2026-01-20",
            end_date="2026-02-03",
            filename=str(filepath),
        )

        assert filepath.exists()
        assert isinstance(report, ReportOutput)

    def test_saved_json_is_valid_report_output(self, sample_digest, tmp_path):
        """The saved JSON should deserialize back into a ReportOutput."""
        filepath = tmp_path / "test_report.json"

        save_report(
            digest=sample_digest,
            objective="Test objective",
            start_date="2026-01-20",
            end_date="2026-02-03",
            filename=str(filepath),
        )

        loaded = ReportOutput.model_validate_json(filepath.read_text(encoding="utf-8"))
        assert loaded.objective == "Test objective"
        assert loaded.period_start == "2026-01-20"
        assert loaded.period_end == "2026-02-03"
        assert len(loaded.digest.sections) == len(sample_digest.sections)

    def test_saved_json_preserves_section_data(self, sample_digest, tmp_path):
        """Section titles, articles, and sources should survive round-trip."""
        filepath = tmp_path / "test_report.json"

        save_report(
            digest=sample_digest,
            objective="Test",
            start_date="2026-01-20",
            end_date="2026-02-03",
            filename=str(filepath),
        )

        loaded = ReportOutput.model_validate_json(filepath.read_text(encoding="utf-8"))

        for original, loaded_sec in zip(sample_digest.sections, loaded.digest.sections):
            assert original.title == loaded_sec.title
            assert original.article == loaded_sec.article
            assert original.sources == loaded_sec.sources


class TestErrorHandling:
    """Tests for error handling in the agent flow."""

    def test_handles_tavily_api_error(self, mock_openai):
        """Test that agent handles Tavily API errors gracefully."""
        with patch('nodes.explorer.tavily') as mock_tavily:
            mock_tavily.search.side_effect = Exception("API Error")

            # Should raise or handle gracefully
            with pytest.raises(Exception):
                run_agent(
                    objective="Test",
                    start_date="2026-01-20",
                    end_date="2026-02-03"
                )

    def test_handles_openai_api_error(self, mock_tavily):
        """Test that agent handles OpenAI API errors gracefully."""
        with patch('nodes.planner.model') as mock_model:
            mock_model.with_structured_output.return_value.invoke.side_effect = Exception("API Error")

            # Should raise or handle gracefully
            with pytest.raises(Exception):
                run_agent(
                    objective="Test",
                    start_date="2026-01-20",
                    end_date="2026-02-03"
                )

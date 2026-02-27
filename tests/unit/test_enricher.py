"""
Unit tests for the enricher node (Pioneer AI entity extraction).
"""
import pytest
from unittest.mock import MagicMock

from nodes.enricher import enrich_content_node


class TestEnricherNode:
    """Tests for enrich_content_node function."""

    def test_returns_enriched_raw_content(self, mock_openai, sample_raw_content):
        """Enricher should return raw_content with entities added."""
        state = {"raw_content": sample_raw_content}

        result = enrich_content_node(state)

        assert "raw_content" in result
        assert len(result["raw_content"]) == len(sample_raw_content)

    def test_adds_entities_to_sources(self, mock_openai, sample_raw_content):
        """Each source should have an 'entities' field after enrichment."""
        state = {"raw_content": sample_raw_content}

        result = enrich_content_node(state)

        for topic_data in result["raw_content"]:
            for source in topic_data["sources"]:
                assert "entities" in source

    def test_entities_are_grouped_by_label(self, monkeypatch, sample_raw_content):
        """Entities should be grouped as {label: [values]}."""
        mock_pioneer = MagicMock(return_value=[
            {"label": "PERSON", "text": "Tim Cook"},
            {"label": "ORGANIZATION", "text": "Apple"},
            {"label": "ORGANIZATION", "text": "Google"},
        ])
        monkeypatch.setattr("nodes.enricher.pioneer_extract", mock_pioneer)

        state = {"raw_content": sample_raw_content}
        result = enrich_content_node(state)

        first_source = result["raw_content"][0]["sources"][0]
        entities = first_source["entities"]

        assert "PERSON" in entities
        assert "Tim Cook" in entities["PERSON"]
        assert "ORGANIZATION" in entities
        assert len(entities["ORGANIZATION"]) == 2

    def test_handles_empty_raw_content(self, mock_openai):
        """Enricher should handle case with no content."""
        state = {"raw_content": []}

        result = enrich_content_node(state)

        assert result["raw_content"] == []

    def test_handles_pioneer_returning_empty(self, monkeypatch, sample_raw_content):
        """Enricher should handle Pioneer returning no entities gracefully."""
        mock_pioneer = MagicMock(return_value=[])
        monkeypatch.setattr("nodes.enricher.pioneer_extract", mock_pioneer)

        state = {"raw_content": sample_raw_content}
        result = enrich_content_node(state)

        for topic_data in result["raw_content"]:
            for source in topic_data["sources"]:
                assert source["entities"] == {}

    def test_skips_short_content(self, monkeypatch, sample_raw_content):
        """Enricher should skip sources with very short content."""
        mock_pioneer = MagicMock(return_value=[
            {"label": "PERSON", "text": "Test"},
        ])
        monkeypatch.setattr("nodes.enricher.pioneer_extract", mock_pioneer)

        sample_raw_content[0]["sources"][0]["content"] = "Too short"
        state = {"raw_content": sample_raw_content}

        result = enrich_content_node(state)

        short_source = result["raw_content"][0]["sources"][0]
        assert short_source["entities"] == {}

    def test_truncates_long_content(self, monkeypatch, sample_raw_content):
        """Enricher should truncate content longer than 4000 chars."""
        call_args = []

        def capture_pioneer(model_id, text, schema):
            call_args.append(text)
            return [{"label": "PERSON", "text": "Test"}]

        monkeypatch.setattr("nodes.enricher.pioneer_extract", capture_pioneer)

        sample_raw_content[0]["sources"][0]["content"] = "A" * 10000
        state = {"raw_content": sample_raw_content}

        enrich_content_node(state)

        assert len(call_args[0]) == 4000

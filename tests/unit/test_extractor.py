"""
Unit tests for the extractor node.
"""
import pytest

from nodes.extractor import extract_content_node


class TestExtractorNode:
    """Tests for extract_content_node function."""
    
    def test_returns_enriched_raw_content(self, mock_tavily, sample_raw_content):
        """Extractor should return enriched raw_content."""
        state = {"raw_content": sample_raw_content}
        
        result = extract_content_node(state)
        
        assert "raw_content" in result
        assert isinstance(result["raw_content"], list)
    
    def test_calls_extract_for_each_topic(self, mock_tavily, sample_raw_content):
        """Extractor should call Tavily extract for each topic's URLs."""
        state = {"raw_content": sample_raw_content}
        
        extract_content_node(state)
        
        # Should be called once per topic with sources
        assert mock_tavily.extract.call_count == len(sample_raw_content)
    
    def test_handles_empty_sources(self, mock_tavily):
        """Extractor should handle topics with no sources."""
        state = {
            "raw_content": [
                {"topic": "Empty topic", "sources": []}
            ]
        }
        
        result = extract_content_node(state)
        
        # Should not call extract for empty sources
        mock_tavily.extract.assert_not_called()
        assert len(result["raw_content"]) == 1
    
    def test_handles_extraction_errors(self, mock_tavily, sample_raw_content):
        """Extractor should handle API errors gracefully."""
        mock_tavily.extract.side_effect = Exception("API Error")
        
        state = {"raw_content": sample_raw_content}
        
        # Should not raise, just log error
        result = extract_content_node(state)
        
        assert "raw_content" in result
    
    def test_removes_failed_extractions(self, mock_tavily):
        """Extractor should remove sources that failed to extract."""
        # Create fresh test data to avoid mutation issues
        test_content = [
            {
                "topic": "Test Topic",
                "sources": [
                    {"url": "https://fail.com/article", "title": "Will Fail", "content": "..."},
                    {"url": "https://success.com/article", "title": "Will Succeed", "content": "..."}
                ]
            }
        ]
        
        mock_tavily.extract.return_value = {
            "results": [{"url": "https://success.com/article", "raw_content": "Success content"}],
            "failed_results": [{"url": "https://fail.com/article"}]
        }
        
        state = {"raw_content": test_content}
        
        result = extract_content_node(state)
        
        # Should have removed the failed URL
        first_topic = result["raw_content"][0]
        assert len(first_topic["sources"]) == 1
        assert first_topic["sources"][0]["url"] == "https://success.com/article"
    
    def test_truncates_content_to_3000_chars(self, mock_tavily):
        """Extractor should truncate extracted content to 3000 characters."""
        long_content = "x" * 5000
        mock_tavily.extract.return_value = {
            "results": [{"url": "https://test.com", "raw_content": long_content}],
            "failed_results": []
        }
        
        state = {
            "raw_content": [
                {"topic": "Test", "sources": [{"url": "https://test.com", "title": "Test", "content": ""}]}
            ]
        }
        
        result = extract_content_node(state)
        
        extracted_content = result["raw_content"][0]["sources"][0]["content"]
        assert len(extracted_content) <= 3000

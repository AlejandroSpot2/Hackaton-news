"""
Unit tests for the converter module.
"""
import json

import pytest

from converter import convert, to_markdown, to_plaintext
from models import ReportOutput


class TestToMarkdown:
    """Tests for Markdown conversion."""

    def test_contains_title(self, sample_report_output):
        """Markdown output should have the main heading."""
        md = to_markdown(sample_report_output)
        assert "# News Research Report" in md

    def test_contains_section_headings(self, sample_report_output):
        """Each digest section should appear as an h2."""
        md = to_markdown(sample_report_output)
        for section in sample_report_output.digest.sections:
            assert f"## {section.title}" in md

    def test_contains_sources(self, sample_report_output):
        """All source URLs should be present."""
        md = to_markdown(sample_report_output)
        for section in sample_report_output.digest.sections:
            for source in section.sources:
                assert source in md

    def test_contains_metadata(self, sample_report_output):
        """Objective and period should be in the output."""
        md = to_markdown(sample_report_output)
        assert sample_report_output.objective in md
        assert sample_report_output.period_start in md
        assert sample_report_output.period_end in md


class TestToPlaintext:
    """Tests for plain-text conversion."""

    def test_contains_header(self, sample_report_output):
        """Plain-text output should have the report header."""
        txt = to_plaintext(sample_report_output)
        assert "NEWS RESEARCH REPORT" in txt

    def test_contains_section_titles(self, sample_report_output):
        """Each section title should appear in the output."""
        txt = to_plaintext(sample_report_output)
        for section in sample_report_output.digest.sections:
            assert section.title in txt

    def test_contains_sources(self, sample_report_output):
        """All source URLs should be present."""
        txt = to_plaintext(sample_report_output)
        for section in sample_report_output.digest.sections:
            for source in section.sources:
                assert source in txt

    def test_contains_metadata(self, sample_report_output):
        """Objective and period should be in the output."""
        txt = to_plaintext(sample_report_output)
        assert sample_report_output.objective in txt
        assert sample_report_output.period_start in txt


class TestConvertFunction:
    """Tests for the convert() function (file I/O)."""

    def test_convert_to_md(self, sample_report_output, tmp_path):
        """convert() should create an .md file."""
        json_file = tmp_path / "report.json"
        json_file.write_text(
            sample_report_output.model_dump_json(indent=2), encoding="utf-8"
        )
        output_file = tmp_path / "report.md"

        result_paths = convert(str(json_file), fmt="md", output_path=str(output_file))
        assert result_paths[0].endswith(".md")
        content = output_file.read_text(encoding="utf-8")
        assert "# News Research Report" in content

    def test_convert_to_txt(self, sample_report_output, tmp_path):
        """convert() should create a .txt file."""
        json_file = tmp_path / "report.json"
        json_file.write_text(
            sample_report_output.model_dump_json(indent=2), encoding="utf-8"
        )
        output_file = tmp_path / "report.txt"

        result_paths = convert(str(json_file), fmt="txt", output_path=str(output_file))
        assert result_paths[0].endswith(".txt")
        content = output_file.read_text(encoding="utf-8")
        assert "NEWS RESEARCH REPORT" in content

    def test_convert_custom_output_path(self, sample_report_output, tmp_path):
        """convert() should honour a custom output path."""
        json_file = tmp_path / "report.json"
        json_file.write_text(
            sample_report_output.model_dump_json(indent=2), encoding="utf-8"
        )
        custom = tmp_path / "custom_name.md"

        result_paths = convert(str(json_file), fmt="md", output_path=str(custom))
        assert result_paths[0] == str(custom)
        assert custom.exists()

    def test_convert_raises_on_missing_file(self, tmp_path):
        """convert() should raise FileNotFoundError for missing input."""
        with pytest.raises(FileNotFoundError):
            convert(str(tmp_path / "nope.json"))

    def test_convert_raises_on_bad_format(self, sample_report_output, tmp_path):
        """convert() should reject unsupported formats."""
        json_file = tmp_path / "report.json"
        json_file.write_text(
            sample_report_output.model_dump_json(indent=2), encoding="utf-8"
        )

        with pytest.raises(ValueError, match="Unsupported format"):
            convert(str(json_file), fmt="html")

    def test_roundtrip_json_to_md(self, sample_report_output, tmp_path):
        """Full round-trip: ReportOutput -> JSON -> .md preserves content."""
        json_file = tmp_path / "report.json"
        json_file.write_text(
            sample_report_output.model_dump_json(indent=2), encoding="utf-8"
        )
        output_file = tmp_path / "report.md"

        convert(str(json_file), fmt="md", output_path=str(output_file))
        md = output_file.read_text(encoding="utf-8")

        for section in sample_report_output.digest.sections:
            assert section.title in md
            assert section.article in md

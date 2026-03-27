"""Tests for scimap.utils.pdf_reader."""
from unittest.mock import patch, MagicMock
from pathlib import Path

from scimap.utils.pdf_reader import extract_metadata, load_pdfs


class TestExtractMetadata:
    def test_extracts_year_from_text(self):
        text = "Published in 2023 by the journal..."
        result = extract_metadata(text, "paper.pdf")
        assert result["year"] == "2023"

    def test_extracts_title_from_first_long_line(self):
        text = "Journal of ML\nDeep Learning for Natural Language Processing\nSmith, J. and Doe, A.\n2023"
        result = extract_metadata(text, "paper.pdf")
        assert result["title"] == "Deep Learning for Natural Language Processing"

    def test_extracts_authors_after_title(self):
        text = "Short\nA Comprehensive Study of Transformer Models\nSmith, J. and Doe, A.\n2023"
        result = extract_metadata(text, "paper.pdf")
        assert result["authors"] == "Smith, J. and Doe, A."

    def test_falls_back_to_filename_for_title(self):
        text = "x\ny\nz"  # No line > 15 chars
        result = extract_metadata(text, "my_cool_paper-2023.pdf")
        assert result["title"] == "my cool paper 2023"

    def test_extracts_year_from_filename(self):
        text = "no year in the text at all"
        result = extract_metadata(text, "paper_2021_final.pdf")
        assert result["year"] == "2021"

    def test_skips_doi_lines(self):
        text = "doi:10.1234/foo\nActual Title of the Paper Here\nAuthors here"
        result = extract_metadata(text, "paper.pdf")
        assert result["title"] == "Actual Title of the Paper Here"

    def test_no_authors_when_missing(self):
        text = "A Long Enough Title For Detection\n2023\nSome other stuff"
        result = extract_metadata(text, "paper.pdf")
        # "2023" doesn't contain comma or "and", so no authors
        assert result["authors"] is None

    def test_handles_empty_text(self):
        result = extract_metadata("", "unknown.pdf")
        assert result["title"] == "unknown"
        assert result["year"] is None


class TestLoadPdfs:
    @patch("scimap.utils.pdf_reader.extract_text")
    def test_loads_pdfs_from_directory(self, mock_extract, tmp_path):
        # Create fake PDF files
        (tmp_path / "paper1.pdf").write_bytes(b"fake pdf")
        (tmp_path / "paper2.pdf").write_bytes(b"fake pdf")
        (tmp_path / "not_a_pdf.txt").write_text("ignore me")

        mock_extract.return_value = "A Title That Is Long Enough to Match\nSmith, J. and Lee, B.\nPublished 2022\n\nContent here."

        papers = load_pdfs(str(tmp_path))
        assert len(papers) == 2
        assert all(p["source"] == "local_pdf" for p in papers)
        assert all(p["full_text"] is True for p in papers)

    @patch("scimap.utils.pdf_reader.extract_text")
    def test_handles_extraction_error(self, mock_extract, tmp_path):
        (tmp_path / "bad.pdf").write_bytes(b"corrupted")
        mock_extract.side_effect = Exception("PDF parse error")

        papers = load_pdfs(str(tmp_path))
        assert len(papers) == 1
        assert papers[0]["full_text"] is False
        assert "error" in papers[0]

    @patch("scimap.utils.pdf_reader.extract_text")
    def test_skips_empty_pdfs(self, mock_extract, tmp_path):
        (tmp_path / "empty.pdf").write_bytes(b"fake")
        mock_extract.return_value = "   "  # whitespace only

        papers = load_pdfs(str(tmp_path))
        assert len(papers) == 0

    def test_empty_directory(self, tmp_path):
        papers = load_pdfs(str(tmp_path))
        assert papers == []

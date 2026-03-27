"""Tests for scimap.pipeline.ingestion."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

from scimap.pipeline.ingestion import ingest_papers, _ingest_remote, _pdf_bytes_to_text


class TestIngestPapers:
    @patch("scimap.pipeline.ingestion._ingest_local")
    def test_local_path(self, mock_local):
        mock_local.return_value = [{"title": "Local Paper"}]
        result = ingest_papers(pdf_dir="/some/path")
        mock_local.assert_called_once_with("/some/path")
        assert result == [{"title": "Local Paper"}]

    @patch("scimap.pipeline.ingestion._ingest_remote")
    def test_remote_with_question(self, mock_remote):
        mock_remote.return_value = [{"title": "Remote Paper"}]
        result = ingest_papers(question="What is NLP?")
        mock_remote.assert_called_once_with("What is NLP?", 20)

    @patch("scimap.pipeline.ingestion._ingest_remote")
    def test_remote_with_topic(self, mock_remote):
        mock_remote.return_value = []
        ingest_papers(topic="machine learning")
        mock_remote.assert_called_once_with("machine learning", 20)

    @patch("scimap.pipeline.ingestion._ingest_remote")
    def test_remote_with_n_papers(self, mock_remote):
        mock_remote.return_value = []
        ingest_papers(question="query", n_papers=50)
        mock_remote.assert_called_once_with("query", 50)

    @patch("scimap.pipeline.ingestion._ingest_remote")
    def test_question_takes_precedence_over_topic(self, mock_remote):
        mock_remote.return_value = []
        ingest_papers(question="specific question", topic="broad topic")
        assert mock_remote.call_args[0][0] == "specific question"


class TestIngestRemote:
    @patch("scimap.pipeline.ingestion.download_pdf")
    @patch("scimap.pipeline.ingestion.search_arxiv")
    @patch("scimap.pipeline.ingestion.fetch_with_rate_limit")
    def test_semantic_scholar_only(self, mock_ss, mock_arxiv, mock_dl):
        mock_ss.return_value = [
            {"title": "Paper 1", "pdf_url": None, "abstract": "Abstract 1"},
            {"title": "Paper 2", "pdf_url": None, "abstract": "Abstract 2"},
        ]
        papers = _ingest_remote("query", n_papers=2)
        assert len(papers) == 2
        mock_arxiv.assert_not_called()

    @patch("scimap.pipeline.ingestion.download_pdf")
    @patch("scimap.pipeline.ingestion.search_arxiv")
    @patch("scimap.pipeline.ingestion.fetch_with_rate_limit")
    def test_supplements_with_arxiv(self, mock_ss, mock_arxiv, mock_dl):
        mock_ss.return_value = [
            {"title": "SS Paper", "pdf_url": None, "abstract": "abs"},
        ]
        mock_arxiv.return_value = [
            {"title": "ArXiv Paper", "pdf_url": None, "abstract": "abs2"},
        ]
        papers = _ingest_remote("query", n_papers=5)
        assert len(papers) == 2
        mock_arxiv.assert_called_once()

    @patch("scimap.pipeline.ingestion.download_pdf")
    @patch("scimap.pipeline.ingestion.search_arxiv")
    @patch("scimap.pipeline.ingestion.fetch_with_rate_limit")
    def test_deduplicates_by_title(self, mock_ss, mock_arxiv, mock_dl):
        mock_ss.return_value = [
            {"title": "Same Title", "pdf_url": None, "abstract": "abs1"},
        ]
        mock_arxiv.return_value = [
            {"title": "Same Title", "pdf_url": None, "abstract": "abs2"},
            {"title": "Different Paper", "pdf_url": None, "abstract": "abs3"},
        ]
        papers = _ingest_remote("query", n_papers=5)
        titles = [p["title"] for p in papers]
        assert titles.count("Same Title") == 1
        assert "Different Paper" in titles

    @patch("scimap.pipeline.ingestion._pdf_bytes_to_text")
    @patch("scimap.pipeline.ingestion.download_pdf")
    @patch("scimap.pipeline.ingestion.search_arxiv")
    @patch("scimap.pipeline.ingestion.fetch_with_rate_limit")
    def test_downloads_pdf_when_available(self, mock_ss, mock_arxiv, mock_dl, mock_pdf2text):
        mock_ss.return_value = [
            {"title": "Paper", "pdf_url": "https://example.com/p.pdf", "abstract": "short abs"},
        ]
        mock_dl.return_value = b"pdf bytes"
        mock_pdf2text.return_value = "x" * 300  # > 200 chars threshold

        papers = _ingest_remote("query", n_papers=1)
        assert papers[0]["full_text"] is True
        assert papers[0]["text"] == "x" * 300

    @patch("scimap.pipeline.ingestion.download_pdf")
    @patch("scimap.pipeline.ingestion.search_arxiv")
    @patch("scimap.pipeline.ingestion.fetch_with_rate_limit")
    def test_falls_back_to_abstract(self, mock_ss, mock_arxiv, mock_dl):
        mock_ss.return_value = [
            {"title": "Paper", "pdf_url": "https://example.com/p.pdf", "abstract": "The abstract"},
        ]
        mock_dl.return_value = None  # download failed

        papers = _ingest_remote("query", n_papers=1)
        assert papers[0]["full_text"] is False
        assert papers[0]["text"] == "The abstract"

    @patch("scimap.pipeline.ingestion._pdf_bytes_to_text")
    @patch("scimap.pipeline.ingestion.download_pdf")
    @patch("scimap.pipeline.ingestion.search_arxiv")
    @patch("scimap.pipeline.ingestion.fetch_with_rate_limit")
    def test_short_pdf_text_uses_abstract(self, mock_ss, mock_arxiv, mock_dl, mock_pdf2text):
        mock_ss.return_value = [
            {"title": "Paper", "pdf_url": "https://example.com/p.pdf", "abstract": "Good abstract"},
        ]
        mock_dl.return_value = b"pdf"
        mock_pdf2text.return_value = "short"  # < 200 chars

        papers = _ingest_remote("query", n_papers=1)
        assert papers[0]["full_text"] is False
        assert papers[0]["text"] == "Good abstract"


class TestPdfBytesToText:
    @patch("scimap.pipeline.ingestion.extract_text")
    def test_converts_pdf_bytes(self, mock_extract):
        mock_extract.return_value = "Extracted text from PDF"
        result = _pdf_bytes_to_text(b"fake pdf bytes")
        assert result == "Extracted text from PDF"

    @patch("scimap.pipeline.ingestion.extract_text")
    def test_returns_none_on_error(self, mock_extract):
        mock_extract.side_effect = Exception("parse error")
        result = _pdf_bytes_to_text(b"bad pdf")
        assert result is None

"""Tests for scimap.utils.arxiv_fetcher."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import patch, MagicMock

import responses
import pytest

from scimap.utils.arxiv_fetcher import search_arxiv, download_arxiv_pdf


def _make_arxiv_result(entry_id="http://arxiv.org/abs/2301.12345v1", title="Test Paper",
                        authors=None, year=2023, summary="Abstract text",
                        pdf_url="https://arxiv.org/pdf/2301.12345v1"):
    """Create a mock arxiv.Result object."""
    result = MagicMock()
    result.entry_id = entry_id
    result.title = title
    result.authors = authors or [MagicMock(name="Author A"), MagicMock(name="Author B")]
    # MagicMock.name is special — set it explicitly
    for i, a in enumerate(result.authors):
        a.name = f"Author {chr(65 + i)}"
    result.published = MagicMock()
    result.published.year = year
    result.summary = summary
    result.pdf_url = pdf_url
    result.get_short_id.return_value = "2301.12345v1"
    return result


class TestSearchArxiv:
    @patch("scimap.utils.arxiv_fetcher.arxiv.Client")
    @patch("scimap.utils.arxiv_fetcher.arxiv.Search")
    def test_basic_search(self, mock_search_cls, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.results.return_value = [_make_arxiv_result()]

        papers = search_arxiv("transformers", max_results=5)

        assert len(papers) == 1
        assert papers[0]["title"] == "Test Paper"
        assert papers[0]["authors"] == "Author A, Author B"
        assert papers[0]["year"] == 2023
        assert papers[0]["source"] == "arxiv"
        assert papers[0]["arxiv_id"] == "2301.12345v1"
        assert papers[0]["pdf_url"] == "https://arxiv.org/pdf/2301.12345v1"

    @patch("scimap.utils.arxiv_fetcher.arxiv.Client")
    @patch("scimap.utils.arxiv_fetcher.arxiv.Search")
    def test_handles_no_publish_date(self, mock_search_cls, mock_client_cls):
        result = _make_arxiv_result()
        result.published = None

        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.results.return_value = [result]

        papers = search_arxiv("query")
        assert papers[0]["year"] is None

    @patch("scimap.utils.arxiv_fetcher.arxiv.Client")
    @patch("scimap.utils.arxiv_fetcher.arxiv.Search")
    def test_empty_results(self, mock_search_cls, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.results.return_value = []

        papers = search_arxiv("nonexistent topic")
        assert papers == []

    @patch("scimap.utils.arxiv_fetcher.arxiv.Client")
    @patch("scimap.utils.arxiv_fetcher.arxiv.Search")
    def test_multiple_results(self, mock_search_cls, mock_client_cls):
        results = [
            _make_arxiv_result(entry_id=f"http://arxiv.org/abs/230{i}.00001v1", title=f"Paper {i}")
            for i in range(3)
        ]
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.results.return_value = results

        papers = search_arxiv("query", max_results=10)
        assert len(papers) == 3

    @patch("scimap.utils.arxiv_fetcher.arxiv.Client")
    @patch("scimap.utils.arxiv_fetcher.arxiv.Search")
    def test_citation_count_is_none(self, mock_search_cls, mock_client_cls):
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.results.return_value = [_make_arxiv_result()]

        papers = search_arxiv("query")
        assert papers[0]["citation_count"] is None


class TestDownloadArxivPdf:
    @responses.activate
    def test_downloads_pdf(self):
        pdf_bytes = b"%PDF-1.4 content"
        responses.add(
            responses.GET,
            "https://arxiv.org/pdf/2301.12345v1",
            body=pdf_bytes,
            status=200,
        )
        paper = {"pdf_url": "https://arxiv.org/pdf/2301.12345v1"}
        result = download_arxiv_pdf(paper)
        assert result == pdf_bytes

    def test_returns_none_without_url(self):
        paper = {"pdf_url": None}
        result = download_arxiv_pdf(paper)
        assert result is None

    def test_returns_none_missing_key(self):
        paper = {}
        result = download_arxiv_pdf(paper)
        assert result is None

    @responses.activate
    def test_returns_none_on_http_error(self):
        responses.add(
            responses.GET,
            "https://arxiv.org/pdf/bad.pdf",
            status=500,
        )
        paper = {"pdf_url": "https://arxiv.org/pdf/bad.pdf"}
        result = download_arxiv_pdf(paper)
        assert result is None

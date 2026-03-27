"""Tests for scimap.utils.semantic_scholar."""
from __future__ import annotations

import responses
from responses import matchers

from scimap.utils.semantic_scholar import BASE_URL, search_papers, download_pdf, fetch_with_rate_limit


SEARCH_RESPONSE = {
    "data": [
        {
            "paperId": "abc123",
            "title": "Transformers for NLP",
            "authors": [{"name": "Smith, J."}, {"name": "Doe, A."}],
            "year": 2023,
            "abstract": "We study transformers.",
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "citationCount": 42,
            "externalIds": {"ArXiv": "2301.12345"},
        },
        {
            "paperId": "def456",
            "title": "Attention Is All You Need",
            "authors": None,
            "year": 2017,
            "abstract": "A new architecture.",
            "openAccessPdf": None,
            "citationCount": 50000,
            "externalIds": None,
        },
    ],
    "next": None,
}


class TestSearchPapers:
    @responses.activate
    def test_basic_search(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = search_papers("transformers NLP", limit=20)
        assert len(papers) == 2
        assert papers[0]["title"] == "Transformers for NLP"
        assert papers[0]["authors"] == "Smith, J., Doe, A."
        assert papers[0]["year"] == 2023
        assert papers[0]["pdf_url"] == "https://example.com/paper.pdf"
        assert papers[0]["arxiv_id"] == "2301.12345"
        assert papers[0]["source"] == "semantic_scholar"

    @responses.activate
    def test_handles_null_authors(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = search_papers("attention", limit=20)
        assert papers[1]["authors"] is None

    @responses.activate
    def test_handles_no_pdf(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = search_papers("attention", limit=20)
        assert papers[1]["pdf_url"] is None

    @responses.activate
    def test_handles_no_external_ids(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = search_papers("attention", limit=20)
        assert papers[1]["arxiv_id"] is None

    @responses.activate
    def test_empty_results(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json={"data": []},
            status=200,
        )
        papers = search_papers("nonexistent topic xyz")
        assert papers == []

    @responses.activate
    def test_limit_capped_at_100(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json={"data": []},
            status=200,
        )
        search_papers("query", limit=500)
        assert responses.calls[0].request.params["limit"] == "100"

    @responses.activate
    def test_raises_on_http_error(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json={"error": "forbidden"},
            status=403,
        )
        import requests
        import pytest
        with pytest.raises(requests.HTTPError):
            search_papers("query")


class TestDownloadPdf:
    @responses.activate
    def test_downloads_pdf(self):
        pdf_content = b"%PDF-1.4 fake pdf content"
        responses.add(
            responses.GET,
            "https://example.com/paper.pdf",
            body=pdf_content,
            status=200,
            content_type="application/pdf",
        )
        result = download_pdf("https://example.com/paper.pdf")
        assert result == pdf_content

    @responses.activate
    def test_returns_none_on_non_pdf(self):
        responses.add(
            responses.GET,
            "https://example.com/page.html",
            body=b"<html>not a pdf</html>",
            status=200,
            content_type="text/html",
        )
        result = download_pdf("https://example.com/page.html")
        assert result is None

    @responses.activate
    def test_returns_none_on_error(self):
        responses.add(
            responses.GET,
            "https://example.com/gone.pdf",
            status=404,
        )
        result = download_pdf("https://example.com/gone.pdf")
        assert result is None

    @responses.activate
    def test_accepts_pdf_url_extension(self):
        # Even if content-type is missing, .pdf extension should work
        responses.add(
            responses.GET,
            "https://example.com/paper.pdf",
            body=b"pdf bytes",
            status=200,
            content_type="application/octet-stream",
        )
        result = download_pdf("https://example.com/paper.pdf")
        assert result == b"pdf bytes"


class TestFetchWithRateLimit:
    @responses.activate
    def test_basic_fetch(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = fetch_with_rate_limit("transformers", limit=20)
        assert len(papers) == 2

    @responses.activate
    def test_respects_limit(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = fetch_with_rate_limit("transformers", limit=1)
        assert len(papers) == 1

    @responses.activate
    def test_handles_rate_limit_then_success(self):
        # First call returns 429, second returns data
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json={"message": "rate limited"},
            status=429,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json=SEARCH_RESPONSE,
            status=200,
        )
        papers = fetch_with_rate_limit("query", limit=2)
        assert len(papers) == 2

    @responses.activate
    def test_handles_server_error(self):
        responses.add(
            responses.GET,
            f"{BASE_URL}/paper/search",
            json={"error": "internal"},
            status=500,
        )
        papers = fetch_with_rate_limit("query", limit=5)
        assert papers == []

    @responses.activate
    def test_pagination_with_next(self):
        batch1 = {
            "data": [
                {
                    "paperId": "p1",
                    "title": "Paper 1",
                    "authors": [{"name": "A"}],
                    "year": 2023,
                    "abstract": "abs1",
                    "openAccessPdf": None,
                    "citationCount": 1,
                    "externalIds": None,
                }
            ],
            "next": 20,
        }
        batch2 = {
            "data": [
                {
                    "paperId": "p2",
                    "title": "Paper 2",
                    "authors": [{"name": "B"}],
                    "year": 2022,
                    "abstract": "abs2",
                    "openAccessPdf": None,
                    "citationCount": 2,
                    "externalIds": None,
                }
            ],
            "next": None,
        }
        responses.add(responses.GET, f"{BASE_URL}/paper/search", json=batch1, status=200)
        responses.add(responses.GET, f"{BASE_URL}/paper/search", json=batch2, status=200)

        papers = fetch_with_rate_limit("query", limit=5)
        assert len(papers) == 2
        assert papers[0]["title"] == "Paper 1"
        assert papers[1]["title"] == "Paper 2"

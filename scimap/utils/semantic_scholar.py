from __future__ import annotations

import time

import requests

from scimap.config import SEMANTIC_SCHOLAR_API_KEY

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,authors,year,abstract,openAccessPdf,citationCount,externalIds"


def search_papers(query: str, limit: int = 20) -> list[dict]:
    """Search Semantic Scholar for papers matching a query."""
    headers = {}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": FIELDS,
    }

    resp = requests.get(f"{BASE_URL}/paper/search", params=params, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    papers = []
    for item in data.get("data", []):
        author_names = [a.get("name", "") for a in (item.get("authors") or [])]
        pdf_url = None
        if item.get("openAccessPdf"):
            pdf_url = item["openAccessPdf"].get("url")

        papers.append({
            "paperId": item.get("paperId"),
            "title": item.get("title", "Unknown"),
            "authors": ", ".join(author_names) if author_names else None,
            "year": item.get("year"),
            "abstract": item.get("abstract"),
            "pdf_url": pdf_url,
            "citation_count": item.get("citationCount", 0),
            "arxiv_id": (item.get("externalIds") or {}).get("ArXiv"),
            "source": "semantic_scholar",
        })

    return papers


def download_pdf(url: str, timeout: int = 60) -> bytes | None:
    """Download PDF content from a URL."""
    try:
        resp = requests.get(url, timeout=timeout, headers={"User-Agent": "scimap/1.0"})
        resp.raise_for_status()
        if "pdf" in resp.headers.get("content-type", "").lower() or url.endswith(".pdf"):
            return resp.content
    except Exception:
        pass
    return None


def fetch_with_rate_limit(query: str, limit: int = 20) -> list[dict]:
    """Search with basic rate limiting for the free tier."""
    papers = []
    batch_size = 20
    offset = 0

    while len(papers) < limit:
        headers = {}
        if SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

        params = {
            "query": query,
            "limit": min(batch_size, limit - len(papers)),
            "offset": offset,
            "fields": FIELDS,
        }

        try:
            resp = requests.get(f"{BASE_URL}/paper/search", params=params, headers=headers, timeout=30)
            if resp.status_code == 429:
                time.sleep(3)
                continue
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            break

        batch = data.get("data", [])
        if not batch:
            break

        for item in batch:
            author_names = [a.get("name", "") for a in (item.get("authors") or [])]
            pdf_url = None
            if item.get("openAccessPdf"):
                pdf_url = item["openAccessPdf"].get("url")

            papers.append({
                "paperId": item.get("paperId"),
                "title": item.get("title", "Unknown"),
                "authors": ", ".join(author_names) if author_names else None,
                "year": item.get("year"),
                "abstract": item.get("abstract"),
                "pdf_url": pdf_url,
                "citation_count": item.get("citationCount", 0),
                "arxiv_id": (item.get("externalIds") or {}).get("ArXiv"),
                "source": "semantic_scholar",
            })

        offset += batch_size
        if data.get("next") is None:
            break
        time.sleep(1)  # Rate limit courtesy

    return papers[:limit]

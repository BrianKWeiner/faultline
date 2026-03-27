from __future__ import annotations

import arxiv


def search_arxiv(query: str, max_results: int = 20) -> list[dict]:
    """Search arXiv for papers and return structured results."""
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
    )

    papers = []
    for result in client.results(search):
        papers.append({
            "paperId": result.entry_id,
            "title": result.title,
            "authors": ", ".join(a.name for a in result.authors),
            "year": result.published.year if result.published else None,
            "abstract": result.summary,
            "pdf_url": result.pdf_url,
            "citation_count": None,
            "arxiv_id": result.get_short_id(),
            "source": "arxiv",
        })

    return papers


def download_arxiv_pdf(paper: dict) -> bytes | None:
    """Download PDF for an arXiv paper."""
    import requests

    pdf_url = paper.get("pdf_url")
    if not pdf_url:
        return None

    try:
        resp = requests.get(pdf_url, timeout=60, headers={"User-Agent": "scimap/1.0"})
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None

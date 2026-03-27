from __future__ import annotations

import tempfile
from pathlib import Path

from rich.console import Console
from rich.progress import Progress

from scimap.utils.pdf_reader import load_pdfs, extract_text
from scimap.utils.semantic_scholar import fetch_with_rate_limit, download_pdf
from scimap.utils.arxiv_fetcher import search_arxiv, download_arxiv_pdf

console = Console()


def ingest_papers(
    question: str | None = None,
    topic: str | None = None,
    pdf_dir: str | None = None,
    n_papers: int = 20,
) -> list[dict]:
    """Ingest papers from local PDFs or by fetching from APIs.

    Returns a list of paper dicts with keys:
        title, authors, year, text, source, full_text, abstract
    """
    if pdf_dir:
        return _ingest_local(pdf_dir)
    else:
        query = question or topic or ""
        return _ingest_remote(query, n_papers)


def _ingest_local(pdf_dir: str) -> list[dict]:
    """Load papers from a local directory of PDFs."""
    console.print(f"[bold]Loading PDFs from {pdf_dir}[/bold]")
    papers = load_pdfs(pdf_dir)
    console.print(f"  Loaded {len(papers)} papers")
    return papers


def _ingest_remote(query: str, n_papers: int) -> list[dict]:
    """Fetch papers from Semantic Scholar and arXiv."""
    console.print(f"[bold]Searching for papers: [cyan]{query}[/cyan][/bold]")

    # Search Semantic Scholar first
    console.print("  Querying Semantic Scholar...")
    ss_papers = fetch_with_rate_limit(query, limit=n_papers)
    console.print(f"  Found {len(ss_papers)} papers on Semantic Scholar")

    # If not enough, supplement with arXiv
    if len(ss_papers) < n_papers:
        shortfall = n_papers - len(ss_papers)
        console.print(f"  Querying arXiv for {shortfall} more...")
        arxiv_papers = search_arxiv(query, max_results=shortfall)

        # Deduplicate by title similarity
        existing_titles = {p["title"].lower().strip() for p in ss_papers}
        for ap in arxiv_papers:
            if ap["title"].lower().strip() not in existing_titles:
                ss_papers.append(ap)

    papers = ss_papers[:n_papers]

    # Try to download PDFs for papers that have them
    with Progress() as progress:
        task = progress.add_task("Downloading PDFs...", total=len(papers))
        for paper in papers:
            pdf_url = paper.get("pdf_url")
            if pdf_url:
                pdf_bytes = download_pdf(pdf_url)
                if pdf_bytes:
                    text = _pdf_bytes_to_text(pdf_bytes)
                    if text and len(text) > 200:
                        paper["text"] = text
                        paper["full_text"] = True
                        progress.advance(task)
                        continue

            # Fall back to abstract
            paper["text"] = paper.get("abstract", "") or ""
            paper["full_text"] = False
            progress.advance(task)

    full = sum(1 for p in papers if p.get("full_text"))
    abstract_only = len(papers) - full
    console.print(f"  [green]{full}[/green] full text, [yellow]{abstract_only}[/yellow] abstract only")

    return papers


def _pdf_bytes_to_text(pdf_bytes: bytes) -> str | None:
    """Convert raw PDF bytes to text via a temp file."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            return extract_text(tmp.name)
    except Exception:
        return None

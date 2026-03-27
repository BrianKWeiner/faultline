from __future__ import annotations

import os
import re
from pathlib import Path

import pdfplumber


def extract_text(pdf_path: str | Path) -> str:
    """Extract full text from a PDF using pdfplumber."""
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
    return "\n\n".join(pages)


def extract_metadata(text: str, filename: str) -> dict:
    """Attempt to extract title, authors, and year from first page text or filename."""
    title = None
    authors = None
    year = None

    # Try to get year from text
    year_match = re.search(r'\b(19|20)\d{2}\b', text[:2000])
    if year_match:
        year = year_match.group(0)

    # Title heuristic: first non-empty line that's long enough
    lines = [l.strip() for l in text[:3000].split('\n') if l.strip()]
    if lines:
        # Skip lines that look like headers/journal names (usually short)
        for line in lines[:5]:
            if len(line) > 15 and not re.match(r'^(doi|http|arxiv|volume|journal)', line, re.I):
                title = line
                break

    # Authors heuristic: line after title with commas or "and"
    if title and lines:
        try:
            idx = lines.index(title)
            if idx + 1 < len(lines):
                candidate = lines[idx + 1]
                if ',' in candidate or ' and ' in candidate.lower():
                    authors = candidate
        except ValueError:
            pass

    # Fallback to filename
    if not title:
        title = Path(filename).stem.replace('_', ' ').replace('-', ' ')
    if not year:
        fname_year = re.search(r'(19|20)\d{2}', filename)
        if fname_year:
            year = fname_year.group(0)

    return {"title": title, "authors": authors, "year": year}


def load_pdfs(pdf_dir: str) -> list[dict]:
    """Load all PDFs from a directory, returning structured paper dicts."""
    papers = []
    pdf_dir = Path(pdf_dir)

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            text = extract_text(pdf_file)
            if not text.strip():
                continue
            meta = extract_metadata(text, pdf_file.name)
            papers.append({
                "filename": pdf_file.name,
                "title": meta["title"],
                "authors": meta["authors"],
                "year": meta["year"],
                "text": text,
                "source": "local_pdf",
                "full_text": True,
            })
        except Exception as e:
            papers.append({
                "filename": pdf_file.name,
                "title": pdf_file.stem,
                "authors": None,
                "year": None,
                "text": "",
                "source": "local_pdf",
                "full_text": False,
                "error": str(e),
            })

    return papers

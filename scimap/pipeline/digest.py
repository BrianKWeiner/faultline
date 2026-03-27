"""Two-pass digest strategy for papers exceeding context limits."""
from __future__ import annotations

import asyncio

from scimap.pipeline.llm import call_llm


async def generate_digest(paper: dict, model: str | None = None, cache_dir: str = "output/.cache") -> dict:
    """Generate a structured ~500-word digest of a single paper."""
    text = paper.get("text", "") or paper.get("abstract", "")
    if not text:
        return {**paper, "text": "[No content available]", "digest": True}

    title = paper.get("title", "Unknown")
    authors = paper.get("authors", "Unknown")
    year = paper.get("year", "Unknown")

    prompt = f"""Produce a structured digest of the following paper in approximately 500 words.

Paper: {title}
Authors: {authors}
Year: {year}

Structure your digest as:
CLAIM: [The paper's central claim in 1-2 sentences]
METHOD: [Research methodology in 2-3 sentences]
KEY FINDINGS: [3-5 bullet points]
LIMITATIONS: [1-2 sentences on acknowledged or apparent limitations]
CONNECTIONS: [How this relates to the broader field, 1-2 sentences]

Paper text:
{text[:20000]}"""

    system = "You are a research analyst creating structured paper digests. Be precise and concise."
    digest_text = await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)

    return {**paper, "text": digest_text, "digest": True}


async def generate_digests(
    papers: list[dict],
    model: str | None = None,
    cache_dir: str = "output/.cache",
) -> list[dict]:
    """Generate digests for all papers concurrently."""
    tasks = [generate_digest(p, model=model, cache_dir=cache_dir) for p in papers]
    return await asyncio.gather(*tasks)

"""Phase 1 — Orient: Landscape Map + Knowledge Structure"""
from __future__ import annotations

import asyncio

from scimap.pipeline.llm import call_llm


def _format_papers_block(papers: list[dict]) -> str:
    """Format papers into a text block for prompt injection."""
    parts = []
    for i, p in enumerate(papers, 1):
        header = f"--- Paper {i}: {p.get('title', 'Unknown')} ---"
        meta = f"Authors: {p.get('authors', 'Unknown')} | Year: {p.get('year', 'Unknown')}"
        text = p.get("text", p.get("abstract", "")) or "[No text available]"
        parts.append(f"{header}\n{meta}\n\n{text}")
    return "\n\n".join(parts)


async def _run_paper_inventory(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 1a: Paper Inventory."""
    papers_block = _format_papers_block(papers)

    prompt = f"""I am providing {len(papers)} papers on the topic: {topic}

For each paper:
1. List it as: Author(s) + Year | Core claim in one sentence
2. Group all papers into clusters of shared assumptions
3. Flag any paper that directly contradicts another — mark with \u26a0\ufe0f

Do not summarize. Map the landscape.

PAPERS:
{papers_block}"""

    system = "You are a research analyst mapping a scientific literature landscape. Be precise and exhaustive."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def _run_knowledge_structure(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 1b: Knowledge Structure."""
    papers_block = _format_papers_block(papers)

    prompt = f"""Create a structured knowledge map of the following literature on: {topic}

Output as a clean outline with exactly this structure:
CENTRAL CLAIM: [one sentence the field orbits around]

SUPPORTING PILLARS:
- [3-5 well-established sub-claims with supporting paper refs]

CONTESTED ZONES:
- [2-3 active debates with the papers on each side]

FRONTIER QUESTIONS:
- [1-2 questions nobody has solved yet]

MUST-READ FIRST:
- Paper 1: [title] — because [one sentence reason]
- Paper 2: [title] — because [one sentence reason]
- Paper 3: [title] — because [one sentence reason]

Output as outline only. No prose.

PAPERS:
{papers_block}"""

    system = "You are a research analyst creating structured knowledge maps. Output only the requested outline format."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def run_phase1(
    papers: list[dict],
    topic: str,
    model: str | None = None,
    cache_dir: str = "output/.cache",
) -> dict:
    """Run Phase 1 (Orient) — two sub-tasks in parallel.

    Returns dict with keys: paper_inventory, knowledge_structure
    """
    inventory, structure = await asyncio.gather(
        _run_paper_inventory(papers, topic, model, cache_dir),
        _run_knowledge_structure(papers, topic, model, cache_dir),
    )

    return {
        "paper_inventory": inventory,
        "knowledge_structure": structure,
    }

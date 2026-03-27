"""Phase 3 — Synthesize: Gaps + Assumptions"""
from __future__ import annotations

import asyncio

from scimap.pipeline.llm import call_llm
from scimap.pipeline.phase1_orient import _format_papers_block


async def _run_gap_scanner(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 3a: Gap Scanner."""
    papers_block = _format_papers_block(papers)

    prompt = f"""Based on all papers on "{topic}", identify the 5 research questions that NOBODY has fully answered yet.

For each gap:
- State the unanswered question clearly
- Why does this gap exist? (too technically hard / too niche / methodologically overlooked / assumed away?)
- Which existing paper came closest to answering it, and what stopped them?
- What methodology or data would be needed to close it?

PAPERS:
{papers_block}"""

    system = "You are a research strategist identifying the most important gaps in scientific literature. Be specific and actionable."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def _run_assumption_killer(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 3b: Assumption Killer."""
    papers_block = _format_papers_block(papers)

    prompt = f"""List every assumption that the MAJORITY of these papers on "{topic}" share but never explicitly test or justify.

For each hidden assumption:
- State it clearly and precisely
- Name 1-2 papers that rely on it most heavily
- What would happen to the field's conclusions if this assumption turned out to be false?

This is how paradigm-shifting papers get written.

PAPERS:
{papers_block}"""

    system = "You are a scientific philosopher exposing hidden assumptions in research. Be incisive and precise."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def run_phase3(
    papers: list[dict],
    topic: str,
    model: str | None = None,
    cache_dir: str = "output/.cache",
) -> dict:
    """Run Phase 3 (Synthesize) — two sub-tasks in parallel.

    Returns dict with keys: gap_scan, assumption_kill
    """
    gaps, assumptions = await asyncio.gather(
        _run_gap_scanner(papers, topic, model, cache_dir),
        _run_assumption_killer(papers, topic, model, cache_dir),
    )

    return {
        "gap_scan": gaps,
        "assumption_kill": assumptions,
    }

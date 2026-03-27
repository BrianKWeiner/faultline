"""Phase 2 — Interrogate: Contradictions + Lineage + Methods"""
from __future__ import annotations

import asyncio

from scimap.pipeline.llm import call_llm
from scimap.pipeline.phase1_orient import _format_papers_block


async def _run_contradiction_finder(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 2a: Contradiction Finder."""
    papers_block = _format_papers_block(papers)

    prompt = f"""Across all papers on "{topic}", identify every point where two or more authors directly contradict each other.

For each contradiction, produce a table row with columns:
| Topic | Position A (Paper, Year) | Position B (Paper, Year) | Likely Reason for Disagreement (methodology / dataset / era / field of origin) |

Be exhaustive. If a disagreement is subtle or implicit, flag it anyway.

PAPERS:
{papers_block}"""

    system = "You are a critical research analyst focused on finding contradictions and disagreements in scientific literature. Be thorough and precise."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def _run_citation_chain(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 2b: Citation Chain (Intellectual Lineage)."""
    papers_block = _format_papers_block(papers)

    prompt = f"""Pick the 3 most-cited or most-foundational concepts across these papers on "{topic}".

For each concept:
- Who introduced it first? (paper + year)
- Who challenged it? (paper + year + how)
- Who refined or extended it? (paper + year + how)
- What is the current consensus, if any?

Display as an ASCII family tree or indented outline showing intellectual lineage.

PAPERS:
{papers_block}"""

    system = "You are a research historian tracing intellectual lineage through scientific literature. Show the evolution of ideas clearly."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def _run_methodology_audit(papers: list[dict], topic: str, model: str | None, cache_dir: str) -> str:
    """Phase 2c: Methodology Audit."""
    papers_block = _format_papers_block(papers)

    prompt = f"""Compare the research methodologies used across all papers on "{topic}".

Group papers by method type: surveys, experiments, simulations, meta-analyses, case studies, computational/ML, or other.

Then flag:
- Which methodology dominates this field and why?
- Which methodology is conspicuously underused given the questions being asked?
- Which paper's methodology is weakest relative to its claims, and why specifically?

PAPERS:
{papers_block}"""

    system = "You are a methodologist auditing research approaches. Be specific about strengths and weaknesses."
    return await call_llm(prompt, system=system, model=model, cache_dir=cache_dir)


async def run_phase2(
    papers: list[dict],
    topic: str,
    model: str | None = None,
    cache_dir: str = "output/.cache",
) -> dict:
    """Run Phase 2 (Interrogate) — three sub-tasks in parallel.

    Returns dict with keys: contradictions, citation_chain, methodology_audit
    """
    contradictions, citation_chain, methodology_audit = await asyncio.gather(
        _run_contradiction_finder(papers, topic, model, cache_dir),
        _run_citation_chain(papers, topic, model, cache_dir),
        _run_methodology_audit(papers, topic, model, cache_dir),
    )

    return {
        "contradictions": contradictions,
        "citation_chain": citation_chain,
        "methodology_audit": methodology_audit,
    }

"""Phase 4 — Distill: The 'So What'"""
from __future__ import annotations

from scimap.pipeline.llm import call_llm


async def run_phase4(
    papers: list[dict],
    topic: str,
    phase1_results: dict,
    phase2_results: dict,
    phase3_results: dict,
    model: str | None = None,
    cache_dir: str = "output/.cache",
) -> str:
    """Run Phase 4 (Distill) — single task, uses quality model by default.

    This phase receives all prior phase outputs for maximum context.
    """
    # Build a context summary from prior phases
    prior_context = f"""PRIOR ANALYSIS CONTEXT:

=== LANDSCAPE MAP ===
{phase1_results.get('paper_inventory', '')}

=== KNOWLEDGE STRUCTURE ===
{phase1_results.get('knowledge_structure', '')}

=== CONTRADICTIONS ===
{phase2_results.get('contradictions', '')}

=== INTELLECTUAL LINEAGE ===
{phase2_results.get('citation_chain', '')}

=== METHODOLOGY AUDIT ===
{phase2_results.get('methodology_audit', '')}

=== RESEARCH GAPS ===
{phase3_results.get('gap_scan', '')}

=== HIDDEN ASSUMPTIONS ===
{phase3_results.get('assumption_kill', '')}"""

    # Paper listing for reference
    paper_list = "\n".join(
        f"- {p.get('authors', 'Unknown')} ({p.get('year', '?')}): {p.get('title', 'Unknown')}"
        for p in papers
    )

    prompt = f"""You have conducted a deep analysis of {len(papers)} papers on: {topic}

{prior_context}

PAPERS ANALYZED:
{paper_list}

Now, pretend you have to explain this entire body of research to a brilliant non-expert in 5 minutes.

Give me exactly three things:
1. THE PROOF: One sentence stating what this field has actually established beyond reasonable doubt
2. THE HOLE: One honest sentence about the most important thing this field still does not know
3. THE IMPLICATION: The single real-world implication that matters most to someone outside academia

Rules: No jargon. No hedging. No academic throat-clearing. No "further research is needed."
If you cannot state each item in under 30 words, you have not understood it well enough. Try again."""

    system = "You are a master communicator distilling complex research into crystal-clear insights. Be bold, clear, and honest."

    # Use quality model by default for distillation
    use_quality = model is None
    return await call_llm(
        prompt,
        system=system,
        model=model,
        use_quality_model=use_quality,
        cache_dir=cache_dir,
    )

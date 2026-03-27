#!/usr/bin/env python3
"""scimap — Structured research pipeline powered by Claude."""
from __future__ import annotations

import asyncio
import shutil
import sys
from enum import Enum
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from scimap import config
from scimap.pipeline.ingestion import ingest_papers
from scimap.pipeline.phase1_orient import run_phase1
from scimap.pipeline.phase2_interrogate import run_phase2
from scimap.pipeline.phase3_synthesize import run_phase3
from scimap.pipeline.phase4_distill import run_phase4
from scimap.pipeline.digest import generate_digests
from scimap.pipeline.report import assemble_report, write_report
from scimap.utils.chunker import estimate_tokens, prepare_papers_for_context
from scimap.pipeline.llm import estimate_cost, set_backend, detect_backend, get_backend

app = typer.Typer(name="scimap", help="Structured research literature analysis pipeline.")
console = Console()


class ModelChoice(str, Enum):
    opus = "opus"
    sonnet = "sonnet"


class FormatChoice(str, Enum):
    markdown = "markdown"
    html = "html"
    both = "both"


class BackendChoice(str, Enum):
    auto = "auto"
    api = "api"
    claude_code = "claude-code"


def _resolve_model(choice: ModelChoice | None) -> str | None:
    """Convert CLI model choice to API model name. None means use defaults."""
    if choice is None:
        return None
    return config.MODEL_QUALITY if choice == ModelChoice.opus else config.MODEL_FAST


def _parse_phases(phases_str: str) -> set[int]:
    """Parse phase selection string like 'all' or '1,2,3'."""
    if phases_str.lower() == "all":
        return {1, 2, 3, 4}
    return {int(p.strip()) for p in phases_str.split(",") if p.strip().isdigit()}


def _estimate_total_cost(papers: list[dict], phases: set[int], model: str | None) -> float:
    """Rough cost estimate based on paper lengths and selected phases."""
    total_input_tokens = sum(estimate_tokens(p.get("text", "") or "") for p in papers)

    # Estimate: each phase sends all papers + gets ~2k tokens response
    # Phase sub-tasks: P1=2, P2=3, P3=2, P4=1
    subtask_counts = {1: 2, 2: 3, 3: 2, 4: 1}

    fast_model = model or config.MODEL_FAST
    quality_model = model or config.MODEL_QUALITY

    cost = 0.0
    est_output = 3000  # tokens per response

    for phase in phases:
        n = subtask_counts.get(phase, 0)
        m = quality_model if phase == 4 and model is None else fast_model
        cost += n * estimate_cost(total_input_tokens, est_output, m)

    return cost


def _make_status_table(phase_status: dict[str, str]) -> Table:
    """Create a rich table showing phase status."""
    table = Table(title="Pipeline Status", show_header=True)
    table.add_column("Phase", style="bold")
    table.add_column("Status")

    status_styles = {
        "pending": "[dim]pending[/dim]",
        "running": "[yellow]running...[/yellow]",
        "done": "[green]done[/green]",
        "error": "[red]error[/red]",
        "skipped": "[dim]skipped[/dim]",
    }

    for phase, status in phase_status.items():
        table.add_row(phase, status_styles.get(status, status))

    return table


def _check_backend_available(backend: str) -> bool:
    """Verify the chosen backend is actually usable."""
    if backend == "api":
        return bool(config.ANTHROPIC_API_KEY)
    if backend == "claude-code":
        return shutil.which("claude") is not None
    return False


async def _run_pipeline(
    papers: list[dict],
    topic: str,
    phases: set[int],
    model: str | None,
    output_dir: str,
    fmt: str,
    verbose: bool,
    cache_dir: str,
) -> None:
    """Core async pipeline runner."""
    phase_status = {}
    for i in range(1, 5):
        phase_status[f"Phase {i}"] = "pending" if i in phases else "skipped"

    results = {
        "phase1": None,
        "phase2": None,
        "phase3": None,
        "phase4": None,
    }
    errors = {}

    # Check if we need digest mode
    prepared_papers, needs_digest = prepare_papers_for_context(papers)
    if needs_digest:
        console.print("[yellow]Papers exceed context limit. Running digest pass first...[/yellow]")
        prepared_papers = await generate_digests(prepared_papers, model=model, cache_dir=cache_dir)
        console.print("[green]Digest pass complete.[/green]")

    # Run phases 1-3 concurrently, then phase 4
    async def run_p1():
        if 1 not in phases:
            return None
        phase_status["Phase 1"] = "running"
        try:
            result = await run_phase1(prepared_papers, topic, model=model, cache_dir=cache_dir)
            phase_status["Phase 1"] = "done"
            return result
        except Exception as e:
            phase_status["Phase 1"] = "error"
            errors["phase1"] = str(e)
            console.print(f"[red]Phase 1 error: {e}[/red]")
            return None

    async def run_p2():
        if 2 not in phases:
            return None
        phase_status["Phase 2"] = "running"
        try:
            result = await run_phase2(prepared_papers, topic, model=model, cache_dir=cache_dir)
            phase_status["Phase 2"] = "done"
            return result
        except Exception as e:
            phase_status["Phase 2"] = "error"
            errors["phase2"] = str(e)
            console.print(f"[red]Phase 2 error: {e}[/red]")
            return None

    async def run_p3():
        if 3 not in phases:
            return None
        phase_status["Phase 3"] = "running"
        try:
            result = await run_phase3(prepared_papers, topic, model=model, cache_dir=cache_dir)
            phase_status["Phase 3"] = "done"
            return result
        except Exception as e:
            phase_status["Phase 3"] = "error"
            errors["phase3"] = str(e)
            console.print(f"[red]Phase 3 error: {e}[/red]")
            return None

    # Phases 1-3 run concurrently
    console.print("\n[bold]Running phases 1-3 concurrently...[/bold]")
    p1_result, p2_result, p3_result = await asyncio.gather(run_p1(), run_p2(), run_p3())

    results["phase1"] = p1_result
    results["phase2"] = p2_result
    results["phase3"] = p3_result

    # Phase 4 runs after 1-3 complete
    if 4 in phases:
        phase_status["Phase 4"] = "running"
        console.print("\n[bold]Running phase 4 (distillation)...[/bold]")
        try:
            results["phase4"] = await run_phase4(
                prepared_papers,
                topic,
                phase1_results=results["phase1"] or {},
                phase2_results=results["phase2"] or {},
                phase3_results=results["phase3"] or {},
                model=model,
                cache_dir=cache_dir,
            )
            phase_status["Phase 4"] = "done"
        except Exception as e:
            phase_status["Phase 4"] = "error"
            errors["phase4"] = str(e)
            console.print(f"[red]Phase 4 error: {e}[/red]")

    # Print final status
    console.print()
    console.print(_make_status_table(phase_status))

    # Assemble and write report
    console.print("\n[bold]Assembling report...[/bold]")
    report_md = assemble_report(
        topic=topic,
        papers=papers,
        phase1=results["phase1"],
        phase2=results["phase2"],
        phase3=results["phase3"],
        phase4=results["phase4"],
        errors=errors,
    )

    written = write_report(report_md, topic, output_dir=output_dir, fmt=fmt)
    for path in written:
        console.print(f"[green]Report written: {path}[/green]")


@app.command()
def run(
    question: Optional[str] = typer.Option(None, "--question", "-q", help="Research question to investigate"),
    topic: Optional[str] = typer.Option(None, "--topic", "-t", help="Research topic for landscape scan"),
    pdf_dir: Optional[str] = typer.Option(None, "--pdf-dir", "-d", help="Directory of PDFs to analyze"),
    n_papers: int = typer.Option(config.DEFAULT_N_PAPERS, "--n-papers", "-n", help="Number of papers to fetch"),
    model: Optional[ModelChoice] = typer.Option(None, "--model", "-m", help="Model: opus (quality) or sonnet (fast)"),
    output_dir: str = typer.Option(config.DEFAULT_OUTPUT_DIR, "--output-dir", "-o", help="Output directory"),
    fmt: FormatChoice = typer.Option(FormatChoice.markdown, "--format", "-f", help="Output format"),
    phases: str = typer.Option("all", "--phases", "-p", help="Phases to run: all or comma-separated (1,2,3,4)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    mode: Optional[str] = typer.Option(None, "--mode", help="Run mode: landscape"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip cost confirmation"),
    backend: BackendChoice = typer.Option(
        BackendChoice.auto, "--backend", "-b",
        help="LLM backend: 'api' (Anthropic API key), 'claude-code' (Claude Code CLI), or 'auto' (detect)"
    ),
) -> None:
    """Run the scimap research analysis pipeline."""
    # Validate inputs
    if not question and not topic and not pdf_dir:
        console.print("[red]Error: Provide --question, --topic, or --pdf-dir[/red]")
        raise typer.Exit(1)

    # --- Backend resolution ---
    set_backend(backend.value)
    resolved_backend = get_backend()

    if not _check_backend_available(resolved_backend):
        if resolved_backend == "api":
            # API key missing — check if claude-code is available as fallback
            has_claude = shutil.which("claude") is not None
            if has_claude and backend == BackendChoice.auto:
                console.print("[yellow]No ANTHROPIC_API_KEY found. Detected Claude Code CLI — using it instead.[/yellow]")
                set_backend("claude-code")
                resolved_backend = "claude-code"
            elif has_claude:
                console.print("[red]ANTHROPIC_API_KEY not set.[/red]")
                console.print("  Tip: Use [bold]--backend claude-code[/bold] to run via your Claude Code subscription instead.")
                raise typer.Exit(1)
            else:
                console.print("[red]Error: ANTHROPIC_API_KEY not set and Claude Code CLI not found.[/red]")
                console.print("  Option 1: Set ANTHROPIC_API_KEY in .env or environment")
                console.print("  Option 2: Install Claude Code CLI (npm install -g @anthropic-ai/claude-code)")
                raise typer.Exit(1)
        else:
            console.print("[red]Error: Claude Code CLI ('claude') not found on PATH.[/red]")
            console.print("  Install with: npm install -g @anthropic-ai/claude-code")
            raise typer.Exit(1)

    effective_topic = question or topic or f"Papers from {pdf_dir}"
    selected_phases = _parse_phases(phases)
    resolved_model = _resolve_model(model)

    backend_label = {
        "api": "Anthropic API (direct)",
        "claude-code": "Claude Code CLI (subscription)",
    }[resolved_backend]

    console.print(Panel(
        f"[bold]scimap[/bold] — Research Pipeline\n"
        f"Query: [cyan]{effective_topic}[/cyan]\n"
        f"Phases: {', '.join(str(p) for p in sorted(selected_phases))}\n"
        f"Model: {resolved_model or 'default (sonnet phases 1-3, opus phase 4)'}\n"
        f"Backend: {backend_label}",
        title="Configuration",
    ))

    # Ingest papers
    console.print("\n[bold]Phase 0: Paper Ingestion[/bold]")
    papers = ingest_papers(
        question=question,
        topic=topic,
        pdf_dir=pdf_dir,
        n_papers=n_papers,
    )

    if not papers:
        console.print("[red]No papers found. Try a different query or provide a PDF directory.[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]{len(papers)} papers loaded.[/bold]")

    # Cost estimation (only relevant for API backend)
    est_cost = _estimate_total_cost(papers, selected_phases, resolved_model)
    if resolved_backend == "claude-code":
        console.print("Cost: included in your Claude Code subscription")
    elif est_cost > 1.00 and not yes:
        console.print(f"\n[yellow]Estimated API cost: ${est_cost:.2f}[/yellow]")
        if not typer.confirm("Continue?"):
            raise typer.Exit(0)
    else:
        console.print(f"Estimated API cost: ${est_cost:.2f}")

    # Set cache dir
    cache_dir = str(Path(output_dir) / ".cache")

    # Run pipeline
    asyncio.run(_run_pipeline(
        papers=papers,
        topic=effective_topic,
        phases=selected_phases,
        model=resolved_model,
        output_dir=output_dir,
        fmt=fmt.value,
        verbose=verbose,
        cache_dir=cache_dir,
    ))

    console.print("\n[bold green]Pipeline complete.[/bold green]")


if __name__ == "__main__":
    app()

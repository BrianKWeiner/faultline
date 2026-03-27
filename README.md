# Faultline

**AI-powered pipeline that finds research gaps, traces intellectual lineage, and critically evaluates the literature for any research area.**

Faultline (internally `scimap`) takes a research question or topic, automatically fetches relevant papers from Semantic Scholar and arXiv, and runs them through a structured four-phase analysis pipeline powered by Claude. The output is a publication-ready report that maps the landscape, finds contradictions, exposes hidden assumptions, and distills the "so what" for non-experts.

---

## Table of Contents

- [Quick Start](#quick-start)
- [What It Does](#what-it-does)
- [Installation](#installation)
- [Usage](#usage)
  - [Basic Examples](#basic-examples)
  - [CLI Reference](#cli-reference)
  - [Backends](#backends)
  - [Using Local PDFs](#using-local-pdfs)
- [Pipeline Architecture](#pipeline-architecture)
  - [Phase 0: Ingestion](#phase-0-ingestion)
  - [Phase 1: Orient](#phase-1-orient--landscape-map)
  - [Phase 2: Interrogate](#phase-2-interrogate--deep-structure)
  - [Phase 3: Synthesize](#phase-3-synthesize--gaps--assumptions)
  - [Phase 4: Distill](#phase-4-distill--the-so-what)
- [Output Formats](#output-formats)
- [Configuration](#configuration)
- [Search Tips](#search-tips)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [License](#license)

---

## Quick Start

**Prerequisites**: Python 3.11+ and either an [Anthropic API key](https://console.anthropic.com/) or [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) installed.

```bash
# 1. Clone and install
git clone https://github.com/yourusername/faultline.git
cd faultline
pip install -e .

# 2. Set your API key (or skip if using Claude Code CLI)
export ANTHROPIC_API_KEY="sk-ant-..."

# 3. Run your first analysis
scimap --topic "CRISPR off-target detection methods" --n-papers 10 -y

# 4. Open the report
ls output/   # Markdown report is here
```

That's it. The pipeline will fetch 10 papers, run all four analysis phases, and write a Markdown report to `output/`.

**Using Claude Code CLI instead of an API key:**

```bash
scimap --topic "CRISPR off-target detection methods" --backend claude-code -y
```

**Analyze your own PDFs:**

```bash
scimap --pdf-dir ~/papers/my-collection/ --topic "my research area" -y
```

---

## What It Does

Faultline is designed for researchers, graduate students, and anyone who needs to rapidly understand a body of scientific literature at a structural level — not just "what do these papers say?" but:

- **Where do authors contradict each other**, and why?
- **What assumptions does the entire field share** but never explicitly test?
- **What are the most important unanswered questions**, and what methodology would close them?
- **What is the intellectual lineage** — who introduced a concept, who challenged it, who refined it?
- **What is the "so what"** for a non-expert, in three sentences?

### Example Output (Huntington's Disease Research)

Given the topic `"somatic CAG repeat expansion Huntington disease DNA mismatch repair MSH3"`, Faultline analyzed 15 papers and produced:

- A **landscape map** clustering papers into 6 research groups with cross-group contradictions flagged
- **18 contradictions** identified across papers (e.g., Msh3 ablation prevents expansion but doesn't rescue pathology at very high CAG repeats)
- **3 intellectual lineage trees** traced as ASCII diagrams (MutSbeta as primary driver, two-step threshold model, FAN1 dual-function mechanism)
- A **methodology audit** finding that computational modeling is entirely absent despite the field's quantitative claims
- **5 open research gaps** with specific proposals for what experiments would close them
- **8 hidden assumptions** the field relies on, including the provocative observation that nobody has excluded the possibility that somatic expansion is a *consequence* rather than a *cause* of neuronal dysfunction
- A **three-sentence distillation** accessible to non-experts

---

## Installation

### From Source

```bash
git clone https://github.com/yourusername/faultline.git
cd faultline
pip install -e .
```

### Dependencies

Core dependencies (installed automatically):

| Package | Purpose |
|---------|---------|
| `anthropic` | Claude API client |
| `pdfplumber` | PDF text extraction |
| `arxiv` | arXiv paper search and download |
| `requests` | HTTP client for Semantic Scholar API |
| `typer` | CLI framework |
| `rich` | Terminal formatting and progress bars |
| `jinja2` | HTML report templating |
| `python-dotenv` | Environment variable loading from `.env` |

### Environment Setup

Create a `.env` file in the project root (optional):

```env
ANTHROPIC_API_KEY=sk-ant-...
SEMANTIC_SCHOLAR_API_KEY=...   # Optional: higher rate limits
```

Or export directly:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

If you have no API key, Faultline will automatically detect and use the Claude Code CLI if it's installed on your PATH.

---

## Usage

### Basic Examples

```bash
# Research question — most specific, best results
scimap --question "What drives somatic CAG repeat expansion in Huntington's disease neurons?" -y

# Topic scan — broader landscape mapping
scimap --topic "transformer attention mechanisms" --n-papers 15 -y

# Local PDFs — analyze your own paper collection
scimap --pdf-dir ~/Downloads/papers/ --topic "gene therapy delivery" -y

# HTML output for browser viewing
scimap --topic "LLM hallucination detection" --format both -y

# Run only specific phases
scimap --topic "quantum error correction" --phases 1,2 -y

# Use the higher-quality model for all phases
scimap --topic "protein folding" --model opus -y

# Use Claude Code CLI backend explicitly
scimap --topic "CRISPR base editing" --backend claude-code -y
```

### CLI Reference

```
scimap [OPTIONS]

Options:
  -q, --question TEXT       Research question to investigate
  -t, --topic TEXT          Research topic for landscape scan
  -d, --pdf-dir PATH        Directory of PDFs to analyze
  -n, --n-papers INTEGER    Number of papers to fetch [default: 20]
  -m, --model [opus|sonnet] Model: opus (quality) or sonnet (fast)
  -o, --output-dir PATH     Output directory [default: output]
  -f, --format [markdown|html|both]
                            Output format [default: markdown]
  -p, --phases TEXT         Phases to run: all or comma-separated (1,2,3,4)
                            [default: all]
  -v, --verbose             Verbose output
  -y, --yes                 Skip cost confirmation prompt
  -b, --backend [auto|api|claude-code]
                            LLM backend [default: auto]
  --help                    Show this message and exit
```

**Input options** (at least one required):

| Option | Use When |
|--------|----------|
| `--question` | You have a specific research question. The pipeline uses this as both the search query and the analysis focus. |
| `--topic` | You want a broad landscape scan of a research area. Works best with keyword-style queries. |
| `--pdf-dir` | You already have PDFs downloaded. Pair with `--topic` to provide analysis context. |

### Backends

Faultline supports two LLM backends:

| Backend | Flag | Requirements | Cost |
|---------|------|-------------|------|
| **Anthropic API** | `--backend api` | `ANTHROPIC_API_KEY` env var | Pay-per-token (estimated before run) |
| **Claude Code CLI** | `--backend claude-code` | `claude` on PATH | Included in Claude Code subscription |
| **Auto** (default) | `--backend auto` | Tries API first, falls back to Claude Code CLI | Depends on which is available |

The auto backend checks for an API key first. If none is found, it looks for the `claude` CLI on your PATH. If neither is available, it exits with setup instructions.

**Cost estimation**: When using the API backend, Faultline estimates the total token cost before running and asks for confirmation if it exceeds $1.00. Use `-y` to skip the prompt.

### Using Local PDFs

When using `--pdf-dir`, Faultline:

1. Scans the directory for all `.pdf` files
2. Extracts full text using `pdfplumber`
3. Parses metadata (title, authors, year) from the PDF content heuristically
4. Runs the full analysis pipeline on the extracted text

This works well for:
- Papers behind paywalls that couldn't be auto-downloaded
- Pre-prints or internal documents
- Curated reading lists

```bash
# Analyze a folder of PDFs with a topic for context
scimap --pdf-dir ~/papers/immunotherapy/ --topic "CAR-T cell therapy resistance mechanisms" -y
```

---

## Pipeline Architecture

Faultline runs a structured four-phase analysis pipeline. Phases 1-3 run **concurrently** for speed, and Phase 4 runs after them since it synthesizes their outputs.

```
                    ┌──────────────────────────┐
                    │   Phase 0: Ingestion     │
                    │  Semantic Scholar + arXiv │
                    │  or local PDF loading     │
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
              ▼                  ▼                   ▼
   ┌─────────────────┐ ┌────────────────┐ ┌──────────────────┐
   │ Phase 1: Orient │ │Phase 2: Inter- │ │Phase 3: Synthe-  │
   │                 │ │   rogate       │ │   size           │
   │ 1a. Paper       │ │ 2a. Contra-    │ │ 3a. Gap Scanner  │
   │    Inventory    │ │    dictions    │ │ 3b. Assumption   │
   │ 1b. Knowledge   │ │ 2b. Citation   │ │     Killer       │
   │    Structure    │ │    Chain       │ └──────────────────┘
   └─────────────────┘ │ 2c. Method     │           │
              │        │    Audit       │           │
              │        └────────────────┘           │
              │                  │                   │
              └──────────────────┼───────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  Phase 4: Distill        │
                    │  THE PROOF / THE HOLE /   │
                    │  THE IMPLICATION           │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │  Report Generation       │
                    │  Markdown + HTML          │
                    └──────────────────────────┘
```

### Phase 0: Ingestion

Fetches and prepares papers for analysis.

**Remote search** (`--question` or `--topic`):
1. Queries Semantic Scholar API with the search string
2. If fewer than `n_papers` found, supplements with arXiv search
3. Deduplicates papers by title across both sources
4. Attempts to download full-text PDFs for each paper with an open-access URL
5. Falls back to abstract-only when PDF download fails or yields < 200 characters of text

**Local loading** (`--pdf-dir`):
1. Scans directory for `.pdf` files
2. Extracts text with pdfplumber
3. Parses metadata (title, authors, year) heuristically from the first page

**Context management**: If the total token count of all papers exceeds the context limit (150K tokens), Faultline runs a **digest pass** — each paper is condensed to a structured ~500-word summary (CLAIM / METHOD / KEY FINDINGS / LIMITATIONS / CONNECTIONS) before being sent to the analysis phases.

### Phase 1: Orient — Landscape Map

Runs two sub-tasks concurrently:

**1a. Paper Inventory**: Lists every paper with its core claim in one sentence, groups papers into clusters of shared assumptions, and flags direct contradictions with warning markers.

**1b. Knowledge Structure**: Produces a structured outline:
- CENTRAL CLAIM: What the field orbits around
- SUPPORTING PILLARS: 3-5 established sub-claims with paper refs
- CONTESTED ZONES: 2-3 active debates with papers on each side
- FRONTIER QUESTIONS: 1-2 unsolved problems
- MUST-READ FIRST: Top 3 papers with one-sentence justifications

### Phase 2: Interrogate — Deep Structure

Runs three sub-tasks concurrently:

**2a. Contradiction Finder**: Identifies every point where two or more authors contradict each other. Outputs a table with columns: Topic | Position A | Position B | Likely Reason for Disagreement (methodology / dataset / era / field of origin).

**2b. Citation Chain**: Traces the intellectual lineage of the 3 most foundational concepts. For each: who introduced it, who challenged it, who refined it, and what the current consensus is. Displayed as ASCII family trees.

**2c. Methodology Audit**: Groups papers by method type (experiments, surveys, simulations, meta-analyses, etc.) and flags: which methodology dominates and why, which is conspicuously underused, and which paper's methodology is weakest relative to its claims.

### Phase 3: Synthesize — Gaps & Assumptions

Runs two sub-tasks concurrently:

**3a. Gap Scanner**: Identifies the 5 most important unanswered research questions. For each: the question, why the gap exists, which paper came closest, and what methodology/data would close it.

**3b. Assumption Killer**: Lists every assumption the majority of papers share but never explicitly test. For each: the assumption stated precisely, 1-2 papers that rely on it most, and what happens to the field's conclusions if it's false.

### Phase 4: Distill — The "So What"

Runs as a single task after Phases 1-3, using all prior outputs as context. Uses the higher-quality model (Opus) by default.

Produces exactly three items:
1. **THE PROOF**: One sentence stating what the field has established beyond reasonable doubt
2. **THE HOLE**: One honest sentence about the most important thing the field does not know
3. **THE IMPLICATION**: The single real-world implication that matters most to someone outside academia

Rules enforced in the prompt: no jargon, no hedging, no "further research is needed," each item under 30 words.

---

## Output Formats

### Markdown (default)

A single `.md` file with all phases, bibliography, and metadata. Works in any Markdown viewer, GitHub, or text editor.

```bash
scimap --topic "topic" --format markdown
```

### HTML

A styled HTML report with:
- Responsive layout (max-width 900px)
- Styled tables and blockquotes
- Phase 4 highlighted in a green bordered box
- Print-friendly

```bash
scimap --topic "topic" --format html
```

### Both

Writes both `.md` and `.html` files side by side.

```bash
scimap --topic "topic" --format both
```

Reports are written to the output directory (default: `output/`) with the naming pattern:

```
{sanitized_topic}_{YYYYMMDD_HHMMSS}.md
{sanitized_topic}_{YYYYMMDD_HHMMSS}.html
```

---

## Configuration

### Models

Faultline uses two model tiers:

| Tier | Model | Used For |
|------|-------|----------|
| Fast | `claude-sonnet-4-6` | Phases 1-3 (all sub-tasks) |
| Quality | `claude-opus-4-6` | Phase 4 (distillation) |

Override with `--model`:
- `--model sonnet` — use Sonnet for all phases (faster, cheaper)
- `--model opus` — use Opus for all phases (higher quality throughout)

### Token Limits

Configured in `scimap/config.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `MAX_CONTEXT_TOKENS` | 150,000 | Total token budget across all papers; triggers digest mode if exceeded |
| `CHUNK_TOKEN_LIMIT` | 4,000 | Per-paper token limit when chunking is needed |
| `DIGEST_TARGET_WORDS` | 500 | Target length for digest-mode paper summaries |

### Caching

LLM responses are cached to `{output_dir}/.cache/` as JSON files keyed by a hash of (model, system prompt, user prompt). This means:
- Re-running the same analysis is instant (cache hit)
- Changing the topic/question/papers produces fresh results (cache miss)
- Delete `.cache/` to force re-generation

---

## Search Tips

The quality of Faultline's output depends heavily on the papers it finds. Here are tips for getting the best results:

### Use `--topic` with Keywords, Not Natural Language

Semantic Scholar's search API works best with keyword-style queries:

```bash
# Good — keyword-focused, hits Semantic Scholar well
scimap --topic "somatic CAG repeat expansion Huntington disease DNA mismatch repair MSH3"

# Less effective — natural language question may miss relevant papers
scimap --question "What drives somatic CAG repeat expansion in Huntington's disease?"
```

`--question` works well when papers directly address that question in their titles/abstracts. For niche or cross-disciplinary topics, `--topic` with targeted keywords is more reliable.

### Include Key Author Names or Method Names

```bash
scimap --topic "CRISPR base editing CBE ABE Komor Gaudelli"
scimap --topic "transformer attention mechanism Vaswani self-attention"
```

### Supplement with Local PDFs

If important papers are behind paywalls or not indexed:

```bash
scimap --pdf-dir ~/papers/curated/ --topic "my specific area" -y
```

### Adjust Paper Count

- `--n-papers 5-10` for a focused analysis of a narrow question
- `--n-papers 15-20` (default) for a standard landscape scan
- `--n-papers 30+` for comprehensive coverage (will trigger digest mode for large papers)

---

## Testing

Install test dependencies:

```bash
pip install -e ".[test]"
```

Run the full test suite:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run a specific test file:

```bash
pytest tests/unit/test_chunker.py -v
```

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (sample papers, temp dirs)
├── unit/
│   ├── test_chunker.py            # Token estimation, section extraction, chunking
│   ├── test_pdf_reader.py         # PDF text extraction, metadata parsing
│   ├── test_llm.py                # Caching, backend detection, cost estimation
│   ├── test_report.py             # Report assembly, HTML rendering, file output
│   ├── test_main.py               # Phase parsing, model resolution, CLI helpers
│   ├── test_semantic_scholar.py   # Paper search, PDF download, rate limiting
│   └── test_arxiv_fetcher.py      # arXiv search and download
└── integration/
    ├── test_phases.py             # All 4 phases + digest with mocked LLM
    ├── test_ingestion.py          # Paper ingestion with mocked APIs
    └── test_cli.py                # CLI end-to-end with Typer CliRunner
```

All external API calls and LLM calls are mocked in tests. No network access or API keys required to run the test suite.

---

## Project Structure

```
faultline/
├── scimap/
│   ├── main.py                    # CLI entry point, pipeline orchestration
│   ├── config.py                  # Models, token limits, cost tables, defaults
│   ├── pipeline/
│   │   ├── llm.py                 # Dual-backend LLM calls (API + Claude Code CLI), caching
│   │   ├── ingestion.py           # Paper fetching (Semantic Scholar, arXiv, local PDF)
│   │   ├── phase1_orient.py       # Paper inventory + knowledge structure
│   │   ├── phase2_interrogate.py  # Contradictions + citation chain + method audit
│   │   ├── phase3_synthesize.py   # Gap scanner + assumption killer
│   │   ├── phase4_distill.py      # The proof / the hole / the implication
│   │   ├── digest.py              # Two-pass digest for papers exceeding context
│   │   └── report.py              # Markdown + HTML report generation
│   └── utils/
│       ├── chunker.py             # Token estimation, section extraction, context limiting
│       ├── pdf_reader.py          # PDF text extraction and metadata parsing
│       ├── semantic_scholar.py    # Semantic Scholar API client with rate limiting
│       └── arxiv_fetcher.py       # arXiv search and PDF download
├── tests/                         # 160 tests, 82% coverage
├── output/                        # Generated reports land here
├── pyproject.toml                 # Package config, dependencies, pytest settings
├── requirements.txt               # Pinned dependencies
└── LICENSE                        # MIT
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.

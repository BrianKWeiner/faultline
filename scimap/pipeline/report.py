"""Report assembly — Markdown and HTML output."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Template


def assemble_report(
    topic: str,
    papers: list[dict],
    phase1: dict | None = None,
    phase2: dict | None = None,
    phase3: dict | None = None,
    phase4: str | None = None,
    errors: dict | None = None,
) -> str:
    """Assemble all phase outputs into a Markdown report."""
    errors = errors or {}
    full_count = sum(1 for p in papers if p.get("full_text"))
    abstract_count = len(papers) - full_count
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    sections = []

    sections.append(f"""# Research Pipeline Report
**Query**: {topic}
**Papers analyzed**: {len(papers)} ({full_count} full text, {abstract_count} abstract only)
**Generated**: {timestamp}

---""")

    # Phase 1
    sections.append("## Phase 1: Landscape Map")
    if phase1:
        sections.append("### Paper Inventory")
        sections.append(phase1.get("paper_inventory", "*Phase 1a did not produce output.*"))
        sections.append("")
        sections.append("### Knowledge Structure")
        sections.append(phase1.get("knowledge_structure", "*Phase 1b did not produce output.*"))
    elif "phase1" in errors:
        sections.append(f"> **Error in Phase 1**: {errors['phase1']}")
    else:
        sections.append("*Phase 1 was not run.*")

    sections.append("\n---")

    # Phase 2
    sections.append("## Phase 2: Deep Structure")
    if phase2:
        sections.append("### Contradictions")
        sections.append(phase2.get("contradictions", "*Phase 2a did not produce output.*"))
        sections.append("")
        sections.append("### Intellectual Lineage")
        sections.append(phase2.get("citation_chain", "*Phase 2b did not produce output.*"))
        sections.append("")
        sections.append("### Methodology Audit")
        sections.append(phase2.get("methodology_audit", "*Phase 2c did not produce output.*"))
    elif "phase2" in errors:
        sections.append(f"> **Error in Phase 2**: {errors['phase2']}")
    else:
        sections.append("*Phase 2 was not run.*")

    sections.append("\n---")

    # Phase 3
    sections.append("## Phase 3: Gaps & Assumptions")
    if phase3:
        sections.append("### Open Research Questions")
        sections.append(phase3.get("gap_scan", "*Phase 3a did not produce output.*"))
        sections.append("")
        sections.append("### Hidden Assumptions")
        sections.append(phase3.get("assumption_kill", "*Phase 3b did not produce output.*"))
    elif "phase3" in errors:
        sections.append(f"> **Error in Phase 3**: {errors['phase3']}")
    else:
        sections.append("*Phase 3 was not run.*")

    sections.append("\n---")

    # Phase 4
    sections.append("## Phase 4: The Distillation")
    if phase4:
        sections.append(phase4)
    elif "phase4" in errors:
        sections.append(f"> **Error in Phase 4**: {errors['phase4']}")
    else:
        sections.append("*Phase 4 was not run.*")

    sections.append("\n---")

    # Bibliography
    sections.append("## Bibliography")
    for i, p in enumerate(papers, 1):
        authors = p.get("authors", "Unknown")
        year = p.get("year", "?")
        title = p.get("title", "Unknown")
        source = p.get("source", "")
        ft = "full text" if p.get("full_text") else "abstract only"
        sections.append(f"{i}. {authors} ({year}). *{title}*. [{source}, {ft}]")

    return "\n\n".join(sections)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SciMap Report: {{ topic }}</title>
<style>
body { font-family: 'Segoe UI', system-ui, sans-serif; max-width: 900px; margin: 0 auto; padding: 2rem; line-height: 1.6; color: #1a1a1a; }
h1 { border-bottom: 3px solid #2563eb; padding-bottom: 0.5rem; }
h2 { color: #2563eb; margin-top: 2rem; }
h3 { color: #4b5563; }
table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
th, td { border: 1px solid #d1d5db; padding: 0.5rem; text-align: left; }
th { background: #f3f4f6; }
blockquote { border-left: 4px solid #ef4444; padding-left: 1rem; color: #991b1b; background: #fef2f2; margin: 1rem 0; padding: 0.5rem 1rem; }
.phase4 { background: #f0fdf4; border: 2px solid #22c55e; border-radius: 8px; padding: 1.5rem; margin: 1rem 0; }
.meta { color: #6b7280; font-size: 0.9rem; }
pre { background: #f8fafc; padding: 1rem; border-radius: 4px; overflow-x: auto; }
hr { border: none; border-top: 1px solid #e5e7eb; margin: 2rem 0; }
</style>
</head>
<body>
{{ content }}
</body>
</html>"""


def render_html(markdown_content: str, topic: str) -> str:
    """Convert markdown report to HTML using a simple template.

    Note: This does basic conversion. For full Markdown rendering,
    a library like markdown or mistune could be used.
    """
    import re

    content = markdown_content

    # Basic markdown to HTML conversion
    # Headers
    content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', content, flags=re.MULTILINE)
    content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', content, flags=re.MULTILINE)
    content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', content, flags=re.MULTILINE)

    # Bold and italic
    content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', content)
    content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', content)

    # Blockquotes
    content = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', content, flags=re.MULTILINE)

    # Horizontal rules
    content = re.sub(r'^---$', r'<hr>', content, flags=re.MULTILINE)

    # Tables (basic: detect | delimited lines)
    lines = content.split('\n')
    in_table = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('|') and stripped.endswith('|'):
            cells = [c.strip() for c in stripped.strip('|').split('|')]
            if all(re.match(r'^[-:]+$', c) for c in cells):
                continue  # Skip separator row
            if not in_table:
                new_lines.append('<table>')
                new_lines.append('<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>')
                in_table = True
            else:
                new_lines.append('<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>')
        else:
            if in_table:
                new_lines.append('</table>')
                in_table = False
            new_lines.append(line)
    if in_table:
        new_lines.append('</table>')
    content = '\n'.join(new_lines)

    # Wrap paragraphs (lines not already wrapped in tags)
    content = re.sub(r'^(?!<[a-z])(.+)$', r'<p>\1</p>', content, flags=re.MULTILINE)

    # Wrap Phase 4 in special div
    content = content.replace(
        '<h2>Phase 4: The Distillation</h2>',
        '<h2>Phase 4: The Distillation</h2>\n<div class="phase4">'
    )
    # Close div before next hr or end
    content = re.sub(
        r'(<div class="phase4">.*?)(<hr>)',
        r'\1</div>\2',
        content,
        count=1,
        flags=re.DOTALL,
    )

    template = Template(HTML_TEMPLATE)
    return template.render(topic=topic, content=content)


def write_report(
    report_md: str,
    topic: str,
    output_dir: str = "output",
    fmt: str = "markdown",
) -> list[str]:
    """Write report to files. Returns list of written file paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Create a safe filename from topic
    safe_name = "".join(c if c.isalnum() or c in " -_" else "" for c in topic)[:60].strip().replace(" ", "_")
    if not safe_name:
        safe_name = "report"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{safe_name}_{timestamp}"

    written = []

    if fmt in ("markdown", "both"):
        md_path = output_dir / f"{base}.md"
        md_path.write_text(report_md)
        written.append(str(md_path))

    if fmt in ("html", "both"):
        html_content = render_html(report_md, topic)
        html_path = output_dir / f"{base}.html"
        html_path.write_text(html_content)
        written.append(str(html_path))

    return written

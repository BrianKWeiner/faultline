"""Tests for scimap.pipeline.report."""
from pathlib import Path

from scimap.pipeline.report import assemble_report, render_html, write_report


class TestAssembleReport:
    def test_basic_structure(self, sample_papers):
        report = assemble_report(
            topic="NLP advances",
            papers=sample_papers,
            phase1={"paper_inventory": "Inventory here", "knowledge_structure": "Structure here"},
            phase2={"contradictions": "None found", "citation_chain": "Chain here", "methodology_audit": "Audit here"},
            phase3={"gap_scan": "Gaps here", "assumption_kill": "Assumptions here"},
            phase4="The proof, the hole, the implication.",
        )
        assert "# Research Pipeline Report" in report
        assert "NLP advances" in report
        assert "Inventory here" in report
        assert "The proof, the hole, the implication." in report

    def test_includes_bibliography(self, sample_papers):
        report = assemble_report("test", sample_papers)
        assert "## Bibliography" in report
        assert "Smith, J., Doe, A." in report
        assert "2023" in report

    def test_error_messages_shown(self, sample_papers):
        report = assemble_report(
            "test",
            sample_papers,
            errors={"phase1": "API timeout", "phase2": "Rate limited"},
        )
        assert "API timeout" in report
        assert "Rate limited" in report

    def test_skipped_phases(self, sample_papers):
        report = assemble_report("test", sample_papers)
        assert "*Phase 1 was not run.*" in report
        assert "*Phase 4 was not run.*" in report

    def test_paper_count(self, sample_papers):
        report = assemble_report("test", sample_papers)
        # 2 full text, 1 abstract only
        assert "2 full text" in report
        assert "1 abstract only" in report

    def test_missing_phase_subkeys(self, sample_papers):
        # Pass a phase dict with missing expected keys
        report = assemble_report("test", sample_papers, phase1={"unexpected_key": "value"})
        assert "*Phase 1a did not produce output.*" in report


class TestRenderHtml:
    def test_produces_html(self):
        md = "# Test Report\n\n## Phase 1: Landscape Map\n\nSome content."
        html = render_html(md, "test topic")
        assert "<html" in html
        assert "test topic" in html
        assert "<h1>" in html

    def test_converts_bold_and_italic(self):
        md = "**bold text** and *italic text*"
        html = render_html(md, "test")
        assert "<strong>bold text</strong>" in html
        assert "<em>italic text</em>" in html

    def test_converts_blockquotes(self):
        md = "> This is a warning"
        html = render_html(md, "test")
        assert "<blockquote>" in html

    def test_converts_tables(self):
        md = "| Col1 | Col2 |\n| --- | --- |\n| a | b |"
        html = render_html(md, "test")
        assert "<table>" in html
        assert "<th>Col1</th>" in html
        assert "<td>a</td>" in html

    def test_phase4_special_div(self):
        md = "## Phase 4: The Distillation\n\nContent here\n\n---"
        html = render_html(md, "test")
        assert 'class="phase4"' in html


class TestWriteReport:
    def test_writes_markdown(self, tmp_path):
        files = write_report("# Report", "test topic", output_dir=str(tmp_path), fmt="markdown")
        assert len(files) == 1
        assert files[0].endswith(".md")
        assert Path(files[0]).read_text() == "# Report"

    def test_writes_html(self, tmp_path):
        files = write_report("# Report", "test topic", output_dir=str(tmp_path), fmt="html")
        assert len(files) == 1
        assert files[0].endswith(".html")

    def test_writes_both(self, tmp_path):
        files = write_report("# Report", "test topic", output_dir=str(tmp_path), fmt="both")
        assert len(files) == 2
        extensions = {Path(f).suffix for f in files}
        assert extensions == {".md", ".html"}

    def test_creates_output_dir(self, tmp_path):
        out = str(tmp_path / "new" / "dir")
        files = write_report("# Report", "topic", output_dir=out, fmt="markdown")
        assert len(files) == 1
        assert Path(files[0]).exists()

    def test_safe_filename(self, tmp_path):
        files = write_report("# R", "topic with $pecial chars!!", output_dir=str(tmp_path), fmt="markdown")
        filename = Path(files[0]).name
        assert "$" not in filename
        assert "!" not in filename

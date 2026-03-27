"""Integration tests for pipeline phases with mocked LLM calls."""
from __future__ import annotations

from unittest.mock import patch, AsyncMock

import pytest

from scimap.pipeline.phase1_orient import run_phase1, _format_papers_block
from scimap.pipeline.phase2_interrogate import run_phase2
from scimap.pipeline.phase3_synthesize import run_phase3
from scimap.pipeline.phase4_distill import run_phase4
from scimap.pipeline.digest import generate_digest, generate_digests


class TestFormatPapersBlock:
    def test_formats_papers(self, sample_papers):
        block = _format_papers_block(sample_papers)
        assert "Paper 1:" in block
        assert "Paper 2:" in block
        assert "Deep Learning" in block
        assert "Smith, J., Doe, A." in block

    def test_missing_text_uses_abstract(self):
        papers = [{"title": "Test", "authors": "A", "year": 2023, "abstract": "Abstract text"}]
        block = _format_papers_block(papers)
        assert "Abstract text" in block

    def test_no_text_shows_placeholder(self):
        papers = [{"title": "Test", "authors": "A", "year": 2023}]
        block = _format_papers_block(papers)
        assert "[No text available]" in block


class TestPhase1:
    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase1_orient.call_llm", new_callable=AsyncMock)
    async def test_run_phase1_returns_dict(self, mock_llm, sample_papers):
        mock_llm.return_value = "LLM output"
        result = await run_phase1(sample_papers, "NLP")
        assert "paper_inventory" in result
        assert "knowledge_structure" in result
        assert result["paper_inventory"] == "LLM output"

    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase1_orient.call_llm", new_callable=AsyncMock)
    async def test_calls_llm_twice(self, mock_llm, sample_papers):
        mock_llm.return_value = "output"
        await run_phase1(sample_papers, "topic")
        assert mock_llm.call_count == 2


class TestPhase2:
    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase2_interrogate.call_llm", new_callable=AsyncMock)
    async def test_run_phase2_returns_dict(self, mock_llm, sample_papers):
        mock_llm.return_value = "LLM output"
        result = await run_phase2(sample_papers, "NLP")
        assert "contradictions" in result
        assert "citation_chain" in result
        assert "methodology_audit" in result

    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase2_interrogate.call_llm", new_callable=AsyncMock)
    async def test_calls_llm_three_times(self, mock_llm, sample_papers):
        mock_llm.return_value = "output"
        await run_phase2(sample_papers, "topic")
        assert mock_llm.call_count == 3


class TestPhase3:
    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase3_synthesize.call_llm", new_callable=AsyncMock)
    async def test_run_phase3_returns_dict(self, mock_llm, sample_papers):
        mock_llm.return_value = "LLM output"
        result = await run_phase3(sample_papers, "NLP")
        assert "gap_scan" in result
        assert "assumption_kill" in result

    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase3_synthesize.call_llm", new_callable=AsyncMock)
    async def test_calls_llm_twice(self, mock_llm, sample_papers):
        mock_llm.return_value = "output"
        await run_phase3(sample_papers, "topic")
        assert mock_llm.call_count == 2


class TestPhase4:
    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase4_distill.call_llm", new_callable=AsyncMock)
    async def test_run_phase4_returns_string(self, mock_llm, sample_papers):
        mock_llm.return_value = "THE PROOF: ...\nTHE HOLE: ...\nTHE IMPLICATION: ..."
        result = await run_phase4(
            sample_papers,
            "NLP",
            phase1_results={"paper_inventory": "inv", "knowledge_structure": "struct"},
            phase2_results={"contradictions": "c", "citation_chain": "cc", "methodology_audit": "ma"},
            phase3_results={"gap_scan": "gs", "assumption_kill": "ak"},
        )
        assert isinstance(result, str)
        assert "THE PROOF" in result

    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase4_distill.call_llm", new_callable=AsyncMock)
    async def test_uses_quality_model_by_default(self, mock_llm, sample_papers):
        mock_llm.return_value = "output"
        await run_phase4(sample_papers, "t", {}, {}, {})
        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs.get("use_quality_model") is True

    @pytest.mark.asyncio
    @patch("scimap.pipeline.phase4_distill.call_llm", new_callable=AsyncMock)
    async def test_explicit_model_disables_quality(self, mock_llm, sample_papers):
        mock_llm.return_value = "output"
        await run_phase4(sample_papers, "t", {}, {}, {}, model="claude-sonnet-4-6")
        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs.get("use_quality_model") is False


class TestDigest:
    @pytest.mark.asyncio
    @patch("scimap.pipeline.digest.call_llm", new_callable=AsyncMock)
    async def test_generate_digest(self, mock_llm):
        mock_llm.return_value = "CLAIM: ...\nMETHOD: ...\nKEY FINDINGS: ..."
        paper = {"title": "Test", "authors": "A", "year": 2023, "text": "Full paper text here."}
        result = await generate_digest(paper)
        assert result["digest"] is True
        assert "CLAIM" in result["text"]

    @pytest.mark.asyncio
    async def test_generate_digest_empty_text(self):
        paper = {"title": "Test", "text": "", "abstract": ""}
        result = await generate_digest(paper)
        assert result["text"] == "[No content available]"
        assert result["digest"] is True

    @pytest.mark.asyncio
    @patch("scimap.pipeline.digest.call_llm", new_callable=AsyncMock)
    async def test_generate_digests_concurrent(self, mock_llm):
        mock_llm.return_value = "digest"
        papers = [{"title": f"Paper {i}", "text": f"Text {i}"} for i in range(3)]
        results = await generate_digests(papers)
        assert len(results) == 3
        assert mock_llm.call_count == 3

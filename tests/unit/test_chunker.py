"""Tests for scimap.utils.chunker."""
from scimap.utils.chunker import (
    estimate_tokens,
    extract_sections,
    chunk_paper,
    prepare_papers_for_context,
)


class TestEstimateTokens:
    def test_empty_string(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        # 20 chars -> 5 tokens
        assert estimate_tokens("a" * 20) == 5

    def test_realistic_text(self):
        text = "This is a sample sentence for estimation."
        tokens = estimate_tokens(text)
        assert tokens == len(text) // 4


class TestExtractSections:
    def test_no_sections_returns_full(self):
        text = "Just some plain text with no section headers."
        result = extract_sections(text)
        assert "full" in result
        assert result["full"] == text

    def test_detects_abstract(self):
        text = "Abstract\n\nThis is the abstract content.\n\nIntroduction\n\nThis is intro."
        result = extract_sections(text)
        assert "abstract" in result
        assert "introduction" in result

    def test_detects_methods_variants(self):
        text = "Abstract\n\nContent here.\n\nMethodology\n\nWe used these methods."
        result = extract_sections(text)
        assert "methods" in result

    def test_detects_conclusion_plural(self):
        text = "Abstract\n\nContent.\n\nConclusions\n\nWe conclude that..."
        result = extract_sections(text)
        assert "conclusion" in result

    def test_numbered_headers(self):
        text = "1. Abstract\n\nContent.\n\n2. Introduction\n\nMore content."
        result = extract_sections(text)
        assert "abstract" in result
        assert "introduction" in result

    def test_related_work(self):
        text = "Abstract\n\nStuff.\n\nRelated Work\n\nPrior work includes..."
        result = extract_sections(text)
        assert "related_work" in result

    def test_sections_ordered_by_position(self, long_paper_text):
        result = extract_sections(long_paper_text)
        assert "full" not in result
        keys = list(result.keys())
        assert keys[0] == "abstract"


class TestChunkPaper:
    def test_short_text_unchanged(self):
        text = "Short paper text."
        result = chunk_paper(text, token_limit=4000)
        assert result == text

    def test_long_text_without_sections_truncated(self):
        text = "x" * 100_000  # ~25k tokens, no section headers
        result = chunk_paper(text, token_limit=1000)
        assert len(result) < len(text)
        assert "[... truncated ...]" in result

    def test_long_text_with_sections_prioritized(self, long_paper_text):
        result = chunk_paper(long_paper_text, token_limit=500)
        # Should prioritize abstract, introduction, conclusion
        assert "abstract" in result.lower() or "introduction" in result.lower()
        assert len(result) < len(long_paper_text)

    def test_section_truncation_marker(self, long_paper_text):
        result = chunk_paper(long_paper_text, token_limit=300)
        # With a very tight limit, sections get truncated
        assert "[... section truncated ...]" in result or len(result) < len(long_paper_text)


class TestPreparePapersForContext:
    def test_small_papers_unchanged(self, sample_papers):
        result, used_digests = prepare_papers_for_context(sample_papers, max_total_tokens=150_000)
        assert not used_digests
        assert len(result) == len(sample_papers)

    def test_large_papers_trigger_chunking(self):
        papers = [{"text": "word " * 200_000}]  # ~250k tokens
        result, used_digests = prepare_papers_for_context(papers, max_total_tokens=1000)
        assert len(result[0]["text"]) < len(papers[0]["text"])

    def test_digest_mode_flagged_when_still_over_limit(self):
        # Even after chunking, if still over limit, digest mode is flagged
        papers = [{"text": "word " * 200_000} for _ in range(10)]
        result, used_digests = prepare_papers_for_context(papers, max_total_tokens=100)
        assert used_digests is True

    def test_empty_text_handled(self):
        papers = [{"text": ""}, {"text": None}, {}]
        result, used_digests = prepare_papers_for_context(papers, max_total_tokens=150_000)
        assert not used_digests
        assert len(result) == 3

    def test_per_paper_limit_calculated(self):
        papers = [{"text": "a" * 40_000} for _ in range(5)]
        # 40k chars = 10k tokens each = 50k total, limit is 30k
        result, used_digests = prepare_papers_for_context(papers, max_total_tokens=30_000)
        # Each paper should be chunked to ~6k tokens (30k / 5)
        for p in result:
            # Allow small overhead from truncation markers
            assert estimate_tokens(p["text"]) <= 6100

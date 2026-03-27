"""Shared fixtures for scimap tests."""
from __future__ import annotations

import pytest


@pytest.fixture
def sample_papers():
    """A small list of realistic paper dicts for testing."""
    return [
        {
            "paperId": "abc123",
            "title": "Deep Learning for Natural Language Processing",
            "authors": "Smith, J., Doe, A.",
            "year": 2023,
            "text": "Abstract\n\nThis paper explores deep learning methods for NLP tasks.\n\nIntroduction\n\nNatural language processing has seen rapid advances...\n\nMethods\n\nWe use transformer architectures...\n\nResults\n\nOur model achieves state-of-the-art...\n\nDiscussion\n\nThe results suggest that...\n\nConclusion\n\nWe have shown that deep learning improves NLP.",
            "abstract": "This paper explores deep learning methods for NLP tasks.",
            "source": "semantic_scholar",
            "full_text": True,
            "pdf_url": "https://example.com/paper1.pdf",
            "citation_count": 42,
        },
        {
            "paperId": "def456",
            "title": "Attention Mechanisms in Machine Translation",
            "authors": "Lee, B., Park, C.",
            "year": 2022,
            "text": "We present a novel attention mechanism for machine translation that outperforms existing approaches.",
            "abstract": "We present a novel attention mechanism for machine translation.",
            "source": "arxiv",
            "full_text": True,
            "pdf_url": "https://example.com/paper2.pdf",
            "citation_count": 15,
        },
        {
            "paperId": "ghi789",
            "title": "Survey of Reinforcement Learning Applications",
            "authors": "Wang, X.",
            "year": 2021,
            "text": "",
            "abstract": "A comprehensive survey of RL applications in robotics and game playing.",
            "source": "semantic_scholar",
            "full_text": False,
            "pdf_url": None,
            "citation_count": 100,
        },
    ]


@pytest.fixture
def long_paper_text():
    """A longer paper text with identifiable sections for chunker tests."""
    return (
        "Abstract\n\n"
        + "This is the abstract. " * 50
        + "\n\nIntroduction\n\n"
        + "This is the introduction section. " * 100
        + "\n\nMethods\n\n"
        + "This is the methods section with detailed methodology. " * 200
        + "\n\nResults\n\n"
        + "This is the results section with findings. " * 200
        + "\n\nDiscussion\n\n"
        + "This is the discussion of our results. " * 100
        + "\n\nConclusion\n\n"
        + "This is our conclusion. " * 50
    )


@pytest.fixture
def tmp_cache_dir(tmp_path):
    """Provide a temporary cache directory."""
    cache = tmp_path / "cache"
    cache.mkdir()
    return str(cache)

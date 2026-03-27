"""Tests for scimap.main helper functions."""
from unittest.mock import patch

import pytest

from scimap.main import _parse_phases, _resolve_model, _check_backend_available, _estimate_total_cost, ModelChoice
from scimap import config


class TestParsePhases:
    def test_all(self):
        assert _parse_phases("all") == {1, 2, 3, 4}

    def test_all_case_insensitive(self):
        assert _parse_phases("ALL") == {1, 2, 3, 4}
        assert _parse_phases("All") == {1, 2, 3, 4}

    def test_single_phase(self):
        assert _parse_phases("1") == {1}

    def test_multiple_phases(self):
        assert _parse_phases("1,3,4") == {1, 3, 4}

    def test_with_spaces(self):
        assert _parse_phases("1, 2, 3") == {1, 2, 3}

    def test_invalid_entries_ignored(self):
        assert _parse_phases("1,abc,3") == {1, 3}

    def test_empty_string(self):
        assert _parse_phases("") == set()


class TestResolveModel:
    def test_none_returns_none(self):
        assert _resolve_model(None) is None

    def test_opus(self):
        assert _resolve_model(ModelChoice.opus) == config.MODEL_QUALITY

    def test_sonnet(self):
        assert _resolve_model(ModelChoice.sonnet) == config.MODEL_FAST


class TestCheckBackendAvailable:
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_api_with_key(self):
        assert _check_backend_available("api") is True

    @patch.object(config, "ANTHROPIC_API_KEY", "")
    def test_api_without_key(self):
        assert _check_backend_available("api") is False

    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_claude_code_found(self, mock_which):
        assert _check_backend_available("claude-code") is True

    @patch("shutil.which", return_value=None)
    def test_claude_code_not_found(self, mock_which):
        assert _check_backend_available("claude-code") is False

    def test_unknown_backend(self):
        assert _check_backend_available("unknown") is False


class TestEstimateTotalCost:
    def test_all_phases(self, sample_papers):
        cost = _estimate_total_cost(sample_papers, {1, 2, 3, 4}, None)
        assert cost >= 0.0

    def test_no_phases_zero_cost(self, sample_papers):
        cost = _estimate_total_cost(sample_papers, set(), None)
        assert cost == 0.0

    @patch("scimap.pipeline.llm._backend", "api")
    @patch("scimap.pipeline.llm.ANTHROPIC_API_KEY", "sk-key")
    def test_single_phase(self, sample_papers):
        cost_one = _estimate_total_cost(sample_papers, {1}, None)
        cost_all = _estimate_total_cost(sample_papers, {1, 2, 3, 4}, None)
        assert cost_one < cost_all

    def test_with_explicit_model(self, sample_papers):
        cost = _estimate_total_cost(sample_papers, {1, 2, 3, 4}, config.MODEL_FAST)
        assert cost >= 0.0

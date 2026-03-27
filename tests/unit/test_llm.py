"""Tests for scimap.pipeline.llm."""
from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from scimap.pipeline import llm
from scimap.pipeline.llm import (
    _cache_key,
    _cache_path,
    load_cached,
    save_cache,
    _model_to_claude_code_flag,
    detect_backend,
    set_backend,
    get_backend,
    estimate_cost,
    call_llm,
    call_llm_sync,
)


class TestCacheKey:
    def test_deterministic(self):
        k1 = _cache_key("model", "sys", "prompt")
        k2 = _cache_key("model", "sys", "prompt")
        assert k1 == k2

    def test_different_inputs_different_keys(self):
        k1 = _cache_key("model", "sys", "prompt1")
        k2 = _cache_key("model", "sys", "prompt2")
        assert k1 != k2

    def test_key_length(self):
        key = _cache_key("m", "s", "p")
        assert len(key) == 16


class TestCachePath:
    def test_returns_json_path(self, tmp_path):
        path = _cache_path("abc123", str(tmp_path))
        assert path.suffix == ".json"
        assert "abc123" in path.name


class TestLoadAndSaveCache:
    def test_save_then_load(self, tmp_cache_dir):
        save_cache("model", "sys", "prompt", "response text", tmp_cache_dir)
        result = load_cached("model", "sys", "prompt", tmp_cache_dir)
        assert result == "response text"

    def test_load_missing_returns_none(self, tmp_cache_dir):
        result = load_cached("model", "sys", "nonexistent", tmp_cache_dir)
        assert result is None

    def test_load_corrupted_returns_none(self, tmp_cache_dir):
        key = _cache_key("model", "sys", "prompt")
        path = _cache_path(key, tmp_cache_dir)
        path.write_text("not json{{{")
        result = load_cached("model", "sys", "prompt", tmp_cache_dir)
        assert result is None

    def test_cache_creates_directory(self, tmp_path):
        cache_dir = str(tmp_path / "new" / "nested" / "cache")
        save_cache("m", "s", "p", "r", cache_dir)
        assert load_cached("m", "s", "p", cache_dir) == "r"


class TestModelToClaudeCodeFlag:
    def test_opus(self):
        assert _model_to_claude_code_flag("claude-opus-4-6") == "opus"

    def test_sonnet(self):
        assert _model_to_claude_code_flag("claude-sonnet-4-6") == "sonnet"

    def test_haiku(self):
        assert _model_to_claude_code_flag("claude-haiku-4-5-20251001") == "haiku"

    def test_unknown_defaults_to_sonnet(self):
        assert _model_to_claude_code_flag("some-future-model") == "sonnet"


class TestDetectBackend:
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-test-key")
    def test_api_key_present(self):
        assert detect_backend() == "api"

    @patch.object(llm, "ANTHROPIC_API_KEY", "")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_claude_code_fallback(self, mock_which):
        assert detect_backend() == "claude-code"

    @patch.object(llm, "ANTHROPIC_API_KEY", "")
    @patch("shutil.which", return_value=None)
    def test_no_backend_defaults_to_api(self, mock_which):
        assert detect_backend() == "api"


class TestSetAndGetBackend:
    def test_set_and_get(self):
        original = llm._backend
        try:
            set_backend("claude-code")
            assert get_backend() == "claude-code"
            set_backend("api")
            assert get_backend() == "api"
        finally:
            llm._backend = original

    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    def test_auto_resolves(self):
        original = llm._backend
        try:
            set_backend("auto")
            assert get_backend() == "api"
        finally:
            llm._backend = original


class TestEstimateCost:
    @patch.object(llm, "_backend", "api")
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    def test_api_cost_calculation(self):
        cost = estimate_cost(1_000_000, 1_000_000, "claude-sonnet-4-6")
        # input: 1M * 3.0/M = 3.0, output: 1M * 15.0/M = 15.0
        assert cost == pytest.approx(18.0)

    @patch.object(llm, "_backend", "claude-code")
    def test_claude_code_zero_cost(self):
        cost = estimate_cost(1_000_000, 1_000_000, "claude-sonnet-4-6")
        assert cost == 0.0

    @patch.object(llm, "_backend", "api")
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    def test_unknown_model_uses_defaults(self):
        cost = estimate_cost(1_000_000, 1_000_000, "unknown-model")
        # defaults: 3.0 input + 15.0 output = 18.0
        assert cost == pytest.approx(18.0)


class TestCallLlm:
    @pytest.mark.asyncio
    async def test_returns_cached_response(self, tmp_cache_dir):
        save_cache("claude-sonnet-4-6", "", "test prompt", "cached response", tmp_cache_dir)
        result = await call_llm("test prompt", cache_dir=tmp_cache_dir)
        assert result == "cached response"

    @pytest.mark.asyncio
    @patch("scimap.pipeline.llm._call_api")
    @patch.object(llm, "_backend", "api")
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    async def test_calls_api_backend(self, mock_api, tmp_cache_dir):
        mock_api.return_value = "api response"
        result = await call_llm("new prompt", cache_dir=tmp_cache_dir)
        assert result == "api response"
        mock_api.assert_called_once()

    @pytest.mark.asyncio
    @patch("scimap.pipeline.llm._call_claude_code")
    @patch.object(llm, "_backend", "claude-code")
    async def test_calls_claude_code_backend(self, mock_cc, tmp_cache_dir):
        mock_cc.return_value = "cc response"
        result = await call_llm("prompt", cache_dir=tmp_cache_dir)
        assert result == "cc response"

    @pytest.mark.asyncio
    @patch("scimap.pipeline.llm._call_api")
    @patch.object(llm, "_backend", "api")
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    async def test_caches_new_response(self, mock_api, tmp_cache_dir):
        mock_api.return_value = "fresh response"
        await call_llm("unique prompt", cache_dir=tmp_cache_dir)
        cached = load_cached("claude-sonnet-4-6", "", "unique prompt", tmp_cache_dir)
        assert cached == "fresh response"

    @pytest.mark.asyncio
    @patch("scimap.pipeline.llm._call_api")
    @patch.object(llm, "_backend", "api")
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    async def test_quality_model_flag(self, mock_api, tmp_cache_dir):
        mock_api.return_value = "quality response"
        await call_llm("prompt", use_quality_model=True, cache_dir=tmp_cache_dir)
        call_args = mock_api.call_args
        assert "opus" in call_args.kwargs.get("model", call_args.args[2] if len(call_args.args) > 2 else "")


class TestCallLlmSync:
    @patch("scimap.pipeline.llm._call_api_sync")
    @patch.object(llm, "_backend", "api")
    @patch.object(llm, "ANTHROPIC_API_KEY", "sk-key")
    def test_sync_calls_api(self, mock_api, tmp_cache_dir):
        mock_api.return_value = "sync response"
        result = call_llm_sync("prompt", cache_dir=tmp_cache_dir)
        assert result == "sync response"

    def test_sync_returns_cached(self, tmp_cache_dir):
        save_cache("claude-sonnet-4-6", "", "cached prompt", "cached value", tmp_cache_dir)
        result = call_llm_sync("cached prompt", cache_dir=tmp_cache_dir)
        assert result == "cached value"

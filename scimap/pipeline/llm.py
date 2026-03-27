"""Shared LLM call utilities with caching, async support, and dual backends."""
from __future__ import annotations

import asyncio
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from scimap.config import ANTHROPIC_API_KEY, MODEL_FAST, MODEL_QUALITY

# Backend setting — set by main.py before pipeline runs
_backend: str = "auto"  # "api", "claude-code", or "auto"

# Lazy-initialized clients for API backend
_async_client = None
_sync_client = None


def set_backend(backend: str) -> None:
    """Set the active backend. Called by main.py at startup."""
    global _backend
    _backend = backend


def get_backend() -> str:
    """Return the resolved backend name ('api' or 'claude-code')."""
    if _backend == "auto":
        return detect_backend()
    return _backend


def detect_backend() -> str:
    """Auto-detect the best available backend."""
    if ANTHROPIC_API_KEY:
        return "api"
    if shutil.which("claude"):
        return "claude-code"
    return "api"  # Will fail with a clear error at call time


def get_async_client():
    import anthropic
    global _async_client
    if _async_client is None:
        _async_client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
    return _async_client


def get_sync_client():
    import anthropic
    global _sync_client
    if _sync_client is None:
        _sync_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _sync_client


# ---------------------------------------------------------------------------
# Caching (shared by both backends)
# ---------------------------------------------------------------------------

def _cache_key(model: str, system: str, prompt: str) -> str:
    h = hashlib.sha256(f"{model}:{system}:{prompt}".encode()).hexdigest()[:16]
    return h


def _cache_path(key: str, cache_dir: str) -> Path:
    return Path(cache_dir) / f"{key}.json"


def load_cached(model: str, system: str, prompt: str, cache_dir: str) -> str | None:
    key = _cache_key(model, system, prompt)
    path = _cache_path(key, cache_dir)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data.get("response")
        except Exception:
            pass
    return None


def save_cache(model: str, system: str, prompt: str, response: str, cache_dir: str) -> None:
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    key = _cache_key(model, system, prompt)
    path = _cache_path(key, cache_dir)
    path.write_text(json.dumps({
        "model": model,
        "system_hash": hashlib.sha256(system.encode()).hexdigest()[:8],
        "prompt_hash": hashlib.sha256(prompt.encode()).hexdigest()[:8],
        "response": response,
    }))


# ---------------------------------------------------------------------------
# Claude Code CLI backend
# ---------------------------------------------------------------------------

def _model_to_claude_code_flag(model: str) -> str:
    """Convert an API model name to a claude CLI --model flag value."""
    if "opus" in model:
        return "opus"
    if "haiku" in model:
        return "haiku"
    return "sonnet"


async def _call_claude_code(
    prompt: str,
    system: str = "",
    model: str = MODEL_FAST,
    max_tokens: int = 8192,
) -> str:
    """Call Claude via the `claude` CLI in non-interactive mode.

    Pipes the prompt via stdin to avoid OS argument length limits.
    """
    cmd = [
        "claude",
        "-p", "-",
        "--model", _model_to_claude_code_flag(model),
        "--output-format", "text",
    ]
    if system:
        cmd.extend(["--append-system-prompt", system])

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=prompt.encode())

    if proc.returncode != 0:
        err_msg = stderr.decode().strip() if stderr else f"claude exited with code {proc.returncode}"
        raise RuntimeError(f"Claude Code CLI error: {err_msg}")

    return stdout.decode().strip()


def _call_claude_code_sync(
    prompt: str,
    system: str = "",
    model: str = MODEL_FAST,
    max_tokens: int = 8192,
) -> str:
    """Synchronous version of Claude Code CLI call.

    Pipes the prompt via stdin to avoid OS argument length limits.
    """
    cmd = [
        "claude",
        "-p", "-",
        "--model", _model_to_claude_code_flag(model),
        "--output-format", "text",
    ]
    if system:
        cmd.extend(["--append-system-prompt", system])

    result = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        err_msg = result.stderr.strip() if result.stderr else f"claude exited with code {result.returncode}"
        raise RuntimeError(f"Claude Code CLI error: {err_msg}")

    return result.stdout.strip()


# ---------------------------------------------------------------------------
# API backend
# ---------------------------------------------------------------------------

async def _call_api(
    prompt: str,
    system: str = "",
    model: str = MODEL_FAST,
    max_tokens: int = 8192,
) -> str:
    """Call the Anthropic API directly."""
    import anthropic
    client = get_async_client()

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = await client.messages.create(**kwargs)
    return response.content[0].text


def _call_api_sync(
    prompt: str,
    system: str = "",
    model: str = MODEL_FAST,
    max_tokens: int = 8192,
) -> str:
    """Synchronous API call."""
    import anthropic
    client = get_sync_client()

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        kwargs["system"] = system

    response = client.messages.create(**kwargs)
    return response.content[0].text


# ---------------------------------------------------------------------------
# Unified call interface
# ---------------------------------------------------------------------------

async def call_llm(
    prompt: str,
    system: str = "",
    model: str | None = None,
    use_quality_model: bool = False,
    cache_dir: str = "output/.cache",
    max_tokens: int = 8192,
) -> str:
    """Call the LLM using the configured backend, with caching.

    Args:
        prompt: The user message content
        system: System prompt
        model: Override model name. If None, uses quality or fast based on flag.
        use_quality_model: If True and model is None, use the quality (opus) model
        cache_dir: Directory for response cache
        max_tokens: Max output tokens
    """
    if model is None:
        model = MODEL_QUALITY if use_quality_model else MODEL_FAST

    # Check cache
    cached = load_cached(model, system, prompt, cache_dir)
    if cached is not None:
        return cached

    backend = get_backend()
    if backend == "claude-code":
        text = await _call_claude_code(prompt, system=system, model=model, max_tokens=max_tokens)
    else:
        text = await _call_api(prompt, system=system, model=model, max_tokens=max_tokens)

    # Cache the response
    save_cache(model, system, prompt, text, cache_dir)
    return text


def call_llm_sync(
    prompt: str,
    system: str = "",
    model: str | None = None,
    use_quality_model: bool = False,
    cache_dir: str = "output/.cache",
    max_tokens: int = 8192,
) -> str:
    """Synchronous LLM call using the configured backend."""
    if model is None:
        model = MODEL_QUALITY if use_quality_model else MODEL_FAST

    cached = load_cached(model, system, prompt, cache_dir)
    if cached is not None:
        return cached

    backend = get_backend()
    if backend == "claude-code":
        text = _call_claude_code_sync(prompt, system=system, model=model, max_tokens=max_tokens)
    else:
        text = _call_api_sync(prompt, system=system, model=model, max_tokens=max_tokens)

    save_cache(model, system, prompt, text, cache_dir)
    return text


def estimate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Estimate API cost in USD. Returns 0 for claude-code backend."""
    if get_backend() == "claude-code":
        return 0.0
    from scimap.config import COST_PER_M_INPUT, COST_PER_M_OUTPUT
    input_cost = (input_tokens / 1_000_000) * COST_PER_M_INPUT.get(model, 3.0)
    output_cost = (output_tokens / 1_000_000) * COST_PER_M_OUTPUT.get(model, 15.0)
    return input_cost + output_cost

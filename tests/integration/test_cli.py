"""CLI integration tests for scimap.main using Typer's CliRunner."""
from __future__ import annotations

from unittest.mock import patch, AsyncMock, MagicMock

import pytest
from typer.testing import CliRunner

from scimap.main import app
from scimap import config

runner = CliRunner()


class TestCliValidation:
    def test_requires_question_or_topic_or_pdf_dir(self):
        result = runner.invoke(app, [])
        assert result.exit_code != 0
        assert "Provide --question, --topic, or --pdf-dir" in result.output

    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_no_papers_found_exits(self, mock_gb, mock_cb, mock_ingest):
        mock_ingest.return_value = []
        result = runner.invoke(app, ["--topic", "quantum computing"])
        assert result.exit_code != 0
        assert "No papers found" in result.output


class TestBackendResolution:
    @patch.object(config, "ANTHROPIC_API_KEY", "")
    @patch("shutil.which", return_value=None)
    def test_no_backend_available(self, mock_which):
        result = runner.invoke(app, ["--topic", "test", "--backend", "api"])
        assert result.exit_code != 0
        assert "ANTHROPIC_API_KEY" in result.output

    @patch.object(config, "ANTHROPIC_API_KEY", "")
    @patch("shutil.which", return_value=None)
    def test_claude_code_not_found(self, mock_which):
        result = runner.invoke(app, ["--topic", "test", "--backend", "claude-code"])
        assert result.exit_code != 0
        assert "not found" in result.output

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch.object(config, "ANTHROPIC_API_KEY", "")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_auto_falls_back_to_claude_code(self, mock_which, mock_ingest, mock_run):
        mock_ingest.return_value = [{"title": "P", "text": "t", "full_text": True}]
        result = runner.invoke(app, ["--topic", "test", "--backend", "auto", "-y"])
        assert result.exit_code == 0
        assert "Claude Code CLI" in result.output

    @patch.object(config, "ANTHROPIC_API_KEY", "")
    @patch("shutil.which", return_value="/usr/bin/claude")
    def test_api_explicitly_requested_but_no_key_hints_claude_code(self, mock_which):
        result = runner.invoke(app, ["--topic", "test", "--backend", "api"])
        assert result.exit_code != 0
        assert "--backend claude-code" in result.output


class TestFullPipelineRun:
    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_successful_run(self, mock_gb, mock_cb, mock_ingest, mock_run):
        mock_ingest.return_value = [
            {"title": "Paper 1", "text": "content", "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, [
            "--question", "What is deep learning?",
            "--n-papers", "5",
            "--phases", "1,2",
            "-y",
        ])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output
        mock_run.assert_called_once()

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="claude-code")
    def test_claude_code_shows_subscription_cost(self, mock_gb, mock_cb, mock_ingest, mock_run):
        mock_ingest.return_value = [
            {"title": "P", "text": "t", "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, ["--topic", "test", "--backend", "claude-code", "-y"])
        assert result.exit_code == 0
        assert "subscription" in result.output

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_pdf_dir_option(self, mock_gb, mock_cb, mock_ingest, mock_run):
        mock_ingest.return_value = [
            {"title": "Local Paper", "text": "content", "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, ["--pdf-dir", "/tmp/papers", "-y"])
        assert result.exit_code == 0
        mock_ingest.assert_called_once()
        call_kwargs = mock_ingest.call_args.kwargs
        assert call_kwargs["pdf_dir"] == "/tmp/papers"

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_model_option(self, mock_gb, mock_cb, mock_ingest, mock_run):
        mock_ingest.return_value = [
            {"title": "P", "text": "t", "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, ["--topic", "test", "--model", "opus", "-y"])
        assert result.exit_code == 0
        assert "opus" in result.output.lower() or "claude-opus" in result.output.lower()

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_format_option(self, mock_gb, mock_cb, mock_ingest, mock_run):
        mock_ingest.return_value = [
            {"title": "P", "text": "t", "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, ["--topic", "test", "--format", "both", "-y"])
        assert result.exit_code == 0

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_phases_option(self, mock_gb, mock_cb, mock_ingest, mock_run):
        mock_ingest.return_value = [
            {"title": "P", "text": "t", "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, ["--topic", "test", "--phases", "1,4", "-y"])
        assert result.exit_code == 0
        assert "1, 4" in result.output


class TestCostConfirmation:
    @patch("scimap.main.asyncio.run")
    @patch("scimap.main._estimate_total_cost", return_value=5.50)
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_high_cost_prompts_confirmation(self, mock_gb, mock_cb, mock_ingest, mock_cost, mock_run):
        mock_ingest.return_value = [
            {"title": "P", "text": "t" * 100000, "full_text": True, "authors": "A", "year": 2023},
        ]
        # Respond "n" to cost confirmation
        result = runner.invoke(app, ["--topic", "test"], input="n\n")
        assert result.exit_code == 0  # typer.Exit(0) on decline

    @patch("scimap.main.asyncio.run")
    @patch("scimap.main._estimate_total_cost", return_value=5.50)
    @patch("scimap.main.ingest_papers")
    @patch("scimap.main._check_backend_available", return_value=True)
    @patch("scimap.main.get_backend", return_value="api")
    @patch.object(config, "ANTHROPIC_API_KEY", "sk-test")
    def test_yes_flag_skips_confirmation(self, mock_gb, mock_cb, mock_ingest, mock_cost, mock_run):
        mock_ingest.return_value = [
            {"title": "P", "text": "t" * 100000, "full_text": True, "authors": "A", "year": 2023},
        ]
        result = runner.invoke(app, ["--topic", "test", "-y"])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output

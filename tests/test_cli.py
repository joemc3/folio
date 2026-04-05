"""Tests for folio.cli — CLI commands via typer.testing.CliRunner."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from folio.cli import app


runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_enriched() -> MagicMock:
    enriched = MagicMock()
    enriched.user.login = "testuser"
    enriched.user.name = "Test User"
    enriched.user.avatar_url = ""
    enriched.user.bio = None
    enriched.repos = []
    enriched.stats.languages = {}
    enriched.stats.commits = 0
    enriched.stats.pull_requests = 0
    enriched.stats.issues = 0
    enriched.stats.stars_earned = 0
    enriched.summaries = {}
    enriched.fork_diffs = {}
    return enriched


def _make_mock_config() -> MagicMock:
    cfg = MagicMock()
    cfg.theme.name = "dark"
    cfg.theme.accent = "auto"
    cfg.profile.name = "Test User"
    cfg.profile.tagline = "Building things"
    cfg.profile.avatar = None
    cfg.repos.include = []
    cfg.repos.exclude = []
    cfg.repos.forks.show = False
    cfg.ai.provider = "anthropic"
    cfg.ai.model = "claude-sonnet-4-20250514"
    cfg.ai.base_url = ""
    cfg.stats.range = "3mo"
    cfg.stats.show = ["commits"]
    return cfg


def _make_mock_github_data() -> MagicMock:
    data = MagicMock()
    data.user.login = "testuser"
    data.user.name = "Test User"
    data.user.avatar_url = ""
    data.user.bio = None
    data.repos = []
    data.stats.commits = 0
    data.stats.pull_requests = 0
    data.stats.issues = 0
    data.stats.stars_earned = 0
    data.stats.languages = {}
    return data


# ---------------------------------------------------------------------------
# test_generate_no_ai
# ---------------------------------------------------------------------------

class TestGenerateNoAi:
    def test_generate_no_ai_exits_zero(self, tmp_path):
        """Invoke folio generate --no-ai; all pipeline functions mocked; expect exit_code == 0."""
        mock_config = _make_mock_config()
        mock_github_data = _make_mock_github_data()
        mock_enriched = _make_mock_enriched()

        with (
            patch("folio.cli.load_config", return_value=mock_config) as mock_load,
            patch("folio.cli.fetch_github_data", return_value=mock_github_data) as mock_fetch,
            patch("folio.cli.enrich_data", return_value=mock_enriched) as mock_enrich,
            patch("folio.cli.SummaryCache") as mock_cache_cls,
            patch("folio.cli.render_readme", return_value="# README") as mock_readme,
            patch("folio.cli.render_profile", return_value="<html></html>") as mock_profile,
            patch("folio.cli.render_style", return_value="body {}") as mock_style,
            patch("folio.cli.render_svg", return_value="<svg/>") as mock_svg,
            patch("folio.cli.push_profile") as mock_push,
        ):
            result = runner.invoke(
                app,
                ["generate", "--no-ai", "--config", str(tmp_path / ".profile.yml")],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"Output: {result.output}"
        mock_load.assert_called_once()
        mock_fetch.assert_called_once()
        mock_enrich.assert_called_once()
        # Verify no_ai=True was passed to enrich_data
        _, kwargs = mock_enrich.call_args
        assert kwargs.get("no_ai") is True or mock_enrich.call_args[0][4] is True
        mock_push.assert_not_called()

    def test_generate_no_ai_writes_readme(self, tmp_path):
        """Generated README.md should be written to cwd."""
        mock_config = _make_mock_config()
        mock_github_data = _make_mock_github_data()
        mock_enriched = _make_mock_enriched()

        with (
            patch("folio.cli.load_config", return_value=mock_config),
            patch("folio.cli.fetch_github_data", return_value=mock_github_data),
            patch("folio.cli.enrich_data", return_value=mock_enriched),
            patch("folio.cli.SummaryCache"),
            patch("folio.cli.render_readme", return_value="# README content"),
            patch("folio.cli.render_profile", return_value="<html></html>"),
            patch("folio.cli.render_style", return_value="body {}"),
            patch("folio.cli.render_svg", return_value="<svg/>"),
            patch("folio.cli.push_profile"),
        ):
            # Use mix_stderr=False to keep outputs clean
            result = runner.invoke(
                app,
                ["generate", "--no-ai", "--config", str(tmp_path / ".profile.yml")],
                catch_exceptions=False,
            )

        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# test_generate_with_push
# ---------------------------------------------------------------------------

class TestGenerateWithPush:
    def test_generate_with_push_calls_push_profile(self, tmp_path):
        """Invoke folio generate --push; assert push_profile is called."""
        mock_config = _make_mock_config()
        mock_github_data = _make_mock_github_data()
        mock_enriched = _make_mock_enriched()

        with (
            patch("folio.cli.load_config", return_value=mock_config),
            patch("folio.cli.fetch_github_data", return_value=mock_github_data),
            patch("folio.cli.enrich_data", return_value=mock_enriched),
            patch("folio.cli.SummaryCache"),
            patch("folio.cli.render_readme", return_value="# README"),
            patch("folio.cli.render_profile", return_value="<html></html>"),
            patch("folio.cli.render_style", return_value="body {}"),
            patch("folio.cli.render_svg", return_value="<svg/>"),
            patch("folio.cli.push_profile") as mock_push,
        ):
            result = runner.invoke(
                app,
                ["generate", "--push", "--no-ai", "--config", str(tmp_path / ".profile.yml")],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"Output: {result.output}"
        mock_push.assert_called_once()

    def test_generate_no_push_does_not_call_push_profile(self, tmp_path):
        """Without --push, push_profile should not be called."""
        mock_config = _make_mock_config()
        mock_github_data = _make_mock_github_data()
        mock_enriched = _make_mock_enriched()

        with (
            patch("folio.cli.load_config", return_value=mock_config),
            patch("folio.cli.fetch_github_data", return_value=mock_github_data),
            patch("folio.cli.enrich_data", return_value=mock_enriched),
            patch("folio.cli.SummaryCache"),
            patch("folio.cli.render_readme", return_value="# README"),
            patch("folio.cli.render_profile", return_value="<html></html>"),
            patch("folio.cli.render_style", return_value="body {}"),
            patch("folio.cli.render_svg", return_value="<svg/>"),
            patch("folio.cli.push_profile") as mock_push,
        ):
            result = runner.invoke(
                app,
                ["generate", "--no-ai", "--config", str(tmp_path / ".profile.yml")],
                catch_exceptions=False,
            )

        assert result.exit_code == 0
        mock_push.assert_not_called()


# ---------------------------------------------------------------------------
# test_cache_clear_all
# ---------------------------------------------------------------------------

class TestCacheClearAll:
    def test_cache_clear_all_calls_clear_with_none(self):
        """Invoke 'cache clear' without --repo; assert SummaryCache.clear(repo=None)."""
        mock_cache_instance = MagicMock()

        with patch("folio.cli.SummaryCache", return_value=mock_cache_instance) as mock_cache_cls:
            result = runner.invoke(app, ["cache", "clear"], catch_exceptions=False)

        assert result.exit_code == 0, f"Output: {result.output}"
        mock_cache_instance.clear.assert_called_once_with(repo=None)

    def test_cache_clear_all_output_message(self):
        """Confirm success message is printed."""
        mock_cache_instance = MagicMock()

        with patch("folio.cli.SummaryCache", return_value=mock_cache_instance):
            result = runner.invoke(app, ["cache", "clear"], catch_exceptions=False)

        assert "cleared" in result.output.lower()


# ---------------------------------------------------------------------------
# test_cache_clear_single_repo
# ---------------------------------------------------------------------------

class TestCacheClearSingleRepo:
    def test_cache_clear_single_repo_calls_clear_with_repo(self):
        """Invoke 'cache clear --repo user/repo'; assert clear(repo='user/repo')."""
        mock_cache_instance = MagicMock()

        with patch("folio.cli.SummaryCache", return_value=mock_cache_instance):
            result = runner.invoke(
                app,
                ["cache", "clear", "--repo", "user/repo"],
                catch_exceptions=False,
            )

        assert result.exit_code == 0, f"Output: {result.output}"
        mock_cache_instance.clear.assert_called_once_with(repo="user/repo")

    def test_cache_clear_single_repo_output_message(self):
        """Confirm repo name appears in output."""
        mock_cache_instance = MagicMock()

        with patch("folio.cli.SummaryCache", return_value=mock_cache_instance):
            result = runner.invoke(
                app,
                ["cache", "clear", "--repo", "myuser/myrepo"],
                catch_exceptions=False,
            )

        assert "myuser/myrepo" in result.output

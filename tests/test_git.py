"""Tests for folio/git.py — fork diff extraction."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from folio.git import get_fork_diff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo_with_upstream():
    """Return a mock Repo that has an 'upstream' remote."""
    repo = MagicMock()
    upstream = MagicMock()
    upstream.name = "upstream"
    repo.remotes = [upstream]
    return repo


def _make_repo_without_upstream():
    """Return a mock Repo that has no 'upstream' remote."""
    repo = MagicMock()
    origin = MagicMock()
    origin.name = "origin"
    repo.remotes = [origin]
    return repo


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetForkDiff:
    def test_returns_diff_when_upstream_exists(self):
        """Returns diff text (truncated to 3000 chars) when upstream remote is present."""
        mock_repo = _make_repo_with_upstream()
        mock_repo.git.diff.return_value = "diff --git a/foo.py b/foo.py\n+added line\n"

        with patch("folio.git.Repo", return_value=mock_repo):
            result = get_fork_diff("/fake/repo")

        assert result is not None
        assert "diff" in result
        mock_repo.git.diff.assert_called_once_with("upstream/HEAD", "HEAD")

    def test_returns_none_when_no_upstream_remote(self):
        """Returns None (with warning) when no 'upstream' remote is configured."""
        mock_repo = _make_repo_without_upstream()

        with patch("folio.git.Repo", return_value=mock_repo):
            result = get_fork_diff("/fake/repo")

        assert result is None

    def test_returns_none_on_git_command_error(self):
        """Returns None (with warning) when the git diff command raises GitCommandError."""
        from git.exc import GitCommandError

        mock_repo = _make_repo_with_upstream()
        mock_repo.git.diff.side_effect = GitCommandError("diff", 128)

        with patch("folio.git.Repo", return_value=mock_repo):
            result = get_fork_diff("/fake/repo")

        assert result is None

    def test_returns_none_when_not_a_git_repo(self):
        """Returns None (with warning) when the path is not a git repository."""
        from git.exc import InvalidGitRepositoryError

        with patch("folio.git.Repo", side_effect=InvalidGitRepositoryError("/fake/repo")):
            result = get_fork_diff("/fake/repo")

        assert result is None

    def test_diff_truncated_to_3000_chars(self):
        """Diff output is truncated to 3000 characters."""
        mock_repo = _make_repo_with_upstream()
        mock_repo.git.diff.return_value = "x" * 10_000

        with patch("folio.git.Repo", return_value=mock_repo):
            result = get_fork_diff("/fake/repo")

        assert result is not None
        assert len(result) <= 3000

    def test_lockfile_hunks_stripped(self):
        """Hunks for lockfiles (e.g. package-lock.json) are removed from the diff."""
        lockfile_hunk = (
            "diff --git a/package-lock.json b/package-lock.json\n"
            "--- a/package-lock.json\n"
            "+++ b/package-lock.json\n"
            "@@ -1,3 +1,3 @@\n"
            " {\n"
            '-  "version": "1.0.0"\n'
            '+  "version": "1.0.1"\n'
            " }\n"
        )
        real_hunk = (
            "diff --git a/main.py b/main.py\n"
            "--- a/main.py\n"
            "+++ b/main.py\n"
            "@@ -1,2 +1,3 @@\n"
            " def foo():\n"
            "+    pass\n"
        )
        mock_repo = _make_repo_with_upstream()
        mock_repo.git.diff.return_value = lockfile_hunk + real_hunk

        with patch("folio.git.Repo", return_value=mock_repo):
            result = get_fork_diff("/fake/repo")

        assert result is not None
        assert "package-lock.json" not in result
        assert "main.py" in result

"""Tests for folio/github.py — auth chain, data types, and fetch logic."""

from __future__ import annotations

import os
import subprocess
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from folio.github import (
    GitHubData,
    RepoData,
    StatsData,
    UserProfile,
    fetch_github_data,
    get_github_token,
)


# ---------------------------------------------------------------------------
# Helpers / shared fixtures
# ---------------------------------------------------------------------------

def _make_config(
    include=None,
    exclude=None,
    stats_range="3mo",
    show_forks=True,
):
    """Return a minimal config-like object for tests."""
    cfg = MagicMock()
    cfg.repos.include = include  # list[dict] or None
    cfg.repos.exclude = exclude or []
    cfg.repos.forks.show = show_forks
    cfg.stats.range = stats_range
    cfg.stats.show = ["commits", "pull_requests", "issues", "streak", "top_languages", "stars_earned"]
    return cfg


# ---------------------------------------------------------------------------
# Auth chain tests
# ---------------------------------------------------------------------------

class TestGetGithubToken:
    def test_returns_gh_cli_token_when_available(self):
        """gh CLI is tried first; if it succeeds the token is returned."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="ghp_faketoken123\n"
            )
            token = get_github_token()
        assert token == "ghp_faketoken123"
        mock_run.assert_called_once()

    def test_falls_back_to_env_var_when_gh_cli_fails(self):
        """When gh CLI fails, GITHUB_TOKEN env var is used."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_xyz"}):
                token = get_github_token()
        assert token == "env_token_xyz"

    def test_falls_back_to_env_var_when_gh_cli_raises(self):
        """When gh CLI raises FileNotFoundError (not installed), env var is used."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch.dict(os.environ, {"GITHUB_TOKEN": "env_token_xyz"}):
                token = get_github_token()
        assert token == "env_token_xyz"

    def test_raises_runtime_error_when_no_token_available(self):
        """RuntimeError raised when gh CLI fails and GITHUB_TOKEN is not set."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="")
            env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(RuntimeError, match="No GitHub token"):
                    get_github_token()

    def test_raises_runtime_error_when_gh_cli_raises_and_no_env(self):
        """RuntimeError raised when gh CLI raises and GITHUB_TOKEN is absent."""
        with patch("subprocess.run", side_effect=FileNotFoundError):
            env = {k: v for k, v in os.environ.items() if k != "GITHUB_TOKEN"}
            with patch.dict(os.environ, env, clear=True):
                with pytest.raises(RuntimeError, match="No GitHub token"):
                    get_github_token()


# ---------------------------------------------------------------------------
# Data type constructability tests
# ---------------------------------------------------------------------------

class TestDataTypes:
    def test_user_profile_constructable(self):
        up = UserProfile(
            login="jdoe",
            name="Jane Doe",
            avatar_url="https://example.com/avatar.png",
            bio="Engineer",
            followers=100,
            following=50,
        )
        assert up.login == "jdoe"
        assert up.bio == "Engineer"

    def test_user_profile_optional_bio(self):
        up = UserProfile(
            login="jdoe",
            name="Jane Doe",
            avatar_url="https://example.com/avatar.png",
            bio=None,
            followers=0,
            following=0,
        )
        assert up.bio is None

    def test_repo_data_constructable_minimal(self):
        rd = RepoData(
            name="my-repo",
            full_name="jdoe/my-repo",
            description=None,
            language="Python",
            stars=42,
            last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
            is_fork=False,
            is_private=False,
            fork_parent=None,
            private_reason=None,
            html_url="https://github.com/jdoe/my-repo",
        )
        assert rd.readme_text == ""
        assert rd.recent_commits == []

    def test_repo_data_with_all_fields(self):
        rd = RepoData(
            name="my-repo",
            full_name="jdoe/my-repo",
            description="A project",
            language="Python",
            stars=10,
            last_updated=datetime(2024, 6, 1, tzinfo=timezone.utc),
            is_fork=True,
            is_private=False,
            fork_parent="upstream/my-repo",
            private_reason=None,
            html_url="https://github.com/jdoe/my-repo",
            readme_text="Hello world",
            recent_commits=["fix: bug", "feat: thing"],
        )
        assert rd.fork_parent == "upstream/my-repo"
        assert len(rd.recent_commits) == 2

    def test_stats_data_defaults(self):
        sd = StatsData()
        assert sd.commits == 0
        assert sd.pull_requests == 0
        assert sd.issues == 0
        assert sd.streak_days == 0
        assert sd.stars_earned == 0
        assert sd.languages == {}

    def test_stats_data_with_values(self):
        sd = StatsData(
            commits=100,
            pull_requests=20,
            issues=5,
            streak_days=30,
            stars_earned=500,
            languages={"Python": 0.75, "JavaScript": 0.25},
        )
        assert sd.commits == 100
        assert sd.languages["Python"] == 0.75

    def test_github_data_constructable(self):
        up = UserProfile(
            login="jdoe", name="Jane", avatar_url="", bio=None, followers=0, following=0
        )
        gd = GitHubData(user=up, repos=[], stats=StatsData())
        assert gd.user.login == "jdoe"
        assert gd.repos == []


# ---------------------------------------------------------------------------
# fetch_github_data tests (mocked PyGitHub)
# ---------------------------------------------------------------------------

def _make_mock_repo(
    name="public-project",
    full_name=None,
    description="A repo",
    language="Python",
    stargazers_count=10,
    pushed_at=None,
    fork=False,
    private=False,
    parent=None,
    readme_content="README content here",
):
    """Build a mock PyGitHub Repository object."""
    repo = MagicMock()
    repo.name = name
    repo.full_name = full_name or f"jdoe/{name}"
    repo.description = description
    repo.language = language
    repo.stargazers_count = stargazers_count
    repo.pushed_at = pushed_at or datetime(2024, 3, 1, tzinfo=timezone.utc)
    repo.fork = fork
    repo.private = private
    repo.html_url = f"https://github.com/jdoe/{name}"
    repo.parent = parent

    # get_readme mock
    mock_readme = MagicMock()
    mock_readme.decoded_content = readme_content.encode()
    repo.get_readme.return_value = mock_readme

    # get_commits mock — returns list of commit mocks
    def _make_commit(msg):
        c = MagicMock()
        c.commit.message = msg
        return c

    mock_commits = MagicMock()
    mock_commits.__iter__ = MagicMock(
        return_value=iter([_make_commit("feat: add thing"), _make_commit("fix: bug")])
    )
    repo.get_commits.return_value = mock_commits

    return repo


def _make_mock_github(repos, login="jdoe", name="Jane Doe"):
    """Build a mock Github() client."""
    mock_user = MagicMock()
    mock_user.login = login
    mock_user.name = name
    mock_user.avatar_url = "https://example.com/avatar.png"
    mock_user.bio = "Engineer"
    mock_user.followers = 42
    mock_user.following = 10

    # get_repos returns all repos
    mock_user.get_repos.return_value = repos

    mock_gh = MagicMock()
    mock_gh.get_user.return_value = mock_user

    # search_commits / search_issues
    mock_result = MagicMock()
    mock_result.totalCount = 5
    mock_gh.search_commits.return_value = mock_result
    mock_gh.search_issues.return_value = mock_result

    return mock_gh


class TestFetchGithubData:
    def test_returns_github_data_object(self):
        """fetch_github_data returns a GitHubData instance."""
        repos = [_make_mock_repo()]
        mock_gh = _make_mock_github(repos)
        config = _make_config()

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert isinstance(result, GitHubData)
        assert isinstance(result.user, UserProfile)
        assert isinstance(result.stats, StatsData)

    def test_include_list_filters_repos(self):
        """When include list is set, only those repos are returned."""
        repo_a = _make_mock_repo(name="public-project")
        repo_b = _make_mock_repo(name="private-project")
        repo_c = _make_mock_repo(name="other-project")
        all_repos = [repo_a, repo_b, repo_c]

        include = [
            {"name": "public-project"},
            {"name": "private-project", "private_reason": "Under NDA"},
        ]
        config = _make_config(include=include)

        mock_gh = _make_mock_github(all_repos)

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        names = [r.name for r in result.repos]
        assert "public-project" in names
        assert "private-project" in names
        assert "other-project" not in names

    def test_exclude_list_removes_repos(self):
        """Repos in exclude list are not returned."""
        repo_a = _make_mock_repo(name="keep-me")
        repo_b = _make_mock_repo(name="old-project")
        all_repos = [repo_a, repo_b]

        config = _make_config(exclude=["old-project"])

        mock_gh = _make_mock_github(all_repos)

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        names = [r.name for r in result.repos]
        assert "keep-me" in names
        assert "old-project" not in names

    def test_private_reason_from_include_list(self):
        """private_reason from include config entry is attached to the RepoData."""
        repo = _make_mock_repo(name="private-project", private=True)
        config = _make_config(
            include=[{"name": "private-project", "private_reason": "Under NDA"}]
        )
        mock_gh = _make_mock_github([repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert len(result.repos) == 1
        assert result.repos[0].private_reason == "Under NDA"

    def test_private_repo_without_reason_gets_default(self):
        """Private repos without an explicit private_reason get the default message."""
        repo = _make_mock_repo(name="private-project", private=True)
        # Include the repo but don't specify private_reason
        config = _make_config(
            include=[{"name": "private-project"}]
        )
        mock_gh = _make_mock_github([repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert len(result.repos) == 1
        assert result.repos[0].private_reason == "Private repository"

    def test_public_repo_without_private_reason_is_none(self):
        """Public repos that are not private have private_reason=None."""
        repo = _make_mock_repo(name="public-project", private=False)
        config = _make_config(include=[{"name": "public-project"}])
        mock_gh = _make_mock_github([repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert result.repos[0].private_reason is None

    def test_fork_parent_attached(self):
        """Fork repos have fork_parent set to parent.full_name."""
        parent = MagicMock()
        parent.full_name = "upstream/public-project"
        repo = _make_mock_repo(name="public-project", fork=True, parent=parent)
        config = _make_config(include=[{"name": "public-project"}])
        mock_gh = _make_mock_github([repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert result.repos[0].fork_parent == "upstream/public-project"

    def test_readme_truncated_to_2000_chars(self):
        """README text is truncated to 2000 characters."""
        long_readme = "x" * 5000
        repo = _make_mock_repo(name="public-project", readme_content=long_readme)
        config = _make_config(include=[{"name": "public-project"}])
        mock_gh = _make_mock_github([repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert len(result.repos[0].readme_text) <= 2000

    def test_readme_fetch_failure_handled_gracefully(self):
        """When get_readme raises (no README), readme_text is empty string."""
        from github import GithubException
        repo = _make_mock_repo(name="public-project")
        repo.get_readme.side_effect = GithubException(404, "Not Found", None)
        config = _make_config(include=[{"name": "public-project"}])
        mock_gh = _make_mock_github([repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert result.repos[0].readme_text == ""

    def test_no_include_list_fetches_public_repos(self):
        """When include is None, all public repos from get_repos are used."""
        public_repo = _make_mock_repo(name="my-public", private=False)
        config = _make_config(include=None)
        mock_gh = _make_mock_github([public_repo])

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        assert any(r.name == "my-public" for r in result.repos)

    def test_stats_populated(self):
        """StatsData fields are populated from search results."""
        repos = [_make_mock_repo()]
        mock_gh = _make_mock_github(repos)
        config = _make_config()

        with patch("folio.github.get_github_token", return_value="fake_token"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)

        # search_commits and search_issues both return totalCount=5
        assert isinstance(result.stats.commits, int)
        assert isinstance(result.stats.pull_requests, int)
        assert isinstance(result.stats.issues, int)

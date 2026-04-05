"""GitHub data types, authentication, and API fetching for Folio."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from github import Github, GithubException


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class UserProfile:
    login: str
    name: str
    avatar_url: str
    bio: str | None
    followers: int
    following: int


@dataclass
class RepoData:
    name: str
    full_name: str
    description: str | None
    language: str | None
    stars: int
    last_updated: datetime
    is_fork: bool
    is_private: bool
    fork_parent: str | None
    private_reason: str | None
    html_url: str
    readme_text: str = ""
    recent_commits: list[str] = field(default_factory=list)


@dataclass
class StatsData:
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    streak_days: int = 0
    stars_earned: int = 0
    languages: dict[str, float] = field(default_factory=dict)


@dataclass
class GitHubData:
    user: UserProfile
    repos: list[RepoData]
    stats: StatsData


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

_NOISE_PREFIXES = (
    "Merge pull request",
    "Merge branch",
    "Merge remote-tracking",
    "chore(deps)",
    "bump version",
    "auto-generated",
    "automated",
)


def get_github_token() -> str:
    """Return a GitHub personal access token.

    Resolution order:
    1. ``gh auth token`` subprocess (gh CLI)
    2. ``GITHUB_TOKEN`` environment variable
    3. Raise ``RuntimeError``
    """
    # Try gh CLI
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            token = result.stdout.strip()
            if token:
                return token
    except (FileNotFoundError, OSError):
        pass

    # Fall back to environment variable
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        return token

    raise RuntimeError(
        "No GitHub token found. Run `gh auth login` or set the GITHUB_TOKEN "
        "environment variable."
    )


# ---------------------------------------------------------------------------
# Date range helper
# ---------------------------------------------------------------------------

_RANGE_MAP = {
    "1mo": timedelta(days=30),
    "3mo": timedelta(days=91),
    "1yr": timedelta(days=365),
    "alltime": None,
}


def _compute_since(stats_range: str) -> datetime | None:
    """Convert a range string (1mo/3mo/1yr/alltime) to a UTC datetime cutoff."""
    delta = _RANGE_MAP.get(stats_range)
    if delta is None:
        return None
    return datetime.now(tz=timezone.utc) - delta


# ---------------------------------------------------------------------------
# Repo fetching helpers
# ---------------------------------------------------------------------------

_NOISE_PREFIXES = (
    "Merge pull request",
    "Merge branch",
    "Merge remote-tracking",
    "chore(deps)",
    "Bump ",
    "bump version",
    "Auto-generated",
    "automated",
)


def _is_noisy_commit(message: str) -> bool:
    first_line = message.split("\n", 1)[0]
    return any(first_line.startswith(prefix) for prefix in _NOISE_PREFIXES)


def _fetch_readme(repo: Any) -> str:
    """Return up to 2000 chars of the repo README, or empty string on failure."""
    try:
        readme = repo.get_readme()
        text = readme.decoded_content.decode("utf-8", errors="replace")
        return text[:2000]
    except GithubException:
        return ""
    except Exception:
        return ""


def _fetch_recent_commits(repo: Any, since: datetime | None) -> list[str]:
    """Return last 10 non-noisy commit messages."""
    try:
        kwargs: dict[str, Any] = {}
        if since is not None:
            kwargs["since"] = since
        commits = repo.get_commits(**kwargs)
        messages: list[str] = []
        for commit in commits:
            if len(messages) >= 10:
                break
            msg = commit.commit.message.split("\n", 1)[0]
            if not _is_noisy_commit(msg):
                messages.append(msg)
        return messages
    except GithubException:
        return []
    except Exception:
        return []


def _build_repo_data(
    repo: Any,
    private_reason: str | None,
) -> RepoData:
    """Convert a PyGitHub Repository to a RepoData instance."""
    fork_parent: str | None = None
    if repo.fork and repo.parent is not None:
        fork_parent = repo.parent.full_name

    # Determine private_reason
    effective_private_reason = private_reason
    if repo.private and effective_private_reason is None:
        effective_private_reason = "Private repository"

    readme_text = _fetch_readme(repo)
    recent_commits = _fetch_recent_commits(repo, since=None)

    return RepoData(
        name=repo.name,
        full_name=repo.full_name,
        description=repo.description,
        language=repo.language,
        stars=repo.stargazers_count,
        last_updated=repo.pushed_at,
        is_fork=repo.fork,
        is_private=repo.private,
        fork_parent=fork_parent,
        private_reason=effective_private_reason,
        html_url=repo.html_url,
        readme_text=readme_text,
        recent_commits=recent_commits,
    )


# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------

def _fetch_stats(gh: Any, login: str, since: datetime | None, repos: list[RepoData]) -> StatsData:
    """Aggregate stats from the GitHub search API and repo data."""
    since_qualifier = ""
    if since is not None:
        since_qualifier = f" committer-date:>={since.strftime('%Y-%m-%d')}"

    # Commits authored by user
    try:
        commit_results = gh.search_commits(
            query=f"author:{login}{since_qualifier}"
        )
        commits = commit_results.totalCount
    except Exception:
        commits = 0

    # Pull requests
    since_pr_qualifier = ""
    if since is not None:
        since_pr_qualifier = f" created:>={since.strftime('%Y-%m-%d')}"
    try:
        pr_results = gh.search_issues(
            query=f"type:pr author:{login}{since_pr_qualifier}"
        )
        pull_requests = pr_results.totalCount
    except Exception:
        pull_requests = 0

    # Issues
    try:
        issue_results = gh.search_issues(
            query=f"type:issue author:{login}{since_pr_qualifier}"
        )
        issues = issue_results.totalCount
    except Exception:
        issues = 0

    # Stars earned (sum from fetched repos)
    stars_earned = sum(r.stars for r in repos)

    # Languages aggregated (by occurrence, then normalized)
    lang_counts: dict[str, int] = {}
    for repo in repos:
        if repo.language:
            lang_counts[repo.language] = lang_counts.get(repo.language, 0) + 1
    total = sum(lang_counts.values()) or 1
    languages = {lang: count / total for lang, count in lang_counts.items()}

    return StatsData(
        commits=commits,
        pull_requests=pull_requests,
        issues=issues,
        streak_days=0,  # streak requires event timeline — deferred
        stars_earned=stars_earned,
        languages=languages,
    )


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def fetch_github_data(config: Any) -> GitHubData:
    """Fetch GitHub data for the authenticated user and return a GitHubData instance.

    Args:
        config: A config object (folio.config.FolioConfig or compatible mock)
                with .repos.include, .repos.exclude, .repos.forks.show,
                .stats.range attributes.

    Returns:
        GitHubData populated with user profile, repo list, and aggregate stats.
    """
    token = get_github_token()
    gh = Github(token)
    user = gh.get_user()

    profile = UserProfile(
        login=user.login,
        name=user.name or "",
        avatar_url=user.avatar_url or "",
        bio=user.bio,
        followers=user.followers,
        following=user.following,
    )

    since = _compute_since(getattr(config.stats, "range", "3mo"))

    # Build lookup: repo name → private_reason from include list
    include_list = config.repos.include  # list[dict] or None
    exclude_set: set[str] = set(config.repos.exclude or [])

    include_map: dict[str, str | None] | None = None
    if include_list is not None:
        include_map = {}
        for entry in include_list:
            # entry may be a dict or a MagicMock-like object with .name / .get()
            if isinstance(entry, dict):
                repo_name = entry["name"]
                reason = entry.get("private_reason")
            else:
                # Attribute-style access (e.g. pydantic models)
                repo_name = entry.name
                reason = getattr(entry, "private_reason", None)
            include_map[repo_name] = reason

    # Fetch repos
    all_repos = user.get_repos()
    repo_data_list: list[RepoData] = []

    for repo in all_repos:
        # Apply include filter
        if include_map is not None:
            if repo.name not in include_map:
                continue
        else:
            # Default: only public repos
            if repo.private:
                continue

        # Apply exclude filter
        if repo.name in exclude_set:
            continue

        private_reason: str | None = None
        if include_map is not None:
            private_reason = include_map.get(repo.name)

        rd = _build_repo_data(repo, private_reason=private_reason)
        repo_data_list.append(rd)

    stats = _fetch_stats(gh, profile.login, since, repo_data_list)

    return GitHubData(user=profile, repos=repo_data_list, stats=stats)

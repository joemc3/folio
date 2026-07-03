"""GitHub data types, authentication, and API fetching for Folio."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
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
    email: str | None = None


@dataclass
class SiteLink:
    label: str
    url: str


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
    homepage: str | None = None
    link: SiteLink | None = None


@dataclass
class StatsData:
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    streak_days: int = 0
    stars_earned: int = 0
    languages: dict[str, float] = field(default_factory=dict)
    contribution_weeks: list = field(default_factory=list)   # list[list[ContribDay]]
    contribution_total: int = 0


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
    config_link: SiteLink | None = None,
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

    homepage = getattr(repo, "homepage", None) or None
    if config_link is not None:
        link = config_link
    elif homepage:
        link = SiteLink(label="View site", url=homepage)
    else:
        link = None

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
        homepage=homepage,
        link=link,
    )


# ---------------------------------------------------------------------------
# Stats helper
# ---------------------------------------------------------------------------

def _fetch_stats(gh: Any, login: str, since: datetime | None, repos: list[RepoData], language_count: int = 6) -> StatsData:
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
    sorted_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)
    top_langs = sorted_langs[:language_count]
    languages = {lang: round(count / total * 100, 1) for lang, count in top_langs}

    return StatsData(
        commits=commits,
        pull_requests=pull_requests,
        issues=issues,
        streak_days=0,  # streak requires event timeline — deferred
        stars_earned=stars_earned,
        languages=languages,
    )


# ---------------------------------------------------------------------------
# Contribution calendar helpers (pure, no network)
# ---------------------------------------------------------------------------


@dataclass
class ContribDay:
    count: int
    level: int


def _contribution_level(count: int, max_count: int) -> int:
    """Map a day's contribution count to a 0–4 intensity level."""
    if count <= 0 or max_count <= 0:
        return 0
    frac = count / max_count
    if frac <= 0.25:
        return 1
    if frac <= 0.5:
        return 2
    if frac <= 0.75:
        return 3
    return 4


def _parse_contribution_calendar(payload: dict) -> tuple[list[list[ContribDay]], int]:
    """Turn a GitHub GraphQL contributionCalendar payload into weeks + total.

    Raises KeyError/TypeError on a malformed payload — callers wrap in try/except.
    """
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = int(cal["totalContributions"])
    raw_weeks = cal["weeks"]
    counts = [int(d["contributionCount"]) for w in raw_weeks for d in w["contributionDays"]]
    max_count = max(counts) if counts else 0
    weeks: list[list[ContribDay]] = []
    for w in raw_weeks:
        days = [
            ContribDay(count=int(d["contributionCount"]),
                       level=_contribution_level(int(d["contributionCount"]), max_count))
            for d in w["contributionDays"]
        ]
        weeks.append(days)
    return weeks, total


def _compute_streak(weeks: list[list[ContribDay]]) -> int:
    """Current consecutive days with contributions, counting back from today.

    A trailing zero (today, not yet done) does not break the streak.
    """
    days = [d for w in weeks for d in w]
    if not days:
        return 0
    start = len(days) - 1
    if days[start].count == 0:
        start -= 1
    streak = 0
    for i in range(start, -1, -1):
        if days[i].count > 0:
            streak += 1
        else:
            break
    return streak


# ---------------------------------------------------------------------------
# Contribution calendar fetch (network, best-effort)
# ---------------------------------------------------------------------------

_ACTIVITY_DAYS = {"3mo": 90, "6mo": 182, "1yr": 365}

_CONTRIB_QUERY = (
    "query($login:String!,$from:DateTime!,$to:DateTime!){"
    "user(login:$login){contributionsCollection(from:$from,to:$to){"
    "contributionCalendar{totalContributions "
    "weeks{contributionDays{contributionCount date weekday}}}}}}"
)


def _fetch_contribution_calendar(
    token: str, login: str, activity_range: str
) -> tuple[list[list[ContribDay]], int]:
    """Best-effort GitHub GraphQL contribution calendar. Empty on any failure."""
    days = _ACTIVITY_DAYS.get(activity_range, 90)
    to_dt = datetime.now(tz=timezone.utc)
    from_dt = to_dt - timedelta(days=days)
    try:
        resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": _CONTRIB_QUERY, "variables": {
                "login": login, "from": from_dt.isoformat(), "to": to_dt.isoformat()}},
            headers={"Authorization": f"bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return _parse_contribution_calendar(resp.json())
    except Exception:
        return [], 0


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
        email=getattr(user, "email", None) or None,
    )

    since = _compute_since(getattr(config.stats, "range", "3mo"))

    # Build lookup: repo name → private_reason from include list
    include_list = config.repos.include  # list[dict] or None
    exclude_set: set[str] = set(config.repos.exclude or [])

    def _entry_link(entry) -> SiteLink | None:
        # dict entry
        if isinstance(entry, dict):
            raw = entry.get("link")
            if isinstance(raw, dict) and raw.get("label") and raw.get("url"):
                return SiteLink(label=raw["label"], url=raw["url"])
            return None
        # pydantic RepoEntry (or attr-style)
        raw = getattr(entry, "link", None)
        if raw is not None and getattr(raw, "label", None) and getattr(raw, "url", None):
            return SiteLink(label=raw.label, url=raw.url)
        return None

    include_map: dict[str, tuple[str | None, SiteLink | None]] | None = None
    if include_list is not None:
        include_map = {}
        for entry in include_list:
            if isinstance(entry, dict):
                repo_name = entry["name"]
                reason = entry.get("private_reason")
            else:
                repo_name = entry.name
                reason = getattr(entry, "private_reason", None)
            include_map[repo_name] = (reason, _entry_link(entry))

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

        private_reason = None
        config_link: SiteLink | None = None
        if include_map is not None:
            private_reason, config_link = include_map.get(repo.name, (None, None))

        rd = _build_repo_data(repo, private_reason=private_reason, config_link=config_link)
        repo_data_list.append(rd)

    stats = _fetch_stats(gh, profile.login, since, repo_data_list, config.stats.language_count)

    activity_range = getattr(config.stats, "activity_range", "3mo")
    if not isinstance(activity_range, str):
        activity_range = "3mo"
    weeks, total = _fetch_contribution_calendar(token, profile.login, activity_range)
    stats.contribution_weeks = weeks
    stats.contribution_total = total
    stats.streak_days = _compute_streak(weeks)

    return GitHubData(user=profile, repos=repo_data_list, stats=stats)

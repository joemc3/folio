"""AI summarization with LiteLLM, disk-backed caching, and enrichment pipeline."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import litellm

from folio.github import GitHubData, RepoData, StatsData, UserProfile


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

REPO_SUMMARY_PROMPT = """You are writing a two-sentence project description for a card on a developer's
profile page. The reader is scanning, not studying.

Sentence 1: What the project does, stated plainly.
Sentence 2: What makes it interesting — a technical choice, a hard problem it
solves, or who it's for.

Be concrete. Use specifics from the README and commit history, not generic
phrases. Write the way a thoughtful engineer would describe a colleague's work.
Avoid marketing language, buzzwords, and filler.

Repository: {name}
Description: {description}
README (excerpt): {readme_excerpt}
Recent commit messages: {commit_messages}"""

FORK_DIFF_PROMPT = """A developer forked "{upstream_name}" and made modifications. Write 1-2 sentences
describing what they changed, written in first person ("I added...", "I fixed...").

Be specific — name the features, files, or fixes visible in the diff. If the
changes are minor (typo fixes, config tweaks), say so honestly. Do not inflate
small contributions.

Upstream project: {upstream_description}
Diff summary: {diff_text}"""


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

DEFAULT_CACHE_PATH = Path.home() / ".folio" / "cache.json"


class SummaryCache:
    """Disk-backed JSON cache keyed by repo full name and head SHA."""

    def __init__(self, path: Path = DEFAULT_CACHE_PATH) -> None:
        self._path = path
        self._data: dict[str, dict[str, str]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(self._data, indent=2), encoding="utf-8"
        )

    def get(self, repo_full_name: str, head_sha: str) -> str | None:
        """Return cached summary if repo exists and SHA matches, else None."""
        entry = self._data.get(repo_full_name)
        if entry is None:
            return None
        if entry.get("sha") != head_sha:
            return None
        return entry.get("summary")

    def set(self, repo_full_name: str, head_sha: str, summary: str) -> None:
        """Store summary for the given repo and SHA."""
        self._data[repo_full_name] = {"sha": head_sha, "summary": summary}
        self._save()

    def clear(self, repo: str | None = None) -> None:
        """Clear all entries or a single repo's entry."""
        if repo is None:
            self._data = {}
        else:
            self._data.pop(repo, None)
        self._save()


# ---------------------------------------------------------------------------
# Model string helpers
# ---------------------------------------------------------------------------

def _build_model_string(provider: str, model: str) -> str:
    """Build the litellm model string from provider and model name."""
    if provider == "ollama":
        return f"ollama/{model}"
    if provider == "openrouter":
        return f"openrouter/{model}"
    return model


# ---------------------------------------------------------------------------
# Summarization functions
# ---------------------------------------------------------------------------

def summarize_repo(
    repo: RepoData,
    provider: str,
    model: str,
    base_url: str = "",
) -> str:
    """Generate a two-sentence summary for a repository using the AI provider.

    Returns stripped content string, or "" on any failure.
    """
    commit_messages = "\n".join(repo.recent_commits) if repo.recent_commits else "(none)"
    prompt = REPO_SUMMARY_PROMPT.format(
        name=repo.name,
        description=repo.description or "(no description)",
        readme_excerpt=repo.readme_text or "(no README)",
        commit_messages=commit_messages,
    )

    model_str = _build_model_string(provider, model)
    kwargs: dict[str, Any] = {
        "model": model_str,
        "messages": [{"role": "user", "content": prompt}],
    }
    if base_url:
        kwargs["api_base"] = base_url

    try:
        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception:
        return ""


def summarize_fork_diff(
    upstream_name: str,
    upstream_description: str,
    diff_text: str,
    provider: str,
    model: str,
    base_url: str = "",
) -> str:
    """Generate a 1-2 sentence description of fork modifications.

    Returns stripped content string, or "" on any failure.
    """
    prompt = FORK_DIFF_PROMPT.format(
        upstream_name=upstream_name,
        upstream_description=upstream_description or "(no description)",
        diff_text=diff_text,
    )

    model_str = _build_model_string(provider, model)
    kwargs: dict[str, Any] = {
        "model": model_str,
        "messages": [{"role": "user", "content": prompt}],
    }
    if base_url:
        kwargs["api_base"] = base_url

    try:
        response = litellm.completion(**kwargs)
        content = response.choices[0].message.content
        return content.strip() if content else ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Enriched data type
# ---------------------------------------------------------------------------

@dataclass
class EnrichedData:
    """GitHub data augmented with AI-generated summaries and fork diffs."""

    user: UserProfile
    repos: list[RepoData]
    stats: StatsData
    summaries: dict[str, str] = field(default_factory=dict)
    fork_diffs: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Cache key helper
# ---------------------------------------------------------------------------

def _cache_key_for_repo(repo: RepoData) -> str:
    """Return a stable SHA-like key for a repo based on its last updated time."""
    # Use a combination of the last_updated timestamp and recent commits
    # as a proxy for "head SHA" when we don't have actual commit SHAs.
    parts = [repo.full_name, str(repo.last_updated)]
    if repo.recent_commits:
        parts.append(repo.recent_commits[0])
    return "|".join(parts)


# ---------------------------------------------------------------------------
# Enrichment pipeline
# ---------------------------------------------------------------------------

def enrich_data(
    github_data: GitHubData,
    config: Any,
    fork_diff_texts: dict[str, str],
    cache: SummaryCache | None = None,
    no_ai: bool = False,
) -> EnrichedData:
    """Enrich GitHub data with AI summaries and fork diff descriptions.

    Args:
        github_data: Raw GitHub data (user, repos, stats).
        config: Config object with .ai.provider, .ai.model, .ai.base_url.
        fork_diff_texts: Mapping of repo full_name -> diff text for forks.
        cache: Optional SummaryCache for memoizing results across runs.
        no_ai: If True, skip all AI calls and return empty summaries/diffs.

    Returns:
        EnrichedData with summaries and fork_diffs populated (or empty if no_ai).
    """
    if no_ai:
        return EnrichedData(
            user=github_data.user,
            repos=github_data.repos,
            stats=github_data.stats,
            summaries={},
            fork_diffs={},
        )

    provider = config.ai.provider
    model = config.ai.model
    base_url = getattr(config.ai, "base_url", "")

    summaries: dict[str, str] = {}
    fork_diffs: dict[str, str] = {}

    for repo in github_data.repos:
        head_sha = _cache_key_for_repo(repo)

        # Check cache first
        if cache is not None:
            cached = cache.get(repo.full_name, head_sha)
            if cached is not None:
                summaries[repo.full_name] = cached
                continue

        # Call AI
        summary = summarize_repo(repo, provider=provider, model=model, base_url=base_url)
        summaries[repo.full_name] = summary

        # Store in cache
        if cache is not None and summary:
            cache.set(repo.full_name, head_sha, summary)

    for repo in github_data.repos:
        if not repo.is_fork:
            continue
        diff_text = fork_diff_texts.get(repo.full_name)
        if not diff_text:
            continue

        upstream_name = repo.fork_parent or ""
        upstream_description = ""  # Not directly available; use empty string

        diff_summary = summarize_fork_diff(
            upstream_name=upstream_name,
            upstream_description=upstream_description,
            diff_text=diff_text,
            provider=provider,
            model=model,
            base_url=base_url,
        )
        fork_diffs[repo.full_name] = diff_summary

    return EnrichedData(
        user=github_data.user,
        repos=github_data.repos,
        stats=github_data.stats,
        summaries=summaries,
        fork_diffs=fork_diffs,
    )

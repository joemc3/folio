"""Tests for folio/summarize.py — AI summarization and caching."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from folio.github import GitHubData, RepoData, StatsData, UserProfile
from folio.summarize import (
    FORK_DIFF_PROMPT,
    REPO_SUMMARY_PROMPT,
    EnrichedData,
    SummaryCache,
    enrich_data,
    summarize_fork_diff,
    summarize_repo,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_repo(
    name="my-project",
    full_name="jdoe/my-project",
    description="A cool project",
    readme_text="This is the readme.",
    recent_commits=None,
    is_fork=False,
    fork_parent=None,
):
    return RepoData(
        name=name,
        full_name=full_name,
        description=description,
        language="Python",
        stars=10,
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        is_fork=is_fork,
        is_private=False,
        fork_parent=fork_parent,
        private_reason=None,
        html_url=f"https://github.com/{full_name}",
        readme_text=readme_text,
        recent_commits=recent_commits or ["feat: add feature", "fix: bug"],
    )


def _make_github_data(repos=None):
    user = UserProfile(
        login="jdoe",
        name="Jane Doe",
        avatar_url="",
        bio=None,
        followers=0,
        following=0,
    )
    return GitHubData(
        user=user,
        repos=repos or [_make_repo()],
        stats=StatsData(),
    )


def _make_config(provider="ollama", model="llama3", base_url="http://localhost:11434"):
    cfg = MagicMock()
    cfg.ai.provider = provider
    cfg.ai.model = model
    cfg.ai.base_url = base_url
    return cfg


def _make_litellm_response(content="Generated summary text."):
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = content
    return mock_resp


# ---------------------------------------------------------------------------
# 1. Prompt construction includes repo name and description
# ---------------------------------------------------------------------------

class TestPromptConstruction:
    def test_repo_summary_prompt_contains_name(self):
        prompt = REPO_SUMMARY_PROMPT.format(
            name="my-project",
            description="A cool project",
            readme_excerpt="Short readme",
            commit_messages="feat: add feature",
        )
        assert "my-project" in prompt

    def test_repo_summary_prompt_contains_description(self):
        prompt = REPO_SUMMARY_PROMPT.format(
            name="my-project",
            description="A cool project",
            readme_excerpt="Short readme",
            commit_messages="feat: add feature",
        )
        assert "A cool project" in prompt

    def test_repo_summary_prompt_contains_readme(self):
        prompt = REPO_SUMMARY_PROMPT.format(
            name="my-project",
            description="A cool project",
            readme_excerpt="Short readme",
            commit_messages="feat: add feature",
        )
        assert "Short readme" in prompt

    def test_repo_summary_prompt_contains_commits(self):
        prompt = REPO_SUMMARY_PROMPT.format(
            name="my-project",
            description="A cool project",
            readme_excerpt="Short readme",
            commit_messages="feat: add feature",
        )
        assert "feat: add feature" in prompt


# ---------------------------------------------------------------------------
# 2. Fork diff prompt includes upstream name and diff text
# ---------------------------------------------------------------------------

class TestForkDiffPrompt:
    def test_fork_diff_prompt_contains_upstream_name(self):
        prompt = FORK_DIFF_PROMPT.format(
            upstream_name="upstream/cool-tool",
            upstream_description="A useful CLI tool",
            diff_text="Added --verbose flag",
        )
        assert "upstream/cool-tool" in prompt

    def test_fork_diff_prompt_contains_diff_text(self):
        prompt = FORK_DIFF_PROMPT.format(
            upstream_name="upstream/cool-tool",
            upstream_description="A useful CLI tool",
            diff_text="Added --verbose flag",
        )
        assert "Added --verbose flag" in prompt

    def test_fork_diff_prompt_contains_upstream_description(self):
        prompt = FORK_DIFF_PROMPT.format(
            upstream_name="upstream/cool-tool",
            upstream_description="A useful CLI tool",
            diff_text="Added --verbose flag",
        )
        assert "A useful CLI tool" in prompt


# ---------------------------------------------------------------------------
# 3. Cache miss returns None
# ---------------------------------------------------------------------------

class TestCacheMiss:
    def test_cache_miss_returns_none(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        result = cache.get("jdoe/my-project", "abc123")
        assert result is None

    def test_cache_miss_for_unknown_repo(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/repo-a", "sha1", "Some summary")
        result = cache.get("jdoe/repo-b", "sha1")
        assert result is None


# ---------------------------------------------------------------------------
# 4. Cache hit returns summary
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_cache_hit_returns_summary(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/my-project", "abc123", "This is a summary.")
        result = cache.get("jdoe/my-project", "abc123")
        assert result == "This is a summary."


# ---------------------------------------------------------------------------
# 5. Cache invalidated by SHA change
# ---------------------------------------------------------------------------

class TestCacheInvalidation:
    def test_cache_invalidated_on_sha_change(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/my-project", "old-sha", "Old summary.")
        result = cache.get("jdoe/my-project", "new-sha")
        assert result is None

    def test_new_sha_overwrites_old(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/my-project", "sha1", "Summary v1.")
        cache.set("jdoe/my-project", "sha2", "Summary v2.")
        assert cache.get("jdoe/my-project", "sha2") == "Summary v2."
        assert cache.get("jdoe/my-project", "sha1") is None


# ---------------------------------------------------------------------------
# 6. Cache persists to disk
# ---------------------------------------------------------------------------

class TestCachePersistence:
    def test_cache_persists_to_disk(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        cache = SummaryCache(path=cache_path)
        cache.set("jdoe/my-project", "abc123", "Persisted summary.")

        assert cache_path.exists()
        data = json.loads(cache_path.read_text())
        assert "jdoe/my-project" in data

    def test_cache_reloads_from_disk(self, tmp_path):
        cache_path = tmp_path / "cache.json"

        cache1 = SummaryCache(path=cache_path)
        cache1.set("jdoe/my-project", "abc123", "Persisted summary.")

        cache2 = SummaryCache(path=cache_path)
        result = cache2.get("jdoe/my-project", "abc123")
        assert result == "Persisted summary."

    def test_cache_creates_parent_dirs(self, tmp_path):
        cache_path = tmp_path / "nested" / "dirs" / "cache.json"
        cache = SummaryCache(path=cache_path)
        cache.set("jdoe/my-project", "abc123", "Some summary.")
        assert cache_path.exists()


# ---------------------------------------------------------------------------
# 7. Cache clear all
# ---------------------------------------------------------------------------

class TestCacheClearAll:
    def test_clear_all_removes_all_entries(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/repo-a", "sha1", "Summary A.")
        cache.set("jdoe/repo-b", "sha2", "Summary B.")
        cache.clear()
        assert cache.get("jdoe/repo-a", "sha1") is None
        assert cache.get("jdoe/repo-b", "sha2") is None

    def test_clear_all_persists_empty_state(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        cache = SummaryCache(path=cache_path)
        cache.set("jdoe/repo-a", "sha1", "Summary A.")
        cache.clear()
        cache2 = SummaryCache(path=cache_path)
        assert cache2.get("jdoe/repo-a", "sha1") is None


# ---------------------------------------------------------------------------
# 8. Cache clear single repo
# ---------------------------------------------------------------------------

class TestCacheClearSingleRepo:
    def test_clear_single_repo(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/repo-a", "sha1", "Summary A.")
        cache.set("jdoe/repo-b", "sha2", "Summary B.")
        cache.clear("jdoe/repo-a")
        assert cache.get("jdoe/repo-a", "sha1") is None
        assert cache.get("jdoe/repo-b", "sha2") == "Summary B."

    def test_clear_nonexistent_repo_is_no_op(self, tmp_path):
        cache = SummaryCache(path=tmp_path / "cache.json")
        cache.set("jdoe/repo-a", "sha1", "Summary A.")
        cache.clear("jdoe/nonexistent")
        assert cache.get("jdoe/repo-a", "sha1") == "Summary A."


# ---------------------------------------------------------------------------
# 9. summarize_repo calls litellm and returns content
# ---------------------------------------------------------------------------

class TestSummarizeRepo:
    def test_summarize_repo_returns_content(self):
        repo = _make_repo()
        mock_resp = _make_litellm_response("A concise project summary.")

        with patch("litellm.completion", return_value=mock_resp) as mock_litellm:
            result = summarize_repo(repo, provider="ollama", model="llama3")

        assert result == "A concise project summary."
        mock_litellm.assert_called_once()

    def test_summarize_repo_uses_ollama_model_prefix(self):
        repo = _make_repo()
        mock_resp = _make_litellm_response("Summary text.")

        with patch("litellm.completion", return_value=mock_resp) as mock_litellm:
            summarize_repo(repo, provider="ollama", model="llama3")

        call_kwargs = mock_litellm.call_args
        model_arg = call_kwargs[1].get("model") or call_kwargs[0][0]
        assert model_arg == "ollama/llama3"

    def test_summarize_repo_uses_openrouter_model_prefix(self):
        repo = _make_repo()
        mock_resp = _make_litellm_response("Summary text.")

        with patch("litellm.completion", return_value=mock_resp) as mock_litellm:
            summarize_repo(repo, provider="openrouter", model="mistralai/mistral-7b-instruct")

        call_kwargs = mock_litellm.call_args
        model_arg = call_kwargs[1].get("model") or call_kwargs[0][0]
        assert model_arg == "openrouter/mistralai/mistral-7b-instruct"

    def test_summarize_repo_other_provider_uses_model_as_is(self):
        repo = _make_repo()
        mock_resp = _make_litellm_response("Summary text.")

        with patch("litellm.completion", return_value=mock_resp) as mock_litellm:
            summarize_repo(repo, provider="anthropic", model="claude-3-haiku-20240307")

        call_kwargs = mock_litellm.call_args
        model_arg = call_kwargs[1].get("model") or call_kwargs[0][0]
        assert model_arg == "claude-3-haiku-20240307"

    def test_summarize_repo_strips_whitespace(self):
        repo = _make_repo()
        mock_resp = _make_litellm_response("  Summary with whitespace.  \n")

        with patch("litellm.completion", return_value=mock_resp):
            result = summarize_repo(repo, provider="ollama", model="llama3")

        assert result == "Summary with whitespace."


# ---------------------------------------------------------------------------
# 10. summarize_repo returns "" on failure
# ---------------------------------------------------------------------------

class TestSummarizeRepoFailure:
    def test_summarize_repo_returns_empty_on_exception(self):
        repo = _make_repo()

        with patch("litellm.completion", side_effect=Exception("Connection refused")):
            result = summarize_repo(repo, provider="ollama", model="llama3")

        assert result == ""

    def test_summarize_fork_diff_returns_empty_on_exception(self):
        with patch("litellm.completion", side_effect=Exception("Timeout")):
            result = summarize_fork_diff(
                upstream_name="upstream/tool",
                upstream_description="A tool",
                diff_text="Added flag",
                provider="ollama",
                model="llama3",
            )

        assert result == ""

    def test_summarize_fork_diff_returns_content_on_success(self):
        mock_resp = _make_litellm_response("I added a --verbose flag to the CLI.")

        with patch("litellm.completion", return_value=mock_resp):
            result = summarize_fork_diff(
                upstream_name="upstream/tool",
                upstream_description="A tool",
                diff_text="Added --verbose flag",
                provider="ollama",
                model="llama3",
            )

        assert result == "I added a --verbose flag to the CLI."


# ---------------------------------------------------------------------------
# EnrichedData dataclass
# ---------------------------------------------------------------------------

class TestEnrichedData:
    def test_enriched_data_constructable(self):
        github_data = _make_github_data()
        ed = EnrichedData(
            user=github_data.user,
            repos=github_data.repos,
            stats=github_data.stats,
            summaries={"jdoe/my-project": "A summary."},
            fork_diffs={},
        )
        assert ed.user.login == "jdoe"
        assert ed.summaries["jdoe/my-project"] == "A summary."
        assert ed.fork_diffs == {}


# ---------------------------------------------------------------------------
# enrich_data
# ---------------------------------------------------------------------------

class TestEnrichData:
    def test_no_ai_returns_empty_summaries(self):
        github_data = _make_github_data()
        config = _make_config()
        result = enrich_data(github_data, config, fork_diff_texts={}, no_ai=True)
        assert isinstance(result, EnrichedData)
        assert result.summaries == {}
        assert result.fork_diffs == {}

    def test_no_ai_preserves_repos_and_stats(self):
        repo = _make_repo()
        github_data = _make_github_data(repos=[repo])
        config = _make_config()
        result = enrich_data(github_data, config, fork_diff_texts={}, no_ai=True)
        assert result.repos == github_data.repos
        assert result.stats == github_data.stats
        assert result.user == github_data.user

    def test_enrich_data_calls_summarize_repo(self):
        repo = _make_repo(name="my-project", full_name="jdoe/my-project")
        github_data = _make_github_data(repos=[repo])
        config = _make_config()
        mock_resp = _make_litellm_response("AI summary.")

        with patch("litellm.completion", return_value=mock_resp):
            result = enrich_data(github_data, config, fork_diff_texts={})

        assert "jdoe/my-project" in result.summaries
        assert result.summaries["jdoe/my-project"] == "AI summary."

    def test_enrich_data_uses_cache_on_hit(self, tmp_path):
        repo = _make_repo(name="my-project", full_name="jdoe/my-project")
        github_data = _make_github_data(repos=[repo])
        config = _make_config()

        cache = SummaryCache(path=tmp_path / "cache.json")
        # Pre-populate cache; head_sha is derived from repo full_name (use a known approach)
        # We'll just check that if cache has entry for the repo with some sha,
        # and litellm is not called if cache hits.
        # Since enrich_data uses cache.get/set internally, let's test it end-to-end.

        with patch("litellm.completion", return_value=_make_litellm_response("Cached summary.")) as mock_litellm:
            result1 = enrich_data(github_data, config, fork_diff_texts={}, cache=cache)

        call_count_first = mock_litellm.call_count

        # Second call with same data and same cache — should not call litellm again
        with patch("litellm.completion", return_value=_make_litellm_response("New summary.")) as mock_litellm2:
            result2 = enrich_data(github_data, config, fork_diff_texts={}, cache=cache)

        assert mock_litellm2.call_count == 0
        assert result2.summaries["jdoe/my-project"] == result1.summaries["jdoe/my-project"]

    def test_enrich_data_calls_fork_diff(self):
        repo = _make_repo(
            name="forked",
            full_name="jdoe/forked",
            is_fork=True,
            fork_parent="upstream/original",
            description="Forked project",
        )
        github_data = _make_github_data(repos=[repo])
        config = _make_config()
        fork_diff_texts = {"jdoe/forked": "Added a new flag to CLI."}

        def mock_completion(**kwargs):
            msg = kwargs["messages"][0]["content"]
            if "upstream/original" in msg:
                return _make_litellm_response("I added a new flag.")
            return _make_litellm_response("Repo summary.")

        with patch("litellm.completion", side_effect=mock_completion):
            result = enrich_data(github_data, config, fork_diff_texts=fork_diff_texts)

        assert "jdoe/forked" in result.fork_diffs
        assert result.fork_diffs["jdoe/forked"] == "I added a new flag."

"""Tests for folio.render — Jinja2 rendering engine."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

from folio.config import ProfileConfig, ProfileSection, ThemeSection, StatsSection
from folio.github import RepoData, SiteLink, StatsData, UserProfile
from folio.summarize import EnrichedData


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> UserProfile:
    return UserProfile(
        login="testdev",
        name="Test Developer",
        avatar_url="https://avatars.githubusercontent.com/u/12345",
        bio="Open source enthusiast",
        followers=42,
        following=10,
    )


def _make_public_repo() -> RepoData:
    return RepoData(
        name="public-project",
        full_name="testdev/public-project",
        description="A public open-source tool",
        language="Python",
        stars=10,
        last_updated=datetime(2024, 1, 1, tzinfo=timezone.utc),
        is_fork=False,
        is_private=False,
        fork_parent=None,
        private_reason=None,
        html_url="https://github.com/testdev/public-project",
        readme_text="# Public Project\nA nice tool.",
        recent_commits=["Initial commit", "Add feature X"],
        homepage="https://public-project.example",
        link=SiteLink(label="View site", url="https://public-project.example"),
    )


def _make_private_repo() -> RepoData:
    return RepoData(
        name="secret-tool",
        full_name="testdev/secret-tool",
        description="Confidential project",
        language="Go",
        stars=0,
        last_updated=datetime(2024, 2, 1, tzinfo=timezone.utc),
        is_fork=False,
        is_private=True,
        fork_parent=None,
        private_reason="Under NDA",
        html_url="https://github.com/testdev/secret-tool",
    )


def _make_fork_repo() -> RepoData:
    return RepoData(
        name="forked-lib",
        full_name="testdev/forked-lib",
        description="Fork of a popular library",
        language="TypeScript",
        stars=0,
        last_updated=datetime(2024, 3, 1, tzinfo=timezone.utc),
        is_fork=True,
        is_private=False,
        fork_parent="upstream/forked-lib",
        private_reason=None,
        html_url="https://github.com/testdev/forked-lib",
    )


def _make_stats() -> StatsData:
    from folio.github import ContribDay

    return StatsData(
        commits=150,
        pull_requests=25,
        issues=10,
        streak_days=7,
        stars_earned=100,
        languages={"Python": 0.6, "Go": 0.3, "TypeScript": 0.1},
        contribution_weeks=[[ContribDay(count=(i % 5), level=(i % 5)) for i in range(7)]],
        contribution_total=42,
    )


def _make_config() -> ProfileConfig:
    raw = {
        "profile": {
            "name": "Test Developer",
            "tagline": "Building cool things",
            "location": "Austin, TX",
            "avatar": None,
            "social": {},
        },
        "ai": {
            "provider": "anthropic",
            "model": "claude-sonnet-4-6",
        },
        "theme": {
            "name": "dark",
            "accent": None,
        },
        "stats": {
            "range": "3mo",
            "show": ["commits", "pull_requests"],
        },
    }
    return ProfileConfig.model_validate(raw)


def _make_enriched_data() -> EnrichedData:
    public_repo = _make_public_repo()
    private_repo = _make_private_repo()
    fork_repo = _make_fork_repo()
    user = _make_user()
    stats = _make_stats()

    return EnrichedData(
        user=user,
        repos=[public_repo, private_repo, fork_repo],
        stats=stats,
        summaries={
            "testdev/public-project": "A very useful tool for developers. It solves the hard problem of X.",
        },
        fork_diffs={
            "testdev/forked-lib": "I added async support and fixed a memory leak in the parser.",
        },
    )


# ---------------------------------------------------------------------------
# Tests: render_profile
# ---------------------------------------------------------------------------

class TestRenderProfile:
    """Tests for render_profile()."""

    def test_returns_valid_html_with_doctype(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        assert result.strip().startswith("<!DOCTYPE html>")

    def test_contains_user_name_in_h1(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        assert "<h1>" in result
        assert "Test Developer" in result

    def test_public_repo_has_link_to_html_url(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        assert "https://github.com/testdev/public-project" in result
        assert 'href="https://github.com/testdev/public-project"' in result

    def test_private_repo_shows_private_reason(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        assert "Under NDA" in result

    def test_private_repo_has_no_link(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        # The private repo's html_url should NOT appear as a link
        assert 'href="https://github.com/testdev/secret-tool"' not in result

    def test_fork_shows_fork_diff_text(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        assert "async support" in result or "memory leak" in result

    def test_tagline_in_output(self):
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()
        result = render_profile(data, config)

        assert "Building cool things" in result


# ---------------------------------------------------------------------------
# Tests: render_readme
# ---------------------------------------------------------------------------

class TestRenderReadme:
    """Tests for render_readme()."""

    def test_returns_non_empty_markdown(self):
        from folio.render import render_readme

        data = _make_enriched_data()
        config = _make_config()
        result = render_readme(data, config)

        assert result.strip() != ""

    def test_contains_generated_by_folio_comment(self):
        from folio.render import render_readme

        data = _make_enriched_data()
        config = _make_config()
        result = render_readme(data, config)

        assert "Generated by Folio" in result

    def test_contains_user_name(self):
        from folio.render import render_readme

        data = _make_enriched_data()
        config = _make_config()
        result = render_readme(data, config)

        assert "Test Developer" in result

    def test_readme_is_minimal_teaser(self):
        """README should be a hero card + link, not a full repo listing."""
        from folio.render import render_readme

        data = _make_enriched_data()
        config = _make_config()
        result = render_readme(data, config)

        # Should have hero SVG link and CTA
        assert "hero.svg" in result
        assert "Full Profile" in result
        # Should NOT list individual repos
        assert "public-project" not in result
        assert "secret-tool" not in result


# ---------------------------------------------------------------------------
# Tests: render_style
# ---------------------------------------------------------------------------

class TestRenderStyle:
    """Tests for render_style()."""

    def test_returns_css_with_font_family(self):
        from folio.render import render_style

        data = _make_enriched_data()
        config = _make_config()
        result = render_style(data, config)

        assert "font-family" in result

    def test_css_has_accent_var(self):
        from folio.render import render_style

        data = _make_enriched_data()
        config = _make_config()
        result = render_style(data, config)

        assert "--accent:" in result

    def test_accent_defaults_to_terracotta_when_auto(self):
        from folio.render import render_style

        data = _make_enriched_data()
        config = _make_config()
        # config has accent=None which now falls through to the designed
        # Editorial terracotta rather than a language-derived color.
        result = render_style(data, config)

        assert "#ff6a3c" in result  # dark Editorial accent

    def test_accent_explicit_override(self):
        from folio.render import render_style

        data = _make_enriched_data()
        # Create config with explicit accent
        raw = {
            "profile": {"name": "Test", "social": {}},
            "ai": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "theme": {"name": "dark", "accent": "#ff5500"},
            "stats": {"range": "3mo", "show": []},
        }
        config = ProfileConfig.model_validate(raw)
        result = render_style(data, config)

        assert "#ff5500" in result


# ---------------------------------------------------------------------------
# Tests: Editorial redesign contract
# ---------------------------------------------------------------------------

class TestEditorialProfile:
    """Behavioral contract for the Editorial (1A) profile page."""

    def test_no_stars_anywhere(self):
        from folio.render import render_profile
        result = render_profile(_make_enriched_data(), _make_config())
        assert "★" not in result
        assert "stars" not in result.lower()

    def test_second_link_renders_when_present(self):
        from folio.render import render_profile
        result = render_profile(_make_enriched_data(), _make_config())
        assert "View site" in result
        assert "https://public-project.example" in result

    def test_second_link_absent_for_private_repo(self):
        # secret-tool has no link -> its label must not appear as a second link
        from folio.render import render_profile
        result = render_profile(_make_enriched_data(), _make_config())
        assert "secret-tool" in result            # still listed
        assert 'href="https://github.com/testdev/secret-tool"' not in result

    def test_heatmap_cells_present(self):
        from folio.render import render_profile
        result = render_profile(_make_enriched_data(), _make_config())
        assert "heat-cell" in result              # css class used by each day cell

    def test_available_for_work_badge_conditional(self):
        from folio.render import render_profile
        # default config: available_for_work False -> no badge
        assert "Available for work" not in render_profile(_make_enriched_data(), _make_config())
        raw = {
            "profile": {"name": "T", "available_for_work": True, "social": {}},
            "ai": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "theme": {"name": "dark", "accent": None},
            "stats": {"range": "3mo", "show": ["commits"]},
        }
        cfg = ProfileConfig.model_validate(raw)
        assert "Available for work" in render_profile(_make_enriched_data(), cfg)

    def test_activity_header_reads_months_not_weeks(self):
        """Activity section header should read 'last N months', derived from
        stats.activity_range (3mo -> 3), not a count of contribution_weeks."""
        from folio.render import render_profile

        data = _make_enriched_data()
        config = _make_config()  # activity_range defaults to "3mo"
        result = render_profile(data, config)

        match = re.search(r'<span class="label">(Activity.*?)</span>', result)
        assert match is not None
        assert match.group(1) == "Activity — last 3 months"

    def test_render_profile_does_not_raise_on_empty_name_and_login(self):
        """If both the resolved display name and the GitHub login are empty
        strings, the masthead h1 and avatar monogram must not raise
        IndexError — they should fall back to '?'."""
        from folio.render import render_profile

        empty_user = UserProfile(
            login="",
            name="",
            avatar_url="",
            bio=None,
            followers=0,
            following=0,
        )
        data = EnrichedData(
            user=empty_user,
            repos=[],
            stats=None,
            summaries={},
            fork_diffs={},
        )
        # profile.name is left unset (defaults to "") so full_name resolves
        # to (user.name or user.login), which is also "".
        raw = {
            "profile": {"social": {}},
            "ai": {"provider": "anthropic", "model": "claude-sonnet-4-6"},
            "theme": {"name": "dark", "accent": None},
            "stats": {"range": "3mo", "show": []},
        }
        config = ProfileConfig.model_validate(raw)

        result = render_profile(data, config)

        assert isinstance(result, str)
        assert "?" in result

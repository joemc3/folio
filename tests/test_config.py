"""Tests for folio.config module."""

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_CONFIG = FIXTURES_DIR / "sample_config.yml"


# ---------------------------------------------------------------------------
# RepoEntry tests
# ---------------------------------------------------------------------------

class TestRepoEntry:
    def test_from_flexible_with_string(self):
        from folio.config import RepoEntry
        entry = RepoEntry.from_flexible("my-repo")
        assert entry.name == "my-repo"
        assert entry.private_reason is None

    def test_from_flexible_with_dict(self):
        from folio.config import RepoEntry
        entry = RepoEntry.from_flexible({"name": "my-repo", "private_reason": "NDA"})
        assert entry.name == "my-repo"
        assert entry.private_reason == "NDA"

    def test_from_flexible_with_dict_no_reason(self):
        from folio.config import RepoEntry
        entry = RepoEntry.from_flexible({"name": "my-repo"})
        assert entry.name == "my-repo"
        assert entry.private_reason is None

    def test_from_flexible_with_repo_entry_instance(self):
        from folio.config import RepoEntry
        original = RepoEntry(name="existing")
        result = RepoEntry.from_flexible(original)
        assert result.name == "existing"
        assert result.private_reason is None

    def test_repo_entry_direct_construction(self):
        from folio.config import RepoEntry
        entry = RepoEntry(name="direct", private_reason="secret")
        assert entry.name == "direct"
        assert entry.private_reason == "secret"


# ---------------------------------------------------------------------------
# ReposSection include field coercion tests
# ---------------------------------------------------------------------------

class TestReposSectionIncludeCoercion:
    def test_include_list_coerces_strings(self):
        from folio.config import ReposSection
        repos = ReposSection(include=["repo-a", "repo-b"])
        assert len(repos.include) == 2
        assert repos.include[0].name == "repo-a"
        assert repos.include[1].name == "repo-b"

    def test_include_list_coerces_dicts(self):
        from folio.config import ReposSection
        repos = ReposSection(include=[{"name": "repo-a"}, {"name": "repo-b", "private_reason": "NDA"}])
        assert repos.include[0].name == "repo-a"
        assert repos.include[1].private_reason == "NDA"

    def test_include_list_mixed(self):
        from folio.config import ReposSection
        repos = ReposSection(include=["plain-string", {"name": "dict-entry"}])
        assert repos.include[0].name == "plain-string"
        assert repos.include[1].name == "dict-entry"

    def test_include_defaults_to_none_when_omitted(self):
        from folio.config import ReposSection
        repos = ReposSection()
        assert repos.include is None

    def test_include_none_explicit(self):
        from folio.config import ReposSection
        repos = ReposSection(include=None)
        assert repos.include is None


# ---------------------------------------------------------------------------
# AISection provider validation
# ---------------------------------------------------------------------------

class TestAISectionProvider:
    @pytest.mark.parametrize("provider", ["anthropic", "openai", "ollama", "openrouter"])
    def test_valid_providers(self, provider):
        from folio.config import AISection
        ai = AISection(provider=provider, model="some-model")
        assert ai.provider == provider

    def test_invalid_provider_raises(self):
        from folio.config import AISection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AISection(provider="badprovider", model="some-model")

    def test_invalid_provider_empty_raises(self):
        from folio.config import AISection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            AISection(provider="", model="some-model")


# ---------------------------------------------------------------------------
# StatsSection range validation
# ---------------------------------------------------------------------------

class TestStatsSectionRange:
    @pytest.mark.parametrize("range_val", ["1mo", "3mo", "1yr", "alltime"])
    def test_valid_ranges(self, range_val):
        from folio.config import StatsSection
        stats = StatsSection(range=range_val)
        assert stats.range == range_val

    def test_invalid_range_raises(self):
        from folio.config import StatsSection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StatsSection(range="2yr")

    def test_invalid_range_month_raises(self):
        from folio.config import StatsSection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StatsSection(range="6mo")


# ---------------------------------------------------------------------------
# StatsSection show field validation
# ---------------------------------------------------------------------------

class TestStatsSectionShow:
    @pytest.mark.parametrize("stat", ["commits", "pull_requests", "issues", "streak", "top_languages", "stars_earned"])
    def test_valid_stats(self, stat):
        from folio.config import StatsSection
        stats = StatsSection(show=[stat])
        assert stat in stats.show

    def test_invalid_stat_raises(self):
        from folio.config import StatsSection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            StatsSection(show=["bad_stat"])


# ---------------------------------------------------------------------------
# ThemeSection name validation
# ---------------------------------------------------------------------------

class TestThemeSectionName:
    @pytest.mark.parametrize("theme", ["dark", "light", "auto"])
    def test_valid_themes(self, theme):
        from folio.config import ThemeSection
        t = ThemeSection(name=theme)
        assert t.name == theme

    def test_invalid_theme_raises(self):
        from folio.config import ThemeSection
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ThemeSection(name="solarized")


# ---------------------------------------------------------------------------
# load_config tests
# ---------------------------------------------------------------------------

class TestLoadConfig:
    def test_load_valid_config(self):
        from folio.config import load_config, ProfileConfig
        config = load_config(SAMPLE_CONFIG)
        assert isinstance(config, ProfileConfig)

    def test_load_config_profile_fields(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        assert config.profile.name == "Test User"
        assert config.profile.tagline == "Building things"
        assert config.profile.location == "Austin, TX"

    def test_load_config_social_fields(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        assert config.profile.social.twitter == "testuser"
        assert config.profile.social.linkedin == "testuser"

    def test_load_config_ai_section(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        assert config.ai.provider == "anthropic"
        assert config.ai.model == "claude-sonnet-4-6"

    def test_load_config_repos_section(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        # Sample config has 3 include entries: public-project, private-project, my-fork
        assert config.repos.include is not None
        assert len(config.repos.include) == 3
        names = [e.name for e in config.repos.include]
        assert "public-project" in names
        assert "private-project" in names

    def test_load_config_repos_private_reason(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        private = next(e for e in config.repos.include if e.name == "private-project")
        assert private.private_reason == "Under NDA"

    def test_load_config_stats_section(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        assert config.stats.range == "3mo"
        assert "commits" in config.stats.show
        assert config.stats.language_count == 6

    def test_load_config_theme_section(self):
        from folio.config import load_config
        config = load_config(SAMPLE_CONFIG)
        assert config.theme.name == "dark"

    def test_load_config_missing_file_raises(self, tmp_path):
        from folio.config import load_config
        missing = tmp_path / "nonexistent.yml"
        with pytest.raises(FileNotFoundError):
            load_config(missing)

    def test_load_config_omitted_include_is_none(self, tmp_path):
        """When 'include' is omitted from repos section, it should default to None."""
        import yaml
        config_data = {
            "profile": {"name": "Test", "social": {}},
            "ai": {"provider": "openai", "model": "gpt-4"},
            "repos": {"exclude": ["old-repo"], "forks": {"show": False}},
            "stats": {"range": "1mo", "show": ["commits"]},
            "theme": {"name": "light"},
        }
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(config_data))
        from folio.config import load_config
        config = load_config(config_file)
        assert config.repos.include is None

    def test_load_config_string_to_repo_entry_coercion(self, tmp_path):
        """String items in include list are coerced to RepoEntry."""
        import yaml
        config_data = {
            "profile": {"name": "Test", "social": {}},
            "ai": {"provider": "openai", "model": "gpt-4"},
            "repos": {"include": ["my-string-repo"]},
            "stats": {"range": "1mo", "show": ["commits"]},
            "theme": {"name": "light"},
        }
        config_file = tmp_path / "config.yml"
        config_file.write_text(yaml.dump(config_data))
        from folio.config import load_config, RepoEntry
        config = load_config(config_file)
        assert len(config.repos.include) == 1
        assert isinstance(config.repos.include[0], RepoEntry)
        assert config.repos.include[0].name == "my-string-repo"

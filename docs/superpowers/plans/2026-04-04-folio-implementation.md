# Folio Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that generates a GitHub profile page (README.md + HTML site) from local config, GitHub data, and AI summaries.

**Architecture:** Linear pipeline — config → GitHub fetch → AI summarize → Jinja2 render → write files. Each module is a pure-ish function that takes typed data in and returns typed data out. CLI orchestrates the pipeline. Templates produce two outputs: an SVG-heavy README.md for the GitHub profile and a self-contained HTML site for GitHub Pages.

**Tech Stack:** Python 3.11+, Typer, Rich, Pydantic, PyGitHub, GitPython, LiteLLM, Jinja2, PyYAML, pytest

**Design spec:** `docs/superpowers/specs/2026-04-04-folio-design.md`

**Important for agentic workers — Visual Design:**
The generated HTML site MUST NOT look like generic AI output. No purple gradients, no Inter font, no SaaS landing page aesthetic, no glassmorphism, no shadcn-style cards. Use the frontend-design skill when implementing templates. Reference the design spec Section 7 for exact colors, typography, and layout rules. The mockup at `.superpowers/brainstorm/30352-1775349518/content/profile-direction-v3.html` is the approved visual direction.

---

## File Map

### Create

| File | Responsibility |
|---|---|
| `pyproject.toml` | Package config, deps, entry point |
| `.gitignore` | Ignore .profile.yml, dist/, __pycache__, .folio/ |
| `.profile.yml.example` | Template config for new users |
| `folio/__init__.py` | Package init, version |
| `folio/config.py` | Pydantic models, YAML loading, validation |
| `folio/github.py` | Auth, data types, GitHub API fetching |
| `folio/git.py` | Fork diff via GitPython |
| `folio/summarize.py` | LiteLLM wrapper, prompts, cache |
| `folio/render.py` | Jinja2 rendering engine |
| `folio/push.py` | Git commit + push |
| `folio/cli.py` | Typer app, all commands, pipeline orchestration |
| `folio/colors.py` | GitHub language → color mapping |
| `templates/profile.html.j2` | Full HTML profile site template |
| `templates/style.css.j2` | CSS with theme variables (rendered, not static) |
| `templates/readme.md.j2` | GitHub profile README template |
| `templates/components/hero.svg.j2` | SVG hero card for README |
| `templates/components/stats_card.svg.j2` | SVG stats for README |
| `templates/components/language_chart.svg.j2` | SVG language bar for README |
| `tests/conftest.py` | Shared fixtures |
| `tests/test_config.py` | Config validation tests |
| `tests/test_github.py` | Mocked GitHub API tests |
| `tests/test_git.py` | Mocked GitPython tests |
| `tests/test_summarize.py` | Mocked LiteLLM + cache tests |
| `tests/test_render.py` | Template rendering tests |
| `tests/test_push.py` | Mocked push tests |
| `tests/test_cli.py` | CLI command tests |
| `tests/fixtures/sample_config.yml` | Valid test config |
| `tests/fixtures/sample_readme.md` | Sample repo README for summarize tests |

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `folio/__init__.py`, `tests/conftest.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "folio-profile"
version = "0.1.0"
description = "Generate a spectacular GitHub profile page from your local machine."
requires-python = ">=3.11"
license = "MIT"

dependencies = [
    "typer[all]>=0.12",
    "rich>=13",
    "pydantic>=2",
    "PyGithub>=2",
    "GitPython>=3",
    "litellm>=1.40",
    "jinja2>=3",
    "pyyaml>=6",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-cov>=5",
]

[project.scripts]
folio = "folio.cli:app"
```

- [ ] **Step 2: Create .gitignore**

```gitignore
# Personal config — never commit
.profile.yml

# Generated output
dist/

# Python
__pycache__/
*.pyc
*.egg-info/
.venv/

# Folio cache
.folio/

# Brainstorm artifacts
.superpowers/
```

- [ ] **Step 3: Create folio/__init__.py**

```python
"""Folio — Generate a spectacular GitHub profile page from your local machine."""

__version__ = "0.1.0"
```

- [ ] **Step 4: Create tests/conftest.py**

```python
"""Shared test fixtures for Folio."""

import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir():
    return FIXTURES_DIR


@pytest.fixture
def tmp_config(tmp_path):
    """Write a valid .profile.yml to a temp directory and return its path."""
    config_text = (FIXTURES_DIR / "sample_config.yml").read_text()
    config_path = tmp_path / ".profile.yml"
    config_path.write_text(config_text)
    return config_path
```

- [ ] **Step 5: Create tests/fixtures directory and sample_config.yml**

```yaml
profile:
  name: "Test User"
  tagline: "Building things"
  location: "Austin, TX"
  resume_url: "https://example.com/resume"
  avatar: ""
  social:
    twitter: "testuser"
    linkedin: "testuser"
    website: "https://example.com"

ai:
  provider: anthropic
  model: claude-sonnet-4-20250514
  base_url: ""

repos:
  include:
    - name: public-project
    - name: private-project
      private_reason: "Under NDA"
    - name: my-fork
  exclude:
    - old-project
  forks:
    show: true
    summarize_diff: true

stats:
  range: 3mo
  show:
    - commits
    - pull_requests
    - issues
    - streak
    - top_languages
    - stars_earned
  language_count: 6

theme:
  name: dark
  accent: auto
```

- [ ] **Step 6: Create tests/fixtures/sample_readme.md**

```markdown
# My Project

A tool for doing interesting things with data.

## Installation

pip install my-project

## Usage

Run `my-project analyze` to get started.
```

- [ ] **Step 7: Install in dev mode and verify**

Run: `cd /Users/joemc3/tmp/folio && python -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"`

Expected: Successful install, `folio` entry point registered (will fail to run since cli.py doesn't exist yet, that's fine)

- [ ] **Step 8: Verify pytest runs**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/ -v`

Expected: "no tests ran" or similar — no errors about missing packages

- [ ] **Step 9: Commit**

```bash
git add pyproject.toml .gitignore folio/__init__.py tests/conftest.py tests/fixtures/
git commit -m "scaffold: project structure, deps, and test fixtures"
```

---

## Task 2: Config Module

**Files:**
- Create: `folio/config.py`, `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config loading**

File: `tests/test_config.py`

```python
"""Tests for config loading and validation."""

import pytest
import yaml
from pathlib import Path
from folio.config import load_config, ProfileConfig, RepoEntry


class TestRepoEntryCoercion:
    """RepoEntry accepts plain strings or objects."""

    def test_string_coerced_to_repo_entry(self):
        entry = RepoEntry.from_flexible("my-repo")
        assert entry.name == "my-repo"
        assert entry.private_reason is None

    def test_dict_parsed_to_repo_entry(self):
        entry = RepoEntry.from_flexible({"name": "my-repo", "private_reason": "NDA"})
        assert entry.name == "my-repo"
        assert entry.private_reason == "NDA"

    def test_dict_without_reason(self):
        entry = RepoEntry.from_flexible({"name": "my-repo"})
        assert entry.name == "my-repo"
        assert entry.private_reason is None


class TestProfileConfig:
    """Config loading from YAML."""

    def test_load_valid_config(self, tmp_config):
        config = load_config(tmp_config)
        assert config.profile.name == "Test User"
        assert config.profile.tagline == "Building things"
        assert config.ai.provider == "anthropic"
        assert len(config.repos.include) == 3
        assert config.repos.include[1].private_reason == "Under NDA"
        assert config.stats.range == "3mo"
        assert config.theme.name == "dark"

    def test_load_config_with_string_includes(self, tmp_path):
        config_text = """
profile:
  name: "Test"
  tagline: "Test"
  location: ""
  resume_url: ""
  avatar: ""
  social:
    twitter: ""
    linkedin: ""
    website: ""
ai:
  provider: anthropic
  model: claude-sonnet-4-20250514
  base_url: ""
repos:
  include:
    - simple-repo
    - name: detailed-repo
      private_reason: "Secret"
  exclude: []
  forks:
    show: true
    summarize_diff: true
stats:
  range: 3mo
  show: [commits]
  language_count: 6
theme:
  name: dark
  accent: auto
"""
        config_path = tmp_path / ".profile.yml"
        config_path.write_text(config_text)
        config = load_config(config_path)
        assert config.repos.include[0].name == "simple-repo"
        assert config.repos.include[0].private_reason is None
        assert config.repos.include[1].name == "detailed-repo"
        assert config.repos.include[1].private_reason == "Secret"

    def test_invalid_provider_raises(self, tmp_path):
        config_text = """
profile:
  name: "Test"
  tagline: "Test"
  location: ""
  resume_url: ""
  avatar: ""
  social: {twitter: "", linkedin: "", website: ""}
ai:
  provider: invalid_provider
  model: test
  base_url: ""
repos:
  include: []
  exclude: []
  forks: {show: true, summarize_diff: true}
stats:
  range: 3mo
  show: [commits]
  language_count: 6
theme:
  name: dark
  accent: auto
"""
        config_path = tmp_path / ".profile.yml"
        config_path.write_text(config_text)
        with pytest.raises(ValueError, match="provider"):
            load_config(config_path)

    def test_invalid_range_raises(self, tmp_path):
        config_text = """
profile:
  name: "Test"
  tagline: "Test"
  location: ""
  resume_url: ""
  avatar: ""
  social: {twitter: "", linkedin: "", website: ""}
ai:
  provider: anthropic
  model: test
  base_url: ""
repos:
  include: []
  exclude: []
  forks: {show: true, summarize_diff: true}
stats:
  range: 6mo
  show: [commits]
  language_count: 6
theme:
  name: dark
  accent: auto
"""
        config_path = tmp_path / ".profile.yml"
        config_path.write_text(config_text)
        with pytest.raises(ValueError, match="range"):
            load_config(config_path)

    def test_missing_config_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_config(tmp_path / "nonexistent.yml")

    def test_include_defaults_to_empty_when_omitted(self, tmp_path):
        config_text = """
profile:
  name: "Test"
  tagline: "Test"
  location: ""
  resume_url: ""
  avatar: ""
  social: {twitter: "", linkedin: "", website: ""}
ai:
  provider: anthropic
  model: test
  base_url: ""
repos:
  exclude: []
  forks: {show: true, summarize_diff: true}
stats:
  range: 3mo
  show: [commits]
  language_count: 6
theme:
  name: dark
  accent: auto
"""
        config_path = tmp_path / ".profile.yml"
        config_path.write_text(config_text)
        config = load_config(config_path)
        assert config.repos.include is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_config.py -v`

Expected: ImportError — `folio.config` doesn't exist yet

- [ ] **Step 3: Implement config.py**

File: `folio/config.py`

```python
"""Configuration loading and validation for Folio."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, field_validator, model_validator


VALID_PROVIDERS = {"anthropic", "openai", "ollama", "openrouter"}
VALID_RANGES = {"1mo", "3mo", "1yr", "alltime"}
VALID_STATS = {"commits", "pull_requests", "issues", "streak", "top_languages", "stars_earned"}
VALID_THEMES = {"dark", "light", "auto"}


class RepoEntry(BaseModel):
    """A repo in the include list."""

    name: str
    private_reason: str | None = None

    @classmethod
    def from_flexible(cls, value: str | dict) -> RepoEntry:
        """Accept a plain string or a dict with name + optional private_reason."""
        if isinstance(value, str):
            return cls(name=value)
        if isinstance(value, dict):
            return cls(**value)
        raise ValueError(f"Expected string or dict for repo entry, got {type(value)}")


class SocialSection(BaseModel):
    twitter: str = ""
    linkedin: str = ""
    website: str = ""


class ProfileSection(BaseModel):
    name: str
    tagline: str
    location: str = ""
    resume_url: str = ""
    avatar: str = ""
    social: SocialSection = SocialSection()


class AISection(BaseModel):
    provider: str
    model: str
    base_url: str = ""

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in VALID_PROVIDERS:
            raise ValueError(
                f"Unknown provider '{v}'. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
            )
        return v


class ForksSection(BaseModel):
    show: bool = True
    summarize_diff: bool = True


class ReposSection(BaseModel):
    include: list[RepoEntry] | None = None
    exclude: list[str] = []
    forks: ForksSection = ForksSection()

    @field_validator("include", mode="before")
    @classmethod
    def coerce_include(cls, v):
        if v is None:
            return None
        return [RepoEntry.from_flexible(item) for item in v]


class StatsSection(BaseModel):
    range: str = "3mo"
    show: list[str] = ["commits", "pull_requests", "issues", "streak", "top_languages", "stars_earned"]
    language_count: int = 6

    @field_validator("range")
    @classmethod
    def validate_range(cls, v: str) -> str:
        if v not in VALID_RANGES:
            raise ValueError(
                f"Unknown range '{v}'. Must be one of: {', '.join(sorted(VALID_RANGES))}"
            )
        return v

    @field_validator("show", mode="before")
    @classmethod
    def validate_show(cls, v):
        for item in v:
            if item not in VALID_STATS:
                raise ValueError(
                    f"Unknown stat '{item}'. Must be one of: {', '.join(sorted(VALID_STATS))}"
                )
        return v


class ThemeSection(BaseModel):
    name: str = "dark"
    accent: str = "auto"

    @field_validator("name")
    @classmethod
    def validate_theme(cls, v: str) -> str:
        if v not in VALID_THEMES:
            raise ValueError(
                f"Unknown theme '{v}'. Must be one of: {', '.join(sorted(VALID_THEMES))}"
            )
        return v


class ProfileConfig(BaseModel):
    profile: ProfileSection
    ai: AISection
    repos: ReposSection = ReposSection()
    stats: StatsSection = StatsSection()
    theme: ThemeSection = ThemeSection()


def load_config(path: Path) -> ProfileConfig:
    """Load and validate .profile.yml from the given path."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with open(path) as f:
        raw = yaml.safe_load(f)

    return ProfileConfig(**raw)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_config.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add folio/config.py tests/test_config.py
git commit -m "feat: config module with Pydantic validation and RepoEntry coercion"
```

---

## Task 3: GitHub Data Types & Auth

**Files:**
- Create: `folio/github.py`, `tests/test_github.py`

- [ ] **Step 1: Write failing tests for auth and data types**

File: `tests/test_github.py`

```python
"""Tests for GitHub data fetching."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone

from folio.github import (
    get_github_token,
    UserProfile,
    RepoData,
    StatsData,
    GitHubData,
    fetch_github_data,
)
from folio.config import load_config


class TestAuth:
    """GitHub auth token resolution."""

    @patch("folio.github.subprocess.run")
    def test_gh_cli_token(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="ghp_test_token_123\n"
        )
        token = get_github_token()
        assert token == "ghp_test_token_123"

    @patch("folio.github.subprocess.run")
    @patch.dict("os.environ", {"GITHUB_TOKEN": "env_token_456"})
    def test_fallback_to_env_var(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        token = get_github_token()
        assert token == "env_token_456"

    @patch("folio.github.subprocess.run")
    @patch.dict("os.environ", {}, clear=True)
    def test_no_token_raises(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        # Also clear GITHUB_TOKEN if present
        import os
        os.environ.pop("GITHUB_TOKEN", None)
        with pytest.raises(RuntimeError, match="auth"):
            get_github_token()


class TestDataTypes:
    """Data types are constructable."""

    def test_user_profile(self):
        user = UserProfile(
            login="testuser",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            bio="Hello",
            followers=10,
            following=5,
        )
        assert user.login == "testuser"

    def test_repo_data(self):
        repo = RepoData(
            name="my-repo",
            full_name="testuser/my-repo",
            description="A test repo",
            language="Python",
            stars=5,
            last_updated=datetime.now(timezone.utc),
            is_fork=False,
            is_private=False,
            fork_parent=None,
            private_reason=None,
            html_url="https://github.com/testuser/my-repo",
        )
        assert repo.name == "my-repo"
        assert not repo.is_fork

    def test_stats_data(self):
        stats = StatsData(
            commits=100,
            pull_requests=10,
            issues=5,
            streak_days=42,
            stars_earned=20,
            languages={"Python": 60.0, "Go": 40.0},
        )
        assert stats.commits == 100
        assert stats.languages["Python"] == 60.0


class TestFetchGitHubData:
    """Mocked GitHub API fetching."""

    def _make_mock_github(self):
        """Build a mock Github instance with user and repos."""
        mock_gh = MagicMock()

        # Mock user
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_user.name = "Test User"
        mock_user.avatar_url = "https://example.com/avatar.png"
        mock_user.bio = "Hello world"
        mock_user.followers = 50
        mock_user.following = 20
        mock_gh.get_user.return_value = mock_user

        # Mock repos
        mock_repo1 = MagicMock()
        mock_repo1.name = "public-project"
        mock_repo1.full_name = "testuser/public-project"
        mock_repo1.description = "A public project"
        mock_repo1.language = "Python"
        mock_repo1.stargazers_count = 10
        mock_repo1.updated_at = datetime(2026, 3, 1, tzinfo=timezone.utc)
        mock_repo1.fork = False
        mock_repo1.private = False
        mock_repo1.parent = None
        mock_repo1.html_url = "https://github.com/testuser/public-project"
        mock_repo1.size = 1000
        mock_repo1.get_readme.return_value = MagicMock(decoded_content=b"# Public Project\nA public project.")
        mock_repo1.get_commits.return_value = [
            MagicMock(commit=MagicMock(message="feat: add feature"))
        ]

        mock_repo2 = MagicMock()
        mock_repo2.name = "private-project"
        mock_repo2.full_name = "testuser/private-project"
        mock_repo2.description = "A private project"
        mock_repo2.language = "Go"
        mock_repo2.stargazers_count = 0
        mock_repo2.updated_at = datetime(2026, 2, 15, tzinfo=timezone.utc)
        mock_repo2.fork = False
        mock_repo2.private = True
        mock_repo2.parent = None
        mock_repo2.html_url = "https://github.com/testuser/private-project"
        mock_repo2.size = 500
        mock_repo2.get_readme.return_value = MagicMock(decoded_content=b"# Private\nSecret stuff.")
        mock_repo2.get_commits.return_value = [
            MagicMock(commit=MagicMock(message="fix: patch bug"))
        ]

        mock_user.get_repos.return_value = [mock_repo1, mock_repo2]

        # Mock search for commits
        mock_gh.search_commits.return_value.totalCount = 100

        # Mock search for issues/PRs
        mock_gh.search_issues.return_value.totalCount = 10

        return mock_gh

    @patch("folio.github.Github")
    @patch("folio.github.get_github_token", return_value="fake_token")
    def test_fetch_repos_with_include_list(self, mock_token, mock_gh_cls, tmp_config):
        mock_gh = self._make_mock_github()
        mock_gh_cls.return_value = mock_gh

        config = load_config(tmp_config)
        data = fetch_github_data(config)

        assert isinstance(data, GitHubData)
        assert data.user.login == "testuser"
        # Should include public-project and private-project (both in include list)
        repo_names = [r.name for r in data.repos]
        assert "public-project" in repo_names
        assert "private-project" in repo_names

    @patch("folio.github.Github")
    @patch("folio.github.get_github_token", return_value="fake_token")
    def test_exclude_filters_repos(self, mock_token, mock_gh_cls, tmp_config):
        mock_gh = self._make_mock_github()
        mock_gh_cls.return_value = mock_gh

        config = load_config(tmp_config)
        data = fetch_github_data(config)

        repo_names = [r.name for r in data.repos]
        assert "old-project" not in repo_names

    @patch("folio.github.Github")
    @patch("folio.github.get_github_token", return_value="fake_token")
    def test_private_reason_attached(self, mock_token, mock_gh_cls, tmp_config):
        mock_gh = self._make_mock_github()
        mock_gh_cls.return_value = mock_gh

        config = load_config(tmp_config)
        data = fetch_github_data(config)

        private_repo = next(r for r in data.repos if r.name == "private-project")
        assert private_repo.private_reason == "Under NDA"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_github.py -v`

Expected: ImportError — `folio.github` doesn't exist yet

- [ ] **Step 3: Implement github.py**

File: `folio/github.py`

```python
"""GitHub API data fetching for Folio."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from github import Github, GithubException

if TYPE_CHECKING:
    from folio.config import ProfileConfig


# ── Data Types ──────────────────────────────────────────


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


# ── Auth ────────────────────────────────────────────────


def get_github_token() -> str:
    """Get GitHub token: try gh CLI first, then GITHUB_TOKEN env var."""
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        return token

    raise RuntimeError(
        "No GitHub auth found. Run 'gh auth login' or set GITHUB_TOKEN environment variable."
    )


# ── Fetching ────────────────────────────────────────────


def _compute_since(range_str: str) -> datetime | None:
    """Convert a range string to a datetime cutoff."""
    now = datetime.now(timezone.utc)
    match range_str:
        case "1mo":
            return now - timedelta(days=30)
        case "3mo":
            return now - timedelta(days=90)
        case "1yr":
            return now - timedelta(days=365)
        case "alltime":
            return None
    return None


def _fetch_user(gh: Github) -> UserProfile:
    """Fetch authenticated user profile."""
    user = gh.get_user()
    return UserProfile(
        login=user.login,
        name=user.name or user.login,
        avatar_url=user.avatar_url,
        bio=user.bio,
        followers=user.followers,
        following=user.following,
    )


def _fetch_repos(gh: Github, config: ProfileConfig, username: str) -> list[RepoData]:
    """Fetch repos according to include/exclude config."""
    user = gh.get_user()

    # Build lookup of config entries for private_reason
    reason_map: dict[str, str | None] = {}
    include_names: set[str] | None = None
    if config.repos.include is not None:
        include_names = set()
        for entry in config.repos.include:
            include_names.add(entry.name)
            reason_map[entry.name] = entry.private_reason

    exclude_names = set(config.repos.exclude)

    # Fetch all repos the user has access to
    all_repos = user.get_repos(sort="updated")

    repos: list[RepoData] = []
    for repo in all_repos:
        # Filter by include list
        if include_names is not None and repo.name not in include_names:
            continue
        # Filter by exclude list
        if repo.name in exclude_names:
            continue
        # If no include list, default to public repos only
        if include_names is None and repo.private:
            continue

        # Skip forks if configured to hide them
        if repo.fork and not config.repos.forks.show:
            continue

        # Get fork parent
        fork_parent = None
        if repo.fork and repo.parent:
            fork_parent = repo.parent.full_name

        # Get private reason
        private_reason = reason_map.get(repo.name)
        if repo.private and private_reason is None:
            private_reason = "Private repository"

        # Get README text
        readme_text = ""
        try:
            readme = repo.get_readme()
            readme_text = readme.decoded_content.decode("utf-8", errors="replace")[:2000]
        except GithubException:
            pass

        # Get recent commits
        recent_commits = []
        try:
            commits = repo.get_commits()
            noise_patterns = {"merge branch", "merge pull request", "fix typo", "update readme"}
            count = 0
            for commit in commits:
                if count >= 10:
                    break
                msg = commit.commit.message.split("\n")[0]
                if not any(p in msg.lower() for p in noise_patterns):
                    recent_commits.append(msg)
                    count += 1
        except GithubException:
            pass

        repos.append(RepoData(
            name=repo.name,
            full_name=repo.full_name,
            description=repo.description,
            language=repo.language,
            stars=repo.stargazers_count,
            last_updated=repo.updated_at,
            is_fork=repo.fork,
            is_private=repo.private,
            fork_parent=fork_parent,
            private_reason=private_reason if repo.private else None,
            html_url=repo.html_url,
            readme_text=readme_text,
            recent_commits=recent_commits,
        ))

    return repos


def _fetch_stats(gh: Github, config: ProfileConfig, username: str, repos: list[RepoData]) -> StatsData:
    """Fetch user stats for the configured time range."""
    since = _compute_since(config.stats.range)
    since_str = since.strftime("%Y-%m-%d") if since else ""

    stats = StatsData()

    # Commits
    if "commits" in config.stats.show:
        try:
            query = f"author:{username}"
            if since_str:
                query += f" committer-date:>{since_str}"
            result = gh.search_commits(query=query)
            stats.commits = result.totalCount
        except GithubException:
            pass

    # Pull requests
    if "pull_requests" in config.stats.show:
        try:
            query = f"author:{username} type:pr"
            if since_str:
                query += f" created:>{since_str}"
            result = gh.search_issues(query=query)
            stats.pull_requests = result.totalCount
        except GithubException:
            pass

    # Issues
    if "issues" in config.stats.show:
        try:
            query = f"author:{username} type:issue"
            if since_str:
                query += f" created:>{since_str}"
            result = gh.search_issues(query=query)
            stats.issues = result.totalCount
        except GithubException:
            pass

    # Stars earned
    if "stars_earned" in config.stats.show:
        stats.stars_earned = sum(r.stars for r in repos)

    # Top languages
    if "top_languages" in config.stats.show:
        lang_sizes: dict[str, int] = {}
        for repo in repos:
            if repo.language:
                lang_sizes[repo.language] = lang_sizes.get(repo.language, 0) + 1
        total = sum(lang_sizes.values()) or 1
        # Sort by count descending, take top N
        sorted_langs = sorted(lang_sizes.items(), key=lambda x: x[1], reverse=True)
        top = sorted_langs[:config.stats.language_count]
        stats.languages = {lang: round(count / total * 100, 1) for lang, count in top}

    # Streak — simplified: count from commit search results
    if "streak" in config.stats.show:
        try:
            query = f"author:{username}"
            if since_str:
                query += f" committer-date:>{since_str}"
            commits = gh.search_commits(query=query)
            # Collect commit dates for streak calculation
            dates: set[str] = set()
            for i, commit in enumerate(commits):
                if i >= 500:  # limit iteration
                    break
                date_str = commit.commit.committer.date.strftime("%Y-%m-%d")
                dates.add(date_str)

            # Calculate longest consecutive streak
            if dates:
                sorted_dates = sorted(datetime.strptime(d, "%Y-%m-%d") for d in dates)
                max_streak = 1
                current_streak = 1
                for i in range(1, len(sorted_dates)):
                    if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
                        current_streak += 1
                        max_streak = max(max_streak, current_streak)
                    else:
                        current_streak = 1
                stats.streak_days = max_streak
        except GithubException:
            pass

    return stats


def fetch_github_data(config: ProfileConfig) -> GitHubData:
    """Main entry point: fetch all GitHub data per config."""
    token = get_github_token()
    gh = Github(token)

    user = _fetch_user(gh)
    repos = _fetch_repos(gh, config, user.login)
    stats = _fetch_stats(gh, config, user.login, repos)

    return GitHubData(user=user, repos=repos, stats=stats)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_github.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add folio/github.py tests/test_github.py
git commit -m "feat: GitHub data types, auth chain, and API fetching"
```

---

## Task 4: Git Module (Fork Diffs)

**Files:**
- Create: `folio/git.py`, `tests/test_git.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_git.py`

```python
"""Tests for git operations (fork diffs)."""

import pytest
from unittest.mock import patch, MagicMock
from folio.git import get_fork_diff


class TestGetForkDiff:
    """Fork diff against upstream."""

    @patch("folio.git.Repo")
    def test_returns_diff_text(self, mock_repo_cls, tmp_path):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.git.diff.return_value = "diff --git a/file.py b/file.py\n+new line"
        mock_repo.remotes = {"upstream": MagicMock(), "origin": MagicMock()}

        result = get_fork_diff(str(tmp_path))
        assert "new line" in result

    @patch("folio.git.Repo")
    def test_missing_upstream_returns_none_with_warning(self, mock_repo_cls, tmp_path, caplog):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.remotes = {"origin": MagicMock()}
        # Make remote lookup raise
        type(mock_repo).remotes = property(lambda self: MagicMock(__contains__=lambda s, k: k != "upstream"))

        result = get_fork_diff(str(tmp_path))
        assert result is None

    @patch("folio.git.Repo")
    def test_git_error_returns_none(self, mock_repo_cls, tmp_path):
        from git.exc import GitCommandError
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo
        mock_repo.git.diff.side_effect = GitCommandError("diff", "error")
        mock_repo.remotes.__contains__ = lambda self, k: True

        result = get_fork_diff(str(tmp_path))
        assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_git.py -v`

Expected: ImportError — `folio.git` doesn't exist

- [ ] **Step 3: Implement git.py**

File: `folio/git.py`

```python
"""Git operations for Folio — fork diff analysis."""

from __future__ import annotations

import logging

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

logger = logging.getLogger(__name__)

# Patterns to strip from diffs (lockfiles, generated code)
NOISE_PATTERNS = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "go.sum",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
}


def _strip_noise_from_diff(diff_text: str) -> str:
    """Remove lockfile and generated code hunks from diff text."""
    lines = diff_text.split("\n")
    result = []
    skip = False

    for line in lines:
        if line.startswith("diff --git"):
            # Check if this file is noise
            skip = any(noise in line for noise in NOISE_PATTERNS)
            if skip:
                continue
        if skip:
            continue
        result.append(line)

    return "\n".join(result)[:3000]


def get_fork_diff(repo_path: str) -> str | None:
    """Get diff between HEAD and upstream/HEAD for a forked repo.

    Returns the diff text (truncated to 3000 chars with noise stripped),
    or None if upstream remote doesn't exist or diff fails.
    """
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        logger.warning("Not a git repository: %s", repo_path)
        return None

    # Check for upstream remote
    remote_names = [r.name for r in repo.remotes]
    if "upstream" not in remote_names:
        logger.warning(
            "No 'upstream' remote found in %s. "
            "Add it with: git remote add upstream <url>",
            repo_path,
        )
        return None

    try:
        diff_text = repo.git.diff("upstream/HEAD", "HEAD")
        return _strip_noise_from_diff(diff_text)
    except GitCommandError as e:
        logger.warning("Failed to get fork diff for %s: %s", repo_path, e)
        return None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_git.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add folio/git.py tests/test_git.py
git commit -m "feat: git module for fork diff analysis"
```

---

## Task 5: Summarize Module (AI + Cache)

**Files:**
- Create: `folio/summarize.py`, `tests/test_summarize.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_summarize.py`

```python
"""Tests for AI summarization and caching."""

import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from folio.summarize import (
    summarize_repo,
    summarize_fork_diff,
    SummaryCache,
    enrich_data,
    REPO_SUMMARY_PROMPT,
    FORK_DIFF_PROMPT,
)
from folio.github import RepoData, StatsData, UserProfile, GitHubData
from folio.config import load_config
from datetime import datetime, timezone


@pytest.fixture
def sample_repo():
    return RepoData(
        name="test-repo",
        full_name="user/test-repo",
        description="A test repository",
        language="Python",
        stars=5,
        last_updated=datetime.now(timezone.utc),
        is_fork=False,
        is_private=False,
        fork_parent=None,
        private_reason=None,
        html_url="https://github.com/user/test-repo",
        readme_text="# Test Repo\nThis does testing things.",
        recent_commits=["feat: add feature X", "fix: resolve issue Y"],
    )


class TestPromptConstruction:
    """Prompts are built correctly from repo data."""

    def test_repo_summary_prompt_includes_name(self, sample_repo):
        prompt = REPO_SUMMARY_PROMPT.format(
            name=sample_repo.name,
            description=sample_repo.description,
            readme_excerpt=sample_repo.readme_text,
            commit_messages="\n".join(sample_repo.recent_commits),
        )
        assert "test-repo" in prompt
        assert "A test repository" in prompt

    def test_fork_diff_prompt_includes_upstream(self):
        prompt = FORK_DIFF_PROMPT.format(
            upstream_name="original/repo",
            upstream_description="The original project",
            diff_text="+ added new feature",
        )
        assert "original/repo" in prompt
        assert "added new feature" in prompt


class TestSummaryCache:
    """Cache stores and retrieves summaries by repo+SHA."""

    def test_cache_miss(self, tmp_path):
        cache = SummaryCache(tmp_path / "cache.json")
        assert cache.get("user/repo", "abc123") is None

    def test_cache_hit(self, tmp_path):
        cache = SummaryCache(tmp_path / "cache.json")
        cache.set("user/repo", "abc123", "A great project.")
        assert cache.get("user/repo", "abc123") == "A great project."

    def test_cache_invalidated_by_sha_change(self, tmp_path):
        cache = SummaryCache(tmp_path / "cache.json")
        cache.set("user/repo", "abc123", "Old summary.")
        assert cache.get("user/repo", "def456") is None

    def test_cache_persists_to_disk(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        cache1 = SummaryCache(cache_path)
        cache1.set("user/repo", "abc123", "Persisted.")

        cache2 = SummaryCache(cache_path)
        assert cache2.get("user/repo", "abc123") == "Persisted."

    def test_clear_all(self, tmp_path):
        cache = SummaryCache(tmp_path / "cache.json")
        cache.set("user/repo1", "aaa", "Summary 1")
        cache.set("user/repo2", "bbb", "Summary 2")
        cache.clear()
        assert cache.get("user/repo1", "aaa") is None
        assert cache.get("user/repo2", "bbb") is None

    def test_clear_single_repo(self, tmp_path):
        cache = SummaryCache(tmp_path / "cache.json")
        cache.set("user/repo1", "aaa", "Summary 1")
        cache.set("user/repo2", "bbb", "Summary 2")
        cache.clear(repo="user/repo1")
        assert cache.get("user/repo1", "aaa") is None
        assert cache.get("user/repo2", "bbb") == "Summary 2"


class TestSummarizeRepo:
    """AI summarization of repos."""

    @patch("folio.summarize.litellm.completion")
    def test_calls_litellm(self, mock_completion, sample_repo):
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="This is a great project. It does cool things."))]
        )
        result = summarize_repo(sample_repo, provider="anthropic", model="claude-sonnet-4-20250514")
        assert "great project" in result
        mock_completion.assert_called_once()

    @patch("folio.summarize.litellm.completion")
    def test_returns_empty_on_failure(self, mock_completion, sample_repo):
        mock_completion.side_effect = Exception("API error")
        result = summarize_repo(sample_repo, provider="anthropic", model="test")
        assert result == ""


class TestSummarizeForkDiff:
    """AI summarization of fork diffs."""

    @patch("folio.summarize.litellm.completion")
    def test_calls_litellm_with_diff(self, mock_completion):
        mock_completion.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="I added retry logic."))]
        )
        result = summarize_fork_diff(
            upstream_name="BerriAI/litellm",
            upstream_description="LLM proxy",
            diff_text="+ retry logic",
            provider="anthropic",
            model="test",
        )
        assert "retry" in result
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_summarize.py -v`

Expected: ImportError

- [ ] **Step 3: Implement summarize.py**

File: `folio/summarize.py`

```python
"""AI summarization and caching for Folio."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import litellm

if TYPE_CHECKING:
    from folio.github import GitHubData, RepoData

logger = logging.getLogger(__name__)


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


# ── Cache ───────────────────────────────────────────────


DEFAULT_CACHE_PATH = Path.home() / ".folio" / "cache.json"


class SummaryCache:
    """Simple JSON cache keyed by repo_full_name:head_sha."""

    def __init__(self, path: Path = DEFAULT_CACHE_PATH):
        self.path = Path(path)
        self._data: dict[str, dict] = {}
        self._load()

    def _load(self):
        if self.path.exists():
            try:
                self._data = json.loads(self.path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2))

    def get(self, repo_full_name: str, head_sha: str) -> str | None:
        entry = self._data.get(repo_full_name)
        if entry and entry.get("sha") == head_sha:
            return entry.get("summary")
        return None

    def set(self, repo_full_name: str, head_sha: str, summary: str):
        self._data[repo_full_name] = {"sha": head_sha, "summary": summary}
        self._save()

    def clear(self, repo: str | None = None):
        if repo:
            self._data.pop(repo, None)
        else:
            self._data = {}
        self._save()


# ── Summarization ───────────────────────────────────────


def _get_model_string(provider: str, model: str, base_url: str = "") -> str:
    """Build the LiteLLM model string."""
    if provider == "ollama":
        return f"ollama/{model}"
    if provider == "openrouter":
        return f"openrouter/{model}"
    # anthropic and openai are handled natively by litellm
    return model


def summarize_repo(
    repo: RepoData,
    provider: str,
    model: str,
    base_url: str = "",
) -> str:
    """Generate a 2-sentence summary for a repo."""
    prompt = REPO_SUMMARY_PROMPT.format(
        name=repo.name,
        description=repo.description or "No description",
        readme_excerpt=repo.readme_text[:2000],
        commit_messages="\n".join(repo.recent_commits),
    )

    model_str = _get_model_string(provider, model, base_url)

    try:
        kwargs = {"model": model_str, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}
        if base_url:
            kwargs["api_base"] = base_url
        response = litellm.completion(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("AI summarization failed for %s: %s", repo.name, e)
        return ""


def summarize_fork_diff(
    upstream_name: str,
    upstream_description: str,
    diff_text: str,
    provider: str,
    model: str,
    base_url: str = "",
) -> str:
    """Generate a summary of what the user changed in a fork."""
    prompt = FORK_DIFF_PROMPT.format(
        upstream_name=upstream_name,
        upstream_description=upstream_description or "No description",
        diff_text=diff_text[:3000],
    )

    model_str = _get_model_string(provider, model, base_url)

    try:
        kwargs = {"model": model_str, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}
        if base_url:
            kwargs["api_base"] = base_url
        response = litellm.completion(**kwargs)
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("AI fork diff summarization failed for %s: %s", upstream_name, e)
        return ""


# ── Enrichment ──────────────────────────────────────────


@dataclass
class EnrichedData:
    """GitHubData with AI summaries attached."""

    user: object  # UserProfile
    repos: list  # list[RepoData]
    stats: object  # StatsData
    summaries: dict[str, str] = field(default_factory=dict)
    fork_diffs: dict[str, str] = field(default_factory=dict)


def enrich_data(
    github_data: GitHubData,
    config: object,  # ProfileConfig
    fork_diff_texts: dict[str, str],
    cache: SummaryCache | None = None,
    no_ai: bool = False,
) -> EnrichedData:
    """Run AI summarization on all repos and return enriched data."""
    summaries: dict[str, str] = {}
    fork_diffs: dict[str, str] = {}

    if no_ai:
        return EnrichedData(
            user=github_data.user,
            repos=github_data.repos,
            stats=github_data.stats,
            summaries=summaries,
            fork_diffs=fork_diffs,
        )

    for repo in github_data.repos:
        # Check cache first (using repo name as a simple key — no SHA available here)
        # In practice, cli.py will resolve HEAD SHA before calling this
        cached = cache.get(repo.full_name, "latest") if cache else None
        if cached:
            summaries[repo.name] = cached
        else:
            summary = summarize_repo(
                repo,
                provider=config.ai.provider,
                model=config.ai.model,
                base_url=config.ai.base_url,
            )
            if summary:
                summaries[repo.name] = summary
                if cache:
                    cache.set(repo.full_name, "latest", summary)

        # Fork diff summary
        if repo.is_fork and repo.fork_parent and repo.name in fork_diff_texts:
            diff_text = fork_diff_texts[repo.name]
            if diff_text:
                fork_summary = summarize_fork_diff(
                    upstream_name=repo.fork_parent,
                    upstream_description=repo.description or "",
                    diff_text=diff_text,
                    provider=config.ai.provider,
                    model=config.ai.model,
                    base_url=config.ai.base_url,
                )
                if fork_summary:
                    fork_diffs[repo.name] = fork_summary

    return EnrichedData(
        user=github_data.user,
        repos=github_data.repos,
        stats=github_data.stats,
        summaries=summaries,
        fork_diffs=fork_diffs,
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_summarize.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add folio/summarize.py tests/test_summarize.py
git commit -m "feat: AI summarization with LiteLLM, caching, and enrichment pipeline"
```

---

## Task 6: Language Colors

**Files:**
- Create: `folio/colors.py`

- [ ] **Step 1: Create colors.py with GitHub language color map**

File: `folio/colors.py`

```python
"""GitHub language colors — subset of commonly used languages."""

# Sourced from https://github.com/github-linguist/linguist/blob/master/lib/linguist/languages.yml
LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5",
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#178600",
    "Ruby": "#701516",
    "PHP": "#4F5D95",
    "Swift": "#F05138",
    "Kotlin": "#A97BFF",
    "Scala": "#c22d40",
    "Shell": "#89e051",
    "Lua": "#000080",
    "Perl": "#0298c3",
    "R": "#198CE7",
    "Dart": "#00B4AB",
    "Elixir": "#6e4a7e",
    "Clojure": "#db5855",
    "Haskell": "#5e5086",
    "OCaml": "#3be133",
    "Zig": "#ec915c",
    "Nim": "#ffc200",
    "Julia": "#a270ba",
    "HTML": "#e34c26",
    "CSS": "#563d7c",
    "SCSS": "#c6538c",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Objective-C": "#438eff",
    "PowerShell": "#012456",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "Nix": "#7e7eff",
    "HCL": "#844FBA",
    "Terraform": "#5c4ee5",
}

DEFAULT_COLOR = "#8b8b8b"


def get_language_color(language: str) -> str:
    """Get the GitHub color for a language, with fallback."""
    return LANGUAGE_COLORS.get(language, DEFAULT_COLOR)


def get_accent_from_languages(languages: dict[str, float]) -> str:
    """Get accent color from the user's top language."""
    if not languages:
        return DEFAULT_COLOR
    top_lang = max(languages, key=languages.get)
    return get_language_color(top_lang)
```

- [ ] **Step 2: Commit**

```bash
git add folio/colors.py
git commit -m "feat: GitHub language color mapping for theme accent"
```

---

## Task 7: Render Module

**Files:**
- Create: `folio/render.py`, `tests/test_render.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_render.py`

```python
"""Tests for template rendering."""

import pytest
from datetime import datetime, timezone
from pathlib import Path

from folio.render import render_profile, render_readme, render_style
from folio.github import UserProfile, RepoData, StatsData
from folio.summarize import EnrichedData
from folio.config import load_config


@pytest.fixture
def enriched_data():
    return EnrichedData(
        user=UserProfile(
            login="testuser",
            name="Test User",
            avatar_url="https://example.com/avatar.png",
            bio="A test bio",
            followers=50,
            following=20,
        ),
        repos=[
            RepoData(
                name="public-project",
                full_name="testuser/public-project",
                description="A public project",
                language="Python",
                stars=10,
                last_updated=datetime(2026, 3, 1, tzinfo=timezone.utc),
                is_fork=False,
                is_private=False,
                fork_parent=None,
                private_reason=None,
                html_url="https://github.com/testuser/public-project",
                readme_text="# Public",
                recent_commits=["feat: stuff"],
            ),
            RepoData(
                name="private-project",
                full_name="testuser/private-project",
                description="Secret project",
                language="Go",
                stars=0,
                last_updated=datetime(2026, 2, 15, tzinfo=timezone.utc),
                is_fork=False,
                is_private=True,
                fork_parent=None,
                private_reason="Under NDA",
                html_url="https://github.com/testuser/private-project",
            ),
            RepoData(
                name="my-fork",
                full_name="testuser/my-fork",
                description="Forked project",
                language="TypeScript",
                stars=2,
                last_updated=datetime(2026, 3, 10, tzinfo=timezone.utc),
                is_fork=True,
                is_private=False,
                fork_parent="original/my-fork",
                private_reason=None,
                html_url="https://github.com/testuser/my-fork",
            ),
        ],
        stats=StatsData(
            commits=247,
            pull_requests=18,
            issues=34,
            streak_days=42,
            stars_earned=89,
            languages={"Python": 38.0, "Go": 22.0, "TypeScript": 18.0, "Shell": 12.0, "Rust": 10.0},
        ),
        summaries={
            "public-project": "A CLI that builds GitHub profiles. Uses Jinja2 for templating.",
            "private-project": "Internal admin panel for waiver workflows. Handles compliance reporting.",
            "my-fork": "",
        },
        fork_diffs={
            "my-fork": "I added retry logic for streaming responses.",
        },
    )


class TestRenderProfile:
    """HTML profile rendering."""

    def test_renders_valid_html(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        html = render_profile(enriched_data, config)
        assert "<!DOCTYPE html>" in html
        assert "Test User" in html
        assert "public-project" in html

    def test_includes_private_reason(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        html = render_profile(enriched_data, config)
        assert "Under NDA" in html

    def test_includes_fork_diff_summary(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        html = render_profile(enriched_data, config)
        assert "retry logic" in html

    def test_no_link_for_private_repos(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        html = render_profile(enriched_data, config)
        assert "github.com/testuser/private-project" not in html

    def test_link_for_public_repos(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        html = render_profile(enriched_data, config)
        assert "github.com/testuser/public-project" in html


class TestRenderReadme:
    """README.md rendering."""

    def test_renders_non_empty_markdown(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        md = render_readme(enriched_data, config)
        assert len(md) > 0
        assert "Generated by Folio" in md
        assert "Test User" in md


class TestRenderStyle:
    """CSS rendering with theme variables."""

    def test_renders_css(self, enriched_data, tmp_config):
        config = load_config(tmp_config)
        css = render_style(enriched_data, config)
        assert "font-family" in css
        assert len(css) > 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_render.py -v`

Expected: ImportError

- [ ] **Step 3: Implement render.py**

File: `folio/render.py`

```python
"""Jinja2 rendering engine for Folio."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from jinja2 import Environment, FileSystemLoader

from folio.colors import get_language_color, get_accent_from_languages

if TYPE_CHECKING:
    from folio.config import ProfileConfig
    from folio.summarize import EnrichedData

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _build_env() -> Environment:
    """Create Jinja2 environment with template directory."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["lang_color"] = get_language_color
    env.globals["now"] = datetime.now(timezone.utc)
    return env


def _build_context(data: EnrichedData, config: ProfileConfig) -> dict:
    """Build the template context from enriched data and config."""
    # Resolve accent color
    accent = config.theme.accent
    if accent == "auto":
        accent = get_accent_from_languages(data.stats.languages)

    # Resolve avatar
    avatar = config.profile.avatar or data.user.avatar_url

    # Resolve bio
    bio = data.user.bio or ""

    return {
        "user": data.user,
        "profile": config.profile,
        "repos": data.repos,
        "stats": data.stats,
        "summaries": data.summaries,
        "fork_diffs": data.fork_diffs,
        "theme": config.theme.name,
        "accent": accent,
        "avatar": avatar,
        "bio": bio,
        "stats_range": config.stats.range,
        "stats_show": config.stats.show,
        "generated_at": datetime.now(timezone.utc).strftime("%b %-d, %Y"),
        "lang_color": get_language_color,
    }


def render_profile(data: EnrichedData, config: ProfileConfig) -> str:
    """Render the full HTML profile page."""
    env = _build_env()
    template = env.get_template("profile.html.j2")
    return template.render(**_build_context(data, config))


def render_style(data: EnrichedData, config: ProfileConfig) -> str:
    """Render the CSS stylesheet with theme variables."""
    env = _build_env()
    template = env.get_template("style.css.j2")
    return template.render(**_build_context(data, config))


def render_readme(data: EnrichedData, config: ProfileConfig) -> str:
    """Render the README.md for the GitHub profile."""
    env = _build_env()
    template = env.get_template("readme.md.j2")
    return template.render(**_build_context(data, config))


def render_svg(template_name: str, data: EnrichedData, config: ProfileConfig) -> str:
    """Render an SVG component template."""
    env = _build_env()
    template = env.get_template(f"components/{template_name}")
    return template.render(**_build_context(data, config))
```

- [ ] **Step 4: Create skeleton templates so render tests pass**

Create minimal templates that the tests need. These will be fully implemented in Tasks 8 and 9.

File: `templates/profile.html.j2`

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{ profile.name }}</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<div class="page">
  <section class="hero">
    <h1>{{ profile.name }}</h1>
    <p class="tagline">{{ profile.tagline }}</p>
  </section>
  <section class="projects">
    {% for repo in repos %}
    <div class="project">
      <span class="project-name">
        {% if not repo.is_private %}
        <a href="{{ repo.html_url }}">{{ repo.name }}</a>
        {% else %}
        {{ repo.name }}
        {% endif %}
      </span>
      {% if summaries.get(repo.name) %}
      <p class="project-summary">{{ summaries[repo.name] }}</p>
      {% endif %}
      {% if repo.is_private and repo.private_reason %}
      <p class="project-private">{{ repo.private_reason }}</p>
      {% endif %}
      {% if repo.is_fork and fork_diffs.get(repo.name) %}
      <p class="fork-diff">{{ fork_diffs[repo.name] }}</p>
      {% endif %}
    </div>
    {% endfor %}
  </section>
</div>
</body>
</html>
```

File: `templates/style.css.j2`

```css
:root {
  --bg: #151519;
  --fg: #e0e0e6;
  --accent: {{ accent }};
  --mono: 'JetBrains Mono', ui-monospace, monospace;
  --sans: 'DM Sans', system-ui, sans-serif;
}

body {
  background: var(--bg);
  color: var(--fg);
  font-family: var(--mono);
}
```

File: `templates/readme.md.j2`

```
<!-- Generated by Folio. Do not edit manually. -->

# {{ profile.name }}

{{ profile.tagline }}
```

- [ ] **Step 5: Create templates/components/ directory with empty files**

```bash
mkdir -p templates/components
touch templates/components/hero.svg.j2
touch templates/components/stats_card.svg.j2
touch templates/components/language_chart.svg.j2
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_render.py -v`

Expected: All tests PASS

- [ ] **Step 7: Commit**

```bash
git add folio/render.py tests/test_render.py templates/
git commit -m "feat: Jinja2 render engine with skeleton templates"
```

---

## Task 8: Push Module

**Files:**
- Create: `folio/push.py`, `tests/test_push.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_push.py`

```python
"""Tests for git push operations."""

import pytest
from unittest.mock import patch, MagicMock, call
from folio.push import push_profile


class TestPushProfile:
    """Commit and push generated files."""

    @patch("folio.push.Repo")
    def test_stages_correct_files(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        push_profile("/fake/repo")

        # Should stage README.md and dist/
        mock_repo.index.add.assert_called_once()
        added_files = mock_repo.index.add.call_args[0][0]
        assert "README.md" in added_files
        assert "dist" in added_files

    @patch("folio.push.Repo")
    def test_commit_message_format(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        push_profile("/fake/repo")

        commit_msg = mock_repo.index.commit.call_args[0][0]
        assert commit_msg.startswith("folio: regenerate profile")

    @patch("folio.push.Repo")
    def test_pushes_to_origin(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        push_profile("/fake/repo")

        mock_repo.remotes.origin.push.assert_called_once()

    @patch("folio.push.Repo")
    def test_no_force_push(self, mock_repo_cls):
        mock_repo = MagicMock()
        mock_repo_cls.return_value = mock_repo

        push_profile("/fake/repo")

        push_call = mock_repo.remotes.origin.push
        push_call.assert_called_once()
        # Ensure no force flag
        args, kwargs = push_call.call_args
        assert kwargs.get("force", False) is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_push.py -v`

Expected: ImportError

- [ ] **Step 3: Implement push.py**

File: `folio/push.py`

```python
"""Git commit and push for Folio."""

from __future__ import annotations

from datetime import datetime, timezone

from git import Repo


def push_profile(repo_path: str) -> None:
    """Stage README.md and dist/, commit, and push to origin."""
    repo = Repo(repo_path)

    # Stage files
    repo.index.add(["README.md", "dist"])

    # Commit
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo.index.commit(f"folio: regenerate profile {timestamp}")

    # Push (no force)
    repo.remotes.origin.push(force=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_push.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add folio/push.py tests/test_push.py
git commit -m "feat: push module for commit and push to origin"
```

---

## Task 9: CLI Module

**Files:**
- Create: `folio/cli.py`, `tests/test_cli.py`

- [ ] **Step 1: Write failing tests**

File: `tests/test_cli.py`

```python
"""Tests for CLI commands."""

import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from pathlib import Path

from folio.cli import app

runner = CliRunner()


class TestGenerate:
    """folio generate command."""

    @patch("folio.cli.push_profile")
    @patch("folio.cli.render_readme")
    @patch("folio.cli.render_style")
    @patch("folio.cli.render_profile")
    @patch("folio.cli.enrich_data")
    @patch("folio.cli.fetch_github_data")
    @patch("folio.cli.load_config")
    def test_generate_no_ai(
        self, mock_load, mock_fetch, mock_enrich, mock_render_html,
        mock_render_css, mock_render_readme, mock_push, tmp_path
    ):
        # Setup
        config_path = tmp_path / ".profile.yml"
        config_path.write_text("profile:\n  name: Test\n  tagline: Test\n  location: ''\n  resume_url: ''\n  avatar: ''\n  social: {twitter: '', linkedin: '', website: ''}\nai:\n  provider: anthropic\n  model: test\n  base_url: ''\nrepos:\n  include: []\n  exclude: []\n  forks: {show: true, summarize_diff: true}\nstats:\n  range: 3mo\n  show: [commits]\n  language_count: 6\ntheme:\n  name: dark\n  accent: auto\n")

        mock_load.return_value = MagicMock()
        mock_fetch.return_value = MagicMock()
        mock_enrich.return_value = MagicMock()
        mock_render_html.return_value = "<html>test</html>"
        mock_render_css.return_value = "body { color: red; }"
        mock_render_readme.return_value = "# Test"

        result = runner.invoke(app, ["generate", "--config", str(config_path), "--no-ai"])
        assert result.exit_code == 0

    @patch("folio.cli.push_profile")
    @patch("folio.cli.render_readme")
    @patch("folio.cli.render_style")
    @patch("folio.cli.render_profile")
    @patch("folio.cli.enrich_data")
    @patch("folio.cli.fetch_github_data")
    @patch("folio.cli.load_config")
    def test_generate_with_push(
        self, mock_load, mock_fetch, mock_enrich, mock_render_html,
        mock_render_css, mock_render_readme, mock_push, tmp_path
    ):
        config_path = tmp_path / ".profile.yml"
        config_path.write_text("profile:\n  name: Test\n  tagline: Test\n  location: ''\n  resume_url: ''\n  avatar: ''\n  social: {twitter: '', linkedin: '', website: ''}\nai:\n  provider: anthropic\n  model: test\n  base_url: ''\nrepos:\n  include: []\n  exclude: []\n  forks: {show: true, summarize_diff: true}\nstats:\n  range: 3mo\n  show: [commits]\n  language_count: 6\ntheme:\n  name: dark\n  accent: auto\n")

        mock_load.return_value = MagicMock()
        mock_fetch.return_value = MagicMock()
        mock_enrich.return_value = MagicMock()
        mock_render_html.return_value = "<html>test</html>"
        mock_render_css.return_value = "body { color: red; }"
        mock_render_readme.return_value = "# Test"

        result = runner.invoke(app, ["generate", "--config", str(config_path), "--no-ai", "--push"])
        assert result.exit_code == 0
        mock_push.assert_called_once()


class TestCacheClear:
    """folio cache clear command."""

    @patch("folio.cli.SummaryCache")
    def test_cache_clear_all(self, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache_cls.return_value = mock_cache

        result = runner.invoke(app, ["cache", "clear"])
        assert result.exit_code == 0
        mock_cache.clear.assert_called_once_with(repo=None)

    @patch("folio.cli.SummaryCache")
    def test_cache_clear_single_repo(self, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache_cls.return_value = mock_cache

        result = runner.invoke(app, ["cache", "clear", "--repo", "user/my-repo"])
        assert result.exit_code == 0
        mock_cache.clear.assert_called_once_with(repo="user/my-repo")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_cli.py -v`

Expected: ImportError

- [ ] **Step 3: Implement cli.py**

File: `folio/cli.py`

```python
"""Folio CLI — generate your GitHub profile page."""

from __future__ import annotations

import difflib
import http.server
import os
import socketserver
import threading
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from folio.config import load_config
from folio.github import fetch_github_data
from folio.git import get_fork_diff
from folio.summarize import enrich_data, SummaryCache
from folio.render import render_profile, render_readme, render_style, render_svg
from folio.push import push_profile

app = typer.Typer(help="Generate a spectacular GitHub profile page.")
cache_app = typer.Typer(help="Manage AI summary cache.")
app.add_typer(cache_app, name="cache")

console = Console()

# ── Defaults ────────────────────────────────────────────

DEFAULT_CONFIG = ".profile.yml"
DIST_DIR = "dist"


# ── Commands ────────────────────────────────────────────


@app.command()
def generate(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", help="Path to .profile.yml"),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI summarization"),
    push: bool = typer.Option(False, "--push", help="Commit and push after generating"),
    verbose: bool = typer.Option(False, "--verbose", help="Show detailed progress"),
    theme: Optional[str] = typer.Option(None, "--theme", help="Override theme from config"),
):
    """Fetch data, run AI summaries, render and write profile."""
    config_path = Path(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # 1. Load config
        task = progress.add_task("Loading config...", total=None)
        cfg = load_config(config_path)
        if theme:
            cfg.theme.name = theme
        progress.update(task, description="Config loaded", completed=True)

        # 2. Fetch GitHub data
        task = progress.add_task("Fetching GitHub data...", total=None)
        github_data = fetch_github_data(cfg)
        progress.update(task, description=f"Fetched {len(github_data.repos)} repos", completed=True)

        # 3. Get fork diffs
        fork_diffs: dict[str, str] = {}
        if cfg.repos.forks.summarize_diff:
            fork_repos = [r for r in github_data.repos if r.is_fork]
            if fork_repos:
                task = progress.add_task("Analyzing forks...", total=None)
                for repo in fork_repos:
                    # Fork diffs require the repo to be cloned locally
                    local_path = Path.cwd() / repo.name
                    if local_path.exists():
                        diff = get_fork_diff(str(local_path))
                        if diff:
                            fork_diffs[repo.name] = diff
                progress.update(task, description=f"Analyzed {len(fork_diffs)} forks", completed=True)

        # 4. AI summarization
        cache = SummaryCache()
        task = progress.add_task("Summarizing repos...", total=None)
        enriched = enrich_data(github_data, cfg, fork_diffs, cache=cache, no_ai=no_ai)
        summary_count = len(enriched.summaries)
        progress.update(task, description=f"Generated {summary_count} summaries", completed=True)

        # 5. Render
        task = progress.add_task("Rendering templates...", total=None)
        html = render_profile(enriched, cfg)
        css = render_style(enriched, cfg)
        readme = render_readme(enriched, cfg)
        progress.update(task, description="Templates rendered", completed=True)

        # 6. Write output
        task = progress.add_task("Writing output...", total=None)
        dist = Path(DIST_DIR)
        dist.mkdir(parents=True, exist_ok=True)

        (dist / "index.html").write_text(html)
        (dist / "style.css").write_text(css)
        Path("README.md").write_text(readme)

        # Render SVG components for README
        for svg_name in ["hero.svg.j2", "stats_card.svg.j2", "language_chart.svg.j2"]:
            svg_path = Path("templates") / "components" / svg_name
            if svg_path.exists() and svg_path.read_text().strip():
                svg_content = render_svg(svg_name, enriched, cfg)
                out_name = svg_name.replace(".j2", "")
                (dist / out_name).write_text(svg_content)

        progress.update(task, description="Output written", completed=True)

    console.print(f"\n[green]✓[/green] Profile generated")
    console.print(f"  README.md  → ./README.md")
    console.print(f"  HTML site  → ./{DIST_DIR}/index.html")

    # 7. Push if requested
    if push:
        console.print("\nPushing to origin...")
        push_profile(str(Path.cwd()))
        console.print("[green]✓[/green] Pushed to origin")


@app.command()
def init(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", help="Path to write .profile.yml"),
):
    """Interactive setup wizard for .profile.yml."""
    console.print("[bold]Folio Setup[/bold]\n")

    name = typer.prompt("Your name")
    tagline = typer.prompt("Tagline (one-liner about you)")
    location = typer.prompt("Location", default="")
    resume_url = typer.prompt("Resume URL", default="")

    twitter = typer.prompt("Twitter/X handle", default="")
    linkedin = typer.prompt("LinkedIn username", default="")
    website = typer.prompt("Personal website URL", default="")

    console.print("\n[bold]AI Provider[/bold]")
    provider = typer.prompt("Provider (anthropic/openai/ollama/openrouter)", default="anthropic")
    model = typer.prompt("Model", default="claude-sonnet-4-20250514")
    base_url = ""
    if provider == "ollama":
        base_url = typer.prompt("Ollama base URL", default="http://localhost:11434")

    stats_range = typer.prompt("Stats time range (1mo/3mo/1yr/alltime)", default="3mo")
    theme_name = typer.prompt("Theme (dark/light/auto)", default="dark")

    config_text = f"""profile:
  name: "{name}"
  tagline: "{tagline}"
  location: "{location}"
  resume_url: "{resume_url}"
  avatar: ""
  social:
    twitter: "{twitter}"
    linkedin: "{linkedin}"
    website: "{website}"

ai:
  provider: {provider}
  model: {model}
  base_url: "{base_url}"

repos:
  include: []
  exclude: []
  forks:
    show: true
    summarize_diff: true

stats:
  range: {stats_range}
  show:
    - commits
    - pull_requests
    - issues
    - streak
    - top_languages
    - stars_earned
  language_count: 6

theme:
  name: {theme_name}
  accent: auto
"""

    # Validate before writing
    import yaml
    from folio.config import ProfileConfig
    raw = yaml.safe_load(config_text)
    ProfileConfig(**raw)  # Will raise on invalid input

    Path(config).write_text(config_text)
    console.print(f"\n[green]✓[/green] Config written to {config}")
    console.print("  Edit the [bold]repos.include[/bold] list to add your repos, then run [bold]folio generate[/bold]")


@app.command()
def preview(
    port: int = typer.Option(8000, "--port", help="Port to serve on"),
):
    """Serve the generated site locally."""
    dist = Path(DIST_DIR)
    if not dist.exists():
        console.print("[red]No dist/ directory found.[/red] Run [bold]folio generate[/bold] first.")
        raise typer.Exit(1)

    handler = http.server.SimpleHTTPRequestHandler
    os.chdir(dist)
    with socketserver.TCPServer(("", port), handler) as httpd:
        console.print(f"Serving at [bold]http://localhost:{port}[/bold]")
        console.print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\nStopped.")


@app.command()
def status(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", help="Path to .profile.yml"),
):
    """Show what would change without generating."""
    config_path = Path(config)
    cfg = load_config(config_path)
    github_data = fetch_github_data(cfg)
    enriched = enrich_data(github_data, cfg, {}, no_ai=True)

    new_readme = render_readme(enriched, cfg)
    current_readme = ""
    if Path("README.md").exists():
        current_readme = Path("README.md").read_text()

    if new_readme == current_readme:
        console.print("[green]No changes[/green] — README.md is up to date")
    else:
        diff = difflib.unified_diff(
            current_readme.splitlines(keepends=True),
            new_readme.splitlines(keepends=True),
            fromfile="README.md (current)",
            tofile="README.md (generated)",
        )
        console.print("".join(diff))


@cache_app.command("clear")
def cache_clear(
    repo: Optional[str] = typer.Option(None, "--repo", help="Clear cache for a specific repo"),
):
    """Clear the AI summary cache."""
    cache = SummaryCache()
    cache.clear(repo=repo)
    if repo:
        console.print(f"[green]✓[/green] Cleared cache for {repo}")
    else:
        console.print("[green]✓[/green] All cache cleared")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_cli.py -v`

Expected: All tests PASS

- [ ] **Step 5: Verify CLI entry point works**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && folio --help`

Expected: Shows help text with available commands

- [ ] **Step 6: Commit**

```bash
git add folio/cli.py tests/test_cli.py
git commit -m "feat: CLI with generate, init, preview, status, and cache commands"
```

---

## Task 10: HTML Profile Template (Dark Theme)

**Files:**
- Modify: `templates/profile.html.j2`
- Modify: `templates/style.css.j2`

This is a core visual deliverable. Use the **frontend-design skill** when implementing.

Reference: `.superpowers/brainstorm/30352-1775349518/content/profile-direction-v3.html` — the approved mockup.

Reference: Design spec Section 7 — all visual rules.

**Critical design rules:**
- Monospace-first (JetBrains Mono for structure, DM Sans for prose only)
- Dark: bg `#151519`, text `#e0e0e6`, bright `#f5f5f8`, dim `#888899`, borders `#303040`
- Light: warm white base, same restraint
- Auto: `prefers-color-scheme` media query
- No gradients, no rounded corners, no shadows, no hover-lift
- Section headers: `// SECTION NAME` format, accent-colored `//`
- One animation: blinking cursor on tagline
- Left-aligned hero, projects as rows not cards
- No CDN deps, zero JS, fonts via `@font-face` with woff2 in `dist/fonts/`
- Mobile responsive
- **Do NOT produce generic AI aesthetics**

- [ ] **Step 1: Download font files**

Run:
```bash
mkdir -p /Users/joemc3/tmp/folio/folio/static/fonts
cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -c "
import httpx, re, os

fonts_dir = 'folio/static/fonts'
os.makedirs(fonts_dir, exist_ok=True)

# Fetch JetBrains Mono (Regular, SemiBold, Bold)
for weight in ['400', '600', '700']:
    css_url = f'https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@{weight}&display=swap'
    css = httpx.get(css_url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}).text
    urls = re.findall(r'url\((https://[^)]+\.woff2)\)', css)
    for url in urls[:1]:  # Take latin subset only
        data = httpx.get(url).content
        fname = f'jetbrains-mono-{weight}.woff2'
        with open(f'{fonts_dir}/{fname}', 'wb') as f:
            f.write(data)
        print(f'Downloaded {fname} ({len(data)} bytes)')

# Fetch DM Sans (Regular, Medium)
for weight in ['400', '500']:
    css_url = f'https://fonts.googleapis.com/css2?family=DM+Sans:wght@{weight}&display=swap'
    css = httpx.get(css_url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'}).text
    urls = re.findall(r'url\((https://[^)]+\.woff2)\)', css)
    for url in urls[:1]:
        data = httpx.get(url).content
        fname = f'dm-sans-{weight}.woff2'
        with open(f'{fonts_dir}/{fname}', 'wb') as f:
            f.write(data)
        print(f'Downloaded {fname} ({len(data)} bytes)')
"
```

Expected: Font files downloaded to `folio/static/fonts/`

- [ ] **Step 2: Implement full profile.html.j2**

Replace `templates/profile.html.j2` with the full template. This must match the approved visual direction from the mockup. The template receives the context variables defined in `render.py:_build_context()`.

The implementing agent MUST invoke the **frontend-design skill** before writing this template. Full template code is intentionally not provided here — this is a creative visual deliverable that must be crafted using the mockup as reference, not copied from a plan. The HTML must include all five sections (hero, about, projects, stats, footer), all three repo variants (public/private/fork), the blinking cursor animation, and responsive layout.

Key template variables available:
- `user` (UserProfile), `profile` (ProfileSection), `repos` (list[RepoData])
- `stats` (StatsData), `summaries` (dict), `fork_diffs` (dict)
- `theme` (str), `accent` (str hex), `avatar` (str url), `bio` (str)
- `stats_range` (str), `stats_show` (list[str]), `generated_at` (str)
- `lang_color` (callable: language name → hex color string)

- [ ] **Step 3: Implement full style.css.j2**

Replace `templates/style.css.j2` with complete CSS. Must include:
- `@font-face` declarations for all woff2 files (paths relative to `dist/`)
- CSS custom properties for dark theme
- `@media (prefers-color-scheme: light)` block for light theme
- `.theme-light` class override for explicit light mode
- All component styles matching the approved mockup
- `@keyframes blink` for cursor
- Mobile responsive breakpoints

- [ ] **Step 4: Update cli.py to copy font files to dist/**

Add to the "Write output" section of `generate()` in `cli.py`:

```python
# Copy font files to dist/
fonts_src = Path(__file__).parent / "static" / "fonts"
fonts_dst = dist / "fonts"
fonts_dst.mkdir(parents=True, exist_ok=True)
if fonts_src.exists():
    import shutil
    for font_file in fonts_src.glob("*.woff2"):
        shutil.copy2(font_file, fonts_dst / font_file.name)
```

- [ ] **Step 5: Run all tests**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/ -v`

Expected: All tests PASS

- [ ] **Step 6: Manual visual check**

Run:
```bash
cd /Users/joemc3/tmp/folio && source .venv/bin/activate
folio generate --config tests/fixtures/sample_config.yml --no-ai 2>/dev/null || true
# Open dist/index.html in browser to visually verify
```

- [ ] **Step 7: Commit**

```bash
git add templates/ folio/static/ folio/cli.py
git commit -m "feat: full HTML profile template with dark/light/auto themes"
```

---

## Task 11: README & SVG Templates

**Files:**
- Modify: `templates/readme.md.j2`
- Modify: `templates/components/hero.svg.j2`
- Modify: `templates/components/stats_card.svg.j2`
- Modify: `templates/components/language_chart.svg.j2`

**SVG constraints (GitHub):**
- No external fonts — use system mono: `ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace`
- No `<foreignObject>`, no `@import`, no external CSS
- Inline styles only
- No animations (GitHub strips them)
- GitHub wraps SVGs — use `viewBox` for sizing, not fixed width/height

- [ ] **Step 1: Implement hero.svg.j2**

File: `templates/components/hero.svg.j2`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 200" fill="none">
  <rect width="800" height="200" rx="0" fill="#151519"/>
  <text x="40" y="60" font-family="ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace" font-size="28" font-weight="700" fill="#f5f5f8">{{ profile.name }}</text>
  <text x="40" y="90" font-family="ui-monospace, 'Cascadia Code', 'Source Code Pro', Menlo, Consolas, monospace" font-size="14" fill="#e0e0e6">{{ profile.tagline }}</text>
  <line x1="40" y1="110" x2="760" y2="110" stroke="{{ accent }}" stroke-width="1" opacity="0.4"/>
  {% if "commits" in stats_show %}
  <text x="40" y="145" font-family="ui-monospace, monospace" font-size="24" font-weight="700" fill="#f5f5f8">{{ stats.commits }}</text>
  <text x="40" y="165" font-family="ui-monospace, monospace" font-size="10" fill="#888899" letter-spacing="1">COMMITS</text>
  {% endif %}
  {% if "pull_requests" in stats_show %}
  <text x="180" y="145" font-family="ui-monospace, monospace" font-size="24" font-weight="700" fill="#f5f5f8">{{ stats.pull_requests }}</text>
  <text x="180" y="165" font-family="ui-monospace, monospace" font-size="10" fill="#888899" letter-spacing="1">PULL REQUESTS</text>
  {% endif %}
  {% if "streak" in stats_show %}
  <text x="360" y="145" font-family="ui-monospace, monospace" font-size="24" font-weight="700" fill="#f5f5f8">{{ stats.streak_days }}d</text>
  <text x="360" y="165" font-family="ui-monospace, monospace" font-size="10" fill="#888899" letter-spacing="1">STREAK</text>
  {% endif %}
</svg>
```

- [ ] **Step 2: Implement language_chart.svg.j2**

File: `templates/components/language_chart.svg.j2`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 60" fill="none">
  <!-- Language bar -->
  {% set bar_width = 720 %}
  {% set bar_x = 40 %}
  {% set bar_y = 10 %}
  {% set bar_h = 4 %}
  {% set offset = [0] %}
  {% for lang, pct in stats.languages.items() %}
  {% set seg_width = (pct / 100 * bar_width) | round | int %}
  <rect x="{{ bar_x + offset[0] }}" y="{{ bar_y }}" width="{{ seg_width }}" height="{{ bar_h }}" fill="{{ lang_color(lang) }}"/>
  {% if offset.append(offset.pop() + seg_width + 2) %}{% endif %}
  {% endfor %}
  <!-- Legend -->
  {% set lx = [40] %}
  {% for lang, pct in stats.languages.items() %}
  <rect x="{{ lx[0] }}" y="28" width="8" height="8" fill="{{ lang_color(lang) }}"/>
  <text x="{{ lx[0] + 12 }}" y="36" font-family="ui-monospace, monospace" font-size="11" fill="#888899">{{ lang }} {{ pct }}%</text>
  {% if lx.append(lx.pop() + (lang | length + (pct | string | length) + 2) * 7 + 24) %}{% endif %}
  {% endfor %}
</svg>
```

- [ ] **Step 3: Implement stats_card.svg.j2**

File: `templates/components/stats_card.svg.j2`

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 10" fill="none">
  <line x1="40" y1="5" x2="760" y2="5" stroke="{{ accent }}" stroke-width="1" opacity="0.3"/>
</svg>
```

- [ ] **Step 4: Implement readme.md.j2**

File: `templates/readme.md.j2`

```markdown
<!-- Generated by Folio. Do not edit manually. -->

<a href="https://{{ user.login }}.github.io">
  <img src="dist/hero.svg" alt="{{ profile.name }}" width="800">
</a>

<img src="dist/stats_card.svg" alt="" width="800">

<a href="https://{{ user.login }}.github.io">
  <img src="dist/language_chart.svg" alt="Languages" width="800">
</a>

<br>

**[→ Full Profile](https://{{ user.login }}.github.io)**
```

- [ ] **Step 5: Run render tests**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_render.py -v`

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add templates/
git commit -m "feat: README and SVG templates for GitHub profile card"
```

---

## Task 12: .profile.yml.example & FOLIO.md

**Files:**
- Create: `.profile.yml.example`, `FOLIO.md`

- [ ] **Step 1: Create .profile.yml.example**

File: `.profile.yml.example`

```yaml
# Folio — .profile.yml
# Copy this to .profile.yml and customize. Never commit .profile.yml directly.

profile:
  name: "Your Name"
  tagline: "What you do in one line"
  location: ""
  resume_url: ""
  avatar: ""              # Leave blank to use your GitHub avatar
  social:
    twitter: ""
    linkedin: ""
    website: ""

ai:
  provider: anthropic     # anthropic | openai | ollama | openrouter
  model: claude-sonnet-4-20250514
  base_url: ""            # Required for ollama (e.g. http://localhost:11434)
  # API key comes from environment variable — never store it here.
  # ANTHROPIC_API_KEY | OPENAI_API_KEY | OPENROUTER_API_KEY | ollama needs no key

repos:
  # List repos to include on your profile. If omitted, defaults to all public repos.
  include:
    - name: my-cool-project
    - name: private-work
      private_reason: "Under NDA"   # Shown instead of a link
    # - name: my-fork             # Forks get automatic "what I changed" summaries
  exclude:
    - old-project-to-hide
  forks:
    show: true
    summarize_diff: true

stats:
  range: 3mo              # 1mo | 3mo | 1yr | alltime
  show:
    - commits
    - pull_requests
    - issues
    - streak
    - top_languages
    - stars_earned
  language_count: 6

theme:
  name: dark              # dark | light | auto
  accent: auto            # auto = derived from your top language | or hex like "#e8b84a"
```

- [ ] **Step 2: Create FOLIO.md**

File: `FOLIO.md`

```markdown
# Folio

Generate a spectacular GitHub profile page from your local machine.

## What Is This?

Folio is a CLI tool that builds your GitHub profile page. This repo **is** your profile repo — fork it, configure it, run `folio generate`, and push. Your README.md and a full HTML profile site are generated from your GitHub data and AI-powered summaries.

## Quick Start

1. Fork this repo and rename it to `yourusername/yourusername`
2. Clone it locally
3. Install: `pip install -e .`
4. Run the setup wizard: `folio init`
5. Edit `.profile.yml` to add your repos
6. Generate your profile: `folio generate`
7. Push: `git push`
8. (Optional) Enable GitHub Pages on the repo for the full HTML site

## Commands

| Command | What it does |
|---|---|
| `folio init` | Interactive setup wizard — creates `.profile.yml` |
| `folio generate` | Fetch GitHub data, run AI summaries, write README.md and dist/ |
| `folio preview` | Serve the generated HTML site locally |
| `folio status` | Show what would change without generating |
| `folio cache clear` | Clear the AI summary cache |

### Flags

| Flag | Description |
|---|---|
| `--config PATH` | Custom config file path (default: `.profile.yml`) |
| `--no-ai` | Skip AI summarization |
| `--push` | Commit and push after generating |
| `--verbose` | Detailed progress output |
| `--theme THEME` | Override the theme (dark/light/auto) |

## Configuration

Copy `.profile.yml.example` to `.profile.yml` and customize. The config file is gitignored — it contains your personal preferences and is never committed.

See `.profile.yml.example` for all options and documentation.

## AI Providers

Folio uses [LiteLLM](https://github.com/BerriAI/litellm) to support multiple AI providers. Set your provider and model in `.profile.yml`, and your API key as an environment variable:

- **Anthropic**: `export ANTHROPIC_API_KEY=sk-ant-...`
- **OpenAI**: `export OPENAI_API_KEY=sk-...`
- **OpenRouter**: `export OPENROUTER_API_KEY=sk-or-...`
- **Ollama**: No key needed — set `base_url` to your Ollama instance

## How Repos Work

- **Public repos** show a summary and a link to GitHub
- **Private repos** show a summary and a reason (e.g. "Under NDA") — no link
- **Forks** show what the upstream project does and what you changed
- All repos are opt-in via the `include` list (or default to all public repos)
- Use `exclude` to hide specific repos

## License

MIT
```

- [ ] **Step 3: Commit**

```bash
git add .profile.yml.example FOLIO.md
git commit -m "docs: add .profile.yml.example and FOLIO.md"
```

---

## Task 13: End-to-End Smoke Test

**Files:**
- Create: `tests/test_smoke.py`

- [ ] **Step 1: Write smoke test**

File: `tests/test_smoke.py`

```python
"""End-to-end smoke test for folio generate."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from datetime import datetime, timezone
from typer.testing import CliRunner

from folio.cli import app
from folio.github import UserProfile, RepoData, StatsData, GitHubData

runner = CliRunner()


@pytest.fixture
def mock_github_data():
    return GitHubData(
        user=UserProfile(
            login="smoketest",
            name="Smoke Test",
            avatar_url="https://example.com/avatar.png",
            bio="Testing the pipeline",
            followers=10,
            following=5,
        ),
        repos=[
            RepoData(
                name="public-repo",
                full_name="smoketest/public-repo",
                description="A test repo",
                language="Python",
                stars=5,
                last_updated=datetime(2026, 3, 1, tzinfo=timezone.utc),
                is_fork=False,
                is_private=False,
                fork_parent=None,
                private_reason=None,
                html_url="https://github.com/smoketest/public-repo",
                readme_text="# Test\nA test repo.",
                recent_commits=["feat: add stuff"],
            ),
            RepoData(
                name="private-repo",
                full_name="smoketest/private-repo",
                description="Secret",
                language="Go",
                stars=0,
                last_updated=datetime(2026, 2, 1, tzinfo=timezone.utc),
                is_fork=False,
                is_private=True,
                fork_parent=None,
                private_reason="Under NDA",
                html_url="https://github.com/smoketest/private-repo",
            ),
        ],
        stats=StatsData(
            commits=100,
            pull_requests=8,
            issues=12,
            streak_days=21,
            stars_earned=5,
            languages={"Python": 60.0, "Go": 40.0},
        ),
    )


class TestSmoke:
    """Full pipeline with mocked GitHub, no AI."""

    @patch("folio.cli.fetch_github_data")
    def test_generate_no_ai_writes_files(self, mock_fetch, mock_github_data, tmp_path, monkeypatch):
        # Set up working directory
        monkeypatch.chdir(tmp_path)

        # Write config
        config_path = tmp_path / ".profile.yml"
        fixtures = Path(__file__).parent / "fixtures"
        config_path.write_text((fixtures / "sample_config.yml").read_text())

        mock_fetch.return_value = mock_github_data

        result = runner.invoke(app, ["generate", "--config", str(config_path), "--no-ai"])

        # Check exit code
        assert result.exit_code == 0, f"CLI failed: {result.output}"

        # Check README.md was written
        readme = tmp_path / "README.md"
        assert readme.exists(), "README.md not created"
        readme_text = readme.read_text()
        assert len(readme_text) > 0, "README.md is empty"
        assert "Generated by Folio" in readme_text

        # Check dist/ was created
        dist = tmp_path / "dist"
        assert dist.exists(), "dist/ not created"
        assert (dist / "index.html").exists(), "index.html not created"

        html = (dist / "index.html").read_text()
        assert "<!DOCTYPE html>" in html
        assert "Smoke Test" in html or "Test User" in html

    @patch("folio.cli.fetch_github_data")
    def test_private_repo_no_link_in_html(self, mock_fetch, mock_github_data, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config_path = tmp_path / ".profile.yml"
        fixtures = Path(__file__).parent / "fixtures"
        config_path.write_text((fixtures / "sample_config.yml").read_text())
        mock_fetch.return_value = mock_github_data

        runner.invoke(app, ["generate", "--config", str(config_path), "--no-ai"])

        html = (tmp_path / "dist" / "index.html").read_text()
        assert "github.com/smoketest/private-repo" not in html
```

- [ ] **Step 2: Run smoke test**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/test_smoke.py -v`

Expected: All tests PASS

- [ ] **Step 3: Run full test suite**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/ -v`

Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_smoke.py
git commit -m "test: end-to-end smoke test for generate pipeline"
```

---

## Task 14: Final Polish

- [ ] **Step 1: Run the full test suite one final time**

Run: `cd /Users/joemc3/tmp/folio && source .venv/bin/activate && python -m pytest tests/ -v --tb=short`

Expected: All tests PASS

- [ ] **Step 2: Test the actual CLI**

Run:
```bash
cd /Users/joemc3/tmp/folio && source .venv/bin/activate
folio --help
folio init --help
folio generate --help
folio cache clear --help
```

Expected: All commands show help text without errors

- [ ] **Step 3: Verify .gitignore is correct**

Run:
```bash
cd /Users/joemc3/tmp/folio
echo "test" > .profile.yml
git status
```

Expected: `.profile.yml` does NOT appear in untracked files (it's gitignored). Clean up: `rm .profile.yml`

- [ ] **Step 4: Final commit of any remaining changes**

```bash
git add -A
git status
# Only commit if there are actual changes
git commit -m "chore: final polish and cleanup"
```

---

## Summary

| Task | Module | Tests |
|---|---|---|
| 1 | Scaffolding | — |
| 2 | config.py | test_config.py |
| 3 | github.py | test_github.py |
| 4 | git.py | test_git.py |
| 5 | summarize.py | test_summarize.py |
| 6 | colors.py | — |
| 7 | render.py | test_render.py |
| 8 | push.py | test_push.py |
| 9 | cli.py | test_cli.py |
| 10 | HTML templates | (render tests) |
| 11 | README + SVG templates | (render tests) |
| 12 | .profile.yml.example, FOLIO.md | — |
| 13 | Smoke test | test_smoke.py |
| 14 | Final polish | — |

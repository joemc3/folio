"""Configuration loading and Pydantic models for Folio."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, field_validator, model_validator


# ---------------------------------------------------------------------------
# Valid value sets
# ---------------------------------------------------------------------------

VALID_PROVIDERS = {"anthropic", "openai", "ollama", "openrouter"}
VALID_RANGES = {"1mo", "3mo", "1yr", "alltime"}
VALID_STATS = {"commits", "pull_requests", "issues", "streak", "top_languages"}
VALID_ACTIVITY_RANGES = {"3mo", "6mo", "1yr"}
VALID_THEMES = {"dark", "light", "auto"}


# ---------------------------------------------------------------------------
# RepoLink
# ---------------------------------------------------------------------------

class RepoLink(BaseModel):
    """A second link for a project (live site, demo, App Store, …)."""

    label: str
    url: str


# ---------------------------------------------------------------------------
# RepoEntry
# ---------------------------------------------------------------------------

class RepoEntry(BaseModel):
    """Represents a single repository entry in the include list."""

    name: str
    private_reason: str | None = None
    link: RepoLink | None = None

    @classmethod
    def from_flexible(cls, value: Any) -> "RepoEntry":
        """Accept a plain string, a dict, or an existing RepoEntry instance."""
        if isinstance(value, cls):
            return value
        if isinstance(value, str):
            return cls(name=value)
        if isinstance(value, dict):
            return cls(**value)
        raise ValueError(f"Cannot coerce {type(value)!r} to RepoEntry")


# ---------------------------------------------------------------------------
# SocialSection
# ---------------------------------------------------------------------------

class SocialSection(BaseModel):
    """Social media / contact links."""

    twitter: str | None = None
    linkedin: str | None = None
    website: str | None = None


# ---------------------------------------------------------------------------
# ProfileSection
# ---------------------------------------------------------------------------

class ProfileSection(BaseModel):
    """Top-level profile metadata."""

    name: str = ""
    tagline: str | None = None
    location: str | None = None
    resume_url: str | None = None
    avatar: str | None = None
    email: str | None = None
    available_for_work: bool = False
    social: SocialSection = SocialSection()

    @field_validator("social", mode="before")
    @classmethod
    def coerce_social(cls, v: Any) -> Any:
        if v is None:
            return SocialSection()
        return v


# ---------------------------------------------------------------------------
# AISection
# ---------------------------------------------------------------------------

class AISection(BaseModel):
    """AI provider configuration."""

    provider: str
    model: str
    base_url: str | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v not in VALID_PROVIDERS:
            raise ValueError(
                f"Invalid provider {v!r}. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"
            )
        return v


# ---------------------------------------------------------------------------
# ForksSection
# ---------------------------------------------------------------------------

class ForksSection(BaseModel):
    """Settings for forked repositories."""

    show: bool = False
    summarize_diff: bool = False


# ---------------------------------------------------------------------------
# ReposSection
# ---------------------------------------------------------------------------

class ReposSection(BaseModel):
    """Repository filtering configuration."""

    include: list[RepoEntry] | None = None
    exclude: list[str] = []
    forks: ForksSection = ForksSection()

    @field_validator("include", mode="before")
    @classmethod
    def coerce_include(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, list):
            return [RepoEntry.from_flexible(item) for item in v]
        raise ValueError(f"include must be a list or None, got {type(v)!r}")

    @field_validator("forks", mode="before")
    @classmethod
    def coerce_forks(cls, v: Any) -> Any:
        if v is None:
            return ForksSection()
        return v


# ---------------------------------------------------------------------------
# StatsSection
# ---------------------------------------------------------------------------

class StatsSection(BaseModel):
    """GitHub activity statistics configuration."""

    range: str = "3mo"
    show: list[str] = []
    language_count: int = 5
    activity_range: str = "3mo"

    @field_validator("range")
    @classmethod
    def validate_range(cls, v: str) -> str:
        if v not in VALID_RANGES:
            raise ValueError(
                f"Invalid range {v!r}. Must be one of: {', '.join(sorted(VALID_RANGES))}"
            )
        return v

    @field_validator("show", mode="before")
    @classmethod
    def validate_show(cls, v: Any) -> Any:
        if not isinstance(v, list):
            return v
        for item in v:
            if item not in VALID_STATS:
                raise ValueError(
                    f"Invalid stat {item!r}. Must be one of: {', '.join(sorted(VALID_STATS))}"
                )
        return v

    @field_validator("activity_range")
    @classmethod
    def validate_activity_range(cls, v: str) -> str:
        if v not in VALID_ACTIVITY_RANGES:
            raise ValueError(
                f"Invalid activity_range {v!r}. Must be one of: "
                f"{', '.join(sorted(VALID_ACTIVITY_RANGES))}"
            )
        return v


# ---------------------------------------------------------------------------
# ThemeSection
# ---------------------------------------------------------------------------

class ThemeSection(BaseModel):
    """Visual theme configuration."""

    name: str = "dark"
    accent: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if v not in VALID_THEMES:
            raise ValueError(
                f"Invalid theme {v!r}. Must be one of: {', '.join(sorted(VALID_THEMES))}"
            )
        return v


# ---------------------------------------------------------------------------
# ProfileConfig (top-level)
# ---------------------------------------------------------------------------

class ProfileConfig(BaseModel):
    """Complete Folio configuration."""

    profile: ProfileSection = ProfileSection()
    ai: AISection
    repos: ReposSection = ReposSection()
    stats: StatsSection = StatsSection()
    theme: ThemeSection = ThemeSection()


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------

def load_config(path: Path | str) -> ProfileConfig:
    """Load a YAML config file and return a validated ProfileConfig.

    Raises:
        FileNotFoundError: If the config file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    return ProfileConfig.model_validate(raw)

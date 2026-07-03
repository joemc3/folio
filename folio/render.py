"""Jinja2 rendering engine for Folio profile output."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from folio.colors import get_accent_from_languages, get_language_color

# Templates directory is at the repo root level (parent of the folio package)
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _make_env() -> Environment:
    """Create and return a configured Jinja2 Environment."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        keep_trailing_newline=True,
    )
    env.filters["lang_color"] = get_language_color
    return env


def _build_context(data: Any, config: Any) -> dict[str, Any]:
    """Build the template context dictionary from enriched data and config.

    Args:
        data: An EnrichedData instance with user, repos, stats, summaries,
              fork_diffs attributes.
        config: A ProfileConfig instance with profile, theme, stats sections.

    Returns:
        Dictionary ready to pass as template context.
    """
    # Resolve theme
    theme_section = getattr(config, "theme", None)
    theme = getattr(theme_section, "name", "dark") if theme_section else "dark"

    # Resolve accent: explicit config value or auto from top languages.
    # (Legacy key, still consumed by the SVG/readme templates.)
    accent: str | None = getattr(theme_section, "accent", None) if theme_section else None
    if not accent or accent == "auto":
        languages = getattr(data.stats, "languages", {}) if data.stats else {}
        accent = get_accent_from_languages(languages)

    # Editorial accent: only an explicit hex overrides the themed default.
    # auto/None falls through to the terracotta baked into the token blocks.
    raw_accent = getattr(theme_section, "accent", None) if theme_section else None
    accent_override = raw_accent if (raw_accent and raw_accent != "auto") else None

    # Profile section
    profile_section = getattr(config, "profile", None)

    # Avatar: config override takes precedence, fall back to GitHub avatar
    avatar: str | None = None
    if profile_section:
        avatar = getattr(profile_section, "avatar", None) or None
    if not avatar:
        avatar = getattr(data.user, "avatar_url", None)

    # Bio from GitHub
    bio: str | None = getattr(data.user, "bio", None)

    # Stats display settings
    stats_section = getattr(config, "stats", None)
    stats_range = getattr(stats_section, "range", "3mo") if stats_section else "3mo"
    stats_show = getattr(stats_section, "show", []) if stats_section else []

    return {
        "user": data.user,
        "profile": profile_section,
        "repos": data.repos,
        "stats": data.stats,
        "summaries": data.summaries,
        "fork_diffs": data.fork_diffs,
        "theme": theme,
        "accent": accent,
        "accent_override": accent_override,
        "avatar": avatar,
        "bio": bio,
        "stats_range": stats_range,
        "stats_show": stats_show,
        "generated_at": datetime.now(tz=timezone.utc).strftime("%Y-%m-%d"),
        "lang_color": get_language_color,
    }


def render_profile(data: Any, config: Any) -> str:
    """Render the full HTML profile page.

    Args:
        data: EnrichedData instance.
        config: ProfileConfig instance.

    Returns:
        Rendered HTML string.
    """
    env = _make_env()
    template = env.get_template("profile.html.j2")
    context = _build_context(data, config)
    return template.render(**context)


def render_style(data: Any, config: Any) -> str:
    """Render the CSS stylesheet.

    Args:
        data: EnrichedData instance.
        config: ProfileConfig instance.

    Returns:
        Rendered CSS string.
    """
    env = _make_env()
    # CSS does not need HTML escaping
    env.autoescape = False
    template = env.get_template("style.css.j2")
    context = _build_context(data, config)
    return template.render(**context)


def render_readme(data: Any, config: Any) -> str:
    """Render the Markdown README.

    Args:
        data: EnrichedData instance.
        config: ProfileConfig instance.

    Returns:
        Rendered Markdown string.
    """
    env = _make_env()
    env.autoescape = False
    template = env.get_template("readme.md.j2")
    context = _build_context(data, config)
    return template.render(**context)


def render_svg(template_name: str, data: Any, config: Any) -> str:
    """Render an SVG component template.

    Args:
        template_name: Template filename within templates/components/ (e.g.
                       "hero.svg.j2").
        data: EnrichedData instance.
        config: ProfileConfig instance.

    Returns:
        Rendered SVG string.
    """
    env = _make_env()
    template = env.get_template(f"components/{template_name}")
    context = _build_context(data, config)
    return template.render(**context)

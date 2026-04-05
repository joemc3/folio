"""Folio CLI — generate, init, preview, status, and cache commands."""

from __future__ import annotations

import difflib
import http.server
import os
import shutil
import socketserver
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from folio.config import (
    AISection,
    ProfileConfig,
    ProfileSection,
    ReposSection,
    SocialSection,
    StatsSection,
    ThemeSection,
    VALID_PROVIDERS,
    VALID_RANGES,
    VALID_THEMES,
    load_config,
)
from folio.github import fetch_github_data
from folio.git import get_fork_diff
from folio.summarize import enrich_data, SummaryCache
from folio.render import render_profile, render_readme, render_style, render_svg
from folio.push import push_profile

import yaml

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="folio",
    help="Generate a spectacular GitHub profile page from your local machine.",
    no_args_is_help=True,
)
cache_app = typer.Typer(help="Cache management commands.")
app.add_typer(cache_app, name="cache")

console = Console()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COMPONENT_TEMPLATES = [
    ("components/hero.svg.j2", "dist/hero.svg"),
    ("components/stats_card.svg.j2", "dist/stats_card.svg"),
]


def _write_outputs(
    readme_text: str,
    html: str,
    css: str,
    cwd: Path,
) -> None:
    """Write rendered outputs to disk."""
    dist = cwd / "dist"
    dist.mkdir(exist_ok=True)

    (cwd / "README.md").write_text(readme_text, encoding="utf-8")
    (dist / "index.html").write_text(html, encoding="utf-8")
    (dist / "style.css").write_text(css, encoding="utf-8")


def _copy_fonts(cwd: Path) -> None:
    """Copy font files from folio/static/fonts/ to dist/fonts/ if they exist."""
    fonts_src = Path(__file__).parent / "static" / "fonts"
    if not fonts_src.exists():
        return
    fonts_dst = cwd / "dist" / "fonts"
    fonts_dst.mkdir(parents=True, exist_ok=True)
    for font_file in fonts_src.iterdir():
        if font_file.is_file():
            shutil.copy2(font_file, fonts_dst / font_file.name)


def _render_svg_components(enriched: object, config: object, cwd: Path) -> None:
    """Render SVG component templates that have content."""
    templates_dir = Path(__file__).parent.parent / "templates"
    for template_name, output_rel in _COMPONENT_TEMPLATES:
        template_path = templates_dir / template_name
        if not template_path.exists():
            continue
        content = template_path.read_text(encoding="utf-8").strip()
        if not content:
            continue
        svg = render_svg(template_name, enriched, config)
        out_path = cwd / output_rel
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(svg, encoding="utf-8")


def _collect_fork_diffs(github_data: object, config: object) -> dict[str, str]:
    """Collect diff texts for fork repos where a local path is configured."""
    fork_diffs: dict[str, str] = {}
    repos_section = getattr(config, "repos", None)
    include_list = getattr(repos_section, "include", None) or []

    for repo in github_data.repos:
        if not repo.is_fork:
            continue
        # Look for a local_path in the include entry for this repo
        local_path: str | None = None
        for entry in include_list:
            entry_name = entry.name if hasattr(entry, "name") else entry.get("name", "")
            if entry_name == repo.name:
                local_path = getattr(entry, "local_path", None)
                break

        if local_path and Path(local_path).exists():
            diff = get_fork_diff(local_path)
            if diff:
                fork_diffs[repo.full_name] = diff

    return fork_diffs


# ---------------------------------------------------------------------------
# generate command
# ---------------------------------------------------------------------------

@app.command()
def generate(
    config: str = typer.Option(".profile.yml", "--config", help="Path to profile config file."),
    no_ai: bool = typer.Option(False, "--no-ai", help="Skip AI summarization."),
    push: bool = typer.Option(False, "--push", help="Commit and push generated files."),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show verbose output."),
    theme: Optional[str] = typer.Option(None, "--theme", help="Override theme (dark/light/auto)."),
) -> None:
    """Generate the GitHub profile README and site."""
    cwd = Path.cwd()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=not verbose,
    ) as progress:
        # 1. Load config
        task = progress.add_task("Loading config...", total=None)
        try:
            cfg = load_config(config)
        except FileNotFoundError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        progress.update(task, description="[green]Config loaded[/green]")

        # 2. Fetch GitHub data
        progress.update(task, description="Fetching GitHub data...")
        try:
            github_data = fetch_github_data(cfg)
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)
        if verbose:
            console.print(f"Fetched {len(github_data.repos)} repos.")
        progress.update(task, description="[green]GitHub data fetched[/green]")

        # 3. Collect fork diffs
        progress.update(task, description="Collecting fork diffs...")
        fork_diff_texts = _collect_fork_diffs(github_data, cfg)
        if verbose and fork_diff_texts:
            console.print(f"Got diffs for {len(fork_diff_texts)} fork(s).")

        # 4. Enrich data (AI summaries)
        progress.update(task, description="Enriching data..." if not no_ai else "Skipping AI enrichment...")
        cache = SummaryCache()
        enriched = enrich_data(github_data, cfg, fork_diff_texts, cache, no_ai=no_ai)
        progress.update(task, description="[green]Data enriched[/green]")

        # 5. Render outputs
        progress.update(task, description="Rendering outputs...")
        effective_theme = theme or cfg.theme.name
        readme_text = render_readme(enriched, cfg)
        html = render_profile(enriched, cfg)
        css = render_style(enriched, cfg)
        progress.update(task, description="[green]Outputs rendered[/green]")

        # 6. Write files
        progress.update(task, description="Writing files...")
        _write_outputs(readme_text, html, css, cwd)
        if verbose:
            console.print(f"Written: README.md, dist/index.html, dist/style.css")

        # 7. Render SVG components
        progress.update(task, description="Rendering SVG components...")
        _render_svg_components(enriched, cfg, cwd)

        # 8. Copy fonts
        _copy_fonts(cwd)

        progress.update(task, description="[green]Done![/green]")

    console.print("[bold green]Profile generated successfully.[/bold green]")

    # 9. Push if requested
    if push:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Pushing to origin...", total=None)
            try:
                push_profile(str(cwd))
                progress.update(task, description="[green]Pushed to origin[/green]")
            except Exception as exc:
                console.print(f"[red]Push failed:[/red] {exc}")
                raise typer.Exit(1)
        console.print("[bold green]Pushed successfully.[/bold green]")


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------

@app.command()
def init(
    output: str = typer.Option(".profile.yml", "--output", "-o", help="Output config file path."),
) -> None:
    """Interactive wizard to create a new .profile.yml config file."""
    console.print("[bold]Folio Init — Create your profile config[/bold]\n")

    # Profile section
    name = typer.prompt("Your name")
    tagline = typer.prompt("Tagline", default="")
    location = typer.prompt("Location", default="")
    resume_url = typer.prompt("Resume URL", default="")

    # Social links
    console.print("\n[bold]Social Links[/bold]")
    twitter = typer.prompt("Twitter handle", default="")
    linkedin = typer.prompt("LinkedIn handle", default="")
    website = typer.prompt("Website URL", default="")

    # AI config
    console.print(f"\n[bold]AI Configuration[/bold] (providers: {', '.join(sorted(VALID_PROVIDERS))})")
    while True:
        provider = typer.prompt("AI provider", default="anthropic")
        if provider in VALID_PROVIDERS:
            break
        console.print(f"[red]Invalid provider. Choose from: {', '.join(sorted(VALID_PROVIDERS))}[/red]")

    model_default = "claude-sonnet-4-20250514" if provider == "anthropic" else "gpt-4o"
    model = typer.prompt("AI model", default=model_default)

    # Stats
    console.print(f"\n[bold]Stats Range[/bold] (options: {', '.join(sorted(VALID_RANGES))})")
    while True:
        stats_range = typer.prompt("Stats range", default="3mo")
        if stats_range in VALID_RANGES:
            break
        console.print(f"[red]Invalid range. Choose from: {', '.join(sorted(VALID_RANGES))}[/red]")

    # Theme
    console.print(f"\n[bold]Theme[/bold] (options: {', '.join(sorted(VALID_THEMES))})")
    while True:
        theme = typer.prompt("Theme", default="dark")
        if theme in VALID_THEMES:
            break
        console.print(f"[red]Invalid theme. Choose from: {', '.join(sorted(VALID_THEMES))}[/red]")

    # Build config dict
    raw: dict = {
        "profile": {
            "name": name,
            "tagline": tagline or None,
            "location": location or None,
            "resume_url": resume_url or None,
            "social": {
                "twitter": twitter or None,
                "linkedin": linkedin or None,
                "website": website or None,
            },
        },
        "ai": {
            "provider": provider,
            "model": model,
        },
        "repos": {
            "include": None,
            "exclude": [],
            "forks": {"show": False, "summarize_diff": False},
        },
        "stats": {
            "range": stats_range,
            "show": ["commits", "pull_requests", "issues", "stars_earned"],
        },
        "theme": {
            "name": theme,
            "accent": "auto",
        },
    }

    # Validate with Pydantic before writing
    try:
        ProfileConfig.model_validate(raw)
    except Exception as exc:
        console.print(f"[red]Validation error:[/red] {exc}")
        raise typer.Exit(1)

    out_path = Path(output)
    out_path.write_text(yaml.dump(raw, default_flow_style=False, allow_unicode=True), encoding="utf-8")
    console.print(f"\n[bold green]Config written to {out_path}[/bold green]")
    console.print("Run [cyan]folio generate[/cyan] to build your profile.")


# ---------------------------------------------------------------------------
# preview command
# ---------------------------------------------------------------------------

@app.command()
def preview(
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on."),
) -> None:
    """Serve the dist/ directory locally for preview."""
    dist_dir = Path.cwd() / "dist"
    if not dist_dir.exists():
        console.print("[red]Error:[/red] dist/ directory not found. Run [cyan]folio generate[/cyan] first.")
        raise typer.Exit(1)

    original_dir = os.getcwd()
    os.chdir(dist_dir)
    try:
        handler = http.server.SimpleHTTPRequestHandler
        with socketserver.TCPServer(("", port), handler) as httpd:
            console.print(f"[bold green]Serving dist/ at http://localhost:{port}[/bold green]")
            console.print("Press [bold]Ctrl+C[/bold] to stop.")
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                console.print("\n[yellow]Server stopped.[/yellow]")
    finally:
        os.chdir(original_dir)


# ---------------------------------------------------------------------------
# status command
# ---------------------------------------------------------------------------

@app.command()
def status(
    config: str = typer.Option(".profile.yml", "--config", help="Path to profile config file."),
) -> None:
    """Show what would change by regenerating the profile (no AI, dry-run diff)."""
    cwd = Path.cwd()

    # Load config
    try:
        cfg = load_config(config)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Fetching GitHub data...", total=None)
        try:
            github_data = fetch_github_data(cfg)
        except RuntimeError as exc:
            console.print(f"[red]Error:[/red] {exc}")
            raise typer.Exit(1)

        progress.update(task, description="Enriching (no AI)...")
        enriched = enrich_data(github_data, cfg, {}, cache=None, no_ai=True)

        progress.update(task, description="Rendering...")
        readme_text = render_readme(enriched, cfg)
        html = render_profile(enriched, cfg)
        css = render_style(enriched, cfg)
        progress.update(task, description="Done.")

    # Diff against existing files
    files_to_diff = [
        (cwd / "README.md", readme_text, "README.md"),
        (cwd / "dist" / "index.html", html, "dist/index.html"),
        (cwd / "dist" / "style.css", css, "dist/style.css"),
    ]

    any_diff = False
    for existing_path, new_content, label in files_to_diff:
        if existing_path.exists():
            existing = existing_path.read_text(encoding="utf-8")
        else:
            existing = ""

        diff = list(
            difflib.unified_diff(
                existing.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile=f"a/{label}",
                tofile=f"b/{label}",
                n=3,
            )
        )
        if diff:
            any_diff = True
            console.print(f"\n[bold yellow]Changes in {label}:[/bold yellow]")
            for line in diff:
                if line.startswith("+"):
                    console.print(f"[green]{line}[/green]", end="")
                elif line.startswith("-"):
                    console.print(f"[red]{line}[/red]", end="")
                else:
                    console.print(line, end="")

    if not any_diff:
        console.print("[bold green]No changes detected.[/bold green]")
    else:
        console.print("\n[bold yellow]Changes detected. Run [cyan]folio generate[/cyan] to apply.[/bold yellow]")


# ---------------------------------------------------------------------------
# cache subcommands
# ---------------------------------------------------------------------------

@cache_app.command("clear")
def cache_clear(
    repo: Optional[str] = typer.Option(None, "--repo", help="Clear cache for a single repo (user/repo)."),
) -> None:
    """Clear the summary cache."""
    cache = SummaryCache()
    cache.clear(repo=repo)
    if repo:
        console.print(f"[green]Cache cleared for {repo}.[/green]")
    else:
        console.print("[green]All cache entries cleared.[/green]")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    app()


if __name__ == "__main__":
    main()

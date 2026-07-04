# CLAUDE.md

Guidance for Claude Code working in this repo. Keep it lean — facts that aren't obvious from the code, plus the conventions this project holds itself to.

## What Folio is

A Python CLI that generates a GitHub profile page (README + a full HTML site under `dist/`) from your GitHub data and AI summaries. User-facing docs live in `FOLIO.md`.

This codebase plays **two roles** — know which checkout you're in before committing generated output:

- **Upstream tool** (`*/folio`, e.g. `joemc3/folio`): the open-source project people fork. Here `dist/` is gitignored build output, `README.md` is a placeholder, and `.profile.yml` + any generated profile output are personal — **never commit them**.
- **Profile deployment** (a fork renamed to `username/username`): the generated `README.md` and the `dist/` site *are* the published GitHub Pages artifacts and are meant to be committed/deployed.
- **How to tell:** the repo name / git remote. `*/folio` + placeholder README + gitignored `dist/` → tool; `username/username` (owner == repo name) + a generated README → deployment.

## Commands

Use the venv interpreter directly — **never** `source .venv/bin/activate`.

```bash
.venv/bin/python -m pytest          # run the test suite
.venv/bin/python -m pytest tests/test_cli.py -k generate   # one test
.venv/bin/pip install -e ".[dev]"   # editable install with dev deps
.venv/bin/folio generate            # build README.md + dist/
.venv/bin/folio preview             # serve dist/ at localhost:8000
.venv/bin/folio status              # dry-run diff, no AI
.venv/bin/folio init                # interactive .profile.yml wizard
```

## Architecture

`generate` is the spine — everything else supports it. Pipeline:

`load_config → fetch_github_data → collect fork diffs → enrich_data (AI) → render → write outputs → render SVG components → copy fonts → (optional) push`

| Module | Responsibility |
|---|---|
| `folio/cli.py` | Typer app; commands: `generate`, `init`, `preview`, `status`, `cache clear` |
| `folio/config.py` | Pydantic models + `load_config`; `VALID_PROVIDERS / VALID_RANGES / VALID_THEMES` |
| `folio/github.py` | `fetch_github_data`, `get_github_token` (PyGithub) |
| `folio/git.py` | `get_fork_diff` — what changed vs. fork upstream (GitPython) |
| `folio/summarize.py` | `enrich_data`, `SummaryCache` — AI summaries via LiteLLM, with caching |
| `folio/render.py` | `render_readme / render_profile / render_style / render_svg` (Jinja2) |
| `folio/push.py` | `push_profile` — commit + push (GitPython) |
| `folio/colors.py` | theme/accent color helpers |
| `templates/` | Jinja2: `readme.md.j2`, `profile.html.j2`, `style.css.j2`, `components/*.svg.j2` |
| `folio/static/fonts/` | bundled fonts, copied into `dist/fonts/` on generate |

## Config & generated files

- `.profile.yml` — the user's config. **Gitignored, personal, never committed.** `.profile.yml.example` is the committed template; keep it in sync when config schema changes.
- `dist/` is **gitignored build output in the tool repo** — regenerate with `folio generate`, don't hand-edit. It's the committed GitHub Pages site *only* in a `username/username` profile deployment.
- AI provider is pluggable via LiteLLM (anthropic / openai / openrouter / ollama); key comes from an env var, model from `.profile.yml`.

## Conventions (binding)

- **No generic AI aesthetic.** No purple gradients, no Inter, no SaaS-landing-page feel. This is a design-forward tool — visual quality is the product. When in doubt, make it distinctive, not "safe."
- **Use the `frontend-design` skill** for any visual or frontend work (HTML/CSS/SVG templates, the generated site).
- **Basics before polish.** Core UX flows (`init → generate → preview → push`) must work end-to-end before layering on AI or visual flourishes.
- **Brainstorm before building.** Use the `brainstorming` skill before features or behavior changes — explore intent first.
- **Spec is a starting point.** `docs/superpowers/specs/` was quick-drafted; treat every detail as up for evaluation, not gospel.

## Where things live

- Spec & implementation plan: `docs/superpowers/`
- Tests: `tests/` (pytest; fixtures in `tests/fixtures/`, shared fixtures in `conftest.py`)

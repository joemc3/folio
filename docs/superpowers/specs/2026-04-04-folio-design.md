# Folio — Design Specification

> Generate a spectacular GitHub profile page from your local machine.

---

## 1. What Folio Is

Folio is a Python CLI tool that **is** your GitHub profile repo. You clone or fork it, rename the repo to `username/username`, run `folio generate`, and push. The tool, your config, and your profile all live in the same repo.

The key principle: **the tool runs locally as the user**, using their existing `gh` CLI auth or git credentials. No GitHub Actions, no secrets management, no external servers. Private repo access is trivially available because the tool runs as the authenticated user.

### User Flow

```
1. Clone folio → rename repo to username/username on GitHub
2. folio init           → generates .profile.yml interactively
3. folio generate       → fetches data, runs AI summaries, writes output
4. git push             → profile is live at github.com/username
5. (optional) Enable GitHub Pages → full profile site at username.github.io
```

### Two Outputs, Both Vital

1. **`README.md`** (repo root) — the GitHub profile card. What visitors see at `github.com/username`. SVG-heavy, minimal, designed to look striking in GitHub's markdown renderer.

2. **`dist/index.html`** (+ `dist/style.css`) — the full profile site. Self-contained HTML, no CDN deps, no JS frameworks, zero JavaScript. Served via GitHub Pages.

Both are generated on every `folio generate`. Both are first-class deliverables.

---

## 2. Commands & Flags

```
folio init          Walk through .profile.yml interactively
folio generate      Fetch data → AI summarize → render → write output
folio preview       Serve dist/ locally on localhost
folio status        Diff current output against what generate would produce
folio cache clear   Wipe AI summary cache (all or per-repo via --repo)
```

### Flags

| Flag | Description |
|---|---|
| `--config PATH` | Path to `.profile.yml` (default: `.profile.yml` in repo root) |
| `--no-ai` | Skip all AI summarization passes |
| `--push` | After generating, commit and push README.md + dist/ |
| `--verbose` | Show detailed per-repo progress output |
| `--theme THEME` | Override theme from config |

---

## 3. Configuration — `.profile.yml`

```yaml
profile:
  name: "Joe McConnell"
  tagline: "Builder of things that shouldn't exist yet"
  location: "Houston, TX"
  resume_url: "https://example.com/resume"
  avatar: ""              # Leave blank → use GitHub avatar
  social:
    twitter: ""
    linkedin: ""
    website: ""

ai:
  provider: anthropic     # anthropic | openai | ollama | openrouter
  model: claude-sonnet-4-20250514
  base_url: ""            # Required for ollama (e.g. http://localhost:11434)
  # API key from env var — never stored here.
  # ANTHROPIC_API_KEY | OPENAI_API_KEY | OPENROUTER_API_KEY | ollama: no key

repos:
  include:                # Opt-in list. If omitted, defaults to all public repos.
    - name: my-public-project
    - name: waiver-admin
      private_reason: "Under NDA with client"
    - name: homelab-notes
      private_reason: "Work in progress"
    - name: secret-stuff        # Defaults to "Private repository"
    - name: cool-fork           # Fork — gets diff summary automatically

  exclude:                # Repos to hide. Applied after include resolution.
    - old-abandoned-project

  forks:
    show: true
    summarize_diff: true  # AI "what I changed" summary against upstream

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
  accent: auto            # auto (from top language color) | hex e.g. "#e8b84a"
```

### Config Rules

- `include` entries are either plain strings (coerced to `RepoEntry(name=str)`) or objects with `name` + optional `private_reason`.
- If `include` is omitted entirely, defaults to all public repos for the authenticated user.
- `exclude` is applied after include resolution.
- `private_reason` defaults to `"Private repository"` if not specified on a private repo.
- No `output` section — README always goes to repo root, HTML site always to `./dist/`.
- No `pinned_only` — all repos are treated equally regardless of GitHub pinning.
- `.profile.yml` is gitignored. `.profile.yml.example` is committed as a template.

---

## 4. Architecture & Data Flow

```
folio generate
│
├── 1. Load & validate .profile.yml → ProfileConfig (Pydantic)
│
├── 2. GitHub fetch (github.py — PyGitHub) → GitHubData
│   ├── User profile (name, avatar, bio, followers)
│   ├── Repos (resolved include/exclude list)
│   ├── Fork repos → git.py for local diff against upstream
│   └── Stats (commits, PRs, issues, streak, languages, stars)
│
├── 3. AI summarization (summarize.py — LiteLLM) → EnrichedData
│   ├── All included repos: README + commits → 2-sentence summary
│   ├── Forks: diff output → "what I changed" summary
│   └── Cached to ~/.folio/cache.json (keyed by repo + HEAD SHA)
│
├── 4. Render (render.py — Jinja2) → rendered strings
│   ├── templates/readme.md.j2 → README.md content
│   ├── templates/profile.html.j2 → index.html content
│   └── SVG components rendered as Jinja2 includes
│
└── 5. Write output (cli.py writes to disk)
    ├── README.md → repo root
    ├── dist/index.html + dist/style.css → ./dist/
    ├── dist/*.svg → SVG assets for README
    └── Optional: --push flag → commit + push via GitPython
```

### Data Types

```python
# config.py
class RepoEntry(BaseModel):
    name: str
    private_reason: str | None = None

class ProfileConfig(BaseModel):
    profile: ProfileSection
    ai: AISection
    repos: ReposSection
    stats: StatsSection
    theme: ThemeSection

# github.py
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
    fork_parent: str | None        # e.g. "BerriAI/litellm"
    private_reason: str | None     # from config
    html_url: str

@dataclass
class StatsData:
    commits: int
    pull_requests: int
    issues: int
    streak_days: int
    stars_earned: int
    languages: dict[str, float]    # language → percentage

@dataclass
class GitHubData:
    user: UserProfile
    repos: list[RepoData]
    stats: StatsData

# summarize.py adds summaries → EnrichedData
@dataclass
class EnrichedData:
    user: UserProfile
    repos: list[RepoData]
    stats: StatsData
    summaries: dict[str, str]      # repo name → 2-sentence summary
    fork_diffs: dict[str, str]     # repo name → "what I changed" summary
```

---

## 5. Module Responsibilities

### `cli.py`
- Typer application with all command definitions and flag parsing
- Rich progress display during `generate` (per-stage announcements, `--verbose` for per-repo detail)
- Orchestrates the pipeline: config → fetch → summarize → render → write
- Writes rendered output to disk (render.py returns strings, doesn't touch the filesystem)
- `folio init`: interactive wizard using `typer.prompt`, validates with Pydantic on the fly, writes `.profile.yml`
- `folio preview`: simple HTTP server pointed at `./dist/` with file watching for template changes
- `folio status`: runs full pipeline, diffs rendered output against existing files using `difflib`

### `config.py`
- Pydantic models for `.profile.yml`
- `RepoEntry` coercion: plain strings become `RepoEntry(name=str)`
- Validation with helpful errors (unknown provider, invalid date range, etc.)

### `github.py`
- PyGitHub wrapper
- Auth chain: `gh auth token` subprocess → `GITHUB_TOKEN` env var → error with clear message
- Fetches user profile, repos (respecting include/exclude), stats by date range
- Returns `GitHubData` — typed dataclasses, not raw PyGitHub objects
- For each fork: gets `repo.parent` info for the "forked from X" display
- Rate limiting handled by PyGitHub automatically

### `git.py`
- GitPython operations for fork diffs only
- `git diff HEAD upstream/HEAD` — requires upstream remote to exist locally
- Returns diff as string, passed to `summarize.py`
- If upstream remote missing: log warning, skip diff, don't crash

### `summarize.py`
- LiteLLM wrapper
- Two prompt types: repo summary and fork diff summary (see Section 6)
- Cache: `~/.folio/cache.json`, keyed by `{owner/repo}:{head_sha}`
- `--no-ai` skips this module entirely — repos get no summary text
- If an AI call fails: warn and continue without summary for that repo. Never crash the pipeline.

### `render.py`
- Jinja2 environment pointed at `templates/`
- Pure function: takes `EnrichedData` + `ProfileConfig`, returns rendered strings
- Renders `readme.md.j2` → README.md content
- Renders `profile.html.j2` → index.html content
- SVG components are Jinja2 includes, rendered inline

### `push.py`
- Invoked only with `--push` flag
- GitPython: stage `README.md` and `dist/`, commit, push to origin
- Commit message: `folio: regenerate profile [ISO timestamp]`
- Normal push only — no force-push

---

## 6. AI Summarization

### Repo Summary Prompt

```
You are writing a two-sentence project description for a card on a developer's
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
Recent commit messages: {commit_messages}
```

### Fork Diff Prompt

```
A developer forked "{upstream_name}" and made modifications. Write 1-2 sentences
describing what they changed, written in first person ("I added...", "I fixed...").

Be specific — name the features, files, or fixes visible in the diff. If the
changes are minor (typo fixes, config tweaks), say so honestly. Do not inflate
small contributions.

Upstream project: {upstream_description}
Diff summary: {diff_text}
```

### Preprocessing

- README excerpt: first 2000 characters
- Commit messages: last 10, filtered to remove noise (`merge branch`, `fix typo` style messages)
- Fork diffs: first 3000 characters, with lockfile and generated code changes stripped (patterns: `package-lock.json`, `yarn.lock`, `*.min.js`, `go.sum`, etc.)

### Cache

- File: `~/.folio/cache.json`
- Key: `{repo_full_name}:{head_sha}`
- Cache hit: return cached summary, skip AI call
- Cache miss (new repo or SHA changed): call AI, store result
- `folio cache clear`: wipe entire cache file
- `folio cache clear --repo name`: remove one entry
- Cache is never automatically pruned

### Provider Support

All via LiteLLM. User sets `ai.provider` and `ai.model` in config. API keys from env vars:
- Anthropic: `ANTHROPIC_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- OpenRouter: `OPENROUTER_API_KEY`
- Ollama: no key needed, requires `ai.base_url`

---

## 7. The Generated Profile Site (index.html)

### Visual Design Direction

The design must feel like a human designer made deliberate choices. No AI slop aesthetics — no purple gradients, no Inter font, no SaaS landing page feel, no glassmorphism, no shadcn-style cards.

**Typography:**
- Primary: `JetBrains Mono` — monospace as the design language, not just for code. Weight, size, and spacing for hierarchy.
- Prose: `DM Sans` — used only for readable body text (summaries, about section).
- System mono fallback stack: `ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, monospace`

**Color:**
- No gradients. Flat, high-contrast.
- Dark theme: background `#151519`, text `#e0e0e6`, bright text `#f5f5f8`, dim text `#888899`, borders `#303040`
- Accent: single hue from user's top language color (or user-specified hex). Used sparingly — cursor, section label prefixes, hover states. Not splashed everywhere.
- Light theme: warm white base, same restraint (details TBD during implementation).
- Auto theme: `prefers-color-scheme` media query.

**Layout:**
- Left-aligned, not centered hero.
- Max-width 900px, generous vertical spacing between sections.
- Projects as rows (not cards) — name/tags on left, summary in middle, meta on right. Separated by 1px border lines.
- Dense where density serves (stats), spacious where breathing room matters (about, between sections).

**Cards/Elements:**
- No shadows, no rounded corners, no hover-lift animations.
- Differentiation through spacing and typography.
- Private repos: subtle accent-colored `○` marker + reason text.
- Forks: italic "forked from X" note.
- Tags: 1px bordered, small, understated.

**The one animation:** Blinking cursor on the tagline. CSS `step-end` blink, 1.2s interval. Nothing else moves.

**Section headers:** `// Section Name` format — monospace, 14px, weight 600, uppercase with letter-spacing. The `//` prefix in accent color.

### Sections (top to bottom)

1. **Hero** — name (h1, bold mono), tagline with blinking cursor, links (resume, social, location), avatar (small, top-right)
2. **About** — bio from config (or GitHub bio fallback). DM Sans, comfortable reading width (~620px).
3. **Projects** — row-based list. Each project shows:
   - Public/private repos: name, language tag, AI summary, recent activity indicator, stars, last updated
   - Forks: upstream description, then AI diff summary of what the user changed. "Forked from X" note.
   - Private repos: lock icon or `private` tag, reason text, no GitHub link
   - Public repos: name links to GitHub
4. **Stats** — at the bottom. Numeric row (commits, PRs, issues, streak, stars earned) + language breakdown bar (thin, segmented, colored by language, with legend below).
5. **Footer** — "Built with Folio" + "Last generated [date]"

### Technical Constraints

- Self-contained: no CDN dependencies in generated output
- Zero JavaScript
- Fonts: JetBrains Mono and DM Sans woff2 files embedded in `dist/fonts/` and loaded via `@font-face` in the CSS. No runtime CDN calls. The generated site works fully offline.
- Mobile responsive
- All three themes (dark, light, auto) complete and polished

---

## 8. The Generated README.md (GitHub Profile Card)

The README renders at `github.com/username`. GitHub's markdown renderer is the constraint: limited HTML, no `<style>`, no JS, SVGs via `<img>` tags only.

### Approach

Generate SVG files into `dist/` and reference them from README.md with relative `<img>` paths. SVGs are Jinja2-rendered with the same data as the HTML site.

### Contents

1. `<!-- Generated by Folio. Do not edit manually. -->` header comment
2. SVG hero card — name, tagline, 2-3 headline stats baked in
3. Subtle SVG accent element (thin accent-colored rule — no animation, GitHub strips it)
4. Brief text: 2-3 lines max
5. Link to full Pages site: `→ username.github.io`

### SVG Constraints

GitHub caches and sanitizes SVGs aggressively:
- No external fonts, no `<foreignObject>`, no `@import`
- Inline styles and system fonts only
- The README will look *related* to the full site but not identical — system mono stack instead of JetBrains Mono
- This is intentional: the README is a teaser, not a replica

---

## 9. Stats Implementation

Stats fetched from GitHub API via PyGitHub, scoped to the configured time range. No caching — stats change frequently and are re-fetched on every `folio generate`.

The time range is a **generation-time config option**, not a viewer-facing control. The user picks their range in `.profile.yml`, and the output shows stats for that range. No interactive toggle on the generated page.

**Date ranges:**
- `1mo` → 30 days ago
- `3mo` → 90 days ago
- `1yr` → 365 days ago
- `alltime` → no date filter

**Stat types:**
- Commits: `search_commits(query=f"author:{username} committer-date:>{since}")`
- Pull requests: `search_issues(query=f"author:{username} type:pr created:>{since}")`
- Issues: `search_issues(query=f"author:{username} type:issue created:>{since}")`
- Stars earned: sum of `stargazers_count` across included repos
- Top languages: aggregate `repo.language` across included repos, weighted by repo size
- Streak: longest consecutive days with commits in the configured range, computed from commit dates

Language breakdown rendered as custom inline SVG — thin segmented bar with colored segments and text legend. No third-party image services.

---

## 10. Project Structure

```
folio/
├── folio/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── github.py
│   ├── git.py
│   ├── summarize.py
│   ├── render.py
│   └── push.py
├── templates/
│   ├── profile.html.j2
│   ├── readme.md.j2
│   └── components/
│       ├── hero.svg.j2
│       ├── stats_card.svg.j2
│       ├── language_chart.svg.j2
│       └── repo_card.html.j2
├── tests/
│   ├── test_config.py
│   ├── test_github.py
│   ├── test_summarize.py
│   ├── test_render.py
│   ├── test_push.py
│   └── fixtures/
├── .profile.yml          # gitignored — personal config
├── .profile.yml.example  # committed — template for new users
├── .gitignore
├── README.md             # generated — DO NOT EDIT
├── FOLIO.md              # project documentation
├── pyproject.toml
└── SPEC.md               # original spec (reference)
```

---

## 11. Dependencies

```toml
[project]
name = "folio-profile"
version = "0.1.0"
requires-python = ">=3.11"

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

[project.scripts]
folio = "folio.cli:app"
```

---

## 12. Testing

- **`test_config.py`** — valid/invalid `.profile.yml` inputs, Pydantic coercion (string → RepoEntry), missing fields, bad provider names, validation error messages
- **`test_github.py`** — mocked PyGitHub responses, date range stat math, exclude list filtering, fork parent detection
- **`test_summarize.py`** — mocked LiteLLM calls, cache hit/miss logic, prompt construction, `--no-ai` bypass
- **`test_render.py`** — render with fixture data, assert valid HTML and non-empty markdown
- **`test_push.py`** — mocked GitPython, assert correct files staged and commit message format
- **Smoke test:** `folio generate --no-ai` against fixture data → assert README.md and dist/index.html written and non-empty

No live integration tests initially — mocked tests cover the logic. Live tests against a real GitHub account can be added later with CI token setup.

---

## 13. Error Handling Philosophy

- **Config errors:** fail fast with clear Pydantic validation messages (wrong provider, malformed YAML, unknown fields)
- **AI failures:** warn and continue — skip summary for that repo, never crash the pipeline
- **Missing upstream remote on forks:** warn, skip diff summary, still show the fork card with basic info
- **GitHub rate limiting:** PyGitHub handles rate limit headers. Rich progress output shows what's being fetched so the user knows it's working.
- **Partial output:** never leave partial output on disk — either complete the generate or roll back

---

## 14. Resolved Decisions

Decisions made during design that differ from or clarify the original spec:

1. **No `output` config section.** README always → repo root, HTML site always → `./dist/`. No path configurability needed.
2. **No `pinned_only`.** All repos treated equally. Include/exclude list is the only filtering mechanism.
3. **No interactive stats toggle.** Time range is a generation-time config option. The viewer gets static output. No JavaScript on the generated page.
4. **No GraphQL dependency.** With `pinned_only` removed, everything goes through PyGitHub's REST API.
5. **Prompts revised.** Both repo summary and fork diff prompts rewritten for better tone, specificity, and context.
6. **Zero JavaScript** on the generated HTML site. Dropping the interactive toggle made this achievable.
7. **Project cards show more detail.** Forks show upstream description + what-I-changed summary. Regular repos show summary + recent activity. Not just name + two-line summary.
8. **Font strategy split.** HTML site uses JetBrains Mono + DM Sans (web fonts). README SVGs use system mono stack (GitHub sanitizes external fonts).

# Folio — Editorial Redesign (Direction 1A)

**Status:** Approved for planning
**Date:** 2026-07-03
**Source design:** Claude Design project `25b8ebbf-…`, file `Folio Redesign.dc.html`, option **1A · Editorial**

## Summary

Reskin Folio's generated HTML site from its current cool-gray terminal look to the
**Editorial** direction: warm, magazine-grade, `Instrument Serif` masthead over a
cream/terracotta palette. This is a **reskin plus two small, additive data changes**
(a real contribution heatmap and an optional second link per project) — *not* a
rewrite. The `generate` pipeline, config model, and every existing data binding stay
intact; we extend them.

### Scope boundary

- **In scope:** `templates/profile.html.j2` + `templates/style.css.j2` → `dist/index.html`
  + `dist/style.css`, plus the config/data plumbing the new sections require.
- **Out of scope this pass:** `templates/readme.md.j2` and the three SVG components
  (`hero`, `stats_card`, `language_chart`). They render on the *repo README surface*,
  not the site page, so the site redesign doesn't touch them. Revisit later if they
  drift too far from the new site look.

## Non-negotiables (user decisions)

1. **No stars anywhere.** Remove per-project `★ stars` from the work list **and** the
   `stars_earned` overview tile. This is a work showcase, not social proof.
2. **Second project link is optional and quiet.** A project shows a second link only
   when one exists; otherwise it renders name + description and nothing else.
3. **Editorial (1A), not System (1B).** Warm palette, serif masthead, numbered work list.
4. **Real heatmap data**, not approximated — via the GitHub GraphQL contribution calendar
   (which also lets us finally compute a real streak; today `streak_days` is hardcoded `0`).
5. **No fake browser chrome.** The mockup's traffic-lights/URL-bar/drop-shadow frame on a
   gray canvas is a presentation device. The real site is a full-bleed cream page with a
   centered max-width content column.
6. **Fonts bundled locally.** Add `Instrument Serif` (regular + italic) as local woff2 in
   `folio/static/fonts/`; never hotlink Google Fonts (matches how JetBrains Mono / DM Sans
   ship today).

## Visual system

### Typography
- **Instrument Serif** — masthead first name, italic tagline, project names, editorial numerals.
- **DM Sans** — body copy, buttons, project descriptions, pills.
- **JetBrains Mono** — eyebrows, section labels, dates, meta, footer.

### Palette → CSS tokens
Replace the current cool-gray token set with the Editorial warm set, wired into the
**existing** `:root` / `@media (prefers-color-scheme)` / `.theme-light` / `.theme-dark`
structure so `theme.name` (`dark` | `light` | `auto`) keeps working unchanged.

| Token | Light | Dark |
|---|---|---|
| `--bg` | `#f7f3ea` | `#17130c` |
| `--bg2` | `#efe7d7` | `#20190f` |
| `--panel` | `#fffdf8` | `#1c160d` |
| `--fg` | `#1c1813` | `#f1e9db` |
| `--fg-mid` | `#4c4539` | `#cabfac` |
| `--fg-dim` | `#847b6b` | `#998e7c` |
| `--border` | `#e4dccb` | `#342a1b` |
| `--border-strong` | `#d2c7b0` | `#453923` |
| `--accent` | `#dd4d27` | `#ff6a3c` |
| `--accent-ink` | `#b93c1c` | `#ff8a63` |
| `--heat0` | `#e9e2d1` | `#2c2416` |
| `--shadow` | `rgba(60,45,20,0.12)` | `rgba(0,0,0,0.55)` |

New tokens vs. today: `--fg-mid`, `--panel`, `--border-strong`, `--accent-ink`, `--heat0`.
(`--shadow` is optional now that the drop-shadowed card frame is dropped; keep for hover/CTA depth.)

### Accent resolution (deliberate change — flag if unwanted)
Today `accent = "auto"` derives from the top language color, which would clash with the
warm palette. For the Editorial theme, **`auto`/unset → the designed terracotta accent**
(per light/dark above). An explicit `theme.accent` hex still overrides the accent token
(and `--accent-ink` derives from it). If you'd rather keep language-derived accents, say so
at spec review.

## Section mapping (design → template + data source)

Rendered top-to-bottom inside a centered content column on a full-bleed `--bg` page:

| Section | Content | Data source |
|---|---|---|
| Eyebrow | `Portfolio — {year}` · `● Available for work` badge | `generated_at` year; new `profile.available_for_work` (hidden when false/unset) |
| Masthead | Giant serif first name; italic serif tagline; round avatar (photo or accent monogram); **Résumé** + **Email** buttons | `profile.name`/`user.name`; `profile.tagline`; `avatar`; `profile.resume_url`; new email source |
| About | Paragraph | existing `bio` |
| Stack | Language pills with colored dots | existing `stats.languages` + `lang_color` filter (replaces the old language bar) |
| Selected work | Numbered list `01…N`; per project: name (repo link), tags (`private`/`fork`/`lang`), summary, fork/private notes, date, **second link** | existing `repos` loop + `summaries`/`fork_diffs`; **no stars** |
| Activity — last {3\|6\|12} months | Contribution heatmap (renders the weeks in the configured window × 7), legend, `{total} contributions` header | new `stats.contribution_weeks` + total; window from `stats.activity_range` |
| Stat line | commits / pull requests / issues / streak (editorial styling) | existing search-API totals + new real `streak_days`; **no stars tile** |

> **Note:** the numeric **stat line is a deliberate addition to 1A** — the literal Editorial
> mockup has no stats row. It's kept (in editorial styling) because the user values that data and
> it's already fetched. Flag at spec review if you'd rather go literal and drop it.
| CTA | "Let's build something." + Résumé/Email | `resume_url`/email |
| Footer | "Built with Folio" + generated date | existing |

## Data & config changes (additive)

### 1. Second project link
- **New Pydantic model** `RepoLink { label: str; url: str }`; add optional `link: RepoLink | None`
  to `RepoEntry` in `config.py`.
- **`RepoData`** (github.py) gains `homepage: str | None` (from `repo.homepage`) and a resolved
  `link: RepoLink | None`.
- **Resolution precedence**, done during `fetch_github_data` (thread the include entry, not just
  `private_reason`, through `include_map` → `_build_repo_data`):
  1. `.profile.yml` `link` block for that repo → use it (custom label).
  2. Else GitHub repo Website field (`repo.homepage`) → label **"View site"**.
  3. Else → `None` (renders no second link).
- Template: `{% if repo.link %}<a href="{{ repo.link.url }}">{{ repo.link.label }} ↗</a>{% endif %}`.

### 2. Contribution heatmap + real streak
- **Configurable window.** New `StatsSection.activity_range: str = "3mo"`, validated against a
  new `VALID_ACTIVITY_RANGES = {"3mo", "6mo", "1yr"}` (deliberately no `1mo`/`alltime` — a
  one-month grid is too sparse and a grid can't be unbounded). Kept **separate** from
  `stats.range` (the stat-totals window) so the two can differ. Default `3mo` matches today's
  intent; bump to `6mo` or `1yr` by changing one line.
- **New fetch** in github.py: POST the GitHub GraphQL API (`requests`, already transitive via
  PyGithub) with the existing token, passing the window as `from`/`to` DateTime args
  (`from = now − N months`, `to = now`):
  `user(login:$login){ contributionsCollection(from:$from, to:$to){ contributionCalendar{
  totalContributions weeks{ contributionDays{ contributionCount date weekday } } } } }`.
- Map into `StatsData`: `contribution_weeks: list[list[ContribDay]]` where
  `ContribDay { count: int; level: int (0–4) }`, and `contribution_total: int`.
  Level buckets: `0` = none; `1–4` by ascending count thresholds (define in impl, GitHub-like).
- **Grid width follows the window** (~13 weeks at 3mo, ~26 at 6mo, ~52 at 1yr). Cells stay a
  fixed size; the matrix left-aligns within its section rather than stretching, and the section
  label reads **"Activity — last {3|6|12} months"** to match. The `frontend-design` pass makes
  the shorter grid read as intentional (e.g. matrix not forced to full column width).
- **Real `streak_days`**: current consecutive days with `count > 0` up to today, computed from
  the fetched calendar (replaces the hardcoded `0`). A streak longer than the window is capped
  at the window — acceptable for the ranges offered.
- Fetch is best-effort: on GraphQL failure, return empty weeks + `streak_days=0` so `generate`
  never breaks (matches existing try/except style in `_fetch_stats`).

### 3. Small profile fields
- `ProfileSection.available_for_work: bool = False` — drives the eyebrow badge.
- Email source for the Email/CTA buttons: add `ProfileSection.email: str | None` (fall back to
  public `user.email` if unset; hide the button if neither exists).

### 4. Stats cleanup
- Remove `stars_earned` from `VALID_STATS` and from `.profile.yml.example`'s default `show`.
  Stop rendering stars entirely (the `RepoData.stars` field may remain in the model, unused).
- Reconcile the stat-key mismatch: `VALID_STATS` uses `streak`/`top_languages` while the old
  template checked `streak_days`. The rewritten template uses the canonical `VALID_STATS` keys;
  add `streak` to the example's `show`.
- Add `activity_range: 3mo` under `stats` in `.profile.yml.example`, with a comment noting the
  allowed `3mo | 6mo | 1yr` and that it controls only the heatmap window.

### 5. Config example
- Update `.profile.yml.example`: drop `stars_earned`; add a commented `link:` example on a repo
  entry; add `available_for_work` and `email`. Keep it in sync with the schema (repo convention).

## Fonts
- Add `folio/static/fonts/instrument-serif-400.woff2` and `instrument-serif-400-italic.woff2`.
- Add matching `@font-face` blocks to `style.css.j2`.
- Verify `generate`'s font-copy step copies the whole `static/fonts/` dir (so new files ship to
  `dist/fonts/` automatically); adjust if it enumerates specific files.

## Testing
- **Render:** `render_profile` on a fixture `EnrichedData` asserts — masthead present, **no `★`
  / no "stars" anywhere**, second link renders when `repo.link` set and is absent otherwise,
  heatmap emits the expected cell count, eyebrow badge shows only when `available_for_work`.
- **Config:** `RepoEntry` parses a `link` block; `stars_earned` no longer valid; example file loads.
- **GitHub:** contribution-calendar fetch parses a mocked GraphQL payload into weeks; streak
  computation unit test (including the all-zero and broken-streak cases); homepage/link resolution
  precedence.
- Full existing suite stays green (`.venv/bin/python -m pytest`).
- Regenerate and commit `dist/` (it is the deployed site, per CLAUDE.md).

## Files touched
- `templates/profile.html.j2` — restructured to the Editorial layout.
- `templates/style.css.j2` — Editorial tokens, type, layout; new `@font-face`.
- `folio/config.py` — `RepoLink`, `RepoEntry.link`, `ProfileSection.available_for_work`/`email`,
  `StatsSection.activity_range` + `VALID_ACTIVITY_RANGES`, `VALID_STATS` cleanup.
- `folio/github.py` — `RepoData.homepage`/`link`, contribution-calendar fetch, real streak,
  `StatsData.contribution_weeks`/`contribution_total`, `ContribDay`.
- `folio/render.py` — thread any new context (mostly flows through the existing data objects).
- `folio/static/fonts/` — Instrument Serif woff2.
- `folio/cli.py` — confirm font-copy is directory-wide.
- `.profile.yml.example` — schema sync.
- `dist/` — regenerated.
- `tests/` — new coverage above.

## Decisions confirmed at spec review
- **Accent:** `auto`/unset → designed terracotta; an explicit `theme.accent` hex still overrides. ✔
- **Second link:** both sources — GitHub Website field *and* `.profile.yml` override (config wins). ✔
- **Stat line:** kept (commits / PRs / issues / streak) in editorial styling — a deliberate
  addition to the literal 1A mockup. ✔
- **Activity window:** configurable `stats.activity_range`, default `3mo` (`3mo | 6mo | 1yr`). ✔
- **Default theme** stays `dark` per current config; Editorial light *and* dark are both fully styled.

# Editorial Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reskin Folio's generated HTML site to the warm, magazine-grade Editorial (1A) direction, plus two additive data features (a real contribution heatmap with real streak, and an optional second link per project), with stars removed everywhere.

**Architecture:** The `generate` pipeline is unchanged in shape. New data flows through the existing objects: `RepoData` gains `homepage`/`link`, `StatsData` gains `contribution_weeks`/`contribution_total` and a real `streak_days`, `UserProfile` gains `email` — all reach the templates automatically via `EnrichedData`. The visual change is confined to `templates/profile.html.j2` + `templates/style.css.j2` (+ a small `render.py` accent tweak). Contribution data comes from one best-effort GitHub GraphQL call; everything degrades gracefully to empty when it fails.

**Tech Stack:** Python 3, Pydantic v2, PyGithub, `requests` (GraphQL POST), Jinja2, pytest. Fonts: Instrument Serif / DM Sans / JetBrains Mono as local woff2.

**Design reference:** Spec at `docs/superpowers/specs/2026-07-03-editorial-redesign-design.md`. The pixel-level source is Claude Design `25b8ebbf-…` file `Folio Redesign.dc.html`, **option 1A**.

## Global Constraints

- **No stars anywhere** — not per-project, not in the stat line. The `RepoData.stars` / `StatsData.stars_earned` *fields* may remain (unused); nothing renders `★` or "stars".
- **No generic AI aesthetic** — warm cream/terracotta editorial look; distinctive, not "safe" (repo convention).
- **Use the `frontend-design` skill** for all template/CSS work (Task 6).
- **Fonts bundled locally** — never hotlink Google Fonts.
- **Venv interpreter directly** — `.venv/bin/python -m pytest`; never `source`.
- **`dist/` is committed** — regenerate, don't hand-edit.
- **Best-effort network** — the contribution fetch must never break `generate`; on any failure return empty weeks.
- **Full suite green** after every task: `.venv/bin/python -m pytest`.

---

### Task 1: Config model changes + config-adjacent sync

**Files:**
- Modify: `folio/config.py`
- Modify: `.profile.yml.example`
- Modify: `folio/cli.py:414-418` (init's `stats.show` default)
- Modify: `tests/fixtures/sample_config.yml:31-38`
- Modify/Test: `tests/test_config.py`

**Interfaces:**
- Produces: `RepoLink{label:str, url:str}`; `RepoEntry.link: RepoLink | None`; `ProfileSection.email: str|None`, `ProfileSection.available_for_work: bool`; `StatsSection.activity_range: str` (validated `3mo|6mo|1yr`); `VALID_ACTIVITY_RANGES`; `VALID_STATS` without `stars_earned`.

- [ ] **Step 1: Write failing config tests**

Add to `tests/test_config.py`:

```python
def test_repo_entry_accepts_link_block():
    from folio.config import ReposSection
    section = ReposSection.model_validate({
        "include": [{"name": "folio", "link": {"label": "View site", "url": "https://x.dev"}}]
    })
    entry = section.include[0]
    assert entry.link.label == "View site"
    assert entry.link.url == "https://x.dev"

def test_repo_entry_without_link_is_none():
    from folio.config import RepoEntry
    assert RepoEntry.from_flexible("folio").link is None

def test_activity_range_defaults_to_3mo():
    from folio.config import StatsSection
    assert StatsSection().activity_range == "3mo"

def test_activity_range_rejects_invalid():
    import pytest
    from folio.config import StatsSection
    with pytest.raises(ValueError, match="activity_range"):
        StatsSection(activity_range="2yr")

def test_stars_earned_no_longer_valid_stat():
    import pytest
    from folio.config import StatsSection
    with pytest.raises(ValueError, match="stars_earned"):
        StatsSection(show=["stars_earned"])

def test_profile_available_for_work_and_email_defaults():
    from folio.config import ProfileSection
    p = ProfileSection()
    assert p.available_for_work is False
    assert p.email is None
```

- [ ] **Step 2: Run and verify they fail**

Run: `.venv/bin/python -m pytest tests/test_config.py -k "link or activity_range or stars_earned or available" -v`
Expected: FAIL (fields/validators don't exist yet).

- [ ] **Step 3: Implement config.py changes**

In `folio/config.py`:

```python
# Update the valid-values block:
VALID_STATS = {"commits", "pull_requests", "issues", "streak", "top_languages"}
VALID_ACTIVITY_RANGES = {"3mo", "6mo", "1yr"}
```

```python
# New model, placed just above RepoEntry:
class RepoLink(BaseModel):
    """A second link for a project (live site, demo, App Store, …)."""
    label: str
    url: str


class RepoEntry(BaseModel):
    name: str
    private_reason: str | None = None
    link: RepoLink | None = None
    # from_flexible unchanged — cls(**value) coerces a nested link dict via Pydantic.
```

```python
# ProfileSection — add two optional fields (order before `social`):
class ProfileSection(BaseModel):
    name: str = ""
    tagline: str | None = None
    location: str | None = None
    resume_url: str | None = None
    avatar: str | None = None
    email: str | None = None
    available_for_work: bool = False
    social: SocialSection = SocialSection()
    # (existing coerce_social validator unchanged)
```

```python
# StatsSection — add activity_range + validator:
class StatsSection(BaseModel):
    range: str = "3mo"
    show: list[str] = []
    language_count: int = 5
    activity_range: str = "3mo"

    # (existing validate_range + validate_show unchanged)

    @field_validator("activity_range")
    @classmethod
    def validate_activity_range(cls, v: str) -> str:
        if v not in VALID_ACTIVITY_RANGES:
            raise ValueError(
                f"Invalid activity_range {v!r}. Must be one of: "
                f"{', '.join(sorted(VALID_ACTIVITY_RANGES))}"
            )
        return v
```

- [ ] **Step 4: Update fixture, parametrize, and init default to keep the suite green**

`tests/fixtures/sample_config.yml` — delete the `- stars_earned` line (line 37) and add `activity_range: 3mo` under `stats:`:

```yaml
stats:
  range: 3mo
  activity_range: 3mo
  show:
    - commits
    - pull_requests
    - issues
    - streak
    - top_languages
  language_count: 6
```

`tests/test_config.py:135` — remove `"stars_earned"` from the parametrize list:

```python
@pytest.mark.parametrize("stat", ["commits", "pull_requests", "issues", "streak", "top_languages"])
```

`folio/cli.py` — in `init` (the `raw` dict, ~line 416), drop `stars_earned` and add `activity_range`:

```python
        "stats": {
            "range": stats_range,
            "activity_range": "3mo",
            "show": ["commits", "pull_requests", "issues", "streak", "top_languages"],
            "language_count": 6,
        },
```

- [ ] **Step 5: Update `.profile.yml.example`**

Replace the `repos.include` and `stats` blocks:

```yaml
repos:
  include:
    - name: my-cool-project
      # Optional second link shown next to the repo link:
      # link:
      #   label: View site      # button text (e.g. Live demo, Landing page, App Store)
      #   url: https://my-cool-project.example.com
    - name: private-work
      private_reason: "Under NDA"   # Shown instead of a link
      # link:                        # private repos can still carry a second link
      #   label: App Store
      #   url: https://apps.apple.com/app/idXXXXXXXX
  exclude:
    - old-project-to-hide
  forks:
    show: true
    summarize_diff: true

stats:
  range: 3mo              # 1mo | 3mo | 1yr | alltime  (stat totals window)
  activity_range: 3mo     # 3mo | 6mo | 1yr            (contribution heatmap window)
  show:
    - commits
    - pull_requests
    - issues
    - streak
    - top_languages
  language_count: 6
```

And in the `profile:` block add `email` + `available_for_work`:

```yaml
profile:
  name: "Your Name"
  tagline: "What you do in one line"
  location: ""
  resume_url: ""
  email: ""                 # For the Email button; blank = use your public GitHub email, or hide it
  available_for_work: false # true shows an "● Available for work" badge
  avatar: ""
  social:
    twitter: ""
    linkedin: ""
    website: ""
```

- [ ] **Step 6: Run tests, verify green**

Run: `.venv/bin/python -m pytest tests/test_config.py -v && .venv/bin/python -m pytest`
Expected: PASS (whole suite).

- [ ] **Step 7: Commit**

```bash
git add folio/config.py .profile.yml.example folio/cli.py tests/fixtures/sample_config.yml tests/test_config.py
git commit -m "feat(config): add repo link, activity_range, profile email/available; drop stars_earned"
```

---

### Task 2: GitHub data model — homepage, second-link resolution, user email

**Files:**
- Modify: `folio/github.py`
- Modify/Test: `tests/test_github.py`

**Interfaces:**
- Consumes: `RepoEntry.link` (Task 1) via config include entries.
- Produces: `SiteLink{label:str, url:str}`; `RepoData.homepage: str|None`, `RepoData.link: SiteLink|None`; `UserProfile.email: str|None`. Resolution precedence: config `link` → repo `homepage` (label "View site") → `None`.

- [ ] **Step 1: Write failing tests**

Add to `tests/test_github.py`. First update the mock repo factory to set `homepage` (default off) — change the signature and body of `_make_mock_repo`:

```python
def _make_mock_repo(
    name="public-project",
    full_name=None,
    description="A repo",
    language="Python",
    stargazers_count=10,
    pushed_at=None,
    fork=False,
    private=False,
    parent=None,
    readme_content="README content here",
    homepage=None,               # NEW
):
    repo = MagicMock()
    repo.name = name
    # ... existing attrs ...
    repo.homepage = homepage     # NEW
    # ... rest unchanged ...
```

And set `mock_user.email = None` in `_make_mock_github` (add after `mock_user.following = 10`).

Then add tests:

```python
class TestSecondLink:
    def test_link_from_config_wins_with_custom_label(self):
        from folio.github import fetch_github_data
        repo = _make_mock_repo(name="folio", homepage="https://ignored.example")
        config = _make_config(include=[
            {"name": "folio", "link": {"label": "View site", "url": "https://joe.dev/folio"}}
        ])
        # include carries pydantic-style entries in real use; dict is accepted by fetch too
        mock_gh = _make_mock_github([repo])
        with patch("folio.github.get_github_token", return_value="t"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)
        link = result.repos[0].link
        assert link is not None
        assert link.label == "View site"
        assert link.url == "https://joe.dev/folio"

    def test_link_falls_back_to_homepage_as_view_site(self):
        from folio.github import fetch_github_data
        repo = _make_mock_repo(name="folio", homepage="https://joe.dev/folio")
        config = _make_config(include=[{"name": "folio"}])
        mock_gh = _make_mock_github([repo])
        with patch("folio.github.get_github_token", return_value="t"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)
        link = result.repos[0].link
        assert link.label == "View site"
        assert link.url == "https://joe.dev/folio"

    def test_no_link_when_neither(self):
        from folio.github import fetch_github_data
        repo = _make_mock_repo(name="folio", homepage=None)
        config = _make_config(include=[{"name": "folio"}])
        mock_gh = _make_mock_github([repo])
        with patch("folio.github.get_github_token", return_value="t"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(config)
        assert result.repos[0].link is None
        assert result.repos[0].homepage is None
```

Note: `_make_config` in this file builds a `MagicMock`; its `.repos.include` returns whatever list you pass. The fetch code must handle dict entries (it already does for `private_reason`).

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python -m pytest tests/test_github.py -k "SecondLink" -v`
Expected: FAIL (`SiteLink`/`link`/`homepage` don't exist).

- [ ] **Step 3: Implement github.py data-model + resolution**

Add a `SiteLink` dataclass (near the other dataclasses):

```python
@dataclass
class SiteLink:
    label: str
    url: str
```

Add fields to `UserProfile` and `RepoData`:

```python
@dataclass
class UserProfile:
    login: str
    name: str
    avatar_url: str
    bio: str | None
    followers: int
    following: int
    email: str | None = None      # NEW
```

```python
@dataclass
class RepoData:
    # ... existing required fields through html_url ...
    html_url: str
    readme_text: str = ""
    recent_commits: list[str] = field(default_factory=list)
    homepage: str | None = None   # NEW
    link: SiteLink | None = None  # NEW
```

Populate `UserProfile.email` in `fetch_github_data`:

```python
    profile = UserProfile(
        login=user.login,
        name=user.name or "",
        avatar_url=user.avatar_url or "",
        bio=user.bio,
        followers=user.followers,
        following=user.following,
        email=getattr(user, "email", None) or None,   # NEW
    )
```

Extend the include lookup to carry the config link. Replace the `include_map` build so it maps name → `(private_reason, SiteLink|None)`:

```python
    def _entry_link(entry) -> SiteLink | None:
        # dict entry
        if isinstance(entry, dict):
            raw = entry.get("link")
            if isinstance(raw, dict) and raw.get("label") and raw.get("url"):
                return SiteLink(label=raw["label"], url=raw["url"])
            return None
        # pydantic RepoEntry (or attr-style)
        raw = getattr(entry, "link", None)
        if raw is not None and getattr(raw, "label", None) and getattr(raw, "url", None):
            return SiteLink(label=raw.label, url=raw.url)
        return None
```

Build the map (replaces the current `include_map` dict-comprehension body):

```python
    include_map: dict[str, tuple[str | None, SiteLink | None]] | None = None
    if include_list is not None:
        include_map = {}
        for entry in include_list:
            if isinstance(entry, dict):
                repo_name = entry["name"]
                reason = entry.get("private_reason")
            else:
                repo_name = entry.name
                reason = getattr(entry, "private_reason", None)
            include_map[repo_name] = (reason, _entry_link(entry))
```

Update the filter loop's use of `include_map` (membership + reason extraction):

```python
        if include_map is not None:
            if repo.name not in include_map:
                continue
        else:
            if repo.private:
                continue
        if repo.name in exclude_set:
            continue

        private_reason = None
        config_link: SiteLink | None = None
        if include_map is not None:
            private_reason, config_link = include_map.get(repo.name, (None, None))

        rd = _build_repo_data(repo, private_reason=private_reason, config_link=config_link)
        repo_data_list.append(rd)
```

Update `_build_repo_data` to resolve homepage + link:

```python
def _build_repo_data(
    repo: Any,
    private_reason: str | None,
    config_link: SiteLink | None = None,
) -> RepoData:
    fork_parent = None
    if repo.fork and repo.parent is not None:
        fork_parent = repo.parent.full_name

    effective_private_reason = private_reason
    if repo.private and effective_private_reason is None:
        effective_private_reason = "Private repository"

    readme_text = _fetch_readme(repo)
    recent_commits = _fetch_recent_commits(repo, since=None)

    homepage = getattr(repo, "homepage", None) or None
    if config_link is not None:
        link = config_link
    elif homepage:
        link = SiteLink(label="View site", url=homepage)
    else:
        link = None

    return RepoData(
        name=repo.name,
        full_name=repo.full_name,
        description=repo.description,
        language=repo.language,
        stars=repo.stargazers_count,
        last_updated=repo.pushed_at,
        is_fork=repo.fork,
        is_private=repo.private,
        fork_parent=fork_parent,
        private_reason=effective_private_reason,
        html_url=repo.html_url,
        readme_text=readme_text,
        recent_commits=recent_commits,
        homepage=homepage,
        link=link,
    )
```

- [ ] **Step 4: Run tests, verify green**

Run: `.venv/bin/python -m pytest tests/test_github.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add folio/github.py tests/test_github.py
git commit -m "feat(github): resolve second project link (config/homepage) and user email"
```

---

### Task 3: Contribution calendar — pure helpers

**Files:**
- Modify: `folio/github.py`
- Test: `tests/test_github.py`

**Interfaces:**
- Produces: `ContribDay{count:int, level:int}`; `_contribution_level(count, max_count) -> int (0–4)`; `_parse_contribution_calendar(payload: dict) -> tuple[list[list[ContribDay]], int]`; `_compute_streak(weeks) -> int`. All pure (no network).

- [ ] **Step 1: Write failing pure-unit tests**

Add to `tests/test_github.py`:

```python
class TestContributionHelpers:
    def _payload(self, week_counts):
        # week_counts: list of 7-int lists
        return {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
            "totalContributions": sum(c for w in week_counts for c in w),
            "weeks": [
                {"contributionDays": [
                    {"contributionCount": c, "date": "2026-01-01", "weekday": i}
                    for i, c in enumerate(w)
                ]} for w in week_counts
            ]}}}}}

    def test_level_buckets(self):
        from folio.github import _contribution_level
        assert _contribution_level(0, 10) == 0
        assert _contribution_level(1, 100) == 1       # 1% -> low bucket
        assert _contribution_level(50, 100) == 2      # 50%
        assert _contribution_level(75, 100) == 3      # 75%
        assert _contribution_level(100, 100) == 4     # max
        assert _contribution_level(5, 0) == 0         # no max -> 0

    def test_parse_calendar(self):
        from folio.github import _parse_contribution_calendar
        weeks, total = _parse_contribution_calendar(self._payload([[0, 4, 0, 0, 0, 0, 0], [2, 0, 0, 0, 0, 0, 0]]))
        assert total == 6
        assert len(weeks) == 2
        assert len(weeks[0]) == 7
        assert weeks[0][1].count == 4
        assert weeks[0][1].level == 4      # 4 is the max -> level 4
        assert weeks[0][0].level == 0

    def test_streak_counts_trailing_active_days(self):
        from folio.github import _parse_contribution_calendar, _compute_streak
        # last recorded day (today) is 0 -> ignored; two active days before it
        weeks, _ = _parse_contribution_calendar(self._payload([[0, 0, 0, 0, 1, 2, 0]]))
        assert _compute_streak(weeks) == 2

    def test_streak_breaks_on_zero(self):
        from folio.github import _parse_contribution_calendar, _compute_streak
        weeks, _ = _parse_contribution_calendar(self._payload([[3, 0, 5, 5, 5, 5, 5]]))
        assert _compute_streak(weeks) == 5     # last is 5, counts back until the 0

    def test_streak_empty(self):
        from folio.github import _compute_streak
        assert _compute_streak([]) == 0
```

- [ ] **Step 2: Run, verify fail**

Run: `.venv/bin/python -m pytest tests/test_github.py -k "ContributionHelpers" -v`
Expected: FAIL (functions undefined).

- [ ] **Step 3: Implement pure helpers in github.py**

```python
@dataclass
class ContribDay:
    count: int
    level: int


def _contribution_level(count: int, max_count: int) -> int:
    """Map a day's contribution count to a 0–4 intensity level."""
    if count <= 0 or max_count <= 0:
        return 0
    frac = count / max_count
    if frac <= 0.25:
        return 1
    if frac <= 0.5:
        return 2
    if frac <= 0.75:
        return 3
    return 4


def _parse_contribution_calendar(payload: dict) -> tuple[list[list[ContribDay]], int]:
    """Turn a GitHub GraphQL contributionCalendar payload into weeks + total.

    Raises KeyError/TypeError on a malformed payload — callers wrap in try/except.
    """
    cal = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    total = int(cal["totalContributions"])
    raw_weeks = cal["weeks"]
    counts = [int(d["contributionCount"]) for w in raw_weeks for d in w["contributionDays"]]
    max_count = max(counts) if counts else 0
    weeks: list[list[ContribDay]] = []
    for w in raw_weeks:
        days = [
            ContribDay(count=int(d["contributionCount"]),
                       level=_contribution_level(int(d["contributionCount"]), max_count))
            for d in w["contributionDays"]
        ]
        weeks.append(days)
    return weeks, total


def _compute_streak(weeks: list[list[ContribDay]]) -> int:
    """Current consecutive days with contributions, counting back from today.

    A trailing zero (today, not yet done) does not break the streak.
    """
    days = [d for w in weeks for d in w]
    if not days:
        return 0
    start = len(days) - 1
    if days[start].count == 0:
        start -= 1
    streak = 0
    for i in range(start, -1, -1):
        if days[i].count > 0:
            streak += 1
        else:
            break
    return streak
```

- [ ] **Step 4: Run tests, verify green**

Run: `.venv/bin/python -m pytest tests/test_github.py -k "ContributionHelpers" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add folio/github.py tests/test_github.py
git commit -m "feat(github): pure contribution-calendar parse, level, and streak helpers"
```

---

### Task 4: Contribution fetch + wiring + offline test stub

**Files:**
- Modify: `folio/github.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_github.py`

**Interfaces:**
- Consumes: `_parse_contribution_calendar`, `_compute_streak` (Task 3).
- Produces: `StatsData.contribution_weeks: list`, `StatsData.contribution_total: int`; `_fetch_contribution_calendar(token, login, activity_range) -> tuple[list, int]`; `fetch_github_data` now sets `stats.contribution_weeks/contribution_total/streak_days`.

- [ ] **Step 1: Add the offline autouse stub to conftest**

`tests/conftest.py` — so no test touches the network for contributions:

```python
from unittest.mock import patch

@pytest.fixture(autouse=True)
def _no_network_contributions():
    """Block the contribution GraphQL POST by default; tests opt in explicitly."""
    with patch("folio.github.requests.post", side_effect=ConnectionError("blocked in tests")):
        yield
```

- [ ] **Step 2: Write failing tests**

Add to `tests/test_github.py`:

```python
class TestContributionFetch:
    def _resp(self, payload):
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.return_value = payload
        return r

    def test_fetch_parses_when_post_succeeds(self):
        from folio.github import _fetch_contribution_calendar
        payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
            "totalContributions": 5,
            "weeks": [{"contributionDays": [{"contributionCount": 5, "date": "2026-01-01", "weekday": 0}]}]}}}}}
        with patch("folio.github.requests.post", return_value=self._resp(payload)):
            weeks, total = _fetch_contribution_calendar("t", "joe", "3mo")
        assert total == 5
        assert weeks[0][0].count == 5

    def test_fetch_returns_empty_on_failure(self):
        from folio.github import _fetch_contribution_calendar
        # autouse stub already makes requests.post raise
        weeks, total = _fetch_contribution_calendar("t", "joe", "3mo")
        assert weeks == []
        assert total == 0

    def test_fetch_github_data_populates_contributions(self):
        from folio.github import fetch_github_data
        payload = {"data": {"user": {"contributionsCollection": {"contributionCalendar": {
            "totalContributions": 3,
            "weeks": [{"contributionDays": [{"contributionCount": 1, "date": "2026-01-01", "weekday": 0},
                                            {"contributionCount": 2, "date": "2026-01-02", "weekday": 1}]}]}}}}}
        repo = _make_mock_repo()
        mock_gh = _make_mock_github([repo])
        with patch("folio.github.get_github_token", return_value="t"), \
             patch("folio.github.Github", return_value=mock_gh), \
             patch("folio.github.requests.post", return_value=self._resp(payload)):
            result = fetch_github_data(_make_config())
        assert result.stats.contribution_total == 3
        assert len(result.stats.contribution_weeks) == 1
        assert result.stats.streak_days == 2   # last day count=2 (>0), prior=1 (>0)

    def test_fetch_github_data_survives_contribution_failure(self):
        from folio.github import fetch_github_data
        repo = _make_mock_repo()
        mock_gh = _make_mock_github([repo])
        # autouse stub: requests.post raises -> empty, generate must not break
        with patch("folio.github.get_github_token", return_value="t"), \
             patch("folio.github.Github", return_value=mock_gh):
            result = fetch_github_data(_make_config())
        assert result.stats.contribution_weeks == []
        assert result.stats.streak_days == 0
```

- [ ] **Step 3: Run, verify fail**

Run: `.venv/bin/python -m pytest tests/test_github.py -k "ContributionFetch" -v`
Expected: FAIL (`_fetch_contribution_calendar` / new StatsData fields missing).

- [ ] **Step 4: Implement fetch + wiring**

Add `import requests` at the top of `folio/github.py`. Add `contribution_weeks`/`contribution_total` to `StatsData`:

```python
@dataclass
class StatsData:
    commits: int = 0
    pull_requests: int = 0
    issues: int = 0
    streak_days: int = 0
    stars_earned: int = 0
    languages: dict[str, float] = field(default_factory=dict)
    contribution_weeks: list = field(default_factory=list)   # list[list[ContribDay]]
    contribution_total: int = 0
```

Add the network fetch:

```python
_ACTIVITY_DAYS = {"3mo": 90, "6mo": 182, "1yr": 365}

_CONTRIB_QUERY = (
    "query($login:String!,$from:DateTime!,$to:DateTime!){"
    "user(login:$login){contributionsCollection(from:$from,to:$to){"
    "contributionCalendar{totalContributions "
    "weeks{contributionDays{contributionCount date weekday}}}}}}"
)


def _fetch_contribution_calendar(
    token: str, login: str, activity_range: str
) -> tuple[list[list[ContribDay]], int]:
    """Best-effort GitHub GraphQL contribution calendar. Empty on any failure."""
    days = _ACTIVITY_DAYS.get(activity_range, 90)
    to_dt = datetime.now(tz=timezone.utc)
    from_dt = to_dt - timedelta(days=days)
    try:
        resp = requests.post(
            "https://api.github.com/graphql",
            json={"query": _CONTRIB_QUERY, "variables": {
                "login": login, "from": from_dt.isoformat(), "to": to_dt.isoformat()}},
            headers={"Authorization": f"bearer {token}"},
            timeout=10,
        )
        resp.raise_for_status()
        return _parse_contribution_calendar(resp.json())
    except Exception:
        return [], 0
```

Wire into `fetch_github_data` after `stats = _fetch_stats(...)`:

```python
    stats = _fetch_stats(gh, profile.login, since, repo_data_list, config.stats.language_count)

    activity_range = getattr(config.stats, "activity_range", "3mo")
    if not isinstance(activity_range, str):
        activity_range = "3mo"
    weeks, total = _fetch_contribution_calendar(token, profile.login, activity_range)
    stats.contribution_weeks = weeks
    stats.contribution_total = total
    stats.streak_days = _compute_streak(weeks)

    return GitHubData(user=profile, repos=repo_data_list, stats=stats)
```

(The `isinstance` guard keeps the `MagicMock` configs in `test_github` from passing a mock into `.get`.)

- [ ] **Step 5: Run tests, verify green**

Run: `.venv/bin/python -m pytest tests/test_github.py -v && .venv/bin/python -m pytest`
Expected: PASS (whole suite — the autouse stub keeps it offline).

- [ ] **Step 6: Commit**

```bash
git add folio/github.py tests/conftest.py tests/test_github.py
git commit -m "feat(github): fetch contribution calendar, real streak, offline test stub"
```

---

### Task 5: Bundle Instrument Serif

**Files:**
- Create: `folio/static/fonts/instrument-serif-400.woff2`
- Create: `folio/static/fonts/instrument-serif-400-italic.woff2`

**Interfaces:** none (asset only; `_copy_fonts` already ships the whole dir).

- [ ] **Step 1: Download the woff2 files**

```bash
curl -fsSL -o folio/static/fonts/instrument-serif-400.woff2 \
  https://cdn.jsdelivr.net/fontsource/fonts/instrument-serif@latest/latin-400-normal.woff2
curl -fsSL -o folio/static/fonts/instrument-serif-400-italic.woff2 \
  https://cdn.jsdelivr.net/fontsource/fonts/instrument-serif@latest/latin-400-italic.woff2
```

- [ ] **Step 2: Verify both files are real woff2 (non-empty, correct magic bytes)**

Run:
```bash
ls -l folio/static/fonts/instrument-serif-*.woff2 && \
.venv/bin/python -c "import pathlib; [print(p, p.read_bytes()[:4]) for p in pathlib.Path('folio/static/fonts').glob('instrument-serif-*.woff2')]"
```
Expected: both files > 10 KB and first 4 bytes `b'wOF2'`. If the CDN 404s, fall back to google-webfonts-helper (`gwfh.mranftl.com`) for Instrument Serif `400` + `400 italic` woff2, latin subset.

- [ ] **Step 3: Commit**

```bash
git add folio/static/fonts/instrument-serif-400.woff2 folio/static/fonts/instrument-serif-400-italic.woff2
git commit -m "chore(fonts): bundle Instrument Serif (regular + italic)"
```

---

### Task 6: Editorial reskin — CSS + HTML + accent resolution

**REQUIRED SKILL: `frontend-design`.** This is the visual task; drive it with the frontend-design skill and verify in a browser, not by string-matching alone.

**Files:**
- Rewrite: `templates/style.css.j2`
- Rewrite: `templates/profile.html.j2`
- Modify: `folio/render.py` (`_build_context` — accent override)
- Modify/Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `profile` (`name`, `tagline`, `resume_url`, `email`, `available_for_work`, `social`), `user` (`name`, `login`, `email`), `avatar`, `bio`, `repos` (each: `name`, `html_url`, `is_private`/`is_fork`, `language`, `private_reason`, `fork_parent`, `homepage`, `link{label,url}`), `summaries`, `fork_diffs`, `stats` (`commits`, `pull_requests`, `issues`, `streak_days`, `languages`, `contribution_weeks` [`ContribDay.count/level`], `contribution_total`), `stats_show`, `theme`, `accent_override`, `generated_at`, `lang_color`.
- Produces: an Editorial `dist/index.html` + `dist/style.css`. No `★`, no "stars".

**Design contract (from spec + `Folio Redesign.dc.html` option 1A):** full-bleed `--bg` page, centered max-width column (~760–820px content), sections in order: eyebrow (`Portfolio — {year}` + optional `● Available for work`), serif masthead (giant `Instrument Serif` first name + italic serif tagline + round avatar/monogram + Résumé/Email buttons), About paragraph, Stack pills, numbered "Selected work" list, "Activity — last {N} months" heatmap, stat line, "Let's build something." CTA, footer. **No browser-chrome frame.** Token values per the spec's table.

- [ ] **Step 1: Write/adjust render tests (the contract)**

In `tests/test_render.py`:

(a) Extend `_make_stats()` to include a small heatmap and drop reliance on stars:

```python
def _make_stats() -> StatsData:
    from folio.github import ContribDay
    return StatsData(
        commits=150, pull_requests=25, issues=10, streak_days=7, stars_earned=100,
        languages={"Python": 0.6, "Go": 0.3, "TypeScript": 0.1},
        contribution_weeks=[[ContribDay(count=(i % 5), level=(i % 5)) for i in range(7)]],
        contribution_total=42,
    )
```

(b) Give the public repo a second link in `_make_public_repo()`:

```python
    # add to the RepoData(...) call:
        homepage="https://public-project.example",
        link=SiteLink(label="View site", url="https://public-project.example"),
```
…and add `from folio.github import SiteLink` to the imports.

(c) Update the accent test that now inverts, and add new assertions:

```python
class TestEditorialProfile:
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
```

Update the existing `TestRenderStyle.test_accent_resolved_from_languages_when_auto` to assert the terracotta default (config theme is `dark`):

```python
    def test_accent_defaults_to_terracotta_when_auto(self):
        from folio.render import render_style
        result = render_style(_make_enriched_data(), _make_config())
        assert "#ff6a3c" in result     # dark Editorial accent
```
(Delete/replace the old language-derived assertion. Keep `test_accent_explicit_override` — `#ff5500` must still win.)

The existing `test_contains_user_name_in_h1` asserts `<h1>` + name — the masthead keeps an `<h1>`, so it stays valid. Keep `test_tagline_in_output`, `test_public_repo_has_link_to_html_url`, `test_private_repo_shows_private_reason`, `test_private_repo_has_no_link`, `test_fork_shows_fork_diff_text` — the new template must preserve all these behaviors.

- [ ] **Step 2: Run, verify the new ones fail**

Run: `.venv/bin/python -m pytest tests/test_render.py -v`
Expected: new tests FAIL; note which existing ones fail (they guide the rewrite).

- [ ] **Step 3: Accent override in `render.py`**

In `_build_context`, replace the auto-accent block so the template gets an *override-or-none*, and stop language-deriving:

```python
    # Accent: only an explicit hex overrides the themed Editorial default.
    raw_accent = getattr(theme_section, "accent", None) if theme_section else None
    accent_override = raw_accent if (raw_accent and raw_accent != "auto") else None
```

Add `"accent_override": accent_override` to the returned context. (Leave the old `"accent"` key in place for the SVG/readme templates that still use it; those are out of scope. The `get_accent_from_languages` import can stay.)

- [ ] **Step 4: Rewrite `style.css.j2` (frontend-design)**

Build the Editorial stylesheet:
- Keep the existing JetBrains Mono + DM Sans `@font-face` blocks; **add** Instrument Serif:

```css
@font-face {
  font-family: 'Instrument Serif';
  src: url('fonts/instrument-serif-400.woff2') format('woff2');
  font-weight: 400; font-style: normal; font-display: swap;
}
@font-face {
  font-family: 'Instrument Serif';
  src: url('fonts/instrument-serif-400-italic.woff2') format('woff2');
  font-weight: 400; font-style: italic; font-display: swap;
}
```

- Replace the token blocks with the spec's Editorial sets, keeping the same four selectors (`:root` = dark default, `@media (prefers-color-scheme: light)`, `.theme-dark`, `.theme-light`), and adding `--fg-mid`, `--panel`, `--border-strong`, `--accent-ink`, `--heat0`. Define `--sans: 'DM Sans'…`, `--mono: 'JetBrains Mono'…`, `--serif: 'Instrument Serif', Georgia, serif`.
- After the theme blocks, apply the explicit-accent override when set:

```css
{% if accent_override %}
:root, .theme-dark, .theme-light { --accent: {{ accent_override }}; --accent-ink: {{ accent_override }}; }
{% endif %}
```

- Layout per the design (full-bleed `--bg`; centered column; no browser chrome). Implement the classes the HTML uses (below), including a `.heat-cell` day cell whose background derives from its level (0 → `var(--heat0)`; 1–4 → `var(--accent)` at opacity `0.28/0.5/0.74/1`). Match the source design's scale (masthead ~120px serif desktop, italic tagline ~29px, numbered list serif numerals, pill radii, 3px heatmap cell gaps). Responsive: single-column masthead, wrapping work-list rows, horizontally-scrollable heatmap on narrow screens.

- [ ] **Step 5: Rewrite `profile.html.j2` (frontend-design)**

Produce the Editorial structure. Bindings that MUST be preserved for tests: `<h1>` contains the name; public repos link to `html_url`; private repos render `private_reason` and NO `html_url` link; forks show `fork_diffs`/`fork_parent`; tagline appears. New/changed:
- Eyebrow: `Portfolio — {{ generated_at[:4] }}`; `{% if profile and profile.available_for_work %}<span>● Available for work</span>{% endif %}`.
- Masthead first name: `{{ (profile.name or user.name or user.login).split()[0] }}` in serif; italic serif tagline from `profile.tagline`.
- Résumé button if `profile.resume_url`; Email button if `profile.email or user.email` (mailto).
- Stack pills: `{% if "top_languages" in stats_show and stats.languages %}` loop `stats.languages`, dot color `{{ lang | lang_color }}`.
- Selected work: numbered loop over `repos`; per repo name (link when not private), tags (`private`/`fork`/`language`), `summaries`/`fork_diffs`/`description`, fork/private notes — **no stars** — date `last_updated.strftime('%b %Y')`, and:
  `{% if repo.link %}<a href="{{ repo.link.url }}">{{ repo.link.label }} ↗</a>{% endif %}`.
- Activity: `{% if stats.contribution_weeks %}` header `Activity — last {{ {'3mo':3,'6mo':6,'1yr':12}.get(... , 3) }} months` (compute the label from `stats.contribution_weeks|length` weeks, or pass the number — simplest: `{{ (stats.contribution_weeks|length) }} weeks`); render columns of `.heat-cell` divs keyed by `day.level`; legend Less→More; header shows `{{ stats.contribution_total }} contributions`.
- Stat line: only stats in `stats_show` (`commits`/`pull_requests`/`issues`/`streak` → `stats.streak_days`). **No stars tile.**
- CTA + footer (keep the correct `https://github.com/joemc3/folio` link and `generated_at`).

- [ ] **Step 6: Visual verification in a browser**

Render representative output to a scratch dir and open it (no live GitHub needed):

```bash
.venv/bin/python - <<'PY'
from tests.test_render import _make_enriched_data, _make_config
from folio.render import render_profile, render_style
import pathlib, shutil
out = pathlib.Path("/private/tmp/claude-501/-Users-joemc3-tmp-folio/d50ae6fc-94c7-4737-905d-69e56a34d819/scratchpad/preview")
(out / "fonts").mkdir(parents=True, exist_ok=True)
out.joinpath("index.html").write_text(render_profile(_make_enriched_data(), _make_config()))
out.joinpath("style.css").write_text(render_style(_make_enriched_data(), _make_config()))
for f in pathlib.Path("folio/static/fonts").glob("*.woff2"): shutil.copy2(f, out / "fonts" / f.name)
print(out / "index.html")
PY
```

Open the printed path in Chrome (claude-in-chrome). Check: masthead scale, terracotta accent, heatmap cells shaded by level, pills, numbered list, second link on the public repo, no stars, dark↔light both good (toggle `class="theme-light"` on `<html>` to spot-check the light palette). Iterate CSS/HTML until it matches the 1A design, then screenshot for the user.

- [ ] **Step 7: Run the full suite, verify green**

Run: `.venv/bin/python -m pytest`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add templates/style.css.j2 templates/profile.html.j2 folio/render.py tests/test_render.py
git commit -m "feat(site): Editorial redesign — serif masthead, heatmap, second links, no stars"
```

---

### Task 7: Regenerate `dist/`, verify end-to-end, final review

**Files:**
- Modify: `dist/index.html`, `dist/style.css`, `dist/fonts/` (regenerated)

**Interfaces:** none (build output).

- [ ] **Step 1: Regenerate against real data** (needs the user's `gh auth`/token + network)

Run: `.venv/bin/folio generate --no-ai` (add AI on a later real run if desired), then `.venv/bin/folio preview` and open `http://localhost:8000`.
Expected: the real profile renders in the Editorial style; heatmap reflects the configured `activity_range` (default 3mo); no stars; second links appear where a repo has a Website or a `.profile.yml` `link`.

- [ ] **Step 2: Sanity-check the generated site**

Confirm: no `★`/"stars" in `dist/index.html`; `dist/fonts/instrument-serif-400.woff2` present; private repos unlinked; footer link correct. Screenshot dark + light for the user.

- [ ] **Step 3: Full suite once more**

Run: `.venv/bin/python -m pytest`
Expected: PASS.

- [ ] **Step 4: Commit the regenerated site**

```bash
git add dist/
git commit -m "chore(dist): regenerate site with Editorial redesign"
```

- [ ] **Step 5: Finish the branch**

Use superpowers:finishing-a-development-branch to choose merge/PR/cleanup for `editorial-redesign`.

---

## Self-Review

**Spec coverage:** scope (HTML-only) ✔ Task 6; type/palette/tokens ✔ Task 6; section mapping ✔ Task 6 Steps 4–5; second link (config+homepage, precedence, no-link) ✔ Tasks 1–2, 6; heatmap + configurable `activity_range` + real streak ✔ Tasks 1,3,4,6; stars removed everywhere ✔ Global + Tasks 1,6; no browser chrome ✔ Task 6 contract; fonts bundled ✔ Task 5; `available_for_work`/email ✔ Tasks 1,2,6; accent terracotta-default + hex override ✔ Task 6 Step 3; config example sync ✔ Task 1; tests ✔ each task; regenerate dist ✔ Task 7. No uncovered spec requirement.

**Placeholder scan:** data/config tasks (1–4) contain complete code + exact tests. Task 6 is intentionally contract-driven (structure, bindings, token/level rules, browser verification) rather than a verbatim CSS dump, because pixel fidelity is produced iteratively with the frontend-design skill against the named source design — the render tests lock the observable contract.

**Type consistency:** `SiteLink{label,url}` (github) vs `RepoLink{label,url}` (config) — resolution converts config `RepoLink`/dict → `SiteLink` in `_build_repo_data`; template reads `repo.link.label/.url`. `ContribDay{count,level}` used consistently by parse/streak/StatsData/template. `_fetch_contribution_calendar` / `_parse_contribution_calendar` / `_compute_streak` names match across Tasks 3–4. `accent_override` context key matches render.py ↔ style.css.j2. Stat keys (`commits/pull_requests/issues/streak/top_languages`) consistent across config, template, example.

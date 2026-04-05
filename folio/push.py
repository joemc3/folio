"""Git commit and push for Folio."""

from __future__ import annotations

from datetime import datetime, timezone

from git import Repo


def push_profile(repo_path: str) -> None:
    """Stage README.md and dist/, commit, and push to origin."""
    repo = Repo(repo_path)
    repo.index.add(["README.md", "dist"])
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo.index.commit(f"folio: regenerate profile {timestamp}")
    repo.remotes.origin.push(force=False)

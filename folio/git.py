"""Git utilities for Folio — fork diff extraction."""

from __future__ import annotations

import logging
import re

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

logger = logging.getLogger(__name__)

# Lockfiles whose diff hunks should be stripped as noise
_LOCKFILE_PATTERNS = [
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "go.sum",
    "Cargo.lock",
    "poetry.lock",
    "Pipfile.lock",
]

_MAX_DIFF_CHARS = 3000


def _strip_lockfile_hunks(diff: str) -> str:
    """Remove diff hunks for lockfiles from a unified diff string.

    Each top-level file block starts with ``diff --git a/... b/...``.
    Any block whose filename matches a known lockfile is dropped entirely.
    """
    # Split on the "diff --git" header lines, keeping the delimiter
    blocks = re.split(r"(?=^diff --git )", diff, flags=re.MULTILINE)
    kept = []
    for block in blocks:
        if not block:
            continue
        # Check whether this block is for a lockfile
        first_line = block.split("\n", 1)[0]
        if any(lf in first_line for lf in _LOCKFILE_PATTERNS):
            continue
        kept.append(block)
    return "".join(kept)


def get_fork_diff(repo_path: str) -> str | None:
    """Return the diff between HEAD and upstream/HEAD for a forked repository.

    Args:
        repo_path: Filesystem path to the git repository.

    Returns:
        A cleaned, truncated diff string, or ``None`` if the diff cannot be
        obtained (no upstream remote, git error, or not a git repository).
    """
    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        logger.warning("Not a git repository: %s", repo_path)
        return None

    remote_names = [r.name for r in repo.remotes]
    if "upstream" not in remote_names:
        logger.warning("No 'upstream' remote found in %s", repo_path)
        return None

    try:
        raw_diff = repo.git.diff("upstream/HEAD", "HEAD")
    except GitCommandError as exc:
        logger.warning("git diff failed for %s: %s", repo_path, exc)
        return None

    cleaned = _strip_lockfile_hunks(raw_diff)
    return cleaned[:_MAX_DIFF_CHARS]

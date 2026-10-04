# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Resolver code identity (SIG-REL-014, P34.23; G3 §3.2 ★ / §9.3).

``resolver_version`` names the *resolver code* that produced a resolution —
distinct from the reconciliation ruleset (SIG-EXPORT-003). It is the
``resolution`` package version plus the working tree's commit:
``<resolution version>+g<commit8>`` — never the exports placeholder
(the ``0.0.0`` every release carried before REL-10, finding NEW-3/GT-7).

The commit is taken **from the tree, never typed** (GT-7): ``git rev-parse
--short=8 HEAD`` over the repository the source tree lives in. When no git
tree answers (a deployed artifact with no checkout) the suffix is omitted
rather than invented — ``0.1.0`` is honest code identity; a fabricated
commit never is.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

#: The repo root this source tree sits in (exports/src/exports → repo root).
_REPO_ROOT = Path(__file__).resolve().parents[3]


def code_commit8(repo: Path | None = None) -> str:
    """The 8-char commit of ``repo``'s HEAD, or ``""`` when no git tree answers."""
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short=8", "HEAD"],
            cwd=str(repo or _REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    commit = out.stdout.strip()
    return commit if out.returncode == 0 and len(commit) == 8 else ""


def default_resolver_version(*, code_commit: str | None = None) -> str:
    """``<resolution version>+g<commit8>`` — the resolver's code identity.

    ``code_commit`` lets a caller that already resolved the tree's commit
    pass it in; otherwise it is read from git. When no commit can be
    resolved the bare resolution version is returned — still the true
    resolver version, only without the commit suffix.
    """
    from resolution import __version__ as resolution_version

    commit = code_commit if code_commit is not None else code_commit8()
    suffix = commit[:8]
    if suffix and all(c in "0123456789abcdef" for c in suffix.lower()):
        return f"{resolution_version}+g{suffix.lower()}"
    return resolution_version


__all__ = ["code_commit8", "default_resolver_version"]

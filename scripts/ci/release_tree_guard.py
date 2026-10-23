#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""NEW-5 (G3 RM-8, P35.53) recommit guard: real candidate release trees and
staging registries never live in the public repository — under
``docs/build/reports/`` the committed report *files* (manifests, readouts,
exports, snapshots) stay, but the ``r|v|s|releases/p-<pub>/`` trees and the
``staged/`` + registry-file layer (catalog.json, compat_index.json,
withdrawals.json, activations/, events/, latest.json, LOCK) are private
staging state and must never be recommitted.

Usage: ``python scripts/ci/release_tree_guard.py [ROOT …]`` — exits 1 with
the flagged paths named when anything evicted-shaped is found under a root
(default: ``docs/build/reports``). The pytest layer calls
``find_evicted_paths`` directly and also feeds it a synthetic tree so the
guard itself is tested.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path, PurePosixPath

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "docs" / "build" / "reports"

#: A p-<64 lowercase hex> directory is an immutable publication tree —
#: whatever namespace it hangs under.
PUBLICATION_DIR = re.compile(r"^p-[0-9a-f]{64}$")

#: Registry-owned file names — the G3 §4.1 registry namespace
#: (catalog/compat/withdrawals + the publication pointer + the registry lock).
REGISTRY_FILES = {
    "catalog.json",
    "compat_index.json",
    "withdrawals.json",
    "latest.json",
    "LOCK",
}

#: Registry-owned directory names — the staged namespace, the activation
#: receipts and the event journal.
REGISTRY_DIRS = {"staged", "activations", "events"}

#: A directory that is a release-tree or registry ROOT — it contains staged
#: or published namespaces. These names flag only when the directory
#: actually carries release-tree/registry contents (checked in the walk).
_TREE_CONTENT_MARKERS = {"r", "v", "s", "releases"}


def _flags_dir(path: Path) -> str | None:
    name = path.name
    if PUBLICATION_DIR.match(name):
        return f"publication tree directory {name}/"
    if name in REGISTRY_DIRS:
        return f"registry directory {name}/"
    if name in _TREE_CONTENT_MARKERS or name == "release":
        # `r/`, `v/`, `s/`, `releases/`, `release/` are namespace roots only
        # when they carry p-<pub>/ children or releases/<pub>/+r/<pub>/ pairs;
        # a bare empty namespace dir is still private-staging shape.
        children = {c.name for c in path.iterdir() if c.is_dir()}
        if any(PUBLICATION_DIR.match(c) for c in children):
            return f"release namespace directory {name}/ carrying p-<pub>/ trees"
        if name in _TREE_CONTENT_MARKERS and path.parent.name == "staged":
            return f"staged release namespace {path.parent.name}/{name}/"
    return None


def find_evicted_paths(root: Path | str) -> list[str]:
    """All paths under ``root`` shaped like committed release trees or
    registry state — the NEW-5 eviction's recommit surface."""
    root = Path(root)
    if not root.exists():
        return []
    flagged: list[str] = []
    for path in sorted(root.rglob("*")):
        rel = PurePosixPath(path.relative_to(root))
        if path.is_dir():
            why = _flags_dir(path)
            if why is not None:
                flagged.append(f"{rel}  ({why})")
        elif path.name in REGISTRY_FILES:
            flagged.append(f"{rel}  (registry file {path.name})")
    return flagged


def main(argv: list[str]) -> int:
    roots = [Path(a) for a in argv[1:]] or [DEFAULT_ROOT]
    flagged: list[str] = []
    for root in roots:
        for hit in find_evicted_paths(root):
            flagged.append(f"{root}: {hit}")
    if flagged:
        print(
            "release-tree guard REFUSED — committed release trees / registry "
            "state under a reports root (G3 NEW-5 / RM-8):",
            file=sys.stderr,
        )
        for hit in flagged:
            print(f"  {hit}", file=sys.stderr)
        return 1
    print(f"release-tree guard: clean ({len(roots)} root(s) scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

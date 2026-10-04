# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""`resolver_version` = resolution version + `+g<commit8>` (SIG-REL-014, G3 §3.2 ★).

Never the exports placeholder — the ``0.0.0`` the 09-27 manifest carried
(NEW-3/GT-7). The commit is taken from the tree, never typed.
"""

from __future__ import annotations

import re

from exports.versioning import code_commit8, default_resolver_version

import resolution


def test_default_resolver_version_is_resolution_plus_commit() -> None:
    rv = default_resolver_version()
    assert rv != "0.0.0"
    # In the repo checkout git answers, so the full contract holds:
    # <resolution __version__>+g<8 lowercase hex>.
    assert re.fullmatch(rf"{re.escape(resolution.__version__)}\+g[0-9a-f]{{8}}", rv), (
        f"resolver_version {rv!r} must be <resolution version>+g<commit8>"
    )


def test_explicit_code_commit_is_used() -> None:
    rv = default_resolver_version(code_commit="deadbeefcafe")
    assert rv == f"{resolution.__version__}+gdeadbeef"


def test_non_commit_suffix_is_dropped_not_invented() -> None:
    """A caller-typed non-hex revision degrades to the bare version —
    honest identity, never a fabricated +g suffix."""
    assert default_resolver_version(code_commit="unknown") == resolution.__version__


def test_code_commit8_reads_the_tree() -> None:
    commit = code_commit8()
    assert re.fullmatch(r"[0-9a-f]{8}", commit)


def test_code_commit8_outside_a_repo_is_empty() -> None:
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        assert code_commit8(Path(tmp)) == ""

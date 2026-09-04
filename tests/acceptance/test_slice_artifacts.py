# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The committed slice artifacts: the written retrospective (P06.1 AC5) and the
hardness-precondition declaration (AC6)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_SLICE = _ROOT / "docs" / "slice"


def test_retrospective_is_committed_and_substantive() -> None:
    # AC5: a written retrospective recording what the design got wrong on real data.
    path = _SLICE / "P06.1_retrospective.md"
    assert path.exists(), "the slice retrospective MUST be committed (HARD GATE §54)"
    text = path.read_text()
    # a retrospective, not a stub: it must name real findings.
    assert len(text) > 2000, "retrospective is too thin to be a real retrospective"
    for anchor in ("Oklahoma City", "count", "PREDICATE_CONFLATION", "what the design got wrong"):
        assert anchor in text, f"retrospective missing {anchor!r}"


def test_precondition_declaration_is_committed() -> None:
    assert (_SLICE / "P06.1_hardness_precondition.md").exists()

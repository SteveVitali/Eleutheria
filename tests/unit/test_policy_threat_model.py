# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The threat model as a maintained, versioned artifact (§44, SIG-SEC-001)."""

from __future__ import annotations

import pytest

from policy import threat_model as tm


def test_threat_model_is_versioned() -> None:
    assert tm.threat_model_version()


def test_every_adversary_row_maps_to_a_defined_requirement_id() -> None:
    rows = tm.load_threat_model()
    assert rows
    for row in rows:
        assert any(tm.is_requirement_id(m) for m in row.mitigations), row.adversary
    # The whole artifact validates against the phase-gate invariant.
    tm.validate_threat_model(rows)


def test_shipped_threat_model_validates() -> None:
    tm.validate_threat_model()  # does not raise


def test_a_row_with_no_mapped_requirement_fails_the_gate() -> None:
    bad = (tm.ThreatRow(adversary="X", objective="Y", mitigations=("conservative crawling",)),)
    with pytest.raises(tm.ThreatModelError):
        tm.validate_threat_model(bad)


def test_empty_threat_model_fails_the_gate() -> None:
    with pytest.raises(tm.ThreatModelError):
        tm.validate_threat_model(())


@pytest.mark.parametrize(
    "token,ok",
    [
        ("SIG-PUB-007", True),
        ("SIG-LIC-004a", True),
        ("SIG-PUB-014a", True),
        ("§45", False),
        ("crawler conduct", False),
        ("PUB-007", False),
    ],
)
def test_requirement_id_recognition(token: str, ok: bool) -> None:
    assert tm.is_requirement_id(token) is ok

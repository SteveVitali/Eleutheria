# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The quality-check registry contract (P34.44a, SIG-CONF-006, ADR-154 d.1):
all 27 deduplicated checks GQ-01…GQ-27, declared fields, valid vocabularies,
fixing rows that resolve, and the SIG-CONF-003 rule that B3/B4 evidence may
never gate."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
from exports.quality import (
    BASIS_CLASSES,
    CHECK_ID_RE,
    GATING_BASIS_CLASSES,
    MODES,
    PLACEMENTS,
    SCHEMA,
    CheckRegistry,
    QualityCheck,
    RegistryError,
    Threshold,
    load_registry,
    validate_registry,
)
from support import REPO_ROOT

MANIFEST = REPO_ROOT / "docs/tickets/00_MANIFEST.md"


def _manifest_rows() -> set[str]:
    """The ticket ids the manifest declares — used for *reference resolution*
    (allowed under BM-TEST-01; we never assert a manifest value)."""
    return set(re.findall(r"\d+_(P\d+\.\d+[a-z]?)__", MANIFEST.read_text(encoding="utf-8")))


def _doc() -> dict:
    return tomllib.loads(
        (REPO_ROOT / "exports/src/exports/data/quality_checks.toml").read_text(encoding="utf-8")
    )


def test_registry_loads_clean() -> None:
    registry = load_registry()
    assert registry.version == "1"
    assert registry.digest


def test_registry_declares_exactly_gq01_through_gq27() -> None:
    registry = load_registry()
    ids = [c.check_id for c in registry.checks]
    assert len(ids) == 27
    assert sorted(ids) == [f"GQ-{i:02d}" for i in range(1, 28)]
    assert len(set(ids)) == len(ids)


def test_every_check_carries_the_sig_conf_006_fields() -> None:
    for c in load_registry().checks:
        assert CHECK_ID_RE.match(c.check_id)
        assert c.statement.strip()
        assert c.population.strip()
        assert c.source_ids.strip()
        assert c.placement and c.placement <= PLACEMENTS
        assert c.mode in MODES
        assert c.basis_class in BASIS_CLASSES
        assert c.unit in {"count", "share", "ratio"}
        assert c.threshold.op in {"none", "<=", "<", ">", ">=", "=="}


def test_every_fixing_row_resolves_to_a_manifest_ticket() -> None:
    """ADR-154: each check names the ticket(s) that will fix it — the rows must
    be real manifest tickets (reference resolution, not a value pin)."""
    known = _manifest_rows()
    fixing = {row for c in load_registry().checks for row in c.fixing}
    assert fixing
    assert fixing <= known


def test_only_mechanical_checks_gate() -> None:
    """SIG-CONF-003: enforce/ratchet modes gate; B3/B4 may never gate."""
    for c in load_registry().checks:
        if c.mode in ("enforce", "ratchet"):
            assert c.basis_class in GATING_BASIS_CLASSES, c.check_id


def test_ratchet_checks_declare_a_baseline() -> None:
    for c in load_registry().checks:
        if c.mode == "ratchet":
            assert c.baseline is not None or c.baseline_pending, c.check_id


def test_seed_posture_matches_the_contract() -> None:
    """The contract pins which checks start in each mode."""
    by_id = load_registry().by_id()
    assert by_id["GQ-20"].mode == "enforce"  # release diff
    assert by_id["GQ-24"].mode == "enforce"  # inferential auto-write lock
    assert by_id["GQ-27"].mode == "enforce"  # basis/claim markers
    assert by_id["GQ-22"].mode == "report" and by_id["GQ-22"].basis_class == "B3"
    assert by_id["GQ-05"].mode == "report"  # key stability — report
    assert by_id["GQ-19"].mode == "report"  # upstream reconciliation — report
    assert by_id["GQ-21"].mode == "report"  # accountability join — report


def test_validator_rejects_missing_fields_and_bad_vocab(tmp_path: Path) -> None:
    bad = {
        "version": "1",
        "schema": SCHEMA,
        "check": [
            {
                "id": "XX-01",
                "statement": "",
                "placement": ["Z"],
                "mode": "sometimes",
                "direction": "sideways",
                "threshold": "about five",
                "unit": "kg",
                "basis_class": "B9",
                "fixing": "P35.1",
            }
        ],
    }
    errors = validate_registry(bad)
    assert errors
    joined = "\n".join(errors)
    for fragment in (
        "id must match",
        "statement",
        "placement",
        "mode",
        "direction",
        "threshold",
        "unit",
        "basis_class",
        "fixing",
    ):
        assert fragment in joined
    path = tmp_path / "bad.toml"
    path.write_text("[check]\n")
    with pytest.raises(RegistryError):
        load_registry(path)


def test_validator_rejects_a_gating_b3_check() -> None:
    """SIG-CONF-003, mechanically: the registry refuses to load a check that
    gates on agent-labelled or maintainer-check evidence."""
    doc = _doc()
    doc["check"] = [
        c
        for c in doc["check"]
        if c["id"] != "GQ-22"  # keep the parse minimal
    ][:1]
    row = dict(doc["check"][0])
    row.update(mode="enforce", basis_class="B3")
    doc["check"] = [row]
    errors = validate_registry(doc)
    assert any("may never gate" in e for e in errors)


def test_validator_flags_unknown_fixing_rows() -> None:
    doc = _doc()
    row = dict(doc["check"][0])
    row["fixing"] = ["P99.99"]
    doc["check"] = [row]
    errors = validate_registry(doc, known_rows=_manifest_rows())
    assert any("not a manifest row" in e for e in errors)


def test_threshold_grammar_and_semantics() -> None:
    assert Threshold.parse("none").op == "none"
    assert Threshold.parse("<= 0").allows(0)
    assert not Threshold.parse("<= 0").allows(1)
    assert Threshold.parse("< 0.5").allows(0.4)
    assert Threshold.parse(">= 0.999").allows(0.999)
    assert Threshold.parse("== 1").allows(1)
    with pytest.raises(RegistryError):
        Threshold.parse("<= soon")
    with pytest.raises(RegistryError):
        Threshold.parse(5)


def test_registry_is_versioned_and_digest_stable() -> None:
    a, b = load_registry(), load_registry()
    assert a.digest == b.digest  # deterministic content digest


@pytest.mark.parametrize("check_id", ["GQ-01", "GQ-27"])
def test_single_check_dataclass_is_immutable(check_id: str) -> None:
    import dataclasses

    check = load_registry().by_id()[check_id]
    with pytest.raises(dataclasses.FrozenInstanceError):
        check.mode = "report"  # type: ignore[misc]


def test_registry_type() -> None:
    registry = load_registry()
    assert isinstance(registry, CheckRegistry)
    assert all(isinstance(c, QualityCheck) for c in registry.checks)

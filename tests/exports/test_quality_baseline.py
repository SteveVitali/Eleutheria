# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The L2 baseline machinery (P34.44b, SIG-CONF-006/007, ADR-205): the
``sig.quality-baseline/1`` record, the measured-baseline proposal, the
``baseline_run``/``baseline_at`` provenance pair, and
:func:`apply_baselines` — the only registry writer of measured baselines,
re-diffed against the ratchet rules so a loosening can never be written."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from exports.quality import (
    BASELINE_AT_RE,
    BASELINE_VERSION,
    CheckRegistry,
    RegistryError,
    apply_baselines,
    baseline_proposal,
    build_baseline_record,
    load_registry,
    validate_registry,
)
from support import REPO_ROOT

REGISTRY_PATH = REPO_ROOT / "exports/src/exports/data/quality_checks.toml"


def _report(checks: dict[str, dict], placement: str = "M") -> dict:
    """A minimal sig.quality-report/1 shape with the given check rows."""
    return {
        "version": "sig.quality-report/1",
        "placement": placement,
        "checks": [{"id": cid, **row} for cid, row in checks.items()],
        "summary": {"overall": "pass"},
        "totals": {},
    }


def _registry_with_baseline(*, pending: bool = False, value: float = 10.0) -> CheckRegistry:
    """A one-check registry over the real validator: keep only GQ-14's block
    with its baseline line rewritten to the fixture value."""
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^\[\[check\]\])", text, flags=re.M)
    head = blocks[0]
    fixture = next(b for b in blocks if 'id = "GQ-14"' in b)
    if pending:
        fixture = re.sub(r"^baseline\s*=.*$", 'baseline = "pending"', fixture, flags=re.M)
    else:
        fixture = re.sub(r"^baseline\s*=.*$", f"baseline = {value:g}", fixture, flags=re.M)
    reg_path = _write(head + fixture)
    return load_registry(reg_path)


_TMPS: list[Path] = []


def _write(text: str) -> Path:
    import tempfile

    fd, name = tempfile.mkstemp(suffix=".toml")
    p = Path(name)
    p.write_text(text, encoding="utf-8")
    _TMPS.append(p)
    return p


# --- the provenance pair in the validator ---------------------------------------


def _check_doc(extra: str = "") -> dict:
    import tomllib

    head = """
schema = "sig.quality-checks/1"
version = "1"

[[check]]
id = "GQ-01"
statement = "s"
population = "p"
placement = ["M"]
mode = "ratchet"
direction = "lower_is_better"
threshold = "<= 0"
baseline = 5
unit = "count"
basis_class = "B1"
fixing = ["P35.29"]
from = "L2"
"""
    return tomllib.loads(head + extra)


def test_baseline_provenance_pair_validates() -> None:
    doc = _check_doc('\nbaseline_run = "baseline-x"\nbaseline_at = "2026-10-14"\n')
    # validator appends to the check table — the extra lines must sit INSIDE
    # [[check]]; put them before the closing table by appending after `from`.
    errors = validate_registry(doc)
    assert errors == []


def test_baseline_run_without_at_is_refused() -> None:
    doc = _check_doc()
    doc["check"][0]["baseline_run"] = "baseline-x"
    errors = validate_registry(doc)
    assert any("land together" in e for e in errors)


def test_baseline_at_must_be_a_date() -> None:
    doc = _check_doc()
    doc["check"][0]["baseline_run"] = "baseline-x"
    doc["check"][0]["baseline_at"] = "10/14/2026"
    errors = validate_registry(doc)
    assert any("YYYY-MM-DD" in e for e in errors)


def test_baseline_run_on_pending_baseline_is_refused() -> None:
    doc = _check_doc()
    doc["check"][0]["baseline"] = "pending"
    doc["check"][0]["baseline_run"] = "baseline-x"
    doc["check"][0]["baseline_at"] = "2026-10-14"
    errors = validate_registry(doc)
    assert any("not a measured value" in e for e in errors)


# --- the proposal ----------------------------------------------------------------


def test_proposal_baselines_a_pending_check_from_measurement() -> None:
    reg = _registry_with_baseline(pending=True)
    reports = {"R": _report({"GQ-14": {"measured": 0, "outcome": "pass"}}, "R")}
    proposal = baseline_proposal(reg, reports)
    assert len(proposal) == 1
    row = proposal[0]
    assert row["state"] == "baselined"
    assert row["proposed"] == 0.0
    assert row["placement"] == "R"


def test_proposal_tightens_only_toward_the_threshold() -> None:
    reg = _registry_with_baseline(value=10.0)  # direction lower_is_better
    reports = {"R": _report({"GQ-14": {"measured": 3, "outcome": "pass"}}, "R")}
    row = baseline_proposal(reg, reports)[0]
    assert row["state"] == "tightened" and row["proposed"] == 3.0
    # A worse measured value is a recorded regression — the baseline stands.
    reports = {
        "R": _report({"GQ-14": {"measured": 40, "outcome": "fail", "regression": True}}, "R")
    }
    row = baseline_proposal(reg, reports)[0]
    assert row["state"] == "regression_kept"
    assert row["proposed"] == 10.0  # never loosened


def test_proposal_marks_unevaluated_checks_not_measured() -> None:
    reg = _registry_with_baseline(value=10.0)
    reports = {"R": _report({"GQ-14": {"outcome": "not_evaluable", "reason": "no scan dir"}}, "R")}
    row = baseline_proposal(reg, reports)[0]
    assert row["state"] == "not_measured" and row["proposed"] is None


def test_proposal_ignores_enforce_and_report_checks() -> None:
    reg = load_registry()  # the committed registry — only ratchet rows proposed
    reports = {"M": _report({})}
    proposal = baseline_proposal(reg, reports)
    modes = {c.mode for c in reg.checks if c.check_id in {r["check"] for r in proposal}}
    assert modes == {"ratchet"}


# --- the record ---------------------------------------------------------------------


def test_build_baseline_record_shape() -> None:
    reg = load_registry()
    reports = {
        "M": _report({"GQ-03": {"measured": 1, "outcome": "fail"}}, "M"),
        "R": _report({"GQ-14": {"measured": 0, "outcome": "pass"}}, "R"),
    }
    record = build_baseline_record(
        registry=reg, reports=reports, target="hosted-spine", run_id="baseline-t"
    )
    assert record["version"] == BASELINE_VERSION
    assert record["run_id"] == "baseline-t"
    assert record["registry"]["digest"] == reg.digest
    assert record["placements"] == ["M", "R"]
    assert len(record["l2_comparison"]) == len(reg.checks)
    assert record["counts"]["checks"] == len(reg.checks)
    # GQ-03 failed → a named finding carrying its fixing rows.
    checks = {f["check"] for f in record["findings"]}
    assert "GQ-03" in checks
    finding = next(f for f in record["findings"] if f["check"] == "GQ-03")
    assert finding["fixing"]
    # Unevaluated checks show up as not_run in the comparison, not as failures.
    row = next(r for r in record["l2_comparison"] if r["id"] == "GQ-01")
    assert row["outcome"] in {"not_run", "not_evaluable"}


# --- apply_baselines: the only writer ------------------------------------------------


def _registry_text_for_gq14(baseline: str) -> str:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    blocks = re.split(r"(?=^\[\[check\]\])", text, flags=re.M)
    head = blocks[0]
    gq14 = next(b for b in blocks if 'id = "GQ-14"' in b)
    gq14 = re.sub(r"^baseline\s*=.*$", baseline, gq14, flags=re.M)
    return head + gq14


def test_apply_baselines_resolves_pending_and_stamps_provenance() -> None:
    text = _registry_text_for_gq14('baseline = "pending"')
    proposal = [{"check": "GQ-14", "proposed": 0.0}]
    new_text = apply_baselines(
        text, proposal, run_id="baseline-2026-10-14", at="2026-10-14", ticket="P34.44b"
    )
    assert "baseline = 0" in new_text
    assert 'baseline_run = "baseline-2026-10-14"' in new_text
    assert 'baseline_at = "2026-10-14"' in new_text
    assert 'baseline = "pending"' not in new_text
    # The rewritten registry still validates.
    p = _write(new_text)
    reg = load_registry(p)
    check = reg.by_id()["GQ-14"]
    assert check.baseline == 0.0
    assert check.baseline_run == "baseline-2026-10-14"
    assert check.baseline_at == "2026-10-14"


def test_apply_baselines_preserves_untouched_blocks_byte_for_byte() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")
    proposal = [{"check": "GQ-14", "proposed": 0.0}]
    new_text = apply_baselines(text, proposal, run_id="r", at="2026-10-14", ticket="P34.44b")
    # Every line outside GQ-14's block is identical.
    old_blocks = re.split(r"(?=^\[\[check\]\])", text, flags=re.M)
    new_blocks = re.split(r"(?=^\[\[check\]\])", new_text, flags=re.M)
    assert len(old_blocks) == len(new_blocks)
    for old_b, new_b in zip(old_blocks, new_blocks, strict=True):
        if 'id = "GQ-14"' in old_b:
            continue
        assert old_b == new_b


def test_apply_baselines_refuses_a_loosening() -> None:
    text = _registry_text_for_gq14("baseline = 5")
    proposal = [{"check": "GQ-14", "proposed": 99.0}]  # worse — never writable
    with pytest.raises(RegistryError, match="illegal ratchet move"):
        apply_baselines(text, proposal, run_id="r", at="2026-10-14", ticket="P34.44b")


def test_apply_baselines_refuses_unknown_checks() -> None:
    text = _registry_text_for_gq14('baseline = "pending"')
    proposal = [{"check": "GQ-99", "proposed": 1.0}]
    with pytest.raises(RegistryError, match="unknown checks"):
        apply_baselines(text, proposal, run_id="r", at="2026-10-14", ticket="P34.44b")


def test_apply_baselines_refuses_bad_inputs() -> None:
    text = _registry_text_for_gq14('baseline = "pending"')
    with pytest.raises(RegistryError, match="run_id"):
        apply_baselines(text, [], run_id="", at="2026-10-14", ticket="P34.44b")
    with pytest.raises(RegistryError, match="YYYY-MM-DD"):
        apply_baselines(text, [], run_id="r", at="yesterday", ticket="P34.44b")


def test_apply_baselines_rewrites_stale_provenance() -> None:
    """A second apply overwrites baseline_run/baseline_at — one writer,
    current provenance only."""
    text = _registry_text_for_gq14("baseline = 5")
    text = text.replace(
        'unit = "count"',
        'baseline_run = "old-run"\nbaseline_at = "2026-01-01"\nunit = "count"',
        1,
    )
    proposal = [{"check": "GQ-14", "proposed": 2.0}]  # tighter — legal
    new_text = apply_baselines(text, proposal, run_id="new-run", at="2026-10-14", ticket="P34.44b")
    assert 'baseline_run = "new-run"' in new_text
    assert "old-run" not in new_text
    assert new_text.count("baseline_run") == 1


# --- the end-to-end apply through the CLI path ------------------------------------


def test_apply_end_to_end_from_a_record(tmp_path: Path) -> None:
    """baseline record → apply_baselines over the committed registry text —
    the same path `sig-exports quality apply-baselines` drives."""
    text = _registry_text_for_gq14('baseline = "pending"')
    reg = load_registry(_write(text))
    reports = {"R": _report({"GQ-14": {"measured": 0, "outcome": "pass"}}, "R")}
    record = build_baseline_record(
        registry=reg, reports=reports, target="hosted-spine", run_id="baseline-e2e"
    )
    new_text = apply_baselines(
        text,
        record["proposal"],
        run_id=record["run_id"],
        at="2026-10-14",
        ticket="P34.44b",
        adr_ids=("ADR-205",),
    )
    reg2 = load_registry(_write(new_text))
    assert reg2.by_id()["GQ-14"].baseline == 0.0


def test_baseline_at_re() -> None:
    assert BASELINE_AT_RE.match("2026-10-14")
    assert not BASELINE_AT_RE.match("2026-1-4")
    assert not BASELINE_AT_RE.match("14-10-2026")

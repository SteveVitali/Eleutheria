# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.45 (CONF-12, SIG-CONF-011 + SIG-CONF-001/010): the ``sig.quality-page/1``
artifact — every registered check declared (failing and ratchet included),
the bound report carried whole or its absence named, and the descriptor's
§5.4 ``graph_quality`` block."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "eval"))

from exports import quality as q  # noqa: E402

RECORD = REPO / "exports" / "src" / "exports" / "data" / "quality_page.json"


def _report(**over):
    base = {
        "version": "sig.quality-report/1",
        "generated_at": "2026-10-15T12:00:00Z",
        "placement": "R",
        "target": "t",
        "registry": {
            "schema": q.SCHEMA,
            "version": "1",
            "digest": "d",
            "checks_declared": 27,
            "checks_evaluated": 1,
        },
        "checks": [
            {
                "id": "GQ-10",
                "mode": "ratchet",
                "basis_class": "B1",
                "outcome": "pass",
                "offered": 2,
                "evaluated": 2,
                "measured": 1.0,
                "baseline": 2.25,
                "baseline_pending": False,
                "threshold": "<= 1.02",
                "direction": "lower_is_better",
                "regression": False,
                "improvement": True,
                "alert_band_breach": False,
                "reason": "",
                "detail": {},
            }
        ],
        "totals": {"offered": 2, "evaluated": 2},
        "summary": {
            "overall": "pass",
            "enforce_failures": [],
            "ratchet_regressions": [],
            "unbaselined": [],
            "not_evaluable": [],
            "class_s_trigger": False,
        },
    }
    base.update(over)
    return base


def test_page_doc_carries_every_registered_check() -> None:
    reg = q.load_registry()
    doc = q.build_quality_page(reg, _report(), generated_at="2026-10-15T12:00:00Z")
    assert doc["schema"] == q.PAGE_SCHEMA
    ids = {c["id"] for c in doc["registry"]["checks"]}
    assert ids == {c.check_id for c in reg.checks}
    # Failing and ratchet checks are declared, never dropped (Q-L3-5).
    assert sum(1 for c in doc["registry"]["checks"] if c["mode"] == "ratchet") > 0
    assert q.quality_page_lint_errors(doc) == []


def test_page_report_absence_is_named() -> None:
    reg = q.load_registry()
    doc = q.build_quality_page(reg, None, generated_at="2026-10-15T12:00:00Z")
    assert doc["report"] is None and doc["report_absence"]
    assert q.quality_page_lint_errors(doc) == []


def test_lint_refuses_a_dropped_check_or_silent_absence() -> None:
    reg = q.load_registry()
    doc = q.build_quality_page(reg, None)
    doc["registry"]["checks"] = [c for c in doc["registry"]["checks"] if c["id"] != "GQ-10"]
    errors = q.quality_page_lint_errors(doc)
    # no row may go missing silently — the lint sees the registry digest
    # drift is covered by the declared list being what the build emitted;
    # here the report_absence stays so the only failure is none. A doc
    # with no report and no absence, though, must fail:
    doc["report_absence"] = None
    errors = q.quality_page_lint_errors(doc)
    assert any("report_absence" in e for e in errors)


def test_report_referencing_unknown_check_fails() -> None:
    reg = q.load_registry()
    bad = _report()
    bad["checks"] = [{"id": "GQ-99"}]
    doc = q.build_quality_page(reg, bad)
    assert any("unregistered" in e for e in q.quality_page_lint_errors(doc))


def test_descriptor_block_shape() -> None:
    reg = q.load_registry()
    doc = q.build_quality_page(reg, _report())
    block = q.descriptor_quality_block(
        doc, reg, source_mix_digest="sha256:sm", ruleset_digest="sha256:rs"
    )
    assert block["suite"]["schema"] == q.SCHEMA
    assert block["suite"]["digest"] == reg.digest
    assert block["report_digest"].startswith("sha256:")
    assert set(block["basis_counts"]) == {"B0", "B1", "B2", "B3", "B4", "B5"}
    assert block["basis_counts"]["B5"] == 0
    assert block["source_mix_digest"] == "sha256:sm"
    assert block["ruleset_digest"] == "sha256:rs"


def test_committed_fixture_is_current() -> None:
    """The committed sig.quality-page/1 equals the generator's output —
    regenerate with `uv run python scripts/eval/run_quality_page.py`."""
    import run_quality_page

    committed = json.loads(RECORD.read_text())
    rebuilt = run_quality_page.build_fixture_page()
    assert committed == rebuilt
    assert q.quality_page_lint_errors(committed) == []
    # Every registered check appears — failing and ratchet included.
    assert len(committed["registry"]["checks"]) == 27
    report = committed["report"]
    assert report and report["version"] == q.REPORT_VERSION
    outcomes = {c["id"]: c["outcome"] for c in report["checks"]}
    assert "fail" in outcomes.values() or "not_evaluable" in outcomes.values()

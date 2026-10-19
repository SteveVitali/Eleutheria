# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The officer-naming gate at the web-dossier builder (P35.28, §43.4, H-9).

The gate binds at the BUILDER so every dossier surface the bundle feeds — the
page, the print export, the JSON endpoint, the index — inherits it: a
``isPublicEmployeeName`` row shows only when a persisted two-reviewer
concurrence names its ``(subject_id, predicate_id)`` AND the jurisdiction rule
permits (SIG-PUB-017); everything else withholds with the refusal recorded on
the row (§3.1 — never silently dropped).
"""

from __future__ import annotations

from typing import Any

from exports.web_dossier import build_web_dossiers
from policy.officer import (
    OfficerNamingProngs,
    OfficerNamingRecord,
    ReviewerConcurrence,
    decision_to_record,
    evaluate_officer_naming,
)


def _name_rows(dossier: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for section in dossier["sections"]
        for row in section.get("rows", [])
        if row.get("isPublicEmployeeName")
    ]


def _concur_record(subject_id: str, predicate_id: str) -> OfficerNamingRecord:
    decision = evaluate_officer_naming(
        OfficerNamingProngs(True, True, True, True, True),
        (
            ReviewerConcurrence("reviewer-a", True, "official conduct on the record"),
            ReviewerConcurrence("reviewer-b", True, "claim fails without the name"),
        ),
    )
    assert decision.permitted
    return decision_to_record(
        subject_id,
        predicate_id,
        decision,
        recorded_at="2026-10-14T00:00:00Z",
        recorded_by="operator (recorded two-reviewer act)",
    )


def test_builder_withholds_an_unrecorded_name_row() -> None:
    # The committed registry is empty — no two-reviewer concurrence has been
    # recorded (ADR-163) — so the OKC dossier's Approving-official row is
    # withheld at build, whatever US-DEFAULT's jurisdiction leg says.
    dossier = build_web_dossiers("okc")[0]
    rows = _name_rows(dossier)
    assert rows, "the OKC dossier must carry a flagged officer-name row"
    for row in rows:
        assert row["withheld"] is True
        assert row["value"] is None
        assert "default deny" in row["note"]
        assert row["subject_id"] and row["predicate_id"]


def test_builder_shows_a_recorded_concurrence() -> None:
    # With an injected concur record (the test seam — the committed registry
    # stays empty) the same row shows and carries the decision id as provenance.
    record = _concur_record("agency:okcpd", "approving_official")
    dossier = build_web_dossiers("okc", naming_decisions=[record])[0]
    row = _name_rows(dossier)[0]
    assert row.get("withheld") is not True
    assert row["value"] == "Chief Wade Gourley"
    assert row["namingDecisionId"] == record.decision_id


def test_builder_withholds_on_deny_and_on_restrictive_jurisdiction() -> None:
    # A non-concur record withholds even in a permissive jurisdiction …
    deny = decision_to_record(
        "agency:okcpd",
        "approving_official",
        evaluate_officer_naming(
            OfficerNamingProngs(True, True, True, True, True),
            (ReviewerConcurrence("reviewer-a", True, "ok"),),  # one reviewer only
        ),
        recorded_at="2026-10-14T00:00:00Z",
        recorded_by="test",
    )
    dossier = build_web_dossiers("okc", naming_decisions=[deny])[0]
    row = _name_rows(dossier)[0]
    assert row["withheld"] is True and row["value"] is None
    assert row["namingDecisionId"] == deny.decision_id  # the recorded refusal
    # … and a concur record withholds where the jurisdiction leg denies (FR).
    fr_record = _concur_record("agency:france:prefecture-ain", "signing_officer")
    fr = build_web_dossiers("france", naming_decisions=[fr_record])[0]
    fr_row = _name_rows(fr)[0]
    assert fr_row["withheld"] is True and fr_row["value"] is None
    assert "SIG-PUB-017" in fr_row["note"]

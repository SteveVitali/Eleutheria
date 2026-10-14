# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The persisted officer-naming gate on the publication path (P35.28).

``sig.officer-naming-decisions/1`` is the append-only record the export/web
publication path reads; ``employee_name_publishable`` composes the persisted
concurrence (SIG-PUB-007/008) with the jurisdiction rule (SIG-PUB-017) — both
legs or withhold. These tests assert the invariants, never the living state of
the registry (OM-15): the committed table starts empty because no two-reviewer
naming concurrence has been recorded (the sole-maintainer self-concurrence in
``docs/build/reports/okc/concurrence.md`` is not independent — ADR-163).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from policy.officer import (
    NAMING_DECISIONS_SCHEMA,
    OfficerNamingProngs,
    OfficerNamingRecord,
    ReviewerConcurrence,
    append_decision,
    decision_to_record,
    employee_name_publishable,
    evaluate_officer_naming,
    evaluate_record,
    latest_decision_for,
    load_naming_decisions,
    record_concurs,
    record_to_dict,
)

SUBJECT = "agency:fixture-police"
PREDICATE = "approving_official"


def _all_prongs() -> OfficerNamingProngs:
    return OfficerNamingProngs(True, True, True, True, True)


def _two_reviewers() -> tuple[ReviewerConcurrence, ...]:
    return (
        ReviewerConcurrence("reviewer-a", True, "official conduct on the record"),
        ReviewerConcurrence("reviewer-b", True, "claim fails without the name"),
    )


def _concur_record(**overrides: object) -> OfficerNamingRecord:
    decision = evaluate_officer_naming(_all_prongs(), _two_reviewers())
    assert decision.permitted
    kwargs: dict[str, object] = {
        "recorded_at": "2026-10-14T00:00:00Z",
        "recorded_by": "operator (recorded two-reviewer act)",
    }
    kwargs.update(overrides)
    return decision_to_record(SUBJECT, PREDICATE, decision, **kwargs)


def _empty_table() -> dict:
    return {
        "schema": NAMING_DECISIONS_SCHEMA,
        "generated_for": "test",
        "recorded_at": "2026-10-14",
        "policy": {},
        "decisions": [],
    }


# --- the committed registry ----------------------------------------------------


def test_committed_registry_is_a_valid_empty_table() -> None:
    # The honest starting state: no recorded concurrence exists, so the registry
    # is empty and the gate denies by default. (Invariant: the table parses and
    # every entry is a well-formed record — the emptiness itself is incidental.)
    records = load_naming_decisions()
    assert all(isinstance(r, OfficerNamingRecord) for r in records)


def test_malformed_table_fails_loud() -> None:
    with pytest.raises(ValueError, match="not a valid"):
        from policy.officer import _decisions_from_table

        _decisions_from_table({"schema": "wrong", "decisions": []})
    with pytest.raises(ValueError, match="decisions.*list"):
        from policy.officer import _decisions_from_table as dft

        dft({"schema": NAMING_DECISIONS_SCHEMA})


# --- record round-trip + replay ------------------------------------------------


def test_decision_to_record_round_trips_and_replays() -> None:
    record = _concur_record()
    assert record.decision_id.startswith("ond-")
    wire = record_to_dict(record)
    reparsed = json.loads(json.dumps(wire))  # the JSON boundary
    from policy.officer import _record_from_dict

    parsed = _record_from_dict(reparsed)
    assert parsed.subject_id == SUBJECT and parsed.predicate_id == PREDICATE
    replay = evaluate_record(parsed)
    assert replay.permitted is True
    assert record_concurs(parsed) is True


def test_inconsistent_record_is_denied() -> None:
    # A record CLAIMING a permit whose stored inputs do not concur (one reviewer)
    # must never publish — the replayed evaluation is authoritative.
    decision = evaluate_officer_naming(_all_prongs(), _two_reviewers()[:1])
    record = decision_to_record(
        SUBJECT,
        PREDICATE,
        decision,
        recorded_at="2026-10-14T00:00:00Z",
        recorded_by="test",
    )
    assert record.permitted is False
    forged = OfficerNamingRecord(**{**record.__dict__, "permitted": True})
    assert record_concurs(forged) is False
    replay = evaluate_record(forged)
    assert replay.permitted is False


def test_carveout_flags_deny_regardless_of_stored_flag() -> None:
    # SIG-PUB-009/010 travel with the record: even a stored permit over
    # carve-out flags replays to a deny.
    for flag in ("is_home_address", "is_routine_audit_row"):
        decision = evaluate_officer_naming(_all_prongs(), _two_reviewers())
        record = decision_to_record(
            SUBJECT,
            PREDICATE,
            decision,
            recorded_at="2026-10-14T00:00:00Z",
            recorded_by="test",
            **{flag: True},
        )
        assert evaluate_record(record).permitted is False
        assert record_concurs(record) is False


def test_latest_record_governs_append_order_is_supersede_order() -> None:
    concur = _concur_record()
    deny_decision = evaluate_officer_naming(
        _all_prongs(),
        (
            ReviewerConcurrence("reviewer-a", True, "still official"),
            ReviewerConcurrence("reviewer-b", False, "no longer proportionate"),
        ),
    )
    deny = decision_to_record(
        SUBJECT,
        PREDICATE,
        deny_decision,
        recorded_at="2026-10-14T01:00:00Z",
        recorded_by="operator (recorded two-reviewer act)",
        supersedes=concur.decision_id,
    )
    records = (concur, deny)
    latest = latest_decision_for(SUBJECT, PREDICATE, records)
    assert latest is deny
    assert record_concurs(latest) is False


def test_no_record_means_no_decision() -> None:
    assert latest_decision_for(SUBJECT, PREDICATE, ()) is None


# --- the publication gate (record leg AND jurisdiction leg) --------------------


def test_default_deny_empty_registry_on_every_jurisdiction() -> None:
    for subject_j, origin_j in (("US", "US"), ("FR", "FR"), ("UK", "UK"), ("ZZ", "ZZ")):
        verdict = employee_name_publishable(
            SUBJECT,
            PREDICATE,
            subject_jurisdiction=subject_j,
            record_origin_jurisdiction=origin_j,
            decisions=(),
        )
        assert verdict.permitted is False
        assert "default deny" in verdict.reason


def test_concur_record_plus_permissive_jurisdiction_permits() -> None:
    verdict = employee_name_publishable(
        SUBJECT,
        PREDICATE,
        subject_jurisdiction="US",
        record_origin_jurisdiction="US",
        decisions=[_concur_record()],
    )
    assert verdict.permitted is True
    assert verdict.decision_id is not None and verdict.decision_id.startswith("ond-")


def test_concur_record_still_withholds_under_restrictive_or_unknown_jurisdiction() -> None:
    record = _concur_record()
    for subject_j, origin_j in (("FR", "FR"), ("US", "FR"), ("ZZ", "US"), ("EU", "EU")):
        verdict = employee_name_publishable(
            SUBJECT,
            PREDICATE,
            subject_jurisdiction=subject_j,
            record_origin_jurisdiction=origin_j,
            decisions=[record],
        )
        assert verdict.permitted is False, (subject_j, origin_j)
        assert "SIG-PUB-017" in verdict.reason


def test_deny_record_and_inconsistent_record_withhold() -> None:
    deny = decision_to_record(
        SUBJECT,
        PREDICATE,
        evaluate_officer_naming(_all_prongs(), _two_reviewers()[:1]),
        recorded_at="2026-10-14T00:00:00Z",
        recorded_by="test",
    )
    forged = OfficerNamingRecord(**{**deny.__dict__, "permitted": True})
    for record in (deny, forged):
        verdict = employee_name_publishable(
            SUBJECT,
            PREDICATE,
            subject_jurisdiction="US",
            record_origin_jurisdiction="US",
            decisions=[record],
        )
        assert verdict.permitted is False
        assert verdict.decision_id == record.decision_id


# --- the append-only writer ----------------------------------------------------


def test_append_decision_writes_a_valid_entry(tmp_path: Path) -> None:
    path = tmp_path / "officer_naming_decisions.json"
    path.write_text(json.dumps(_empty_table()))
    record = _concur_record()
    append_decision(record, table_path=path)
    table = json.loads(path.read_text())
    assert len(table["decisions"]) == 1
    from policy.officer import _decisions_from_table

    reloaded = _decisions_from_table(table)
    assert reloaded[0].decision_id == record.decision_id
    # The appended record governs lookups against the written table.
    assert latest_decision_for(SUBJECT, PREDICATE, reloaded) == reloaded[0]


def test_append_decision_refuses_inconsistent_and_duplicate(tmp_path: Path) -> None:
    path = tmp_path / "officer_naming_decisions.json"
    path.write_text(json.dumps(_empty_table()))
    record = _concur_record()
    # A stored permit whose inputs do not concur must be refused.
    deny = decision_to_record(
        SUBJECT,
        PREDICATE,
        evaluate_officer_naming(_all_prongs(), _two_reviewers()[:1]),
        recorded_at="2026-10-14T00:00:00Z",
        recorded_by="test",
    )
    bad = OfficerNamingRecord(**{**deny.__dict__, "permitted": True, "decision_id": "ond-bad"})
    with pytest.raises(ValueError, match="inconsistent"):
        append_decision(bad, table_path=path)
    with pytest.raises(ValueError, match="recorded_at"):
        append_decision(
            OfficerNamingRecord(**{**record.__dict__, "recorded_at": ""}),
            table_path=path,
        )
    append_decision(record, table_path=path)
    with pytest.raises(ValueError, match="already recorded"):
        append_decision(record, table_path=path)
    # A consistent record whose supersedes pointer names no recorded decision
    # is refused (the pointer must resolve inside the append-only chain).
    orphan = decision_to_record(
        SUBJECT,
        PREDICATE,
        evaluate_officer_naming(_all_prongs(), _two_reviewers()[:1]),
        recorded_at="2026-10-14T02:00:00Z",
        recorded_by="test",
        supersedes="ond-missing",
    )
    with pytest.raises(ValueError, match="supersedes"):
        append_decision(orphan, table_path=path)

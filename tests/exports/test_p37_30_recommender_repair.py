# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.30 (R11-K13-WX-05 / K7 §5.7, F-485) — the evidence-recommender repair:
per-(artifact, subject) D/C/retrievability emitted on ``web/evidence.json``;
the score names exactly the subject it measures; an uncomputable pair is
counted and emitted nowhere (fails typed, never a silent zero); the one-hop
subject neighbourhood is emitted for the scoped ranking; and the
``decision_point.json`` analytic becomes a per-item list."""

from __future__ import annotations

import json

import pytest
from exports.spine_export import EXPORT_QUERIES, _retrievability
from test_spine_export import _build, _site


def _artifact_row(**over):
    """An evidence_artifacts row in the widened P37.30 shape (13 columns)."""
    row = [
        "art-1",  # artifact_id
        "src_a",  # source_id
        "The source document",  # title
        "contract",  # artifact_type
        "https://example.org/doc",  # stable_locator
        "primary",  # primary_or_secondary
        "captured",  # capture_status
        "2026-09",  # published_at_edtf
        "Example Source",  # source_name
        "synthetic",  # capture_classification
        "https://example.org/doc",  # upstream_url
        [],  # captures
        None,  # disappeared_observed_at
    ]
    for k, v in over.items():
        idx = {
            "artifact_id": 0,
            "primary_or_secondary": 5,
            "capture_status": 6,
            "published_at_edtf": 7,
            "disappeared_observed_at": 12,
        }[k]
        row[idx] = v
    return tuple(row)


def _subject_claim_row(**over):
    """An evidence_subject_claims row in the SELECT order."""
    row = {
        "artifact_id": "art-1",
        "subject_id": "subj-1",
        "subject_key": "contract:src:tenant:body:C-1",
        "claim_id": "cl-1",
        "predicate_id": "end_date",  # IMMUTABLE → C1
        "claim_directness": "D2",
        "observed_at": "2026-05-01",
        "object_entity": None,
        "object_key": None,
    }
    row.update(over)
    return row


def _evidence(export):
    return json.loads(export.web_artifacts["web/evidence.json"].decode("utf-8"))


# --- the producer --------------------------------------------------------- #


def test_subject_claims_query_carries_the_shared_gates() -> None:
    """The score-input read is gated exactly like its binding siblings — the
    publishable-claim gate, the artifact gate, the capture-seal gate and
    effective rights; a withheld claim or artifact never feeds a score."""
    guard, sql = EXPORT_QUERIES["evidence_subject_claims"]
    assert guard == "claim_evidence"
    assert "{PUB_CLAIM_GATE}" in sql
    assert "{PUB_ARTIFACT_GATE}" in sql
    assert "{CAPTURE_SEAL_GATE}" in sql
    assert "{EFFECTIVE}" in sql and "latest_decision" in sql
    assert "redistributable = 'yes'" in sql
    # the axes the D/C derivation needs + the subject + the neighbourhood hop
    for col in (
        "claim_directness",
        "observed_at",
        "predicate_id",
        "object_entity",
        "sig.connector.subject",
    ):
        assert col in sql


def test_evidence_artifacts_query_carries_the_disappearance_column() -> None:
    """§17.6's ``disappeared_observed_at`` rides the artifact row — the
    retrievability input (an observed disappearance reads link_rotted)."""
    _guard, sql = EXPORT_QUERIES["evidence_artifacts"]
    assert "disappeared_observed_at" in sql


# --- retrievability -------------------------------------------------------- #


def test_retrievability_maps_the_capture_status_vocabulary() -> None:
    assert _retrievability("captured", None) == "retrievable"
    assert _retrievability("access_restricted", None) == "access_restricted"
    assert _retrievability("paywalled", None) == "paywalled"
    assert _retrievability("link_rotted", None) == "link_rotted"
    # an observed disappearance (§17.6) reads link_rotted whatever the status
    assert _retrievability("captured", "2026-09-01") == "link_rotted"


def test_retrievability_fails_closed_on_an_unmapped_status() -> None:
    """An unmapped status raises — never a silent "retrievable" (SIG-ENG-042)."""
    with pytest.raises(ValueError, match="unmapped"):
        _retrievability("refused_by_policy", None)


# --- per-(artifact, subject) scores --------------------------------------- #


def test_subject_scores_emit_per_artifact_subject_pair() -> None:
    """The score names exactly what it measures: each (artifact, subject)
    pair carries the BEST directness and currency over the artifact's claims
    about THAT subject — plus the subject-scoped dispute flags."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "evidence_artifacts": [_artifact_row()],
            "evidence_subject_claims": [
                _subject_claim_row(claim_id="c1", claim_directness="D3"),
                _subject_claim_row(claim_id="c2", claim_directness="D1"),  # best
                _subject_claim_row(claim_id="c3", claim_directness="D6"),  # non-probative
                _subject_claim_row(
                    claim_id="c4",
                    subject_id="subj-2",
                    subject_key="organisation:okc:council",
                    claim_directness="D5",
                    predicate_id="title",
                ),
            ],
            "materialized_contradictions": [{"claim_ids": ["c1"], "subject_id": "subj-1"}],
            "research_tasks": [
                (
                    "T-1",  # task_id
                    "contract_expiring",  # task_type
                    "subj-2",  # subject_id
                    "j1",  # jurisdiction_id
                    1,  # priority
                    "open",  # status
                    "open",  # disposition
                    "terms recorded",  # closing_condition
                    "det/1",  # detector_version
                    None,  # trigger_kind
                    None,  # trigger_ref
                    "2026-09-01",  # generated_at
                )
            ],
        },
    )
    ev = _evidence(export)
    (art,) = ev["artifacts"]
    scores = {s["subject_id"]: s for s in art["subject_scores"]}
    assert set(scores) == {"subj-1", "subj-2"}
    # subj-1: best D over its three claims is D1 (the D6 never contributes);
    # best C is C1 (end_date is IMMUTABLE); the contradiction touches subj-1.
    assert scores["subj-1"]["directness"] == "D1"
    assert scores["subj-1"]["currency"] == "C1"
    assert scores["subj-1"]["subject_key"] == "contract:src:tenant:body:C-1"
    assert scores["subj-1"]["touches_open_contradiction"] is True
    assert scores["subj-1"]["answers_open_task"] is False
    # subj-2: its own D5 — never subj-1's stronger class — and the open task.
    assert scores["subj-2"]["directness"] == "D5"
    assert scores["subj-2"]["answers_open_task"] is True
    # flat headline fields: best over the whole artifact; the spine values
    # keep their true names (primary_or_secondary / published_at_edtf).
    assert art["directness"] == "D1"
    assert art["currency"] == "C1"
    assert art["capture_status"] == "retrievable"
    assert art["primary_or_secondary"] == "primary"
    assert art["published_at_edtf"] == "2026-09"
    assert art["touches_open_contradiction"] is True
    assert art["answers_open_task"] is True


def test_uncomputable_pair_is_counted_never_emitted() -> None:
    """A pair whose axes cannot be computed — no probative directness or no
    derivable currency — is COUNTED under build.recommender_scores and
    emitted nowhere: an uncomputable score fails typed, never a silent zero."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "evidence_artifacts": [_artifact_row()],
            "evidence_subject_claims": [
                # D6 only — no probative directness.
                _subject_claim_row(claim_id="c1", claim_directness="D6"),
                # D2 but no observed_at — no derivable currency.
                _subject_claim_row(
                    claim_id="c2",
                    subject_id="subj-2",
                    claim_directness="D2",
                    observed_at=None,
                ),
                # D1 but an unknown predicate — currency underivable.
                _subject_claim_row(
                    claim_id="c3",
                    subject_id="subj-3",
                    claim_directness="D1",
                    predicate_id="not_a_registered_predicate",
                ),
            ],
        },
    )
    ev = _evidence(export)
    (art,) = ev["artifacts"]
    assert art["subject_scores"] == []
    assert art["subject_scores_uncomputable"] == 3
    assert ev["build"]["recommender_scores"]["pairs_emitted"] == 0
    assert ev["build"]["recommender_scores"]["pairs_uncomputable"] == 3
    # the flat fields are the named absence, never a fabricated class
    assert art["directness"] == "not_recorded"
    assert art["currency"] == "not_recorded"


def test_currency_is_derived_against_predicate_volatility() -> None:
    """Currency is the §28.3 class vs predicate half-life at as_of — an old
    observation on a volatile predicate ranks below a current one."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "evidence_artifacts": [_artifact_row()],
            "evidence_subject_claims": [
                # product_status is MODERATE/12mo — a 2024 observation is C4.
                _subject_claim_row(
                    claim_id="c1",
                    predicate_id="product_status",
                    observed_at="2024-01-01",
                ),
                _subject_claim_row(
                    claim_id="c2",
                    predicate_id="product_status",
                    observed_at="2026-09-01",  # C1 at the 2026-09-22 as_of
                ),
            ],
        },
    )
    (art,) = _evidence(export)["artifacts"]
    (score,) = art["subject_scores"]
    assert score["currency"] == "C1"  # the best class wins


def test_subject_neighbours_record_the_one_claim_hop() -> None:
    """A bound claim's subject and its object entity are mutual one-hop
    neighbours — the contract/agency neighbourhood the recommender expands."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "evidence_artifacts": [_artifact_row()],
            "evidence_subject_claims": [
                _subject_claim_row(
                    claim_id="c1",
                    object_entity="ent-council",
                    object_key="organisation:okc:council",
                ),
            ],
        },
    )
    ev = _evidence(export)
    assert "contract:src:tenant:body:C-1" in ev["subject_neighbours"]
    assert "organisation:okc:council" in ev["subject_neighbours"]["contract:src:tenant:body:C-1"]
    assert "contract:src:tenant:body:C-1" in ev["subject_neighbours"]["organisation:okc:council"]


def test_pre_repair_rows_degrade_honestly() -> None:
    """A pre-P37.30 row shape (11 columns, no subject_claims read) emits the
    honest absences — not_recorded axes, no scores, retrievable status."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"evidence_artifacts": [_artifact_row()[:11]]},
    )
    (art,) = _evidence(export)["artifacts"]
    assert art["subject_scores"] == []
    assert art["directness"] == "not_recorded"
    assert art["currency"] == "not_recorded"
    assert art["capture_status"] == "retrievable"


def test_disappeared_artifact_reads_link_rotted() -> None:
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"evidence_artifacts": [_artifact_row(disappeared_observed_at="2026-09-01")]},
    )
    (art,) = _evidence(export)["artifacts"]
    assert art["capture_status"] == "link_rotted"
    assert art["disappeared_observed_at"] == "2026-09-01"


def test_single_subject_artifact_names_its_subject() -> None:
    """The flat ``subject_id`` names the subject ONLY when exactly one is
    scored — the subject_scores list stays the authoritative shape."""
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "evidence_artifacts": [_artifact_row()],
            "evidence_subject_claims": [_subject_claim_row()],
        },
    )
    (art,) = _evidence(export)["artifacts"]
    assert art["subject_id"] == "contract:src:tenant:body:C-1"


# --- the per-item decision points ----------------------------------------- #


def _watch_claim(**over):
    """A ``watch_claims`` row (WATCH_CLAIMS_COLUMNS order) for one contract
    subject the producer derives an item from."""
    row = {
        "claim_id": "wc-1",
        "subject_id": "ent-c1",
        "subject_key": "contract:src:tenant:body:C-1",
        "entity_type": "contract",
        "predicate_id": "end_date",
        "value_text": None,
        "value_num": None,
        "value_bool": None,
        "value_json": None,
        "raw_value": None,
        "observed_at": "2026-05-01",
        "recorded_at": "2026-05-01",
        "revises_claim": None,
        "retraction_of": None,
        "review_status": "not_run",
        "source_id": "src_a",
        "spdx_expression": "ODbL-1.0",
    }
    row.update(over)
    return row


def test_decision_point_emits_the_per_item_list() -> None:
    """``decision_point.json`` keeps the national headline AND gains the
    per-item list — the ranked evidence lives on the item page."""
    # An auto-renewing contract with a 90-day notice window → the producer's
    # renewal_deadline item (expiry − window).
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={
            "watch_claims": [
                _watch_claim(
                    claim_id="wc-end",
                    predicate_id="end_date",
                    value_text="2027-04-02",  # future-ok: synthetic: fixture end
                ),
                _watch_claim(claim_id="wc-auto", predicate_id="auto_renews", value_bool=True),
                _watch_claim(claim_id="wc-win", predicate_id="notice_window_days", value_num=90),
            ]
        },
    )
    watch = json.loads(export.web_artifacts["web/watch.json"].decode("utf-8"))
    (item,) = watch["items"]
    dp = json.loads(export.web_artifacts["web/analytics/decision_point.json"].decode("utf-8"))
    # the headline stays the earliest derivable next_decision_date
    assert dp["decision_point"]["subject_id"] == "contract:src:tenant:body:C-1"
    assert dp["decision_point"]["date"] == "2027-01-02"  # future-ok: synthetic: derived
    # and the per-item list carries the scoped decision the item page reads
    (point,) = dp["decision_points"]
    assert point["handle"] == item["handle"]
    assert point["decision_type"] == "renewal"
    assert point["subject_id"] == "contract:src:tenant:body:C-1"
    assert point["subject_ids"] == ["contract:src:tenant:body:C-1"]
    assert point["kind"] == "renewal_deadline"
    assert point["date_certainty"] == "derived"

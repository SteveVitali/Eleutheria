# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.22 / F-504 — emitter-side claim identity + the claim-minting-diff harness.

Emitter-side and sink-side minting run ONE identity function
(``evidence.claim_identity.claim_digest``); ``db.claim_sink.content_digest``
delegates to it, ``connectors.claim_identity_ingest.emitted_claim_digest``
resolves the SAME registry classes. These tests pin: byte-for-byte digest
parity, the registry-read obs/ref classes, the ``ingest_claim_reconcile.csv``
round-trip, the diff verdicts, and class-aware replay/shadow diffs.
"""

from __future__ import annotations

from connectors.claim_identity_ingest import (
    RECONCILE_FIELDS,
    diff_minting,
    emitted_claim_digest,
    emitted_row_key,
    is_claim_record,
    predicate_temporal_classes,
    read_rows,
    reconcile_rows,
    write_rows,
)
from connectors.replay import diff_claim_sets
from db.claim_sink import content_digest


def _claim(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "subject_id": "cam:okc-42",
        "predicate_id": "camera_operator",
        "value": "ACME Surveillance",
        "source_id": "okc_registry",
        "license": "CC0-1.0",
        "record_kind": "claim",
    }
    base.update(over)
    return base


# --- registry-read classes ------------------------------------------------------


def test_registry_classes_project_the_real_vocab() -> None:
    classes = predicate_temporal_classes()
    # The committed registry is the same source vocab_predicate seeds from.
    assert classes["windowed_search_count"] == "obs"  # interval_union
    assert classes["observed_use_edge"] == "obs"
    # The F-504 camera-registry predicates are REFERENCE class — their temporal
    # axis is the sighting history in claim_evidence (ADR-R9-RESIGHT), not the
    # claim id.
    assert classes["camera_operator"] == "ref"  # max_support
    assert classes["camera_latitude"] == "ref"  # latest_observation_wins
    assert classes["contract_signed_date"] == "ref"  # authoritative_source_wins


# --- emitted-vs-stored digest parity (the dedup-parity obligation) ---------------


def test_emitter_and_sink_digests_are_byte_identical() -> None:
    classes = predicate_temporal_classes()
    record = _claim(
        row_index=7,
        capture_digest="f" * 64,
        retrieved_at="2026-10-18T00:00:00Z",
        value_json={"b": 2, "a": 1.0},
    )
    emitted = emitted_claim_digest(record, classes=classes)
    stored_side = content_digest(record, temporal_class=classes["camera_operator"])
    assert emitted == stored_side


def test_obs_class_record_parity() -> None:
    classes = predicate_temporal_classes()
    record = _claim(
        predicate_id="windowed_search_count",
        value=12,
        valid_from="2026-01-01",
        valid_to="2026-02-01",
        row_index=0,
    )
    emitted = emitted_claim_digest(record, classes=classes)
    stored_side = content_digest(record, temporal_class="obs")
    assert emitted == stored_side
    # The window is identity: another window is another claim.
    other = dict(record, valid_from="2026-02-01", valid_to="2026-03-01")
    assert emitted_claim_digest(other, classes=classes) != emitted


def test_re_observation_rebinds_never_remints() -> None:
    """The F-504 defect class: a re-ingest at another row position / page /
    fetch produces the SAME digest the sink dedups on."""
    classes = predicate_temporal_classes()
    first = _claim(row_index=0, page=1, retrieved_at="2026-10-01T00:00:00Z")
    second = _claim(row_index=41, page=4, retrieved_at="2026-10-18T00:00:00Z")
    assert emitted_claim_digest(first, classes=classes) == emitted_claim_digest(
        second, classes=classes
    )


def test_is_claim_record_matches_the_sink_filter() -> None:
    assert is_claim_record(_claim())
    bare = _claim()
    del bare["record_kind"]
    assert is_claim_record(bare)
    assert not is_claim_record(_claim(record_kind="traffic_camera"))
    assert not is_claim_record(_claim(record_kind="portal_document"))


# --- ingest_claim_reconcile.csv codec + the diff ---------------------------------


def test_reconcile_csv_round_trip() -> None:
    records = [
        _claim(row_index=0),
        _claim(subject_id="cam:okc-43", value="OtherCo", row_index=1),
        _claim(record_kind="traffic_camera"),  # non-claim: never enters the diff
    ]
    rows = reconcile_rows(records, source_id="okc_registry")
    assert len(rows) == 2
    text = write_rows(rows)
    parsed = read_rows(text)
    assert parsed == rows
    assert all(set(r) == set(RECONCILE_FIELDS) for r in parsed)


def test_diff_minting_rebound() -> None:
    records = [_claim(row_index=0), _claim(subject_id="cam:okc-43", row_index=1)]
    emitted = reconcile_rows(records, source_id="okc_registry")
    # The stored side reports the same digests (re-ingest re-bound).
    stored = [dict(r, side="stored") for r in emitted]
    diff = diff_minting([*emitted, *stored])
    assert diff.converged
    assert diff.rebound == len(emitted)
    assert diff.minted == 0 and diff.divergent == 0
    assert diff.summary()["converged"] is True


def test_diff_minting_detects_new_mints_and_divergence() -> None:
    emitted = reconcile_rows([_claim(row_index=0)], source_id="okc_registry")
    # Nothing stored yet → the row would mint.
    fresh = diff_minting(emitted)
    assert not fresh.converged and fresh.minted == 1
    # A stored digest under a DIFFERENT scheme for the same row → divergence.
    stored_other = [dict(emitted[0], side="stored", content_digest="0" * 64)]
    divergent = diff_minting([*emitted, *stored_other])
    assert not divergent.converged and divergent.divergent == 1


def test_reordered_repaged_ingest_is_byte_identical() -> None:
    """Two passes over the same rows, re-ordered and re-paged, emit the same
    digest stream — the parity the harness compares."""
    classes = predicate_temporal_classes()
    run_a = [
        _claim(row_index=0, page=1, retrieved_at="2026-10-01T00:00:00Z"),
        _claim(subject_id="cam:okc-43", row_index=1, page=1),
    ]
    run_b = [
        _claim(subject_id="cam:okc-43", row_index=0, page=2, retrieved_at="2026-10-18T00:00:00Z"),
        _claim(row_index=7, page=2, retrieved_at="2026-10-18T00:00:00Z"),
    ]
    digests_a = sorted(emitted_claim_digest(r, classes=classes) for r in run_a)
    digests_b = sorted(emitted_claim_digest(r, classes=classes) for r in run_b)
    assert digests_a == digests_b


# --- class-aware replay/shadow diff ----------------------------------------------


def test_shadow_diff_ignores_volatile_churn() -> None:
    current = [_claim(row_index=0, capture_digest="a" * 64, retrieved_at="t0")]
    new = [_claim(row_index=9, capture_digest="b" * 64, retrieved_at="t1")]
    diff = diff_claim_sets(current, new, classes=predicate_temporal_classes())
    assert diff.summary() == {
        "added": 0,
        "removed": 0,
        "unchanged": 1,
        "changed": 0,
    }


def test_shadow_diff_sees_obs_window_change() -> None:
    current = [
        _claim(
            predicate_id="windowed_search_count",
            valid_from="2026-01-01",
            valid_to="2026-02-01",
            value=12,
        )
    ]
    new = [
        _claim(
            predicate_id="windowed_search_count",
            valid_from="2026-02-01",
            valid_to="2026-03-01",
            value=12,
        )
    ]
    diff = diff_claim_sets(current, new, classes=predicate_temporal_classes())
    assert diff.summary()["added"] == 1 and diff.summary()["removed"] == 1


def test_fixture_reconcile_csv_verdicts() -> None:
    """The committed ``ingest_claim_reconcile.csv`` fixture: two re-ingested
    rows re-bind (identical digest across new row positions/fetch dates) and
    one genuinely new fact mints — the harness separates the two classes."""
    from pathlib import Path

    fixture = (
        Path(__file__).resolve().parent
        / "fixtures"
        / "claim_identity"
        / "ingest_claim_reconcile.csv"
    )
    rows = read_rows(fixture.read_text(encoding="utf-8"))
    diff = diff_minting(rows)
    assert diff.emitted == 3 and diff.stored == 2
    assert diff.rebound == 2, "the two unchanged facts re-bind"
    assert diff.minted == 1, "the new fact (cam:3) mints — legitimate, not a duplicate"
    assert diff.divergent == 0, "no emitted-vs-stored identity divergence"
    # minted detail names the genuinely new row
    assert any("cam:3" in k for k in diff.detail)


def test_emitted_row_key_is_stable_across_volatile_fields() -> None:
    a = _claim(row_index=0, page=1)
    b = _claim(row_index=4, page=7)
    assert emitted_row_key(a) == emitted_row_key(b)
    assert emitted_row_key(a, ordinal=0) != emitted_row_key(a, ordinal=1)

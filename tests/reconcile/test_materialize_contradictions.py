# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the P28.3 contradiction materialization mapping (no DB).

Proves the writer (`contradiction_row` / `contradiction_input_digest` /
`detected_contradictions`) maps ANY `reconcile.model.Contradiction` onto the
`_persisted_contradictions`-shaped row — so §29 reconciliation (`reconcile.counts`),
the §29.4 lifecycle (`reconcile.lifecycle`), and the §31 entity
(`reconcile.contradiction`) all materialize through the SAME writer (reuse, not
re-implement — SIG-ENG-035). The DB round-trip is `tests/db/test_contradiction_materialize.py`.
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from reconcile.contradiction import materialize as materialize_contradiction_entity
from reconcile.counts import reconcile_counts
from reconcile.lifecycle import render_lifecycle_status
from reconcile.materialize import (
    contradiction_input_digest,
    contradiction_row,
    detected_contradictions,
)
from reconcile.model import VALUE_DISAGREEMENT, Contradiction, CountClaim, Evidence

AS_OF = date(2026, 9, 1)


def _ev(genre: str, tag: str) -> Evidence:
    return Evidence(
        source_id=f"src:{genre}",
        source_family=genre,
        artifact_type=genre,
        stable_locator=f"https://example/{tag}",
        capture_digest="b" + "0" * 40,
        locator={"selector": "#count", "text_span": [0, 3]},
        excerpt="…",
    )


def _count(basis: str, value: int, *, R: str, genre: str, observed: date) -> CountClaim:
    return CountClaim(
        count_basis=basis,
        value=value,
        reliability=R,
        integrity="I1",
        observed_at=observed,
        genre=genre,
        evidence=_ev(genre, f"{basis}-{value}"),
    )


# --- digest determinism + lifecycle sensitivity -------------------------------


def _row(**over: object) -> dict[str, object]:
    base: dict[str, object] = {
        "subject_id": "s1",
        "predicate_id": "claimed_device_count",
        "contradiction_type": VALUE_DISAGREEMENT,
        "claim_ids": ["c2", "c1"],
        "status": "open",
        "severity": "notable",
    }
    base.update(over)
    return base


def test_input_digest_is_deterministic_and_order_independent() -> None:
    a = contradiction_input_digest(_row(claim_ids=["c1", "c2"]))
    b = contradiction_input_digest(_row(claim_ids=["c2", "c1"]))
    assert a == b  # the claim-id set is sorted into the digest


def test_input_digest_changes_with_lifecycle_status() -> None:
    # A lifecycle transition (open -> superseded) MUST change the digest so it lands
    # as a NEW superseding row, never an edit of the open one.
    assert contradiction_input_digest(_row(status="open")) != contradiction_input_digest(
        _row(status="superseded")
    )


def test_input_digest_changes_with_claim_set_and_severity() -> None:
    assert contradiction_input_digest(_row(claim_ids=["c1"])) != contradiction_input_digest(
        _row(claim_ids=["c1", "c2"])
    )
    assert contradiction_input_digest(_row(severity="notable")) != contradiction_input_digest(
        _row(severity="blocking")
    )


# --- contradiction_row maps the §31 entity, both evidence sides ---------------


def test_contradiction_row_carries_both_evidence_sides() -> None:
    detected = Contradiction(
        contradiction_type=VALUE_DISAGREEMENT,
        subject_id="s1",
        predicate_id="claimed_device_count",
        claim_values=(190, 299),
        note="299 vs 190",
        claim_ids=("c-299", "c-190"),
    )
    row = contradiction_row(detected)
    assert row is not None
    assert row["contradiction_type"] == VALUE_DISAGREEMENT
    assert row["status"] == "open"
    assert set(row["claim_ids"]) == {"c-299", "c-190"}  # both sides visible
    assert row["input_digest"]


def test_contradiction_row_refuses_an_unevidenced_contradiction() -> None:
    # No claim_ids -> not materializable (§3.1: no unevidenced contradiction).
    detected = Contradiction(
        contradiction_type=VALUE_DISAGREEMENT,
        subject_id="s1",
        predicate_id="p",
        claim_values=(1, 2),
        note="n",
        claim_ids=(),
    )
    assert contradiction_row(detected) is None


# --- REUSE: §29 count reconciliation (reconcile.counts) materializes here ------


def test_count_reconciliation_299_vs_190_materializes(  # noqa: N802 the 299-vs-190 pattern
) -> None:
    # The canonical 299-vs-190 pattern: DeFlock ~299 vs Chief Bacy ~190 on claimed count.
    claims = [
        _count("claimed", 299, R="R4", genre="news_article", observed=date(2026, 8, 3)),
        _count("claimed", 190, R="R2", genre="council_minutes", observed=date(2026, 8, 18)),
    ]
    rec = reconcile_counts("dep:okc", claims, as_of=AS_OF)
    disagreements = [c for c in rec.contradictions if c.contradiction_type == VALUE_DISAGREEMENT]
    assert disagreements, "expected a value_disagreement from reconcile_counts"
    # The §29 output flows through the P08.3 entity + the SAME writer (reuse).
    entity = materialize_contradiction_entity(disagreements[0], claim_ids=("c-299", "c-190"))
    row = contradiction_row(entity)
    assert row is not None
    assert row["contradiction_type"] == VALUE_DISAGREEMENT
    assert set(row["claim_ids"]) == {"c-299", "c-190"}
    assert set(entity.claim_values) == {190, 299}  # neither collapsed


# --- REUSE: §29.4 lifecycle (reconcile.lifecycle) materializes here ------------


def test_lifecycle_contradiction_materializes() -> None:
    status = render_lifecycle_status(
        "dep:x", procurement_state="canceled", physical_state="installed", as_of_edtf="2026-09"
    )
    assert status.contradiction is not None  # canceled contract, hardware present
    entity = materialize_contradiction_entity(status.contradiction, claim_ids=("c-proc", "c-phys"))
    row = contradiction_row(entity)
    assert row is not None
    assert row["contradiction_type"] == "value_disagreement"
    assert row["severity"] == "notable"


# --- detected_contradictions mirrors compute-on-read --------------------------


def test_detected_synthesizes_value_disagreement_from_conflict_state() -> None:
    resolved = SimpleNamespace(
        considered_claim_ids=("c1", "c2"),
        contradictions=(),
        contradiction_state="unresolved_conflict",
    )
    claims = [
        SimpleNamespace(value=299),
        SimpleNamespace(value=190),
    ]
    out = detected_contradictions("s1", "claimed_device_count", resolved, claims)  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0].contradiction_type == VALUE_DISAGREEMENT
    assert set(out[0].claim_ids) == {"c1", "c2"}


def test_detected_yields_nothing_for_a_clean_resolution() -> None:
    resolved = SimpleNamespace(
        considered_claim_ids=("c1",),
        contradictions=(),
        contradiction_state="uncontested",
    )
    out = detected_contradictions("s1", "p", resolved, [SimpleNamespace(value=1)])  # type: ignore[arg-type]
    assert out == []


def test_detected_materializes_the_resolvers_own_contradiction() -> None:
    # A resolver-emitted contradiction (e.g. predicate_conflation) is materialized with
    # its real type; the synthesized value_disagreement is NOT double-added.
    emitted = Contradiction(
        contradiction_type="predicate_conflation",
        subject_id="s1",
        predicate_id="claimed_device_count",
        claim_values=(5,),
        note="dropped a mismatched basis",
    )
    resolved = SimpleNamespace(
        considered_claim_ids=("c1", "c2"),
        contradictions=(emitted,),
        contradiction_state="resolved_conflict",
    )
    out = detected_contradictions(
        "s1", "claimed_device_count", resolved, [SimpleNamespace(value=5)]
    )  # type: ignore[arg-type]
    types = {c.contradiction_type for c in out}
    assert "predicate_conflation" in types
    # resolver already spoke; a synthesized value_disagreement is only added when the
    # resolver emitted none of its own.
    assert "value_disagreement" not in types
    assert all(set(c.claim_ids) == {"c1", "c2"} for c in out)

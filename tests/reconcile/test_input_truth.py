# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Resolver input truth (P35.27 / CP-9, CONF-05; F-519).

The resolver's inputs are now truthful: claims carry their declared
``valid_period`` bounds, the connector-DECLARED per-claim directness (the
weaker of declared vs the genre x predicate matrix, SIG-EPIS-017/018), and
within-tolerance pooled disagreement is disclosed as the ``contested`` dissent
signal — ``MINOR_DISAGREEMENT`` + persisted contested claim ids — instead of
being silently absorbed (the F-519 "0 dissent in 19,121 sampled resolutions"
defect). The four-state ``contradiction_state`` vocabulary (SIG-STORE-015) is
preserved exactly: ``contested`` is a dissent signal, never a fifth state.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime

from reconcile.model import Evidence
from reconcile.resolve import (
    RESOLVE,
    RESOLVER_VERSION,
    Claim,
    Resolution,
    declared_directness,
)

AS_OF = date(2026, 9, 1)

#: The complete ``contradiction_state`` vocabulary (SIG-STORE-015) — P35.27
#: preserves it verbatim; ``contested`` is a dissent signal, never a state.
FOUR_STATES = {"uncontested", "insufficient", "resolved_conflict", "unresolved_conflict"}


def _ev(family: str) -> Evidence:
    return Evidence(
        source_id=f"src:{family}",
        source_family=family,
        artifact_type=family,
        stable_locator=f"https://example/{family}",
        capture_digest="b" + "0" * 40,
        locator={"selector": "#v", "text_span": [0, 3]},
        excerpt="…",
    )


def _claim(
    cid: str,
    predicate: str,
    value: object,
    *,
    R: str,
    genre: str,
    observed: date,
    integrity: str = "I1",
    subject: str = "S",
    method: str | None = None,
    indep: str | None = None,
    source_id: str | None = None,
    rank: int | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
    declared_d: str | None = None,
    count_basis: str | None = None,
) -> Claim:
    return Claim(
        claim_id=cid,
        subject_id=subject,
        predicate_id=predicate,
        value=value,
        reliability=R,
        integrity=integrity,
        genre=genre,
        observed_at=observed,
        raw_value=str(value),
        source_id=source_id or f"src:{cid}",
        collection_method=method or genre,
        independence_class=indep,
        source_registry_rank=rank,
        valid_from=valid_from,
        valid_to=valid_to,
        declared_directness=declared_d,
        count_basis=count_basis,
        evidence=_ev(genre),
    )


def _resolve(predicate: str, claims: list[Claim], *, as_of: date = AS_OF) -> Resolution:
    return RESOLVE("S", predicate, claims, as_of_world=as_of, as_of_belief=as_of)


def _resolution(**overrides: object) -> Resolution:
    """A minimal stored-decision record for the pure delta classifier tests."""
    base: dict[str, object] = dict(
        subject_id="S",
        predicate_id="p",
        resolution_status="RESOLVED",
        value=1,
        support="PROBABLE",
        agreement="UNCONTESTED",
        currency="CURRENT",
        contradiction_state="uncontested",
        strategy_id="authoritative_source_wins",
        rationale_code="RESOLVED_DIRECT",
        rationale_text="1, as reported by a source.",
        winning_claim_id="a",
        considered_claim_ids=("a",),
        supporting_claim_ids=("a",),
        dissenting_claim_ids=(),
        excluded=(),
        independence_class_ids=("cls",),
        rules_fired=(),
        ruleset_version="2026.3",
        resolver_version=RESOLVER_VERSION,
        input_digest="d",
        as_of_world=AS_OF,
        as_of_belief=AS_OF,
        computed_at=datetime(2026, 1, 1),
    )
    base.update(overrides)
    return Resolution(**base)  # type: ignore[arg-type]


def _live(state: str, *, value: object = 1, winner: object = "a", digest: str = "old") -> dict:
    return {
        "contradiction_state": state,
        "value": value,
        "winning_claim": winner,
        "input_digest": digest,
    }


# --- declared_directness: the basis-marker decoding ---------------------------


def test_declared_directness_reads_only_real_declarations() -> None:
    # An explicit declaration stands — including an explicit D2 (no default
    # marker recorded against it).
    assert declared_directness("D6", "connector_record") == "D6"
    assert declared_directness("D2", "connector_record") == "D2"
    assert (
        declared_directness("D4", "connector_record|source_reliability=connector_default_R3")
        == "D4"
    )
    # The sink's ``connector_default_D2`` marker: the column holds the schema
    # default, not a declaration — the matrix governs alone.
    assert (
        declared_directness("D2", "connector_record|claim_directness=connector_default_D2") is None
    )
    # Pre-P32.2 writes carry no declaration surface at all.
    assert declared_directness("D2", "legacy_synthetic") is None
    assert declared_directness("D2", None) is None
    assert declared_directness(None, "connector_record") is None


# --- valid-time-aware candidate selection (deliverable 1) ---------------------


def test_non_overlapping_valid_times_never_conflict() -> None:
    # A 2019 claim and a 2024 claim asserting different values are both true —
    # temporal disagreement is succession, never a contradiction. Each era's
    # as_of resolves its own claim alone; the other is excluded with the
    # Phase 1.2 label.
    old = _claim(
        "old",
        "contracted_device_count",
        299,
        R="R1",
        genre="executed_contract",
        observed=date(2019, 6, 1),
        valid_from=date(2019, 1, 1),
        valid_to=date(2021, 1, 1),
        indep="src:old",
    )
    new = _claim(
        "new",
        "contracted_device_count",
        42,
        R="R1",
        genre="executed_contract",
        observed=date(2024, 6, 1),
        valid_from=date(2024, 1, 1),
        indep="src:new",
    )
    r_2020 = _resolve("contracted_device_count", [old, new], as_of=date(2020, 6, 1))
    assert r_2020.resolution_status == "RESOLVED"
    assert r_2020.value == 299
    assert r_2020.contradiction_state == "uncontested"
    assert "SIG-RECON-006:1.2" in r_2020.rules_fired
    excluded = {e.claim_id: e.reason for e in r_2020.excluded}
    assert excluded["new"] == "valid_period does not intersect as_of_world"

    r_2026 = _resolve("contracted_device_count", [old, new], as_of=date(2026, 1, 1))
    assert r_2026.resolution_status == "RESOLVED"
    assert r_2026.value == 42
    assert r_2026.contradiction_state == "uncontested"
    assert "old" in {e.claim_id for e in r_2026.excluded}


def test_overlapping_valid_times_disagreement_is_a_conflict() -> None:
    # The same two values asserted for INTERSECTING valid periods genuinely
    # conflict — the heavier claim wins and the disagreement is a real
    # resolved_conflict, not succession.
    a = _claim(
        "a",
        "contracted_device_count",
        299,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        valid_from=date(2024, 1, 1),
        indep="src:a",
    )
    b = _claim(
        "b",
        "contracted_device_count",
        42,
        R="R3",
        genre="news_article",
        observed=date(2025, 5, 1),
        valid_from=date(2020, 1, 1),
        indep="src:b",
    )
    r = _resolve("contracted_device_count", [a, b])
    # A real conflict — one source vs one source is never resolved by fiat
    # (U3), so the disagreement stands as an unresolved_conflict with both
    # claims considered and the loser retained as dissent.
    assert r.contradiction_state in {"resolved_conflict", "unresolved_conflict"}
    assert r.unresolved_code == "U3"
    assert "b" in r.dissenting_claim_ids
    assert set(r.considered_claim_ids) == {"a", "b"}


def test_overlapping_valid_times_corroborated_winner_resolves_conflict() -> None:
    # Two independent classes on the winning value make it resolvable: the
    # overlap disagreement materializes as a resolved_conflict.
    a = _claim(
        "a",
        "contracted_device_count",
        299,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        valid_from=date(2024, 1, 1),
        indep="src:a",
    )
    a2 = _claim(
        "a2",
        "contracted_device_count",
        299,
        R="R2",
        genre="invoice",
        observed=date(2025, 4, 10),
        valid_from=date(2024, 6, 1),
        indep="src:a2",
    )
    b = _claim(
        "b",
        "contracted_device_count",
        42,
        R="R3",
        genre="news_article",
        observed=date(2025, 5, 1),
        valid_from=date(2020, 1, 1),
        indep="src:b",
    )
    r = _resolve("contracted_device_count", [a, a2, b])
    assert r.resolution_status == "RESOLVED"
    assert r.value == 299
    assert r.contradiction_state == "resolved_conflict"
    assert "b" in r.dissenting_claim_ids


# --- connector-declared directness (deliverable 2, SIG-EPIS-017/018) ----------


def test_declared_d6_drops_a_matrix_probative_claim() -> None:
    # The connector knows how it observed: a declared D6 stamp on a nominally
    # probative genre is honoured — the claim is excluded, labelled as a
    # connector declaration.
    d6 = _claim(
        "d6",
        "contracted_device_count",
        42,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        declared_d="D6",
        indep="src:d6",
    )
    good = _claim(
        "good",
        "contracted_device_count",
        299,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        indep="src:good",
    )
    r = _resolve("contracted_device_count", [d6, good])
    assert r.resolution_status == "RESOLVED"
    assert r.value == 299
    assert "D6-exclude" in r.rules_fired
    reasons = {e.claim_id: e.reason for e in r.excluded}
    assert reasons["d6"] == "connector-declared D6 non-probative for this predicate"
    assert "SIG-EPIS-017:declared_directness=D6" in r.rules_fired


def test_declared_weaker_directness_applies() -> None:
    # Declared D4 on a D3 matrix row weighs the claim at D4 (W1 at R2 — still
    # resolving, but out-weighed by the matrix-D3 sibling at W2).
    weak = _claim(
        "weak",
        "active_device_count",
        40,
        R="R2",
        genre="news_article",
        observed=date(2026, 8, 1),
        declared_d="D4",
        indep="src:weak",
    )
    strong = _claim(
        "strong",
        "active_device_count",
        38,
        R="R2",
        genre="news_article",
        observed=date(2026, 8, 1),
        indep="src:strong",
    )
    r = _resolve("active_device_count", [weak, strong])
    assert "SIG-EPIS-017:declared_directness=D4" in r.rules_fired
    assert r.value == 38  # the matrix-D3 claim wins; the declared-D4 one dissents
    assert "weak" in r.dissenting_claim_ids


def test_declared_stronger_directness_is_capped_by_the_matrix() -> None:
    # A connector may never self-strengthen: declared D1 on a D3 matrix row is
    # capped at D3 and the cap is labelled — the two R2 claims stay equal-
    # weight, so the disagreement stands as a U2 standoff (a real D1 would
    # have lifted the declaring claim to W3 and won outright).
    boosted = _claim(
        "boosted",
        "active_device_count",
        40,
        R="R2",
        genre="news_article",
        observed=date(2026, 8, 1),
        declared_d="D1",
        indep="src:boosted",
        method="m1",
    )
    plain = _claim(
        "plain",
        "active_device_count",
        38,
        R="R2",
        genre="news_article",
        observed=date(2026, 8, 1),
        indep="src:plain",
        method="m2",
    )
    r = _resolve("active_device_count", [boosted, plain])
    assert "SIG-EPIS-017:matrix_caps_declared=D1" in r.rules_fired
    assert r.unresolved_code == "U2"


def test_defaulted_d2_does_not_override_the_matrix() -> None:
    # ``declared_directness=None`` (the resolved ``connector_default_D2``
    # absence-of-declaration) leaves the matrix in charge: an undeclared
    # portal_snapshot on contract_signed_date is still matrix-D6 excluded.
    undated = _claim(
        "u",
        "contract_signed_date",
        "2026-07",
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 15),
        declared_d=None,
    )
    r = _resolve("contract_signed_date", [undated])
    assert r.unresolved_code == "U0"
    assert any("D6" in e.reason for e in r.excluded)


# --- tolerance-aware dissent (deliverable 3, F-519) ---------------------------


def test_within_tolerance_disagreement_is_contested_not_a_conflict() -> None:
    # camera_latitude declares an absolute tolerance of 0.0005°. Two claims
    # 0.0004° apart disagree inside it: disclosed dissent (contested signal +
    # MINOR_DISAGREEMENT), never a contradiction and never a fifth state.
    a = _claim(
        "a",
        "camera_latitude",
        52.1000,
        R="R3",
        genre="camera_registry",
        observed=date(2026, 8, 1),
        indep="src:a",
    )
    b = _claim(
        "b",
        "camera_latitude",
        52.1004,
        R="R3",
        genre="camera_registry",
        observed=date(2026, 8, 1),
        indep="src:b",
    )
    r = _resolve("camera_latitude", [a, b])
    assert r.resolution_status == "RESOLVED"
    assert r.value == 52.1000  # the representative's own observed value, no mean
    assert r.contradiction_state == "uncontested"  # NOT a contradiction
    assert r.agreement == "MINOR_DISAGREEMENT"  # disclosed, not absorbed
    # The contested signal: the differing pool member is recorded AND joins the
    # dissenting set while remaining a supporter of the pooled candidate.
    assert r.contested_claim_ids == ("b",)
    assert "b" in r.dissenting_claim_ids
    assert set(r.supporting_claim_ids) == {"a", "b"}
    assert "SIG-RECON-053:contested" in r.rules_fired
    assert r.rationale_code == "RESOLVED_CONTENDED_TOLERANCE"
    assert "{n_contested}" not in r.rationale_text and "tolerance" in r.rationale_text
    # No value_disagreement entity is minted for within-tolerance jitter.
    assert not any(c.contradiction_type == "value_disagreement" for c in r.contradictions)


def test_unresolved_with_contested_keeps_the_unresolved_rationale() -> None:
    # The contested-dissent template is only honest on a RESOLVED outcome: two
    # within-tolerance claims too weak to resolve (U1) still record the
    # contested signal, but the rationale stays UNRESOLVED_* — it must never
    # assert "…as reported by…" a value the resolver did not resolve.
    a = _claim(
        "a",
        "camera_latitude",
        35.4676,
        R="R3",
        genre="camera_registry",
        observed=date(1970, 1, 1),
        indep="src:a",
    )
    b = _claim(
        "b",
        "camera_latitude",
        35.4679,  # 0.0003° apart — inside the declared 0.0005° tolerance
        R="R3",
        genre="camera_registry",
        observed=date(1970, 1, 1),
        indep="src:b",
    )
    # Ancient (1970) dated claims: admissible but HISTORICAL-weak — they pool
    # (within tolerance) and land UNRESOLVED U1 rather than resolving.
    r = _resolve("camera_latitude", [a, b])
    assert r.resolution_status == "UNRESOLVED"
    assert r.unresolved_code == "U1"
    # The dissent signal survives the unresolved outcome…
    assert r.contested_claim_ids == ("b",)
    # …but the rationale is the honest UNRESOLVED one, never the RESOLVED_*
    # contested template claiming a resolved value.
    assert r.rationale_code.startswith("UNRESOLVED_")
    assert "as reported by" not in r.rationale_text


def test_beyond_tolerance_disagreement_is_a_real_conflict() -> None:
    # 0.002° apart exceeds the declared 0.0005° tolerance: two distinct
    # candidates, the dispositive claim wins, and the loser is a genuine
    # dissenting candidate — a resolved_conflict.
    a = _claim(
        "a",
        "camera_latitude",
        52.1000,
        R="R1",
        genre="camera_registry",
        observed=date(2026, 8, 1),
        indep="src:a",
    )
    b = _claim(
        "b",
        "camera_latitude",
        52.1020,
        R="R3",
        genre="camera_registry",
        observed=date(2026, 8, 1),
        indep="src:b",
    )
    r = _resolve("camera_latitude", [a, b])
    assert r.resolution_status == "RESOLVED"
    assert r.value == 52.1000
    assert r.contradiction_state == "resolved_conflict"
    assert r.agreement == "CONTESTED"
    assert r.contested_claim_ids == ()
    assert "b" in r.dissenting_claim_ids


def test_no_declared_tolerance_means_any_disagreement_is_a_candidate_conflict() -> None:
    # The recorded default (never a guessed tolerance): a predicate without a
    # declared value_tolerance treats any disagreement as a candidate
    # conflict — contract_signed_date is categorical, so the dissenting
    # claim forms its own candidate.
    a = _claim(
        "a",
        "contract_signed_date",
        "2025-04-03",
        R="R1",
        genre="executed_contract",
        observed=date(2025, 5, 1),
        indep="src:a",
    )
    b = _claim(
        "b",
        "contract_signed_date",
        "2025-04-04",
        R="R3",
        genre="news_article",
        observed=date(2025, 5, 2),
        indep="src:b",
    )
    r = _resolve("contract_signed_date", [a, b])
    # The disagreement forms its own candidate (never pooled away): a genuine
    # conflict state with the dissenting claim retained — here a U3 standoff
    # because one source vs one source is never resolvable by fiat.
    assert r.contradiction_state == "unresolved_conflict"
    assert "b" in r.dissenting_claim_ids


# --- declared independence / the mirror rule (the P35.25 input this reads) ----


def test_a_mirrors_agreement_counts_as_one_voice() -> None:
    # Two claims sharing ONE declared independence class agreeing on a value
    # are one voice: the resolved class set has a single member.
    a = _claim(
        "a",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        indep="mirror:upstream",
        source_id="src:a",
        method="m1",
    )
    b = _claim(
        "b",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 1),
        indep="mirror:upstream",
        source_id="src:b",
        method="m2",
    )
    r = _resolve("active_device_count", [a, b])
    assert r.resolution_status == "RESOLVED"
    assert r.independence_class_ids == ("mirror:upstream",)
    # CONFIRMED needs two W3+ classes; a single mirror class can never reach it.
    assert r.support != "CONFIRMED"


def test_a_mirror_disagreement_structures_not_doubles() -> None:
    # Two members of one mirror class disagreeing (38 vs 40) plus an
    # independent claim for 38: the mirror casts ONE voice for each side, so
    # the winner has two classes — not three — and the second candidate's
    # class overlaps the winner's (no U2 standoff), a resolved_conflict.
    m1 = _claim(
        "m1",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        indep="mirror:up",
        source_id="src:m1",
        method="x",
    )
    m2 = _claim(
        "m2",
        "active_device_count",
        40,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        indep="mirror:up",
        source_id="src:m2",
        method="y",
    )
    c = _claim(
        "c",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        indep="src:c",
        source_id="src:c",
        method="z",
    )
    r = _resolve("active_device_count", [m1, m2, c])
    assert r.resolution_status == "RESOLVED"
    assert r.value == 38
    assert set(r.independence_class_ids) == {"mirror:up", "src:c"}
    assert r.contradiction_state == "resolved_conflict"


# --- the four-state vocabulary is preserved (deliverable 4) -------------------


def test_contradiction_state_is_exactly_the_four_state_vocabulary() -> None:
    # ``contested`` is a dissent SIGNAL (agreement axis + contested ids),
    # never a state — every emitted state stays in the SIG-STORE-015 set.
    cases = [
        _resolve(
            "contracted_device_count",
            [
                _claim(
                    "a",
                    "contracted_device_count",
                    1,
                    R="R1",
                    genre="executed_contract",
                    observed=date(2025, 1, 1),
                    indep="a",
                ),
            ],
        ),
        _resolve(
            "camera_latitude",
            [
                _claim(
                    "a",
                    "camera_latitude",
                    52.1,
                    R="R3",
                    genre="camera_registry",
                    observed=date(2026, 8, 1),
                    indep="a",
                ),
                _claim(
                    "b",
                    "camera_latitude",
                    52.1004,
                    R="R3",
                    genre="camera_registry",
                    observed=date(2026, 8, 1),
                    indep="b",
                ),
            ],
        ),
        _resolve(
            "camera_latitude",
            [
                _claim(
                    "a",
                    "camera_latitude",
                    52.1,
                    R="R1",
                    genre="camera_registry",
                    observed=date(2026, 8, 1),
                    indep="a",
                ),
                _claim(
                    "b",
                    "camera_latitude",
                    52.2,
                    R="R3",
                    genre="camera_registry",
                    observed=date(2026, 8, 1),
                    indep="b",
                ),
            ],
        ),
        _resolve(
            "active_device_count",
            [
                _claim(
                    "a",
                    "active_device_count",
                    38,
                    R="R2",
                    genre="portal_snapshot",
                    observed=date(2026, 8, 1),
                    indep="a",
                    method="m1",
                ),
                _claim(
                    "b",
                    "active_device_count",
                    40,
                    R="R2",
                    genre="portal_snapshot",
                    observed=date(2026, 8, 1),
                    indep="b",
                    method="m2",
                ),
            ],
        ),
        _resolve(
            "contract_signed_date",
            [
                _claim(
                    "a",
                    "contract_signed_date",
                    "x",
                    R="R2",
                    genre="portal_snapshot",
                    observed=date(2026, 1, 1),
                ),
            ],
        ),
    ]
    states = {r.contradiction_state for r in cases}
    assert states <= FOUR_STATES
    assert states == {
        "uncontested",  # single-claim + within-tolerance contested
        "resolved_conflict",
        "unresolved_conflict",  # the U2 standoff
        "insufficient",  # the D6-only pair (U0)
    }
    assert "contested" not in states


# --- input digest covers the new decision inputs (SIG-RECON-020) ---------------


def test_input_digest_moves_with_valid_bounds_and_declared_directness() -> None:
    # A re-perioded or re-graded claim is a different decision input: the
    # digest token — and so the pair's input_digest — MUST move, minting the
    # superseding resolution append-only rather than standing on stale inputs.
    base = _claim(
        "a",
        "contracted_device_count",
        299,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        valid_from=date(2024, 1, 1),
        declared_d="D1",
    )
    assert base.digest_token() != replace(base, valid_to=date(2026, 1, 1)).digest_token()
    assert base.digest_token() != replace(base, declared_directness="D3").digest_token()
    assert base.digest_token() != replace(base, declared_directness=None).digest_token()
    r1 = _resolve("contracted_device_count", [base])
    r2 = _resolve("contracted_device_count", [replace(base, declared_directness="D3")])
    assert r1.input_digest != r2.input_digest


# --- the read-only rematerialize delta classes (deliverable 5) -----------------


def test_classify_pair_delta_names_every_transition() -> None:
    from reconcile.materialize import classify_pair_delta

    # Temporal deconfliction: the new pass excluded a claim by valid period.
    r = _resolution(
        contradiction_state="uncontested",
        rules_fired=("SIG-RECON-006:1.2",),
        winning_claim_id="new",
        value=42,
    )
    classes = classify_pair_delta(_live("unresolved_conflict"), r)
    assert "temporal-deconflicted" in classes
    assert "state-shift" in classes

    # Directness reweight: a declared D fired.
    r = _resolution(rules_fired=("SIG-EPIS-017:declared_directness=D4",))
    assert "directness-reweighted" in classify_pair_delta(_live("uncontested"), r)

    # Contested disclosure without a state flip (the F-519 signal itself).
    r = _resolution(contested_claim_ids=("b",), agreement="MINOR_DISAGREEMENT")
    assert "contested-disclosed" in classify_pair_delta(_live("uncontested"), r)

    # Tolerance de-escalation: a conflict state resolved into contested dissent.
    r = _resolution(
        contradiction_state="uncontested",
        contested_claim_ids=("b",),
        agreement="MINOR_DISAGREEMENT",
    )
    classes = classify_pair_delta(_live("resolved_conflict"), r)
    assert "tolerance-de-escalated" in classes
    assert "contested-disclosed" in classes

    # Escalation + reclassification + value revision.
    r = _resolution(
        contradiction_state="unresolved_conflict",
        resolution_status="UNRESOLVED",
        value=None,
        winning_claim_id=None,
    )
    assert "escalated-conflict" in classify_pair_delta(_live("uncontested"), r)
    assert "conflict-reclassified" in classify_pair_delta(_live("resolved_conflict"), r)
    r = _resolution(value=99, winning_claim_id="z")
    assert "value-revised" in classify_pair_delta(_live("uncontested"), r)

    # A first materialization + the honest residual class.
    assert classify_pair_delta(None, _resolution()) == ("new-resolution",)
    assert classify_pair_delta(_live("uncontested"), _resolution()) == ("other-input-change",)


def test_rematerialize_report_vocabulary_is_closed() -> None:
    # The report's delta-class vocabulary is the committed set — the queued
    # leg's state-distribution report explains every delta with these names.
    from reconcile.materialize import DELTA_CLASSES

    assert set(DELTA_CLASSES) == {
        "new-resolution",
        "temporal-deconflicted",
        "directness-reweighted",
        "contested-disclosed",
        "tolerance-de-escalated",
        "escalated-conflict",
        "conflict-reclassified",
        "state-shift",
        "value-revised",
        "other-input-change",
    }

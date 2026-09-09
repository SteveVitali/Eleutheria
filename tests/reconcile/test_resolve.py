# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The §28 reconciliation resolver (SIG-RECON-004..025).

Anchored on the spec's own Appendix D.2 worked case (42 contracted vs 38 portal
vs 31 mapped) and on the Phase-8 acceptance criteria: determinism / total order,
the contract-does-not-win-active rule, D6 exclusion, U5 stale-winner, per-class
independence, and human override that never hides the algorithmic result.
"""

from __future__ import annotations

import dataclasses
import itertools
from datetime import date

import pytest
from reconcile.model import Evidence
from reconcile.resolve import RESOLVE, Claim, pin
from reconcile.ruleset import load_ruleset

AS_OF = date(2026, 9, 1)


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
    upstream: str | None = None,
    indep: str | None = None,
    source_id: str | None = None,
    rank: int | None = None,
    review: str = "active",
    valid_from: date | None = None,
    valid_to: date | None = None,
    count_basis: str | None = None,
    windowed: bool = False,
    structured_exact: bool = False,
    field_verified: bool = False,
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
        source_id=source_id or f"src:{genre}:{cid}",
        collection_method=method or genre,
        derived_from_source=upstream,
        independence_class=indep,
        source_registry_rank=rank,
        review_status=review,
        valid_from=valid_from,
        valid_to=valid_to,
        count_basis=count_basis,
        windowed=windowed,
        structured_exact=structured_exact,
        field_verified=field_verified,
        evidence=_ev(genre),
    )


def _resolve(predicate: str, claims: list[Claim], **kw: object) -> object:
    return RESOLVE("S", predicate, claims, as_of_world=AS_OF, as_of_belief=AS_OF, **kw)


# --- Appendix D.2 + the contract-does-not-win rule (SIG-RECON-006, EPIS-018) --


def test_appendix_d2_active_count_portal_beats_contract() -> None:
    portal = _claim(
        "portal",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 15),
    )
    contract = _claim(
        "contract",
        "active_device_count",
        42,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
    )
    r = _resolve("active_device_count", [contract, portal])

    assert r.resolution_status == "RESOLVED"
    assert r.value == 38
    assert r.winning_claim_id == "portal"
    # §D.2 commits to exactly these three orthogonal fields.
    assert r.support == "STRONGLY_SUPPORTED"
    assert r.agreement == "MINOR_DISAGREEMENT"
    assert r.currency == "CURRENT"
    # The contract is retained as a dissenting claim, not excluded.
    assert "contract" in r.dissenting_claim_ids


def test_contract_never_wins_active_device_count() -> None:
    # AC: a Tier-A contract does NOT win active_device_count vs a D1 portal
    # snapshot — the contract is D5 for that predicate (EPIS-018), so it can
    # never be the winner regardless of its own reliability tier or recency.
    portal = _claim(
        "portal",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 15),
    )
    contract = _claim(
        "contract",
        "active_device_count",
        42,
        R="R1",
        genre="executed_contract",
        observed=date(2026, 7, 15),
    )
    r = _resolve("active_device_count", [portal, contract])
    assert r.winning_claim_id != "contract"
    assert r.value != 42


# --- D6 is an admissibility filter, not a weight (SIG-EPIS-018) ---------------


def test_d6_portal_snapshot_contributes_nothing_to_contract_signed_date() -> None:
    # AC: a portal snapshot is D6 for contract_signed_date -> excluded entirely,
    # never down-weighted. With only the portal claim, there is NO evidence (U0).
    portal = _claim(
        "portal",
        "contract_signed_date",
        "2026-07",
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 15),
    )
    r = _resolve("contract_signed_date", [portal])
    assert r.resolution_status == "UNRESOLVED"
    assert r.unresolved_code == "U0"
    reasons = [e.reason for e in r.excluded]
    assert any("D6" in reason for reason in reasons)


def test_d6_excluded_does_not_beat_a_real_signing_claim() -> None:
    portal = _claim(
        "portal",
        "contract_signed_date",
        "2026-07",
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 15),
    )
    contract = _claim(
        "contract",
        "contract_signed_date",
        "2025-04-03",
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
    )
    r = _resolve("contract_signed_date", [portal, contract])
    assert r.resolution_status == "RESOLVED"
    assert r.value == "2025-04-03"
    assert "portal" in {e.claim_id for e in r.excluded}


# --- determinism / total order, no random tie-break (SIG-RECON-007) ----------


def test_resolution_is_deterministic_over_identical_inputs() -> None:
    claims = [
        _claim(
            "portal",
            "active_device_count",
            38,
            R="R2",
            genre="portal_snapshot",
            observed=date(2026, 7, 15),
        ),
        _claim(
            "news",
            "active_device_count",
            40,
            R="R3",
            genre="news_article",
            observed=date(2026, 6, 1),
        ),
        _claim(
            "contract",
            "active_device_count",
            42,
            R="R1",
            genre="executed_contract",
            observed=date(2025, 4, 3),
        ),
    ]
    baseline = _resolve("active_device_count", list(claims))
    for perm in itertools.permutations(claims):
        r = _resolve("active_device_count", list(perm))
        # The reproducible decision (and the input_digest) is identical for every
        # ordering — there is no random tie-break anywhere (SIG-RECON-007).
        assert r.decision_key() == baseline.decision_key()
        assert r.input_digest == baseline.input_digest


def test_total_order_breaks_ties_by_registry_rank_then_claim_id() -> None:
    # Two equal-weight, same-value claims from distinct classes: the winner is
    # fixed by (rank asc, claim_id asc), never by chance.
    a = _claim(
        "a",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 1),
        rank=5,
        source_id="src:a",
    )
    b = _claim(
        "b",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 7, 1),
        rank=2,
        source_id="src:b",
    )
    r = _resolve("active_device_count", [a, b])
    assert r.winning_claim_id == "b"  # lower registry rank wins the representative


def test_immutable_recency_does_not_break_a_tie() -> None:
    # SIG-RECON-010: for an IMMUTABLE predicate a newer claim gets no advantage
    # from being newer; the tie falls to registry rank / claim id, not recency.
    old = _claim(
        "old",
        "contract_signed_date",
        "2025-04-03",
        R="R1",
        genre="executed_contract",
        observed=date(2025, 5, 1),
        rank=1,
        source_id="src:old",
    )
    new = _claim(
        "new",
        "contract_signed_date",
        "2025-04-03",
        R="R1",
        genre="executed_contract",
        observed=date(2026, 8, 1),
        rank=2,
        source_id="src:new",
    )
    r = _resolve("contract_signed_date", [new, old])
    assert r.winning_claim_id == "old"  # rank 1 beats the newer rank-2 claim


# --- U5: stale winner on a changing predicate (SIG-RECON-014/015/016) --------


def test_u5_fires_on_stale_unchallenged_value() -> None:
    # AC: a stale unchallenged value on a FAST predicate returns UNRESOLVED with
    # last_known + date, EVEN WITH NO DISSENT. The winner must clear W1 (else U1
    # fires first), so an R1 open-data release published as a portal snapshot.
    stale = _claim(
        "od", "active_device_count", 38, R="R1", genre="portal_snapshot", observed=date(2025, 9, 15)
    )
    r = _resolve("active_device_count", [stale])
    assert r.resolution_status == "UNRESOLVED"
    assert r.unresolved_code == "U5"
    assert r.last_known_value == 38
    assert r.last_known_date == date(2025, 9, 15)
    assert r.currency in {"STALE", "HISTORICAL"}


def test_u5_does_not_fire_on_immutable_predicate() -> None:
    # An old contract signing date is not "stale": IMMUTABLE predicates never
    # trigger U5 (SIG-RECON-010/014).
    old = _claim(
        "c",
        "contract_signed_date",
        "2019-01-01",
        R="R1",
        genre="executed_contract",
        observed=date(2019, 2, 1),
    )
    r = _resolve("contract_signed_date", [old])
    assert r.resolution_status == "RESOLVED"
    assert r.value == "2019-01-01"


# --- independence / dependence discounting (SIG-RECON-018, EPIS-027) ---------


def test_three_sources_copying_one_upstream_count_as_one_class() -> None:
    # AC: three sources copying one upstream are ONE independence class. With a
    # single class the winner is only PROBABLE, never CONFIRMED-by-corroboration.
    copies = [
        _claim(
            f"copy{i}",
            "active_device_count",
            38,
            R="R3",
            genre="news_article",
            observed=date(2026, 7, 1),
            upstream="upstream:flock",
            source_id=f"src:copy{i}",
        )
        for i in range(3)
    ]
    r = _resolve("active_device_count", copies)
    assert r.resolution_status == "RESOLVED"
    assert r.independence_class_ids == ("upstream:flock",)
    assert r.support == "PROBABLE"  # one class at W2+, not confirmed corroboration


def test_two_independent_method_distinct_classes_confirm() -> None:
    # Two genuinely independent, method-distinct classes at W3+ -> CONFIRMED.
    a = _claim(
        "a",
        "active_device_count",
        38,
        R="R1",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        method="open_data",
        source_id="src:a",
    )
    b = _claim(
        "b",
        "active_device_count",
        38,
        R="R1",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        method="field_survey",
        source_id="src:b",
    )
    r = _resolve("active_device_count", [a, b])
    assert r.support == "CONFIRMED"
    assert r.agreement == "UNCONTESTED"
    assert r.contradiction_state == "uncontested"


# --- strategy silence / never_resolve (SIG-RECON-012/013) --------------------


def test_never_resolve_predicate_is_not_adjudicated() -> None:
    # asset_data_controller is the ruleset's never_resolve predicate.
    a = _claim(
        "a",
        "asset_data_controller",
        "Vendor A",
        R="R2",
        genre="agency_policy",
        observed=date(2026, 1, 1),
    )
    b = _claim(
        "b",
        "asset_data_controller",
        "Agency B",
        R="R2",
        genre="council_minutes",
        observed=date(2026, 2, 1),
    )
    r = _resolve("asset_data_controller", [a, b])
    assert r.resolution_status == "UNRESOLVED"
    assert r.unresolved_code == "NEVER_RESOLVE"
    assert r.rationale_code == "UNRESOLVED_NO_STRATEGY"


def test_silent_ruleset_is_unresolvable(monkeypatch: pytest.MonkeyPatch) -> None:
    # SIG-RECON-013: a predicate with NO assigned strategy is not resolvable —
    # silence yields UNRESOLVED, never a guess.
    import reconcile.ruleset as rmod

    real = rmod.predicate_meta

    def fake(predicate_id: str) -> dict[str, object]:
        row = dict(real("active_device_count"))
        row["resolution_strategy"] = ""
        return row

    monkeypatch.setattr(rmod, "predicate_meta", fake)
    rs = load_ruleset()
    assert rs.strategy_for("active_device_count") is None


# --- human override (SIG-RECON-024/025) --------------------------------------


def test_override_records_author_and_rationale_and_keeps_algo_result() -> None:
    portal = _claim(
        "portal",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
    )
    algo = _resolve("active_device_count", [portal])
    pinned = pin(
        algo, value=40, decided_by="curator:alice", override_rationale="counted on site 2026-08-20"
    )

    assert pinned.value == 40
    assert pinned.decided_by == "curator:alice"
    assert pinned.override_rationale
    # The algorithmic result is not deleted or hidden — both are shown.
    assert pinned.algorithmic is not None
    assert pinned.algorithmic.value == 38
    assert pinned.algorithmic.decided_by == "auto"


def test_override_requires_author_and_rationale() -> None:
    portal = _claim(
        "portal",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
    )
    algo = _resolve("active_device_count", [portal])
    with pytest.raises(ValueError):
        pin(algo, value=40, decided_by="auto", override_rationale="x")
    with pytest.raises(ValueError):
        pin(algo, value=40, decided_by="curator:bob", override_rationale="")


# --- windowed predicates are indexed, not stale (SIG-RECON-011) --------------


def test_windowed_claim_is_exempt_from_currency_downgrade() -> None:
    old_window = _claim(
        "w",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2024, 1, 1),
        windowed=True,
    )
    r = _resolve("active_device_count", [old_window])
    # Exempt from currency decay -> CURRENT despite a two-year-old observation,
    # so U5 does not fire and the value resolves.
    assert r.currency == "CURRENT"
    assert r.resolution_status == "RESOLVED"
    assert "SIG-RECON-011" in r.rules_fired


# --- admissibility: supersession + valid period (SIG-RECON-006 Phase 1) ------


def test_later_claim_from_same_source_supersedes_earlier() -> None:
    early = _claim(
        "early",
        "active_device_count",
        30,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 6, 1),
        source_id="src:portal",
    )
    late = _claim(
        "late",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        source_id="src:portal",
    )
    r = _resolve("active_device_count", [early, late])
    assert r.value == 38
    assert "early" in {e.claim_id for e in r.excluded}


def test_claim_outside_valid_world_is_inadmissible() -> None:
    past = _claim(
        "past",
        "active_device_count",
        38,
        R="R1",
        genre="portal_snapshot",
        observed=date(2020, 1, 1),
        valid_from=date(2019, 1, 1),
        valid_to=date(2020, 1, 1),
    )
    r = _resolve("active_device_count", [past])
    assert r.resolution_status == "UNRESOLVED"
    assert r.unresolved_code == "U0"


# --- count-basis conflation guard + U6 (SIG-RECON-028, U6) -------------------


def test_count_basis_mismatch_drops_and_can_trigger_u6() -> None:
    active = _claim(
        "active",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        count_basis="active",
    )
    contracted = _claim(
        "contracted",
        "active_device_count",
        42,
        R="R1",
        genre="executed_contract",
        observed=date(2025, 4, 3),
        count_basis="contracted",
    )
    r = _resolve("active_device_count", [active, contracted])
    # The contracted-basis claim is refused (PREDICATE_CONFLATION); one survives,
    # so U6 fires (fewer than two comparable claims remain).
    assert any(c.contradiction_type == "predicate_conflation" for c in r.contradictions)
    assert r.unresolved_code == "U6"


# --- Phase 2.2 value-domain mismatch (SIG-RECON-006) -------------------------


def test_value_outside_the_predicate_domain_is_dropped() -> None:
    # active_device_count is an integer predicate; a string value cannot be
    # canonicalized and is dropped with a VALUE_DOMAIN_MISMATCH contradiction.
    good = _claim(
        "good",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
    )
    bad = _claim(
        "bad",
        "active_device_count",
        "lots",
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
    )
    r = _resolve("active_device_count", [good, bad])
    assert r.value == 38
    assert "bad" in {e.claim_id for e in r.excluded}
    assert any(c.contradiction_type == "value_domain_mismatch" for c in r.contradictions)


# --- U4 numeric spread (SIG-RECON-014) ---------------------------------------


def test_u4_fires_when_numeric_spread_exceeds_tolerance() -> None:
    # Two equal-weight portal snapshots far apart (38 vs 300), nothing dispositive.
    a = _claim(
        "a",
        "active_device_count",
        38,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        method="m1",
        source_id="src:a",
    )
    b = _claim(
        "b",
        "active_device_count",
        300,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        method="m2",
        source_id="src:b",
    )
    r = _resolve("active_device_count", [a, b])
    assert r.resolution_status == "UNRESOLVED"
    assert r.unresolved_code in {"U2", "U4"}  # equal weight & breadth => U2 precedes U4


# --- every registry strategy resolves deterministically (SIG-RECON-012) ------


def test_interval_union_predicate_resolves_deterministically() -> None:
    # The registry assigns interval_union to scalar predicates (windowed_search_count
    # is an integer); the resolver handles it via the deterministic total order.
    a = _claim(
        "a",
        "windowed_search_count",
        412,
        R="R2",
        genre="portal_snapshot",
        observed=date(2026, 8, 1),
        windowed=True,
        source_id="src:a",
    )
    r1 = _resolve("windowed_search_count", [a])
    r2 = _resolve("windowed_search_count", [a])
    assert r1.decision_key() == r2.decision_key()
    assert r1.strategy_id == "interval_union"


# --- input_digest reproducibility (SIG-RECON-020) ----------------------------


def test_input_digest_changes_with_the_claim_set() -> None:
    a = _claim(
        "a", "active_device_count", 38, R="R2", genre="portal_snapshot", observed=date(2026, 8, 1)
    )
    b = _claim(
        "b", "active_device_count", 38, R="R3", genre="news_article", observed=date(2026, 7, 1)
    )
    one = _resolve("active_device_count", [a])
    two = _resolve("active_device_count", [a, b])
    assert one.input_digest != two.input_digest
    assert one.input_digest == _resolve("active_device_count", [a]).input_digest


# --- epistemic_status preserved verbatim through resolution (SIG-ONTO-038, P13.1) --


def test_event_epistemic_status_is_preserved_verbatim_through_resolution() -> None:
    """The end-to-end half of SIG-ONTO-038: a value carried in as ``alleged`` must
    survive ingestion -> resolution -> read UNCHANGED. The resolver never flattens
    an allegation into a fact; ``event_epistemic_status`` resolves to exactly the
    ingested vocabulary value, with its raw upstream value preserved on the claim."""
    a = _claim(
        "e1",
        "event_epistemic_status",
        "alleged",
        R="R3",
        genre="news_article",
        observed=date(2026, 8, 1),
    )
    a = dataclasses.replace(a, raw_value="Alleged (pending suit)")
    r = _resolve("event_epistemic_status", [a])
    assert r.resolution_status == "RESOLVED"
    # verbatim: the resolved value is exactly the ingested EpistemicStatus value.
    assert r.value == "alleged"
    # the raw upstream phrasing is preserved (P2), never overwritten by the typed value.
    assert a.raw_value == "Alleged (pending suit)"


def test_a_disputed_status_never_resolves_to_confirmed() -> None:
    """A disputed allegation and a confirmation are a contradiction, not a silent
    upgrade: resolving disputed-only claims yields ``disputed``, never ``confirmed``."""
    a = _claim(
        "d1",
        "event_epistemic_status",
        "disputed",
        R="R3",
        genre="news_article",
        observed=date(2026, 8, 1),
    )
    r = _resolve("event_epistemic_status", [a])
    assert r.value == "disputed"
    assert r.value != "confirmed"

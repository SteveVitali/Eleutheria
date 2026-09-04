# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Camera-count reconciliation (§29.1, SIG-RECON-026/027/028/029).

Two anchors: the spec's own Appendix D.2 worked case (42/38/31), and the P06.1
slice jurisdiction (Oklahoma City: 90 contracted / 90 active / 299 mapped).
"""

from __future__ import annotations

from datetime import date

import pytest
from reconcile.counts import (
    reconcile_as_single_count,
    reconcile_counts,
)
from reconcile.model import (
    PREDICATE_CONFLATION,
    VALUE_DISAGREEMENT,
    CountClaim,
    Evidence,
)

AS_OF = date(2026, 9, 1)


def _ev(source_family: str, artifact_type: str, locator: str) -> Evidence:
    return Evidence(
        source_id=f"src:{source_family}",
        source_family=source_family,
        artifact_type=artifact_type,
        stable_locator=locator,
        capture_digest="b" + "0" * 40,
        locator={"selector": "#count", "text_span": [0, 3]},
        excerpt="…",
    )


def _claim(
    basis: str,
    value: int,
    *,
    R: str,
    genre: str,
    observed: date,
    integrity: str = "I1",
    structured_exact: bool = False,
    scope: str | None = None,
) -> CountClaim:
    return CountClaim(
        count_basis=basis,
        value=value,
        reliability=R,
        integrity=integrity,
        observed_at=observed,
        genre=genre,
        evidence=_ev(genre, genre, f"https://example/{basis}/{value}"),
        structured_exact=structured_exact,
        scope_note=scope,
    )


# --- the spec's own worked example (Appendix D.2) -----------------------------


def _appendix_d_claims() -> list[CountClaim]:
    return [
        # contract, signed 2025-04-03: contracted (D1 -> W4) AND weak active (D5 -> W1)
        _claim("contracted", 42, R="R1", genre="executed_contract", observed=date(2025, 4, 3)),
        _claim("active", 42, R="R1", genre="executed_contract", observed=date(2025, 4, 3)),
        # portal capture 2026-07-15: active (D1 -> W3)
        _claim("active", 38, R="R2", genre="portal_snapshot", observed=date(2026, 7, 15)),
        # OSM 2026-08-20: mapped (D3 + structured export -> W2)
        _claim(
            "mapped",
            31,
            R="R5",
            genre="osm_node_set",
            observed=date(2026, 8, 20),
            structured_exact=True,
        ),
    ]


def test_three_answers_to_three_questions_not_one() -> None:
    rec = reconcile_counts("dep:example", _appendix_d_claims(), as_of=AS_OF)
    # contracted resolves to 42 at W4; active resolves to 38 (portal beats the
    # contract's D5 evidence by two weight classes); mapped is 31, a lower bound.
    assert rec.resolutions["contracted"].value == 42
    assert rec.resolutions["contracted"].weight == 4
    assert rec.resolutions["active"].value == 38
    assert rec.resolutions["active"].weight == 3
    assert rec.resolutions["mapped"].value == 31
    assert rec.resolutions["mapped"].lower_bound is True
    # The contract's 42-as-active is retained as a dissent, not resolving.
    assert any(d.value == 42 for d in rec.resolutions["active"].dissenting)


def test_no_single_true_count_is_emitted() -> None:
    rec = reconcile_counts("dep:example", _appendix_d_claims(), as_of=AS_OF)
    with pytest.raises(NotImplementedError):
        rec.true_count()


def test_deltas_become_research_tasks() -> None:
    rec = reconcile_counts("dep:example", _appendix_d_claims(), as_of=AS_OF)
    deltas = {(d.higher_basis, d.lower_basis): d for d in rec.unresolved_deltas}
    assert deltas[("contracted", "active")].delta == 4  # 42 - 38
    assert deltas[("active", "mapped")].delta == 7  # 38 - 31
    # every delta carries a typed task with a testable closing condition
    for d in rec.unresolved_deltas:
        assert d.task.closing_condition
        assert d.task in rec.tasks


# --- PREDICATE_CONFLATION guard (SIG-RECON-028) ------------------------------


def test_conflating_contracted_and_mapped_emits_predicate_conflation() -> None:
    contract = _claim(
        "contracted", 90, R="R1", genre="executed_contract", observed=date(2023, 1, 1)
    )
    deflock = _claim(
        "mapped",
        299,
        R="R5",
        genre="osm_node_set",
        observed=date(2026, 8, 20),
        structured_exact=True,
    )
    con = reconcile_as_single_count("dep:okc", [contract, deflock])
    assert con is not None
    assert con.contradiction_type == PREDICATE_CONFLATION
    assert con.severity == "blocking"
    assert set(con.claim_values) == {90, 299}


def test_same_basis_claims_do_not_trigger_conflation() -> None:
    a = _claim("active", 90, R="R2", genre="portal_snapshot", observed=date(2026, 8, 1))
    b = _claim("active", 88, R="R2", genre="portal_snapshot", observed=date(2026, 6, 1))
    assert reconcile_as_single_count("dep:okc", [a, b]) is None


# --- the OKC slice numbers ---------------------------------------------------


def _okc_claims() -> list[CountClaim]:
    return [
        _claim("contracted", 90, R="R1", genre="executed_contract", observed=date(2023, 1, 1)),
        _claim("active", 90, R="R2", genre="council_minutes", observed=date(2026, 8, 18)),
        _claim(
            "mapped",
            299,
            R="R5",
            genre="osm_node_set",
            observed=date(2026, 8, 20),
            structured_exact=True,
            scope="metro",
        ),
        # within-predicate disagreement: DeFlock ~299 vs Chief Bacy ~190
        _claim(
            "claimed", 299, R="R4", genre="news_article", observed=date(2026, 8, 3), scope="metro"
        ),
        _claim(
            "claimed",
            190,
            R="R2",
            genre="council_minutes",
            observed=date(2026, 8, 18),
            scope="city limits",
        ),
    ]


def test_okc_predicates_stay_distinct() -> None:
    rec = reconcile_counts("dep:okc", _okc_claims(), as_of=AS_OF)
    assert rec.resolutions["contracted"].value == 90
    assert rec.resolutions["active"].value == 90
    assert rec.resolutions["mapped"].value == 299
    assert rec.resolutions["mapped"].lower_bound is True


def test_okc_claimed_count_disagreement_is_a_contradiction_not_a_collapse() -> None:
    rec = reconcile_counts("dep:okc", _okc_claims(), as_of=AS_OF)
    disagreements = [c for c in rec.contradictions if c.contradiction_type == VALUE_DISAGREEMENT]
    assert disagreements, "expected a value_disagreement on claimed_device_count"
    con = disagreements[0]
    assert set(con.claim_values) == {190, 299}
    # both figures retained; a research task is generated
    assert any(t.task_type == "reconcile_disagreeing_count" for t in rec.tasks)


def test_okc_mapped_exceeds_active_becomes_attribution_task() -> None:
    rec = reconcile_counts("dep:okc", _okc_claims(), as_of=AS_OF)
    d = next(
        d for d in rec.unresolved_deltas if (d.higher_basis, d.lower_basis) == ("active", "mapped")
    )
    # active 90 - mapped 299 = -209: the surplus is non-city / unknown operators.
    assert d.delta == -209
    assert "operator" in d.task.closing_condition.lower()

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Camera-registry predicates in the §28 resolver (P30.2a, ADR-104).

Pins the four things ADR-104 decides, against the generated registry and the real
resolver (no Postgres; the DB round-trip is ``tests/db/test_resolution_materialize.py``):

* every camera-registry predicate measured on the hosted spine has a complete registry
  row (volatility + half-life, a strategy, a full directness row) — SIG-ONTO-066/067;
* coordinates carry an absolute tolerance: values that agree within it corroborate one
  candidate whose value is an OBSERVED value (never a mean, §19.4), and any spread beyond
  it — including a single-linkage chain — is UNRESOLVED with the dissent kept visible;
* identifiers are exact-match identity: two different ids never pool;
* an undated claim is dated from its capture, and that inference is labelled.
"""

from __future__ import annotations

import contextlib
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
from reconcile.materialize import (
    CAPTURE_TIME_BASIS,
    CAPTURE_TIME_JOIN,
    detected_contradictions,
    materialize_resolutions,
    observation_time,
)
from reconcile.resolve import RESOLVE, Claim
from reconcile.ruleset import load_ruleset
from reconcile.weight import predicate_registry

from reconcile import ruleset as ruleset_mod

REPO = Path(__file__).resolve().parents[2]
INVENTORY = REPO / "docs/build/reports/p30.2a-hosted/predicate_inventory_before.json"
AS_OF = date(2026, 9, 24)
CAPTURED = date(2026, 9, 18)
TOL = 0.0005


def _claim(
    cid: str,
    value: object,
    *,
    pred: str = "camera_latitude",
    source: str = "dot_511_ok",
    genre: str = "camera_registry",
    observed_at: date = CAPTURED,
    basis: str = CAPTURE_TIME_BASIS,
) -> Claim:
    return Claim(
        claim_id=cid,
        subject_id="traffic_camera:dot_511_ok:t:1",
        predicate_id=pred,
        value=value,
        reliability="R3",
        integrity="I1",
        genre=genre,
        observed_at=observed_at,
        observed_at_basis=basis,
        source_id=source,
    )


def _resolve(pred: str, claims: list[Claim]):
    return RESOLVE(
        "traffic_camera:dot_511_ok:t:1",
        pred,
        claims,
        as_of_world=AS_OF,
        as_of_belief=AS_OF,
        computed_at=datetime(2026, 9, 24),
    )


# --- the registry rows (AC1/AC2) ---------------------------------------------------------


def _measured_camera_predicates() -> list[str]:
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    preds: list[str] = data["camera_registry_predicates"]
    assert preds, "the committed hosted inventory names the camera-registry predicates"
    return preds


def test_every_measured_camera_predicate_has_a_complete_registry_row() -> None:
    reg = predicate_registry()
    genres = set(
        json.loads((REPO / "ontology/generated/registry/predicate_registry.json").read_text())[
            "artifact_genres"
        ]
    )
    for pid in _measured_camera_predicates():
        row = reg[pid]  # KeyError here = an unregistered hosted camera predicate
        assert row["volatility_class"] and row["half_life"], pid
        assert load_ruleset().strategy_for(pid) is not None, pid
        assert set(row["directness"]) == genres, pid


def test_the_hosted_camera_genres_are_on_the_genre_axis() -> None:
    data = json.loads(INVENTORY.read_text(encoding="utf-8"))
    measured = {
        g
        for p in data["predicates"]
        if p["camera_registry_predicate"]
        for g in p["claims_by_genre"]
    }
    reg = predicate_registry()
    for pid in _measured_camera_predicates():
        assert measured <= set(reg[pid]["directness"]), pid


def test_strategy_choices_per_predicate_class() -> None:
    rs = load_ruleset()
    # coordinates: a spatial (absolute, degree) tolerance — not exact-match, not relative.
    for pid in ("camera_latitude", "camera_longitude"):
        assert rs.absolute_tolerance(pid) == TOL
        assert rs.predicate(pid)["value_tolerance"]["unit"] == "degree"
    # identifiers: identity-bearing, immutable, exact match only.
    for pid in ("external_id", "camera_external_ref"):
        assert rs.strategy_for(pid) == "authoritative_source_wins"
        assert rs.volatility_class(pid) == "IMMUTABLE"
        assert rs.absolute_tolerance(pid) is None
        assert rs.predicate(pid)["directness"]["camera_registry"] == "D1"
    # operator / jurisdiction: categorical.
    for pid in ("camera_operator", "camera_jurisdiction"):
        assert rs.strategy_for(pid) == "max_support"
    # operational status changes: FAST, latest observation wins (as operational_state).
    assert rs.strategy_for("camera_status") == "latest_observation_wins"
    assert rs.volatility_class("camera_status") == "FAST"


def test_p31_8_assessed_the_owed_camera_registry_and_connector_run_cells() -> None:
    # D-P30.2a-1 closed in P31.8: the remaining pre-existing rows no longer read
    # the P30.2a blanket D6 for camera_registry/connector_run — the cells are
    # assessed under ADR-104's rule (a connector pull is D3 for a record's
    # descriptive facts, D1 for its own identifiers; a camera registry bears on
    # camera-record facts and device counts, nothing else). The full
    # measured-pair admissibility invariant lives in
    # tests/ontology/test_predicate_registry_p318.py.
    reg = predicate_registry()
    # identifiers: the pull IS the record -> D1.
    assert reg["federal_award_id"]["directness"]["connector_run"] == "D1"
    assert reg["organization_ori"]["directness"]["connector_run"] == "D1"
    # descriptive facts: the pull strongly implies the record's fields -> D3.
    for pid in (
        "deployment_exists",
        "contract_value",
        "statutory_citation",
        "configured_retention_days",
        "active_device_count",
        "windowed_search_count",
        "asset_data_controller",  # admitted, then never_resolve fires (§12.4)
    ):
        assert reg[pid]["directness"]["connector_run"] == "D3", pid
    # a camera registry enumerates devices and states locations/operators; it
    # says nothing about procurement or proceedings.
    assert reg["active_device_count"]["directness"]["camera_registry"] == "D3"
    assert reg["fixed_asset_location"]["directness"]["camera_registry"] == "D2"
    assert reg["proceeding_posture"]["directness"]["camera_registry"] == "D6"
    assert reg["contract_value"]["directness"]["camera_registry"] == "D6"
    # the measured genres beyond the P31.5 axis are on every row.
    for row in reg.values():
        assert {
            "agenda_document",
            "bill_index",
            "portal_document",
            "community_map",
            "contract",
            "official_statement",
        } <= set(row["directness"])


def test_absolute_tolerance_rejects_an_unknown_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    rs = load_ruleset()
    monkeypatch.setattr(
        ruleset_mod,
        "predicate_meta",
        lambda pid: {"value_tolerance": {"kind": "relative", "value": 0.1}},
    )
    with pytest.raises(ValueError, match="unknown value_tolerance kind"):
        rs.absolute_tolerance("anything")


# --- resolution behaviour (AC3 semantics) ------------------------------------------------


def test_single_registry_coordinate_resolves_and_labels_the_capture_time() -> None:
    res = _resolve("camera_latitude", [_claim("c1", 35.4676)])
    assert res.resolution_status == "RESOLVED"
    assert res.value == 35.4676
    assert res.contradiction_state == "uncontested"
    assert res.strategy_id == "latest_observation_wins"
    assert f"SIG-RECON-008:observed_at={CAPTURE_TIME_BASIS}" in res.rules_fired


def test_undated_claim_without_the_capture_fallback_would_be_historical() -> None:
    # Why ADR-104 dates undated claims from the capture: the 1970 placeholder makes a
    # 2026 registry row HISTORICAL (C4) -> W1 -> U1, i.e. "insufficient evidence" — false.
    res = _resolve(
        "camera_latitude", [_claim("c1", 35.4676, observed_at=date(1970, 1, 1), basis="claim")]
    )
    assert res.resolution_status == "UNRESOLVED"
    assert res.unresolved_code == "U1"


def test_values_within_tolerance_corroborate_one_observed_value() -> None:
    a = _claim("c-a", 35.46760, source="dot_511_ok")
    b = _claim("c-b", 35.46790, source="camreg_okc")  # 0.0003 deg (~33 m) apart
    res = _resolve("camera_latitude", [a, b])
    assert res.resolution_status == "RESOLVED"
    assert set(res.supporting_claim_ids) == {"c-a", "c-b"}
    assert res.dissenting_claim_ids == ()
    # the winning value is one of the observed values — never an average (§19.4).
    assert res.value in {35.46760, 35.46790}
    assert res.value != pytest.approx((35.46760 + 35.46790) / 2)
    assert "SIG-RECON-014:value_tolerance" in res.rules_fired


def test_values_beyond_tolerance_stay_unresolved_and_visible() -> None:
    a = _claim("c-a", 35.4676, source="dot_511_ok")
    b = _claim("c-b", 35.4776, source="camreg_okc")  # 0.01 deg (~1.1 km) apart
    res = _resolve("camera_latitude", [a, b])
    assert res.resolution_status == "UNRESOLVED"
    assert res.unresolved_code == "U2"  # one source vs one equal source: a standoff
    assert res.contradiction_state == "unresolved_conflict"
    assert res.winning_claim_id is None
    assert set(res.considered_claim_ids) == {"c-a", "c-b"}
    found = detected_contradictions(res.subject_id, "camera_latitude", res, [a, b])
    assert [c.contradiction_type for c in found] == ["value_disagreement"]
    assert set(found[0].claim_ids) == {"c-a", "c-b"}


def test_two_pools_beyond_tolerance_fire_the_absolute_u4() -> None:
    # Two sources agree (one pool, two classes) and a third is ~1.1 km away: no U2/U3
    # standoff, so the absolute-tolerance U4 is what keeps the disagreement unresolved.
    claims = [
        _claim("c-a", 35.46760, source="s1"),
        _claim("c-b", 35.46770, source="s2"),
        _claim("c-c", 35.47760, source="s3"),
    ]
    res = _resolve("camera_latitude", claims)
    assert res.resolution_status == "UNRESOLVED"
    assert res.unresolved_code == "U4"
    assert res.contradiction_state == "unresolved_conflict"
    assert set(res.dissenting_claim_ids) == {"c-c"}


def test_absolute_u4_only_applies_to_tolerance_predicates() -> None:
    # The same three values on a predicate WITHOUT value_tolerance are exact candidates
    # judged by the relative U4 (0.03% spread < the SLOW 8% tolerance) — no pooling rule.
    claims = [
        _claim("c-a", 35.46760, pred="camera_name", source="s1"),
        _claim("c-b", 35.46770, pred="camera_name", source="s2"),
    ]
    res = _resolve("camera_name", claims)
    assert "SIG-RECON-014:value_tolerance" not in res.rules_fired


def test_a_single_linkage_chain_cannot_hide_a_wide_spread() -> None:
    # Each step is within tolerance, the whole chain is not: one pool, but U4 fires.
    claims = [
        _claim("c-a", 35.4670, source="s1"),
        _claim("c-b", 35.4674, source="s2"),
        _claim("c-c", 35.4678, source="s3"),
    ]
    res = _resolve("camera_latitude", claims)
    assert res.resolution_status == "UNRESOLVED"
    assert res.unresolved_code == "U4"


def test_identifiers_are_exact_match_identity() -> None:
    a = _claim("c-a", "CAM-17", pred="external_id", source="s1")
    b = _claim("c-b", "CAM-18", pred="external_id", source="s2")
    res = _resolve("external_id", [a, b])
    assert res.resolution_status == "UNRESOLVED"
    assert res.contradiction_state == "unresolved_conflict"


def test_same_source_reobservation_is_superseded_not_a_contradiction() -> None:
    # The hosted shape: every camera subject is one source's row; a later capture of the
    # same row supersedes the earlier (§28 Phase 1.4) — value resolution WITHIN a subject.
    old = _claim("c-old", 35.4676, observed_at=date(2026, 9, 17))
    new = _claim("c-new", 35.4680, observed_at=date(2026, 9, 21))
    res = _resolve("camera_latitude", [old, new])
    assert res.resolution_status == "RESOLVED"
    assert res.winning_claim_id == "c-new"
    assert any(e.claim_id == "c-old" and "superseded" in e.reason for e in res.excluded)


# --- the reader + materializer seam -------------------------------------------------------


def test_observation_time_prefers_the_claim_then_the_capture() -> None:
    assert observation_time(datetime(2026, 5, 1, 12), datetime(2026, 9, 18)) == (
        date(2026, 5, 1),
        "claim",
    )
    assert observation_time(None, datetime(2026, 9, 18, 3)) == (
        date(2026, 9, 18),
        CAPTURE_TIME_BASIS,
    )
    assert observation_time(None, None) == (date(1970, 1, 1), "claim")
    # the capture date is the UTC calendar date, whatever the session time zone.
    late = datetime(2026, 9, 17, 23, 30, tzinfo=timezone(timedelta(hours=-5)))
    assert observation_time(None, late) == (date(2026, 9, 18), CAPTURE_TIME_BASIS)


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]] | None = None, one: Any = None) -> None:
        self._rows = rows or []
        self._one = one

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self._rows

    def fetchone(self) -> Any:
        return self._one


class _FakeConn:
    """Records statements; serves claim rows; the resolution insert is idempotent."""

    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self.rows = rows
        self.sql: list[str] = []
        self.digests: set[str] = set()
        self.transactions = 0

    def transaction(self) -> contextlib.AbstractContextManager[None]:
        self.transactions += 1
        return contextlib.nullcontext()

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> _Result:
        self.sql.append(sql)
        if sql.startswith("SELECT c.subject_id"):
            return _Result(rows=self.rows)
        if sql.startswith("INSERT INTO resolution"):
            digest = params[-1]
            if digest in self.digests:
                return _Result(one=None)
            self.digests.add(digest)
            return _Result(one=("rid",))
        return _Result()


def _row(subject: str, pred: str, cid: str, num: float | None, text: str) -> tuple[Any, ...]:
    # SELECT column order of reconcile.materialize.read_claim_groups.
    return (
        subject, pred, cid, "value", text, num, None, text, None,  # observed_at NULL
        "R3", "I1", "active", "dot_511_ok", "camera_registry", datetime(2026, 9, 18, 3),
    )  # fmt: skip


def test_materializer_reads_capture_time_and_upserts_vocab_once() -> None:
    rows = [
        _row(
            f"traffic_camera:s:t:{i}",
            "camera_latitude",
            f"c{i}",
            35.0 + i / 100,
            f"{35.0 + i / 100}",
        )
        for i in range(5)
    ]
    conn = _FakeConn(rows)
    seen: list[tuple[int, int, int]] = []
    summary = materialize_resolutions(
        conn, as_of=AS_OF, progress=lambda *a: seen.append(a), progress_every=2, batch_size=2
    )
    assert summary.inserted == 5 and summary.resolved == 5 and summary.unresolved == 0
    assert CAPTURE_TIME_JOIN in conn.sql[0]
    # one (strategy, rationale, confidence) triple -> its three vocab upserts happen once.
    assert sum(s.startswith("INSERT INTO vocab_") for s in conn.sql) == 3
    assert seen and seen[0][:2] == (2, 5)
    assert conn.transactions == 3  # 5 envelopes in batches of 2 -> 3 commits
    # re-run over the same claims: +0 (idempotent on input_digest).
    again = materialize_resolutions(conn, as_of=AS_OF)
    assert again.inserted == 0 and again.skipped_existing == 5

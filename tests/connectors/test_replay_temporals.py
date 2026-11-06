# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Replay preserves source temporals; as_of_belief still returns the old
interpretation (SIG-INGEST-005).

Re-extraction MUST preserve ``observed_at`` and ``valid_*`` from the source
while minting a fresh ``recorded_at``/``sys_period`` — a parser improvement
produces *new claim rows*, never mutations of the old ones, so an
``as_of_belief`` read pinned before the re-extraction still answers the old
interpretation. The spine-side half is the Docker-gated ``claim_as_of`` suite
(``tests/db/test_as_of.py``); this file pins the framework half: the replay
machinery preserves the source temporals verbatim, and belief-pinning over
the append-only claim stream reproduces the earlier answer.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest
from connectors.replay import asserting_replay, replay
from connectors.stages import (
    CaptureRef,
    Connector,
    FetchResult,
    RunContext,
)

_VALID = {
    "valid_from": "2026-01-01",
    "valid_to": "2026-12-31",
    "valid_from_kind": "exact",
    "valid_to_kind": "exact",
    "valid_edtf": "2026-01-01/2026-12-31",
}
_TEMPORAL_KEYS = (
    "observed_at",
    "observed_at_kind",
    "valid_from",
    "valid_to",
    "valid_from_kind",
    "valid_to_kind",
    "valid_edtf",
)


class TemporalToy(Connector):
    """A connector whose claims carry source temporals (§9) — the replay
    surface SIG-INGEST-005 names."""

    name = "temporal-toy"
    version = "1"
    ingestion_mode = "html_scraping"
    incrementality = "normalized-content hashing on extracted structure"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        raise AssertionError("replay never fetches (SIG-INGEST-018)")

    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        return {
            "payload": json.loads(ctx.captures.get(capture.digest)),
            "retrieved_at": capture.retrieved_at,
        }

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        return [parsed["payload"] | {"retrieved_at": parsed["retrieved_at"]}]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        return [
            {
                "subject_id": str(r["id"]),
                "predicate_id": "camera_count",
                "raw_value": str(r["cameras"]),
                "value_num": int(r["cameras"]),
                # The source temporals — the capture's retrieval instant is the
                # observation (T2); the payload carries the validity window.
                "observed_at": str(r["retrieved_at"]),
                "observed_at_kind": "exact",
                **_VALID,
            }
            for r in raw_claims
        ]

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        # Re-extraction mints fresh belief time — `recorded_at = now()` — while
        # the source temporals pass through verbatim (SIG-INGEST-005).
        import uuid

        now = datetime.now(UTC).isoformat()
        return [
            {**c, "claim_id": str(uuid.uuid4()), "recorded_at": now, "sys_period": f"[{now},)"}
            for c in linked
        ]


class TemporalToyV2(TemporalToy):
    """The "improved parser" — same source temporals, a corrected value."""

    name = "temporal-toy-v2"
    version = "2"

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        rows = super().extract(ctx, parsed)
        return [dict(r, cameras=int(r["cameras"]) + 10) for r in rows]


def _archive(ctx, payload: dict) -> Any:
    return ctx.captures.put(
        json.dumps(payload, sort_keys=True).encode("utf-8"),
        media_type="application/json",
        source_uri="https://portal.example/p1",
        retrieved_at=datetime(2026, 6, 1, tzinfo=UTC),
    )


def test_replay_preserves_source_temporals_verbatim(make_context) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-005: re-extraction preserves `observed_at` and `valid_*`
    # from the source — the same capture replays identical temporals while
    # minting fresh belief columns.
    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 42})

    a = replay(TemporalToy(), ctx, [capture])
    b = replay(TemporalToy(), ctx, [capture])

    for key in _TEMPORAL_KEYS:
        assert a[0][key] == b[0][key], f"replay must preserve {key} verbatim"
    assert a[0]["observed_at"] == "2026-06-01 00:00:00+00:00"
    assert a[0]["claim_id"] != b[0]["claim_id"]
    assert a[0]["sys_period"] != b[0]["sys_period"]
    assert a[0]["recorded_at"] != b[0]["recorded_at"]


def test_reextraction_asserts_new_rows_never_mutates(make_context) -> None:  # type: ignore[no-untyped-def]
    # SIG-INGEST-005: an improved parser's re-extraction lands NEW claim rows
    # carrying the SAME source temporals; nothing edits the prior assertion.
    ctx = make_context()
    capture = _archive(ctx, {"id": "p1", "cameras": 42})

    asserting_replay(TemporalToy(), ctx, [capture])
    belief_between = datetime.now(UTC)
    asserting_replay(TemporalToyV2(), ctx, [capture])

    claims = list(ctx.claim_sink.claims)
    assert len(claims) == 2
    old, new = claims[0], claims[1]
    # The v2 value differs; the v1 row is untouched (append-only, P1–P3).
    assert old["value_num"] == 42
    assert new["value_num"] == 52
    # The source temporals carry over verbatim; only the belief columns move.
    for key in _TEMPORAL_KEYS:
        assert old[key] == new[key], f"re-extraction must preserve {key}"
    assert old["recorded_at"] != new["recorded_at"]

    # An as_of_belief read pinned before the re-extraction returns the old
    # interpretation — the belief filter the spine's claim_as_of applies
    # (SIG-TIME-008) over the assertion-time axis.
    def as_of_belief(belief: datetime) -> list[Mapping[str, Any]]:
        return [
            c
            for c in claims
            if c["sys_period"].removeprefix("[").split(",")[0] <= belief.isoformat()
        ]

    assert [c["value_num"] for c in as_of_belief(belief_between)] == [42]
    assert sorted(c["value_num"] for c in as_of_belief(datetime.now(UTC))) == [42, 52]


def test_temporal_qualifier_stays_in_obs_identity(make_context) -> None:  # type: ignore[no-untyped-def]
    # P35.22 (the obs/ref identity classes): for an `obs`-class predicate the
    # temporal qualifier is part of claim identity, so a preserved temporal
    # replays to an unchanged claim and a *changed* one registers — the rule
    # SIG-INGEST-005's as_of semantics rest on.
    from connectors.claim_identity_ingest import predicate_temporal_classes
    from connectors.replay import diff_claim_sets

    classes = predicate_temporal_classes()
    obs_predicates = {p for p, c in classes.items() if c == "obs"}
    assert obs_predicates, "the registry must declare obs-class predicates for this test"
    pid = sorted(obs_predicates)[0]

    base = {
        "subject_id": "p1",
        "predicate_id": pid,
        "value_num": 42,
        "observed_at": "2026-06-01",
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31",
    }
    same = dict(base, claim_id="other", sys_period="[later,)")
    drifted = dict(base, claim_id="other2", sys_period="[later,)", valid_to="2027-06-30")

    assert diff_claim_sets([base], [same], classes=classes).summary()["changed"] == 0
    assert diff_claim_sets([base], [drifted], classes=classes).summary()["changed"] == 2
    # A ref-class predicate drops the temporal qualifier from identity — the
    # registry class, never the record's shape, decides.
    ref = dict(base, predicate_id="camera_count")
    assert (
        diff_claim_sets(
            [ref], [drifted | {"predicate_id": "camera_count"}], classes=classes
        ).summary()["changed"]
        == 0
    )


@pytest.fixture
def temporal_connector() -> TemporalToy:
    return TemporalToy()

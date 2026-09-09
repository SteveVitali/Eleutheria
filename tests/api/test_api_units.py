# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the pure assembly + policy layers of the read API (P14.1).

These exercise the adapters directly (no HTTP), so a regression is localised: the
envelope adapter (SIG-API-002), the as-of cache decision (SIG-API-006), the
coordinate reduction (SIG-API-012), and the prohibition matcher (SIG-API-012).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from api.asof import AsOfContext
from api.dereference import select_media_type
from api.envelope import coverage_statement, resolution_envelope
from api.models import RESOLUTION_ENVELOPE_FIELDS
from api.prohibitions import check_path
from db.temporal import AsOf
from inference.coverage import CoverageRecord
from reconcile.resolve import RESOLVE, Claim


def _claim(cid: str, value: int, r: str, genre: str) -> Claim:
    return Claim(
        claim_id=cid,
        subject_id="S",
        predicate_id="active_device_count",
        value=value,
        reliability=r,
        integrity="I1",
        genre=genre,
        observed_at=date(2026, 7, 1),
        raw_value=str(value),
        source_id=f"src:{cid}",
        collection_method=genre,
    )


def test_resolution_envelope_maps_all_section_37_1_fields() -> None:
    resolved = RESOLVE(
        "S",
        "active_device_count",
        [_claim("portal", 38, "R2", "portal_snapshot")],
        as_of_world=date(2026, 9, 1),
        as_of_belief=date(2026, 9, 1),
    )
    env = resolution_envelope(resolved)
    dumped = env.model_dump()
    for field in RESOLUTION_ENVELOPE_FIELDS:
        assert field in dumped
    assert env.rationale.code and env.rationale.text
    assert env.value == 38


def test_asof_context_belief_pinned_iff_belief_supplied_explicitly() -> None:
    now = datetime(2026, 9, 1, 12, tzinfo=UTC)
    # Defaulted belief → now-pinned, not cacheable (resolves fresh every request).
    defaulted = AsOfContext.build(AsOf.resolve(None, None, now=now))
    assert defaulted.belief_pinned is False
    # Explicit belief → a fixed, reproducible cut → pinned/immutable, whether it is
    # a past instant or the current one.
    past = AsOfContext.build(AsOf.resolve(None, date(2026, 1, 1), now=now))
    assert past.belief_pinned is True
    at_now = AsOfContext.build(AsOf.resolve(None, now, now=now))
    assert at_now.belief_pinned is True


def test_coverage_statement_counts_evaluated_vs_not() -> None:
    records = [
        CoverageRecord(
            predicate_id="p1",
            absence_kind="searched_not_found",
            subject_id="S",
            sources_searched=("a",),
        ),
        CoverageRecord(predicate_id="p2", absence_kind="not_researched", subject_id="S"),
    ]
    cov = coverage_statement("S", records)
    assert cov.evaluated == 1
    assert cov.not_evaluable == 1
    assert cov.complete is False


def test_prohibition_matcher_flags_forbidden_and_passes_allowed() -> None:
    assert check_path("/v1/person/{name}") is not None
    assert check_path("/v1/device/liveness") is not None
    assert check_path("/v1/resolution/{s}/{p}") is None
    assert check_path("/v1/entity/{type}/{id}") is None


def test_media_type_selection() -> None:
    assert select_media_type("application/ld+json") == "application/ld+json"
    assert select_media_type("text/turtle") == "text/turtle"
    assert select_media_type("application/rdf+xml") == "text/turtle"
    assert select_media_type("text/html") == "text/html"
    assert select_media_type(None) == "text/html"
    assert select_media_type("*/*") == "text/html"

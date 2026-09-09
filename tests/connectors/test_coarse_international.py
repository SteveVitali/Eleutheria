# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Coarse international datasets (§22.7, §52, SIG-ENG-036/SIG-INGEST-042, P18.1).

Country- and vendor-level international datasets MUST be ingested at explicit
coarse granularity and MUST NEVER be disaggregated to agency level by inference.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.replay import shadow_replay
from connectors.runner import LiveGateRefused, RunMode, run_source
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun

from connectors import coarse_international as ci

_FIX = Path(__file__).parent / "fixtures" / "coarse_international"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


class _StaticTransport:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _flipped_ctx(source_id: str, fixture: str) -> tuple[RunContext, Any]:
    """A RunContext for a source the operator has FLIPPED (packet + review, P21.8).

    The registry row stays LINK / not_contacted / false (SIG-INGEST-028); this
    simulates the post-flip state the REFERENCE-capture path is designed for — a
    REFERENCE custody posture with a compact status that permits ingestion.
    """
    transport = _StaticTransport((_FIX / fixture).read_bytes())
    fetcher = PoliteFetcher(
        connector_name="coarse_international", connector_version="1.0.0", transport=transport
    )
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        custody_posture=CustodyPosture.REFERENCE,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    ctx = RunContext(
        source=source,
        run=IngestRun("coarse_international", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "t1", "url": f"https://{source_id}/x", "kind": "bulk"}]},
    )
    return ctx, transport


def _run_over(source_id: str, fixture: str) -> list[dict[str, Any]]:
    ctx, _ = _flipped_ctx(source_id, fixture)
    return run(ci.CoarseInternationalConnector(), ctx).claims


def test_all_three_named_datasets_are_registered_and_gated() -> None:
    # §22.7: the coarse datasets are registered LINK-posture and not yet permitted.
    for sid, dataset in ci.DATASETS.items():
        rec = get(sid)
        assert rec.custody_posture.value == "LINK"
        assert rec.ingestion_permitted is False
        assert dataset.granularity in ci.COARSE_GRANULARITIES


def test_country_and_vendor_granularities_are_declared() -> None:
    assert ci.DATASETS["carnegie_ai_gsi"].granularity == "country"
    assert ci.DATASETS["facial_recognition_world_map"].granularity == "country"
    assert ci.DATASETS["aspi_mapping_chinas_tech_giants"].granularity == "vendor"


def test_coarse_claim_stamps_explicit_granularity_and_preserves_raw_value() -> None:
    dataset = ci.DATASETS["carnegie_ai_gsi"]
    row = ci.coarse_claim(
        dataset,
        subject_kind="jurisdiction",
        subject_id="jurisdiction:iso.3166-1:CN",
        predicate="uses_ai_surveillance",
        value=True,
        raw_value="China — AI surveillance: yes",
        attribution="Carnegie Endowment",
    )
    assert row["granularity"] == "country"  # explicit, never inferred finer
    assert row["disaggregation_prohibited"] is True
    assert row["raw_value"] == "China — AI surveillance: yes"  # P2 preserved
    assert row["subject_kind"] == "jurisdiction"


def test_vendor_dataset_claims_a_vendor_subject() -> None:
    dataset = ci.DATASETS["aspi_mapping_chinas_tech_giants"]
    row = ci.coarse_claim(
        dataset,
        subject_kind="vendor",
        subject_id="sig:org:hikvision",
        predicate="operates_in_country",
        value="RS",
        raw_value="Hikvision — Serbia",
        attribution="ASPI",
    )
    assert row["granularity"] == "vendor"


@pytest.mark.parametrize("dataset_id", ["carnegie_ai_gsi", "aspi_mapping_chinas_tech_giants"])
@pytest.mark.parametrize("subject_kind", sorted(ci.DISAGGREGATED_SUBJECT_KINDS))
def test_agency_level_disaggregation_is_refused(dataset_id: str, subject_kind: str) -> None:
    # SIG-ENG-036 / SIG-INGEST-042: neither a country-level index NOR a vendor-level
    # dataset may be pinned to an agency (or deployment/device) by inference — that
    # manufactures precision (P4).
    dataset = ci.DATASETS[dataset_id]
    with pytest.raises(ci.DisaggregationError):
        ci.coarse_claim(
            dataset,
            subject_kind=subject_kind,
            subject_id="atlas:some-agency",
            predicate="uses_surveillance",
            value=True,
            raw_value="x",
            attribution="upstream",
        )


def test_country_dataset_rejects_a_vendor_subject_and_vice_versa() -> None:
    # The subject kind must match the dataset's own granularity.
    with pytest.raises(ci.DisaggregationError):
        ci.assert_not_disaggregated(ci.DATASETS["carnegie_ai_gsi"], "vendor")
    with pytest.raises(ci.DisaggregationError):
        ci.assert_not_disaggregated(ci.DATASETS["aspi_mapping_chinas_tech_giants"], "jurisdiction")


def test_a_non_coarse_granularity_is_rejected_at_construction() -> None:
    with pytest.raises(ci.CoarseGranularityError):
        ci.CoarseDataset(source_id="x", name="x", granularity="agency")


# --- the REFERENCE-capture path (P21.8) ---------------------------------------


def test_coarse_connector_is_registered() -> None:
    assert "coarse_international" in registered_connectors()
    assert registered_connectors()["coarse_international"] is ci.CoarseInternationalConnector


@pytest.mark.parametrize(
    "source_id,fixture,granularity",
    [
        ("carnegie_ai_gsi", "carnegie_ai_gsi.json", "country"),
        ("facial_recognition_world_map", "facial_recognition_world_map.json", "country"),
        ("aspi_mapping_chinas_tech_giants", "aspi_mapping_chinas_tech_giants.json", "vendor"),
    ],
)
def test_capture_path_runs_over_fixtures_at_coarse_granularity(
    source_id: str, fixture: str, granularity: str
) -> None:
    claims = _run_over(source_id, fixture)
    assert claims
    for c in claims:
        assert c["granularity"] == granularity
        assert c["disaggregation_prohibited"] is True
        assert c["subject_kind"] in ("jurisdiction", "vendor")
        assert c["raw_value"]  # P2 preserved verbatim


def test_all_three_coarse_sources_keep_link_posture_and_are_gated() -> None:
    # P21.8 keeps LINK posture: a live run is refused until a packet + flip.
    for sid in (
        "carnegie_ai_gsi",
        "facial_recognition_world_map",
        "aspi_mapping_chinas_tech_giants",
    ):
        rec = get(sid)
        assert rec.custody_posture.value == "LINK"
        assert rec.ingestion_permitted is False
        with pytest.raises(LiveGateRefused):
            run_source(sid, mode=RunMode.LIVE)


def test_shadow_replay_over_coarse_fixture_has_zero_diffs() -> None:
    # A flipped source re-run over its committed fixture is byte-identical => 0 diffs
    # (SIG-INGEST-019). Driven through the framework then diffed via shadow_replay.
    ctx, _ = _flipped_ctx("carnegie_ai_gsi", "carnegie_ai_gsi.json")
    connector = ci.CoarseInternationalConnector()
    report = run(connector, ctx)
    diff = shadow_replay(connector, ctx, report.captures, report.claims)
    assert diff.changed_count == 0

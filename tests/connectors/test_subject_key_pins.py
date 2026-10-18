# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Emitter-side contract for the pinned subject keys (P35.24 / ADR-212).

Covers the four key classes the ticket rewires: state-scoped Atlas/EFF agency
keys, tenant-scoped Legistar contract keys, the camera pin mint, and the
GQ-04 per-capture uniqueness enforcement that fails a target run closed.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

import pytest


class _MapTransport:
    """Per-URL canned responses + permissive robots — no real network."""

    def __init__(self, responses: Mapping[str, Any]) -> None:
        self._responses = dict(responses)

    def robots(self, robots_url: str) -> Any:
        from connectors.net import RobotsResult

        return RobotsResult(text="User-agent: *\nAllow: /\n")

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> Any:
        result = self._responses[url]
        return dataclasses.replace(result, url=url)


def _atlas_ctx() -> Any:
    from connectors.registry import get
    from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
    from evidence.ingest_run import IngestRun

    source = dataclasses.replace(get("eff_atlas_of_surveillance"), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun("eff_atlas_of_surveillance", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=None,  # type: ignore[arg-type]
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={},
    )


def test_atlas_emits_state_scoped_subject_keys() -> None:
    from connectors.atlas import AtlasConnector

    rows = AtlasConnector().normalize(
        _atlas_ctx(),
        [
            {
                "record_kind": "atlas_row",
                "agency": "Fresno PD",
                "category": "Automated License Plate Readers",
                "context": {"State": "CA"},
                "raw_evidence_component": "osint",
                "feed_records_component": True,
            }
        ],
    )
    claim_rows = [r for r in rows if r.get("record_kind") == "claim"]
    assert claim_rows
    assert all(r["subject_id"].startswith("atlas:us.state_abbr:CA:Fresno PD") for r in claim_rows)


def test_atlas_missing_state_mints_unscoped_sentinel() -> None:
    from connectors.atlas import AtlasConnector

    rows = AtlasConnector().normalize(
        _atlas_ctx(),
        [
            {
                "record_kind": "atlas_row",
                "agency": "Border Agency",
                "category": "Unknown Category Z",
                "context": {},
                "feed_records_component": False,
            }
        ],
    )
    # unmapped categories emit the unmapped_category record on the agency subject
    assert rows and rows[0]["record_kind"] == "unmapped_category"
    assert rows[0]["subject_id"] == "atlas:us.state_abbr:unscoped:Border Agency"


def test_data_driven_emits_state_scoped_agency_key() -> None:
    from connectors.data_driven import AgencyAggregate

    agg = AgencyAggregate(
        agency_id="TX0570000",
        agency_name="Houston PD",
        state="TX",
        vendor="flock",
        detections=None,
        hits=None,
        sharing_partner_degree=None,
        pooled_lookup_participant=False,
        retention={},
        records_request=None,
    )
    assert agg.subject_id == "data_driven:agency:us.state_abbr:TX:TX0570000"
    no_state = AgencyAggregate(
        agency_id="X",
        agency_name="X",
        state=None,
        vendor=None,
        detections=None,
        hits=None,
        sharing_partner_degree=None,
        pooled_lookup_participant=False,
        retention={},
        records_request=None,
    )
    assert no_state.subject_id == "data_driven:agency:us.state_abbr:unscoped:X"


def test_contract_mints_tenant_segment_for_platform_rows() -> None:
    from connectors.procurement import Contract

    c = Contract(external_id="C-241", source_id="legistar", raw={"tenant_id": "okc"})
    assert c.subject_id == "contract:legistar:tenant:okc:C-241"
    single = Contract(external_id="PO-1", source_id="usaspending")
    assert single.subject_id == "contract:usaspending:PO-1"


def test_duplicate_camera_key_in_one_capture_fails_closed() -> None:
    """GQ-04: two features minting one pinned key in a single capture abort
    the run — the defect that silently merged 5,278 subjects."""
    from connectors.dot_511 import Dot511Connector
    from connectors.live_targets import live_targets
    from connectors.net import PoliteFetcher
    from connectors.pipeline import run as run_connector
    from connectors.registry import get
    from connectors.stages import (
        FetchResult,
        InMemoryCaptureStore,
        InMemoryClaimSink,
        RunContext,
    )
    from db.subject_keys import SubjectKeyCollision
    from evidence.ingest_run import IngestRun

    connector = Dot511Connector()
    source = dataclasses.replace(get("dot_511_ky"), ingestion_permitted=True)
    targets = [t for t in live_targets("dot_511_ky") if t["id"] == "ky_kytc_traffic_cameras"]
    assert targets
    # A capture where TWO features carry the same camera id — the registry's
    # declared key is non-unique for this upstream.
    doc = {
        "features": [
            {
                "attributes": {"id": "KYTC-DUP", "latitude": 36.0, "longitude": -86.0},
                "geometry": {"x": -86.0, "y": 36.0},
            },
            {
                "attributes": {"id": "KYTC-DUP", "latitude": 38.0, "longitude": -85.0},
                "geometry": {"x": -85.0, "y": 38.0},
            },
        ]
    }
    responses = {
        t["url"]: FetchResult(
            url=t["url"],
            status=200,
            body=json.dumps(doc).encode(),
            media_type="application/json",
            retrieved_at=datetime(2026, 10, 18, tzinfo=UTC),
        )
        for t in targets
    }
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=_MapTransport(responses),
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    with pytest.raises(SubjectKeyCollision, match="KYTC-DUP"):
        run_connector(connector, ctx)


def test_seeded_slug_subjects_still_parse() -> None:
    """The committed seed subjects (live_targets.toml slug convention) stay
    valid legacy shapes — the sink never quarantines them."""
    from db.subject_keys import parse_subject_key

    for seed in (
        "contract:okc-flock-c241032",
        "contract:sandiego-ubicquia-ps",
        "agenda_item:haskell-ar-19-2025",
    ):
        parsed = parse_subject_key(seed)
        assert parsed is not None and parsed.key_version == 1, seed

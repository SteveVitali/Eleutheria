# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `osm` connector: tag vocabulary, keying, history, deletion, licence (§23.2, P04.2).

Every acceptance criterion of P04.2 is pinned here against committed fixtures
(SIG-PARSE-007): a real Overpass snapshot, a per-element history document, and a
second snapshot that drops an element (for deletion diffing). The connector is
driven end-to-end through the P04.1 framework and its pure helpers are tested
directly.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.loader import assert_export_compatible
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.osm import (
    DELETED_FROM_OSM_PREDICATE,
    ODBL_COMPARTMENT,
    ODBL_LICENSE,
    OSM_SOURCE_ID,
    REMOVED_FROM_STREET_PREDICATE,
    BulkStitchingForbidden,
    ElementRef,
    OSMConnector,
    acquisition_mode,
    assert_own_or_public_instance,
    build_overpass_query,
    canary_findings,
    first_observed_from_history,
    history_versions,
    is_surveillance_element,
    map_mobility,
    map_surveillance_type,
    overpass_status_action,
    physical_asset_rows,
    snapshot_diff,
    split_multivalue,
    strip_mapper_identity,
    vocab,
    vocab_version,
)
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from policy.licensing import LicenseIncompatibilityError
from policy.rights import RightsRecord

_FIX = Path(__file__).parent / "fixtures" / "osm"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"


def _fixture_bytes(name: str) -> bytes:
    return (_FIX / name).read_bytes()


def _fixture_json(name: str) -> dict[str, Any]:
    return json.loads((_FIX / name).read_text())


class _StaticTransport:
    """Serves one document's bytes for any URL — no real network (SIG-INGEST-011)."""

    def __init__(self, body: bytes) -> None:
        self._body = body
        self.user_agents: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str) -> FetchResult:
        self.user_agents.append(user_agent)
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _run_over(fixture: str, *, kind: str = "overpass") -> tuple[Any, list[dict[str, Any]]]:
    """Run the OSM connector end-to-end over a committed fixture; return (transport, claims)."""
    transport = _StaticTransport(_fixture_bytes(fixture))
    fetcher = PoliteFetcher(connector_name="osm", connector_version="1.0.0", transport=transport)
    # The seed row stays ingestion_permitted=false (SIG-INGEST-028); a reviewer
    # flips it to run, exactly as the eyes_on_flock framework tests do.
    source = dataclasses.replace(get(OSM_SOURCE_ID), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun("osm", "1.0.0", "deadbeef", "r1", vocab_version(), ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "t1", "url": "https://overpass-api.de/x", "kind": kind}]},
    )
    report = run(OSMConnector(), ctx)
    return transport, report.claims


# --- registration -------------------------------------------------------------


def test_osm_connector_is_registered() -> None:
    # SIG-INGEST-021: the connector self-registers on import under its name.
    assert "osm" in registered_connectors()
    assert registered_connectors()["osm"] is OSMConnector


# --- AC1: nodes/ways/relations, ';' split, four keys, id + version ------------


def test_handles_nodes_ways_relations_and_preserves_id_and_version() -> None:
    _, claims = _run_over("overpass_snapshot.json")
    assets = physical_asset_rows(claims)
    by_key = {(a["osm_element_type"], a["osm_element_id"]): a for a in assets}
    # All three element types are ingested (SIG-GEO-003: not just nodes).
    assert {t for t, _ in by_key} == {"node", "way", "relation"}
    # The non-surveillance café node is excluded by the selection predicate.
    assert ("node", 4004) not in by_key
    # Element id AND version are preserved (REQ-R1-01 / SIG-INGEST-045b).
    assert by_key[("node", 1001)]["osm_version"] == 5
    assert by_key[("way", 2002)]["osm_version"] == 2
    assert by_key[("relation", 3003)]["osm_version"] == 1


def test_subject_id_is_id_space_scoped() -> None:
    # SIG-INGEST-045f: (osm_type, osm_id), never osm_id alone.
    assert ElementRef("node", 1001).subject_id == "osm:node/1001"
    assert ElementRef("way", 1001).subject_id == "osm:way/1001"
    assert ElementRef("node", 1001).subject_id != ElementRef("way", 1001).subject_id


def test_semicolon_multivalue_is_split_as_an_unordered_set() -> None:
    # §23.2: split on ';' into an unordered set. split is dedup + strip + sorted.
    assert split_multivalue("ALPR;camera") == ("ALPR", "camera")
    assert split_multivalue("b ; a ; a ; ") == ("a", "b")
    _, claims = _run_over("overpass_snapshot.json")
    asset_type = _one(claims, osm_id=1001, predicate_id="asset_type")
    assert asset_type["value_set"] == ["ALPR", "camera"]
    assert set(asset_type["value_set_normalized"]) == {"alpr", "camera"}
    assert asset_type["raw_value"] == "ALPR;camera"  # P2: raw preserved


def test_all_four_surveillance_keys_are_normalized_and_mobility_inferred() -> None:
    _, claims = _run_over("overpass_snapshot.json")
    preds = {c["osm_key"]: c for c in claims if c.get("osm_id") == 1001 and "osm_key" in c}
    for key in ("surveillance:type", "surveillance", "surveillance:zone", "camera:type"):
        assert key in preds, f"expected a claim for {key}"
    # surveillance and surveillance:zone both normalize onto the zone predicate.
    assert preds["surveillance"]["predicate_id"] == "surveillance_zone"
    assert preds["surveillance:zone"]["predicate_id"] == "surveillance_zone"
    # camera:type=fixed drives mobility.
    asset = _one(physical_asset_rows(claims), osm_element_id=1001)
    assert asset["mobility"] == "fixed"
    assert asset["asset_technology"] == "alpr"


def test_mobility_and_type_maps() -> None:
    assert map_mobility("fixed") == "fixed"
    assert map_mobility("dome") == "fixed"
    assert map_mobility("drone") == "mobile"
    assert map_mobility("something_new") == "unknown"  # never guessed
    assert map_surveillance_type("ALPR") == "alpr"
    assert map_surveillance_type("gunshot_detector") == "acoustic_gunshot_detector"
    assert map_surveillance_type("AFR") == "automated_facial_recognition"
    assert map_surveillance_type("nonsense") is None


def test_non_camera_surveillance_types_are_in_scope() -> None:
    # R1-F1.3: gunshot_detector and AFR are Phase-4 in scope, not deferred.
    _, claims = _run_over("overpass_snapshot.json")
    way = _one(physical_asset_rows(claims), osm_element_id=2002)
    assert way["asset_technology"] == "acoustic_gunshot_detector"


# --- REQ-R1-02: an unallowlisted surveillance-bearing tag → unmapped + task ---


def test_unallowlisted_surveillance_key_becomes_unmapped_value_plus_task() -> None:
    _, claims = _run_over("overpass_snapshot.json")
    # `surveillance:brand_note` is surveillance-bearing but not in the allowlist.
    unmapped = _one(claims, osm_id=1001, predicate_id="unmapped_surveillance_tag")
    assert unmapped["osm_key"] == "surveillance:brand_note"
    assert unmapped["raw_value"] == "installed for the 2024 pilot"  # raw preserved
    assert unmapped["research_task"]["task_type"] == "unmapped_surveillance_tag"
    assert unmapped["research_task"]["subject_id"] == "osm:node/1001"


def test_unmapped_surveillance_type_value_records_a_task() -> None:
    # An allowlisted key with an unmapped VALUE still keeps the raw value and files
    # a research task (SIG-INGEST-045), rather than dropping the device kind.
    _, claims = _run_over("overpass_snapshot.json")
    rel = _one(claims, osm_id=3003, predicate_id="asset_type")
    assert rel["value_set"] == ["novel_sensor_kind"]
    assert rel["unmapped_values"] == ["novel_sensor_kind"]
    assert rel["research_task"]["task_type"] == "unmapped_surveillance_tag"


# --- AC2: first_observed from history, never the creation timestamp -----------


def test_first_observed_is_walked_from_history_not_creation() -> None:
    versions = history_versions(_fixture_json("element_history_node_1001.json"))
    fo = first_observed_from_history(versions)
    assert fo is not None
    # The node was imported as a freeway feature in 2009 and retagged surveillance
    # in 2024; first_observed is the 2024 retag (v5), NOT the 2009 creation.
    assert fo.version == 5
    assert fo.timestamp == datetime(2024, 12, 15, 10, 0, tzinfo=UTC)
    assert fo.timestamp.year != 2009


def test_first_observed_none_when_never_surveillance() -> None:
    doc = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "version": 1,
                "timestamp": "2009-01-01T00:00:00Z",
                "tags": {"highway": "motorway_junction"},
            },
            {
                "type": "node",
                "id": 1,
                "version": 2,
                "timestamp": "2010-01-01T00:00:00Z",
                "tags": {"highway": "motorway_junction"},
            },
        ]
    }
    assert first_observed_from_history(history_versions(doc)) is None


def test_first_observed_flows_through_the_pipeline() -> None:
    _, claims = _run_over("element_history_node_1001.json", kind="history")
    fo = _one(claims, osm_id=1001, predicate_id="first_observed")
    assert fo["value_time"] == datetime(2024, 12, 15, 10, 0, tzinfo=UTC)
    assert fo["osm_version"] == 5


def test_snapshot_asset_first_observed_is_never_the_creation_timestamp() -> None:
    # Without a history walk, first_observed stays unresolved (None) — the
    # connector never falls back to the element/creation timestamp (SIG-INGEST-045a).
    _, claims = _run_over("overpass_snapshot.json")
    for asset in physical_asset_rows(claims):
        assert asset["first_observed"] is None


# --- AC3: deletion via snapshot diffing; mapping event != street removal ------


def _survey_refs(fixture: str) -> list[ElementRef]:
    doc = _fixture_json(fixture)
    return [
        ElementRef(e["type"], e["id"])
        for e in doc["elements"]
        if is_surveillance_element(e.get("tags", {}))
    ]


def test_deletion_is_detected_by_snapshot_diff_as_a_mapping_event() -> None:
    diff = snapshot_diff(
        _survey_refs("overpass_snapshot.json"), _survey_refs("overpass_snapshot_next.json")
    )
    # The way vanished from OSM; a new node appeared.
    assert diff.deleted_from_osm == frozenset({ElementRef("way", 2002)})
    assert diff.added == frozenset({ElementRef("node", 5005)})
    events = diff.deletion_events(datetime(2026, 9, 20, tzinfo=UTC))
    assert len(events) == 1
    # A deletion from OSM is a MAPPING event, not a street removal (SIG-INGEST-045g).
    assert events[0]["predicate_id"] == DELETED_FROM_OSM_PREDICATE
    assert events[0]["event_class"] == "mapping_event"
    assert events[0]["predicate_id"] != REMOVED_FROM_STREET_PREDICATE
    assert events[0]["subject_id"] == "osm:way/2002"


def test_snapshot_diff_does_not_treat_a_persisting_element_as_gone() -> None:
    diff = snapshot_diff(
        _survey_refs("overpass_snapshot.json"), _survey_refs("overpass_snapshot_next.json")
    )
    assert ElementRef("node", 1001) in diff.persisted
    assert ElementRef("node", 1001) not in diff.deleted_from_osm


# --- AC4: mapper identity discarded; changeset retained -----------------------


def test_strip_mapper_identity_drops_user_and_uid_keeps_changeset() -> None:
    element = {
        "type": "node",
        "id": 1,
        "version": 1,
        "user": "alice",
        "uid": 42,
        "changeset": 900,
        "tags": {},
    }
    clean = strip_mapper_identity(element)
    assert "user" not in clean and "uid" not in clean
    assert clean["changeset"] == 900


def test_no_output_row_ever_carries_user_or_uid() -> None:
    # SIG-INGEST-045e: a targeting surface MUST NOT be built — user/uid never stored.
    _, claims = _run_over("overpass_snapshot.json")
    for claim in claims:
        assert "user" not in claim
        assert "uid" not in claim
    for asset in physical_asset_rows(claims):
        assert "user" not in asset and "uid" not in asset
        assert asset["changeset"] is not None  # changeset IS retained as provenance


# --- AC5: output lands in the ODbL table; export mixing with CC-BY fails ------


def test_every_output_row_is_stamped_into_the_odbl_compartment() -> None:
    _, claims = _run_over("overpass_snapshot.json")
    assert claims
    for claim in claims:
        assert claim["license"] == ODBL_LICENSE
        assert claim["compartment"] == ODBL_COMPARTMENT
        assert claim["source_id"] == OSM_SOURCE_ID
    for asset in physical_asset_rows(claims):
        assert asset["license"] == ODBL_LICENSE and asset["compartment"] == ODBL_COMPARTMENT


def test_export_mixing_osm_with_the_cc_by_graph_fails() -> None:
    # AC5 / SIG-LIC-006 / SIG-LIC-010: the OSM ODbL layer and the SIG CC-BY-4.0
    # graph are physically separate compartments and MUST NOT merge into one
    # export — the build fails on the mix (ODbL-1.0 relicensable only to itself).
    odbl = get(OSM_SOURCE_ID).rights  # ODbL-1.0
    sig_graph = RightsRecord(
        source_id="sig_graph",
        spdx="CC-BY-4.0",
        attribution="© The SIG project",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://creativecommons.org/licenses/by/4.0/",
        retrieval_date=datetime(2026, 8, 20, tzinfo=UTC).date(),
    )
    from policy.licensing import compute_export_license

    # The OSM layer alone exports cleanly under ODbL-1.0.
    assert compute_export_license([odbl]) == ODBL_LICENSE
    # Mixing it with the CC-BY graph raises — the licence violation is caught.
    with pytest.raises(LicenseIncompatibilityError):
        compute_export_license([odbl, sig_graph])


def test_osm_sources_share_one_compatible_compartment() -> None:
    # The connector-loader realisation: the OSM sources compute to a single licence.
    assert assert_export_compatible([OSM_SOURCE_ID, "osm_element_history"]) == ODBL_LICENSE


# --- AC6: committed fixtures + canary -----------------------------------------


def test_canary_passes_on_the_committed_fixture() -> None:
    # SIG-PARSE-008: no structural drift on a known-good response.
    assert canary_findings(_fixture_json("overpass_snapshot.json")) == []


def test_canary_flags_structural_drift() -> None:
    # An upstream that drops the version field (the reference key) is drift.
    drifted = {"elements": [{"type": "node", "id": 9, "tags": {"man_made": "surveillance"}}]}
    findings = canary_findings(drifted)
    assert any("version" in f for f in findings)
    # A response missing the elements list entirely is drift.
    assert canary_findings({"generator": "x"}) == ["missing top-level 'elements' list"]


# --- Overpass etiquette (SIG-INGEST-045d / 045h / 045i / 045j) ----------------


def test_overpass_query_respects_etiquette() -> None:
    q = build_overpass_query(bbox=(37.0, -122.5, 37.8, -122.0))
    assert "[timeout:180]" in q and "[maxsize:" in q  # SIG-INGEST-045h
    # No space inside a tag-value filter (SIG-INGEST-045d): a space trips the filter.
    filt = q[q.index('["man_made"') : q.index("]", q.index('["man_made"')) + 1]
    assert " " not in filt
    assert "node" in q and "way" in q and "relation" in q


def test_unbounded_query_is_refused_as_bulk_stitching() -> None:
    # SIG-INGEST-045i: stitching bounding boxes to scrape the world is prohibited.
    with pytest.raises(BulkStitchingForbidden):
        build_overpass_query(bbox=None)
    assert acquisition_mode(bulk=True) == "pbf_tag_filter"
    assert acquisition_mode(bulk=False) == "overpass_tiled"


def test_overpass_status_actions() -> None:
    # SIG-INGEST-045h: 429 => back off in time; 504 => shrink the query.
    assert overpass_status_action(429) == "back_off"
    assert overpass_status_action(504) == "shrink"
    assert overpass_status_action(200) == "ok"
    assert overpass_status_action(404) == "record_disappearance"


def test_only_public_or_permitted_overpass_instances_are_used() -> None:
    # SIG-INGEST-045j: never another project's self-hosted instance without permission.
    assert_own_or_public_instance("overpass-api.de")
    with pytest.raises(PermissionError):
        assert_own_or_public_instance("someones-private-overpass.example")
    assert_own_or_public_instance(
        "someones-private-overpass.example",
        permitted_self_hosted=["someones-private-overpass.example"],
    )


def test_fetch_carries_a_descriptive_user_agent() -> None:
    # SIG-INGEST-045d: a descriptive, contact-carrying UA (a browser spoof gets 406).
    transport, _ = _run_over("overpass_snapshot.json")
    assert transport.user_agents, "the connector fetched through the shared layer"
    ua = transport.user_agents[0]
    assert ua.startswith("osm/1.0.0") and "+" in ua


# --- vocabulary is versioned data ---------------------------------------------


def test_vocabulary_is_versioned() -> None:
    # §20 / SIG-INGEST-045: the tag→claim mapping is versioned data, not code.
    assert vocab_version() == vocab()["version"]
    assert vocab()["selection_key"] == "man_made"


# --- helpers ------------------------------------------------------------------


def _one(rows: list[dict[str, Any]], **match: Any) -> dict[str, Any]:
    """The single row matching all key=value constraints (fails loudly otherwise)."""
    found = [r for r in rows if all(r.get(k) == v for k, v in match.items())]
    assert len(found) == 1, f"expected exactly one row matching {match}, got {len(found)}"
    return found[0]

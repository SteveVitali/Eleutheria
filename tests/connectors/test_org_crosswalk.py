# SPDX-License-Identifier: Apache-2.0
"""P37.46a — the `org_crosswalk` connector: the four identity lanes over
committed fixtures (R11-CONF-13 13a; design CP-10; SIG-INGEST-033/034)."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.net import RobotsResult
from connectors.replay import replay, replay_fingerprint, shadow_replay
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

from connectors import org_crosswalk as oc

_FIX = Path(__file__).resolve().parent / "fixtures" / "org_crosswalk"
_RETRIEVED = datetime(2026, 11, 13, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

FIXTURE_FOR_SOURCE: dict[str, str] = {
    "wikidata_sparql": "wikidata_sparql.json",
    "census_of_governments": "census_of_governments.csv",
    "sam_gov_entities": "sam_gov_entities.json",
    "leaic_crosswalk": "leaic_crosswalk.csv",
}


class _Source:
    def __init__(self, source_id: str) -> None:
        self.id = source_id


class _Transport:
    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requested: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> FetchResult:
        self.requested.append(url)
        return FetchResult(
            url=url,
            status=200,
            body=self.body,
            media_type="application/json",
            retrieved_at=_RETRIEVED,
        )


def _run(source_id: str):
    from connectors.net import PoliteFetcher, RateLimiter

    body = (_FIX / FIXTURE_FOR_SOURCE[source_id]).read_bytes()
    ctx = RunContext(
        source=_Source(source_id),
        run=IngestRun("org_crosswalk", "1.0.0", "test", "r1", "v1", ()),
        fetcher=PoliteFetcher(
            connector_name="org_crosswalk",
            connector_version="1.0.0",
            transport=_Transport(body),
            rate_limiter=RateLimiter(sleep=lambda _s: None),
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"url": f"https://example.test/{source_id}"}]},
    )
    connector = oc.OrgCrosswalkConnector()
    targets = connector.discover(ctx)
    captures = []
    for t in targets:
        fr = connector.fetch(ctx, t)
        cap = ctx.captures.put(
            fr.body, source_uri=fr.url, media_type=fr.media_type, retrieved_at=fr.retrieved_at
        )
        captures.append(cap)
    claims: list[dict[str, Any]] = []
    for cap in captures:
        parsed = connector.parse(ctx, cap)
        raw = connector.extract(ctx, parsed)
        claims.extend(connector.normalize(ctx, raw))
    return connector, ctx, captures, claims


def _claims(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("record_kind") == "claim"]


def _candidates(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for r in rows:
        c = r.get("candidate_identifier")
        if c:
            out.add((c["scheme"], c["value"]))
    return out


def test_lane_for_source() -> None:
    assert oc.lane_for_source("wikidata_sparql") == "wikidata_qid"
    assert oc.lane_for_source("census_of_governments") == "census_geoid"
    assert oc.lane_for_source("sam_gov_entities") == "sam_uei"
    assert oc.lane_for_source("leaic_crosswalk") == "ori_fips"
    assert oc.lane_for_source("osm_overpass") is None


def test_allowlist_refuses_deployment() -> None:
    with pytest.raises(oc.PredicateNotAllowed):
        oc.assert_predicate_allowed("deployment_exists")
    for p in ("external_id", "organization_legal_name", "organization_ori"):
        assert oc.assert_predicate_allowed(p) == p


@pytest.mark.parametrize("source_id", sorted(FIXTURE_FOR_SOURCE))
def test_lane_fixture_replays(source_id: str) -> None:
    connector, ctx, captures, rows = _run(source_id)
    assert captures and _claims(rows)
    # determinism: shadow diff = 0
    replay_a = replay(connector, ctx, captures)
    replay_b = replay(connector, ctx, captures)
    assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)


@pytest.mark.parametrize("source_id", sorted(FIXTURE_FOR_SOURCE))
def test_shadow_diff_zero(source_id: str) -> None:
    connector, ctx, captures, rows = _run(source_id)
    diff = shadow_replay(connector, ctx, captures, rows)
    assert diff.changed_count == 0, diff.summary()


def test_wikidata_lane_candidates() -> None:
    _, _, _, rows = _run("wikidata_sparql")
    cands = _candidates(rows)
    assert ("wikidata.qid", "Q4915") in cands
    # the established crosswalk: the same entity's ORI statement
    assert ("us.fbi.ori", "OK0261100") in cands


def test_wikidata_person_shaped_name_suppressed() -> None:
    _, _, _, rows = _run("wikidata_sparql")
    suppressed = [r for r in _claims(rows) if r.get("part_viii_suppressed")]
    assert suppressed, "the sole-trader row's name is suppressed (Part VIII)"


def test_census_lane_geoid_candidates() -> None:
    _, _, _, rows = _run("census_of_governments")
    cands = _candidates(rows)
    assert ("us.census.geoid", "4046250000") in cands
    assert ("us.census.geoid", "4075300000") in cands


def test_sam_lane_uei_and_cage() -> None:
    _, _, _, rows = _run("sam_gov_entities")
    cands = _candidates(rows)
    assert ("us.sam.uei", "ZK12AB34CD56") in cands
    assert ("us.dla.cage", "1ABC2") in cands
    assert ("gleif.lei", "549300LJ9XAMPLE0001") in cands


def test_leaic_lane_ori_plus_geoid_established() -> None:
    _, _, _, rows = _run("leaic_crosswalk")
    cands = _candidates(rows)
    assert ("us.fbi.ori", "OK0261100") in cands
    assert ("us.census.geoid", "4046250000") in cands
    # both ids asserted on the SAME subject — the established crosswalk
    subjects = {
        r["subject_id"]
        for r in _claims(rows)
        if r.get("candidate_identifier", {}).get("scheme") == "us.census.geoid"
    }
    assert subjects == {
        "org_crosswalk_entry:ori_fips:OK0261100",
        "org_crosswalk_entry:ori_fips:OK7230100",
    }


def test_subjects_are_org_scoped() -> None:
    _, _, _, rows = _run("wikidata_sparql")
    for r in rows:
        assert r["subject_id"].startswith("org_crosswalk_entry:wikidata_qid:")


def test_missing_key_is_content_drift() -> None:
    from connectors.stages import ContentDrift

    body = json.dumps({"entities": [{"legal_business_name": "No Id Inc"}]}).encode()
    ctx = RunContext(
        source=_Source("sam_gov_entities"),
        run=IngestRun("org_crosswalk", "1.0.0", "test", "r1", "v1", ()),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )
    cap = ctx.captures.put(body, source_uri="https://example.test/x", media_type="application/json")
    connector = oc.OrgCrosswalkConnector()
    parsed = connector.parse(ctx, cap)
    raw = connector.extract(ctx, parsed)
    with pytest.raises(ContentDrift):
        connector.normalize(ctx, raw)


def test_load_l1_stamps_ids() -> None:
    _, ctx, _, rows = _run("census_of_governments")
    l1 = oc.load_claims_for_l1(rows)
    for r in l1:
        if r["record_kind"] in ("claim", "org_crosswalk_entry"):
            assert r["claim_id"] and r["sys_period"].startswith("[")


def test_unflipped_sources_stay_refused() -> None:
    """The two new registry rows keep ingestion_permitted=false (HG-03 is the
    operator's act, OP-26) — the loader gate refuses their live run."""
    from connectors.registry import get

    for sid in ("census_of_governments", "sam_gov_entities"):
        src = get(sid)
        assert src.ingestion_permitted is False
    # the permitted lanes ride flipped rows
    assert get("wikidata_sparql").ingestion_permitted is True
    assert get("fbi_cde_agency_registry").ingestion_permitted is True

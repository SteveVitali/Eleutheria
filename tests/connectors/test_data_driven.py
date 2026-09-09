# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `data_driven` connector: EFF/MuckRock Data Driven releases (§23.9, P21.8).

Every acceptance criterion of P21.8's connector is pinned here against committed
fixtures (SIG-PARSE-007): two release snapshots (v1, v2) prove versioning; a
release with a per-search column proves the aggregate-only schema rejection; a
seeded SIG identity proves the P03.2 crosswalk; and the live gate proves a live
fetch is refused (exit 3) while the source is un-flipped.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.cli import main
from connectors.data_driven import (
    DATA_DRIVEN_SOURCE_ID,
    ORI_SCHEME,
    AgencyAggregate,
    DataDrivenConnector,
    InvalidRelease,
    PerSearchColumnError,
    PredicateNotAllowed,
    ReleaseManifest,
    agency_identity,
    assert_aggregate_only,
    assert_predicate_allowed,
    predicate_allowlist,
    records_request_link,
    vocab_version,
)
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.records import RecordsRequest
from connectors.registry import get
from connectors.replay import diff_claim_sets
from connectors.runner import LiveGateRefused, RunMode, run_source
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun, canonical_claim_tuple

_FIX = Path(__file__).parent / "fixtures" / "data_driven"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"

# A known SIG identity carrying Austin PD's ORI — the crosswalk should resolve the
# fixture's Austin aggregate to it at tier 0 (exact shared canonical identifier).
_KNOWN_IDENTITIES = [
    {
        "entity_id": "sig:org:austin-pd",
        "organization_class": "law_enforcement_agency",
        "name": "Austin Police Department",
        "state": "TX",
        "identifiers": [{"scheme": ORI_SCHEME, "value": "TX0570000"}],
    }
]


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


def _run_over(
    fixture: str, *, sig_identities: list[dict[str, Any]] | None = None
) -> list[dict[str, Any]]:
    transport = _StaticTransport((_FIX / fixture).read_bytes())
    fetcher = PoliteFetcher(
        connector_name="data_driven", connector_version="1.0.0", transport=transport
    )
    source = dataclasses.replace(get(DATA_DRIVEN_SOURCE_ID), ingestion_permitted=True)
    params: dict[str, Any] = {
        "targets": [{"id": "t1", "url": "https://eff.example/data_driven", "kind": "bulk_file"}]
    }
    if sig_identities is not None:
        params["sig_identities"] = sig_identities
    ctx = RunContext(
        source=source,
        run=IngestRun("data_driven", "1.0.0", "deadbeef", "r1", vocab_version(), ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters=params,
    )
    return run(DataDrivenConnector(), ctx).claims


def _claims(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [r for r in rows if r.get("record_kind") == "claim"]


# --- registration -------------------------------------------------------------


def test_data_driven_connector_is_registered() -> None:
    assert "data_driven" in registered_connectors()
    assert registered_connectors()["data_driven"] is DataDrivenConnector


def test_list_connectors_cli_includes_data_driven(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["list-connectors"]) == 0
    out = capsys.readouterr().out
    assert "data_driven" in out
    assert "coarse_international" in out


# --- per-agency aggregate ONLY, historical (SIG-INGEST-043/043a) --------------


def test_writes_per_agency_aggregate_claims_only() -> None:
    claims = _claims(_run_over("release_v1.json"))
    assert claims
    for c in claims:
        assert c["granularity"] == "agency_aggregate"
        assert c["subject_kind"] == "agency"
        assert c["temporal_class"] == "historical"  # never a current-state claim
        assert c["observed_at"]  # SIG-INGEST-043/044: dated, decays
        assert c["predicate_id"] in predicate_allowlist()


def test_non_hit_proportion_is_the_key_structural_number() -> None:
    claims = _claims(_run_over("release_v1.json"))
    cbp = [
        c
        for c in claims
        if c["predicate_id"] == "non_hit_proportion_observed"
        and c["subject_id"].endswith("federal-cbp")
    ]
    assert len(cbp) == 1
    # 2,441,566,055 detections vs 10,936,164 hits => ~99.552% non-hit (SIG-INGEST-043a).
    assert cbp[0]["value"] == pytest.approx(0.99552, abs=1e-5)


def test_sharing_is_degree_only_never_an_edge_list() -> None:
    # SIG-INGEST-043c: degree supports "shared with 851 others"; never the edges.
    claims = _claims(_run_over("release_v1.json"))
    degree = [c for c in claims if c["predicate_id"] == "sharing_partner_degree"]
    assert degree
    for c in degree:
        assert c["degree_only_no_edge_list"] is True
        assert "sharing_partners" not in c and "edge_list" not in c
    austin = next(c for c in degree if c["subject_id"].endswith("TX0570000"))
    assert austin["value"] == 851


def test_retention_window_preserved_per_column_never_normalized() -> None:
    # SIG-INGEST-043d: incommensurable units preserved per column, not merged.
    claims = _claims(_run_over("release_v1.json"))
    retention = [c for c in claims if c["predicate_id"] == "retention_window_observed"]
    units = {c["retention_unit"] for c in retention}
    assert units == {"days", "months"}  # incommensurable, kept distinct
    for c in retention:
        assert c["incommensurable_units_preserved"] is True
        assert c["retention_window_definition"]  # the per-column window definition


# --- release versioning: new dated claims, never overwrite (SIG-INGEST-043d/017)


def test_versioned_reingest_appends_new_dated_claims_and_overwrites_nothing() -> None:
    v1 = _claims(_run_over("release_v1.json"))
    v2 = _claims(_run_over("release_v2.json"))
    v1_keys = {canonical_claim_tuple(c) for c in v1}
    v2_keys = {canonical_claim_tuple(c) for c in v2}
    # No v2 claim collides with a v1 claim => appending v2 overwrites nothing.
    assert v1_keys.isdisjoint(v2_keys)
    # v1 rows are retained: a store holding v1 ∪ v2 keeps every v1 claim.
    combined = v1_keys | v2_keys
    assert v1_keys <= combined
    assert len(combined) == len(v1_keys) + len(v2_keys)
    # And a shadow diff (current=v1, new=v2) shows all-added, zero-removed-as-overwrite
    diff = diff_claim_sets(v1, v2)
    assert len(diff.added) == len(v2)
    assert diff.unchanged == []


def test_the_release_version_is_what_separates_the_two_dated_claim_sets() -> None:
    # Strip the per-release provenance and the two releases' claims collide — proof
    # the version+digest+date is exactly what makes a re-ingest a NEW dated claim.
    def stripped(c: dict[str, Any]) -> tuple[Any, ...]:
        drop = {
            "release_version",
            "release_digest",
            "retrieved_date",
            "observed_at",
            "claim_id",
            "sys_period",
        }
        return tuple(sorted((k, str(v)) for k, v in c.items() if k not in drop))

    v1 = _claims(_run_over("release_v1.json"))
    v2 = _claims(_run_over("release_v2.json"))
    # sharing degree changed 851->863 so that row differs on value; but the two
    # deployment_exists rows are identical once the release stamp is removed.
    v1_dep = {stripped(c) for c in v1 if c["predicate_id"] == "deployment_exists"}
    v2_dep = {stripped(c) for c in v2 if c["predicate_id"] == "deployment_exists"}
    assert v1_dep == v2_dep  # identical modulo the release stamp => version separates them


# --- aggregate-only schema rejection (SIG-INGEST-043, RISK-P21-15) ------------


def test_per_search_column_release_is_refused() -> None:
    with pytest.raises(PerSearchColumnError):
        _run_over("release_with_per_search_column.json")


def test_assert_aggregate_only_rejects_forbidden_tokens() -> None:
    for bad in (
        "individual_searches",
        "per_search_count",
        "sharing_edge_list",
        "officer_name",
        "plate_reads",
        "partner_list",
    ):
        with pytest.raises(PerSearchColumnError):
            assert_aggregate_only(["agency_id", "detections", bad])
    # a clean aggregate schema passes
    assert_aggregate_only(["agency_id", "detections", "hits", "sharing_partner_degree"])


def test_predicate_allowlist_is_a_hard_gate() -> None:
    assert assert_predicate_allowed("deployment_exists") == "deployment_exists"
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("per_search_row")
    with pytest.raises(PredicateNotAllowed):
        assert_predicate_allowed("sharing_edge")


# --- agency crosswalk through the P03.2 cascade (SIG-INGEST-043c/§14.6) --------


def test_crosswalk_resolves_at_least_one_agency_to_a_sig_identity() -> None:
    claims = _claims(_run_over("release_v1.json", sig_identities=_KNOWN_IDENTITIES))
    austin = [c for c in claims if c["subject_id"].endswith("TX0570000")]
    assert austin
    for c in austin:
        assert c["resolved_entity_id"] == "sig:org:austin-pd"
        assert c["match_tier"] == 0  # exact shared canonical identifier (ORI)
        assert c["tier_label"] == "0"
        assert c["match_evidence"]["rule"] == "exact_shared_canonical_identifier"
    # CBP has no known identity => unresolved (no crosswalk stamp), never guessed.
    cbp = [c for c in claims if c["subject_id"].endswith("federal-cbp")]
    assert all("resolved_entity_id" not in c for c in cbp)


def test_without_known_identities_link_is_identity() -> None:
    claims = _claims(_run_over("release_v1.json"))
    assert all("resolved_entity_id" not in c for c in claims)


def test_ori_shaped_agency_routes_canonical_else_surrogate() -> None:
    assert agency_identity("TX0570000").route == "canonical"
    assert agency_identity("Austin Police Department").route == "surrogate"


# --- records-request linkage (SIG-INGEST-044) ---------------------------------


def test_records_request_linkage_points_at_the_request_entity() -> None:
    rows = _run_over("release_v1.json")
    links = [r for r in rows if r.get("record_kind") == "records_request_link"]
    assert len(links) == 2
    austin = next(link for link in links if link["subject_id"].endswith("TX0570000"))
    expected = RecordsRequest(
        external_id="foia-2018-austin-alpr",
        platform="muckrock",
        source_id=DATA_DRIVEN_SOURCE_ID,
    ).subject_id
    assert austin["records_request_subject"] == expected
    assert austin["records_request_platform"] == "muckrock"


def test_records_request_link_helper_is_faithful() -> None:
    link = records_request_link(
        "data_driven:agency:x",
        {"platform": "muckrock", "external_id": "foia-1", "target_agency": "X PD"},
    )
    assert link["records_request_external_id"] == "foia-1"
    assert link["target_agency"] == "X PD"


# --- release manifest provenance (SIG-INGEST-043b) ----------------------------


def test_release_manifest_requires_file_artifacts_not_the_article() -> None:
    with pytest.raises(InvalidRelease):
        ReleaseManifest(
            release_id="x",
            version="2018.11",
            retrieved_date="2026-08-20",
            observed_at="2018-11",
            data_file_urls=(),
            article_url="https://eff.example/article",
        )


def test_release_digest_changes_between_versions() -> None:
    m1 = ReleaseManifest(
        release_id="x",
        version="2018.11",
        retrieved_date="2026-08-20",
        observed_at="2018-11",
        data_file_urls=("https://f/1.csv",),
    )
    m2 = ReleaseManifest(
        release_id="x",
        version="2019.05",
        retrieved_date="2026-08-21",
        observed_at="2019-05",
        data_file_urls=("https://f/2.csv",),
    )
    assert m1.digest != m2.digest


def test_aggregate_non_hit_none_when_no_detections() -> None:
    agg = AgencyAggregate(
        agency_id="x",
        agency_name="X",
        state=None,
        vendor=None,
        detections=0,
        hits=5,
        sharing_partner_degree=None,
        pooled_lookup_participant=False,
        retention=None,
        records_request=None,
    )
    assert agg.non_hit_proportion is None


# --- run modes: live REFUSES (exit 3); shadow 0 diffs; replay reproducible -----


def test_live_run_is_refused_while_source_is_unflipped() -> None:
    with pytest.raises(LiveGateRefused) as exc:
        run_source(DATA_DRIVEN_SOURCE_ID, mode=RunMode.LIVE)
    assert any("ingestion_permitted" in r for r in exc.value.reasons)


def test_cli_live_run_exits_3(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["run", "--source", DATA_DRIVEN_SOURCE_ID, "--mode", "live"])
    assert rc == 3
    out = capsys.readouterr().out
    assert "REFUSED" in out


def test_shadow_over_fixture_has_zero_diffs() -> None:
    report = run_source(
        DATA_DRIVEN_SOURCE_ID,
        mode=RunMode.SHADOW,
        fixture=_FIX / "release_v1.json",
        media_type="application/json",
        kind="bulk_file",
    )
    assert report.diff is not None
    assert report.diff.changed_count == 0


def test_replay_is_reproducible() -> None:
    report = run_source(
        DATA_DRIVEN_SOURCE_ID,
        mode=RunMode.REPLAY,
        fixture=_FIX / "release_v1.json",
        media_type="application/json",
        kind="bulk_file",
    )
    assert report.replay_reproducible is True

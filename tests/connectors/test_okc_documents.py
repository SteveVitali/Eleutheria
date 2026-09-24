# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The three OKC document connectors (LIVE.1a, GL-LIVE-01, P23.5).

Pins the deliverables: `okc_procurement` / `okcpd_policy` / `ok_statute` are registered
and wired to their green registry sources (RIGHTS.1 / HG-03); each fetches → captures →
parses via sig-parsing → emits the fixture-encoded claims, and a shadow replay over the
committed fixture is byte-identical (0 diffs, SIG-INGEST-019). Part VIII §0.7 is honored
on every parsed claim: no plate/trip/per-person data (`assert_part_viii_safe`), the
officer-naming gate (`assert_person_naming_permitted`), and the sensitivity tier travel
with the claim — each guarded by a test that fails if the guard is removed.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.replay import shadow_replay
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, is_review_status_green, run_source
from connectors.stages import (
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    registered_connectors,
)
from evidence.ingest_run import IngestRun
from parsing.genre import DocumentGenre
from policy.officer import OfficerNamingProngs, ReviewerConcurrence
from policy.publication import excluded_kinds

from connectors import okc_documents as okc

_FIX = Path(__file__).parent / "fixtures" / "okc"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"

# The three connectors, keyed by name = registry source id (they coincide here).
_CONNECTORS = ("okc_procurement", "okcpd_policy", "ok_statute")


class _StaticTransport:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(self, url: str, *, user_agent: str, headers: Any | None = None) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _ctx(name: str) -> RunContext:
    transport = _StaticTransport((_FIX / f"{name}.json").read_bytes())
    fetcher = PoliteFetcher(connector_name=name, connector_version="1.0.0", transport=transport)
    source = dataclasses.replace(get(name), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=IngestRun(name, "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "t1", "url": f"https://{name}/x", "kind": "doc"}]},
    )


def _run(name: str) -> list[dict[str, Any]]:
    connector = registered_connectors()[name]()
    return run(connector, _ctx(name)).claims


# --- registration + wiring ----------------------------------------------------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_connector_is_registered(name: str) -> None:
    assert name in registered_connectors()


@pytest.mark.parametrize("name", _CONNECTORS)
def test_source_is_wired_to_its_connector(name: str) -> None:
    assert CONNECTOR_FOR_SOURCE[name] == name


@pytest.mark.parametrize("name", _CONNECTORS)
def test_source_is_green_hg03_satisfied(name: str) -> None:
    # RIGHTS.1 (P21.1 re-run, GL-GATE-03) flipped these three to ingestion_permitted;
    # a live fetch is now permitted (the fetch itself is P21.3 + HG-09, deferred).
    assert is_review_status_green(name), f"{name} must be green for the LIVE.1a code half"


# --- claims are typed, evidenced, and match the fixture-encoded facts ---------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_emits_typed_evidenced_claims(name: str) -> None:
    claims = _run(name)
    assert claims
    allowlist = okc.predicate_allowlist(name)
    for c in claims:
        assert c["predicate_id"] in allowlist  # typed + allowlisted (SIG-INGEST-033)
        assert c["raw_value"] is not None  # P2 preserved
        assert c["connector"] == name
        ev = c["evidence"]
        assert ev["source_url"] and ev["retrieved_date"]  # evidenced + dated
        assert ev["locator"] and ev["extraction_method"]  # locator mandatory (SIG-PARSE-003)


def test_parser_layers_are_exercised() -> None:
    methods = {c["evidence"]["extraction_method"] for n in _CONNECTORS for c in _run(n)}
    assert "pdf_table" in methods  # layer-4 table extraction (parsing.tables) — procurement
    assert "pdf_text" in methods  # layer-3 clause locator (parsing.clauses) — policy/statute


def test_procurement_emits_the_fixture_encoded_contract_facts() -> None:
    by_pred = {c["predicate_id"]: c for c in _run("okc_procurement")}
    assert by_pred["contract_number"]["value"] == "C241032"
    assert by_pred["contract_amount"]["value"] == 270000.0
    assert by_pred["contract_amount"]["raw_value"] == "$270,000"  # P2 verbatim
    assert by_pred["quantity"]["value"] == 90
    assert by_pred["vendor_name"]["value"] == "Flock Safety"


def test_policy_emits_the_fixture_encoded_sharing_restriction() -> None:
    values = {c["predicate_id"]: c["value"] for c in _run("okcpd_policy")}
    assert "law enforcement information database" in values["sharing_restriction"]


def test_statute_emits_the_fixture_encoded_citation_and_restriction() -> None:
    values = {c["predicate_id"]: c["value"] for c in _run("ok_statute")}
    assert "7-606.1" in values["statutory_citation"]
    assert values["use_restriction"] == "limited to insurance enforcement"


# --- shadow replay is byte-identical (0 diffs, SIG-INGEST-019) ----------------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_shadow_replay_over_fixture_has_zero_diffs(name: str) -> None:
    connector = registered_connectors()[name]()
    ctx = _ctx(name)
    report = run(connector, ctx)
    diff = shadow_replay(registered_connectors()[name](), ctx, report.captures, report.claims)
    assert diff.changed_count == 0


@pytest.mark.parametrize("name", _CONNECTORS)
def test_run_source_shadow_and_replay(name: str) -> None:
    fixture = _FIX / f"{name}.json"
    shadow = run_source(name, mode=RunMode.SHADOW, fixture=fixture, kind="doc")
    replay = run_source(name, mode=RunMode.REPLAY, fixture=fixture, kind="doc")
    assert shadow.diff is not None and shadow.diff.changed_count == 0
    assert replay.replay_reproducible is True


# --- Part VIII §0.7: no plate/trip/per-person data (test fails if removed) -----


@pytest.mark.parametrize(
    "bad",
    [
        "per_person_location",
        "license_plate_number",
        "per_trip_route",
        "travel_history",
        "per_search_hit",
    ],
)
def test_part_viii_guard_refuses_forbidden_predicate(bad: str) -> None:
    with pytest.raises(okc.PartVIIIViolation):
        okc.assert_part_viii_safe(bad, "some value")


def test_part_viii_guard_refuses_forbidden_raw_value() -> None:
    # The token can hide in the VALUE, not just the predicate name — scanned too.
    with pytest.raises(okc.PartVIIIViolation):
        okc.assert_part_viii_safe("use_restriction", "records the license plate of each vehicle")


def test_part_viii_guard_refuses_categorically_excluded_kind() -> None:
    # Any policy/data/exclusions.toml kind is refused at the ingest boundary (§43.2).
    for kind in excluded_kinds():
        with pytest.raises(okc.PartVIIIViolation):
            okc.assert_part_viii_safe(kind, "x")


def test_okc_claim_routes_through_the_part_viii_guard() -> None:
    # A claim whose raw value carries a plate token is refused by okc_claim itself —
    # if the guard call is removed from okc_claim, this test fails.
    ctx = okc.DocumentContext(
        connector="okcpd_policy",
        source_id="okcpd_policy",
        source_url="https://example/x",
        retrieved_date="2026-09-01",
        genre=DocumentGenre.POLICY_DOCUMENT,
        subject_id="sig:deployment:okc-okcpd-flock",
    )
    with pytest.raises(okc.PartVIIIViolation):
        okc.okc_claim(
            ctx,
            predicate="use_restriction",
            value="stores the license plate of every passing car",
            raw_value="stores the license plate of every passing car",
            extraction_method="pdf_text",
            locator={"kind": "byte_range", "start": 0, "end": 1},
        )


def test_no_emitted_claim_carries_a_forbidden_token() -> None:
    # End-to-end: the real fixtures emit institutional facts only.
    tokens = okc.forbidden_tokens()
    for name in _CONNECTORS:
        for c in _run(name):
            hay = f"{c['predicate_id']} {c['raw_value']}".lower()
            assert not any(t in hay for t in tokens)


# --- Part VIII §43.4: the officer-naming gate (test fails if removed) ---------


def test_person_naming_predicate_is_refused_by_default() -> None:
    # A person-named claim with no prongs + no reviewers defaults to no-publish.
    with pytest.raises(okc.OfficerNamingRefused):
        okc.assert_person_naming_permitted("officer_name")


def test_person_naming_permitted_only_with_all_prongs_and_two_reviewers() -> None:
    prongs = OfficerNamingProngs(True, True, True, True, True)
    reviewers = (
        ReviewerConcurrence("rev-a", True, "official conduct on the face of an R1 record"),
        ReviewerConcurrence("rev-b", True, "public in-jurisdiction; claim fails without the name"),
    )
    # All prongs + two independent written concurrences → the gate permits it.
    okc.assert_person_naming_permitted("officer_name", prongs=prongs, reviewers=reviewers)
    # One reviewer is not enough (SIG-PUB-008).
    with pytest.raises(okc.OfficerNamingRefused):
        okc.assert_person_naming_permitted("officer_name", prongs=prongs, reviewers=reviewers[:1])


def test_non_person_predicate_bypasses_the_officer_gate() -> None:
    # A non-person-naming predicate is unaffected by the officer test.
    okc.assert_person_naming_permitted("contract_amount")


# --- Part VIII §43.3: the sensitivity tier travels with the claim -------------


@pytest.mark.parametrize("name", _CONNECTORS)
def test_every_claim_carries_a_sensitivity_tier(name: str) -> None:
    # If the sensitivity stamp is removed from okc_claim, this test fails.
    for c in _run(name):
        assert c["sensitivity_class"] == okc.default_sensitivity_class().value
        assert c["geo_tier"] == 0  # C1 institutional/public-record facts, no coordinate


# --- the predicate allowlist as a hard schema gate (SIG-INGEST-033) -----------


def test_predicate_allowlist_is_enforced() -> None:
    with pytest.raises(okc.PredicateNotAllowed):
        okc.assert_predicate_allowed("okc_procurement", "deployed")


def test_each_connector_has_a_disjoint_source_and_allowlist() -> None:
    for name in _CONNECTORS:
        cfg = okc.connector_config(name)
        assert cfg["source_id"] == name
        assert okc.predicate_allowlist(name)


# --- genre is re-derived from the text, never trusted from a label ------------


def test_mislabelled_genre_is_rejected() -> None:
    doc = {
        "connector": "okc_procurement",
        "documents": [
            {
                "id": "mislabelled",
                "genre": "policy_document",  # a policy label on a procurement connector
                "kind": "procurement_table",
                "source_url": "https://example/x",
                "subject_id": "contract:x",
                "text": "Vendor | Amount\nFlock | $1",
                "columns": {"Vendor": {"predicate": "vendor_name"}},
            }
        ],
    }
    with pytest.raises(ValueError):
        okc.extract_documents("okc_procurement", doc)


# --- the fixtures cite their public sources -----------------------------------


def test_fixtures_have_a_sources_md() -> None:
    assert (_FIX / "SOURCES.md").exists()
    text = (_FIX / "SOURCES.md").read_text()
    for name in _CONNECTORS:
        assert f"{name}.json" in text

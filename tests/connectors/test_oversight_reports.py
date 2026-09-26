# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P31.12 targeted oversight-report path (BREADTH.1, §22.6 E).

The four P29.3 rights-flipped sources — ``gao_surveillance_reports``,
``dhs_oig_reports``, ``dhs_fusion_center_assessments`` and
``uk_surveillance_camera_commissioner`` — run through the existing
``accountability`` connector as targeted lookups of ONE reviewed published
document each (a landing page or the report PDF — never an index or listing,
SIG-INGEST-036/037). The reviewed ``live_targets.toml`` row carries the fields
the capture must prove (SIG-INGEST-038): the report's own ``external_id``, its
``title`` + verbatim ``literals`` (a missing one is ContentDrift — fail closed,
never a claim asserted beyond the capture), and the reviewed §11.17 event
fields the one-per-report AccountabilityEvent carries. ``event_organizations``
gains an entity-ref claim per name the Part VIII organisation rule accepts
(P31.5); a refused name stays the text claim it is.
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.accountability import CrawlAttempted
from connectors.live_targets import live_targets
from connectors.net import FetchResult, PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.replay import replay, replay_fingerprint
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, run_source
from connectors.stages import (
    ContentDrift,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun

from connectors import accountability as acc

_FIX = Path(__file__).parent / "fixtures" / "oversight_reports"
_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"
_RETRIEVED = datetime(2026, 9, 26, tzinfo=UTC)

#: The four P31.12 sources: registry id → (committed fixture, media type).
_SOURCES: dict[str, tuple[str, str]] = {
    "gao_surveillance_reports": ("gao-21-518.html", "text/html"),
    "dhs_oig_reports": ("oig-09-12.pdf", "application/pdf"),
    "dhs_fusion_center_assessments": ("fusion-assessment-2021.pdf", "application/pdf"),
    "uk_surveillance_camera_commissioner": ("bscc-ar-22-23.html", "text/html"),
}


def _targets(source_id: str) -> list[dict[str, Any]]:
    return live_targets(source_id)


def _target(source_id: str) -> dict[str, Any]:
    (row,) = _targets(source_id)
    return row


class _MappedTransport:
    """Serves per-URL fixture bytes — no real network (SIG-INGEST-011)."""

    def __init__(self, bodies: dict[str, tuple[bytes, str]]) -> None:
        self._bodies = bodies
        self.urls: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Any = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.urls.append(url)
        if url not in self._bodies:
            return FetchResult(url=url, status=404, body=b"", retrieved_at=_RETRIEVED)
        content, media_type = self._bodies[url]
        return FetchResult(
            url=url,
            status=200,
            body=content,
            media_type=media_type,
            retrieved_at=_RETRIEVED,
        )


def _ctx(
    source_id: str,
    transport: _MappedTransport | None = None,
    targets: list[dict[str, Any]] | None = None,
) -> RunContext:
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        custody_posture=CustodyPosture.REFERENCE,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    fetcher = PoliteFetcher(
        connector_name="accountability",
        connector_version=acc.AccountabilityConnector.version,
        transport=transport or _MappedTransport({}),
        rate_limiter=RateLimiter(default_delay=0.0),
    )
    return RunContext(
        source=source,
        run=IngestRun(
            "accountability", acc.AccountabilityConnector.version, "deadbeef", "r1", "v1", ()
        ),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets if targets is not None else _targets(source_id)},
    )


def _fixture_transport(source_id: str, mutate: bytes | None = None) -> _MappedTransport:
    name, media_type = _SOURCES[source_id]
    body = (_FIX / name).read_bytes() if mutate is None else mutate
    return _MappedTransport({str(_target(source_id)["url"]): (body, media_type)})


def _fixture_run(source_id: str, **ctx_kwargs: Any) -> Any:
    connector = acc.AccountabilityConnector()
    ctx = _ctx(source_id, _fixture_transport(source_id), **ctx_kwargs)
    return ctx, run(connector, ctx)


def _claims(report: Any) -> list[dict[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "claim"]


def _events(report: Any) -> list[dict[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "accountability_event"]


def _links(report: Any) -> list[dict[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "evidence_link"]


# --- the wiring ---------------------------------------------------------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_source_maps_to_the_accountability_connector(source_id: str) -> None:
    assert CONNECTOR_FOR_SOURCE[source_id] == "accountability"
    # The vocabulary names each source + the oversight-report config lists it.
    assert acc.source_ids()[source_id] == source_id
    assert source_id in acc.oversight_report_source_ids()
    assert acc.oversight_report_config()["kind"] == "oversight_report"
    assert acc.oversight_report_config()["source_class"] in acc.source_classes()


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_reviewed_live_target_row_carries_the_contract(source_id: str) -> None:
    row = _target(source_id)
    assert row["kind"] == "oversight_report"
    assert str(row["url"]).startswith("https://")
    assert row["external_id"]
    assert row["title"]
    assert row["literals"] and all(str(lit).strip() for lit in row["literals"])
    assert row["organizations"]
    assert row["epistemic_status"] in acc.epistemic_statuses()
    assert row["event_type"] in acc.event_types()
    assert acc.assert_oversight_report_target(row) is row


# --- fixture runs: one reviewed report → one §11.17 event ---------------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_fixture_run_lands_one_event_and_its_claims(source_id: str) -> None:
    ctx, report = _fixture_run(source_id)
    target = _target(source_id)

    # One accountability event, its §11.17 predicate claims, one evidence link.
    (event,) = _events(report)
    assert event["external_id"] == target["external_id"]
    assert event["epistemic_status"] == target["epistemic_status"]
    assert event["source_classes"] == [target["source_class"]]
    claims = _claims(report)
    by_pred = {c["predicate_id"]: c["value"] for c in claims if not c.get("object_ref")}
    assert by_pred["event_type"] == target["event_type"]
    assert by_pred["event_epistemic_status"] == target["epistemic_status"]
    assert by_pred["event_date"] == target["event_date"]
    assert by_pred["event_organizations"] == list(target["organizations"])
    # The event's stable locator is the reviewed document URL it rests on.
    (link,) = _links(report)
    assert link["value"] == target["url"]
    assert link["source_class"] == target["source_class"]
    # Every claim rides the event subject, all inside the predicate allowlist.
    subject = event["subject_id"]
    assert all(c["subject_id"] == subject for c in claims)
    assert all(acc.is_predicate_allowed(c["predicate_id"]) for c in report.claims)
    # An oversight finding is never a deployment/policy/device claim.
    forbidden = {"deployment_exists", "device_count", "policy", "contract_value"}
    assert not forbidden & {c["predicate_id"] for c in report.claims}


def test_gao_event_names_the_audited_agencies_with_entity_refs() -> None:
    _, report = _fixture_run("gao_surveillance_reports")
    refs = [c for c in report.claims if c.get("object_ref")]
    ref_orgs = {c["object_ref"]["value"] for c in refs}
    assert "u s government accountability office" in ref_orgs
    assert "federal bureau of investigation" in ref_orgs
    assert "drug enforcement administration" in ref_orgs
    # The list-valued text claim stays beside the per-name entity refs (P31.5).
    text = [
        c
        for c in _claims(report)
        if c["predicate_id"] == "event_organizations" and not c.get("object_ref")
    ]
    assert len(text) == 1 and isinstance(text[0]["value"], list)


def test_uk_commissioner_name_stays_a_text_claim_home_office_resolves() -> None:
    """A role-shaped office name ('… Commissioner') is refused — text only (Part VIII)."""
    _, report = _fixture_run("uk_surveillance_camera_commissioner")
    refs = {c["value"]: c["object_ref"] for c in report.claims if c.get("object_ref")}
    assert "Home Office" in refs
    # The refused name never gains an object_ref — it remains the verbatim text claim.
    assert "Biometrics and Surveillance Camera Commissioner" not in refs
    text = [
        c
        for c in _claims(report)
        if c["predicate_id"] == "event_organizations" and not c.get("object_ref")
    ]
    assert "Biometrics and Surveillance Camera Commissioner" in text[0]["value"]


def test_fusion_assessment_names_the_national_network() -> None:
    _, report = _fixture_run("dhs_fusion_center_assessments")
    refs = {c["object_ref"]["value"] for c in report.claims if c.get("object_ref")}
    assert "national network of fusion centers" in refs
    assert "u s department of homeland security" in refs


# --- fail closed: drift + unreviewed targets -----------------------------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_a_capture_missing_a_reviewed_literal_is_content_drift(source_id: str) -> None:
    """A page/PDF that lost a reviewed literal is not the reviewed document (§3.1)."""
    name, media_type = _SOURCES[source_id]
    body = (_FIX / name).read_bytes()
    if media_type == "application/pdf":
        # A different PDF: the cover literals are gone.
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent))
        from support import minimal_pdf

        body = minimal_pdf([["An unrelated document with none of the reviewed text"]])
    else:
        # Remove the first reviewed literal from the captured page bytes.
        first = str(_target(source_id)["literals"][0])
        assert first.encode() in body, "the committed fixture must carry the literal"
        body = body.replace(first.encode(), b"REDACTED-IN-DRIFT")
    ctx = _ctx(source_id, _MappedTransport({str(_target(source_id)["url"]): (body, media_type)}))
    connector = acc.AccountabilityConnector()
    with pytest.raises(ContentDrift):
        run(connector, ctx)


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_an_unreviewed_url_is_refused_at_discover(source_id: str) -> None:
    """A target that names no reviewed live-targets row fails closed (SIG-INGEST-038)."""
    bogus = {
        "id": "t-x",
        "url": "https://example.gov/not-a-reviewed-report",
        "kind": "oversight_report",
    }
    ctx = _ctx(source_id, targets=[bogus])
    connector = acc.AccountabilityConnector()
    with pytest.raises(acc.UnreviewedReportTarget):
        connector.discover(ctx)


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_an_unreviewed_url_never_reaches_fetch(source_id: str) -> None:
    """discover refuses an unreviewed row before any socket opens (SIG-INGEST-036)."""
    transport = _fixture_transport(source_id)
    bogus = {
        "id": "t-x",
        "url": "https://example.gov/not-a-reviewed-report",
        "kind": "oversight_report",
    }
    ctx = _ctx(source_id, transport, targets=[bogus])
    connector = acc.AccountabilityConnector()
    with pytest.raises(acc.UnreviewedReportTarget):
        run(connector, ctx)
    assert transport.urls == [], "an unreviewed target must never be fetched"


@pytest.mark.parametrize(
    "patch",
    [
        {"mode": "crawl"},
        {"mode": "enumerate"},
        {"page": 2},
        {"cursor": "abc"},
    ],
)
def test_a_crawl_or_pagination_shape_is_refused(patch: dict[str, Any]) -> None:
    """Oversight reports are targeted lookups — never a crawl/list (SIG-INGEST-036/037)."""
    row = dict(_target("gao_surveillance_reports"))
    row.update(patch)
    with pytest.raises(CrawlAttempted):
        acc.assert_oversight_report_target(row)


def test_a_row_missing_reviewed_fields_is_a_data_error() -> None:
    for bad_field in ("external_id", "title", "literals", "organizations", "epistemic_status"):
        row = dict(_target("gao_surveillance_reports"))
        row.pop(bad_field, None)
        with pytest.raises(acc.UnreviewedReportTarget):
            acc.assert_oversight_report_target(row)
    # An out-of-vocabulary status/type/class is refused, never coerced.
    for field, value in (
        ("epistemic_status", "possibly-true"),
        ("event_type", "deployment"),
        ("source_class", "blog_post"),
    ):
        row = dict(_target("dhs_oig_reports"))
        row[field] = value
        with pytest.raises(acc.UnreviewedReportTarget):
            acc.assert_oversight_report_target(row)


# --- replay/shadow parity ------------------------------------------------------


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_shadow_replay_over_the_fixture_has_zero_diffs(source_id: str) -> None:
    """Re-interpreting the committed capture is byte-identical (SIG-INGEST-019)."""
    name, media_type = _SOURCES[source_id]
    report = run_source(
        source_id,
        mode=RunMode.SHADOW,
        fixture=_FIX / name,
        media_type=media_type,
        kind="oversight_report",
    )
    assert report.diff is not None
    assert report.diff.changed_count == 0, f"shadow diff must be empty: {report.diff.summary()}"
    # The fixture-encoded claim set is what the report carries.
    assert _events(report) and _claims(report)


@pytest.mark.parametrize("source_id", sorted(_SOURCES))
def test_replay_is_byte_reproducible(source_id: str) -> None:
    """Two replays of the same capture yield identical claim fingerprints (SIG-INGEST-003)."""
    name, media_type = _SOURCES[source_id]
    report = run_source(
        source_id,
        mode=RunMode.REPLAY,
        fixture=_FIX / name,
        media_type=media_type,
        kind="oversight_report",
    )
    assert report.replay_reproducible


def test_replay_is_byte_reproducible_at_the_parse_level() -> None:
    """parse/extract/normalize are pure functions of the capture bytes."""
    ctx, report = _fixture_run("dhs_oig_reports")
    connector = acc.AccountabilityConnector()
    a = replay(connector, ctx, report.captures)
    b = replay(connector, ctx, report.captures)
    assert replay_fingerprint(a) == replay_fingerprint(b)

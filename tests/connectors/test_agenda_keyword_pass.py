# SPDX-License-Identifier: Apache-2.0
"""P35.8 (ACQ-04, I8 §4.1) — the Legistar keyword-filtered, paged matter pass.

The recency ``$top=100`` matter query now runs BESIDE a reviewed keyword pass:
one paged ``substringof`` OR-group target per reviewed group, paged until a
short page or the reviewed ``keyword_index_max_pages`` bound, carrying a
client-side word-boundary precision filter (the agenda-content vocabulary
regexes) that drops the broad-substring noise the server returns. A matter
seen by both passes is one claim through ``content_digest``; the per-tenant
document window never widens. Everything runs over committed fixtures — no
live Legistar fetch happens in this ticket.
"""

import dataclasses
import json
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import connectors.procurement as procurement
import pytest
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.procurement import (
    ProcurementConnector,
    agenda_tenants,
    source_ids,
    tenant_targets,
)
from connectors.registry import get
from connectors.replay import diff_claim_sets, replay, shadow_replay
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun, canonical_claim_tuple

FIXTURES = Path(__file__).parent / "fixtures" / "promoted"
REPO_ROOT = Path(__file__).resolve().parents[2]
_ALLOW_ALL = "User-agent: *\nAllow: /\n"


def _fixture(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="procurement",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


class _MapTransport:
    """URL-substring-keyed canned responses — no real network."""

    def __init__(self) -> None:
        self.responses: list[tuple[str, int, bytes, str]] = []
        self.requested: list[str] = []

    def add(self, needle: str, status: int, body: bytes, media: str) -> None:
        self.responses.append((needle, status, body, media))

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> FetchResult:
        self.requested.append(url)
        for needle, status, resp_body, media in self.responses:
            if needle in url:
                return FetchResult(
                    url=url,
                    status=status,
                    body=resp_body,
                    media_type=media,
                    retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
                )
        return FetchResult(
            url=url,
            status=404,
            body=b"",
            media_type="text/plain",
            retrieved_at=datetime(2026, 10, 10, tzinfo=UTC),
        )


# The pinned registry subset — real registry row shape (P35.7 key order kept).
_CABQ = {
    "albuquerque_nm": {
        "jurisdiction": "City of Albuquerque, NM",
        "platform": "legistar",
        "tenant": "cabq",
        "api_base": "https://webapi.legistar.com/v1/cabq",
    }
}
_THREE_TENANTS = {
    **_CABQ,
    "columbus_oh": {
        "jurisdiction": "City of Columbus, OH",
        "platform": "legistar",
        "tenant": "columbus",
        "api_base": "https://webapi.legistar.com/v1/columbus",
    },
    "newark": {
        "jurisdiction": "Newark, NJ",
        "platform": "legistar",
        "tenant": "newark",
        "api_base": "https://webapi.legistar.com/v1/newark",
    },
}


def _pin_registry(
    monkeypatch: pytest.MonkeyPatch,
    rows: dict[str, dict[str, Any]],
    *,
    page_size: int = 3,
    doc_per_tenant: int | None = None,
) -> None:
    """Pin the tenant registry to ``rows`` and the keyword page bound to
    ``page_size`` so the paging loop is exercisable over small fixtures — the
    bound stays data on the endpoint row, never a code constant."""
    monkeypatch.setattr(procurement, "agenda_tenants", lambda: dict(rows))
    endpoints = {k: dict(v) for k, v in procurement.platform_endpoints().items()}
    legistar = dict(endpoints["legistar"])
    legistar["keyword_index_page_size"] = page_size
    legistar["keyword_index_max_pages"] = 3
    if doc_per_tenant is not None:
        legistar["doc_per_tenant"] = doc_per_tenant
    endpoints["legistar"] = legistar
    monkeypatch.setattr(procurement, "platform_endpoints", lambda: endpoints)


def _run_legistar(transport: _MapTransport) -> tuple[Any, RunContext]:
    """A full pipeline run over the pinned legistar tenants (gate open)."""
    source = dataclasses.replace(get(source_ids()["legistar"]), ingestion_permitted=True)
    fetcher = PoliteFetcher(
        connector_name="procurement",
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    ctx = RunContext(
        source=source,
        run=_ingest_run(),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": []},
    )
    return run(ProcurementConnector(), ctx), ctx


def _cabq_transport() -> _MapTransport:
    transport = _MapTransport()
    # Page-1 needle first — it is a strict substring-superset of the page-0 one.
    transport.add(
        "$skip=3", 200, _fixture("legistar_cabq_matters_keyword_p1.json"), "application/json"
    )
    transport.add(
        "cabq/matters?$filter",
        200,
        _fixture("legistar_cabq_matters_keyword_p0.json"),
        "application/json",
    )
    transport.add(
        "cabq/matters?", 200, _fixture("legistar_cabq_matters_recency.json"), "application/json"
    )
    transport.add(
        "cabq/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    return transport


def _index_rows(report: Any) -> list[dict[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "agenda_index"]


def _slice_rows(report: Any) -> list[dict[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "agenda_index_slice"]


def _canonical(rows: list[dict[str, Any]]) -> set[Any]:
    return {canonical_claim_tuple(c) for c in rows}


# --- generated targets: the second slice rides the reviewed config (AC1/AC2) ---


def test_legistar_targets_emit_recency_plus_keyword_slices() -> None:
    """Every legistar tenant emits the unchanged recency target PLUS one paged
    keyword target per reviewed OR-group — the second index slice is target
    data, never a code path that skips discovery."""
    targets = tenant_targets("legistar")
    assert targets
    by_tenant: dict[str, list[dict[str, Any]]] = {}
    for t in targets:
        by_tenant.setdefault(str(t["tenant_id"]), []).append(t)
    for tenant_id, ts in by_tenant.items():
        recency = [t for t in ts if t.get("index_slice") is None]
        keyword = [t for t in ts if t.get("index_slice") == "keyword"]
        assert len(recency) == 1
        assert len(keyword) == len(
            procurement.platform_endpoints()["legistar"]["keyword_index_groups"]
        )
        r = recency[0]
        assert r["id"] == tenant_id
        assert "$top=100&$orderby=MatterLastModifiedUtc%20desc" in r["url"]
        assert "$filter" not in r["url"]
        for i, k in enumerate(keyword):
            assert k["id"] == f"{tenant_id}:kw{i}"
            assert "$filter=(substringof(" in k["url"]
            assert "%20or%20substringof(" in k["url"]
            assert "&$top=1000&$skip=0" in k["url"]
            assert k["paged"] is True
            assert k["page_size"] == 1000
            assert k["max_pages"] > 0
            assert len(k["url"]) < 1500, "the reviewed URL bound (I8 §4.1)"
            # the tenant's doc bounds + labels ride the keyword row unchanged
            assert k["doc_per_tenant"] == r["doc_per_tenant"] == 20
            assert k["doc_run_cap"] == r["doc_run_cap"] == 350
            assert k["jurisdiction"] == r["jurisdiction"]
        # target ids are unique — two passes never collide
        assert len({t["id"] for t in ts}) == len(ts)
        assert len({t["url"] for t in ts}) == len(ts)


def test_keyword_term_set_is_the_reviewed_round11_list() -> None:
    groups = procurement.platform_endpoints()["legistar"]["keyword_index_groups"]
    flat = {t for g in groups for t in g}
    assert len(groups) == 4
    assert {
        "license plate",
        "LPR",
        "Flock",
        "Vigilant",
        "Fusus",
        "real time crime",
        "real-time crime",
        "ShotSpotter",
        "SoundThinking",
        "gunshot",
        "drone",
        "unmanned aer",
        "facial recognition",
        "Clearview",
        "Cellebrite",
        "GrayKey",
        "Grayshift",
        "Magnet Forensics",
        "Dataminr",
        "Babel Street",
        "Gaggle",
        "GoGuardian",
        "Securly",
        "Lightspeed",
        "Verra",
        "red light camera",
        "speed camera",
        "speed safety",
        "automated enforcement",
        "automated traffic",
        "electronic monitoring",
        "body-worn",
        "body worn",
        "Axon",
        "BriefCam",
        "Genetec",
        "Rekor",
        "surveillance",
    } <= flat


def test_ousd_and_washoe_are_genuine_legistar_tenants_and_stay() -> None:
    """The design's disposition check: OUSD and Washoe ARE InSite tenants, so
    the widened pass reaches them — no false-tenant ACQ-22 move here."""
    rows = agenda_tenants()
    for key in ("ousd", "washoe_county_nv"):
        assert rows[key]["platform"] == "legistar"
        assert rows[key]["api_base"].startswith("https://webapi.legistar.com/v1/")


def test_corrected_labels_ride_the_widened_targets() -> None:
    """P35.7's six corrected jurisdiction labels land on the keyword targets —
    the widened pass never resurrects a false jurisdiction."""
    targets = {t["tenant_id"]: t for t in tenant_targets("legistar") if t["id"] == t["tenant_id"]}
    expected = {
        "charlotte_ia": "Charlotte, NC",
        "concord_ca": "Concord, NH",
        "san_bernardino_ca": "San Bernardino County, CA",
        "newark": "Newark, NJ",
        "clark": "Clark County, NV",
        "carrollton_ga": "Carrollton, TX",
    }
    for tenant_id, jurisdiction in expected.items():
        assert targets[tenant_id]["jurisdiction"] == jurisdiction, tenant_id
    kw = {t["tenant_id"]: t for t in tenant_targets("legistar") if t["id"].endswith(":kw0")}
    for tenant_id, jurisdiction in expected.items():
        assert kw[tenant_id]["jurisdiction"] == jurisdiction, tenant_id


def test_legistar_task_timeout_is_the_reviewed_3h() -> None:
    """The widened run fits the reviewed 3h task budget (I8 §4.1 ~1.3–1.6k
    requests) — the cadence row is data, asserted as reviewed config."""
    cadence = tomllib.loads((REPO_ROOT / "ops" / "cadence.toml").read_text())
    legistar = [r for r in cadence["sources"] if r.get("id") == "legistar"]
    assert legistar, "a sig-ingest-legistar cadence row"
    assert legistar[0].get("task_timeout") == "3h"


# --- the paged keyword pass ----------------------------------------------------


def test_keyword_slice_pages_until_a_short_page(monkeypatch: pytest.MonkeyPatch) -> None:
    """A full page fetches the next; a short page stops the loop — every page
    request went through the shared fetcher and landed on the capture's
    sig_paged provenance."""
    _pin_registry(monkeypatch, _CABQ)
    transport = _cabq_transport()
    report, _ctx = _run_legistar(transport)

    kw_p0 = [u for u in transport.requested if "$filter" in u and "$skip=0" in u]
    kw_p1 = [u for u in transport.requested if "$skip=3" in u]
    assert len(kw_p0) == 4  # one per reviewed OR-group
    assert len(kw_p1) == 4  # every group paged: the fixture p0 is a full page
    assert not [u for u in transport.requested if "$skip=6" in u], (
        "the short second page stops the loop — never page 3"
    )
    slices = _slice_rows(report)
    assert len(slices) == 4
    for row in slices:
        assert row["paged"]["truncated"] is False
        assert [p["skip"] for p in row["paged"]["pages"]] == [0, 3]
        assert row["items_count"] == 5
        assert row["dropped_count"] == 2  # pigeon-Flock + gunshot-victims noise


def test_max_pages_is_a_recorded_truncation(monkeypatch: pytest.MonkeyPatch) -> None:
    """Paging hits the reviewed bound and SAYS so — a truncated slice is
    first-class run record, never a silent stop."""
    _pin_registry(monkeypatch, _CABQ, page_size=3)
    transport = _MapTransport()
    # every page answers the full p0 fixture → the loop exhausts max_pages=3
    transport.add(
        "$filter", 200, _fixture("legistar_cabq_matters_keyword_p0.json"), "application/json"
    )
    transport.add(
        "cabq/matters?", 200, _fixture("legistar_cabq_matters_recency.json"), "application/json"
    )
    transport.add(
        "cabq/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    report, _ctx = _run_legistar(transport)
    slices = _slice_rows(report)
    assert slices and all(
        row["paged"]["truncated"] is True and len(row["paged"]["pages"]) == 3 for row in slices
    )


def test_first_page_error_envelope_stays_a_tenant_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unprovisioned tenant's InSite error envelope on page 0 is the slice's
    honest outcome — a tenant_api_error row, never a silent empty page."""
    _pin_registry(monkeypatch, _CABQ)
    transport = _MapTransport()
    envelope = json.dumps(
        {"Message": "An error has occurred.", "ExceptionMessage": "invalid client"}
    ).encode()
    transport.add("$filter", 200, envelope, "application/json")
    transport.add(
        "cabq/matters?", 200, _fixture("legistar_cabq_matters_recency.json"), "application/json"
    )
    transport.add(
        "cabq/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    report, _ctx = _run_legistar(transport)
    errors = [c for c in report.claims if c.get("record_kind") == "tenant_api_error"]
    assert len(errors) == 4  # one per keyword slice, each honestly recorded
    assert not _slice_rows(report)


def test_mid_slice_failure_truncates_with_the_fetched_pages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A page-1 500 keeps page 0's items and marks the slice truncated —
    partial evidence, never fabricated completeness."""
    _pin_registry(monkeypatch, _CABQ)
    transport = _MapTransport()
    transport.add("$skip=3", 500, b"boom", "text/plain")
    transport.add(
        "cabq/matters?$filter",
        200,
        _fixture("legistar_cabq_matters_keyword_p0.json"),
        "application/json",
    )
    transport.add(
        "cabq/matters?", 200, _fixture("legistar_cabq_matters_recency.json"), "application/json"
    )
    transport.add(
        "cabq/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    report, _ctx = _run_legistar(transport)
    slices = _slice_rows(report)
    assert slices and all(row["paged"]["truncated"] is True for row in slices)
    assert all(len(row["paged"]["pages"]) == 1 for row in slices)
    # page-0's precise items still landed
    ids = {r["external_id"] for r in _index_rows(report) if r["tenant_id"] == "albuquerque_nm"}
    assert {"C-25-088", "R-25-118"} <= ids


# --- precision: the client-side word-boundary pass -----------------------------


def test_keyword_precision_filter_drops_substring_noise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The broad ``substringof`` terms surface noise the reviewed vocabulary
    rejects — pigeon-Flock ('Flock'), gunshot-victims ('gunshot'), Saxon/
    workers-comp ('Axon' inside 'Saxon' — the I4-C218 class)."""
    _pin_registry(monkeypatch, _THREE_TENANTS)
    transport = _cabq_transport()
    transport.add(
        "columbus/matters?$filter",
        200,
        _fixture("legistar_columbus_matters_keyword.json"),
        "application/json",
    )
    transport.add(
        "newark/matters?$filter",
        200,
        _fixture("legistar_newark_matters_keyword.json"),
        "application/json",
    )
    transport.add("columbus/matters?", 404, b"", "text/plain")
    transport.add("newark/matters?", 404, b"", "text/plain")
    transport.add(
        "columbus/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    transport.add(
        "newark/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    report, _ctx = _run_legistar(transport)

    by_tenant: dict[str, set[str]] = {}
    for row in _index_rows(report):
        by_tenant.setdefault(str(row["tenant_id"]), set()).add(str(row["external_id"]))
    # the noise items never land as agenda_index rows
    assert "R-25-096" not in by_tenant["albuquerque_nm"]  # pigeon-Flock
    assert "R-25-131" not in by_tenant["albuquerque_nm"]  # gunshot victims
    assert "WC-24-1187" not in by_tenant["newark"]  # workers-comp / Saxon
    # the true positives did — ATE, EM, ALPR, RTCC, vendor terms all survived
    assert {"C-25-088", "R-25-118", "C-25-102", "O-25-041"} <= by_tenant["albuquerque_nm"]
    assert {"Ord 1330-2025", "Ord 1440-2025"} <= by_tenant["columbus_oh"]
    assert {"25-1187"} <= by_tenant["newark"]
    # the corrected P35.7 jurisdiction rides the keyword-derived rows
    assert all(
        r["jurisdiction"] == "Newark, NJ" for r in _index_rows(report) if r["tenant_id"] == "newark"
    )


def test_all_caps_title_still_matches_the_precision_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I4 Q5's collation question is pinned: an ALL-CAPS InSite title keeps
    matching — the precision scan is case-insensitive on the client side."""
    _pin_registry(monkeypatch, _CABQ)
    transport = _cabq_transport()
    report, _ctx = _run_legistar(transport)
    titles = {r["title"] for r in _index_rows(report)}
    assert any("FLOCK SAFETY" in (t or "") for t in titles)


def test_recency_slice_is_unfiltered_and_dedupes_against_keyword(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The recency pass keeps items the vocabulary does not name (the budget
    ordinance), and a matter seen by BOTH passes is one canonical claim — the
    dedupe rides content_digest, not an item-id table."""
    _pin_registry(monkeypatch, _CABQ)
    transport = _cabq_transport()
    report, _ctx = _run_legistar(transport)

    rows = _index_rows(report)
    shared = [r for r in rows if r["external_id"] == "C-25-088"]
    assert len(shared) == 5  # recency + four keyword-group captures
    assert len(_canonical(shared)) == 1, "identical matter → identical claim tuple"
    budget = [r for r in rows if r["external_id"] == "O-25-041"]
    assert len(budget) == 1, "recency-only item lands once, vocabulary-free"


# --- the per-tenant document window never widens --------------------------------


def test_doc_window_is_per_tenant_across_both_passes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """doc_per_tenant bounds the MERGED item set (recency ∪ keyword), not each
    capture — the widened acquisition never doubles the document fan-out."""
    _pin_registry(monkeypatch, _CABQ, doc_per_tenant=2)
    transport = _cabq_transport()
    report, _ctx = _run_legistar(transport)
    doc_requests = [
        u for u in transport.requested if "/matters/" in u.rstrip("/").rsplit("?", 1)[0]
    ]
    # the merged precise set is {C-25-088, R-25-118, O-25-041, C-25-102} —
    # four items, but the reviewed window is two per TENANT, not two per slice.
    assert len(doc_requests) == 2
    docs = [c for c in report.claims if c.get("record_kind") == "agenda_document"]
    assert len(docs) == 2


# --- replay / shadow determinism -------------------------------------------------


def test_shadow_run_and_replay_are_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Shadow diff is zero and the replayed claim set is identical — the
    merged paging + precision pass stay pure functions of the captures."""
    _pin_registry(monkeypatch, _THREE_TENANTS)
    transport = _cabq_transport()
    transport.add(
        "columbus/matters?$filter",
        200,
        _fixture("legistar_columbus_matters_keyword.json"),
        "application/json",
    )
    transport.add(
        "newark/matters?$filter",
        200,
        _fixture("legistar_newark_matters_keyword.json"),
        "application/json",
    )
    transport.add("columbus/matters?", 404, b"", "text/plain")
    transport.add("newark/matters?", 404, b"", "text/plain")
    transport.add(
        "columbus/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    transport.add(
        "newark/matters/", 200, _fixture("legistar_seattle_matter_11400.json"), "application/json"
    )
    report, ctx = _run_legistar(transport)

    diff = shadow_replay(ProcurementConnector(), ctx, list(report.captures), list(report.claims))
    assert diff.changed_count == 0, diff.summary()
    replayed = replay(ProcurementConnector(), ctx, list(report.captures))
    assert diff_claim_sets(list(report.claims), replayed).changed_count == 0


def test_no_forbidden_predicates_or_tokens_in_widened_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Part VIII stays fail-closed on the widened pass: no person/plate
    predicates, no forbidden tokens in emitted rows."""
    _pin_registry(monkeypatch, _CABQ)
    transport = _cabq_transport()
    report, _ctx = _run_legistar(transport)
    forbidden = {"officer_name", "person_name", "plate_number", "per_trip", "per_search"}
    for claim in report.claims:
        assert claim.get("predicate_id") not in forbidden
        raw = str(claim.get("raw_value") or "")
        assert "hotlist" not in raw.lower()

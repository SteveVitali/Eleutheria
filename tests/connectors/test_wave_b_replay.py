# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.12 — the Wave-B activated path, exercised over committed fixtures.

The wave's live legs run inside 2026-10-26 → 11-05 under the operator's
OP-26 flips; the tests here assert the *committed* truth the wave relies
on (never a live fetch, never a flip):

* every source on the Wave-B flip list resolves in the registry and
  stays ``ingestion_permitted=False`` — the flag is the operator's;
* the widen hosts (Denver HALO, Seattle CCTV, Chicago aggregates,
  OpenStates bills) are already permitted — their targets ride existing
  seats, no new flag;
* the cadence batches the legs run on carry exactly the gated members
  the gate declares;
* the activated path end-to-end: a gated source replayed on a permitted
  *copy* (the in-memory flip the live window will do for real) emits
  claims over a committed fixture — including ``enforcement_count`` on
  the Chicago aggregate lane the ``vocab_enforcement_count`` migration
  registers;
* the Flock probe's served/refused paths over its committed fixtures —
  every outcome recorded, a challenge stops-and-records.
"""

from __future__ import annotations

import dataclasses
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from connectors.dot_511 import Dot511Connector
from connectors.flock_portal_probe import (
    PROBE_CONNECTOR_NAME,
    PROBE_SOURCE_ID,
    FlockPortalProbeConnector,
    ProbeInventory,
    ProbeTarget,
    load_probe_inventory,
    probe_run_record,
)
from connectors.live_targets import live_targets
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
)
from evidence.ingest_run import IngestRun
from support import REPO_ROOT

from ops import wave_b

_DOT_FIX = Path(__file__).resolve().parent / "fixtures" / "dot_511"
_PROBE_FIX = Path(__file__).resolve().parent / "fixtures" / "flock_portal_probe"
_RETRIEVED = datetime(2026, 10, 12, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"


# --- committed-truth: the flip list vs the registry + cadence --------------------


def test_every_flip_row_registered_and_still_gated() -> None:
    """All 96 flip-list rows resolve and stay ``ingestion_permitted=False``
    — no agent flips a flag; the OP-26 execution is the operator's."""
    for sid in wave_b.FLIP_SOURCES:
        src = get(sid)
        assert src is not None, f"{sid} on the flip list must resolve"
        assert src.ingestion_permitted is False, (
            f"{sid} must stay gated until the operator's OP-26 flip"
        )


def test_widen_hosts_are_already_permitted() -> None:
    """The widen executions ride existing flips — never a new flag row."""
    widen_hosts = {sid for leg in wave_b.FAMILY_LEGS for sid in wave_b.LEG_SCOPE[leg]["widen"]}
    assert widen_hosts == {
        "camreg_denver_co",
        "camreg_seattle_wa",
        "camreg_chicago_il",
        "openstates",
    }
    for sid in widen_hosts:
        assert get(sid).ingestion_permitted is True, (
            f"{sid} widens under an existing flip — it must already be permitted"
        )
        assert sid not in wave_b.FLIP_SOURCES


def test_cadence_batches_carry_exactly_the_gated_members() -> None:
    """The gate's declared scope and the committed cadence registry agree —
    a rename that drifts must fail honestly here, not at live leg time."""
    cadence = tomllib.loads((REPO_ROOT / "ops/cadence.toml").read_text("utf-8"))
    batches = {b["id"]: set(b["members"]) for b in cadence["batches"]}
    leg_batch = {
        "L1": "r11-layers-01",
        "L2": "r11-layers-02",
        "L3": "r11-ate-01",
        "L4": "r11-procurement-01",
        "L5": "r11-disclosures-01",
        "L6": "r11-disclosures-02",
    }
    for leg, bid in leg_batch.items():
        assert set(wave_b.LEG_SCOPE[leg]["gated"]) == batches[bid], (
            f"{leg}: the gate's gated set and {bid} members disagree"
        )
    doc_members = batches["r11-documents-01"]
    assert (
        set(wave_b.LEG_SCOPE["L7"]["gated"]) | set(wave_b.LEG_SCOPE["L8"]["gated"]) == doc_members
    )


def test_probe_source_is_the_only_seatless_row() -> None:
    """The probe rides the documents job but holds no cadence batch seat —
    like L7's six hosted ccops rows."""
    cadence = tomllib.loads((REPO_ROOT / "ops/cadence.toml").read_text("utf-8"))
    all_members = {m for b in cadence["batches"] for m in b["members"]}
    assert PROBE_SOURCE_ID not in all_members
    for sid in wave_b.LEG_SCOPE["L7"]["hosted"]:
        assert sid not in all_members


def test_never_sources_are_never_declared() -> None:
    blob = {sid for leg in wave_b.LEG_SCOPE.values() for group in leg.values() for sid in group}
    assert "doj_ctas_awards" not in blob
    assert "camreg_tribal_all_leaders_directory" not in blob
    assert "legis_tribal_tohono_oodham_notice" not in blob


# --- the activated path over fixtures (the in-memory flip, never committed) ------


class _MapTransport:
    def __init__(self, responses: Mapping[str, FetchResult]) -> None:
        self._responses = dict(responses)
        self.request_log: list[str] = []

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        self.request_log.append(url)
        return dataclasses.replace(self._responses[url], url=url)


def _resp(url: str, body: bytes, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url,
        status=status,
        body=body,
        media_type="application/json",
        retrieved_at=_RETRIEVED,
    )


def _ctx(source_id: str, targets: list[dict[str, Any]], responses):
    connector = Dot511Connector()
    # The live leg's flip, modelled honestly: a permitted in-memory COPY —
    # the committed registry row is untouched and stays gated.
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=connector.version,
        transport=_MapTransport(responses),
    )
    return connector, RunContext(
        source=source,
        run=IngestRun(connector.name, connector.version, "test", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )


def _fixture_run(source_id: str, target_id: str, fixture: str, empty: bytes):
    targets = [t for t in live_targets(source_id) if t["id"] == target_id]
    assert targets, f"{source_id}:{target_id} must resolve registry targets"
    body = _DOT_FIX.joinpath(fixture).read_bytes()
    responses = {
        t["url"]: _resp(t["url"], body if t.get("page", 0) == 0 else empty) for t in targets
    }
    connector, ctx = _ctx(source_id, targets, responses)
    return run(connector, ctx)


def test_new_source_family_activated_path() -> None:
    """L1's dot_511_de — a new gated source — emits registry claims over its
    committed fixture once flipped (in memory). The committed row stays
    gated: the run asserts the flag is in-memory only."""
    report = _fixture_run(
        "dot_511_de",
        "traffic_devices_camera_de_boundary_and_point_layer_26",
        "de_firstmap.json",
        b'{"features": []}',
    )
    claims = [c for c in report.claims if c.get("record_kind") == "claim"]
    assert claims, "the activated dot_511_de path must emit claims"
    assert get("dot_511_de").ingestion_permitted is False


def test_widen_target_activated_path_emits_enforcement_count() -> None:
    """L3's Chicago widen — the camera-month aggregate on the already-flipped
    camreg_chicago_il — emits ``enforcement_count`` claims, the predicate
    the vocab_enforcement_count migration registers before the leg."""
    report = _fixture_run(
        "camreg_chicago_il",
        "chicago_speed_violations_monthly",
        "chicago_speed_violations.json",
        b"[]",
    )
    counts = [
        c
        for c in report.claims
        if c.get("record_kind") == "claim" and c.get("predicate_id") == "enforcement_count"
    ]
    assert counts, "the socrata_aggregate widen must emit enforcement_count claims"
    assert get("camreg_chicago_il").ingestion_permitted is True  # rides the existing flip


def test_denver_halo_widen_target_resolves() -> None:
    """L1's Denver HALO widen: the target resolves on the existing seat."""
    targets = [t for t in live_targets("camreg_denver_co") if "halo" in t["id"]]
    assert targets, "denver_police_halo must resolve under camreg_denver_co"


def test_openstates_bill_targets_resolve() -> None:
    """L8's two pinned bill queries ride the already-flipped openstates row
    (the connector's committed plan expands them to sweep targets)."""
    plan = tomllib.loads(
        (REPO_ROOT / "connectors/src/connectors/data/openstates_plan.toml").read_text("utf-8")
    )
    pinned = {q["id"] for q in plan.get("pinned_bill_queries", [])}
    assert {"az_hb2574_2024", "ny_s7037_2025_2026"} <= pinned


# --- the Flock probe: served / refused over committed fixtures ---------------------


def _probe_target(slug: str) -> ProbeTarget:
    return ProbeTarget(slug=slug, url=f"https://transparency.flock.com/{slug}", opted_out=False)


def _probe_inventory(*targets: ProbeTarget) -> ProbeInventory:
    return dataclasses.replace(load_probe_inventory(), portals=tuple(targets))


def _probe_run(pages: dict[str, FetchResult], *targets: ProbeTarget):
    class _T:
        def __init__(self, r):
            self._r = r

        def robots(self, u):
            return RobotsResult(text=_ALLOW_ALL)

        def request(self, url, *, user_agent, headers=None, body=None):
            return self._r[url]

    conn = FlockPortalProbeConnector(inventory=_probe_inventory(*targets))
    source = dataclasses.replace(get(PROBE_SOURCE_ID), ingestion_permitted=True)
    fetcher = PoliteFetcher(
        connector_name=PROBE_CONNECTOR_NAME,
        connector_version="1.0.0",
        transport=_T(pages),
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    report = run(
        conn,
        RunContext(
            source=source,
            run=IngestRun(PROBE_CONNECTOR_NAME, "1.0.0", "test", "r1", "v1", ()),
            fetcher=fetcher,
            captures=InMemoryCaptureStore(),
            claim_sink=InMemoryClaimSink(),
            parameters={},
        ),
    )
    return report, conn


def _page(url: str, fixture: str, status: int = 200) -> FetchResult:
    return FetchResult(
        url=url,
        status=status,
        body=_PROBE_FIX.joinpath(fixture).read_bytes(),
        media_type="text/html",
        retrieved_at=_RETRIEVED,
    )


def test_probe_served_and_refused_both_record() -> None:
    """One served portal + one challenged portal — the run record lands both
    outcomes; L9's gate reads exactly this shape."""
    served, refused = _probe_target("sunnydale-ca-pd"), _probe_target("adrian-mi-pd")
    pages = {
        served.url: _page(served.url, "served_sunnydale.html"),
        refused.url: _page(refused.url, "challenge_403.html", status=403),
    }
    report, conn = _probe_run(pages, served, refused)
    rec = probe_run_record(conn, report, run_id="r1", generated_at="2026-01-01T00:00:00Z")
    assert rec["version"] == "sig.probe-run/1"
    results = {r["portal"]: r for r in rec["results"]}
    assert results["sunnydale-ca-pd"]["result"] == "served"
    assert results["adrian-mi-pd"]["result"] == "refused"
    assert results["adrian-mi-pd"]["refusal_kind"]


def test_probe_inventory_is_the_committed_917() -> None:
    """L9's gate asserts ``portals_attempted == 917`` — the committed set."""
    assert len(load_probe_inventory().portals) == wave_b.PROBE_INVENTORY

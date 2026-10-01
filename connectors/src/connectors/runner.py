# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The connector runner — fixture spine wiring (P19.4) and live/replay/shadow (P21.3).

This drives one registered connector end-to-end through the eight stages
(:func:`connectors.pipeline.run`). Two entry points:

* :func:`run_connector_over_fixture` (P19.4) — a **local fixture file**, no real
  network, a static transport serving the fixture bytes for every URL, asserting
  the run's claims into a selected :class:`~connectors.stages.ClaimSink`. The
  spine-wiring path the composed stack and ``--sink pg`` use.
* :func:`run_source` (P21.3) — the source-driven ``sig-connectors run`` surface
  with an explicit ``mode``: ``live`` **refuses** (raising :class:`LiveGateRefused`,
  CLI exit 3) unless the source's rights-review status is *fully green*
  (SIG-INGEST-028 / P21.1) — so a live fetch is structurally impossible without a
  green review-status (LD-X08 can never recur) — then executes the eight stages
  over the real :class:`~connectors.transports.HttpxTransport` into an
  :class:`~connectors.capture_ocfl.OcflCaptureStore`, writing a **fetch record**
  (:class:`FetchRecord`) that carries no content; ``replay`` / ``shadow`` run over
  a committed fixture under network isolation and never fetch.
"""

from __future__ import annotations

import dataclasses
import json
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from evidence.ingest_run import IngestRun

from .loader import compact_permits_ingestion, custody_permits_fetch
from .net import (
    FetchResult,
    PoliteFetcher,
    RateLimiter,
    RobotsDisallowed,
    RobotsResult,
    RobotsUnretrievable,
)
from .pipeline import RunReport, run
from .registry import SourceRecord, get
from .replay import ShadowDiff, replay, replay_fingerprint, shadow_replay
from .review import has_review_metadata, has_rights_block
from .sinks import make_claim_sink
from .stages import (
    ArtifactStore,
    CaptureRef,
    ClaimSink,
    Connector,
    ContentDrift,
    InMemoryCaptureStore,
    RunContext,
    registered_connectors,
)

_ROBOTS_ALLOW_ALL = "User-agent: *\nAllow: /\n"

#: The connector each critical-path source runs through, so ``run --source ID``
#: can pick the adapter without ``--connector`` (SIG-INGEST-021). Extend as
#: sources are wired; ``--connector`` overrides.
CONNECTOR_FOR_SOURCE: dict[str, str] = {
    "osm_overpass": "osm",
    "osm_element_history": "osm",
    "eff_atlas_of_surveillance": "atlas",
    "muckrock": "records",
    "usaspending": "procurement",
    "okc_council": "procurement",
    "okc_procurement": "okc_procurement",
    "okcpd_policy": "okcpd_policy",
    "ok_statute": "ok_statute",
    "eff_data_driven": "data_driven",
    "carnegie_ai_gsi": "coarse_international",
    "facial_recognition_world_map": "coarse_international",
    "aspi_mapping_chinas_tech_giants": "coarse_international",
    "pathways_rtcc_federation": "pathways",
    "pathways_fr_css_forensics": "pathways",
    "pathways_acoustic_drone_location": "pathways",
    # The second jurisdiction (P24.6 / JURIS.2): the France/Belgium sources route
    # through the P18.2 connectors — records for the arrêté + CADA path,
    # procurement for the DECP national open-data path. All stay
    # `ingestion_permitted=false` (HG-03); they run over committed fixtures in
    # replay/shadow only.
    "raa_prefectures": "france_belgium_records",
    "madada": "france_belgium_records",
    "declarationcamera_be": "france_belgium_records",
    "decp_fr": "france_belgium_procurement",
    # The CCOPS class (P24.7 / CCOPS.1 / GL-CCOPS-01): the three paying source
    # adapters of the `government_mandated_disclosure` connector (SIG-INGEST-049c).
    # All stay `ingestion_permitted=false` (HG-03); replay/shadow run over
    # committed fixtures in `tests/connectors/fixtures/ccops/`.
    "ccops_seattle": "government_mandated_disclosure",
    "ccops_nyc_post": "government_mandated_disclosure",
    "ccops_sf": "government_mandated_disclosure",
    # The committed one-time seed (P25.7 / D-CCOPS.1-1, SIG-INGEST-049f): loaded
    # via `sig-connectors load-seed` / `run_seed` — the packaged asset over the
    # static transport, never a live fetch.
    "state_alpr_statute_inventory": "state_statute_seed",
    # The nine P25.6 `promote` sources, made real under P26.2 (SOURCES.2). Each
    # routes through its named class connector — no bespoke adapters:
    #   * legistar / civicclerk / primegov — the agenda-platform tenant path the
    #     procurement connector already owns (§22.3, §23.6): discover() reads the
    #     published tenant registry, fetch hits the per-tenant index endpoint,
    #     and a reviewed matter-type match emits a Contract claim;
    #   * sam_gov — the procurement connector's federal-opportunity path
    #     (`procurement_notice` records; api_key from $SIG_SAM_GOV_KEY, HG-09);
    #   * courtlistener_recap — the accountability connector's targeted-lookup
    #     CourtListener path (SIG-INGEST-036/037: known dockets only);
    #   * documentcloud — the records connector's released-document index path
    #     (targeted document lookups, never the search listing);
    #   * eyes_on_flock — the existing flock_portal connector (P11.1);
    #   * openstates — the accountability connector's bill-index path: a state
    #     bill is NOT a §11.14 LegalInstrument (the frozen LegalInstrumentType
    #     vocabulary has no 'bill' and a pending bill is not a statute), so the
    #     bill row is an index_only evidence link (primary_record class) — the
    #     index fact is recorded, no legal effect is asserted (§3.1);
    #   * fbi_cde_agency_registry — the new `agency_registry` connector (P26.2):
    #     the ORI9 agency identity substrate, not procurement/records semantics.
    "legistar": "procurement",
    "civicclerk": "procurement",
    "primegov": "procurement",
    # P26.5 (SOURCES.5): eScribe joins the agenda-platform tenant path — the
    # tenant's public calendar page itself calls the bounded JSON webmethod the
    # registry row names (MeetingsCalendarView.aspx/GetCalendarMeetings).
    "escribe": "procurement",
    "sam_gov": "procurement",
    "courtlistener_recap": "accountability",
    "documentcloud": "records",
    "eyes_on_flock": "flock_portal",
    "openstates": "accountability",
    "fbi_cde_agency_registry": "agency_registry",
    # P26.12 (SOURCES.11): the federal companion to the OpenStates sweep — the
    # accountability connector's Congress.gov bill-index path. A federal bill
    # is likewise PROPOSED law, never a §11.14 LegalInstrument (§3.1); the
    # existing api.data.gov key ($SIG_DATA_GOV_KEY) rides the X-Api-Key
    # header, never the URL.
    "congress_gov": "accountability",
    # P31.12 (BREADTH.1): the four P29.3 GL-GATE-07 rights flips route through
    # the accountability connector's targeted `oversight_report` lookup — one
    # reviewed live-targets row per published report (landing page or report
    # PDF, never an index); an oversight finding is an AccountabilityEvent,
    # never a deployment claim (procured/reviewed ≠ deployed).
    "gao_surveillance_reports": "accountability",
    "dhs_oig_reports": "accountability",
    "dhs_fusion_center_assessments": "accountability",
    "uk_surveillance_camera_commissioner": "accountability",
    # P26.7 (SOURCES.7): state DOT/511 traffic-camera location registries — one
    # source row per state so rights/robots/cadence stay per-host granular; all
    # route through the `dot_511` connector over the per-state target registry
    # (data/dot_511_targets.toml). Only GL-GATE-06-resolved rows are flipped.
    "dot_511_ky": "dot_511",
    "dot_511_il": "dot_511",
    "dot_511_ut": "dot_511",
    "dot_511_or": "dot_511",
    "dot_511_la": "dot_511",
    "dot_511_ia": "dot_511",
    "dot_511_wa": "dot_511",
    "dot_511_dc": "dot_511",
    "dot_511_ga": "dot_511",
    "dot_511_al": "dot_511",
    "dot_511_mo": "dot_511",
    "dot_511_tx": "dot_511",
    "dot_511_md": "dot_511",
    # P26.9 (SOURCES.8): municipal / transit / non-US camera registries — one
    # source row per publisher; all route through the `dot_511` connector over
    # the merged target registry (data/camera_registry_targets.toml). Gated
    # rows stay `ingestion_permitted=false` until their named rights blocker
    # resolves (DEFERRALS D-SOURCES.8-1/-2).
    "camreg_austin_tx": "dot_511",
    "camreg_nola_la": "dot_511",
    "camreg_batonrouge_la": "dot_511",
    "camreg_winnipeg_mb": "dot_511",
    "camreg_act_au": "dot_511",
    "camreg_siouxfalls_sd": "dot_511",
    "camreg_baltimore_md": "dot_511",
    "camreg_ottawa_on": "dot_511",
    "camreg_sheffield_gb": "dot_511",
    "camreg_chicago_il": "dot_511",
    "camreg_calgary_ab": "dot_511",
    "camreg_edmonton_ab": "dot_511",
    "camreg_honolulu_hi": "dot_511",
    "camreg_md_opendata": "dot_511",
    "camreg_york_on": "dot_511",
    "camreg_arlington_va": "dot_511",
    "camreg_seattle_wa": "dot_511",
    "camreg_bellevue_wa": "dot_511",
    "camreg_lexington_ky": "dot_511",
    "camreg_nzta_nz": "dot_511",
    "camreg_qldc_au": "dot_511",
    "camreg_donegal_ie": "dot_511",
    "camreg_hk_hk": "dot_511",
    # P26.13 (SOURCES.12): open-data-catalog sweep yield — the clear-licence
    # point-feature registries qualified by the Socrata/ArcGIS-Hub/CKAN sweep,
    # routed through the same `dot_511` connector over
    # data/camera_registry_targets.toml. The gated remainder is named in
    # DEFERRALS D-SOURCES.12-1.
    "camreg_washington_dc": "dot_511",
    "camreg_nottingham_gb": "dot_511",
    "camreg_york_gb": "dot_511",
    "camreg_glasgow_gb": "dot_511",
    "camreg_northayrshire_gb": "dot_511",
    "camreg_lambeth_gb": "dot_511",
    "camreg_peel_on": "dot_511",
    "camreg_stalbert_ab": "dot_511",
    "camreg_rochester_ny": "dot_511",
    "camreg_goldcoast_au": "dot_511",
    "camreg_puertogaitan_co": "dot_511",
    # --- P26.16 (SOURCES.15) generated block — regenerated by p2616_batch.py
    "camreg_achd_id": "dot_511",
    "camreg_aikner": "dot_511",
    "camreg_amber_kh": "dot_511",
    "camreg_apram_pt": "dot_511",
    "camreg_arc_1975641302": "dot_511",
    "camreg_avctransport": "dot_511",
    "camreg_azdot_az": "dot_511",
    "camreg_baltimore_atves_md": "dot_511",
    "camreg_bangla_bd": "dot_511",
    "camreg_bargabos": "dot_511",
    "camreg_bedford_gb": "dot_511",
    "camreg_bettendorf_ia": "dot_511",
    "camreg_bouhan_jp": "dot_511",
    "camreg_brea_ca": "dot_511",
    "camreg_caledon_on": "dot_511",
    "camreg_caloes_ca": "dot_511",
    "camreg_camberwell_au": "dot_511",
    "camreg_camilo_schools": "dot_511",
    "camreg_carver_mn": "dot_511",
    "camreg_cclemire": "dot_511",
    "camreg_chattanooga_tn": "dot_511",
    "camreg_cheicylia": "dot_511",
    "camreg_colgis": "dot_511",
    "camreg_cotgeo": "dot_511",
    "camreg_cphang": "dot_511",
    "camreg_cwarcgis": "dot_511",
    "camreg_dc_dot_dc": "dot_511",
    "camreg_denver_co": "dot_511",
    "camreg_dover_gb": "dot_511",
    "camreg_dubuque_ia": "dot_511",
    "camreg_duganmeyer": "dot_511",
    "camreg_durham_gb": "dot_511",
    "camreg_eastdun_gb": "dot_511",
    "camreg_ebrgis_la": "dot_511",
    "camreg_esri_dash": "dot_511",
    "camreg_esriukpolice_gb": "dot_511",
    "camreg_essex_gb": "dot_511",
    "camreg_fifia": "dot_511",
    "camreg_firemedic": "dot_511",
    "camreg_fl511_fl": "dot_511",
    "camreg_forwardalliance": "dot_511",
    "camreg_freese_dm": "dot_511",
    "camreg_friendswood_tx": "dot_511",
    "camreg_gainesville_fl": "dot_511",
    "camreg_gedling_gb": "dot_511",
    "camreg_gistel_be": "dot_511",
    "camreg_gmh_emc_ga": "dot_511",
    "camreg_guildford_gb": "dot_511",
    "camreg_gvanmaren": "dot_511",
    "camreg_helberg": "dot_511",
    "camreg_indonesia_id": "dot_511",
    "camreg_infocemosa": "dot_511",
    "camreg_infraestructura": "dot_511",
    "camreg_ira": "dot_511",
    "camreg_jcfd3_or": "dot_511",
    "camreg_jelenic": "dot_511",
    "camreg_jmh_us": "dot_511",
    "camreg_kcmo_mo": "dot_511",
    "camreg_keizer_or": "dot_511",
    "camreg_keshan": "dot_511",
    "camreg_kirkland_wa": "dot_511",
    "camreg_kosman": "dot_511",
    "camreg_kunying": "dot_511",
    "camreg_langan": "dot_511",
    "camreg_lawrence_ks": "dot_511",
    "camreg_lenhardt": "dot_511",
    "camreg_leon_fl": "dot_511",
    "camreg_lisburn_gb": "dot_511",
    "camreg_lojic_ky": "dot_511",
    "camreg_lpd_flock": "dot_511",
    "camreg_manhattan_ks": "dot_511",
    "camreg_mark43": "dot_511",
    "camreg_massdot_ma": "dot_511",
    "camreg_mbrc_au": "dot_511",
    "camreg_mctx_tx": "dot_511",
    "camreg_mhebert": "dot_511",
    "camreg_mndot_mn": "dot_511",
    "camreg_monmap_mn": "dot_511",
    "camreg_mueller_de": "dot_511",
    "camreg_nashville_tn": "dot_511",
    "camreg_nitro": "dot_511",
    "camreg_nola_safety_la": "dot_511",
    "camreg_nurnazihah": "dot_511",
    "camreg_nyc_jgrayson_ny": "dot_511",
    "camreg_nyc_weltia_ny": "dot_511",
    "camreg_oem_camera": "dot_511",
    "camreg_olsson": "dot_511",
    "camreg_oosgis_nl": "dot_511",
    "camreg_osm_surveillance": "dot_511",
    "camreg_palmdesert_ca": "dot_511",
    "camreg_penndot_pa": "dot_511",
    "camreg_pgcounty_md": "dot_511",
    "camreg_pipeline_sec": "dot_511",
    "camreg_plymouth_gb": "dot_511",
    "camreg_polyu_hk": "dot_511",
    "camreg_portland_or": "dot_511",
    "camreg_raleigh_nc": "dot_511",
    "camreg_ramallah_ps": "dot_511",
    "camreg_redmond_wa": "dot_511",
    "camreg_riyadh_sa": "dot_511",
    "camreg_rjcoleman": "dot_511",
    "camreg_ruslan": "dot_511",
    "camreg_salisbury_nc": "dot_511",
    "camreg_sarasota_fl": "dot_511",
    "camreg_schellinger": "dot_511",
    "camreg_sensenet": "dot_511",
    "camreg_sfoss": "dot_511",
    "camreg_smart_sky": "dot_511",
    "camreg_squan": "dot_511",
    "camreg_stanford_us": "dot_511",
    "camreg_surrey_bc": "dot_511",
    "camreg_sweeney": "dot_511",
    "camreg_tblose": "dot_511",
    "camreg_thailand_th": "dot_511",
    "camreg_toronto_on": "dot_511",
    "camreg_townofws": "dot_511",
    "camreg_trafficops_ca": "dot_511",
    "camreg_trpa_us": "dot_511",
    "camreg_tulane_la": "dot_511",
    "camreg_txdot_rep_tx": "dot_511",
    "camreg_uchicago": "dot_511",
    "camreg_ucsd": "dot_511",
    "camreg_ukm_my": "dot_511",
    "camreg_umbc_md": "dot_511",
    "camreg_univmb_mb": "dot_511",
    "camreg_uofmd_md": "dot_511",
    "camreg_vancouver_bc": "dot_511",
    "camreg_vidya": "dot_511",
    "camreg_webappfme": "dot_511",
    "camreg_wellington_nz": "dot_511",
    "camreg_whatley": "dot_511",
    "camreg_wim_camera": "dot_511",
    "camreg_yazid": "dot_511",
    "camreg_yline": "dot_511",
    "camreg_yorku": "dot_511",
    "camreg_zyinger": "dot_511",
    # --- end P26.16 generated block ---
    # P26.10 (SOURCES.9): multi-tenant procurement portals — the `procurement`
    # connector reads its targets from the published portal tenant registry
    # (data/procurement_portal_tenants.toml, live_targets
    # kind=procurement_portal_tenants). BidNet storefronts, Bonfire/OpenGov
    # portals, and city Socrata contract datasets — one source row per
    # publisher/platform so rights/robots/cadence stay granular; gated rows
    # stay `ingestion_permitted=false` until their named blocker resolves
    # (DEFERRALS D-SOURCES.9-1..4).
    "bidnet_direct": "procurement",
    "bonfire": "procurement",
    "opengov_procurement": "procurement",
    "procportal_austin_tx": "procurement",
    "procportal_sf_ca": "procurement",
    "procportal_kcmo_mo": "procurement",
    "procportal_nyc_ny": "procurement",
    "procportal_chicago_il": "procurement",
    # P26.15 (SOURCES.14): the EU procurement surface — TED (Tenders Electronic
    # Daily) OJ S notices via the procurement connector's bounded Search-API
    # sweep (keyless documented POST /v3/notices/search; a tender notice is
    # procurement evidence only — procured ≠ deployed).
    "ted_eu": "procurement",
}


class RunMode(StrEnum):
    """The three run modes ``sig-connectors run --mode`` accepts (SIG-INGEST-018/019)."""

    LIVE = "live"
    REPLAY = "replay"
    SHADOW = "shadow"


class LiveGateRefused(Exception):
    """Raised when a ``live`` run is attempted on a source that is not fully green.

    A live fetch is permitted **only** for a source whose rights-review status is
    fully green (flipped by the operator in P21.1 with recorded review metadata).
    Any other source is refused *before any fetch* (SIG-INGEST-014/028) — the
    structural guarantee that a live fetch is impossible without a green
    review-status (LD-X08 can never recur). The CLI maps this to exit code 3.
    """

    def __init__(self, source_id: str, reasons: Sequence[str]) -> None:
        self.source_id = source_id
        self.reasons = list(reasons)
        joined = "; ".join(self.reasons)
        super().__init__(
            f"live fetch refused for source {source_id!r}: {joined} "
            "(SIG-INGEST-028; a live fetch requires a fully-green review-status — P21.1/HG-03)."
        )


def live_gate_reasons(source: SourceRecord | str) -> list[str]:
    """Every reason a ``live`` fetch is refused for ``source`` — empty means green.

    "Fully green" is the P21.1 review-status: ``ingestion_permitted`` true, a
    compact status that permits ingestion, a content-fetching custody posture, a
    resolved (non-``UNDETERMINED``) rights block, and recorded review metadata
    (``rights_reviewed_by`` + ``rights_reviewed_on``). A single missing field
    refuses the fetch (fail-closed, SIG-INGEST-028).
    """
    record = get(source) if isinstance(source, str) else source
    reasons: list[str] = []
    if not record.ingestion_permitted:
        reasons.append("ingestion_permitted=false (not flipped by a reviewer, SIG-INGEST-028)")
    if not compact_permits_ingestion(record.compact_status):
        reasons.append(
            f"compact_status={record.compact_status.value!r} does not permit ingestion (§22.4)"
        )
    if not custody_permits_fetch(record.custody_posture):
        reasons.append(f"custody_posture={record.custody_posture.value!r} is link-only (§8.4)")
    if not has_rights_block(record):
        reasons.append("rights block is UNDETERMINED (SIG-LIC-004)")
    if not has_review_metadata(record):
        reasons.append("no recorded review metadata (rights_reviewed_by/on, SIG-INGEST-038)")
    return reasons


def is_review_status_green(source: SourceRecord | str) -> bool:
    """Whether a ``live`` fetch is permitted (review-status fully green, P21.1)."""
    return not live_gate_reasons(source)


class _StaticFileTransport:
    """Serves one fixture's bytes for any URL — no real network (SIG-INGEST-011)."""

    def __init__(self, body: bytes, media_type: str) -> None:
        self._body = body
        self._media_type = media_type

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ROBOTS_ALLOW_ALL)

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type=self._media_type,
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _chunk_kwargs(commit_chunk_size: int | None) -> dict[str, Any]:
    """Kwargs for a PG sink's ``commit_chunk_size`` — empty when unset (default).

    Keeps the module default authoritative in ``db.claim_sink``: passing nothing
    lets the sink apply :data:`db.claim_sink.DEFAULT_COMMIT_CHUNK_SIZE`, so the
    connector layer never hard-codes a chunk size (P26.18 / SOURCES.17).
    """
    return {} if commit_chunk_size is None else {"commit_chunk_size": commit_chunk_size}


def run_connector_over_fixture(
    connector_name: str,
    source_id: str,
    fixture: Path,
    *,
    media_type: str,
    kind: str,
    sink: ClaimSink | None = None,
    sink_kind: str = "memory",
    dsn: str | None = None,
    code_commit: str = "unknown",
    target_url: str | None = None,
    commit_chunk_size: int | None = None,
) -> RunReport:
    """Run ``connector_name`` over ``fixture`` and assert claims into the sink.

    Either pass a built ``sink`` or a ``sink_kind`` (+ ``dsn`` for ``pg``); a PG
    sink is stamped with the connector identity so its ``ingest_run`` is coherent.
    ``commit_chunk_size`` (PG sink only) bounds the per-transaction claim count;
    ``None`` uses the sink's default (small sources commit in one chunk).
    """
    registry = registered_connectors()
    if connector_name not in registry:
        raise ValueError(f"unknown connector {connector_name!r}; registered: {sorted(registry)}")
    connector: Connector = registry[connector_name]()
    version = getattr(connector, "version", "1.0.0")

    if sink is None:
        if sink_kind == "pg":
            sink = make_claim_sink(
                "pg",
                dsn=dsn,
                connector_name=connector.name,
                connector_version=version,
                code_commit=code_commit,
                **_chunk_kwargs(commit_chunk_size),
            )
        else:
            sink = make_claim_sink(sink_kind)

    # A reviewer flips the seed row to permitted to run (the seed stays
    # ingestion_permitted=false; SIG-INGEST-028), exactly as the tests do.
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    transport = _StaticFileTransport(fixture.read_bytes(), media_type)
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=version,
        transport=transport,
        # A fixture replay opens no socket — the politeness bookkeeping still
        # runs, but it must not burn REAL sleep seconds per same-host tenant
        # now that a source fans out to hundreds of registry targets (P26.5).
        rate_limiter=RateLimiter(sleep=lambda _seconds: None),
    )
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, version, code_commit, "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=sink,
        parameters={
            "targets": [
                {
                    "id": "t1",
                    "url": target_url or f"https://{source_id}/x",
                    "kind": kind,
                }
            ]
        },
    )
    return run(connector, ctx)


def run_seed(
    source_id: str,
    *,
    connector_name: str | None = None,
    sink_kind: str = "memory",
    dsn: str | None = None,
    code_commit: str = "unknown",
) -> RunReport:
    """Load a committed one-time seed asset into the claim spine (P25.7).

    The seed is **packaged reviewed data, never a feed**: the ``seeds.toml`` row
    names the packaged asset + target kind, and the run goes through the same
    eight-stage pipeline, the same loader gate, and the same append-only
    ``ClaimSink`` as every source — over the static transport, so no network is
    ever opened. The in-memory ``ingestion_permitted`` flip is the documented
    seed carve-out of :func:`run_connector_over_fixture` (SIG-INGEST-028); the
    registry row stays false — a live run for the seed source is still refused.
    """
    from .seeds import seed_asset_path, seed_spec

    spec = seed_spec(source_id)
    if spec is None:
        from .seeds import SeedNotRegistered

        raise SeedNotRegistered(f"source {source_id!r} has no committed seed asset in seeds.toml")
    name = connector_name or CONNECTOR_FOR_SOURCE.get(source_id)
    if name is None:
        raise ValueError(f"no connector known for seed source {source_id!r}; pass a connector name")
    return run_connector_over_fixture(
        name,
        source_id,
        seed_asset_path(source_id),
        media_type=str(spec["media_type"]),
        kind=str(spec["kind"]),
        sink_kind=sink_kind,
        dsn=dsn,
        code_commit=code_commit,
        target_url=str(spec.get("target_url") or "") or None,
    )


# --- the fetch record (P21.3 owns this format; SIG-INGEST-015) ----------------


@dataclass
class FetchRecord:
    """The immutable record one live run writes (``docs/build/live_runs/``).

    It carries **no content** — only what was fetched, from where, when, and the
    crawler-conduct evidence (rate-limit events + robots decisions, RISK-P21-04) a
    reviewer needs to audit the run. The captured bytes live in the OCFL store
    (content-addressed by ``capture_digests``); the record is provenance, not a
    copy (append-only, P1–P3: a re-run writes a new dated record, never edits one).
    """

    source_id: str
    connector: str
    mode: str
    started_at: str
    duration_seconds: float
    urls: list[str] = field(default_factory=list)
    status_codes: list[int] = field(default_factory=list)
    byte_counts: list[int] = field(default_factory=list)
    capture_digests: list[str] = field(default_factory=list)
    claim_count: int = 0
    rate_limit_events: list[Mapping[str, Any]] = field(default_factory=list)
    robots_decisions: list[Mapping[str, Any]] = field(default_factory=list)
    #: Per-URL rows for fetches that proceeded despite a non-grant robots
    #: verdict (GL-GATE-08 / ADR-088): ``{"url", "host", "verdict"}`` with
    #: verdict ``"disallowed"`` or ``"unretrievable"``. The marker keeps the
    #: audit trail honest — a claim asserted from such a fetch has provenance
    #: saying the fetch ignored a refusal.
    robots_disregarded: list[Mapping[str, Any]] = field(default_factory=list)
    #: Set when the live content no longer matched the connector's expected shape
    #: (P25.1 / ADR-082): the run emitted 0 claims and recorded the drift, loud.
    content_drift: str | None = None
    #: Set when the politeness layer refused the run outright — a seed target
    #: whose fetch raised a politeness refusal (SIG-INGEST-012). The refusal is
    #: recorded, never bypassed. Under GL-GATE-08 / ADR-088 ``PoliteFetcher``
    #: no longer raises robots refusals — this field is retained for the
    #: record vocabulary and non-standard fetchers.
    politeness_refusal: str | None = None
    #: Per-document politeness refusals on discovery-continuation targets
    #: (P25.5): a resolved child whose host refuses is a recorded disposition,
    #: and the run continues to the next resolved target.
    refusals: list[Mapping[str, Any]] = field(default_factory=list)
    #: Per-document disappearances (a resolved child that 404s / is
    #: access-restricted — SIG-INGEST-009/010), recorded loud so a dead filing
    # link is visible, never a silent empty result.
    disappearances: list[Mapping[str, Any]] = field(default_factory=list)
    #: Per-document content drift on resolved child documents (P26.6): a
    #: document whose captured bytes no longer parse as the platform's genre is
    #: recorded here — fail-closed per document, never a fabricated extraction.
    document_drift: list[Mapping[str, Any]] = field(default_factory=list)
    #: Per-document outcomes for resolved agenda_document children (P26.6): each
    #: fetched document's url, tenant, outcome (matched/no_match/empty) and the
    #: capture digest that established it — durable provenance the claim rows
    #: deliberately do not carry (a byte-volatile capture id must not key a
    #: claim's content_digest).
    document_outcomes: list[Mapping[str, Any]] = field(default_factory=list)
    #: Quota-bounded sweep bookkeeping (P26.19): the number of quota-governed
    #: requests this run ISSUED (a refused request still counts), the per-run
    #: budget in force, and whether the run stopped at the budget (headroom) or
    #: at a 429 wall. For a non-sweep source these stay at their defaults.
    sweep_requests: int = 0
    sweep_budget: int | None = None
    budget_reached: bool = False
    quota_reached: bool = False
    sweep_skipped: list[Mapping[str, Any]] = field(default_factory=list)
    #: Incremental restart (P31.4 / ADR-111): the number of fetches this execution
    #: issued, and the targets it did not re-fetch because an interrupted execution
    #: of the same logical run had already captured (``reprocessed``) or flushed
    #: (``skipped``) them. The logical run key it resumed under, when it had one.
    fetches: int = 0
    resumed: list[Mapping[str, Any]] = field(default_factory=list)
    logical_run: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """A JSON-serialisable dict; content is never included (§3.1, §17)."""
        return {
            "source_id": self.source_id,
            "connector": self.connector,
            "mode": self.mode,
            "started_at": self.started_at,
            "duration_seconds": round(self.duration_seconds, 6),
            "urls": list(self.urls),
            "status_codes": list(self.status_codes),
            "byte_counts": list(self.byte_counts),
            "capture_digests": list(self.capture_digests),
            "claim_count": self.claim_count,
            "rate_limit_events": [dict(e) for e in self.rate_limit_events],
            "robots_decisions": [dict(d) for d in self.robots_decisions],
            "robots_disregarded": [dict(d) for d in self.robots_disregarded],
            "content_drift": self.content_drift,
            "politeness_refusal": self.politeness_refusal,
            "refusals": [dict(r) for r in self.refusals],
            "disappearances": [dict(d) for d in self.disappearances],
            "document_drift": [dict(d) for d in self.document_drift],
            "document_outcomes": [dict(d) for d in self.document_outcomes],
            "sweep_requests": self.sweep_requests,
            "sweep_budget": self.sweep_budget,
            "budget_reached": self.budget_reached,
            "quota_reached": self.quota_reached,
            "sweep_skipped": [dict(s) for s in self.sweep_skipped],
            "fetches": self.fetches,
            "resumed": [dict(r) for r in self.resumed],
            "logical_run": self.logical_run,
        }


#: Where dated fetch records land (SIG-INGEST-015; P21.3 owns the format).
LIVE_RUNS_DIR = Path("docs/build/live_runs")


def write_fetch_record(record: FetchRecord, directory: Path | None = None) -> Path:
    """Write ``record`` to ``<directory>/<date>_<source>.json`` (append-only)."""
    directory = directory or LIVE_RUNS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    date = record.started_at[:10]
    path = directory / f"{date}_{record.source_id}.json"
    path.write_text(
        json.dumps(record.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


# --- the source-driven run surface (P21.3) ------------------------------------


@dataclass
class SourceRunReport:
    """The outcome of one ``sig-connectors run --source`` invocation."""

    source_id: str
    connector: str
    mode: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    captures: list[Any] = field(default_factory=list)
    asserted: bool = False
    diff: ShadowDiff | None = None
    replay_reproducible: bool | None = None
    fetch_record: FetchRecord | None = None
    refusals: list[dict[str, Any]] = field(default_factory=list)
    disappearances: list[dict[str, Any]] = field(default_factory=list)
    drifted: list[dict[str, Any]] = field(default_factory=list)
    #: The ``ingest_run`` this execution wrote (PG sink only; P31.2 / ADR-109), so
    #: the scheduled wrapper's WORM run row can name it. ``None`` for other sinks.
    run_id: str | None = None
    #: Every record the run emitted, exact even when ``claims`` retains only some
    #: (a live PG run flushes per capture and keeps only what its fetch record
    #: needs, P31.4). ``None`` = not counted separately: use ``len(claims)``.
    claim_count: int | None = None
    #: The P31.4 resume bookkeeping (see :class:`FetchRecord`).
    fetches: int = 0
    resumed: list[dict[str, Any]] = field(default_factory=list)

    @property
    def emitted(self) -> int:
        """The number of records the run emitted (``claim_count`` or ``len(claims)``)."""
        return self.claim_count if self.claim_count is not None else len(self.claims)


#: The record kinds a live run's fetch record reports per document (P26.6/.11/.15).
#: A live PG run retains only these in memory (P31.4 / ADR-111).
_OUTCOME_RECORD_KINDS = frozenset(
    {"agenda_document", "portal_document", "bill_query", "ted_eu_slice"}
)


def _retain_outcome_record(record: Mapping[str, Any]) -> bool:
    return record.get("record_kind") in _OUTCOME_RECORD_KINDS


def _flushed_records(sink: Any) -> int:
    """Records a sink had flushed when a run raised (P31.4 / ADR-111).

    Since claims are flushed per capture, the captures before a failing one may have
    committed; the fetch record reports them instead of claiming 0. A PG sink counts
    records considered; the in-memory sink keeps what it was handed.
    """
    report = getattr(sink, "report", None)
    if report is not None and isinstance(getattr(report, "considered", None), int):
        return int(report.considered)
    return len(getattr(sink, "claims", ()) or ())


def _robots_decisions(fetcher: PoliteFetcher) -> list[Mapping[str, Any]]:
    """The per-host robots.txt audit rows a live run records (ADR-087).

    Each entry names the host, the robots URL probed, the HTTP status the
    transport saw (``None`` on a connection-level failure), and the outcome —
    ``retrieved`` (a policy governs), ``no_policy_4xx`` (RFC 9309 §2.3.1.4: no
    policy exists), or ``unretrievable`` (not granted, SIG-INGEST-012).
    """
    return [{"host": host, **outcome} for host, outcome in fetcher.robots_outcomes.items()]


def _connector_for(source_id: str, connector_name: str | None) -> Connector:
    name = connector_name or CONNECTOR_FOR_SOURCE.get(source_id)
    if name is None:
        raise ValueError(
            f"no connector known for source {source_id!r}; pass --connector "
            f"(known: {sorted(CONNECTOR_FOR_SOURCE)})"
        )
    registry = registered_connectors()
    if name not in registry:
        raise ValueError(f"unknown connector {name!r}; registered: {sorted(registry)}")
    return registry[name]()


def run_source(
    source_id: str,
    *,
    mode: RunMode | str,
    connector_name: str | None = None,
    fixture: Path | None = None,
    media_type: str = "application/json",
    kind: str = "overpass",
    sink_kind: str = "memory",
    dsn: str | None = None,
    capture_dir: Path | None = None,
    wacz: bool = False,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    run_record_uri: str | None = None,
    logical_run: str | None = None,
    target_limit: int | None = None,
) -> SourceRunReport:
    """Run one source in ``live`` / ``replay`` / ``shadow`` mode (P21.3).

    ``live`` refuses (raising :class:`LiveGateRefused`) unless the source's
    review-status is fully green — so a live fetch is impossible without a green
    review-status (LD-X08). ``replay`` / ``shadow`` run over ``fixture`` under the
    static transport and never touch the network. ``commit_chunk_size`` bounds
    the PG sink's per-transaction claim count (``None`` = the sink default, so
    ordinary sources commit in a single chunk — P26.18 / SOURCES.17).
    ``run_record_uri`` (live, PG sink) names the WORM run row the scheduled wrapper
    writes for this execution; it is recorded on the run and its completion.
    ``logical_run`` (live, PG sink; P31.4 / ADR-111) is the logical run key
    (source + cadence window): a restarted execution with the same key resumes an
    interrupted one instead of re-fetching everything. ``target_limit`` bounds a
    live run to its first N seed targets (a bounded slice; the run completes
    ``partial``).
    """
    mode = RunMode(mode)
    connector = _connector_for(source_id, connector_name)

    if mode is RunMode.LIVE:
        return _run_live(
            source_id,
            connector,
            sink_kind=sink_kind,
            dsn=dsn,
            capture_dir=capture_dir,
            wacz=wacz,
            code_commit=code_commit,
            commit_chunk_size=commit_chunk_size,
            run_record_uri=run_record_uri,
            logical_run=logical_run,
            target_limit=target_limit,
        )

    if fixture is None:
        raise ValueError(f"--fixture is required for {mode.value!r} mode (no live network)")
    return _run_over_fixture(
        source_id, connector, fixture, media_type=media_type, kind=kind, mode=mode
    )


def _run_live(
    source_id: str,
    connector: Connector,
    *,
    sink_kind: str,
    dsn: str | None,
    capture_dir: Path | None,
    wacz: bool,
    code_commit: str,
    commit_chunk_size: int | None = None,
    run_record_uri: str | None = None,
    logical_run: str | None = None,
    target_limit: int | None = None,
) -> SourceRunReport:
    # The gate is checked BEFORE any transport is constructed or any socket is
    # opened (SIG-INGEST-014/028): a non-green source is refused here.
    reasons = live_gate_reasons(source_id)
    if reasons:
        raise LiveGateRefused(source_id, reasons)

    # Real per-source fetch targets come from the declarative live-targets table
    # (P24.1 / ADR-082) — NOT a placeholder. A green source with no configured
    # target is refused here rather than fetching a bogus URL (SIG-INGEST-045i).
    from .live_targets import NoLiveTargets, live_targets

    targets = live_targets(source_id)
    if not targets:
        raise NoLiveTargets(source_id)

    # --- green-source live path -----------------------------------------------
    # The real HTTP transport + OCFL capture store, driven by the configured
    # targets through the shared politeness layer.
    from evidence.ocfl import OcflStore  # local import: heavy evidence deps
    from evidence.storage import LocalFileStore

    from .capture_ocfl import OcflCaptureStore
    from .transports import HttpxTransport

    version = getattr(connector, "version", "1.0.0")
    started = datetime.now(UTC)
    t0 = time.monotonic()
    # RATE-LIMIT HONESTY (P26.19): the SAM.gov sweep rides api.data.gov's daily
    # request quota, where a 429 means the window is EXHAUSTED — a back-off retry
    # is a re-probe that re-burns it (the recorded lesson; the P26.14 sweep's
    # retries wedged the run into a SIGKILL). So the SAM.gov live transport never
    # retries a 429: the first one surfaces immediately as a challenge and the
    # driver stops the sweep cleanly. Other sources (Overpass slot-exhaustion
    # etiquette) keep the default backoff-retry.
    transport = HttpxTransport(max_retries=0) if source_id == "sam_gov" else HttpxTransport()
    fetcher = PoliteFetcher(
        connector_name=connector.name, connector_version=version, transport=transport
    )
    # A target row may pin its host's minimum request interval — the reviewed
    # API budget declared on the row (e.g. OpenStates' 5/min for the 50-state
    # sweep, P26.11; the api_allowlist row is the reviewed source of it). The
    # politeness layer enforces it so a long bounded sweep never out-runs the
    # source's ToS rate; rate-limit/backoff events are still recorded.
    for _t in targets:
        _rpm = _t.get("rate_limit_per_min")
        if _rpm:
            fetcher.set_host_delay(urlsplit(str(_t["url"])).netloc, 60.0 / float(_rpm))
    capture_dir = capture_dir or Path(".sig/captures")
    store = OcflStore(LocalFileStore(str(capture_dir)))
    captures = OcflCaptureStore(store, capture_wacz=wacz)
    sink = make_claim_sink(
        sink_kind,
        dsn=dsn,
        connector_name=connector.name,
        connector_version=version,
        code_commit=code_commit,
        **_chunk_kwargs(commit_chunk_size),
        **({"run_record_uri": run_record_uri} if run_record_uri else {}),
        **({"logical_run": logical_run} if logical_run and sink_kind == "pg" else {}),
    )
    source = get(source_id)
    parameters: dict[str, Any] = {"targets": targets}
    if target_limit is not None:
        parameters["target_limit"] = int(target_limit)
    if source_id == "muckrock":
        parameters["muckrock_token_cache"] = _muckrock_token_cache(fetcher)
    if source_id == "sam_gov":
        # P26.19: bound the sweep to one daily quota window. The driver counts
        # every quota-governed slice against this budget and stops cleanly before
        # the 429 wall (headroom under the api.data.gov daily tier).
        from .procurement import sam_gov_daily_request_budget

        budget = sam_gov_daily_request_budget()
        if budget is not None:
            parameters["request_budget"] = budget
    # P31.4 / ADR-111: a PG run flushes each capture's claims as it goes, so it
    # keeps only the records its fetch record reports and the latest artifact per
    # stage — memory bounded by one capture, not the whole source.
    bounded = sink_kind == "pg"
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, version, code_commit, "r1", "v1", ()),
        fetcher=fetcher,
        captures=captures,
        claim_sink=sink,
        parameters=parameters,
        artifacts=ArtifactStore(keep_history=not bounded),
        retain_record=_retain_outcome_record if bounded else None,
    )
    try:
        report = run(connector, ctx)
    except ContentDrift as drift:
        # The fetch succeeded but the content no longer matches the parser's shape
        # (P25.1 / ADR-082): record the drift loud, never garbage, then
        # re-raise so the CLI exits non-zero.
        write_fetch_record(
            FetchRecord(
                source_id=source_id,
                connector=connector.name,
                mode=RunMode.LIVE.value,
                started_at=started.isoformat(),
                duration_seconds=time.monotonic() - t0,
                # P31.4: pages before the failing one may already have committed.
                claim_count=_flushed_records(sink),
                rate_limit_events=list(transport.rate_limit_events),
                robots_decisions=_robots_decisions(fetcher),
                robots_disregarded=[dict(d) for d in fetcher.robots_disregarded],
                content_drift=str(drift),
            ),
            capture_dir / "live_runs",
        )
        transport.close()
        raise
    except (RobotsUnretrievable, RobotsDisallowed) as exc:
        # GL-GATE-08 / ADR-088: PoliteFetcher never raises these — robots
        # verdicts are recorded (robots_disregarded), never enforced. This
        # path is retained for a non-standard fetcher that still refuses:
        # record the refusal loud, never bypass it, then re-raise so the CLI
        # exits non-zero.
        write_fetch_record(
            FetchRecord(
                source_id=source_id,
                connector=connector.name,
                mode=RunMode.LIVE.value,
                started_at=started.isoformat(),
                duration_seconds=time.monotonic() - t0,
                # P31.4: pages before the failing one may already have committed.
                claim_count=_flushed_records(sink),
                rate_limit_events=list(transport.rate_limit_events),
                robots_decisions=_robots_decisions(fetcher),
                robots_disregarded=[dict(d) for d in fetcher.robots_disregarded],
                politeness_refusal=f"{type(exc).__name__}: {exc}",
            ),
            capture_dir / "live_runs",
        )
        transport.close()
        raise
    fetch_record = FetchRecord(
        source_id=source_id,
        connector=connector.name,
        mode=RunMode.LIVE.value,
        started_at=started.isoformat(),
        duration_seconds=time.monotonic() - t0,
        capture_digests=[c.digest for c in report.captures],
        claim_count=report.claim_count,
        rate_limit_events=list(transport.rate_limit_events),
        robots_decisions=_robots_decisions(fetcher),
        robots_disregarded=[dict(d) for d in fetcher.robots_disregarded],
        refusals=[dict(r) for r in report.refusals],
        disappearances=[
            {
                "artifact_id": d.event.artifact_id,
                "failing_status": d.event.failing_status,
                "observed_at": d.event.observed_at.isoformat(),
            }
            for d in report.disappearances
        ],
        document_drift=[dict(d) for d in report.drifted],
        document_outcomes=[
            {
                "url": r.get("raw_value") or r.get("url"),
                "platform": r.get("platform"),
                "tenant_id": r.get("tenant_id"),
                "outcome": r.get("outcome"),
                "matched_terms": r.get("matched_terms"),
                "capture_digest": r.get("capture_digest"),
                **(
                    {
                        # P26.11 — the per-jurisdiction × per-family sweep
                        # outcome row (hits / empty; a persistent 429 lands on
                        # `disappearances` instead).
                        "jurisdiction": r.get("jurisdiction"),
                        "session": r.get("session"),
                        "query_family": r.get("query_family"),
                        "total_items": r.get("total_items"),
                        "returned_count": r.get("returned_count"),
                        "bills_indexed": r.get("bills_indexed"),
                        "bills_matched": r.get("bills_matched"),
                        "truncated": r.get("truncated"),
                        # P26.12 — the federal page's own fields (congress /
                        # page offset); absent for the state sweep.
                        "congress": r.get("congress"),
                        "page_offset": r.get("page_offset"),
                        "plan_version": r.get("plan_version"),
                    }
                    if r.get("record_kind") == "bill_query"
                    else {}
                ),
                **(
                    {
                        # P26.15 — the per-slice TED sweep outcome row (hits /
                        # empty / timed_out; a persistent 429 lands on
                        # `disappearances` instead, never re-probed).
                        "url": r.get("source_uri"),
                        "slice": (r.get("provenance") or {}).get("slice"),
                        "query_kind": (r.get("provenance") or {}).get("query_kind"),
                        "ted_keyword": (r.get("provenance") or {}).get("ted_keyword"),
                        "cpv_code": (r.get("provenance") or {}).get("cpv_code"),
                        "query": (r.get("provenance") or {}).get("query"),
                        "page": r.get("page"),
                        "limit": r.get("limit"),
                        "items_count": r.get("items_count"),
                        "total_notice_count": r.get("total_notice_count"),
                        "timed_out": r.get("timed_out"),
                        "truncated": r.get("truncated"),
                        "plan_version": r.get("plan_version"),
                    }
                    if r.get("record_kind") == "ted_eu_slice"
                    else {}
                ),
            }
            for r in report.claims
            if r.get("record_kind") in _OUTCOME_RECORD_KINDS
        ],
        # P26.19 — the quota-bounded sweep record: per-run request count, the
        # budget, and whether the run stopped at the budget or a 429 wall.
        sweep_requests=report.sweep_requests,
        sweep_budget=report.sweep_budget,
        budget_reached=report.budget_reached,
        quota_reached=report.quota_reached,
        sweep_skipped=[dict(s) for s in report.sweep_skipped],
        fetches=report.fetches,
        resumed=[dict(r) for r in report.resumed],
        logical_run=getattr(sink, "logical_run", None),
    )
    write_fetch_record(fetch_record, capture_dir / "live_runs")
    transport.close()
    return SourceRunReport(
        source_id=source_id,
        connector=connector.name,
        mode=RunMode.LIVE.value,
        claims=report.claims,
        captures=report.captures,
        asserted=report.asserted,
        fetch_record=fetch_record,
        refusals=list(report.refusals),
        disappearances=[
            {
                "artifact_id": d.event.artifact_id,
                "failing_status": d.event.failing_status,
                "observed_at": d.event.observed_at.isoformat(),
            }
            for d in report.disappearances
        ],
        drifted=list(report.drifted),
        run_id=getattr(sink, "run_id", None),
        claim_count=report.claim_count,
        fetches=report.fetches,
        resumed=[dict(r) for r in report.resumed],
    )


def _muckrock_token_cache(fetcher: PoliteFetcher) -> Any:
    """Build the refreshing MuckRock JWT cache for a live run (§23.5, F4.2/F4.3).

    The mint exchanges ``$SIG_MUCKROCK_REFRESH`` (a long-lived refresh token,
    HG-09 env-only) at the documented Squarelet ``/api/refresh/`` endpoint for a
    5-minute access JWT. The exchange itself rides the shared politeness layer —
    the accounts host is ADR-083 allow-listed, so the credential exchange is
    rate-limited and audited like every other egress. A missing refresh token is
    a loud configuration error, never a silent unauthenticated run.
    """
    import os

    from .records import MuckRockTokenCache, muckrock_config

    refresh = os.environ.get("SIG_MUCKROCK_REFRESH", "").strip()
    if not refresh:
        raise RuntimeError(
            "muckrock live run requires $SIG_MUCKROCK_REFRESH (the long-lived "
            "refresh token that mints the 5-minute api_v2 JWT, §23.5 F4.2/HG-09); "
            "without it the run would 401 on every data endpoint."
        )
    cfg = muckrock_config()
    refresh_url = str(cfg["token_refresh_url"])

    class _RefreshTokenSource:
        """Mints an access JWT by POSTing the refresh token through the fetcher."""

        def mint(self) -> str:
            result = fetcher.fetch(
                refresh_url,
                headers={"Content-Type": "application/json"},
                body=json.dumps({"refresh": refresh}).encode("utf-8"),
            )
            if result.status != 200:
                raise RuntimeError(
                    f"MuckRock token refresh returned HTTP {result.status}; the "
                    "access JWT was not minted (§23.5 F4.3) — check the credential."
                )
            return str(json.loads(result.body)["access"])

    return MuckRockTokenCache(_RefreshTokenSource())


# --- asserting replay (P31.6 / ADR-113) ---------------------------------------


@dataclass
class ReplayIngestReport:
    """The outcome of one :func:`replay_ingest` execution (P31.6 / ADR-113)."""

    source_id: str
    connector: str
    #: The new ``is_replay`` ingest_run this execution wrote under.
    run_id: str | None = None
    #: The original (live) runs whose capture marks this replay consumed.
    replayed_from_runs: tuple[str, ...] = ()
    #: Distinct persisted captures selected for reinterpretation.
    captures_considered: int = 0
    captures_replayed: int = 0
    #: Capture digests the DB names but the capture store does not hold —
    #  recorded loudly, never silently skipped.
    missing_captures: tuple[str, ...] = ()
    #: Claims the reinterpretation produced / handed to the sink.
    claims_produced: int = 0
    claims_asserted: int = 0
    #: The sink's exact insert/dedupe split (a re-run of the same captures on
    #  the same code is all ``duplicates`` — the +0 proof).
    claims_inserted: int = 0
    claims_duplicate: int = 0
    status: str = "ok"
    detail: str = ""


def replay_ingest(
    source_id: str,
    *,
    dsn: str,
    capture_dir: Path | str,
    run_ids: Sequence[str] | None = None,
    connector_name: str | None = None,
    code_commit: str = "unknown",
    run_record_uri: str | None = None,
    commit_chunk_size: int | None = None,
    replay_key: str | None = None,
) -> ReplayIngestReport:
    """Re-assert a source's persisted captures as a new ``is_replay`` run (P31.6).

    The named asserting reinterpretation (ADR-113): ``ingest_run_capture`` marks
    are the only DB link to real OCFL objects (ADR-111), so this selects exactly
    the capture digests a recorded execution flushed — ``--run-id`` rows, else
    every non-replay run of the source's logical-run prefix — resolves their
    bytes from the OCFL capture store (a mounted bucket on hosted), and runs the
    post-capture stages under network isolation through
    :func:`connectors.replay.asserting_replay`. NOTHING is fetched: a digest the
    store does not hold is reported ``missing_captures`` and skipped, never
    re-acquired (a source without persisted bytes waits for its next cadence
    run).

    The sink is a fresh ``is_replay`` :class:`PgClaimSink` whose run parameters
    name the replayed-from runs and whose ``ingest_run_capture`` marks record the
    original capture lineage under ``replay:``-prefixed target keys. Claims the
    spine already holds dedupe to +0; only claims the new code adds insert.
    """
    import psycopg  # lazy: the PG driver only loads on this hosted path
    from db.claim_sink import PgClaimSink, record_object_ref
    from evidence.ocfl import OcflStore
    from evidence.storage import LocalFileStore

    from .capture_ocfl import OcflCaptureStore
    from .replay import asserting_replay

    connector = _connector_for(source_id, connector_name)
    version = getattr(connector, "version", "1.0.0")
    conn = psycopg.connect(dsn, autocommit=True)
    if run_ids:
        rows = conn.execute(
            "SELECT c.run_id::text, c.target_key, c.capture_digest, c.source_uri,"
            " c.media_type, c.byte_size, c.retrieved_at"
            " FROM ingest_run_capture c"
            " WHERE c.run_id::text = ANY(%s::text[])"
            " ORDER BY c.run_id, c.target_key",
            (list(run_ids),),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT c.run_id::text, c.target_key, c.capture_digest, c.source_uri,"
            " c.media_type, c.byte_size, c.retrieved_at"
            " FROM ingest_run_capture c"
            " JOIN ingest_run r ON r.run_id = c.run_id"
            " WHERE r.connector_name = %s AND NOT r.is_replay"
            "   AND r.parameters ->> 'logical_run' LIKE %s"
            " ORDER BY c.run_id, c.target_key",
            (connector.name, f"{source_id}@%"),
        ).fetchall()

    # One entry per distinct capture digest: a re-fetched identical body marks
    # the same content-addressed object, and replaying it twice adds nothing.
    seen: set[str] = set()
    marks: list[dict[str, Any]] = []
    for run_id, target_key, digest, uri, media, size, retrieved in rows:
        if str(digest) in seen:
            continue
        seen.add(str(digest))
        marks.append(
            {
                "run_id": str(run_id),
                "target_key": str(target_key),
                "capture_digest": str(digest),
                "source_uri": str(uri),
                "media_type": str(media),
                "byte_size": int(size or 0),
                "retrieved_at": retrieved,
            }
        )
    replayed_from = sorted({m["run_id"] for m in marks})

    store = OcflStore(LocalFileStore(str(capture_dir)))
    captures = OcflCaptureStore(store)
    refs: list[CaptureRef] = []
    missing: list[str] = []
    marks_by_digest: dict[str, dict[str, Any]] = {}
    for mark in marks:
        ref = CaptureRef(
            digest=mark["capture_digest"],
            media_type=mark["media_type"],
            source_uri=mark["source_uri"],
            byte_size=mark["byte_size"],
            retrieved_at=mark["retrieved_at"],
        )
        marks_by_digest.setdefault(ref.digest, mark)
        if captures.has(ref.digest):
            refs.append(ref)
        else:
            missing.append(ref.digest)

    sink = PgClaimSink(
        conn,
        connector_name=connector.name,
        connector_version=version,
        code_commit=code_commit,
        is_replay=True,
        object_resolver=record_object_ref,
        run_record_uri=run_record_uri,
        # The replay run's own logical key scopes its lineage marks; live resume
        # never consumes them (resume_marks excludes is_replay runs, and the key
        # names a replay window, never a cadence window).
        logical_run=replay_key or f"{source_id}@replay-p31-6",
        extra_parameters={
            "replay_of_runs": ",".join(replayed_from),
            "replay_source": source_id,
        },
        **_chunk_kwargs(commit_chunk_size),
    )
    from .live_targets import live_targets

    ctx = RunContext(
        source=get(source_id),
        run=IngestRun(connector.name, version, code_commit, "r1", "v1", tuple(sorted(seen))),
        captures=captures,
        claim_sink=sink,
        # The replay never fetches; targets are declarative registry data (URLs +
        # file-kind metadata — never secrets, HG-09) a connector's post-capture
        # stages consult to resolve which reviewed target a stored capture came
        # from (audit file_kind, dot_511 registry rows). ``live_targets`` returns
        # ``[]`` for an unconfigured source and the connectors' registry-row
        # fallback then resolves the target, same as the fixture path.
        parameters={"targets": live_targets(source_id)},
        artifacts=ArtifactStore(keep_history=False),
    )

    def _mark_flushed(capture: CaptureRef, claims: list[dict[str, Any]]) -> None:
        mark = marks_by_digest[capture.digest]
        # The lineage mark names the ORIGINAL target key and capture digest, so
        # the replay run's ingest_run_capture rows point back at the live
        # execution's persisted evidence (ADR-113).
        sink.record_capture(
            f"replay:{mark['target_key']}",
            state="flushed",
            capture_digest=capture.digest,
            source_uri=capture.source_uri,
            media_type=capture.media_type,
            byte_size=capture.byte_size,
            retrieved_at=capture.retrieved_at,
            records=len(claims),
        )

    outcome = asserting_replay(connector, ctx, refs, on_capture=_mark_flushed)
    status = "ok" if not missing else "partial"
    detail = (
        f"{len(missing)} persisted capture digest(s) absent from the store — skipped"
        if missing
        else ""
    )
    sink.record_completion(status, source_id=source_id, detail=detail or None)
    return ReplayIngestReport(
        source_id=source_id,
        connector=connector.name,
        run_id=sink.run_id,
        replayed_from_runs=tuple(replayed_from),
        captures_considered=len(marks),
        captures_replayed=outcome.captures,
        missing_captures=tuple(sorted(missing)),
        claims_produced=outcome.claims,
        claims_asserted=outcome.asserted,
        claims_inserted=sink.report.inserted,
        claims_duplicate=sink.report.duplicates,
        status=status,
        detail=detail,
    )


def _run_over_fixture(
    source_id: str,
    connector: Connector,
    fixture: Path,
    *,
    media_type: str,
    kind: str,
    mode: RunMode,
) -> SourceRunReport:
    version = getattr(connector, "version", "1.0.0")
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    transport = _StaticFileTransport(fixture.read_bytes(), media_type)
    fetcher = PoliteFetcher(
        connector_name=connector.name,
        connector_version=version,
        transport=transport,
        # Static-transport replay/shadow: no socket is opened, so per-host
        # politeness sleeps must not burn real time across tenant fan-out.
        rate_limiter=RateLimiter(sleep=lambda _seconds: None),
    )
    targets: list[Mapping[str, Any]] = [{"id": "t1", "url": f"https://{source_id}/x", "kind": kind}]
    if kind == "oversight_report":
        # P31.12: a targeted report lookup resolves its reviewed live_targets row
        # (the synthetic fixture URL names no reviewed report). The static
        # transport serves the fixture bytes for the reviewed URL — fixture runs
        # never open a socket (SIG-INGEST-011).
        from .live_targets import live_targets

        targets = [dict(t) for t in live_targets(source_id)]
    ctx = RunContext(
        source=source,
        run=IngestRun(connector.name, version, "unknown", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=make_claim_sink("memory"),
        parameters={"targets": targets},
    )
    # Produce the fixture-encoded ("current") claim set + captures via the driver.
    fixture_report = run(connector, ctx)

    if mode is RunMode.REPLAY:
        replay_a = replay(connector, ctx, fixture_report.captures)
        replay_b = replay(connector, ctx, fixture_report.captures)
        return SourceRunReport(
            source_id=source_id,
            connector=connector.name,
            mode=mode.value,
            claims=replay_a,
            captures=fixture_report.captures,
            replay_reproducible=replay_fingerprint(replay_a) == replay_fingerprint(replay_b),
        )

    # SHADOW: diff a fresh replay against the fixture-encoded claim set. For an
    # unchanged parser over committed fixtures this is byte-identical => 0 diffs
    # (SIG-INGEST-019; the additive/back-compat invariant this ticket must hold).
    diff = shadow_replay(connector, ctx, fixture_report.captures, fixture_report.claims)
    return SourceRunReport(
        source_id=source_id,
        connector=connector.name,
        mode=mode.value,
        claims=fixture_report.claims,
        captures=fixture_report.captures,
        diff=diff,
    )


__all__ = [
    "CONNECTOR_FOR_SOURCE",
    "FetchRecord",
    "LIVE_RUNS_DIR",
    "LiveGateRefused",
    "ReplayIngestReport",
    "RunMode",
    "SourceRunReport",
    "is_review_status_green",
    "live_gate_reasons",
    "replay_ingest",
    "run_connector_over_fixture",
    "run_seed",
    "run_source",
    "write_fetch_record",
]

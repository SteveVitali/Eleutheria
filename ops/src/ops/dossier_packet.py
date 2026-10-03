# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Oklahoma City ``sig.dossier-packet/1`` builder (P32.18 / S2, SIG-DOS-003).

This module *authors the reviewed packet* — the input artifact the shared
``exports.research_dossier`` machinery composes into the OKC research dossier.
It forks none of the dossier machinery: packet composition, the six-state
answer vocabulary, the rubric, release validation and the ledger all stay in
``exports``; this module only gathers the reviewed records and the packet-level
declarations the machinery cannot infer.

Record provenance — every affirmative answer must cite committed bytes:

* The three ``dossier_okc`` documents (official usage page, council memo,
  contract amendment) are replayed through the real ``dossier_documents``
  connector over the committed stand-in fixtures — the emitted records are
  consumed verbatim (only the connector-transient ``claim_id``/``sys_period``
  are dropped).
* The ``ok_statute`` / ``okcpd_policy`` / ``okc_procurement`` shadow fixtures
  (P23.5 reviewed transcriptions) are replayed through their real document
  connectors; each emitted claim gets its reviewed ``dossier_field`` question
  assignment + ``document_id`` and one authored ``evidence_artifact`` row whose
  digest is the multihash of the committed fixture bytes (honestly labelled a
  transcription fixture, never a live capture).
* Journalism/council statements from the committed P06.1 evidence fixture
  (``okc_sources.json``) become authored claims carrying byte-range locators
  into the file, ``claim_directness=D6`` (a reported statement is never an
  instrument), and declared scopes — the corrected-seed interpretations
  (``ops.seed_correction``) so metro/city/owned/private/active never collapse.

Gate discipline: ``live_verification=false``. Nothing here fetches, flips a
source's rights posture, completes a human gate, or marks the independent
semantic review as anything but ``not_run`` (D-R10-HUMAN-1 OPEN). The bounded
live-capture obligations are recorded as a RETURN PASS packet
(:func:`live_return_pass`), owned by deferral ``D-P32.18-1``.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from db.claim_sink import content_digest
from evidence.digest import multihash
from exports.research_dossier import (
    CORRECTION_ROUTE,
    PACKET_SCHEMA,
    build_dossier,
    build_portfolio,
    render_dossier_print_html,
    render_portfolio_json,
    validate_packet,
)
from reconcile.count_scope import QUALIFIER_EVIDENCE_ORIGIN

from . import seed_correction

DOSSIER_ID = "okc-flock-alpr"
DEPLOYMENT = "sig:deployment:okc-okcpd-flock"
JURISDICTION = "us.state_abbr:OK"
#: The packet's as-of pair: after the announced 2026-10-01 retention change —
#: the effective date is a STATED date (announced), never operational evidence.
AS_OF_WORLD = "2026-10-02"
AS_OF_BELIEF = "2026-10-02"
_FIXTURE_RETRIEVED = datetime(2026, 10, 1, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

_REPO = Path(__file__).resolve().parents[3]
_DOSSIER_FIX = _REPO / "tests" / "connectors" / "fixtures" / "dossier"
_OKC_FIX = _REPO / "tests" / "connectors" / "fixtures" / "okc"
_PACK_FIX = _REPO / "tests" / "acceptance" / "fixtures" / "okc_sources.json"

#: doc_id → (fixture file, media type) for the dossier_okc targets — the
#: reviewed target row names the URL; the canned transport serves committed
#: stand-in bytes for it (SIG-INGEST-011 — never a real fetch).
_DOSSIER_FIXTURES: dict[str, tuple[str, str]] = {
    "okc-flock-usage-2026": ("okc_usage_page.html", "text/html"),
    "okc-council-memo-2026-08": ("okc_council_memo_2026.pdf", "application/pdf"),
    "okc-flock-amendment-2026": ("okc_amendment_1_2026.pdf", "application/pdf"),
}

#: The P23.5 shadow-fixture connectors whose emits join the packet
#: (procurement/policy/scoped UVED legal material): connector → fixture +
#: per-predicate dossier question assignments (the connectors emit no
#: ``dossier_field`` — the packet author makes the reviewed assignment).
_DOC_CONNECTORS: dict[str, dict[str, Any]] = {
    "okc_procurement": {
        "fixture": "okc_procurement.json",
        "fields": {
            "vendor_name": "q1",
            "product_name": "q2",
            "contract_number": "q5",
            "contract_amount": "q5",
            "quantity": "q3",
        },
    },
    "okcpd_policy": {
        "fixture": "okcpd_policy.json",
        "fields": {
            "sharing_restriction": "q8",
            "use_restriction": "q6",
        },
    },
    "ok_statute": {
        "fixture": "ok_statute.json",
        "fields": {
            "statutory_citation": "q6",
            "use_restriction": "q6",
        },
    },
}


# --------------------------------------------------------------------------- #
# Fixture replay (no network)
# --------------------------------------------------------------------------- #


class _MapTransport:
    """URL-keyed canned responses — no real network (SIG-INGEST-011)."""

    def __init__(self, responses: Mapping[str, tuple[bytes, str]]) -> None:
        self._responses = dict(responses)

    def robots(self, robots_url: str) -> Any:
        from connectors.net import RobotsResult

        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> Any:
        from connectors.stages import FetchResult

        if url in self._responses:
            payload, media = self._responses[url]
            return FetchResult(
                url=url, status=200, body=payload, media_type=media, retrieved_at=_FIXTURE_RETRIEVED
            )
        return FetchResult(
            url=url, status=404, body=b"", media_type="text/plain", retrieved_at=_FIXTURE_RETRIEVED
        )


def _fetcher(name: str, transport: Any) -> Any:
    from connectors.net import PoliteFetcher, RateLimiter

    return PoliteFetcher(
        connector_name=name,
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda _s: None),
    )


def _strip_transient(record: Mapping[str, Any]) -> dict[str, Any]:
    """Drop the connector-transient ids the pipeline mints — the packet keeps
    only the reproducible record payload (digests never cover them anyway)."""
    return {k: v for k, v in record.items() if k not in ("claim_id", "sys_period")}


def _dossier_records() -> list[dict[str, Any]]:
    """Replay the three ``dossier_okc`` targets through the real connector."""
    from connectors.dossier_documents import DossierDocumentsConnector
    from connectors.live_targets import live_targets
    from connectors.pipeline import run
    from connectors.registry import CompactStatus, get
    from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
    from evidence.ingest_run import IngestRun

    source_id = "dossier_okc"
    targets = copy.deepcopy(list(live_targets(source_id)))
    responses: dict[str, tuple[bytes, str]] = {}
    for target in targets:
        doc_id = str(target.get("doc_id") or target.get("id"))
        name, media = _DOSSIER_FIXTURES[doc_id]
        responses[str(target["url"])] = ((_DOSSIER_FIX / name).read_bytes(), media)
    # The documented fixture-runner carve-out: the registry row itself stays
    # ingestion_permitted=false (D-R10-SOURCES-1 OPEN); the in-memory flip is a
    # replay posture only — never a rights decision.
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    ctx = RunContext(
        source=source,
        run=IngestRun("dossier_documents", "1.0.0", "p32.18-packet", "r1", "v1", ()),
        fetcher=_fetcher("dossier_documents", _MapTransport(responses)),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    report = run(DossierDocumentsConnector(), ctx)
    return [_strip_transient(r) for r in report.claims]


def _document_records() -> list[dict[str, Any]]:
    """Replay the three P23.5 shadow-fixture connectors; adapt emits into
    packet records (document_id + reviewed dossier_field) plus one authored
    evidence_artifact row per fixture — the digest is over the committed
    transcription bytes, honestly labelled, never a live-capture claim."""
    from connectors.pipeline import run
    from connectors.registry import get
    from connectors.stages import (
        InMemoryCaptureStore,
        InMemoryClaimSink,
        RunContext,
        registered_connectors,
    )
    from evidence.ingest_run import IngestRun

    records: list[dict[str, Any]] = []
    for name, spec in _DOC_CONNECTORS.items():
        fixture = _OKC_FIX / str(spec["fixture"])
        body = fixture.read_bytes()
        parsed = json.loads(body)
        doc = parsed["documents"][0]
        doc_id = str(doc["id"])
        source = dataclasses.replace(get(name), ingestion_permitted=True)
        ctx = RunContext(
            source=source,
            run=IngestRun(name, "1.0.0", "p32.18-packet", "r1", "v1", ()),
            fetcher=_fetcher(
                name, _MapTransport({f"https://{name}/x": (body, "application/json")})
            ),
            captures=InMemoryCaptureStore(),
            claim_sink=InMemoryClaimSink(),
            parameters={"targets": [{"id": "t1", "url": f"https://{name}/x", "kind": "doc"}]},
        )
        connector = registered_connectors()[name]()
        report = run(connector, ctx)
        for raw in report.claims:
            claim = _strip_transient(raw)
            pred = str(claim.get("predicate_id") or "")
            claim["dossier_field"] = spec["fields"].get(pred)
            claim["document_id"] = doc_id
            if pred == "quantity":
                # The contract's unit count declares its universe: contracted
                # units are not active sensors (same rule as the seed fix).
                claim["qualifiers"] = [
                    {"qualifier_id": "count_scope", "value": "city_limits"},
                    {"qualifier_id": "count_scope_detail", "value": "contracted_units"},
                    {"qualifier_id": QUALIFIER_EVIDENCE_ORIGIN, "value": "shadow_fixture"},
                ]
            records.append(claim)
        records.append(
            _fixture_artifact(
                doc_id=doc_id,
                fixture_bytes=body,
                source_url=str(doc["source_url"]),
                retrieved_date=str(doc.get("retrieved_date", "2026-09-01")),
                connector=name,
                genre=str(doc.get("genre") or "document"),
            )
        )
    return records


def _fixture_artifact(
    *,
    doc_id: str,
    fixture_bytes: bytes,
    source_url: str,
    retrieved_date: str,
    connector: str,
    genre: str,
) -> dict[str, Any]:
    """An evidence_artifact row over a committed fixture — labelled so no
    reader mistakes the stand-in bytes for a live capture (D-R10-SOURCES-1)."""
    return {
        "record_kind": "evidence_artifact",
        "connector": connector,
        "document_id": doc_id,
        "capture_digest": multihash(fixture_bytes),
        "byte_size": len(fixture_bytes),
        "media_type": "application/json",
        "method": "fixture_transcription",
        "access_mode": "committed_fixture",
        "capture_kind": "shadow_transcription_fixture",
        "source_uri": source_url,
        "source_id": connector,
        "retrieved_date": retrieved_date,
        "evidence_genre": genre,
        "sensitivity_class": "C1",
        "note": (
            "digest is over the committed reviewed-transcription fixture bytes, "
            "not a live capture — D-R10-SOURCES-1 owns the actual-fetch obligation"
        ),
    }


# --------------------------------------------------------------------------- #
# Authored journalism/council/seed records over the P06.1 evidence fixture
# --------------------------------------------------------------------------- #

_PACK_DOC_ID = "okc-p06-evidence-fixture"
_PACK_RETRIEVED = "2026-09-01"


def _pack_bytes() -> bytes:
    return _PACK_FIX.read_bytes()


def _locator(literal: str) -> dict[str, Any]:
    """A byte-range locator over the committed fixture — every cited literal
    must really occur in the bytes (a missing literal fails closed)."""
    data = _pack_bytes()
    needle = literal.encode("utf-8")
    start = data.find(needle)
    if start < 0:
        raise ValueError(f"literal not present in {_PACK_FIX.name}: {literal!r}")
    if data.find(needle, start + 1) >= 0:
        raise ValueError(f"literal not unique in {_PACK_FIX.name}: {literal!r}")
    return {"kind": "byte_range", "start": start, "end": start + len(needle)}


def _pack_claim(
    *,
    predicate: str,
    value: Any,
    literal: str,
    source_url: str,
    source_id: str,
    genre: str,
    observed_at: str,
    dossier_field: str,
    rationale: str,
    directness: str | None = "D6",
    qualifiers: list[dict[str, Any]] | None = None,
    subject_id: str = DEPLOYMENT,
    valid_from: str | None = None,
    valid_to: str | None = None,
) -> dict[str, Any]:
    """One authored packet claim cited to a fixture byte range."""
    claim: dict[str, Any] = {
        "record_kind": "claim",
        "connector": "ops.dossier_packet",
        "source_id": source_id,
        "source_attribution": source_id,
        "document_genre": genre,
        "evidence_genre": genre,
        "dossier_field": dossier_field,
        "document_id": _PACK_DOC_ID,
        "subject_id": subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": literal,
        "assertion_rationale": rationale,
        "evidence": {
            "source_url": source_url,
            "retrieved_date": _PACK_RETRIEVED,
            "extraction_method": "fixture_transcription",
            "locator": _locator(literal),
        },
        "observed_at": observed_at,
        "sensitivity_class": "C1",
        "geo_tier": 0,
    }
    if directness:
        claim["claim_directness"] = directness
    if qualifiers:
        claim["qualifiers"] = qualifiers
    if valid_from:
        claim["valid_from"] = valid_from
    if valid_to:
        claim["valid_to"] = valid_to
    return claim


_JOURNALRECORD = "src:journalrecord"
_COUNCIL = "src:okc-council"
_OKLAHOMAN = "src:oklahoman"
_KGOU_URL = (
    "https://www.kgou.org/politics-and-government/2026-08-19/"
    "oklahoma-city-council-renews-license-plate-reader-contract-despite-pushback"
)
_JR_URL = (
    "https://journalrecord.com/2026/08/18/okc-council-votes-keep-flock-cameras-privacy-concerns/"
)
_OKM_URL = (
    "https://www.oklahoman.com/story/news/local/2026/08/03/"
    "okc-council-will-vote-on-police-contract-for-flock-cameras/90958514007/"
)
_DEFLOCK_URL = "https://deflockokc.com/"
_CONTRACT_URL = "https://deflockokc.com/the-case.html"


def _pack_records() -> list[dict[str, Any]]:
    """Journalism/council statements + the corrected-seed claims."""
    records: list[dict[str, Any]] = []
    # --- journalism / council statements (D6 — reported, never instruments) --
    records.append(
        _pack_claim(
            predicate="buyer",
            value="City of Oklahoma City",
            literal="the city's contract with ALPR vendor Flock Safety",
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q1",
            rationale=(
                "council record names the buying party — a journalism-reported "
                "statement (D6), corroborated by the procurement record"
            ),
        )
    )
    records.append(
        _pack_claim(
            predicate="technology",
            value="automatic license plate reader (ALPR), fixed camera network",
            literal="90 active ALPR cameras operated under the OKCPD contract",
            source_url=_OKM_URL,
            source_id=_OKLAHOMAN,
            genre="news_article",
            observed_at="2026-08-03",
            dossier_field="q2",
            rationale=(
                "the deployed technology class as the journalism states it — "
                "fixed ALPR, distinct from vehicle-mounted readers"
            ),
        )
    )
    records.append(
        _pack_claim(
            predicate="pooled_lookup_participation",
            value="nationwide sharing platform — removal announced 2026-08-18",
            literal="removing its data from a nationwide sharing platform",
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q4",
            rationale=(
                "the stated external-access change: announced withdrawal from the "
                "vendor's pooled/nationwide lookup network — a stated intent, "
                "never an observed removal"
            ),
        )
    )
    records.append(
        _pack_claim(
            predicate="data_system_scope",
            value="vendor_cloud_shared — stated national network (5,000+ agencies claimed)",
            literal=(
                "Flock's network spans more than 5,000 agencies and 100,000 "
                "cameras sharing data nationwide"
            ),
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q4",
            rationale=(
                "the hosted/pooled system's declared reach — a network-scope "
                "statement, never a count of OKC's deployment"
            ),
        )
    )
    records.append(
        _pack_claim(
            predicate="sharing_restriction",
            value=(
                "the amendment gives Oklahoma City sole power to share data with federal agencies"
            ),
            literal=(
                "an amendment that gives Oklahoma City, rather than Flock, "
                "the sole power to share data with federal agencies"
            ),
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q8",
            rationale=(
                "the journalism's actor-scoped reading: the restriction binds "
                "one party's disclosure — it is not a prohibition on every "
                "City-authorized share"
            ),
        )
    )
    records.append(
        _pack_claim(
            predicate="written_policy_value",
            value=("retention period reduced from 30 days to 7 days (stated 2026-08-18)"),
            literal="reducing the data retention period from 30 to 7 days",
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q7",
            rationale=(
                "the announced retention change as a stated transition — kept "
                "verbatim so the announced effective date stays a stated date"
            ),
        )
    )
    records.append(
        _pack_claim(
            predicate="contract_end_date",
            value="2027-06-30",
            literal=(
                "The one-year renewal runs through 2027-06-30 and returns to "
                "the council before another renewal"
            ),
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q9",
            rationale="the stated renewal horizon — a stated date, never an observed end",
        )
    )
    records.append(
        _pack_claim(
            predicate="authorization_state",
            value="renewal approved 5–3 by council vote 2026-08-18, public opposition on record",
            literal="council members Cooper, Hamon, and Pennington voted no after public comment",
            source_url=_KGOU_URL,
            source_id=_COUNCIL,
            genre="council_minutes",
            observed_at="2026-08-19",
            dossier_field="q10",
            rationale=(
                "the oversight body's recorded institutional response — the vote "
                "split and the opposition are stated facts, not findings"
            ),
        )
    )
    # --- the corrected-seed count claims (q3) — identical interpretation to
    # the correction packet's replacement records; cited to the fixture. ----
    pkt = seed_correction.correction_packet()
    fixups = {
        "deflock-299-metro-scope": {
            "literal": "299 across the OKC metro area",
            "source_url": _DEFLOCK_URL,
            "genre": "community_map",
        },
        "okc-council-190-derived-not-sourced": {
            "literal": "businesses own around 100 within city limits",
            "source_url": _JR_URL,
            "genre": "news_article",
        },
        "okc-council-90-active-scope": {
            "literal": "OKCPD has 90 cameras",
            "source_url": _JR_URL,
            "genre": "official_statement",
        },
        "contract-90-scope": {
            "literal": "a year for 90 cameras",
            "source_url": _CONTRACT_URL,
            "genre": "contract",
        },
        "osm-31-metro-scope": None,  # ODbL compartment claim — kept out of the CC-BY pack
    }
    for correction in pkt["corrections"]:
        cid = str(correction["correction_id"])
        fix = fixups[cid]
        if fix is None:
            continue
        repl = dict(correction["replacement_records"][0])
        claim = _pack_claim(
            predicate=str(repl["predicate_id"]),
            value=repl["value"],
            literal=str(fix["literal"]),
            source_url=str(fix["source_url"]),
            source_id=str(repl["source_id"]),
            genre=str(fix["genre"]),
            observed_at=str(repl["observed_at"]),
            dossier_field="q3",
            rationale=str(repl["assertion_rationale"]),
            directness=repl.get("claim_directness"),
            qualifiers=[dict(q) for q in repl.get("qualifiers") or ()],
        )
        claim["spdx"] = repl.get("spdx")
        records.append(claim)
    # --- the pack's own evidence_artifact row ------------------------------
    records.append(
        _fixture_artifact(
            doc_id=_PACK_DOC_ID,
            fixture_bytes=_pack_bytes(),
            source_url=_CONTRACT_URL,
            retrieved_date=_PACK_RETRIEVED,
            connector="ops.dossier_packet",
            genre="evidence_fixture",
        )
    )
    return records


# --------------------------------------------------------------------------- #
# Packet composition
# --------------------------------------------------------------------------- #


def packet_records() -> list[dict[str, Any]]:
    """Every record the reviewed packet carries, in stable order."""
    return _dossier_records() + _document_records() + _pack_records()


def _digest_of(records: Sequence[Mapping[str, Any]], predicate: str, scope: str) -> str:
    for r in records:
        if r.get("record_kind") != "claim" or r.get("predicate_id") != predicate:
            continue
        for q in r.get("qualifiers") or ():
            if (
                str(q.get("qualifier_id") or q.get("predicate")) == "count_scope"
                and str(q.get("value")) == scope
            ):
                return content_digest(r)
    raise ValueError(f"no {predicate} claim at scope {scope!r} in the packet")


def _search_entry(
    question: str, sources: list[str], note: str, outcome: str = "found"
) -> dict[str, Any]:
    return {
        "question": question,
        "outcome": outcome,
        "sources_searched": sources,
        "searched_at": AS_OF_WORLD,
        "note": note,
    }


_DOCS = ["okc-flock-usage-2026", "okc-council-memo-2026-08", "okc-flock-amendment-2026"]
_SHADOW = ["okc-statute-47-7-606-1", "okc-ops-manual-5-118", "okc-contract-c241032"]


def build_packet() -> dict[str, Any]:
    """The reviewed ``sig.dossier-packet/1`` for the OKC pilot dossier."""
    records = packet_records()
    active90 = _digest_of(records, "active_device_count", "city_limits")
    private100 = _digest_of(records, "claimed_device_count", "city_limits")
    derived = seed_correction.correction_packet()["derived_labels"][0]
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "dossier_id": DOSSIER_ID,
        "subject": {
            "slug": DOSSIER_ID,
            "label": "Oklahoma City — OKCPD Flock Safety ALPR program",
            "jurisdiction": "Oklahoma City, Oklahoma (us.state_abbr:OK)",
            "entity_id": DEPLOYMENT,
            "jurisdiction_slug": "oklahoma-city-ok",
        },
        "as_of": {"world": AS_OF_WORLD, "belief": AS_OF_BELIEF},
        "records": records,
        "declared": {
            "derived": [
                {
                    "question": "q3",
                    "method": (
                        "reconcile.count_scope.derive_approximate_sum over the two "
                        "disjoint city_limits claims (agency-operated 90 + "
                        "privately-owned ~100)"
                    ),
                    "value": derived["view"],
                    "inputs": [active90, private100],
                    "note": (
                        "'~190' is a DERIVED approximate city-limits total — never "
                        "a sourced figure. Inputs are disjoint sub-populations; "
                        "double-counting is possible and recorded as an assumption."
                    ),
                }
            ],
            "partial": [
                {
                    "question": "q6",
                    "rationale": (
                        "authority/applicability is traceable but unresolved: 47 O.S. "
                        "§7-606.1 constrains the UVED insurance-enforcement program; "
                        "whether it binds OKCPD's Flock use is unverified — the city "
                        "page alone cannot support that legal conclusion, and the "
                        "manual's §5-118 scope is vehicle-mounted readers"
                    ),
                },
                {
                    "question": "q8",
                    "rationale": (
                        "the 109 figure is an aggregate partner-agency degree — the "
                        "roster itself was refused on record ('No, ma'am'); mode and "
                        "per-agency scope stay partial"
                    ),
                },
            ],
        },
        "search_log": [
            _search_entry(
                "q1",
                ["okc-contract-c241032", _PACK_DOC_ID],
                "buyer/vendor named by the procurement record + council report",
            ),
            _search_entry(
                "q2",
                _DOCS + [_PACK_DOC_ID],
                "technology class from the usage page + journalism (fixed ALPR)",
            ),
            _search_entry(
                "q3",
                _DOCS + _SHADOW + [_PACK_DOC_ID],
                "count universe partitioned: metro community map / city-owned official "
                "/ private journalism / contracted units — different scopes, co-visible",
            ),
            _search_entry(
                "q4",
                [_PACK_DOC_ID, "okc-flock-usage-2026"],
                "external access stated: nationwide sharing platform + withdrawal "
                "announcement — configured access, never local hardware ownership",
            ),
            _search_entry(
                "q5",
                _DOCS + ["okc-contract-c241032"],
                "renewal funding $270,000 + covered period + unsigned-signature field "
                "states recorded (execution unverified)",
            ),
            _search_entry(
                "q6",
                _SHADOW + ["okc-flock-amendment-2026"],
                "statute + manual scope + amendment precedence captured; "
                "applicability to the Flock program deliberately partial",
            ),
            _search_entry(
                "q7",
                _DOCS + [_PACK_DOC_ID],
                "city page states 7-day retention effective 2026-10-01 with the "
                "investigation exception preserved verbatim",
            ),
            _search_entry(
                "q8",
                _DOCS + _SHADOW + [_PACK_DOC_ID],
                "109 partner agencies (aggregate degree), the refused roster, the "
                "actor-scoped federal-disclosure restriction + law-enforcement-only "
                "policy lane",
            ),
            _search_entry(
                "q9",
                _DOCS + [_PACK_DOC_ID],
                "lifecycle labels, posted/as-of dates and the stated renewal horizon "
                "— publication/effective/as-of kinds kept distinct",
            ),
            _search_entry(
                "q10",
                [_PACK_DOC_ID, "okc-council-memo-2026-08"],
                "the council's recorded response (5–3 vote, public opposition) — "
                "no audit/oversight report exists in the evidence pack",
            ),
        ],
        "follow_ups": [
            {
                "question": "q5",
                "action": (
                    "capture the executed signature pages of Amendment 1 to "
                    "C241032 in the bounded live pass"
                ),
                "closing_condition": (
                    "captured bytes show both parties' signature/date blocks, or "
                    "a recorded absence keeps execution unverified"
                ),
            },
            {
                "question": "q6",
                "action": (
                    "obtain the UVED program's applicability determination — "
                    "whether 47 O.S. §7-606.1 constrains OKCPD's Flock program "
                    "or only the DAC insurance-enforcement program it governs"
                ),
                "closing_condition": (
                    "an authoritative instrument or agency statement ties the "
                    "statute to OKCPD Flock use (or bounds it), reviewed under HG-03"
                ),
            },
            {
                "question": "q7",
                "action": (
                    "re-capture the official usage page after the stated 2026-10-01 "
                    "retention effective date"
                ),
                "closing_condition": (
                    "captured bytes show the implemented retention rule (the "
                    "announced change observed operating) or the stated text "
                    "remains announced-only"
                ),
            },
            {
                "question": "q8",
                "action": (
                    "obtain the partner-agency roster and sharing mode for the "
                    "109-degree aggregate (refused on record)"
                ),
                "closing_condition": (
                    "a captured roster/mode document, or a persisted recorded refusal"
                ),
            },
            {
                "question": "q10",
                "action": (
                    "search council audit/PAB/CCOPS oversight corpora for any "
                    "review of the ALPR program"
                ),
                "closing_condition": (
                    "an oversight artifact is captured, or the search's absence "
                    "is documented with named sources"
                ),
            },
        ],
        "restricted": [],
        "review": {
            "status": "not_run",
            "note": (
                "no independent reviewer exists on this build — D-R10-HUMAN-1 "
                "OPEN; the mark is honest, never fabricated"
            ),
        },
        "correction_route": CORRECTION_ROUTE,
        "seed_correction_packet": seed_correction.PACKET_ID,
        "notes": [
            "live_verification=false: every record replays committed fixture bytes; "
            "no live fetch, no rights flip, no gate completion",
            "the official page's '90 readers' is city-OWNED; journalism's '90 active' "
            "and the contract's '90 cameras' are different predicates/scopes — kept "
            "distinct, never collapsed",
            "the UVED statute is scoped legal material: it governs the insurance-"
            "enforcement program; application to OKCPD Flock use stays unresolved",
        ],
    }
    return packet


# --------------------------------------------------------------------------- #
# The evidence pack + the bounded live RETURN PASS packet
# --------------------------------------------------------------------------- #


def evidence_pack_markdown(packet: Mapping[str, Any] | None = None) -> str:
    """The reviewed evidence pack — one row per document: capture availability,
    digest/signature state, rights posture, and what the document supports."""
    pkt = packet or build_packet()
    captures = {
        str(r["document_id"]): r
        for r in pkt["records"]
        if r.get("record_kind") == "evidence_artifact"
    }
    claims = [r for r in pkt["records"] if r.get("record_kind") == "claim"]
    by_doc: dict[str, list[Mapping[str, Any]]] = {}
    for c in claims:
        by_doc.setdefault(str(c.get("document_id")), []).append(c)
    lines = [
        "<!-- SPDX-License-Identifier: Apache-2.0 -->",
        "# P32.18 — Oklahoma City dossier evidence pack (offline)",
        "",
        f"Packet `{pkt['schema']}` / dossier `{pkt['dossier_id']}` — as-of "
        f"{pkt['as_of']['world']} (world) / {pkt['as_of']['belief']} (belief). "
        "Every row names the bytes the claims were read from and how those bytes "
        "were obtained. `live_verification=false`: nothing below is a live capture.",
        "",
        "| document | bytes | capture digest (multihash) | how obtained | claims |",
        "|---|---|---|---|---|",
    ]
    for doc_id in sorted(captures):
        cap = captures[doc_id]
        n = len(by_doc.get(doc_id, ()))
        lines.append(
            f"| `{doc_id}` | {cap.get('byte_size')} | "
            f"`{str(cap.get('capture_digest'))[:32]}…` | "
            f"{cap.get('method')} / {cap.get('access_mode')} | {n} |"
        )
    lines += [
        "",
        "## Document inventory and what each supports",
        "",
        "| document | kind | what the packet takes from it |",
        "|---|---|---|",
        "| `okc-flock-usage-2026` | official city page (HTML stand-in) | 90 city-owned "
        "readers; 109 partner agencies (aggregate degree); 7-day retention effective "
        "2026-10-01; the ongoing-investigation exception |",
        "| `okc-council-memo-2026-08` | council/governance document (PDF stand-in) | "
        "Amendment 1 / Renewal 3; $270,000 for Jul 2026–Jun 2027; posted 2026-08-18 — "
        "a governance record, NOT executed-contract evidence |",
        "| `okc-flock-amendment-2026` | amendment text (PDF stand-in) | actor-scoped "
        "federal-disclosure restriction + compulsory-process exception; precedence "
        "over the Agreement; `signed_date`/`execution_state` recorded "
        "`present_but_empty` — execution is unverified, never inferred |",
        "| `okc-statute-47-7-606-1` | committed transcription fixture (ok_statute) | "
        "47 O.S. §7-606.1 — insurance-enforcement restriction scoped to the UVED "
        "program; NOT generalized to the OKCPD Flock program |",
        "| `okc-ops-manual-5-118` | committed transcription fixture (okcpd_policy) | "
        "sharing restriction + the manual's own scope (vehicle-mounted readers) — "
        "policy evidence, applicability recorded |",
        "| `okc-contract-c241032` | committed transcription fixture (okc_procurement) | "
        "vendor Flock Safety; contract C241032; $270,000/yr; 90 units |",
        f"| `{_PACK_DOC_ID}` | P06.1 committed evidence fixture | journalism/council "
        "statements (D6) + the corrected-seed scope partition — DeFlock 299 metro, "
        "the chief ~100 private city-limits, 90 active agency-operated, ~190 derived |",
        "",
        "## Digest, signature and temporal uncertainty (recorded, not resolved)",
        "",
        "- `signed_date` and `execution_state` on the amendment are "
        "`present_but_empty`: a partially-evidenced signature block means "
        "execution is unknown — the packet asserts neither signing nor execution.",
        "- The council memo's original-approval references are internally "
        "inconsistent; the packet keeps the lifecycle label verbatim and asserts "
        "no reconciled original date.",
        "- The 7-day retention rule is a STATED rule with a stated effective date "
        "(2026-10-01). As-of " + AS_OF_WORLD + " the change is announced; "
        "operational implementation is unverified (follow-up in the packet).",
        "- Retrieval/capture dates (fixture replay 2026-10-01) are kept distinct "
        "from stated valid dates on every claim.",
        "",
        "## Rights, review and acquisition posture",
        "",
        "- `dossier_okc` stays `ingestion_permitted=false` (D-R10-SOURCES-1 OPEN): "
        "the three documents replayed committed stand-ins; the URLs are reviewed "
        "targets, not captured bytes. The OKC shadow fixtures are reviewed "
        "transcriptions, not live captures.",
        "- Journalism is `claim_directness=D6` — reported statements, never "
        "instruments; council materials are governance records, never "
        "executed-contract evidence.",
        "- Independent semantic review: `not_run` — D-R10-HUMAN-1 OPEN. "
        "Mechanical completeness is reported separately from pilot completion.",
        "- The ODbL OSM compartment stays separate; its seed row is scope-labelled "
        "by the correction packet and is not part of this CC-BY pack.",
        "",
        "## Follow-up / RETURN PASS",
        "",
        "Bounded live obligations are recorded in `LIVE_RETURN_PASS.json` "
        "(deferral `D-P32.18-1`): actual byte captures of the six reviewed URLs, "
        "the amendment signature pages, the post-effective retention page, the "
        "OSCN statutory version, the purchasing index (WAF-gated) — all behind "
        "HG-03, no rights flip, no gate completion.",
        "",
    ]
    return "\n".join(lines)


LIVE_PASS_SCHEMA = "sig.dossier-live-return-pass/1"


def live_return_pass() -> dict[str, Any]:
    """The bounded live-capture stage the offline packet defers (D-P32.18-1).

    Prepared, never executed: it names the exact targets and the bounded
    questions a later HG-03-cleared pass answers, and forbids every shortcut
    (no rights flip, no gate completion, no publication)."""
    dossier_targets = []
    from connectors.live_targets import live_targets

    for target in live_targets("dossier_okc"):
        dossier_targets.append(
            {
                "doc_id": str(target.get("doc_id") or target.get("id")),
                "url": str(target["url"]),
                "kind": "clause_fields",
                "goal": "actual byte capture replacing the committed stand-in",
            }
        )
    extra = [
        {
            "doc_id": "okc-statute-47-7-606-1",
            "url": "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=478582",
            "kind": "document_page",
            "goal": "verify the effective statutory version on the live OSCN page",
        },
        {
            "doc_id": "okc-ops-manual-5-118",
            "url": (
                "https://www.okc.gov/files/assets/city/v/2/police/documents/"
                "operations-manual-6th-edition-june-15-2026.pdf"
            ),
            "kind": "document_page",
            "goal": "capture the 6th-edition manual §5-118 pages (real PDF)",
        },
        {
            "doc_id": "okc-purchasing-index",
            "url": "https://www.okc.gov/departments/finance/purchasing",
            "kind": "document_page",
            "goal": (
                "locate the executed-contract record for C241032 "
                "(edge WAF may refuse — record the refusal)"
            ),
        },
    ]
    return {
        "schema": LIVE_PASS_SCHEMA,
        "packet_id": "okc-dossier-live-pass",
        "status": "prepared_not_executed",
        "deferral": "D-P32.18-1",
        "reason_deferred": (
            "live_verification=false: D-R10-SOURCES-1 stays OPEN — source/evidence-use "
            "review and the HG-03 rights decision are pending"
        ),
        "targets": dossier_targets + extra,
        "bounded_questions": [
            "actual bytes of the usage page — do the 90/109/retention claims match",
            "the amendment's signature/execution state on real captured pages",
            "the post-2026-10-01 retention rule operating (announced vs implemented)",
            "the purchasing index route to the executed C241032 instrument",
            "the OSCN statutory version effective for the UVED program window",
        ],
        "preconditions": [
            "HG-03 source/rights review per target (published-URL ownership screen)",
            "Part VIII preflight — no plate/trip/person data is ever captured",
            "resource bounds identical to the replay path (2 protocols, page/byte caps)",
        ],
        "non_goals": [
            "no source rights flip inside this packet",
            "no operator-gate completion",
            "no publication or public release",
        ],
    }


# --------------------------------------------------------------------------- #
# Artifact writer
# --------------------------------------------------------------------------- #

ARTIFACT_NAMES = {
    "packet": "okc_dossier_packet.json",
    "dossier": "okc_dossier.json",
    "portfolio": "okc_dossier_portfolio.json",
    "print": "okc_dossier.print.html",
    "correction_packet": "okc_seed_correction_packet.json",
    "evidence_pack": "EVIDENCE_PACK.md",
    "live_pass": "LIVE_RETURN_PASS.json",
}


def write(out_dir: Path) -> dict[str, Path]:
    """Emit the whole P32.18 artifact set into ``out_dir`` (deterministic)."""
    packet = build_packet()
    problems = validate_packet(packet)
    if problems:
        raise ValueError(f"packet validation failed: {problems}")
    dossier = build_dossier(packet)
    portfolio = build_portfolio([packet])
    out_dir.mkdir(parents=True, exist_ok=True)
    out: dict[str, Path] = {}
    blobs = {
        "packet": (
            json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode(),
        "dossier": (
            json.dumps(dossier, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode(),
        "portfolio": render_portfolio_json(portfolio),
        "print": render_dossier_print_html(dossier).encode("utf-8"),
        "correction_packet": seed_correction.render_packet_json(
            seed_correction.correction_packet()
        ),
        "evidence_pack": evidence_pack_markdown(packet).encode("utf-8"),
        "live_pass": (
            json.dumps(live_return_pass(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode(),
    }
    for key, blob in blobs.items():
        path = out_dir / ARTIFACT_NAMES[key]
        path.write_bytes(blob)
        out[key] = path
    return out


__all__ = [
    "DOSSIER_ID",
    "DEPLOYMENT",
    "AS_OF_WORLD",
    "build_packet",
    "packet_records",
    "evidence_pack_markdown",
    "live_return_pass",
    "write",
    "ARTIFACT_NAMES",
    "LIVE_PASS_SCHEMA",
]

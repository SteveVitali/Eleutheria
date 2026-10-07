# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The San Diego ``sig.dossier-packet/1`` builder (P32.20 / S2, SIG-DOS-005).

This module *authors the reviewed packet* — the input artifact the shared
``exports.research_dossier`` machinery composes into the San Diego research
dossier. It forks none of the dossier machinery: packet composition, the
six-state answer vocabulary, the rubric, release validation and the ledger
all stay in ``exports``; this module only gathers the reviewed records and
the packet-level declarations the machinery cannot infer.

Record provenance — every affirmative answer must cite committed bytes:

* The four ``dossier_san_diego`` documents — the 2025 SDPD Annual
  Surveillance Report (the Vigilant LEARN **hosted-database subscription**
  section), the City–Ubicquia public-safety agreement, the SDPD technology
  index and the Privacy Advisory Board reports index — are replayed through
  the real ``dossier_documents`` connector over the committed stand-in
  fixtures. The emitted records are consumed verbatim (only the
  connector-transient ``claim_id``/``sys_period`` are dropped).
* A small set of authored claims records the ticket's load-bearing
  distinctions verbatim: the operator attribution, the physical ALPR
  program's technology, the subscription's bounded non-ownership
  statement, the prime-vs-component role split, the program's contracting
  instrument, and the oversight recommendation's ``proposed`` state —
  each cited to a committed span with locator + capture binding.

The ticket's core distinctions are enforced by construction:

* **subscription ≠ hardware** — the ASR target carries
  ``access_mode="subscription"``; the connector's hardware guard bars every
  device/location predicate on it, and no claim in the packet asserts a
  local SDPD camera, device count, deployment existence or fixed asset
  from the Vigilant subscription. The subscription's *only* q3 content is
  the agency's own bounded statement ("owns no ALPR cameras or hardware
  under this arrangement") — scoped verbatim, never a universal absence.
* **prime contractor ≠ component vendor** — ``seller = Ubicquia, Inc.`` is
  the named contracting party; ``vendor = Flock Safety, Inc.`` is the
  component supplier whose terms are incorporated by reference. The roles
  stay separate predicates on the contract and an authored claim makes the
  split explicit — a vendor mention is never an operational relationship.
* **recommendation ≠ adoption** — the PAB index evidences the
  recommendation's existence + verbatim title only; the recommendation
  stays ``proposed`` (an authored ``authorization_state`` claim cited to
  the index anchor span) — no enactment/adoption is asserted, and the
  agency's annual self-report stays genre-distinct from oversight.
* **signature ≠ execution** — the agreement's ``signed_date`` is the
  vendor-side date verbatim ("Vendor Date: 12/15/2023") and ``City Date:``
  is a ``present_but_empty`` field-state; the genre stays ``contract``,
  never ``executed_contract``. Nothing calls the agreement executed.
* **Part VIII preflight is metadata-only** — the ALPR index's 2024–2026
  network-audit spreadsheet links (SRC-027) are recorded by link metadata
  only. No workbook byte, XLSX container, ZIP member or ``sharedStrings``
  stream is ever transported; the workbook acquisition path is
  ``rejected`` permanently (E4-B3 = a, 2026-10-01T04:51:39Z).

Gate discipline: ``live_verification=false``. Nothing here fetches, flips a
source's rights posture, completes a human gate, sends a records request,
or marks the independent semantic review as anything but ``not_run``
(D-R10-HUMAN-1 OPEN). The bounded live-capture obligations are recorded as
a RETURN PASS packet (:func:`live_return_pass`), owned by deferral
``D-P32.20-1``; the gap follow-ups are drafted through the real
``tasks.detect`` machinery — drafted, never sent (``records_requests_sent``
stays 0); the network-audit preflight (:func:`network_audit_preflight`) is
metadata-only and performs no acquisition.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exports.research_dossier import (
    CORRECTION_ROUTE,
    PACKET_SCHEMA,
    build_dossier,
    build_portfolio,
    render_dossier_print_html,
    render_portfolio_json,
    validate_packet,
)

from .dossier_packet import (
    CAPTURE_KIND_FIXTURE_REPLAY,
    CAPTURE_KIND_STAND_IN,
    _fetcher,
    _fixture_commit,
    _MapTransport,
    _refuse_as_of_after_build,
    _refuse_retrieval_after_commit,
    _stamp_replay,
)

DOSSIER_ID = "san-diego-sdpd-alpr"
DEPLOYMENT = "sig:deployment:sdpd-alpr"
VIGILANT = "sig:deployment:sdpd-vigilant"
CONTRACT = "contract:sandiego-ubicquia-ps"
JURISDICTION = "us.state_abbr:CA"
#: P34.22b chronology: the packet's as-of/searched dates are the evidence
#: ANCHOR — the newest fixture authoring commit, git-derived — never a typed
#: replay date. The documents' STATED dates — the 2023-12-15 vendor
#: signature date, the 2025 report period, the 2026-02-15 posted date —
#: are document dates and are never promoted to capture/observation dates.
#: Captured index listings are not asserted to be the current versions
#: (the live pass re-checks them).

_REPO = Path(__file__).resolve().parents[3]
_DOSSIER_FIX = _REPO / "tests" / "connectors" / "fixtures" / "dossier"

#: doc_id → (fixture file, media type) for the dossier_san_diego targets —
#: the reviewed target row names the URL; the canned transport serves
#: committed stand-in bytes for it (SIG-INGEST-011 — never a real fetch).
_DOSSIER_FIXTURES: dict[str, tuple[str, str]] = {
    "sd-asr-2025-vigilant": ("sd_asr_2025_vigilant.pdf", "application/pdf"),
    "sd-ubicquia-agreement-2023": ("sd_ubicquia_agreement_2023.pdf", "application/pdf"),
    "sd-technology-index": ("sd_technology_index.html", "text/html"),
    "sd-pab-index": ("sd_pab_index.html", "text/html"),
}

_DOCS = [
    "sd-asr-2025-vigilant",
    "sd-ubicquia-agreement-2023",
    "sd-technology-index",
    "sd-pab-index",
]

_ASR_URL = "https://www.sandiego.gov/sites/default/files/sdpd-annual-surveillance-report-2025.pdf"
_UBICQUIA_URL = (
    "https://www.sandiego.gov/sites/default/files/cosd-public-safety-agreement-ubicquia.pdf"
)
_TECH_INDEX_URL = "https://www.sandiego.gov/police/data-transparency/technology"
_PAB_INDEX_URL = "https://www.sandiego.gov/pab/reports"
_ALPR_PAGE_URL = "https://www.sandiego.gov/police/data-transparency/technology?tech=alpr"
_ALPR_POLICY_URL = "https://www.sandiego.gov/sites/default/files/alpr-use-policy.pdf"
_PAB_REC_URL = "https://www.sandiego.gov/sites/default/files/pab-final-recommendation-alpr-2025.pdf"


# --------------------------------------------------------------------------- #
# Fixture replay (no network)
# --------------------------------------------------------------------------- #


def _dossier_records(retrieved_at: datetime | None = None) -> list[dict[str, Any]]:
    """Replay the four ``dossier_san_diego`` targets through the connector."""
    from connectors.dossier_documents import DossierDocumentsConnector
    from connectors.live_targets import live_targets
    from connectors.pipeline import run
    from connectors.registry import CompactStatus, get
    from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
    from evidence.ingest_run import IngestRun

    source_id = "dossier_san_diego"
    targets = copy.deepcopy(list(live_targets(source_id)))
    responses: dict[str, tuple[bytes, str, datetime]] = {}
    for target in targets:
        doc_id = str(target.get("doc_id") or target.get("id"))
        name, media = _DOSSIER_FIXTURES[doc_id]
        fixture = _DOSSIER_FIX / name
        if retrieved_at is not None:
            _refuse_retrieval_after_commit(retrieved_at, fixture)
        responses[str(target["url"])] = (
            fixture.read_bytes(),
            media,
            _fixture_commit(fixture)[1],
        )
    # The documented fixture-runner carve-out (same posture as P32.18/19):
    # the registry row itself stays ingestion_permitted=false
    # (D-R10-SOURCES-1 OPEN); the in-memory flip is a replay posture only —
    # never a rights decision.
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    ctx = RunContext(
        source=source,
        run=IngestRun("dossier_documents", "1.0.0", "p32.20-packet", "r1", "v1", ()),
        fetcher=_fetcher("dossier_documents", _MapTransport(responses, retrieved_at=retrieved_at)),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    report = run(DossierDocumentsConnector(), ctx)
    return [_stamp_replay(r) for r in report.claims]


# --------------------------------------------------------------------------- #
# Authored claims — the distinctions the crosswalk's configured fields don't
# carry, each cited to a committed span (locator + capture binding)
# --------------------------------------------------------------------------- #


def _evidence(
    *,
    source_url: str,
    locator: Mapping[str, Any],
    extraction_method: str,
    fixture_committed_at: str,
) -> dict[str, Any]:
    """The citation block of a hand-authored stand-in claim (P34.22b /
    B4 G1 R4): locator + the fixture's real authoring commit — NO retrieval
    date, since nothing was ever retrieved."""
    return {
        "source_url": source_url,
        "fixture_committed_at": fixture_committed_at,
        "extraction_method": extraction_method,
        "locator": dict(locator),
    }


def _authored(
    *,
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: Any,
    document_id: str,
    document_genre: str,
    evidence_genre: str,
    source_url: str,
    locator: Mapping[str, Any],
    extraction_method: str,
    dossier_field: str,
    rationale: str,
    object_type: str | None = None,
    valid_from: str | None = None,
) -> dict[str, Any]:
    _sha, committed = _fixture_commit(_DOSSIER_FIX / _DOSSIER_FIXTURES[document_id][0])
    claim: dict[str, Any] = {
        "record_kind": "claim",
        "connector": "ops.san_diego_dossier_packet",
        "source_id": "dossier_san_diego",
        "source_attribution": "dossier_san_diego",
        "subject_id": subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,
        "document_genre": document_genre,
        "evidence_genre": evidence_genre,
        "document_id": document_id,
        "dossier_field": dossier_field,
        "sensitivity_class": "C1",
        "geo_tier": 0,
        "capture_kind": CAPTURE_KIND_STAND_IN,
        "assertion_rationale": rationale,
        "evidence": _evidence(
            source_url=source_url,
            locator=locator,
            extraction_method=extraction_method,
            fixture_committed_at=committed.isoformat(),
        ),
        "observed_at": committed.date().isoformat(),
    }
    if object_type is not None:
        claim["object_type"] = object_type
    if valid_from is not None:
        claim["valid_from"] = valid_from
        claim["valid_from_kind"] = "exact"
    return claim


def _index_locator(fixture_name: str, literal: str) -> dict[str, Any]:
    """A byte-range locator over the committed index fixture — the cited
    literal must really occur in the bytes (a missing literal fails closed)."""
    data = (_DOSSIER_FIX / fixture_name).read_bytes()
    needle = literal.encode("utf-8")
    start = data.find(needle)
    if start < 0:
        raise ValueError(f"literal not present in {fixture_name}: {literal!r}")
    if data.find(needle, start + 1) >= 0:
        raise ValueError(f"literal not unique in {fixture_name}: {literal!r}")
    return {"kind": "byte_range", "start": start, "end": start + len(needle)}


def _operator_claim() -> dict[str, Any]:
    """``asset_operator = San Diego Police Department`` cited to the ASR.

    The department's own published Annual Surveillance Report names the
    agency on its face — an operator attribution at self-report strength.
    It says who reports the program; it says nothing about a funder and
    nothing about the subscription creating hardware.
    """
    return _authored(
        subject_id=DEPLOYMENT,
        predicate="asset_operator",
        value="San Diego Police Department",
        raw_value="San Diego Police Department",
        object_type="organization",
        document_id="sd-asr-2025-vigilant",
        document_genre="deployment_report",
        evidence_genre="official_statement",
        source_url=_ASR_URL,
        locator={"kind": "page", "page": 1},
        extraction_method="pdf_text",
        dossier_field="q1",
        rationale=(
            "the reporting agency named on the face of its own published "
            "Annual Surveillance Report — an operator attribution, never "
            "evidence of a funder or of hardware under the subscription"
        ),
    )


def _technology_claim() -> dict[str, Any]:
    """``technology`` on the physical ALPR program — the streetlight system.

    The City's own technology index lists the "ALPR Program" as a
    surveillance technology; the Ubicquia agreement's contracted units are
    the streetlight-mounted hardware channel. This names the physical
    program's technology — distinct from the Vigilant LEARN hosted-database
    subscription (a separate subject, a separate evidence chain).
    """
    return _authored(
        subject_id=DEPLOYMENT,
        predicate="technology",
        value=(
            "automated license-plate recognition — streetlight-mounted "
            "public-safety platform (physical program; distinct from the "
            "Vigilant LEARN hosted-database subscription)"
        ),
        raw_value="ALPR Program",
        document_id="sd-technology-index",
        document_genre="deployment_report",
        evidence_genre="portal_document",
        source_url=_TECH_INDEX_URL,
        locator=_index_locator("sd_technology_index.html", "ALPR Program"),
        extraction_method="html_text",
        dossier_field="q2",
        rationale=(
            "the City's own technology index lists the ALPR Program as a "
            "surveillance technology — the physical streetlight program, "
            "distinct from the Vigilant subscription access (q4)"
        ),
    )


def _subscription_no_hardware_claim() -> dict[str, Any]:
    """The agency's own bounded statement: no hardware under the subscription.

    The ASR states verbatim that the Department owns no ALPR cameras or
    hardware *under this arrangement*. This is a scoped official statement
    — it makes the subscription-vs-hardware distinction an evidenced fact
    on q3, and it is never generalised into "SDPD has no ALPR hardware"
    (the streetlight program is a separate channel with contracted units).
    """
    return _authored(
        subject_id=VIGILANT,
        predicate="written_policy_value",
        value=(
            "the Department owns no ALPR cameras or hardware under the "
            "Vigilant subscription arrangement (agency-reported, scoped "
            "verbatim to this arrangement)"
        ),
        raw_value=("The Department owns no ALPR cameras or hardware under this arrangement."),
        document_id="sd-asr-2025-vigilant",
        document_genre="deployment_report",
        evidence_genre="official_statement",
        source_url=_ASR_URL,
        locator={"kind": "page", "page": 1},
        extraction_method="pdf_text",
        dossier_field="q3",
        rationale=(
            "the agency's own bounded non-ownership statement — scoped "
            "verbatim 'under this arrangement'; it keeps the subscription "
            "from minting local hardware without fabricating a universal "
            "absence (the streetlight program is separately contracted)"
        ),
    )


def _prime_vs_component_claim() -> dict[str, Any]:
    """Prime contractor vs component vendor — roles kept distinct.

    The agreement names ``Ubicquia, Inc.`` as the contracting party
    ("Vendor"/``seller``) and incorporates ``Flock Safety, Inc.``'s terms
    by reference — the component supplier. A named incorporation is not an
    operational relationship: the two roles stay separate predicates on the
    contract and this claim records the split verbatim.
    """
    return _authored(
        subject_id=CONTRACT,
        predicate="written_policy_value",
        value=(
            "Ubicquia, Inc. is the named prime contracting party "
            "('Vendor'); Flock Safety, Inc. terms are incorporated by "
            "reference as the component supplier — the prime contractor "
            "and the component vendor are distinct roles"
        ),
        raw_value=("The terms and conditions of Flock Safety, Inc. are incorporated by reference."),
        document_id="sd-ubicquia-agreement-2023",
        document_genre="procurement_record",
        evidence_genre="contract",
        source_url=_UBICQUIA_URL,
        locator={"kind": "page", "page": 1},
        extraction_method="pdf_text",
        dossier_field="q1",
        rationale=(
            "the agreement's own clause structure: Ubicquia is the "
            "counterparty ('Vendor'/seller), Flock Safety supplies the "
            "incorporated component terms — a vendor mention is never an "
            "operational relationship"
        ),
    )


def _authority_claim() -> dict[str, Any]:
    """``legal_authority`` — the program's recorded contracting instrument.

    The City-published public-safety agreement is the authority surface the
    pack can evidence for the streetlight program — cited with its
    execution caveat intact (vendor-only signed date; City date
    ``present_but_empty``). The use-policy and ordinance chain beyond it
    is undocumented in the pack → q6 declared partial.
    """
    return _authored(
        subject_id=DEPLOYMENT,
        predicate="legal_authority",
        value=(
            "City of San Diego–Ubicquia public-safety agreement is the "
            "program's published contracting instrument (execution "
            "unverified — vendor-only signed date; City date blank)"
        ),
        raw_value="Public Safety Agreement",
        document_id="sd-ubicquia-agreement-2023",
        document_genre="procurement_record",
        evidence_genre="contract",
        source_url=_UBICQUIA_URL,
        locator={"kind": "page", "page": 1},
        extraction_method="pdf_text",
        dossier_field="q6",
        rationale=(
            "the agreement is the program's recorded contracting "
            "instrument on the City's own portal — cited with the "
            "signature gap intact; never an 'executed' label"
        ),
    )


def _recommendation_status_claim() -> dict[str, Any]:
    """``authorization_state`` — the PAB recommendation stays ``proposed``.

    The PAB reports index evidences the recommendation's existence and
    verbatim title (the original index span is the locator); its contents
    were not captured (the PDF exceeds the connector's byte bound) and no
    adoption/enactment record exists in the pack. A recommendation is a
    proposal by nature — it stays ``proposed`` and is never rendered as
    enacted policy, and the agency's annual self-report stays a distinct
    genre from this oversight instrument.
    """
    return _authored(
        subject_id=DEPLOYMENT,
        predicate="authorization_state",
        value=(
            "PAB recommendation on the 2025 ALPR Annual Surveillance "
            "Report — proposed (existence and verbatim title evidenced; "
            "content and any adoption/enactment not evidenced in the pack)"
        ),
        raw_value=("PAB Recommendation on the 2025 ALPR Annual Surveillance Report"),
        document_id="sd-pab-index",
        document_genre="deployment_report",
        evidence_genre="portal_document",
        source_url=_PAB_INDEX_URL,
        locator=_index_locator(
            "sd_pab_index.html",
            "PAB Recommendation on the 2025 ALPR Annual Surveillance Report",
        ),
        extraction_method="html_text",
        dossier_field="q10",
        rationale=(
            "the oversight body's recommendation exists per its own index "
            "listing — a proposal is asserted, never adoption: nothing in "
            "the pack evidences enactment, and the ASR self-report remains "
            "genre-distinct from oversight"
        ),
    )


def _sharing_mode_claim() -> dict[str, Any]:
    """``written_policy_value`` on q8 — the evidenced sharing MODE, scoped.

    The ASR states verbatim that the LEARN database is "a shared national
    database" — "hosted vendor database shared across subscribing
    agencies". That evidences the subscription's sharing *mode* (an
    inbound pooled vendor-hosted lookup for SDPD); it does NOT name the
    outbound actors — which agencies or parties SDPD's own data is
    shared with stays unevidenced → q8 declared partial. The per-agency
    actor detail is exactly what the prohibited-until-review network
    audit could close through a safe aggregate.
    """
    return _authored(
        subject_id=VIGILANT,
        predicate="written_policy_value",
        value=(
            "the Vigilant LEARN database is a vendor-hosted national pool "
            "shared across subscribing agencies — an inbound pooled-lookup "
            "sharing mode for SDPD; the pack does not evidence which "
            "agencies or parties SDPD's own data is shared with"
        ),
        raw_value=("hosted vendor database shared across subscribing agencies"),
        document_id="sd-asr-2025-vigilant",
        document_genre="deployment_report",
        evidence_genre="official_statement",
        source_url=_ASR_URL,
        locator={"kind": "page", "page": 1},
        extraction_method="pdf_text",
        dossier_field="q8",
        rationale=(
            "the sharing MODE is stated verbatim (a pooled vendor-hosted "
            "database across subscribing agencies); outbound sharing "
            "actors are not evidenced — a scoped partial answer, never a "
            "silent zero and never a fabricated roster"
        ),
    )


def authored_claims() -> list[dict[str, Any]]:
    """The seven authored records carrying the ticket's distinctions."""
    return [
        _operator_claim(),
        _technology_claim(),
        _subscription_no_hardware_claim(),
        _prime_vs_component_claim(),
        _authority_claim(),
        _recommendation_status_claim(),
        _sharing_mode_claim(),
    ]


def packet_records(retrieved_at: datetime | None = None) -> list[dict[str, Any]]:
    """Every record the reviewed packet carries, in stable order."""
    return _dossier_records(retrieved_at) + authored_claims()


# --------------------------------------------------------------------------- #
# The Part VIII preflight — metadata only, never a workbook transport
# --------------------------------------------------------------------------- #


def network_audit_preflight() -> dict[str, Any]:
    """The Part VIII structural preflight for the network-audit source.

    The ALPR index's 2024–2026 network-audit spreadsheet links are recorded
    in the acquisition queue as SRC-027 with ``preflight.status =
    rejected``: the operator's E4-B3 answer ("a", 2026-10-01T04:51:39Z —
    SRC-027 workbooks metadata-only permanently) IS the explicit
    content-admissibility decision — the per-query workbook path is
    permanently barred (plates, person-level queries and officer
    identities; a "redacted" label is not a content-admissibility check)
    and the link-label metadata path is kept. This record documents the
    metadata-only posture: **no workbook byte, XLSX container, ZIP member
    or ``sharedStrings`` stream is fetched, staged or transported** — only
    the link/label metadata observed during the bounded research pass and
    the committed queue row are cited. A safe agency-level aggregate could
    later support q8 (declared-vs-observed sharing) through an approved
    workflow; it is explicitly NOT required for dossier completeness.
    """
    return {
        "schema": "sig.part-viii-preflight/1",
        "dossier_id": DOSSIER_ID,
        "generated_at": _packet_anchor().date().isoformat(),
        "source_reference": "SRC-027 (tasks acquisition queue)",
        "target_family": (
            "sandiego.gov ALPR index — 2024–2026 SDPD ALPR network-audit "
            "spreadsheet links (link/label metadata only)"
        ),
        "review_basis": (
            "index link labels and acquisition-queue metadata reviewed; "
            "no workbook bytes fetched or staged at any point"
        ),
        "workbook_transport": "never",
        "acquisition_status": "rejected",
        "decision": {
            "ref": "E4-B3",
            "answer": "a",
            "decided_by": "operator",
            "decided_on": "2026-10-01T04:51:39Z",
            "effect": (
                "the per-query network-audit workbooks are metadata-only "
                "permanently — the workbook acquisition path is rejected; "
                "the link-label metadata path is kept"
            ),
        },
        "prohibited_content": [
            "license_plate values",
            "person or officer identifiers",
            "per-query / per-search audit rows",
            "XLSX workbook bytes (ZIP container incl. sharedStrings.xml)",
            "any row-level network-audit content",
        ],
        "permitted_metadata": [
            "link labels and existence metadata on the public index",
            "period labels (2024–2026) on the link metadata",
            "published annual aggregate documents through the normal gate",
        ],
        "safe_aggregate_path": {
            "status": "open_question",
            "description": (
                "a safe annual/agency-level aggregate produced under an "
                "approved workflow could close the declared-vs-observed "
                "sharing gap on q8; SRC-027 is optional research — the "
                "dossier does not depend on it"
            ),
        },
        "question_support": {
            "q8": (
                "could evidence outbound sharing actors/mode IF an approved "
                "safe aggregate exists; otherwise the unknown stands"
            ),
        },
        "preconditions": [
            "the content-admissibility decision is RECORDED (E4-B3 = a): "
            "workbook bytes rejected permanently — any aggregate path needs "
            "an approved production method, never workbook transport",
            "source/rights review under D-R10-SOURCES-1",
            "a bounded acquisition method that never transports workbook "
            "bytes — approved aggregate production only",
        ],
        "rights_posture": (
            "dossier_san_diego stays ingestion_permitted=false; the "
            "network-audit workbook path is rejected (E4-B3) — this "
            "record is a preflight, never a fetch"
        ),
        "deferral": "D-P32.20-1",
    }


# --------------------------------------------------------------------------- #
# Packet composition
# --------------------------------------------------------------------------- #


def _fixture_manifest() -> dict[str, dict[str, str]]:
    """``document_id`` → the committed fixture the packet replays + the bytes'
    real authoring commit (git-derived, never typed — P34.22b / B4 G1 R4)."""
    out: dict[str, dict[str, str]] = {}
    for doc_id, (name, _media) in _DOSSIER_FIXTURES.items():
        fx = _DOSSIER_FIX / name
        sha, committed = _fixture_commit(fx)
        out[doc_id] = {
            "path": str(fx.relative_to(_REPO)),
            "commit": sha,
            "committed_at": committed.isoformat(),
        }
    return out


def _packet_anchor() -> datetime:
    """The packet's evidence anchor: the NEWEST fixture authoring commit —
    the earliest instant at which every cited byte existed."""
    return max(datetime.fromisoformat(f["committed_at"]) for f in _fixture_manifest().values())


def _search_entry(
    question: str,
    sources: list[str],
    note: str,
    *,
    searched_at: str,
    outcome: str = "found",
) -> dict[str, Any]:
    return {
        "question": question,
        "outcome": outcome,
        "sources_searched": sources,
        "searched_at": searched_at,
        "note": note,
    }


_S2_SEARCH = (
    "S2 research bounded pass (sandiego.gov portal, PAB corpus; named "
    "leads left as follow-ups, not citations)"
)

_AUDIT_LINKS = (
    "SDPD ALPR index — 2024–2026 network-audit spreadsheet links "
    "(SRC-027; link metadata only — workbook bytes never transported)"
)


def build_packet(
    *,
    retrieved_at: datetime | None = None,
    as_of: str | None = None,
    build_time: datetime | None = None,
) -> dict[str, Any]:
    """The reviewed ``sig.dossier-packet/1`` for the San Diego pilot dossier.

    P34.22b chronology (B1 §5.4 / B4 G1 R4): every capture date comes from the
    fixtures' real authoring commit times, read from git. ``retrieved_at``
    later than a fixture's commit or ``as_of`` later than the build is
    REFUSED, never silently corrected; ``as_of``/``searched_at`` default to
    the evidence anchor (the newest fixture commit).
    """
    build_time = build_time or datetime.now(UTC)
    anchor = _packet_anchor()
    anchor_date = anchor.date().isoformat()
    as_of_date = as_of or anchor_date
    _refuse_as_of_after_build(as_of_date, build_time)
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "dossier_id": DOSSIER_ID,
        "subject": {
            "slug": DOSSIER_ID,
            "label": (
                "San Diego — San Diego Police Department: streetlight/ALPR "
                "program (City–Ubicquia) + Vigilant LEARN hosted-database "
                "subscription"
            ),
            "jurisdiction": "San Diego, California (us.state_abbr:CA)",
            "entity_id": DEPLOYMENT,
            "jurisdiction_slug": "san-diego-ca",
        },
        "as_of": {"world": as_of_date, "belief": as_of_date},
        "capture": {
            "kind": CAPTURE_KIND_FIXTURE_REPLAY,
            "live_verification": False,
            "anchor": anchor.isoformat(),
            "fixtures": _fixture_manifest(),
        },
        "records": packet_records(retrieved_at),
        "declared": {
            "partial": [
                {
                    "question": "q1",
                    "rationale": (
                        "operator evidenced (SDPD's own report), buyer "
                        "(City of San Diego) and contracting roles evidenced "
                        "by the published agreement — but the funder is not "
                        "evidenced and the execution/signature chain is "
                        "incomplete"
                    ),
                },
                {
                    "question": "q3",
                    "rationale": (
                        "the only device count is 500 streetlight units "
                        "CONTRACTED under the Ubicquia agreement "
                        "(count_scope=contracted_units — contracted is not "
                        "installed); the subscription carries the agency's "
                        "bounded no-hardware statement; no installed/active/"
                        "current count exists in the pack"
                    ),
                },
                {
                    "question": "q5",
                    "rationale": (
                        "contract value, term and the vendor-side signed "
                        "date are evidenced, but execution is unverified — "
                        "the City date is present_but_empty and the "
                        "instrument stays 'contract', never executed"
                    ),
                },
                {
                    "question": "q6",
                    "rationale": (
                        "the published City–Ubicquia agreement is the "
                        "recorded contracting instrument, but the authority "
                        "chain beyond it — the ALPR Use Policy's contents "
                        "(index-linked, uncaptured) and any ordinance/"
                        "applicability record — is undocumented in the pack"
                    ),
                },
                {
                    "question": "q7",
                    "rationale": (
                        "the 60-day period is evidenced but scoped verbatim "
                        "to the Vigilant LEARN subscription's ALPR data; the "
                        "streetlight program's own retention rule is not in "
                        "the pack"
                    ),
                },
                {
                    "question": "q8",
                    "rationale": (
                        "the sharing mode is evidenced verbatim — a "
                        "vendor-hosted national pool shared across "
                        "subscribing agencies (inbound pooled access for "
                        "SDPD); the outbound sharing actors and the mode "
                        "of any SDPD outbound sharing are not evidenced"
                    ),
                },
                {
                    "question": "q10",
                    "rationale": (
                        "oversight existence is evidenced (the PAB "
                        "recommendation's index listing) and the "
                        "recommendation stays proposed — its content and "
                        "any adoption/enactment are unevidenced; the ASR "
                        "self-report stays genre-distinct from oversight"
                    ),
                },
            ],
        },
        "search_log": [
            _search_entry(
                "q1",
                _DOCS,
                "operator evidenced by SDPD's own report; buyer/seller/"
                "component-vendor roles evidenced by the agreement — the "
                "funder is not evidenced and the execution chain is "
                "incomplete → partial",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q2",
                _DOCS,
                "two distinct surfaces evidenced: the streetlight ALPR "
                "program (index-listed) and the Vigilant LEARN hosted "
                "database product — never collapsed into one technology",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q3",
                _DOCS + [_ALPR_PAGE_URL, _S2_SEARCH],
                "the only count is contracted units (500, scoped "
                "contracted_units); the subscription's bounded "
                "no-hardware statement is the agency's own; no "
                "installed/active count in the pack → partial",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q4",
                ["sd-asr-2025-vigilant"],
                "the ASR evidences configured subscription access, pooled "
                "lookup participation and a vendor-cloud-shared data "
                "scope — inbound access to the shared database; never a "
                "local device or outbound edge",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q5",
                ["sd-ubicquia-agreement-2023", _S2_SEARCH],
                "value/term/vendor-signed date evidenced; the City date "
                "is present_but_empty — execution unverified, never "
                "'executed'; the 2025-12-10 council memorandum and FY27 "
                "budget response are reviewed leads, uncaptured",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q6",
                _DOCS,
                "the published agreement is the recorded instrument; the "
                "index-listed ALPR Use Policy is uncaptured (latest "
                "retrieval 403 per research) and no ordinance record is "
                "in the pack → partial",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q7",
                ["sd-asr-2025-vigilant", "sd-ubicquia-agreement-2023"],
                "the only numeric period (60 days) is scoped to the "
                "Vigilant LEARN subscription's ALPR data; the streetlight "
                "program's retention is not in the pack → partial",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q8",
                _DOCS + [_S2_SEARCH],
                "found the sharing MODE (a vendor-hosted pool shared "
                "across subscribing agencies — inbound access for SDPD); "
                "the outbound side stays unevidenced: no claim names the "
                "agencies or parties SDPD's own data is shared with → "
                "declared partial",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q8",
                [_AUDIT_LINKS],
                "the 2024–2026 network-audit workbooks could close the "
                "declared-vs-observed sharing gap, but the workbook path "
                "is rejected permanently — E4-B3 = a (plates/person/"
                "officer content risk); only link metadata was reviewed — "
                "the safe-aggregate path stays an open precondition "
                "(follow-up q8)",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q9",
                _DOCS,
                "stated dates stay document dates: the 2023-12-15 "
                "vendor-signed date, the 2025 report period and the "
                "2026-02-15 posted date are never promoted to the "
                "git-derived replay retrieved/observed dates; index "
                "currentness is a live-pass question",
                searched_at=anchor_date,
            ),
            _search_entry(
                "q10",
                _DOCS + [_PAB_REC_URL, _S2_SEARCH],
                "the PAB recommendation exists per its own index listing "
                "and stays proposed — its ~16 MB PDF exceeds the bounded "
                "fetch limit (uncaptured) and no adoption/enactment "
                "record is in the pack",
                searched_at=anchor_date,
            ),
        ],
        "follow_ups": [
            {
                "question": "q3",
                "action": (
                    "capture the ASR's ALPR-program section (the reported "
                    "deployment/location figure for the streetlight "
                    "program) and any installed-device inventory under "
                    "HG-03 — the contracted 500 stays a contracted scope"
                ),
                "closing_condition": (
                    "a scoped installed/active count is captured and "
                    "rendered with its count_scope, or the documented "
                    "absence keeps installed counts unknown"
                ),
            },
            {
                "question": "q5",
                "action": (
                    "capture the executed signature pages of the Ubicquia "
                    "agreement (the City side of 'City Date:'), the "
                    "2025-12-10 council memorandum and the FY27 budget "
                    "response under HG-03; the drafted CPRA request "
                    "(FOLLOW_UP_DRAFTS.json) is the fallback route"
                ),
                "closing_condition": (
                    "a captured executed/verified signature page or a "
                    "recorded council rescission/adoption record resolves "
                    "the execution state, or it stays unverified"
                ),
            },
            {
                "question": "q6",
                "action": (
                    "capture the index-linked ALPR Use Policy (the "
                    "recorded 403 needs an approved bounded method) and "
                    "any surveillance-technology ordinance/applicability "
                    "record"
                ),
                "closing_condition": (
                    "policy content is captured with its effective dates, "
                    "or the retrieval failure is the recorded answer"
                ),
            },
            {
                "question": "q7",
                "action": (
                    "obtain the streetlight program's own retention rule "
                    "(use policy / ASR ALPR section) — the captured "
                    "60-day clause is Vigilant-subscription-scoped only"
                ),
                "closing_condition": (
                    "a scoped retention value lands for the physical "
                    "program, or the scope caveat stays declared"
                ),
            },
            {
                "question": "q8",
                "action": (
                    "after the SRC-027 content-admissibility + rights "
                    "decision, pursue a safe agency-level sharing "
                    "aggregate through an approved workflow (never the "
                    "row-level workbook); else keep the unknown"
                ),
                "closing_condition": (
                    "an approved aggregate names outbound sharing "
                    "actors/mode, or the unknown is recorded as final "
                    "with the workbook still unfetched"
                ),
            },
            {
                "question": "q10",
                "action": (
                    "capture the PAB recommendation PDF (~16 MB — over "
                    "the connector's byte bound; needs an approved "
                    "method) and check council minutes/records for "
                    "adoption or rejection"
                ),
                "closing_condition": (
                    "the recommendation's content lands and its status "
                    "moves proposed → adopted/rejected only on evidence, "
                    "or it stays proposed"
                ),
            },
        ],
        "restricted": [],
        "network_audit_preflight": network_audit_preflight(),
        "review": {
            "status": "not_run",
            "note": (
                "no independent reviewer exists on this build — D-R10-HUMAN-1 "
                "OPEN; the mark is honest, never fabricated"
            ),
        },
        "correction_route": CORRECTION_ROUTE,
        "notes": [
            "live_verification=false: every record replays committed fixture "
            "bytes; no live fetch, no rights flip, no gate completion",
            "subscription ≠ hardware: the Vigilant LEARN ASR section "
            "carries access_mode=subscription — the connector's hardware "
            "guard bars device predicates on it; the only q3 statement is "
            "the agency's own bounded 'owns no ALPR cameras or hardware "
            "under this arrangement'; no local SDPD device/location "
            "assertion exists from the subscription",
            "prime ≠ component: Ubicquia, Inc. is the named contracting "
            "party (seller); Flock Safety, Inc. is the incorporated "
            "component supplier — distinct predicates, recorded verbatim",
            "recommendation ≠ adoption: the PAB recommendation exists and "
            "stays proposed; no enactment/adoption evidence is asserted; "
            "the ASR self-report and the PAB index are distinct genres",
            "signature ≠ execution: 'Vendor Date: 12/15/2023' is a "
            "vendor-side date verbatim and 'City Date:' is "
            "present_but_empty — the instrument is a contract, never "
            "executed; stated dates are document dates distinct from "
            "capture dates — replayed records carry each fixture's real "
            "authoring commit time (git-derived, P34.22b)",
            "Part VIII: the network-audit spreadsheet links (SRC-027) are "
            "preflighted metadata-only — no workbook/XLSX/ZIP/sharedStrings "
            "or row-level plate/person/query content is transported; "
            "the workbook acquisition path is rejected permanently (E4-B3)",
            "unsupported facts stay unknown with documented search basis + "
            "precise follow-up — never zero and never inferred affirmative",
            "follow-up requests are DRAFTED, never sent — "
            "records_requests_sent is 0 (FOLLOW_UP_DRAFTS.json)",
        ],
    }
    return packet


# --------------------------------------------------------------------------- #
# The follow-up drafts — bounded research/request drafts, never sent
# --------------------------------------------------------------------------- #


def follow_up_drafts() -> dict[str, Any]:
    """The packet's gap follow-ups as a drafted research queue + request drafts.

    Runs the real ``tasks.detect`` machinery over the coverage gaps this
    packet honestly records — the records-obtainable gaps (execution chain,
    sharing instruments) route to ``missing_contract`` → the California
    Public Records Act ``alpr_contract`` template; the inventory and
    oversight-adoption gaps stay ``coverage_hole`` research tasks. Every
    draft stays ``status="drafted"``: no filer, no consent, no transmit
    path — ``records_requests_sent`` is 0.
    """
    from tasks.detect import JurisdictionInfo, MaterializedInputs, run_detectors

    def _gap(cid: str, subject: str, predicate: str) -> dict[str, object]:
        return {
            "coverage_id": cid,
            "subject_id": subject,
            "subject_class": None,
            "jurisdiction_id": JURISDICTION,
            "predicate_id": predicate,
            "absence_kind": "searched_not_found",
        }

    coverage = [
        _gap("sd-gap-executed-instrument", CONTRACT, "contract_signed_date"),
        _gap("sd-gap-sharing-actors", DEPLOYMENT, "sharing_agreement"),
        _gap("sd-gap-installed-count", DEPLOYMENT, "installed_device_count"),
        _gap("sd-gap-oversight-adoption", DEPLOYMENT, "oversight_recommendation_adoption"),
    ]
    anchor = _packet_anchor()
    res = run_detectors(
        MaterializedInputs(coverage=coverage),
        now=anchor,
        jurisdiction_resolver=lambda _s, _j: JurisdictionInfo(
            records_law_key="CA",
            target_agency="San Diego Police Department",
        ),
    )
    return {
        "schema": "sig.dossier-follow-up-drafts/1",
        "dossier_id": DOSSIER_ID,
        "generated_at": anchor.date().isoformat(),
        "posture": "drafted_not_sent",
        "records_requests_sent": 0,
        "coverage_gaps": coverage,
        "research_queue": [
            {
                "task_type": t.task_type,
                "subject_id": t.subject_id,
                "jurisdiction_id": t.jurisdiction_id,
                "trigger_kind": t.trigger_kind,
                "trigger_ref": t.trigger_ref,
                "status": t.status.value,
                "priority": t.priority,
            }
            for t in res.queue
        ],
        "records_request_drafts": [d.as_dict() for d in res.drafts],
        "summary": res.summary.as_dict(),
        "note": (
            "drafts only — no filer or consent is fabricated (SIG-TASK-018) "
            "and no request is transmitted; the packet's follow_ups name the "
            "precise action + closing condition per question"
        ),
    }


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
        "# P32.20 — San Diego dossier evidence pack (offline)",
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
            f"{cap.get('method')} / {cap.get('access_mode')} / "
            f"{cap.get('capture_kind', '—')} | {n} |"
        )
    lines += [
        "",
        "## Document inventory and what each supports",
        "",
        "| document | kind | what the packet takes from it |",
        "|---|---|---|",
        "| `sd-asr-2025-vigilant` | SDPD Annual Surveillance Report 2025 "
        "(Vigilant section; `official_statement`, access_mode `subscription`) "
        "| configured subscription access + pooled lookup participation + "
        "vendor-cloud-shared data scope (q4); vendor Vigilant Solutions and "
        "product Vigilant LEARN (q1/q2); the 2025 report period (q9); the "
        "60-day period scoped to the subscription's ALPR data (q7); the "
        "agency's bounded no-hardware statement (q3, authored) — **never a "
        "device count, deployment existence, location or implementation "
        "claim** |",
        "| `sd-ubicquia-agreement-2023` | City–Ubicquia public-safety "
        "agreement (genre `contract`) | buyer City of San Diego, prime "
        "contractor `seller` Ubicquia, Inc. and component `vendor` Flock "
        "Safety, Inc. as distinct roles; value $11,662,500 and five-year "
        "term; 500 streetlight units scoped `contracted_units` — contracted "
        "≠ installed; vendor-side `signed_date` 2023-12-15 verbatim and "
        "`City Date:` recorded `present_but_empty` — execution unverified |",
        "| `sd-technology-index` | SDPD surveillance-technology index "
        "(`portal_document`) | the index listings — ALPR Program, 2025 ASR, "
        "ALPR Use Policy — existence + verbatim titles + the 2026-02-15 "
        "posted date; the authored technology claim for the physical "
        "program cites the ALPR Program anchor span |",
        "| `sd-pab-index` | Privacy Advisory Board reports index "
        "(`portal_document`) | the PAB recommendation's existence + verbatim "
        "title and the Annual Reports listing; the authored "
        "`authorization_state` keeps the recommendation **proposed** — "
        "cited to the index anchor span |",
        "",
        "## Subscription vs hardware — enforced, not resolved",
        "",
        "- The ASR's `access_mode` is `subscription`: the connector's "
        "hardware guard barred every device/location predicate at emit "
        "time, and the packet asserts no local SDPD camera, device count, "
        "deployment existence or fixed asset from the subscription.",
        "- The only q3 subscription statement is the agency's own bounded "
        "sentence — 'owns no ALPR cameras or hardware **under this "
        "arrangement**' — scoped verbatim; it is never a universal "
        "absence claim and never evidence about the streetlight program.",
        "- The physical program's only count is 500 units scoped "
        "`contracted_units` — contracted is not installed; no "
        "installed/active/current count is asserted anywhere.",
        "",
        "## Prime contractor vs component vendor",
        "",
        "- `seller = Ubicquia, Inc.` is the named contracting party; "
        "`vendor = Flock Safety, Inc.` is the component supplier whose "
        "terms are incorporated by reference — separate predicates, an "
        "authored claim records the split, and a vendor mention never "
        "mints an operational relationship.",
        "",
        "## Recommendation vs adoption — and self-report vs oversight",
        "",
        "- The PAB recommendation is evidenced by its index listing "
        "(existence + verbatim title + original span locator) and stays "
        "`proposed` — no claim asserts adoption, enactment or policy "
        "force.",
        "- The 2025 ASR is the agency's own self-report "
        "(`official_statement`) — distinct in genre and in what it can "
        "support from the oversight body's instrument.",
        "",
        "## Signature vs execution — recorded, not resolved",
        "",
        "- `signed_date` carries 'Vendor Date: 12/15/2023' verbatim — a "
        "vendor-side date; `City Date:` is a `present_but_empty` "
        "field-state. The genre stays `contract`; nothing calls the "
        "agreement executed.",
        "",
        "## Part VIII preflight — metadata only",
        "",
        "- The ALPR index's 2024–2026 network-audit spreadsheet links "
        "(SRC-027) were reviewed by link/label metadata only. No workbook "
        "byte, XLSX container, ZIP member or `sharedStrings` stream was "
        "fetched, staged or transported; per-query audit workbooks may "
        "carry plates, person-level queries and officer identities — "
        "the workbook acquisition path is `rejected` permanently (E4-B3 = a).",
        "- A safe agency-level aggregate could later support q8 through "
        "an approved workflow; it is optional and the dossier does not "
        "depend on it (PART_VIII_PREFLIGHT.json).",
        "",
        "## Temporal distinctions (recorded, not resolved)",
        "",
        "- Stated dates are document dates — the 2023-12-15 vendor-signed "
        "date, the 2025 report period and the 2026-02-15 posted date are "
        "never promoted to capture dates: replayed records carry each "
        "fixture's real authoring commit time, read from git (never a "
        f"fetch); the evidence anchor is {pkt['capture']['anchor']}.",
        "- Captured index listings are not asserted to be the current "
        "versions: index currency is a live-pass question.",
        "",
        "## Rights, review and acquisition posture",
        "",
        "- `dossier_san_diego` stays `ingestion_permitted=false` "
        "(D-R10-SOURCES-1 OPEN): the four documents replayed committed "
        "stand-ins; the URLs are reviewed targets, not captured bytes.",
        "- Independent semantic review: `not_run` — D-R10-HUMAN-1 OPEN. "
        "Mechanical completeness is reported separately from pilot "
        "completion (the honest `independent_semantic_review` checklist "
        "item fails rather than fabricating a reviewer).",
        "- Unsupported facts are `unknown` or declared `partial` with a "
        "documented search basis and a precise follow-up — never zero, "
        "never an inferred affirmative.",
        "",
        "## Follow-up / RETURN PASS",
        "",
        "Bounded live obligations are recorded in `LIVE_RETURN_PASS.json` "
        "(deferral `D-P32.20-1`): actual byte captures of the four "
        "reviewed URLs plus the ALPR detail page, the ALPR Use Policy, "
        "the PAB recommendation PDF, the council/budget leads and the "
        "preflight-only network-audit links — all behind HG-03, no rights "
        "flip, no gate completion. Gap follow-ups are drafted in "
        "`FOLLOW_UP_DRAFTS.json` through the real `tasks.detect` machinery "
        "— `status: drafted`, `records_requests_sent: 0`.",
        "",
    ]
    return "\n".join(lines)


LIVE_PASS_SCHEMA = "sig.dossier-live-return-pass/1"


def live_return_pass() -> dict[str, Any]:
    """The bounded live-capture stage the offline packet defers (D-P32.20-1).

    Prepared, never executed: it names the exact targets and the bounded
    questions a later HG-03-cleared pass answers, and forbids every shortcut
    (no rights flip, no gate completion, no request sent, no publication,
    no workbook transport)."""
    from connectors.live_targets import live_targets

    dossier_targets = [
        {
            "doc_id": str(t.get("doc_id") or t.get("id")),
            "url": str(t["url"]),
            "kind": "clause_fields",
            "goal": "actual byte capture replacing the committed stand-in",
        }
        for t in live_targets("dossier_san_diego")
    ]
    extra = [
        {
            "doc_id": "sd-alpr-program-page",
            "url": _ALPR_PAGE_URL,
            "kind": "document_page",
            "goal": (
                "capture the ALPR program detail page — deployment/location "
                "figures, program retention and sharing terms the index "
                "only links"
            ),
        },
        {
            "doc_id": "sd-alpr-use-policy",
            "url": _ALPR_POLICY_URL,
            "kind": "clause_fields",
            "goal": (
                "capture the index-linked ALPR Use Policy (the recorded "
                "403 needs an approved bounded method) — authority, "
                "retention and use/sharing restrictions for the "
                "streetlight program"
            ),
            # E4-B4 = a (2026-10-01T04:51:39Z): a per-target byte-bound
            # exception plus ONE bounded retry is recorded on this target —
            # never a blind retry.
            "byte_bound_exception": "per-target exception under E4-B4 (a)",
            "bounded_retries": 1,
        },
        {
            "doc_id": "sd-pab-recommendation-2025",
            "url": _PAB_REC_URL,
            "kind": "document_page",
            "goal": (
                "capture the PAB recommendation (~16 MB — over the "
                "connector's byte bound; needs an approved method) and "
                "check council records for adoption/rejection — the "
                "recommendation stays proposed until evidence lands"
            ),
            # E4-B4 = a (2026-10-01T04:51:39Z): a per-target byte-bound
            # exception plus ONE bounded retry is recorded on this target —
            # never a blind retry.
            "byte_bound_exception": "per-target exception under E4-B4 (a)",
            "bounded_retries": 1,
        },
        {
            "doc_id": "sd-council-memo-2025-12-10",
            "url": "https://www.sandiego.gov/city-clerk/officialdocs/council-documents",
            "kind": "document_page",
            "goal": (
                "reviewed lead — the 2025-12-10 council memorandum and "
                "FY27 budget response on the public-safety program "
                "(execution/adoption chain)"
            ),
        },
        {
            "doc_id": "sd-network-audit-links",
            "url": _ALPR_PAGE_URL,
            "kind": "metadata_only_preflight",
            "goal": (
                "PREFLIGHT ONLY (SRC-027, rejected under E4-B3 — metadata "
                "only permanently): the 2024–2026 network-audit spreadsheet "
                "links — link/label metadata only; no workbook, XLSX, ZIP "
                "member or sharedStrings transport; row-level content "
                "rejected permanently"
            ),
        },
    ]
    return {
        "schema": LIVE_PASS_SCHEMA,
        "packet_id": "san-diego-dossier-live-pass",
        "status": "prepared_not_executed",
        "deferral": "D-P32.20-1",
        "reason_deferred": (
            "live_verification=false: D-R10-SOURCES-1 stays OPEN — "
            "source/evidence-use review and the HG-03 rights decision are "
            "pending; SRC-027's workbook path is rejected permanently "
            "(E4-B3 = a) — metadata only"
        ),
        "targets": dossier_targets + extra,
        "bounded_questions": [
            "actual bytes of the four reviewed documents — do the emitted "
            "subscription/contract/index claims match real captures",
            "the ASR's ALPR-program section — the streetlight program's "
            "reported deployment figures with their stated scope",
            "the Ubicquia agreement's signature pages — does a City "
            "signature/date exist (execution currently unverified)",
            "the ALPR Use Policy's authority/retention/sharing content "
            "(currently index-linked only, retrieval 403)",
            "the PAB recommendation's content and any council "
            "adoption/rejection record — proposed until evidenced",
            "the 2025-12-10 council memorandum + FY27 budget response — "
            "the execution/adoption and funding chain",
        ],
        "preconditions": [
            "HG-03 source/rights review per target (published-URL ownership screen)",
            "Part VIII preflight holds — the network-audit family stays "
            "metadata-only: no workbook/XLSX/ZIP/sharedStrings or "
            "row-level plate/person/query transport EVER",
            "SRC-027's content-admissibility decision is RECORDED "
            "(E4-B3 = a): workbook bytes rejected permanently — aggregate "
            "production only under an approved method",
            "resource bounds identical to the replay path (2 protocols, "
            "page/byte caps) — the ~16 MB PAB recommendation needs an "
            "approved method",
            "the drafted records requests are reviewed before any filing "
            "— sending is a separate operator act, never this pass's output",
        ],
        "non_goals": [
            "no source rights flip inside this packet",
            "no operator-gate completion",
            "no records request sent (drafted_not_sent stays)",
            "no publication or public release",
            "no network-audit workbook or row-level content acquisition",
        ],
    }


# --------------------------------------------------------------------------- #
# Artifact writer
# --------------------------------------------------------------------------- #

ARTIFACT_NAMES = {
    "packet": "san_diego_dossier_packet.json",
    "dossier": "san_diego_dossier.json",
    "portfolio": "san_diego_dossier_portfolio.json",
    "print": "san_diego_dossier.print.html",
    "evidence_pack": "EVIDENCE_PACK.md",
    "live_pass": "LIVE_RETURN_PASS.json",
    "follow_up_drafts": "FOLLOW_UP_DRAFTS.json",
    "preflight": "PART_VIII_PREFLIGHT.json",
}


def write(out_dir: Path) -> dict[str, Path]:
    """Emit the whole P32.20 artifact set into ``out_dir`` (deterministic)."""
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
        "evidence_pack": evidence_pack_markdown(packet).encode("utf-8"),
        "live_pass": (
            json.dumps(live_return_pass(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode(),
        "follow_up_drafts": (
            json.dumps(follow_up_drafts(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode(),
        "preflight": (
            json.dumps(network_audit_preflight(), indent=2, sort_keys=True, ensure_ascii=False)
            + "\n"
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
    "VIGILANT",
    "CONTRACT",
    "JURISDICTION",
    "CAPTURE_KIND_STAND_IN",
    "CAPTURE_KIND_FIXTURE_REPLAY",
    "build_packet",
    "packet_records",
    "authored_claims",
    "network_audit_preflight",
    "follow_up_drafts",
    "evidence_pack_markdown",
    "live_return_pass",
    "write",
    "ARTIFACT_NAMES",
    "LIVE_PASS_SCHEMA",
]

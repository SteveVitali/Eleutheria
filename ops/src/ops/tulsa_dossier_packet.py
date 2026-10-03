# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Tulsa ``sig.dossier-packet/1`` builder (P32.19 / S2, SIG-DOS-004).

This module *authors the reviewed packet* — the input artifact the shared
``exports.research_dossier`` machinery composes into the Tulsa research
dossier. It forks none of the dossier machinery: packet composition, the
six-state answer vocabulary, the rubric, release validation and the ledger
all stay in ``exports``; this module only gathers the reviewed records and
the packet-level declarations the machinery cannot infer.

Record provenance — every affirmative answer must cite committed bytes:

* The three ``dossier_tulsa`` documents (TPD Policy 113C, TPD Policy 113E
  and the public private-camera integration MOU **template**) are replayed
  through the real ``dossier_documents`` connector over the committed
  stand-in fixtures — the emitted records are consumed verbatim (only the
  connector-transient ``claim_id``/``sys_period`` are dropped).
* One authored claim — ``asset_operator = Tulsa Police Department`` — is
  cited to the 113C policy page: the department's own enacted ALPR policy
  is the operator attribution. Everything the fixtures do NOT support
  (executed instrument, MOU parties, inventory, spend, configured/observed
  sharing and use) stays ``unknown`` with a documented search basis and a
  precise follow-up — never zero and never inferred.

The ticket's core distinctions are enforced by construction:

* **template ≠ executed** — the MOU's Licensor/Licensee/Date/Signature
  fields emit ``present_but_empty`` field-states; the template's offered
  terms emit only D6 claims under non-execution predicates; no
  ``buyer``/``seller``/``signed_date``/``contract_value`` claim exists.
* **template ≠ participants/partner edge** — no claim asserts an actual
  sharing relationship, roster or participant; the offered purpose clause
  is a D6 ``written_policy_value``, never an access edge.
* **policy effective ≠ retrieval date** — ``effective_from`` claims carry
  the policies' stated dates (2023-07-07 / 2023-10-04) while
  ``observed_at``/``retrieved_date`` stay the replay date (2026-10-01);
  2023 documents are not asserted to be the current versions.
* **unsupported ≠ zero** — counts, spend, partners and use are ``unknown``
  with named sources searched, a search date and a precise next action.

Gate discipline: ``live_verification=false``. Nothing here fetches, flips a
source's rights posture, completes a human gate, sends a records request,
or marks the independent semantic review as anything but ``not_run``
(D-R10-HUMAN-1 OPEN). The bounded live-capture obligations are recorded as
a RETURN PASS packet (:func:`live_return_pass`), owned by deferral
``D-P32.19-1``; the gap follow-ups are drafted through the real
``tasks.detect`` machinery — drafted, never sent (``records_requests_sent``
stays 0).
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

from .dossier_packet import _fetcher, _MapTransport, _strip_transient

DOSSIER_ID = "tulsa-tpd-alpr"
DEPLOYMENT = "sig:deployment:tulsa-tpd-alpr"
JURISDICTION = "us.state_abbr:OK"
#: The packet's as-of pair — the replay-scenario date. The shared transport
#: labels the fixture replay's ``retrieved_at``/``observed_at`` 2026-10-01
#: (the recorded stand-in replay date, same as the emitted claims carry);
#: the as-of pair names the scenario day the dossier's claims hold at.
#: The policies' STATED effective dates (2023-07-07 / 2023-10-04) are
#: document dates and are never promoted to capture/observation dates, and
#: the captured 2023 policy files are not asserted to be the current
#: enforceable versions (the live pass re-checks the policies index).
AS_OF_WORLD = "2026-10-01"
AS_OF_BELIEF = "2026-10-01"
_REPLAY_DATE = "2026-10-01"
_GENERATED_AT = datetime(2026, 10, 1, tzinfo=UTC)

_REPO = Path(__file__).resolve().parents[3]
_DOSSIER_FIX = _REPO / "tests" / "connectors" / "fixtures" / "dossier"

#: doc_id → (fixture file, media type) for the dossier_tulsa targets — the
#: reviewed target row names the URL; the canned transport serves committed
#: stand-in bytes for it (SIG-INGEST-011 — never a real fetch).
_DOSSIER_FIXTURES: dict[str, tuple[str, str]] = {
    "tulsa-mou-template": ("tulsa_mou_template.pdf", "application/pdf"),
    "tulsa-policy-113c": ("tulsa_policy_113c.pdf", "application/pdf"),
    "tulsa-policy-113e": ("tulsa_policy_113e.pdf", "application/pdf"),
}

_DOCS = ["tulsa-mou-template", "tulsa-policy-113c", "tulsa-policy-113e"]
_POLICY_URL = "https://www.tulsapolice.org/files/policy-113c-alpr.pdf"
_FLOCK_PAGE_URL = "https://www.tulsapolice.org/flock-safety"
_POLICIES_INDEX_URL = "https://www.tulsapolice.org/policies-and-procedures"
_SAFETY_GUIDE_URL = (
    "https://www.cityoftulsa.org/government/departments/planning-and-neighborhoods/"
    "community-planning/commercial-corridor-safety-guide/"
)


# --------------------------------------------------------------------------- #
# Fixture replay (no network)
# --------------------------------------------------------------------------- #


def _dossier_records() -> list[dict[str, Any]]:
    """Replay the three ``dossier_tulsa`` targets through the real connector."""
    from connectors.dossier_documents import DossierDocumentsConnector
    from connectors.live_targets import live_targets
    from connectors.pipeline import run
    from connectors.registry import CompactStatus, get
    from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
    from evidence.ingest_run import IngestRun

    source_id = "dossier_tulsa"
    targets = copy.deepcopy(list(live_targets(source_id)))
    responses: dict[str, tuple[bytes, str]] = {}
    for target in targets:
        doc_id = str(target.get("doc_id") or target.get("id"))
        name, media = _DOSSIER_FIXTURES[doc_id]
        responses[str(target["url"])] = ((_DOSSIER_FIX / name).read_bytes(), media)
    # The documented fixture-runner carve-out (same posture as P32.18): the
    # registry row itself stays ingestion_permitted=false (D-R10-SOURCES-1
    # OPEN); the in-memory flip is a replay posture only — never a rights
    # decision.
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    ctx = RunContext(
        source=source,
        run=IngestRun("dossier_documents", "1.0.0", "p32.19-packet", "r1", "v1", ()),
        fetcher=_fetcher("dossier_documents", _MapTransport(responses)),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )
    report = run(DossierDocumentsConnector(), ctx)
    return [_strip_transient(r) for r in report.claims]


# --------------------------------------------------------------------------- #
# The authored operator claim (q1) — the one thing the fixtures evidence
# beyond the crosswalk's configured fields
# --------------------------------------------------------------------------- #


def _operator_claim() -> dict[str, Any]:
    """``asset_operator = Tulsa Police Department`` cited to the 113C policy.

    TPD's own enacted ALPR policy names the department and governs "the
    system" — an operator attribution at agency-policy strength (the
    predicate's directness table rates agency_policy D3 for
    ``asset_operator``, so no D6 stamp). The claim is honest about its
    ceiling: it says who runs the program per its own policy; it says
    nothing about an executed procurement, a buyer, a funder, or the MOU's
    blank parties. ``valid_from`` is the policy's STATED effective date —
    distinct from the replay's ``observed_at``/``retrieved_date``
    (2026-10-01).
    """
    return {
        "record_kind": "claim",
        "connector": "ops.tulsa_dossier_packet",
        "source_id": "dossier_tulsa",
        "source_attribution": "dossier_tulsa",
        "subject_id": DEPLOYMENT,
        "predicate_id": "asset_operator",
        "value": "Tulsa Police Department",
        "raw_value": "Tulsa Police Department",
        "object_type": "organization",
        "document_genre": "policy_document",
        "evidence_genre": "agency_policy",
        "document_id": "tulsa-policy-113c",
        "dossier_field": "q1",
        "sensitivity_class": "C1",
        "geo_tier": 0,
        "assertion_rationale": (
            "the operating agency named on the face of its own enacted ALPR "
            "policy (113C) — an operator attribution, never evidence of an "
            "executed procurement, a buyer, a funder, or the MOU's unnamed "
            "parties"
        ),
        "evidence": {
            "source_url": _POLICY_URL,
            "retrieved_date": _REPLAY_DATE,
            "extraction_method": "pdf_text",
            "locator": {"kind": "page", "page": 1},
        },
        "observed_at": _REPLAY_DATE,
        "valid_from": "2023-07-07",
        "valid_from_kind": "exact",
    }


def packet_records() -> list[dict[str, Any]]:
    """Every record the reviewed packet carries, in stable order."""
    return _dossier_records() + [_operator_claim()]


# --------------------------------------------------------------------------- #
# Packet composition
# --------------------------------------------------------------------------- #


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


_S2_SEARCH = (
    "S2 research bounded search 2026-09-25 (tulsapolice.org, cityoftulsa.org; "
    "named leads left as follow-ups, not citations)"
)


def build_packet() -> dict[str, Any]:
    """The reviewed ``sig.dossier-packet/1`` for the Tulsa pilot dossier."""
    packet: dict[str, Any] = {
        "schema": PACKET_SCHEMA,
        "dossier_id": DOSSIER_ID,
        "subject": {
            "slug": DOSSIER_ID,
            "label": (
                "Tulsa — Tulsa Police Department ALPR program "
                "(Flock Safety fixed + Axon Fleet 3 in-car)"
            ),
            "jurisdiction": "Tulsa, Oklahoma (us.state_abbr:OK)",
            "entity_id": DEPLOYMENT,
            "jurisdiction_slug": "tulsa-ok",
        },
        "as_of": {"world": AS_OF_WORLD, "belief": AS_OF_BELIEF},
        "records": packet_records(),
        "declared": {
            "partial": [
                {
                    "question": "q1",
                    "rationale": (
                        "the operator (Tulsa Police Department) is evidenced by "
                        "its own enacted policies, but the buyer and funder are "
                        "not — the MOU's Licensor/Licensee fields are recorded "
                        "present_but_empty and no procurement instrument exists "
                        "in the pack"
                    ),
                },
                {
                    "question": "q6",
                    "rationale": (
                        "the governing instruments are evidenced (TPD policies "
                        "113C/113E as enacted, effective-dated agency policy; "
                        "the MOU's offered terms), but the authority chain "
                        "beyond department policy — ordinance, contract, "
                        "appropriation or council action authorizing the program "
                        "and the MOU's referenced separate City agreement — is "
                        "undocumented in the pack"
                    ),
                },
                {
                    "question": "q7",
                    "rationale": (
                        "the only numeric period (12 months) is scoped verbatim "
                        "to manually entered LPR data; 113E records the general "
                        "retention rule as reviewed-absent — configured retention "
                        "for non-manual scans stays unresolved"
                    ),
                },
                {
                    "question": "q8",
                    "rationale": (
                        "the sharing rule is evidenced (Chief of Police or "
                        "designee approval required), but the actual sharing "
                        "actors and mode are not — no executed agreement, "
                        "roster or observed share exists in the pack; the MOU's "
                        "offered purpose is terms only"
                    ),
                },
            ],
        },
        "search_log": [
            _search_entry(
                "q1",
                ["tulsa-policy-113c", "tulsa-mou-template"],
                "operator evidenced by TPD's own enacted policy; MOU party "
                "fields recorded present_but_empty — buyer/funder not evidenced",
            ),
            _search_entry(
                "q2",
                ["tulsa-policy-113c"],
                "two distinct ALPR products named verbatim — Flock Safety fixed "
                "and Axon Fleet 3 in-car, kept separate",
            ),
            _search_entry(
                "q3",
                _DOCS + [_SAFETY_GUIDE_URL, _S2_SEARCH],
                "no device count anywhere in the captured pack; the S2 "
                "Commercial Corridor Safety Guide excerpt is a count LEAD only "
                "(date/scope unestablished) — follow-up opens it",
                outcome="searched_not_found",
            ),
            _search_entry(
                "q4",
                _DOCS + [_FLOCK_PAGE_URL, _S2_SEARCH],
                "the captured corpus holds only the MOU's offered purpose "
                "clause — terms, never configured access; the TPD Flock page's "
                "registration-vs-integration distinction is a reviewed lead, "
                "uncaptured",
                outcome="searched_not_found",
            ),
            _search_entry(
                "q5",
                _DOCS + [_S2_SEARCH],
                "bounded searches found no executed Tulsa City Flock purchase "
                "contract; the MOU's Date/signature fields are "
                "present_but_empty — 'searched, not found', never 'no contract "
                "exists'",
                outcome="searched_not_found",
            ),
            _search_entry(
                "q6",
                _DOCS,
                "enacting body + the two policies' stated effective dates + the "
                "MOU's offered terms; authority beyond department policy "
                "declared partial",
            ),
            _search_entry(
                "q7",
                ["tulsa-policy-113c", "tulsa-policy-113e", "tulsa-mou-template"],
                "12-month period scoped to manually entered data verbatim; "
                "113E's uniform period reviewed absent (field-state, never a "
                "fabricated value); use restrictions captured from all three "
                "documents",
            ),
            _search_entry(
                "q8",
                _DOCS,
                "approval-based sharing rule evidenced from 113E; no executed "
                "sharing instrument, roster or observed share in the pack",
            ),
            _search_entry(
                "q9",
                ["tulsa-policy-113c", "tulsa-policy-113e"],
                "each policy's stated effective date is its own document's "
                "declared date (113C 2023-07-07, 113E 2023-10-04) — two "
                "instruments, both values co-visible under the same-scope "
                "rule, never promoted to retrieval dates; version-currentness "
                "not proven by the captured files",
            ),
            _search_entry(
                "q10",
                _DOCS + [_S2_SEARCH],
                "no oversight artifact exists in the captured pack and the "
                "bounded research pass found none — follow-up names the "
                "oversight corpora to check",
                outcome="searched_not_found",
            ),
        ],
        "follow_ups": [
            {
                "question": "q1",
                "action": (
                    "obtain the executed camera-integration MOU(s) and the "
                    "procurement instrument — the parties the template's blank "
                    "Licensor/Licensee fields would name, and the program's "
                    "buyer/funder"
                ),
                "closing_condition": (
                    "captured bytes of an executed instrument naming the "
                    "parties/buyer, or a recorded absence over named sources "
                    "keeps buyer/funder unknown"
                ),
            },
            {
                "question": "q3",
                "action": (
                    "open the Commercial Corridor Safety Guide page and "
                    "establish the date and scope of its camera-count passage; "
                    "obtain TPD's camera inventory/count for the two ALPR "
                    "product families"
                ),
                "closing_condition": (
                    "a scoped, dated count is captured and rendered with its "
                    "count_scope, or the lead is exhausted and the absence is "
                    "documented with named sources"
                ),
            },
            {
                "question": "q4",
                "action": (
                    "capture the TPD Flock page (registration vs live "
                    "integration vs RTIC context) and obtain any executed "
                    "camera-integration MOU or sharing agreement"
                ),
                "closing_condition": (
                    "captured bytes or an executed instrument establish what "
                    "external/configured access exists — registration, "
                    "integration and pooled access stay distinct — or a "
                    "recorded absence keeps external access unknown"
                ),
            },
            {
                "question": "q5",
                "action": (
                    "search the City clerk/council agenda corpus (Tulsa's "
                    "already-identified Granicus family) by contract number and "
                    "the finance purchase-order/renewal records for the "
                    "executed City–Flock instrument; the drafted Oklahoma Open "
                    "Records Act request (FOLLOW_UP_DRAFTS.json) is the "
                    "fallback route"
                ),
                "closing_condition": (
                    "an executed instrument is captured (contract number, "
                    "parties, value, term), or the named sources' documented "
                    "absence keeps procurement unknown"
                ),
            },
            {
                "question": "q6",
                "action": (
                    "obtain the instrument authorizing the program beyond "
                    "department policy — the City agreement the MOU's terms "
                    "reference, any ordinance or council authorization"
                ),
                "closing_condition": (
                    "captured authorizing instrument(s), or a documented "
                    "absence keeps the authority chain partial"
                ),
            },
            {
                "question": "q7",
                "action": (
                    "verify on the TPD policies index that the 2023 113C/113E "
                    "files are the current enforceable versions, and obtain the "
                    "configured retention for non-manual ALPR scans (product "
                    "configuration or a general retention rule)"
                ),
                "closing_condition": (
                    "the index confirms current versions and a configured "
                    "retention document is captured, or the scope caveat stays "
                    "declared"
                ),
            },
            {
                "question": "q8",
                "action": (
                    "obtain executed sharing agreements, the partner roster, "
                    "and any sharing-mode records behind the Chief-of-Police "
                    "approval rule"
                ),
                "closing_condition": (
                    "captured executed instruments/roster establish the actual "
                    "sharing actors and mode, or a documented absence keeps "
                    "them unknown"
                ),
            },
            {
                "question": "q10",
                "action": (
                    "search council records, the city auditor, and RTIC "
                    "governance corpora for any oversight review of the ALPR "
                    "program"
                ),
                "closing_condition": (
                    "an oversight artifact is captured, or the search's "
                    "absence is documented with named sources"
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
        "notes": [
            "live_verification=false: every record replays committed fixture "
            "bytes; no live fetch, no rights flip, no gate completion",
            "the MOU is a TEMPLATE: its offered terms emit D6 claims only; "
            "its Licensor/Licensee/Date/Signature fields are present_but_empty "
            "field-states — no executed contract, no named participants, no "
            "actual sharing edge is asserted",
            "policy effective dates (2023-07-07 / 2023-10-04) are document "
            "dates distinct from the 2026-10-01 replay/retrieval date; the "
            "2023 files are not asserted to be the current versions; the two "
            "instruments' distinct stated dates surface under the same-scope "
            "conflict rule — both rendered, never collapsed to one timeline",
            "unsupported counts, spend, partners and use are unknown with "
            "documented search basis + precise follow-up — never zero and "
            "never inferred affirmative",
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
    packet honestly records — the executed-contract gap routes to
    ``missing_contract`` (RECORDS_REQUESTER → the Oklahoma Open Records Act
    ``alpr_contract`` template); the remaining gaps are honest
    ``coverage_hole`` research tasks. Every draft stays ``status="drafted"``:
    no filer, no consent, no transmit path — ``records_requests_sent`` is 0.
    """
    from tasks.detect import JurisdictionInfo, MaterializedInputs, run_detectors

    def _gap(cid: str, predicate: str) -> dict[str, object]:
        return {
            "coverage_id": cid,
            "subject_id": DEPLOYMENT,
            "subject_class": None,
            "jurisdiction_id": JURISDICTION,
            "predicate_id": predicate,
            "absence_kind": "searched_not_found",
        }

    coverage = [
        _gap("tulsa-gap-executed-contract", "procurement_contract"),
        _gap("tulsa-gap-device-inventory", "device_count"),
        _gap("tulsa-gap-executed-sharing", "sharing_agreement"),
        _gap("tulsa-gap-oversight", "oversight_review"),
    ]
    res = run_detectors(
        MaterializedInputs(coverage=coverage),
        now=_GENERATED_AT,
        jurisdiction_resolver=lambda _s, _j: JurisdictionInfo(
            records_law_key="OK",
            target_agency="Tulsa Police Department",
        ),
    )
    return {
        "schema": "sig.dossier-follow-up-drafts/1",
        "dossier_id": DOSSIER_ID,
        "generated_at": AS_OF_WORLD,
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
        "# P32.19 — Tulsa dossier evidence pack (offline)",
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
        "| `tulsa-policy-113c` | TPD agency policy (PDF stand-in) | enacting body "
        "(Tulsa Police Department); the operator attribution authored from it; "
        "two distinct products — Flock Safety fixed ALPR and Axon Fleet 3 "
        "in-car; the 12-month period scoped verbatim to *manually entered* "
        "data; access restricted to authorized personnel; the stated "
        "2023-07-07 effective date |",
        "| `tulsa-policy-113e` | TPD agency policy (PDF stand-in) | sharing "
        "requires Chief of Police or designee approval; use limited to "
        "legitimate law enforcement purposes and official business; the "
        "uniform numeric retention period recorded reviewed-`absent` (a "
        "field-state, never a fabricated value); the stated 2023-10-04 "
        "effective date |",
        "| `tulsa-mou-template` | blank MOU template (PDF stand-in, genre "
        "`template`) | offered structure/terms only — the purpose clause and "
        "the legitimate-law-enforcement-purposes use restriction as D6 "
        "claims; Licensor/Licensee/Date recorded `present_but_empty` — no "
        "executed contract, no named participants, no actual sharing edge |",
        "",
        "## Template vs executed — recorded, not resolved",
        "",
        "- The document marks itself 'TEMPLATE - not an executed instrument': "
        "the packet takes structure and offered terms only.",
        "- The MOU's executed-instrument fields are `present_but_empty`: the "
        "packet asserts no execution, no parties and no signature date. The "
        "template proves terms *offered* — never adoption or an active "
        "partner relationship.",
        "- No claim in the packet carries an executed-instrument predicate "
        "(`buyer`/`seller`/`signed_date`/`contract_value`/`amends_contract`) "
        "on the template — the emit-time guard and the release-side re-check "
        "both enforce it.",
        "- The template's purpose clause ('the parties intend to share "
        "access to camera systems') lands as a D6 `written_policy_value` on "
        "q6 — offered terms — and never mints an access/partner edge on q4.",
        "",
        "## Temporal distinctions (recorded, not resolved)",
        "",
        "- Policy effective dates are STATED document dates — 113C "
        "2023-07-07, 113E 2023-10-04 (`valid_from`, `effective_from`) — kept "
        "distinct from the replay's retrieved/observed date (2026-10-01).",
        "- The captured 2023 policy files are NOT asserted to be the current "
        "enforceable versions: the published index's currency is a live-pass "
        "question (the packet declares the limitation, never a recency claim).",
        "- The 12-month retention clause is scoped verbatim to manually "
        "entered LPR data; it is never generalized to every scan, and 113E's "
        "uniform period stays an honest `absent` field-state.",
        "",
        "## Rights, review and acquisition posture",
        "",
        "- `dossier_tulsa` stays `ingestion_permitted=false` "
        "(D-R10-SOURCES-1 OPEN): the three documents replayed committed "
        "stand-ins; the URLs are reviewed targets, not captured bytes.",
        "- Independent semantic review: `not_run` — D-R10-HUMAN-1 OPEN. "
        "Mechanical completeness is reported separately from pilot "
        "completion (the honest `independent_semantic_review` checklist "
        "item fails rather than fabricating a reviewer).",
        "- Unsupported counts, spend, partners and use are `unknown` with a "
        "documented search basis and a precise follow-up — never zero, "
        "never an inferred affirmative.",
        "",
        "## Follow-up / RETURN PASS",
        "",
        "Bounded live obligations are recorded in `LIVE_RETURN_PASS.json` "
        "(deferral `D-P32.19-1`): actual byte captures of the three reviewed "
        "URLs plus the TPD Flock page, the policies index and the "
        "Commercial Corridor Safety Guide lead — all behind HG-03, no "
        "rights flip, no gate completion. Gap follow-ups are drafted in "
        "`FOLLOW_UP_DRAFTS.json` through the real `tasks.detect` machinery "
        "— `status: drafted`, `records_requests_sent: 0`.",
        "",
    ]
    return "\n".join(lines)


LIVE_PASS_SCHEMA = "sig.dossier-live-return-pass/1"


def live_return_pass() -> dict[str, Any]:
    """The bounded live-capture stage the offline packet defers (D-P32.19-1).

    Prepared, never executed: it names the exact targets and the bounded
    questions a later HG-03-cleared pass answers, and forbids every shortcut
    (no rights flip, no gate completion, no request sent, no publication)."""
    from connectors.live_targets import live_targets

    dossier_targets = [
        {
            "doc_id": str(t.get("doc_id") or t.get("id")),
            "url": str(t["url"]),
            "kind": "clause_fields",
            "goal": "actual byte capture replacing the committed stand-in",
        }
        for t in live_targets("dossier_tulsa")
    ]
    extra = [
        {
            "doc_id": "tpd-flock-page",
            "url": _FLOCK_PAGE_URL,
            "kind": "document_page",
            "goal": (
                "capture the TPD Flock page — operation-since date, "
                "registration-vs-integration distinction, RTIC context "
                "(reviewed lead; not a fixture)"
            ),
        },
        {
            "doc_id": "tpd-policies-index",
            "url": _POLICIES_INDEX_URL,
            "kind": "document_page",
            "goal": (
                "verify the captured 2023 113C/113E files are the current "
                "enforceable policy versions"
            ),
        },
        {
            "doc_id": "tulsa-corridor-safety-guide",
            "url": _SAFETY_GUIDE_URL,
            "kind": "document_page",
            "goal": (
                "open the device-count lead and establish its date/scope "
                "before any count is used — an excerpt is never a count"
            ),
        },
    ]
    return {
        "schema": LIVE_PASS_SCHEMA,
        "packet_id": "tulsa-dossier-live-pass",
        "status": "prepared_not_executed",
        "deferral": "D-P32.19-1",
        "reason_deferred": (
            "live_verification=false: D-R10-SOURCES-1 stays OPEN — "
            "source/evidence-use review and the HG-03 rights decision are "
            "pending"
        ),
        "targets": dossier_targets + extra,
        "bounded_questions": [
            "actual bytes of the three reviewed documents — do the emitted "
            "policy/term/field-state claims match real captures",
            "the TPD Flock page's registration-vs-integration distinction and "
            "the operation-since date (captured, not a research note)",
            "whether the 2023 113C/113E files are the current enforceable "
            "versions per the published policies index",
            "the Commercial Corridor Safety Guide count lead opened with its "
            "date and scope established",
            "the executed City–Flock instrument via the clerk/council agenda "
            "corpus (Granicus family, already identified) or finance "
            "purchase-order/renewal records — and the MOU's executed parties",
        ],
        "preconditions": [
            "HG-03 source/rights review per target (published-URL ownership screen)",
            "Part VIII preflight — no plate/trip/person data is ever captured",
            "resource bounds identical to the replay path (2 protocols, page/byte caps)",
            "the drafted records request is reviewed before any filing — "
            "sending is a separate operator act, never this pass's output",
        ],
        "non_goals": [
            "no source rights flip inside this packet",
            "no operator-gate completion",
            "no records request sent (drafted_not_sent stays)",
            "no publication or public release",
        ],
    }


# --------------------------------------------------------------------------- #
# Artifact writer
# --------------------------------------------------------------------------- #

ARTIFACT_NAMES = {
    "packet": "tulsa_dossier_packet.json",
    "dossier": "tulsa_dossier.json",
    "portfolio": "tulsa_dossier_portfolio.json",
    "print": "tulsa_dossier.print.html",
    "evidence_pack": "EVIDENCE_PACK.md",
    "live_pass": "LIVE_RETURN_PASS.json",
    "follow_up_drafts": "FOLLOW_UP_DRAFTS.json",
}


def write(out_dir: Path) -> dict[str, Path]:
    """Emit the whole P32.19 artifact set into ``out_dir`` (deterministic)."""
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
    "follow_up_drafts",
    "evidence_pack_markdown",
    "live_return_pass",
    "write",
    "ARTIFACT_NAMES",
    "LIVE_PASS_SCHEMA",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.12 `dossier_documents` connector — bounded document adapters for the
three pilot dossiers (ticket 172, SIG-ACQ-003).

Drives the REAL ``pipeline.run`` over a per-URL canned transport (no network,
SIG-INGEST-011): committed redacted/allowed stand-in fixtures stand in for the
captured upstream bytes. Covers: the common adapter contract + its two
narrowly-scoped format handlers (``clause_fields`` / ``index_listing`` over
``html_text`` / ``pdf_text``), the frozen field crosswalk (every configured
field resolves; an unmapped required field fails closed to a scoped
amendment), the genre guards (a template never asserts an executed instrument;
a subscription never asserts local hardware), publication-vs-effective vs
coverage valid-time semantics, missing/redacted field states, parser resource
bounds, malformed/encrypted/unsupported-document failure with no partial
affirmative claim, the shared Part VIII guard, organisation-role entity-ref
twins, replay/shadow determinism, the loader gate, and licence/compartment
preservation.
"""

from __future__ import annotations

import copy
import dataclasses
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.dossier_documents import (
    DOSSIER_SOURCES,
    DossierDocumentsConnector,
    GenreGuardViolation,
    UnmappedField,
    adapter_config,
    assert_genre_permits,
    check_crosswalk,
    crosswalk,
    document_protocols,
    field_map,
    predicate_allowlist,
    resource_bounds,
    vocab,
)
from connectors.live_targets import live_targets
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.okc_documents import PartVIIIViolation, assert_part_viii_safe
from connectors.pipeline import run
from connectors.registry import CompactStatus, get
from connectors.replay import replay, replay_fingerprint, shadow_replay
from connectors.runner import CONNECTOR_FOR_SOURCE, live_gate_reasons
from connectors.stages import (
    ContentDrift,
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    get_connector,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "dossier"
_RETRIEVED = datetime(2026, 10, 1, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

CONNECTOR = "dossier_documents"

#: doc_id -> (fixture file, media type). The fixture-runner contract: the
#: reviewed live_targets row names the URL; the canned transport serves the
#: committed stand-in bytes for it.
FIXTURE_FOR_DOC: dict[str, tuple[str, str]] = {
    "okc-flock-usage-2026": ("okc_usage_page.html", "text/html"),
    "okc-council-memo-2026-08": ("okc_council_memo_2026.pdf", "application/pdf"),
    "okc-flock-amendment-2026": ("okc_amendment_1_2026.pdf", "application/pdf"),
    "tulsa-mou-template": ("tulsa_mou_template.pdf", "application/pdf"),
    "tulsa-policy-113c": ("tulsa_policy_113c.pdf", "application/pdf"),
    "tulsa-policy-113e": ("tulsa_policy_113e.pdf", "application/pdf"),
    "sd-asr-2025-vigilant": ("sd_asr_2025_vigilant.pdf", "application/pdf"),
    "sd-ubicquia-agreement-2023": ("sd_ubicquia_agreement_2023.pdf", "application/pdf"),
    "sd-technology-index": ("sd_technology_index.html", "text/html"),
    "sd-pab-index": ("sd_pab_index.html", "text/html"),
}


class _MapTransport:
    """URL-keyed canned responses — no real network (SIG-INGEST-011)."""

    def __init__(self) -> None:
        self.responses: dict[str, tuple[bytes, str]] = {}
        self.requested: list[str] = []

    def add_url(self, url: str, body: bytes, media: str) -> None:
        self.responses[url] = (body, media)

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> FetchResult:
        self.requested.append(url)
        if url in self.responses:
            resp_body, media = self.responses[url]
            return FetchResult(
                url=url,
                status=200,
                body=resp_body,
                media_type=media,
                retrieved_at=_RETRIEVED,
            )
        return FetchResult(
            url=url,
            status=404,
            body=b"",
            media_type="text/plain",
            retrieved_at=_RETRIEVED,
        )


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name=CONNECTOR,
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _target(source_id: str, doc_id: str) -> dict[str, Any]:
    # deepcopy: mutation tests must never leak field edits into the shared
    # live_targets table the other tests replay over.
    for target in live_targets(source_id):
        if str(target.get("doc_id") or target.get("id")) == doc_id:
            return copy.deepcopy(target)
    raise KeyError(f"{source_id} has no live target for {doc_id!r}")


def _ctx(
    source_id: str,
    targets: list[dict[str, Any]],
    *,
    sink: InMemoryClaimSink | None = None,
    transport: _MapTransport | None = None,
) -> RunContext:
    """A full pipeline context: the in-memory gate flip (the documented
    fixture-runner carve-out — the registry row itself stays
    ``ingestion_permitted=false``) + a URL-keyed canned transport."""
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    if transport is None:
        transport = _MapTransport()
        for target in targets:
            doc_id = str(target.get("doc_id") or target.get("id"))
            name, media = FIXTURE_FOR_DOC[doc_id]
            transport.add_url(str(target["url"]), (_FIX / name).read_bytes(), media)
    fetcher = PoliteFetcher(
        connector_name=CONNECTOR,
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    return RunContext(
        source=source,
        run=_ingest_run(),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=sink or InMemoryClaimSink(),
        parameters={"targets": targets},
    )


def _connector() -> DossierDocumentsConnector:
    return get_connector(CONNECTOR)()


def _claims(report_or_list: Any) -> list[Mapping[str, Any]]:
    rows = report_or_list.claims if hasattr(report_or_list, "claims") else report_or_list
    return [c for c in rows if c.get("record_kind", "claim") == "claim"]


def _claims_for(report: Any, predicate: str) -> list[Mapping[str, Any]]:
    return [c for c in _claims(report) if c.get("predicate_id") == predicate]


def _run_doc(source_id: str, doc_id: str):
    """Run one configured target through the whole pipeline."""
    ctx = _ctx(source_id, [_target(source_id, doc_id)])
    return run(_connector(), ctx), ctx


def _run_source(source_id: str):
    targets = copy.deepcopy(list(live_targets(source_id)))
    ctx = _ctx(source_id, targets)
    return run(_connector(), ctx), ctx


# --- wiring: registration, sources blocked, adapter config --------------------


def test_connector_registered_and_routed() -> None:
    assert get_connector(CONNECTOR) is DossierDocumentsConnector
    for source_id in DOSSIER_SOURCES:
        assert CONNECTOR_FOR_SOURCE[source_id] == CONNECTOR


def test_new_source_rows_stay_blocked() -> None:
    """The three NEW rows are fail-closed: not permitted, rights UNDETERMINED,
    no fabricated review metadata — the loader gate refuses before any fetch."""
    for source_id in DOSSIER_SOURCES:
        record = get(source_id)
        assert record.ingestion_permitted is False
        assert record.compact_status is CompactStatus.NOT_CONTACTED
        assert record.rights.spdx.strip().upper() == "UNDETERMINED"
        assert record.rights.redistributable is False
        assert not record.rights_reviewed_by
        assert not record.review_packet
        assert live_gate_reasons(source_id), "new rows must carry live-gate reasons"
        with pytest.raises(IngestionNotPermitted):
            assert_loadable(record)


def test_bounded_protocols_and_adapters() -> None:
    """≤2 existing document protocols; each adapter names jurisdiction +
    allowlist, and every allowlisted predicate is an ontology term."""
    assert set(document_protocols()) == {"html_text", "pdf_text"}
    assert len(document_protocols()) <= 2
    from connectors.dossier_documents import _ontology_predicate_ids

    ontology = _ontology_predicate_ids()
    for source_id in DOSSIER_SOURCES:
        config = adapter_config(source_id)
        assert config["jurisdiction"].startswith("us.state_abbr:")
        allowlist = predicate_allowlist(source_id)
        assert allowlist
        unknown = allowlist - ontology
        assert not unknown, f"{source_id} allowlists non-ontology predicates: {unknown}"


# --- the frozen crosswalk ------------------------------------------------------


def test_crosswalk_is_clean_against_live_targets() -> None:
    assert check_crosswalk() == []


def test_every_crosswalk_row_names_an_existing_term_or_scoped_amendment() -> None:
    from connectors.dossier_documents import _ontology_predicate_ids

    ontology = _ontology_predicate_ids()
    for field_id, row in crosswalk()["fields"].items():
        status = str(row.get("status", "mapped"))
        if status == "mapped":
            assert str(row["predicate"]) in ontology, field_id
            assert str(row["dossier_field"]) in {str(q) for q in crosswalk()["dossier_fields"]}
            assert str(row["valid_time"]) in {str(k) for k in crosswalk()["valid_time_kinds"]}
            assert str(row.get("applicability") or "").strip()
        else:
            # The amendment route is recorded — never an ad-hoc predicate.
            assert status == "needs_amendment"
            assert "predicate" not in row
            assert str(row.get("amendment") or "").strip()


def test_unmapped_field_fails_closed() -> None:
    with pytest.raises(UnmappedField):
        field_map("per_plate_read")  # never a field — and never invented


def test_scoped_amendment_row_shape() -> None:
    row = field_map("execution_state")
    assert row["status"] == "needs_amendment"
    assert "instrument_execution_state" in row["amendment"]


# --- family runs: OKC -----------------------------------------------------------


def test_okc_usage_page_scoped_counts_and_future_effective_retention() -> None:
    report, _ = _run_doc("dossier_okc", "okc-flock-usage-2026")
    counts = _claims_for(report, "claimed_device_count")
    assert len(counts) == 1
    (count,) = counts
    assert count["value"] == 90
    scopes = {q["qualifier_id"]: q["value"] for q in count["qualifiers"]}
    assert scopes["count_scope"] == "city_owned"
    assert "partner" not in scopes["count_scope_detail"]

    (degree,) = _claims_for(report, "sharing_partner_degree")
    assert degree["value"] == 109
    dscopes = {q["qualifier_id"]: q["value"] for q in degree["qualifiers"]}
    assert dscopes["count_scope"] == "partner_agencies"

    (asof,) = _claims_for(report, "as_of")
    assert asof["value"] == "2026-08-18"

    # The future-effective retention clause keeps its STATED effective date —
    # never the capture date — and the exception survives verbatim alongside.
    (retention,) = _claims_for(report, "retention_period")
    assert retention["value"] == "7 days"
    assert retention["valid_from"] == "2026-10-01"
    assert "ongoing investigation" in retention["raw_context"]
    (exc,) = _claims_for(report, "use_restriction")
    assert "ongoing investigation" in exc["raw_value"]

    # Every claim carries capture provenance + a typed locator.
    for claim in _claims(report):
        assert claim["evidence"]["locator"]["kind"] == "byte_range"
        assert claim["evidence"]["extraction_method"] == "html_text"
        assert claim["sensitivity_class"] == "C1"


def test_okc_council_memo_publication_not_execution() -> None:
    report, _ = _run_doc("dossier_okc", "okc-council-memo-2026-08")
    (posted,) = _claims_for(report, "posted_date")
    assert posted["value"] == "2026-08-18"
    # posted_date is publication-classed: it may carry valid_from as the
    # document's posting date — distinct from any effective date.
    assert posted["valid_from"] == "2026-08-18"
    (lifecycle,) = _claims_for(report, "lifecycle_transition")
    assert lifecycle["value"] == "amendment 1 / renewal 3"
    (funding,) = _claims_for(report, "funding_amount")
    assert funding["value"] == 270000
    (period,) = _claims_for(report, "period")
    assert period["valid_from"] == "2026-07-01" and period["valid_to"] == "2027-06-30"
    # The memo is an agenda_document: it asserts NOTHING about execution.
    assert not _claims_for(report, "signed_date")
    assert not _claims_for(report, "amends_contract")


def test_okc_amendment_links_without_executing() -> None:
    report, _ = _run_doc("dossier_okc", "okc-flock-amendment-2026")
    (amends,) = _claims_for(report, "amends_contract")
    assert amends["value"] == "C241032"
    assert amends["subject_id"] == "contract:okc-flock-c241032-amendment-1"
    (sharing,) = _claims_for(report, "sharing_restriction")
    assert "federal law enforcement" in sharing["raw_value"]
    (carve,) = _claims_for(report, "use_restriction")
    assert "compulsory legal process" in carve["raw_value"]
    (policy,) = _claims_for(report, "written_policy_value")
    assert "controls over the Agreement" in policy["value"]
    # The incomplete signature line is a recorded field-state — TWO states:
    # the mapped signed_date row AND the unmapped execution_state amendment.
    states = _claims_for(report, "disclosure_field_state")
    assert {c["field_state"] for c in states} == {"present_but_empty"}
    assert {c["value"] for c in states} == {"signed_date", "execution_state"}
    (exec_state,) = [c for c in states if c["value"] == "execution_state"]
    assert "scoped amendment" in exec_state["assertion_rationale"]
    # Genre honesty: the instrument is `contract`, never `executed_contract`.
    artifacts = [r for r in report.claims if r.get("record_kind") == "evidence_artifact"]
    assert artifacts[0]["evidence_genre"] == "contract"


# --- family runs: Tulsa ---------------------------------------------------------


def test_tulsa_template_never_executes() -> None:
    report, _ = _run_doc("dossier_tulsa", "tulsa-mou-template")
    claims = _claims(report)
    assert claims, "a template still yields its structure + field-states"
    # EVERY claim on a template is D6 (non-probative) — the ADR-122 rule made
    # mechanical, not left to convention.
    assert all(c.get("claim_directness") == "D6" for c in claims)
    assert all(c.get("evidence_genre") == "template" for c in claims)
    # The guard bars every executed-instrument predicate: parties, signature
    # dates, values, term dates are field-states only.
    guarded = set(vocab()["template_execution_guard"])
    assert not [c for c in claims if c.get("predicate_id") in guarded]
    predicates = {c["predicate_id"] for c in claims}
    assert predicates == {"written_policy_value", "use_restriction", "disclosure_field_state"}
    states = {c["value"] for c in _claims_for(report, "disclosure_field_state")}
    assert states == {"buyer", "seller", "signed_date"}
    (purpose,) = _claims_for(report, "written_policy_value")
    assert "memorandum of understanding" in purpose["value"]


def test_tulsa_policy_113c_two_products_scoped_retention() -> None:
    report, _ = _run_doc("dossier_tulsa", "tulsa-policy-113c")
    techs = {c["value"] for c in _claims_for(report, "technology")}
    assert techs == {"Flock Safety fixed ALPR", "Axon Fleet 3 in-car ALPR"}
    (effective,) = _claims_for(report, "effective_from")
    assert effective["value"] == "2023-07-07"
    assert effective["valid_from"] == "2023-07-07"
    (retention,) = _claims_for(report, "retention_period")
    assert retention["value"] == "12 months"
    # The retention scope stays scoped to manually entered data — never
    # generalized to every scan (S2 caution), carried verbatim.
    assert "manually entered" in retention["raw_context"]
    (body,) = _claims_for(report, "enacting_body")
    assert body["value"] == "Tulsa Police Department"


def test_tulsa_policy_113e_absent_retention_is_a_recorded_state() -> None:
    report, _ = _run_doc("dossier_tulsa", "tulsa-policy-113e")
    (sharing,) = _claims_for(report, "sharing_restriction")
    assert "Chief of Police" in sharing["value"]
    # Reviewed 'absent': the field emits a disclosure_field_state claim whose
    # locator spans the whole document — searched everything, found nothing.
    (absent,) = _claims_for(report, "disclosure_field_state")
    assert absent["value"] == "retention_period"
    assert absent["field_state"] == "absent"
    assert absent["evidence"]["locator"]["kind"] == "page"
    # No fabricated retention value claim.
    assert not _claims_for(report, "retention_period")


# --- family runs: San Diego ------------------------------------------------------


def test_san_diego_subscription_is_access_not_hardware() -> None:
    report, _ = _run_doc("dossier_san_diego", "sd-asr-2025-vigilant")
    (edge,) = _claims_for(report, "configured_access_edge")
    assert edge["value"] is True
    (pooled,) = _claims_for(report, "pooled_lookup_participation")
    assert pooled["value"] is True
    (scope,) = _claims_for(report, "data_system_scope")
    assert scope["value"] == "vendor_cloud_shared"
    vendors = _claims_for(report, "vendor")
    (text_vendor,) = [c for c in vendors if not c.get("object_ref")]
    assert text_vendor["value"] == "Vigilant Solutions"
    # The partner-ref twin mints a scoped candidate under the vendor role.
    assert [c for c in vendors if c.get("object_ref")]
    (period,) = _claims_for(report, "period")
    assert period["value"] == "2025"
    # The subscription_hardware_guard bars every device/deployment predicate:
    # access ≠ local hardware (S2). Asserted two ways — nothing emitted, and
    # the guard itself refuses.
    guarded = set(vocab()["subscription_hardware_guard"])
    assert not [c for c in _claims(report) if c.get("predicate_id") in guarded]
    artifacts = [r for r in report.claims if r.get("record_kind") == "evidence_artifact"]
    assert artifacts[0]["access_mode"] == "subscription"


def test_san_diego_ubicquia_agreement_instrument_facts() -> None:
    report, _ = _run_doc("dossier_san_diego", "sd-ubicquia-agreement-2023")
    (buyer,) = [c for c in _claims_for(report, "buyer") if not c.get("object_ref")]
    assert buyer["value"] == "City of San Diego"
    (seller,) = [c for c in _claims_for(report, "seller") if not c.get("object_ref")]
    assert seller["value"] == "Ubicquia, Inc."
    (vendor,) = [c for c in _claims_for(report, "vendor") if not c.get("object_ref")]
    assert vendor["value"] == "Flock Safety, Inc."
    (value,) = _claims_for(report, "contract_value")
    assert value["value"] == 11662500
    assert value["object_type"] == "quantity" and value["unit"] == "USD"
    (count,) = _claims_for(report, "contracted_device_count")
    assert count["value"] == 500
    scopes = {q["qualifier_id"]: q["value"] for q in count["qualifiers"]}
    assert scopes["count_scope"] == "contracted_units"
    (signed,) = _claims_for(report, "signed_date")
    assert signed["value"] == "2023-12-15"
    # City execution is NOT visually verified: the unmapped execution_state
    # field emits only its scoped-amendment field-state — no fabricated verdict.
    (exec_state,) = _claims_for(report, "disclosure_field_state")
    assert exec_state["value"] == "execution_state"
    assert exec_state["field_state"] == "present_but_empty"
    artifacts = [r for r in report.claims if r.get("record_kind") == "evidence_artifact"]
    assert artifacts[0]["evidence_genre"] == "contract"


def test_san_diego_indexes_list_links_only() -> None:
    for source_id, doc_id, expected in (
        ("dossier_san_diego", "sd-technology-index", 3),
        ("dossier_san_diego", "sd-pab-index", 2),
    ):
        report, _ = _run_doc(source_id, doc_id)
        docs = _claims_for(report, "document")
        titles = _claims_for(report, "title")
        assert len(docs) == len(titles) == expected
        for doc in docs:
            assert doc["value"].startswith("https://www.sandiego.gov/")
            assert doc["evidence"]["locator"]["kind"] == "byte_range"
        index_pages = [r for r in report.claims if r.get("record_kind") == "index_page"]
        assert index_pages and index_pages[0]["listings_resolved"] == expected

    report, _ = _run_doc("dossier_san_diego", "sd-technology-index")
    (posted,) = _claims_for(report, "posted_date")
    assert posted["value"] == "Posted: 2026-02-15"
    # A posted date is never promoted to an effective date: posted_date's row
    # is publication-classed and the claim carries the publication valid_from
    # only when the reviewer declares it — this listing declares none.
    assert "valid_from" not in posted


# --- the guards themselves -------------------------------------------------------


def test_template_guard_refuses_execution_predicates() -> None:
    for predicate in ("buyer", "signed_date", "contract_value", "lifecycle_transition"):
        with pytest.raises(GenreGuardViolation):
            assert_genre_permits(
                "dossier_tulsa",
                document_genre="template",
                access_mode="document",
                predicate=predicate,
                doc_id="tulsa-mou-template",
            )


def test_subscription_guard_refuses_hardware_predicates() -> None:
    for predicate in ("claimed_device_count", "contracted_device_count", "deployment_exists"):
        with pytest.raises(GenreGuardViolation):
            assert_genre_permits(
                "dossier_san_diego",
                document_genre="official_statement",
                access_mode="subscription",
                predicate=predicate,
                doc_id="sd-asr-2025-vigilant",
            )


def test_allowlist_bars_out_of_scope_predicate() -> None:
    with pytest.raises(GenreGuardViolation):
        assert_genre_permits(
            "dossier_tulsa",
            document_genre="agency_policy",
            access_mode="document",
            predicate="configured_access_edge",  # a dossier_san_diego term
            doc_id="tulsa-policy-113c",
        )


def test_part_viii_guard_shared_not_forked() -> None:
    """The dossier adapter consumes the OKC Part VIII guard — a plate-token
    literal is refused even though the field would otherwise resolve."""
    with pytest.raises(PartVIIIViolation):
        assert_part_viii_safe("retention_period", "manually entered license plate data")
    # Same refusal end-to-end: a captured page carrying a plate-token literal
    # locates fine, then the claim-builder refuses it before any claim exists.
    target = _target("dossier_okc", "okc-flock-usage-2026")
    target["fields"] = [
        {"field": "claimed_count", "literal": "license plate reader count is 90", "value": 90}
    ]
    body = b"<html><body><p>license plate reader count is 90</p></body></html>"
    ctx, sink = _single_target_ctx("dossier_okc", "okc-flock-usage-2026", body, "text/html")
    ctx = dataclasses.replace(ctx, parameters={"targets": [target]})
    with pytest.raises(PartVIIIViolation):
        run(_connector(), ctx)
    assert _claims(sink.claims) == []


def test_no_claim_mints_a_person() -> None:
    report, _ = _run_source("dossier_san_diego")
    for claim in _claims(report):
        assert claim.get("object_type") != "person"


# --- organisation-role entity-ref twins (P32.3) -----------------------------------


def test_vendor_role_mints_scoped_entity_ref_twin() -> None:
    report, _ = _run_doc("dossier_san_diego", "sd-ubicquia-agreement-2023")
    twins = [
        c
        for c in _claims(report)
        if c.get("object_ref") and c.get("predicate_id") in {"buyer", "seller", "vendor"}
    ]
    assert len(twins) == 3
    by_predicate = {c["predicate_id"]: c for c in twins}
    assert by_predicate["buyer"]["object_ref"]["role"] == "buyer"
    assert by_predicate["seller"]["object_ref"]["role"] == "vendor"
    assert by_predicate["vendor"]["object_ref"]["role"] == "vendor"
    # Name-only mints are jurisdiction-scoped candidates — never merged.
    for twin in twins:
        ref = twin["object_ref"]
        assert ref["scheme"] == "sig.org.name_scoped"
        assert ref["jurisdiction"] == "us.state_abbr:CA"
        assert ref["candidate"] is True


# --- failure behaviour: explicit, bounded, no partial claims ---------------------


def _single_target_ctx(source_id: str, doc_id: str, body: bytes, media: str):
    target = _target(source_id, doc_id)
    transport = _MapTransport()
    transport.add_url(str(target["url"]), body, media)
    sink = InMemoryClaimSink()
    ctx = _ctx(source_id, [target], sink=sink, transport=transport)
    return ctx, sink


def test_malformed_pdf_is_explicit_failure_no_claims() -> None:
    body = (_FIX / "malformed_document.pdf").read_bytes()
    ctx, sink = _single_target_ctx(
        "dossier_okc", "okc-flock-amendment-2026", body, "application/pdf"
    )
    with pytest.raises(ContentDrift, match="no text layer"):
        run(_connector(), ctx)
    # A failed document emits NO partial affirmative claim — the sink stays empty.
    assert _claims(sink.claims) == []


def test_encrypted_pdf_is_explicit_failure_no_claims(tmp_path: Path) -> None:
    from pypdf import PdfReader, PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret-password")
    enc = tmp_path / "encrypted.pdf"
    with enc.open("wb") as fh:
        writer.write(fh)
    body = enc.read_bytes()
    assert PdfReader(enc).is_encrypted
    ctx, sink = _single_target_ctx(
        "dossier_okc", "okc-flock-amendment-2026", body, "application/pdf"
    )
    with pytest.raises(ContentDrift):
        run(_connector(), ctx)
    assert _claims(sink.claims) == []


def test_oversized_document_refused_before_parse() -> None:
    bound = int(resource_bounds()["max_document_bytes"])
    body = b"<html><body>" + b"x" * bound + b"</body></html>"
    ctx, sink = _single_target_ctx("dossier_okc", "okc-flock-usage-2026", body, "text/html")
    with pytest.raises(ContentDrift, match="over the .*-byte bound"):
        run(_connector(), ctx)
    assert _claims(sink.claims) == []


def test_unsupported_format_is_explicit_failure() -> None:
    body = b'{"kind":"json","not":"a document protocol"}'
    ctx, sink = _single_target_ctx("dossier_okc", "okc-flock-usage-2026", body, "application/json")
    with pytest.raises(ContentDrift, match="not a supported format"):
        run(_connector(), ctx)
    assert _claims(sink.claims) == []


def test_absent_reviewed_literal_is_recorded_drift() -> None:
    """A captured page that no longer carries the reviewed literal is drift —
    the connector never emits a claim beyond the captured bytes."""
    body = (
        (_FIX / "okc_usage_page.html")
        .read_bytes()
        .replace(b"90 city-owned LPR readers", b"several readers")
    )
    ctx, sink = _single_target_ctx("dossier_okc", "okc-flock-usage-2026", body, "text/html")
    with pytest.raises(ContentDrift, match="literal for field 'claimed_count'"):
        run(_connector(), ctx)
    assert _claims(sink.claims) == []


def test_unconfigured_capture_url_never_emits() -> None:
    """A capture whose source URI names no reviewed target is drift — the
    adapter reads only reviewed targets (multi-target context, no guessing)."""
    targets = [dict(t) for t in live_targets("dossier_okc")]  # 3 targets
    ctx = _ctx("dossier_okc", targets)
    # A capture from a URI the configured set never names: defense-in-depth —
    # claims are never built off an unbound capture.
    capture = ctx.captures.put(
        b"<html>x</html>",
        media_type="text/html",
        source_uri="https://www.okc.gov/unreviewed/page",
        retrieved_at=_RETRIEVED,
    )
    with pytest.raises(ContentDrift, match="no configured dossier target"):
        _connector().parse(ctx, capture)


def test_index_link_fanout_is_bounded() -> None:
    bound = int(resource_bounds()["max_index_links"])
    links = "".join(f'<li><a href="/d/{i}">doc {i}</a></li>' for i in range(bound + 1))
    body = f"<html><body><ul>{links}</ul></body></html>".encode()
    ctx, _ = _single_target_ctx("dossier_san_diego", "sd-pab-index", body, "text/html")
    with pytest.raises(ContentDrift, match="link bound"):
        run(_connector(), ctx)


def test_absent_state_probe_present_is_drift() -> None:
    """A field reviewed 'absent' whose probe literal DOES appear is drift —
    the reviewed absence no longer holds on the captured bytes."""
    target = _target("dossier_tulsa", "tulsa-policy-113e")
    for field in target["fields"]:
        if field["field"] == "retention_period":
            field["label"] = "Chief of Police"  # a phrase that IS in the capture
    ctx, sink = _single_target_ctx(
        "dossier_tulsa",
        "tulsa-policy-113e",
        (_FIX / "tulsa_policy_113e.pdf").read_bytes(),
        "application/pdf",
    )
    # Rebind the mutated target into the context (transport already serves it).
    ctx = dataclasses.replace(ctx, parameters={"targets": [target]})
    with pytest.raises(ContentDrift, match="reviewed 'absent' but its literal"):
        run(_connector(), ctx)
    assert _claims(sink.claims) == []


def test_redacted_field_emits_somevalue_never_fabricated() -> None:
    """A redacted field records 'a value exists, unknown' — a somevalue claim
    under the mapped predicate, never a fabricated literal."""
    target = _target("dossier_san_diego", "sd-ubicquia-agreement-2023")
    for field in target["fields"]:
        if field["field"] == "signed_date":
            field["state"] = "redacted"
            field["label"] = "Vendor Date:"
            field.pop("literal", None)
            field.pop("value", None)
    report = run(_connector(), _ctx("dossier_san_diego", [target]))
    (redacted,) = _claims_for(report, "signed_date")
    assert redacted["value"] is None
    assert redacted["value_kind"] == "somevalue"
    assert redacted["field_state"] == "redacted"


def test_needs_amendment_field_never_emits_value_claim() -> None:
    """execution_state has no existing predicate: it emits only the
    disclosure_field_state row carrying the scoped amendment — never a value."""
    report, _ = _run_doc("dossier_san_diego", "sd-ubicquia-agreement-2023")
    for claim in _claims(report):
        assert claim.get("predicate_id") != "instrument_execution_state"
    (state,) = [
        c for c in _claims_for(report, "disclosure_field_state") if c["value"] == "execution_state"
    ]
    assert "scoped" in state["assertion_rationale"]


# --- determinism / no-network -----------------------------------------------------


def test_same_fixture_replays_deterministically() -> None:
    for source_id in DOSSIER_SOURCES:
        report, ctx = _run_source(source_id)
        replay_a = replay(_connector(), ctx, report.captures)
        replay_b = replay(_connector(), ctx, report.captures)
        assert replay_fingerprint(replay_a) == replay_fingerprint(replay_b)
        diff = shadow_replay(_connector(), ctx, report.captures, report.claims)
        assert diff.changed_count == 0, f"{source_id} shadow diff: {diff.summary()}"


def test_replay_emits_no_network_and_no_assertion() -> None:
    """Post-capture stages are pure functions of the stored bytes: replay
    asserts nothing and the canned transport is never asked again."""
    source_id = "dossier_okc"
    targets = [dict(t) for t in live_targets(source_id)]
    transport = _MapTransport()
    for target in targets:
        doc_id = str(target.get("doc_id") or target.get("id"))
        name, media = FIXTURE_FOR_DOC[doc_id]
        transport.add_url(str(target["url"]), (_FIX / name).read_bytes(), media)
    sink = InMemoryClaimSink()
    ctx = _ctx(source_id, targets, sink=sink, transport=transport)
    report = run(_connector(), ctx)
    fetched = len(transport.requested)
    assert fetched == len(targets)
    replayed = replay(_connector(), ctx, report.captures)
    assert len(transport.requested) == fetched  # replay opened no request
    assert _claims(replayed)  # the replayed claim set is non-empty


# --- the typed assertion envelope --------------------------------------------------


def test_every_claim_survives_the_typed_assertion_adapter() -> None:
    """P32.2's contract: emitted records convert to sig.assertion/1 rows
    without rejections."""
    from db.assertion import Rejection, assertion_from_record

    for source_id in DOSSIER_SOURCES:
        report, _ = _run_source(source_id)
        rejections = [
            r
            for r in (assertion_from_record(c) for c in _claims(report))
            if isinstance(r, Rejection)
        ]
        assert not rejections, f"{source_id}: {rejections[:2]}"


def test_claim_provenance_fields_complete() -> None:
    """Every emitted claim carries the P32.3 provenance spine: source, capture
    binding (digest via artifact row), locator, raw literal, dossier field,
    sensitivity tier and crosswalk normalization id."""
    report, _ = _run_source("dossier_okc")
    artifacts = [r for r in report.claims if r.get("record_kind") == "evidence_artifact"]
    assert len(artifacts) == 3
    for claim in _claims(report):
        assert claim["source_id"] == "dossier_okc"
        assert claim["source_attribution"] == "dossier_okc"
        assert claim["raw_value"]
        assert claim["evidence"]["source_url"]
        assert claim["evidence"]["retrieved_date"] == _RETRIEVED.date().isoformat()
        assert claim["evidence"]["locator"]["kind"]
        assert claim["dossier_field"].startswith("q")
        assert claim["source_field"]
        assert claim["sensitivity_class"] == "C1"
        assert claim["normalization_id"] == "dossier-field-crosswalk"


# --- licence / compartment preservation --------------------------------------------


def test_undetermined_rights_fail_the_export_gate_closed() -> None:
    from connectors.loader import assert_export_compatible
    from policy.licensing import ExportGateClosed

    for source_id in DOSSIER_SOURCES:
        with pytest.raises(ExportGateClosed, match="UNDETERMINED"):
            assert_export_compatible([source_id])


def test_claims_carry_the_source_compartment_and_tier() -> None:
    """Licence compartment preservation: claims keep their source attribution
    and the adapter's declared C1 sensitivity class — nothing is promoted."""
    for source_id in DOSSIER_SOURCES:
        report, _ = _run_source(source_id)
        for claim in _claims(report):
            assert claim["source_id"] == source_id
            assert claim["sensitivity_class"] == "C1"
            assert claim["geo_tier"] is not None


# --- golden field→locator outputs ----------------------------------------------------


def _golden() -> dict[str, Any]:
    """The golden field→locator rows the reviewed field map must reproduce.

    One row per emitted claim — field, predicate, verbatim literal and typed
    locator — so a duplicated field (113C's two technologies) still pins every
    claim's evidence span, and a locator drift fails loudly."""
    golden: dict[str, Any] = {}
    for source_id in DOSSIER_SOURCES:
        for target in live_targets(source_id):
            doc_id = str(target.get("doc_id") or target.get("id"))
            report, _ = _run_doc(source_id, doc_id)
            rows = [
                {
                    "field": str(claim.get("source_field") or ""),
                    "predicate": str(claim.get("predicate_id") or ""),
                    "raw_value": str(claim.get("raw_value") or ""),
                    "locator": claim["evidence"]["locator"],
                }
                for claim in _claims(report)
                if not claim.get("object_ref")  # entity-ref twins share the row's locator
            ]
            golden[doc_id] = rows
    return golden


def test_golden_field_to_locator_outputs() -> None:
    golden_path = _FIX / "golden_locators.json"
    expected = json.loads(golden_path.read_text())
    actual = _golden()
    assert actual == expected, (
        "field→locator outputs drifted — regenerate golden_locators.json only "
        "after the reviewed field map itself is re-reviewed"
    )


def test_golden_file_covers_every_configured_target() -> None:
    golden = json.loads((_FIX / "golden_locators.json").read_text())
    assert sorted(golden) == sorted(FIXTURE_FOR_DOC)

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `accountability` connector (§23.8, §§11.17–11.18, P13.1).

Anchored on the Phase-13 acceptance criteria sub-set to this ticket: epistemic_status
REQUIRED and preserved verbatim (SIG-ONTO-038), all six OL-2E-AL-03 source classes
linkable with the class recorded (SIG-ONTO-039), the predicate allowlist as a hard
schema gate (SIG-INGEST-033), the upstream record categories crosswalked not adopted
wholesale (§23.8), and CourtListener as targeted-lookup only (§22.2).
"""

from __future__ import annotations

import dataclasses
import json

import pytest
from connectors.accountability import (
    AccountabilityConnector,
    AccountabilityEventRecord,
    CrawlAttempted,
    EvidenceLink,
    InvalidSourceClass,
    LegalProceedingRecord,
    MissingEpistemicStatus,
    PredicateNotAllowed,
    assert_predicate_allowed,
    assert_targeted_lookup,
    atlas_artifacts,
    category_crosswalk,
    epistemic_statuses,
    event_types,
    forbidden_predicate_genres,
    is_predicate_allowed,
    postures,
    predicate_allowlist,
    source_classes,
    source_ids,
)
from connectors.registry import get
from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun
from support import load_schemaview

_SIX_CLASSES = (
    "primary_record",
    "court_record",
    "agency_statement",
    "vendor_statement",
    "investigative_article",
    "advocacy_analysis",
)


# --- fixtures -----------------------------------------------------------------


def _ingest_run() -> IngestRun:
    return IngestRun(
        connector_name="accountability",
        connector_version="1.0.0",
        code_commit="deadbeef",
        ruleset_version="r1",
        vocab_version="v1",
        input_digests=(),
    )


def _ctx(source_key: str = "accountability_atlas") -> RunContext:
    source = dataclasses.replace(get(source_ids()[source_key]), ingestion_permitted=True)
    return RunContext(
        source=source,
        run=_ingest_run(),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )


def _capture(ctx: RunContext, data: bytes, *, source_uri: str, media_type: str):
    return ctx.captures.put(data, media_type=media_type, source_uri=source_uri)


# --- SIG-ONTO-038: epistemic_status required + preserved verbatim -------------


def test_epistemic_status_is_required_on_write() -> None:
    with pytest.raises(MissingEpistemicStatus):
        AccountabilityEventRecord(external_id="i1", source_id="s", epistemic_status="")


def test_epistemic_status_outside_the_vocabulary_is_rejected() -> None:
    from connectors.accountability import InvalidAccountabilityEvent

    with pytest.raises(InvalidAccountabilityEvent):
        AccountabilityEventRecord(external_id="i1", source_id="s", epistemic_status="probably")


def test_epistemic_status_is_preserved_verbatim_on_the_claim_rows() -> None:
    event = AccountabilityEventRecord(
        external_id="i1",
        source_id="alpr_accountability_atlas",
        epistemic_status="alleged",
        raw_epistemic_status="Alleged in a pending suit",
        event_type="wrongful_arrest",
    )
    rows = event.claim_rows()
    status_rows = [r for r in rows if r["predicate_id"] == "event_epistemic_status"]
    assert len(status_rows) == 1
    # the typed value is the exact vocabulary term; the raw upstream wording is kept (P2).
    assert status_rows[0]["value"] == "alleged"
    assert status_rows[0]["raw_value"] == "Alleged in a pending suit"
    # it is emitted under the ontology's registered predicate so RESOLVE() carries it.
    assert status_rows[0]["predicate_id"] == "event_epistemic_status"


# --- SIG-ONTO-039: six source classes linkable, class recorded ---------------


def test_an_incident_links_to_all_six_source_classes_with_the_class_recorded() -> None:
    links = tuple(
        EvidenceLink(source_ref=f"https://example/{cls}", source_class=cls) for cls in _SIX_CLASSES
    )
    event = AccountabilityEventRecord(
        external_id="i1", source_id="s", epistemic_status="reported", sources=links
    )
    rows = event.claim_rows()
    link_rows = [r for r in rows if r["record_kind"] == "evidence_link"]
    assert len(link_rows) == 6
    # every link carries its OL-2E-AL-03 class.
    recorded = {r["source_class"] for r in link_rows}
    assert recorded == set(_SIX_CLASSES)
    for r in link_rows:
        assert r["source_class"] in source_classes()


def test_advocacy_only_claim_is_distinguishable_from_a_court_record_claim() -> None:
    advocacy_only = AccountabilityEventRecord(
        external_id="a",
        source_id="s",
        epistemic_status="alleged",
        sources=(EvidenceLink("https://adv", "advocacy_analysis"),),
    )
    court_backed = AccountabilityEventRecord(
        external_id="b",
        source_id="s",
        epistemic_status="adjudicated",
        sources=(EvidenceLink("https://court", "court_record"),),
    )
    assert advocacy_only.rests_only_on("advocacy_analysis")
    assert not advocacy_only.rests_only_on("court_record")
    assert court_backed.rests_only_on("court_record")
    assert advocacy_only.source_class_set != court_backed.source_class_set


def test_an_out_of_vocabulary_source_class_is_rejected() -> None:
    with pytest.raises(InvalidSourceClass):
        EvidenceLink(source_ref="https://x", source_class="a_blog_i_like")


# --- SIG-INGEST-033: the predicate allowlist as a hard schema gate -----------


def test_the_allowlist_is_the_only_write_set() -> None:
    for predicate in predicate_allowlist():
        assert assert_predicate_allowed(predicate) == predicate


def test_a_forbidden_predicate_is_refused_at_the_ingest_boundary() -> None:
    # Policy / LegalInstrument is P13.2, not this connector.
    for genre in ("policy", "legal_instrument", "deployment_exists", "device_count"):
        assert not is_predicate_allowed(genre)
        with pytest.raises(PredicateNotAllowed):
            assert_predicate_allowed(genre)


def test_forbidden_genres_are_outside_the_allowlist() -> None:
    for genre in forbidden_predicate_genres():
        assert not is_predicate_allowed(genre), genre


# --- §23.8: crosswalk the upstream categories, never adopt wholesale ---------


def test_upstream_categories_are_crosswalked_not_adopted_wholesale() -> None:
    mapping = category_crosswalk("wrongful_stop_false_alert")
    assert mapping is not None
    # the SIG event_type is a member of the frozen vocabulary, not the raw upstream label.
    assert mapping["event_type"] in event_types()
    assert mapping["event_type"] == "false_stop"
    # crosswalk provenance is carried (SKOS relation + lossy flag), like the atlas connector.
    assert mapping["relation"] in {"closeMatch", "broadMatch", "narrowMatch", "relatedMatch"}


def test_a_litigation_category_spawns_a_proceeding_and_defaults_to_alleged() -> None:
    mapping = category_crosswalk("litigation")
    assert mapping is not None
    assert mapping["creates_proceeding"] is True
    # a filed lawsuit's allegations are `alleged` until a court adjudicates them.
    assert mapping["epistemic_default"] == "alleged"


def test_an_unmapped_category_yields_a_research_task_never_a_guess() -> None:
    ctx = _ctx()
    conn = AccountabilityConnector()
    row = conn._normalize_issue_record(  # noqa: SLF001 - exercising the crosswalk boundary
        ctx, {"id": "x1", "category": "something_the_atlas_invented_yesterday"}
    )
    assert len(row) == 1
    assert row[0]["record_kind"] == "unmapped_category"
    assert row[0]["research_task"]["task_type"] == "unmapped_accountability_category"


# --- §22.2 / SIG-INGEST-036/037: CourtListener is targeted-lookup only -------


def test_a_known_docket_lookup_is_allowed() -> None:
    target = {
        "url": "https://www.courtlistener.com/api/rest/v4/dockets/12345/",
        "docket_id": "12345",
    }
    assert assert_targeted_lookup(target) is target


def test_crawling_the_court_api_is_refused() -> None:
    with pytest.raises(CrawlAttempted):
        assert_targeted_lookup(
            {"mode": "crawl", "url": "https://www.courtlistener.com/api/rest/v4/dockets/"}
        )
    with pytest.raises(CrawlAttempted):
        assert_targeted_lookup({"url": "https://www.courtlistener.com/api/rest/v4/dockets/"})
    with pytest.raises(CrawlAttempted):
        assert_targeted_lookup({"url": "https://www.courtlistener.com/api/rest/v4/search/?q=alpr"})


def test_discover_refuses_a_courtlistener_crawl_target() -> None:
    ctx = _ctx("courtlistener")
    ctx = dataclasses.replace(ctx, parameters={"targets": [{"mode": "list", "url": "x"}]})
    with pytest.raises(CrawlAttempted):
        AccountabilityConnector().discover(ctx)


# --- §23.8: all five Atlas artifacts are consumed ----------------------------


def test_all_five_atlas_artifacts_are_named_and_consumed() -> None:
    assert set(atlas_artifacts()) == {
        "issue_record_csv",
        "source_index_csv",
        "geojson",
        "data_dictionary",
        "research_archive",
    }


def test_issue_record_csv_produces_epistemically_honest_events() -> None:
    ctx = _ctx()
    conn = AccountabilityConnector()
    csv_bytes = (
        b"id,category,epistemic_status,agency,source_url\n"
        b"inc-1,wrongful_stop_false_alert,alleged,Oklahoma City PD,https://news/story\n"
    )
    cap = _capture(
        ctx, csv_bytes, source_uri="https://alpratlas.org/issue_records.csv", media_type="text/csv"
    )
    parsed = conn.parse(ctx, cap)
    assert parsed["kind"] == "issue_record_csv"
    raw = conn.extract(ctx, parsed)
    rows = conn.normalize(ctx, raw)
    events = [r for r in rows if r["record_kind"] == "accountability_event"]
    assert len(events) == 1
    assert events[0]["epistemic_status"] == "alleged"
    assert events[0]["upstream_category"] == "wrongful_stop_false_alert"


def test_an_upstream_epistemic_label_is_normalized_but_kept_verbatim() -> None:
    # "carried verbatim from the upstream where provided" (SIG-ONTO-038): the raw
    # upstream string is preserved; the typed value is the vocabulary term.
    ctx = _ctx()
    conn = AccountabilityConnector()
    csv_bytes = (
        b"id,category,epistemic_status,source_url\n"
        b"inc-9,wrongful_stop_false_alert,Alleged,https://news/x\n"
    )
    cap = _capture(
        ctx, csv_bytes, source_uri="https://alpratlas.org/issue.csv", media_type="text/csv"
    )
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))
    status = [r for r in rows if r["predicate_id"] == "event_epistemic_status"][0]
    assert status["value"] == "alleged"  # typed value on the vocabulary
    assert status["raw_value"] == "Alleged"  # upstream string preserved verbatim (P2)


def test_an_upstream_epistemic_label_outside_the_vocabulary_is_not_guessed() -> None:
    ctx = _ctx()
    conn = AccountabilityConnector()
    # no crosswalk default (category omitted) + an out-of-vocab label => unmapped, never guessed.
    row = conn._normalize_issue_record(  # noqa: SLF001
        ctx, {"id": "z1", "epistemic_status": "probably true"}
    )
    assert row[0]["record_kind"] == "unmapped_category"


def test_source_index_csv_types_each_source_per_ol_2e_al_03() -> None:
    ctx = _ctx()
    conn = AccountabilityConnector()
    csv_bytes = b"id,source_class,source_url\ninc-1,court_record,https://courtlistener/docket/1\n"
    cap = _capture(
        ctx, csv_bytes, source_uri="https://alpratlas.org/source-index.csv", media_type="text/csv"
    )
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))
    links = [r for r in rows if r["record_kind"] == "evidence_link"]
    assert len(links) == 1
    assert links[0]["source_class"] == "court_record"


def test_a_geojson_artifact_is_consumed_as_context_not_a_device_layer() -> None:
    ctx = _ctx()
    conn = AccountabilityConnector()
    geo = json.dumps({"type": "FeatureCollection", "features": []}).encode("utf-8")
    cap = _capture(
        ctx,
        geo,
        source_uri="https://alpratlas.org/incidents.geojson",
        media_type="application/geo+json",
    )
    parsed = conn.parse(ctx, cap)
    assert parsed["kind"] == "geojson"
    # context artifacts carry no claims — they are authority/provenance, not facts.
    assert conn.normalize(ctx, conn.extract(ctx, parsed)) == []


def test_courtlistener_payload_becomes_a_court_record_backed_proceeding() -> None:
    ctx = _ctx("courtlistener")
    conn = AccountabilityConnector()
    payload = json.dumps(
        {"id": 999, "docket_number": "5:24-cv-1", "case_name": "Doe v. City", "posture": "pending"}
    ).encode("utf-8")
    cap = _capture(
        ctx,
        payload,
        source_uri="https://www.courtlistener.com/api/rest/v4/dockets/999/",
        media_type="application/json",
    )
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))
    proceedings = [r for r in rows if r["record_kind"] == "legal_proceeding"]
    assert len(proceedings) == 1
    links = [r for r in rows if r["record_kind"] == "evidence_link"]
    # a court record is a court_record-class link by construction (SIG-ONTO-039).
    assert links and all(link["source_class"] == "court_record" for link in links)


def test_abuse_library_entries_are_index_only_advocacy_links_never_facts() -> None:
    ctx = _ctx("abuse_library")
    conn = AccountabilityConnector()
    payload = json.dumps(
        {"entries": [{"incident": "inc-1", "url": "https://library.kansas.watch/x"}]}
    ).encode("utf-8")
    cap = _capture(
        ctx,
        payload,
        source_uri="https://library.kansas.watch/index.json",
        media_type="application/json",
    )
    rows = conn.normalize(ctx, conn.extract(ctx, conn.parse(ctx, cap)))
    links = [r for r in rows if r["record_kind"] == "evidence_link"]
    assert len(links) == 1
    assert links[0]["source_class"] == "advocacy_analysis"
    assert links[0]["index_only"] is True  # OL-2E-AL-02: an index, not normalized to a fact.


# --- LegalProceeding posture validation (§11.18) -----------------------------


def test_a_proceeding_posture_outside_the_vocabulary_is_rejected() -> None:
    from connectors.accountability import InvalidLegalProceeding

    with pytest.raises(InvalidLegalProceeding):
        LegalProceedingRecord(external_id="p1", source_id="s", posture="vibes")


# --- Vocabulary lock-step with the frozen ontology enums (§§11.17–11.18) -----


def test_epistemic_status_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    assert epistemic_statuses() == set(sv.get_enum("EpistemicStatus").permissible_values)


def test_event_type_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    assert event_types() == set(sv.get_enum("AccountabilityEventType").permissible_values)


def test_posture_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    assert postures() == set(sv.get_enum("ProceedingPosture").permissible_values)


def test_source_class_vocab_matches_the_ontology_enum() -> None:
    sv = load_schemaview()
    assert source_classes() == set(sv.get_enum("SourceClass").permissible_values)

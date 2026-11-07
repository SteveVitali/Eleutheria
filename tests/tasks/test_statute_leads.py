# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Statute-seeded records leads (P37.14, SIG-INGEST-025a/b/c).

The catalog acceptance shape: **each statute duty produces a gap row or a
CoverageRecord** — a mandate is a records-acquisition lead, never a feed. The
generator is desk-research only (no fetch, no send, no flips).
"""

from __future__ import annotations

import pytest
from connectors.france_belgium import (
    LEGAL_INSTRUMENT_PUBLISH_GATE,
    LegalInstrument,
)
from connectors.registry import registry as source_registry
from inference.coverage import CoverageRecord
from tasks.statute_leads import (
    LEADS_SCHEMA,
    DutyPosture,
    OneTimeSurveyArtifact,
    StatuteLeadsError,
    _seed_duty_ids,
    generate_leads,
    load_leads_table,
)

DUTY_IDS = {
    "future_statutory_disclosure_va",
    "future_statutory_disclosure_nm",
    "future_statutory_disclosure_al",
    "future_statutory_disclosure_ar",
    "future_statutory_disclosure_ut",
    "future_statutory_disclosure_mn",
}


def _instrument(**kw) -> LegalInstrument:
    base = dict(external_id="x:1", source_id="src", instrument_type="statute")
    base.update(kw)
    return LegalInstrument(**base)


# --- the leads table ----------------------------------------------------------


def test_leads_table_parses_and_covers_every_seed_duty() -> None:
    duties, artifacts = load_leads_table()
    assert {d.duty_id for d in duties} == DUTY_IDS
    # Fail-closed join: the leads table covers exactly the seed's duty ids.
    assert {d.duty_id for d in duties} == set(_seed_duty_ids())
    assert len(artifacts) == 1


def test_every_duty_id_is_a_registered_source() -> None:
    registered = source_registry()
    for d in load_leads_table()[0]:
        assert d.duty_id in registered
        assert registered[d.duty_id].ingestion_permitted is False


# --- the acceptance shape: one output per statute duty ------------------------


def test_each_statute_duty_produces_a_gap_row_or_a_coverage_record() -> None:
    result = generate_leads()
    outputs = {lead.duty_id for lead in result.gap_rows}
    for d in load_leads_table()[0]:
        # exactly one of lead / coverage per duty — never both, never none.
        if d.requestable:
            assert d.duty_id in outputs
        else:
            assert any(
                c.jurisdiction_id == f"us.state:{d.state}"
                and c.predicate_id == "statutory_disclosure_artifact"
                for c in result.coverage
            )


def test_commenced_duties_emit_requestable_leads() -> None:
    leads = {lead.duty_id: lead for lead in generate_leads().gap_rows}
    for duty_id in (
        "future_statutory_disclosure_va",
        "future_statutory_disclosure_al",
        "future_statutory_disclosure_ar",
        "future_statutory_disclosure_ut",
    ):
        lead = leads[duty_id]
        assert lead.mandated_artifacts
        assert lead.record_holder
        assert lead.text_ref.startswith("https://")
        assert lead.as_dict()["requestable"] is True


def test_nm_not_yet_due_is_a_not_applicable_coverage() -> None:
    cov = next(c for c in generate_leads().coverage if "New Mexico" in c.jurisdiction_id)
    assert cov.absence_kind == "not_applicable"
    assert "2027-04-01" in (cov.search_method or "")  # future-ok: real-world: the registered duty's first-reports due date


def test_mn_contingent_duty_is_a_not_researched_coverage() -> None:
    """An unverified mandate can never mint a requestable lead (S5 guard)."""
    cov = next(c for c in generate_leads().coverage if "Minnesota" in c.jurisdiction_id)
    assert cov.absence_kind == "not_researched"


def test_table_rejects_a_row_for_an_unregistered_duty(monkeypatch) -> None:
    duties, artifacts = load_leads_table()
    bad = duties[0].__class__(**{**duties[0].__dict__, "duty_id": "future_statutory_disclosure_xx"})
    monkeypatch.setattr(
        "tasks.statute_leads.load_leads_table", lambda: ((bad, *duties[1:]), artifacts)
    )
    with pytest.raises(StatuteLeadsError):
        generate_leads()


# --- the one-time auditor-survey artifact + no-follow-up coverage -------------


def test_auditor_survey_is_one_time_desk_research_only() -> None:
    (artifact,) = load_leads_table()[1]
    assert isinstance(artifact, OneTimeSurveyArtifact)
    assert artifact.artifact_type == "state_auditor_survey"
    assert artifact.capture_status == "not_attempted"  # gated rows — no capture
    assert artifact.recurrence_expected is False
    assert artifact.survey_rows == 381
    # the gated registry rows it cites — never flipped
    for sid in artifact.source_ids:
        assert source_registry()[sid].ingestion_permitted is False


def test_no_follow_up_is_a_searched_not_found_coverage() -> None:
    (artifact,) = load_leads_table()[1]
    cov = artifact.no_follow_up_coverage()
    assert isinstance(cov, CoverageRecord)
    assert cov.absence_kind == "searched_not_found"
    assert cov.sources_searched  # SIG-METRIC-001/002 requires naming the sources
    assert "California" in (cov.jurisdiction_id or "")
    # the no-follow-up record rides the generated coverage set too
    assert any(c.predicate_id == "state_auditor_survey" for c in generate_leads().coverage)


# --- the LegalInstrument session/text publish gate (SIG-INGEST-025c) ---------


def test_statute_with_session_and_text_publishes() -> None:
    v = _instrument(
        citation="SB 40 (2026)",
        session="26 Regular",
        text_ref="https://www.nmlegis.gov/Sessions/26%20Regular/final/SB0040.PDF",
    ).publish_verdict()
    assert v.publishable is True and v.reasons == ()
    assert v.gate == LEGAL_INSTRUMENT_PUBLISH_GATE


def test_session_less_statute_never_publishes() -> None:
    """The CA SB 34 case: a session-less legislative citation is withheld."""
    v = _instrument(
        citation="Civ. Code §§ 1798.29, 1798.90.5 (SB 34)",
        text_ref="https://example.invalid/text",
    ).publish_verdict()
    assert v.publishable is False
    assert any("session" in r for r in v.reasons)


def test_citation_without_text_resolution_never_publishes() -> None:
    v = _instrument(
        citation="SB 40 (2026)", session="26 Regular", text_ref="not-a-url"
    ).publish_verdict()
    assert v.publishable is False
    assert any("cannot be resolved to text" in r for r in v.reasons)


def test_regulation_needs_text_but_not_session() -> None:
    v = _instrument(
        instrument_type="regulation",
        citation="Ala. Admin. Code r. 265-X-6",
        text_ref="https://admincode.legislature.state.al.us/api/chapter/265-X-6",
    ).publish_verdict()
    assert v.publishable is True


def test_claim_rows_carry_the_publish_verdict() -> None:
    rows = _instrument(citation="SB 34", text_ref="https://x/t").claim_rows()
    entity = next(r for r in rows if r["record_kind"] == "legal_instrument")
    assert entity["publishable"] is False
    assert entity["publish_gate"] == LEGAL_INSTRUMENT_PUBLISH_GATE
    assert entity["publish_gate_reasons"]


def test_posture_vocabulary_is_closed() -> None:
    assert {p.value for p in DutyPosture} == {"commenced", "not_yet_due", "contingent"}
    assert LEADS_SCHEMA == "sig.statute-leads/1"

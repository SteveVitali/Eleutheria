# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Statute-seeded records leads: the mandate → gap generator (P37.14).

State reporting mandates are **records-acquisition leads, not data feeds**
(SIG-INGEST-025a): a statutory duty to *do* something is not a duty to *publish*
it, and neither implies a machine-readable dataset exists. The connector for
this class is a records-request generator (§36) seeded from the statute —
"this jurisdiction is required to hold X, therefore X is requestable"
(SIG-INGEST-025b).

This module is the pure generator: it reads the committed leads table
``data/statute_leads.toml`` (``sig.statute-leads/1`` — one reviewed ``[[duties]]``
row per registered ``future_statutory_disclosure_*`` duty named by the
``statute_seed/2`` asset's duty table, plus the desk-researched one-time
artifacts) and emits, **per statute duty, exactly one output**:

* a :class:`StatuteRecordsLead` — the gap row feeding the records-request
  queue, for duties whose mandated record exists and is requestable
  (``posture = "commenced"``); or
* a :class:`~inference.coverage.CoverageRecord` — for duties whose honest
  output is a coverage fact: ``not_applicable`` while the first reports are
  not yet due (a lawful absence before the due date — the registry rows' own
  rule), or ``not_researched`` while the mandate itself is unverified
  (``posture = "contingent"`` — a bill is not an appropriation, S5 guard).

The join is **fail-closed**: a seed duty with no leads row, a leads row naming
an unregistered duty id, or a malformed row raises :class:`StatuteLeadsError`
rather than dropping a mandate silently — the catalog's acceptance shape is
"each statute duty produces a gap row or a CoverageRecord".

The one-time auditor-survey artifact (SIG-INGEST-025b's second clause) is
modelled desk-research-only: a ``state_auditor_survey`` artifact (§23.6,
SIG-INGEST-047) with its own ``capture_status`` — ``not_attempted`` while the
registered sources stay ``ingestion_permitted=false`` — that MUST NOT create
an expectation of recurrence, plus a ``searched_not_found`` CoverageRecord for
the follow-up survey desk research did not locate.

The RecordsRequest → task link is out of scope (R11-K13-RQ-04); nothing here
files, sends, or fetches anything.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from importlib.resources import files
from typing import Any

from connectors.registry import registry as source_registry
from connectors.statute_seed import parse_statute_seed
from inference.coverage import CoverageRecord

from ._data import load_table

__all__ = [
    "LEADS_SCHEMA",
    "LEADS_TABLE_VERSION",
    "SEED_ASSET",
    "DutyPosture",
    "StatuteLeadsError",
    "StatuteDuty",
    "OneTimeSurveyArtifact",
    "StatuteRecordsLead",
    "StatuteLeadsResult",
    "load_leads_table",
    "generate_leads",
    "auditor_survey_records",
]

LEADS_SCHEMA = "sig.statute-leads/1"
LEADS_TABLE_VERSION = "2026.11.07.1"

#: The committed statute-seed asset the duty table is joined against.
SEED_ASSET = "state_alpr_statute_seed_2026.toml"

#: The capture_status vocabulary (db/deploy/evidence.sql comment).
_CAPTURE_STATUSES = frozenset(
    {
        "captured",
        "access_restricted",
        "paywalled",
        "link_rotted",
        "not_attempted",
        "refused_by_policy",
    }
)

_DUTY_POSTURES = ("commenced", "not_yet_due", "contingent")


class StatuteLeadsError(ValueError):
    """A leads-table row failed validation or a seed duty has no leads row."""


class DutyPosture(StrEnum):
    """The desk-researched posture deciding a duty's output kind."""

    COMMENCED = "commenced"
    NOT_YET_DUE = "not_yet_due"
    CONTINGENT = "contingent"


@dataclass(frozen=True)
class StatuteDuty:
    """One reviewed ``[[duties]]`` row: a statute's reporting mandate."""

    duty_id: str
    state: str
    instrument_type: str
    citation: str
    session: str
    text_ref: str
    posture: DutyPosture
    first_due: str
    mandated_artifacts: tuple[str, ...]
    record_holder: str
    searched: tuple[str, ...]
    evidence: tuple[str, ...]
    notes: str

    @property
    def requestable(self) -> bool:
        """Whether the duty emits a requestable-records gap row (not coverage)."""
        return self.posture == DutyPosture.COMMENCED


@dataclass(frozen=True)
class OneTimeSurveyArtifact:
    """A one-time mandated-adjacent artifact (SIG-INGEST-025b, desk research only)."""

    artifact_id: str
    title: str
    artifact_type: str
    source_ids: tuple[str, ...]
    url: str
    published: str
    survey_rows: int
    capture_status: str
    recurrence_expected: bool
    no_follow_up_basis: str
    searched: tuple[str, ...]
    evidence: tuple[str, ...]
    notes: str

    def no_follow_up_coverage(self) -> CoverageRecord:
        """The CoverageRecord the absent follow-up writes (SIG-INGEST-025b).

        ``searched_not_found`` names the desk-research surfaces searched — the
        auditor's reports index and the legislative record (the recurring-audit
        bill was vetoed; the successor clause is appropriation-contingent).
        """
        return CoverageRecord(
            predicate_id="state_auditor_survey",
            absence_kind="searched_not_found",
            subject_class="recurring_state_auditor_survey",
            jurisdiction_id="us.state:California",
            sources_searched=self.searched,
            searched_by="statute_leads desk review (P37.14)",
            search_method=f"desk_research:{self.no_follow_up_basis}",
        )


@dataclass(frozen=True)
class StatuteRecordsLead:
    """The gap row a commenced statute duty produces (SIG-INGEST-025a/b).

    The records-acquisition lead: the jurisdiction is required to hold or
    produce the mandated artifact, therefore it is requestable. Carries the
    desk-researched statutory basis (citation + session + text_ref,
    SIG-INGEST-025c) and the review evidence; nothing is filed or sent.
    """

    lead_id: str
    duty_id: str
    state: str
    statutory_citation: str
    session: str
    text_ref: str
    mandated_artifacts: tuple[str, ...]
    record_holder: str
    first_due: str
    searched: tuple[str, ...]
    evidence: tuple[str, ...]
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "lead_id": self.lead_id,
            "duty_id": self.duty_id,
            "state": self.state,
            "statutory_citation": self.statutory_citation,
            "session": self.session,
            "text_ref": self.text_ref,
            "mandated_artifacts": list(self.mandated_artifacts),
            "record_holder": self.record_holder,
            "first_due": self.first_due,
            "searched": list(self.searched),
            "evidence": list(self.evidence),
            "notes": self.notes,
            "requestable": True,
        }


@dataclass(frozen=True)
class StatuteLeadsResult:
    """The generator's output: one row per statute duty, plus artifacts."""

    gap_rows: tuple[StatuteRecordsLead, ...]
    coverage: tuple[CoverageRecord, ...]
    artifacts: tuple[OneTimeSurveyArtifact, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": LEADS_SCHEMA,
            "table_version": LEADS_TABLE_VERSION,
            "gap_rows": [g.as_dict() for g in self.gap_rows],
            "coverage": [
                {
                    "predicate_id": c.predicate_id,
                    "absence_kind": c.absence_kind,
                    "subject_class": c.subject_class,
                    "jurisdiction_id": c.jurisdiction_id,
                    "sources_searched": list(c.sources_searched),
                    "search_method": c.search_method,
                }
                for c in self.coverage
            ],
            "artifacts": [
                {
                    "artifact_id": a.artifact_id,
                    "artifact_type": a.artifact_type,
                    "capture_status": a.capture_status,
                    "recurrence_expected": a.recurrence_expected,
                    "source_ids": list(a.source_ids),
                    "url": a.url,
                }
                for a in self.artifacts
            ],
            "duty_count": len(self.gap_rows)
            + len([c for c in self.coverage if c.predicate_id == "statutory_disclosure_artifact"]),
        }


def _str_list(what: str, value: Any, *, allow_empty: bool = True) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list) or any(not str(v).strip() for v in value):
        raise StatuteLeadsError(f"{what} must be a list of non-empty strings")
    out = tuple(str(v).strip() for v in value)
    if not out and not allow_empty:
        raise StatuteLeadsError(f"{what} must be a non-empty list")
    return out


def _seed_duty_ids() -> frozenset[str]:
    """The ``future_statutory_disclosure_*`` ids the committed seed's duty table names."""
    path = files("connectors").joinpath("data", SEED_ASSET)
    with path.open("rb") as fh:
        seed = parse_statute_seed(fh.read(), source_id="statute_leads")
    return frozenset(d for row in seed.duty_rows for d in row.duties)


def load_leads_table() -> tuple[tuple[StatuteDuty, ...], tuple[OneTimeSurveyArtifact, ...]]:
    """Parse the committed ``statute_leads.toml`` — strict, fail-closed."""
    data = load_table("statute_leads")
    if data.get("schema") != LEADS_SCHEMA:
        raise StatuteLeadsError(
            f"statute_leads `schema` {data.get('schema')!r} is not {LEADS_SCHEMA!r}"
        )
    duties: list[StatuteDuty] = []
    for i, row in enumerate(data.get("duties") or []):
        where = f"statute_leads [[duties]] #{i}"
        if not isinstance(row, dict):
            raise StatuteLeadsError(f"{where} is not a TOML table")
        duty_id = str(row.get("duty_id") or "").strip()
        if not duty_id.startswith("future_statutory_disclosure_"):
            raise StatuteLeadsError(
                f"{where} duty_id {duty_id!r} is not a future_statutory_disclosure_* id"
            )
        state = str(row.get("state") or "").strip()
        citation = str(row.get("citation") or "").strip()
        instrument_type = str(row.get("instrument_type") or "").strip()
        text_ref = str(row.get("text_ref") or "").strip()
        if not (state and citation and instrument_type and text_ref):
            raise StatuteLeadsError(
                f"{where} ({duty_id}) lacks state/citation/instrument_type/text_ref"
            )
        posture = str(row.get("posture") or "")
        if posture not in _DUTY_POSTURES:
            raise StatuteLeadsError(
                f"{where} ({duty_id}) `posture` {posture!r} not in {_DUTY_POSTURES}"
            )
        duties.append(
            StatuteDuty(
                duty_id=duty_id,
                state=state,
                instrument_type=instrument_type,
                citation=citation,
                session=str(row.get("session") or "").strip(),
                text_ref=text_ref,
                posture=DutyPosture(posture),
                first_due=str(row.get("first_due") or "").strip(),
                mandated_artifacts=_str_list(
                    f"{where} `mandated_artifacts`",
                    row.get("mandated_artifacts"),
                    allow_empty=False,
                ),
                record_holder=str(row.get("record_holder") or "").strip(),
                searched=_str_list(f"{where} `searched`", row.get("searched")),
                evidence=_str_list(f"{where} `evidence`", row.get("evidence"), allow_empty=False),
                notes=str(row.get("notes") or "").strip(),
            )
        )
    artifacts: list[OneTimeSurveyArtifact] = []
    for i, row in enumerate(data.get("one_time_artifacts") or []):
        where = f"statute_leads [[one_time_artifacts]] #{i}"
        if not isinstance(row, dict):
            raise StatuteLeadsError(f"{where} is not a TOML table")
        artifact_type = str(row.get("artifact_type") or "")
        if artifact_type != "state_auditor_survey":
            raise StatuteLeadsError(
                f"{where} `artifact_type` {artifact_type!r} is not 'state_auditor_survey' "
                "(SIG-INGEST-047)"
            )
        capture_status = str(row.get("capture_status") or "")
        if capture_status not in _CAPTURE_STATUSES:
            raise StatuteLeadsError(
                f"{where} `capture_status` {capture_status!r} not in {sorted(_CAPTURE_STATUSES)}"
            )
        if row.get("recurrence_expected") is not False:
            raise StatuteLeadsError(
                f"{where} must declare `recurrence_expected = false` — a one-time "
                "artifact MUST NOT create an expectation of recurrence (SIG-INGEST-025b)"
            )
        artifact_id = str(row.get("artifact_id") or "").strip()
        url = str(row.get("url") or "").strip()
        if not (artifact_id and url.startswith(("http://", "https://"))):
            raise StatuteLeadsError(f"{where} lacks artifact_id or a fetch-shaped url")
        searched = _str_list(f"{where} `searched`", row.get("searched"), allow_empty=False)
        artifacts.append(
            OneTimeSurveyArtifact(
                artifact_id=artifact_id,
                title=str(row.get("title") or "").strip(),
                artifact_type=artifact_type,
                source_ids=_str_list(
                    f"{where} `source_ids`", row.get("source_ids"), allow_empty=False
                ),
                url=url,
                published=str(row.get("published") or "").strip(),
                survey_rows=int(row.get("survey_rows") or 0),
                capture_status=capture_status,
                recurrence_expected=False,
                no_follow_up_basis=str(row.get("no_follow_up_basis") or "").strip(),
                searched=searched,
                evidence=_str_list(f"{where} `evidence`", row.get("evidence"), allow_empty=False),
                notes=str(row.get("notes") or "").strip(),
            )
        )
    return tuple(duties), tuple(artifacts)


def _coverage_for_duty(duty: StatuteDuty) -> CoverageRecord:
    """The coverage row a not-yet-due or contingent statute duty produces."""
    if duty.posture == DutyPosture.NOT_YET_DUE:
        return CoverageRecord(
            predicate_id="statutory_disclosure_artifact",
            absence_kind="not_applicable",
            subject_class="mandated_statutory_publication",
            jurisdiction_id=f"us.state:{duty.state}",
            search_method=(
                f"{duty.duty_id}: first reports due {duty.first_due} — absence "
                "before the due date is a lawful not_applicable coverage state"
            ),
        )
    return CoverageRecord(
        predicate_id="statutory_disclosure_artifact",
        absence_kind="not_researched",
        subject_class="mandated_statutory_publication",
        jurisdiction_id=f"us.state:{duty.state}",
        search_method=(
            f"{duty.duty_id}: contingent mandate — enactment unverified "
            "(a bill is not an appropriation); the duty's existence is not established"
        ),
    )


def generate_leads() -> StatuteLeadsResult:
    """Emit one gap row or one CoverageRecord per statute duty (SIG-INGEST-025a/b).

    The join is fail-closed: every ``future_statutory_disclosure_*`` id the
    committed seed's duty table names must have a reviewed ``[[duties]]`` row
    and every leads row must name a registered duty source — a mandate is never
    dropped silently, and an unmapped row is an error, not a skipped duty.
    """
    duties, artifacts = load_leads_table()
    seed_duties = _seed_duty_ids()
    registered = source_registry()
    table_ids = {d.duty_id for d in duties}
    missing = seed_duties - table_ids
    if missing:
        raise StatuteLeadsError(
            f"seed duties {sorted(missing)} have no [[duties]] row — each statute "
            "duty must produce a gap row or a CoverageRecord"
        )
    extra = table_ids - seed_duties
    if extra:
        raise StatuteLeadsError(
            f"[[duties]] rows {sorted(extra)} name duties the seed's duty table "
            "does not carry — the leads table joins the seed, never invents a duty"
        )
    for d in duties:
        if d.duty_id not in registered:
            raise StatuteLeadsError(
                f"duty {d.duty_id!r} is not a registered source — the lead cites "
                "the registry's row, never an unregistered mandate"
            )
    gap_rows: list[StatuteRecordsLead] = []
    coverage: list[CoverageRecord] = []
    for duty in duties:
        if duty.requestable:
            gap_rows.append(
                StatuteRecordsLead(
                    lead_id=f"statute_lead:{duty.duty_id}",
                    duty_id=duty.duty_id,
                    state=duty.state,
                    statutory_citation=duty.citation,
                    session=duty.session,
                    text_ref=duty.text_ref,
                    mandated_artifacts=duty.mandated_artifacts,
                    record_holder=duty.record_holder,
                    first_due=duty.first_due,
                    searched=duty.searched,
                    evidence=duty.evidence,
                    notes=duty.notes,
                )
            )
        else:
            coverage.append(_coverage_for_duty(duty))
    for artifact in artifacts:
        coverage.append(artifact.no_follow_up_coverage())
    return StatuteLeadsResult(
        gap_rows=tuple(gap_rows), coverage=tuple(coverage), artifacts=artifacts
    )


def auditor_survey_records() -> tuple[OneTimeSurveyArtifact, ...]:
    """The desk-researched one-time artifacts (the CA auditor survey)."""
    _, artifacts = load_leads_table()
    return artifacts

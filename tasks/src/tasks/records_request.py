# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Records-request generation: the correct statute, residency routing, consent (§36).

A detected research gap ("no ALPR contract on file for this agency") becomes a
**ready-to-file public-records request** here. This module owns the four §36 MUSTs
that turn a gap into filable, lawful, attributable work:

* **Emit with the correct statute (SIG-TASK-015).** :class:`RecordsRequestGenerator`
  emits a request naming the target agency and its records contact, the **statutory
  citation for that jurisdiction** (looked up in the §36 reference table, never
  guessed), the proven request language for the record type, and the specific
  records sought.
* **The 51-jurisdiction reference table (SIG-TASK-016).** :func:`records_law_table`
  loads the per-jurisdiction statute name/citation, response deadline, fee rules,
  appeal path, and residency flag from ``data/records_law.toml`` — data, not code.
* **Residency is operationally binding (SIG-TASK-016a/016b).** In the six
  residency-restricted states a non-resident's request *is not a valid request*, so
  the generator **refuses to emit** it, routes the task to the jurisdiction's local
  filers (§33.5, the local-group registry becomes load-bearing here), and records
  the constraint as a **coverage fact** so thin evidence there reads as a legal
  barrier, not an absence (§9.5/§32.2). Unknown residency defaults to this
  restrictive behaviour — never assume openness.
* **Versioned templates + measured success rates (SIG-TASK-017).**
  :class:`TemplateLibrary` holds versioned language; :class:`TemplateOutcomeLog`
  measures each version's success rate from recorded outcomes and flags
  denial-producing language for revision — which wording works is itself a finding.
* **Consent (SIG-TASK-018).** SIG does not file on a contributor's behalf without
  explicit consent, and every emitted request carries a notice that filing is a
  public act attributable to the filer.

The residency coverage fact reuses ``inference.coverage.CoverageRecord`` (P09.1),
and the no-responsive-records path (:func:`record_no_responsive_records`) reuses
``tasks.dispositions.resolve_no_evidence_exists`` (SIG-TASK-009) — neither is
re-encoded here. Persisting the emitted request and actually transmitting it are
downstream; this module owns the generation, the routing decision, and the shapes.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from functools import cache
from typing import Any

from inference.coverage import CoverageRecord

from ._data import load_table
from .dispositions import resolve_no_evidence_exists
from .geographic import GeographicQueue
from .groups import LocalGroup, LocalGroupRegistry
from .lifecycle import ResearchTask

__all__ = [
    "JURISDICTION_COUNT",
    "RESIDENCY_RESTRICTED_JURISDICTIONS",
    "ResidencyStatus",
    "RecordsLaw",
    "records_law_table",
    "records_law_for",
    "table_version",
    "RequestTemplate",
    "TemplateLibrary",
    "TemplateOutcomeLog",
    "template_library",
    "Filer",
    "ResearchGap",
    "GeneratedRecordsRequest",
    "ResidencyBlock",
    "RequestGenerationResult",
    "RecordsRequestGenerator",
    "ConsentNotGrantedError",
    "UnknownJurisdictionError",
    "residency_barrier_coverage",
    "record_no_responsive_records",
]

#: The reference table covers every US state plus the District of Columbia.
JURISDICTION_COUNT = 51

#: The `not_researched` coverage kind: a residency barrier means SIG *could not*
#: search (a non-resident cannot file), so the negative is "not researched", never
#: "searched, found nothing" (that is the whole §9.5/§32.2 distinction).
_RESIDENCY_BARRIER_ABSENCE_KIND = "not_researched"


# --- the per-jurisdiction records-law reference table (SIG-TASK-016) ----------


class UnknownJurisdictionError(KeyError):
    """Raised when a request targets a jurisdiction absent from the §36 table."""


@dataclass(frozen=True)
class RecordsLaw:
    """One jurisdiction's public-records law (§36, the reference-table row).

    Carries every field SIG-TASK-016 enumerates. `citation` is load-bearing — it is
    the statute the emitted request cites (SIG-TASK-015) — as is `residency_required`
    (SIG-TASK-016a: a true value refuses a non-resident filer). The operational
    fields are honest seed summaries pending counsel review (RISK-P10-16).
    """

    jurisdiction_id: str
    name: str
    statute: str
    citation: str
    response_deadline: str
    fee_rules: str
    appeal_path: str
    residency_required: bool


@cache
def _law_data() -> dict[str, Any]:
    return load_table("records_law")


@cache
def records_law_table() -> dict[str, RecordsLaw]:
    """The §36 reference table: `jurisdiction_id` → :class:`RecordsLaw` (all 51)."""
    data = _law_data()
    rows = data["jurisdictions"]
    assert isinstance(rows, dict)
    table = {
        jid: RecordsLaw(
            jurisdiction_id=jid,
            name=str(row["name"]),
            statute=str(row["statute"]),
            citation=str(row["citation"]),
            response_deadline=str(row["response_deadline"]),
            fee_rules=str(row["fee_rules"]),
            appeal_path=str(row["appeal_path"]),
            residency_required=bool(row["residency_required"]),
        )
        for jid, row in rows.items()
    }
    return table


def table_version() -> str:
    """The reference table's version, stamped onto every emitted request (§20)."""
    return str(_law_data()["table_version"])


@cache
def _residency_restricted() -> frozenset[str]:
    restricted = _law_data()["residency_restricted"]
    assert isinstance(restricted, list)
    return frozenset(str(j) for j in restricted)


#: The six residency-restricted jurisdictions (§36, SIG-TASK-016a): a non-resident's
#: request there is not a valid request. Sourced from the reference table's own
#: ``residency_restricted`` list so the operational refusal and the per-row flag
#: cannot drift (a test asserts they agree).
RESIDENCY_RESTRICTED_JURISDICTIONS: frozenset[str] = _residency_restricted()


def records_law_for(jurisdiction_id: str) -> RecordsLaw:
    """The :class:`RecordsLaw` for `jurisdiction_id`, or raise (SIG-TASK-016)."""
    try:
        return records_law_table()[jurisdiction_id]
    except KeyError:
        raise UnknownJurisdictionError(
            f"jurisdiction {jurisdiction_id!r} is not in the §36 records-law table; "
            f"the table covers {JURISDICTION_COUNT} US jurisdictions (SIG-TASK-016)"
        ) from None


# --- residency status (SIG-TASK-016a/016b) ------------------------------------


class ResidencyStatus(StrEnum):
    """A filer's residency relative to the target jurisdiction (§36).

    `UNKNOWN` is a first-class value, not a missing one: SIG-TASK-016b requires an
    undetermined residency to be *recorded as unknown* and to **default to the
    restrictive behaviour** (route to a local filer) rather than assuming openness.
    """

    RESIDENT = "resident"
    NON_RESIDENT = "non_resident"
    UNKNOWN = "unknown"


#: The residency statuses that a residency-restricted jurisdiction refuses. Unknown
#: is here by SIG-TASK-016b (default to restrictive); only a confirmed resident may
#: file in a restricted jurisdiction.
_BLOCKED_IN_RESTRICTED: frozenset[ResidencyStatus] = frozenset(
    {ResidencyStatus.NON_RESIDENT, ResidencyStatus.UNKNOWN}
)


# --- versioned templates + measured success rates (SIG-TASK-017) --------------


@dataclass(frozen=True)
class RequestTemplate:
    """A versioned request template for a record type (§36, SIG-TASK-017).

    `body` is the proven request language (with named `str.format` placeholders the
    generator fills); `records_sought` is the record-type-specific clause naming the
    specific records sought. A wording change is a NEW `version`, never an in-place
    edit, so a measured success rate always refers to exactly the language that
    produced it.
    """

    record_type: str
    version: str
    body: str
    records_sought: str


class TemplateLibrary:
    """The versioned request-template set (§36, SIG-TASK-017).

    Loads the templates from ``data/request_templates.toml`` (data, not code) and
    exposes the current version per record type plus the full version history. A
    body change lands as an appended version, so the history is the audit trail the
    outcome log measures against.
    """

    def __init__(
        self,
        *,
        templates: dict[str, tuple[RequestTemplate, ...]],
        set_version: str,
        revision_success_floor: float,
        revision_min_sample: int,
    ) -> None:
        self._templates = templates
        self._set_version = set_version
        self.revision_success_floor = revision_success_floor
        self.revision_min_sample = revision_min_sample

    @property
    def set_version(self) -> str:
        """The template set's version, stamped onto every emitted request (§20)."""
        return self._set_version

    def record_types(self) -> frozenset[str]:
        """Every record type the library has a template for."""
        return frozenset(self._templates)

    def versions(self, record_type: str) -> tuple[RequestTemplate, ...]:
        """Every version for `record_type`, in the order declared (oldest first)."""
        try:
            return self._templates[record_type]
        except KeyError:
            raise KeyError(
                f"no request template for record type {record_type!r}; add a versioned "
                "template to data/request_templates.toml (SIG-TASK-017)"
            ) from None

    def current(self, record_type: str) -> RequestTemplate:
        """The latest version for `record_type` (the one the generator files)."""
        return self.versions(record_type)[-1]


@cache
def _template_data() -> dict[str, Any]:
    return load_table("request_templates")


@cache
def template_library() -> TemplateLibrary:
    """The versioned template library seeded from ``request_templates.toml``."""
    data = _template_data()
    raw = data["templates"]
    assert isinstance(raw, dict)
    templates: dict[str, tuple[RequestTemplate, ...]] = {}
    for record_type, entry in raw.items():
        assert isinstance(entry, dict)
        records_sought = str(entry["records_sought"])
        versions = tuple(
            RequestTemplate(
                record_type=record_type,
                version=str(v["version"]),
                body=str(v["body"]),
                records_sought=records_sought,
            )
            for v in entry["versions"]
        )
        if not versions:
            raise ValueError(f"record type {record_type!r} declares no template versions")
        templates[record_type] = versions
    return TemplateLibrary(
        templates=templates,
        set_version=str(data["template_set_version"]),
        revision_success_floor=float(data["revision_success_floor"]),
        revision_min_sample=int(data["revision_min_sample"]),
    )


class TemplateOutcomeLog:
    """Measures each template version's success rate (§36, SIG-TASK-017).

    Records the outcome of each filed request (did the language get records
    released?) per ``(record_type, version)`` and reports the measured success rate.
    A version whose rate falls below the revision floor over a minimum sample
    "produces denials" and is flagged for revision — and the rates themselves are a
    publishable finding about which language works.

    A ``no_responsive_records`` reply is **not** a template failure: the agency
    answered on the record (it becomes a coverage finding, SIG-TASK-009), so it is
    not counted here — only outcomes the caller reports as successes/failures are.
    """

    def __init__(
        self,
        *,
        revision_success_floor: float | None = None,
        revision_min_sample: int | None = None,
    ) -> None:
        lib = template_library()
        self._floor = (
            revision_success_floor
            if revision_success_floor is not None
            else lib.revision_success_floor
        )
        self._min_sample = (
            revision_min_sample if revision_min_sample is not None else lib.revision_min_sample
        )
        #: (record_type, version) -> [successes, total]
        self._counts: dict[tuple[str, str], list[int]] = {}

    def record_outcome(self, record_type: str, version: str, *, succeeded: bool) -> None:
        """Record one filed request's outcome for a template version."""
        counts = self._counts.setdefault((record_type, version), [0, 0])
        counts[0] += int(succeeded)
        counts[1] += 1

    def sample_size(self, record_type: str, version: str) -> int:
        """How many outcomes have been recorded for this version."""
        return self._counts.get((record_type, version), [0, 0])[1]

    def success_rate(self, record_type: str, version: str) -> float | None:
        """The measured success rate, or `None` if nothing has been recorded yet."""
        successes, total = self._counts.get((record_type, version), [0, 0])
        return successes / total if total else None

    def needs_revision(self, record_type: str, version: str) -> bool:
        """Whether this version's measured language should be revised (SIG-TASK-017).

        True only once at least `revision_min_sample` outcomes exist (so a single
        early denial does not condemn a template) and the measured rate is below the
        revision floor. Under-sampled versions return False — not enough is known.
        """
        rate = self.success_rate(record_type, version)
        return (
            rate is not None
            and self.sample_size(record_type, version) >= self._min_sample
            and rate < self._floor
        )

    def flagged_for_revision(self) -> frozenset[tuple[str, str]]:
        """Every `(record_type, version)` whose language is flagged for revision."""
        return frozenset(key for key in self._counts if self.needs_revision(key[0], key[1]))


# --- the filer, the gap, and the emitted request ------------------------------


class ConsentNotGrantedError(ValueError):
    """Raised when a request would name a filer who has not consented (SIG-TASK-018)."""


@dataclass(frozen=True)
class Filer:
    """The contributor who would file the request (§36, SIG-TASK-016a/018).

    Bundles who they are, their residency relative to the target jurisdiction
    (which decides SIG-TASK-016a routing), and their consent (SIG-TASK-018): SIG
    files nothing on a contributor's behalf without `consent_granted`, and the
    contributor must acknowledge that filing is a public act attributable to them.
    """

    filer_id: str
    display_name: str
    residency_status: ResidencyStatus = ResidencyStatus.UNKNOWN
    consent_granted: bool = False
    acknowledged_public_act: bool = False


@dataclass(frozen=True)
class ResearchGap:
    """The gap a request would fill (§36, SIG-TASK-015 input).

    Names the subject and predicate the request seeks evidence for, the target
    jurisdiction (the reference-table key), the agency and its records contact, the
    record type (which template to use), and the earliest date to request from. A
    gap MUST identify a subject (`subject_id` or `subject_class`) so the residency
    coverage fact has a subject (§3.1: every node has identity).
    """

    predicate_id: str
    jurisdiction_id: str
    target_agency: str
    records_contact: str
    record_type: str
    subject_id: str | None = None
    subject_class: str | None = None
    start_date: str = "the earliest available date"

    def __post_init__(self) -> None:
        if not (self.subject_id or self.subject_class):
            raise ValueError(
                "a ResearchGap MUST identify a subject (subject_id or subject_class); "
                "the residency coverage fact needs a subject (§3.1)"
            )


@dataclass(frozen=True)
class GeneratedRecordsRequest:
    """A ready-to-file public-records request (§36, SIG-TASK-015).

    Everything a contributor needs to file: the target agency + records contact, the
    **statutory citation for the jurisdiction**, the proven request language
    (`request_text`) filled from the versioned template, and the specific records
    sought — plus the operational reference fields and the versions (`table_version`,
    `template_version`, `template_set_version`) stamped for provenance (§20).
    """

    jurisdiction_id: str
    jurisdiction_name: str
    target_agency: str
    records_contact: str
    statute_name: str
    statutory_citation: str
    predicate_id: str
    record_type: str
    records_sought: str
    request_text: str
    response_deadline: str
    fee_rules: str
    appeal_path: str
    filer_id: str
    filer_display_name: str
    public_act_notice: str
    template_version: str
    template_set_version: str
    table_version: str
    generated_at: datetime | None = None


@dataclass(frozen=True)
class ResidencyBlock:
    """The outcome when residency law refuses a request (§36, SIG-TASK-016a/016b).

    SIG did **not** emit a request (it would not be valid). Instead the task is
    routed to the jurisdiction's local filers, and the constraint is recorded as a
    `coverage` fact (`not_researched`, attributed to the legal barrier) so thin
    evidence there is not read as an absence of surveillance. `local_filers` are the
    registry's groups for the jurisdiction (the load-bearing local-contributor
    coverage); `claimant_groups` are those with an active geographic-queue claim.
    """

    jurisdiction_id: str
    statutory_citation: str
    residency_status: ResidencyStatus
    reason: str
    coverage: CoverageRecord
    local_filers: tuple[LocalGroup, ...] = ()
    claimant_groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class RequestGenerationResult:
    """The result of :meth:`RecordsRequestGenerator.generate`.

    Exactly one of `emitted` / `residency_block` is set: a request was emitted
    (SIG-TASK-015), or residency law refused it and it was routed (SIG-TASK-016a/b).
    """

    emitted: GeneratedRecordsRequest | None = None
    residency_block: ResidencyBlock | None = None

    @property
    def was_emitted(self) -> bool:
        """Whether a ready-to-file request was produced."""
        return self.emitted is not None


def residency_barrier_coverage(
    gap: ResearchGap,
    law: RecordsLaw,
    *,
    searched_by: str | None = None,
    searched_at: datetime | None = None,
) -> CoverageRecord:
    """The coverage fact a residency barrier writes (§36, SIG-TASK-016a; §9.5/§32.2).

    The absence kind is `not_researched`, never `searched_not_found`: SIG could not
    search (a non-resident cannot file), so the negative must read as a **legal
    barrier**, not "searched and found nothing". The barrier is attributed in
    `search_method` (the residency statute), so a downstream reader sees *why* the
    predicate is unresearched in this jurisdiction and does not mistake thin
    coverage there for an absence of surveillance.
    """
    return CoverageRecord(
        predicate_id=gap.predicate_id,
        absence_kind=_RESIDENCY_BARRIER_ABSENCE_KIND,
        subject_id=gap.subject_id,
        subject_class=gap.subject_class,
        jurisdiction_id=gap.jurisdiction_id,
        searched_at=searched_at,
        searched_by=searched_by,
        search_method=f"residency_barrier:{law.citation}",
    )


class RecordsRequestGenerator:
    """Emits ready-to-file records requests, or routes residency-blocked ones (§36).

    Holds the §36 reference table and the versioned template library, and applies
    the three §36 rules in order for each gap: residency first (SIG-TASK-016a/016b —
    a blocked jurisdiction never reaches the emit path), then consent
    (SIG-TASK-018 — SIG files nothing without it), then emit with the correct
    statute and proven language (SIG-TASK-015).
    """

    def __init__(self, *, templates: TemplateLibrary | None = None) -> None:
        self._templates = templates if templates is not None else template_library()

    def generate(
        self,
        gap: ResearchGap,
        filer: Filer,
        *,
        registry: LocalGroupRegistry | None = None,
        queue: GeographicQueue | None = None,
        now: datetime | None = None,
    ) -> RequestGenerationResult:
        """Generate a request for `gap` filed by `filer`, applying the §36 rules.

        Returns a :class:`RequestGenerationResult`: either an emitted request, or a
        :class:`ResidencyBlock` when residency law refuses it. When blocked, and a
        `registry`/`queue` is supplied, the block names the local filers and active
        claimant groups the task routes to (§33.5). Raises
        :class:`ConsentNotGrantedError` on the emit path if the filer has not
        consented (SIG-TASK-018), and :class:`UnknownJurisdictionError` for a
        jurisdiction absent from the table.
        """
        law = records_law_for(gap.jurisdiction_id)

        if law.residency_required and filer.residency_status in _BLOCKED_IN_RESTRICTED:
            return RequestGenerationResult(
                residency_block=self._route_residency_block(
                    gap, filer, law, registry=registry, queue=queue, now=now
                )
            )

        self._check_consent(filer)
        return RequestGenerationResult(emitted=self._emit(gap, filer, law, now=now))

    # --- the emit path (SIG-TASK-015/018) -------------------------------------

    def _check_consent(self, filer: Filer) -> None:
        if not filer.consent_granted:
            raise ConsentNotGrantedError(
                f"filer {filer.filer_id!r} has not consented; SIG does not file a records "
                "request on a contributor's behalf without explicit consent (SIG-TASK-018)"
            )
        if not filer.acknowledged_public_act:
            raise ConsentNotGrantedError(
                f"filer {filer.filer_id!r} has not acknowledged that filing is a public act "
                "attributable to them; that acknowledgement is part of consent (SIG-TASK-018)"
            )

    def _emit(
        self, gap: ResearchGap, filer: Filer, law: RecordsLaw, *, now: datetime | None
    ) -> GeneratedRecordsRequest:
        template = self._templates.current(gap.record_type)
        records_sought = template.records_sought.format(
            agency=gap.target_agency, start_date=gap.start_date
        )
        public_act_notice = (
            f"Please note: this request is filed by {filer.display_name} as a public act. "
            "In most jurisdictions the identity of a records requester is itself a public "
            "record attributable to the filer (SIG-TASK-018)."
        )
        request_text = template.body.format(
            agency=gap.target_agency,
            records_contact=gap.records_contact,
            statute=law.statute,
            citation=law.citation,
            records_sought=records_sought,
            response_deadline=law.response_deadline,
            filer=filer.display_name,
            public_act_notice=public_act_notice,
        )
        return GeneratedRecordsRequest(
            jurisdiction_id=law.jurisdiction_id,
            jurisdiction_name=law.name,
            target_agency=gap.target_agency,
            records_contact=gap.records_contact,
            statute_name=law.statute,
            statutory_citation=law.citation,
            predicate_id=gap.predicate_id,
            record_type=gap.record_type,
            records_sought=records_sought,
            request_text=request_text,
            response_deadline=law.response_deadline,
            fee_rules=law.fee_rules,
            appeal_path=law.appeal_path,
            filer_id=filer.filer_id,
            filer_display_name=filer.display_name,
            public_act_notice=public_act_notice,
            template_version=template.version,
            template_set_version=self._templates.set_version,
            table_version=table_version(),
            generated_at=now,
        )

    # --- the residency-block path (SIG-TASK-016a/016b) ------------------------

    def _route_residency_block(
        self,
        gap: ResearchGap,
        filer: Filer,
        law: RecordsLaw,
        *,
        registry: LocalGroupRegistry | None,
        queue: GeographicQueue | None,
        now: datetime | None,
    ) -> ResidencyBlock:
        coverage = residency_barrier_coverage(gap, law, searched_by=filer.filer_id)
        local_filers = (
            tuple(registry.by_jurisdiction(gap.jurisdiction_id)) if registry is not None else ()
        )
        claimant_groups = (
            queue.claimant_groups(gap.jurisdiction_id, now)
            if queue is not None and now is not None
            else frozenset()
        )
        qualifier = (
            "is not a resident of"
            if filer.residency_status is ResidencyStatus.NON_RESIDENT
            else "has unknown residency in"
        )
        reason = (
            f"{law.name} restricts records requests to residents ({law.citation}); the filer "
            f"{qualifier} the jurisdiction, so the request would not be valid. Routed to a "
            "local filer (SIG-TASK-016a/016b)."
        )
        return ResidencyBlock(
            jurisdiction_id=gap.jurisdiction_id,
            statutory_citation=law.citation,
            residency_status=filer.residency_status,
            reason=reason,
            coverage=coverage,
            local_filers=local_filers,
            claimant_groups=claimant_groups,
        )


# --- the no-responsive-records path (SIG-TASK-009 through records) ------------


def record_no_responsive_records(
    task: ResearchTask,
    request: GeneratedRecordsRequest,
    *,
    extra_sources: Sequence[str] = (),
    searched_at: datetime | None = None,
    searched_by: str | None = None,
) -> CoverageRecord:
    """Close a records task whose reply held no responsive record (SIG-TASK-009).

    When a filed request comes back "no responsive records", that agency statement
    is a **positive finding**, not nothing: it becomes a `searched_not_found`
    `CoverageRecord` naming the sources searched. This routes through
    :func:`tasks.dispositions.resolve_no_evidence_exists` — the single
    coverage-writing bridge — so the §36 records path exercises SIG-TASK-009 exactly
    as every other search path does. The emitted request itself is the primary named
    source (the agency queried under its statute); `extra_sources` adds any others.
    """
    sources = (
        f"{request.target_agency} records request under {request.statutory_citation}",
        *extra_sources,
    )
    return resolve_no_evidence_exists(
        task,
        predicate_id=request.predicate_id,
        sources_searched=sources,
        searched_at=searched_at,
        searched_by=searched_by,
        search_method="records_request",
    )

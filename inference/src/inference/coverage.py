# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `CoverageRecord`: negative space made queryable, not editorial (§32.1).

"Not in the Atlas" and "not in the Atlas, not in any portal, and not in three
years of council minutes" are very different statements (§32, SIG-METRIC-002).
A `CoverageRecord` is the object that carries that difference: it names the
subject/predicate that was sought, the way the absence is known (`absence_kind`),
and — when SIG looked and found nothing — *which sources it searched*.

This is the runtime value object for the §32.1 shape, aligned field-for-field with
the physical `coverage_record` table (`db/deploy/graph_annotations.sql`) and reusing
the four-state §9.5 model (:mod:`db.absence`) rather than re-encoding it. Persisting
it and serving it over HTTP are downstream (the read-API envelope is P14.1); this
module owns the shape, the validation, and the distinguishable rendering every read
path consumes.

Two invariants are enforced here rather than left to convention:

* `sources_searched[]` is **required** for `searched_not_found` (SIG-METRIC-001/002)
  — a `searched_not_found` record without it is rejected, mirroring the DDL CHECK.
* discovery-probe negatives are **retained**: an enumerated candidate-identifier
  space keeps its confirmed-absent members as `searched_not_found` records, not only
  the present ones (SIG-METRIC-002a).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime

from db.absence import (
    ABSENCE_KINDS,
    NOT_APPLICABLE_KIND,
    AbsenceRendering,
    AbsenceState,
    render_coverage_kind,
    state_from_coverage_kind,
)

__all__ = [
    "CoverageRecord",
    "probe_coverage_records",
]

#: The `absence_kind` that MUST name the sources searched (SIG-METRIC-001/002).
_SEARCHED_NOT_FOUND = "searched_not_found"


@dataclass(frozen=True)
class CoverageRecord:
    """A queryable negative-space record for one subject+predicate (§32.1).

    Field-for-field the `coverage_record` table shape. Either `subject_id` (a
    concrete entity) or `subject_class` (a class within a jurisdiction) MUST be
    given — a coverage record with no subject identity is meaningless (§3.1: every
    node has identity). `sources_searched` is required for `searched_not_found`
    (SIG-METRIC-001/002) and forbidden-when-empty there; it is optional otherwise.
    """

    predicate_id: str
    absence_kind: str
    subject_id: str | None = None
    subject_class: str | None = None
    jurisdiction_id: str | None = None
    sources_searched: tuple[str, ...] = ()
    searched_at: datetime | None = None
    searched_by: str | None = None
    search_method: str | None = None

    def __post_init__(self) -> None:
        if self.absence_kind not in ABSENCE_KINDS:
            raise ValueError(
                f"absence_kind {self.absence_kind!r} is not one of {sorted(ABSENCE_KINDS)} (§32.1)"
            )
        if not (self.subject_id or self.subject_class):
            raise ValueError(
                "a CoverageRecord MUST identify a subject (subject_id or "
                "subject_class); negative space needs a subject (§3.1)"
            )
        if self.absence_kind == _SEARCHED_NOT_FOUND and not self.sources_searched:
            raise ValueError(
                "sources_searched[] is REQUIRED for absence_kind='searched_not_found' "
                "(SIG-METRIC-001/002): 'not in the Atlas' and 'not in the Atlas, any "
                "portal, or three years of minutes' are different statements"
            )

    @property
    def epistemic_state(self) -> AbsenceState | None:
        """The §9.5 state this record encodes, or `None` for `not_applicable`.

        `not_applicable` is a coverage kind, not a kind of "unknown": the predicate
        simply does not apply to the subject, so it maps to no epistemic state.
        """
        if self.absence_kind == NOT_APPLICABLE_KIND:
            return None
        return state_from_coverage_kind(self.absence_kind)

    def rendering(self) -> AbsenceRendering:
        """The distinguishable presentation of this record (SIG-TIME-011/012)."""
        return render_coverage_kind(
            self.absence_kind, sources_searched=self.sources_searched or None
        )

    def public_view(self) -> dict[str, object]:
        """The API-facing projection (the HTTP envelope itself is P14.1).

        Carries the machine `code` and human `label`/`detail` so a consumer never
        has to re-derive the §9.5 distinction — and never renders `not_researched`
        identically to `searched_not_found` (SIG-TIME-012).
        """
        rendered = self.rendering()
        state = self.epistemic_state
        return {
            "subject_id": self.subject_id,
            "subject_class": self.subject_class,
            "jurisdiction_id": self.jurisdiction_id,
            "predicate_id": self.predicate_id,
            "absence_kind": self.absence_kind,
            "epistemic_state": state.value if state is not None else None,
            "absence_code": rendered.code,
            "absence_label": rendered.label,
            "absence_detail": rendered.detail,
            "sources_searched": list(self.sources_searched),
            "searched_at": self.searched_at.isoformat() if self.searched_at else None,
            "searched_by": self.searched_by,
            "search_method": self.search_method,
        }


def probe_coverage_records(
    *,
    predicate_id: str,
    candidates: Iterable[str],
    present: Iterable[str],
    sources_searched: Sequence[str],
    subject_class: str | None = None,
    jurisdiction_id: str | None = None,
    searched_at: datetime | None = None,
    searched_by: str | None = None,
    search_method: str | None = None,
) -> tuple[CoverageRecord, ...]:
    """Retain a discovery probe's **negatives** as coverage records (SIG-METRIC-002a).

    A discovery probe enumerates a candidate identifier space — portal slugs, agency
    identifiers, tenant names — and learns which candidates exist. The confirmed-absent
    members are the more informative half: they convert "we found N" into "we tested M
    candidates and N exist", which is a denominator (SIG-METRIC-003) and lets a *new*
    member be detected later without re-probing the whole space. They MUST be stored,
    not discarded.

    Returns one `searched_not_found` `CoverageRecord` per confirmed-absent candidate,
    keyed by the candidate identifier as `subject_id`. Present candidates yield no
    coverage record (they are positive findings handled elsewhere). Raises if a
    "present" identifier is not in the candidate space (the probe is inconsistent) or
    if `sources_searched` is empty (SIG-METRIC-002).
    """
    if not sources_searched:
        raise ValueError(
            "a discovery probe MUST name the sources searched (SIG-METRIC-002); "
            "an anonymous negative is rhetoric, not coverage"
        )
    candidate_set = tuple(dict.fromkeys(candidates))  # de-dupe, preserve order
    present_set = set(present)
    unknown = present_set - set(candidate_set)
    if unknown:
        raise ValueError(
            f"present identifiers {sorted(unknown)} are not in the probed candidate "
            "space; the probe is inconsistent (SIG-METRIC-002a)"
        )
    searched = tuple(sources_searched)
    return tuple(
        CoverageRecord(
            predicate_id=predicate_id,
            absence_kind=_SEARCHED_NOT_FOUND,
            subject_id=candidate,
            subject_class=subject_class,
            jurisdiction_id=jurisdiction_id,
            sources_searched=searched,
            searched_at=searched_at,
            searched_by=searched_by,
            search_method=search_method,
        )
        for candidate in candidate_set
        if candidate not in present_set
    )

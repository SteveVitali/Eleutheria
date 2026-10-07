# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The gap-driven reviewed acquisition queue (P32.11, §55.6, SIG-ACQ-001/002, ADR-130).

Acquisition is a **reviewed queue**, not a crawler. Every candidate is a passport
that starts from a named gap (the S2 dossier questions or a justified national
need), carries its own discovery provenance, is joined against the *live* source
registry and the recorded P31.12/.13 rights dispositions, and is prioritised by a
versioned ordinal score that usefulness alone can never use to open a gate.

The load-bearing disciplines, each enforced in code rather than prose:

* **Evidence-first provenance (SIG-ACQ-001).** The queue is seeded from the
  committed research inventory
  ``docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv``
  verbatim — search excerpts are *leads*, never full-document review, and the
  recorded review depth is carried into every entry's ``uncertainty``. Seeding
  approves nothing: no candidate can carry a ``decided`` rights lane without a
  recorded reviewer disposition, and ``ingestion_permitted`` is never touched.
* **Lineage, not URLs (SIG-ACQ-001).** A candidate's value is supported new
  relationships or closed gaps *after deduplication*. The S5 lineage vocabulary
  is closed: ``same_bytes``/``republished_document``/``derived_summary``/
  ``new_version``/``amends``/``response_to`` documents in one lineage can never
  score as independent corroboration — only ``independent_account`` yields it,
  and two candidates in one ``lineage_group`` still cannot corroborate each
  other (an aggregate and its underlying audit are one provenance). URL
  normalisation detects literal duplicates across the queue and against
  registered ``homepage_url``s.
* **Registry + dispositions join.** ``registry_links`` resolve against
  :func:`connectors.registry.registry` (an unknown id fails the load);
  ``same_source`` links mark the candidate *as* an existing row — an
  improvement under that row, never a second onboarding — and a ``same_source``
  link into :data:`P31_OWNED_SOURCES` is refused outright. The recorded P31.12/
  .13 dispositions (``docs/build/reports/rights/p27*_dispositions.json``) are
  joined through :func:`db.rights_decisions.load_resolutions`.
* **Hard gates, not offsets (SIG-ACQ-002).** Rights and sensitivity are gates
  independent of score: undetermined or rejected lanes, a Part VIII preflight
  that is un-screened/prohibited/rejected, and municipal publication *observed*
  (never a licence decision — a municipal PDF is not auto-CC0, 17 U.S.C. §105
  covers federal works and Compendium §313.6(C)(2) distinguishes copyrightable
  non-edict state/local works) all block admissibility no matter how high the
  usefulness score.
* **Separate rights lanes (SIG-ACQ-002).** Raw document bytes (including
  embedded third-party material), factual extraction/quotation, and the
  derived-artifact publication licence are assessed *separately*.
* **Versioned, explainable, honestly-costed scores.** ``acq-score/1`` is the
  research-documented ``3G + 3R + 2I + 2U + T + J − 2E − 2A − 2S`` ordinal
  model over nine 0–3 dimensions recorded under a version tag with an assessor
  (a role, never a personal name), an evidence citation and a measured/
  estimated flag; :func:`score` returns per-dimension contributions, unknown
  dimensions stay unscored with named unknowns, and
  :func:`diff_assessments` explains any change between two versioned input
  sets. Utility is a transparent prioritisation aid, not a probability of
  truth. Cost carries ``estimated`` (the CSV effort band) separately from
  ``measured`` (empty until an approved acquisition run reports real minutes —
  never fabricated).

The ``acq-seed/1`` assessment is an *engineering* seed: ordinal values assigned
from the declared CSV fields per documented rules, labelled estimated, and
intended to be superseded by reviewer assessments under a new version — the
model records disagreement rather than hiding it. Nothing in this module runs
a fetch, mints a ``rights_decision``, or flips a source.
"""

from __future__ import annotations

import csv
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from connectors.registry import registry as source_registry
from db.rights_decisions import RightsResolution, load_resolutions

from ._data import load_table

# --------------------------------------------------------------------------- #
# Versioned contract ids                                                      #
# --------------------------------------------------------------------------- #

#: Schema of ``data/acquisition_queue.toml`` (the queue's committed seed data).
QUEUE_SCHEMA = "acquisition-queue/1"
#: The ordinal score model version (S5 "Scoring that rewards missing answers").
SCORING_VERSION = "acq-score/1"
#: The version of the dimension assessments seeded by this ticket — explicit
#: estimates derived from the CSV's declared fields, intended to be superseded
#: by reviewer assessments under a new version.
SEED_VERSION = "acq-seed/1"

#: The nine ordinal scoring dimensions (each 0–3). `G` closes an explicit
#: dossier/coverage gap; `R` yields named institutional relationships/governance;
#: `I` adds independent provenance; `U` has reusable extraction structure;
#: `T` improves timeliness; `J` serves the current geographic need; `E` is
#: engineering/review effort; `A` is access friction; `S` is sensitive-content
#: exposure. `E`/`A`/`S` carry negative weight.
DIMENSIONS: tuple[str, ...] = ("G", "R", "I", "U", "T", "J", "E", "A", "S")

#: `acq-score/1` weights (S5): ``3G + 3R + 2I + 2U + T + J − 2E − 2A − 2S``.
DIMENSION_WEIGHTS: dict[str, int] = {
    "G": 3,
    "R": 3,
    "I": 2,
    "U": 2,
    "T": 1,
    "J": 1,
    "E": -2,
    "A": -2,
    "S": -2,
}

#: The eight sources already owned by P31.12/.13 (S5 "Baseline and
#: non-duplication") — consumed or improved, never emitted as new work.
P31_OWNED_SOURCES: frozenset[str] = frozenset(
    {
        "gao_surveillance_reports",
        "dhs_oig_reports",
        "dhs_fusion_center_assessments",
        "uk_surveillance_camera_commissioner",
        "fema_hsgp_allocations",
        "ccops_oakland",
        "ccops_cambridge",
        "ccops_somerville",
    }
)

#: SIG-PUB-002 — the categorically excluded content a Part VIII preflight
#: screens for (never stored at any tier).
PART_VIII_EXCLUDED_CATEGORIES: tuple[str, ...] = (
    "license_plate",
    "travel_history",
    "home_address",
    "private_person_name",
    "personal_identifier",
)

#: Committed research inventory (read-only input — it is a lead list, never an
#: ingestion permission list).
DEFAULT_INVENTORY = "docs/build/planning/2026-09-25-six-streams/data/source-candidates.csv"

#: The committed rights-disposition artifacts joined for provenance (P27.2 +
#: P29.3 — append-only ``rights_decision`` records, ADR-095).
DISPOSITION_ARTIFACTS: tuple[str, ...] = (
    "docs/build/reports/rights/p272_dispositions.json",
    "docs/build/reports/rights/p293_dispositions.json",
    "docs/build/reports/rights/p3438_dispositions.json",
)


class AcquisitionQueueError(ValueError):
    """A queue row failed validation or referenced an undecidable state."""


# --------------------------------------------------------------------------- #
# Lineage                                                                     #
# --------------------------------------------------------------------------- #


class LineageClass(StrEnum):
    """The S5 closed lineage vocabulary (research §Discovery procedure, step 5).

    Only ``INDEPENDENT_ACCOUNT`` can count as independent corroboration; the
    rest are one lineage however many URLs host them — a mirror, republication,
    derivative, revision or amendment of an existing report has low independent
    yield by construction.
    """

    SAME_BYTES = "same_bytes"
    REPUBLISHED_DOCUMENT = "republished_document"
    DERIVED_SUMMARY = "derived_summary"
    NEW_VERSION = "new_version"
    RESPONSE_TO = "response_to"
    AMENDS = "amends"
    INDEPENDENT_ACCOUNT = "independent_account"


#: Lineage classes that can never yield independent corroboration. ``response_to``
#: is included conservatively: a reply document is one oversight exchange with
#: the report it answers (the response is still acquired and scored on its own
#: merits — it simply cannot corroborate the document it responds to).
NON_INDEPENDENT_LINEAGE: frozenset[LineageClass] = frozenset(
    {
        LineageClass.SAME_BYTES,
        LineageClass.REPUBLISHED_DOCUMENT,
        LineageClass.DERIVED_SUMMARY,
        LineageClass.NEW_VERSION,
        LineageClass.AMENDS,
        LineageClass.RESPONSE_TO,
    }
)


# --------------------------------------------------------------------------- #
# Registry join                                                               #
# --------------------------------------------------------------------------- #


class LinkKind(StrEnum):
    """How a candidate relates to an existing registry row."""

    #: The candidate IS this registry row — deepening/improvement happens under
    #: the existing row; a second onboarding is refused.
    SAME_SOURCE = "same_source"
    #: A dedupe-aware neighbour — distinct target that must not double-count
    #: claims or documents the linked source already covers.
    RELATED = "related"


class RegistryRelation(StrEnum):
    """A candidate's relation to the landed source registry."""

    #: A P31.12/.13-owned source — consumed/improved, never re-onboarded.
    P31_OWNED = "p31_owned"
    #: Identical to a registered, ingestion-permitted source.
    EXISTING_PERMITTED = "existing_permitted"
    #: Identical to a registered but not-permitted source.
    EXISTING_UNPERMITTED = "existing_unpermitted"
    #: A URL-level duplicate (of another candidate or a registered homepage).
    DUPLICATE = "duplicate"
    #: No matching registry row — a genuinely new target.
    NET_NEW = "net_new"


@dataclass(frozen=True)
class RegistryLink:
    """One declared link from a candidate to an existing registry row."""

    source_id: str
    kind: LinkKind
    note: str = ""


@dataclass(frozen=True)
class LinkedSource:
    """A resolved registry link: the declared link plus the live record."""

    link: RegistryLink
    record: Any  # connectors.registry.SourceRecord (kept as Any to stay decoupled)
    dispositions: tuple[RightsResolution, ...] = ()

    @property
    def source_id(self) -> str:
        return self.record.id

    @property
    def permitted(self) -> bool:
        return bool(self.record.ingestion_permitted)

    @property
    def p31_owned(self) -> bool:
        return self.record.id in P31_OWNED_SOURCES


@dataclass(frozen=True)
class RegistryJoin:
    """The resolved join of one candidate against registry + dispositions."""

    relation: RegistryRelation
    linked: tuple[LinkedSource, ...]
    #: Normalized-URL collision detail ("candidate:SRC-0NN" or "source:<id>").
    duplicate_of: str = ""


# --------------------------------------------------------------------------- #
# Rights — three separate lanes (SIG-ACQ-002)                                 #
# --------------------------------------------------------------------------- #


class LaneDecision(StrEnum):
    """The state of one rights lane. ``decided`` requires a recorded reviewer
    disposition — the queue itself can never mint one (HG-03)."""

    UNDETERMINED = "undetermined"
    DECIDED = "decided"
    REJECTED = "rejected"  # reviewed and not permissible — honest, not a bypass


class RightsLane(StrEnum):
    """The three lanes assessed separately (S5 rights-review packet)."""

    #: (a) Original document bytes and embedded third-party material (vendor
    #: exhibits, Lexipol boilerplate, photographs).
    DOCUMENT_BYTES = "document_bytes"
    #: (b) Access terms/technical constraints + factual extraction and
    #: permitted quotation.
    FACT_EXTRACTION = "fact_extraction"
    #: (d/e) Licence/compartment of derived outputs + publication posture.
    DERIVED_PUBLICATION = "derived_publication"


@dataclass(frozen=True)
class LaneRecord:
    """One rights lane: a decision state plus its recorded provenance."""

    decision: LaneDecision
    #: Repo-relative path/id of the recorded reviewer disposition (required for
    #: ``decided`` — e.g. a rights packet under docs/build/reports/rights/).
    decision_ref: str = ""
    #: The reviewer ROLE that recorded the decision (never a personal name).
    decided_by: str = ""
    decided_on: date | None = None
    basis: str = ""

    def problems(self, lane: RightsLane) -> list[str]:
        """Fail-closed validation — a decided lane must cite a recorded review."""
        errors: list[str] = []
        if self.decision == LaneDecision.DECIDED:
            if not self.decision_ref.strip():
                errors.append(
                    f"{lane.value}: decided without a recorded decision_ref "
                    "(a reviewer disposition the queue can cite, never invent)"
                )
            if not self.decided_by.strip():
                errors.append(f"{lane.value}: decided without a reviewer role (decided_by)")
            if self.decided_on is None:
                errors.append(f"{lane.value}: decided without a decision date")
            if not self.basis.strip():
                errors.append(f"{lane.value}: decided without a recorded basis")
        return errors


@dataclass(frozen=True)
class RightsAssessment:
    """The three separately-assessed rights lanes + observed context flags.

    ``municipal_publication_observed`` records that the artifact is published
    on a municipal/state site — an *observation*, never a licence decision:
    municipal publication is NOT auto-CC0 (17 U.S.C. §105 is federal-only;
    Compendium §313.6(C)(2) carves out copyrightable non-edict state/local
    works), so the flag can never satisfy a lane.
    """

    document_bytes: LaneRecord
    fact_extraction: LaneRecord
    derived_publication: LaneRecord
    municipal_publication_observed: bool = False

    def lanes(self) -> tuple[tuple[RightsLane, LaneRecord], ...]:
        return (
            (RightsLane.DOCUMENT_BYTES, self.document_bytes),
            (RightsLane.FACT_EXTRACTION, self.fact_extraction),
            (RightsLane.DERIVED_PUBLICATION, self.derived_publication),
        )

    def decided(self) -> bool:
        """All three lanes carry recorded decisions."""
        return all(lr.decision == LaneDecision.DECIDED for _, lr in self.lanes())

    def rejected(self) -> bool:
        """Any lane reviewed and found not permissible."""
        return any(lr.decision == LaneDecision.REJECTED for _, lr in self.lanes())

    def problems(self) -> list[str]:
        errors: list[str] = []
        for lane, record in self.lanes():
            errors.extend(record.problems(lane))
        return errors


# --------------------------------------------------------------------------- #
# Part VIII preflight                                                         #
# --------------------------------------------------------------------------- #


class PreflightStatus(StrEnum):
    """The Part VIII (SIG-PUB-002) sensitivity preflight state."""

    #: Nobody has screened the artifact — cannot be assumed clean.
    NOT_ASSESSED = "not_assessed"
    #: Person-level fields are known/suspected; capture must be screened or
    #: restricted to safe aggregates before any acquisition.
    SCREENING_REQUIRED = "screening_required"
    #: Acquisition is prohibited until an explicit content-admissibility +
    #: rights decision (e.g. per-query network-audit workbooks).
    PROHIBITED_UNTIL_REVIEW = "prohibited_until_review"
    #: Screened; no excluded category present.
    CLEAR = "clear"
    #: Contains categorically excluded content that cannot be remediated —
    #: a hard rejection no score can offset.
    REJECTED = "rejected"


@dataclass(frozen=True)
class PartVIIIPreflight:
    """The sensitivity preflight carried before prioritization (SIG-ACQ-002)."""

    status: PreflightStatus
    #: Which PART_VIII_EXCLUDED_CATEGORIES may be present.
    flags: tuple[str, ...] = ()
    notes: str = ""

    def problems(self) -> list[str]:
        return [
            f"preflight flag {f!r} is not a Part VIII excluded category"
            for f in self.flags
            if f not in PART_VIII_EXCLUDED_CATEGORIES
        ]


# --------------------------------------------------------------------------- #
# Score model (acq-score/1)                                                    #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DimensionAssessment:
    """One versioned set of the nine ordinal inputs (SIG-ACQ-001/002).

    The assessor is a role label (never a personal name); ``evidence`` cites
    what the values derive from; ``measured=False`` marks estimates. A value of
    ``None`` means *unknown* — unknown stays unknown rather than silently
    defaulting, and the candidate scores as unscored with named unknowns.
    """

    version: str
    assessor: str
    assessed_on: date
    evidence: str
    measured: bool
    values: Mapping[str, int | None]

    def problems(self) -> list[str]:
        errors: list[str] = []
        if not self.version.strip():
            errors.append("assessment version is empty — inputs must be versioned")
        if not self.assessor.strip():
            errors.append("assessor is empty — a role label is required")
        if not self.evidence.strip():
            errors.append("evidence is empty — every score input cites its basis")
        keys = set(self.values)
        if keys != set(DIMENSIONS):
            errors.append(
                f"dimensions must be exactly {list(DIMENSIONS)}, "
                f"got {sorted(keys)} (missing {sorted(set(DIMENSIONS) - keys)}, "
                f"extra {sorted(keys - set(DIMENSIONS))})"
            )
        for dim, val in self.values.items():
            if val is not None and not (0 <= val <= 3):
                errors.append(f"dimension {dim} = {val}; must be 0..3 or null (unknown)")
        return errors


@dataclass(frozen=True)
class ScoreResult:
    """The computed score under a named model+input version.

    ``value`` is ``None`` when any dimension is unknown — an unscored candidate
    reports its named unknowns rather than a fabricated number.
    """

    scoring_version: str
    assessment_version: str
    value: int | None
    contributions: dict[str, int]
    unscored_dimensions: tuple[str, ...]


def score(assessment: DimensionAssessment) -> ScoreResult:
    """Compute ``3G + 3R + 2I + 2U + T + J − 2E − 2A − 2S`` (acq-score/1).

    Returns the weighted total plus the per-dimension contribution table that
    makes any score explainable from its inputs. Unknown dimensions stay
    unknown: ``value`` is ``None`` and they are named in
    ``unscored_dimensions``.
    """
    errors = assessment.problems()
    if errors:
        raise AcquisitionQueueError("invalid dimension assessment: " + "; ".join(errors))
    contributions = {d: DIMENSION_WEIGHTS[d] * (assessment.values[d] or 0) for d in DIMENSIONS}
    unknown = tuple(d for d in DIMENSIONS if assessment.values[d] is None)
    value = None if unknown else sum(contributions.values())
    return ScoreResult(
        scoring_version=SCORING_VERSION,
        assessment_version=assessment.version,
        value=value,
        contributions=contributions,
        unscored_dimensions=unknown,
    )


@dataclass(frozen=True)
class DimensionDelta:
    """One dimension's change between two versioned assessment sets."""

    dimension: str
    old: int | None
    new: int | None
    weight: int
    delta: int  # weighted contribution change


def diff_assessments(
    old: DimensionAssessment, new: DimensionAssessment
) -> tuple[DimensionDelta, ...]:
    """Explain a score change between two versioned input sets.

    Returns the per-dimension deltas (weighted) so a changed score is
    explainable from the recorded inputs rather than a black box.
    """
    deltas: list[DimensionDelta] = []
    for d in DIMENSIONS:
        ov, nv = old.values.get(d), new.values.get(d)
        if ov != nv:
            deltas.append(
                DimensionDelta(
                    dimension=d,
                    old=ov,
                    new=nv,
                    weight=DIMENSION_WEIGHTS[d],
                    delta=DIMENSION_WEIGHTS[d] * ((nv or 0) - (ov or 0)),
                )
            )
    return tuple(deltas)


# --------------------------------------------------------------------------- #
# Candidate passport                                                          #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DiscoveryProvenance:
    """How the candidate was found and how deeply it was reviewed."""

    primary_url: str
    secondary_url: str
    accessed_on: date
    #: The research review-depth verbatim (e.g. ``primary_search_excerpts``) —
    #: search excerpts are leads, not full-document review.
    review_status: str
    reviewed_scope: str
    #: The research row's own registry/plan note (dedupe context).
    existing_registry_or_plan: str


@dataclass(frozen=True)
class RegistryLinkSpec:
    source_id: str
    kind: LinkKind
    note: str = ""


@dataclass(frozen=True)
class CostRecord:
    """Cost honesty: estimates and measurements are different fields.

    ``measured_minutes`` is ``None`` until an approved run reports real
    minutes — an estimate is never silently relabelled as a measurement.
    """

    estimated_effort: str  # verbatim research effort band (L-M / M / M-H / H)
    estimated_basis: str = ""
    measured_minutes: int | None = None
    measured_basis: str = ""

    def problems(self) -> list[str]:
        errors: list[str] = []
        if self.measured_minutes is not None and not self.measured_basis.strip():
            errors.append("measured_minutes requires measured_basis")
        if self.measured_minutes is not None and self.measured_minutes < 0:
            errors.append("measured_minutes cannot be negative")
        return errors


@dataclass(frozen=True)
class CandidatePassport:
    """The full passport every candidate must carry before prioritization."""

    candidate_id: str
    rank: int
    family: str
    jurisdiction: str
    #: The publishing authority for rights review (institution, not a person).
    authority: str
    #: The named evidence/question/relationship gap or justified need this
    #: candidate exists to close — acquisition never starts from a source
    #: without one (SIG-ACQ-001).
    gap: str
    #: The temporal scope the artifact itself covers (scope/time — SIG-ACQ-002).
    content_window: str
    novelty: str
    priority: str
    claims_supported: str
    not_supported: str
    rights_access_unknowns: str
    lineage_notes: str
    dependencies: str
    target_predicates: tuple[str, ...]
    discovery: DiscoveryProvenance
    lineage_class: LineageClass
    #: Institutional provenance group — two candidates in one group cannot
    #: corroborate each other (an aggregate and its underlying audit are one
    #: provenance even when separately fetched).
    lineage_group: str
    registry_links: tuple[RegistryLinkSpec, ...]
    rights: RightsAssessment
    preflight: PartVIIIPreflight
    dimensions: DimensionAssessment
    cost: CostRecord
    extra_questions: tuple[str, ...] = ()

    @property
    def independent_yield(self) -> bool:
        """Whether this candidate can add independent corroboration."""
        return self.lineage_class not in NON_INDEPENDENT_LINEAGE

    def problems(self) -> list[str]:
        errors: list[str] = []
        if not self.candidate_id.strip():
            errors.append("candidate_id is empty")
        if not self.authority.strip():
            errors.append(f"{self.candidate_id}: authority is empty")
        if not self.jurisdiction.strip():
            errors.append(f"{self.candidate_id}: jurisdiction is empty")
        if not self.gap.strip():
            errors.append(
                f"{self.candidate_id}: gap is empty — a candidate must start "
                "from a named evidence/question/relationship gap"
            )
        if not self.content_window.strip():
            errors.append(f"{self.candidate_id}: content_window (scope/time) is empty")
        if not self.discovery.primary_url.strip():
            errors.append(f"{self.candidate_id}: primary_url is empty")
        if not self.discovery.review_status.strip():
            errors.append(f"{self.candidate_id}: review_status (depth) is empty")
        if not self.novelty.strip():
            errors.append(f"{self.candidate_id}: novelty is empty")
        if not self.lineage_group.strip():
            errors.append(f"{self.candidate_id}: lineage_group is empty")
        errors.extend(self.rights.problems())
        errors.extend(self.preflight.problems())
        errors.extend(self.dimensions.problems())
        errors.extend(self.cost.problems())
        if not self.independent_yield and (self.dimensions.values.get("I") or 0) > 0:
            errors.append(
                f"{self.candidate_id}: lineage_class={self.lineage_class.value!r} "
                "cannot yield independent corroboration — dimension I must be 0 "
                "(a mirror never scores as independent)"
            )
        return errors


def independent_corroboration(a: CandidatePassport, b: CandidatePassport) -> bool:
    """Whether ``b`` can corroborate ``a``'s claims as an independent source.

    False whenever either side is a non-independent lineage class or the two
    share an institutional ``lineage_group`` — mirrors, derivatives and
    same-publisher document families are one provenance.
    """
    return (
        a.independent_yield
        and b.independent_yield
        and a.lineage_group != b.lineage_group
        and a.candidate_id != b.candidate_id
    )


# --------------------------------------------------------------------------- #
# Hard gates + queue disposition                                              #
# --------------------------------------------------------------------------- #


class Gate(StrEnum):
    """The score-independent gates a queue entry carries."""

    #: One or more rights lanes unresolved — routed to rights review.
    RIGHTS_UNDETERMINED = "rights_undetermined"
    #: A rights lane was reviewed and found not permissible.
    RIGHTS_REJECTED = "rights_rejected"
    #: Municipal/state publication observed — municipal publication is not
    #: auto-CC0; needs the explicit non-edict review.
    MUNICIPAL_RIGHTS_REVIEW = "municipal_rights_review"
    #: Part VIII preflight un-screened or screening-required.
    PREFLIGHT_REQUIRED = "preflight_required"
    #: Prohibited until an explicit content-admissibility decision.
    PREFLIGHT_PROHIBITED = "preflight_prohibited"
    #: Categorically excluded content — refused outright.
    SENSITIVE_REJECTED = "sensitive_rejected"
    #: P31.12/.13-owned source — consumed/improved, never re-onboarded.
    P31_OWNED = "p31_owned"
    #: Literal duplicate of another candidate or a registered homepage.
    DUPLICATE = "duplicate"


class QueueDisposition(StrEnum):
    """Where a queue entry routes. None of them is an approval."""

    #: New target awaiting the operator's scoped review (HG-03 leg).
    REVIEW_NEW_TARGET = "review_new_target"
    #: Improvement/deepening under an already-registered source row.
    REVIEW_IMPROVEMENT = "review_improvement"
    #: A P31-owned source — consumed/improved under prior decisions only.
    CONSUME_EXISTING = "consume_existing"
    #: Literal duplicate — never onboarded twice.
    REFUSED_DUPLICATE = "refused_duplicate"
    #: Sensitive-content rejection or rights-rejected — blocked regardless
    #: of usefulness.
    BLOCKED = "blocked"


@dataclass(frozen=True)
class QueueEntry:
    """One fully-joined, gated, scored queue row."""

    passport: CandidatePassport
    join: RegistryJoin
    score_result: ScoreResult
    gates: frozenset[Gate]
    disposition: QueueDisposition
    #: "improvement" (an existing row is deepened) or "new_target".
    kind: str
    #: What the review depth does and does not establish (honest bounds).
    uncertainty: str
    missing_questions: tuple[str, ...]

    @property
    def admissible(self) -> bool:
        """Whether the entry has passed every hard gate (no gate ≠ approval —
        an admissible candidate still needs the recorded operator decision)."""
        return not self.gates

    @property
    def onboardable(self) -> bool:
        """Whether this could ever be registered as a NEW source row —
        requires a gate-clean (admissible) net-new review target. Still not an
        approval: the recorded operator decision comes first."""
        return (
            self.admissible
            and self.join.relation == RegistryRelation.NET_NEW
            and self.disposition == QueueDisposition.REVIEW_NEW_TARGET
        )


def gates_for(passport: CandidatePassport, join: RegistryJoin) -> frozenset[Gate]:
    """Compute the score-independent hard gates for one candidate.

    Usefulness cannot open these: they are AND-ed after the score, never
    added to it (SIG-ACQ-002).
    """
    gates: set[Gate] = set()
    if join.relation == RegistryRelation.P31_OWNED:
        gates.add(Gate.P31_OWNED)
    if join.relation == RegistryRelation.DUPLICATE:
        gates.add(Gate.DUPLICATE)
    if passport.rights.rejected():
        gates.add(Gate.RIGHTS_REJECTED)
    elif not passport.rights.decided():
        gates.add(Gate.RIGHTS_UNDETERMINED)
    if passport.rights.municipal_publication_observed:
        gates.add(Gate.MUNICIPAL_RIGHTS_REVIEW)
    if passport.preflight.status == PreflightStatus.REJECTED:
        gates.add(Gate.SENSITIVE_REJECTED)
    elif passport.preflight.status == PreflightStatus.PROHIBITED_UNTIL_REVIEW:
        gates.add(Gate.PREFLIGHT_PROHIBITED)
    elif passport.preflight.status in (
        PreflightStatus.NOT_ASSESSED,
        PreflightStatus.SCREENING_REQUIRED,
    ):
        gates.add(Gate.PREFLIGHT_REQUIRED)
    return frozenset(gates)


def disposition_for(
    passport: CandidatePassport, join: RegistryJoin, gates: frozenset[Gate]
) -> QueueDisposition:
    """Route the entry — none of these dispositions is an approval."""
    if Gate.DUPLICATE in gates:
        return QueueDisposition.REFUSED_DUPLICATE
    if Gate.P31_OWNED in gates:
        return QueueDisposition.CONSUME_EXISTING
    if Gate.SENSITIVE_REJECTED in gates or Gate.RIGHTS_REJECTED in gates:
        return QueueDisposition.BLOCKED
    if join.relation in (
        RegistryRelation.EXISTING_PERMITTED,
        RegistryRelation.EXISTING_UNPERMITTED,
    ) or passport.novelty.startswith("existing_"):
        return QueueDisposition.REVIEW_IMPROVEMENT
    return QueueDisposition.REVIEW_NEW_TARGET


# --------------------------------------------------------------------------- #
# Loading — the CSV inventory + the committed queue data                      #
# --------------------------------------------------------------------------- #


def _repo_root() -> Path:
    """The repository root (tasks/src/tasks/acquisition.py → parents[3])."""
    return Path(__file__).resolve().parents[3]


def _parse_date(raw: str, where: str) -> date:
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise AcquisitionQueueError(f"{where}: bad date {raw!r}") from exc


def normalize_url(url: str) -> str:
    """Normalize a URL for duplicate detection: scheme/case/www/trailing-slash
    insensitive, query+fragment dropped. Not for fetching — dedupe only."""
    parts = urlsplit(url.strip())
    host = (parts.netloc or parts.path.split("/")[0]).lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path if parts.netloc else "/".join(parts.path.split("/")[1:])
    path = "/" + path.strip("/") if path.strip("/") else ""
    return f"{host}{path}"


def load_research_rows(path: str | Path | None = None) -> list[dict[str, str]]:
    """Parse the committed candidate CSV verbatim (the 27-row inventory)."""
    csv_path = Path(path) if path else _repo_root() / DEFAULT_INVENTORY
    with csv_path.open(newline="", encoding="utf-8") as fh:
        rows = [dict(r) for r in csv.DictReader(fh)]
    if not rows:
        raise AcquisitionQueueError(f"{csv_path}: no candidate rows")
    required = {
        "rank",
        "candidate_id",
        "family",
        "jurisdiction",
        "primary_url",
        "novelty",
        "accessed_on",
        "review_status",
        "priority",
        "effort",
    }
    for i, row in enumerate(rows):
        missing = [k for k in required if not (row.get(k) or "").strip()]
        if missing:
            raise AcquisitionQueueError(
                f"{csv_path} row {i} ({row.get('candidate_id', '?')}): "
                f"missing required fields {missing}"
            )
    return rows


def _lane(raw: Mapping[str, Any]) -> LaneRecord:
    decided_on = raw.get("decided_on")
    return LaneRecord(
        decision=LaneDecision(str(raw.get("decision", "undetermined"))),
        decision_ref=str(raw.get("decision_ref", "")),
        decided_by=str(raw.get("decided_by", "")),
        decided_on=(
            decided_on
            if isinstance(decided_on, date)
            else (_parse_date(str(decided_on), "decided_on") if decided_on else None)
        ),
        basis=str(raw.get("basis", "")),
    )


def _load_dispositions(root: Path) -> dict[str, list[RightsResolution]]:
    """Join the recorded rights dispositions (P27.2/P29.3 artifacts)."""
    by_source: dict[str, list[RightsResolution]] = {}
    for rel in DISPOSITION_ARTIFACTS:
        path = root / rel
        if not path.exists():
            continue
        for res in load_resolutions(path):
            by_source.setdefault(res.source_id, []).append(res)
    return by_source


def load_candidates(
    csv_path: str | Path | None = None,
    *,
    queue_table: Mapping[str, Any] | None = None,
    root: Path | None = None,
) -> list[CandidatePassport]:
    """Build the 27 passports: CSV provenance + committed queue data merged.

    The queue TOML supplies what the research CSV does not: registry links,
    lineage class/group, rights lanes (all ``undetermined`` at seed — the queue
    cannot mint decisions), Part VIII flags, target predicates, and the
    versioned dimension assessment. Any passport problem raises
    :class:`AcquisitionQueueError` — a malformed candidate fails closed.
    """
    table = queue_table if queue_table is not None else load_table("acquisition_queue")
    if str(table.get("schema", "")) != QUEUE_SCHEMA:
        raise AcquisitionQueueError(
            f"acquisition queue schema must be {QUEUE_SCHEMA!r}, got {table.get('schema')!r}"
        )
    candidates_data: Mapping[str, Any] = table.get("candidates", {})
    assessment_data: Mapping[str, Any] = table.get("assessment", {})

    rows = load_research_rows(csv_path)
    passports: list[CandidatePassport] = []
    errors: list[str] = []
    seen_ids: set[str] = set()
    for i, row in enumerate(rows):
        cid = str(row["candidate_id"]).strip()
        where = f"candidate {cid} (csv row {i})"
        if cid in seen_ids:
            errors.append(f"{where}: duplicate candidate_id")
            continue
        seen_ids.add(cid)
        supp = candidates_data.get(cid)
        if supp is None:
            errors.append(f"{where}: no acquisition_queue.toml entry")
            continue
        try:
            links = tuple(
                RegistryLinkSpec(
                    source_id=str(ln["id"]),
                    kind=LinkKind(str(ln.get("kind", "related"))),
                    note=str(ln.get("note", "")),
                )
                for ln in supp.get("links", [])
            )
            rights_raw = supp.get("rights", {})
            preflight_raw = supp.get("preflight", {})
            dims_raw = supp.get("dimensions", {})
            extra_dims = sorted(set(dims_raw) - set(DIMENSIONS))
            if extra_dims:
                raise AcquisitionQueueError(
                    f"{where}: unknown dimension keys {extra_dims} — "
                    f"the closed set is {list(DIMENSIONS)}"
                )
            passport = CandidatePassport(
                candidate_id=cid,
                rank=int(str(row["rank"]).strip()),
                family=str(row["family"]).strip(),
                jurisdiction=str(row["jurisdiction"]).strip(),
                authority=str(supp.get("authority", "")).strip(),
                gap=str(supp.get("gap", "")).strip(),
                content_window=str(supp.get("content_window", "")).strip(),
                novelty=str(row["novelty"]).strip(),
                priority=str(row["priority"]).strip(),
                claims_supported=str(row.get("claims_supported", "")).strip(),
                not_supported=str(row.get("not_supported", "")).strip(),
                rights_access_unknowns=str(row.get("rights_access_unknowns", "")).strip(),
                lineage_notes=str(row.get("lineage_notes", "")).strip(),
                dependencies=str(row.get("dependencies", "")).strip(),
                target_predicates=tuple(str(p) for p in supp.get("target_predicates", [])),
                discovery=DiscoveryProvenance(
                    primary_url=str(row["primary_url"]).strip(),
                    secondary_url=str(row.get("secondary_url", "") or "").strip(),
                    accessed_on=_parse_date(str(row["accessed_on"]), where),
                    review_status=str(row["review_status"]).strip(),
                    reviewed_scope=str(row.get("reviewed_scope", "")).strip(),
                    existing_registry_or_plan=str(row.get("existing_registry_or_plan", "")).strip(),
                ),
                lineage_class=LineageClass(str(supp.get("lineage_class", "independent_account"))),
                lineage_group=str(supp.get("lineage_group", "")).strip(),
                registry_links=links,
                rights=RightsAssessment(
                    document_bytes=_lane(rights_raw.get("document_bytes", {})),
                    fact_extraction=_lane(rights_raw.get("fact_extraction", {})),
                    derived_publication=_lane(rights_raw.get("derived_publication", {})),
                    municipal_publication_observed=bool(supp.get("municipal_publication", False)),
                ),
                preflight=PartVIIIPreflight(
                    status=PreflightStatus(str(preflight_raw.get("status", "not_assessed"))),
                    flags=tuple(str(f) for f in preflight_raw.get("flags", [])),
                    notes=str(preflight_raw.get("notes", "")),
                ),
                dimensions=DimensionAssessment(
                    version=str(assessment_data.get("version", "")),
                    assessor=str(assessment_data.get("assessor", "")),
                    assessed_on=_parse_date(str(assessment_data.get("assessed_on", "")), where),
                    evidence=str(supp.get("dimension_evidence", "")),
                    measured=bool(assessment_data.get("measured", False)),
                    values={
                        d: (int(dims_raw[d]) if dims_raw.get(d) is not None else None)
                        for d in DIMENSIONS
                    },
                ),
                cost=CostRecord(
                    estimated_effort=str(row.get("effort", "")).strip(),
                    estimated_basis=(
                        "research effort band (source-candidates.csv `effort`); "
                        "ordinal, not minutes"
                    ),
                    measured_minutes=None,
                    measured_basis="",
                ),
                extra_questions=tuple(str(q) for q in supp.get("extra_questions", [])),
            )
            problems = passport.problems()
            if problems:
                errors.extend(f"{where}: {p}" for p in problems)
                continue
            passports.append(passport)
        except (KeyError, ValueError, AcquisitionQueueError) as exc:
            errors.append(f"{where}: {exc}")
    if errors:
        raise AcquisitionQueueError("invalid acquisition queue:\n  " + "\n  ".join(errors))
    return passports


# --------------------------------------------------------------------------- #
# The join                                                                    #
# --------------------------------------------------------------------------- #


def join_candidate(
    passport: CandidatePassport,
    *,
    registry: Mapping[str, Any] | None = None,
    dispositions: Mapping[str, list[RightsResolution]] | None = None,
    peers: Sequence[CandidatePassport] = (),
) -> RegistryJoin:
    """Resolve one candidate against the live registry + recorded dispositions.

    ``same_source`` links make the candidate *identical to* the linked row —
    ``p31_owned`` when the row is P31-owned (refused re-onboarding), else
    ``existing_permitted``/``existing_unpermitted``. A normalized-URL collision
    — across sibling candidates or a registered ``homepage_url`` — is a literal
    ``duplicate``. Everything else is ``net_new`` with its ``related`` context.
    """
    reg = registry if registry is not None else source_registry()
    if dispositions is None:
        dispositions = _load_dispositions(_repo_root())

    linked: list[LinkedSource] = []
    errors: list[str] = []
    for spec in passport.registry_links:
        record = reg.get(spec.source_id)
        if record is None:
            errors.append(
                f"{passport.candidate_id}: registry link {spec.source_id!r} "
                "does not resolve to a registered source"
            )
            continue
        linked.append(
            LinkedSource(
                link=RegistryLink(source_id=spec.source_id, kind=spec.kind, note=spec.note),
                record=record,
                dispositions=tuple(dispositions.get(spec.source_id, ())),
            )
        )
    if errors:
        raise AcquisitionQueueError("; ".join(errors))

    # Identity links (the candidate IS an existing row).
    same = [ls for ls in linked if ls.link.kind == LinkKind.SAME_SOURCE]
    if any(ls.p31_owned for ls in same):
        return RegistryJoin(relation=RegistryRelation.P31_OWNED, linked=tuple(linked))
    if same:
        if any(ls.permitted for ls in same):
            return RegistryJoin(relation=RegistryRelation.EXISTING_PERMITTED, linked=tuple(linked))
        return RegistryJoin(relation=RegistryRelation.EXISTING_UNPERMITTED, linked=tuple(linked))

    # Literal URL duplicates — against sibling candidates and registered homepages.
    own = {
        normalize_url(u)
        for u in (passport.discovery.primary_url, passport.discovery.secondary_url)
        if u
    }
    for peer in peers:
        if peer.candidate_id == passport.candidate_id:
            continue
        theirs = {
            normalize_url(u)
            for u in (peer.discovery.primary_url, peer.discovery.secondary_url)
            if u
        }
        if own & theirs:
            return RegistryJoin(
                relation=RegistryRelation.DUPLICATE,
                linked=tuple(linked),
                duplicate_of=f"candidate:{peer.candidate_id}",
            )
    for record in reg.values():
        home = getattr(record, "homepage_url", "") or ""
        if home and normalize_url(home) in own:
            return RegistryJoin(
                relation=RegistryRelation.DUPLICATE,
                linked=tuple(linked),
                duplicate_of=f"source:{record.id}",
            )
    return RegistryJoin(relation=RegistryRelation.NET_NEW, linked=tuple(linked))


# --------------------------------------------------------------------------- #
# Uncertainty + missing questions + review packets                            #
# --------------------------------------------------------------------------- #

_DEPTH_BOUNDS: tuple[tuple[str, str], ...] = (
    (
        "primary_search_excerpts",
        "search-result excerpts only — documents not read in full; nothing here "
        "is full-document review or production evidence",
    ),
    (
        "index_metadata_only",
        "index/metadata only — artifact bytes never fetched; no content-level claim can be drawn",
    ),
    (
        "index_opened",
        "index opened, selected excerpts — full artifacts unreviewed",
    ),
    (
        "opened_selected_text",
        "selected sections read — the full document was not reviewed",
    ),
    (
        "opened_text",
        "text reviewed at the stated scope — portions outside `reviewed_scope` are unverified",
    ),
)


def uncertainty_for(passport: CandidatePassport) -> str:
    """The honest bound on what this candidate's review established."""
    status = passport.discovery.review_status
    for prefix, text in _DEPTH_BOUNDS:
        if status.startswith(prefix):
            return f"{status}: {text}"
    return f"{status}: review depth as recorded; residual risk unquantified"


def missing_questions(passport: CandidatePassport, join: RegistryJoin) -> tuple[str, ...]:
    """The precise questions an operator's review must answer — generated from
    the undetermined/unknown fields, one per open gap, plus the research row's
    own stated unknowns."""
    qs: list[str] = []
    name = passport.family
    authority = passport.authority
    url = passport.discovery.primary_url

    if passport.rights.document_bytes.decision == LaneDecision.UNDETERMINED:
        qs.append(
            f"Do {authority}'s terms permit lawful capture and retention of "
            f"{url} and its linked artifacts — including embedded third-party "
            "material (vendor exhibits, boilerplate policy text, photographs)?"
        )
    if passport.rights.fact_extraction.decision == LaneDecision.UNDETERMINED:
        qs.append(
            "May SIG store and publish the factual fields extracted from this "
            f"document ({passport.claims_supported}) — and under which "
            "attribution and quotation posture?"
        )
    if passport.rights.derived_publication.decision == LaneDecision.UNDETERMINED:
        qs.append(
            "Which licence compartment and attribution govern claims derived "
            f"from {name}, and may the derived artifacts be republished?"
        )
    if passport.rights.municipal_publication_observed:
        qs.append(
            "Is this municipal/state publication an uncopyrightable edict or "
            "public record under the applicable law, or a copyrightable "
            "non-edict work (Compendium §313.6(C)(2))? Municipal publication is "
            "not auto-CC0 — a recorded determination is required."
        )
    for flag in passport.preflight.flags:
        qs.append(
            f"Does the artifact contain {flag.replace('_', ' ')} content "
            "(a Part VIII excluded category), and if so what redaction or "
            "aggregate-only capture is required before any acquisition?"
        )
    if passport.preflight.status == PreflightStatus.PROHIBITED_UNTIL_REVIEW:
        qs.append(
            "What explicit content-admissibility and rights decision would "
            "permit acquiring this target at all — and is the safe-aggregate "
            "alternative sufficient for the dossier gap it answers?"
        )
    if passport.rights_access_unknowns:
        qs.append(f"Research-recorded unknown: {passport.rights_access_unknowns}")
    qs.extend(passport.extra_questions)
    for linked in join.linked:
        if linked.link.kind == LinkKind.RELATED:
            qs.append(
                f"Does {linked.record.id}'s existing coverage "
                f"({linked.record.name}) already supply any of this candidate's "
                "expected claims — i.e., what is the net-new remainder after "
                "deduplication?"
            )
    return tuple(qs)


def build_queue(
    csv_path: str | Path | None = None,
    *,
    queue_table: Mapping[str, Any] | None = None,
    registry: Mapping[str, Any] | None = None,
    dispositions: Mapping[str, list[RightsResolution]] | None = None,
    root: Path | None = None,
) -> list[QueueEntry]:
    """Join + gate + score every candidate into the reviewed queue."""
    passports = load_candidates(csv_path, queue_table=queue_table, root=root)
    if dispositions is None:
        dispositions = _load_dispositions(root or _repo_root())
    entries: list[QueueEntry] = []
    for passport in passports:
        join = join_candidate(
            passport, registry=registry, dispositions=dispositions, peers=passports
        )
        gates = gates_for(passport, join)
        entries.append(
            QueueEntry(
                passport=passport,
                join=join,
                score_result=score(passport.dimensions),
                gates=gates,
                disposition=disposition_for(passport, join, gates),
                kind=(
                    "improvement"
                    if any(ls.link.kind == LinkKind.SAME_SOURCE for ls in join.linked)
                    or passport.novelty.startswith("existing_")
                    else "new_target"
                ),
                uncertainty=uncertainty_for(passport),
                missing_questions=missing_questions(passport, join),
            )
        )
    return entries


def rank_entries(entries: Sequence[QueueEntry]) -> list[QueueEntry]:
    """Deterministic priority order: scored desc, unscored last, rank asc."""

    def key(e: QueueEntry) -> tuple[int, int, int]:
        return (
            0 if e.score_result.value is not None else 1,
            -(e.score_result.value or 0),
            e.passport.rank,
        )

    return sorted(entries, key=key)


# --------------------------------------------------------------------------- #
# CI invariants (`sig-tasks acquisition check`)                               #
# --------------------------------------------------------------------------- #


def check_queue(entries: Sequence[QueueEntry]) -> list[str]:
    """The completeness invariants a CI gate enforces on the queue.

    A violation means the queue data is malformed — it fails loudly, never
    silently degrades to an unreviewed state.
    """
    violations: list[str] = []
    ids: set[str] = set()
    for e in entries:
        p = e.passport
        if p.candidate_id in ids:
            violations.append(f"duplicate candidate_id {p.candidate_id}")
        ids.add(p.candidate_id)
        if not e.missing_questions:
            violations.append(f"{p.candidate_id}: no missing questions generated")
        if not e.uncertainty.strip():
            violations.append(f"{p.candidate_id}: uncertainty is empty")
        if p.cost.measured_minutes is not None and not p.cost.measured_basis:
            violations.append(f"{p.candidate_id}: measured cost without a measured basis")
        for lane, record in p.rights.lanes():
            if record.decision == LaneDecision.DECIDED and not record.decision_ref:
                violations.append(
                    f"{p.candidate_id}/{lane.value}: decided without a recorded "
                    "decision_ref (the queue cannot mint approvals)"
                )
    return violations


# --------------------------------------------------------------------------- #
# Review packets + the queue report                                           #
# --------------------------------------------------------------------------- #


def _fmt_decision(record: LaneRecord) -> str:
    if record.decision == LaneDecision.DECIDED:
        return (
            f"decided (ref `{record.decision_ref}`, {record.decided_by}, "
            f"{record.decided_on}, {record.basis})"
        )
    return record.decision.value


def review_packet(entry: QueueEntry) -> str:
    """Render the operator review packet for one candidate.

    The packet organizes what a reviewer must decide; it authorizes nothing
    and fabricates no review.
    """
    p = entry.passport
    s = entry.score_result
    lines: list[str] = []
    lines.append(f"# Acquisition review packet — {p.candidate_id}: {p.family}")
    lines.append("")
    lines.append("**This packet authorizes nothing.** It is the reviewed-queue")
    lines.append("input for the operator's scoped source/evidence-use review")
    lines.append("(HG-03 leg of `D-R10-SOURCES-1`); no source is flipped, fetched,")
    lines.append("or approved by its existence.")
    lines.append("")
    lines.append("## Passport")
    lines.append("")
    lines.append(
        f"- Candidate: `{p.candidate_id}` (research rank {p.rank}, priority `{p.priority}`)"
    )
    lines.append(f"- Authority / publisher: {p.authority}")
    lines.append(f"- Jurisdiction / scope: {p.jurisdiction}")
    lines.append(f"- Named gap this candidate closes: {p.gap}")
    lines.append(f"- Content window (scope/time): {p.content_window}")
    lines.append(f"- Novelty: `{p.novelty}` — {p.discovery.existing_registry_or_plan}")
    lines.append(f"- Primary URL: {p.discovery.primary_url}")
    if p.discovery.secondary_url:
        lines.append(f"- Secondary URL: {p.discovery.secondary_url}")
    lines.append(f"- Accessed: {p.discovery.accessed_on.isoformat()}")
    lines.append(f"- Review depth: `{p.discovery.review_status}` — {p.discovery.reviewed_scope}")
    lines.append(f"- Expected claims: {p.claims_supported}")
    lines.append(f"- Explicitly not supported: {p.not_supported}")
    lines.append(f"- Target predicates: {', '.join(p.target_predicates) or '(none declared)'}")
    lines.append(f"- Dependencies: {p.dependencies or '(none)'}")
    lines.append("")
    lines.append("## Registry + disposition join")
    lines.append("")
    lines.append(
        f"- Relation: `{entry.join.relation.value}`; queue kind: `{entry.kind}`; "
        f"disposition: `{entry.disposition.value}`"
    )
    if entry.join.duplicate_of:
        lines.append(f"- Duplicate of: `{entry.join.duplicate_of}`")
    for ls in entry.join.linked:
        st = "ingestion_permitted" if ls.permitted else "not permitted"
        p31 = " (P31.12/.13-owned)" if ls.p31_owned else ""
        lines.append(f"- `{ls.link.kind.value}` → `{ls.source_id}` — {ls.record.name} [{st}]{p31}")
        for d in ls.dispositions:
            lines.append(
                f"  - recorded disposition {d.reviewed_on}: {d.spdx} "
                f"(redistributable={d.redistributable}, by {d.reviewed_by}) — "
                f"{d.review_packet or 'no packet ref'}"
            )
    lines.append("")
    lines.append("## Lineage")
    lines.append("")
    lines.append(f"- Class: `{p.lineage_class.value}`; group: `{p.lineage_group}`")
    yield_text = "yes" if p.independent_yield else "NO — one provenance, cannot corroborate"
    lines.append(f"- Independent corroboration yield: **{yield_text}**")
    lines.append(f"- Lineage notes: {p.lineage_notes}")
    lines.append("")
    lines.append("## Rights (three separate lanes)")
    lines.append("")
    for lane, record in p.rights.lanes():
        lines.append(f"- `{lane.value}`: {_fmt_decision(record)}")
    municipal = (
        "yes — not auto-CC0, needs the non-edict determination"
        if p.rights.municipal_publication_observed
        else "no"
    )
    lines.append(f"- Municipal publication observed: {municipal}")
    lines.append("")
    lines.append("## Part VIII preflight")
    lines.append("")
    lines.append(f"- Status: `{p.preflight.status.value}`")
    if p.preflight.flags:
        lines.append(f"- Excluded-category flags: {', '.join(p.preflight.flags)}")
    if p.preflight.notes:
        lines.append(f"- Notes: {p.preflight.notes}")
    lines.append("")
    lines.append("## Score (versioned inputs)")
    lines.append("")
    lines.append(
        f"- Model `{s.scoring_version}` over assessment `{s.assessment_version}` "
        f"(assessor: {p.dimensions.assessor}; measured: {p.dimensions.measured})"
    )
    lines.append(
        f"- Value: **{s.value if s.value is not None else 'unscored'}**"
        + (
            f" — unscored dimensions: {', '.join(s.unscored_dimensions)}"
            if s.unscored_dimensions
            else ""
        )
    )
    contrib = ", ".join(f"{d}:{s.contributions[d]:+d}" for d in DIMENSIONS)
    lines.append(f"- Contributions: {contrib}")
    lines.append("")
    lines.append("## Gates")
    lines.append("")
    if entry.gates:
        for g in sorted(g.value for g in entry.gates):
            lines.append(f"- `{g}`")
    else:
        lines.append(
            "- none — *admissible* (still requires the recorded operator "
            "decision; admissible ≠ approved)"
        )
    lines.append("")
    lines.append("## Cost + uncertainty")
    lines.append("")
    lines.append(f"- Estimated effort: `{p.cost.estimated_effort}` ({p.cost.estimated_basis})")
    measured = (
        f"{p.cost.measured_minutes} min"
        if p.cost.measured_minutes is not None
        else "none yet — no approved run"
    )
    lines.append(f"- Measured: {measured}")
    lines.append(f"- Uncertainty: {entry.uncertainty}")
    lines.append("")
    lines.append("## Missing questions for the operator")
    lines.append("")
    for i, q in enumerate(entry.missing_questions, 1):
        lines.append(f"{i}. {q}")
    lines.append("")
    return "\n".join(lines)


def queue_report(entries: Sequence[QueueEntry]) -> str:
    """The ranked queue readout — improvements and new targets side by side."""
    ranked = rank_entries(entries)
    lines: list[str] = []
    lines.append("# Gap-driven acquisition queue — reviewed candidates")
    lines.append("")
    lines.append(
        f"Seeded from `{DEFAULT_INVENTORY}` ({len(entries)} candidates) under "
        f"`{QUEUE_SCHEMA}` / `{SCORING_VERSION}` / `{SEED_VERSION}`. This queue "
        "approves nothing: every row routes to operator review (HG-03 leg of "
        "D-R10-SOURCES-1), `ingestion_permitted` is untouched, and blocked/"
        "refused rows stay visible with reasons."
    )
    lines.append("")
    header = (
        "| rank | candidate | kind | relation | disposition | score "
        f"(`{SCORING_VERSION}`) | gates |"
    )
    lines.append(header)
    lines.append("|---|---|---|---|---|---|---|")
    for e in ranked:
        p = e.passport
        val = str(e.score_result.value) if e.score_result.value is not None else "unscored"
        gates = ", ".join(sorted(g.value for g in e.gates)) or "—"
        lines.append(
            f"| {p.rank} | `{p.candidate_id}` {p.family} | {e.kind} | "
            f"{e.join.relation.value} | {e.disposition.value} | {val} | {gates} |"
        )
    lines.append("")
    blocked = [e for e in ranked if e.disposition == QueueDisposition.BLOCKED]
    refused = [e for e in ranked if e.disposition == QueueDisposition.REFUSED_DUPLICATE]
    if blocked or refused:
        lines.append("## Blocked / refused (kept visible, never dropped)")
        lines.append("")
        for e in (*blocked, *refused):
            lines.append(
                f"- `{e.passport.candidate_id}` — {e.disposition.value}: "
                f"{', '.join(sorted(g.value for g in e.gates))}"
            )
        lines.append("")
    return "\n".join(lines)


def entries_as_json(entries: Sequence[QueueEntry]) -> list[dict[str, Any]]:
    """Machine-readable queue projection (the `queue --json` output)."""
    out: list[dict[str, Any]] = []
    for e in rank_entries(entries):
        p = e.passport
        out.append(
            {
                "candidate_id": p.candidate_id,
                "rank": p.rank,
                "family": p.family,
                "jurisdiction": p.jurisdiction,
                "authority": p.authority,
                "gap": p.gap,
                "content_window": p.content_window,
                "novelty": p.novelty,
                "priority": p.priority,
                "kind": e.kind,
                "relation": e.join.relation.value,
                "duplicate_of": e.join.duplicate_of,
                "linked_sources": [
                    {
                        "id": ls.source_id,
                        "kind": ls.link.kind.value,
                        "ingestion_permitted": ls.permitted,
                        "p31_owned": ls.p31_owned,
                        "dispositions": len(ls.dispositions),
                    }
                    for ls in e.join.linked
                ],
                "lineage_class": p.lineage_class.value,
                "lineage_group": p.lineage_group,
                "independent_yield": p.independent_yield,
                "rights": {lane.value: _fmt_decision(record) for lane, record in p.rights.lanes()},
                "municipal_publication_observed": p.rights.municipal_publication_observed,
                "preflight": {
                    "status": p.preflight.status.value,
                    "flags": list(p.preflight.flags),
                },
                "score": {
                    "scoring_version": e.score_result.scoring_version,
                    "assessment_version": e.score_result.assessment_version,
                    "value": e.score_result.value,
                    "contributions": e.score_result.contributions,
                    "unscored_dimensions": list(e.score_result.unscored_dimensions),
                },
                "gates": sorted(g.value for g in e.gates),
                "disposition": e.disposition.value,
                "admissible": e.admissible,
                "onboardable": e.onboardable,
                "cost": {
                    "estimated_effort": p.cost.estimated_effort,
                    "estimated_basis": p.cost.estimated_basis,
                    "measured_minutes": p.cost.measured_minutes,
                    "measured_basis": p.cost.measured_basis or None,
                },
                "uncertainty": e.uncertainty,
                "missing_questions": list(e.missing_questions),
            }
        )
    return out


__all__ = [
    "DIMENSIONS",
    "DIMENSION_WEIGHTS",
    "DISPOSITION_ARTIFACTS",
    "DEFAULT_INVENTORY",
    "AcquisitionQueueError",
    "CandidatePassport",
    "CostRecord",
    "DimensionAssessment",
    "DimensionDelta",
    "DiscoveryProvenance",
    "Gate",
    "LaneDecision",
    "LaneRecord",
    "LineageClass",
    "LinkKind",
    "LinkedSource",
    "NON_INDEPENDENT_LINEAGE",
    "P31_OWNED_SOURCES",
    "PART_VIII_EXCLUDED_CATEGORIES",
    "PartVIIIPreflight",
    "PreflightStatus",
    "QUEUE_SCHEMA",
    "QueueDisposition",
    "QueueEntry",
    "RegistryJoin",
    "RegistryLink",
    "RegistryLinkSpec",
    "RegistryRelation",
    "RightsAssessment",
    "RightsLane",
    "SCORING_VERSION",
    "SEED_VERSION",
    "ScoreResult",
    "build_queue",
    "check_queue",
    "diff_assessments",
    "disposition_for",
    "entries_as_json",
    "gates_for",
    "independent_corroboration",
    "join_candidate",
    "load_candidates",
    "load_research_rows",
    "missing_questions",
    "normalize_url",
    "queue_report",
    "rank_entries",
    "review_packet",
    "score",
    "uncertainty_for",
]

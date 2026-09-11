# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The five-tier contributor write model (§34.1, SIG-CONTRIB-001/002/006).

Who may write what, and under what review, is a fixed, testable vocabulary — not
free text and not a per-deployment setting. This module owns the five tiers
(§34.1), the per-tier **write scope** and **review requirement** they carry, and
the three load-bearing invariants the rest of the contributor system rests on:

* **No claim without provenance (SIG-CONTRIB-002).** No tier — not even a
  maintainer — may write a claim that carries no provenance;
  :func:`assert_has_provenance` is the choke point.
* **Submissions enter at L0, never L1 (SIG-CONTRIB-002).** A contribution is a
  *piece of evidence* (a photo, a document, a report), not a graph claim. The
  entry level is a constant (:data:`SUBMISSION_ENTRY_LEVEL`) that is L0 for every
  tier; the L0→L1 step is resolution's job, downstream and reviewed.
* **Pseudonymity at every tier (SIG-CONTRIB-006).** :func:`supports_pseudonymous`
  takes a tier and always returns ``True`` — including trusted-reviewer. A
  :class:`Contributor` is keyed by a pseudonymous `handle` and carries **no**
  real-name field, so the model cannot represent a legal-identity requirement.

The `Person`-creation gate (:func:`may_create_person`) encodes the §34.1 +
Notes rule that no tier below Curator may create a `Person`; the officer-naming
test and §11.3/§43.4 constraints enforce the substance of that decision upstream.

Scopes are **cumulative up the ladder**: a higher tier holds every lower tier's
scope plus its own additions, which is the natural trust model — a maintainer can
do anything a curator can. Each tier's *added* scopes are declared once
(:data:`_ADDED_SCOPES`); the cumulative set is derived, never hand-listed twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "ContributorTier",
    "WriteScope",
    "ReviewRequirement",
    "EvidenceLevel",
    "Contributor",
    "MissingProvenanceError",
    "SUBMISSION_ENTRY_LEVEL",
    "TIER_ORDER",
    "scopes_for",
    "may_write",
    "review_requirement",
    "may_create_person",
    "supports_pseudonymous",
    "entry_level_for_submission",
    "assert_has_provenance",
]


class ContributorTier(StrEnum):
    """The five write tiers, in ascending order of trust (§34.1, SIG-CONTRIB-001).

    Exactly the five the spec table enumerates — no more, no fewer.
    """

    ANONYMOUS = "anonymous"
    REGISTERED = "registered"
    TRUSTED_REVIEWER = "trusted_reviewer"
    CURATOR = "curator"
    MAINTAINER = "maintainer"


class WriteScope(StrEnum):
    """The distinct things a tier may write (§34.1, the "May write" column)."""

    #: Anonymous — submissions to a review queue (never a direct landing).
    QUEUE_SUBMISSION = "queue_submission"
    #: Registered — claims at reliability R5 (the lowest non-provisional band).
    CLAIM_R5 = "claim_r5"
    #: Registered — task dispositions on the research queue.
    TASK_DISPOSITION = "task_disposition"
    #: Trusted reviewer — verify other contributors' submissions.
    VERIFY_SUBMISSIONS = "verify_submissions"
    #: Trusted reviewer — promote candidates for higher trust.
    PROMOTE_CANDIDATES = "promote_candidates"
    #: Curator — human assertions into the graph.
    HUMAN_ASSERTION = "human_assertion"
    #: Curator — resolution overrides (a decided_by != 'auto' resolution).
    RESOLUTION_OVERRIDE = "resolution_override"
    #: Curator — sensitivity classification of a subject.
    SENSITIVITY_CLASSIFICATION = "sensitivity_classification"
    #: Curator — `Person` creation (gated below this tier; §11.3/§43.4).
    PERSON_CREATION = "person_creation"
    #: Maintainer — the resolution ruleset.
    RULESET = "ruleset"
    #: Maintainer — the controlled vocabulary.
    VOCABULARY = "vocabulary"
    #: Maintainer — the schema.
    SCHEMA = "schema"


class ReviewRequirement(StrEnum):
    """The review a tier's writes are subject to (§34.1, the "Review" column)."""

    ALL_BEFORE_LANDING = "all_reviewed_before_landing"
    SAMPLED_REVIEW = "sampled_review"
    SAMPLED_AUDIT = "sampled_audit"
    PEER_REVIEW = "peer_review"
    ADR_AND_REVIEW = "adr_and_review"


class EvidenceLevel(StrEnum):
    """The epistemic level a datum enters at (§10, §34.1).

    ``L0_EVIDENCE`` is a raw artifact (a photo, a document, a report); ``L1_CLAIM``
    is a subject·predicate·object assertion in the graph. Contributions enter at
    L0 and are promoted to L1 only by reviewed resolution — never directly
    (SIG-CONTRIB-002).
    """

    L0_EVIDENCE = "L0"
    L1_CLAIM = "L1"


#: A contribution's entry level is L0 for every tier, always (SIG-CONTRIB-002).
SUBMISSION_ENTRY_LEVEL: EvidenceLevel = EvidenceLevel.L0_EVIDENCE

#: The tiers in ascending trust order — the ladder scopes accumulate along.
TIER_ORDER: tuple[ContributorTier, ...] = (
    ContributorTier.ANONYMOUS,
    ContributorTier.REGISTERED,
    ContributorTier.TRUSTED_REVIEWER,
    ContributorTier.CURATOR,
    ContributorTier.MAINTAINER,
)

# The scopes each tier *adds* over the tier below it (§34.1). The cumulative
# scope of a tier is its own additions unioned with every lower tier's.
_ADDED_SCOPES: dict[ContributorTier, frozenset[WriteScope]] = {
    ContributorTier.ANONYMOUS: frozenset({WriteScope.QUEUE_SUBMISSION}),
    ContributorTier.REGISTERED: frozenset({WriteScope.CLAIM_R5, WriteScope.TASK_DISPOSITION}),
    ContributorTier.TRUSTED_REVIEWER: frozenset(
        {WriteScope.VERIFY_SUBMISSIONS, WriteScope.PROMOTE_CANDIDATES}
    ),
    ContributorTier.CURATOR: frozenset(
        {
            WriteScope.HUMAN_ASSERTION,
            WriteScope.RESOLUTION_OVERRIDE,
            WriteScope.SENSITIVITY_CLASSIFICATION,
            WriteScope.PERSON_CREATION,
        }
    ),
    ContributorTier.MAINTAINER: frozenset(
        {WriteScope.RULESET, WriteScope.VOCABULARY, WriteScope.SCHEMA}
    ),
}

# The review requirement each tier's writes are subject to (§34.1).
_REVIEW: dict[ContributorTier, ReviewRequirement] = {
    ContributorTier.ANONYMOUS: ReviewRequirement.ALL_BEFORE_LANDING,
    ContributorTier.REGISTERED: ReviewRequirement.SAMPLED_REVIEW,
    ContributorTier.TRUSTED_REVIEWER: ReviewRequirement.SAMPLED_AUDIT,
    ContributorTier.CURATOR: ReviewRequirement.PEER_REVIEW,
    ContributorTier.MAINTAINER: ReviewRequirement.ADR_AND_REVIEW,
}


class MissingProvenanceError(ValueError):
    """Raised when a claim is written without provenance (SIG-CONTRIB-002)."""


@dataclass(frozen=True)
class Contributor:
    """A contributor, keyed by a pseudonymous handle (§34.1, SIG-CONTRIB-006).

    There is deliberately **no real-name field**: the model cannot represent a
    legal-identity requirement, so pseudonymity holds structurally at every tier.
    Reputation attaches to the `handle`, not to a person.
    """

    handle: str
    tier: ContributorTier

    def __post_init__(self) -> None:
        if not self.handle:
            raise ValueError("a Contributor MUST carry a (pseudonymous) handle")


def scopes_for(tier: ContributorTier) -> frozenset[WriteScope]:
    """The cumulative write scope of `tier` — its additions plus every lower tier's."""
    scopes: set[WriteScope] = set()
    for rung in TIER_ORDER:
        scopes |= _ADDED_SCOPES[rung]
        if rung is tier:
            break
    return frozenset(scopes)


def may_write(tier: ContributorTier, scope: WriteScope) -> bool:
    """Whether `tier` may write `scope` (§34.1, SIG-CONTRIB-001)."""
    return scope in scopes_for(tier)


def review_requirement(tier: ContributorTier) -> ReviewRequirement:
    """The review `tier`'s writes are subject to (§34.1, SIG-CONTRIB-001)."""
    return _REVIEW[tier]


def may_create_person(tier: ContributorTier) -> bool:
    """Whether `tier` may create a `Person` — Curator and above only (§34.1 Notes).

    No contributor tier below Curator may create a `Person`; the substance of that
    decision (the officer-naming test, §11.3/§43.4) is enforced upstream.
    """
    return WriteScope.PERSON_CREATION in scopes_for(tier)


def supports_pseudonymous(tier: ContributorTier) -> bool:
    """Whether pseudonymous contribution is supported at `tier` (SIG-CONTRIB-006).

    Always ``True``, for every tier including trusted-reviewer. This takes a tier
    only to make the invariant explicit at each call site — there is no tier for
    which it returns ``False``, which is precisely the guarantee.
    """
    return tier in TIER_ORDER


def entry_level_for_submission() -> EvidenceLevel:
    """The level a contributor submission enters at — L0, always (SIG-CONTRIB-002)."""
    return SUBMISSION_ENTRY_LEVEL


def assert_has_provenance(provenance: object) -> None:
    """Refuse a claim with no provenance, for any tier (SIG-CONTRIB-002).

    Empty provenance — ``None``, an empty string, or an empty collection — is a
    write of a claim without a source, which no tier may do.
    """
    if provenance is None or (hasattr(provenance, "__len__") and len(provenance) == 0):  # type: ignore[arg-type]
        raise MissingProvenanceError(
            "no tier may write a claim without provenance (SIG-CONTRIB-002)"
        )

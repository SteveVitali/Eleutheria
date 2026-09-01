# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Published denominators and per-jurisdiction coverage (§32.2, §32.3).

"37 agencies share data outside their state" is non-conformant. "37 of 214
evaluable agencies; 1,109 not evaluable for lack of evidence" is conformant
(SIG-METRIC-003). Every published aggregate MUST carry its denominator *and* the
count excluded for lack of evidence; a bare count must not be publishable at all.

This module makes that structural: :class:`PublishedAggregate` is the only shape a
number ships in, and :func:`assert_denominated` refuses a bare ``int`` — so "a bare
count fails the build" is a type error a test can assert, not a review-time hope.
On top of it, :func:`jurisdiction_coverage` computes the §32.4 per-jurisdiction
surface (SIG-METRIC-004) and :func:`provenance_completeness` measures the share of
published claims with resolvable evidence, targeted at 100% (SIG-METRIC-005).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field

__all__ = [
    "PublishedAggregate",
    "assert_denominated",
    "AgencyCoverageInput",
    "JurisdictionCoverage",
    "jurisdiction_coverage",
    "ProvenanceCompleteness",
    "provenance_completeness",
]


@dataclass(frozen=True)
class PublishedAggregate:
    """A count that carries its denominator and its not-evaluable count (§32.2).

    `count` is the numerator (subjects satisfying the predicate), `denominator` the
    evaluable population, `not_evaluable` those excluded for lack of evidence. The
    three are validated so a published number can never imply a denominator of
    reality (SIG-METRIC-010): `count <= denominator`, and all are non-negative.
    """

    label: str
    count: int
    denominator: int
    not_evaluable: int = 0

    def __post_init__(self) -> None:
        if self.count < 0 or self.denominator < 0 or self.not_evaluable < 0:
            raise ValueError(f"aggregate {self.label!r} has a negative component")
        if self.count > self.denominator:
            raise ValueError(
                f"aggregate {self.label!r}: count {self.count} exceeds evaluable "
                f"denominator {self.denominator} — a numerator cannot beat its "
                "denominator (§32.2)"
            )

    @property
    def evaluable(self) -> int:
        """Alias for the denominator — the evaluable population."""
        return self.denominator

    def phrase(self) -> str:
        """The conformant §32.2 phrasing, denominator and not-evaluable inline."""
        base = f"{self.count} of {self.denominator} evaluable {self.label}"
        if self.not_evaluable:
            return f"{base}; {self.not_evaluable} not evaluable for lack of evidence"
        return base

    def as_json(self) -> dict[str, object]:
        return {
            "label": self.label,
            "count": self.count,
            "denominator": self.denominator,
            "not_evaluable": self.not_evaluable,
            "phrase": self.phrase(),
        }


def assert_denominated(value: object) -> PublishedAggregate:
    """Refuse to publish a bare count (SIG-METRIC-003).

    Returns `value` unchanged if it is a :class:`PublishedAggregate`; otherwise
    raises. This is the choke point every published aggregate routes through, so a
    raw ``int`` (or anything without a denominator) fails the build rather than
    shipping as "37 agencies share data" with no evaluable population behind it.
    """
    if not isinstance(value, PublishedAggregate):
        raise TypeError(
            f"a published aggregate MUST be a PublishedAggregate carrying its "
            f"denominator (§32.2), not a bare {type(value).__name__}: {value!r}"
        )
    return value


@dataclass(frozen=True)
class AgencyCoverageInput:
    """One agency's evidence flags, the input to per-jurisdiction coverage (§32.4).

    `evidence_age_days` is `None` when the agency has no dated evidence — it is then
    excluded from the mean rather than counted as age zero (a silent zero is how
    coverage becomes a lie, §32). `weight_class` is the §10.6 class of the agency's
    best claim, or `None` if it has no claims yet.
    """

    agency_id: str
    has_deployment_evidence: bool = False
    has_contract_evidence: bool = False
    has_portal_evidence: bool = False
    has_mapped_devices: bool = False
    evidence_age_days: int | None = None
    open_contradictions: int = 0
    weight_class: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_age_days is not None and self.evidence_age_days < 0:
            raise ValueError(f"agency {self.agency_id!r}: evidence_age_days cannot be negative")
        if self.open_contradictions < 0:
            raise ValueError(f"agency {self.agency_id!r}: open_contradictions cannot be negative")


@dataclass(frozen=True)
class JurisdictionCoverage:
    """The computed, publishable per-jurisdiction coverage surface (SIG-METRIC-004)."""

    jurisdiction_id: str
    agencies_known: int
    with_deployment_evidence: PublishedAggregate
    with_contract_evidence: PublishedAggregate
    with_portal_evidence: PublishedAggregate
    with_mapped_devices: PublishedAggregate
    mean_evidence_age_days: float | None
    open_contradiction_count: int
    weight_class_distribution: Mapping[str, int]

    def as_json(self) -> dict[str, object]:
        return {
            "jurisdiction_id": self.jurisdiction_id,
            "agencies_known": self.agencies_known,
            "with_deployment_evidence": self.with_deployment_evidence.as_json(),
            "with_contract_evidence": self.with_contract_evidence.as_json(),
            "with_portal_evidence": self.with_portal_evidence.as_json(),
            "with_mapped_devices": self.with_mapped_devices.as_json(),
            "mean_evidence_age_days": self.mean_evidence_age_days,
            "open_contradiction_count": self.open_contradiction_count,
            "weight_class_distribution": dict(self.weight_class_distribution),
        }


def jurisdiction_coverage(
    jurisdiction_id: str,
    agencies: Iterable[AgencyCoverageInput],
) -> JurisdictionCoverage:
    """Compute the §32.4 per-jurisdiction coverage from the known agencies.

    Every derived count is a :class:`PublishedAggregate` denominated by the number of
    agencies known (SIG-METRIC-003/004). The mean evidence age is over agencies with
    dated evidence only; it is `None` when none have any (never a silent zero).
    """
    known = list(agencies)
    ids = [a.agency_id for a in known]
    if len(ids) != len(set(ids)):
        raise ValueError(f"duplicate agency id in jurisdiction {jurisdiction_id!r} coverage")
    n = len(known)

    def _agg(label: str, predicate: str) -> PublishedAggregate:
        satisfied = sum(1 for a in known if getattr(a, predicate))
        # Every known agency is evaluable for "has any X evidence"; none are excluded
        # for lack of evidence here (absence of evidence is itself the negative answer).
        return PublishedAggregate(label=label, count=satisfied, denominator=n)

    ages = [a.evidence_age_days for a in known if a.evidence_age_days is not None]
    mean_age = sum(ages) / len(ages) if ages else None

    distribution: dict[str, int] = {}
    for a in known:
        if a.weight_class is not None:
            distribution[a.weight_class] = distribution.get(a.weight_class, 0) + 1

    return JurisdictionCoverage(
        jurisdiction_id=jurisdiction_id,
        agencies_known=n,
        with_deployment_evidence=_agg(
            "agencies with deployment evidence", "has_deployment_evidence"
        ),
        with_contract_evidence=_agg("agencies with contract evidence", "has_contract_evidence"),
        with_portal_evidence=_agg("agencies with portal evidence", "has_portal_evidence"),
        with_mapped_devices=_agg("agencies with mapped devices", "has_mapped_devices"),
        mean_evidence_age_days=mean_age,
        open_contradiction_count=sum(a.open_contradictions for a in known),
        weight_class_distribution=distribution,
    )


@dataclass(frozen=True)
class ProvenanceCompleteness:
    """Share of published claims with a resolvable evidence artifact (§32.3).

    Targeted at 100%. Any shortfall is **a defect list, not a statistic**
    (SIG-METRIC-005): `defects` names the claim ids that lack resolvable evidence,
    so the shortfall is actionable rather than a number to admire.
    """

    published_claims: int
    with_resolvable_evidence: int
    defects: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.with_resolvable_evidence > self.published_claims:
            raise ValueError("more resolvable than published claims (§32.3)")
        expected_missing = self.published_claims - self.with_resolvable_evidence
        if len(self.defects) != expected_missing:
            raise ValueError(
                f"provenance shortfall is a defect list (SIG-METRIC-005): "
                f"{expected_missing} claims lack resolvable evidence but "
                f"{len(self.defects)} are named"
            )

    @property
    def share(self) -> float:
        """Fraction with resolvable evidence in [0, 1]; 1.0 when there are none."""
        if self.published_claims == 0:
            return 1.0
        return self.with_resolvable_evidence / self.published_claims

    @property
    def is_complete(self) -> bool:
        """Whether the 100% target is met (SIG-METRIC-005)."""
        return not self.defects

    def as_json(self) -> dict[str, object]:
        return {
            "published_claims": self.published_claims,
            "with_resolvable_evidence": self.with_resolvable_evidence,
            "share": self.share,
            "target": 1.0,
            "is_complete": self.is_complete,
            "defects": list(self.defects),
        }


def provenance_completeness(
    claim_ids: Sequence[str],
    *,
    claims_with_resolvable_evidence: Iterable[str],
) -> ProvenanceCompleteness:
    """Measure provenance completeness over published claims (SIG-METRIC-005).

    The shortfall is materialized as the list of claim ids lacking resolvable
    evidence, so it is a defect list to close, not a statistic to publish.
    """
    published = list(dict.fromkeys(claim_ids))
    resolvable = set(claims_with_resolvable_evidence)
    defects = tuple(cid for cid in published if cid not in resolvable)
    return ProvenanceCompleteness(
        published_claims=len(published),
        with_resolvable_evidence=len(published) - len(defects),
        defects=defects,
    )

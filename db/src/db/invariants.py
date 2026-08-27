# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The eight temporal invariants TI-1..TI-8 as run-failing data-quality checks (§9.6).

SIG-TIME-013 requires these be enforced as database constraints **or** as pipeline
data-quality checks that fail the run — never as application-level conventions.
Some are already physical constraints from P02.1 (a `tstzrange` structurally
guarantees `lower <= upper`, discharging TI-1/TI-2 for the range columns; the
`resolution_no_overlap` GiST EXCLUDE covers same-predicate L3 overlap; the
`claim_observed_not_future` CHECK covers TI-5). This module is the *pipeline*
half (SIG-ENG-017): pure, deterministic checks a connector runs over the claims
and resolutions it is about to assert, failing the run before bad data lands. The
same functions are what the TI-1..TI-8 property tests (SIG-TIME-014) exercise.

TI-3 and TI-4 compare cross-layer timestamps that may be time-zone-free source
dates, so they allow a **configurable tolerance** for clock skew.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta

# Default skew tolerance for the cross-layer ordering invariants (TI-3, TI-4).
DEFAULT_SKEW_TOLERANCE = timedelta(days=1)


class TemporalInvariantViolation(ValueError):
    """A temporal invariant TI-N was violated (a data-quality failure)."""


@dataclass(frozen=True)
class Violation:
    """One invariant breach, carrying the invariant id and a human reason."""

    invariant: str  # e.g. "TI-1"
    subject: str  # the claim_id / resolution_id / chain the breach is about
    reason: str


@dataclass(frozen=True)
class ClaimTiming:
    """The temporal fields of a claim TI-1..TI-8 reason about.

    A thin projection of the `claim` row (plus its evidence's publication time),
    so the checks are pure and unit-testable without a live database.
    """

    claim_id: str
    recorded_at: datetime  # lower(sys_period), T5
    superseded_at: datetime | None = None  # upper(sys_period), T5 close
    valid_from: datetime | None = None  # lower(valid_period), T1
    valid_to: datetime | None = None  # upper(valid_period), T1
    valid_from_kind: str = "unknown"
    valid_to_kind: str = "unknown"
    observed_at: datetime | None = None  # T2
    published_at: datetime | None = None  # T3, from the evidence artifact
    supersedes_claim_id: str | None = None  # revises_claim
    temporally_unanchored: bool = False
    temporally_unanchored_reason: str | None = None


@dataclass(frozen=True)
class ResolvedInterval:
    """An L3 resolution's validity interval, for the TI-6 overlap check."""

    resolution_id: str
    subject_id: str
    predicate_id: str
    valid_from: datetime | None
    valid_to: datetime | None


def check_ti1(c: ClaimTiming) -> Violation | None:
    """TI-1: `valid_from <= valid_to` when both bounds are `exact`."""
    if (
        c.valid_from_kind == "exact"
        and c.valid_to_kind == "exact"
        and c.valid_from is not None
        and c.valid_to is not None
        and c.valid_from > c.valid_to
    ):
        return Violation("TI-1", c.claim_id, f"valid_from {c.valid_from} > valid_to {c.valid_to}")
    return None


def check_ti2(c: ClaimTiming) -> Violation | None:
    """TI-2: `recorded_at <= superseded_at` when superseded."""
    if c.superseded_at is not None and c.recorded_at > c.superseded_at:
        return Violation(
            "TI-2", c.claim_id, f"recorded_at {c.recorded_at} > superseded_at {c.superseded_at}"
        )
    return None


def check_ti3(c: ClaimTiming, *, tolerance: timedelta = DEFAULT_SKEW_TOLERANCE) -> Violation | None:
    """TI-3: `observed_at <= published_at` when both known (± tolerance)."""
    if (
        c.observed_at is not None
        and c.published_at is not None
        and c.observed_at - c.published_at > tolerance
    ):
        return Violation(
            "TI-3", c.claim_id, f"observed_at {c.observed_at} > published_at {c.published_at}"
        )
    return None


def check_ti4(
    published_at: datetime | None,
    retrieved_at: datetime | None,
    *,
    subject: str = "capture",
    tolerance: timedelta = DEFAULT_SKEW_TOLERANCE,
) -> Violation | None:
    """TI-4: `published_at <= retrieved_at` when both known (± tolerance)."""
    if (
        published_at is not None
        and retrieved_at is not None
        and published_at - retrieved_at > tolerance
    ):
        return Violation(
            "TI-4", subject, f"published_at {published_at} > retrieved_at {retrieved_at}"
        )
    return None


def check_ti5(c: ClaimTiming) -> Violation | None:
    """TI-5: `observed_at` MUST NOT be in the future relative to `recorded_at`."""
    if c.observed_at is not None and c.observed_at > c.recorded_at:
        return Violation(
            "TI-5", c.claim_id, f"observed_at {c.observed_at} is after recorded_at {c.recorded_at}"
        )
    return None


def _overlaps(a: ResolvedInterval, b: ResolvedInterval) -> bool:
    # Half-open [from, to); None = unbounded. Two intervals overlap iff
    # a.from < b.to and b.from < a.to.
    a_lo, a_hi = a.valid_from, a.valid_to
    b_lo, b_hi = b.valid_from, b.valid_to
    left = a_lo is None or b_hi is None or a_lo < b_hi
    right = b_lo is None or a_hi is None or b_lo < a_hi
    return left and right


def check_ti6(
    resolutions: Iterable[ResolvedInterval], mutually_exclusive_predicates: Sequence[str]
) -> list[Violation]:
    """TI-6: resolved L3 intervals for mutually-exclusive predicates on one
    subject MUST NOT overlap. (L1 overlap is a contradiction, not an error.)"""
    exclusive = set(mutually_exclusive_predicates)
    by_subject: dict[str, list[ResolvedInterval]] = {}
    for r in resolutions:
        if r.predicate_id in exclusive:
            by_subject.setdefault(r.subject_id, []).append(r)
    violations: list[Violation] = []
    for subject_id, rows in by_subject.items():
        for i in range(len(rows)):
            for j in range(i + 1, len(rows)):
                if _overlaps(rows[i], rows[j]):
                    violations.append(
                        Violation(
                            "TI-6",
                            subject_id,
                            f"resolved intervals {rows[i].resolution_id} and "
                            f"{rows[j].resolution_id} overlap for mutually-exclusive predicates",
                        )
                    )
    return violations


def check_ti7(claims: Iterable[ClaimTiming]) -> list[Violation]:
    """TI-7: the `supersedes` chain MUST be acyclic and MUST terminate."""
    edges: dict[str, str] = {
        c.claim_id: c.supersedes_claim_id for c in claims if c.supersedes_claim_id is not None
    }
    violations: list[Violation] = []
    for start in edges:
        seen: set[str] = set()
        node: str | None = start
        while node is not None and node in edges:
            if node in seen:
                violations.append(
                    Violation("TI-7", start, f"supersedes chain from {start} cycles at {node}")
                )
                break
            seen.add(node)
            node = edges.get(node)
    return violations


def check_ti8(c: ClaimTiming) -> Violation | None:
    """TI-8: a claim MUST have `observed_at`, `published_at`, or an explicit
    `temporally_unanchored` flag with a reason. None of these = data-quality
    failure (a claim floating free of all time)."""
    if c.observed_at is not None or c.published_at is not None:
        return None
    if c.temporally_unanchored and c.temporally_unanchored_reason:
        return None
    return Violation(
        "TI-8",
        c.claim_id,
        "claim has no observed_at, no published_at, and no reasoned temporally_unanchored flag",
    )


@dataclass
class InvariantReport:
    """The result of a full temporal data-quality pass."""

    violations: list[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def raise_if_failed(self) -> None:
        """Fail the run if any invariant was violated (SIG-TIME-013)."""
        if self.violations:
            lines = "\n".join(f"  {v.invariant} [{v.subject}]: {v.reason}" for v in self.violations)
            raise TemporalInvariantViolation(
                f"{len(self.violations)} temporal invariant violation(s):\n{lines}"
            )


def check_all(
    claims: Iterable[ClaimTiming],
    *,
    resolutions: Iterable[ResolvedInterval] | None = None,
    mutually_exclusive_predicates: Sequence[str] = (),
    captures: Iterable[Mapping[str, datetime | None]] | None = None,
    tolerance: timedelta = DEFAULT_SKEW_TOLERANCE,
) -> InvariantReport:
    """Run every applicable invariant over a batch; collect all violations.

    This is the pipeline data-quality gate (SIG-ENG-017): a connector calls it on
    the claims/resolutions it is about to assert and `raise_if_failed()` before the
    write. Per-row checks (TI-1..TI-3, TI-5, TI-8) run over `claims`; TI-4 over
    `captures`; graph checks (TI-6, TI-7) over the batch.
    """
    claims = list(claims)
    report = InvariantReport()
    per_row = (check_ti1, check_ti2, check_ti3, check_ti5, check_ti8)
    for c in claims:
        for check in per_row:
            result = check(c, tolerance=tolerance) if check is check_ti3 else check(c)
            if result is not None:
                report.violations.append(result)
    for cap in captures or ():
        result = check_ti4(cap.get("published_at"), cap.get("retrieved_at"), tolerance=tolerance)
        if result is not None:
            report.violations.append(result)
    report.violations.extend(check_ti7(claims))
    if resolutions is not None and mutually_exclusive_predicates:
        report.violations.extend(check_ti6(resolutions, mutually_exclusive_predicates))
    return report

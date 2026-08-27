# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Corrections, suppression, and deletion as executable primitives (§45).

The prose takedown/corrections policy lives in ``docs/governance/``; this module
makes its two **load-bearing, deterministic** distinctions real and testable,
ahead of the claim spine (P02.1) that will enforce them in Postgres:

* **Corrections preserve history (SIG-GOV-005, mirrors §16.6).** A correction is
  a *new assertion* that supersedes the old one — never a deletion or overwrite.
  A query at a prior ``as_of_belief`` still returns the value SIG believed then,
  so a citation made before the correction remains reproducible.
* **Suppression is a primitive distinct from deletion (SIG-GOV-007/008).**
  Suppression removes material from public surfaces and exports while retaining
  it internally under the ``sealed`` tier, with author and rationale recorded.
  True deletion is reserved for material SIG must not hold at all: it requires
  two-person authorization and leaves a tombstone (category and date, never
  content).

:class:`BeliefLog` is an append-only, in-memory model of these rules — the same
shape the claim table will take (append-only, ``revises_claim``, no writable
"current value" column). The intake categories, SLAs, permitted outcomes, and
transparency-report shape are read from ``data/takedown.toml`` (data, not code).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from ._data import load_table

# The sensitivity tier suppressed material is retained under internally (§45.4,
# SIG-EVID-006 governance-mode Object Lock). Public surfaces never read it.
SEALED_TIER = "sealed"


class GovernanceError(Exception):
    """Base class for governance-primitive violations (§45)."""


class DeletionAuthorizationError(GovernanceError):
    """Raised when true deletion lacks two distinct authorizers (SIG-GOV-008)."""


@dataclass(frozen=True)
class Assertion:
    """One append-only belief about a subject's value over a system-time interval.

    ``belief_from`` / ``belief_to`` bound *when SIG held this belief* (system
    time), not when the fact was true in the world. ``belief_to is None`` means
    the belief is still current. A correction closes the prior assertion's
    interval and appends a new one with :attr:`revises` set — the old row is
    never mutated in place beyond stamping its ``belief_to``.
    """

    subject: str
    value: str
    belief_from: datetime
    belief_to: datetime | None = None
    revises: int | None = None
    correction_reason: str | None = None
    suppressed: bool = False
    suppression_author: str | None = None
    suppression_rationale: str | None = None
    tier: str | None = None


@dataclass(frozen=True)
class Tombstone:
    """The residue of a true deletion: category and date, never content (SIG-GOV-008)."""

    subject: str
    category: str
    date: datetime
    authorizers: tuple[str, str]


@dataclass
class BeliefLog:
    """An append-only log of :class:`Assertion` rows with as-of-belief queries.

    Deliberately mirrors the append-only claim table: there is no writable
    "current value" — the current belief is derived by reading the open interval.
    """

    _assertions: list[Assertion] = field(default_factory=list)
    _tombstones: list[Tombstone] = field(default_factory=list)

    # -- writes -------------------------------------------------------------
    def assert_value(self, subject: str, value: str, *, at: datetime) -> int:
        """Append a fresh belief about ``subject``. Returns the assertion id (index)."""
        self._assertions.append(Assertion(subject=subject, value=value, belief_from=at))
        return len(self._assertions) - 1

    def correct(self, subject: str, new_value: str, *, reason: str, at: datetime) -> int:
        """Correct ``subject`` (SIG-GOV-005): close the open belief, append a new one.

        Never deletes or overwrites the prior value. The new assertion carries
        ``revises`` pointing at the corrected one and a ``correction_reason``.
        """
        prior_id = self._open_id(subject)
        if prior_id is None:
            raise GovernanceError(f"no open belief about {subject!r} to correct")
        prior = self._assertions[prior_id]
        self._assertions[prior_id] = replace(prior, belief_to=at)
        self._assertions.append(
            Assertion(
                subject=subject,
                value=new_value,
                belief_from=at,
                revises=prior_id,
                correction_reason=reason,
            )
        )
        return len(self._assertions) - 1

    def suppress(self, subject: str, *, author: str, rationale: str) -> None:
        """Suppress ``subject`` from public surfaces (SIG-GOV-007), retaining it internally.

        A flag, not a delete: the value is retained under the ``sealed`` tier with
        the decision's author and rationale recorded. Distinct from :meth:`delete`.
        """
        if not author or not rationale:
            raise GovernanceError("suppression MUST record an author and a rationale (SIG-GOV-007)")
        open_id = self._open_id(subject)
        if open_id is None:
            raise GovernanceError(f"no open belief about {subject!r} to suppress")
        self._assertions[open_id] = replace(
            self._assertions[open_id],
            suppressed=True,
            suppression_author=author,
            suppression_rationale=rationale,
            tier=SEALED_TIER,
        )

    def delete(
        self, subject: str, *, category: str, authorizers: tuple[str, str], at: datetime
    ) -> None:
        """True deletion (SIG-GOV-008): reserved, two-person-authorized, leaves a tombstone.

        Requires two *distinct* authorizers. Removes the content and records a
        tombstone (category + date, never content). Unlike suppression, the value
        does not survive internally.
        """
        if len({a for a in authorizers if a}) < 2:
            raise DeletionAuthorizationError(
                "true deletion requires two distinct authorizers (SIG-GOV-008)"
            )
        self._assertions = [a for a in self._assertions if a.subject != subject]
        self._tombstones.append(
            Tombstone(subject=subject, category=category, date=at, authorizers=authorizers)
        )

    # -- reads --------------------------------------------------------------
    def value_as_of_belief(self, subject: str, as_of: datetime) -> str | None:
        """The value SIG believed about ``subject`` at system time ``as_of`` (SIG-GOV-005).

        Includes suppressed values: suppression hides from the *public*, not from
        the internal reproducible record.
        """
        for a in self._assertions:
            if a.subject != subject:
                continue
            if a.belief_from <= as_of and (a.belief_to is None or as_of < a.belief_to):
                return a.value
        return None

    def public_value_as_of_belief(self, subject: str, as_of: datetime) -> str | None:
        """As :meth:`value_as_of_belief`, but suppressed material is withheld (SIG-GOV-007)."""
        for a in self._assertions:
            if a.subject != subject:
                continue
            if a.belief_from <= as_of and (a.belief_to is None or as_of < a.belief_to):
                return None if a.suppressed else a.value
        return None

    def tombstone_for(self, subject: str) -> Tombstone | None:
        """The tombstone left by a true deletion of ``subject``, if any (SIG-GOV-008)."""
        for t in self._tombstones:
            if t.subject == subject:
                return t
        return None

    def _open_id(self, subject: str) -> int | None:
        for i, a in enumerate(self._assertions):
            if a.subject == subject and a.belief_to is None:
                return i
        return None


# -- policy tables (data, not code) -----------------------------------------
def intake_categories() -> list[dict[str, Any]]:
    """The intake categories with their SLAs, priority-ordered (SIG-GOV-001/003)."""
    cats = load_table("takedown")["intake"]["categories"]
    return sorted(cats, key=lambda c: (c["priority"], c["id"]))


def identity_required_for(category_id: str) -> bool:
    """Whether intake requires identifying the submitter for ``category_id`` (SIG-GOV-002)."""
    intake = load_table("takedown")["intake"]
    return category_id in set(intake["identity_required_for"])


def permitted_outcomes() -> list[dict[str, Any]]:
    """The permitted handling outcomes, including ``refuse`` (SIG-GOV-004)."""
    return list(load_table("takedown")["outcomes"])


def transparency_report_shape() -> dict[str, Any]:
    """The transparency-report grouping/period, refusals included (SIG-GOV-011)."""
    return dict(load_table("takedown")["transparency_report"])

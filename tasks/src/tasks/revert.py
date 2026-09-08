# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Revert a contribution as a unit — a new assertion, never a deletion
(§34.4, SIG-CONTRIB-009; the mechanism of §16.6).

Every contribution MUST be revertible **as a unit**, and the revert MUST be
recorded as a *new assertion* (never a deletion). This mirrors the claim spine
(P02.1): reverting closes each affected claim's system-time interval and appends
a new claim with ``retraction_of`` set — the original rows are preserved, so a
citation made before the revert stays reproducible at its ``as_of_belief``. The
claim table already carries the ``retraction_of`` self-reference for exactly this
(see ``db/deploy/claim.sql``); ``tests/db/test_reverts.py`` proves the append-only
revert over the real Postgres schema.

:class:`ContributionLedger` is an in-memory, append-only model of that rule — the
same shape as :class:`policy.governance.BeliefLog`, extended with the
*contribution* grouping a revert operates over. It has **no delete path**: the
only way to withdraw a contribution is to append retraction assertions, which is
the guarantee. A revert is atomic over the contribution's open assertions: either
every one gets a retraction, or (if none are open) the revert is refused.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime

__all__ = [
    "ContributionAssertion",
    "ContributionLedger",
    "NothingToRevertError",
]


class NothingToRevertError(ValueError):
    """Raised when a revert names a contribution with no open assertions (SIG-CONTRIB-009)."""


@dataclass(frozen=True)
class ContributionAssertion:
    """One append-only assertion produced by, or retracting, a contribution.

    ``belief_to is None`` means SIG still holds this belief. A retraction is itself
    an assertion: it carries ``retraction_of`` pointing at the assertion it
    withdraws and a ``revert_reason`` — it never mutates or removes the original,
    which mirrors ``claim.retraction_of`` on the append-only spine.
    """

    assertion_id: int
    contribution_id: str
    subject: str
    value: str | None
    belief_from: datetime
    belief_to: datetime | None = None
    retraction_of: int | None = None
    revert_reason: str | None = None

    @property
    def is_retraction(self) -> bool:
        """Whether this assertion retracts another (SIG-CONTRIB-009)."""
        return self.retraction_of is not None


@dataclass
class ContributionLedger:
    """An append-only ledger of contribution assertions with unit revert.

    Deliberately mirrors the append-only claim table: no writable "current value",
    and **no delete** — the current belief is derived from the open assertions,
    and withdrawal happens by appending retractions.
    """

    _assertions: list[ContributionAssertion] = field(default_factory=list)

    def assert_value(self, contribution_id: str, subject: str, value: str, *, at: datetime) -> int:
        """Append an open assertion produced by `contribution_id`. Returns its id."""
        assertion_id = len(self._assertions)
        self._assertions.append(
            ContributionAssertion(
                assertion_id=assertion_id,
                contribution_id=contribution_id,
                subject=subject,
                value=value,
                belief_from=at,
            )
        )
        return assertion_id

    def revert_contribution(self, contribution_id: str, *, reason: str, at: datetime) -> list[int]:
        """Revert every open assertion of `contribution_id` as one unit (SIG-CONTRIB-009).

        For each still-open assertion belonging to the contribution: close its
        belief interval (stamping ``belief_to``, the only permitted in-place
        change, exactly as the claim spine closes ``sys_period``) and append a new
        retraction assertion pointing back at it. Nothing is deleted. Returns the
        ids of the appended retraction assertions. Refuses a contribution with no
        open assertions (``NothingToRevertError``) so a revert is never a silent
        no-op.
        """
        if not reason:
            raise ValueError("a revert MUST record a reason (SIG-CONTRIB-009)")
        open_ids = [
            a.assertion_id
            for a in self._assertions
            if a.contribution_id == contribution_id and a.belief_to is None and not a.is_retraction
        ]
        if not open_ids:
            raise NothingToRevertError(
                f"contribution {contribution_id!r} has no open assertions to revert"
            )
        appended: list[int] = []
        for original_id in open_ids:
            original = self._assertions[original_id]
            self._assertions[original_id] = replace(original, belief_to=at)
            retraction_id = len(self._assertions)
            self._assertions.append(
                ContributionAssertion(
                    assertion_id=retraction_id,
                    contribution_id=contribution_id,
                    subject=original.subject,
                    value=None,
                    belief_from=at,
                    retraction_of=original_id,
                    revert_reason=reason,
                )
            )
            appended.append(retraction_id)
        return appended

    # -- reads --------------------------------------------------------------
    def all_assertions(self) -> list[ContributionAssertion]:
        """Every assertion ever appended, in order (append-only; nothing removed)."""
        return list(self._assertions)

    def assertions_for(self, contribution_id: str) -> list[ContributionAssertion]:
        """Every assertion (original and retraction) tied to `contribution_id`."""
        return [a for a in self._assertions if a.contribution_id == contribution_id]

    def open_assertions(self) -> list[ContributionAssertion]:
        """The assertions SIG still holds (open belief, not themselves retractions)."""
        return [a for a in self._assertions if a.belief_to is None and not a.is_retraction]

    def is_reverted(self, contribution_id: str) -> bool:
        """Whether `contribution_id` has been fully reverted (no open originals left)."""
        rows = self.assertions_for(contribution_id)
        if not rows:
            return False
        return not any(a.belief_to is None and not a.is_retraction for a in rows)

    def value_as_of_belief(self, subject: str, as_of: datetime) -> str | None:
        """The value SIG believed about `subject` at system time `as_of`.

        Reproducibility: a revert closes but never deletes, so a belief time before
        the revert still returns the pre-revert value.
        """
        for a in self._assertions:
            if a.subject != subject or a.is_retraction:
                continue
            if a.belief_from <= as_of and (a.belief_to is None or as_of < a.belief_to):
                return a.value
        return None

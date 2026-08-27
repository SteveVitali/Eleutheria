# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The officer-naming test (§43.4, SIG-PUB-007..010).

A named individual MAY be published **only** if all five prongs hold *and* two
independent reviewers concur in writing (SIG-PUB-007/008). This module is the
deterministic gate; the concurrence itself is an agentic, recorded act. The gate
defaults to no-publish on any disagreement or missing prong, and records the
decision, its reasoning, and its reviewers.

Two categorical carve-outs sit outside the test entirely:

* Home addresses are never publishable under any prong (SIG-PUB-009) — they are
  categorically excluded (SIG-PUB-003).
* Routine audit-log rows naming an officer MUST NOT trigger the test, because
  they MUST NOT be ingested at all (SIG-PUB-010, §18.1).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class OfficerNamingProngs:
    """The five prongs of SIG-PUB-007. A name may be published only if all hold."""

    #: 1. The claim concerns official conduct, not private life.
    official_conduct: bool
    #: 2. The name appears on the face of an R1/R2 record — never inferred/assembled.
    name_on_face_of_record: bool
    #: 3. The record is public in the jurisdiction that produced it.
    record_public_in_jurisdiction: bool
    #: 4. The accountability claim genuinely fails without the name.
    claim_fails_without_name: bool
    #: 5. Severity, currency, and safety are proportionate.
    proportionate: bool

    def all_hold(self) -> bool:
        return (
            self.official_conduct
            and self.name_on_face_of_record
            and self.record_public_in_jurisdiction
            and self.claim_fails_without_name
            and self.proportionate
        )

    def failed(self) -> tuple[str, ...]:
        """The names of the prongs that do not hold (for the recorded reasoning)."""
        checks = {
            "official_conduct": self.official_conduct,
            "name_on_face_of_record": self.name_on_face_of_record,
            "record_public_in_jurisdiction": self.record_public_in_jurisdiction,
            "claim_fails_without_name": self.claim_fails_without_name,
            "proportionate": self.proportionate,
        }
        return tuple(name for name, ok in checks.items() if not ok)


@dataclass(frozen=True)
class ReviewerConcurrence:
    """One reviewer's written position (SIG-PUB-008)."""

    reviewer_id: str
    agrees: bool
    rationale: str
    #: Reviewers must be independent of each other.
    independent: bool = True


@dataclass(frozen=True)
class OfficerNamingDecision:
    """The recorded outcome of the officer-naming test (SIG-PUB-008)."""

    permitted: bool
    reason: str
    prongs: OfficerNamingProngs | None = None
    reviewers: tuple[ReviewerConcurrence, ...] = field(default_factory=tuple)


def _concurrence_ok(reviewers: tuple[ReviewerConcurrence, ...]) -> tuple[bool, str]:
    written = [r for r in reviewers if r.independent and r.rationale.strip()]
    distinct = {r.reviewer_id for r in written}
    if len(distinct) < 2:
        return False, "fewer than two independent reviewers recorded a written position"
    if not all(r.agrees for r in written):
        # Disagreement defaults to no-publish (SIG-PUB-008).
        return False, "reviewers did not concur; disagreement defaults to no-publish"
    return True, "two independent reviewers concurred in writing"


def evaluate_officer_naming(
    prongs: OfficerNamingProngs,
    reviewers: tuple[ReviewerConcurrence, ...],
    *,
    is_home_address: bool = False,
    is_routine_audit_row: bool = False,
) -> OfficerNamingDecision:
    """Decide whether a person-named claim may be published (§43.4).

    Returns a recorded :class:`OfficerNamingDecision`. Publication requires every
    prong to hold *and* two independent reviewers to concur in writing; any
    failure defaults to no-publish.
    """
    if is_home_address:
        return OfficerNamingDecision(
            permitted=False,
            reason="home addresses are outside the test entirely (SIG-PUB-009/003)",
            prongs=prongs,
            reviewers=reviewers,
        )
    if is_routine_audit_row:
        return OfficerNamingDecision(
            permitted=False,
            reason="routine audit-log rows must not trigger the test and must not "
            "be ingested (SIG-PUB-010, §18.1)",
            prongs=prongs,
            reviewers=reviewers,
        )
    if not prongs.all_hold():
        return OfficerNamingDecision(
            permitted=False,
            reason=f"prong(s) not met: {', '.join(prongs.failed())} (SIG-PUB-007)",
            prongs=prongs,
            reviewers=reviewers,
        )
    ok, why = _concurrence_ok(reviewers)
    return OfficerNamingDecision(
        permitted=ok,
        reason=why + (" (SIG-PUB-008)" if not ok else "; all five prongs hold (SIG-PUB-007/008)"),
        prongs=prongs,
        reviewers=reviewers,
    )

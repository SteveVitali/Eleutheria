# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ONE publication eligibility/disposition policy (P32.5 / ADR-124, SIG-TRUST-006).

Every public consumer — API routes, export shaping, tiles, analytics, index inputs,
edge/relationship surfaces, labels and search — decides "may this item be publicly
represented, and if not, what does the honest tombstone say" through the pure decision
functions in this module. A surface that decides locally is the defect this contract
closes (the partner-organisation ``cached_canonical_name`` leak, D-P31.5-2).

The policy is a **conjunction** (S1 §4.5 of the plan): an item is publicly permitted
only when ALL of these hold:

* **Factual/correction state** — the assertion has not been withdrawn/suppressed and
  no current ``withhold``/``restrict``/``withdraw`` disposition governs it or the
  entities it exposes (subject, object, label target). A correction appended at a
  later belief time never rewrites the earlier permissible history — the disposition
  is a NEW row over an intact spine.
* **Rights** — the rights layer's ``effective_redistributable == "yes"`` (already a
  conjunction over every cited source via :mod:`policy.rights`).
* **Sensitivity** — ``sensitivity_tier == 0`` (the API/exchange public tier).
* **Publication review** — ``organization.publication_review_required`` withholds the
  organisation from public labels/listings until an ``allow`` disposition is
  recorded. A ``withhold``/``restrict``/``withdraw`` disposition always denies; an
  ``allow`` disposition is the recorded, authority-stamped way a reviewer releases a
  flagged identity (the operator-facing policy choice stays a recorded row, never a
  silent code path).
* **Current overrides history** — dispositions are evaluated at **access time**
  (``decided_at <= now``), never at the artifact's build time: a withhold recorded in
  release R2 still denies the data under a rollback to R1, on every operator-
  controlled origin, cache, archive and compressed-origin path. Immutable artifacts
  are denied whole rather than rewritten.

Append-only: a disposition is one new row in ``publication_disposition``
(``db.deploy.publication_dispositions``); no row is ever updated or deleted. A later
disposition supersedes an earlier one *for access decisions* while the earlier row
remains on record — that is the append-only "override" semantics.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

#: The contract version stamped on every decision and persisted on every
#: ``publication_disposition`` row (SIG-TRUST-006: "recorded policy version and
#: reason"). Bump together with the SQL twin + consumers when the rule changes.
POLICY_VERSION = "publication-eligibility/1"


class Disposition(StrEnum):
    """The recorded publication dispositions (the ``disposition`` vocabulary)."""

    #: Explicitly reviewed and released — the ONLY thing that lifts a pending flag.
    ALLOW = "allow"
    #: Deliberately withheld pending a decision/remediation.
    WITHHOLD = "withhold"
    #: Restricted publication (aggregate/coarsened only — not publicly served raw).
    RESTRICT = "restrict"
    #: Withdrawn from public access (safety/rights withdrawal → tombstone).
    WITHDRAW = "withdraw"


#: Dispositions that deny public representation. ``allow`` is the only permit;
#: anything else recorded on a target denies (fail-closed — a disposition is never
#: recorded without an access consequence).
DENYING: frozenset[Disposition] = frozenset(
    {Disposition.WITHHOLD, Disposition.RESTRICT, Disposition.WITHDRAW}
)


class ReasonCategory(StrEnum):
    """Public-safe reason categories for a tombstone (never the raw rationale).

    The free-text ``rationale`` on a disposition row is for the internal record and
    stays privileged (``sig_read_public`` cannot select it); these categories are the
    only thing a public tombstone may state (S1 §4.2 "safe public categories").
    """

    REVIEW_PENDING = "pending_publication_review"
    REVIEW_DENIED = "withheld_after_review"
    RIGHTS_WITHDRAWAL = "rights_withdrawal"
    SAFETY_WITHDRAWAL = "safety_withdrawal"
    POLICY_RESTRICTION = "policy_restriction"
    SUPPRESSED = "suppressed"


class TargetKind(StrEnum):
    """What a disposition governs (``publication_disposition.target_kind``)."""

    ENTITY = "entity"  # an entity row (organisation label/listing, deployment, …)
    CLAIM = "claim"  # a single assertion
    ARTIFACT = "artifact"  # an evidence artifact/capture
    RELEASE_ARTIFACT = "release_artifact"  # a published bundle/tile/archive object


@dataclass(frozen=True)
class DispositionRecord:
    """One append-only disposition (mirrors the ``publication_disposition`` row)."""

    target_kind: TargetKind
    target_id: str
    disposition: Disposition
    reason_category: ReasonCategory
    authority: str
    #: The decision instant. ``None`` means *not yet stamped* — the database
    #: stamps it at INSERT (``DEFAULT clock_timestamp()``, the single clock
    #: authority the SQL fragments evaluate; P32.10a). An explicit value is a
    #: replay/migration input for already-recorded history only; the writer's
    #: host clock never decides a live write.
    decided_at: datetime | None
    policy_version: str = POLICY_VERSION
    decided_by: str | None = None
    rationale: str | None = None
    evidence_claim_id: str | None = None
    supersedes: str | None = None
    #: Insert order (``disposition_seq`` in PG) — the deterministic tie-break when
    #: two rows share ``decided_at``. Pure-model records may omit it (defaults 0).
    seq: int = 0


@dataclass(frozen=True)
class PublicationDecision:
    """The selector's answer: may this target be publicly represented, and if not,
    what the honest tombstone states (policy version + safe reason + authority)."""

    permitted: bool
    reason_category: ReasonCategory | None = None
    authority: str | None = None
    policy_version: str = POLICY_VERSION

    def tombstone(self) -> dict[str, Any]:
        """The public tombstone payload — reason CATEGORY and authority, never
        the privileged rationale."""
        return {
            "permitted": self.permitted,
            "reason_category": self.reason_category.value if self.reason_category else None,
            "authority": self.authority,
            "policy_version": self.policy_version,
        }


#: The decision every permitted target returns (allocated once — decisions are
#: immutable). Reasons are only carried on a denial.
_PERMITTED = PublicationDecision(permitted=True)


def latest_disposition(
    records: list[DispositionRecord] | tuple[DispositionRecord, ...],
    at: datetime | None = None,
) -> DispositionRecord | None:
    """Pure twin of ``sig.effective_disposition``: the latest row decided on or
    before ``at`` (``None`` = current access time). ``seq`` breaks an exact
    ``decided_at`` tie deterministically. An un-stamped record
    (``decided_at is None`` — not yet written) is never the effective
    disposition, mirroring ``decided_at <= clock_timestamp()`` which can never
    see an unstamped or future-dated row."""
    eligible = [
        r for r in records if r.decided_at is not None and (at is None or r.decided_at <= at)
    ]
    if not eligible:
        return None
    return max(eligible, key=lambda r: (r.decided_at, r.seq))


def organization_publication_decision(
    *,
    publication_review_required: bool,
    status: str | None,
    effective: DispositionRecord | None,
) -> PublicationDecision:
    """The entity/organisation branch — D-P31.5-2's gate (SIG-TRUST-006).

    Precedence (fail-closed): a recorded deny disposition wins; a recorded ``allow``
    lifts the pending flag; an un-reviewed flag withholds; a ``withdrawn``/
    ``suppressed`` organisation status denies outright.
    """
    if effective is not None and effective.disposition in DENYING:
        return PublicationDecision(
            permitted=False,
            reason_category=effective.reason_category,
            authority=effective.authority,
            policy_version=effective.policy_version,
        )
    allowed = effective is not None and effective.disposition is Disposition.ALLOW
    if status == "withdrawn":
        return PublicationDecision(
            permitted=False,
            reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
            authority="organization.status",
        )
    if status == "suppressed":
        return PublicationDecision(
            permitted=False,
            reason_category=ReasonCategory.SUPPRESSED,
            authority="organization.status",
        )
    if publication_review_required and not allowed:
        return PublicationDecision(
            permitted=False,
            reason_category=ReasonCategory.REVIEW_PENDING,
            authority="organization.publication_review_required",
        )
    return _PERMITTED


def claim_publication_decision(
    *,
    effective: DispositionRecord | None,
    subject: PublicationDecision | None = None,
    object_entity: PublicationDecision | None = None,
) -> PublicationDecision:
    """The claim branch: a claim is public only when it is not dispositioned AND
    neither the entity it describes (subject) nor the entity it references
    (``object_entity`` — the partner-org seam) is withheld."""
    if effective is not None and effective.disposition in DENYING:
        return PublicationDecision(
            permitted=False,
            reason_category=effective.reason_category,
            authority=effective.authority,
            policy_version=effective.policy_version,
        )
    for entity in (subject, object_entity):
        if entity is not None and not entity.permitted:
            return entity
    return _PERMITTED


def access_decision(
    effective: DispositionRecord | None,
) -> PublicationDecision:
    """The artifact/release branch — the rollback rule (SIG-TRUST-006).

    A ``release_artifact`` (a versioned bundle, tile archive, compressed-origin
    object) is served only when the CURRENT effective disposition permits it: a
    withhold recorded after the artifact shipped still denies it under rollback.
    Immutable artifacts are denied whole, never rewritten.
    """
    if effective is not None and effective.disposition in DENYING:
        return PublicationDecision(
            permitted=False,
            reason_category=effective.reason_category,
            authority=effective.authority,
            policy_version=effective.policy_version,
        )
    return _PERMITTED


def new_disposition(
    *,
    target_kind: TargetKind,
    target_id: str,
    disposition: Disposition,
    reason_category: ReasonCategory,
    authority: str,
    decided_at: datetime | None = None,
    decided_by: str | None = None,
    rationale: str | None = None,
    evidence_claim_id: str | None = None,
    supersedes: str | None = None,
    seq: int = 0,
) -> DispositionRecord:
    """Validate + construct one disposition record (the sink validates through the
    same function the SQL CHECK enforces — no path records a malformed row).

    ``decided_at`` is left ``None`` for a normal write — the decision instant is
    stamped by the DATABASE (``DEFAULT clock_timestamp()``, P32.10a: one clock
    authority, so the writer's host clock can never future-date a fresh row
    against the server clock the eligibility fragments evaluate). An explicit
    ``decided_at`` is accepted only as a replay/migration input that re-records
    already-decided history — never as a substitute "now".
    """
    if not target_id:
        raise ValueError("disposition target_id is required")
    if not authority:
        raise ValueError("disposition authority is required (who/what decided)")
    return DispositionRecord(
        target_kind=target_kind,
        target_id=target_id,
        disposition=disposition,
        reason_category=reason_category,
        authority=authority,
        decided_at=decided_at,
        policy_version=POLICY_VERSION,
        decided_by=decided_by,
        rationale=rationale,
        evidence_claim_id=evidence_claim_id,
        supersedes=supersedes,
        seq=seq,
    )

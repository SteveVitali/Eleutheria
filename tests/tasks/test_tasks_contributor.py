# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The five-tier contributor write model (§34.1, SIG-CONTRIB-001/002/006).

Covers the per-tier write scope and review requirement (SIG-CONTRIB-001), the
no-claim-without-provenance and L0-entry rules (SIG-CONTRIB-002, AC1's Python
side), the `Person`-creation gate (§34.1 Notes), and AC3 — pseudonymous
contribution at every tier including trusted reviewer (SIG-CONTRIB-006).
"""

from __future__ import annotations

from dataclasses import fields

import pytest
from tasks.contributor import (
    Contributor,
    ContributorTier,
    EvidenceLevel,
    MissingProvenanceError,
    ReviewRequirement,
    WriteScope,
    assert_has_provenance,
    entry_level_for_submission,
    may_create_person,
    may_write,
    review_requirement,
    scopes_for,
    supports_pseudonymous,
)

ALL_TIERS = tuple(ContributorTier)


def test_exactly_five_tiers() -> None:
    """SIG-CONTRIB-001: the five write tiers, no more and no fewer."""
    assert {t.value for t in ContributorTier} == {
        "anonymous",
        "registered",
        "trusted_reviewer",
        "curator",
        "maintainer",
    }


def test_write_scope_is_cumulative_up_the_ladder() -> None:
    """SIG-CONTRIB-001: each tier holds its own scope plus every lower tier's."""
    assert may_write(ContributorTier.ANONYMOUS, WriteScope.QUEUE_SUBMISSION)
    assert not may_write(ContributorTier.ANONYMOUS, WriteScope.CLAIM_R5)

    # Registered adds R5 claims + dispositions, and still may submit to the queue.
    assert may_write(ContributorTier.REGISTERED, WriteScope.CLAIM_R5)
    assert may_write(ContributorTier.REGISTERED, WriteScope.TASK_DISPOSITION)
    assert may_write(ContributorTier.REGISTERED, WriteScope.QUEUE_SUBMISSION)
    assert not may_write(ContributorTier.REGISTERED, WriteScope.HUMAN_ASSERTION)

    # Trusted reviewer verifies + promotes.
    assert may_write(ContributorTier.TRUSTED_REVIEWER, WriteScope.VERIFY_SUBMISSIONS)
    assert may_write(ContributorTier.TRUSTED_REVIEWER, WriteScope.PROMOTE_CANDIDATES)
    assert not may_write(ContributorTier.TRUSTED_REVIEWER, WriteScope.RESOLUTION_OVERRIDE)

    # Curator: assertions, overrides, sensitivity, Person creation.
    for scope in (
        WriteScope.HUMAN_ASSERTION,
        WriteScope.RESOLUTION_OVERRIDE,
        WriteScope.SENSITIVITY_CLASSIFICATION,
        WriteScope.PERSON_CREATION,
    ):
        assert may_write(ContributorTier.CURATOR, scope)
    assert not may_write(ContributorTier.CURATOR, WriteScope.SCHEMA)

    # Maintainer: ruleset/vocabulary/schema, and everything below cumulatively.
    for scope in (WriteScope.RULESET, WriteScope.VOCABULARY, WriteScope.SCHEMA):
        assert may_write(ContributorTier.MAINTAINER, scope)
    assert scopes_for(ContributorTier.MAINTAINER) == frozenset(WriteScope)


def test_review_requirement_per_tier() -> None:
    """SIG-CONTRIB-001: each tier maps to the spec's review requirement."""
    assert review_requirement(ContributorTier.ANONYMOUS) is ReviewRequirement.ALL_BEFORE_LANDING
    assert review_requirement(ContributorTier.REGISTERED) is ReviewRequirement.SAMPLED_REVIEW
    assert review_requirement(ContributorTier.TRUSTED_REVIEWER) is ReviewRequirement.SAMPLED_AUDIT
    assert review_requirement(ContributorTier.CURATOR) is ReviewRequirement.PEER_REVIEW
    assert review_requirement(ContributorTier.MAINTAINER) is ReviewRequirement.ADR_AND_REVIEW


def test_person_creation_gated_below_curator() -> None:
    """§34.1 Notes: no tier below Curator may create a `Person`."""
    assert not may_create_person(ContributorTier.ANONYMOUS)
    assert not may_create_person(ContributorTier.REGISTERED)
    assert not may_create_person(ContributorTier.TRUSTED_REVIEWER)
    assert may_create_person(ContributorTier.CURATOR)
    assert may_create_person(ContributorTier.MAINTAINER)


@pytest.mark.parametrize("tier", ALL_TIERS, ids=lambda t: t.value)
def test_pseudonymous_supported_at_every_tier(tier: ContributorTier) -> None:
    """AC3 / SIG-CONTRIB-006: pseudonymity holds at every tier, incl. trusted reviewer."""
    assert supports_pseudonymous(tier)
    # A contributor is constructible from a pseudonymous handle alone, at any tier.
    contributor = Contributor(handle="anon-mapper-7", tier=tier)
    assert contributor.handle == "anon-mapper-7"
    assert contributor.tier is tier


def test_trusted_reviewer_pseudonymity_is_explicit() -> None:
    """SIG-CONTRIB-006 calls out the trusted-reviewer tier specifically."""
    assert supports_pseudonymous(ContributorTier.TRUSTED_REVIEWER)


def test_contributor_carries_no_real_name_field() -> None:
    """SIG-CONTRIB-006/005: the model cannot represent a legal-identity requirement."""
    field_names = {f.name for f in fields(Contributor)}
    assert "handle" in field_names
    assert not (field_names & {"real_name", "legal_name", "name", "email"})


def test_submission_enters_at_l0_never_l1() -> None:
    """SIG-CONTRIB-002: the entry level is L0 for every tier."""
    assert entry_level_for_submission() is EvidenceLevel.L0_EVIDENCE
    assert EvidenceLevel.L0_EVIDENCE.value == "L0"


def test_no_claim_without_provenance() -> None:
    """SIG-CONTRIB-002: no tier may write a claim with empty provenance."""
    with pytest.raises(MissingProvenanceError):
        assert_has_provenance(None)
    with pytest.raises(MissingProvenanceError):
        assert_has_provenance("")
    with pytest.raises(MissingProvenanceError):
        assert_has_provenance([])
    # A non-empty provenance passes.
    assert_has_provenance(["evidence:ocfl-object-123"])
    assert_has_provenance("contract.pdf#p3")

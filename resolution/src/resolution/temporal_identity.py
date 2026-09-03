# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Temporal identity: reified, bitemporal OrganizationRelation records, and the
one rule everything downstream depends on — **a rename is not a succession**
(§14.5, SIG-IDENT-016/017).

Organizational change (merges, splits, absorptions, acquisitions, parentage) is
modelled as first-class :class:`OrganizationRelation` records carrying valid time
and transaction time — never as a mutable column, because the history is the
point. A pure rename is deliberately excluded from that vocabulary: it produces a
new organization *version* and a dated alias, and MUST NOT mint a succession
relation or a new identifier (SIG-IDENT-017). Conflating the two fragments an
entity's history, which is exactly the failure this ticket fixes and later tickets
must not re-introduce.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum

from .identity import Organization


class OrganizationRelationType(StrEnum):
    """The seven-value reified-relation vocabulary (SIG-IDENT-016).

    Mirrors the ontology ``OrganizationRelationType`` enum (single source of
    truth). ``renamed`` is intentionally absent — see module docstring.
    """

    SAME_AS = "same_as"
    SUCCEEDED_BY = "succeeded_by"
    MERGED_INTO = "merged_into"
    SPLIT_INTO = "split_into"
    ABSORBED = "absorbed"
    PARENT_OF = "parent_of"
    ACQUIRED = "acquired"


@dataclass(frozen=True)
class OrganizationRelation:
    """A reified, bitemporal relation between two organizations (SIG-IDENT-016).

    ``valid_from`` / ``valid_to`` are valid time (when the relation held in the
    world). Transaction time (``sys_period``) is DB-controlled and assigned on
    persist, so it is not set here. ``evidence_claim`` links the supporting claim.
    """

    from_entity: str
    to_entity: str
    relation_type: OrganizationRelationType
    valid_from: date
    valid_to: date | None = None
    evidence_claim: str | None = None

    def __post_init__(self) -> None:
        # Coerce/validate the vocabulary; a stray string fails loudly.
        object.__setattr__(self, "relation_type", OrganizationRelationType(self.relation_type))
        if self.from_entity == self.to_entity:
            raise ValueError("an organization relation MUST join two distinct entities")

    def to_row(self) -> dict[str, object]:
        """The ``organization_relation`` row (App C.4), minus DB-controlled sys_period."""
        return {
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "relation_type": self.relation_type.value,
            "valid_from": self.valid_from,
            "valid_to": self.valid_to,
            "evidence_claim": self.evidence_claim,
        }


@dataclass(frozen=True)
class Alias:
    """An organization alias with its temporal validity (§11.2)."""

    name: str
    alias_type: str = "former_name"
    valid_from: date | None = None
    valid_to: date | None = None


@dataclass(frozen=True)
class RenameResult:
    """The outcome of a pure rename (SIG-IDENT-017).

    ``relations`` and ``new_identifiers`` are ALWAYS empty: a rename is not a
    succession and never mints an identifier. ``organization`` is the new *version*
    — same ``entity_id`` and same identifier set as before (identity preserved).
    """

    organization: Organization
    new_canonical_name: str
    former_alias: Alias
    relations: tuple[OrganizationRelation, ...] = ()
    new_identifiers: tuple[str, ...] = ()


def rename_organization(
    organization: Organization,
    *,
    old_name: str,
    new_name: str,
    effective: date,
) -> RenameResult:
    """Rename an organization: new version + dated alias, no succession (SIG-IDENT-017).

    The old name becomes a ``former_name`` alias with a ``valid_to`` of the
    effective date; the new name is the current canonical name of a new version of
    the *same* entity. No :class:`OrganizationRelation` is produced and no new
    identifier is minted — the identifier set is carried over unchanged.
    """
    if not old_name or not new_name:
        raise ValueError("a rename needs both the old and new names (SIG-IDENT-017)")
    former = Alias(name=old_name, alias_type="former_name", valid_to=effective)
    # A new version of the same entity: identity (entity_id + identifiers) preserved.
    new_version = replace(organization)
    return RenameResult(
        organization=new_version,
        new_canonical_name=new_name,
        former_alias=former,
        relations=(),
        new_identifiers=(),
    )


# --- The five worked succession cases (SIG-IDENT-019) -------------------------
# Each returns the reified relation(s) plus the set of entity ids retired to
# `inactive` by the change, so a caller (and the fixtures) can assert both the
# edge and the lifecycle transition.


@dataclass(frozen=True)
class SuccessionOutcome:
    """Relations produced by a succession, plus the entity ids it retires."""

    relations: tuple[OrganizationRelation, ...] = ()
    retired: tuple[str, ...] = ()


def absorb(
    *, absorbed: str, into: str, effective: date, evidence_claim: str | None = None
) -> SuccessionOutcome:
    """A body is disbanded and absorbed by another (e.g. a PD taken over by a county sheriff)."""
    return SuccessionOutcome(
        relations=(
            OrganizationRelation(
                from_entity=absorbed,
                to_entity=into,
                relation_type=OrganizationRelationType.ABSORBED,
                valid_from=effective,
                evidence_claim=evidence_claim,
            ),
        ),
        retired=(absorbed,),
    )


def merge(
    *, sources: tuple[str, ...], into: str, effective: date, evidence_claim: str | None = None
) -> SuccessionOutcome:
    """Two or more bodies merge into a new one; each source is retired."""
    if len(sources) < 2:
        raise ValueError("a merge needs at least two source organizations (SIG-IDENT-019)")
    return SuccessionOutcome(
        relations=tuple(
            OrganizationRelation(
                from_entity=src,
                to_entity=into,
                relation_type=OrganizationRelationType.MERGED_INTO,
                valid_from=effective,
                evidence_claim=evidence_claim,
            )
            for src in sources
        ),
        retired=tuple(sources),
    )


def split(
    *, source: str, into: tuple[str, ...], effective: date, evidence_claim: str | None = None
) -> SuccessionOutcome:
    """A body splits into two or more; the source is retired."""
    if len(into) < 2:
        raise ValueError("a split needs at least two resulting organizations (SIG-IDENT-019)")
    return SuccessionOutcome(
        relations=tuple(
            OrganizationRelation(
                from_entity=source,
                to_entity=child,
                relation_type=OrganizationRelationType.SPLIT_INTO,
                valid_from=effective,
                evidence_claim=evidence_claim,
            )
            for child in into
        ),
        retired=(source,),
    )


def acquire(
    *, acquirer: str, acquired: str, effective: date, evidence_claim: str | None = None
) -> SuccessionOutcome:
    """One organization acquires another; the acquired body is not retired (it
    persists under new ownership). Product-ownership transfer is a separate vendor
    claim on the Product — see :func:`transfer_product_vendor`."""
    return SuccessionOutcome(
        relations=(
            OrganizationRelation(
                from_entity=acquirer,
                to_entity=acquired,
                relation_type=OrganizationRelationType.ACQUIRED,
                valid_from=effective,
                evidence_claim=evidence_claim,
            ),
        ),
        retired=(),
    )


def transfer_product_vendor(*, product_id: str, new_vendor: str) -> dict[str, str]:
    """The vendor-ownership transfer an acquisition produces: a new Product vendor.

    Returned as a plain mapping (a new ``vendor`` claim on the Product), never a
    mutation — products change owners through acquisition (§11.4).
    """
    return {"product_id": product_id, "vendor": new_vendor}


def municipality_department_pair(
    *,
    municipality: Organization,
    department: Organization,
    effective: date,
    evidence_claim: str | None = None,
) -> tuple[Organization, Organization, OrganizationRelation]:
    """A municipality and its police department as DISTINCT orgs joined by parent_of.

    The city and the department have different identifiers, legal capacities, and
    surveillance postures — the city signs the contract, the department operates
    the system (SIG-IDENT-009). Returns both organizations and the ``parent_of``
    relation from the municipality to the department.
    """
    if municipality.entity_id is None or department.entity_id is None:
        raise ValueError("both organizations need entity ids to be joined (SIG-IDENT-009)")
    if municipality.entity_id == department.entity_id:
        raise ValueError(
            "a municipality and its police department MUST be distinct organizations "
            "(SIG-IDENT-009)"
        )
    relation = OrganizationRelation(
        from_entity=municipality.entity_id,
        to_entity=department.entity_id,
        relation_type=OrganizationRelationType.PARENT_OF,
        valid_from=effective,
        evidence_claim=evidence_claim,
    )
    return municipality, department, relation

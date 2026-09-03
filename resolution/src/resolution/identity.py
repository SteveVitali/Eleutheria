# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Organization identity: identifiers-as-sets, the two classification axes, the
surrogate identity basis, and agency-name parsing (§11.2, §14.2-14.4).

The organization registry is the single entity for **all** institutional actors —
"vendor" is a role, not a subtype (SIG-ONTO-012). Identity here means only the
stable handles: the set of ``(scheme, value)`` external identifiers
(SIG-IDENT-006), the two independent classification axes (SIG-IDENT-010), the
lifecycle status (SIG-IDENT-018), and — for a body with no external identifier —
an immutable minted ``identity_basis`` (SIG-IDENT-012) plus the publication-review
routing a small private body needs before it is ever named (SIG-ONTO-013). The
temporal-identity relations themselves live in :mod:`resolution.temporal_identity`.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from enum import StrEnum

# A fixed namespace so the surrogate key minted from an identity basis is
# reproducible: the same basis always mints the same surrogate (idempotent
# minting — NOT the probabilistic same-as cascade, which is P03.2).
_SURROGATE_NAMESPACE = uuid.UUID("6f6b8f9e-3b6a-5e2a-9f1a-000000000031")


class OrgStatus(StrEnum):
    """Organization lifecycle status (SIG-IDENT-018).

    ``withdrawn`` means the entity was created in error; ``suppressed`` means it
    exists but is not publishable (§14.4). The two are never conflated.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
    WITHDRAWN = "withdrawn"
    SUPPRESSED = "suppressed"


@dataclass(frozen=True, order=True)
class Identifier:
    """One external identifier: a ``(scheme, value)`` pair, never a bare column.

    Frozen and hashable so a collection of them is a genuine set — the same
    ``(us.fbi.ori, TX0570000)`` observed twice is one identifier (SIG-IDENT-006).
    """

    scheme: str
    value: str

    def __post_init__(self) -> None:
        if not self.scheme or not self.value:
            raise ValueError("an identifier needs both a scheme and a value (SIG-IDENT-006)")


def identifier_set(pairs: Iterable[Identifier | tuple[str, str]]) -> frozenset[Identifier]:
    """Build the identifier **set** for an entity (SIG-IDENT-006), deduplicating."""
    out: set[Identifier] = set()
    for p in pairs:
        out.add(p if isinstance(p, Identifier) else Identifier(*p))
    return frozenset(out)


@dataclass(frozen=True)
class TwoAxisClassification:
    """The two independent axes an organization is classified on (SIG-IDENT-010).

    ``organization_class`` is *what kind of body it is* — a value of the ontology
    ``OrganizationType`` vocabulary (``us.le.sheriff``, ``university``, …).
    ``operating_relationship`` is *how it relates to the surveillance in question*
    — a value of the fourteen-role ``Role`` vocabulary (``purchaser``,
    ``operator``, …). A university is a class; "purchaser but not operator" is a
    relationship, and the same body holds different relationships over different
    deployments. The axes are orthogonal: no combination is forbidden by the other.
    """

    organization_class: str
    operating_relationship: str

    def __post_init__(self) -> None:
        if not self.organization_class:
            raise ValueError("organization_class is required (SIG-IDENT-010)")
        if not self.operating_relationship:
            raise ValueError("operating_relationship is required (SIG-IDENT-010)")


def classify(organization_class: str, operating_relationship: str) -> TwoAxisClassification:
    """Classify an organization on both axes (SIG-IDENT-010)."""
    return TwoAxisClassification(organization_class, operating_relationship)


# Namespaces whose organizations are candidate small private bodies — an HOA, an
# apartment complex, a small business, a private security firm (§11.2, SIG-ONTO-013).
_PRIVATE_CLASS_PREFIX = "private."


def requires_publication_review(organization_class: str, *, has_external_identifier: bool) -> bool:
    """Whether a surrogate-only private body must be routed through §43.4.

    A small private body observed only inside a vendor network listing "is arguably
    a set of private individuals wearing an institutional name" (SIG-ONTO-013), so
    it MUST carry a publication-review flag before any public exposure. A body with
    an external canonical identifier (an ORI, an LEI, a GEOID) is a public
    institution and is not routed by this rule.
    """
    return (not has_external_identifier) and organization_class.startswith(_PRIVATE_CLASS_PREFIX)


@dataclass(frozen=True)
class IdentityBasis:
    """The immutable basis a SIG surrogate identity is minted from (SIG-IDENT-012).

    Frozen: once minted for a body with no external identifier, the basis is never
    edited (editing it would silently repoint a surrogate at a different real-world
    organization). ``place_geoid`` and ``address_hash`` are optional — an HOA seen
    only in a portal may have neither — but the field is always present.
    """

    normalized_name: str
    org_class: str
    first_seen_source_ref: str
    first_seen_at: str
    place_geoid: str | None = None
    address_hash: str | None = None

    def __post_init__(self) -> None:
        for name in ("normalized_name", "org_class", "first_seen_source_ref", "first_seen_at"):
            if not getattr(self, name):
                raise ValueError(f"identity_basis.{name} is required (SIG-IDENT-012)")

    def stable_key(self) -> str:
        """A deterministic key over the basis; identical bases mint one surrogate."""
        return "|".join(
            (
                self.normalized_name,
                self.org_class,
                self.place_geoid or "",
                self.address_hash or "",
                self.first_seen_source_ref,
                self.first_seen_at,
            )
        )

    def as_jsonb(self) -> dict[str, str | None]:
        """The ``organization.identity_basis`` jsonb payload (App C.4)."""
        return {
            "normalized_name": self.normalized_name,
            "org_class": self.org_class,
            "place_geoid": self.place_geoid,
            "address_hash": self.address_hash,
            "first_seen_source_ref": self.first_seen_source_ref,
            "first_seen_at": self.first_seen_at,
        }


@dataclass(frozen=True)
class Organization:
    """An organization's identity surface (identity only; attributes are claims)."""

    organization_class: str
    status: OrgStatus = OrgStatus.ACTIVE
    entity_id: str | None = None
    identifiers: frozenset[Identifier] = field(default_factory=frozenset)
    identity_basis: IdentityBasis | None = None
    publication_review_required: bool = False

    @property
    def has_external_identifier(self) -> bool:
        return bool(self.identifiers)

    def to_row(self) -> dict[str, object]:
        """The ``organization`` table row (App C.4). ``cached_canonical_name`` is a
        resolver output and is deliberately never written from here."""
        return {
            "entity_id": self.entity_id,
            "organization_type": self.organization_class,
            "status": self.status.value,
            "identity_basis": self.identity_basis.as_jsonb() if self.identity_basis else None,
            "cached_canonical_name": None,
            "publication_review_required": self.publication_review_required,
        }


def mint_surrogate(basis: IdentityBasis) -> Organization:
    """Mint a surrogate-identity organization for a body with no external id.

    The surrogate ``entity_id`` is derived deterministically from the immutable
    basis (idempotent minting, SIG-IDENT-012), and a private body is flagged for
    §43.4 publication review (SIG-ONTO-013). Public ``sig:`` identifier minting and
    the same-as cascade are out of scope here (P03.2).
    """
    entity_id = str(uuid.uuid5(_SURROGATE_NAMESPACE, basis.stable_key()))
    return Organization(
        organization_class=basis.org_class,
        status=OrgStatus.ACTIVE,
        entity_id=entity_id,
        identifiers=frozenset(),
        identity_basis=basis,
        publication_review_required=requires_publication_review(
            basis.org_class, has_external_identifier=False
        ),
    )


@dataclass(frozen=True)
class AgencyName:
    """A parsed agency name: an optional parent body plus the local unit (SIG-IDENT-011)."""

    parent: str | None
    unit: str

    @property
    def has_parent(self) -> bool:
        return self.parent is not None


def parse_agency_name(name: str) -> AgencyName:
    """Parse a colon-delimited agency name into parent + local unit (SIG-IDENT-011).

    ``"Los Angeles County: Sheriff's Department"`` parses to parent
    ``"Los Angeles County"`` and unit ``"Sheriff's Department"``; the parent MUST
    then be materialized as its own Organization by the caller. A name with no
    colon has no parent and passes through unchanged. Only the first colon splits,
    so a unit may itself contain a colon.
    """
    if ":" not in name:
        return AgencyName(parent=None, unit=name.strip())
    parent, _, unit = name.partition(":")
    parent = parent.strip()
    unit = unit.strip()
    if not parent or not unit:
        # A dangling colon is not a parent/unit split — treat the whole as a unit.
        return AgencyName(parent=None, unit=name.strip())
    return AgencyName(parent=parent, unit=unit)

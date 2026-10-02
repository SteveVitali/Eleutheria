# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The canonical organisation-role taxonomy (P32.3 / SIG-TRUST-003).

Publishers, hosts, operators, owners, vendors, prime contractors, funders and
access partners are **distinct roles** — a predicate whose object is an
organisation names exactly one of them, and nothing may be inferred from a
different role's claim. The two rules this module encodes for every consumer
(the ``dot_511`` adapter, ``resolution.partner_identity`` and the P28.6
accountability join):

* **Provenance roles are never operational relationships.** ``PUBLISHER`` and
  ``HOST`` describe the source artifact's custodian — who published or hosted
  the registry, feed or page — not who operates, owns or supplies the hardware
  the record describes. A ``camera_registry_publisher`` claim is durable
  provenance (the registry's own attribution) and MUST NOT mint an
  ``operator`` entity-ref or join the accountability operator leg.
* **Operational roles mint entity candidates — the role travels with them.**
  ``OPERATOR``/``OWNER``/``VENDOR``/``PRIME``/``FUNDER``/``ACCESS``/``BUYER``/
  ``RECIPIENT`` claims carry the role on their ``object_ref`` so the identity
  layer records WHICH relationship the organisation candidate was minted for;
  the same organisation can legitimately hold several roles, but each is
  evidenced separately (SIG-TRUST-003: distinct unless evidence relates them).

The taxonomy is data, not code: connectors name roles through
:data:`ROLE_OF_PREDICATE`; the accountability join names the SAME roles for its
chain legs. This module is deliberately dependency-free so ``db``,
``resolution``, ``connectors`` and ``inference`` all consume the one mapping —
a second private role table is exactly the drift SIG-TRUST-003 forbids.
"""

from __future__ import annotations

import enum
from collections.abc import Mapping

__all__ = [
    "ENTITY_REF_ROLES",
    "ORGANIZATION_ROLES",
    "PROVENANCE_ROLES",
    "ROLE_OF_PREDICATE",
    "OrganizationRole",
    "mints_entity_ref",
    "predicates_for_role",
    "role_for_predicate",
]


class OrganizationRole(enum.StrEnum):
    """The legal/operational relationship an organisation claim asserts.

    ``PUBLISHER``/``HOST`` are provenance roles: the organisation produced or
    hosts the *source artifact*, which says nothing about the hardware or the
    parties named in it. The rest are operational roles: the organisation plays
    the named role toward the claim's subject — and only that role.
    """

    #: The organisation published the source artifact (a registry layer, feed,
    #: page or dataset). Provenance only — never an operator/owner relationship.
    PUBLISHER = "publisher"
    #: The organisation hosts the source artifact (an open-data portal or
    #: aggregation account). Weaker than PUBLISHER — it may not even have
    #: produced the record.
    HOST = "host"
    #: The organisation operates the subject (runs the camera fleet/system).
    OPERATOR = "operator"
    #: The organisation owns the subject asset.
    OWNER = "owner"
    #: The organisation sells/supplies under a contract or release.
    VENDOR = "vendor"
    #: The organisation is the prime awardee on a contract or assistance
    #: instrument — carried on ``recipient``/``seller`` claims whose award
    #: context says prime (the prime/subcontractor distinction rides on the
    #: award-kind qualifier, not on a second predicate).
    PRIME = "prime"
    #: The organisation funds the subject instrument.
    FUNDER = "funder"
    #: The organisation is a configured access/sharing partner of the subject.
    ACCESS = "access"
    #: The procuring counterparty of a contract (§11.11).
    BUYER = "buyer"
    #: The receiving party of a funding instrument (§11.12) — the generic
    #: recipient role; refines to ``PRIME`` when the instrument is a prime
    #: award or to a subcontractor role under a sub-award.
    RECIPIENT = "recipient"
    #: An organisation a legal instrument requires authorization of — the
    #: regulated party, not the regulator.
    REGULATED = "regulated"
    #: An oversight role: the organisation regulates the subject.
    REGULATOR = "regulator"
    #: An oversight role: the organisation audits the subject.
    AUDITOR = "auditor"
    #: An organisation an accountability event names (§11.17 participant — the
    #: event record lists it; the role does not by itself imply operator,
    #: vendor or access status).
    PARTICIPANT = "participant"


#: Every canonical role.
ORGANIZATION_ROLES: frozenset[OrganizationRole] = frozenset(OrganizationRole)

#: Provenance roles — the organisation published/hosted the SOURCE ARTIFACT.
#: A claim in one of these roles MUST NOT mint an organisation entity-ref for
#: any operational relationship, and MUST NOT join an operational
#: accountability leg. Keeping the label as text provenance is the honest
#: record (SIG-TRUST-003/004: a publisher label is not an identity proof for
#: the observed operator).
PROVENANCE_ROLES: frozenset[OrganizationRole] = frozenset(
    {OrganizationRole.PUBLISHER, OrganizationRole.HOST}
)

#: Roles whose claims may mint an ``organization`` entity-ref candidate (the
#: partner-ref surface, ADR-112 + P32.3): every operational role, never a
#: provenance one. The candidate stays a *candidate* — scoped until a recorded
#: identity disposition links it (SIG-TRUST-004).
ENTITY_REF_ROLES: frozenset[OrganizationRole] = frozenset(
    set(OrganizationRole) - set(PROVENANCE_ROLES)
)


#: Predicate id → the organisation role its object plays. Covers the ontology
#: predicate ids the connectors emit AND the legacy spine predicate ids the
#: accountability join reads (``operator``/``owned_by``/… — the historical
#: entity-ref surface, ADR-112 §3). A predicate absent here names no
#: organisation role; :func:`role_for_predicate` returns ``None``.
ROLE_OF_PREDICATE: Mapping[str, OrganizationRole] = {
    # -- provenance (P32.3): the registry's own publisher/host attribution.
    "camera_registry_publisher": OrganizationRole.PUBLISHER,
    # -- operational roles.
    "camera_operator": OrganizationRole.OPERATOR,
    "operator": OrganizationRole.OPERATOR,
    "operated_by": OrganizationRole.OPERATOR,
    "asset_operator": OrganizationRole.OPERATOR,
    "operator_stated": OrganizationRole.OPERATOR,
    "owner": OrganizationRole.OWNER,
    "owned_by": OrganizationRole.OWNER,
    "purchaser": OrganizationRole.BUYER,
    "vendor": OrganizationRole.VENDOR,
    "platform_provider": OrganizationRole.VENDOR,
    "provides_platform_to": OrganizationRole.VENDOR,
    "buyer": OrganizationRole.BUYER,
    "seller": OrganizationRole.VENDOR,
    "recipient": OrganizationRole.RECIPIENT,
    "funder": OrganizationRole.FUNDER,
    "configured_sharing_partner": OrganizationRole.ACCESS,
    "configured_access_edge": OrganizationRole.ACCESS,
    "requires_authorization_of": OrganizationRole.REGULATED,
    "regulator": OrganizationRole.REGULATOR,
    "auditor": OrganizationRole.AUDITOR,
    "event_organizations": OrganizationRole.PARTICIPANT,
}


def role_for_predicate(predicate_id: str) -> OrganizationRole | None:
    """The organisation role ``predicate_id``'s object plays, or ``None``."""
    return ROLE_OF_PREDICATE.get(predicate_id)


def predicates_for_role(role: OrganizationRole) -> frozenset[str]:
    """Every predicate id whose object plays ``role``."""
    return frozenset(p for p, r in ROLE_OF_PREDICATE.items() if r is role)


def mints_entity_ref(predicate_id: str) -> bool:
    """Whether ``predicate_id`` may mint an organisation entity-ref candidate.

    True exactly for the operational roles (:data:`ENTITY_REF_ROLES`); a
    provenance-role claim (``camera_registry_publisher``) and an unmapped
    predicate mint nothing. The accountability operator leg reads the same
    rule — a publisher NEVER becomes an evidenced operator (SIG-TRUST-004).
    """
    role = role_for_predicate(predicate_id)
    return role is not None and role in ENTITY_REF_ROLES

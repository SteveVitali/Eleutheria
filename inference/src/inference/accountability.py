# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Materialize the accountability linkage as labelled L4 inference (P28.6, ADR-099).

Connect the accountability layer — the §11.11-11.18 ``contract`` / ``funding_instrument``
/ ``policy`` / ``accountability_event`` / ``legal_instrument`` / ``legal_proceeding``
entities — to the RESOLVED deployments/orgs (P28.1) so a dossier answers *"who deployed
it, funded how, governed by which policy, with what oversight."* The
:func:`materialize_accountability_links` pass walks the accountability-layer entity-ref
claims out of the real spine and WRITES each discovered
**deployment→vendor→contract→funding→policy→oversight** link as a durable
:mod:`inference.derived_fact` L4 row, honoring every invariant the defining standard
demands:

* **Labelled inference, never an observation (§30, SIG-ONTO-002 / SIG-RECON-047).** A
  link lands in the L4 ``inference.*`` namespace (the ``accountability_link_materialize``
  sqitch change), carrying its ``derivation_rule`` / ``rule_version`` /
  ``input_claim_ids`` / ``confidence`` — reusing :class:`reconcile.model.Inference` (the
  labelled value object, CONSUMED not re-implemented, SIG-ENG-035). This IS the
  **procured ≠ deployed** two-layer guard at the storage layer: a contract/procurement
  claim yields a *derived accountability link*, never a deployment observation. The
  materializer NEVER coins a deployment-layer predicate (:func:`assert_not_deployment_link`)
  and NEVER reads a procurement/count claim as evidence a deployment exists — an anchor
  is an already-resolved ``deployment`` entity, not something a procurement record
  conjures.
* **Every link cites its establishing claims (§3.1, no synthetic certainty).** A link is
  emitted only when a real accountability entity-ref claim establishes it; ``input_claim_ids``
  carries them all (``derived_fact.input_claim_ids`` is NOT NULL by construction). A
  deployment for which no vendor/contract/funding/policy/oversight claim exists gets NO
  link for that segment — the honest gap the dossier shows, never a fabricated link.
* **Append-only + idempotent (+0) (ADR-005 / ADR-099).** This path only ``INSERT``s —
  there is no ``UPDATE``/``DELETE``. The insert is ``ON CONFLICT (input_digest) DO NOTHING``
  against the ``derived_fact_input_digest_key`` partial unique index; a changed
  establishing-claim set yields a new :func:`accountability_link_digest` and a superseding
  row; a re-run over an unchanged spine inserts +0.

The chain is assembled over the ``operator``/``owner``/``purchaser`` role edge that ties a
deployment to its org: a contract is reached because the deployment's operator is the
contract's ``buyer``; the vendor because it is that contract's ``seller``; the funder
because the operator is the funding instrument's ``recipient``; and so on. Anchors are
``deployment`` entities that survive resolution (``merged_into IS NULL`` — the surviving
resolved node after P28.1 dedup).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, cast

from reconcile.model import Inference

__all__ = [
    "AccountabilityLinkSummary",
    "LINK_TYPES",
    "ACCOUNTABILITY_PREDICATES",
    "DERIVATION_RULE",
    "RULE_VERSION",
    "assert_not_deployment_link",
    "accountability_link_digest",
    "link_inference",
    "read_accountability_claims",
    "read_deployment_anchors",
    "assemble_links",
    "materialize_accountability_links",
    "materialize_accountability_links_from_dsn",
    "read_materialized_accountability_links",
]

DERIVATION_RULE = "accountability_linkage/§13"
RULE_VERSION = "p28.6/1"

# --- the accountability chain link types (the L4 derived predicates) ----------
#: The five segments of the deployment→vendor→contract→funding→policy→oversight
#: chain. Each is an ACCOUNTABILITY-LAYER predicate (§13) — deliberately NOT a
#: deployment-layer one (procured ≠ deployed): a contract/procurement claim produces
#: ``procured_under_contract`` (an accountability link), never ``deployed``.
HAS_VENDOR = "has_vendor"
PROCURED_UNDER_CONTRACT = "procured_under_contract"
FUNDED_BY = "funded_by"
GOVERNED_BY_POLICY = "governed_by_policy"
OVERSEEN_BY = "overseen_by"

LINK_TYPES: frozenset[str] = frozenset(
    {HAS_VENDOR, PROCURED_UNDER_CONTRACT, FUNDED_BY, GOVERNED_BY_POLICY, OVERSEEN_BY}
)

#: The L4 predicate id a link is stored under (``inference.derived_fact.predicate_id``),
#: namespaced so it can never be confused with an observed L1 claim predicate.
_PREDICATE_PREFIX = "accountability_link:"


def link_predicate(link_type: str) -> str:
    """The namespaced ``derived_fact`` predicate id for a chain link type."""
    return f"{_PREDICATE_PREFIX}{link_type}"


# --- the procured ≠ deployed guard --------------------------------------------
#: The deployment-layer predicates a link MUST NEVER be (RISK-P21-16, §46 — the
#: predicate-layer guard applied to the accountability class). A procurement/contract
#: claim is an accountability fact; it does not deploy anything. If a link type ever
#: collided with one of these the two layers would have merged — the materializer
#: refuses to emit it. Mirrors the §29.1 count bases + the deployment lifecycle tracks.
_DEPLOYMENT_LAYER_PREDICATES: frozenset[str] = frozenset(
    {
        "deployed",
        "deployment",
        "contracted_device_count",
        "invoiced_device_count",
        "installed_device_count",
        "active_device_count",
        "mapped_device_count",
        "claimed_device_count",
        "procurement_state",
        "physical_state",
        "operational_state",
        "authorization_state",
    }
)


def assert_not_deployment_link(link_type: str) -> str:
    """Refuse a link type that would masquerade as a deployment fact (procured ≠ deployed).

    The choke point every emitted link routes through. A link type must be one of the
    accountability-layer chain segments (:data:`LINK_TYPES`) and MUST NOT be a
    deployment-layer predicate (:data:`_DEPLOYMENT_LAYER_PREDICATES`) — so a
    contract/procurement claim can never become a ``deployed`` link and the two-layer
    separation holds as a failure a test asserts, not a review-time hope.
    """
    if link_type in _DEPLOYMENT_LAYER_PREDICATES:
        raise ValueError(
            f"procured ≠ deployed: {link_type!r} is a deployment-layer predicate and MUST NOT "
            "be materialized as an accountability link (§46 RISK-P21-16; the two layers stay "
            "separate — a procurement/contract claim is not a deployment)"
        )
    if link_type not in LINK_TYPES:
        raise ValueError(
            f"unknown accountability link type {link_type!r} (expected one of {sorted(LINK_TYPES)})"
        )
    return link_type


# --- the accountability-layer predicates read off the spine -------------------
#: deployment → org role edges (§12.4): who operates / owns / purchased the deployment.
#: The join spine — a contract/funding/policy/oversight fact reaches a deployment
#: through the org that operates it.
#: P31.5 / ADR-112: ``camera_operator`` is the camera registry's operator attribution —
#: the same deployment → operating-organisation edge, emitted as an entity-ref claim.
_OPERATOR_PREDICATES: frozenset[str] = frozenset(
    {"operator", "owner", "purchaser", "operated_by", "owned_by", "camera_operator"}
)
#: deployment → vendor org, asserted directly on the deployment (§12.4 vendor/platform).
#: ``seller`` is NOT here (P31.5 / ADR-112): it is a §11.11 *contract* predicate, and a
#: procurement record that the connector sink typed with the placeholder ``deployment``
#: must never make its seller a deployment's vendor (procured ≠ deployed). A vendor is
#: reached through the contract (operator → buyer → seller) instead.
_VENDOR_PREDICATES: frozenset[str] = frozenset(
    {"vendor", "platform_provider", "provides_platform_to"}
)
#: contract → buyer (the org) / seller (the vendor) (§11.11).
_CONTRACT_BUYER = "buyer"
_CONTRACT_SELLER = "seller"
#: funding instrument → recipient (the org) / funder (§11.12).
_FUNDING_RECIPIENT = "recipient"
_FUNDING_FUNDER = "funder"
#: policy → what it applies to (org / deployment / product) (§11.13).
_POLICY_APPLIES = "applies_to"
#: oversight: accountability_event → its deployments / organizations (§11.17); legal
#: instrument → who it requires authorization of (§11.14); regulator/auditor role edges
#: (§12.4).
_EVENT_DEPLOYMENTS = "deployments"
_EVENT_ORGANIZATIONS = "organizations"
#: The accountability connector's emitted names for the same two §11.17 slots
#: (P31.5 / ADR-112: ``event_organizations`` entity-ref claims).
_EVENT_DEPLOYMENT_PREDICATES: frozenset[str] = frozenset({_EVENT_DEPLOYMENTS, "event_deployments"})
_EVENT_ORGANIZATION_PREDICATES: frozenset[str] = frozenset(
    {_EVENT_ORGANIZATIONS, "event_organizations"}
)

#: The entity type the connector claim sink gives every subject it mints (the
#: ``db.claim_sink`` placeholder). A procurement record's or an accountability
#: event's subject carries it too, so for those subjects the domain of the predicate
#: says what the subject is: the subject of a ``buyer``/``seller`` claim is a contract
#: (§11.11), of a ``recipient``/``funder`` claim a funding instrument (§11.12), of an
#: ``event_organizations``/``event_deployments`` claim an accountability event
#: (§11.17) (P31.5 / ADR-112). Such a subject is never a deployment anchor (procured ≠
#: deployed; an event is not a deployment).
_PLACEHOLDER_SUBJECT_TYPE = "deployment"
_SUBJECT_DOMAIN_BY_PREDICATE: dict[str, str] = {
    "buyer": "contract",
    "seller": "contract",
    "recipient": "funding_instrument",
    "funder": "funding_instrument",
    "event_organizations": "accountability_event",
    "event_deployments": "accountability_event",
}
_LEGAL_REQUIRES_AUTH = "requires_authorization_of"
_OVERSIGHT_ROLE_PREDICATES: frozenset[str] = frozenset({"regulator", "auditor"})

#: The full set of accountability-layer entity-ref predicates the reader pulls (a single
#: read; assembly is in Python, mirroring ``inference.materialize.read_negative_space``).
ACCOUNTABILITY_PREDICATES: frozenset[str] = frozenset(
    _OPERATOR_PREDICATES
    | _VENDOR_PREDICATES
    | {
        _CONTRACT_BUYER,
        _CONTRACT_SELLER,
        _FUNDING_RECIPIENT,
        _FUNDING_FUNDER,
        _POLICY_APPLIES,
        _LEGAL_REQUIRES_AUTH,
    }
    | _EVENT_DEPLOYMENT_PREDICATES
    | _EVENT_ORGANIZATION_PREDICATES
    | _OVERSIGHT_ROLE_PREDICATES
)


@dataclass(frozen=True)
class AcctClaim:
    """One accountability-layer entity-ref claim ``subject --predicate--> object``."""

    claim_id: str
    subject_id: str
    subject_type: str
    predicate_id: str
    object_id: str
    object_type: str


@dataclass(frozen=True)
class AccountabilityLinkSummary:
    """The outcome of one accountability-link materialization pass — all accounted for."""

    deployments_considered: int = 0
    claims_considered: int = 0
    links_derived: int = 0
    inserted: int = 0
    skipped_existing: int = 0
    by_link_type: dict[str, int] = field(default_factory=dict)

    @property
    def written(self) -> int:
        return self.inserted

    def as_dict(self) -> dict[str, Any]:
        return {
            "deployments_considered": self.deployments_considered,
            "claims_considered": self.claims_considered,
            "links_derived": self.links_derived,
            "inserted": self.inserted,
            "skipped_existing": self.skipped_existing,
            "by_link_type": dict(sorted(self.by_link_type.items())),
        }


def accountability_link_digest(value: dict[str, Any]) -> str:
    """A deterministic sha256 over a link's reproducible content (the idempotency key).

    Two passes over the same derived link (same deployment, link type, object, the org /
    contract it was assembled through, and the same sorted establishing-claim id set)
    digest identically → the insert is a no-op (+0). A changed establishing-claim set →
    a new digest → a superseding append-only row.
    """
    stable = {
        "link_type": value["link_type"],
        "deployment_id": value["deployment_id"],
        "object_id": value["object_id"],
        "object_type": value["object_type"],
        "via_org": value.get("via_org"),
        "via_contract": value.get("via_contract"),
        "establishing_claims": sorted(value["establishing_claims"]),
    }
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def link_inference(
    *,
    link_type: str,
    deployment_id: str,
    object_id: str,
    object_type: str,
    establishing_claims: Iterable[str],
    chain_role: str,
    via_org: str | None = None,
    via_contract: str | None = None,
    establishing_predicates: Iterable[str] = (),
    confidence: str = "probable",
) -> Inference:
    """Build ONE derived accountability link as a labelled L4 :class:`Inference`.

    Routes the link type through :func:`assert_not_deployment_link` (procured ≠ deployed)
    and requires at least one establishing claim (no unevidenced link, §3.1). The value
    carries the object, the chain role, and the org/contract the link was assembled
    through, so every downstream surface can render *why* the link holds. ``confidence``
    is the §29.2 ``probable`` default — the link never promotes its own certainty.
    """
    assert_not_deployment_link(link_type)
    claims = sorted({str(c) for c in establishing_claims if c})
    if not claims:
        raise ValueError(
            "an accountability link MUST cite at least one establishing claim — an "
            "unevidenced link is the forbidden unexplained edge (§3.1)"
        )
    value: dict[str, Any] = {
        "link_type": link_type,
        "chain_role": chain_role,
        "deployment_id": deployment_id,
        "object_id": object_id,
        "object_type": object_type,
        "via_org": via_org,
        "via_contract": via_contract,
        "establishing_claims": claims,
        "establishing_predicates": sorted({str(p) for p in establishing_predicates if p}),
    }
    return Inference(
        subject_id=deployment_id,
        predicate_id=link_predicate(link_type),
        value=value,
        derivation_rule=DERIVATION_RULE,
        rule_version=RULE_VERSION,
        input_claim_ids=tuple(claims),
        confidence=confidence,
        rationale=_rationale(link_type, deployment_id, object_id, via_org, via_contract),
    )


def _rationale(
    link_type: str,
    deployment_id: str,
    object_id: str,
    via_org: str | None,
    via_contract: str | None,
) -> str:
    via_bits = []
    if via_org:
        via_bits.append(f"via operator org {via_org}")
    if via_contract:
        via_bits.append(f"via contract {via_contract}")
    via = f" ({'; '.join(via_bits)})" if via_bits else " (asserted directly)"
    return (
        f"deployment {deployment_id} {link_type} {object_id}{via}; a labelled L4 inference "
        f"citing its establishing accountability-layer claims (§3.1, procured ≠ deployed)."
    )


# ---------------------------------------------------------------------------
# Reads over the resolved spine (tier-0, currently-valid; contradictions visible).
# ---------------------------------------------------------------------------


def _jurisdiction_clause(jurisdiction: str | None, column: str, params: list[Any]) -> str:
    """The §32.4 per-jurisdiction scope — the entity_identifier token match the other
    P28.x materializers use. Empty when no jurisdiction is given."""
    if not jurisdiction:
        return ""
    params.append(f"%{jurisdiction}%")
    return f" AND {column} IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"


def read_deployment_anchors(
    conn: Any, *, jurisdiction: str | None = None, subject: str | None = None
) -> list[str]:
    """The resolved ``deployment`` anchors: surviving nodes (``merged_into IS NULL``).

    A deployment entity IS the resolved deployment node — physical observations resolve
    into it (P28.1); ``merged_into IS NULL`` keeps only the surviving node after dedup, so
    a link never anchors on a merged-away duplicate. This is the procured ≠ deployed guard's
    first line: an anchor must already exist as a ``deployment`` entity — a procurement
    record cannot conjure one.
    """
    where = ["e.entity_type = 'deployment'", "e.merged_into IS NULL"]
    params: list[Any] = []
    if subject:
        where.append("e.entity_id = %s")
        params.append(subject)
    if jurisdiction:
        where.append(
            "e.entity_id IN (SELECT entity_id FROM entity_identifier WHERE value ILIKE %s)"
        )
        params.append(f"%{jurisdiction}%")
    rows = conn.execute(
        "SELECT e.entity_id::text FROM entity e WHERE "
        + " AND ".join(where)
        + " ORDER BY e.entity_id",
        tuple(params),
    ).fetchall()
    return [str(r[0]) for r in rows]


def read_accountability_claims(conn: Any) -> list[AcctClaim]:
    """Read the tier-0, currently-valid accountability-layer entity-ref claims.

    One read (assembly is in Python) of every claim whose predicate is an
    accountability-layer predicate (:data:`ACCOUNTABILITY_PREDICATES`) and that carries
    an ``object_entity`` — with the subject's and object's entity types, so the assembler
    can tell a contract's ``buyer`` from a funding instrument's ``recipient``. NEVER reads
    a procurement/count claim as evidence (those predicates are not in the set), so a
    deployment with only procurement claims yields no link (honest gap).
    """
    predicates = tuple(sorted(ACCOUNTABILITY_PREDICATES))
    rows = conn.execute(
        "SELECT c.claim_id::text, c.subject_id::text, se.entity_type, c.predicate_id, "
        "       c.object_entity::text, oe.entity_type "
        "  FROM claim c "
        "  JOIN entity se ON se.entity_id = c.subject_id "
        "  JOIN entity oe ON oe.entity_id = c.object_entity "
        " WHERE c.sensitivity_tier = 0 AND upper_inf(c.sys_period) "
        "   AND c.object_entity IS NOT NULL "
        "   AND c.predicate_id = ANY(%s) "
        " ORDER BY c.subject_id, c.predicate_id, c.claim_id",
        (list(predicates),),
    ).fetchall()
    return [
        AcctClaim(
            claim_id=str(r[0]),
            subject_id=str(r[1]),
            subject_type=str(r[2]),
            predicate_id=str(r[3]),
            object_id=str(r[4]),
            object_type=str(r[5]),
        )
        for r in rows
    ]


# ---------------------------------------------------------------------------
# The assembler — pure, DB-less, unit-testable.
# ---------------------------------------------------------------------------


def assemble_links(anchors: Iterable[str], claims: Iterable[AcctClaim]) -> list[Inference]:
    """Assemble the deployment→vendor→contract→funding→policy→oversight links (pure).

    Walks the accountability-layer claims and, for each resolved deployment anchor, emits
    a labelled L4 :class:`Inference` per discovered chain segment, each citing its
    establishing claims. The chain is assembled through the deployment's operator org
    (``buyer``/``recipient``/``applies_to`` all key on that org), plus the links asserted
    directly on the deployment (a direct ``vendor`` claim, a ``policy applies_to
    deployment``, an ``accountability_event deployments`` reference). Honest gaps: a
    segment with no establishing claim yields no link.
    """
    claims = list(claims)
    # A placeholder-typed subject that carries a contract, funding or event predicate
    # is a procurement record or an accountability event, not a deployment: it is
    # typed by the predicate's domain and removed from the anchors (procured ≠
    # deployed, P31.5 / ADR-112).
    record_subjects = {
        c.subject_id
        for c in claims
        if c.subject_type == _PLACEHOLDER_SUBJECT_TYPE
        and c.predicate_id in _SUBJECT_DOMAIN_BY_PREDICATE
    }
    anchor_set = {str(a) for a in anchors} - record_subjects

    # deployment -> [(org, operator_claim_id)]  (the join spine)
    deployment_orgs: dict[str, list[tuple[str, str]]] = {}
    # deployment -> [(vendor, claim_id)]        (direct vendor assertion)
    direct_vendors: dict[str, list[tuple[str, str]]] = {}
    # org -> [(contract, buyer_claim_id)]
    contracts_by_buyer: dict[str, list[tuple[str, str]]] = {}
    # contract -> [(vendor, seller_claim_id)]
    contract_sellers: dict[str, list[tuple[str, str]]] = {}
    # org -> [(funding, recipient_claim_id)]
    funding_by_recipient: dict[str, list[tuple[str, str]]] = {}
    # policy -> [(target_entity, applies_claim_id)]   (target: org OR deployment)
    policy_targets: dict[str, list[tuple[str, str]]] = {}
    # target_entity -> [(oversight_entity, claim_id, kind)]   (target: org OR deployment)
    oversight_by_target: dict[str, list[tuple[str, str, str]]] = {}

    for c in claims:
        p = c.predicate_id
        subject_type = c.subject_type
        if subject_type == _PLACEHOLDER_SUBJECT_TYPE and c.subject_id in record_subjects:
            subject_type = _SUBJECT_DOMAIN_BY_PREDICATE.get(p, subject_type)
        if p in _OPERATOR_PREDICATES and subject_type == "deployment":
            deployment_orgs.setdefault(c.subject_id, []).append((c.object_id, c.claim_id))
        elif p in _VENDOR_PREDICATES and subject_type == "deployment":
            direct_vendors.setdefault(c.subject_id, []).append((c.object_id, c.claim_id))
        elif p == _CONTRACT_BUYER and subject_type == "contract":
            contracts_by_buyer.setdefault(c.object_id, []).append((c.subject_id, c.claim_id))
        elif p == _CONTRACT_SELLER and subject_type == "contract":
            contract_sellers.setdefault(c.subject_id, []).append((c.object_id, c.claim_id))
        elif p == _FUNDING_RECIPIENT and subject_type == "funding_instrument":
            funding_by_recipient.setdefault(c.object_id, []).append((c.subject_id, c.claim_id))
        elif p == _POLICY_APPLIES and subject_type == "policy":
            policy_targets.setdefault(c.subject_id, []).append((c.object_id, c.claim_id))
        elif p in _EVENT_DEPLOYMENT_PREDICATES:
            # (event, deployments, D) — subject is the oversight entity, object the deployment.
            oversight_by_target.setdefault(c.object_id, []).append(
                (c.subject_id, c.claim_id, subject_type)
            )
        elif p in _EVENT_ORGANIZATION_PREDICATES:
            oversight_by_target.setdefault(c.object_id, []).append(
                (c.subject_id, c.claim_id, subject_type)
            )
        elif p == _LEGAL_REQUIRES_AUTH and c.subject_type == "legal_instrument":
            # (legal_instrument, requires_authorization_of, org/deployment).
            oversight_by_target.setdefault(c.object_id, []).append(
                (c.subject_id, c.claim_id, c.subject_type)
            )
        elif p in _OVERSIGHT_ROLE_PREDICATES:
            # (deployment/org, regulator|auditor, overseer) — subject is overseen.
            oversight_by_target.setdefault(c.subject_id, []).append(
                (c.object_id, c.claim_id, "organization")
            )

    # Invert policy targets: target_entity -> [(policy, claim_id)].
    policy_by_target: dict[str, list[tuple[str, str]]] = {}
    for policy_id, targets in policy_targets.items():
        for target, claim_id in targets:
            policy_by_target.setdefault(target, []).append((policy_id, claim_id))

    out: list[Inference] = []
    seen: set[str] = set()

    def _emit(inf: Inference) -> None:
        digest = accountability_link_digest(cast("dict[str, Any]", inf.value))
        if digest in seen:
            return
        seen.add(digest)
        out.append(inf)

    for dep in sorted(anchor_set):
        orgs = deployment_orgs.get(dep, [])

        # --- has_vendor: direct assertion on the deployment ------------------
        for vendor_id, claim_id in direct_vendors.get(dep, []):
            _emit(
                link_inference(
                    link_type=HAS_VENDOR,
                    deployment_id=dep,
                    object_id=vendor_id,
                    object_type="organization",
                    establishing_claims=[claim_id],
                    chain_role="vendor",
                    establishing_predicates=["vendor"],
                )
            )

        # --- via the operator org: contract / vendor-through-contract / funding
        for org_id, op_claim in orgs:
            for contract_id, buyer_claim in contracts_by_buyer.get(org_id, []):
                # procured_under_contract (deployment → contract)
                _emit(
                    link_inference(
                        link_type=PROCURED_UNDER_CONTRACT,
                        deployment_id=dep,
                        object_id=contract_id,
                        object_type="contract",
                        establishing_claims=[op_claim, buyer_claim],
                        chain_role="contract",
                        via_org=org_id,
                        establishing_predicates=["operator", _CONTRACT_BUYER],
                    )
                )
                # has_vendor through the contract's seller (deployment → vendor)
                for vendor_id, seller_claim in contract_sellers.get(contract_id, []):
                    _emit(
                        link_inference(
                            link_type=HAS_VENDOR,
                            deployment_id=dep,
                            object_id=vendor_id,
                            object_type="organization",
                            establishing_claims=[op_claim, buyer_claim, seller_claim],
                            chain_role="vendor",
                            via_org=org_id,
                            via_contract=contract_id,
                            establishing_predicates=["operator", _CONTRACT_BUYER, _CONTRACT_SELLER],
                        )
                    )
            # funded_by (deployment → funding instrument)
            for funding_id, recipient_claim in funding_by_recipient.get(org_id, []):
                _emit(
                    link_inference(
                        link_type=FUNDED_BY,
                        deployment_id=dep,
                        object_id=funding_id,
                        object_type="funding_instrument",
                        establishing_claims=[op_claim, recipient_claim],
                        chain_role="funding",
                        via_org=org_id,
                        establishing_predicates=["operator", _FUNDING_RECIPIENT],
                    )
                )

        # --- governed_by_policy: direct (applies_to deployment) + via org ----
        for policy_id, applies_claim in policy_by_target.get(dep, []):
            _emit(
                link_inference(
                    link_type=GOVERNED_BY_POLICY,
                    deployment_id=dep,
                    object_id=policy_id,
                    object_type="policy",
                    establishing_claims=[applies_claim],
                    chain_role="policy",
                    establishing_predicates=[_POLICY_APPLIES],
                )
            )
        for org_id, op_claim in orgs:
            for policy_id, applies_claim in policy_by_target.get(org_id, []):
                _emit(
                    link_inference(
                        link_type=GOVERNED_BY_POLICY,
                        deployment_id=dep,
                        object_id=policy_id,
                        object_type="policy",
                        establishing_claims=[op_claim, applies_claim],
                        chain_role="policy",
                        via_org=org_id,
                        establishing_predicates=["operator", _POLICY_APPLIES],
                    )
                )

        # --- overseen_by: direct (deployments/requires_auth on D) + via org --
        for over_id, claim_id, over_type in oversight_by_target.get(dep, []):
            _emit(
                link_inference(
                    link_type=OVERSEEN_BY,
                    deployment_id=dep,
                    object_id=over_id,
                    object_type=over_type,
                    establishing_claims=[claim_id],
                    chain_role="oversight",
                    establishing_predicates=["deployments"],
                )
            )
        for org_id, op_claim in orgs:
            for over_id, claim_id, over_type in oversight_by_target.get(org_id, []):
                _emit(
                    link_inference(
                        link_type=OVERSEEN_BY,
                        deployment_id=dep,
                        object_id=over_id,
                        object_type=over_type,
                        establishing_claims=[op_claim, claim_id],
                        chain_role="oversight",
                        via_org=org_id,
                        establishing_predicates=["operator", "organizations"],
                    )
                )

    return out


# ---------------------------------------------------------------------------
# The write path — append-only, idempotent.
# ---------------------------------------------------------------------------


def _insert_link(conn: Any, inf: Inference) -> bool:
    """INSERT one derived accountability link, idempotent on ``input_digest``.

    True iff a row was inserted. The value carries its establishing claims; the L4 row
    carries ``derivation_rule`` / ``rule_version`` / ``input_claim_ids`` / ``confidence``
    so the link says it is an inference (never an observation, SIG-ONTO-002).
    """
    value = cast("dict[str, Any]", inf.value)
    digest = accountability_link_digest(value)
    result = conn.execute(
        "INSERT INTO inference.derived_fact"
        "(subject_id, predicate_id, value_json, derivation_rule, rule_version, "
        " input_claim_ids, confidence, input_digest) "
        "VALUES (%s, %s, %s::jsonb, %s, %s, %s::uuid[], %s, %s) "
        "ON CONFLICT (input_digest) WHERE input_digest IS NOT NULL "
        "DO NOTHING RETURNING derived_id",
        (
            inf.subject_id,
            inf.predicate_id,
            json.dumps(value, sort_keys=True, ensure_ascii=False),
            inf.derivation_rule,
            inf.rule_version,
            list(inf.input_claim_ids),
            inf.confidence,
            digest,
        ),
    ).fetchone()
    return result is not None


def materialize_accountability_links(
    conn: Any,
    *,
    jurisdiction: str | None = None,
    subject: str | None = None,
    role: str | None = None,
) -> AccountabilityLinkSummary:
    """Materialize the accountability linkage over the resolved spine (P28.6).

    Reads the resolved ``deployment`` anchors and the accountability-layer entity-ref
    claims, assembles each deployment→vendor→contract→funding→policy→oversight link
    (:func:`assemble_links`), and writes it as an append-only, idempotent L4
    ``inference.derived_fact`` row — each link citing its establishing claims, none
    fabricated (§3.1), and never a deployment fact (procured ≠ deployed). A second call
    over an unchanged spine inserts +0.
    """
    if role:
        conn.execute(f"SET ROLE {role}")

    anchors = read_deployment_anchors(conn, jurisdiction=jurisdiction, subject=subject)
    claims = read_accountability_claims(conn)
    links = assemble_links(anchors, claims)

    inserted = skipped_existing = 0
    by_link_type: dict[str, int] = {}
    for inf in links:
        link_type = str(cast("dict[str, Any]", inf.value)["link_type"])
        if _insert_link(conn, inf):
            inserted += 1
            by_link_type[link_type] = by_link_type.get(link_type, 0) + 1
        else:
            skipped_existing += 1

    return AccountabilityLinkSummary(
        deployments_considered=len(anchors),
        claims_considered=len(claims),
        links_derived=len(links),
        inserted=inserted,
        skipped_existing=skipped_existing,
        by_link_type=by_link_type,
    )


def materialize_accountability_links_from_dsn(dsn: str, **kwargs: Any) -> AccountabilityLinkSummary:
    """Open an autocommit connection from ``dsn`` and materialize links (CLI convenience)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_accountability_links(conn, **kwargs)
    finally:
        conn.close()


def read_materialized_accountability_links(
    conn: Any, *, role: str | None = None
) -> list[dict[str, Any]]:
    """Read the materialized accountability links (the P28.5 surface / dossier seam).

    The real governance-chain dataset the dossier enrichment consumes to render
    "who deployed it, funded how, governed by which policy, with what oversight" —
    deterministically ordered, every row carrying its object, chain role, the org/contract
    it was assembled through, its establishing claims, and its confidence label. Only rows
    the materializer wrote (``input_digest IS NOT NULL``) are returned; never a link the
    evidence does not support. Read-only.
    """
    if role:
        conn.execute(f"SET ROLE {role}")
    rows = conn.execute(
        "SELECT derived_id::text, subject_id::text, predicate_id, value_json, "
        "       confidence, input_claim_ids "
        "  FROM inference.derived_fact "
        " WHERE input_digest IS NOT NULL AND predicate_id LIKE 'accountability_link:%%' "
        " ORDER BY subject_id, predicate_id, derived_id"
    ).fetchall()
    out: list[dict[str, Any]] = []
    for r in rows:
        value = r[3] if isinstance(r[3], dict) else json.loads(r[3])
        out.append(
            {
                "derived_id": r[0],
                "deployment_id": r[1],
                "predicate_id": r[2],
                "link_type": value.get("link_type"),
                "chain_role": value.get("chain_role"),
                "object_id": value.get("object_id"),
                "object_type": value.get("object_type"),
                "via_org": value.get("via_org"),
                "via_contract": value.get("via_contract"),
                "establishing_claims": [str(c) for c in (value.get("establishing_claims") or ())],
                "establishing_predicates": [
                    str(p) for p in (value.get("establishing_predicates") or ())
                ],
                "confidence": r[4],
                "input_claim_ids": [str(c) for c in (r[5] or ())],
            }
        )
    return out

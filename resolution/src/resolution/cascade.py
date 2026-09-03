# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The deterministic half of the resolution cascade — tiers 0–3 (§14.6,
SIG-IDENT-020/025).

The full cascade is six tiers; this module owns the **deterministic, auto-writing**
ones (0–3). Tiers 4–5 (Splink probabilistic matching + the review queue) and tier 6
(discard) belong to P05.1 and are deliberately not implemented here.

| Tier | Rule | Disposition |
|------|------|-------------|
| 0 | exact shared canonical identifier (ORI9/GEOID/LEI/UEI/QID) | auto-write |
| 1 | exact upstream-id crosswalk already established | auto-write |
| 2 | normalized name + state + class, minus a data-generated collision list | auto-write |
| 3a | shared government domain, minus a shared-hosting denylist | auto-write |
| 3b | exact address key **K1** + normalized name | auto-write |

Two invariants the tests pin:

* **Every match records ``match_tier`` and ``match_evidence``** (SIG-IDENT-025) —
  an unexplainable auto-merge is a violation of the defining standard.
* **Blocking-only address keys (K3/K4) are never identity evidence**
  (SIG-IDENT-013) — tier 3b uses K1 only; K3/K4 could only ever narrow a candidate
  set, which is out of this deterministic path's scope.

A civil/applicant ORI (SIG-IDENT-003) is refused as a tier-0 sole basis: it needs a
second corroborating source, so it never auto-links by itself.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from functools import cache
from importlib.resources import files
from typing import Any

from .address import AddressKeys
from .identity import Identifier
from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name
from .ori import is_civil_ori, is_valid_ori

__all__ = [
    "Candidate",
    "MatchResult",
    "CascadeContext",
    "resolve",
]


@cache
def _rules() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "cascade_rules.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


@dataclass(frozen=True)
class Candidate:
    """One side of a candidate match: an organisation's resolution surface.

    Only the fields the deterministic tiers need. ``crosswalk_ids`` are external
    identifiers an upstream crosswalk has already established as this body's (tier
    1). ``gov_domain`` is a government web domain sourced from a Tier-A/B source
    (tier 3a). ``address`` carries the tiered keys (tier 3b uses K1 only).
    """

    entity_id: str
    organization_class: str
    name: str
    state: str | None = None
    identifiers: frozenset[Identifier] = field(default_factory=frozenset)
    crosswalk_ids: frozenset[Identifier] = field(default_factory=frozenset)
    gov_domain: str | None = None
    address: AddressKeys | None = None

    @property
    def normalized_name(self) -> str:
        return normalize_org_name(self.name)


@dataclass(frozen=True)
class MatchResult:
    """A deterministic auto-write match, with its tier and machine-readable evidence.

    ``match_tier`` is the integer tier (0–3) and ``tier_label`` the "3a"/"3b"
    refinement; ``match_evidence`` is the explanation recorded with the merge
    (SIG-IDENT-025). ``disposition`` is always ``"auto_write"`` here.
    """

    left: str
    right: str
    match_tier: int
    tier_label: str
    match_evidence: dict[str, Any]
    disposition: str = "auto_write"


@dataclass(frozen=True)
class CascadeContext:
    """The deterministic cascade's exclusion data (defaults loaded from data).

    Injectable so tests (and a real data-generated collision list) can supply their
    own without touching code.
    """

    name_collisions: frozenset[str] = field(default_factory=frozenset)
    shared_hosting_domains: frozenset[str] = field(default_factory=frozenset)
    tier0_schemes: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def from_data(cls) -> CascadeContext:
        rules = _rules()
        return cls(
            name_collisions=frozenset(rules["name_collisions"]),
            shared_hosting_domains=frozenset(rules["shared_hosting_domains"]),
            tier0_schemes=frozenset(rules["tier0_schemes"]),
        )


def _shared_canonical_ids(
    a: Candidate, b: Candidate, tier0_schemes: frozenset[str]
) -> list[Identifier]:
    shared = a.identifiers & b.identifiers
    return sorted(i for i in shared if i.scheme in tier0_schemes)


def _tier0(a: Candidate, b: Candidate, ctx: CascadeContext) -> MatchResult | None:
    shared = _shared_canonical_ids(a, b, ctx.tier0_schemes)
    if not shared:
        return None

    # An ORI is usable as a tier-0 basis only if it is a valid ORI9 AND is not a
    # civil/applicant ORI (SIG-IDENT-003): a civil ORI needs a second corroborating
    # source, and a malformed ORI is not a canonical identifier at all. Non-ORI
    # shared canonical ids (GEOID/LEI/UEI/QID) pass through untouched.
    def _usable(i: Identifier) -> bool:
        if i.scheme != "us.fbi.ori":
            return True
        return is_valid_ori(i.value) and not is_civil_ori(i.value)

    usable = [i for i in shared if _usable(i)]
    if not usable:
        return None
    return MatchResult(
        left=a.entity_id,
        right=b.entity_id,
        match_tier=0,
        tier_label="0",
        match_evidence={
            "rule": "exact_shared_canonical_identifier",
            "shared_identifiers": [{"scheme": i.scheme, "value": i.value} for i in usable],
        },
    )


def _tier1(a: Candidate, b: Candidate, ctx: CascadeContext) -> MatchResult | None:
    # An upstream crosswalk has already established equivalence when one side's
    # canonical identifier appears in the other side's crosswalk-established set.
    established = sorted((a.identifiers & b.crosswalk_ids) | (b.identifiers & a.crosswalk_ids))
    if not established:
        return None
    return MatchResult(
        left=a.entity_id,
        right=b.entity_id,
        match_tier=1,
        tier_label="1",
        match_evidence={
            "rule": "established_upstream_crosswalk",
            "crosswalk_identifiers": [{"scheme": i.scheme, "value": i.value} for i in established],
        },
    )


def _tier2(a: Candidate, b: Candidate, ctx: CascadeContext) -> MatchResult | None:
    if a.state is None or a.state != b.state:
        return None
    if a.organization_class != b.organization_class:
        return None
    name = a.normalized_name
    if not name or name != b.normalized_name:
        return None
    # A name on the data-generated collision list is too ambiguous to auto-write on,
    # even with state + class — route it to review instead of merging.
    if name in ctx.name_collisions:
        return None
    return MatchResult(
        left=a.entity_id,
        right=b.entity_id,
        match_tier=2,
        tier_label="2",
        match_evidence={
            "rule": "normalized_name_state_class",
            "normalized_name": name,
            "state": a.state,
            "organization_class": a.organization_class,
            "normalize_ruleset_version": NORMALIZE_RULESET_VERSION,
        },
    )


def _tier3a(a: Candidate, b: Candidate, ctx: CascadeContext) -> MatchResult | None:
    if not a.gov_domain or a.gov_domain.lower() != (b.gov_domain or "").lower():
        return None
    domain = a.gov_domain.lower()
    if domain in ctx.shared_hosting_domains:
        return None  # a shared-hosting domain is not evidence of one body
    return MatchResult(
        left=a.entity_id,
        right=b.entity_id,
        match_tier=3,
        tier_label="3a",
        match_evidence={"rule": "shared_government_domain", "domain": domain},
    )


def _tier3b(a: Candidate, b: Candidate, ctx: CascadeContext) -> MatchResult | None:
    # K1 (TIGER line + side) is the ONLY address key this identity path may use;
    # K3/K4 are blocking-only and never reach here (SIG-IDENT-013).
    if a.address is None or b.address is None:
        return None
    k1 = a.address.k1
    if not k1 or k1 != b.address.k1:
        return None
    name = a.normalized_name
    if not name or name != b.normalized_name:
        return None
    return MatchResult(
        left=a.entity_id,
        right=b.entity_id,
        match_tier=3,
        tier_label="3b",
        match_evidence={
            "rule": "address_key_k1_plus_normalized_name",
            "address_key": {"K1": k1},
            "normalized_name": name,
        },
    )


_TIERS = (_tier0, _tier1, _tier2, _tier3a, _tier3b)


def resolve(
    a: Candidate,
    b: Candidate,
    *,
    context: CascadeContext | None = None,
) -> MatchResult | None:
    """Run the deterministic cascade (tiers 0→3) on a candidate pair.

    Returns the first tier's :class:`MatchResult` that fires (each auto-write, each
    carrying ``match_tier`` + ``match_evidence``), or ``None`` if no deterministic
    tier matches — in which case the pair falls through to the probabilistic tiers
    4–5 (the review queue), which are out of scope here (P05.1).
    """
    if a.entity_id == b.entity_id:
        raise ValueError("resolve() compares two distinct candidates")
    ctx = context if context is not None else CascadeContext.from_data()
    for tier in _TIERS:
        result = tier(a, b, ctx)
        if result is not None:
            return result
    return None

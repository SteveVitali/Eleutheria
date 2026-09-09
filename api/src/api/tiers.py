# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Access tiers and the restricted/sealed boundary (§37.4, SIG-API-011).

Three tiers exist — anonymous (rate-limited public data), registered (higher
limits), and partner (bulk, agreed terms). The load-bearing rule is that **no
tier grants ``restricted`` or ``sealed`` material through the public API**: the
tier only changes rate limits, never what classes of data are reachable. So the
visibility gate here is deliberately tier-independent — a partner key is refused
``restricted``/``sealed`` exactly as an anonymous caller is (SIG-API-012 Part VIII
enforcement, not a convenience).
"""

from __future__ import annotations

from enum import StrEnum

from evidence.tiers import StorageTier
from fastapi import Header, HTTPException


class AccessTier(StrEnum):
    """The three public-API access tiers (SIG-API-011)."""

    ANONYMOUS = "anonymous"
    REGISTERED = "registered"
    PARTNER = "partner"


#: Per-minute request budgets, exposed as metadata (rate limits differ by tier;
#: the data reachable does not — SIG-API-011). The enforcement middleware is an
#: ops concern; the budgets are declared here so the contract is inspectable.
TIER_RATE_LIMITS: dict[AccessTier, int] = {
    AccessTier.ANONYMOUS: 60,
    AccessTier.REGISTERED: 600,
    AccessTier.PARTNER: 6000,
}

#: A tiny demo key registry mapping bearer tokens to tiers. Production wires this
#: to the real credential store; the mapping shape is what the API depends on.
_DEMO_KEYS: dict[str, AccessTier] = {
    "registered-demo-key": AccessTier.REGISTERED,
    "partner-demo-key": AccessTier.PARTNER,
}


def tier_dependency(
    authorization: str | None = Header(default=None),
) -> AccessTier:
    """Resolve the caller's tier from a bearer token; no token → anonymous."""
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        return _DEMO_KEYS.get(token, AccessTier.ANONYMOUS)
    return AccessTier.ANONYMOUS


def assert_public_visibility(visibility: StorageTier) -> None:
    """Refuse ``restricted``/``sealed`` material to every tier (SIG-API-011/012).

    The public API surface only ever serves ``public`` rows. Restricted and
    sealed material is never reachable here regardless of access tier — the
    caller gets a 404 (its existence is not even confirmed through this surface).
    """
    if visibility is not StorageTier.PUBLIC:
        raise HTTPException(
            status_code=404,
            detail="not found in the public read API (restricted/sealed material "
            "is not served through any tier — SIG-API-011)",
        )

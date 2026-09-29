# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The issue/invite-based, pseudonymous tier-token curator store (§34.1, §36; ADR-100).

This productionizes the demo ``CURATION_KEYS`` registry the curation service
(:mod:`api.curation`) used to authenticate against. It replaces a hard-coded map of
token → contributor with a **real** store built from two separable halves, which is
exactly the identity-minimization posture ADR-100 records:

* **A committed, non-secret invite registry (:data:`INVITES`).** Each :class:`Invite`
  records a **pseudonymous handle**, the tier it is issued at, and the **issue / PR
  reference** that authorized it — an *audit trail of who was invited and why*. It
  carries **no token, no secret, and no real-name field** (Part VIII §0.7,
  SIG-CONTRIB-006), so the registry is safe to commit. The curator set is small and
  **vetted**: onboarding a curator is appending an invite row, **not** an open signup.

* **Per-invite bearer tokens provisioned from the environment only (HG-09).** The
  actual secret bearer token for an invited handle is read from an environment
  variable named :func:`token_env_var` (``SIG_CURATION_TOKEN_<HANDLE>``) — never a
  literal in any committed file. A handle with no committed invite can never
  authenticate **even if** a token is set for it; a token for an invited handle only
  works once the operator exports it. This is "invite-based, not open signup" with
  "secrets env-only" in one mechanism.

Everything downstream of the store is unchanged: the resolved principal is a P16.1
pseudonymous :class:`~tasks.contributor.Contributor`, every curation write stays
append-only carrying the handle as the human actor id (:class:`api.curation.CurationLog`),
anti-poisoning still applies (:mod:`tasks.poisoning`), and the surface stays
authenticated + non-public + loopback-bound (``SIG_CURATION_ENABLED``, ADR-068).

A **demo fallback** (:data:`DEMO_TOKENS`) exists solely so ``sig-api serve-curation``
and the test suite have working tokens on a machine where the operator has provisioned
nothing. :func:`load_tier_token_store` uses it **only** when no invited handle has an
env-provisioned token; the moment the operator provisions even one real token the demo
tokens are inert. A production deployment provisions real tokens, so the demo tokens
never resolve there.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

from tasks.contributor import Contributor, ContributorTier

__all__ = [
    "TIER_TOKEN_ENV_PREFIX",
    "Invite",
    "INVITES",
    "DEMO_TOKENS",
    "TierTokenStore",
    "token_env_var",
    "load_tier_token_store",
]

#: The prefix of the per-handle bearer-token environment variable (HG-09). The full
#: name is :func:`token_env_var` — ``SIG_CURATION_TOKEN_<HANDLE>``. Tokens are secrets
#: and live **only** in the environment; no committed file carries a token literal.
TIER_TOKEN_ENV_PREFIX = "SIG_CURATION_TOKEN_"


@dataclass(frozen=True)
class Invite:
    """One committed, non-secret curator invite (issue/invite-based onboarding, ADR-100).

    An invite authorizes a **pseudonymous** ``handle`` to authenticate at ``tier`` once
    the operator provisions its bearer token in the environment. ``issue_ref`` is the
    issue / PR / decision that authorized the invite — the audit trail that makes the
    curator set *vetted* rather than open. There is deliberately **no token field and
    no real-name field**: the registry is safe to commit and cannot represent a
    legal-identity requirement (SIG-CONTRIB-006, Part VIII §0.7). A ``revoked`` invite
    never resolves, so off-boarding a curator is appending ``revoked=True`` (append-only,
    an invite row is never deleted), not removing a row.
    """

    handle: str
    tier: ContributorTier
    issue_ref: str
    revoked: bool = False

    def __post_init__(self) -> None:
        if not self.handle:
            raise ValueError("an Invite MUST carry a (pseudonymous) handle")
        if not self.issue_ref:
            raise ValueError(
                "an Invite MUST cite the issue/PR that authorized it (issue-based, ADR-100)"
            )

    @property
    def contributor(self) -> Contributor:
        """The pseudonymous, tiered contributor this invite authorizes (§34.1)."""
        return Contributor(handle=self.handle, tier=self.tier)


#: The committed invite registry — the small, vetted curator set (ADR-100). Each row is
#: a pseudonymous handle + tier + the authorizing reference; **no tokens, no PII**.
#: Adding a curator is appending a row here (issue-based); it is NOT open signup, and
#: the row alone grants nothing until the operator provisions the handle's env token.
INVITES: tuple[Invite, ...] = (
    Invite(handle="sig-maintainer", tier=ContributorTier.MAINTAINER, issue_ref="ADR-100/P29.1"),
    Invite(handle="sig-curator", tier=ContributorTier.CURATOR, issue_ref="ADR-100/P29.1"),
    Invite(handle="sig-reviewer", tier=ContributorTier.TRUSTED_REVIEWER, issue_ref="ADR-100/P29.1"),
)


#: The demo token map — used **only** as a fallback when the operator has provisioned no
#: real tokens (dev, tests, ``serve-curation`` on a fresh machine). These are NOT
#: secrets (they are published here on purpose) and never resolve in a deployment that
#: has provisioned real tokens. No real-name field exists (SIG-CONTRIB-006).
DEMO_TOKENS: dict[str, Contributor] = {
    "anon-demo-key": Contributor(handle="anon-1", tier=ContributorTier.ANONYMOUS),
    "registered-demo-key": Contributor(handle="registered-1", tier=ContributorTier.REGISTERED),
    "reviewer-demo-key": Contributor(handle="reviewer-1", tier=ContributorTier.TRUSTED_REVIEWER),
    "curator-demo-key": Contributor(handle="curator-1", tier=ContributorTier.CURATOR),
    "maintainer-demo-key": Contributor(handle="maintainer-1", tier=ContributorTier.MAINTAINER),
}


def token_env_var(handle: str) -> str:
    """The environment-variable name that provisions ``handle``'s bearer token (HG-09).

    ``SIG_CURATION_TOKEN_<HANDLE>`` with the handle upper-cased and non-alphanumeric
    characters folded to ``_`` (e.g. ``sig-curator`` → ``SIG_CURATION_TOKEN_SIG_CURATOR``).
    """
    slug = "".join(ch if ch.isalnum() else "_" for ch in handle).upper()
    return f"{TIER_TOKEN_ENV_PREFIX}{slug}"


@dataclass(frozen=True)
class TierTokenStore:
    """A resolved token → contributor store (issue/invite-based, pseudonymous, ADR-100).

    Built by :func:`load_tier_token_store` from the invite registry and the environment.
    :meth:`resolve` maps a presented bearer token to its pseudonymous, tiered
    :class:`~tasks.contributor.Contributor`, or ``None`` for an unknown/empty token —
    the curation service turns ``None`` into a 401. ``demo_mode`` records whether the
    store is the published demo fallback (no operator-provisioned tokens) so the surface
    can disclose it.
    """

    _by_token: Mapping[str, Contributor]
    demo_mode: bool

    def resolve(self, token: str | None) -> Contributor | None:
        """The contributor a bearer token authenticates as, or ``None`` if unknown."""
        if not token:
            return None
        return self._by_token.get(token)

    @property
    def size(self) -> int:
        """How many tokens the store can resolve (provisioned invites, or demo tokens)."""
        return len(self._by_token)


def load_tier_token_store(
    env: Mapping[str, str] | None = None,
    *,
    invites: tuple[Invite, ...] = INVITES,
    allow_demo_fallback: bool = True,
) -> TierTokenStore:
    """Build the tier-token store from the invite registry + environment (ADR-100, HG-09).

    For each non-revoked invite whose bearer token is set in the environment
    (:func:`token_env_var`), bind that token to the invite's pseudonymous contributor.
    A revoked invite, or one with no env token, contributes nothing — so a handle can
    authenticate **only** when it is both invited (committed registry) and provisioned
    (operator env), which is precisely "invite-based, not open signup" + "secrets
    env-only". A token set for a handle that has no committed invite is ignored.

    When no invite is provisioned and ``allow_demo_fallback`` is true, fall back to the
    published :data:`DEMO_TOKENS` (``demo_mode=True``) so dev/test/``serve-curation``
    work; the moment one real token is provisioned the demo tokens are inert.
    """
    source = os.environ if env is None else env
    by_token: dict[str, Contributor] = {}
    for invite in invites:
        if invite.revoked:
            continue
        token = (source.get(token_env_var(invite.handle)) or "").strip()
        if token:
            by_token[token] = invite.contributor
    if by_token:
        return TierTokenStore(_by_token=by_token, demo_mode=False)
    if allow_demo_fallback:
        return TierTokenStore(_by_token=dict(DEMO_TOKENS), demo_mode=True)
    return TierTokenStore(_by_token={}, demo_mode=False)

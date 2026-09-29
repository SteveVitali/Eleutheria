# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The issue/invite-based, pseudonymous tier-token curator store (P29.1, ADR-100).

Deterministic acceptance criteria for the productionized curator store:

* **Issue/invite-based, NOT open signup.** A token authenticates only when its handle
  is both *invited* (committed :data:`INVITES`) and *provisioned* (operator env). A
  token for a non-invited handle never resolves; a revoked invite never resolves.
* **Secrets env-only (HG-09).** The token value comes from the environment; no token
  literal is committed. The invite registry carries no token and no real-name field.
* **Pseudonymous (SIG-CONTRIB-006).** The resolved principal is keyed by a pseudonymous
  handle; the model has no real-name field at any tier.
* **Demo fallback only when nothing is provisioned.** The published demo tokens are
  active only when no invite has an env token; one real token makes them inert.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from api.tier_tokens import (
    DEMO_TOKENS,
    INVITES,
    Invite,
    TierTokenStore,
    load_tier_token_store,
    token_env_var,
)
from tasks.contributor import ContributorTier


def test_invites_are_pseudonymous_and_carry_no_secret() -> None:
    # The committed invite registry is safe to commit: no token field, no real-name
    # field, and every row cites the issue/PR that authorized it (issue-based).
    fields = {f.name for f in dataclasses.fields(Invite)}
    assert "token" not in fields
    assert not fields & {"name", "real_name", "legal_name", "email"}
    assert INVITES, "the vetted curator set must not be empty"
    for invite in INVITES:
        assert invite.handle  # pseudonymous handle
        assert invite.issue_ref  # audit trail of who authorized it


def test_token_resolves_only_when_invited_and_provisioned() -> None:
    invite = INVITES[0]
    env = {token_env_var(invite.handle): "s3cret-provisioned-token"}
    store = load_tier_token_store(env)
    assert store.demo_mode is False
    resolved = store.resolve("s3cret-provisioned-token")
    assert resolved is not None
    assert resolved.handle == invite.handle
    assert resolved.tier == invite.tier
    # An unknown / empty token never resolves.
    assert store.resolve("not-a-token") is None
    assert store.resolve("") is None
    assert store.resolve(None) is None


def test_token_for_a_non_invited_handle_is_ignored_not_open_signup() -> None:
    # Setting a token for a handle that has no committed invite grants nothing — this
    # is the "not open signup" property: presence of an env token is insufficient.
    env = {token_env_var("random-outsider"): "outsider-token"}
    store = load_tier_token_store(env, allow_demo_fallback=False)
    assert store.resolve("outsider-token") is None
    assert store.size == 0


def test_revoked_invite_never_resolves() -> None:
    revoked = Invite(
        handle="sig-former-curator",
        tier=ContributorTier.CURATOR,
        issue_ref="ADR-100/P29.1",
        revoked=True,
    )
    env = {token_env_var(revoked.handle): "revoked-token"}
    store = load_tier_token_store(env, invites=(revoked,), allow_demo_fallback=False)
    assert store.resolve("revoked-token") is None
    assert store.size == 0


def test_demo_fallback_only_when_nothing_provisioned() -> None:
    # No env tokens → demo fallback, so dev/test/serve-curation work.
    demo = load_tier_token_store({})
    assert demo.demo_mode is True
    assert demo.resolve("curator-demo-key") is not None
    # One provisioned real token → demo tokens are inert.
    env = {token_env_var(INVITES[0].handle): "real-token"}
    provisioned = load_tier_token_store(env)
    assert provisioned.demo_mode is False
    assert provisioned.resolve("curator-demo-key") is None
    assert provisioned.resolve("real-token") is not None


def test_no_real_name_field_in_demo_tokens() -> None:
    # SIG-CONTRIB-006 / Part VIII §0.7: no legal-identity field on the resolved principal.
    for contributor in DEMO_TOKENS.values():
        assert not hasattr(contributor, "real_name")
        assert not hasattr(contributor, "legal_name")
        assert contributor.handle


def test_token_env_var_name_shape() -> None:
    assert token_env_var("sig-curator") == "SIG_CURATION_TOKEN_SIG_CURATOR"
    assert token_env_var("sig_reviewer") == "SIG_CURATION_TOKEN_SIG_REVIEWER"


def test_no_provisioned_token_literal_in_contribution_sources() -> None:
    # HG-09: the tier-token + contribution-back sources provision tokens from the
    # environment only — no committed file carries a curator token or MapRoulette key
    # literal. (The published DEMO_TOKENS keys are non-secret dev placeholders.)
    root = Path(__file__).resolve().parents[1].parent
    sources = [
        root / "api" / "src" / "api" / "tier_tokens.py",
        root / "api" / "src" / "api" / "curation.py",
        root / "tasks" / "src" / "tasks" / "maproulette.py",
        root / "ops" / "config.toml",
    ]
    env_assign = re.compile(r"""SIG_[A-Z0-9_]*(?:TOKEN|KEY)\s*=\s*["'][^"']""")
    api_key_literal = re.compile(r"""\bapi_key\s*=\s*["'][^"']""")
    offenders: list[str] = []
    for path in sources:
        for lineno, line in enumerate(path.read_text().splitlines(), start=1):
            if "os.environ" in line or "getenv" in line or "source.get" in line:
                continue
            if env_assign.search(line) or api_key_literal.search(line):
                offenders.append(f"{path.name}:{lineno}: {line.strip()}")
    assert not offenders, "provisioned token literal(s) found:\n" + "\n".join(offenders)


def test_store_is_frozen_and_disallows_open_signup_by_construction() -> None:
    # There is no method that *adds* a token at runtime — the store is immutable and
    # built once from the invite registry + env. (No open-signup surface exists.)
    store = load_tier_token_store({})
    assert isinstance(store, TierTokenStore)
    assert not hasattr(store, "register")
    assert not hasattr(store, "signup")
    assert not hasattr(store, "add_token")

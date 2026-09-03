# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Backfill, replay, and shadow mode (§21.7, SIG-INGEST-017/018/019).

Re-running extraction over archived captures with an improved parser MUST produce
a new claim set **without destroying the old one** (SIG-INGEST-017). Replay runs
against archived snapshots only, in a network-isolated context, so it is both
reproducible and incapable of hammering an upstream (SIG-INGEST-018) — the replay
here reads captures back from the store by digest and runs the post-capture
stages under :func:`connectors.isolation.network_isolated`.

A replay can run in **shadow mode** (SIG-INGEST-019): it produces the new claim
set, diffs it against the current one, and reports the delta *for review* before
anything is asserted. :func:`diff_claim_sets` computes that delta over the same
canonicalisation the reproducibility check uses (:func:`evidence.ingest_run.
canonical_claim_tuple`), so a claim that differs only in its generated id or
transaction time is *unchanged*, and a real change in a derived value is *seen*.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evidence.ingest_run import canonical_claim_tuple, claim_set_fingerprint

from .pipeline import run_post_capture
from .stages import CaptureRef, Connector, RunContext


def replay(
    connector: Connector,
    ctx: RunContext,
    captures: list[CaptureRef],
) -> list[dict[str, Any]]:
    """Re-run the post-capture stages over archived captures (SIG-INGEST-017/018).

    Network-isolated (via :func:`run_post_capture`) and non-asserting: the caller
    gets the new claim set back to compare or store as a new interpretation, and
    the source is never contacted. ``ctx.replay`` is forced true so nothing is
    asserted even if a claim sink is present.
    """
    ctx.replay = True
    claims: list[dict[str, Any]] = []
    for capture in captures:
        claims.extend(run_post_capture(connector, ctx, capture))
    return claims


def replay_fingerprint(claims: list[dict[str, Any]]) -> str:
    """The order-independent fingerprint of a replayed claim set (SIG-INGEST-003/017)."""
    return claim_set_fingerprint([dict(c) for c in claims])


@dataclass(frozen=True)
class ShadowDiff:
    """The delta a shadow replay reports before asserting (SIG-INGEST-019)."""

    added: list[dict[str, Any]] = field(default_factory=list)
    removed: list[dict[str, Any]] = field(default_factory=list)
    unchanged: list[dict[str, Any]] = field(default_factory=list)
    #: A shadow diff never asserts — this is always False, and load is never called.
    asserted: bool = False

    @property
    def changed_count(self) -> int:
        return len(self.added) + len(self.removed)

    def summary(self) -> dict[str, int]:
        """Counts a reviewer sees before deciding to land the parser change."""
        return {
            "added": len(self.added),
            "removed": len(self.removed),
            "unchanged": len(self.unchanged),
            "changed": self.changed_count,
        }


def diff_claim_sets(
    current: list[dict[str, Any]],
    new: list[dict[str, Any]],
) -> ShadowDiff:
    """Diff two claim sets by canonical value (SIG-INGEST-019).

    Identity is the canonical claim tuple, which excludes the generated id and
    transaction time (SIG-INGEST-003), so churn in those never registers as a
    change but a genuinely altered derived value does.
    """
    current_by_key = {canonical_claim_tuple(c): c for c in current}
    new_by_key = {canonical_claim_tuple(c): c for c in new}
    added = [c for k, c in new_by_key.items() if k not in current_by_key]
    removed = [c for k, c in current_by_key.items() if k not in new_by_key]
    unchanged = [c for k, c in new_by_key.items() if k in current_by_key]
    return ShadowDiff(added=added, removed=removed, unchanged=unchanged)


def shadow_replay(
    connector: Connector,
    ctx: RunContext,
    captures: list[CaptureRef],
    current_claims: list[dict[str, Any]],
) -> ShadowDiff:
    """Replay in shadow mode and report the delta without asserting (SIG-INGEST-019).

    Produces the new claim set from the archived captures, diffs it against the
    current one, and returns the delta. Nothing is asserted: ``ctx.shadow`` and
    ``ctx.replay`` suppress the claim sink, and this function never calls it.
    """
    ctx.shadow = True
    ctx.replay = True
    new_claims = replay(connector, ctx, captures)
    return diff_claim_sets(current_claims, new_claims)


__all__ = [
    "ShadowDiff",
    "diff_claim_sets",
    "replay",
    "replay_fingerprint",
    "shadow_replay",
]

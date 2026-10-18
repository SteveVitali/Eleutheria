# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Ingest-run recording and reproducibility (§17.7, SIG-EVID-016/017/018).

Every claim references an ``ingest_run`` recording connector version, code commit,
ruleset version, vocabulary version, input evidence digests, parameters, and
environment (SIG-EVID-016). Ingestion runs with ``LC_ALL=C`` and ``TZ=UTC`` and
MUST NOT use wall-clock time in any derived claim value (SIG-EVID-018).

Re-running a pinned connector over pinned evidence digests MUST produce
byte-identical claim tuples modulo ``claim_id`` and ``sys_period`` (SIG-EVID-017).
:func:`canonical_claim_tuple` is the canonicalisation the reproducibility CI test
compares: it drops the two non-deterministic columns and renders the rest
byte-stably, so a re-run's fingerprint is identical iff the derived facts are.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .claim_identity import PredicateClass, digest_base

# P35.22: the excluded-columns frozenset that used to live here (``claim_id``,
# ``sys_period``, ``recorded_at``) is subsumed by ``claim_identity``'s
# NEVER_IDENTITY_KEYS — the same exclusions plus the volatile-acquisition set.

# The environment ingestion MUST run under (SIG-EVID-018).
REQUIRED_ENVIRONMENT: dict[str, str] = {"LC_ALL": "C", "TZ": "UTC"}


def deterministic_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    """The environment map an ``ingest_run`` records (SIG-EVID-018)."""
    env = dict(REQUIRED_ENVIRONMENT)
    if extra:
        env.update(extra)
    return env


def assert_deterministic_environment(environment: dict[str, str]) -> None:
    """Fail loudly if an ingest environment is not LC_ALL=C / TZ=UTC (SIG-EVID-018)."""
    for key, expected in REQUIRED_ENVIRONMENT.items():
        actual = environment.get(key)
        if actual != expected:
            raise ValueError(
                f"ingestion must run with {key}={expected} (SIG-EVID-018), got {actual!r}"
            )


@dataclass(frozen=True)
class IngestRun:
    """The reproducibility record every claim points back to (SIG-EVID-016)."""

    connector_name: str
    connector_version: str
    code_commit: str
    ruleset_version: str
    vocab_version: str
    input_digests: tuple[str, ...]
    parameters: dict[str, object] = field(default_factory=dict)
    environment: dict[str, str] = field(default_factory=lambda: deterministic_environment())

    def __post_init__(self) -> None:
        assert_deterministic_environment(self.environment)

    def to_row(self) -> dict[str, object]:
        return {
            "connector_name": self.connector_name,
            "connector_version": self.connector_version,
            "code_commit": self.code_commit,
            "ruleset_version": self.ruleset_version,
            "vocab_version": self.vocab_version,
            "input_digests": list(self.input_digests),
            "parameters": self.parameters,
            "environment": self.environment,
        }


def canonical_claim_tuple(
    claim: dict[str, object], *, temporal_class: PredicateClass = "ref"
) -> bytes:
    """Canonicalise a claim tuple for the reproducibility check (SIG-EVID-017).

    P35.22 (F-504): the tuple runs the same identity projection the minted
    ``content_digest`` does (:func:`evidence.claim_identity.digest_base`) — the
    non-deterministic columns AND the volatile acquisition fields (row
    position, page/capture URL, capture digest, fetch time, upstream version
    counters) leave it, so two runs of a pinned connector over pinned digests
    fingerprint identically even when the input's row order, pagination or
    fetch times differ — the derived facts are what is compared. The predicate's
    registry ``obs``/``ref`` class decides whether the temporal qualifier is
    part of the comparison (``obs`` keeps it).
    """
    base = digest_base(claim, temporal_class=temporal_class)
    return json.dumps(
        base, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    ).encode("utf-8")


def claim_set_fingerprint(
    claims: list[dict[str, Any]],
    *,
    classes: Mapping[str, PredicateClass] | None = None,
) -> str:
    """A single fingerprint over a set of claim tuples (order-independent).

    ``classes`` (P35.22) is the registry's predicate → ``obs``/``ref`` map; a
    claim whose predicate is absent from it compares as ``ref``.
    """
    import hashlib

    def cls(claim: Mapping[str, Any]) -> PredicateClass:
        if classes is None:
            return "ref"
        return classes.get(str(claim.get("predicate_id") or ""), "ref")

    parts = sorted(canonical_claim_tuple(c, temporal_class=cls(c)) for c in claims)
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
        digest.update(b"\n")
    return digest.hexdigest()

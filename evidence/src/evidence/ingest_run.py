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
from dataclasses import dataclass, field

# Columns that legitimately differ between two runs of the same connector over the
# same digests, and are therefore excluded from the reproducibility comparison.
NON_DETERMINISTIC_COLUMNS: frozenset[str] = frozenset({"claim_id", "sys_period", "recorded_at"})

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


def canonical_claim_tuple(claim: dict[str, object]) -> bytes:
    """Canonicalise a claim tuple for the reproducibility check (SIG-EVID-017).

    Drops the non-deterministic columns (``claim_id``, ``sys_period``,
    ``recorded_at``) and renders the rest with sorted keys, so two runs of a
    pinned connector over pinned digests fingerprint identically.
    """
    stable = {k: v for k, v in claim.items() if k not in NON_DETERMINISTIC_COLUMNS}
    return json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")


def claim_set_fingerprint(claims: list[dict[str, object]]) -> str:
    """A single fingerprint over a set of claim tuples (order-independent)."""
    import hashlib

    parts = sorted(canonical_claim_tuple(c) for c in claims)
    digest = hashlib.sha256()
    for part in parts:
        digest.update(part)
        digest.update(b"\n")
    return digest.hexdigest()

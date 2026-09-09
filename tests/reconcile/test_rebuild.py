# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Byte-identical L3 rebuild (§28.7, SIG-RECON-019/020/021).

The CI reproducibility gate: regenerate the committed sample resolution and assert
its ``input_digest`` (and full decision key) match byte-for-byte; a resolution is
reproducible from ``(claims + ruleset_version + resolver_version + as_of pair)``
and is never edited in place — a mismatch is a *superseding* new resolution.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import date

import pytest
from reconcile.rebuild import (
    NonReproducible,
    load_sample,
    rebuild_resolution,
    verify_reproducible,
)
from reconcile.resolve import RESOLVER_VERSION
from reconcile.ruleset import load_ruleset

AS_OF = date(2026, 9, 1)


# --- SIG-RECON-020: CI regenerates a sample and asserts a match --------------


def test_committed_sample_regenerates_byte_identically() -> None:
    sample = load_sample()
    # The sample is pinned to the current ruleset/resolver; if this fails the
    # sample must be regenerated deliberately (that is the point of the gate).
    assert sample.ruleset_version == load_ruleset().version
    assert sample.resolver_version == RESOLVER_VERSION

    r = sample.resolve()
    assert r.input_digest == sample.expected_input_digest
    assert json.loads(json.dumps(list(r.decision_key()))) == sample.expected_decision_key


def test_sample_is_a_meaningful_multiclaim_resolution() -> None:
    # Guard against a degenerate sample that would make the gate vacuous.
    sample = load_sample()
    assert len(sample.claims) >= 2
    r = sample.resolve()
    assert r.resolution_status == "RESOLVED"
    assert r.value is not None


# --- SIG-RECON-020: reproducible from the same inputs ------------------------


def test_verify_reproducible_roundtrips_a_stored_resolution() -> None:
    sample = load_sample()
    stored = sample.resolve()
    rebuilt = verify_reproducible(stored, sample.claims)
    assert rebuilt.input_digest == stored.input_digest
    assert rebuilt.decision_key() == stored.decision_key()


def test_a_changed_claim_breaks_the_digest() -> None:
    # The digest is the tamper-evidence: mutate a claim and reproduction fails.
    sample = load_sample()
    stored = sample.resolve()
    tampered = list(sample.claims)
    tampered[0] = replace(tampered[0], value=999)
    with pytest.raises(NonReproducible, match="input_digest mismatch"):
        verify_reproducible(stored, tampered)


# --- SIG-RECON-021: never edited in place; versions must match ---------------


def test_rebuild_returns_a_new_record_and_does_not_mutate_the_stored_one() -> None:
    sample = load_sample()
    stored = sample.resolve()
    rebuilt = rebuild_resolution(stored, sample.claims)
    assert rebuilt is not stored  # a new resolution, never an in-place edit


def test_a_version_change_refuses_to_reproduce() -> None:
    # A different ruleset/resolver version is a legitimate recompute (a superseding
    # resolution), not a reproduction — verify refuses to compare across versions.
    sample = load_sample()
    stored = sample.resolve()
    bumped = replace(stored, ruleset_version="9999.9")
    with pytest.raises(NonReproducible, match="ruleset_version differs"):
        rebuild_resolution(bumped, sample.claims)
    bumped_resolver = replace(stored, resolver_version="p99.9/9.9.9")
    with pytest.raises(NonReproducible, match="resolver_version differs"):
        rebuild_resolution(bumped_resolver, sample.claims)

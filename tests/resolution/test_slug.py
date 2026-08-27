# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vendor-portal slug parsing: versioned grammar, denylist, hypothesis-only
(SIG-IDENT-015)."""

from __future__ import annotations

from resolution.slug import SLUG_GRAMMAR_VERSION, is_denied_slug, parse_slug


def test_slug_parses_by_grammar_into_a_hypothesis() -> None:
    hyp = parse_slug("city-of-berkeley")
    assert hyp is not None
    assert hyp.tokens == ("city", "of", "berkeley")
    assert hyp.name_hypothesis == "city of berkeley"
    # It is a HYPOTHESIS, never an identity assertion (SIG-IDENT-015).
    assert hyp.is_hypothesis is True
    assert hyp.grammar_version == SLUG_GRAMMAR_VERSION


def test_grammar_is_versioned() -> None:
    assert SLUG_GRAMMAR_VERSION


def test_multiple_separators_are_handled_by_the_grammar() -> None:
    hyp = parse_slug("Travis_County.Sheriff-Office")
    assert hyp is not None
    assert hyp.tokens == ("travis", "county", "sheriff", "office")


def test_denylisted_test_tenants_never_parse_to_a_body() -> None:
    for slug in ("test", "demo", "sandbox", "acme-demo", "training"):
        assert is_denied_slug(slug)
        assert parse_slug(slug) is None


def test_contains_denylist_marker_is_denied() -> None:
    assert is_denied_slug("flock-test-tenant")
    assert parse_slug("flock-test-tenant") is None


def test_empty_slug_is_denied() -> None:
    assert is_denied_slug("")
    assert parse_slug("   ") is None

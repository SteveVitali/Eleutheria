# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.3 count-scope semantics (SIG-TRUST-004, ADR-122).

Scope-qualified comparability: 299 metro and ~190 city answer different
questions — a scope mismatch, never a contradiction — while a same-scope value
disagreement stays a contradiction. A derived approximate sum (~190) is
labelled, names its inputs, and can never be an observation.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from reconcile.count_scope import (
    CountScope,
    ScopeRelation,
    compare_scope,
    derive_approximate_sum,
    partition_by_scope,
    scope_from_qualifiers,
    scope_key,
)


@dataclass
class _Claim:
    value: int
    count_basis: str = "observed_devices"
    scope: CountScope | None = None


METRO = CountScope(label="metro", jurisdiction="us.state_abbr:OK")
CITY_ACTIVE = CountScope(label="city_limits", jurisdiction="us.state_abbr:OK", detail="active")
CITY_PRIVATE = CountScope(
    label="city_limits", jurisdiction="us.state_abbr:OK", detail="privately_owned"
)
CITY_OTHER_STATE = CountScope(label="city_limits", jurisdiction="us.state_abbr:TX")


def test_compare_scope_three_way_relation() -> None:
    assert compare_scope(METRO, CountScope("metro", "us.state_abbr:OK")) is ScopeRelation.SAME
    assert compare_scope(METRO, CITY_ACTIVE) is ScopeRelation.DIFFERENT
    assert compare_scope(CITY_ACTIVE, CITY_PRIVATE) is ScopeRelation.DIFFERENT
    # An undeclared scope can never establish comparability — UNKNOWN, not SAME.
    assert compare_scope(METRO, None) is ScopeRelation.UNKNOWN
    assert compare_scope(None, None) is ScopeRelation.UNKNOWN


def test_partition_by_scope_keeps_scopes_separate() -> None:
    claims = [
        _Claim(299, scope=METRO),
        _Claim(300, scope=METRO),  # same-scope pair — the contradiction set
        _Claim(90, scope=CITY_ACTIVE),
        _Claim(100, scope=CITY_PRIVATE),
        _Claim(42),  # undeclared
    ]
    parts = partition_by_scope(claims)
    assert parts[scope_key(METRO)] == [claims[0], claims[1]]
    assert parts[scope_key(CITY_ACTIVE)] == [claims[2]]
    assert parts[scope_key(CITY_PRIVATE)] == [claims[3]]
    assert parts["unscoped"] == [claims[4]]
    # The 299 metro / 90 city pair never lands in one bucket — not a contradiction.
    assert len(parts) == 4


def test_scope_from_qualifiers_reads_mapping_and_rows() -> None:
    mapping = {
        "count_scope": "City_Limits",
        "count_scope_detail": "Active",
        "jurisdiction": "us.state_abbr:OK",
    }
    scope = scope_from_qualifiers(mapping)
    assert scope == CountScope("City_Limits", "us.state_abbr:OK", "Active")
    rows = [
        {
            "qualifier_id": "count_scope",
            "value_text": "metro",
            "jurisdiction": "us.state_abbr:OK",
        },
        {"qualifier_id": "count_scope_detail", "value_text": "mapped"},
        {"qualifier_id": "evidence_origin", "value_text": "seed_fixture"},
    ]
    assert scope_from_qualifiers(rows) == CountScope("metro", "us.state_abbr:OK", "mapped")
    assert scope_from_qualifiers({}) is None
    unscoped = [{"qualifier_id": "evidence_origin", "value_text": "live"}]
    assert scope_from_qualifiers(unscoped) is None


def test_derive_approximate_sum_labels_the_rollup() -> None:
    claims = [
        _Claim(90, "agency_active", CITY_ACTIVE),
        _Claim(100, "claimed_devices", CITY_PRIVATE),
    ]
    total = derive_approximate_sum("okc", claims, basis="derived_total")
    assert total.value == 190 and total.label == "~190"
    assert total.is_observation is False and total.pushable_to_osm is False
    assert total.layer == "L4"
    # The roll-up scope is the shared place without the sub-population detail.
    assert total.scope == CountScope("city_limits", "us.state_abbr:OK")
    view = total.as_view()
    assert view["derived"] is True and view["approximate"] is True
    assert view["inputs"] == [90, 100]
    assert view["scope"] == "city_limits (us.state_abbr:OK)"
    assert set(view["input_bases"]) == {"agency_active", "claimed_devices"}


def test_derive_approximate_sum_refuses_scope_conflation() -> None:
    # Mixed scopes: the exact conflation P32.3 exists to prevent.
    with pytest.raises(ValueError, match="across scopes"):
        derive_approximate_sum("okc", [_Claim(299, scope=METRO), _Claim(90, scope=CITY_ACTIVE)])
    # Undeclared scope: comparability UNKNOWN — never summed.
    with pytest.raises(ValueError, match="undeclared"):
        derive_approximate_sum("okc", [_Claim(10), _Claim(90, scope=CITY_ACTIVE)])
    # Same place but one detail undeclared: disjointness unprovable.
    with pytest.raises(ValueError, match="undeclared sub-population"):
        derive_approximate_sum(
            "okc",
            [
                _Claim(90, scope=CITY_ACTIVE),
                _Claim(50, scope=CountScope("city_limits", "us.state_abbr:OK")),
            ],
        )
    # Same detail twice is the same sub-population — a contradiction set, not parts.
    with pytest.raises(ValueError, match="same sub-population"):
        derive_approximate_sum(
            "okc", [_Claim(90, scope=CITY_ACTIVE), _Claim(95, scope=CITY_ACTIVE)]
        )
    with pytest.raises(ValueError, match="at least one"):
        derive_approximate_sum("okc", [])


def test_derive_approximate_sum_allows_single_input() -> None:
    # A single same-scope input still carries the derived/labelling contract.
    total = derive_approximate_sum("okc", [_Claim(90, "agency_active", CITY_ACTIVE)])
    assert total.value == 90 and total.scope is not None

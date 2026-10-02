# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.3 legacy-name dry-run impact report (SIG-TRUST-004, ADR-122).

``partner-name-audit`` reports every legacy ``sig.org.name`` key, its asserting
sources/predicates, and the ``sig.org.name_scoped`` keys it would decompose
into — the evidence a recorded disposition needs. Read-only; nothing is
re-keyed.
"""

from __future__ import annotations

from resolution.partner_identity import scoped_name_key
from resolution.partner_name_audit import (
    LegacyNameImpact,
    _impacts_from_rows,
    proposed_scoped_keys,
)


def test_proposed_scoped_keys_one_per_source_deterministic() -> None:
    name = "washington state department of transportation"
    keys = proposed_scoped_keys(name, ["usaspending", "govspend", "govspend"])
    assert keys == [
        "src:govspend|" + name,
        "src:usaspending|" + name,
    ]
    # Same construction as live mints — the audit proposes what P32.3 would key.
    assert keys[0] == scoped_name_key(name, scope="govspend")[0]


def test_impacts_group_provenance_per_legacy_key() -> None:
    rows = [
        {
            "name_key": "city of example falls",
            "entity_id": "e1",
            "label": "City of Example Falls",
            "source_id": "govspend",
            "predicate_id": "buyer",
        },
        {
            "name_key": "washington state department of transportation",
            "entity_id": "e2",
            "label": "Washington State Department of Transportation",
            "source_id": "usaspending",
            "predicate_id": "recipient",
        },
        {
            "name_key": "washington state department of transportation",
            "entity_id": "e2",
            "label": "Washington State Department of Transportation",
            "source_id": "govspend",
            "predicate_id": "buyer",
        },
        {
            "name_key": "washington state department of transportation",
            "entity_id": "e2",
            "label": "Washington State Department of Transportation",
            "source_id": "alpr_accountability_atlas",
            "predicate_id": "event_organizations",
            "extra": None,
        },
    ]
    impacts = _impacts_from_rows(rows)
    assert [i.name_key for i in impacts] == sorted(i.name_key for i in impacts)
    wsdot = next(i for i in impacts if i.entity_id == "e2")
    assert wsdot.sources == ("alpr_accountability_atlas", "govspend", "usaspending")
    assert wsdot.predicates == ("buyer", "event_organizations", "recipient")
    # Three asserting sources → the global key decomposes into three
    # unmerged candidates — exactly the cross-source auto-union P32.3 removes.
    assert wsdot.split_count == 3
    single = impacts[0]
    assert single.split_count == 1  # one source collapses to one key
    d = wsdot.as_dict()
    assert d["split_count"] == 3 and len(d["proposed_scoped_keys"]) == 3


def test_split_count_is_at_least_one() -> None:
    # A legacy key with no surviving provenance rows still reports itself.
    impact = LegacyNameImpact(name_key="orphan", entity_id="e9", label=None)
    assert impact.split_count == 1
    assert impact.as_dict()["proposed_scoped_keys"] == []

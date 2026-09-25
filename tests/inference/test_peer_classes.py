# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The declared §32.1 peer classes (P31.9 / DEEPEN.5, ADR-115).

Pins the shipped ``inference/data/peer_classes.toml`` declaration — the rule
that makes the negative space *proportionate* on the real spine (a traffic
camera is compared with its acquisition class, never with legislation
subjects). The DB-side scoping is proven in
``tests/db/test_coverage_materialize.py``; here we pin the declaration's own
invariants:

* the file loads and validates (fail-loud on a malformed declaration);
* every declared class is ``(entity_type, connectors) → tracked`` with all
  fields non-empty and no connector claimed by two classes of one entity type;
* every tracked predicate exists in the ontology-owned predicate registry
  (a tracked name that resolves to nothing is a typo, not a gap);
* per-claim match/marker bookkeeping predicates are never tracked — their
  absence is an extraction outcome, not a research gap.
"""

from __future__ import annotations

import pytest
from inference.peer_classes import PeerClass, _parse, load_peer_classes
from reconcile.weight import predicate_registry

#: Per-claim match/marker bookkeeping — declared NEVER negative space
#: (ADR-115): absence is an extraction outcome, not an unresearched attribute.
BOOKKEEPING_PREDICATES = {
    "matched_keyword",
    "content_term",
    "bill_matched_keyword",
    "unmapped_surveillance_tag",
}


def test_the_shipped_declaration_loads_and_is_well_formed() -> None:
    classes = load_peer_classes()
    assert classes
    for pc in classes:
        assert pc.entity_type
        assert pc.connectors
        assert pc.tracked
        # membership is unambiguous: one (entity_type, connector) → one class
        for connector in pc.connectors:
            others = [
                c
                for c in classes
                if c is not pc and connector in c.connectors and c.entity_type == pc.entity_type
            ]
            assert not others, f"{connector} declared by two {pc.entity_type} classes"


def test_every_tracked_predicate_is_a_registered_predicate() -> None:
    """A tracked name that is not in the predicate registry is a typo, not a gap."""
    known = set(predicate_registry())
    for pc in load_peer_classes():
        for pred in pc.tracked:
            assert pred in known, f"{pred} (class {pc.connectors}) is not in the registry"


def test_bookkeeping_predicates_are_never_tracked() -> None:
    for pc in load_peer_classes():
        assert not (set(pc.tracked) & BOOKKEEPING_PREDICATES), (
            f"{pc.connectors} tracks a bookkeeping predicate (ADR-115)"
        )


def test_the_measured_hosted_connectors_are_all_declared() -> None:
    """Every connector observed producing claims on the hosted spine
    (measured 2026-09-25, ADR-115) has a declared class — no subject falls
    outside every declaration on the spine this declaration was built for."""
    measured = {
        "accountability",
        "atlas",
        "coarse_international",
        "data_driven",
        "dot_511",
        "flock_portal",
        "france-seed",
        "france_belgium_procurement",
        "france_belgium_records",
        "government_mandated_disclosure",
        "ok_statute",
        "okc-seed",
        "okcpd_policy",
        "osm",
        "pathways",
        "procurement",
        "records",
        "state_statute_seed",
    }
    declared = {c for pc in load_peer_classes() for c in pc.connectors}
    assert measured <= declared


def test_parse_refuses_a_malformed_declaration() -> None:
    with pytest.raises(ValueError, match="version"):
        _parse({})
    with pytest.raises(ValueError, match="no entity_type"):
        _parse({"version": "1", "class": [{"connectors": ["x"], "tracked": ["p"]}]})
    with pytest.raises(ValueError, match="no connectors"):
        _parse({"version": "1", "class": [{"entity_type": "deployment"}]})
    with pytest.raises(ValueError, match="no tracked"):
        _parse(
            {
                "version": "1",
                "class": [{"entity_type": "deployment", "connectors": ["x"]}],
            }
        )
    with pytest.raises(ValueError, match="twice"):
        _parse(
            {
                "version": "1",
                "class": [
                    {"entity_type": "deployment", "connectors": ["x"], "tracked": ["p", "p"]}
                ],
            }
        )
    with pytest.raises(ValueError, match="unambiguous"):
        _parse(
            {
                "version": "1",
                "class": [
                    {"entity_type": "deployment", "connectors": ["x"], "tracked": ["p"]},
                    {"entity_type": "deployment", "connectors": ["x"], "tracked": ["q"]},
                ],
            }
        )


def test_read_negative_space_scopes_to_declared_classes() -> None:
    """The scoping rule end-to-end over a canned result set (the SQL only feeds
    subject → (entity_type, connectors, claimed predicates); the real-PG proof
    is tests/db/test_coverage_materialize.py)."""
    from inference.materialize import read_negative_space

    class _Conn:
        def execute(self, *_args, **_kwargs):
            class _Res:
                def fetchall(self):
                    # s1 is a class-A member missing 'b'; s2 is multi-connector
                    # (classes A + B → union {'a','b'} ∪ {'b','c'}); s3 is claimed
                    # only by an undeclared connector; s4 (organization type)
                    # has no class at all.
                    return [
                        ("s1", "deployment", "cA", "a"),
                        ("s2", "deployment", "cA", "a"),
                        ("s2", "deployment", "cB", "b"),
                        ("s3", "deployment", "cUndeclared", "a"),
                        ("s4", "organization", "cA", "a"),
                    ]

            return _Res()

    classes = (
        PeerClass(entity_type="deployment", connectors=("cA",), tracked=("a", "b")),
        PeerClass(entity_type="deployment", connectors=("cB",), tracked=("b", "c")),
    )
    records = read_negative_space(_Conn(), peer_classes=classes)
    got = {(r.subject_id, r.predicate_id) for r in records}
    assert got == {("s1", "b"), ("s2", "c")}  # union rule; no s3/s4 rows
    assert all(r.absence_kind == "not_researched" for r in records)
    assert all(r.subject_class == "deployment" for r in records)

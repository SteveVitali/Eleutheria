# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.25 (R11-L3-CP4, SIG-CONF-014) — declared source lineage.

The registry's ``[sources.<id>.lineage]`` blocks are additive metadata:
absent reads ``undeclared`` (never "independent"), declared kinds require
documentary evidence, upstream references resolve to registry ids only, and
``independence_class`` resolves transitively so a mirror is one voice with
its original. Lineage has no effect on ``assert_loadable`` — it is
corroboration metadata, not an ingestion-permission input.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.registry import (
    UNCLASSIFIED,
    CompactStatus,
    CustodyPosture,
    LineageKind,
    RobotsPolicy,
    SourceKind,
    SourceLineage,
    SourceRecord,
    _lineage_from_row,
    _record_from_row,
    get,
    registry,
    resolve_independence_class,
)
from db.lineage import namespaces, valid_namespace_token
from policy.rights import RightsRecord


def _rights(source_id: str) -> RightsRecord:
    return RightsRecord(
        source_id=source_id,
        spdx="CC0-1.0",
        attribution="",
        redistributable=True,
        derivative_permitted=True,
        terms_url="",
        retrieval_date=date(2026, 1, 1),
    )


def _record(
    source_id: str,
    *,
    lineage: SourceLineage | None = None,
    ingestion_permitted: bool = False,
    compact_status: CompactStatus = CompactStatus.NOT_CONTACTED,
    custody_posture: CustodyPosture = CustodyPosture.LINK,
) -> SourceRecord:
    return SourceRecord(
        id=source_id,
        name=source_id,
        source_kind=SourceKind.COMMERCIAL,
        homepage_url="https://example.invalid",
        default_tier="R5",
        custody_posture=custody_posture,
        compact_status=compact_status,
        robots_policy=RobotsPolicy.HONOR,
        rights=_rights(source_id),
        ingestion_permitted=ingestion_permitted,
        lineage=lineage if lineage is not None else SourceLineage(),
    )


# --- parsing: additive fields, honest defaults ------------------------------


def test_absent_lineage_block_is_explicitly_undeclared() -> None:
    """A row with no [lineage] block parses to the undeclared default —
    additive fields only; undeclared is a recorded state, never independent."""
    lin = _lineage_from_row("src_x", {})
    assert lin == SourceLineage()
    assert lin.kind == LineageKind.UNDECLARED
    assert lin.id_namespace == "" and lin.independence_class == ""


def test_committed_registry_loads_with_lineage_blocks() -> None:
    """The committed sources.toml parses: the three declared rows carry their
    kinds and every other row stays undeclared."""
    records = registry()
    declared = [r for r in records.values() if r.lineage.kind != LineageKind.UNDECLARED]
    assert {r.id for r in declared} == {
        "osm_overpass",
        "deflock_repo",
        "camreg_osm_surveillance",
    }
    assert records["osm_overpass"].lineage.id_namespace == "osm.element"
    assert records["deflock_repo"].lineage.id_namespace == "deflock.node"
    assert records["camreg_osm_surveillance"].lineage.id_namespace == "src:camreg_osm_surveillance"
    # Every other source is undeclared — the honest default, never independent.
    undeclared = [r for r in records.values() if r.lineage.kind == LineageKind.UNDECLARED]
    assert len(undeclared) == len(records) - 3


def test_lineage_block_must_be_a_table() -> None:
    with pytest.raises(ValueError, match="lineage must be a table"):
        _lineage_from_row("src_x", {"lineage": "primary"})


def test_lineage_kind_is_a_closed_vocabulary() -> None:
    with pytest.raises(ValueError):
        _lineage_from_row("src_x", {"lineage": {"kind": "forked", "evidence": "x"}})


def test_derived_from_accepts_and_normalizes_a_list() -> None:
    lin = _lineage_from_row(
        "src_x",
        {"lineage": {"kind": "derived", "derived_from": ["a", "b"], "evidence": "x"}},
    )
    assert lin.derived_from == ("a", "b")


# --- declaration validation: a lineage declaration is a claim ---------------


def test_declared_kind_requires_evidence() -> None:
    """kind != undeclared with no evidence fails closed — a declaration names
    its documentary basis (§3.1)."""
    with pytest.raises(ValueError, match="no lineage.evidence"):
        _record("src_x", lineage=SourceLineage(kind=LineageKind.PRIMARY))


def test_undeclared_needs_no_evidence() -> None:
    _record("src_x", lineage=SourceLineage(kind=LineageKind.UNDECLARED))


def test_a_source_is_never_its_own_lineage() -> None:
    with pytest.raises(ValueError, match="its own lineage"):
        _record(
            "src_x",
            lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_x", evidence="x"),
        )
    with pytest.raises(ValueError, match="its own lineage"):
        _record(
            "src_x",
            lineage=SourceLineage(kind=LineageKind.DERIVED, derived_from=("src_x",), evidence="x"),
        )


def test_a_mirror_names_what_it_copies() -> None:
    with pytest.raises(ValueError, match="a mirror names what it copies"):
        _record(
            "src_x",
            lineage=SourceLineage(kind=LineageKind.MIRROR, evidence="x"),
        )
    # either a registry id or a documentary origin satisfies the requirement
    _record(
        "src_x",
        lineage=SourceLineage(kind=LineageKind.MIRROR, origin="upstream dataset", evidence="x"),
    )


def test_independence_class_is_a_closed_vocabulary() -> None:
    with pytest.raises(ValueError, match="vocabulary"):
        _record(
            "src_x",
            lineage=SourceLineage(
                kind=LineageKind.PRIMARY,
                independence_class="independent",
                evidence="x",
            ),
        )
    for good in ("unclassified", "src:src_x", "ext:shared-upstream"):
        _record(
            "src_x",
            lineage=SourceLineage(
                kind=LineageKind.PRIMARY,
                independence_class=good,
                evidence="x",
            ),
        )


def test_dangling_lineage_upstream_fails_the_registry_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mirror_of/derived_from name REGISTRY ids — a typo'd reference fails the
    whole load rather than resolving `unclassified` for a misspelling."""
    import connectors.registry as reg

    table = {
        "sources": {
            "src_a": {
                "name": "a",
                "source_kind": "commercial",
                "rights": {"spdx": "CC0-1.0", "redistributable": True},
            },
            "src_b": {
                "name": "b",
                "source_kind": "commercial",
                "rights": {"spdx": "CC0-1.0", "redistributable": True},
                "lineage": {
                    "kind": "mirror",
                    "mirror_of": "src_typo",
                    "evidence": "x",
                },
            },
        }
    }
    monkeypatch.setattr(reg, "load_table", lambda name: table)
    with pytest.raises(ValueError, match="not a registered source"):
        reg.registry.__wrapped__()


def test_unknown_id_namespace_fails_the_registry_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A declared id_namespace must be in db/data/id_namespaces.toml (or
    src:<source-id>) — an undeclared token fails closed, never silently
    namespaced."""
    import connectors.registry as reg

    table = {
        "sources": {
            "src_a": {
                "name": "a",
                "source_kind": "commercial",
                "rights": {"spdx": "CC0-1.0", "redistributable": True},
                "lineage": {
                    "kind": "primary",
                    "id_namespace": "made_up.space",
                    "evidence": "x",
                },
            },
        }
    }
    monkeypatch.setattr(reg, "load_table", lambda name: table)
    with pytest.raises(ValueError, match="not a declared namespace"):
        reg.registry.__wrapped__()


# --- independence-class resolution: declared, transitive, never guessed ------


def _resolve(records: list[SourceRecord], target: str) -> str:
    by_id = {r.id: r for r in records}
    return resolve_independence_class(by_id[target], by_id)


def test_undeclared_resolves_unclassified_never_independent() -> None:
    a = _record("src_a")
    assert _resolve([a], "src_a") == UNCLASSIFIED


def test_primary_root_is_its_own_class() -> None:
    a = _record("src_a", lineage=SourceLineage(kind=LineageKind.PRIMARY, evidence="x"))
    assert _resolve([a], "src_a") == "src:src_a"


def test_a_mirror_collapses_onto_its_originals_class() -> None:
    """A mirror agrees with its original as ONE voice — the mirror resolves to
    the upstream's class, never a second independent one."""
    root = _record("src_root", lineage=SourceLineage(kind=LineageKind.PRIMARY, evidence="x"))
    mirror = _record(
        "src_mirror",
        lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_root", evidence="x"),
    )
    assert _resolve([root, mirror], "src_mirror") == "src:src_root"


def test_mirror_of_mirror_resolves_transitively() -> None:
    root = _record(
        "src_root",
        lineage=SourceLineage(
            kind=LineageKind.PRIMARY,
            independence_class="ext:upstream-x",
            evidence="x",
        ),
    )
    m1 = _record(
        "src_m1",
        lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_root", evidence="x"),
    )
    m2 = _record(
        "src_m2",
        lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_m1", evidence="x"),
    )
    assert _resolve([root, m1, m2], "src_m2") == "ext:upstream-x"


def test_derived_single_root_inherits_the_roots_class() -> None:
    root = _record("src_root", lineage=SourceLineage(kind=LineageKind.PRIMARY, evidence="x"))
    derived = _record(
        "src_d",
        lineage=SourceLineage(kind=LineageKind.DERIVED, derived_from=("src_root",), evidence="x"),
    )
    assert _resolve([root, derived], "src_d") == "src:src_root"


def test_derived_multi_root_is_unclassified() -> None:
    """A synthesis of several independent upstreams cannot honestly corroborate
    any single one — multi-root derivation collapses to unclassified (this is
    the committed camreg_osm_surveillance shape)."""
    r1 = _record("src_r1", lineage=SourceLineage(kind=LineageKind.PRIMARY, evidence="x"))
    r2 = _record("src_r2", lineage=SourceLineage(kind=LineageKind.PRIMARY, evidence="x"))
    syn = _record(
        "src_syn",
        lineage=SourceLineage(
            kind=LineageKind.DERIVED,
            derived_from=("src_r1", "src_r2"),
            evidence="x",
        ),
    )
    assert _resolve([r1, r2, syn], "src_syn") == UNCLASSIFIED


def test_explicit_independence_class_override_wins() -> None:
    """Two sources sharing one unregistered upstream declare the same ext:
    token — corroboration still counts them as one voice."""
    a = _record(
        "src_a",
        lineage=SourceLineage(
            kind=LineageKind.SYNDICATED,
            independence_class="ext:shared-feed",
            evidence="x",
        ),
    )
    b = _record(
        "src_b",
        lineage=SourceLineage(
            kind=LineageKind.SYNDICATED,
            independence_class="ext:shared-feed",
            evidence="x",
        ),
    )
    assert _resolve([a, b], "src_a") == _resolve([a, b], "src_b") == "ext:shared-feed"


def test_a_declared_cycle_is_unclassified_never_a_class() -> None:
    a = _record(
        "src_a",
        lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_b", evidence="x"),
    )
    b = _record(
        "src_b",
        lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_a", evidence="x"),
    )
    assert _resolve([a, b], "src_a") == UNCLASSIFIED


def test_mirror_of_an_unregistered_upstream_is_unclassified() -> None:
    """mirror_of pointing outside the records map degrades to unclassified —
    the resolver never guesses a class for an absent upstream."""
    m = _record(
        "src_m",
        lineage=SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_absent", evidence="x"),
    )
    assert _resolve([m], "src_m") == UNCLASSIFIED


# --- committed declarations resolve as recorded ----------------------------


def test_committed_declarations_resolve_the_recorded_classes() -> None:
    records = registry()
    assert resolve_independence_class(get("osm_overpass"), records) == "src:osm_overpass"
    assert resolve_independence_class(get("deflock_repo"), records) == "src:deflock_repo"
    # Two independent upstream roots → the synthesis is unclassified.
    assert resolve_independence_class(get("camreg_osm_surveillance"), records) == UNCLASSIFIED


# --- the namespace vocabulary ----------------------------------------------


def test_namespace_vocabulary_membership() -> None:
    assert {"osm.element", "deflock.node", "dot_511"} <= set(namespaces())


def test_valid_namespace_tokens() -> None:
    assert valid_namespace_token("undeclared")
    assert valid_namespace_token("osm.element")
    assert valid_namespace_token("src:camreg_osm_surveillance")
    assert not valid_namespace_token("")
    assert not valid_namespace_token("made_up.space")
    assert not valid_namespace_token("src:")  # an empty private name
    assert not valid_namespace_token("src:a:b")  # a private name is one token


# --- lineage is never an ingestion-permission input -------------------------


def test_lineage_has_no_effect_on_assert_loadable() -> None:
    """gotcha 4 / the ticket's invariant: the loader gate reads permission
    fields only — declared lineage neither opens nor closes ingestion."""
    for lineage in (
        SourceLineage(),
        SourceLineage(kind=LineageKind.MIRROR, mirror_of="src_root", evidence="x"),
    ):
        unpermitted = _record("src_x", lineage=lineage)
        with pytest.raises(IngestionNotPermitted):
            assert_loadable(unpermitted)
        permitted = _record(
            "src_x",
            lineage=lineage,
            ingestion_permitted=True,
            compact_status=CompactStatus.PERMISSION_GRANTED,
            custody_posture=CustodyPosture.MIRROR,
        )
        assert assert_loadable(permitted) is permitted


def test_row_without_declarations_parses_and_loads() -> None:
    """The ticket's fixture AC: a registry row with no lineage block parses to
    undeclared and stays a valid SourceRecord (additive fields only)."""
    row: dict[str, Any] = {
        "name": "x",
        "source_kind": "commercial",
        "rights": {"spdx": "CC0-1.0", "redistributable": True},
    }
    record = _record_from_row("src_x", row)
    assert record.lineage == SourceLineage()
    assert record.lineage.kind == LineageKind.UNDECLARED

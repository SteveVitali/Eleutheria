# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""OSM-origin camera-site records in the camera-site ER pool (P37.1 / ACQ-17).

A shadow-diff style run (pure ``resolve_camera_sites``, never a live or
production resolution) over two record sets:

* **OSM-origin records** — the subjects the P37.1 connector emits
  (``osm:<type>/<id>``, ``camera_external_ref`` in the declared
  ``osm.element`` namespace, ``camera_jurisdiction=unresolved``);
* **republished registry records** — an ArcGIS camera-registry source whose
  rows carry the OSM element ids verbatim, declared ``derived`` inside the
  same lineage class as ``osm_overpass`` (P35.25 / SIG-CONF-014).

The contract: the republish pairs satisfy the derivation-collapse tiers —
shared ``osm.element`` refs collapse at C1, position-matched copies at C2 —
so **≥95% of the tier ≤3 candidates merge** (I8 §4.3's republish-merge
requirement), a soft-conflicted copy is routed to review rather than
auto-collapsed, and an undeclared-namespace ref match is never
shared-upstream evidence.
"""

from __future__ import annotations

import math

from resolution.camera_sites import (
    CameraRecord,
    CameraSiteRules,
    LineageDeclaration,
    resolve_camera_sites,
)

RULES = CameraSiteRules.from_data()
LAT0, LON0 = 35.4676, -97.5164
M_PER_DEG_LAT = 111_195.0
OSM_SOURCE = "osm_overpass"
REPUB_SOURCE = "camreg_arcgis_ok"
LINEAGE = "L.osm_republish"


def _at(north_m: float, east_m: float) -> tuple[float, float]:
    lat = LAT0 + north_m / M_PER_DEG_LAT
    lon = LON0 + east_m / (M_PER_DEG_LAT * math.cos(math.radians(LAT0)))
    return lat, lon


def _osm_rec(i: int, north_m: float, **kw) -> CameraRecord:
    """An OSM-origin record as the P37.1 connector emits it."""
    lat, lon = _at(north_m, 0.0)
    return CameraRecord(
        subject_id=f"osm:node/{10_000 + i}",
        source_id=OSM_SOURCE,
        latitude=lat,
        longitude=lon,
        external_ref=f"osm:node/{10_000 + i}",
        id_namespace="osm.element",
        jurisdiction="unresolved",
        technology="alpr-fixed",
        declared_technologies=("alpr-fixed",),
        **kw,
    )


def _repub_rec(i: int, north_m: float, *, ref: str | None, **kw) -> CameraRecord:
    """A republished ArcGIS/registry row carrying the OSM element id."""
    lat, lon = _at(north_m, 0.0)
    return CameraRecord(
        subject_id=f"camreg:{i}",
        source_id=REPUB_SOURCE,
        latitude=lat,
        longitude=lon,
        external_ref=ref,
        id_namespace="osm.element" if ref else "undeclared",
        technology="alpr-fixed",
        declared_technologies=("alpr-fixed",),
        **kw,
    )


def _declared() -> tuple[dict[str, str], dict[str, LineageDeclaration]]:
    """The declared copy lineage: osm_overpass is the lineage's primary member,
    the ArcGIS republisher declares itself ``derived`` of the same upstream."""
    declared = {OSM_SOURCE: LINEAGE, REPUB_SOURCE: LINEAGE}
    details = {
        OSM_SOURCE: LineageDeclaration(
            independence_class=LINEAGE, kind="primary", evidence="lineage root"
        ),
        REPUB_SOURCE: LineageDeclaration(
            independence_class=LINEAGE,
            kind="derived",
            evidence="the registry republishes OSM element ids verbatim",
        ),
    }
    return declared, details


def _fixture() -> tuple[list[CameraRecord], dict[str, str], dict[str, LineageDeclaration]]:
    """40 republish pairs spaced ~200m apart along a meridian strip:

    * pairs 0–31  — shared ``osm.element`` ref + coincident point → C1 collapse;
    * pairs 32–38 — coincident point, no shared ref → C2 position-matched copy;
    * pair 39     — shared ref + coincident point but a recorded direction
      conflict (270° vs 90°) → routed to review, never auto-collapsed.
    """
    declared, details = _declared()
    records: list[CameraRecord] = []
    for i in range(40):
        records.append(_osm_rec(i, i * 200.0))
        ref = f"osm:node/{10_000 + i}" if i < 32 or i == 39 else None
        kw: dict[str, object] = {}
        if i == 39:
            records[-1] = _osm_rec(i, i * 200.0, direction="270")
            kw["direction"] = "90"
        # The republisher's point is ~0.2m off the OSM element — inside both
        # coincident_m and copy_tolerance_m.
        records.append(_repub_rec(i, i * 200.0 + 0.2, ref=ref, **kw))
    return records, declared, details


def test_osm_republish_merges_at_or_above_95_percent_of_tier_le_3() -> None:
    records, declared, details = _fixture()
    res = resolve_camera_sites(
        records,
        gold=None,
        threshold=0.98,
        rules=RULES,
        declared_lineages=declared,
        declared_details=details,
    )
    tier_le_3 = [d for d in res.decisions if d.assessment.tier <= 3]
    assert len(tier_le_3) == 40, f"expected 40 tier≤3 candidates, got {len(tier_le_3)}"
    merged = [d for d in tier_le_3 if d.disposition == "auto_write"]
    share = len(merged) / len(tier_le_3)
    assert share >= 0.95, (
        f"the republish merge requirement failed: {len(merged)}/{len(tier_le_3)} "
        f"({share:.1%}) of tier≤3 candidates merged"
    )
    # The merged pairs land in one resolved site each.
    for d in merged:
        assert res.clusters[d.left] == res.clusters[d.right]
        assert d.relation == "derived_from"
    # The derivation census re-verifies every applied collapse (GQ-23).
    assert res.derivation_census is not None
    assert res.derivation_census.checked == len(merged)
    assert res.derivation_census.failures == ()


def test_shared_osm_element_refs_collapse_at_c1() -> None:
    records, declared, details = _fixture()
    res = resolve_camera_sites(
        records,
        gold=None,
        threshold=0.98,
        rules=RULES,
        declared_lineages=declared,
        declared_details=details,
    )
    c1 = [
        d
        for d in res.decisions
        if d.assessment.tier == 1 and d.assessment.evidence.get("shared_upstream_ref")
    ]
    # 33 shared-ref pairs (0–31 plus pair 39): 32 clean + the soft-conflicted copy.
    assert len(c1) == 33
    clean = [d for d in c1 if "camreg:39" not in (d.left, d.right)]
    assert len(clean) == 32
    for d in clean:
        assert d.disposition == "auto_write"
        assert d.assessment.evidence["rule"] == "C1:namespaced_copy"
        assert d.assessment.evidence["id_namespaces"] == ["osm.element", "osm.element"]


def test_position_matched_copies_collapse_at_c2() -> None:
    records, declared, details = _fixture()
    res = resolve_camera_sites(
        records,
        gold=None,
        threshold=0.98,
        rules=RULES,
        declared_lineages=declared,
        declared_details=details,
    )
    c2 = [d for d in res.decisions if d.assessment.tier == 2]
    assert len(c2) == 7
    for d in c2:
        assert d.disposition == "auto_write" and d.relation == "derived_from"
        assert d.assessment.evidence["copy_checks"]["documented_lineage"]


def test_a_soft_conflicted_copy_is_reviewed_never_collapsed() -> None:
    records, declared, details = _fixture()
    res = resolve_camera_sites(
        records,
        gold=None,
        threshold=0.98,
        rules=RULES,
        declared_lineages=declared,
        declared_details=details,
    )
    pair = next(d for d in res.decisions if {d.left, d.right} == {"osm:node/10039", "camreg:39"})
    # Shared ref + coincident + copy lineage would be C1 — but the direction
    # conflict is a soft conflict, and a soft conflict is never auto-written.
    assert pair.disposition == "proposed"
    assert res.clusters[pair.left] != res.clusters[pair.right]


def test_an_undeclared_namespace_ref_match_is_never_shared_evidence() -> None:
    """P35.25 NEW-1: the same ref string with no declared namespace is a
    coincidence — the pair never collapses on it (and at 20m it is only a
    proximate candidate, review-only)."""
    declared, details = _declared()
    lat, lon = _at(0.0, 0.0)
    lat2, lon2 = _at(20.0, 0.0)
    osm = CameraRecord(
        subject_id="osm:node/10000",
        source_id=OSM_SOURCE,
        latitude=lat,
        longitude=lon,
        external_ref="osm:node/10000",
        id_namespace="undeclared",
        jurisdiction="unresolved",
    )
    repub = CameraRecord(
        subject_id="camreg:0",
        source_id=REPUB_SOURCE,
        latitude=lat2,
        longitude=lon2,
        external_ref="osm:node/10000",
        id_namespace="undeclared",
    )
    res = resolve_camera_sites(
        [osm, repub],
        gold=None,
        threshold=0.98,
        rules=RULES,
        declared_lineages=declared,
        declared_details=details,
    )
    (pair,) = res.decisions
    assert pair.disposition != "auto_write"
    assert pair.assessment.evidence["shared_upstream_ref"] is None
    assert res.clusters[pair.left] != res.clusters[pair.right]


def test_same_source_osm_records_never_pair() -> None:
    """Constraint (a): two records of one source are never a candidate pair —
    even two coincident OSM elements stay distinct."""
    declared, details = _declared()
    recs = [_osm_rec(0, 0.0), _osm_rec(1, 0.1)]
    res = resolve_camera_sites(
        recs,
        gold=None,
        threshold=0.98,
        rules=RULES,
        declared_lineages=declared,
        declared_details=details,
    )
    assert not [
        d for d in res.decisions if {d.left, d.right} == {"osm:node/10000", "osm:node/10001"}
    ]
    assert res.clusters["osm:node/10000"] != res.clusters["osm:node/10001"]

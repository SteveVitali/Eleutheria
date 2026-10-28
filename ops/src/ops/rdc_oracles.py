# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.23 / SIG-CONF-008: the corpus oracles — pipeline-INDEPENDENT answers.

Every function here reads raw slice bytes directly (stdlib ``json``/``csv``/
``zipfile`` only) and computes the expected facts the corpus check compares the
pipeline output against. Nothing in this module imports ``connectors``,
``resolution``, ``parsing`` or ``db``: an oracle that shared code with the
pipeline could share its bugs, so a regression on either side is caught by the
disagreement, never hidden by a common implementation.

Each oracle returns a JSON-serialisable fact dict. The committed
``sig.rdc-snapshot/1`` digests over these docs; a slice whose oracle cannot
parse its bytes is corrupt and fails the corpus check (never skipped).
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections.abc import Callable
from typing import Any

# --- helpers ---------------------------------------------------------------


def _norm_name(s: str | None) -> str:
    """Lower-cased alphanumeric name key — the same-shape normalisation the
    two-state-name archetype counts, written out here (not imported)."""
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _require(cond: object, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


# --- ArcGIS FeatureServer/MapServer query pages -----------------------------


def arcgis_camera_facts(
    pages: list[bytes], *, object_id_field: str, extent: tuple[float, ...] | None = None
) -> dict[str, Any]:
    """Expected facts for an ``arcgis_pages`` slice: the raw feature census.

    Reads each page's ``features[]`` directly — never the connector's typed
    extraction — and counts what the pipeline must reproduce:

    * ``feature_count`` — every upstream feature becomes one record;
    * ``distinct_object_ids`` / ``collided_object_ids`` — the declared key
      field's value census (a collision is a recorded archetype, IL-DOT-style);
    * ``features_with_geometry`` / ``null_island`` — how many carry a point,
      and how many sit on (0,0);
    * ``out_of_extent`` — points outside the declared detector extent
      (axis-swap / wrong-jurisdiction signature);
    * ``co_located_groups`` — feature count sharing one exact (x, y) point
      with at least one sibling (the multi-view signature);
    * ``same_id_distinct_points`` — key values attached to >1 distinct point.
    """
    count = 0
    with_geom = 0
    null_island = 0
    out_of_extent = 0
    ids: dict[str, int] = {}
    id_points: dict[str, set[str]] = {}
    points: dict[str, int] = {}
    for raw in pages:
        doc = json.loads(raw.decode("utf-8"))
        _require("features" in doc, "arcgis page carries no features[] member")
        for feat in doc["features"]:
            count += 1
            attrs = feat.get("attributes") or {}
            oid = attrs.get(object_id_field)
            if oid is not None:
                key = str(oid)
                ids[key] = ids.get(key, 0) + 1
            geom = feat.get("geometry") or {}
            x, y = geom.get("x"), geom.get("y")
            if x is None or y is None:
                continue
            with_geom += 1
            pt = f"{x},{y}"
            points[pt] = points.get(pt, 0) + 1
            if oid is not None:
                id_points.setdefault(str(oid), set()).add(pt)
            if x == 0 and y == 0:
                null_island += 1
            if extent is not None:
                west, south, east, north = extent
                if not (west <= x <= east and south <= y <= north):
                    out_of_extent += 1
    collided = sorted(k for k, n in ids.items() if n > 1)
    return {
        "oracle": "arcgis_camera_facts",
        "feature_count": count,
        "features_with_geometry": with_geom,
        "distinct_object_ids": len(ids),
        "collided_object_ids": collided,
        "collision_count": len(collided),
        "null_island": null_island,
        "out_of_extent": out_of_extent,
        "co_located_groups": sum(1 for n in points.values() if n > 1),
        "co_located_features": sum(n for n in points.values() if n > 1),
        "same_id_distinct_points": sum(1 for pts in id_points.values() if len(pts) > 1),
    }


# --- Atlas of Surveillance CSV ----------------------------------------------


def atlas_multistate_facts(data: bytes) -> dict[str, Any]:
    """Expected facts for the Atlas excerpt: the multi-state agency-name census.

    Groups rows by the normalised ``Agency`` value and counts names asserted
    for agencies in two or more distinct ``State`` values — the mechanically
    known "possibly the same agency" population the same-name archetype names.
    """
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
    _require(rows, "atlas excerpt carries no rows")
    states_by_name: dict[str, set[str]] = {}
    for r in rows:
        states_by_name.setdefault(_norm_name(r.get("Agency")), set()).add(
            (r.get("State") or "").strip()
        )
    multi = sorted(n for n, st in states_by_name.items() if len(st) >= 2)
    return {
        "oracle": "atlas_multistate_facts",
        "row_count": len(rows),
        "distinct_names": len(states_by_name),
        "multistate_names": multi,
        "multistate_name_count": len(multi),
        "multistate_rows": sum(1 for r in rows if _norm_name(r.get("Agency")) in set(multi)),
    }


# --- USAspending spending_by_award -------------------------------------------


def usaspending_facts(data: bytes, *, term_classes: dict[str, list[str]]) -> dict[str, Any]:
    """Expected facts for the USAspending sub-award page.

    Counts results and, per declared term class, the rows whose
    ``Sub-Award Description`` mentions at least one term verbatim
    (case-folded). The pipeline's topical-relevance routing must reproduce
    the same term-hit census — an independent count over the raw page.
    """
    doc = json.loads(data.decode("utf-8"))
    results = doc.get("results")
    _require(isinstance(results, list), "usaspending page carries no results[] list")
    counts: dict[str, int] = {}
    hits: dict[str, list[str]] = {}
    for cls, terms in term_classes.items():
        n = 0
        ids: list[str] = []
        for r in results:
            desc = str(r.get("Sub-Award Description") or "").lower()
            if any(t.lower() in desc for t in terms):
                n += 1
                if r.get("Sub-Award ID") is not None:
                    ids.append(str(r["Sub-Award ID"]))
        counts[cls] = n
        hits[cls] = sorted(ids)
    return {
        "oracle": "usaspending_facts",
        "result_count": len(results),
        "term_hits": counts,
        "term_hit_ids": hits,
        "page_metadata": doc.get("page_metadata") or {},
    }


# --- EFF Data Driven zip (restricted lane) -----------------------------------


def eff_release_facts(data: bytes) -> dict[str, Any]:
    """Expected facts for the EFF/MuckRock 2016–17 release zip.

    Opens the zip in memory (never unpacking to disk), reads the aggregate
    CSV and counts rows, plus exact-duplicate (Agency, State, Type, …) tuples
    — the temporal/double-claim signature the archetype records.
    """
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
        csvs = [n for n in names if n.lower().endswith(".csv")]
        _require(csvs, "eff release zip carries no .csv member")
        facts: dict[str, Any] = {
            "oracle": "eff_release_facts",
            "zip_members": sorted(names),
            "csv_members": sorted(csvs),
            "tables": {},
        }
        for name in sorted(csvs):
            rows = list(csv.DictReader(io.StringIO(zf.read(name).decode("utf-8-sig"))))
            key_fields = [
                f for f in ("Agency", "State", "Type of Technology") if rows and f in rows[0]
            ]
            tuples: dict[tuple[str, ...], int] = {}
            for r in rows:
                t = tuple((r.get(f) or "").strip() for f in key_fields)
                tuples[t] = tuples.get(t, 0) + 1
            dupes = sum(n - 1 for n in tuples.values() if n > 1)
            facts["tables"][name] = {
                "row_count": len(rows),
                "fields": list(rows[0].keys()) if rows else [],
                "key_fields": key_fields,
                "exact_repeat_rows": dupes,
            }
        return facts


# --- Legistar tenant matters lists (restricted lane) -------------------------


def legistar_tenant_facts(members: dict[str, bytes]) -> dict[str, Any]:
    """Expected facts for the Legistar tenant-collision pair.

    Each member is one tenant's ``/v1/<tenant>/matters`` JSON page. MatterFile
    keys are tenant-scoped upstream ids — a value appearing under two tenants
    is a NAMESPACE COLLISION (two distinct matters sharing a display key),
    never one matter. The matcher must keep them apart: tenant-scoped
    namespaces are distinct origins.
    """
    per_tenant: dict[str, list[str]] = {}
    matter_ids: dict[str, list[int]] = {}
    for member, raw in sorted(members.items()):
        doc = json.loads(raw.decode("utf-8"))
        if isinstance(doc, dict):
            doc = doc.get("value") or []
        _require(isinstance(doc, list), f"legistar member {member} is not a list payload")
        tenant = member.split("_")[0]
        per_tenant[tenant] = sorted(
            str(m.get("MatterFile")) for m in doc if isinstance(m, dict) and m.get("MatterFile")
        )
        matter_ids[tenant] = sorted(
            int(m["MatterId"]) for m in doc if isinstance(m, dict) and m.get("MatterId") is not None
        )
    tenants = sorted(per_tenant)
    shared_files: dict[str, list[str]] = {}
    for i, t1 in enumerate(tenants):
        for t2 in tenants[i + 1 :]:
            shared = sorted(set(per_tenant[t1]) & set(per_tenant[t2]))
            for f in shared:
                shared_files.setdefault(f, []).append(f"{t1}|{t2}")
    shared_ids = (
        sorted(set(matter_ids[tenants[0]]) & set(matter_ids[tenants[1]]))
        if len(tenants) == 2
        else []
    )
    return {
        "oracle": "legistar_tenant_facts",
        "tenants": {t: len(per_tenant[t]) for t in tenants},
        "shared_matter_files": len(shared_files),
        "shared_matter_file_sample": sorted(shared_files)[:20],
        "shared_matter_ids": shared_ids[:20],
        "shared_matter_id_count": len(shared_ids),
    }


# --- OSM Overpass JSON (restricted lane, ODbL compartment) -------------------


def osm_overpass_facts(data: bytes) -> dict[str, Any]:
    """Expected facts for the Overpass surveillance-node capture.

    Element census: counts by ``type``, distinct element ids, and the
    surveillance-relevant tag histogram — the ODbL-compartment reference the
    camreg/OSM republish archetype compares against.
    """
    doc = json.loads(data.decode("utf-8"))
    elements = doc.get("elements")
    _require(isinstance(elements, list), "overpass page carries no elements[] list")
    by_type: dict[str, int] = {}
    ids: set[int] = set()
    tag_hist: dict[str, int] = {}
    for e in elements:
        by_type[e.get("type", "?")] = by_type.get(e.get("type", "?"), 0) + 1
        if e.get("id") is not None:
            ids.add(int(e["id"]))
        for k in e.get("tags") or {}:
            tag_hist[k] = tag_hist.get(k, 0) + 1
    return {
        "oracle": "osm_overpass_facts",
        "element_count": len(elements),
        "distinct_ids": len(ids),
        "by_type": dict(sorted(by_type.items())),
        "top_tags": dict(sorted(tag_hist.items(), key=lambda kv: -kv[1])[:20]),
    }


#: Oracle registry — slice.toml `oracle = "<name>"` resolves here. Adding an
#: oracle is additive; a slice naming an unregistered oracle fails validation.
ORACLES: dict[str, Callable[..., dict[str, Any]]] = {
    "arcgis_camera_facts": arcgis_camera_facts,
    "atlas_multistate_facts": atlas_multistate_facts,
    "usaspending_facts": usaspending_facts,
    "eff_release_facts": eff_release_facts,
    "legistar_tenant_facts": legistar_tenant_facts,
    "osm_overpass_facts": osm_overpass_facts,
}

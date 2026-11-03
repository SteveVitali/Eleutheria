# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared static-map composition core (K6 VIZ-01a, P36.54, ADR-157).

**Ownership (recorded at T3, one owner):** the *render* core — projection,
simplification, binning, the CSP-safe serializer — is ``exports.figures``
(the FIG-01a kit, P36.27). K1 MAP-05's conditional ("if MAP-05 has not
landed, VIZ-01a builds the core in ``exports/static_map.py``") resolved with
MAP-05 landed (P36.36) consuming the kit; this module is the *shared
composition* half — verified boundary-pack geometry → ``sig.figure-kit-geo/1``
specs, locator/sprite geometry, and the soft coverage layer — that VIZ-01a
(the dossier figures) and MAP-05 (the national overview) both consume. No
parallel renderer exists anywhere in the package.

Everything here is deterministic data shaping:

* :func:`geojson_outline` — a GeoJSON ``Polygon``/``MultiPolygon`` → the
  kit's ``Outline`` rings (the duplicated closing vertex dropped);
* :func:`figure_children` — the K6 §5.1 child set: the next registry level
  down (country→admin-1, admin-1→county) plus, for a US county, the census
  places whose representative point falls inside its outline (registry
  parentage names a place's *state*; containment is what a county figure
  needs);
* :func:`locator_geometry` — the ``sig.dossier-visuals/1`` ``locator``
  block: the registry parent context fitted into the locator box, the
  dossier's own outline drawn in the same frame (``child_d``);
* :func:`coverage_doc` — MAP-01b's ``coverage_by_jurisdiction.json`` in its
  **soft** posture: the rule is D-K1-4-pending, so every entry carries
  ``coverage: "rule_pending"`` and the legend is the K6 §5.1 verbatim
  sentence. The sources/technologies it reports are the *observed* inputs
  (``basis: "records_present"``) — never a "looked" verdict the undecided
  rule cannot yet support.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .figures.model import Outline, Ring
from .figures.paths import outline_to_path
from .figures.projection import fit_bounds, outline_bounds, project_outline
from .jurisdictions import jurisdiction_slug

#: The K6 §5.1 verbatim legend line while the coverage rule is pending
#: (D-K1-4). The figure lexicon draws the same state as a pending dash.
RULE_PENDING_LEGEND = "Where SIG has looked: rule pending — hollow areas rest on one source"
#: The soft coverage document's versioned rule id — a *pending* marker, so a
#: later real rule lands as a version bump, never a silent re-meaning.
RULE_PENDING_VERSION = "rule-pending@1"
COVERAGE_SCHEMA = "sig.jurisdiction-coverage/1"
LOCATOR_SYMBOLS_SCHEMA = "sig.locator-symbols/1"

#: The locator box in view units (K6 §9.1's recorded 160×101 example).
LOCATOR_WIDTH = 160
LOCATOR_HEIGHT = 101
LOCATOR_PADDING = 6


class StaticMapError(ValueError):
    """A fail-closed composition error (SIG-ENG-042)."""


# --------------------------------------------------------------------------- #
# GeoJSON → Outline                                                            #
# --------------------------------------------------------------------------- #


def _ring_from(coords: Sequence[Sequence[float]]) -> Ring:
    """One GeoJSON linear ring → a kit ring (closing duplicate dropped)."""
    pts = tuple((float(p[0]), float(p[1])) for p in coords)
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        raise StaticMapError(f"ring has fewer than 3 points ({len(pts)})")
    return pts


def geojson_outline(geom: Mapping[str, Any]) -> Outline:
    """A GeoJSON ``Polygon``/``MultiPolygon`` → the kit's ``Outline``.

    Rings are ``(lon, lat)`` pairs — the order GeoJSON emits — and hole rings
    stay part of the outline (the path renderer draws them as one compound
    path). A geometry type outside the two minted families refuses.
    """
    gtype = geom.get("type")
    coords = geom.get("coordinates")
    if not isinstance(coords, list):
        raise StaticMapError(f"geometry has no coordinates ({gtype!r})")
    if gtype == "Polygon":
        return tuple(_ring_from(r) for r in coords)
    if gtype == "MultiPolygon":
        return tuple(_ring_from(r) for poly in coords for r in poly)
    raise StaticMapError(f"unsupported geometry type {gtype!r}")


def outlines_from_geojson(docs: Mapping[str, Mapping[str, Any]]) -> dict[str, Outline]:
    """``jkey → Outline`` over a ``jkey → GeoJSON-geometry`` map."""
    return {str(k): geojson_outline(v) for k, v in docs.items()}


# --------------------------------------------------------------------------- #
# Point-in-polygon (pure-Python ray cast; deterministic, no DuckDB)            #
# --------------------------------------------------------------------------- #


def _in_ring(x: float, y: float, ring: Ring) -> bool:
    """Even-odd ray cast for a (lon, lat) point inside one ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def point_in_outline(x: float, y: float, outline: Outline) -> bool:
    """Whether the point lies in the outline's FIRST (outer) ring of each
    polygon — hole rings are not subtracted (a representative point for a
    minted boundary sits on its mainland ring; the recorded caveat rides the
    caller's note)."""
    return bool(outline) and _in_ring(x, y, outline[0])


def _representative_point(
    jkey: str,
    registry_rows: Mapping[str, Mapping[str, Any]],
    outlines: Mapping[str, Outline],
) -> tuple[float, float] | None:
    """The point used to ask 'is this jurisdiction inside that one': the
    registry's recorded ``internal_point`` first, then the outline's vertex
    centroid — deterministic, never guessed."""
    row = registry_rows.get(jkey)
    if row is not None:
        pt = row.get("internal_point")
        if isinstance(pt, list) and len(pt) == 2:
            return float(pt[0]), float(pt[1])
    rings = outlines.get(jkey)
    if rings:
        ring = rings[0]
        return (
            sum(p[0] for p in ring) / len(ring),
            sum(p[1] for p in ring) / len(ring),
        )
    return None


# --------------------------------------------------------------------------- #
# Figure children (K6 §5.1's "counties or places")                             #
# --------------------------------------------------------------------------- #

#: The registry level one step down for the figure's child layer. A US
#: county's children are its census *places* — but registry parentage names
#: a place's STATE (STATEFP), so the county→place link is derived by
#: containment, never guessed by name.
_NEXT_LEVEL = {
    "country": "state_province",
    "state_province": "county",
    "county": "municipality",
}


def figure_children(
    jkey: str,
    *,
    keyed: Any,
    registry_rows: Mapping[str, Mapping[str, Any]],
    outlines: Mapping[str, Outline],
) -> list[str]:
    """The sorted child jkeys a dossier figure draws (K6 §5.1).

    * ``country`` → its ``state_province`` registry children;
    * ``state_province`` → its ``county`` registry children;
    * ``county`` → the ``municipality`` rows whose representative point falls
      inside the county outline (the place→county link the registry's
      state-parentage does not carry);
    * ``municipality`` / national-scheme → none.
    """
    info = keyed.keys.get(jkey) if hasattr(keyed, "keys") else None
    level = str(info.level if info is not None else "")
    want = _NEXT_LEVEL.get(level)
    if want is None:
        return []
    if want != "municipality":
        kids = [
            c
            for c in keyed.children.get(jkey, ())
            if str(keyed.keys[c].level if c in keyed.keys else "") == want
        ]
        return sorted(kids)
    # County → municipalities by containment of the representative point.
    parent_outline = outlines.get(jkey)
    if not parent_outline:
        return []
    out: list[str] = []
    for cand, crow in registry_rows.items():
        if str(crow.get("level")) != "municipality" or cand == jkey:
            continue
        pt = _representative_point(cand, registry_rows, outlines)
        if pt is not None and point_in_outline(pt[0], pt[1], parent_outline):
            out.append(cand)
    return sorted(out)


# --------------------------------------------------------------------------- #
# Locator geometry (K6 §9.1: parent_symbol + child_d + viewbox)                #
# --------------------------------------------------------------------------- #


def locator_symbol_id(jkey: str) -> str:
    """The ``<symbol>`` id a parent context carries — deterministic per key."""
    return f"loc-{jurisdiction_slug(jkey)}"


def locator_geometry(
    context_outline: Outline,
    focus_outline: Outline,
    *,
    width: int = LOCATOR_WIDTH,
    height: int = LOCATOR_HEIGHT,
    padding: int = LOCATOR_PADDING,
) -> dict[str, Any]:
    """The locator block: the context outline fitted into the locator box and
    the focus drawn in the SAME frame — ``context_d``/``child_d`` pair plus
    the viewbox. The focus must sit inside the context's frame (a focus
    outside it is an exporter bug — fail closed, same posture as
    ``figures.build_locator``)."""
    ctx = project_outline(context_outline)
    fcs = project_outline(focus_outline)
    bounds = outline_bounds([ctx])
    fx0, fy0, fx1, fy1 = outline_bounds([fcs])
    if fx0 < bounds[0] or fy0 < bounds[1] or fx1 > bounds[2] or fy1 > bounds[3]:
        raise StaticMapError("locator focus lies outside the context bounds")
    frame = fit_bounds(bounds, width, height, padding)
    ctx_d = outline_to_path(tuple(tuple(frame.point(x, y) for x, y in ring) for ring in ctx))
    fcs_d = outline_to_path(tuple(tuple(frame.point(x, y) for x, y in ring) for ring in fcs))
    if ctx_d is None or fcs_d is None:
        raise StaticMapError("locator outline collapses under the 1.0px perimeter rule")
    return {
        "context_d": ctx_d,
        "child_d": fcs_d,
        "viewbox": [frame.width, frame.height],
    }


def build_locator_symbols(
    parents: Sequence[tuple[str, Outline]],
    *,
    width: int = LOCATOR_WIDTH,
    height: int = LOCATOR_HEIGHT,
    padding: int = LOCATOR_PADDING,
) -> tuple[str, dict[str, Any]]:
    """The ``<symbol>`` sheet for every parent context + its JSON index.

    ``parents`` is a sequence of ``(jkey, outline)``; the emitted SVG carries
    one ``<symbol id="loc-<slug>">`` per parent, each fitted independently so
    a glyph never shifts when a sibling is added (append-only growth). The
    JSON index is ``sig.locator-symbols/1`` — ``jkey → {symbol, viewbox}`` —
    so a page cites one symbol without shipping the sheet.
    """
    if not parents:
        raise StaticMapError("locator symbols need at least one parent context")
    seen: set[str] = set()
    syms: list[str] = []
    index: dict[str, Any] = {"schema": LOCATOR_SYMBOLS_SCHEMA, "symbols": {}}
    for jkey, outline in sorted(parents, key=lambda p: p[0]):
        if jkey in seen:
            raise StaticMapError(f"duplicate parent jkey {jkey!r}")
        seen.add(jkey)
        geo = locator_geometry(outline, outline, width=width, height=height, padding=padding)
        sid = locator_symbol_id(jkey)
        syms.append(
            f'<symbol id="{sid}" viewBox="0 0 {geo["viewbox"][0]} {geo["viewbox"][1]}">'
            f'<path d="{geo["context_d"]}" class="sig-fig-child"/></symbol>'
        )
        index["symbols"][jkey] = {"symbol": sid, "viewbox": geo["viewbox"]}
    svg = '<svg xmlns="http://www.w3.org/2000/svg" style="display:none">' + "".join(syms) + "</svg>"
    return svg, index


# --------------------------------------------------------------------------- #
# The soft coverage layer (MAP-01b pending — D-K1-4)                          #
# --------------------------------------------------------------------------- #


def coverage_doc(
    entries: Mapping[str, Mapping[str, Any]],
    *,
    release: Mapping[str, Any],
) -> dict[str, Any]:
    """``web/map/coverage_by_jurisdiction.json`` — the soft emission.

    ``entries`` is ``jkey → {sources, technologies}`` observed per
    jurisdiction. Every row reports ``basis: "records_present"`` — what the
    evidence shows — and ``coverage: "rule_pending"``, never a covered/not
    verdict the undecided C3/L3 rule (D-K1-4) cannot yet support. The legend
    is the K6 §5.1 verbatim sentence.
    """
    rows = {}
    for jkey in sorted(entries):
        e = entries[jkey]
        rows[str(jkey)] = {
            "sources": sorted(str(s) for s in e.get("sources") or ()),
            "technologies": sorted(str(t) for t in e.get("technologies") or ()),
            "basis": "records_present",
            "coverage": "rule_pending",
        }
    return {
        "schema": COVERAGE_SCHEMA,
        "release": dict(release),
        "rule_version": RULE_PENDING_VERSION,
        "rule_decision": "D-K1-4",
        "pending": True,
        "legend": RULE_PENDING_LEGEND,
        "jurisdictions": rows,
    }


def coverage_json(doc: Mapping[str, Any]) -> bytes:
    """Canonical bytes of the coverage document."""
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"


__all__ = [
    "COVERAGE_SCHEMA",
    "LOCATOR_HEIGHT",
    "LOCATOR_PADDING",
    "LOCATOR_SYMBOLS_SCHEMA",
    "LOCATOR_WIDTH",
    "RULE_PENDING_LEGEND",
    "RULE_PENDING_VERSION",
    "StaticMapError",
    "build_locator_symbols",
    "coverage_doc",
    "coverage_json",
    "figure_children",
    "geojson_outline",
    "locator_geometry",
    "locator_symbol_id",
    "outlines_from_geojson",
    "point_in_outline",
]

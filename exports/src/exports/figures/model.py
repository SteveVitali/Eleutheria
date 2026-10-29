# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The static figure kit's input/output model (``sig.figure-kit-geo/1``).

P36.27 (R11-K13-FIG-01a, ADR-157): every build-time map figure — dossier
at-a-glance maps, locators, index sprites, the no-JS overview — comes from
this one deterministic pipeline (K13 C-07, SIG-UI-066). The contract is a
plain-data document the exporter composes (VIZ-01a per-dossier, MAP-05 the
overview, JUR-04 the index sprite); nothing here touches the spine, a release
tree or a published route.

Honesty rules this model encodes (K6 V-3/V-4/V-9, SIG-UI-123/124/134):

* a record is drawn from its *published* position only — the exporter hands
  the kit the already tier-transformed coordinate; the kit never sees a finer
  value to leak;
* a record the figure does not draw is *counted* in ``not_drawn`` — tier-3
  (no published geometry), conflicting coordinates, a declared place with no
  published point, and records declared here whose published point lies
  elsewhere each get their own counter (SIG-UI-020);
* the emitted SVG carries *no per-area numeric data* — no ``data-*``
  attributes, no per-area ``<title>`` (SIG-UI-134); counts live in the
  figure-level ``<desc>`` and the accompanying places table.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FigureKitError(ValueError):
    """A fail-loud build error in the static figure kit (SIG-ENG-042).

    Raised for malformed input (a ring with fewer than three points, a tier
    outside 0–3, a degenerate frame) and for a figure that cannot meet a
    declared contract (the gzip size cap after every recorded fallback).
    """


class FigureSizeError(FigureKitError):
    """The figure remains over its declared size cap after both recorded
    fallbacks (K6 §5.1: child outlines to 1.0 px, then one coarser H3 res)."""


#: The figure-kit input contract id (the geography half — FIG-01a).
INPUT_SCHEMA = "sig.figure-kit-geo/1"
#: The emitted metadata document id.
RESULT_SCHEMA = "sig.figure-geo-meta/1"

#: A closed ring as ``(lon, lat)`` pairs (input) or ``(x, y)`` view units.
Ring = tuple[tuple[float, float], ...]
#: An outline is a tuple of rings (outer + islands/holes drawn in order).
Outline = tuple[Ring, ...]

#: The closed coverage vocabulary a child outline declares (K6 §5.1 layer 1):
#: ``rule_pending`` until K1's ``coverage_by_jurisdiction.json`` rule exists
#: (D-K1-4); a ``not_covered`` child draws the absence hatch.
COVERAGE_STATES = ("covered", "not_covered", "rule_pending")


@dataclass(frozen=True)
class ReleaseInfo:
    """The release stamp the figure's caption and metadata repeat."""

    label: str
    publication_id: str
    as_of_world: str


@dataclass(frozen=True)
class JurisdictionSpec:
    """The dossier's own jurisdiction identity (K4 keys, SIG-JUR-001)."""

    jkey: str
    slug_path: str
    level: str
    chain: tuple[str, ...]
    name: str
    #: The lexicon's amber-dashed state — a jurisdiction whose boundary or
    #: dossier itself is provisional draws the provisional outline (K14 §4.5).
    provisional: bool = False


@dataclass(frozen=True)
class ChildSpec:
    """A child jurisdiction outline (counties or places) with its drill-down
    link and coverage state (K6 §5.1)."""

    jkey: str
    rings: Outline
    coverage: str
    #: The child dossier href — present only where the child has a dossier
    #: (D-K4-3 thresholds); ``None`` draws the outline without a link.
    href: str | None = None


@dataclass(frozen=True)
class RecordInput:
    """One published record as the figure may see it — published geometry only.

    ``record_id`` exists for ordering/counting only: it is NEVER emitted into
    the SVG (SIG-UI-134 forbids per-area data, and a per-record id would be
    exactly that). Sorting on it keeps output byte-deterministic.
    """

    record_id: str
    #: The published (already tier-transformed) position. ``None`` when the
    #: release publishes no point for this record → ``not_drawn``.
    lat: float | None
    lon: float | None
    #: The §19.4 geospatial tier (0–3). Tier 3 is never drawn.
    tier: int
    #: Contributing source ids — drives the single-source (hollow) /
    #: two-source (halftone) / corroborated (filled) encoding (K1 §3.5).
    sources: frozenset[str]
    #: The licence compartment the record draws in → caption licence lines.
    compartment: str
    #: The record's declared place (K4 jkey) — the ``declared_no_point`` and
    #: ``located_elsewhere`` honesty counters key on it.
    declared_jkey: str | None = None
    #: Set when the record's *published* point lies outside this figure's
    #: jurisdiction while its declared place is inside it — counted under
    #: ``not_drawn.located_elsewhere`` keyed on the jkey it actually sits in.
    located_elsewhere_jkey: str | None = None
    #: Withheld as conflicting coordinates (K6 V-3 third honesty line).
    conflicting: bool = False
    #: Epistemic states the lexicon owns: ``≠`` contested mark; amber-dashed
    #: provisional. A record may carry both; neither changes where it draws.
    contested: bool = False
    provisional: bool = False
    #: The record's published-precision diameter in metres when the input
    #: knows it; ``None`` → derived from the sensitivity tier table
    #: (:func:`binning.precision_m_for_tier`). The binning guard never draws a
    #: record finer than this (K6 V-4, SIG-UI-124).
    precision_m: float | None = None


@dataclass(frozen=True)
class FigureSpec:
    """One build-time map figure's full input (``sig.figure-kit-geo/1``)."""

    release: ReleaseInfo
    jurisdiction: JurisdictionSpec
    #: The jurisdiction outline rings (empty only for a typed empty figure —
    #: a jurisdiction with no boundary yet still emits nothing silently).
    outline: Outline
    children: tuple[ChildSpec, ...]
    records: tuple[RecordInput, ...]
    #: The boundary-pack vintage the caption names ("census.cb.2025.500k" etc).
    boundary_vintage: str
    #: The figure geometry: K6's 720×≤520 main-column box with 8 px padding.
    width: int = 720
    max_height: int = 520
    padding_px: int = 8
    #: K6 §5.1's ≤30 KiB-gzip inline-map cap; ``None`` disables enforcement
    #: (locators and sprites carry their own bounds).
    size_cap_gzip: int | None = 30 * 1024
    #: Extra classes the caller may hang on the root ``<svg>`` (kept minimal —
    #: the class vocabulary is the kit's).
    extra_classes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NotDrawn:
    """The 'not drawn' honesty counters (K6 §5.1, SIG-UI-020)."""

    declared_no_point: int
    located_elsewhere: tuple[tuple[str, int], ...]
    conflicting: int
    tier3: int

    def to_json(self) -> dict[str, Any]:
        return {
            "declared_no_point": self.declared_no_point,
            "located_elsewhere": [
                {"jkey": jkey, "records": n} for jkey, n in self.located_elsewhere
            ],
            "conflicting": self.conflicting,
            "tier3": self.tier3,
        }


@dataclass(frozen=True)
class MapFigureResult:
    """The emitted figure: byte-deterministic SVG plus its build metadata."""

    svg: str
    viewbox: tuple[float, float]
    mode: str
    zoom: float
    rule: str
    h3_res: int | None
    cap_actions: tuple[str, ...]
    not_drawn: NotDrawn
    desc: dict[str, Any]
    compartments_drawn: tuple[str, ...]
    children: tuple[dict[str, Any], ...]
    boundary_vintage: str
    size_bytes: int
    gzip_bytes: int

    def to_json(self) -> dict[str, Any]:
        """The ``sig.figure-geo-meta/1`` document (metadata only — the SVG is
        the artifact; this mirrors K6 §9.1's ``map`` block)."""
        return {
            "schema": RESULT_SCHEMA,
            "viewbox": list(self.viewbox),
            "zoom": round(self.zoom, 3),
            "mode": self.mode,
            "h3_res": self.h3_res,
            "rule": self.rule,
            "cap_actions": list(self.cap_actions),
            "not_drawn": self.not_drawn.to_json(),
            "desc": self.desc,
            "compartments_drawn": list(self.compartments_drawn),
            "children": list(self.children),
            "boundary_vintage": self.boundary_vintage,
            "size_bytes": self.size_bytes,
            "gzip_bytes": self.gzip_bytes,
        }


# --- fail-closed loaders (plain-dict input; SIG-ENG-042) ----------------------


def _ring(obj: object, where: str) -> Ring:
    if not isinstance(obj, (list, tuple)):
        raise FigureKitError(f"{where}: ring is not a list of points")
    pts = []
    for i, p in enumerate(obj):
        if (
            not isinstance(p, (list, tuple))
            or len(p) != 2
            or not all(isinstance(v, (int, float)) for v in p)
        ):
            raise FigureKitError(f"{where}[{i}]: point is not a (lon, lat) pair")
        pts.append((float(p[0]), float(p[1])))
    if len(pts) < 3:
        raise FigureKitError(f"{where}: ring has fewer than 3 points ({len(pts)})")
    return tuple(pts)


def _outline(obj: object, where: str) -> Outline:
    if not isinstance(obj, (list, tuple)):
        raise FigureKitError(f"{where}: outline is not a list of rings")
    return tuple(_ring(r, f"{where}[{i}]") for i, r in enumerate(obj))


def _record(obj: object, where: str) -> RecordInput:
    if not isinstance(obj, Mapping):
        raise FigureKitError(f"{where}: record is not an object")
    tier = obj.get("tier")
    if not isinstance(tier, int) or tier not in (0, 1, 2, 3):
        raise FigureKitError(f"{where}: tier {tier!r} outside 0–3")
    lat, lon = obj.get("lat"), obj.get("lon")
    if (lat is None) != (lon is None):
        raise FigureKitError(f"{where}: lat/lon must both be present or both null")
    if lat is not None and not all(isinstance(v, (int, float)) for v in (lat, lon)):
        raise FigureKitError(f"{where}: lat/lon are not numbers")
    rid = obj.get("record_id")
    if not isinstance(rid, str) or not rid:
        raise FigureKitError(f"{where}: missing record_id")
    sources = obj.get("sources")
    if not isinstance(sources, (list, tuple)) or not all(isinstance(s, str) for s in sources):
        raise FigureKitError(f"{where}: sources is not a list of source ids")
    compartment = obj.get("compartment")
    if not isinstance(compartment, str) or not compartment:
        raise FigureKitError(f"{where}: missing compartment")
    return RecordInput(
        record_id=rid,
        lat=float(lat) if lat is not None else None,
        lon=float(lon) if lon is not None else None,
        tier=tier,
        sources=frozenset(sources),
        compartment=compartment,
        declared_jkey=obj.get("declared_jkey"),
        located_elsewhere_jkey=obj.get("located_elsewhere_jkey"),
        conflicting=bool(obj.get("conflicting", False)),
        contested=bool(obj.get("contested", False)),
        provisional=bool(obj.get("provisional", False)),
        precision_m=(float(obj["precision_m"]) if obj.get("precision_m") is not None else None),
    )


def spec_from_dict(doc: Mapping[str, Any]) -> FigureSpec:
    """Load a ``sig.figure-kit-geo/1`` document — fail-closed on any malformed
    field (SIG-ENG-042: an empty or unverified surface fails, never renders
    silently)."""

    if doc.get("schema") != INPUT_SCHEMA:
        raise FigureKitError(f"schema {doc.get('schema')!r} != {INPUT_SCHEMA!r}")
    rel = doc.get("release")
    jur = doc.get("jurisdiction")
    if not isinstance(rel, Mapping) or not isinstance(jur, Mapping):
        raise FigureKitError("release/jurisdiction blocks missing or not objects")
    children = []
    for i, c in enumerate(doc.get("children") or ()):
        where = f"children[{i}]"
        if not isinstance(c, Mapping):
            raise FigureKitError(f"{where}: child is not an object")
        cov = c.get("coverage", "rule_pending")
        if cov not in COVERAGE_STATES:
            raise FigureKitError(f"{where}: coverage {cov!r} outside {COVERAGE_STATES}")
        children.append(
            ChildSpec(
                jkey=str(c["jkey"]),
                rings=_outline(c.get("rings") or (), where),
                coverage=str(cov),
                href=c.get("href"),
            )
        )
    return FigureSpec(
        release=ReleaseInfo(
            label=str(rel["label"]),
            publication_id=str(rel["publication_id"]),
            as_of_world=str(rel["as_of_world"]),
        ),
        jurisdiction=JurisdictionSpec(
            jkey=str(jur["jkey"]),
            slug_path=str(jur["slug_path"]),
            level=str(jur["level"]),
            chain=tuple(str(k) for k in (jur.get("chain") or ())),
            name=str(jur["name"]),
            provisional=bool(jur.get("provisional", False)),
        ),
        outline=_outline(doc.get("outline") or (), "outline"),
        children=tuple(children),
        records=tuple(_record(r, f"records[{i}]") for i, r in enumerate(doc.get("records") or ())),
        boundary_vintage=str(doc.get("boundary_vintage", "unknown")),
        width=int(doc.get("width", 720)),
        max_height=int(doc.get("max_height", 520)),
        padding_px=int(doc.get("padding_px", 8)),
        size_cap_gzip=(
            int(sc) if (sc := doc.get("size_cap_gzip", 30 * 1024)) is not None else None
        ),
    )


def load_spec(path: Path | str) -> FigureSpec:
    """Load a ``sig.figure-kit-geo/1`` document from disk."""
    p = Path(path)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FigureKitError(f"{p}: cannot read spec — {e}") from e
    if not isinstance(doc, Mapping):
        raise FigureKitError(f"{p}: top level is not an object")
    return spec_from_dict(doc)


__all__ = [
    "COVERAGE_STATES",
    "FigureKitError",
    "FigureSizeError",
    "FigureSpec",
    "ChildSpec",
    "INPUT_SCHEMA",
    "JurisdictionSpec",
    "MapFigureResult",
    "NotDrawn",
    "Outline",
    "RESULT_SCHEMA",
    "RecordInput",
    "ReleaseInfo",
    "Ring",
    "load_spec",
    "spec_from_dict",
]

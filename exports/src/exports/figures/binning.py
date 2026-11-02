# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``static-12px@1`` — the one static binning rule (K6 §5.1, ADR-157, SIG-UI-124).

    At the figure's framing zoom and width, draw tier-0 published points
    when z ≥ 10 *and* the draw count ≤ 1,000. Otherwise draw H3 areas at the
    finest published resolution whose average hexagon diameter still reads as
    ≥ 12 px at that width — and never finer than any record's published
    precision (the tier guard).

Why the rule stands alone (K6's alternatives-considered note, echoed in
ADR-157): a published-state map cannot sit on interactive tile tiling — the
static layer must work with every record the release actually publishes, so
the rule bins published geometry, never a request-time grid. MAP-07's
interactive binning keeps the same numerical contract — both surfaces read
``DENSITY_LEVELS``, both take the published precision ceiling — so the
static figure is never a weaker view of the same release (K0 I-3).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import h3

from .model import FigureKitError, RecordInput

RULE_NAME = "static-12px@1"

#: The K6 constants — single vocabulary, never re-derived per figure.
BIN_POINT_ZOOM_MIN = 10.0
BIN_POINT_MAX_RECORDS = 1000
BIN_HEX_MIN_DIAMETER_PX = 12.0

#: The tier → published-precision table (K6 §5.1, §19.4). Metres: the coarsest
#: grid the record may be read at. Tier-0's negligible bound means "full
#: precision" — the figure may draw the record's own point, never finer than
#: any coarser record also drawn alongside it.
TIER_PRECISION_M = {0: 1.0, 1: 1000.0, 2: 5000.0, 3: math.inf}


@dataclass(frozen=True)
class BinCell:
    """One drawn H3 area: its index (the renderer derives the boundary),
    cell-centre ground position (lon, lat), source multiplicity and the
    compartment it draws in."""

    cell: str
    x: float
    y: float
    sources: frozenset[str]
    compartment: str


@dataclass(frozen=True)
class BinPlan:
    """What the rule decided for one figure (K6 §5.1's emitted ``desc``)."""

    mode: str  # "points" | "h3-areas"
    h3_res: int | None
    #: H3 index → drawn cell, in deterministic order (sorted index).
    cells: tuple[BinCell, ...] | None
    #: Record→cell map for emitted metadata; point mode keeps the record order.
    index_keys: tuple[str, ...]


def meters_per_view_unit(frame_scale: float, mean_lat: float) -> float:
    """Local ground metres per view unit under Web Mercator.

    The Mercator projected metre stretches with latitude; the *ground*
    metres a view unit covers is the projection's unit scale ÷ cos(lat) —
    the same reading the framing zoom uses (one vocabulary).
    """
    cos_lat = math.cos(math.radians(max(-85.0, min(85.0, mean_lat))))
    return 1.0 / (frame_scale * cos_lat)


def precision_m_for_tier(rec: RecordInput) -> float:
    """A record's published-precision bound in metres — the declared value
    when the exporter supplied it, else the tier table."""
    if rec.precision_m is not None:
        return rec.precision_m
    return TIER_PRECISION_M[rec.tier]


def _res_cap_for_bound(bound_m: float) -> int | None:
    """The finest H3 resolution whose average cell *diameter* (2·edge, the
    rule's documented reading — ADR-157) still meets the precision bound:
    drawing at this res or coarser never fabricates finer-than-published
    resolution (K6 V-4). ``None`` when no published resolution is coarse
    enough — a fail-closed state, never silently coarsened past res 0."""
    if bound_m <= 0:
        return 15
    cap: int | None = None
    for res in range(16):
        if 2.0 * h3.average_hexagon_edge_length(res, unit="m") >= bound_m:
            cap = res
    return cap


def finest_drawable_res(records: list[RecordInput]) -> int | None:
    """The finest H3 resolution every drawn record's published precision
    tolerates — the minimum per-record cap across the cohort."""
    cap = 15
    for rec in records:
        r = _res_cap_for_bound(precision_m_for_tier(rec))
        if r is None:
            return None
        cap = min(cap, r)
    return cap


def plan_binning(
    records: list[RecordInput],
    zoom: float,
    frame_scale: float,
    mean_lat: float,
    width: int,
    coerce_res: int | None = None,
) -> BinPlan:
    """Apply ``static-12px@1`` to the drawable cohort.

    ``records`` is the drawable set — the caller has already removed
    no-point / conflicting / tier-3 / elsewhere records (they are counted
    under ``not_drawn``, never binned).

    ``coerce_res`` is the size-cap fallback hook (K6 §5.1): when a figure
    stays over its declared cap after line-width reduction, the caller
    retries the pass at one coarser H3 resolution.
    """
    drawable = [r for r in records if r.lat is not None and r.lon is not None]
    if not drawable:
        return BinPlan(mode="empty", h3_res=None, cells=(), index_keys=())
    if zoom >= BIN_POINT_ZOOM_MIN and len(drawable) <= BIN_POINT_MAX_RECORDS:
        return BinPlan(mode="points", h3_res=None, cells=None, index_keys=())

    res_cap = finest_drawable_res(drawable)
    if res_cap is None:
        raise FigureKitError(
            "drawable records carry no drawable resolution (all tier-3 "
            "or infinite precision bounds) — they must not reach binning"
        )
    m_per_unit = meters_per_view_unit(frame_scale, mean_lat)
    chosen: int | None = None
    for res in range(res_cap, -1, -1):
        diameter_m = 2.0 * h3.average_hexagon_edge_length(res, unit="m")
        if diameter_m / m_per_unit >= BIN_HEX_MIN_DIAMETER_PX:
            chosen = res
            break
    if chosen is None:
        chosen = 0
    if coerce_res is not None:
        chosen = min(chosen, coerce_res)
        if chosen < 0:
            raise FigureKitError("coerced H3 resolution below 0")

    cell_sources: dict[str, set[str]] = {}
    cell_compartments: dict[str, set[str]] = {}
    for rec in drawable:
        assert rec.lat is not None and rec.lon is not None  # narrowed above
        cell = h3.latlng_to_cell(rec.lat, rec.lon, chosen)
        cell_sources.setdefault(cell, set()).update(rec.sources)
        cell_compartments.setdefault(cell, set()).add(rec.compartment)
    ordered: list[BinCell] = []
    for cell in sorted(cell_sources):
        lat, lon = h3.cell_to_latlng(cell)
        # ``x``/``y`` carry the cell-centre *ground* position (lon, lat) —
        # the caller maps it through the frame.
        ordered.append(
            BinCell(
                cell=cell,
                x=lon,
                y=lat,
                sources=frozenset(cell_sources[cell]),
                compartment=_merge_compartment(cell_compartments[cell]),
            )
        )
    return BinPlan(
        mode="h3-areas",
        h3_res=chosen,
        cells=tuple(ordered),
        index_keys=tuple(sorted(cell_sources)),
    )


def _merge_compartment(compartments: set[str]) -> str:
    """A cell draws in the most restrictive compartment it touches — fail-
    closed honesty (K1's licence-first reading): a cell that aggregates both
    ``records`` and ``records-law-enforcement-sensitive`` records draws the
    sensitive compartment's licence line."""
    for c in ("records-law-enforcement-sensitive", "records-sensitive", "records"):
        if c in compartments:
            return c
    return "records"


__all__ = [
    "BIN_HEX_MIN_DIAMETER_PX",
    "BIN_POINT_MAX_RECORDS",
    "BIN_POINT_ZOOM_MIN",
    "RULE_NAME",
    "TIER_PRECISION_M",
    "BinCell",
    "BinPlan",
    "finest_drawable_res",
    "meters_per_view_unit",
    "plan_binning",
    "precision_m_for_tier",
]

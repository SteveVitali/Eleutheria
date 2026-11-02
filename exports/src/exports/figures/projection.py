# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Web Mercator projection and frame fitting (P36.27, ADR-157; K6 §5.1).

One projection, one fit: the static figure and the activated map frame the
same view, so the dossier's static rendition is honest the moment the
interactive map opens over it (K6 V-1, K0 I-2). The one documented exception
is the US country view (K1's Albers + AK/HI/PR insets variant) — a composite
the page layer composes out of frames, never a second projection inside the
kit.

The **framing zoom** is the fitted scale restated in the vocabulary the K1
band table speaks: the zoom at which a 512-px-tile world would reproduce the
figure's pixel-per-metre scale,

    zoom = log2( scale_px_per_mercator_metre · MERCATOR_WORLD_M / 512 ).

This reproduces the design doc's recorded band choices (D-K6-4 — the static
rule, not the K1 interactive band): a US country frame reads ≈ z3, a state
≈ z5, a county ≈ z9–10 and a dense district above z10, which is exactly
where ``static-12px@1`` switches a figure from areas to points.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .model import FigureKitError, Outline, Ring

#: Web Mercator (EPSG:3857) world width in metres — 2π·6,378,137.
MERCATOR_WORLD_M = 40075016.68557849
#: The tile width the framing zoom is expressed against (the D-K6-4 band
#: convention recorded in ADR-157; 512-px tiles, the 2× tile scale).
ZOOM_REFERENCE_TILE_PX = 512.0
#: The latitude bound of EPSG:3857.
MAX_MERCATOR_LAT = 85.05112878
#: A bounds span below this is degenerate — fit clamps rather than dividing
#: by zero, and the caller still gets a deterministic (if tight) frame.
_MIN_SPAN_M = 1e-3


def project(lon: float, lat: float) -> tuple[float, float]:
    """Project (lon, lat) degrees to Web-Mercator metres (EPSG:3857)."""
    lat = max(-MAX_MERCATOR_LAT, min(MAX_MERCATOR_LAT, lat))
    x = math.radians(lon) * MERCATOR_WORLD_M / (2.0 * math.pi)
    y = math.log(math.tan(math.pi / 4.0 + math.radians(lat) / 2.0)) * (
        MERCATOR_WORLD_M / (2.0 * math.pi)
    )
    return (x, y)


def project_ring(ring: Ring) -> Ring:
    return tuple(project(lon, lat) for lon, lat in ring)


def project_outline(outline: Outline) -> Outline:
    return tuple(project_ring(r) for r in outline)


def outline_bounds(outlines: list[Outline]) -> tuple[float, float, float, float]:
    """The union projected bbox ``(x0, y0, x1, y1)`` across every ring —
    fail-closed on empty input (an outline-free spec has no frame)."""
    xs: list[float] = []
    ys: list[float] = []
    for outline in outlines:
        for ring in outline:
            for x, y in ring:
                xs.append(x)
                ys.append(y)
    if not xs:
        raise FigureKitError("no geometry to frame — outline and children are all empty")
    return (min(xs), min(ys), max(xs), max(ys))


@dataclass(frozen=True)
class Frame:
    """The fitted view: projected metres → view units, plus the framing zoom."""

    width: int
    height: int
    scale: float
    #: view = (projected − origin) · scale + padding.
    origin_x: float
    origin_y: float
    padding: float
    zoom: float

    def point(self, x: float, y: float) -> tuple[float, float]:
        """Projected metres → view units (SVG y grows downward — flip)."""
        return (
            self.padding + (x - self.origin_x) * self.scale,
            self.padding + (self.origin_y - y) * self.scale,
        )


def fit_bounds(
    bounds: tuple[float, float, float, float],
    width: int,
    max_height: int,
    padding: int,
) -> Frame:
    """Fit ``bounds`` (projected metres) into ``width`` × ≤ ``max_height`` view
    units with ``padding`` on every side (K6 §5.1's 8 px).

    The height is *derived* from the fitted aspect, capped at ``max_height``:
    a tall jurisdiction keeps its full extent — the 16:10 box is a ceiling,
    never a crop.
    """
    x0, y0, x1, y1 = bounds
    span_x = max(x1 - x0, _MIN_SPAN_M)
    span_y = max(y1 - y0, _MIN_SPAN_M)
    inner_w = width - 2.0 * padding
    inner_h = max_height - 2.0 * padding
    if inner_w <= 0 or inner_h <= 0:
        raise FigureKitError(f"frame {width}×{max_height} leaves no room for {padding}px padding")
    scale = min(inner_w / span_x, inner_h / span_y)
    height = int(math.ceil(span_y * scale + 2.0 * padding))
    height = min(max_height, max(1, height))
    zoom = math.log2(scale * MERCATOR_WORLD_M / ZOOM_REFERENCE_TILE_PX)
    return Frame(
        width=width,
        height=height,
        scale=scale,
        origin_x=x0,
        origin_y=y1,
        padding=float(padding),
        zoom=zoom,
    )


__all__ = [
    "MAX_MERCATOR_LAT",
    "MERCATOR_WORLD_M",
    "Frame",
    "ZOOM_REFERENCE_TILE_PX",
    "fit_bounds",
    "outline_bounds",
    "project",
    "project_outline",
    "project_ring",
]

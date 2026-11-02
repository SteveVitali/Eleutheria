# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Ring simplification — the deterministic Douglas–Peucker (K6 §5.1, ADR-157).

The K6 spec names the one algorithm deliberately: it is documented, stable,
and cheap; visvalingam-whyatt was considered and deferred (K6's alternative-
considered note — ADR-157 records the choice). Geometry is simplified **in
view units** — the figure's own pixel space — so the same published outline
simplifies identically under any emitted scale, and the precision ceiling
(K6 V-4) states its rule in the same units: never draw an outline under
1.0 px, never render record geometry under its published precision.
"""

from __future__ import annotations

import math

from .model import FigureKitError, Outline, Ring

#: The K6 minimum-perimeter rule: an outline that cannot hold 1.0 px of
#: perimeter in view units collapses to nothing — it is never drawn finer.
MIN_PERIMETER_PX = 1.0

#: Default chord threshold: half a view pixel.
DEFAULT_TOLERANCE_PX = 0.5


def _point_line_dist(
    p: tuple[float, float], a: tuple[float, float], b: tuple[float, float]
) -> float:
    """Distance from p to the chord a→b. For a closed ring's ring distance we
    use the Euclidean distance to the chord — the standard DP criterion."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    denom = dx * dx + dy * dy
    if denom == 0.0:
        return math.hypot(px - ax, py - ay)
    t = ((px - ax) * dx + (py - ay) * dy) / denom
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def simplify_ring(ring: Ring, tolerance: float = DEFAULT_TOLERANCE_PX) -> Ring:
    """Douglas–Peucker on a closed ring, in view units.

    The ring is treated as a closed polyline anchored at its first point —
    the iterative stack keeps the same vertex order, so the simplified ring
    is a strict subsequence of the input and the result is byte-stable.
    """
    if tolerance < 0:
        raise FigureKitError(f"negative tolerance {tolerance}")
    n = len(ring)
    if n <= 3:
        return ring
    keep = [False] * n
    keep[0] = keep[n - 1] = True
    stack: list[tuple[int, int]] = [(0, n - 1)]
    while stack:
        i0, i1 = stack.pop()
        a, b = ring[i0], ring[i1]
        max_d, max_i = -1.0, -1
        for i in range(i0 + 1, i1):
            d = _point_line_dist(ring[i], a, b)
            if d > max_d:
                max_d, max_i = d, i
        if max_d > tolerance:
            keep[max_i] = True
            stack.append((i0, max_i))
            stack.append((max_i, i1))
    out = tuple(p for p, k in zip(ring, keep, strict=True) if k)
    return out if len(out) >= 3 else (ring[0], ring[0], ring[0])


def ring_perimeter(ring: Ring) -> float:
    """Closed-ring perimeter in the same units the ring is expressed in."""
    if len(ring) < 2:
        return 0.0
    total = 0.0
    for i in range(len(ring)):
        x0, y0 = ring[i]
        x1, y1 = ring[(i + 1) % len(ring)]
        total += math.hypot(x1 - x0, y1 - y0)
    return total


def simplify_outline(outline: Outline, tolerance: float = DEFAULT_TOLERANCE_PX) -> Outline:
    """Simplify every ring of an outline; drop rings that collapse below
    three points. The 1.0-px *perimeter* ceiling is applied by the caller
    (``paths.outline_to_path``) because it needs the perimeter — this stage is
    pure shape."""
    out: list[Ring] = []
    for ring in outline:
        s = simplify_ring(ring, tolerance)
        if len(s) >= 3:
            out.append(s)
    return tuple(out)


__all__ = [
    "DEFAULT_TOLERANCE_PX",
    "MIN_PERIMETER_PX",
    "ring_perimeter",
    "simplify_outline",
    "simplify_ring",
]

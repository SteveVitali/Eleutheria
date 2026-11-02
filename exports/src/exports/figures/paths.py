# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""View-space geometry → SVG path data (P36.27, ADR-157).

One deterministic ``d`` formatter: ``%.2f`` coordinates, ``M/L/Z`` commands,
spaces between numbers — the same ring in the same frame always yields the
same bytes (K6 §5.1's byte-deterministic output requirement).

The 1.0-px-perimeter rule lives here because it is a *draw-time* honesty
guard (K6 V-4): an outline whose view-space perimeter is under a pixel is
never drawn — the caller receives ``None`` and drops the path (and, for
children, keeps the table row, which is where the coverage state is honestly
readable anyway).
"""

from __future__ import annotations

from .model import Outline, Ring
from .simplify import MIN_PERIMETER_PX, ring_perimeter, simplify_outline


def _fmt(v: float) -> str:
    s = f"{v:.2f}"
    # Normalise "-0.00" → "0.00": a negative zero still serialises stably.
    return "0.00" if s == "-0.00" else s


def ring_path(ring: Ring) -> str:
    """One ring → ``M x y L x y … Z`` path data."""
    head = f"M{_fmt(ring[0][0])} {_fmt(ring[0][1])}"
    rest = "".join(f"L{_fmt(x)} {_fmt(y)}" for x, y in ring[1:])
    return f"{head}{rest}Z"


def outline_to_path(
    outline: Outline,
    tolerance: float | None = None,
    min_perimeter: float = MIN_PERIMETER_PX,
) -> str | None:
    """Simplify + format an outline as a single compound path.

    Returns ``None`` when every ring collapses under the 1.0-px perimeter
    rule — the outline is not drawn (K6 V-4), which the caller surfaces
    honestly (a child still lists in the places table; a jurisdiction that
    cannot draw raises fail-closed upstream).
    """
    if not outline:
        return None
    tol = 0.5 if tolerance is None else tolerance
    rings = []
    for ring in simplify_outline(outline, tol):
        if ring_perimeter(ring) < min_perimeter:
            continue
        rings.append(ring_path(ring))
    if not rings:
        return None
    return "".join(rings)


def circle_path(cx: float, cy: float, r: float) -> str:
    """A circle approximated by two arcs — path-only output keeps one
    element vocabulary (``<path>``) across the kit."""
    return (
        f"M{_fmt(cx - r)} {_fmt(cy)}"
        f"a{_fmt(r)} {_fmt(r)} 0 1 0 {_fmt(2 * r)} 0"
        f"a{_fmt(r)} {_fmt(r)} 0 1 0 {_fmt(-2 * r)} 0Z"
    )


def marker_glyph_path(cx: float, cy: float, half: float = 4.0) -> str:
    """The ``≠`` contested glyph drawn as strokes (the lexicon's one meaning
    for disagreement) — a deterministic two-stroke path so it prints without
    font dependence."""
    a = half
    return (
        f"M{_fmt(cx - a)} {_fmt(cy - a)}L{_fmt(cx + a)} {_fmt(cy - a)}"
        f"M{_fmt(cx - a)} {_fmt(cy + a)}L{_fmt(cx + a)} {_fmt(cy + a)}"
        f"M{_fmt(cx - a * 0.6)} {_fmt(cy + a * 1.4)}L{_fmt(cx + a * 0.6)} {_fmt(cy - a * 1.4)}"
    )


__all__ = ["circle_path", "marker_glyph_path", "outline_to_path", "ring_path"]

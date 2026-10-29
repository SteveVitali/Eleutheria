# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deterministic figure layouts (P36.28, FIG-01b; K6 §6.2, K2 ego).

The ticket's "overview-layout wrapper" is these two pure functions: the
two-column bipartite placement and the per-relation-sector radial ego
placement. Both are closed-form — node order in, view-space coordinates
out — so the emitted bytes are stable across runs (K6 §5.1's byte
determinism) and the package carries **no third-party layout dependency at
all**: the GPL ``igraph`` wheel is never imported (the contract's licence
pin; ``check:licenses`` guards OSI-only on the web side and this module is
in-house Apache-2.0 code, so the compartment stays clean by construction).

Ordering contract every caller honours: nodes reach these functions already
sorted (label, then key — the deterministic tie-break); positions then fall
out of the geometry only.
"""

from __future__ import annotations

import math

from .model import FigureKitError

#: A view-space point.
Point = tuple[float, float]


def bipartite_positions(
    anchors: tuple[str, ...],
    counterparties: tuple[str, ...],
    *,
    width: float,
    row_pitch: float = 20.0,
    pad_y: float = 8.0,
) -> tuple[dict[str, Point], dict[str, Point], float]:
    """The wide two-column layout (K6 §6.2): anchors down the left column,
    counterparties down the right, ``row_pitch`` px rows, top-aligned.

    Returns ``(anchor_edge_points, counterparty_edge_points, node_area_h)`` —
    the points are where edges meet each column (the explicit central
    whitespace sits between them); glyph/label placement is the emitter's.
    """
    if row_pitch < MIN_ROW_PITCH:
        raise FigureKitError(f"row_pitch {row_pitch} under {MIN_ROW_PITCH}")
    rows = max(len(anchors), len(counterparties))
    area_h = rows * row_pitch
    xa = width * ANCHOR_EDGE_X
    xc = width * COUNTERPARTY_EDGE_X
    apos = {k: (xa, pad_y + i * row_pitch + row_pitch / 2) for i, k in enumerate(anchors)}
    cpos = {k: (xc, pad_y + i * row_pitch + row_pitch / 2) for i, k in enumerate(counterparties)}
    return apos, cpos, area_h


def narrow_bipartite_positions(
    anchors: tuple[str, ...],
    counterparties: tuple[str, ...],
    *,
    width: float,
    columns: int = 2,
    row_pitch: float = 18.0,
    gap: float = 48.0,
    pad_y: float = 8.0,
) -> tuple[dict[str, Point], dict[str, Point], float]:
    """The narrow variant (K6 §6.2: 360 viewBox, anchors *above*
    counterparties): each side fills a small ``columns``-wide grid, the
    counterparty block sits one gap-band lower so edges flow downward."""
    if columns < 1:
        raise FigureKitError("narrow layout needs ≥1 column")
    cell_w = (width - 2 * pad_y) / columns
    a_rows = (len(anchors) + columns - 1) // columns
    c_rows = (len(counterparties) + columns - 1) // columns

    def _place(keys: tuple[str, ...], y0: float) -> dict[str, Point]:
        pos: dict[str, Point] = {}
        for i, k in enumerate(keys):
            col, row = i % columns, i // columns
            pos[k] = (
                pad_y + col * cell_w + 10,
                y0 + row * row_pitch + row_pitch / 2,
            )
        return pos

    a_y0 = pad_y + row_pitch / 2
    c_y0 = pad_y + a_rows * row_pitch + gap + row_pitch / 2
    area_h = a_rows * row_pitch + gap + c_rows * row_pitch
    return _place(anchors, a_y0), _place(counterparties, c_y0), area_h


def ego_positions(
    sectors: tuple[tuple[str, tuple[str, ...]], ...],
    *,
    width: float,
    centre_y: float,
    radius: float,
    gap_deg: float = 8.0,
) -> dict[str, Point]:
    """The radial ego layout (K2): the centre node sits at ``(w/2, cy)``;
    neighbours fan out on one circle, grouped into per-relation sectors
    separated by ``gap_deg``. ``sectors`` arrives in its deterministic order
    (relation label, then node sort inside); angles fall out of position
    only — the same input always yields the same ring.
    """
    total = sum(len(nodes) for _, nodes in sectors)
    if total == 0:
        return {}
    cx = width / 2
    gaps = min(len(sectors), total)
    usable = 360.0 - gaps * gap_deg
    if usable <= 0:
        raise FigureKitError("ego layout: sector gaps consume the ring")
    positions: dict[str, Point] = {}
    angle = -90.0  # start at twelve o'clock, clockwise
    for _relation, nodes in sectors:
        span = usable * (len(nodes) / total)
        step = span / len(nodes)
        for i, key in enumerate(nodes):
            a = math.radians(angle + step * (i + 0.5))
            positions[key] = (cx + radius * math.cos(a), centre_y + radius * math.sin(a))
        angle += span + gap_deg
    return positions


MIN_ROW_PITCH = 10.0
ANCHOR_EDGE_X = 0.36
COUNTERPARTY_EDGE_X = 0.64

__all__ = [
    "ANCHOR_EDGE_X",
    "COUNTERPARTY_EDGE_X",
    "MIN_ROW_PITCH",
    "Point",
    "bipartite_positions",
    "ego_positions",
    "narrow_bipartite_positions",
]

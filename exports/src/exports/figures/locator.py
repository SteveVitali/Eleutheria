# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Locator geometry and index-sprite data (K6 §5.1, JUR-04, SIG-UI-123).

* ``build_locator`` — the small "where this sits" figure: the parent context
  outline (a state for a county dossier, the country for a state) with the
  dossier's own outline drawn inside it. Same projection, same serializer,
  same lexicon — a locator is a figure, not a special case (SIG-UI-066).
* ``build_index_sprite`` — the directory/index glyph sheet: each jurisdiction
  mini-outline fitted into a deterministic grid cell, plus the
  ``sig.figure-index-sprite/1`` data document mapping ``jkey → cell`` so pages
  can cite one glyph without shipping the sheet's siblings.
"""

from __future__ import annotations

from dataclasses import dataclass

from .model import FigureKitError, Outline
from .paths import outline_to_path
from .projection import fit_bounds, outline_bounds, project_outline
from .serialize import El, assert_svg_safe, document, svg_root

LOCATOR_WIDTH = 240
LOCATOR_HEIGHT = 160
SPRITE_CELL_PX = 48
SPRITE_SCHEMA = "sig.figure-index-sprite/1"


def build_locator(
    context_outline: Outline,
    focus_outline: Outline,
    context_name: str,
    focus_name: str,
    *,
    width: int = LOCATOR_WIDTH,
    height: int = LOCATOR_HEIGHT,
    padding: int = 6,
) -> str:
    """The locator figure: context outline + focus outline inside it.

    The focus must sit inside the context's frame — a focus outline outside
    the context bbox is an exporter bug and fails closed.
    """
    if not context_outline or not focus_outline:
        raise FigureKitError("locator needs both context and focus outlines")
    ctx = project_outline(context_outline)
    fcs = project_outline(focus_outline)
    bounds = outline_bounds([ctx])
    fx0, fy0, fx1, fy1 = outline_bounds([fcs])
    if fx0 < bounds[0] or fy0 < bounds[1] or fx1 > bounds[2] or fy1 > bounds[3]:
        raise FigureKitError(
            f"locator focus {focus_name} lies outside context {context_name} bounds"
        )
    frame = fit_bounds(bounds, width, height, padding)

    root = svg_root(
        (frame.width, frame.height),
        ("sig-fig", "sig-fig-locator"),
        "loc-t",
        "loc-d",
    )
    title = El("title")
    title.attr("id", "loc-t")
    title.add(f"{focus_name} within {context_name} — locator map")
    root.add(title)
    desc = El("desc")
    desc.attr("id", "loc-d")
    desc.add(f"Locator map showing {focus_name} inside {context_name}.")
    root.add(desc)

    ctx_view = tuple(tuple(frame.point(x, y) for x, y in ring) for ring in ctx)
    fcs_view = tuple(tuple(frame.point(x, y) for x, y in ring) for ring in fcs)
    ctx_d = outline_to_path(ctx_view)
    fcs_d = outline_to_path(fcs_view)
    if ctx_d is None or fcs_d is None:
        raise FigureKitError("locator outline collapses under the 1.0px perimeter rule")
    ctx_el = El("path")
    ctx_el.attr("d", ctx_d)
    ctx_el.attr("class", "sig-fig-child")
    root.add(ctx_el)
    fcs_el = El("path")
    fcs_el.attr("d", fcs_d)
    fcs_el.attr("class", "sig-fig-area sig-fig-src-corroborated")
    root.add(fcs_el)
    return assert_svg_safe(document(root), allow_style_block=False)


@dataclass(frozen=True)
class SpriteEntry:
    """One glyph in the index sprite."""

    jkey: str
    outline: Outline


def build_index_sprite(
    entries: list[SpriteEntry],
    *,
    columns: int = 8,
    cell_px: int = SPRITE_CELL_PX,
    padding: int = 4,
) -> tuple[str, dict[str, object]]:
    """The jurisdiction glyph sheet + its ``sig.figure-index-sprite/1`` index.

    Every cell is the same square; each outline is fitted inside its cell
    independently, so a glyph never shifts when a neighbour is added (the
    index stays stable across releases — append-only sprite growth).
    """
    if columns < 1 or cell_px < 8:
        raise FigureKitError("sprite needs columns ≥1 and cell_px ≥8")
    if not entries:
        raise FigureKitError("sprite needs at least one jurisdiction")
    jkeys = [e.jkey for e in entries]
    if len(set(jkeys)) != len(jkeys):
        raise FigureKitError("duplicate jkey in sprite entries")

    rows = (len(entries) + columns - 1) // columns
    root = svg_root(
        (columns * cell_px, rows * cell_px),
        ("sig-fig", "sig-fig-sprite"),
        "spr-t",
        "spr-d",
    )
    title = El("title")
    title.attr("id", "spr-t")
    title.add("Jurisdiction outline index")
    root.add(title)
    desc = El("desc")
    desc.attr("id", "spr-d")
    desc.add(f"Index sprite sheet: {len(entries)} jurisdiction outlines.")
    root.add(desc)

    cells: list[dict[str, object]] = []
    for i, entry in enumerate(entries):
        col = i % columns
        row = i // columns
        projected = project_outline(entry.outline)
        bounds = outline_bounds([projected])
        frame = fit_bounds(bounds, cell_px, cell_px, padding)
        view_rings = tuple(
            tuple(
                (
                    frame.padding + col * cell_px + (x - frame.origin_x) * frame.scale,
                    frame.padding + row * cell_px + (frame.origin_y - y) * frame.scale,
                )
                for x, y in ring
            )
            for ring in projected
        )
        d = outline_to_path(view_rings)
        if d is None:
            continue
        cell = El("g")
        cell.attr("class", "sig-fig-sprite-cell")
        path = El("path")
        path.attr("d", d)
        path.attr("class", "sig-fig-child")
        cell.add(path)
        root.add(cell)
        cells.append(
            {
                "jkey": entry.jkey,
                "row": row,
                "col": col,
                "x": col * cell_px,
                "y": row * cell_px,
                "cell_px": cell_px,
            }
        )
    svg = assert_svg_safe(document(root), allow_style_block=False)
    index = {
        "schema": SPRITE_SCHEMA,
        "columns": columns,
        "cell_px": cell_px,
        "rows": rows,
        "glyphs": cells,
    }
    return svg, index


__all__ = [
    "LOCATOR_HEIGHT",
    "LOCATOR_WIDTH",
    "SPRITE_CELL_PX",
    "SPRITE_SCHEMA",
    "SpriteEntry",
    "build_index_sprite",
    "build_locator",
]

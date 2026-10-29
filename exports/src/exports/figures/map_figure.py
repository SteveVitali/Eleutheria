# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``build_map_figure`` — the dossier at-a-glance map pipeline (K6 §5.1).

The one code path every build-time geography figure shares (SIG-UI-066):
project → frame → simplify → bin → emit. What it draws is always the
*published* geometry: the caller hands the kit release bytes and the kit
returns deterministic, CSP-safe SVG plus the figure's ``desc``/metadata
(SIG-UI-094, SIG-UI-134).

Draw order is the K6 §5.1 layer list:

1. child jurisdiction outlines (counties, then places) — absence-hatch fill
   for ``not_covered``, the pending dash for ``rule_pending`` (D-K1-4), the
   drill-down link as a pointer affordance whose accessible twin is the
   places table (``result.children``);
2. the dossier's own outline — the plain boundary, amber-dashed when the
   jurisdiction is provisional;
3. the data layer — tier-0 published points or H3 areas under
   ``static-12px@1``, styled by the corroboration encoding (hollow = one
   source, filled = 2+).
"""

from __future__ import annotations

import gzip
from collections import Counter

import h3

from .binning import RULE_NAME, BinPlan, plan_binning
from .lexicon import Lexicon, load_lexicon
from .model import (
    FigureKitError,
    FigureSizeError,
    FigureSpec,
    MapFigureResult,
    NotDrawn,
    RecordInput,
)
from .paths import marker_glyph_path, outline_to_path, ring_path
from .projection import Frame, fit_bounds, outline_bounds, project, project_outline
from .serialize import El, assert_svg_safe, document, svg_root

#: The K6 fallback ladder for a figure over its declared gzip cap
#: (``cap_actions`` records which rung produced the emitted bytes):
#: 1. simplify child outlines at 1.0 px chord (the recorded first fallback);
#: 2. retry at one coarser H3 resolution (the second, ``h3-res-1``).
CHILD_FALLBACK_TOLERANCE_PX = 1.0


def _partition_records(
    records: tuple[RecordInput, ...],
) -> tuple[list[RecordInput], NotDrawn]:
    """Split the cohort into drawable records and the honest counters —
    every record the figure does not draw is counted exactly once (K6 V-3)."""
    drawable: list[RecordInput] = []
    declared_no_point = 0
    located: Counter[str] = Counter()
    conflicting = 0
    tier3 = 0
    for rec in records:
        if rec.tier == 3:
            tier3 += 1
            continue
        if rec.conflicting:
            conflicting += 1
            continue
        if rec.lat is None or rec.lon is None:
            declared_no_point += 1
            continue
        if rec.located_elsewhere_jkey is not None:
            located[rec.located_elsewhere_jkey] += 1
            continue
        drawable.append(rec)
    return drawable, NotDrawn(
        declared_no_point=declared_no_point,
        located_elsewhere=tuple(sorted(located.items())),
        conflicting=conflicting,
        tier3=tier3,
    )


def _mean_lat(spec: FigureSpec) -> float:
    """The mean vertex latitude across the jurisdiction + child outlines —
    the latitude the metre-per-view-unit conversion is read at."""
    lats: list[float] = []
    for ring in spec.outline:
        lats.extend(lat for _, lat in ring)
    for child in spec.children:
        for ring in child.rings:
            lats.extend(lat for _, lat in ring)
    return sum(lats) / len(lats) if lats else 0.0


def _h3_area_path(cell: str, frame: Frame) -> str | None:
    """One H3 cell → a view-space hexagon path (``cell_to_boundary`` returns
    (lat, lng) pairs — the 12-px rule's drawn area)."""
    boundary = h3.cell_to_boundary(cell)
    ring = tuple(frame.point(*project(lng, lat)) for lat, lng in boundary)
    if len(ring) < 3:
        return None
    return ring_path(ring)


def _data_layer(
    spec: FigureSpec,
    frame: Frame,
    drawable: list[RecordInput],
    plan: BinPlan,
    lexicon: Lexicon,
) -> tuple[El, int]:
    """The data layer group + the drawn-record count."""
    g = El("g")
    g.attr("class", "sig-fig-layer")
    drawn = 0
    if plan.mode == "points":
        for rec in drawable:
            assert rec.lat is not None and rec.lon is not None
            x, y = frame.point(*project(rec.lon, rec.lat))
            p = El("circle")
            p.attr("cx", f"{x:.2f}")
            p.attr("cy", f"{y:.2f}")
            p.attr("r", "3")
            p.attr(
                "class",
                " ".join(
                    [
                        lexicon.check_class("sig-fig-point"),
                        lexicon.corroboration_class(len(rec.sources)),
                    ]
                    + (["sig-fig-provisional"] if rec.provisional else [])
                ),
            )
            g.add(p)
            if rec.contested:
                mark = El("path")
                mark.attr("d", marker_glyph_path(x, y))
                mark.attr("class", "sig-fig-contested")
                g.add(mark)
            drawn += 1
    elif plan.mode == "h3-areas":
        assert plan.cells is not None
        for cell in plan.cells:
            d = _h3_area_path(cell.cell, frame)
            if d is None:
                continue
            p = El("path")
            p.attr("d", d)
            p.attr(
                "class",
                " ".join(
                    [
                        lexicon.check_class("sig-fig-area"),
                        lexicon.corroboration_class(len(cell.sources)),
                    ]
                ),
            )
            g.add(p)
    return g, drawn


def _child_layer(
    spec: FigureSpec, frame: Frame, lexicon: Lexicon, tolerance: float | None
) -> tuple[El, list[dict[str, object]]]:
    """Layer 1 — child outlines, absence-hatch states, drill-down links."""
    g = El("g")
    g.attr("class", "sig-fig-layer")
    meta: list[dict[str, object]] = []
    for child in spec.children:
        projected = project_outline(child.rings)
        view_rings = tuple(tuple(frame.point(x, y) for x, y in ring) for ring in projected)
        d = outline_to_path(view_rings, tolerance=tolerance)
        classes = [lexicon.check_class("sig-fig-child")]
        if child.coverage == "not_covered":
            classes.append(lexicon.check_class("sig-fig-child-uncovered"))
        elif child.coverage == "rule_pending":
            classes.append(lexicon.check_class("sig-fig-child-pending"))
        drawn = d is not None
        if drawn:
            path = El("path")
            path.attr("d", d)
            path.attr("class", " ".join(classes))
            if child.coverage == "not_covered":
                path.attr("fill", "url(#fig-hatch)")
            if child.href:
                # The SVG link is a pointer affordance; its accessible twin is
                # the places-table row (result.children → the page renders the
                # list). Keyboard/screen-reader users never lose the link —
                # they use the table (SIG-UI-131).
                a = El("a")
                a.attr("href", child.href)
                a.attr("aria-hidden", "true")
                a.attr("tabindex", "-1")
                a.attr("focusable", "false")
                a.add(path)
                g.add(a)
            else:
                g.add(path)
        meta.append(
            {
                "jkey": child.jkey,
                "coverage": child.coverage,
                "drawn": drawn,
                "href": child.href,
            }
        )
    return g, meta


def _emit(
    spec: FigureSpec,
    lexicon: Lexicon,
    *,
    child_tolerance: float | None,
    coerce_res: int | None,
) -> tuple[str, Frame, BinPlan, list[dict[str, object]], int, NotDrawn]:
    """One full render pass — the size-cap ladder retries through the
    ``child_tolerance``/``coerce_res`` hooks."""
    drawable, not_drawn = _partition_records(spec.records)

    projected = [project_outline(spec.outline)]
    projected.extend(project_outline(c.rings) for c in spec.children)
    bounds = outline_bounds(projected)
    frame = fit_bounds(bounds, spec.width, spec.max_height, spec.padding_px)

    plan = plan_binning(
        drawable,
        zoom=frame.zoom,
        frame_scale=frame.scale,
        mean_lat=_mean_lat(spec),
        width=spec.width,
        coerce_res=coerce_res,
    )

    root = svg_root(
        (frame.width, frame.height),
        ("sig-fig", "sig-fig-geo", *spec.extra_classes),
        "fig-t",
        "fig-d",
    )
    title = El("title")
    title.attr("id", "fig-t")
    title.add(f"{spec.jurisdiction.name} — at-a-glance map, {spec.release.label}")
    root.add(title)

    n_drawn_total = len(drawable)
    desc_text = (
        f"Map of {spec.jurisdiction.name}. {n_drawn_total} published records "
        f"shown as {plan.mode} under the {RULE_NAME} rule at framing zoom "
        f"{frame.zoom:.1f}. Not drawn: {not_drawn.declared_no_point} declared "
        f"without a published point, {sum(n for _, n in not_drawn.located_elsewhere)} "
        f"located elsewhere, {not_drawn.conflicting} conflicting coordinates, "
        f"{not_drawn.tier3} precision tier 3. Hollow marks mean one source; "
        f"filled marks mean corroborated. Release {spec.release.label}, "
        f"boundaries {spec.boundary_vintage}."
    )
    desc = El("desc")
    desc.attr("id", "fig-d")
    desc.add(desc_text)
    root.add(desc)

    # defs — the absence hatch (hatch means absence only; the four kinds are
    # distinguished in the places table, not by four patterns).
    defs = El("defs")
    hatch = El("pattern")
    hatch.attr("id", "fig-hatch")
    hatch.attr("width", "6")
    hatch.attr("height", "6")
    hatch.attr("patternUnits", "userSpaceOnUse")
    hatch.attr("patternTransform", "rotate(45)")
    hl = El("line")
    hl.attr("x1", "0")
    hl.attr("y1", "0")
    hl.attr("x2", "0")
    hl.attr("y2", "6")
    hl.attr("class", "sig-fig-hatch-line")
    hatch.add(hl)
    defs.add(hatch)
    root.add(defs)

    child_g, child_meta = _child_layer(spec, frame, lexicon, child_tolerance)
    root.add(child_g)

    outline_view = tuple(
        tuple(frame.point(x, y) for x, y in ring) for ring in project_outline(spec.outline)
    )
    outline_d = outline_to_path(outline_view)
    if outline_d is None:
        raise FigureKitError(
            f"{spec.jurisdiction.jkey}: jurisdiction outline collapses under "
            "the 1.0px perimeter rule at this frame — cannot draw its own map"
        )
    outline = El("path")
    outline.attr("d", outline_d)
    outline_classes = ["sig-fig-outline"]
    if spec.jurisdiction.level in ("state", "country"):
        outline_classes.append("sig-fig-outline-state")
    if spec.jurisdiction.provisional:
        outline_classes.append("sig-fig-provisional")
    outline.attr("class", " ".join(lexicon.check_class(c) for c in outline_classes))
    root.add(outline)

    data_g, _drawn = _data_layer(spec, frame, drawable, plan, lexicon)
    root.add(data_g)

    svg = assert_svg_safe(document(root), allow_style_block=False)
    return svg, frame, plan, child_meta, len(drawable), not_drawn


def build_map_figure(spec: FigureSpec, lexicon: Lexicon | None = None) -> MapFigureResult:
    """Build the dossier at-a-glance map — deterministic, CSP-safe bytes plus
    the figure's machine-readable description."""
    lex = lexicon or load_lexicon()
    cap_actions: list[str] = []
    svg, frame, plan, child_meta, drawn, not_drawn = _emit(
        spec, lex, child_tolerance=None, coerce_res=None
    )

    if spec.size_cap_gzip is not None:
        gz = len(gzip.compress(svg.encode("utf-8"), compresslevel=9, mtime=0))
        if gz > spec.size_cap_gzip:
            cap_actions.append("child-outline-tol-1.0px")
            svg, frame, plan, child_meta, drawn, not_drawn = _emit(
                spec, lex, child_tolerance=CHILD_FALLBACK_TOLERANCE_PX, coerce_res=None
            )
            gz = len(gzip.compress(svg.encode("utf-8"), compresslevel=9, mtime=0))
        if gz > spec.size_cap_gzip:
            cap_actions.append("h3-res-minus-1")
            coarser = (plan.h3_res - 1) if plan.h3_res else None
            svg, frame, plan, child_meta, drawn, not_drawn = _emit(
                spec,
                lex,
                child_tolerance=CHILD_FALLBACK_TOLERANCE_PX,
                coerce_res=coarser,
            )
            gz = len(gzip.compress(svg.encode("utf-8"), compresslevel=9, mtime=0))
        if gz > spec.size_cap_gzip:
            raise FigureSizeError(
                f"{spec.jurisdiction.jkey}: figure {gz}B-gzip over cap "
                f"{spec.size_cap_gzip}B after {cap_actions}"
            )
    else:
        gz = len(gzip.compress(svg.encode("utf-8"), compresslevel=9, mtime=0))

    compartments = tuple(sorted({r.compartment for r in spec.records if r.tier != 3}))
    return MapFigureResult(
        svg=svg,
        viewbox=(float(frame.width), float(frame.height)),
        mode=plan.mode,
        zoom=frame.zoom,
        rule=RULE_NAME,
        h3_res=plan.h3_res,
        cap_actions=tuple(cap_actions),
        not_drawn=not_drawn,
        desc={
            "records_drawn": drawn,
            "areas_drawn": len(plan.index_keys) if plan.mode == "h3-areas" else 0,
            "records_total": len(spec.records),
            "jurisdiction": spec.jurisdiction.jkey,
            "release": spec.release.label,
            "publication_id": spec.release.publication_id,
        },
        compartments_drawn=compartments,
        children=tuple(
            {
                "jkey": m["jkey"],
                "coverage": m["coverage"],
                "drawn": m["drawn"],
                "href": m["href"],
            }
            for m in child_meta
        ),  # the places-table rows — the accessible twin of every SVG link
        boundary_vintage=spec.boundary_vintage,
        size_bytes=len(svg.encode("utf-8")),
        gzip_bytes=gz,
    )


__all__ = ["CHILD_FALLBACK_TOLERANCE_PX", "build_map_figure"]

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The network figure emitters (P36.28, FIG-01b; K6 §6.2–6.4, SIG-UI-125).

* ``build_network_figure`` — the two-column bipartite dossier figure:
  anchors down the left, counterparties down the right, edges as cubic
  curves across the explicit central whitespace. Over-cap sides are
  *grouped*, never pruned (K6 §6.2); a figure still over the node cap
  refuses. Wide (720 × ≤ 520) and narrow (360, anchors above
  counterparties) variants emit from the same model.
* ``build_ego_figure`` — the K2 radial ego: centre node, neighbours on one
  ring grouped into per-relation sectors, ≤ 50 nodes.

Both share the honesty rules: every drawn node is an ``<a href>``; edges
draw ``aria-hidden`` as one compound ``<path>`` per edge class (access kind
× currency — K6 §6.3) while the table twin lists the H-2 fields verbatim;
historical/undated edges draw muted ink; observed (double-line) edges emit
two copies offset along each edge's own perpendicular — a true double
stroke a shared transform could not produce; the legend is generated from
the lexicon and lists only encodings present.
"""

from __future__ import annotations

import gzip
import math
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .graph_model import (
    ANCHOR_CAP,
    COUNTERPARTY_CAP,
    EGO_NODE_CAP,
    KIND_NOUNS,
    NARROW_LABEL_CHARS,
    NODE_CAP,
    RESULT_SCHEMA_GRAPH,
    ROW_PITCH,
    WIDE_LABEL_CHARS,
    GraphEdge,
    GraphFigureSpec,
    GraphNode,
    StaticFigureResult,
)
from .layout import bipartite_positions, ego_positions, narrow_bipartite_positions
from .legend import LegendEntry, build_legend_entries
from .lexicon import Lexicon, load_lexicon
from .model import FigureKitError
from .paths import _fmt, marker_glyph_path
from .serialize import El, assert_svg_safe, document, svg_root

# --- shared emit helpers ------------------------------------------------------


def _truncate(label: str, chars: int) -> str:
    return label if len(label) <= chars else label[: chars - 1] + "…"


def kind_shape_path(kind: str, cx: float, cy: float) -> str:
    """The K14 §4.7 shape channel — kind is geometry, never colour."""
    if kind == "vendor":
        h = 4.5
        return (
            f"M{_fmt(cx - h)} {_fmt(cy - h)}L{_fmt(cx + h)} {_fmt(cy - h)}"
            f"L{_fmt(cx + h)} {_fmt(cy + h)}L{_fmt(cx - h)} {_fmt(cy + h)}Z"
        )
    if kind == "product":  # ◆
        h = 5.5
        return (
            f"M{_fmt(cx)} {_fmt(cy - h)}L{_fmt(cx + h)} {_fmt(cy)}"
            f"L{_fmt(cx)} {_fmt(cy + h)}L{_fmt(cx - h)} {_fmt(cy)}Z"
        )
    if kind == "site":  # ▲
        return (
            f"M{_fmt(cx)} {_fmt(cy - 5.0)}L{_fmt(cx + 5.0)} {_fmt(cy + 4.0)}"
            f"L{_fmt(cx - 5.0)} {_fmt(cy + 4.0)}Z"
        )
    if kind == "source":  # ⬟ pentagon
        r = 5.0
        pts = [
            (
                cx + r * math.cos(math.radians(-90 + i * 72)),
                cy + r * math.sin(math.radians(-90 + i * 72)),
            )
            for i in range(5)
        ]
        return "M" + "L".join(f"{_fmt(x)} {_fmt(y)}" for x, y in pts) + "Z"
    if kind == "instrument":  # ▭ policy / contract
        w, h = 6.5, 4.0
        return (
            f"M{_fmt(cx - w)} {_fmt(cy - h)}L{_fmt(cx + w)} {_fmt(cy - h)}"
            f"L{_fmt(cx + w)} {_fmt(cy + h)}L{_fmt(cx - w)} {_fmt(cy + h)}Z"
        )
    if kind == "group":  # the aggregate node — a hollow square
        h = 5.0
        return (
            f"M{_fmt(cx - h)} {_fmt(cy - h)}L{_fmt(cx + h)} {_fmt(cy - h)}"
            f"L{_fmt(cx + h)} {_fmt(cy + h)}L{_fmt(cx - h)} {_fmt(cy + h)}Z"
        )
    # agency / entity — ●
    r = 4.5
    return (
        f"M{_fmt(cx - r)} {_fmt(cy)}a{_fmt(r)} {_fmt(r)} 0 1 0 {_fmt(2 * r)} 0"
        f"a{_fmt(r)} {_fmt(r)} 0 1 0 {_fmt(-2 * r)} 0Z"
    )


def _circle_d(cx: float, cy: float, r: float) -> str:
    return (
        f"M{_fmt(cx - r)} {_fmt(cy)}a{_fmt(r)} {_fmt(r)} 0 1 0 {_fmt(2 * r)} 0"
        f"a{_fmt(r)} {_fmt(r)} 0 1 0 {_fmt(-2 * r)} 0Z"
    )


def _swatch_el(entry: LegendEntry, x: float, y_mid: float) -> El | None:
    """The legend sample for one entry — a miniature of the real mark."""
    cls = " ".join(entry.classes)
    if entry.channel == "line":
        g = El("g")
        offsets = (-1.2, 1.2) if "sig-fig-edge-acc-observed" in entry.classes else (0.0,)
        for off in offsets:
            p = El("path")
            p.attr("d", f"M{_fmt(x)} {_fmt(y_mid + off)}L{_fmt(x + 14)} {_fmt(y_mid + off)}")
            p.attr("class", cls)
            g.add(p)
        return g
    if entry.channel in ("fill", "series"):
        if "sig-fig-child-uncovered" in entry.classes:
            # absence swatch — drawn as its own hatch lines so no figure
            # needs a <defs> pattern just to explain the texture
            g = El("g")
            for off in (-4, 0, 4):
                p = El("path")
                p.attr(
                    "d",
                    f"M{_fmt(x)} {_fmt(y_mid + off + 4)}L{_fmt(x + 14)} {_fmt(y_mid + off - 4)}",
                )
                p.attr("class", "sig-fig-hatch-line")
                g.add(p)
            return g
        r = El("rect")
        r.attr("x", _fmt(x))
        r.attr("y", _fmt(y_mid - 4))
        r.attr("width", "14")
        r.attr("height", "8")
        r.attr("class", cls)
        return r
    if entry.channel == "mark":
        p = El("path")
        if "sig-fig-provisional" in entry.classes:
            p.attr("d", _circle_d(x + 7, y_mid, 4))
            p.attr("class", "sig-fig-point sig-fig-provisional")
        else:
            p.attr("d", marker_glyph_path(x + 7, y_mid, 4))
            p.attr("class", cls)
        return p
    if entry.channel == "shape":
        kind = entry.id.partition(":")[2]
        p = El("path")
        p.attr("d", kind_shape_path(kind, x + 7, y_mid))
        p.attr("class", cls)
        return p
    return None


def _legend_layout(
    entries: tuple[LegendEntry, ...], *, width: float, row_h: float
) -> tuple[list[tuple[LegendEntry, int, float]], int]:
    """Entry → (row, x) — one wrap pass shared by the band renderer and the
    height probe so the legend can never disagree with the box."""
    placed: list[tuple[LegendEntry, int, float]] = []
    cx = 0.0
    row = 0
    for entry in entries:
        item_w = 18 + len(entry.label) * 6.4 + 10
        if cx > 0 and cx + item_w > width:
            row += 1
            cx = 0.0
        placed.append((entry, row, cx))
        cx += item_w
    return placed, row + 1 if entries else 0


def legend_height(entries: tuple[LegendEntry, ...], *, width: float) -> float:
    _, rows = _legend_layout(entries, width=width, row_h=16.0)
    return rows * 16.0


def legend_band(
    entries: tuple[LegendEntry, ...],
    *,
    x: float,
    y: float,
    width: float,
    row_h: float = 16.0,
) -> tuple[El, float]:
    """The in-figure legend strip — the generated entries laid out left to
    right, wrapping to ``row_h`` rows. Returns the group + the band height."""
    g = El("g")
    g.attr("class", "sig-fig-legend")
    placed, rows = _legend_layout(entries, width=width, row_h=row_h)
    for entry, row, lx in placed:
        y_mid = y + row * row_h + row_h / 2
        sw = _swatch_el(entry, x + lx, y_mid)
        if sw is not None:
            g.add(sw)
        t = El("text")
        t.attr("class", "sig-fig-legend")
        t.attr("x", _fmt(x + lx + 18))
        t.attr("y", _fmt(y_mid + 4))
        t.add(entry.label)
        g.add(t)
    return g, rows * row_h


@dataclass(frozen=True)
class _DrawNode:
    """A node as drawn — a spec node or a deterministic group node."""

    key: str
    label: str
    kind: str
    href: str
    members: tuple[str, ...]  # spec node keys the draw node stands for
    contested: bool = False
    provisional: bool = False


def _sort_nodes(nodes: list[GraphNode]) -> list[GraphNode]:
    return sorted(nodes, key=lambda n: (n.label.lower(), n.key))


def _group_side(
    nodes: list[GraphNode],
    *,
    cap: int,
    side_noun: str,
    side: str,
) -> tuple[list[_DrawNode], list[str]]:
    """K6 §6.2's honest fallback: over-cap sides group by the caller's
    declared ``group_*`` fields — never silently pruned, never ranked."""
    ordered = _sort_nodes(nodes)
    if len(ordered) <= cap:
        return (
            [
                _DrawNode(
                    key=n.key,
                    label=n.label,
                    kind=n.kind,
                    href=n.href,
                    members=(n.key,),
                    contested=n.contested,
                    provisional=n.provisional,
                )
                for n in ordered
            ],
            [],
        )
    groups: dict[str, list[GraphNode]] = {}
    for n in ordered:
        if not (n.group_key and n.group_label and n.group_href):
            raise FigureKitError(
                f"{side} side exceeds {cap} nodes and {n.key!r} declares no "
                "group_* fields — group honestly or refuse (never prune)"
            )
        groups.setdefault(n.group_key, []).append(n)
    drawn: list[_DrawNode] = []
    for gkey in sorted(groups):
        members = sorted(groups[gkey], key=lambda n: (n.label.lower(), n.key))
        nouns = sorted({m.noun or KIND_NOUNS[m.kind] for m in members})
        noun = nouns[0] if len(nouns) == 1 else side_noun
        place = members[0].group_label or gkey
        drawn.append(
            _DrawNode(
                key=f"group:{gkey}",
                label=f"{place} — {len(members)} {noun}",
                kind="group",
                href=str(members[0].group_href),
                members=tuple(m.key for m in members),
                contested=any(m.contested for m in members),
                provisional=any(m.provisional for m in members),
            )
        )
    drawn.sort(key=lambda d: (d.label.lower(), d.key))
    action = f"{side}: {len(ordered)} nodes grouped into {len(drawn)} place links"
    return drawn, [action]


def _edge_classes(edge: GraphEdge) -> tuple[str, ...]:
    """The access-kind × currency class pair — the page's ``:has()`` toggle
    hooks (K6 §6.4) and the muted-ink currency channel (K14 §4.7)."""
    cls = ["sig-fig-edge"]
    if edge.access_kind:
        cls.append(f"sig-fig-edge-acc-{edge.access_kind}")
    if edge.currency == "historical" or edge.date_kind == "undated":
        cls.append("sig-fig-edge-muted")
    return tuple(cls)


def _cubic(x1: float, y1: float, x2: float, y2: float) -> str:
    k = (x2 - x1) * 0.5
    return (
        f"M{_fmt(x1)} {_fmt(y1)}C{_fmt(x1 + k)} {_fmt(y1)} "
        f"{_fmt(x2 - k)} {_fmt(y2)} {_fmt(x2)} {_fmt(y2)}"
    )


def _vertical_cubic(x1: float, y1: float, x2: float, y2: float) -> str:
    k = (y2 - y1) * 0.5
    return (
        f"M{_fmt(x1)} {_fmt(y1)}C{_fmt(x1)} {_fmt(y1 + k)} "
        f"{_fmt(x2)} {_fmt(y2 - k)} {_fmt(x2)} {_fmt(y2)}"
    )


def _line(x1: float, y1: float, x2: float, y2: float) -> str:
    return f"M{_fmt(x1)} {_fmt(y1)}L{_fmt(x2)} {_fmt(y2)}"


def _emit_edge_group(
    root: El,
    drawn_edges: list[tuple[float, float, float, float, tuple[str, ...], bool]],
    *,
    curve: Callable[[float, float, float, float], str],
) -> None:
    """The ``<g aria-hidden>`` edge layer — one compound ``<path>`` per edge
    class (kind × currency, K6 §6.3). Observed (double-line) edges are the
    documented exception: each emits two copies offset along its own
    perpendicular, because a shared transform cannot offset every angle."""
    g = El("g")
    g.attr("aria-hidden", "true")
    by_class: dict[tuple[str, ...], list[tuple[float, float, float, float]]] = {}
    marks: list[tuple[float, float]] = []
    for x1, y1, x2, y2, classes, contested in drawn_edges:
        by_class.setdefault(classes, []).append((x1, y1, x2, y2))
        if contested:
            marks.append(((x1 + x2) / 2, (y1 + y2) / 2))
    for classes in sorted(by_class):
        segs = by_class[classes]
        cls = " ".join(classes)
        if "sig-fig-edge-acc-observed" in classes:
            for x1, y1, x2, y2 in segs:
                d = curve(x1, y1, x2, y2)
                length = math.hypot(x2 - x1, y2 - y1) or 1.0
                nx, ny = -(y2 - y1) / length * 1.1, (x2 - x1) / length * 1.1
                for ox, oy in ((nx, ny), (-nx, -ny)):
                    p = El("path")
                    p.attr("d", d)
                    p.attr("transform", f"translate({_fmt(ox)} {_fmt(oy)})")
                    p.attr("class", cls)
                    g.add(p)
        else:
            p = El("path")
            p.attr("d", "".join(curve(*seg) for seg in segs))
            p.attr("class", cls)
            g.add(p)
    for mx, my in marks:
        mark = El("path")
        mark.attr("d", marker_glyph_path(mx, my, 4))
        mark.attr("class", "sig-fig-contested")
        g.add(mark)
    root.add(g)


def _emit_node(
    root: El,
    node: _DrawNode,
    cx: float,
    cy: float,
    *,
    label_x: float,
    anchor: str,
    label_chars: int,
    extra_class: str = "",
) -> None:
    """One node: ``<a href>`` wrapping shape + truncated label (the full
    label is the link's ``aria-label``; the twin carries the words)."""
    a = El("a")
    a.attr("href", node.href)
    a.attr("aria-label", node.label)
    classes = f"sig-fig-node sig-fig-node-{node.kind}"
    if extra_class:
        classes += f" {extra_class}"
    p = El("path")
    p.attr("d", kind_shape_path(node.kind, cx, cy))
    p.attr("class", classes)
    a.add(p)
    if node.contested:
        m = El("path")
        m.attr("d", marker_glyph_path(cx, cy - 9, 3))
        m.attr("class", "sig-fig-contested")
        a.add(m)
    if node.provisional:
        pv = El("path")
        pv.attr("d", _circle_d(cx, cy, 7))
        pv.attr("class", "sig-fig-provisional")
        a.add(pv)
    t = El("text")
    t.attr("class", "sig-fig-node-label")
    t.attr("x", _fmt(label_x))
    t.attr("y", _fmt(cy + 4))
    t.attr("text-anchor", anchor)
    t.add(_truncate(node.label, label_chars))
    a.add(t)
    root.add(a)


def _figure_root(
    viewbox: tuple[float, float],
    classes: tuple[str, ...],
    ids: tuple[str, str],
    title_text: str,
    desc_text: str,
) -> El:
    root = svg_root(viewbox, classes, ids[0], ids[1])
    title = El("title")
    title.attr("id", ids[0])
    title.add(title_text)
    root.add(title)
    desc = El("desc")
    desc.attr("id", ids[1])
    desc.add(desc_text)
    root.add(desc)
    return root


def _meta_size(svg: str) -> tuple[int, int]:
    raw = svg.encode("utf-8")
    return len(raw), len(gzip.compress(raw, compresslevel=9))


# --- the bipartite dossier figure ---------------------------------------------


def _prepare_network(
    spec: GraphFigureSpec,
) -> tuple[
    list[_DrawNode],
    list[_DrawNode],
    list[GraphEdge],
    dict[str, str],
    list[str],
]:
    anchors = [n for n in spec.nodes if n.side == "anchor"]
    counterparties = [n for n in spec.nodes if n.side == "counterparty"]
    if not anchors:
        raise FigureKitError("network figure needs ≥1 anchor node")
    sides = {n.key: n.side for n in spec.nodes}
    for i, e in enumerate(spec.edges):
        if sides[e.source] == sides[e.target]:
            raise FigureKitError(f"edges[{i}] connects two {sides[e.source]} nodes")
    a_drawn, a_actions = _group_side(
        anchors, cap=ANCHOR_CAP, side_noun=spec.anchor_noun, side="anchor"
    )
    c_drawn, c_actions = _group_side(
        counterparties,
        cap=COUNTERPARTY_CAP,
        side_noun=spec.counterparty_noun,
        side="counterparty",
    )
    if len(a_drawn) > ANCHOR_CAP or len(c_drawn) > COUNTERPARTY_CAP:
        raise FigureKitError(
            "grouped figure still exceeds K6's row caps — declare coarser group keys"
        )
    if len(a_drawn) + len(c_drawn) > NODE_CAP:
        raise FigureKitError(
            f"figure exceeds the {NODE_CAP}-node cap after grouping — refuse, "
            "never a national hairball (K6 §6.2)"
        )
    remap: dict[str, str] = {}
    for d in a_drawn + c_drawn:
        for m in d.members:
            remap[m] = d.key
    return a_drawn, c_drawn, list(spec.edges), remap, a_actions + c_actions


def _drawn_edge_paths(
    spec_edges: list[GraphEdge],
    remap: dict[str, str],
    positions: dict[str, tuple[float, float]],
) -> list[tuple[float, float, float, float, tuple[str, ...], bool]]:
    """Rewire spec edges through groups and dedupe to one drawn curve per
    (drawn pair, access kind, currency class) — K6 §6.3's class DOM."""
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    contested_pairs: set[tuple[str, str]] = set()
    out = []
    for e in spec_edges:
        s, t = remap[e.source], remap[e.target]
        cls = _edge_classes(e)
        if e.contested:
            contested_pairs.add((s, t))
        key = (s, t, cls)
        if key in seen:
            continue
        seen.add(key)
        x1, y1 = positions[s]
        x2, y2 = positions[t]
        out.append((x1, y1, x2, y2, cls, (s, t)))
    return [(x1, y1, x2, y2, cls, pair in contested_pairs) for x1, y1, x2, y2, cls, pair in out]


def spec_edges_sorted(spec: GraphFigureSpec) -> list[GraphEdge]:
    return sorted(
        spec.edges,
        key=lambda e: (e.source, e.target, e.relation, e.date or "", e.access_kind or ""),
    )


def _table_rows(spec: GraphFigureSpec) -> list[dict[str, Any]]:
    """The H-2 edge table — verbatim fields per *spec* edge (real
    counterparties, never the group labels)."""
    nodes = {n.key: n for n in spec.nodes}
    rows = []
    for e in spec_edges_sorted(spec):
        cp_key = e.target if nodes[e.source].side in ("anchor", "centre") else e.source
        cp = nodes[cp_key]
        rows.append(
            {
                "counterparty": cp.label,
                "href": cp.href,
                "relation": e.relation,
                "direction": e.direction,
                "access_kind": e.access_kind if e.access_kind else "—",
                "date": e.date if e.date else "—",
                "date_kind": e.date_kind,
                "currency": e.currency,
                "support": e.support if e.support else "—",
                "sources": len(e.sources),
                "evidence": list(e.claim_ids),
            }
        )
    return rows


def _present_tokens(drawn: list[_DrawNode], spec: GraphFigureSpec) -> list[str]:
    present: list[str] = [f"kind:{k}" for k in sorted({d.kind for d in drawn})]
    for e in spec.edges:
        present.append(f"line:{e.access_kind}" if e.access_kind else "line:relation")
        if e.currency == "historical" or e.date_kind == "undated":
            present.append("currency:muted")
        if e.contested:
            present.append("mark:contested")
    if any(d.contested for d in drawn):
        present.append("mark:contested")
    if any(d.provisional for d in drawn):
        present.append("mark:provisional")
    return present


_TABLE_COLUMNS = (
    "counterparty",
    "relation",
    "direction",
    "access_kind",
    "date",
    "date_kind",
    "currency",
    "support",
    "sources",
    "evidence",
)


def build_network_figure(
    spec: GraphFigureSpec, lexicon: Lexicon | None = None
) -> StaticFigureResult:
    """The bipartite dossier network figure — wide + narrow SVGs, generated
    legend, H-2 table twin (K6 §6.2, SIG-UI-125/DV03)."""
    lex = lexicon or load_lexicon()
    if spec.kind != "network":
        raise FigureKitError(f"kind {spec.kind!r} is not a network spec")
    a_drawn, c_drawn, spec_edges, remap, actions = _prepare_network(spec)

    entries = build_legend_entries(_present_tokens(a_drawn + c_drawn, spec), lex)
    legend_ids = {e.id for e in entries}

    # --- wide --------------------------------------------------------------
    a_keys = tuple(d.key for d in a_drawn)
    c_keys = tuple(d.key for d in c_drawn)
    apos, cpos, area_h = bipartite_positions(a_keys, c_keys, width=spec.width, row_pitch=ROW_PITCH)
    drawn = _drawn_edge_paths(spec_edges, remap, {**apos, **cpos})

    legend_h = legend_height(entries, width=spec.width - 16)
    height = 8 + area_h + legend_h + 8
    if height > spec.max_height:
        raise FigureKitError(
            f"figure is {_fmt(height)}px tall — over the {spec.max_height}px box "
            "(K6 §6.2: group further or the figure does not fit)"
        )
    root = _figure_root(
        (spec.width, height),
        ("sig-fig", "sig-fig-graph"),
        ("net-t", "net-d"),
        spec.title,
        f"{spec.title}: {len(a_drawn)} anchors and {len(c_drawn)} counterparties "
        f"linked by {len(spec_edges)} recorded relations"
        + (
            "; some edges are historical or undated (muted)"
            if "currency:muted" in legend_ids
            else ""
        )
        + ".",
    )
    _emit_edge_group(root, drawn, curve=_cubic)
    for i, d in enumerate(a_drawn):
        y = 8 + i * ROW_PITCH + ROW_PITCH / 2
        _emit_node(root, d, 14, y, label_x=26, anchor="start", label_chars=WIDE_LABEL_CHARS)
    for i, d in enumerate(c_drawn):
        y = 8 + i * ROW_PITCH + ROW_PITCH / 2
        _emit_node(
            root,
            d,
            spec.width - 14,
            y,
            label_x=spec.width - 26,
            anchor="end",
            label_chars=WIDE_LABEL_CHARS,
        )
    band, _ = legend_band(entries, x=8, y=8 + area_h + 4, width=spec.width - 16)
    root.add(band)
    svg = assert_svg_safe(document(root), allow_style_block=False)

    # --- narrow (360, anchors above counterparties) --------------------------
    napos, ncpos, n_area = narrow_bipartite_positions(a_keys, c_keys, width=spec.narrow_width)
    ndrawn = _drawn_edge_paths(spec_edges, remap, {**napos, **ncpos})
    n_legend_h = legend_height(entries, width=spec.narrow_width - 16)
    n_height = 8 + n_area + n_legend_h + 8
    nroot = _figure_root(
        (spec.narrow_width, n_height),
        ("sig-fig", "sig-fig-graph"),
        ("netn-t", "netn-d"),
        spec.title,
        f"{spec.title} (narrow variant): {len(a_drawn)} anchors, "
        f"{len(c_drawn)} counterparties, {len(spec_edges)} recorded relations.",
    )
    _emit_edge_group(nroot, ndrawn, curve=_vertical_cubic)
    for d in a_drawn:
        x, y = napos[d.key]
        _emit_node(nroot, d, x, y, label_x=x + 10, anchor="start", label_chars=NARROW_LABEL_CHARS)
    for d in c_drawn:
        x, y = ncpos[d.key]
        _emit_node(nroot, d, x, y, label_x=x + 10, anchor="start", label_chars=NARROW_LABEL_CHARS)
    nband, _ = legend_band(entries, x=8, y=8 + n_area + 4, width=spec.narrow_width - 16)
    nroot.add(nband)
    svg_narrow = assert_svg_safe(document(nroot), allow_style_block=False)

    size, gz = _meta_size(svg)
    return StaticFigureResult(
        svg=svg,
        svg_narrow=svg_narrow,
        viewbox=(spec.width, height),
        narrow_viewbox=(spec.narrow_width, n_height),
        mode="bipartite",
        cap_actions=tuple(actions),
        legend=tuple(e.to_json() for e in entries),
        table_columns=_TABLE_COLUMNS,
        table_rows=tuple(_table_rows(spec)),
        node_count=len(a_drawn) + len(c_drawn),
        edge_count=len(spec_edges),
        desc={
            "title": spec.title,
            "as_of_world": spec.release.as_of_world,
            "anchors": len(a_drawn),
            "counterparties": len(c_drawn),
            "edges": len(spec_edges),
            "drawn_edges": len(drawn),
        },
        size_bytes=size,
        gzip_bytes=gz,
        result_schema=RESULT_SCHEMA_GRAPH,
    )


# --- the radial ego figure ------------------------------------------------------


def build_ego_figure(spec: GraphFigureSpec, lexicon: Lexicon | None = None) -> StaticFigureResult:
    """The entity-page radial ego: centre + 1-hop neighbours in per-relation
    sectors on one ring (K2's 50-node ego, deterministic angles)."""
    lex = lexicon or load_lexicon()
    if spec.kind != "ego":
        raise FigureKitError(f"kind {spec.kind!r} is not an ego spec")
    centres = [n for n in spec.nodes if n.side == "centre"]
    neighbours = [n for n in spec.nodes if n.side == "neighbour"]
    if len(centres) != 1 or not neighbours:
        raise FigureKitError("ego figure needs exactly one centre and ≥1 neighbour")
    if len(spec.nodes) > EGO_NODE_CAP:
        raise FigureKitError(
            f"ego figure has {len(spec.nodes)} nodes — over the {EGO_NODE_CAP} "
            "node cap; the exporter must pre-aggregate (K2)"
        )
    centre = centres[0]
    sides = {n.key: n.side for n in spec.nodes}
    relation_of: dict[str, str] = {}
    for i, e in enumerate(spec.edges):
        if centre.key not in (e.source, e.target):
            raise FigureKitError(f"edges[{i}] is not a 1-hop centre edge")
        other = e.target if e.source == centre.key else e.source
        if sides[other] != "neighbour":
            raise FigureKitError(f"edges[{i}] endpoint {other!r} is not a neighbour")
        relation_of.setdefault(other, e.relation)
    for n in neighbours:
        if n.key not in relation_of:
            raise FigureKitError(
                f"neighbour {n.key!r} carries no centre edge — every ego node links"
            )

    sector_map: dict[str, list[GraphNode]] = {}
    for n in neighbours:
        sector_map.setdefault(relation_of[n.key], []).append(n)
    sectors = tuple((rel, tuple(_sort_nodes(nodes))) for rel, nodes in sorted(sector_map.items()))

    entries = build_legend_entries(
        _present_tokens(
            [
                _DrawNode(
                    key=n.key,
                    label=n.label,
                    kind=n.kind,
                    href=n.href,
                    members=(n.key,),
                    contested=n.contested,
                    provisional=n.provisional,
                )
                for n in spec.nodes
            ],
            spec,
        ),
        lex,
    )

    def _emit(
        width: float, label_chars: int, ids: tuple[str, str]
    ) -> tuple[str, tuple[float, float]]:
        radius = width / 2 - 56
        centre_y = radius + 46
        l_h = legend_height(entries, width=width - 16)
        height = 2 * centre_y + l_h + 8
        root = _figure_root(
            (width, height),
            ("sig-fig", "sig-fig-ego"),
            ids,
            spec.title,
            f"{spec.title}: {len(neighbours)} neighbours in {len(sectors)} "
            f"relation sectors around {centre.label}.",
        )
        pos = ego_positions(
            tuple((rel, tuple(n.key for n in nodes)) for rel, nodes in sectors),
            width=width,
            centre_y=centre_y,
            radius=radius,
        )
        cx, cy = width / 2, centre_y

        # sector guide arcs + direct relation labels (K2: sectors per relation)
        total = len(neighbours)
        gap_deg = 8.0
        usable = 360.0 - len(sectors) * gap_deg
        angle = -90.0
        sg = El("g")
        sg.attr("aria-hidden", "true")
        for rel, nodes in sectors:
            span = usable * (len(nodes) / total)
            a0 = math.radians(angle)
            a1 = math.radians(angle + span)
            r_arc = radius + 14
            x0, y0 = cx + r_arc * math.cos(a0), cy + r_arc * math.sin(a0)
            x1, y1 = cx + r_arc * math.cos(a1), cy + r_arc * math.sin(a1)
            arc = El("path")
            arc.attr(
                "d",
                f"M{_fmt(x0)} {_fmt(y0)}A{_fmt(r_arc)} {_fmt(r_arc)} 0 "
                f"{1 if span > 180 else 0} 1 {_fmt(x1)} {_fmt(y1)}",
            )
            arc.attr("class", "sig-fig-sector")
            sg.add(arc)
            mid = math.radians(angle + span / 2)
            lr = radius + 32
            t = El("text")
            t.attr("class", "sig-fig-axis-label")
            t.attr("x", _fmt(cx + lr * math.cos(mid)))
            t.attr("y", _fmt(cy + lr * math.sin(mid) + 4))
            t.attr("text-anchor", "start" if math.cos(mid) >= 0 else "end")
            t.add(rel)
            sg.add(t)
            angle += span + gap_deg
        root.add(sg)

        # edges: centre → neighbour, class-grouped compound paths
        drawn = []
        for e in spec_edges_sorted(spec):
            other = e.target if e.source == centre.key else e.source
            x2, y2 = pos[other]
            drawn.append((cx, cy, x2, y2, _edge_classes(e), e.contested))
        _emit_edge_group(root, drawn, curve=_line)

        # centre node
        a = El("a")
        a.attr("href", centre.href)
        a.attr("aria-label", centre.label)
        cp = El("path")
        cp.attr("d", _circle_d(cx, cy, 6))
        cp.attr("class", f"sig-fig-node sig-fig-node-{centre.kind} sig-fig-centre")
        a.add(cp)
        ct = El("text")
        ct.attr("class", "sig-fig-node-label")
        ct.attr("x", _fmt(cx))
        ct.attr("y", _fmt(cy + 19))
        ct.attr("text-anchor", "middle")
        ct.add(_truncate(centre.label, label_chars))
        a.add(ct)
        root.add(a)

        for _rel, nodes in sectors:
            for n in nodes:
                x, y = pos[n.key]
                outward = x >= cx
                nd = _DrawNode(
                    key=n.key,
                    label=n.label,
                    kind=n.kind,
                    href=n.href,
                    members=(n.key,),
                    contested=n.contested,
                    provisional=n.provisional,
                )
                _emit_node(
                    root,
                    nd,
                    x,
                    y,
                    label_x=x + 9 if outward else x - 9,
                    anchor="start" if outward else "end",
                    label_chars=label_chars,
                    extra_class="sig-fig-neighbour",
                )

        band, _ = legend_band(entries, x=8, y=2 * centre_y + 4, width=width - 16)
        root.add(band)
        svg = assert_svg_safe(document(root), allow_style_block=False)
        return svg, (width, height)

    svg_wide, vb_wide = _emit(spec.width, WIDE_LABEL_CHARS, ("ego-t", "ego-d"))
    svg_narrow, vb_narrow = _emit(spec.narrow_width, NARROW_LABEL_CHARS, ("egon-t", "egon-d"))

    size, gz = _meta_size(svg_wide)
    return StaticFigureResult(
        svg=svg_wide,
        svg_narrow=svg_narrow,
        viewbox=vb_wide,
        narrow_viewbox=vb_narrow,
        mode="ego-radial",
        cap_actions=(),
        legend=tuple(e.to_json() for e in entries),
        table_columns=_TABLE_COLUMNS,
        table_rows=tuple(_table_rows(spec)),
        node_count=len(spec.nodes),
        edge_count=len(spec.edges),
        desc={
            "title": spec.title,
            "as_of_world": spec.release.as_of_world,
            "centre": centre.label,
            "neighbours": len(neighbours),
            "sectors": [rel for rel, _ in sectors],
            "edges": len(spec.edges),
        },
        size_bytes=size,
        gzip_bytes=gz,
        result_schema=RESULT_SCHEMA_GRAPH,
    )


__all__ = [
    "build_ego_figure",
    "build_network_figure",
    "kind_shape_path",
    "legend_band",
    "legend_height",
]

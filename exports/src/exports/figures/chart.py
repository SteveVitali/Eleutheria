# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The chart figure emitters (P36.28, FIG-01b; K14 §4.7 "chart anatomy").

Four chart kinds on the K14 anatomy — one axis, direct labels, thin marks
(2 px strokes, markers ≥ 8 px, a 2 px gap between stacked fills), the
lexicon's encodings only, and a table twin carrying the exact values every
time (SIG-UI-131 parity: the chart never carries data a reader cannot
reach another way):

* ``bar`` — horizontal bars, category labels on the axis, each bar's value
  labelled directly at its end;
* ``stacked-bar`` — vertical columns stacked per series (≤ 9 series — the
  K5 "top 8 + other" ceiling; the ninth step is the neutral aggregate);
* ``strip`` — a run of unlabelled ≥ 8 px markers on a time axis (each
  marker an ``<a>`` where the caller names an href);
* ``timeline`` — the same axis with alternating above/below event labels.

Wide (720) + narrow (360) variants emit from the same spec; undated events
and negative values fail closed — a chart never silently approximates
(SIG-ENG-042).
"""

from __future__ import annotations

import datetime as _dt
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graph_model import StaticFigureResult
from .legend import LegendEntry, build_legend_entries
from .lexicon import Lexicon, load_lexicon
from .model import FigureKitError, ReleaseInfo
from .network_figure import (
    _figure_root,
    _fmt,
    _meta_size,
    _truncate,
    legend_band,
    legend_height,
)
from .serialize import El, assert_svg_safe, document

#: The chart-figure input contract id (P36.28).
INPUT_SCHEMA_CHART = "sig.figure-kit-chart/1"
RESULT_SCHEMA_CHART = "sig.figure-chart-meta/1"

CHART_KINDS = ("bar", "stacked-bar", "strip", "timeline")
SERIES_CAP = 9  # K5's "top 8 + other" ceiling
_CATEGORY_CAP = 48
_EVENT_CAP = 80
_BAR_PITCH = 20.0
_BAR_HEIGHT = 16.0
_STACK_GAP = 2.0  # the 2 px gap between fills (K14 §4.7)
_MARK_R = 4.5  # ≥ 8 px markers


@dataclass(frozen=True)
class ChartCategory:
    label: str
    values: tuple[float, ...]  # one per series (exactly one for `bar`)
    href: str | None = None


@dataclass(frozen=True)
class ChartEvent:
    date: str  # ISO date — required: an undated event cannot sit on a time axis
    label: str
    href: str | None = None
    kind: str | None = None


@dataclass(frozen=True)
class ChartSpec:
    release: ReleaseInfo
    kind: str
    title: str
    unit: str
    categories: tuple[ChartCategory, ...]
    series: tuple[str, ...]
    events: tuple[ChartEvent, ...]
    width: int = 720
    narrow_width: int = 360


def _fnum(v: float) -> str:
    """A direct value label — integers print without the fraction."""
    return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else str(int(v))


def _axis(root: El, x1: float, y1: float, x2: float, y2: float) -> None:
    p = El("path")
    p.attr("d", f"M{_fmt(x1)} {_fmt(y1)}L{_fmt(x2)} {_fmt(y2)}")
    p.attr("class", "sig-fig-axis")
    root.add(p)


def _tick_label(root: El, x: float, y: float, text: str, anchor: str = "middle") -> None:
    t = El("text")
    t.attr("class", "sig-fig-axis-label")
    t.attr("x", _fmt(x))
    t.attr("y", _fmt(y))
    t.attr("text-anchor", anchor)
    t.add(text)
    root.add(t)


def _bar_emit(
    spec: ChartSpec, width: float, label_chars: int, ids: tuple[str, str]
) -> tuple[str, tuple[float, float]]:
    cats = spec.categories
    if not cats:
        raise FigureKitError("bar chart needs ≥1 category")
    if len(cats) > _CATEGORY_CAP:
        raise FigureKitError(f"bar chart exceeds {_CATEGORY_CAP} categories")
    vmax = max(c.values[0] for c in cats)
    if vmax <= 0:
        raise FigureKitError("bar chart has no positive values — nothing to draw")
    label_w = 24 + min(label_chars, 28) * 6.4
    plot_w = width - label_w - 96
    if plot_w < 80:
        raise FigureKitError("bar plot narrower than 80px — widen the viewBox")
    scale = plot_w / vmax
    axis_h = 22.0
    height = 8 + len(cats) * _BAR_PITCH + axis_h + 8
    root = _figure_root(
        (width, height),
        ("sig-fig", "sig-fig-chart"),
        ids,
        spec.title,
        f"{spec.title}: {len(cats)} categories, largest {_fnum(vmax)} {spec.unit}. "
        "The table twin carries every value.",
    )
    for i, c in enumerate(cats):
        v = c.values[0]
        y = 8 + i * _BAR_PITCH
        bar_w = max(v * scale, 0.0)
        body = El("a") if c.href else El("g")
        if c.href:
            body.attr("href", c.href)
            body.attr("aria-label", f"{c.label}: {_fnum(v)} {spec.unit}")
        _tick_label(body, label_w - 6, y + _BAR_HEIGHT - 4, _truncate(c.label, label_chars), "end")
        r = El("rect")
        r.attr("x", _fmt(label_w))
        r.attr("y", _fmt(y))
        r.attr("width", _fmt(bar_w))
        r.attr("height", _fmt(_BAR_HEIGHT))
        r.attr("class", "sig-fig-bar")
        body.add(r)
        _tick_label(body, label_w + bar_w + 6, y + _BAR_HEIGHT - 4, _fnum(v), "start")
        root.add(body)
    base_y = 8 + len(cats) * _BAR_PITCH
    _axis(root, label_w, 8, label_w, base_y + 2)
    _axis(root, label_w, base_y + 2, label_w + plot_w, base_y + 2)
    _tick_label(root, label_w, base_y + axis_h - 4, "0", "middle")
    _tick_label(root, label_w + plot_w, base_y + axis_h - 4, _fnum(vmax), "middle")
    svg = assert_svg_safe(document(root), allow_style_block=False)
    return svg, (width, height)


def _stacked_emit(
    spec: ChartSpec,
    width: float,
    label_chars: int,
    ids: tuple[str, str],
    entries: tuple[LegendEntry, ...],
) -> tuple[str, tuple[float, float]]:
    cats = spec.categories
    nser = len(spec.series)
    if not cats:
        raise FigureKitError("stacked-bar chart needs ≥1 category")
    if nser < 1 or nser > SERIES_CAP:
        raise FigureKitError(f"stacked-bar needs 1–{SERIES_CAP} series, got {nser}")
    if len(cats) > _CATEGORY_CAP:
        raise FigureKitError(f"stacked-bar exceeds {_CATEGORY_CAP} categories")
    totals = [sum(c.values) for c in cats]
    vmax = max(totals)
    if vmax <= 0:
        raise FigureKitError("stacked-bar has no positive totals — nothing to draw")
    pad_l, pad_r, pad_t = 44.0, 8.0, 8.0
    legend_h = legend_height(entries, width=width - 16)
    axis_h = 24.0
    plot_h = 180.0
    height = pad_t + plot_h + axis_h + legend_h + 8
    plot_w = width - pad_l - pad_r
    slot = plot_w / len(cats)
    col_w = min(slot * 0.62, 64.0)
    root = _figure_root(
        (width, height),
        ("sig-fig", "sig-fig-chart"),
        ids,
        spec.title,
        f"{spec.title}: {len(cats)} columns × {nser} series, largest total "
        f"{_fnum(vmax)} {spec.unit}. The table twin carries every segment.",
    )
    y0 = pad_t + plot_h
    for i, c in enumerate(cats):
        x0 = pad_l + i * slot + (slot - col_w) / 2
        if c.href:
            col = El("a")
            col.attr("href", c.href)
            col.attr("aria-label", f"{c.label}: {_fnum(totals[i])} {spec.unit}")
        else:
            col = El("g")
        acc = 0.0
        for si, v in enumerate(c.values):
            if v <= 0:
                continue
            seg_h = v / vmax * plot_h
            r = El("rect")
            r.attr("x", _fmt(x0))
            r.attr("y", _fmt(y0 - acc - seg_h + _STACK_GAP / 2))
            r.attr("width", _fmt(col_w))
            r.attr("height", _fmt(max(seg_h - _STACK_GAP, 0.5)))
            r.attr("class", f"sig-fig-series-{si}")
            col.add(r)
            acc += seg_h
        root.add(col)
        _tick_label(
            root,
            pad_l + i * slot + slot / 2,
            y0 + 14,
            _truncate(c.label, label_chars),
            "middle",
        )
    _axis(root, pad_l - 4, pad_t, pad_l - 4, y0)
    _axis(root, pad_l - 4, y0, pad_l + plot_w, y0)
    _tick_label(root, pad_l - 8, y0 + 4, "0", "end")
    _tick_label(root, pad_l - 8, pad_t + 8, _fnum(vmax), "end")
    band, _ = legend_band(entries, x=pad_l, y=y0 + axis_h, width=width - pad_l - 8)
    root.add(band)
    svg = assert_svg_safe(document(root), allow_style_block=False)
    return svg, (width, height)


def _ordinal(iso: str) -> int:
    try:
        return _dt.date.fromisoformat(iso).toordinal()
    except ValueError as e:
        raise FigureKitError(f"event date {iso!r} is not ISO YYYY-MM-DD") from e


def _time_positions(
    events: list[ChartEvent] | tuple[ChartEvent, ...], lo_x: float, hi_x: float
) -> list[float]:
    days = [_ordinal(e.date) for e in events]
    d0, d1 = min(days), max(days)
    if d0 == d1:
        return [(lo_x + hi_x) / 2] * len(events)
    return [lo_x + (d - d0) / (d1 - d0) * (hi_x - lo_x) for d in days]


def _strip_emit(
    spec: ChartSpec, width: float, label_chars: int, ids: tuple[str, str]
) -> tuple[str, tuple[float, float]]:
    events = sorted(spec.events, key=lambda e: (e.date, e.label))
    if not events:
        raise FigureKitError("strip chart needs ≥1 event")
    if len(events) > _EVENT_CAP:
        raise FigureKitError(f"strip chart exceeds {_EVENT_CAP} events")
    pad_l, pad_r = 16.0, 16.0
    lo_x, hi_x = pad_l + 8, width - pad_r - 8
    xs = _time_positions(events, lo_x, hi_x)
    axis_y = 56.0
    axis_h = 30.0
    height = axis_y + 14 + axis_h + 8
    root = _figure_root(
        (width, height),
        ("sig-fig", "sig-fig-chart"),
        ids,
        spec.title,
        f"{spec.title}: {len(events)} events from {events[0].date} to "
        f"{events[-1].date}. The table twin lists each one.",
    )
    _axis(root, lo_x - 8, axis_y, hi_x + 8, axis_y)
    # same-day events stack into 10px lanes (deterministic by sort order)
    lanes: dict[str, int] = {}
    for i, e in enumerate(events):
        lane = lanes.get(e.date, 0)
        lanes[e.date] = lane + 1
        my = axis_y - 8 - lane * 10
        body = El("a") if e.href else El("g")
        if e.href:
            body.attr("href", e.href)
            body.attr("aria-label", f"{e.date}: {e.label}")
        m = El("path")
        m.attr(
            "d",
            f"M{_fmt(xs[i] - _MARK_R)} {_fmt(my)}a{_fmt(_MARK_R)} {_fmt(_MARK_R)} 0 1 0 "
            f"{_fmt(2 * _MARK_R)} 0a{_fmt(_MARK_R)} {_fmt(_MARK_R)} 0 1 0 "
            f"{_fmt(-2 * _MARK_R)} 0Z",
        )
        m.attr("class", "sig-fig-mark")
        body.add(m)
        root.add(body)
    _tick_label(root, lo_x - 8, axis_y + 22, events[0].date, "start")
    _tick_label(root, hi_x + 8, axis_y + 22, events[-1].date, "end")
    svg = assert_svg_safe(document(root), allow_style_block=False)
    return svg, (width, height)


def _timeline_emit(
    spec: ChartSpec, width: float, label_chars: int, ids: tuple[str, str]
) -> tuple[str, tuple[float, float]]:
    events = sorted(spec.events, key=lambda e: (e.date, e.label))
    if not events:
        raise FigureKitError("timeline needs ≥1 event")
    if len(events) > _EVENT_CAP:
        raise FigureKitError(f"timeline exceeds {_EVENT_CAP} events")
    pad_l, pad_r = 16.0, 16.0
    lo_x, hi_x = pad_l + 8, width - pad_r - 8
    xs = _time_positions(events, lo_x, hi_x)
    axis_y = 120.0
    axis_h = 24.0
    height = axis_y * 2 + axis_h
    root = _figure_root(
        (width, height),
        ("sig-fig", "sig-fig-chart"),
        ids,
        spec.title,
        f"{spec.title}: {len(events)} dated events from {events[0].date} to "
        f"{events[-1].date}. The table twin lists each one.",
    )
    _axis(root, lo_x - 8, axis_y, hi_x + 8, axis_y)
    for i, e in enumerate(events):
        above = i % 2 == 0
        my = axis_y - 14 if above else axis_y + 14
        stem_top = axis_y - 8 if above else axis_y
        stem_bot = axis_y if above else axis_y + 8
        body = El("a") if e.href else El("g")
        if e.href:
            body.attr("href", e.href)
            body.attr("aria-label", f"{e.date}: {e.label}")
        stem = El("path")
        stem.attr("d", f"M{_fmt(xs[i])} {_fmt(stem_top)}L{_fmt(xs[i])} {_fmt(stem_bot)}")
        stem.attr("class", "sig-fig-axis")
        body.add(stem)
        m = El("path")
        m.attr(
            "d",
            f"M{_fmt(xs[i] - _MARK_R)} {_fmt(my - _MARK_R)}L{_fmt(xs[i] + _MARK_R)} "
            f"{_fmt(my - _MARK_R)}L{_fmt(xs[i] + _MARK_R)} {_fmt(my + _MARK_R)}"
            f"L{_fmt(xs[i] - _MARK_R)} {_fmt(my + _MARK_R)}Z",
        )
        m.attr("class", "sig-fig-mark")
        body.add(m)
        t = El("text")
        t.attr("class", "sig-fig-mark-label")
        t.attr("x", _fmt(xs[i] + 12))
        t.attr("y", _fmt(my + 4))
        t.attr("text-anchor", "start")
        t.add(_truncate(f"{e.date} — {e.label}", label_chars))
        body.add(t)
        root.add(body)
    _tick_label(root, lo_x - 8, height - 8, events[0].date, "start")
    _tick_label(root, hi_x + 8, height - 8, events[-1].date, "end")
    svg = assert_svg_safe(document(root), allow_style_block=False)
    return svg, (width, height)


# --- the public builder --------------------------------------------------------


def build_chart(spec: ChartSpec, lexicon: Lexicon | None = None) -> StaticFigureResult:
    """One chart figure — wide + narrow SVGs, generated legend (stacked
    series), table twin. Fail-closed per SIG-ENG-042."""
    lex = lexicon or load_lexicon()
    entries: tuple[LegendEntry, ...] = ()
    if spec.kind == "stacked-bar":
        entries = build_legend_entries(
            [f"series:{i}" for i in range(len(spec.series))],
            lex,
            series_labels=spec.series,
        )
    columns: tuple[str, ...]
    rows: list[dict[str, Any]]
    if spec.kind == "bar":
        columns = ("category", "value", "unit")
        rows = [
            {"category": c.label, "value": c.values[0], "unit": spec.unit, "href": c.href}
            for c in spec.categories
        ]
        svg, vb = _bar_emit(spec, spec.width, 28, ("cht-t", "cht-d"))
        svg_n, vb_n = _bar_emit(spec, spec.narrow_width, 16, ("chtn-t", "chtn-d"))
    elif spec.kind == "stacked-bar":
        columns = ("category", *spec.series, "total")
        rows = [
            {
                "category": c.label,
                **{spec.series[i]: c.values[i] for i in range(len(spec.series))},
                "total": sum(c.values),
                "href": c.href,
            }
            for c in spec.categories
        ]
        svg, vb = _stacked_emit(spec, spec.width, 28, ("cht-t", "cht-d"), entries)
        svg_n, vb_n = _stacked_emit(spec, spec.narrow_width, 16, ("chtn-t", "chtn-d"), entries)
    elif spec.kind in ("strip", "timeline"):
        emit = _strip_emit if spec.kind == "strip" else _timeline_emit
        columns = ("date", "event", "kind", "href")
        rows = [
            {"date": e.date, "event": e.label, "kind": e.kind or "—", "href": e.href}
            for e in sorted(spec.events, key=lambda e: (e.date, e.label))
        ]
        svg, vb = emit(spec, spec.width, 28, ("cht-t", "cht-d"))
        svg_n, vb_n = emit(spec, spec.narrow_width, 16, ("chtn-t", "chtn-d"))
    else:
        raise FigureKitError(f"chart kind {spec.kind!r} outside {CHART_KINDS}")

    legend_entries = tuple(e.to_json() for e in entries)

    size, gz = _meta_size(svg)
    return StaticFigureResult(
        svg=svg,
        svg_narrow=svg_n,
        viewbox=vb,
        narrow_viewbox=vb_n,
        mode=spec.kind,
        cap_actions=(),
        legend=legend_entries,
        table_columns=columns,
        table_rows=tuple(rows),
        node_count=len(spec.categories) or len(spec.events),
        edge_count=0,
        desc={
            "title": spec.title,
            "as_of_world": spec.release.as_of_world,
            "unit": spec.unit,
            "categories": len(spec.categories),
            "events": len(spec.events),
            "series": list(spec.series),
        },
        size_bytes=size,
        gzip_bytes=gz,
        result_schema=RESULT_SCHEMA_CHART,
    )


# --- fail-closed loader --------------------------------------------------------


def chart_spec_from_dict(doc: Mapping[str, Any]) -> ChartSpec:
    """Load a ``sig.figure-kit-chart/1`` document — fail-closed."""
    if doc.get("schema") != INPUT_SCHEMA_CHART:
        raise FigureKitError(f"schema {doc.get('schema')!r} != {INPUT_SCHEMA_CHART!r}")
    rel = doc.get("release")
    if not isinstance(rel, Mapping):
        raise FigureKitError("release block missing or not an object")
    kind = doc.get("kind")
    if kind not in CHART_KINDS:
        raise FigureKitError(f"kind {kind!r} outside {CHART_KINDS}")
    title = doc.get("title")
    if not isinstance(title, str) or not title:
        raise FigureKitError("missing title")
    unit = str(doc.get("unit", "items"))

    categories: list[ChartCategory] = []
    series = tuple(str(s) for s in (doc.get("series") or ()))
    nser = len(series) if series else 1
    for i, c in enumerate(doc.get("categories") or ()):
        where = f"categories[{i}]"
        if not isinstance(c, Mapping):
            raise FigureKitError(f"{where}: category is not an object")
        label = c.get("label")
        if not isinstance(label, str) or not label:
            raise FigureKitError(f"{where}: missing label")
        values = c.get("values")
        if (
            not isinstance(values, (list, tuple))
            or len(values) != nser
            or not all(isinstance(v, (int, float)) for v in values)
        ):
            raise FigureKitError(f"{where}: values is not a {nser}-element list of numbers")
        if any(v < 0 for v in values):
            raise FigureKitError(f"{where}: negative values cannot draw")
        href = c.get("href")
        if href is not None and not (isinstance(href, str) and href.startswith("/")):
            raise FigureKitError(f"{where}: href is not a root-relative path")
        categories.append(
            ChartCategory(label=label, values=tuple(float(v) for v in values), href=href)
        )

    events: list[ChartEvent] = []
    for i, e in enumerate(doc.get("events") or ()):
        where = f"events[{i}]"
        if not isinstance(e, Mapping):
            raise FigureKitError(f"{where}: event is not an object")
        date = e.get("date")
        label = e.get("label")
        if not isinstance(date, str) or not date:
            raise FigureKitError(f"{where}: undated events cannot sit on a time axis")
        if not isinstance(label, str) or not label:
            raise FigureKitError(f"{where}: missing label")
        _ordinal(date)  # validate now
        href = e.get("href")
        if href is not None and not (isinstance(href, str) and href.startswith("/")):
            raise FigureKitError(f"{where}: href is not a root-relative path")
        events.append(ChartEvent(date=date, label=label, href=href, kind=e.get("kind")))

    if kind in ("bar", "stacked-bar") and not categories:
        raise FigureKitError(f"{kind} chart needs categories")
    if kind in ("strip", "timeline") and not events:
        raise FigureKitError(f"{kind} chart needs events")
    if kind == "stacked-bar" and not series:
        raise FigureKitError("stacked-bar chart needs named series")
    if kind == "bar" and len(series) > 1:
        raise FigureKitError("bar chart is single-series — use stacked-bar")

    return ChartSpec(
        release=ReleaseInfo(
            label=str(rel["label"]),
            publication_id=str(rel["publication_id"]),
            as_of_world=str(rel["as_of_world"]),
        ),
        kind=str(kind),
        title=title,
        unit=unit,
        categories=tuple(categories),
        series=series,
        events=tuple(events),
        width=int(doc.get("width", 720)),
        narrow_width=int(doc.get("narrow_width", 360)),
    )


def load_chart_spec(path: Path | str) -> ChartSpec:
    p = Path(path)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FigureKitError(f"{p}: cannot read spec — {e}") from e
    if not isinstance(doc, Mapping):
        raise FigureKitError(f"{p}: top level is not an object")
    return chart_spec_from_dict(doc)


__all__ = [
    "CHART_KINDS",
    "INPUT_SCHEMA_CHART",
    "RESULT_SCHEMA_CHART",
    "SERIES_CAP",
    "ChartCategory",
    "ChartEvent",
    "ChartSpec",
    "build_chart",
    "chart_spec_from_dict",
    "load_chart_spec",
]

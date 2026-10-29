# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The generated figure legend (P36.28; K14 §4.7, SIG-UI-061).

The legend is **generated**, not maintained: emitters declare which
encodings a figure actually uses (``present``), and this module produces
the legend entries — label, plain-language line and spec reference — pulled
verbatim from ``web/src/lib/lexicon.json``. A legend therefore

* lists **only symbols actually present** in the figure (K6 §6.3: the
  legend never advertises an encoding the drawing does not carry), and
* can never invent a term — an encoding id outside this module's
  vocabulary raises ``FigureKitError`` (SIG-ENG-042).

``present`` vocabulary:

* ``fill:singleSource`` / ``fill:corroborated`` — the source-count fill
  states (the lexicon ``legend.fill.encodings`` keys verbatim)
* ``line:configured|declared|observed`` — access-kind line patterns
* ``line:relation`` — a recorded relation edge carrying no access claim
* ``currency:muted`` — the muted-ink state (historical / undated)
* ``mark:contested`` / ``mark:provisional`` — the ≠ and amber marks
* ``absence:<STATE>`` — a lexicon ``states.absence.*`` key (the hatch)
* ``kind:<entity-kind>`` — a shape channel entry (agency, vendor, …)
* ``series:<n>`` — a chart series swatch (label supplied by the caller)
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from .graph_model import NODE_KINDS
from .lexicon import Lexicon
from .model import FigureKitError

#: Canonical legend order — fills, then line patterns, then currency, then
#: the reserved-hue marks, absence, entity kinds, chart series.
_ORDER = {
    "fill": 0,
    "line": 1,
    "currency": 2,
    "mark": 3,
    "absence": 4,
    "kind": 5,
    "series": 6,
}

#: Access-kind line-pattern symbol hints, matched to the emitted classes.
_LINE_CLASSES = {
    "configured": ("sig-fig-edge", "sig-fig-edge-acc-configured"),
    "declared": ("sig-fig-edge", "sig-fig-edge-acc-declared"),
    "observed": ("sig-fig-edge", "sig-fig-edge-acc-observed"),
}


@dataclass(frozen=True)
class LegendEntry:
    """One legend row: the short label, the lexicon's plain-language line,
    the spec reference and the swatch channel + classes a renderer uses to
    draw the matching sample."""

    id: str
    channel: str  # "line" | "fill" | "mark" | "shape" | "text" | "series"
    label: str
    plain: str
    spec: str
    classes: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "channel": self.channel,
            "label": self.label,
            "plain": self.plain,
            "spec": self.spec,
            "classes": list(self.classes),
        }


def build_legend_entries(
    present: Iterable[str],
    lexicon: Lexicon,
    *,
    series_labels: tuple[str, ...] = (),
) -> tuple[LegendEntry, ...]:
    """Generate the legend entries for the encodings a figure carries —
    deterministic order, lexicon-verbatim wording, fail-closed on an
    unknown encoding id."""
    entries: list[LegendEntry] = []
    seen: set[str] = set()
    for token in present:
        if token in seen:
            continue
        seen.add(token)
        family, _, arg = token.partition(":")
        if family == "fill":
            entries.append(_fill(arg, lexicon))
        elif family == "line":
            entries.append(_line(arg, lexicon))
        elif family == "currency" and arg == "muted":
            entries.append(_muted(lexicon))
        elif family == "mark":
            entries.append(_mark(arg, lexicon))
        elif family == "absence":
            entries.append(_absence(arg, lexicon))
        elif family == "kind":
            entries.append(_kind(arg, lexicon))
        elif family == "series":
            entries.append(_series(arg, series_labels))
        else:
            raise FigureKitError(f"legend encoding {token!r} is not in the kit vocabulary")
    return tuple(
        sorted(
            entries,
            key=lambda e: (_ORDER[e.id.partition(":")[0]], _entry_rank(e.id)),
        )
    )


def _entry_rank(entry_id: str) -> tuple[int, str]:
    family, _, arg = entry_id.partition(":")
    order: tuple[str, ...]
    if family == "fill":
        order = ("singleSource", "corroborated")
        return (order.index(arg) if arg in order else 99, arg)
    if family == "line":
        order = ("configured", "declared", "observed", "relation")
        return (order.index(arg) if arg in order else 99, arg)
    if family == "kind":
        return (NODE_KINDS.index(arg) if arg in NODE_KINDS else 99, arg)
    return (0, arg)


def _fill(arg: str, lexicon: Lexicon) -> LegendEntry:
    enc = lexicon.fill_encodings.get(arg)
    if enc is None:
        raise FigureKitError(f"legend fill:{arg!r} — lexicon has no such encoding")
    label = str(enc.get("interimLegendLine", enc.get("label", arg)))
    cls = (
        "sig-fig-area",
        "sig-fig-src-single" if arg == "singleSource" else "sig-fig-src-corroborated",
    )
    return LegendEntry(
        id=f"fill:{arg}",
        channel="fill",
        label=label,
        plain=str(enc.get("plain", "")),
        spec=str(enc.get("spec", "")),
        classes=cls,
    )


def _line(arg: str, lexicon: Lexicon) -> LegendEntry:
    if arg == "relation":
        return LegendEntry(
            id="line:relation",
            channel="line",
            label="Recorded relation",
            plain="A line is a recorded relation between the two columns.",
            spec="K6 §6.2",
            classes=("sig-fig-edge",),
        )
    enc = lexicon.line_pattern.get("encodings", {}).get(arg)
    if enc is None:
        raise FigureKitError(f"legend line:{arg!r} — lexicon has no such encoding")
    state = str(enc.get("state", ""))
    state_key = state.partition(".")[2]
    label = lexicon.state_label("access", state_key)
    return LegendEntry(
        id=f"line:{arg}",
        channel="line",
        label=label,
        plain=f"{enc.get('symbol', '')} — {enc.get('symbolMeaning', 'access kind only')}",
        spec=str(enc.get("state", "")),
        classes=_LINE_CLASSES[arg],
    )


def _muted(lexicon: Lexicon) -> LegendEntry:
    historical = lexicon.state_label("currency", "HISTORICAL")
    return LegendEntry(
        id="currency:muted",
        channel="line",
        label=f"{historical} or undated",
        plain=lexicon.currency_plain,
        spec=str(lexicon.currency_spec),
        classes=("sig-fig-edge", "sig-fig-edge-muted"),
    )


def _mark(arg: str, lexicon: Lexicon) -> LegendEntry:
    if arg == "contested":
        return LegendEntry(
            id="mark:contested",
            channel="mark",
            label=lexicon.state_label("agreement", "CONTESTED"),
            plain=lexicon.labels.get("contested", ""),
            spec="SIG-UI-008",
            classes=("sig-fig-contested",),
        )
    if arg == "provisional":
        return LegendEntry(
            id="mark:provisional",
            channel="mark",
            label=lexicon.state_label("provisional", "PROVISIONAL"),
            plain=lexicon.provisional_plain,
            spec="SIG-UI-062",
            classes=("sig-fig-provisional",),
        )
    raise FigureKitError(f"legend mark:{arg!r} is not in the kit vocabulary")


def _absence(arg: str, lexicon: Lexicon) -> LegendEntry:
    label = lexicon.state_label("absence", arg)
    return LegendEntry(
        id=f"absence:{arg}",
        channel="fill",
        label=label,
        plain=lexicon.absence_plain,
        spec="SIG-UI-007",
        classes=("sig-fig-child-uncovered",),
    )


def _kind(arg: str, lexicon: Lexicon) -> LegendEntry:
    if arg not in NODE_KINDS:
        raise FigureKitError(f"legend kind:{arg!r} outside {NODE_KINDS}")
    return LegendEntry(
        id=f"kind:{arg}",
        channel="shape",
        label=arg if arg != "group" else "grouped records",
        plain=lexicon.entity_kind_plain,
        spec=str(lexicon.entity_kind_spec),
        classes=("sig-fig-node", f"sig-fig-node-{arg}"),
    )


def _series(arg: str, series_labels: tuple[str, ...]) -> LegendEntry:
    try:
        idx = int(arg)
    except ValueError as e:
        raise FigureKitError(f"legend series:{arg!r} is not an index") from e
    if not 0 <= idx < len(series_labels):
        raise FigureKitError(f"legend series:{idx} has no caller label")
    return LegendEntry(
        id=f"series:{idx}",
        channel="series",
        label=series_labels[idx],
        plain="",
        spec="K14 §4.7",
        classes=(f"sig-fig-series-{idx}",),
    )


__all__ = ["LegendEntry", "build_legend_entries"]

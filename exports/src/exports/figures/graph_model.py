# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The static figure kit's graph/chart input/output model (P36.28, FIG-01b).

``sig.figure-kit-graph/1`` covers the two deterministic network layouts K6
§6 defines — the two-column bipartite dossier figure (anchors ×
counterparties, SIG-UI-125 / SIG-UI-DV03) and the radial ego figure (K2's
entity-page 1-hop ego, ≤ 50 nodes, sectors per relation). The honesty rules
this model encodes:

* **no ranking, no hairball** — a side that exceeds its K6 row cap is
  *grouped* (the caller declares each node's ``group_*`` fields; the kit
  forms the groups deterministically), never silently pruned. A figure
  that still exceeds the node cap refuses (SIG-ENG-042).
* **every node links** — a node without an ``href`` fails closed; a group
  node links to the per-place page the caller names.
* **edges carry the H-2 fields** — relation, direction, access kind, date +
  date kind, currency, support, sources and the claim ids; the table twin
  lists them verbatim (a drawn path is ``aria-hidden``; the *words* live in
  the table — K6 §6.3).
* **currency is muted ink, never a pattern** — ``historical``/undated edges
  draw muted; the date/word in the twin carries the exact state (K14 §4.7).
* **line pattern = access kind only** — configured solid, declared dashed,
  observed double (the lexicon's ``legend.linePattern``); a non-access edge
  carries no pattern claim. The three kinds draw distinct classes so the
  page's ``:has()`` checkboxes hide them independently — no JavaScript.
* **the emitted SVG carries no per-edge numerals** — same SIG-UI-134
  posture as the map half; values live in the table twin + metadata.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import FigureKitError, ReleaseInfo

#: The graph-figure input contract id (P36.28).
INPUT_SCHEMA_GRAPH = "sig.figure-kit-graph/1"
#: The emitted graph metadata document id.
RESULT_SCHEMA_GRAPH = "sig.figure-graph-meta/1"

#: Access kinds — the lexicon's ``legend.linePattern`` encodings verbatim.
ACCESS_KINDS = ("configured", "declared", "observed")
#: The §28.3 currency vocabulary — ``historical`` and undated edges draw the
#: muted ink; nothing older is ever drawn as current.
CURRENCY_STATES = ("current", "aging", "stale", "historical")
#: H-2 date kinds (the edge table's ``date_kind`` column).
DATE_KINDS = ("single", "start", "end", "verdict", "undated")
DIRECTIONS = ("outbound", "inbound", "mutual", "unknown")

#: Entity kinds — the K14 §4.7 shape channel (shape carries kind, never
#: epistemic state). ``group`` is the kit's aggregate node kind.
NODE_KINDS = (
    "agency",
    "vendor",
    "product",
    "site",
    "source",
    "instrument",
    "entity",
    "group",
)
#: Plural nouns the deterministic group labels use ("Texas — 14 vendors").
KIND_NOUNS = {
    "agency": "agencies",
    "vendor": "vendors",
    "product": "products",
    "site": "sites",
    "source": "sources",
    "instrument": "instruments",
    "entity": "entities",
    "group": "groups",
}

#: Node sides: the bipartite figure uses ``anchor``/``counterparty``; the
#: ego figure uses ``centre``/``neighbour``.
NODE_SIDES = ("anchor", "counterparty", "centre", "neighbour")
GRAPH_KINDS = ("network", "ego")

#: K6 §6.2's caps — row caps per side, total node cap, the ego cap.
ANCHOR_CAP = 24
COUNTERPARTY_CAP = 16
NODE_CAP = 40
EGO_NODE_CAP = 50
ROW_PITCH = 20.0
MAX_FIGURE_HEIGHT = 520
WIDE_WIDTH = 720
NARROW_WIDTH = 360
WIDE_LABEL_CHARS = 38
NARROW_LABEL_CHARS = 20
MIN_MARKER_PX = 8.0  # K14: markers are never under 8 px


@dataclass(frozen=True)
class GraphNode:
    """One node the figure may draw. ``href`` is required — every node
    links (K6 §6.2); ``group_*`` fields are required on any side that might
    exceed its row cap (the honest fallback is a labelled group link)."""

    key: str
    label: str
    kind: str
    side: str
    href: str
    #: The place/state this node groups into when its side is over cap;
    #: ``group_label`` is the place/state name and ``group_href`` the
    #: per-place page the group node links to.
    group_key: str | None = None
    group_label: str | None = None
    group_href: str | None = None
    #: Optional plural noun override for the group label ("suppliers");
    #: defaults to the kind noun.
    noun: str | None = None
    contested: bool = False
    provisional: bool = False


@dataclass(frozen=True)
class GraphEdge:
    """One recorded relation between two nodes — the H-2 edge fields the
    table twin lists verbatim. ``access_kind`` is present only on access
    edges (the three line patterns mean access kind only)."""

    source: str
    target: str
    relation: str
    direction: str = "outbound"
    access_kind: str | None = None
    date: str | None = None
    date_kind: str = "single"
    currency: str = "current"
    support: str | None = None
    sources: tuple[str, ...] = ()
    claim_ids: tuple[str, ...] = ()
    contested: bool = False


@dataclass(frozen=True)
class GraphFigureSpec:
    """One network/ego figure's full input (``sig.figure-kit-graph/1``)."""

    release: ReleaseInfo
    kind: str  # "network" | "ego"
    title: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    #: Plural nouns for the deterministic group labels per side.
    anchor_noun: str = "agencies"
    counterparty_noun: str = "entities"
    width: int = WIDE_WIDTH
    narrow_width: int = NARROW_WIDTH
    max_height: int = MAX_FIGURE_HEIGHT


@dataclass(frozen=True)
class StaticFigureResult:
    """One emitted figure: byte-deterministic wide + narrow SVGs, the
    generated legend, the table twin rows and build metadata."""

    svg: str
    svg_narrow: str
    viewbox: tuple[float, float]
    narrow_viewbox: tuple[float, float]
    mode: str
    #: Every cap/grouping action taken — the honesty trail ("" = none).
    cap_actions: tuple[str, ...]
    legend: tuple[dict[str, Any], ...]
    table_columns: tuple[str, ...]
    table_rows: tuple[dict[str, Any], ...]
    node_count: int
    edge_count: int
    desc: dict[str, Any]
    size_bytes: int
    gzip_bytes: int
    result_schema: str

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.result_schema,
            "viewbox": list(self.viewbox),
            "narrow_viewbox": list(self.narrow_viewbox),
            "mode": self.mode,
            "cap_actions": list(self.cap_actions),
            "legend": list(self.legend),
            "table_columns": list(self.table_columns),
            "table_rows": list(self.table_rows),
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "desc": self.desc,
            "size_bytes": self.size_bytes,
            "gzip_bytes": self.gzip_bytes,
        }


# --- fail-closed loaders ------------------------------------------------------


def _node(obj: object, where: str) -> GraphNode:
    if not isinstance(obj, Mapping):
        raise FigureKitError(f"{where}: node is not an object")
    key = obj.get("key")
    label = obj.get("label")
    kind = obj.get("kind")
    side = obj.get("side")
    href = obj.get("href")
    if not isinstance(key, str) or not key:
        raise FigureKitError(f"{where}: missing key")
    if not isinstance(label, str) or not label:
        raise FigureKitError(f"{where}: missing label")
    if kind not in NODE_KINDS:
        raise FigureKitError(f"{where}: kind {kind!r} outside {NODE_KINDS}")
    if side not in NODE_SIDES:
        raise FigureKitError(f"{where}: side {side!r} outside {NODE_SIDES}")
    # Every node links (K6 §6.2) — a link-less node is a malformed spec, not
    # a quietly unlinked dot.
    if not isinstance(href, str) or not href.startswith("/"):
        raise FigureKitError(f"{where}: node {key!r} carries no root-relative href")
    return GraphNode(
        key=key,
        label=label,
        kind=str(kind),
        side=str(side),
        href=href,
        group_key=_opt_str(obj.get("group_key")),
        group_label=_opt_str(obj.get("group_label")),
        group_href=_opt_str(obj.get("group_href")),
        noun=_opt_str(obj.get("noun")),
        contested=bool(obj.get("contested", False)),
        provisional=bool(obj.get("provisional", False)),
    )


def _opt_str(v: object) -> str | None:
    return str(v) if isinstance(v, str) and v else None


def _edge(obj: object, where: str) -> GraphEdge:
    if not isinstance(obj, Mapping):
        raise FigureKitError(f"{where}: edge is not an object")
    source, target, relation = obj.get("source"), obj.get("target"), obj.get("relation")
    if not isinstance(source, str) or not source:
        raise FigureKitError(f"{where}: missing source")
    if not isinstance(target, str) or not target:
        raise FigureKitError(f"{where}: missing target")
    if not isinstance(relation, str) or not relation:
        raise FigureKitError(f"{where}: missing relation")
    direction = obj.get("direction", "outbound")
    if direction not in DIRECTIONS:
        raise FigureKitError(f"{where}: direction {direction!r} outside {DIRECTIONS}")
    access_kind = obj.get("access_kind")
    if access_kind is not None and access_kind not in ACCESS_KINDS:
        raise FigureKitError(f"{where}: access_kind {access_kind!r} outside {ACCESS_KINDS}")
    currency = obj.get("currency", "current")
    if currency not in CURRENCY_STATES:
        raise FigureKitError(f"{where}: currency {currency!r} outside {CURRENCY_STATES}")
    date_kind = obj.get("date_kind", "single")
    if date_kind not in DATE_KINDS:
        raise FigureKitError(f"{where}: date_kind {date_kind!r} outside {DATE_KINDS}")
    date = obj.get("date")
    if date_kind == "undated" and date is not None:
        raise FigureKitError(f"{where}: date_kind undated carries a date")
    sources = obj.get("sources") or ()
    claim_ids = obj.get("claim_ids") or ()
    if not all(isinstance(s, str) for s in sources):
        raise FigureKitError(f"{where}: sources is not a list of source ids")
    if not all(isinstance(c, str) for c in claim_ids):
        raise FigureKitError(f"{where}: claim_ids is not a list of claim ids")
    return GraphEdge(
        source=source,
        target=target,
        relation=relation,
        direction=str(direction),
        access_kind=str(access_kind) if access_kind else None,
        date=str(date) if date else None,
        date_kind=str(date_kind),
        currency=str(currency),
        support=str(obj["support"]) if obj.get("support") is not None else None,
        sources=tuple(sources),
        claim_ids=tuple(claim_ids),
        contested=bool(obj.get("contested", False)),
    )


def graph_spec_from_dict(doc: Mapping[str, Any]) -> GraphFigureSpec:
    """Load a ``sig.figure-kit-graph/1`` document — fail-closed."""
    if doc.get("schema") != INPUT_SCHEMA_GRAPH:
        raise FigureKitError(f"schema {doc.get('schema')!r} != {INPUT_SCHEMA_GRAPH!r}")
    rel = doc.get("release")
    if not isinstance(rel, Mapping):
        raise FigureKitError("release block missing or not an object")
    kind = doc.get("kind")
    if kind not in GRAPH_KINDS:
        raise FigureKitError(f"kind {kind!r} outside {GRAPH_KINDS}")
    title = doc.get("title")
    if not isinstance(title, str) or not title:
        raise FigureKitError("missing title")
    nodes = tuple(_node(n, f"nodes[{i}]") for i, n in enumerate(doc.get("nodes") or ()))
    edges = tuple(_edge(e, f"edges[{i}]") for i, e in enumerate(doc.get("edges") or ()))
    keys = [n.key for n in nodes]
    if len(set(keys)) != len(keys):
        raise FigureKitError("duplicate node key")
    keyset = set(keys)
    for i, e in enumerate(edges):
        if e.source not in keyset or e.target not in keyset:
            raise FigureKitError(f"edges[{i}] references an unknown node")
    return GraphFigureSpec(
        release=ReleaseInfo(
            label=str(rel["label"]),
            publication_id=str(rel["publication_id"]),
            as_of_world=str(rel["as_of_world"]),
        ),
        kind=str(kind),
        title=title,
        nodes=nodes,
        edges=edges,
        anchor_noun=str(doc.get("anchor_noun", "agencies")),
        counterparty_noun=str(doc.get("counterparty_noun", "entities")),
        width=int(doc.get("width", WIDE_WIDTH)),
        narrow_width=int(doc.get("narrow_width", NARROW_WIDTH)),
        max_height=int(doc.get("max_height", MAX_FIGURE_HEIGHT)),
    )


def load_graph_spec(path: Path | str) -> GraphFigureSpec:
    """Load a ``sig.figure-kit-graph/1`` document from disk."""
    p = Path(path)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FigureKitError(f"{p}: cannot read spec — {e}") from e
    if not isinstance(doc, Mapping):
        raise FigureKitError(f"{p}: top level is not an object")
    return graph_spec_from_dict(doc)


__all__ = [
    "ACCESS_KINDS",
    "ANCHOR_CAP",
    "COUNTERPARTY_CAP",
    "CURRENCY_STATES",
    "DATE_KINDS",
    "DIRECTIONS",
    "EGO_NODE_CAP",
    "GRAPH_KINDS",
    "INPUT_SCHEMA_GRAPH",
    "KIND_NOUNS",
    "MAX_FIGURE_HEIGHT",
    "MIN_MARKER_PX",
    "NARROW_LABEL_CHARS",
    "NARROW_WIDTH",
    "NODE_CAP",
    "NODE_KINDS",
    "NODE_SIDES",
    "RESULT_SCHEMA_GRAPH",
    "ROW_PITCH",
    "WIDE_LABEL_CHARS",
    "WIDE_WIDTH",
    "GraphEdge",
    "GraphFigureSpec",
    "GraphNode",
    "StaticFigureResult",
    "graph_spec_from_dict",
    "load_graph_spec",
]

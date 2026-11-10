# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The per-dossier network-figure emission (K6 VIZ-01b, P37.28, SIG-UI-125).

For every D-K4-3 page key this module composes the four dossier network
figures — ``fig-supply`` ("Who runs and supplies it", operators + supply),
``fig-funding`` ("Who funds it"), ``fig-access`` ("Who can search this
data") and ``fig-policy`` ("Which rules apply") — as
``sig.figure-kit-graph/1`` specs rendered through the ONE kit
(``exports.figures.build_network_figure``, P36.28). The edge sets reuse the
landed ``graph_overview`` collectors' semantics verbatim — the same
predicate families, the same relevance gate (D-K2-5 / H-13), the same
person-screened literal parties and the same withheld/review-pending drops
— scoped to the dossier's jurisdiction chain instead of the national view:

* **anchors** are published entities whose recorded ``place_jkey`` chain
  contains the dossier key (K6 §6.1 — a name match alone never places an
  entity); manufacturer camera-record groups anchor on their sites' leaf
  place (K6 §6.2's child-jurisdiction grouping, finer than the O1
  overview's admin-1 fold).
* **counterparties** are the recorded vendors, funders, partners,
  technologies and bodies on the other end of an anchored edge — literal
  counterparties carry no place and can never anchor.
* **grouping, never ranking** — every node declares its ``group_*``
  fallback fields (anchors by child jurisdiction linking the child
  dossier's figure anchor; counterparties by kind × admin-1 linking the
  ``/graphs/`` drill-down); the kit groups or refuses, the exporter never
  prunes.
* **H-rules** — every edge carries relation in words, direction, date +
  date kind, §28.3 currency, §10.7 support, bound source names and claim
  ids; historical/undated edges mark ``currency``/``date_kind`` so the
  kit's muted ink applies (SIG-UI-116).
* **access kinds stay separate** — the fig-access edges carry the kit's
  ``access_kind`` token so the page's zero-JS ``:has()`` toggles hide each
  kind independently (SIG-UI-024); the ``sharing_partner_degree`` family
  emits *sentences* (``degree_facts``), never edges (H-4 / SIG-UI-117).
* **typed empties** — a figure with no evidenced edge is never drawn
  (V-7); the emitted entry carries the reason state instead
  (``country_no_figure`` at the national level — K2 G-2, ``no_anchors``,
  ``no_evidenced_edges``, ``over_cap``).

The emitted entry shape lives in ``sig.dossier-visuals/1``'s ``networks[]``
(a restricted build input — never published, SIG-UI-134) and feeds:

* the web slot renderer (``NetworkFigureSlot.astro``) — wide + narrow
  inline SVG, the generated legend, the H-2 table twin, the CSS toggles;
* the ``figures[]`` metadata twin on ``sig.dossier/2`` (K6 §9.2 — caption +
  counts + links, no geometry);
* K5's ``figures[]`` — the ``fig-*`` edge-count breakdowns by source
  (K6 §7.2) emitted through :func:`build_dossier_visuals`' ``figures_k5``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from policy.labels import EntityLabel

from . import entity_page as _ep
from . import graph_overview as _go
from .entity_page import page_claims
from .figures import build_network_figure
from .figures.graph_model import graph_spec_from_dict
from .figures.lexicon import load_lexicon
from .figures.model import FigureKitError

# ---------------------------------------------------------------------------
# The family table — one row per dossier network figure (K6 §4.1/§6.1).
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Family:
    """One dossier network figure's fixed identity (K6 §4.1, §6.1)."""

    figure_id: str  # the K6-fixed anchor id (`#fig-supply`)
    slot: str  # the NETWORK_SLOT_SECTIONS slot it mounts into (`fig-2`)
    overview: str  # the /graphs/<ov>/ overview it slices
    family: str  # the K6 §6.1 family label
    title: str  # the figure's rendered title
    anchor_noun: str  # plural noun for grouped anchor labels
    counterparty_noun: str  # plural noun for grouped counterparty labels


FAMILIES: tuple[Family, ...] = (
    Family(
        figure_id="fig-supply",
        slot="fig-2",
        overview="supply",
        family="supply+operators",
        title="Who runs and supplies it",
        anchor_noun="agencies",
        counterparty_noun="suppliers",
    ),
    Family(
        figure_id="fig-funding",
        slot="fig-3",
        overview="funding",
        family="funding",
        title="Who funds it",
        anchor_noun="recipients",
        counterparty_noun="funders",
    ),
    Family(
        figure_id="fig-access",
        slot="fig-4",
        overview="access",
        family="access",
        title="Who can search this data",
        anchor_noun="agencies",
        counterparty_noun="partners",
    ),
    Family(
        figure_id="fig-policy",
        slot="fig-5",
        overview="governance",
        family="governance",
        title="Which rules apply",
        anchor_noun="instruments",
        counterparty_noun="counterparties",
    ),
)

#: A twin/node band → the figure kit's shape kind (the kit's NODE_KINDS are
#: closed — ``place``/``technology``/``kind`` map onto honest generic shapes,
#: never a kind claim the record does not make).
_BAND_TO_KIND = {
    "agency": "agency",
    "vendor": "vendor",
    "site": "site",
    "instrument": "instrument",
    "source": "source",
    "group": "group",
    "place": "site",
    "technology": "entity",
    "kind": "source",
    "entity": "entity",
}

#: The §12.2 twin access kinds → the kit's line-pattern tokens (SIG-UI-024;
#: line pattern = access kind only — K6 §6.3/D-K6-7).
_ACCESS_KIND_TOKENS = {
    "configured_access": "configured",
    "declared_policy": "declared",
    "observed_use": "observed",
}

#: K2 §6.2 — a relation row carries at most this many supporting claim ids.
_CLAIM_IDS_PER_EDGE = 3

#: The typed-empty statuses a ``networks[]`` entry may carry (the figure is
#: never drawn without an evidenced edge — K6 V-7; the reason is a value,
#: never a blank frame).
EMPTY_STATUSES = frozenset(
    {
        "country_no_figure",
        "no_anchors",
        "no_evidenced_edges",
        "over_cap",
    }
)


@dataclass
class _FamilyGraph:
    """One family's full node/edge set for the export's single snapshot."""

    nodes: dict[str, _go._Node]
    edges: dict[tuple[str, str, str], _go._Edge]


@dataclass
class _Prepared:
    """The once-per-export structures ``entries_for`` slices per dossier."""

    graphs: dict[str, _FamilyGraph]
    #: entity id → the count of published site records recording it as
    #: operator (the fig-supply anchor attr — "recorded operator on N
    #: published records"; K6 §6.1's 'operates N cameras' attribute made
    #: honest: the count is published records, never a camera census).
    operator_records: dict[str, int]
    #: subject id → the degree-only fact rows (H-4 — counts, never edges).
    degree_facts: dict[str, list[dict[str, Any]]]


def _supply_graph(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
    value_claims: Sequence[Any],
    relevance: Mapping[str, str],
    relevance_fields: Mapping[str, Mapping[str, Any]],
) -> _FamilyGraph:
    """fig-supply — buyer→vendor pairs (the O1 rule, H-13 relevance gate)
    plus manufacturer camera-record groups on their sites' leaf place."""
    nodes: dict[str, _go._Node] = {}
    edges: dict[tuple[str, str, str], _go._Edge] = {}

    def _ok(lbl: EntityLabel) -> bool:
        """H-13 — only surveillance-relevant procurement draws a supply edge."""
        if lbl.kind == "notice":
            return relevance.get(lbl.entity_id) == "surveillance_related"
        fields = relevance_fields.get(lbl.subject_key or "")
        if fields is None:
            return False
        from policy.procurement_relevance import classify_notice

        verdict = classify_notice(
            lbl.subject_key or "", fields, entity_id=lbl.entity_id, kind=lbl.kind or "contract"
        )
        return verdict.relevance == "surveillance_related"

    _go._party_pairs(
        labels,
        by_subject,
        subject_kinds=frozenset({"notice", "contract"}),
        left_preds=_go.SUPPLY_BUYER_PREDS,
        right_preds=_go.SUPPLY_SELLER_PREDS,
        left_band="agency",
        right_band="vendor",
        relation="sells to",
        gate=_ok,
        nodes=nodes,
        edges=edges,
    )
    # Manufacturer camera records — grouped per (manufacturer, the site's
    # LEAF place) so a county dossier anchors its own record group (K6
    # §6.2's child-jurisdiction grouping; the O1 overview's admin-1 fold is
    # the national cut, not this figure's).
    manu_claims: dict[tuple[str, str | None], list[Any]] = {}
    for c in value_claims:
        if getattr(c, "predicate_id", None) not in _go.MANUFACTURER_PREDS:
            continue
        sid = getattr(c, "subject_id", "")
        lbl = labels.get(sid)
        if not _go._published(lbl) or getattr(c, "value_text", None) in (None, ""):
            continue
        manu_claims.setdefault(
            (str(c.value_text), getattr(lbl, "place_jkey", None) or None), []
        ).append(c)
    for (manu, leaf), rows in sorted(manu_claims.items()):
        vnode = _go._literal_node(nodes, manu, band="vendor")
        if vnode is None:
            continue
        gkey = f"grp:dn-sites:{manu.strip().lower()}:{leaf or 'unplaced'}"
        nodes[gkey] = _go._Node(
            key=gkey,
            label=f"{len(rows)} camera records",
            band="group",
            place=leaf,
            count=len(rows),
        )
        e = _go._Edge(src=gkey, dst=vnode, relation="manufactured by")
        e.predicates.add("manufacturer")
        for c in rows:
            if getattr(c, "claim_id", None):
                e.claim_ids.add(str(c.claim_id))
            if getattr(c, "source_id", None):
                e.source_ids.add(str(c.source_id))
            obs = _ep._norm_iso_date(getattr(c, "observed_at", None))
            if obs:
                e.observed.add(obs)
        edges[(gkey, vnode, "manufactured by")] = e
    return _FamilyGraph(nodes=nodes, edges=edges)


def _funding_graph(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
) -> _FamilyGraph:
    """fig-funding — funder→recipient pairs on grant subjects (O3)."""
    nodes: dict[str, _go._Node] = {}
    edges: dict[tuple[str, str, str], _go._Edge] = {}
    _go._party_pairs(
        labels,
        by_subject,
        subject_kinds=frozenset({"grant"}),
        left_preds=_go.FUNDER_PREDS,
        right_preds=_go.RECIPIENT_PREDS,
        left_band="agency",
        right_band="agency",
        relation="funds",
        nodes=nodes,
        edges=edges,
    )
    return _FamilyGraph(nodes=nodes, edges=edges)


def prepare(
    labels: Mapping[str, EntityLabel],
    *,
    claim_rows: Sequence[Sequence[Any]],
    value_claims: Sequence[Any],
    relevance: Mapping[str, str],
    relevance_fields: Mapping[str, Mapping[str, Any]],
    places: Mapping[str, _go.PlaceInfo],
) -> _Prepared:
    """The once-per-export family graphs + the operator/degree lookups."""
    by_subject = page_claims(claim_rows)
    graphs: dict[str, _FamilyGraph] = {
        "fig-supply": _supply_graph(labels, by_subject, value_claims, relevance, relevance_fields),
        "fig-funding": _funding_graph(labels, by_subject),
        "fig-access": _FamilyGraph(*_go._access(labels, by_subject)),
        "fig-policy": _FamilyGraph(*_go._governance(labels, by_subject, places)),
    }
    operator_records: Counter[str] = Counter()
    degree_facts: dict[str, list[dict[str, Any]]] = {}
    for sid, claims in by_subject.items():
        for c in claims:
            if c.predicate_id in _go.OPERATOR_PREDS and c.object_entity:
                operator_records[str(c.object_entity)] += 1
        for f in _ep.degree_only_facts(sid, claims, source_names={}, claim_sources={}, as_of=None):
            degree_facts.setdefault(sid, []).append(dict(f))
    return _Prepared(
        graphs=graphs,
        operator_records=dict(operator_records),
        degree_facts=degree_facts,
    )


# ---------------------------------------------------------------------------
# The per-dossier slice
# ---------------------------------------------------------------------------


def _anchor_jkeys(place: str | None, ancestors: Mapping[str, tuple[str, ...]]) -> frozenset[str]:
    """The dossier keys a placed node anchors to — its place's recorded
    chain (root-first, ending at the place — placement@1's own ancestry)."""
    if not place:
        return frozenset()
    return frozenset(ancestors.get(place, (place,)))


def _admin1_of(
    place: str | None,
    ancestors: Mapping[str, tuple[str, ...]],
    places: Mapping[str, _go.PlaceInfo],
) -> str | None:
    return _go._admin1(ancestors, places, place)


def _node_kind(band: str, key: str) -> str:
    if key.startswith("grp:"):
        return "group"
    return _BAND_TO_KIND.get(band, "entity")


def _anchor_group_fields(
    n: _go._Node,
    *,
    figure_id: str,
    overview: str,
    pages: frozenset[str],
    slug_of: Any,
    places: Mapping[str, _go.PlaceInfo],
) -> dict[str, str]:
    """The anchor's declared grouping — by its own leaf place (K6 §6.2:
    'Harris County — 14 agencies' linking the child dossier's figure)."""
    leaf = n.place or "unplaced"
    label = (places.get(leaf) or _go.PlaceInfo("", "", "")).name or (
        leaf.replace("_", " ") if leaf != "unplaced" else "Not yet placed"
    )
    if n.place and n.place in pages:
        href = f"/dossier/{slug_of(n.place)}/#{figure_id}"
    elif n.place and (places.get(leaf) or _go.PlaceInfo("", "", "")).slug_path:
        href = f"/graphs/{overview}/{(places[leaf]).slug_path}/"
    else:
        href = f"/graphs/{overview}/"
    return {"group_key": leaf, "group_label": label, "group_href": href}


def _cp_group_fields(
    n: _go._Node,
    *,
    overview: str,
    ancestors: Mapping[str, tuple[str, ...]],
    places: Mapping[str, _go.PlaceInfo],
) -> dict[str, str]:
    """The counterparty's declared grouping — kind × admin-1 (K6 §6.2)."""
    admin1 = _admin1_of(n.place, ancestors, places)
    label = (places.get(admin1) or _go.PlaceInfo("", "", "")).name or (
        "Not yet placed" if admin1 is None else admin1.replace("_", " ")
    )
    slug = (places.get(admin1) or _go.PlaceInfo("", "", "")).slug_path if admin1 else ""
    return {
        "group_key": f"{n.band}:{admin1 or 'unplaced'}",
        "group_label": label,
        "group_href": f"/graphs/{overview}/{slug}/" if slug else f"/graphs/{overview}/",
    }


def _spec_node(
    n: _go._Node,
    *,
    side: str,
    overview: str,
    group_fields: Mapping[str, str],
) -> dict[str, Any]:
    """One spec node — every drawn node links (the overview drill-down is
    the fallback for a page-less literal/group, never a dead route)."""
    return {
        "key": n.key,
        "label": n.label,
        "kind": _node_kind(n.band, n.key),
        "side": side,
        "href": n.href or f"/graphs/{overview}/",
        **group_fields,
    }


def _kit_currency(word: str | None) -> str:
    """The §28.3 currency word → the kit's closed vocabulary. UNDATED /
    unresolvable reads ``aging`` — 'not demonstrably current', never a
    currency claim the record does not make."""
    return {
        "CURRENT": "current",
        "AGING": "aging",
        "STALE": "stale",
        "HISTORICAL": "historical",
    }.get(word or "", "aging")


def _spec_edge(
    anchor: str,
    cp: str,
    e: _go._Edge,
    *,
    relation: str,
    direction: str,
    access_kind: str | None,
    lineage: Mapping[str, str],
    as_of: Any,
    source_names: Mapping[str, str],
) -> dict[str, Any]:
    """One spec edge — the H-2 fields derived once through the overview's
    own ``_edge_fields`` derivation (never constants)."""
    fields = _go._edge_fields(e, lineage=lineage, as_of=as_of, source_names=source_names)
    out: dict[str, Any] = {
        "source": anchor,
        "target": cp,
        "relation": relation,
        "direction": direction,
        "date_kind": "single" if fields["date"] else "undated",
        "currency": _kit_currency(fields["currency"]),
        "sources": list(fields["sources"]),
        "claim_ids": sorted(e.claim_ids)[:_CLAIM_IDS_PER_EDGE],
    }
    if fields["date"]:
        out["date"] = fields["date"]
    if fields["support"] and fields["support"] != "UNSUPPORTED":
        out["support"] = fields["support"]
    if access_kind:
        out["access_kind"] = access_kind
    return out


def _access_kind_of(e: _go._Edge) -> str | None:
    """The one access kind an edge's predicate set classifies to (the kinds
    never merge — an edge keyed on a different relation is a different
    edge)."""
    kinds = {_ACCESS_KIND_TOKENS.get(_ep._access_kind_for(p) or "") for p in e.predicates}
    kinds.discard(None)
    return sorted(kinds)[0] if len(kinds) == 1 else None


def _anchored_pairs(
    family: Family,
    graph: _FamilyGraph,
    *,
    jkey: str,
    ancestors: Mapping[str, tuple[str, ...]],
    extra_anchors: frozenset[str] = frozenset(),
) -> list[tuple[str, str, _go._Edge, str, str]]:
    """(anchor_key, cp_key, edge, relation, direction) rows for one dossier.

    Anchor side per family (K6 §6.1): the placed endpoint is the anchor,
    its recorded partner the counterparty. When both ends anchor, the
    family's named anchor role wins — the bipartite figure is
    anchor ↔ counterparty, never anchor ↔ anchor:
    * fig-supply — the buyer/record-group side anchors (vendor placed
      alone still anchors with the buyer as counterparty);
    * fig-funding — the recipient anchors (a funder placed alone anchors
      with the recipient as counterparty);
    * fig-access — the access subject anchors;
    * fig-policy — the instrument anchors (its counterparties are the
      technologies and bodies; the 'in jurisdiction' edges only establish
      placement, never draw).
    """
    out: list[tuple[str, str, _go._Edge, str, str]] = []

    def is_anchored(key: str) -> bool:
        n = graph.nodes.get(key)
        return n is not None and (key in extra_anchors or jkey in _anchor_jkeys(n.place, ancestors))

    for (src, dst, _rel), e in sorted(graph.edges.items()):
        if family.figure_id == "fig-supply":
            if is_anchored(src):
                rel = "manufactured by" if src.startswith("grp:") else "bought from"
                out.append((src, dst, e, rel, "outbound"))
            elif is_anchored(dst):
                out.append((dst, src, e, "sold to", "outbound"))
        elif family.figure_id == "fig-funding":
            if is_anchored(dst):
                out.append((dst, src, e, "funded by", "inbound"))
            elif is_anchored(src):
                out.append((src, dst, e, "funds", "outbound"))
        elif family.figure_id == "fig-access":
            if is_anchored(src):
                out.append((src, dst, e, e.relation, "outbound"))
            elif is_anchored(dst):
                out.append((dst, src, e, e.relation, "inbound"))
        elif family.figure_id == "fig-policy":
            # The instrument anchors; 'in jurisdiction' edges mark
            # placement only — they never draw (the place is not a
            # counterparty).
            if e.relation == "in jurisdiction":
                continue
            instrument = dst if e.relation in ("enacts", "oversees") else src
            other = src if instrument == dst else dst
            if is_anchored(instrument):
                direction = "inbound" if e.relation in ("enacts", "oversees") else "outbound"
                out.append((instrument, other, e, e.relation, direction))
    return out


def _policy_anchored(
    graph: _FamilyGraph,
    labels: Mapping[str, EntityLabel],
    *,
    jkey: str,
    ancestors: Mapping[str, tuple[str, ...]],
) -> set[str]:
    """Instruments anchored to this dossier — a published instrument is
    anchored when its recorded ``place_jkey`` chain contains the key OR an
    'in jurisdiction' edge resolves to a place whose chain does (a
    place-literal name never anchors — K4's rule against name placement)."""
    anchored: set[str] = set()
    for src, dst, rel in graph.edges:
        if rel != "in jurisdiction":
            continue
        inst = src  # _governance emits instrument → jurisdiction
        node = graph.nodes.get(dst)
        place = node.place if node is not None else None
        if place is None and node is not None and not dst.startswith("place-lit:"):
            lbl = labels.get(dst)
            place = getattr(lbl, "place_jkey", None)
        if place and jkey in _anchor_jkeys(place, ancestors):
            anchored.add(inst)
    # place_jkey directly on the instrument's label.
    for key in graph.nodes:
        if key.startswith(("lit:", "place:", "place-lit:", "grp:")):
            continue
        if key in anchored:
            continue
        lbl = labels.get(key)
        pj = getattr(lbl, "place_jkey", None)
        if pj and jkey in _anchor_jkeys(pj, ancestors):
            anchored.add(key)
    return anchored


def _table_href(
    family: Family,
    info: Any,
    ancestors: Mapping[str, tuple[str, ...]],
    places: Mapping[str, _go.PlaceInfo],
) -> str:
    """The 'all N →' drill-down — the dossier's own ``/graphs/<ov>/<place>/``
    page for country/admin-1 dossiers, else its admin-1's page, else the
    overview root (never a route the release does not serve)."""
    chain = ancestors.get(info.jkey, (info.jkey,))
    for key in (info.jkey, *chain):
        pinfo = places.get(key)
        if pinfo is not None and pinfo.level in ("country", "state_province") and pinfo.slug_path:
            return f"/graphs/{family.overview}/{pinfo.slug_path}/"
    return f"/graphs/{family.overview}/"


def _explore_href(family: Family, jkey: str) -> str:
    """'Open in the explorer' — the explorer's registered overview +
    jurisdiction params (K6 §6.6; sig.workspace-state/2)."""
    return f"/explore/?v=2&overview={family.overview}&jurisdiction={jkey}"


def entries_for(
    jkey: str,
    info: Any,
    prepared: _Prepared,
    *,
    labels: Mapping[str, EntityLabel],
    ancestors: Mapping[str, tuple[str, ...]],
    places: Mapping[str, _go.PlaceInfo],
    pages: frozenset[str],
    slug_of: Any,
    lineage: Mapping[str, str],
    as_of: Any,
    source_names: Mapping[str, str],
    release: Mapping[str, Any],
    lexicon: Any = None,
) -> list[dict[str, Any]]:
    """The four ``networks[]`` entries for one dossier — drawn figures or
    typed absences, never a missing slot."""
    lex = lexicon if lexicon is not None else load_lexicon()
    entries: list[dict[str, Any]] = []
    country = getattr(info, "level", "") == "country"

    for fam in FAMILIES:
        graph = prepared.graphs[fam.figure_id]
        base: dict[str, Any] = {
            "figure_id": fam.figure_id,
            "slot": fam.slot,
            "family": fam.family,
            "overview": fam.overview,
            "title": fam.title,
        }
        if country:
            entries.append(
                {
                    **base,
                    "status": "country_no_figure",
                    "reason": (
                        "no node-link figure at the national level — the "
                        "national relationship set reads as a count table, "
                        "never a hairball (K2 G-2)"
                    ),
                    "anchors_total": 0,
                    "edges_total": 0,
                    "table_href": f"/graphs/{fam.overview}/",
                    "explore_href": _explore_href(fam, jkey),
                }
            )
            continue

        # fig-policy's anchor set additionally covers instruments whose
        # 'in jurisdiction' edges place them here (see _policy_anchored) —
        # place-name literals never anchor (K4's rule against name
        # placement).
        extra = (
            frozenset(_policy_anchored(graph, labels, jkey=jkey, ancestors=ancestors))
            if fam.figure_id == "fig-policy"
            else frozenset()
        )
        pairs = _anchored_pairs(fam, graph, jkey=jkey, ancestors=ancestors, extra_anchors=extra)
        degree_rows: list[dict[str, Any]] = []
        if fam.figure_id == "fig-access":
            seen: set[str] = set()
            for sid, facts in sorted(prepared.degree_facts.items()):
                lbl = labels.get(sid)
                place = getattr(lbl, "place_jkey", None) if lbl is not None else None
                if not (place and jkey in _anchor_jkeys(place, ancestors)):
                    continue
                for f in facts:
                    for n in f.get("counts") or ():
                        key = f"{sid}:{n}:{f.get('observed_at')}"
                        if key in seen:
                            continue
                        seen.add(key)
                        degree_rows.append(
                            {
                                "count": n,
                                "observed": f.get("observed_at"),
                                "sources": sorted(
                                    {
                                        str(s.get("name") or s.get("id"))
                                        for s in f.get("sources", ())
                                    }
                                ),
                                "claim_ids": sorted(f.get("claim_ids", ()) or ())[
                                    :_CLAIM_IDS_PER_EDGE
                                ],
                            }
                        )

        if not pairs:
            anchors_total = sum(
                1 for _k, n in graph.nodes.items() if jkey in _anchor_jkeys(n.place, ancestors)
            )
            entries.append(
                {
                    **base,
                    "status": "no_anchors" if anchors_total == 0 else "no_evidenced_edges",
                    "reason": (
                        "SIG's release places no entity in this jurisdiction "
                        "with a recorded relationship of this kind"
                        if anchors_total == 0
                        else "entities are placed here but carry no recorded "
                        "relationship of this kind in this release"
                    ),
                    "anchors_total": anchors_total,
                    "edges_total": 0,
                    "degree_facts": degree_rows,
                    "table_href": _table_href(fam, info, ancestors, places),
                    "explore_href": _explore_href(fam, jkey),
                }
            )
            continue

        spec_nodes: dict[str, dict[str, Any]] = {}
        spec_edges: list[dict[str, Any]] = []
        for anchor_key, cp_key, e, relation, direction in pairs:
            a_node = graph.nodes[anchor_key]
            c_node = graph.nodes[cp_key]
            for key, n, side, gfields in (
                (
                    anchor_key,
                    a_node,
                    "anchor",
                    _anchor_group_fields(
                        a_node,
                        figure_id=fam.figure_id,
                        overview=fam.overview,
                        pages=pages,
                        slug_of=slug_of,
                        places=places,
                    ),
                ),
                (
                    cp_key,
                    c_node,
                    "counterparty",
                    _cp_group_fields(
                        c_node, overview=fam.overview, ancestors=ancestors, places=places
                    ),
                ),
            ):
                if key not in spec_nodes or spec_nodes[key]["side"] != side:
                    spec_nodes[key] = _spec_node(
                        n, side=side, overview=fam.overview, group_fields=gfields
                    )
            spec_edges.append(
                _spec_edge(
                    anchor_key,
                    cp_key,
                    e,
                    relation=relation,
                    direction=direction,
                    access_kind=(_access_kind_of(e) if fam.figure_id == "fig-access" else None),
                    lineage=lineage,
                    as_of=as_of,
                    source_names=source_names,
                )
            )

        anchor_attrs = (
            {
                k: f"recorded operator on {n} published record{'s' if n != 1 else ''}"
                for k, n in sorted(prepared.operator_records.items())
                if k in spec_nodes and spec_nodes[k]["side"] == "anchor" and n > 0
            }
            if fam.figure_id == "fig-supply"
            else {}
        )
        toggle_kinds = (
            sorted({e["access_kind"] for e in spec_edges if e.get("access_kind")})
            if fam.figure_id == "fig-access"
            else []
        )

        spec_doc = {
            "schema": "sig.figure-kit-graph/1",
            "release": dict(release),
            "kind": "network",
            "title": f"{fam.title} — {info.name}",
            "anchor_noun": fam.anchor_noun,
            "counterparty_noun": fam.counterparty_noun,
            "nodes": [spec_nodes[k] for k in sorted(spec_nodes)],
            "edges": spec_edges,
        }
        try:
            result = build_network_figure(graph_spec_from_dict(spec_doc), lex)
        except FigureKitError as exc:
            entries.append(
                {
                    **base,
                    "status": "over_cap",
                    "reason": str(exc),
                    "anchors_total": len(
                        {k for k, n in spec_nodes.items() if n["side"] == "anchor"}
                    ),
                    "edges_total": len(spec_edges),
                    "degree_facts": degree_rows,
                    "table_href": _table_href(fam, info, ancestors, places),
                    "explore_href": _explore_href(fam, jkey),
                }
            )
            continue

        meta = result.to_json()
        by_source = Counter(str(s) for _a, _c, e, _r, _d in pairs for s in e.source_ids)
        entries.append(
            {
                **base,
                "status": "drawn",
                "svg": result.svg,
                "svg_narrow": result.svg_narrow,
                "meta": meta,
                "anchors_drawn": meta["desc"]["anchors"],
                "counterparties_drawn": meta["desc"]["counterparties"],
                "edges_drawn": meta["desc"]["edges"],
                "cap_actions": list(meta.get("cap_actions") or ()),
                "toggle_kinds": toggle_kinds,
                "table_rows_total": len(meta.get("table_rows") or ()),
                "table_href": _table_href(fam, info, ancestors, places),
                "explore_href": _explore_href(fam, jkey),
                "anchor_attrs": anchor_attrs,
                "degree_facts": degree_rows,
                "by_source": [
                    {"source_id": s, "value": int(n)} for s, n in sorted(by_source.items())
                ],
            }
        )
    return entries


#: The K5 ``figures[]`` labels per figure (K6 §7.2 — edge counts, by source).
_K5_LABELS = {
    "fig-supply": "Relationships — who runs and supplies it (edges)",
    "fig-funding": "Relationships — who funds it (edges)",
    "fig-access": "Relationships — who can search this data (edges)",
    "fig-policy": "Relationships — which rules apply (edges)",
}


def figures_k5_rows(entries: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The ``fig-*`` K5 figure rows for one dossier — edge counts by source
    (K6 §7.2). Typed absences carry the honest zero through the same shape
    so a reader never sees a silently absent figure id."""
    rows: list[dict[str, Any]] = []
    for e in entries:
        rows.append(
            {
                "figure_id": e["figure_id"],
                "label": _K5_LABELS.get(str(e["figure_id"]), str(e["figure_id"])),
                "edges": int(e.get("edges_drawn") or 0),
                "status": e.get("status"),
                "by_source": list(e.get("by_source") or ()),
            }
        )
    return rows


__all__ = [
    "EMPTY_STATUSES",
    "FAMILIES",
    "Family",
    "entries_for",
    "figures_k5_rows",
    "prepare",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.graph-overview/1`` builder — P37.24 (K2 GX-08a / §5, §6.3),
extended by P37.25 (K2 GX-08b).

The four 08a overviews — O0 ``types`` (what SIG holds, by kind, and how kinds
connect, gaps included), O1 ``supply`` (who sells surveillance technology to
whom, relevance-gated per D-K2-5 / H-13), O3 ``funding`` (who funds whom) and
O4 ``operators`` (which bodies run the cameras, where — the NEW-2 fix:
``published_by`` is provenance, never an operator edge) — plus the 08b set:
O2 ``access`` (who can search whose data — Data Driven's configured-access
form today; the Flock share-list ``configured_sharing_partner`` claims fold
to the state × state weighted matrix at scale, never a national hairball —
SIG-UI-021), O5 ``governance`` (which laws and ordinances govern which
technologies where) and O7 ``adoption`` (which agencies use which technology,
by state — the state × technology matrix at scale) — emitted per licence
compartment from the export's ONE snapshot. The ``sig.graph-components/1``
index (K2 §6.4) rides the same emission: per compartment, the
weakly-connected components of the publishable entity-ref graph, one member
file per component.

The 08b laws the contract adds:

* **the matrix fold** — O2/O5/O7 node-link overviews exist only at small
  scale. Past ``MATRIX_MIN`` endpoints the foldable side collapses to its
  admin-1 place and the edges merge into weighted cells (K2 §5.2 — the
  declared aggregation, recorded in ``cap_actions``, never a smoothed cut).
  Each folded edge carries ``member_count`` — the distinct folded member
  nodes it aggregates.
* **place slices** — a folded overview emits per-place detail docs at
  ``web/graph/<ov>/places/<comp>.<jkey>.json`` (same
  ``sig.graph-overview/1`` schema, ``slice`` marked): the state drill-down's
  unfolded agency-level subgraph — "per-agency egos grouped by state" (K2
  §5.2 O2). Out-of-place counterparties fold to their own place when a
  slice would otherwise exceed the cap.
* **CC BY-SA compartment** — the share-list claims stamp the ``portal``
  (CC-BY-SA-4.0) compartment: access edges file exactly where their claim
  set licenses to (SIG-LIC-009a), so the Flock matrix is published in the
  CC BY-SA compartment or per compartment — never blended (S6R-12).

The laws the contract carries (SIG-UI-117/118, SIG-EXPORT-015, K2 §7):

* **columnar** — K2 §6.3's measured shape: a ``dict`` vocabulary (kinds,
  labels, hrefs, places, predicates, dates, currency classes, sources) plus
  parallel node/edge arrays indexing into it; positions precomputed at
  build by the deterministic banded layout (closed-form, no PRNG, no
  third-party layout dependency — ``igraph`` is never imported).
* **≤ 3,000 nodes or a declared aggregation** (SIG-UI-118 / D-K2-*) — a
  degree-1 literal counterparty set past the collapse bound folds into a
  labelled ``group`` node ("N other suppliers") that links the real page;
  an overview still over the cap refuses the build, never a smoothed cut.
* **H-2 edges** — every edge carries relation in words, date + date kind,
  currency class, sources and supporting claim ids (SIG-EXPORT-015) — the
  CSV download is the full-fidelity form; the columnar doc omits claim ids
  per K2 §6.3 (they are fetched on click through the entity pages).
* **degree-only is not an edge** (SIG-UI-117 / H-4) — the
  ``sharing_partner_degree`` family can never mint an edge here; the guard
  is structural (the predicate set is consulted, never iterated).
* **H-3 / SIG-UI-116** — historical and undated edges are visibly marked
  (muted class + the word), never drawn as current.
* **H-12 / NEW-2** — a source publisher is never an operating organisation:
  ``published_by`` claims produce NO operator edges, ever.
* **A-10 / SIG-UI-080** — a withheld or review-pending entity is never a
  node; an edge that would name one is dropped whole; a literal party that
  fails the person screen drops its edge the same way.
* **compartments** — an edge files under every compartment its claim set
  licenses to (the intersection rule the entity twins carry); a node files
  wherever an incident edge lands (ADR-106, SIG-EXPORT-014).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from policy.labels import KIND_WORDS, KINDS, EntityLabel
from policy.licensing import compute_export_license, export_refusal_reason
from policy.rights import RightsRecord
from resolution.partner_identity import natural_person_signal

from . import compartments as C
from . import entity_page as _ep
from .entity_page import (
    DEGREE_PREDICATES,
    _currency_word,
    _norm_iso_date,
    _support_word,
    claim_rights,
    page_claims,
)
from .figures.network_figure import kind_shape_path

#: The emitted document schema (K2 §6.3).
OVERVIEW_SCHEMA = "sig.graph-overview/1"
#: The ``web/graph/index.json`` manifest schema (the /graphs/ hub's data).
INDEX_SCHEMA = "sig.graph-index/1"
#: The download resource schemas (SIG-TRANSP-016).
GRAPH_NODES_SCHEMA = "sig.graph-nodes/1"
GRAPH_EDGES_SCHEMA = "sig.graph-edges/1"
#: The components contracts (K2 §6.4, SIG-EXPORT-D20).
COMPONENTS_INDEX_SCHEMA = "sig.graph-components/1"
COMPONENT_SCHEMA = "sig.graph-component/1"

#: SIG-UI-118 / K2 §5 — the hard node bound, enforced after aggregation.
NODE_CAP = 3000
#: K2 O1 — a side's degree-1 literal counterparties beyond this count fold
#: into one labelled group node per hub.
COLLAPSE_MIN = 8
#: K2 §5.2 — the node-link → matrix boundary. Past this many endpoints the
#: foldable side collapses to admin-1 places (the state × state / state ×
#: technology matrix; "never node-link nationally" — SIG-UI-021).
MATRIX_MIN = 200

#: The G-6 caption, verbatim — positions carry no geographic meaning.
POSITION_NOTE = "position has no geographic meaning; nearby nodes share relationships"
#: H-8 / SIG-UI-070 — the ER disclosure every count carries (entity_page's).
ER_DISCLOSURE = _ep.ER_DISCLOSURE

#: The overview catalogue — 08a (P37.24) plus the 08b set (P37.25, GX-08b).
OVERVIEWS: tuple[tuple[str, str, str], ...] = (
    ("types", "Type map", "What does SIG hold, by kind, and how do kinds connect?"),
    ("supply", "Supply", "Who sells surveillance technology to whom?"),
    ("funding", "Funding", "Who funds whom?"),
    # D-K14-7: the K2 question wording is reworded — "who runs the" is a
    # banned token under web/src until the operator writes the About
    # "who runs SIG" wording (tests/unit/test_p36_64_copy_batch.py).
    ("operators", "Operators", "Which bodies run the cameras, and where?"),
    ("access", "Access", "Who can search whose data?"),
    ("governance", "Governance", "Which laws and ordinances govern which technologies where?"),
    ("adoption", "Adoption", "Which agencies use which technology, and where?"),
)

#: O2 access — the §12.2 access-edge predicates (the sharing/access family;
#: DEGREE_PREDICATES and the ``*_set``/``*_count`` attribute predicates are
#: deliberately absent — a count or set literal is never an edge).
ACCESS_PREDS = frozenset(
    {
        "configured_sharing_partner",
        "sharing_partner",
        "federates_search_to",
        "requests_data_from",
        "distributes_list_to",
        "live_stream_permitted_to",
        "third_party_integration",
        "holds_data_collected_by",
        "configured_access_edge",
        "observed_use_edge",
    }
)
#: O5 governance — instrument/jurisdiction/technology/body predicates.
GOVERNANCE_PLACE_PREDS = frozenset({"bill_jurisdiction", "in_jurisdiction"})
GOVERNANCE_TECH_PREDS = frozenset(
    {
        "constrains_technology",
        "constrains_capability",
        "event_technologies",
        "implements_technology",
        "requires_authorization_of",
        "technology",
        "technology_category",
    }
)
GOVERNANCE_BODY_PREDS = frozenset({"enacting_body", "oversight_body"})
#: O7 adoption — "the agency uses the technology" predicates.
ADOPTION_PREDS = frozenset(
    {
        "deployment_exists",
        "in_use",
        "uses_facial_recognition",
        "uses_ai_surveillance",
        "procured_technology",
        "implements_technology",
        "technology",
        "technology_category",
        "deployed",
    }
)
#: The subject kinds O5 reads (bills, instruments/ordinances → ``policy``,
#: and agenda items whose technologies are recorded — O6 folds into O5).
GOVERNANCE_SUBJECT_KINDS = frozenset({"bill", "policy", "event"})
#: Literal values that carry no party/technology name — never a node label.
_BOOL_LITERALS = frozenset({"true", "false", "yes", "no", "1", "0"})

#: Literal-party predicates — a text value naming an organisation (O0's
#: kind→org edges + O1/O3/O4's literal counterparties).
SUPPLY_BUYER_PREDS = frozenset({"buyer"})
SUPPLY_SELLER_PREDS = frozenset({"seller", "vendor"})
FUNDER_PREDS = frozenset({"funder"})
RECIPIENT_PREDS = frozenset({"recipient", "recipient_name"})
#: O4 — operator predicates only. ``published_by`` and ``operator_absent``
#: are deliberately absent (NEW-2 / H-12; absence is a count, not an edge).
OPERATOR_PREDS = frozenset({"camera_operator", "operator_stated", "asset_operator"})
MANUFACTURER_PREDS = frozenset({"manufacturer"})
#: The O0 literal-side kind bucket for party predicates.
_PARTY_LITERAL_PREDS = (
    SUPPLY_BUYER_PREDS
    | SUPPLY_SELLER_PREDS
    | FUNDER_PREDS
    | RECIPIENT_PREDS
    | OPERATOR_PREDS
    | MANUFACTURER_PREDS
    | {"published_by", "enacting_body", "oversight_body"}
)

#: Display-kind bands in draw order — K14 §4.7's shape channel reuses the
#: figure kit's kind shapes; ``place``/``kind``/``literal`` draw as entity.
BAND_ORDER: tuple[str, ...] = (
    "kind",
    "place",
    "agency",
    "vendor",
    "site",
    "technology",
    "instrument",
    "entity",
    "group",
)
#: Entity-label kind → figure band.
_KIND_TO_BAND = {
    "agency": "agency",
    "jurisdiction": "place",
    "site": "site",
    "notice": "instrument",
    "contract": "instrument",
    "grant": "instrument",
    "bill": "instrument",
    "policy": "instrument",
    "event": "instrument",
}
#: figure-kit shape kinds for bands outside ``kind_shape_path``'s own map.
_BAND_SHAPE = {"place": "site", "kind": "source", "entity": "entity", "technology": "entity"}

_LAYOUT_PITCH = 18.0
_LAYOUT_COLS = 14
_LAYOUT_BAND_W = 340.0
_LAYOUT_LABEL_MIN_DEGREE = 4


class GraphOverviewError(Exception):
    """A fail-closed overview fault — the build never silently truncates."""


@dataclass(frozen=True)
class PlaceInfo:
    """One jurisdiction's public name + display path (K4 slug path)."""

    name: str
    slug_path: str
    level: str = ""


@dataclass
class _Node:
    key: str
    label: str
    band: str
    place: str | None = None
    href: str | None = None
    count: int = 0
    basis: str | None = None


@dataclass
class _Edge:
    src: str
    dst: str
    relation: str
    predicates: set[str] = field(default_factory=set)
    claim_ids: set[str] = field(default_factory=set)
    source_ids: set[str] = field(default_factory=set)
    observed: set[str] = field(default_factory=set)
    #: The distinct member nodes a matrix fold aggregated into this cell —
    #: empty on an unfolded edge (``member_count`` 0 = not aggregated).
    members: set[str] = field(default_factory=set)
    date_kind: str = "undated"
    historical: bool = False


def _place_name(places: Mapping[str, PlaceInfo], jkey: str) -> str:
    info = places.get(jkey)
    if info is not None and info.name:
        return info.name
    leaf = jkey.rsplit("-", 1)[-1] if "-" in jkey else jkey
    return leaf.replace("_", " ") or jkey


def _place_path(places: Mapping[str, PlaceInfo], jkey: str) -> str | None:
    info = places.get(jkey)
    if info is not None and info.slug_path:
        return f"graphs/__OV__/{info.slug_path}/"
    parts = jkey.split("-")
    if len(parts) >= 2:
        return f"graphs/__OV__/{'/'.join(parts[:2])}/"
    return None


def _literal_label(text: str) -> str | None:
    """The display label for a source-stated literal party, or ``None``.

    The same rule ``spine_export._literal_partner_label`` carries: the
    person screen runs first; a text the shared derivation cannot name
    withholds the whole edge (Part VIII / K2 R-8).
    """
    text = (text or "").strip()
    if not text or natural_person_signal(text):
        return None
    from policy.labels import LabelFacts, derive_label

    lbl = derive_label(
        LabelFacts(
            entity_id=f"literal:{text}",
            kind="org",
            disposition="allow",
            canonical_name=text,
        ),
        person_screen=lambda t: bool(natural_person_signal(t)),
    )
    if lbl.label is None or lbl.label_basis == "fallback":
        return None
    return lbl.label


def _published(label: EntityLabel | None) -> bool:
    return (
        label is not None
        and label.label is not None
        and label.label_state is None
        and label.kind != "person"
    )


def _entity_node(
    nodes: dict[str, _Node], eid: str, labels: Mapping[str, EntityLabel]
) -> str | None:
    """The node key for a published entity, or ``None`` (dropped edge)."""
    if eid in nodes:
        return eid
    lbl = labels.get(eid)
    if not _published(lbl):
        return None
    assert lbl is not None
    band = _KIND_TO_BAND.get(lbl.kind or "", "entity" if lbl.kind != "org" else "vendor")
    nodes[eid] = _Node(
        key=eid,
        label=str(lbl.label),
        band=band,
        place=lbl.place_jkey or None,
        href=lbl.url or None,
        basis=lbl.label_basis,
    )
    return eid


def _literal_node(
    nodes: dict[str, _Node],
    text: str,
    *,
    band: str,
) -> str | None:
    """The node key for a literal party name, or ``None`` when withheld."""
    key = f"lit:{text.strip().lower()}"
    if key in nodes:
        return key
    label = _literal_label(text)
    if label is None:
        return None
    nodes[key] = _Node(key=key, label=label, band=band, basis="source_name")
    return key


def _add_edge(
    edges: dict[tuple[str, str, str], _Edge],
    *,
    src: str | None,
    dst: str | None,
    relation: str,
    predicate: str,
    claim_id: str | None,
    source_id: str | None,
    observed: str | None,
) -> None:
    """Merge one claim into the (src, dst, relation) edge — claims accumulate."""
    if src is None or dst is None or src == dst:
        return
    if predicate in DEGREE_PREDICATES:
        raise GraphOverviewError(f"degree predicate {predicate} can never mint an edge")
    edge = edges.setdefault((src, dst, relation), _Edge(src=src, dst=dst, relation=relation))
    edge.predicates.add(predicate)
    if claim_id:
        edge.claim_ids.add(claim_id)
    if source_id:
        edge.source_ids.add(source_id)
    if observed:
        edge.observed.add(observed)


def _admin1(
    ancestors: Mapping[str, tuple[str, ...]], places: Mapping[str, PlaceInfo], jkey: str | None
) -> str | None:
    """The admin-1 ancestor of a place key for the headline operator view."""
    if not jkey:
        return None
    chain = ancestors.get(jkey) or (jkey,)
    for key in chain:
        if (places.get(key) or PlaceInfo("", "", "")).level == "state_province":
            return key
    return jkey


# ---------------------------------------------------------------------------
# Edge collectors — one per 08a overview
# ---------------------------------------------------------------------------


def _types(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O0 — the kind map: every label kind (gaps included) + kind→kind edges."""
    nodes: dict[str, _Node] = {}
    counts: dict[str, int] = {}
    for lbl in labels.values():
        if _published(lbl):
            counts[lbl.kind or "other"] = counts.get(lbl.kind or "other", 0) + 1
    for kind in KINDS:
        word = KIND_WORDS.get(kind, kind.title())
        nodes[f"kind:{kind}"] = _Node(
            key=f"kind:{kind}",
            label=word,
            band="kind",
            href=f"/entity/{kind}/" if kind in _ep.PAGE_KINDS else None,
            count=counts.get(kind, 0),
        )
    edges: dict[tuple[str, str, str], _Edge] = {}
    for sid, claims in by_subject.items():
        sl = labels.get(sid)
        if not _published(sl):
            continue
        assert sl is not None
        for c in claims:
            if c.predicate_id in DEGREE_PREDICATES:
                continue
            okind: str | None = None
            if c.object_entity:
                ol = labels.get(c.object_entity)
                if _published(ol):
                    okind = ol.kind  # type: ignore[union-attr]
            elif c.predicate_id in _PARTY_LITERAL_PREDS and c.value:
                okind = "org"
            if not okind or okind == "person":
                continue
            _add_edge(
                edges,
                src=f"kind:{sl.kind}",
                dst=f"kind:{okind}",
                relation=c.predicate_id.replace("_", " "),
                predicate=c.predicate_id,
                claim_id=c.claim_id,
                source_id=c.source_id,
                observed=_norm_iso_date(c.observed_at),
            )
    return nodes, edges


def _counterparties(
    claims: Sequence[_ep.PageClaim],
    predicates: frozenset[str],
    labels: Mapping[str, EntityLabel],
    nodes: dict[str, _Node],
    *,
    band: str,
) -> list[str]:
    """Entity-ref or literal counterparty node keys for ``predicates``."""
    out: list[str] = []
    for c in claims:
        if c.predicate_id not in predicates:
            continue
        key = (
            _entity_node(nodes, c.object_entity, labels)
            if c.object_entity
            else (_literal_node(nodes, c.value or "", band=band) if c.value else None)
        )
        if key and key not in out:
            out.append(key)
    return out


def _party_pairs(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
    *,
    subject_kinds: frozenset[str],
    left_preds: frozenset[str],
    right_preds: frozenset[str],
    left_band: str,
    right_band: str,
    relation: str,
    gate: Any = None,
    nodes: dict[str, _Node] | None = None,
    edges: dict[tuple[str, str, str], _Edge] | None = None,
) -> None:
    """left→right edge pairs over page-kind subjects' party claims."""
    assert nodes is not None and edges is not None
    for sid, claims in by_subject.items():
        sl = labels.get(sid)
        if not _published(sl) or sl.kind not in subject_kinds:  # type: ignore[union-attr]
            continue
        if gate is not None and not gate(sl):
            continue
        lefts = _counterparties(claims, left_preds, labels, nodes, band=left_band)
        rights = _counterparties(claims, right_preds, labels, nodes, band=right_band)
        pairs = [(lf, rt) for lf in lefts for rt in rights]
        if not pairs:
            # A single-sided record still shows its named party — the
            # subject entity node carries the honest one-sided row.
            skey = _entity_node(nodes, sid, labels)
            if skey:
                for cp in lefts + rights:
                    _add_edge(
                        edges,
                        src=skey,
                        dst=cp,
                        relation=f"{relation} (party unstated)",
                        predicate=sorted(left_preds | right_preds)[0],
                        claim_id=None,
                        source_id=None,
                        observed=None,
                    )
            continue
        for lf, rt in pairs:
            cids = {c.claim_id for c in claims if c.predicate_id in left_preds | right_preds}
            srcs = {
                c.source_id
                for c in claims
                if c.predicate_id in left_preds | right_preds and c.source_id
            }
            obs = {
                d
                for c in claims
                if c.predicate_id in left_preds | right_preds
                for d in [_norm_iso_date(c.observed_at)]
                if d
            }
            e = edges.setdefault((lf, rt, relation), _Edge(src=lf, dst=rt, relation=relation))
            e.predicates.update(left_preds | right_preds)
            e.claim_ids.update(cids)
            e.source_ids.update(s for s in srcs if s)
            e.observed.update(obs)


def _supply(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
    relevance: Mapping[str, str],
    relevance_fields: Mapping[str, Mapping[str, Any]],
    value_claims: Sequence[Any],
    places: Mapping[str, PlaceInfo],
    ancestors: Mapping[str, tuple[str, ...]],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O1 — buyer→vendor, relevance-gated (D-K2-5), plus manufacturer sites."""
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}

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

    _party_pairs(
        labels,
        by_subject,
        subject_kinds=frozenset({"notice", "contract"}),
        left_preds=SUPPLY_BUYER_PREDS,
        right_preds=SUPPLY_SELLER_PREDS,
        left_band="agency",
        right_band="vendor",
        relation="sells to",
        gate=_ok,
        nodes=nodes,
        edges=edges,
    )
    # Manufacturer sites — collapsed per (manufacturer, place) into group
    # nodes ("N camera records — <place>"); a site is never a supply node.
    manu_sites: dict[tuple[str, str | None], list[str]] = {}
    for c in value_claims:
        if getattr(c, "predicate_id", None) not in MANUFACTURER_PREDS:
            continue
        sid = getattr(c, "subject_id", "")
        lbl = labels.get(sid)
        if not _published(lbl) or getattr(c, "value_text", None) in (None, ""):
            continue
        manu_sites.setdefault((str(c.value_text), getattr(lbl, "place_jkey", None)), []).append(sid)
    for (manu, jkey), sids in sorted(manu_sites.items()):
        vnode = _literal_node(nodes, manu, band="vendor")
        if vnode is None:
            continue
        place = _admin1(ancestors, places, jkey)
        pname = _place_name(places, place) if place else "not yet placed"
        gkey = f"grp:sites:{manu.strip().lower()}:{place or 'unplaced'}"
        nodes[gkey] = _Node(
            key=gkey,
            label=f"{len(sids)} camera records — {pname}",
            band="group",
            place=place,
            href=(
                f"/graphs/supply/{(places.get(place) or PlaceInfo('', '', '')).slug_path}/"
                if place and place in places
                else None
            ),
            count=len(sids),
        )
        _add_edge(
            edges,
            src=gkey,
            dst=vnode,
            relation="manufactured by",
            predicate="manufacturer",
            claim_id=None,
            source_id=None,
            observed=None,
        )
    return nodes, edges


def _funding(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O3 — funder→recipient pairs on grant subjects."""
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}
    _party_pairs(
        labels,
        by_subject,
        subject_kinds=frozenset({"grant"}),
        left_preds=FUNDER_PREDS,
        right_preds=RECIPIENT_PREDS,
        left_band="agency",
        right_band="agency",
        relation="funds",
        nodes=nodes,
        edges=edges,
    )
    return nodes, edges


def _operators(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
    value_claims: Sequence[Any],
    places: Mapping[str, PlaceInfo],
    ancestors: Mapping[str, tuple[str, ...]],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O4 — operator → admin-1 place. ``published_by`` never mints an edge."""
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}

    def _place_node(jkey: str | None) -> str:
        key = f"place:{jkey or 'unplaced'}"
        if key not in nodes:
            nodes[key] = _Node(
                key=key,
                label=_place_name(places, jkey) if jkey else "Not yet placed",
                band="place",
                place=jkey,
                href=(
                    ((_place_path(places, jkey) or "").replace("__OV__", "operators") or None)
                    if jkey
                    else None
                ),
            )
        return key

    def _emit(
        sid: str, op_key: str | None, claims: Sequence[tuple[str | None, str | None, str | None]]
    ) -> None:
        if op_key is None:
            return
        lbl = labels.get(sid)
        place = _admin1(ancestors, places, getattr(lbl, "place_jkey", None))
        pkey = _place_node(place)
        for cid, src, obs in claims:
            _add_edge(
                edges,
                src=op_key,
                dst=pkey,
                relation="operates in",
                predicate="camera_operator",
                claim_id=cid,
                source_id=src,
                observed=obs,
            )

    # Entity-ref operators — org entities the twin seams already carry.
    for sid, claims in by_subject.items():
        sl = labels.get(sid)
        if not _published(sl) or (sl.kind or "") != "site":  # type: ignore[union-attr]
            continue
        for c in claims:
            if c.predicate_id not in OPERATOR_PREDS or not c.object_entity:
                continue
            _emit(
                sid,
                _entity_node(nodes, c.object_entity, labels),
                [(c.claim_id, c.source_id, _norm_iso_date(c.observed_at))],
            )
    # Literal operators — the shaping claims' verbatim values, screened.
    for c in value_claims:
        if getattr(c, "predicate_id", None) not in OPERATOR_PREDS:
            continue
        sid = str(getattr(c, "subject_id", ""))
        lbl = labels.get(sid)
        if not _published(lbl):
            continue
        text = getattr(c, "value_text", None) or getattr(c, "raw_value", None)
        _emit(
            sid,
            _literal_node(nodes, str(text or ""), band="vendor"),
            [
                (
                    getattr(c, "claim_id", None),
                    getattr(c, "source_id", None),
                    _norm_iso_date(getattr(c, "observed_at", None)),
                )
            ],
        )
    return nodes, edges


def _access(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O2 — subject → sharing partner on the §12.2 access predicates.

    Direction is the recorded edge direction (the subject's snapshot asserts
    the configured access); the relation names the §12.2 access kind so the
    three kinds stay visibly separate (SIG-UI-024). A literal partner value
    runs the shared person screen before it can be a node (Part VIII); a
    withheld or review-pending partner drops the whole edge (A-10).
    """
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}
    relation_for = {
        "configured_access": "configured access to",
        "observed_use": "observed access to",
        "declared_policy": "declared-policy access to",
    }
    for sid, claims in by_subject.items():
        for c in claims:
            if c.predicate_id not in ACCESS_PREDS:
                continue
            kind = _ep._access_kind_for(c.predicate_id) or "configured_access"
            relation = relation_for.get(kind, "access to")
            if c.object_entity:
                dst = _entity_node(nodes, c.object_entity, labels)
            else:
                val = (c.value or "").strip()
                dst = (
                    _literal_node(nodes, val, band="agency")
                    if val and val.lower() not in _BOOL_LITERALS
                    else None
                )
            _add_edge(
                edges,
                src=_entity_node(nodes, sid, labels),
                dst=dst,
                relation=relation,
                predicate=c.predicate_id,
                claim_id=c.claim_id,
                source_id=c.source_id,
                observed=_norm_iso_date(c.observed_at),
            )
    return nodes, edges


def _governance(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
    places: Mapping[str, PlaceInfo],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O5 — laws/ordinances → jurisdictions, technologies and bodies."""
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}

    def _juris_node(c: _ep.PageClaim) -> str | None:
        if c.object_entity:
            return _entity_node(nodes, c.object_entity, labels)
        text = (c.value or "").strip()
        if not text or text.lower() in _BOOL_LITERALS:
            return None
        key = f"place-lit:{text.lower()}"
        if key not in nodes:
            nodes[key] = _Node(key=key, label=text, band="place", basis="source_name")
        return key

    for sid, claims in by_subject.items():
        sl = labels.get(sid)
        if not _published(sl) or sl.kind not in GOVERNANCE_SUBJECT_KINDS:  # type: ignore[union-attr]
            continue
        skey = _entity_node(nodes, sid, labels)
        for c in claims:
            if c.predicate_id in GOVERNANCE_PLACE_PREDS:
                _add_edge(
                    edges,
                    src=skey,
                    dst=_juris_node(c),
                    relation="in jurisdiction",
                    predicate=c.predicate_id,
                    claim_id=c.claim_id,
                    source_id=c.source_id,
                    observed=_norm_iso_date(c.observed_at),
                )
            elif c.predicate_id in GOVERNANCE_TECH_PREDS:
                tech = (
                    _entity_node(nodes, c.object_entity, labels)
                    if c.object_entity
                    else (
                        _literal_node(nodes, (c.value or "").strip(), band="technology")
                        if (c.value or "").strip()
                        else None
                    )
                )
                _add_edge(
                    edges,
                    src=skey,
                    dst=tech,
                    relation=c.predicate_id.replace("_", " "),
                    predicate=c.predicate_id,
                    claim_id=c.claim_id,
                    source_id=c.source_id,
                    observed=_norm_iso_date(c.observed_at),
                )
            elif c.predicate_id in GOVERNANCE_BODY_PREDS:
                body = (
                    _entity_node(nodes, c.object_entity, labels)
                    if c.object_entity
                    else (
                        _literal_node(nodes, (c.value or "").strip(), band="agency")
                        if (c.value or "").strip()
                        else None
                    )
                )
                _add_edge(
                    edges,
                    src=body,
                    dst=skey,
                    relation=("enacts" if c.predicate_id == "enacting_body" else "oversees"),
                    predicate=c.predicate_id,
                    claim_id=c.claim_id,
                    source_id=c.source_id,
                    observed=_norm_iso_date(c.observed_at),
                )
    return nodes, edges


def _technology_key(
    nodes: dict[str, _Node],
    c: _ep.PageClaim,
    labels: Mapping[str, EntityLabel],
) -> str | None:
    """The technology node a claim names — entity-ref, the recorded literal,
    or the predicate-derived word for ``uses_*``/boolean deployments."""
    if c.object_entity:
        return _entity_node(nodes, c.object_entity, labels)
    text = (c.value or "").strip()
    if text and text.lower() not in _BOOL_LITERALS:
        return _literal_node(nodes, text, band="technology")
    if c.predicate_id.startswith("uses_"):
        word = c.predicate_id[len("uses_") :].replace("_", " ")
        key = f"tech:{word}"
        if key not in nodes:
            nodes[key] = _Node(key=key, label=word.title(), band="technology", basis="predicate")
        return key
    return None


def _adoption(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge]]:
    """O7 — agency/atlas subject → technology, on the adoption predicates."""
    nodes: dict[str, _Node] = {}
    edges: dict[tuple[str, str, str], _Edge] = {}
    for sid, claims in by_subject.items():
        for c in claims:
            if c.predicate_id not in ADOPTION_PREDS:
                continue
            _add_edge(
                edges,
                src=_entity_node(nodes, sid, labels),
                dst=_technology_key(nodes, c, labels),
                relation="uses",
                predicate=c.predicate_id,
                claim_id=c.claim_id,
                source_id=c.source_id,
                observed=_norm_iso_date(c.observed_at),
            )
    return nodes, edges


def _fold_to_places(
    nodes: dict[str, _Node],
    edges: dict[tuple[str, str, str], _Edge],
    *,
    foldable: Any,
    places: Mapping[str, PlaceInfo],
    ancestors: Mapping[str, tuple[str, ...]],
    labels: Mapping[str, EntityLabel],
) -> tuple[dict[str, _Node], dict[tuple[str, str, str], _Edge], dict[str, str], list[str]]:
    """Fold every node ``foldable(key, node)`` selects to its admin-1 place.

    Returns the folded (nodes, edges), the ``fold_map`` (original key → place
    jkey or ``"unplaced"``), and the declared cap_actions. Folded member keys
    ride each merged edge's ``members`` for the ``member_count`` cell weight.
    """
    fold_map: dict[str, str] = {}
    for key, n in nodes.items():
        if foldable(key, n):
            jkey = n.place
            if jkey is None and not key.startswith(
                ("lit:", "place:", "tech:", "grp:", "place-lit:")
            ):
                jkey = getattr(labels.get(key), "place_jkey", None) or None
            fold_map[key] = _admin1(ancestors, places, jkey) or "unplaced"

    def _folded(key: str) -> str:
        jkey = fold_map.get(key)
        if jkey is None:
            return key
        fkey = f"place:{jkey}"
        if fkey not in fnodes:
            fnodes[fkey] = _Node(
                key=fkey,
                label=_place_name(places, jkey) if jkey != "unplaced" else "Not yet placed",
                band="place",
                place=None if jkey == "unplaced" else jkey,
            )
        return fkey

    fedges: dict[tuple[str, str, str], _Edge] = {}
    fnodes: dict[str, _Node] = {k: n for k, n in nodes.items() if k not in fold_map}
    for (src, dst, rel), e in edges.items():
        fs, fd = _folded(src), _folded(dst)
        merged = fedges.setdefault((fs, fd, rel), _Edge(src=fs, dst=fd, relation=rel))
        merged.predicates |= e.predicates
        merged.claim_ids |= e.claim_ids
        merged.source_ids |= e.source_ids
        merged.observed |= e.observed
        for end in (src, dst):
            merged.members.add(end) if end in fold_map else None
            merged.members |= {m for m in e.members}
    folded_nodes = {k: n for k, n in fnodes.items()}
    actions = [
        f"matrix fold: {len(fold_map)} member nodes folded to "
        f"{len(set(fold_map.values()))} place cells — {len(edges)} edges merged into "
        f"{len(fedges)} weighted cells (agency-level detail on the place drill-downs "
        "and each entity's page)"
    ]
    return folded_nodes, fedges, fold_map, actions


# ---------------------------------------------------------------------------
# Collapse + emit
# ---------------------------------------------------------------------------


def _collapse_degree_one(
    nodes: dict[str, _Node],
    edges: dict[tuple[str, str, str], _Edge],
    *,
    side: str,
    noun: str,
) -> list[str]:
    """Fold each hub's >COLLAPSE_MIN degree-1 literal ``side`` neighbours into
    one group node ("N <noun>") linked to the hub's page — the K2 aggregation."""
    actions: list[str] = []
    degree: dict[str, int] = {}
    for e in edges.values():
        degree[e.src] = degree.get(e.src, 0) + 1
        degree[e.dst] = degree.get(e.dst, 0) + 1
    hubs: dict[str, list[tuple[tuple[str, str, str], _Edge]]] = {}
    for key, e in edges.items():
        for end, other in ((e.src, e.dst), (e.dst, e.src)):
            n = nodes.get(other)
            if (
                n is not None
                and n.band == side
                and n.key.startswith("lit:")
                and degree.get(other) == 1
            ):
                hubs.setdefault(end, []).append((key, e))
    for hub, hits in sorted(hubs.items()):
        if len(hits) <= COLLAPSE_MIN:
            continue
        hub_node = nodes[hub]
        gkey = f"grp:{side}:{hub}"
        nodes[gkey] = _Node(
            key=gkey,
            label=f"{len(hits)} {noun}",
            band="group",
            place=hub_node.place,
            href=hub_node.href,
            count=len(hits),
        )
        for key, e in hits:
            leaf = e.dst if e.src == hub else e.src
            merged = edges.setdefault(
                (hub, gkey, f"with {len(hits)} {noun}"),
                _Edge(src=hub, dst=gkey, relation=f"with {len(hits)} {noun}"),
            )
            merged.predicates.update(e.predicates)
            merged.claim_ids.update(e.claim_ids)
            merged.source_ids.update(e.source_ids)
            merged.observed.update(e.observed)
            del edges[key]
            nodes.pop(leaf, None)
        actions.append(
            f"{hub}: collapsed {len(hits)} degree-1 {side} nodes into '{len(hits)} {noun}'"
        )
    return actions


def _layout(nodes: Mapping[str, _Node]) -> dict[str, tuple[float, float]]:
    """The deterministic banded grid — band index × serpentine position."""
    bands: dict[str, list[_Node]] = {}
    for n in nodes.values():
        bands.setdefault(n.band, []).append(n)
    pos: dict[str, tuple[float, float]] = {}
    for bi, band in enumerate(BAND_ORDER):
        members = sorted(bands.get(band, []), key=lambda n: (n.label, n.key))
        for i, n in enumerate(members):
            pos[n.key] = (
                bi * _LAYOUT_BAND_W + 40.0 + (i % _LAYOUT_COLS) * _LAYOUT_PITCH,
                60.0 + (i // _LAYOUT_COLS) * _LAYOUT_PITCH,
            )
    return pos


def _emit_svg(
    nodes: Mapping[str, _Node],
    edges: Sequence[_Edge],
    pos: Mapping[str, tuple[float, float]],
    *,
    title: str,
    release_label: str,
    as_of: str,
) -> str:
    """The static overview SVG — edges one compound path, nodes kind shapes."""
    height = 80.0 + max((y for _, y in pos.values()), default=0.0) + 30.0
    width = len(BAND_ORDER) * _LAYOUT_BAND_W
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {_f(width)} {_f(height)}" role="img">',
        f"<title>{_esc(title)}</title>",
        f"<desc>Release {_esc(release_label)} as of {_esc(as_of)} — {_esc(POSITION_NOTE)}</desc>",
    ]
    for bi, band in enumerate(BAND_ORDER):
        members = [n for n in nodes.values() if n.band == band]
        if not members:
            continue
        x = bi * _LAYOUT_BAND_W + 40.0
        parts.append(
            f'<text x="{_f(x)}" y="30" class="sig-graph-band">{_esc(band)} ({len(members)})</text>'
        )
    eparts: list[str] = []
    for e in edges:
        a, b = pos.get(e.src), pos.get(e.dst)
        if a is None or b is None:
            continue
        cur = (
            "historical" if e.historical else ("undated" if e.date_kind == "undated" else "current")
        )
        eparts.append(
            f'<path d="M{_f(a[0])} {_f(a[1])}L{_f(b[0])} {_f(b[1])}" '
            f'class="sig-graph-edge sig-graph-edge-{cur}"/>'
        )
    parts.append('<g aria-hidden="true">' + "".join(eparts) + "</g>")
    degree: dict[str, int] = {}
    for e in edges:
        degree[e.src] = degree.get(e.src, 0) + 1
        degree[e.dst] = degree.get(e.dst, 0) + 1
    for n in sorted(nodes.values(), key=lambda n: (n.band, n.label, n.key)):
        x, y = pos[n.key]
        shape = _BAND_SHAPE.get(
            n.band,
            n.band
            if n.band in ("agency", "vendor", "site", "instrument", "entity", "group", "source")
            else "entity",
        )
        d = kind_shape_path(shape, x, y)
        el = (
            f'<path d="{d}" class="sig-graph-node sig-graph-node-{n.band}">'
            f"<title>{_esc(n.label)}</title></path>"
        )
        if n.href:
            el = f'<a href="{_esc(n.href)}">{el}</a>'
        parts.append(el)
        if n.band in ("kind", "group") or degree.get(n.key, 0) >= _LAYOUT_LABEL_MIN_DEGREE:
            text = n.label if len(n.label) <= 28 else n.label[:27] + "…"
            parts.append(
                f'<text x="{_f(x + 8)}" y="{_f(y + 4)}" class="sig-graph-label">{_esc(text)}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def _f(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def _esc(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _edge_fields(
    e: _Edge, *, lineage: Mapping[str, str], as_of: Any, source_names: Mapping[str, str]
) -> dict[str, Any]:
    """The H-2 edge fields — derived, never constants (SIG-EXPORT-015)."""
    observed = sorted(e.observed)[0] if e.observed else None
    date_kind = "observed" if observed else "undated"
    currency = _currency_word(sorted(e.predicates), observed, as_of)
    sources = sorted({source_names.get(s, s) for s in e.source_ids})
    return {
        "relation": e.relation,
        "predicates": sorted(e.predicates),
        "date": observed,
        "date_kind": date_kind,
        "currency": currency,
        "support": _support_word(sorted(e.claim_ids), lineage),
        "sources": sources,
        "source_ids": sorted(e.source_ids),
        "claim_ids": sorted(e.claim_ids),
        "evidence_count": len(e.claim_ids),
        # The matrix cell weight — distinct folded member nodes (0 on an
        # unfolded edge).
        "member_count": len(e.members),
        "historical": currency == "HISTORICAL",
    }


def _claim_comp(
    rights: Mapping[str, RightsRecord],
    rights_id: str,
    *,
    registry: Mapping[str, Any] | None,
    default_compartment: str,
) -> str:
    rec = rights.get(rights_id)
    if rec is None or export_refusal_reason(rec, registry) is not None:
        return default_compartment
    try:
        comp = C.compartment_for_license(compute_export_license([rec], registry), None, registry)
    except Exception:  # noqa: BLE001 — a licence failure files to the default compartment
        return default_compartment
    return str(comp) if comp else default_compartment


def _csv(rows: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(columns), extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow({k: (";".join(v) if isinstance(v, list) else v) for k, v in r.items()})
    return buf.getvalue().encode("utf-8")


def node_column_specs() -> tuple[Any, ...]:
    from .column_registry import ColumnSpec as _CS

    return (
        _CS(
            "node_id",
            "the overview node key (entity id, literal key, group or place key)",
            nullable=False,
        ),
        _CS(
            "label",
            "the display label (sig.entity-label/1 or the screened literal)",
            nullable=False,
        ),
        _CS(
            "kind",
            "the display band (kind|place|agency|vendor|site|instrument|entity|group)",
            nullable=False,
        ),
        _CS("place_key", "the node's jurisdiction key when one is recorded"),
        _CS("href", "the node's link target when it has one"),
        _CS("member_count", "the group/aggregate member count or entity count for kind nodes"),
        _CS("label_basis", "why the label holds (the L-3 vocabulary)"),
    )


def edge_column_specs() -> tuple[Any, ...]:
    from .column_registry import ColumnSpec as _CS

    return (
        _CS("source_id", "the source node key", nullable=False),
        _CS("target_id", "the target node key", nullable=False),
        _CS("relation", "the relation in words (H-2)", nullable=False),
        _CS("predicates", "the backing predicate ids, ;-joined"),
        _CS("date", "the earliest evidenced date (ISO)"),
        _CS("date_kind", "observed | undated"),
        _CS("currency", "the §28.3 currency class"),
        _CS("support", "the §10.7 support floor"),
        _CS("sources", "the bound source names, ;-joined"),
        _CS("claim_ids", "the supporting claim anchors, ;-joined (SIG-EXPORT-015)"),
        _CS("evidence_count", "the claim count"),
        _CS(
            "member_count",
            "the distinct folded member nodes a matrix cell aggregates (0 = unfolded edge)",
        ),
        _CS("historical", "whether the edge is historical-marked"),
    )


NODE_COLUMN_SPECS = node_column_specs()
EDGE_COLUMN_SPECS = edge_column_specs()


def build_overviews(
    labels: Mapping[str, EntityLabel],
    *,
    claim_rows: Sequence[Sequence[Any]],
    value_claims: Sequence[Any],
    relevance: Mapping[str, str],
    relevance_fields: Mapping[str, Mapping[str, Any]],
    lineage: Mapping[str, str],
    source_names: Mapping[str, str],
    places: Mapping[str, PlaceInfo],
    ancestors: Mapping[str, tuple[str, ...]],
    entity_comps: Mapping[str, set[str]],
    default_compartment: str,
    publication: str,
    generated_at: str,
    as_of: Any,
    retrieval: Any,
    registry_license: Mapping[str, Any] | None = None,
) -> dict[str, tuple[Any, str]]:
    """``path → (payload, compartment)`` for the four 08a overviews.

    Emits, per overview × compartment: the columnar
    ``web/graph/<ov>/<comp>.json`` (``sig.graph-overview/1``), the static
    ``overview.<comp>.svg`` and the ``nodes.``/``edges.<comp>.csv``
    downloads (the full-fidelity edge form — claim ids ride the CSV per
    SIG-EXPORT-015), plus the ``web/graph/index.json`` manifest.
    """
    by_subject = page_claims(claim_rows)
    rights = claim_rights(claim_rows, retrieval=retrieval)
    claim_comp: dict[str, str] = {}
    for claims in by_subject.values():
        for c in claims:
            claim_comp[c.claim_id] = _claim_comp(
                rights,
                c.rights_id,
                registry=registry_license,
                default_compartment=default_compartment,
            )
    # ShapingClaim literals file by their own effective rights — the record
    # built from the claim's effective_* fields when the claim-row rights
    # map does not already name the id.
    lit_rights: dict[str, RightsRecord] = {}
    lit_comp: dict[str, str] = {}
    for c in value_claims:
        rid = getattr(c, "effective_rights_id", None)
        cid = getattr(c, "claim_id", None)
        if not (rid and cid):
            continue
        rid = str(rid)
        if rid not in rights and rid not in lit_rights:
            lit_rights[rid] = RightsRecord(
                source_id=str(getattr(c, "source_id", "") or ""),
                spdx=str(getattr(c, "effective_spdx", "") or ""),
                attribution=str(getattr(c, "effective_attribution", "") or ""),
                redistributable=str(getattr(c, "effective_redistributable", "")) == "yes",
                derivative_permitted=str(getattr(c, "effective_derivative_permitted", "")) == "yes",
                terms_url=str(getattr(c, "effective_terms_url", "") or ""),
                retrieval_date=retrieval,
            )
        lit_comp[str(cid)] = _claim_comp(
            {**lit_rights, **rights},
            rid,
            registry=registry_license,
            default_compartment=default_compartment,
        )

    collectors: dict[str, Any] = {
        "types": lambda: _types(labels, by_subject),
        "supply": lambda: _supply(
            labels, by_subject, relevance, relevance_fields, value_claims, places, ancestors
        ),
        "funding": lambda: _funding(labels, by_subject),
        "operators": lambda: _operators(labels, by_subject, value_claims, places, ancestors),
        "access": lambda: _access(labels, by_subject),
        "governance": lambda: _governance(labels, by_subject, places),
        "adoption": lambda: _adoption(labels, by_subject),
    }
    collapse = {"supply": ("vendor", "other suppliers"), "funding": ("agency", "other recipients")}
    # K2 §5.2 — the foldable side of each 08b matrix: O2 folds BOTH ends
    # (every node is an agency/place cell), O5 folds the instrument subject
    # side (nodes incident to the governance predicates), O7 folds the
    # agency side. ``None`` folds nothing — the predicate decides per key.
    foldable: dict[str, Any] = {
        "access": lambda k, n: n.band in ("agency", "vendor", "entity") or k.startswith("lit:"),
        "governance": lambda k, n: k in _gov_subjects,
        "adoption": lambda k, n: n.band in ("agency", "entity"),
    }

    out: dict[str, tuple[Any, str]] = {}
    index_rows: list[dict[str, Any]] = []
    _gov_subjects: set[str] = set()
    for ov_id, title, question in OVERVIEWS:
        nodes, edges = collectors[ov_id]()
        actions: list[str] = []
        if ov_id in collapse:
            side, noun = collapse[ov_id]
            actions = _collapse_degree_one(nodes, edges, side=side, noun=noun)
        # The declared 08b aggregation: past MATRIX_MIN endpoints the
        # foldable side collapses to admin-1 place cells (the weighted
        # matrix — SIG-UI-021, never a national hairball). Unfolded copies
        # stay for the per-place slice docs.
        u_nodes, u_edges = nodes, edges
        fold_map: dict[str, str] = {}
        if ov_id in foldable:
            if ov_id == "governance":
                _gov_subjects = {
                    k
                    for k, n in nodes.items()
                    if not k.startswith(("lit:", "place:", "tech:", "grp:", "place-lit:", "kind:"))
                    and getattr(labels.get(k), "kind", None) in GOVERNANCE_SUBJECT_KINDS
                }
            if len(nodes) > MATRIX_MIN:
                nodes, edges, fold_map, fold_actions = _fold_to_places(
                    nodes,
                    edges,
                    foldable=foldable[ov_id],
                    places=places,
                    ancestors=ancestors,
                    labels=labels,
                )
                actions += fold_actions
        if len(nodes) > NODE_CAP:
            raise GraphOverviewError(
                f"overview {ov_id}: {len(nodes)} nodes exceeds the {NODE_CAP} cap "
                "with no aggregation rule left — refuse, never truncate (SIG-UI-118)"
            )
        edge_fields = {
            k: _edge_fields(e, lineage=lineage, as_of=as_of, source_names=source_names)
            for k, e in edges.items()
        }
        for k, e in edges.items():
            e.date_kind = edge_fields[k]["date_kind"]
            e.historical = edge_fields[k]["historical"]
        pos = _layout(nodes)
        # Per-compartment filing — an edge lands where EVERY claim it cites
        # licenses; a node lands wherever an incident edge lands.
        edge_comps: dict[tuple[str, str, str], set[str]] = {}
        for k, e in edges.items():
            comps = {
                claim_comp.get(cid) or lit_comp.get(cid) or default_compartment
                for cid in e.claim_ids
            }
            edge_comps[k] = comps or {default_compartment}
        node_comps: dict[str, set[str]] = {k: set() for k in nodes}
        for k, e in edges.items():
            node_comps[e.src] |= edge_comps[k]
            node_comps[e.dst] |= edge_comps[k]
        for k in nodes:
            if not node_comps[k]:
                node_comps[k] = set(entity_comps.get(k) or {default_compartment})
        comp_list = sorted({c for s in edge_comps.values() for c in s} | {default_compartment})
        # The unfolded edge set's compartment filing — the slice docs file
        # under exactly the same rule (SIG-LIC-009a, S6R-12).
        u_edge_comps: dict[tuple[str, str, str], set[str]] = {}
        if fold_map:
            for k, e in u_edges.items():
                comps = {
                    claim_comp.get(cid) or lit_comp.get(cid) or default_compartment
                    for cid in e.claim_ids
                }
                u_edge_comps[k] = comps or {default_compartment}
        for comp in comp_list:
            c_nodes = {k: n for k, n in nodes.items() if comp in node_comps[k]}
            c_edges = {k: e for k, e in edges.items() if comp in edge_comps[k]}
            doc, svg, nrows, erows = _emit_doc(
                ov_id,
                title,
                question,
                c_nodes,
                c_edges,
                edge_fields,
                pos,
                publication=publication,
                generated_at=generated_at,
                as_of=as_of,
                compartment=comp,
                actions=actions,
            )
            base = f"web/graph/{ov_id}"
            out[f"{base}/{comp}.json"] = (doc, comp)
            out[f"{base}/overview.{comp}.svg"] = (svg.encode("utf-8"), comp)
            out[f"{base}/nodes.{comp}.csv"] = (
                _csv(nrows, [c.name for c in NODE_COLUMN_SPECS]),
                comp,
            )
            out[f"{base}/edges.{comp}.csv"] = (
                _csv(erows, [c.name for c in EDGE_COLUMN_SPECS]),
                comp,
            )
            # The 08b slice docs — the unfolded agency-level subgraph per
            # admin-1 cell a folded overview aggregated ("per-agency egos
            # grouped by state", K2 §5.2 O2). Same schema, ``slice`` marked.
            for jkey in sorted(set(fold_map.values())):
                s_edges = {
                    k: e
                    for k, e in u_edges.items()
                    if comp in u_edge_comps.get(k, {default_compartment})
                    and (fold_map.get(e.src) == jkey or fold_map.get(e.dst) == jkey)
                }
                if not s_edges:
                    continue
                s_nodes: dict[str, _Node] = {}
                for e in s_edges.values():
                    for end in (e.src, e.dst):
                        n = u_nodes.get(end)
                        if n is not None:
                            s_nodes[end] = n
                # A slice over the cap folds its out-of-place
                # counterparties to their own place cells — bounded, never
                # a smoothed cut (the action rides the slice doc).
                slice_actions: list[str] = []
                if len(s_nodes) > NODE_CAP:
                    inner_fold = {k: v for k, v in fold_map.items() if v != jkey and k in s_nodes}
                    s_nodes, s_edges, _inner_map, inner_actions = _fold_to_places(
                        s_nodes,
                        s_edges,
                        foldable=lambda k, n, f=inner_fold: k in f,
                        places=places,
                        ancestors=ancestors,
                        labels=labels,
                    )
                    slice_actions += inner_actions
                s_fields = {
                    k: _edge_fields(e, lineage=lineage, as_of=as_of, source_names=source_names)
                    for k, e in s_edges.items()
                }
                s_doc, _s_svg, _n, _e = _emit_doc(
                    ov_id,
                    title,
                    question,
                    s_nodes,
                    s_edges,
                    s_fields,
                    _layout(s_nodes),
                    publication=publication,
                    generated_at=generated_at,
                    as_of=as_of,
                    compartment=comp,
                    actions=slice_actions,
                    slice=jkey,
                )
                out[f"{base}/places/{comp}.{jkey}.json"] = (s_doc, comp)
        index_rows.append(
            {
                "id": ov_id,
                "title": title,
                "question": question,
                "nodes": len(nodes),
                "edges": len(edges),
                "compartments": comp_list,
                "cap": NODE_CAP,
                "cap_actions": actions,
                "places": sorted(
                    {
                        n.place
                        for n in nodes.values()
                        if n.place and n.place in places and (places[n.place].slug_path or "")
                    }
                ),
                "slices": sorted(set(fold_map.values())),
            }
        )
    out["web/graph/index.json"] = (
        {
            "schema": INDEX_SCHEMA,
            "release": {
                "label": publication,
                "as_of_world": str(as_of) if as_of else None,
            },
            "generated_at": generated_at,
            "overviews": index_rows,
        },
        default_compartment,
    )
    out.update(
        _component_artifacts(
            labels,
            by_subject,
            claim_comp,
            lit_comp,
            entity_comps,
            default_compartment=default_compartment,
            publication=publication,
            generated_at=generated_at,
            as_of=as_of,
        )
    )
    return out


def _component_artifacts(
    labels: Mapping[str, EntityLabel],
    by_subject: Mapping[str, Sequence[_ep.PageClaim]],
    claim_comp: Mapping[str, str],
    lit_comp: Mapping[str, str],
    entity_comps: Mapping[str, set[str]],
    *,
    default_compartment: str,
    publication: str,
    generated_at: str,
    as_of: Any,
) -> dict[str, tuple[Any, str]]:
    """``sig.graph-components/1`` per compartment (K2 §6.4, SIG-EXPORT-D20).

    The weakly-connected components of the publishable entity-ref graph —
    every claim whose object is another published entity is an undirected
    join — one index per compartment plus one member file per component of
    ≤ ``NODE_CAP`` entities (a larger component splits into named parts;
    the member list is flat, never a graph, so chunking is honest).
    Size-1 components carry no path-search value: the index records their
    count, never the members.
    """
    # comp → undirected entity pair set
    comp_pairs: dict[str, set[tuple[str, str]]] = {}
    for sid, claims in by_subject.items():
        if not _published(labels.get(sid)):
            continue
        for c in claims:
            oid = c.object_entity
            if not oid or c.predicate_id in DEGREE_PREDICATES:
                continue
            if oid == sid or not _published(labels.get(oid)):
                continue
            comp = claim_comp.get(c.claim_id) or lit_comp.get(c.claim_id) or default_compartment
            pair = (sid, oid) if sid < oid else (oid, sid)
            comp_pairs.setdefault(comp, set()).add(pair)
    out: dict[str, tuple[Any, str]] = {}
    # The compartment set = every compartment an edge or entity files under
    # plus the default (an empty graph still emits its index — honest).
    comp_set = {default_compartment} | set(comp_pairs)
    for s in entity_comps.values():
        comp_set |= s
    for comp in sorted(comp_set):
        parent: dict[str, str] = {}

        def find(x: str, p: dict[str, str] = parent) -> str:
            while p.setdefault(x, x) != x:
                p[x] = p[p[x]]
                x = p[x]
            return x

        for a, b in sorted(comp_pairs.get(comp, ())):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
        members: dict[str, set[str]] = {}
        for node in parent:
            members.setdefault(find(node), set()).add(node)
        comps: list[dict[str, Any]] = []
        singletons = 0
        ranked = sorted(members.values(), key=lambda ms: (-len(ms), min(ms)))
        for mem in ranked:
            mem_sorted = sorted(mem)
            if len(mem_sorted) < 2:
                singletons += 1
                continue
            cid = f"cmp-{len(comps) + 1:04d}"
            rows = [
                {
                    "k": eid,
                    "l": labels[eid].label,
                    "t": labels[eid].kind,
                    "h": labels[eid].url,
                }
                for eid in mem_sorted
                if eid in labels
            ]
            files: list[str] = []
            for p in range(0, len(rows), NODE_CAP):
                part = rows[p : p + NODE_CAP]
                suffix = f".part{p // NODE_CAP}" if p else ""
                fname = f"{cid}{suffix}.json"
                files.append(fname)
                out[f"web/graph/components/{comp}/{fname}"] = (
                    {
                        "schema": COMPONENT_SCHEMA,
                        "component_id": cid,
                        "compartment": comp,
                        "release": {
                            "label": publication,
                            "as_of_world": str(as_of) if as_of else None,
                        },
                        "generated_at": generated_at,
                        "size": len(rows),
                        "members": part,
                    },
                    comp,
                )
            comps.append({"component_id": cid, "size": len(rows), "files": files})
        # Singletons — published entities with no publishable entity-ref
        # edge in this compartment — counted honestly, never listed.
        singletons += len(
            [
                eid
                for eid, cs in entity_comps.items()
                if comp in cs
                and _published(labels.get(eid))
                and not any(eid in pair for pair in comp_pairs.get(comp, set()))
            ]
        )
        out[f"web/graph/components/{comp}/index.json"] = (
            {
                "schema": COMPONENTS_INDEX_SCHEMA,
                "compartment": comp,
                "release": {
                    "label": publication,
                    "as_of_world": str(as_of) if as_of else None,
                },
                "generated_at": generated_at,
                "components": comps,
                "singletons": singletons,
            },
            comp,
        )
    return out


def _emit_doc(
    ov_id: str,
    title: str,
    question: str,
    nodes: Mapping[str, _Node],
    edges: Mapping[tuple[str, str, str], _Edge],
    edge_fields: Mapping[tuple[str, str, str], dict[str, Any]],
    pos: Mapping[str, tuple[float, float]],
    *,
    publication: str,
    generated_at: str,
    as_of: Any,
    compartment: str,
    actions: Sequence[str],
    slice: str | None = None,
) -> tuple[dict[str, Any], str, list[dict[str, Any]], list[dict[str, Any]]]:
    """The columnar ``sig.graph-overview/1`` doc + SVG + CSV row sets.

    ``slice`` marks a per-place detail doc (the 08b matrix drill-down) — the
    same schema with the place key it serves recorded.
    """
    node_order = sorted(nodes.values(), key=lambda n: (n.band, n.label, n.key))
    idx = {n.key: i for i, n in enumerate(node_order)}
    dicts: dict[str, list[Any]] = {
        "kinds": [],
        "labels": [],
        "hrefs": [],
        "places": [],
        "predicates": [],
        "dates": [],
        "currency": [],
        "sources": [],
    }

    def _slot(name: str, value: Any) -> int:
        arr = dicts[name]
        try:
            return arr.index(value)
        except ValueError:
            arr.append(value)
            return len(arr) - 1

    place_keys = sorted({n.place for n in node_order if n.place})
    place_map = {k: i for i, k in enumerate(place_keys)}
    dicts["places"] = place_keys
    narr: dict[str, list[Any]] = {
        "id": [],
        "l": [],
        "t": [],
        "j": [],
        "h": [],
        "x": [],
        "y": [],
        "n": [],
    }
    for n in node_order:
        narr["id"].append(n.key)
        narr["l"].append(_slot("labels", n.label))
        narr["t"].append(_slot("kinds", n.band))
        narr["j"].append(place_map.get(n.place, -1) if n.place else -1)
        narr["h"].append(_slot("hrefs", n.href) if n.href else -1)
        x, y = pos.get(n.key, (0.0, 0.0))
        narr["x"].append(round(x, 1))
        narr["y"].append(round(y, 1))
        narr["n"].append(n.count)
    earr: dict[str, list[Any]] = {
        "s": [],
        "t": [],
        "p": [],
        "n": [],
        "y": [],
        "cur": [],
        "src": [],
        "m": [],
    }
    nrows: list[dict[str, Any]] = []
    erows: list[dict[str, Any]] = []
    for n in node_order:
        nrows.append(
            {
                "node_id": n.key,
                "label": n.label,
                "kind": n.band,
                "place_key": n.place or "",
                "href": n.href or "",
                "member_count": n.count or "",
                "label_basis": n.basis or "",
            }
        )
    for (src, dst, _rel), e in sorted(edges.items(), key=lambda kv: kv[0]):
        f = edge_fields[(src, dst, _rel)]
        earr["s"].append(idx[e.src])
        earr["t"].append(idx[e.dst])
        earr["p"].append(_slot("predicates", e.relation))
        earr["n"].append(f["evidence_count"])
        earr["y"].append(_slot("dates", f["date"]) if f["date"] else -1)
        earr["cur"].append(_slot("currency", f["currency"] or "undated"))
        earr["src"].append([_slot("sources", s) for s in f["sources"]])
        earr["m"].append(f["member_count"])
        erows.append(
            {
                "source_id": e.src,
                "target_id": e.dst,
                "relation": e.relation,
                "predicates": f["predicates"],
                "date": f["date"] or "",
                "date_kind": f["date_kind"],
                "currency": f["currency"] or "",
                "support": f["support"],
                "sources": f["sources"],
                "claim_ids": f["claim_ids"],
                "evidence_count": f["evidence_count"],
                "member_count": f["member_count"],
                "historical": f["historical"],
            }
        )
    doc = {
        "schema": OVERVIEW_SCHEMA,
        "overview": ov_id,
        "title": title,
        "question": question,
        "release": {
            "label": publication,
            "as_of_world": str(as_of) if as_of else None,
        },
        "generated_at": generated_at,
        "compartment": compartment,
        "dict": dicts,
        "nodes": narr,
        "edges": earr,
        "cap": NODE_CAP,
        "cap_actions": list(actions),
        "position_note": POSITION_NOTE,
        "er_disclosure": ER_DISCLOSURE,
    }
    if slice is not None:
        doc["slice"] = slice
    svg = _emit_svg(
        nodes,
        [e for e in edges.values()],
        pos,
        title=f"{title} — {question}",
        release_label=publication,
        as_of=str(as_of) if as_of else "",
    )
    return doc, svg, nrows, erows


__all__ = [
    "ACCESS_PREDS",
    "COMPONENT_SCHEMA",
    "COMPONENTS_INDEX_SCHEMA",
    "EDGE_COLUMN_SPECS",
    "ER_DISCLOSURE",
    "GRAPH_EDGES_SCHEMA",
    "GRAPH_NODES_SCHEMA",
    "GraphOverviewError",
    "INDEX_SCHEMA",
    "MATRIX_MIN",
    "NODE_CAP",
    "NODE_COLUMN_SPECS",
    "OPERATOR_PREDS",
    "OVERVIEWS",
    "OVERVIEW_SCHEMA",
    "POSITION_NOTE",
    "PlaceInfo",
    "build_overviews",
]

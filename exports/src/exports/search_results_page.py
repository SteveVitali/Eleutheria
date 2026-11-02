# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The v2 no-JS search results page (P36.39 / K3 SRCH-04 — SIG-SRCH-002,
SIG-SRCH-006, SIG-SRCH-007, SIG-SRCH-008, SIG-SRCH-009).

``GET /v1/releases/{pub or latest}/search?format=html`` (or a browser
``Accept: text/html``) answers this representation of the same
``sig.search-results/2`` page the JSON body carries: the archive chrome
(site nav + dispute link + per-group licences — DR-C4-02), the release
stamp (G3 §6.1 via ``release_stamp_view``), typed sections with cards that
show their evidence basis and match reason, facet GET links, per-group
cursor paging, the honest empty states (K3 §6.4 — never research status,
never recorded absence), HTML error pages for every status (DR-C4-10) and
a "cite this search" block minting the ``sig.workspace-state/2`` snapshot
form with J3 §8.1's interim sentence (ADR-225's posture until TX-13b).

Zero JavaScript (the API ``format=html`` surface is T0 — ADR-155); every
dynamic string is escaped; long identifiers sit in ``<code>`` so the page
reflows at 320 CSS px (DR-C4-14). Entity links ride the card ``href``s the
engine emits — GX-03 keys (P36.29), never minted here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any
from urllib.parse import urlencode

from .release_pages import _e, _layout, release_stamp_view

#: The route path — also the no-JS GET form's action and every facet/cursor
#: link's base. ``{publication_id}`` carries the requested namespace
#: (``latest`` or a ``p-<sha>`` id), so a follow-up link keeps the pointer
#: class the reader asked for.
SEARCH_PATH_V2 = "/v1/releases/{publication_id}/search"

#: Registry-order emission list for the search subset of
#: ``sig.workspace-state/2`` (mirror of ``workspace-state/registry.ts``
#: WORKSPACE_PARAMS — ``v`` and ``view`` mint first, the rest follow the
#: table order). Only parameters the v2 route may actually apply are
#: emitted; ``expand`` is graph-scope in the registry so the alias
#: "show them" affordance never lands in a cite link.
_CITE_PARAM_ORDER = (
    "release",
    "q",
    "type",
    "kind",
    "jurisdiction",
    "technology",
    "source",
    "collection",
    "cursor",
    "within",
)

#: J3 §8.1's interim cite sentence — verbatim from
#: ``web/src/lib/workspace-state/cite.ts`` (INTERIM_CITE_VIEW_TEXT; TX-13b
#: has not landed, so the minted form is shown as copyable text, never a
#: dead anchor).
INTERIM_CITE_SEARCH_TEXT = (
    "The pinned form resolves when the release publishes its site snapshot; "
    "this page is the latest view — an immutable citable copy is not yet published."
)

#: Section headings per catalog doc type (K3 §6.1's typed order).
_SECTION_TITLES = {
    "place": "Places",
    "entity": "Entities",
    "organization": "Organizations",
    "technology": "Technologies",
    "source": "Sources",
    "document": "Documents",
    "page": "Pages",
}


def _query_pairs(
    params: Mapping[str, Any],
    *,
    drop: Sequence[str] = (),
    extra: Mapping[str, str] | None = None,
) -> list[tuple[str, str]]:
    """The request's GET pairs in a stable order — ``format=html`` rides
    every link so the follow-up stays the no-JS representation."""
    out: list[tuple[str, str]] = []
    q = str(params.get("q") or "")
    if q:
        out.append(("q", q))
    for t in params.get("types") or []:
        out.append(("type", str(t)))
    for name in ("kind", "jurisdiction", "source", "technology", "collection"):
        v = (params.get("filters") or {}).get(name)
        if v and name not in drop:
            out.append((name, str(v)))
    out.append(("format", "html"))
    for name in ("cursor", "expand"):
        v = params.get(name)
        if v and name not in drop:
            out.append((name, str(v)))
    for name, value in (extra or {}).items():
        if name in drop:
            continue
        out = [(n, v) for n, v in out if n != name]
        out.append((name, str(value)))
    return out


def _href(action: str, params: Mapping[str, Any], **kw: Any) -> str:
    return f"{action}?{urlencode(_query_pairs(params, **kw))}"


def _cite_form(pub: str, params: Mapping[str, Any]) -> str:
    """The ``sig.workspace-state/2`` snapshot form of this search —
    ``/s/<pub>/search/?v=2&view=list&…`` in registry order (the cite.ts
    ``citeViewHref`` shape, mirrored)."""
    state: dict[str, list[str]] = {"release": [pub]}
    q = str(params.get("q") or "")
    if q:
        state["q"] = [q]
    types = [str(t) for t in (params.get("types") or [])]
    if types:
        state["type"] = types
    for name in ("kind", "jurisdiction", "source", "technology", "collection"):
        v = (params.get("filters") or {}).get(name)
        if v:
            state[name] = [str(v)]
    if params.get("cursor"):
        state["cursor"] = [str(params["cursor"])]
    pairs = [("v", "2"), ("view", "list")]
    for name in _CITE_PARAM_ORDER:
        for value in state.get(name) or []:
            pairs.append((name, value))
    return f"/s/{pub}/search/?{urlencode(pairs)}"


def _card_article(card: Mapping[str, Any]) -> str:
    """One typed result card — ``<article>`` with an ``h3`` link (K3 §6.5),
    its evidence basis (SIG-SRCH-007) and the stated match reason."""
    name = str(card.get("name") or card.get("key") or "")
    href = card.get("href")
    title = f'<a href="{_e(href)}">{_e(name)}</a>' if href else _e(name)
    bits: list[str] = []
    ctype = str(card.get("type") or "")
    label = {
        "place": "Place",
        "entity": "Entity",
        "organization": "Organization",
        "technology": "Technology",
        "source": "Source",
        "document": "Document",
        "page": "Page",
        "record": "Record",
    }.get(ctype, ctype or "Result")
    level = str(card.get("level") or "")
    if level:
        label += f" · {_e(level)}"
    parent = str(card.get("parent") or "")
    if parent:
        label += f" — in {_e(parent)}"
    bits.append(f'<p class="mut">{label}</p>')
    # The evidence basis — per card kind (SIG-SRCH-007).
    basis: list[str] = []
    if ctype == "record":
        if card.get("name_derived"):
            basis.append("<em>name derived — the source gives none</em>")
        if card.get("place"):
            basis.append(_e(card["place"]))
        names = [str(n) for n in (card.get("source_names") or []) if n]
        ids = [str(s) for s in (card.get("sources") or []) if s]
        if names:
            basis.append("source: " + _e("; ".join(names)))
        elif ids:
            basis.append("source: " + _e("; ".join(ids)))
        if card.get("license"):
            basis.append("licence: " + _e(card["license"]))
        if card.get("technology"):
            basis.append("technology: " + _e(card["technology"]))
    else:
        if card.get("source_id"):
            basis.append("source id: <code>" + _e(card["source_id"]) + "</code>")
        if card.get("license"):
            basis.append("licence: " + _e(card["license"]))
        if card.get("family"):
            basis.append(_e(card["family"]))
        if card.get("status"):
            basis.append("status: " + _e(card["status"]))
        recs = card.get("records") or {}
        if recs.get("total") is not None:
            basis.append(
                f"{_e(recs['total'])} record(s) from {_e(recs.get('sources'))} "
                "source(s) in this release"
            )
    if basis:
        bits.append("<p>" + " · ".join(basis) + "</p>")
    matched = str(card.get("matched") or "")
    tier = card.get("tier")
    match_line = f"matched: {_e(matched)}"
    if tier is not None:
        match_line += f" · tier {_e(tier)}"
    bits.append(f'<p class="mut">{match_line}</p>')
    key = card.get("record_key") or card.get("doc_id")
    key_html = f'<p class="mut"><code>{_e(key)}</code></p>' if key else ""
    return f"<article><h3>{title}</h3>{''.join(bits)}{key_html}</article>"


def _alias_card(card: Mapping[str, Any]) -> str:
    """The acronym/term alias card (SIG-SRCH-005 region): the expansion and
    its cited source, the resolved target when it names a SIG thing, else
    the honest "names no record" state — never a relationship claim."""
    key = str(card.get("key") or "")
    expansion = str(card.get("expansion") or "")
    src = str(card.get("expansion_source") or "")
    bits = [
        f"<p><strong>{_e(key)}</strong> = {_e(expansion)}"
        + (f' (<a href="{_e(src)}">source</a>)' if src else "")
        + " — an alias expands a name; it asserts no relationship.</p>"
    ]
    target = card.get("target")
    if isinstance(target, Mapping):
        bits.append(_card_article(target))
    elif target:
        bits.append(f"<p>resolves to <code>{_e(target)}</code></p>")
    else:
        # K3 §6.4: the honest alias-with-no-record state.
        bits.append(
            f"<p><em>SIG's release names no record for {_e(expansion)}. "
            "That is not evidence of any relationship, or of its absence.</em></p>"
        )
    matched = str(card.get("matched") or "alias")
    bits.append(f'<p class="mut">matched: {_e(matched)}</p>')
    return f"<article><h3>{_e(key)} — {_e(expansion)}</h3>{''.join(bits)}</article>"


def _empty_block(result: Mapping[str, Any], action: str, params: Mapping[str, Any]) -> str:
    """K3 §6.4 / SIG-SRCH-008: name what was searched — never research
    status, never a recorded absence."""
    empty = result.get("empty") or {}
    scope = result.get("scope") or {}
    release = result.get("release") or {}
    q = str(params.get("q") or "")
    searched = (
        f"{_e(scope.get('records_searched'))} records in "
        f"{_e(scope.get('groups_searched'))} licence groups searched, "
        f"data as of {_e(release.get('as_of_world'))}"
    )
    if empty.get("kind") == "filtered_to_zero":
        filters = params.get("filters") or {}
        desc = ", ".join(f"{k} = {v}" for k, v in sorted(filters.items())) or "these filters"
        unfiltered = empty.get("matching_without_filters")
        alt = _href(
            action, params, drop=("kind", "jurisdiction", "source", "technology", "collection")
        )
        return (
            f"<p><em>No record matches <strong>{_e(q)}</strong> with {_e(desc)}.</em> "
            f"{_e(unfiltered)} match(es) without those filters — "
            f'<a href="{_e(alt)}">drop the filters</a> ({searched}).</p>'
        )
    return (
        f"<p><em>No record in release {_e(release.get('label'))} matches "
        f"<strong>{_e(q)}</strong></em> ({searched}). This means SIG's "
        "published record does not contain these words. It does not mean "
        "the thing does not exist, and it is not a finding that SIG looked "
        f'for it. <a href="/r/{_e(release.get("publication_id"))}/">Browse '
        'the release</a> — or see <a href="/methodology/">what the '
        "search covers</a>.</p>"
    )


def _facet_block(result: Mapping[str, Any], action: str, params: Mapping[str, Any]) -> str:
    """Facet GET links with counts (K3 §6.1) — each value narrows the same
    query; the selected value stays linkable per ADR-134's rule."""
    facets = result.get("facets") or {}
    titles = {
        "type": "Result type",
        "collection": "Licence group",
        "jurisdiction": "Jurisdiction",
        "source": "Source",
        "technology": "Technology",
    }
    blocks: list[str] = []
    for name in ("type", "collection", "jurisdiction", "source", "technology"):
        vals = facets.get(name) or []
        if not vals:
            continue
        items: list[str] = []
        for pair in vals:
            value, count = str(pair[0]), pair[1]
            current = (params.get("filters") or {}).get(name)
            selected = current == value or (name == "type" and value in (params.get("types") or []))
            link = _href(action, params, drop=("cursor",), extra={name: value})
            mark = " <strong>(selected)</strong>" if selected else ""
            items.append(f'<li><a href="{_e(link)}">{_e(value)}</a> ({_e(count)}){mark}</li>')
        blocks.append(
            f"<fieldset><legend>{_e(titles[name])}</legend><ul>{''.join(items)}</ul></fieldset>"
        )
    if not blocks:
        return ""
    return (
        '<section aria-labelledby="facets-h"><h2 id="facets-h">Narrow this '
        f"search</h2>{''.join(blocks)}</section>"
    )


def search_results_page_v2(
    *,
    requested: str,
    params: Mapping[str, Any],
    result: Mapping[str, Any],
    site_release: Mapping[str, Any] | None = None,
    was_latest: bool = False,
) -> bytes:
    """The complete no-JS results page for one ``sig.search-results/2``
    response — site chrome, stamp, typed sections, cards, facets, per-group
    paging, empty states and "cite this search"."""
    release = result.get("release") or {}
    pub = str(release.get("publication_id") or requested)
    action = SEARCH_PATH_V2.format(publication_id=requested)
    scope = result.get("scope") or {}
    q = str(params.get("q") or "")
    title = f"Search results for {q}" if q else "Search results"

    # The header strip (K3 §6.1): release, as-of, the searched scope —
    # denials named under DR-C4-09, never a bare eligible number.
    excluded = scope.get("excluded_records_by_reason") or {}
    excluded_txt = ""
    if excluded:
        excluded_txt = " · withheld under the current policy — " + ", ".join(
            f"{_e(str(k).replace('_', ' '))}: {_e(v)}" for k, v in sorted(excluded.items())
        )
    strip = (
        f'<p class="mut">Release {_e(release.get("label"))} · data as of '
        f"{_e(release.get('as_of_world'))} · "
        f"{_e(scope.get('records_searched'))} records in "
        f"{_e(scope.get('groups_searched'))} licence groups searched"
        f"{_e(excluded_txt)}</p>"
    )

    # The GET form re-states the request — a plain GET, no script.
    form = (
        f'<form method="get" action="{_e(action)}">'
        '<input type="hidden" name="format" value="html">'
        f'<p><label>Search <input type="search" name="q" value="{_e(q)}" '
        'size="40" maxlength="200" placeholder="words or an exact identifier"></label> '
        '<button type="submit">Search</button></p></form>'
    )

    suggestion = ((result.get("query") or {}).get("suggestion")) or None
    sug_html = ""
    if suggestion:
        orig = str(suggestion.get("original") or q)
        corrected = str(suggestion.get("corrected") or "")
        alt = _href(action, params, extra={"q": orig})
        sug_html = (
            f"<p>Showing results for <em>{_e(corrected)}</em>; "
            f'<a href="{_e(alt)}">search instead for <em>{_e(orig)}</em></a>.</p>'
        )

    cite = _cite_form(pub, params)
    cite_html = (
        '<section aria-labelledby="cite-h"><h2 id="cite-h">Cite this search</h2>'
        f"<p><code>{_e(cite)}</code></p>"
        f'<p class="mut">{_e(INTERIM_CITE_SEARCH_TEXT)}</p></section>'
    )

    parts: list[str] = [strip, form, sug_html, cite_html, _facet_block(result, action, params)]

    # Top matches — identifier, alias and exact-name cards (K3 §6.1).
    top = result.get("top") or []
    if top:
        cards = "".join(
            _alias_card(c) if c.get("type") == "alias" else _card_article(c) for c in top
        )
        parts.append(
            f'<section aria-labelledby="top-h"><h2 id="top-h">Top matches</h2>{cards}</section>'
        )

    # Typed catalog sections.
    for sec in result.get("sections") or []:
        stype = str(sec.get("type") or "")
        heading = _SECTION_TITLES.get(stype, stype.title())
        cards = "".join(_card_article(c) for c in sec.get("results") or [])
        more = ""
        total = int(sec.get("total") or 0)
        shown = len(sec.get("results") or [])
        if total > shown:
            link = _href(action, params, drop=("cursor",), extra={"type": stype})
            more = f'<p><a href="{_e(link)}">more {heading.lower()} ({_e(total)})</a></p>'
        parts.append(
            f'<section aria-labelledby="sec-{_e(stype)}">'
            f'<h2 id="sec-{_e(stype)}">{_e(heading)}</h2>{cards}{more}</section>'
        )

    # Records — grouped by licence compartment, each group its own cursor.
    groups = [g for g in (result.get("record_groups") or []) if g.get("total") or g.get("results")]
    if groups:
        gparts: list[str] = []
        for g in groups:
            comp = str(g.get("compartment") or "")
            licence = str(g.get("license") or "")
            head = (
                f'<h3><code>{_e(comp)}</code> <span class="mut">'
                f"— {_e(licence)}, {_e(g.get('total'))} records match</span></h3>"
            )
            collapsed = g.get("collapsed_reason")
            if collapsed and not g.get("results"):
                show = _href(action, params, extra={"expand": "1"})
                gparts.append(
                    f"{head}<p>{_e(g.get('total'))} records contain the word "
                    f"<em>{_e(q)}</em> — {_e(collapsed)}. "
                    f'<a href="{_e(show)}">show them</a></p>'
                )
                continue
            cards = "".join(_card_article(c) for c in g.get("results") or [])
            nxt = g.get("next_cursor")
            nav = ""
            if nxt:
                nav = (
                    f'<p><a href="{_e(_href(action, params, extra={"cursor": nxt}))}">'
                    "More records in this licence group</a></p>"
                )
            gparts.append(f"{head}{cards}{nav}")
        parts.append(
            '<section aria-labelledby="rec-h"><h2 id="rec-h">Records</h2>'
            f"{''.join(gparts)}</section>"
        )

    if result.get("empty") or not (top or result.get("sections") or groups):
        parts.append(_empty_block(result, action, params))

    parts.append(
        '<p class="mut">Result order is by match quality — how well the words '
        "match, never popularity, evidence counts or confidence; every card "
        "states its match reason. Search covers the pinned release only "
        "(freshness = release freshness); the developer API may hold newer, "
        "uncited data.</p>"
    )

    stamp = None
    if site_release is not None:
        stamp = release_stamp_view(
            site_release,
            describedby=f"/releases/{pub}/release.json",
            variant="latest" if was_latest else "fixed",
        )
    return _layout(
        title=title,
        body="".join(parts),
        publication_id=pub,
        licence="per licence group",
        stamp=stamp,
        description=f"SIG release search results for {q or 'the released corpus'}",
    )


def search_results_error_page_v2(
    *,
    requested: str,
    status: int,
    code: str,
    detail: str,
    tombstone: Mapping[str, Any] | None = None,
) -> bytes:
    """The HTML error state of the federated search (DR-C4-10): a real page
    for every error status — the same zero-JS skeleton, the status, the
    machine code and the plain detail, plus the public-safe tombstone
    fields on a 410. No stamp and no licence line: an error body is dynamic
    output, never pinned citable bytes (the v1 precedent)."""
    titles = {
        400: "the request could not be understood",
        404: "not found",
        409: "the cursor does not belong to this search",
        410: "this release is withdrawn",
        422: "the query was refused",
        429: "the query was rate limited",
        501: "the representation is not implemented",
        503: "search is not ready",
    }
    state = titles.get(int(status), "the search failed")
    tomb_block = ""
    if tombstone:
        tomb_block = (
            '<p><span class="k">Reason category</span> '
            f"{_e(tombstone.get('reason_category'))} · "
            '<span class="k">Authority</span> '
            f"{_e(tombstone.get('authority'))} · "
            '<span class="k">Policy</span> '
            f"{_e(tombstone.get('policy_version'))}</p>"
        )
    action = SEARCH_PATH_V2.format(publication_id=requested)
    body = f"""
<div class="warn">
<p><strong>{_e(status)} — {_e(state)}.</strong></p>
<p>{_e(detail)}</p>
{tomb_block}
<p class="mut">Error code <code>{_e(code)}</code>. Nothing is lost: the same
answer is available as a JSON body to non-HTML clients.</p>
</div>
<p><a href="{_e(action)}?format=html">Back to this release's search form</a> ·
   <a href="/search/">the site search surface</a></p>
"""
    return _layout(
        title=f"Search — {status}",
        body=body,
        publication_id=None,
    )


__all__ = [
    "INTERIM_CITE_SEARCH_TEXT",
    "SEARCH_PATH_V2",
    "search_results_error_page_v2",
    "search_results_page_v2",
]

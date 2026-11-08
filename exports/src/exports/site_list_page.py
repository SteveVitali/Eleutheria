# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The no-JS bbox site list (P37.20 / K1 MAP-06).

``GET /v1/releases/{pub or latest}/sites?bbox=w,s,e,n&page=&format=html`` (or
a browser ``Accept: text/html``) answers this representation of the same
``sig.sites-bbox/1`` page the JSON body carries: the archive chrome (site
nav + dispute link + per-group licence lines — the ODbL compartment keeps
its own attribution, never co-mingled), the release stamp (G3 §6.1 via
``release_stamp_view``), one group per licence compartment with ≤ 100 rows
per page, pagination by ``page=``, and an HTML error page for every status
(DR-C4-10). It is the "Show all N in this area" target the map's In-view
list names and the no-JS equivalent of a bounded ``at=`` view.

Zero JavaScript (the API ``format=html`` surface is T0 — ADR-155); every
dynamic string is escaped; long identifiers sit in ``<code>`` so the page
reflows at 320 CSS px (DR-C4-14). Record links ride the release namespace
hrefs the serving layer emits — never minted here.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from .release_pages import _e, _layout, release_stamp_view

#: The route path — also the no-JS GET form's action and every page link's
#: base. ``{publication_id}`` carries the requested namespace (``latest``
#: or a ``p-<sha>`` id) so a follow-up link keeps the pointer class.
SITES_PATH = "/v1/releases/{publication_id}/sites"
COMPARTMENT_SITES_PATH = "/v1/releases/{publication_id}/compartments/{compartment}/sites"


def _coord_text(row: Mapping[str, Any]) -> str:
    loc = row.get("location") or {}
    lat, lon = loc.get("lat"), loc.get("lon")
    if lat is None or lon is None:
        return "—"
    return f"{lat}, {lon}"


def _row_html(row: Mapping[str, Any]) -> str:
    href = str(row.get("href") or "")
    label = str(row.get("name") or row.get("record_key") or "record")
    basis = str(row.get("name_basis") or "")
    basis_mark = f' <span class="mut">({_e(basis)})</span>' if basis.startswith("derived") else ""
    place = row.get("place") or {}
    source = row.get("source") or {}
    loc = row.get("location") or {}
    return (
        "<tr>"
        f'<td><a href="{_e(href)}">{_e(label)}</a>{basis_mark}</td>'
        f"<td>{_e(row.get('technology') or '—')}</td>"
        f"<td>{_e(place.get('text') or '—')}</td>"
        f"<td>{_e(source.get('name') or source.get('id') or '—')}</td>"
        f"<td>{_e(_coord_text(row))}</td>"
        f"<td>{_e(loc.get('precision') or '—')}</td>"
        "</tr>"
    )


def sites_bbox_page(
    *,
    requested: str,
    bbox: str,
    page: int,
    result: Mapping[str, Any],
    site_release: Mapping[str, Any] | None = None,
    was_latest: bool = False,
) -> bytes:
    """The complete no-JS site list for one ``sig.sites-bbox/1`` response —
    chrome, stamp, one compartment group each with ≤ 100 rows."""
    release = result.get("release") or {}
    pub = str(release.get("publication_id") or requested)
    action = SITES_PATH.format(publication_id=requested)
    scope = result.get("scope") or {}
    groups = result.get("groups") or []
    matched = sum(int(g.get("matched") or 0) for g in groups)
    title = f"Sites in {bbox}"

    excluded = scope.get("excluded_records_by_reason") or {}
    excluded_txt = ""
    if excluded:
        excluded_txt = " · withheld under the current policy — " + ", ".join(
            f"{_e(str(k).replace('_', ' '))}: {_e(v)}" for k, v in sorted(excluded.items())
        )
    strip = (
        f'<p class="mut">Release {_e(release.get("label"))} · data as of '
        f"{_e(release.get('as_of_world'))} · {_e(matched)} located records "
        f"inside the box{excluded_txt}</p>"
    )

    # The GET form re-states the request — a plain GET, no script.
    form = (
        f'<form method="get" action="{_e(action)}">'
        '<input type="hidden" name="format" value="html">'
        f'<p><label>Box (west,south,east,north) <input type="text" name="bbox" '
        f'value="{_e(bbox)}" size="30" maxlength="80" '
        'placeholder="-98.0,35.0,-96.0,36.0"></label> '
        '<button type="submit">List sites</button></p></form>'
        f'<p class="mut"><a href="/map/?bbox={_e(bbox)}">Open this area on the '
        "interactive map</a> — the map frames the same box and keeps working "
        "without JavaScript.</p>"
    )

    parts: list[str] = [strip, form]
    if not groups:
        parts.append(
            "<p>No published record in this release has a located point inside "
            "this box. Records without a published location can never appear "
            "in a box list — use the dossier or search for a place instead.</p>"
        )
    for g in groups:
        comp = str(g.get("compartment") or "")
        licence = str(g.get("license") or "")
        gmatched = int(g.get("matched") or 0)
        rows = g.get("results") or []
        head = (
            f'<h3><code>{_e(comp)}</code> <span class="mut">— {_e(licence)}, '
            f"{_e(gmatched)} located records in the box</span></h3>"
        )
        if rows:
            table = (
                '<table class="list"><thead><tr><th>Site</th><th>Technology</th>'
                "<th>Place</th><th>Source</th><th>Coordinates</th><th>Precision</th>"
                "</tr></thead><tbody>" + "".join(_row_html(r) for r in rows) + "</tbody></table>"
            )
        else:
            table = "<p>No rows on this page of the group.</p>"
        nav = ""
        if gmatched > page * int((result.get("query") or {}).get("page_size") or 100):
            nxt = urlencode({"bbox": bbox, "page": page + 1, "format": "html"})
            nav = f'<p><a href="{_e(action)}?{nxt}">More in this area</a></p>'
        comp_json = (
            COMPARTMENT_SITES_PATH.format(publication_id=requested, compartment=comp)
            + "?"
            + urlencode({"bbox": bbox, "page": page})
        )
        parts.append(
            f'<section aria-labelledby="grp-{_e(comp)}">{head}'
            f'<p class="mut">Licence of the rows in this group: '
            f"<strong>{_e(licence)}</strong> · "
            f'<a href="{_e(comp_json)}">JSON</a></p>'
            f"{table}{nav}</section>"
        )

    prev_nav = ""
    if page > 1:
        prev = urlencode({"bbox": bbox, "page": page - 1, "format": "html"})
        prev_nav = f'<a href="{_e(action)}?{prev}">previous page</a> · '
    parts.append(
        f'<p class="mut">{prev_nav}page {_e(page)} · rows are ordered by label '
        "inside each licence group; coordinates are shown at the published "
        "precision. Only records the release publishes a point for can "
        "appear — the list is release-pinned (freshness = release freshness).</p>"
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
        description=f"SIG release site list for the box {bbox}",
    )


def sites_bbox_error_page(
    *,
    requested: str,
    status: int,
    code: str,
    detail: str,
    tombstone: Mapping[str, Any] | None = None,
) -> bytes:
    """The HTML error state of the bbox list (DR-C4-10): a real page for
    every error status — the same zero-JS skeleton, the status, the machine
    code and the plain detail, plus the public-safe tombstone fields on a
    410. No stamp and no licence line: an error body is dynamic output,
    never pinned citable bytes (the v1 precedent)."""
    titles = {
        400: "the request could not be understood",
        404: "not found",
        410: "this release is withdrawn",
        422: "the query was refused",
        429: "the query was rate limited",
        503: "the site list is not ready",
    }
    state = titles.get(int(status), "the site list failed")
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
    action = SITES_PATH.format(publication_id=requested)
    body = f"""
<div class="warn">
<p><strong>{_e(status)} — {_e(state)}.</strong></p>
<p>{_e(detail)}</p>
{tomb_block}
<p class="mut">Error code <code>{_e(code)}</code>. Nothing is lost: the same
answer is available as a JSON body to non-HTML clients.</p>
</div>
<p><a href="{_e(action)}?format=html">Back to this release's site list</a> ·
   <a href="/map/">the map</a></p>
"""
    return _layout(
        title=f"Sites — {status}",
        body=body,
        publication_id=None,
    )


__all__ = [
    "COMPARTMENT_SITES_PATH",
    "SITES_PATH",
    "sites_bbox_error_page",
    "sites_bbox_page",
]

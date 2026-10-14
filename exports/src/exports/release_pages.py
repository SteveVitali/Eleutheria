# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deterministic, zero-JS HTML emitters for the released record routes
(P32.13 / ADR-132, SIG-FIND-002; P34.34a archive chrome + link repair).

Every page is a **complete** static document: no ``<script>``, no external
asset — it renders byte-identical offline from ``file://`` or any static
host. All dynamic strings are HTML-escaped. No wall-clock timestamps are
emitted (the activation record, outside the hashed bytes, is where real
UTC instants live — see ADR-132).

P34.34a (G2 step-4, ACT-16): every exports-rendered page carries the same
three chrome elements the Astro ``BaseLayout`` gives the live surface —
site navigation, a dispute/correction link (SIG-UI-033), and the licence
of the data the page shows (SIG-LIC-011). Same-origin links are emitted
site-root-absolute (``/r/<pub>/…``) wherever the target lives outside the
page's own directory, so no relative-depth arithmetic can drift: the
``validate_release`` link crawl re-verifies every emitted link regardless
of form.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from html import escape
from typing import Any
from urllib.parse import quote

from .published_record import EvidenceRef, PublishedRecord


def _e(v: Any) -> str:
    return escape("" if v is None else str(v), quote=True)


# --------------------------------------------------------------------------- #
# Archive chrome (P34.34a)                                                      #
# --------------------------------------------------------------------------- #

#: The site-shell navigation every archive page carries (SIG-UI-049): the
#: public Astro routes the release namespace links OUT to. Mirrored against
#: ``web/src/pages`` + ``ops/public_routes.toml`` at test time — a route
#: dropped from the public surface drops from this nav rather than 404ing.
SITE_NAV: tuple[tuple[str, str], ...] = (
    ("Map", "/map/"),
    ("Network", "/network/"),
    ("Search", "/search/"),
    ("Dossiers", "/dossier/"),
    ("Watch", "/watch/"),
    ("Evidence", "/evidence/"),
    ("Methodology", "/methodology/"),
    ("Sources", "/sources/"),
    ("Corrections", "/corrections/"),
    ("Status", "/status/"),
    ("Releases", "/releases/"),
)

#: The public dispute/correction intake route (SIG-UI-033, §45.1) — the same
#: path ``web/src/lib/corrections.ts``'s ``DISPUTE_PATH`` pins.
DISPUTE_HREF = "/dispute/"

#: Every same-origin route an archive page may link to that lives OUTSIDE the
#: release tree — either a public site-shell route (served by the Astro
#: surface) or a pipeline-overlay route emitted at activation
#: (``_emit_overlay`` owns ``/releases/index.html`` + ``releases/catalog.json``
#: + ``compat_index.json``; ``_entity_overlay`` owns ``/entity/<t>/<id>/``).
#: The ``validate_release`` link crawl treats exactly these as resolved —
#: never a wildcard. Route strings are normalised: no leading slash, no
#: trailing slash (``""`` is the homepage).
EXTERNAL_LINK_ROUTES: frozenset[str] = frozenset(
    {
        "",  # the site homepage
        "releases",  # the pipeline-owned archive index
        "releases/index.html",
        "releases/catalog.json",
        "compat_index.json",
    }
    | {href.strip("/") for _, href in SITE_NAV}
    | {DISPUTE_HREF.strip("/")}
)

#: Route prefixes the activation overlay emits that archive pages may link to
#: (the ``/entity/<type>/<id>/`` convenience stubs — mutable pointers, never
#: citations). Checked after :data:`EXTERNAL_LINK_ROUTES`.
EXTERNAL_LINK_PREFIXES: tuple[str, ...] = ("entity/",)


def _site_nav() -> str:
    links = ' <span aria-hidden="true">·</span> '.join(
        f'<a href="{_e(href)}">{_e(label)}</a>' for label, href in SITE_NAV
    )
    return (
        '<nav class="site-nav" aria-label="Site">'
        f'<a href="/"><strong>SIG</strong></a> <span aria-hidden="true">·</span> {links}'
        "</nav>"
    )


_STYLE = """\
body{font-family:system-ui,sans-serif;max-width:56rem;margin:0 auto;padding:1rem;color:#1a1a1a}
header{border-bottom:2px solid #444;padding-bottom:.5rem;margin-bottom:1rem}
h1{font-size:1.4rem;margin:.2rem 0}h2{font-size:1.05rem;margin-top:1.2rem}
table{border-collapse:collapse;width:100%;margin:.4rem 0}
td,th{border:1px solid #bbb;padding:.25rem .45rem;text-align:left;font-size:.9rem;
vertical-align:top}
.mut{color:#555;font-size:.85rem}
.warn{background:#f7f2e0;border:1px solid #c9a227;padding:.5rem;margin:.5rem 0}
.tomb{background:#fdeeee;border:1px solid #a33;padding:.6rem;margin:.6rem 0}
code{word-break:break-all}
footer{border-top:1px solid #bbb;margin-top:1.5rem;padding-top:.5rem;font-size:.8rem;color:#444}
.site-nav{font-size:.85rem;margin-bottom:.6rem}.site-nav a{margin-right:.2rem}
.dispute{margin-top:.9rem}
.licence{font-size:.85rem}
nav a{margin-right:.8rem}.k{color:#555;display:inline-block;min-width:9rem}
"""


def _layout(
    *,
    title: str,
    body: str,
    publication_id: str | None,
    footer_note: str = "",
    licence: str | None = None,
) -> bytes:
    """The shared archive page skeleton (P34.34a): site nav, the title +
    immutable-release stamp, then a footer carrying the dispute/correction
    link (SIG-UI-033) and — when the page shows compartment data — the
    licence that governs it (SIG-LIC-011). ``licence`` is an SPDX id or an
    explicit human-readable basis (e.g. "per compartment"); ``None`` is the
    honest state for pages that show no data (tombstones, error pages)."""
    pub = (
        f'<p class="mut">Immutable release <code>{_e(publication_id)}</code> — '
        "these bytes are version-pinned; cite this URL, not a &ldquo;latest&rdquo; alias.</p>"
        if publication_id
        else ""
    )
    licence_line = (
        f'<p class="licence">Licence of the data on this page: <strong>{_e(licence)}</strong></p>'
        if licence
        else ""
    )
    html = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{_e(title)} — SIG released record</title>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<style>{_STYLE}</style></head><body>"
        f"<header>{_site_nav()}<h1>{_e(title)}</h1>{pub}</header>"
        f"<main>{body}</main>"
        f'<footer>{licence_line}<p class="dispute">Something wrong, or a privacy '
        f'or safety concern? <a href="{_e(DISPUTE_HREF)}">Dispute or correct this '
        "record</a> — reports arrive by e-mail.</p>"
        f"<p>Surveillance Infrastructure Graph (SIG) — evidence-first public record. "
        f"{escape(footer_note)}</p></footer></body></html>"
    )
    return html.encode("utf-8")


# --------------------------------------------------------------------------- #
# Record page                                                                  #
# --------------------------------------------------------------------------- #


def record_page(
    record: PublishedRecord,
    *,
    latest_stub: str,
    evidence_compartment: Mapping[str, str] | None = None,
) -> bytes:
    """The complete released record page — ``<uuid>/index.html``.

    ``evidence_compartment`` maps an evidence ``artifact_id`` to the
    compartment its anchor page was emitted under (the artifact's own
    licence slice — P34.34a fix-forward): a record in ``osm_physical`` may
    cite an artifact published under ``web``/``sig_graph``, so the link must
    name that compartment, not the record's. When the map is supplied, an
    artifact absent from it renders the honest "not published" cell instead
    of a dead link. ``None`` keeps the record's own compartment (direct
    renderer callers outside the release build)."""
    pub = record.publication_id or ""
    comp = record.compartment
    loc = record.location
    if loc.get("kind") == "point":
        loc_html = (
            f'<p><span class="k">Point</span> {_e(loc.get("lat"))}, '
            f'{_e(loc.get("lon"))} <span class="mut">(published precision: '
            f"{_e(loc.get('precision'))})</span></p>"
        )
    elif loc.get("kind") == "unresolved_point":
        loc_html = (
            '<p><span class="k">Point</span> unresolved — the released '
            f"record could not publish a resolved point ({_e(loc.get('precision'))}).</p>"
        )
    else:
        loc_html = (
            '<p><span class="k">Point</span> <strong>not reported</strong> — '
            "this record does not publish a location.</p>"
        )

    # P34.34a (SIG-UI-024): an access-edge claim anchor renders its §12.2 type
    # (configured_access / observed_use / declared_policy — or an honest
    # "unclassified"), never an untyped sharing_access label.
    show_access = any(a.access_kind for a in record.claim_anchors)
    claim_rows = "".join(
        "<tr>"
        f'<td id="claim-{_e(a.claim_id)}"><code>{_e(a.claim_id)}</code></td>'
        "<td>"
        + (
            _e(a.predicate_id)
            if a.predicate_id
            else "<em>detail not published in this release</em>"
        )
        + "</td>"
        + (f"<td>{_e(a.access_kind) if a.access_kind else '—'}</td>" if show_access else "")
        + f"<td>{_e(a.observed_at) if a.observed_at else '—'}</td>"
        f"<td>{_e(a.source_id) if a.source_id else '—'}</td>"
        "</tr>"
        for a in record.claim_anchors
    ) or (
        f'<tr><td colspan="{5 if show_access else 4}"><em>No observation claims are '
        "attached to this record.</em></td></tr>"
    )

    def _ev_cell(e: EvidenceRef) -> str:
        if not e.artifact_id:
            return "<td><em>artifact not published in this release</em></td>"
        ev_comp = (
            evidence_compartment.get(e.artifact_id) if evidence_compartment is not None else comp
        )
        if ev_comp is None:
            return "<td><em>artifact not published in this release</em></td>"
        # P34.34a: site-root-absolute — relative-depth links from the
        # entity/<type>/<id>/ route resolved one level too shallow (C4
        # NEW-1); and the evidence anchor lives under ITS compartment, not
        # the citing record's (the composed-PG release caught a cross-
        # compartment dead link the fixture suites never produced). The
        # validate_release crawl re-checks every link.
        return (
            f'<td><a href="/r/{_e(pub)}/c/{_e(ev_comp)}/evidence/{_e(e.artifact_id)}/">'
            + f"<code>{_e(e.artifact_id)}</code></a></td>"
        )

    ev_rows = "".join(
        "<tr>"
        f"<td><code>{_e(e.claim_id)}</code></td>"
        f"<td><code>{_e(e.capture_id) if e.capture_id else '<em>unlocated</em>'}</code></td>"
        + _ev_cell(e)
        + f"<td>{_e(e.role) if e.role else '—'}</td>"
        f"<td>{_e(e.access)}</td></tr>"
        for e in record.evidence_refs
    ) or (
        '<tr><td colspan="5"><em>No evidence captures are published with this '
        "record — the claim anchors above are the spine-level citations; capture "
        "locators are explicit <code>unlocated</code> state, not an omission.</em></td></tr>"
    )

    src_rows = "".join(
        f"<tr><td>{_e(s.get('source_id'))}</td><td>{_e(s.get('attribution'))}</td>"
        f"<td>{_e(s.get('terms_url')) if s.get('terms_url') else '—'}</td></tr>"
        for s in record.source_refs
    )

    cov = record.coverage
    label_txt = record.label.get("text") or f"Unnamed {record.entity_type}"
    title = f"{label_txt} · {record.entity_type}"
    cite_url = record.href or ""
    access_th = "<th>Access edge</th>" if show_access else ""
    body = f"""
<p><span class="k">Record key</span> <code>{_e(record.record_key)}</code></p>
<p><span class="k">Compartment</span> {_e(record.compartment)} ·
   <span class="k">Licence</span> {_e(record.license)}</p>
<h2>What this record describes</h2>
<p><span class="k">Entity type</span> {_e(record.entity_type)} ·
   <span class="k">Entity id</span> <code>{_e(record.entity_id)}</code></p>
<p><span class="k">Jurisdiction</span> {_e(record.jurisdiction.get("id")) or "<em>unreported</em>"}
   <span class="mut">(basis: {_e(record.jurisdiction.get("basis"))})</span></p>
{loc_html}
<h2>Claim anchors</h2>
<p class="mut">Each anchor is a spine-issued claim id — the claim-level citation.
Anchors without published detail state so explicitly.</p>
<table><tr><th>Claim anchor</th><th>Predicate</th>{access_th}<th>Observed</th><th>Source</th></tr>
{claim_rows}</table>
<h2>Evidence anchors</h2>
<table><tr><th>Claim</th><th>Capture</th><th>Artifact</th><th>Role</th><th>Access</th></tr>
{ev_rows}</table>
<h2>Sources and rights</h2>
<table><tr><th>Source</th><th>Attribution</th><th>Terms</th></tr>{src_rows}</table>
<h2>Coverage</h2>
<p><span class="k">Observation claims</span> {_e(cov.get("observation_claims"))} ·
   <span class="k">Sources</span> {_e(cov.get("source_count"))} ·
   <span class="k">Sensitivity tier</span> {_e(cov.get("sensitivity_tier"))}</p>
<p class="mut">{_e(cov.get("note"))}</p>
<h2>Review</h2>
<p><span class="k">Status</span> {_e(record.review.get("status"))} ·
   <span class="k">Resolution eval</span> {_e(record.review.get("resolution_eval"))}<br>
   <span class="mut">{_e(record.review.get("note"))}</span></p>
<h2>Cite this record</h2>
<p>Canonical released URL: <code>{_e(cite_url)}</code><br>
Machine-readable: <a href="{_e(record.json_href)}"><code>{_e(record.json_href)}</code></a></p>
<p class="mut">Convenience alias (current view — <strong>never cite</strong>):
<a href="{_e(latest_stub)}"><code>{_e(latest_stub)}</code></a></p>
"""
    return _layout(
        title=title,
        body=body,
        publication_id=record.publication_id,
        footer_note=f"Licence {_e(record.license)} — compartment {_e(record.compartment)}.",
        licence=record.license,
    )


# --------------------------------------------------------------------------- #
# Indexes: compartment browse + jurisdiction                                   #
# --------------------------------------------------------------------------- #


def _record_li(item: Mapping[str, Any], *, publication_id: str, compartment: str) -> str:
    label = item.get("label") or f"Unnamed {item.get('entity_type')}"
    # P34.34a: site-root-absolute — the browse/jurisdiction pages sit three
    # levels under the compartment root, where ../../entity/… resolved to the
    # browse/ subtree (C4 NEW-1).
    href = f"/r/{publication_id}/c/{compartment}/entity/{item['entity_type']}/{item['entity_id']}/"
    return (
        f'<li><a href="{_e(href)}">'
        f'{_e(label)}</a> <span class="mut">{_e(item["entity_type"])} · '
        f"{_e(item['jurisdiction']) or '—'}</span></li>"
    )


def browse_page(
    *,
    publication_id: str,
    compartment: str,
    kind: str,
    page: int,
    page_count: int,
    items: Sequence[Mapping[str, Any]],
    total: int,
    licence: str,
) -> bytes:
    """One ``/r/<pub>/c/<comp>/browse/<kind>/<page>/`` index page."""
    lis = "".join(
        _record_li(i, publication_id=publication_id, compartment=compartment) for i in items
    )
    pager = _pager(f"/r/{publication_id}/c/{compartment}/browse/{kind}", page, page_count)
    body = f"""
<p><span class="k">Compartment</span> {_e(compartment)} ·
   <span class="k">Licence</span> {_e(licence)} ·
   <span class="k">Kind</span> {_e(kind)} ·
   <span class="k">Records</span> {_e(total)}</p>
<nav><a href="/r/{_e(publication_id)}/c/{_e(compartment)}/">Compartment overview</a></nav>
<ul>{lis}</ul>
{pager}
"""
    return _layout(
        title=f"{kind} records — {compartment} (page {page}/{page_count})",
        body=body,
        publication_id=publication_id,
        licence=licence,
    )


def _pager(prefix: str, page: int, page_count: int) -> str:
    parts = []
    if page > 1:
        parts.append(f'<a href="{prefix}/{page - 1}/">&larr; previous</a>')
    parts.append(f"page {page} of {page_count}")
    if page < page_count:
        parts.append(f'<a href="{prefix}/{page + 1}/">next &rarr;</a>')
    return f'<nav class="mut">{" · ".join(parts)}</nav>'


def jurisdiction_page(
    *,
    publication_id: str,
    compartment: str,
    jurisdiction: str,
    page: int,
    page_count: int,
    items: Sequence[Mapping[str, Any]],
    total: int,
    licence: str,
) -> bytes:
    lis = "".join(
        _record_li(i, publication_id=publication_id, compartment=compartment) for i in items
    )
    pager = _pager(
        f"/r/{publication_id}/c/{compartment}/jurisdiction/{jurisdiction}",
        page,
        page_count,
    )
    body = f"""
<p><span class="k">Jurisdiction</span> {_e(jurisdiction)} ·
   <span class="k">Compartment</span> {_e(compartment)} ·
   <span class="k">Licence</span> {_e(licence)} ·
   <span class="k">Records</span> {_e(total)}</p>
<nav><a href="/r/{_e(publication_id)}/c/{_e(compartment)}/">Compartment overview</a></nav>
<ul>{lis}</ul>
{pager}
"""
    return _layout(
        title=f"{jurisdiction} — {compartment} (page {page}/{page_count})",
        body=body,
        publication_id=publication_id,
        licence=licence,
    )


def compartment_page(
    *,
    publication_id: str,
    compartment: str,
    licence: str,
    record_count: int,
    kinds: Mapping[str, int],
    jurisdictions: Mapping[str, int],
) -> bytes:
    """``/r/<pub>/c/<comp>/`` — the compartment overview."""
    kind_lis = "".join(
        f'<li><a href="browse/{_e(k)}/1/">{_e(k)}</a> — {_e(n)}</li>'
        for k, n in sorted(kinds.items())
    )
    jur_lis = "".join(
        f'<li><a href="jurisdiction/{_e(j)}/1/">{_e(j)}</a> — {_e(n)}</li>'
        for j, n in sorted(jurisdictions.items())
    )
    empty_note = (
        '<p class="warn">This compartment releases <strong>no records</strong> in '
        "this release — the licence slice published nothing at the pinned as-of "
        "dates; the empty index below is the honest state, not a rendering "
        "fault.</p>"
        if record_count == 0
        else ""
    )
    body = f"""
<p><span class="k">Compartment</span> {_e(compartment)} ·
   <span class="k">Licence</span> {_e(licence)} ·
   <span class="k">Released records</span> {_e(record_count)}</p>
{empty_note}
<h2>Browse by record kind</h2><ul>{kind_lis}</ul>
<h2>Browse by jurisdiction</h2><ul>{jur_lis}</ul>
<h2>Machine index</h2>
<p><a href="records.index.jsonl"><code>records.index.jsonl</code></a> — every
record in this compartment, one key per line (the completeness manifest
recomputes this index).</p>
"""
    return _layout(
        title=f"Compartment {compartment}",
        body=body,
        publication_id=publication_id,
        licence=licence,
    )


# --------------------------------------------------------------------------- #
# Evidence + dossier pages                                                     #
# --------------------------------------------------------------------------- #


def evidence_page(
    *,
    publication_id: str,
    compartment: str,
    artifact: Mapping[str, Any],
    licence: str,
) -> bytes:
    """``/r/<pub>/c/<comp>/evidence/<artifact_id>/`` — the released evidence
    anchor page (metadata only — capture bytes never travel, §17.5)."""
    body = f"""
<p><span class="k">Artifact</span> <code>{_e(artifact.get("artifact_id"))}</code></p>
<p><span class="k">Title</span> {_e(artifact.get("title"))}</p>
<p><span class="k">Source</span> {_e(artifact.get("source"))} ·
   <span class="k">Type</span> {_e(artifact.get("artifact_type"))} ·
   <span class="k">Directness</span> {_e(artifact.get("directness"))}</p>
<p><span class="k">Capture status</span> {_e(artifact.get("capture_status"))} ·
   <span class="k">Published through</span> {_e(artifact.get("currency")) or "—"}</p>
<p><span class="k">Stable locator</span> <code>{_e(artifact.get("permalink"))}</code></p>
<p class="mut">Capture bytes are not served from this namespace (§17.5 —
sealed captures stay metadata-only). The locator identifies the pinned
evidence object in the custody store.</p>
"""
    return _layout(
        title=f"Evidence artifact {artifact.get('artifact_id')}",
        body=body,
        publication_id=publication_id,
        licence=licence,
    )


def dossier_slug(dossier: Mapping[str, Any]) -> str:
    """The route slug one released dossier occupies — the dossier's own
    ``slug`` field when present (the spine dossiers carry a slugified form),
    else the jurisdiction label, else ``unknown``. Shared by the page emitter
    and the release landing so a link can never drift from its route."""
    return str(dossier.get("slug") or dossier.get("jurisdiction") or "unknown")


def dossier_page(*, publication_id: str, dossier: Mapping[str, Any], licence: str) -> bytes:
    """``/r/<pub>/dossier/<slug>/`` — the released dossier overview: the
    published sections/rows verbatim plus links into the compartments.

    P34.34a (C4 NEW-7): the page states its **provisional** posture plainly —
    a computed inventory overview of the released projection at the pinned
    as-of dates, with no human check performed (ADR-152) — and never reads
    as "reviewed". The licence of the data it summarises travels with the
    page (SIG-LIC-011).
    """
    jurisdiction = str(dossier.get("jurisdiction") or "unknown")
    rows: list[str] = []
    for section in dossier.get("sections") or []:
        sid = _e(section.get("section_id"))
        rows.append(f"<h2>{sid}</h2>")
        srows = section.get("rows")
        if not srows:
            rows.append(
                '<p class="mut"><em>No published rows in this section for this '
                "release — an explicit absence, not an empty page.</em></p>"
            )
            continue
        rows.append("<table><tr><th>Field</th><th>Value</th><th>Note</th></tr>")
        for r in srows:
            rows.append(
                f"<tr><td>{_e(r.get('label'))}</td><td>{_e(r.get('value'))}</td>"
                f"<td>{_e(r.get('note')) if r.get('note') else '—'}</td></tr>"
            )
        rows.append("</table>")
    gaps = dossier.get("gaps") or []
    gap_lis = "".join(
        f'<li>{_e(g.get("label"))} <span class="mut">({_e(g.get("kind"))})</span></li>'
        for g in gaps
    )
    if gap_lis:
        rows.append(f"<h2>Recorded gaps</h2><ul>{gap_lis}</ul>")
    asof = dossier.get("asOf") or {}
    body = f"""
<p><span class="k">Jurisdiction</span> {_e(jurisdiction)} ·
   <span class="k">As-of world</span> {_e(asof.get("as_of_world"))} ·
   <span class="k">As-of belief</span> {_e(asof.get("as_of_belief"))} ·
   <span class="k">Ruleset</span> {_e(dossier.get("rulesetVersion"))}</p>
<p class="warn"><strong>Posture: provisional.</strong> This dossier is a computed
inventory overview of the released record projection at the as-of dates above —
no human check performed (ADR-152), not an adjudicated finding.
Recorded gaps below are first-class absences, never omissions.</p>
{"".join(rows)}
"""
    return _layout(
        title=f"Dossier {jurisdiction}",
        body=body,
        publication_id=publication_id,
        licence=licence,
    )


# --------------------------------------------------------------------------- #
# Landing, catalog index, convenience stub, tombstone                          #
# --------------------------------------------------------------------------- #


def release_landing(
    entry: Mapping[str, Any], *, dossiers: Sequence[Mapping[str, Any]] = ()
) -> bytes:
    """``/releases/<pub>/index.html`` — the release landing: descriptor +
    integrity digest + compartment inventory + download pointers.

    P34.34a (C4 NEW-7 / NEW-31): the released dossier overviews are linked
    from here (never orphaned), and a release that publishes zero records
    says so explicitly instead of rendering an empty page."""
    pub = str(entry["publication_id"])
    comp_rows = "".join(
        f'<tr><td><a href="/r/{_e(pub)}/c/{_e(c["compartment"])}/">'
        f"{_e(c['compartment'])}</a></td>"
        f"<td>{_e(c.get('license'))}</td><td>{_e(c.get('record_count'))}</td>"
        f"<td>{_e(c.get('artifact_count'))}</td></tr>"
        for c in entry.get("compartments") or []
    )
    repro = entry.get("reproducibility") or {}
    total_records = int(entry.get("record_count") or 0)
    # C4 NEW-31: an honestly empty release explains itself — the verified,
    # complete state with no records is different from a broken build.
    empty_block = (
        '<div class="warn"><h2>This release publishes no records</h2>'
        "<p>The integrity manifest and descriptor above verify — the export "
        "simply contained no publishable records at the pinned as-of dates "
        "(every input may have been withheld, or the corpus may be empty). "
        "No route under this namespace claims a record that does not exist; "
        "the empty compartment indexes are the honest state, not a rendering "
        "fault.</p></div>"
        if total_records == 0
        else ""
    )
    # C4 NEW-7: released dossier overviews are reachable from the landing —
    # each carries its provisional posture on its own page.
    dossier_lis = "".join(
        f'<li><a href="/r/{_e(pub)}/dossier/{_e(quote(dossier_slug(d), safe=""))}/">'
        f"{_e(str(d.get('jurisdiction') or dossier_slug(d)))}</a>"
        f' <code class="mut">{_e(dossier_slug(d))}</code></li>'
        for d in dossiers
    )
    dossier_block = (
        f'<h2>Dossiers</h2><p class="mut">Provisional, computed inventory '
        f"overviews — no human check performed.</p><ul>{dossier_lis}</ul>"
        if dossier_lis
        else ""
    )
    body = f"""
<p><span class="k">Publication</span> <code>{_e(pub)}</code></p>
<p><span class="k">Data release</span> <code>{_e(entry.get("data_release_id"))}</code> ·
   <span class="k">Descriptor digest</span> <code>{_e(entry.get("descriptor_sha256"))}</code></p>
<p><span class="k">As-of world</span> {_e(repro.get("as_of_world"))} ·
   <span class="k">As-of belief</span> {_e(repro.get("as_of_belief"))} ·
   <span class="k">Ruleset</span> {_e(repro.get("ruleset_version"))} ·
   <span class="k">Policy</span> {_e(repro.get("policy_version"))}</p>
{empty_block}
<h2>Compartments</h2>
<table><tr><th>Compartment</th><th>Licence</th><th>Records</th><th>Artifacts</th></tr>
{comp_rows}</table>
{dossier_block}
<h2>Machine-readable</h2>
<p><a href="catalog_entry.json"><code>catalog_entry.json</code></a> ·
   <a href="integrity_manifest.json"><code>integrity_manifest.json</code></a> ·
   <a href="descriptor.json"><code>descriptor.json</code></a></p>
<p class="mut">Records live under <code>/r/{_e(pub)}/c/&lt;compartment&gt;/…</code>.
Completeness: {_e(_display_label((entry.get("completeness") or {}).get("state")))}.</p>
"""
    return _layout(
        title=f"Release {pub[:15]}…",
        body=body,
        publication_id=pub,
        licence="per compartment — see the table",
    )


def releases_index(entries: Iterable[Mapping[str, Any]], *, latest: str | None) -> bytes:
    """``/releases/index.html`` — the catalog of activated immutable releases."""
    lis = (
        "".join(
            f'<li><a href="{_e(e["publication_id"])}/"><code>{_e(e["publication_id"])}</code></a>'
            f" — {_e((e.get('reproducibility') or {}).get('as_of_world'))} · "
            f"{_e(e.get('record_count'))} records · data release "
            f"<code>{_e(e.get('data_release_id'))}</code>"
            f"{' <strong>(latest)</strong>' if e['publication_id'] == latest else ''}</li>"
            for e in entries
        )
        or "<li><em>No releases are activated yet.</em></li>"
    )
    body = f"""
<p>Every activated publication namespace, newest entry last in the catalog.
Each release is immutable: its bytes never change after activation
(withdrawals deny whole artifacts — they never edit them).</p>
<ul>{lis}</ul>
"""
    return _layout(
        title="SIG releases",
        body=body,
        publication_id=None,
        footer_note="The (latest) marker is a convenience pointer, never a citation.",
        licence="CC-BY-4.0 — this catalog page is SIG metadata; record data "
        "carries its compartment licence",
    )


def entity_stub(
    *,
    entity_type: str,
    entity_id: str,
    latest_publication: str,
    record_href: str,
) -> bytes:
    """The ``/entity/<type>/<uuid>/`` convenience landing — a mutable current
    view pointer. States plainly that it is NOT a citation."""
    body = f"""
<p class="warn"><strong>This is a convenience alias for the current view</strong> —
it re-targets silently when a newer release is activated. Cite the released
record instead:</p>
<p><a href="{_e(record_href)}"><code>{_e(record_href)}</code></a></p>
<p><span class="k">Entity</span> <code>{_e(entity_type)}/{_e(entity_id)}</code> ·
   <span class="k">Current release</span> <code>{_e(latest_publication)}</code></p>
"""
    return _layout(
        title=f"{entity_type} {entity_id}",
        body=body,
        publication_id=None,
        footer_note="Mutable overlay page — never an immutable citation.",
        licence="this page is a pointer only — the linked record carries its compartment licence",
    )


def tombstone_page(
    *,
    path: str,
    reason_category: str,
    authority: str,
    decided: str,
    policy_version: str,
) -> bytes:
    """The deterministic 410 tombstone — content-free, public-safe fields
    only (reason CATEGORY + authority + decided DATE + policy version —
    never the privileged rationale)."""
    body = f"""
<div class="tomb">
<h2>This record is not publicly available</h2>
<p><span class="k">Route</span> <code>{_e(path)}</code></p>
<p><span class="k">State</span> withdrawn — the artifact is denied whole under the
current publication-disposition policy; immutable release bytes are never
rewritten.</p>
<p><span class="k">Reason category</span> {_e(reason_category)} ·
   <span class="k">Authority</span> {_e(authority)} ·
   <span class="k">Decided</span> {_e(decided[:10])} ·
   <span class="k">Policy</span> {_e(policy_version)}</p>
<p class="mut">The recorded identity is retained so citations resolve to an
honest state rather than a generic 404. Withdrawals apply to every release —
including rolled-back ones.</p>
</div>
"""
    return _layout(
        title="Record withdrawn",
        body=body,
        publication_id=None,
        footer_note="Honest unavailability — a tombstone, not silently stale bytes.",
    )


def error_page(*, title: str, detail: str) -> bytes:
    """A small honest error page (404/400/409 bodies for the resolver)."""
    return _layout(
        title=title,
        body=f"<p>{_e(detail)}</p>",
        publication_id=None,
    )


# --------------------------------------------------------------------------- #
# P32.14 (SIG-FIND-003, ADR-133): the no-JS released-corpus search page.
# Served dynamically by the read API from the verified per-compartment FTS5
# index — the static browse/record pages remain the complete offline path.
# Zero JavaScript; every dynamic string escaped; ≤50 rows per page.
# --------------------------------------------------------------------------- #

#: Machine tokens that must never appear as visible labels on a public page
#: (C4 NEW-28). The wire ``value=`` keeps the raw token — only the human text
#: is translated.
_DISPLAY_LABELS = {
    "unreported": "not reported",
    "public-point": "public point",
    "no-public-point": "no public point",
    "not_evaluable": "not evaluable",
}


def _display_label(v: Any) -> str:
    """The human label for a raw enum token (display only — the wire value
    is unchanged)."""
    return _DISPLAY_LABELS.get(str(v), str(v))


def search_error_page(
    *,
    action: str,
    publication_id: str,
    compartment: str,
    status: int,
    code: str,
    detail: str,
    tombstone: Mapping[str, Any] | None = None,
) -> bytes:
    """The HTML error state of the released-corpus search (C4 NEW-13 /
    DR-C4-10, P34.36).

    An HTML client gets a real page — the same zero-JS skeleton as the
    results page — for every error status, never a raw JSON body. The page
    states the status, the machine code and the plain detail, links back to
    the search form, and for a 410 shows the public-safe tombstone fields
    (reason category + authority + decided date — never the privileged
    rationale). No licence line: the page shows no record data.
    """
    titles = {
        400: "the request could not be understood",
        404: "not found",
        409: "the cursor does not belong to this search",
        410: "this release is withdrawn",
        422: "the query was refused",
        429: "the query was rate limited",
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
    body = f"""
<div class="warn">
<p><strong>{_e(status)} — {_e(state)}.</strong></p>
<p>{_e(detail)}</p>
{tomb_block}
<p class="mut">Error code <code>{_e(code)}</code>. Nothing is lost: the same
answer is available as a JSON body to non-HTML clients.</p>
</div>
<p><a href="{_e(action)}">Back to this compartment's search form</a> ·
   <a href="/r/{_e(publication_id)}/c/{_e(compartment)}/">browse the
   compartment's static pages</a></p>
"""
    # No "immutable release" stamp: an error body is dynamic output, never
    # pinned, citable bytes (the tombstone/error-page precedent).
    return _layout(
        title=f"Search {compartment} — {status}",
        body=body,
        publication_id=None,
    )


def search_page(
    *,
    action: str,
    publication_id: str,
    compartment: str,
    licence: str,
    params: Mapping[str, Any],
    facet_options: Mapping[str, Sequence[tuple[str, int]]],
    result: Mapping[str, Any],
) -> bytes:
    """The complete no-JS search page for one released compartment.

    ``params`` echoes the normalized request (``q`` + facet filters);
    ``result`` is the bounded search response dict (≤50 rows). The form is a
    plain GET — a browser navigates with ``Accept: text/html`` so content
    negotiation selects this representation, no scripting required.
    """
    q = str(params.get("q") or "")
    filters = dict(params.get("filters") or {})
    limit = int(params.get("limit") or 50)

    def _select(name: str, label: str, options: Sequence[tuple[str, int]]) -> str:
        opts = [f'<option value="">{_e(label)} — any</option>']
        for value, count in options:
            sel = " selected" if filters.get(name) == value else ""
            # Display labels are humanised (never a raw enum name); the wire
            # value= keeps the raw token so the form keeps filtering.
            opts.append(
                f'<option value="{_e(value)}"{sel}>'
                f"{_e(_display_label(value))} ({_e(count)})</option>"
            )
        return f'<label>{_e(label)} <select name="{_e(name)}">{"".join(opts)}</select></label>'

    loc_value = filters.get("location") or "any"
    loc_opts = "".join(
        f'<option value="{_e(v)}"{" selected" if loc_value == v else ""}>'
        f"{_e(_display_label(v))}</option>"
        for v in ("any", "public-point", "no-public-point")
    )
    controls = "".join(
        _select(name, label, facet_options.get(name, ()))
        for name, label in (
            ("kind", "Record kind"),
            ("jurisdiction", "Jurisdiction"),
            ("source", "Source"),
            ("technology", "Technology"),
        )
    )
    form = f"""
<form method="get" action="{_e(action)}">
  <p><label>Search <input type="search" name="q" value="{_e(q)}" size="40"
      maxlength="200" placeholder="words or an exact identifier"></label>
     <label>Rows <select name="limit">
       {
        "".join(
            f'<option value="{n}"{" selected" if limit == n else ""}>{n}</option>'
            for n in (10, 25, 50)
        )
    }
     </select></label>
     <label>Location <select name="location">{loc_opts}</select></label></p>
  <p>{controls}</p>
  <p><button type="submit">Search this compartment</button></p>
</form>
"""

    rows: list[str] = []
    for hit in result.get("results") or []:
        label = hit.get("label") or f"Unnamed {_e(hit.get('record_key'))}"
        jur = hit.get("jurisdiction") or "unreported"
        loc = hit.get("location") or ""
        srcs = ", ".join(str(s) for s in (hit.get("sources") or []))
        rows.append(
            "<tr>"
            f'<td><a href="{_e(hit.get("href"))}">{_e(label)}</a>'
            f'<br><code class="mut">{_e(hit.get("record_key"))}</code></td>'
            f"<td>{_e(hit.get('kind'))}</td>"
            f"<td>{_e(_display_label(jur))}</td>"
            f"<td>{_e(_display_label(loc))}</td>"
            f"<td>{_e(srcs)}</td>"
            "</tr>"
        )
    scope = result.get("scope") or {}
    qd = result.get("query") or {}
    exact = " — exact identifier lookup" if qd.get("exact_id") else ""
    # Access-time denials are part of the honest scope (C4 NEW-12): when the
    # current policy withholds indexed records the page names the count and
    # the public-safe reason, never a bare eligible number.
    excluded = scope.get("excluded_records_by_reason") or {}
    excluded_txt = ""
    if excluded:
        excluded_txt = " · withheld under the current policy — " + ", ".join(
            f"{_e(str(k).replace('_', ' '))}: {_e(v)}" for k, v in sorted(excluded.items())
        )
    summary = (
        f'<p class="mut">{_e(len(result.get("results") or []))} row(s) on this page'
        f"{_e(exact)} · {_e(scope.get('indexed_records'))} indexed / "
        f"{_e(scope.get('eligible_records'))} eligible released records in this "
        f"compartment{_e(excluded_txt)}. A page is a bound, not the corpus "
        "size — follow &ldquo;next&rdquo; to continue; total counts are not "
        "computed.</p>"
    )
    if rows:
        table = (
            "<table><thead><tr><th>Record</th><th>Kind</th><th>Jurisdiction</th>"
            "<th>Location</th><th>Sources</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
        )
    else:
        # C4 NEW-4 / DR-C4-05: the empty state asserts only the query's
        # result — never research status, never a recorded absence.
        table = (
            "<p><em>No released record in this compartment matches.</em> "
            "Try broader terms or fewer filters.</p>"
        )
    cur = result.get("next_cursor")
    if cur:
        import urllib.parse

        qp: dict[str, str] = {}
        if q:
            qp["q"] = q
        for name in ("kind", "jurisdiction", "source", "location", "technology"):
            if filters.get(name):
                qp[name] = filters[name]
        qp["limit"] = str(limit)
        qp["cursor"] = str(cur)
        nav = (
            f'<p><a href="{_e(action)}?{_e(urllib.parse.urlencode(qp))}">'
            f"next {_e(limit)} &rarr;</a> · "
            f'<a href="{_e(action)}">start over</a></p>'
        )
    else:
        nav = f'<p><a href="{_e(action)}">start over</a></p>'

    body = f"""
<p><span class="k">Compartment</span> {_e(compartment)} ·
   <span class="k">Licence</span> {_e(licence)} ·
   <span class="k">Scope</span> {_e(scope.get("indexed_records"))} released records</p>
{form}
{summary}
{table}
{nav}
<p class="mut">Search is lexical retrieval over one licence compartment — a
page order is the stable label+type+id sort, not a relevance score or a
probability of truth. Withdrawn records are denied under the current
publication policy even inside this fixed release. Cross-compartment search
is deliberately not federated: run one compartment at a time, or use the
complete static browse pages under
<code>/r/{_e(publication_id)}/c/{_e(compartment)}/</code> (no service
required).</p>
"""
    return _layout(
        title=f"Search {compartment}",
        body=body,
        publication_id=publication_id,
        licence=licence,
    )

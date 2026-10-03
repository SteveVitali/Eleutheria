# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Deterministic, zero-JS HTML emitters for the released record routes
(P32.13 / ADR-132, SIG-FIND-002).

Every page is a **complete** static document: no ``<script>``, no external
asset — it renders byte-identical offline from ``file://`` or any static
host. All dynamic strings are HTML-escaped. No wall-clock timestamps are
emitted (the activation record, outside the hashed bytes, is where real
UTC instants live — see ADR-132).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from html import escape
from typing import Any

from .published_record import PublishedRecord


def _e(v: Any) -> str:
    return escape("" if v is None else str(v), quote=True)


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
nav a{margin-right:.8rem}.k{color:#555;display:inline-block;min-width:9rem}
"""


def _layout(
    *,
    title: str,
    body: str,
    publication_id: str | None,
    footer_note: str = "",
) -> bytes:
    pub = (
        f'<p class="mut">Immutable release <code>{_e(publication_id)}</code> — '
        "these bytes are version-pinned; cite this URL, not a &ldquo;latest&rdquo; alias.</p>"
        if publication_id
        else ""
    )
    html = (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{_e(title)} — SIG released record</title>"
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<style>{_STYLE}</style></head><body>"
        f"<header><h1>{_e(title)}</h1>{pub}</header>"
        f"<main>{body}</main>"
        f"<footer><p>Surveillance Infrastructure Graph (SIG) — evidence-first public record. "
        f"{escape(footer_note)}</p></footer></body></html>"
    )
    return html.encode("utf-8")


# --------------------------------------------------------------------------- #
# Record page                                                                  #
# --------------------------------------------------------------------------- #


def record_page(record: PublishedRecord, *, latest_stub: str) -> bytes:
    """The complete released record page — ``<uuid>/index.html``."""
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
        f"<td>{_e(a.observed_at) if a.observed_at else '—'}</td>"
        f"<td>{_e(a.source_id) if a.source_id else '—'}</td>"
        "</tr>"
        for a in record.claim_anchors
    ) or (
        '<tr><td colspan="4"><em>No observation claims are attached to this record.</em></td></tr>'
    )

    ev_rows = "".join(
        "<tr>"
        f"<td><code>{_e(e.claim_id)}</code></td>"
        f"<td><code>{_e(e.capture_id) if e.capture_id else '<em>unlocated</em>'}</code></td>"
        + (
            '<td><a href="../../evidence/'
            + _e(e.artifact_id)
            + f'/"><code>{_e(e.artifact_id)}</code></a></td>'
            if e.artifact_id
            else "<td><em>artifact not published in this release</em></td>"
        )
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
<table><tr><th>Claim anchor</th><th>Predicate</th><th>Observed</th><th>Source</th></tr>
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
    )


# --------------------------------------------------------------------------- #
# Indexes: compartment browse + jurisdiction                                   #
# --------------------------------------------------------------------------- #


def _record_li(item: Mapping[str, Any]) -> str:
    label = item.get("label") or f"Unnamed {item.get('entity_type')}"
    return (
        f'<li><a href="../../entity/{_e(item["entity_type"])}/{_e(item["entity_id"])}/">'
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
    lis = "".join(_record_li(i) for i in items)
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
    lis = "".join(_record_li(i) for i in items)
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
    body = f"""
<p><span class="k">Compartment</span> {_e(compartment)} ·
   <span class="k">Licence</span> {_e(licence)} ·
   <span class="k">Released records</span> {_e(record_count)}</p>
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
    )


# --------------------------------------------------------------------------- #
# Evidence + dossier pages                                                     #
# --------------------------------------------------------------------------- #


def evidence_page(
    *,
    publication_id: str,
    compartment: str,
    artifact: Mapping[str, Any],
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
    )


def dossier_page(*, publication_id: str, dossier: Mapping[str, Any]) -> bytes:
    """``/r/<pub>/dossier/<slug>/`` — the released dossier overview: the
    published sections/rows verbatim plus links into the compartments."""
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
{"".join(rows)}
"""
    return _layout(
        title=f"Dossier {jurisdiction}",
        body=body,
        publication_id=publication_id,
    )


# --------------------------------------------------------------------------- #
# Landing, catalog index, convenience stub, tombstone                          #
# --------------------------------------------------------------------------- #


def release_landing(entry: Mapping[str, Any]) -> bytes:
    """``/releases/<pub>/index.html`` — the release landing: descriptor +
    integrity digest + compartment inventory + download pointers."""
    pub = str(entry["publication_id"])
    comp_rows = "".join(
        f'<tr><td><a href="/r/{_e(pub)}/c/{_e(c["compartment"])}/">'
        f"{_e(c['compartment'])}</a></td>"
        f"<td>{_e(c.get('license'))}</td><td>{_e(c.get('record_count'))}</td>"
        f"<td>{_e(c.get('artifact_count'))}</td></tr>"
        for c in entry.get("compartments") or []
    )
    repro = entry.get("reproducibility") or {}
    body = f"""
<p><span class="k">Publication</span> <code>{_e(pub)}</code></p>
<p><span class="k">Data release</span> <code>{_e(entry.get("data_release_id"))}</code> ·
   <span class="k">Descriptor digest</span> <code>{_e(entry.get("descriptor_sha256"))}</code></p>
<p><span class="k">As-of world</span> {_e(repro.get("as_of_world"))} ·
   <span class="k">As-of belief</span> {_e(repro.get("as_of_belief"))} ·
   <span class="k">Ruleset</span> {_e(repro.get("ruleset_version"))} ·
   <span class="k">Policy</span> {_e(repro.get("policy_version"))}</p>
<h2>Compartments</h2>
<table><tr><th>Compartment</th><th>Licence</th><th>Records</th><th>Artifacts</th></tr>
{comp_rows}</table>
<h2>Machine-readable</h2>
<p><a href="catalog_entry.json"><code>catalog_entry.json</code></a> ·
   <a href="integrity_manifest.json"><code>integrity_manifest.json</code></a> ·
   <a href="descriptor.json"><code>descriptor.json</code></a></p>
<p class="mut">Records live under <code>/r/{_e(pub)}/c/&lt;compartment&gt;/…</code>.
Completeness: {_e((entry.get("completeness") or {}).get("state"))}.</p>
"""
    return _layout(
        title=f"Release {pub[:15]}…",
        body=body,
        publication_id=pub,
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

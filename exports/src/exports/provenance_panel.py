# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The one ``<ProvenancePanel>`` data contract + renderer (P35.36,
R11-K13-TX-08a / J3 §5.1–5.3, K13 §7 W1 / UXR-33, SIG-TRANSP-011).

One claim → one panel. Every consumer surface — the release record pages this
module renders for, and the web surfaces ``web/src/lib/provenance-panel.ts``
(the TypeScript twin of this contract) serves — reads the same field set and
the same verbatim J3 §5.1 binding-state wording:

* ``actual_capture`` — "Captured from <host> on <retrieved_at>; sha256 <…>."
* ``replayed`` — "Re-derived on <date> from a capture made on <retrieved_at>."
* ``document_only`` — "Extracted from a document; no page capture."
* ``legacy_synthetic`` — "Recorded by run <id> on <date>. SIG did not keep a
  per-record copy of the source for this run; the source's page lists the run
  and its captures."
* ``not_recorded`` — the honest fifth state: no publishable binding exists
  (the artifact gate dropped it or none was recorded). Never implied, never a
  fabricated document (C4 NEW-2).

Every field is a value or a named absence kind — ``not_recorded``,
``no_upstream_url_recorded``, ``not_publishable``, ``unavailable`` — never a
blank. No state implies SIG holds a document or capture it does not.
"""

from __future__ import annotations

import html
from collections.abc import Mapping
from typing import Any

from policy.transparency import NO_UPSTREAM_URL

#: The emitted panel-contract schema (``schema`` key on the contract dict).
PANEL_SCHEMA = "sig.provenance-panel/1"

#: Named absence tokens (the shared closed vocabulary the TS twin mirrors).
NOT_RECORDED = "not_recorded"
NOT_PUBLISHABLE = "not_publishable"
UNAVAILABLE = "unavailable"

#: J3 §5.1's verbatim binding-state sentences — the four recorded states plus
#: the named-absence fifth. ``{...}`` slots fill from the statement row; an
#: absent slot value renders ``not_recorded``, never a guessed instant.
BINDING_STATE_TEMPLATES: dict[str, str] = {
    "actual_capture": "Captured from {host} on {retrieved_at}; sha256 {digest}.",
    "replayed": "Re-derived on {bound_at} from a capture made on {retrieved_at}.",
    "document_only": "Extracted from a document; no page capture.",
    "legacy_synthetic": (
        "Recorded by run {run_id} on {recorded_at}. SIG did not keep a per-record "
        "copy of the source for this run; the source's page lists the run and its "
        "captures."
    ),
    NOT_RECORDED: "No published evidence binding is recorded for this claim.",
}

#: J3 §5.2's review wording while a claim is unreviewed/not_run.
NOT_YET_REVIEWED = "Not yet independently reviewed"

#: The panel's ordered field labels (J3 §5.2's verbatim field set).
FIELD_LABELS: tuple[str, ...] = (
    "Source",
    "Binding state",
    "Capture retrieved",
    "Capture digest",
    "Capture bytes",
    "Capture media type",
    "Upstream",
    "View original",
    "Extraction",
    "Directness class",
    "Epistemic tier + review status",
    "Contradictions",
    "Supersession",
    "Rights",
    "Equivalent requests",
    "Dispute",
)


def _v(value: Any, *, absent: str = NOT_RECORDED) -> str:
    """A display value or the named absence token — never a blank."""
    if value is None:
        return absent
    text = str(value).strip()
    return text if text else absent


def _date_only(value: Any) -> str | None:
    """ISO instant → its date grain for the verbatim sentences."""
    text = _v(value, absent="")
    return text[:10] if text else None


def binding_state_text(statement: Mapping[str, Any] | None) -> tuple[str, str]:
    """``(state, sentence)`` — the J3 §5.1 wording verbatim for the claim's
    binding state. Slot values that were never recorded render the
    ``not_recorded`` token inside the sentence — the wording stays exact and
    the absence stays named."""
    stmt = statement or {}
    state = str(stmt.get("binding_status") or NOT_RECORDED)
    if state not in BINDING_STATE_TEMPLATES:
        state = NOT_RECORDED
    capture = stmt.get("capture") or {}
    upstream = stmt.get("upstream") or {}
    recorded = stmt.get("recorded") or {}
    slots = {
        "host": _v(upstream.get("host")),
        "retrieved_at": _v(capture.get("retrieved_at")),
        "digest": _v(capture.get("digest")),
        "bound_at": _v(capture.get("bound_at")),
        "run_id": _v(recorded.get("run_id") or capture.get("run_id")),
        "recorded_at": _v(_date_only(recorded.get("at"))),
    }
    return state, BINDING_STATE_TEMPLATES[state].format(**slots)


def panel_from_statement(
    statement: Mapping[str, Any] | None,
    *,
    claim_id: str,
    source_href: str | None = "/sources/",
    dispute_href: str = "/dispute/",
    json_href: str | None = None,
    api_href: str | None = None,
) -> dict[str, Any]:
    """Normalise one ``sig.statement/1`` row (or its honest absence) into the
    shared ``sig.provenance-panel/1`` contract every surface renders.

    ``statement`` may be ``None`` (a claim anchor whose statement did not
    publish — e.g. a pre-P35.36 export): the panel then carries the
    ``not_recorded`` state and every field the named absence, never a gap.

    ``source_href`` links the source field (the live ``/sources/`` registry
    surface — per-source pages are a later row's surface; ``None`` renders
    the source id unlinked). ``json_href``/``api_href`` are the equivalent
    requests where the record's JSON twin / API route exist (P37.42 owns the
    API route — ``unavailable`` meanwhile, never a fabricated link).
    """
    stmt = dict(statement or {})
    state, state_text = binding_state_text(stmt)
    capture = stmt.get("capture") or {}
    upstream = stmt.get("upstream") or {}
    extraction = stmt.get("extraction") or {}
    epistemics = stmt.get("epistemics") or {}
    supersession = stmt.get("supersession") or {}
    contradictions = stmt.get("contradictions") or {}
    rights = stmt.get("rights") or {}
    view_original = stmt.get("view_original") or {}

    # Upstream display: the S-6 publication form — full URL, or host +
    # path-hash, or the named absence. ``withheld_by_policy`` never renders a
    # link at all (S-5/S-6: a URL that could name a person stays off the page).
    up_status = str(upstream.get("status") or NO_UPSTREAM_URL)
    if up_status == "full_url":
        upstream_display = _v(upstream.get("url"))
        upstream_href = upstream.get("url")
    elif up_status == "host_only":
        upstream_display = (
            f"{_v(upstream.get('host'))}#path_sha256:{_v(upstream.get('path_sha256'))}"
        )
        upstream_href = f"https://{upstream['host']}/" if upstream.get("host") else None
    elif up_status == "withheld_by_policy":
        upstream_display = NOT_PUBLISHABLE
        upstream_href = None
    else:
        upstream_display = NO_UPSTREAM_URL
        upstream_href = None

    review = _v(epistemics.get("review_status"))
    review_display = (
        NOT_YET_REVIEWED if review in {"unreviewed", "not_run", NOT_RECORDED} else review
    )

    con_ids = [str(c) for c in (contradictions.get("contradiction_ids") or [])]
    competitors = [str(c) for c in (contradictions.get("competing_claim_ids") or [])]

    extraction_display = NOT_RECORDED
    if extraction:
        parts = [
            _v(extraction.get("method")),
            _v(extraction.get("extractor_name")),
            _v(extraction.get("extractor_version")),
        ]
        extraction_display = " / ".join(p for p in parts if p != NOT_RECORDED) or NOT_RECORDED
        ex_review = _v(extraction.get("review_status"))
        if ex_review != NOT_RECORDED:
            extraction_display += f" ({ex_review})"

    supersession_parts: list[str] = []
    if supersession.get("revises_claim"):
        prior = _v(supersession.get("prior_recorded_at"))
        supersession_parts.append(f"revises {supersession['revises_claim']} (recorded {prior})")
    if supersession.get("retraction_of"):
        supersession_parts.append(f"retracts {supersession['retraction_of']}")
    supersession_display = "; ".join(supersession_parts) or NOT_RECORDED

    con_display = NOT_RECORDED
    if con_ids or competitors:
        bits = []
        if con_ids:
            bits.append("contradiction " + ", ".join(sorted(con_ids)))
        if competitors:
            bits.append("competing " + ", ".join(sorted(competitors)))
        con_display = "; ".join(bits)

    return {
        "schema": PANEL_SCHEMA,
        "claim_id": claim_id,
        "binding_status": state,
        "binding_text": state_text,
        "source": {
            "id": _v(stmt.get("source_id")),
            "name": stmt.get("source_name"),
            "href": source_href,
        },
        "capture": {
            "capture_id": _v(capture.get("capture_id")),
            "artifact_id": _v(capture.get("artifact_id")),
            "retrieved_at": _v(capture.get("retrieved_at")),
            "digest": _v(capture.get("digest")),
            # Display-grouped (K14 NEW-8): thousands separators, never a bare
            # 5+-digit run. The row's raw integer stays in the statement; a
            # non-numeric value falls back to the named absence, never a crash.
            "byte_size": (
                f"{capture['byte_size']:,}"
                if isinstance(capture.get("byte_size"), int)
                and not isinstance(capture.get("byte_size"), bool)
                else _v(capture.get("byte_size"))
            ),
            "media_type": _v(capture.get("media_type")),
            "storage_tier": _v(capture.get("storage_tier")),
        },
        "upstream": {
            "status": up_status,
            "display": upstream_display,
            "href": upstream_href,
        },
        "view_original": {
            "kind": _v(view_original.get("kind")),
            "label": _v(view_original.get("label")),
            "href": view_original.get("href"),
            "note": view_original.get("note"),
        },
        "extraction": extraction_display,
        "directness": _v(epistemics.get("directness")),
        "epistemic_review": {
            "reliability": _v(epistemics.get("reliability")),
            "integrity": _v(epistemics.get("integrity")),
            "review": review_display,
        },
        "contradictions": {"display": con_display, "ids": con_ids, "competing": competitors},
        "supersession": supersession_display,
        "rights": {
            "spdx": _v(rights.get("spdx")),
            "attribution": _v(rights.get("attribution")),
            "compartment": _v(rights.get("compartment")),
        },
        "equivalent_requests": {
            "json_href": json_href,
            "api_href": api_href,
            "api_status": UNAVAILABLE if api_href is None else "available",
        },
        "dispute_href": dispute_href,
    }


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _field(label: str, value_html: str) -> str:
    return f'<div class="pp-field"><dt>{_e(label)}</dt><dd>{value_html}</dd></div>'


def panel_html(panel: Mapping[str, Any], *, anchor: bool = True) -> str:
    """Render the shared contract to the zero-JS ``<details>`` panel.

    ``anchor`` writes ``id="claim-<claim_id>"`` — the ``#claim-<id>`` anchor
    J3 §5.1 names resolves to the panel itself (the data contract the anchor
    names). The markup is text-escaped field content only — never innerHTML
    input, never a script.
    """
    claim_id = str(panel.get("claim_id") or "")
    anchor_attr = f' id="claim-{_e(claim_id)}"' if anchor and claim_id else ""
    source = panel.get("source") or {}
    src_html = f"<code>{_e(source.get('id'))}</code>"
    if source.get("href") and source.get("id") != NOT_RECORDED:
        src_html = f'<a href="{_e(source["href"])}">{src_html}</a>'
    if source.get("name"):
        src_html += f' <span class="mut">{_e(source["name"])}</span>'

    upstream = panel.get("upstream") or {}
    up_html = f"<code>{_e(upstream.get('display'))}</code>"
    if upstream.get("href"):
        up_html = f'<a href="{_e(upstream["href"])}" rel="nofollow noopener">{up_html}</a>'

    vo = panel.get("view_original") or {}
    vo_html = _e(vo.get("label"))
    if vo.get("href"):
        vo_html = f'<a href="{_e(vo["href"])}" rel="nofollow noopener">{vo_html}</a>'
    if vo.get("note"):
        vo_html += f' <span class="mut">({_e(vo["note"])})</span>'

    capture = panel.get("capture") or {}
    epi = panel.get("epistemic_review") or {}
    con = panel.get("contradictions") or {}
    equiv = panel.get("equivalent_requests") or {}
    equiv_bits: list[str] = []
    if equiv.get("json_href"):
        equiv_bits.append(
            f'<a href="{_e(equiv["json_href"])}"><code>{_e(equiv["json_href"])}</code></a>'
        )
    else:
        equiv_bits.append(f"JSON twin: {UNAVAILABLE}")
    if equiv.get("api_href"):
        equiv_bits.append(
            f'<a href="{_e(equiv["api_href"])}"><code>{_e(equiv["api_href"])}</code></a>'
        )
    else:
        equiv_bits.append(f"API: {_e(equiv.get('api_status') or UNAVAILABLE)}")

    dispute = panel.get("dispute_href")
    dispute_html = (
        f'<a href="{_e(dispute)}">Report a correction</a>' if dispute else _e(UNAVAILABLE)
    )

    rows = "".join(
        [
            _field("Source", src_html),
            _field("Binding state", _e(panel.get("binding_text"))),
            _field("Capture retrieved", _e(capture.get("retrieved_at"))),
            _field("Capture digest", f"<code>{_e(capture.get('digest'))}</code>"),
            _field("Capture bytes", _e(capture.get("byte_size"))),
            _field("Capture media type", _e(capture.get("media_type"))),
            _field("Upstream", up_html),
            _field("View original", vo_html),
            _field("Extraction", _e(panel.get("extraction"))),
            _field("Directness class", _e(panel.get("directness"))),
            _field(
                "Epistemic tier + review status",
                _e(f"{epi.get('reliability')} / {epi.get('integrity')} — {epi.get('review')}"),
            ),
            _field("Contradictions", _e(con.get("display"))),
            _field("Supersession", _e(panel.get("supersession"))),
            _field(
                "Rights",
                _e(
                    f"{(panel.get('rights') or {}).get('spdx')} — "
                    f"{(panel.get('rights') or {}).get('attribution')}"
                ),
            ),
            _field("Equivalent requests", " · ".join(equiv_bits)),
            _field("Dispute", dispute_html),
        ]
    )
    return (
        f'<details class="provenance-panel" data-provenance-panel '
        f'data-binding-state="{_e(panel.get("binding_status"))}"{anchor_attr}>'
        f"<summary>Provenance — <code>{_e(claim_id)}</code> · "
        f"{_e(panel.get('binding_status'))}</summary>"
        f"<dl>{rows}</dl></details>"
    )


__all__ = [
    "BINDING_STATE_TEMPLATES",
    "FIELD_LABELS",
    "NOT_PUBLISHABLE",
    "NOT_RECORDED",
    "NOT_YET_REVIEWED",
    "PANEL_SCHEMA",
    "UNAVAILABLE",
    "binding_state_text",
    "panel_from_statement",
    "panel_html",
]

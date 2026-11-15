# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.evidence-claim-view/1`` claim-view generator (P37.37,
R11-K13-EV-03 / K8 EV-03, SIG-EVUI-004/005/009).

The web claim viewer's producer side. ``claim_view_bindings`` (the
``EXPORT_QUERIES`` row) supplies every publishable claim bound to a REAL
capture — ``binding_status = 'actual_capture'`` on a
``capture_classification = 'actual'`` row — with the recorded locator and
excerpt, the claim's own fields and the capture + artifact metadata. This
module turns those rows into the emitted ``ClaimView`` shape:

* **Generation scope (D-K8-2 [B-22], SIG-EVUI-009):** one view per
  document-genre claim with an ``actual_capture`` binding, capped at
  :data:`CLAIM_VIEW_CAP` per release; the cap, the eligible count and the
  overflow count are emitted in ``build.claim_views`` so ``/evidence/`` can
  state them. Selection is deterministic — the query's
  ``ORDER BY claim_id, capture_id`` and the first ``cap`` rows.
* **The pane is decided by lane × tier × Part VIII (SIG-EVUI-004, amends
  SIG-UI-028):** ``text_span`` only where the release actually carries the
  capture's stored text (``raw['capture_texts']`` — the declared capture-text
  seam) AND the recorded locator resolves to a span; ``download`` where the
  raw archive serves the bytes (``raw['raw_hrefs']``, P37.36's
  ``served_href_map``); ``locator_only`` where the lane forbids inline bytes
  (derived-only / link-only / unknown / raw-ok without served bytes);
  ``metadata_only`` where the lane or the sealed class forbids the bytes
  entirely. A pane never implies bytes or a route the release does not carry.
* **A locator always; an excerpt ≤ 300 characters only where recorded terms
  permit quotation (D-K8-1 [B-44]):** ``excerpt`` emits only on a
  non-metadata pane, only from the recorded ``claim_evidence.excerpt``, only
  where the source's recorded ``[redistribution].quotation_permitted`` is
  true OR the lane is ``raw-ok`` (bytes themselves publish — an excerpt is
  trivially permitted), and is refused past :data:`EXCERPT_MAX_CHARS`.
* **Diffs come only from real captures of the same artifact (SIG-EVUI-005,
  amends SIG-UI-029):** the per-capture ``fields`` map is the recorded
  predicate → raw-value pairs over every publishable bound claim — the rows
  this same query carries, so a diff never draws on fixtures and a second
  capture that was never recorded is a typed absence on the page, not a
  fabricated pair.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from policy.transparency import PART_VIII_SEALED_CLASSES

from . import statements as _stmt

#: The emitted schema (each view's ``schema`` key + the JSON twin's).
CLAIM_VIEW_SCHEMA = "sig.evidence-claim-view/1"

#: D-K8-2 [B-22]: claim views generate for document-genre claims with an
#: ``actual_capture`` binding, up to a published cap per release.
CLAIM_VIEW_CAP = 20_000

#: D-K8-1 [B-44]: an excerpt of at most 300 characters, only where the
#: source's recorded terms permit quotation.
EXCERPT_MAX_CHARS = 300

#: The artifact genres a claim view mints for — the document classes of the
#: closed ``vocab_artifact_genre`` vocabulary (D-K8-2's "document genres").
#: Datasets and run records are deliberately out: ``camera_registry``,
#: ``osm_node_set``, ``community_map``, ``subscription``, ``recommendation``
#: and ``connector_run`` carry per-row or per-run evidence, not a document
#: the viewer can render (recorded in ADR-246).
DOCUMENT_GENRES: frozenset[str] = frozenset(
    {
        "agenda_document",
        "agency_policy",
        "audit_log",
        "bill_index",
        "contract",
        "council_minutes",
        "executed_contract",
        "invoice",
        "news_article",
        "official_statement",
        "portal_document",
        "portal_snapshot",
        "template",
        "vendor_default_page",
    }
)

#: ``claim_view_bindings`` row columns (positional — mirrors the
#: ``EXPORT_QUERIES`` SELECT order).
CLAIM_VIEW_BINDING_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "capture_id",
    "artifact_id",
    "role",
    "binding_status",
    "bound_at",
    "locator_json",
    "excerpt",
    "binding_extractor_version",
    "retrieved_at",
    "content_digest",
    "byte_size",
    "media_type",
    "storage_tier",
    "capture_classification",
    "retrieved_by_run_id",
    "redaction_applied",
    "redaction_method",
    "redaction_version",
    "artifact_type",
    "artifact_title",
    "artifact_url",
    "artifact_source_id",
    "subject_id",
    "predicate_id",
    "raw_value",
    "observed_at",
    "review_status",
    "extraction_method",
    "extraction_name",
    "extraction_version",
    "extraction_review_status",
)

#: ``corrections`` row columns (positional — the first eight, the only ones
#: the claim history reads).
_CORRECTION_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "subject_id",
    "predicate_id",
    "raw_value",
    "reason",
    "revises_claim",
    "retraction_of",
    "recorded",
)


def _rows(raw_rows: Any, columns: Sequence[str]) -> list[dict[str, Any]]:
    """Positional fetchall rows → dicts (the statements.py convention)."""
    out: list[dict[str, Any]] = []
    for r in raw_rows or []:
        if isinstance(r, Mapping):
            out.append({c: r.get(c) for c in columns})
        else:
            out.append(dict(zip(columns, r, strict=False)))
    return out


def _iso(value: Any) -> str | None:
    """An ISO instant string, or None — never a partial scrub."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _lane_entry(
    lane_by_source: Mapping[str, Mapping[str, Any]] | None, sid: str
) -> Mapping[str, Any]:
    """The source's lane entry — an unknown source fails to the empty entry
    (the caller's lane default is ``unknown``, never an assumed lane)."""
    return (lane_by_source or {}).get(str(sid)) or {}


def _lane_of(entry: Mapping[str, Any]) -> str:
    decision = entry.get("decision")
    return str(getattr(decision, "lane", "unknown") or "unknown")


def _p8_of(entry: Mapping[str, Any]) -> str | None:
    p8 = entry.get("p8")
    return str(p8) if p8 else None


def fields_by_capture(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, str]]:
    """capture_id → ``{predicate_id: value}`` — the extracted-field map the
    §4.4 field-by-field diff compares (SIG-UI-029, SIG-EVUI-005).

    Only recorded values: the claim's verbatim ``raw_value``, never a parsed
    or normalized form. A predicate several claims of the same capture carry
    joins its recorded values (sorted, ``"; "``-separated — every component
    verbatim; a set change then diffs honestly). ``not_recorded`` keys never
    appear — a claim without a predicate contributes nothing.
    """
    by_cap: dict[str, dict[str, set[str]]] = {}
    for d in rows:
        pred = _iso(d.get("predicate_id"))
        value = _iso(d.get("raw_value"))
        cap = _iso(d.get("capture_id"))
        if not (pred and value and cap):
            continue
        by_cap.setdefault(cap, {}).setdefault(pred, set()).add(value)
    return {
        cap: {pred: "; ".join(sorted(values)) for pred, values in sorted(preds.items())}
        for cap, preds in by_cap.items()
    }


def _locator(locator_json: Any) -> dict[str, Any]:
    """The recorded ``claim_evidence.locator`` jsonb → the viewer's
    ``{kind, description, span?}`` (a locator always — D-K8-1; the span emits
    only for a ``byte_range`` the text pane can resolve).
    """
    loc: Mapping[str, Any] = {}
    if isinstance(locator_json, str) and locator_json.strip():
        try:
            parsed = json.loads(locator_json)
            if isinstance(parsed, Mapping):
                loc = parsed
        except json.JSONDecodeError:
            loc = {}
    elif isinstance(locator_json, Mapping):
        loc = locator_json
    kind = str(loc.get("kind") or loc.get("type") or "").strip()
    if kind == "byte_range":
        try:
            start = int(loc["start"])
            end = int(loc["end"])
        except (KeyError, TypeError, ValueError):
            return {
                "kind": "byte_range",
                "description": "byte range (bounds not recorded)",
            }
        return {
            "kind": "byte_range",
            "description": f"byte range {start}–{end}",
            "span": {"start": start, "end": end},
        }
    if kind == "page":
        page = loc.get("page")
        desc = f"page {page}" if page is not None else "page (number not recorded)"
        return {"kind": "page", "description": desc}
    if kind == "bbox":
        page = loc.get("page")
        return {
            "kind": "bbox",
            "description": f"page {page}, bounding box" if page is not None else "bounding box",
        }
    if kind == "cell":
        row = loc.get("row")
        col = loc.get("column")
        parts = [
            p
            for p in (
                f"row {row}" if row is not None else None,
                f"column {col}" if col is not None else None,
            )
            if p
        ]
        return {"kind": "cell", "description": ", ".join(parts) or "cell"}
    if kind == "row":
        row = loc.get("row")
        return {"kind": "row", "description": f"row {row}" if row is not None else "row"}
    if kind == "dom_path":
        sel = loc.get("selector")
        return {"kind": "dom_path", "description": f"selector {sel}" if sel else "DOM path"}
    # A kind outside the recorded six — or no recorded locator — surfaces as
    # the honest absence, never a guessed position (SIG-PARSE-003 makes a
    # missing locator the extractor's defect; the page says so).
    if kind:
        return {"kind": kind, "description": f"{kind} locator"}
    return {"kind": "not_recorded", "description": "no recorded locator"}


def _quotation_permitted(entry: Mapping[str, Any]) -> bool:
    """Whether the source's recorded terms permit quoting an excerpt
    (D-K8-1): the ``[redistribution].quotation_permitted`` marker the
    registry of record carries — absent/false = never quoted (fail closed)."""
    return bool(entry.get("quotation_permitted"))


def _pane_and_view(
    *,
    lane: str,
    p8: str | None,
    storage_tier: str,
    document_text: str | None,
    span: Mapping[str, Any] | None,
    redaction: dict[str, str] | None,
) -> dict[str, Any]:
    """The ``pane`` record for one claim view (SIG-EVUI-004 / K8 §4.3).

    ``metadata_only`` where the bytes may never publish (restricted lane,
    sealed Part VIII class, sealed/restricted tier); ``text_span`` only where
    the release carries the stored text AND the locator resolves to a span —
    a redacted derivative's text renders with the redaction's method/version
    named; ``download`` where the raw archive serves the bytes but no inline
    text was emitted; ``locator_only`` everywhere else (the locator always).
    """
    if (
        lane == "restricted"
        or p8 in PART_VIII_SEALED_CLASSES
        or storage_tier in {"sealed", "restricted"}
    ):
        reason = (
            f"part_viii:{p8}"
            if p8 in PART_VIII_SEALED_CLASSES
            else "lane:restricted"
            if lane == "restricted"
            else f"storage_tier:{storage_tier}"
        )
        return {"kind": "metadata_only", "reason": reason}
    if document_text is not None and span is not None:
        pane: dict[str, Any] = {"kind": "text_span"}
        if redaction is not None:
            pane["redaction"] = redaction
        return pane
    if lane == "raw-ok":
        # The archive serving the bytes is the caller's decision — this row
        # only marks which of the two byte-showing forms applies.
        return {"kind": "download_or_locator"}
    return {"kind": "locator_only"}


def _history_events(
    claim_id: str,
    bound_at: str | None,
    observed_at: str | None,
    retrieved_at: str | None,
    raw_value: str | None,
    corrections: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """The claim's full recorded history (SIG-UI-028): its own assertion plus
    every recorded supersession/retraction the corrections log carries —
    prior values stay citable at their belief time, never rewritten."""
    events: list[dict[str, Any]] = [
        {
            "asserted_at": bound_at or observed_at or retrieved_at or "not_recorded",
            "event": "asserted",
            "value": raw_value if raw_value is not None else "not_recorded",
        }
    ]
    for c in corrections or []:
        recorded = _iso(c.get("recorded")) or "not_recorded"
        reason = _iso(c.get("reason"))
        new_value = _iso(c.get("raw_value")) or "not_recorded"
        if _iso(c.get("revises_claim")) == claim_id:
            events.append(
                {
                    "asserted_at": recorded,
                    "event": "superseded",
                    "value": new_value,
                    **({"note": reason} if reason else {}),
                }
            )
        if _iso(c.get("retraction_of")) == claim_id:
            events.append(
                {
                    "asserted_at": recorded,
                    "event": "withdrawn",
                    "value": new_value,
                    **({"note": reason} if reason else {}),
                }
            )
    return events


def claim_views(
    raw: Mapping[str, Any],
    *,
    lane_by_source: Mapping[str, Mapping[str, Any]] | None = None,
    cap: int = CLAIM_VIEW_CAP,
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, dict[str, str]]]:
    """Build the emitted claim views + the per-capture ``fields`` diff maps.

    Returns ``(views, stats, fields_by_capture)``:

    * ``views`` — ``sig.evidence-claim-view/1`` rows, one per document-genre
      claim with an ``actual_capture`` binding, deterministic order
      (``claim_id, capture_id``), at most ``cap``.
    * ``stats`` — the ``build.claim_views`` disclosure (SIG-EVUI-009):
      ``{cap, eligible, emitted, overflow}``.
    * ``fields_by_capture`` — capture_id → ``{predicate: value}`` over EVERY
      bound publishable claim the query carried (all genres — the §4.4 diff
      is not scoped to view-eligible claims).
    """
    rows = _rows(raw.get("claim_view_bindings"), CLAIM_VIEW_BINDING_COLUMNS)
    corrections = _rows(raw.get("corrections"), _CORRECTION_COLUMNS)
    raw_hrefs = raw.get("raw_hrefs") or {}
    texts = raw.get("capture_texts") or {}
    fields = fields_by_capture(rows)

    # Contradiction/competing ids per claim — the materialized set the
    # statements rows read (recorded ids only; the page renders the marker
    # and the ids, never a fabricated competing row).
    contra_by_claim: dict[str, set[str]] = {}
    competing_by_claim: dict[str, set[str]] = {}
    for c in raw.get("materialized_contradictions") or []:
        if not isinstance(c, Mapping):
            continue
        cid_list = [str(x) for x in (c.get("claim_ids") or [])]
        con_id = _iso(c.get("contradiction_id"))
        for cid in cid_list:
            if con_id:
                contra_by_claim.setdefault(cid, set()).add(con_id)
            competing_by_claim.setdefault(cid, set()).update(x for x in cid_list if x != cid)

    # One view per claim: the first binding row is primary (the query orders
    # claim_id, capture_id); every binding's capture ids are recorded on the
    # view's evidence list the same way statements record them.
    primary: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for d in rows:
        cid = str(d["claim_id"])
        if cid not in primary:
            primary[cid] = d
            order.append(cid)
    eligible_ids = [
        cid for cid in order if str(primary[cid].get("artifact_type") or "") in DOCUMENT_GENRES
    ]
    emitted_ids = eligible_ids[:cap]
    overflow = len(eligible_ids) - len(emitted_ids)

    views: list[dict[str, Any]] = []
    for cid in emitted_ids:
        d = primary[cid]
        sid = _iso(d.get("artifact_source_id")) or ""
        entry = _lane_entry(lane_by_source, sid)
        lane = _lane_of(entry)
        p8 = _p8_of(entry)
        tier = _iso(d.get("storage_tier")) or "not_recorded"
        digest = _iso(d.get("content_digest"))
        locator = _locator(d.get("locator_json"))
        span = locator.get("span")
        raw_value = _iso(d.get("raw_value"))
        redaction = None
        if d.get("redaction_applied"):
            redaction = {
                "method": _iso(d.get("redaction_method")) or "not_recorded",
                "version": _iso(d.get("redaction_version")) or "not_recorded",
            }
        # The stored text emits only where it may publish — a public-tier
        # capture on the raw-ok lane; the text itself comes from the declared
        # capture-text seam, never the spine (bytes never travel the export).
        document_text = None
        if lane == "raw-ok" and tier == "public" and digest:
            text = texts.get(digest)
            if isinstance(text, str) and text:
                document_text = text
        raw_href = raw_hrefs.get(digest) if digest else None
        upstream = _stmt.upstream_block(
            _iso(d.get("artifact_url")),
            lane=lane,
            gate_passed=True,
            part_viii_class=p8,
        )
        bytes_stored = tier == "public" and int(d.get("byte_size") or 0) > 0
        view_original = _stmt.capture_view_original(
            lane=lane,
            part_viii_class=p8,
            bytes_stored=bytes_stored,
            upstream=upstream,
            raw_href=raw_href,
        )
        pane = _pane_and_view(
            lane=lane,
            p8=p8,
            storage_tier=tier,
            document_text=document_text,
            span=span if isinstance(span, Mapping) else None,
            redaction=redaction,
        )
        if pane["kind"] == "download_or_locator":
            # raw-ok: the archive's served href decides the byte-showing
            # form — ``download`` where the release carries the object,
            # ``locator_only`` where it does not (a label never implies a
            # route the release does not carry).
            pane = {"kind": "download" if raw_href else "locator_only"}
        # D-K8-1 [B-44]: the recorded excerpt publishes ONLY where recorded
        # terms permit quotation — the registry's ``quotation_permitted``
        # marker, or the raw-ok lane where the bytes themselves publish —
        # and never past 300 chars, never on a metadata-only pane.
        excerpt = None
        recorded_excerpt = _iso(d.get("excerpt"))
        if (
            recorded_excerpt
            and pane["kind"] in {"locator_only", "download", "text_span"}
            and (lane == "raw-ok" or _quotation_permitted(entry))
            and len(recorded_excerpt) <= EXCERPT_MAX_CHARS
        ):
            excerpt = recorded_excerpt

        capture: dict[str, Any] = {
            "capture_id": _iso(d.get("capture_id")),
            "artifact_id": _iso(d.get("artifact_id")),
            "storage_tier": tier,
            "captured_at": _iso(d.get("retrieved_at")),
            "content_digest": digest,
            "acquisition_method": _iso(d.get("acquisition_method")),
            "byte_size": int(d["byte_size"]) if d.get("byte_size") is not None else None,
            "media_type": _iso(d.get("media_type")),
            "capture_classification": _iso(d.get("capture_classification")),
            "fields": fields.get(str(d.get("capture_id"))) or {},
            "view_original": view_original,
        }
        if document_text is not None:
            capture["document_text"] = document_text

        view: dict[str, Any] = {
            "schema": CLAIM_VIEW_SCHEMA,
            "claim_id": cid,
            "claim_label": (_iso(d.get("predicate_id")) or "not_recorded").replace("_", " "),
            "value": raw_value if raw_value is not None else "not_recorded",
            "subject_id": _iso(d.get("subject_id")),
            "capture": capture,
            "binding_status": "actual_capture",
            "lane": lane,
            "part_viii_class": p8,
            "pane": pane,
            "locator": locator,
            "extraction_method": (
                _iso(d.get("extraction_method")) or _iso(d.get("extraction_name")) or "not_recorded"
            ),
            "extraction_version": (
                _iso(d.get("extraction_version"))
                or _iso(d.get("binding_extractor_version"))
                or "not_recorded"
            ),
            "review_status": (
                _iso(d.get("review_status"))
                or _iso(d.get("extraction_review_status"))
                or "not_recorded"
            ),
            "conflicting_claims": [],
            "contradiction_ids": sorted(contra_by_claim.get(cid, ())),
            "competing_claim_ids": sorted(competing_by_claim.get(cid, ())),
            "history": _history_events(
                cid,
                _iso(d.get("bound_at")),
                _iso(d.get("observed_at")),
                _iso(d.get("retrieved_at")),
                raw_value,
                corrections,
            ),
            "upstream": upstream,
        }
        if excerpt is not None:
            view["excerpt"] = excerpt
        views.append(view)

    stats = {
        "cap": cap,
        "eligible": len(eligible_ids),
        "emitted": len(emitted_ids),
        "overflow": overflow,
        "basis": (
            "P37.37 (R11-K13-EV-03 / K8 EV-03, D-K8-2 [B-22]): one claim-view "
            "page per document-genre claim with an actual_capture binding, "
            "deterministically capped (claim_id order); the cap and the "
            "overflow count publish on /evidence/ (SIG-EVUI-009)."
        ),
    }
    return views, stats, fields

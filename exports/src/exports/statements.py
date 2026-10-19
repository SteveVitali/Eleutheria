# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig.statement/1`` per-compartment statements stream (P35.36,
R11-K13-TX-08a / J3 §5.1–5.3, SIG-TRANSP-011).

One row per published claim — the ``record_claims`` stream the release's claim
index already built but never published (J1 §B.4) — widened into the full
provenance record the shared ``<ProvenancePanel>`` contract reads:

* the claim anchor (id, entity, predicate, observed date, source) — the same
  fields ``record_claims.jsonl`` carries;
* the binding state (``claim_evidence.binding_status`` — J3 §5.1's four states,
  rendered verbatim; ``not_recorded`` when no publishable binding exists — an
  honest fifth state, never a fabricated document);
* the bound capture's scrubbed locators (digest, bytes, media type, tier,
  retrieved/run) and the artifact's S-6-gated upstream reference;
* the epistemic block (directness / reliability / integrity / review status),
  the recorded-run pair, the supersession chain and the contradiction links;
* the per-claim rights (SPDX + attribution + compartment).

Two rules are load-bearing and live here, not in prose:

* **The value never publishes.** ``value`` is always the closed token
  ``not_published`` — the record_claims contract already refuses raw claim
  literals; statements inherit the refusal.
* **Every upstream reference passes the P35.31 S-6 gate** — the full
  credential-stripped URL only for ``raw-ok``/``derived-only`` lanes whose
  gate passed; host + path-hash otherwise; ``no_upstream_url_recorded`` when
  none was recorded; ``withheld_by_policy`` when the host itself cannot
  publish (an IP literal, or a sealed Part VIII class). A raw URL is never
  copied through.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from policy.transparency import (
    NO_UPSTREAM_URL,
    PART_VIII_SEALED_CLASSES,
    scrub_source_url,
)

#: The emitted row schema (manifest ``schema`` + the row's own ``schema`` key).
STATEMENT_SCHEMA = "sig.statement/1"

#: J3 §5.1's four binding states — the ``claim_evidence.binding_status``
#: closed vocabulary (``db/deploy/claim_assertion_bindings.sql``).
BINDING_STATES: frozenset[str] = frozenset(
    {"actual_capture", "replayed", "document_only", "legacy_synthetic"}
)

#: The named absence state: no publishable ``claim_evidence`` row exists for
#: the claim (the artifact gate dropped every binding, or none was recorded).
#: Rendered as its own honest state — never implied ``legacy_synthetic`` and
#: never a fabricated document (C4 NEW-2).
BINDING_NOT_RECORDED = "not_recorded"

#: The closed token ``value`` carries — raw claim literals never publish.
VALUE_NOT_PUBLISHED = "not_published"

#: ``upstream.status`` closed vocabulary.
UPSTREAM_FULL_URL = "full_url"
UPSTREAM_HOST_ONLY = "host_only"
UPSTREAM_NONE = NO_UPSTREAM_URL  # "no_upstream_url_recorded"
UPSTREAM_WITHHELD = "withheld_by_policy"
UPSTREAM_STATUSES: frozenset[str] = frozenset(
    {UPSTREAM_FULL_URL, UPSTREAM_HOST_ONLY, UPSTREAM_NONE, UPSTREAM_WITHHELD}
)

#: ``view_original.kind`` closed vocabulary — the J3 §5.3 table's label
#: classes. The byte routes themselves are TX-08b's machinery (P36.51): this
#: row emits the label + the S-6-safe href (only ``view_at_source`` carries
#: one), never a raw-byte link.
VO_DOWNLOAD_ORIGINAL = "download_original"
VO_DOWNLOAD_REDACTED = "download_redacted"
VO_VIEW_AT_SOURCE = "view_at_source"
VO_NOT_REDISTRIBUTABLE = "not_redistributable"
VO_RIGHTS_NOT_REVIEWED = "rights_not_reviewed"
VO_NOT_RECORDED = "not_recorded"
VIEW_ORIGINAL_KINDS: frozenset[str] = frozenset(
    {
        VO_DOWNLOAD_ORIGINAL,
        VO_DOWNLOAD_REDACTED,
        VO_VIEW_AT_SOURCE,
        VO_NOT_REDISTRIBUTABLE,
        VO_RIGHTS_NOT_REVIEWED,
        VO_NOT_RECORDED,
    }
)

#: J3 §5.3: the Part VIII field-screen classes whose bytes serve only as a
#: redacted copy (a recorded NEW capture — TX-08b's machinery).
_P8_REDACTED_CLASSES: frozenset[str] = frozenset({"P8-5", "P8-6", "P8-8"})

#: The lanes whose full upstream URL may publish (J4 S-6).
_URL_PUBLISHING_LANES: frozenset[str] = frozenset({"raw-ok", "derived-only"})

#: ``claim_binding_detail`` row columns (positional — mirrors the
#: ``EXPORT_QUERIES`` SELECT order).
BINDING_DETAIL_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "capture_id",
    "artifact_id",
    "role",
    "binding_status",
    "bound_at",
    "extractor_version",
    "retrieved_at",
    "content_digest",
    "byte_size",
    "media_type",
    "storage_tier",
    "capture_classification",
    "retrieved_by_run_id",
    "artifact_url",
    "artifact_source_id",
    "acquisition_method",
    "extraction_method",
    "extraction_name",
    "extraction_version",
    "extraction_review_status",
)

#: ``claim_provenance`` row columns (positional).
CLAIM_PROVENANCE_COLUMNS: tuple[str, ...] = (
    "claim_id",
    "review_status",
    "claim_directness",
    "source_reliability",
    "artifact_integrity",
    "ingest_run_id",
    "recorded_at",
    "revises_claim",
    "retraction_of",
)


def _rows(raw_rows: Any, columns: Sequence[str]) -> list[dict[str, Any]]:
    """Positional fetchall rows → dicts (the transparency.py convention)."""
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


def upstream_block(
    url: str | None,
    *,
    lane: str,
    gate_passed: bool,
    part_viii_class: str | None = None,
) -> dict[str, Any]:
    """The S-6 publication form of one upstream URL (P35.31 / J4 S-6).

    ``status`` is the closed vocabulary: ``full_url`` | ``host_only`` |
    ``no_upstream_url_recorded`` | ``withheld_by_policy``. A sealed Part VIII
    class or an IP-literal host withholds even the host (S-5 wins over S-6;
    the capture_record sealed rule — no path-hash may bind a sealed row to a
    host).
    """
    out: dict[str, Any] = {
        "status": UPSTREAM_NONE,
        "url": None,
        "host": None,
        "path_sha256": None,
    }
    text = str(url or "").strip()
    if not text:
        return out
    if part_viii_class in PART_VIII_SEALED_CLASSES:
        out["status"] = UPSTREAM_WITHHELD
        return out
    scrubbed = scrub_source_url(text, lane=lane, gate_passed=gate_passed)
    if scrubbed is None:
        return out
    if not scrubbed.host:
        # The host itself is not publishable (an IP literal — S-5) — the
        # gated-row convention emits ``not_publishable`` for exactly this.
        out["status"] = UPSTREAM_WITHHELD
        out["host"] = "not_publishable"
        return out
    out["host"] = scrubbed.host
    if scrubbed.url:
        out["status"] = UPSTREAM_FULL_URL
        out["url"] = scrubbed.url
    else:
        out["status"] = UPSTREAM_HOST_ONLY
        out["path_sha256"] = scrubbed.path_sha256
    return out


def view_original_block(
    *,
    binding_status: str,
    lane: str,
    part_viii_class: str | None,
    bytes_stored: bool,
    upstream: Mapping[str, Any],
) -> dict[str, Any]:
    """The J3 §5.3 label state — the lane × Part VIII × bytes-stored table.

    This row emits the LABEL + the safe href only: ``view_at_source`` links
    the S-6-scrubbed upstream; the byte routes (``download_original`` /
    ``download_redacted``) carry ``href: None`` — minting raw-byte links is
    TX-08b's machinery (P36.51), not this row's.
    """
    label = {
        VO_DOWNLOAD_ORIGINAL: "Download original",
        VO_DOWNLOAD_REDACTED: "Download redacted copy",
        VO_VIEW_AT_SOURCE: "View at source",
        VO_NOT_REDISTRIBUTABLE: "Not redistributable",
        VO_RIGHTS_NOT_REVIEWED: "Rights not reviewed",
        VO_NOT_RECORDED: "not_recorded",
    }
    kind = VO_NOT_RECORDED
    href: str | None = None
    note: str | None = None
    if binding_status in BINDING_STATES:
        if lane == "restricted" or part_viii_class in PART_VIII_SEALED_CLASSES:
            kind = VO_NOT_REDISTRIBUTABLE
            reason = part_viii_class if part_viii_class in PART_VIII_SEALED_CLASSES else "terms"
            note = f"reason: {reason}"
        elif lane == "unknown":
            kind = VO_RIGHTS_NOT_REVIEWED
        elif lane == "raw-ok":
            if bytes_stored:
                if part_viii_class in _P8_REDACTED_CLASSES:
                    kind = VO_DOWNLOAD_REDACTED
                    note = "redacted copy served as a new capture; the original is never served"
                else:
                    kind = VO_DOWNLOAD_ORIGINAL
            else:
                kind = VO_VIEW_AT_SOURCE
                note = "SIG did not retain these bytes"
        elif lane in {"derived-only", "link-only"}:
            kind = VO_VIEW_AT_SOURCE
        else:
            kind = VO_NOT_RECORDED
    if kind == VO_VIEW_AT_SOURCE:
        # The S-6 href only — a host-only upstream links the bare host; a
        # withheld one links nothing (no URL where a URL could name a person).
        if upstream.get("url"):
            href = str(upstream["url"])
        elif upstream.get("host") and upstream.get("status") == UPSTREAM_HOST_ONLY:
            href = f"https://{upstream['host']}/"
    return {"kind": kind, "label": label[kind], "href": href, "note": note}


def _binding_entries(details: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """The claim's ``evidence`` list — every publishable binding, in the
    recorded order (already sorted by the query's ORDER BY), each carrying its
    own binding_status (the claim's stated state is the first row's)."""
    out: list[dict[str, Any]] = []
    for d in details:
        out.append(
            {
                "capture_id": _iso(d.get("capture_id")),
                "artifact_id": _iso(d.get("artifact_id")),
                "role": _iso(d.get("role")),
                "binding_status": (_iso(d.get("binding_status")) or BINDING_NOT_RECORDED),
            }
        )
    return out


def statement_row(
    *,
    claim_id: str,
    entity_id: str,
    predicate_id: str | None,
    observed_at: str | None,
    source_id: str,
    licence: str,
    compartment: str,
    attribution: str | None,
    access_kind: str | None = None,
    provenance: Mapping[str, Any] | None = None,
    details: Sequence[Mapping[str, Any]] = (),
    plain_bindings: Sequence[Mapping[str, Any]] = (),
    lane: str = "unknown",
    lane_basis: str | None = None,
    part_viii_class: str | None = None,
    gate_passed: bool = True,
    source_homepage: str | None = None,
    prior_recorded_at: Mapping[str, str | None] | None = None,
    contradictions: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """One ``sig.statement/1`` row — the published per-claim provenance record.

    ``details`` are the claim's ``claim_binding_detail`` rows (capture +
    artifact + extraction joined); when the spine predates the P32.2 binding
    columns the query is empty and ``plain_bindings`` (the base
    ``claim_id/capture_id/artifact_id/role`` shape) still carries the locators
    — the state is then honestly ``not_recorded``, never a guessed
    ``legacy_synthetic``.
    """
    prov = dict(provenance or {})
    entries = (
        _binding_entries(details)
        if details
        else [
            {
                "capture_id": _iso(b.get("capture_id")),
                "artifact_id": _iso(b.get("artifact_id")),
                "role": _iso(b.get("role")),
                "binding_status": BINDING_NOT_RECORDED,
            }
            for b in (plain_bindings or [])
        ]
    )
    primary = details[0] if details else None
    binding_status = (
        _iso(primary.get("binding_status")) if primary is not None else BINDING_NOT_RECORDED
    ) or BINDING_NOT_RECORDED
    if binding_status not in BINDING_STATES and binding_status != BINDING_NOT_RECORDED:
        # A value outside the closed vocabulary is a defect — fail to the
        # named-absence state rather than leak an unvetted label (S-12).
        binding_status = BINDING_NOT_RECORDED

    capture: dict[str, Any] | None = None
    if primary is not None:
        capture = {
            "capture_id": _iso(primary.get("capture_id")),
            "artifact_id": _iso(primary.get("artifact_id")),
            "retrieved_at": _iso(primary.get("retrieved_at")),
            "digest": _iso(primary.get("content_digest")),
            "byte_size": (
                int(primary["byte_size"]) if primary.get("byte_size") is not None else None
            ),
            "media_type": _iso(primary.get("media_type")),
            "storage_tier": _iso(primary.get("storage_tier")),
            "capture_classification": _iso(primary.get("capture_classification")),
            "run_id": _iso(primary.get("retrieved_by_run_id")),
            "bound_at": _iso(primary.get("bound_at")),
        }

    # The upstream reference: the bound artifact's recorded URL wins; absent
    # one, the source's registry homepage stands in (labelled by the lane's
    # own basis — never derived beyond S-6).
    upstream_url = (_iso(primary.get("artifact_url")) if primary is not None else None) or (
        source_homepage
    )
    p8 = part_viii_class or None
    upstream = upstream_block(
        upstream_url,
        lane=lane,
        gate_passed=gate_passed,
        part_viii_class=p8,
    )

    bytes_stored = bool(
        primary is not None
        and primary.get("storage_tier") == "public"
        and (primary.get("byte_size") or 0) > 0
    )
    view_original = view_original_block(
        binding_status=binding_status,
        lane=lane,
        part_viii_class=p8,
        bytes_stored=bytes_stored,
        upstream=upstream,
    )

    extraction: dict[str, Any] | None = None
    if primary is not None and _iso(primary.get("extraction_method")):
        extraction = {
            "method": _iso(primary.get("extraction_method")),
            "extractor_name": _iso(primary.get("extraction_name")),
            "extractor_version": _iso(primary.get("extraction_version"))
            or _iso(primary.get("extractor_version")),
            "review_status": _iso(primary.get("extraction_review_status")),
        }
    elif primary is not None and _iso(primary.get("extractor_version")):
        extraction = {
            "method": None,
            "extractor_name": None,
            "extractor_version": _iso(primary.get("extractor_version")),
            "review_status": None,
        }

    revises = _iso(prov.get("revises_claim"))
    retracts = _iso(prov.get("retraction_of"))
    contradiction_ids: list[str] = []
    competing_claim_ids: list[str] = []
    for c in contradictions or []:
        cid_list = [str(x) for x in (c.get("claim_ids") or [])]
        if claim_id not in cid_list:
            continue
        con_id = _iso(c.get("contradiction_id"))
        if con_id:
            contradiction_ids.append(con_id)
        competing_claim_ids.extend(cid for cid in cid_list if cid != claim_id)

    row: dict[str, Any] = {
        "schema": STATEMENT_SCHEMA,
        "claim_id": claim_id,
        "entity_id": entity_id,
        "predicate_id": predicate_id,
        "observed_at": observed_at,
        "source_id": source_id,
        "value": VALUE_NOT_PUBLISHED,
        "binding_status": binding_status,
        "binding_role": _iso(primary.get("role")) if primary is not None else None,
        "lane": lane,
        "lane_basis": _iso(lane_basis),
        "capture": capture,
        "upstream": upstream,
        "view_original": view_original,
        "extraction": extraction,
        "epistemics": {
            "directness": _iso(prov.get("claim_directness")),
            "reliability": _iso(prov.get("source_reliability")),
            "integrity": _iso(prov.get("artifact_integrity")),
            "review_status": _iso(prov.get("review_status")),
        },
        "recorded": {
            "run_id": _iso(prov.get("ingest_run_id")),
            "at": _iso(prov.get("recorded_at")),
        },
        "supersession": {
            "revises_claim": revises,
            "retraction_of": retracts,
            "prior_recorded_at": (
                (prior_recorded_at or {}).get(revises)
                if revises
                else (prior_recorded_at or {}).get(retracts)
                if retracts
                else None
            ),
        },
        "contradictions": {
            "contradiction_ids": sorted(set(contradiction_ids)),
            "competing_claim_ids": sorted(set(competing_claim_ids)),
        },
        "rights": {
            "spdx": str(licence),
            "attribution": _iso(attribution),
            "compartment": compartment,
        },
        "evidence": entries,
    }
    if access_kind is not None:
        row["access_kind"] = access_kind
    return row


__all__ = [
    "BINDING_DETAIL_COLUMNS",
    "BINDING_NOT_RECORDED",
    "BINDING_STATES",
    "CLAIM_PROVENANCE_COLUMNS",
    "STATEMENT_SCHEMA",
    "UPSTREAM_FULL_URL",
    "UPSTREAM_HOST_ONLY",
    "UPSTREAM_NONE",
    "UPSTREAM_STATUSES",
    "UPSTREAM_WITHHELD",
    "VALUE_NOT_PUBLISHED",
    "VIEW_ORIGINAL_KINDS",
    "statement_row",
    "upstream_block",
    "view_original_block",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only source-attribution backfill (P34.21a / ADR-194; E2-12, F-387).

The claim spine is append-only: a claim's recorded ``rights_id`` is the
provenance of what was known at assertion time and is never rewritten. Two
recorded defect classes therefore take NEW ``rights_record`` + ``rights_decision``
rows, never an ``UPDATE``:

* **Wrong or missing attribution on a resolved record.** The pre-P34.21a
  ``PgClaimSink`` keyed rights records on SPDX alone, so a source's claims could
  land on a record carrying ANOTHER source's attribution ("DeFlock community
  map" on non-DeFlock rows) or none. The correction is an *attribution
  correction* decision: ``(source_id, prior_rights_id) -> corrected
  rights_record`` where the corrected record keeps the prior's
  ``spdx_expression``, ``redistributable`` and ``derivative_permitted`` — only
  ``attribution_text`` / ``terms_url`` change, so nothing is ever relicensed
  (ADR-194). A correction row that would change a resolved record's licence is
  REFUSED — loudly, before anything is written.
* **Identifier normalisation.** Where the licence identifier itself was
  malformed (``OGL-3.0`` for OGL-UK-3.0), the committed corrections artifact
  declares the mapping per row (``spdx_aliases``) — the same licence text under
  its canonical SPDX id, recorded and reviewed, never a silent relabel.
* **UNDETERMINED priors** lift under the ADR-095 semantics unchanged: the
  corrected record is the resolution.

The corrections artifact is a committed, reviewer-prepared file (generated from
``sources.toml`` by ``sig-connectors attribution-correction-list``); the writer
is dry-run by default and INSERT-only — ``n_tup_upd``/``n_tup_del`` on the spine
tables are unchanged by an apply (verified in the hosted leg's read-back).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

#: `redistributable`/`derivative_permitted` values a corrected record may carry.
DECIDED_VALUES = ("yes", "no", "review_required")

#: The schema id of the committed corrections artifact.
CORRECTIONS_SCHEMA = "sig.attribution-corrections/1"


class AttributionCorrectionError(ValueError):
    """A corrections row failed validation or would relicense a resolved record."""


@dataclass(frozen=True)
class AttributionCorrection:
    """One source's corrected per-source rights record — the backfill list row.

    ``spdx_aliases`` names recorded licence-identifier normalisations: a
    resolved prior whose ``spdx_expression`` is one of these is corrected to
    ``spdx`` (the same licence text under its canonical id — e.g. the malformed
    ``OGL-3.0`` → ``OGL-UK-3.0``). Any other ``spdx`` difference on a resolved
    prior is a licence change and is refused (ADR-194).
    """

    source_id: str
    spdx: str
    attribution: str
    redistributable: str
    derivative_permitted: str
    terms_url: str
    reviewed_by: str  # a ROLE (e.g. 'licensing reviewer'), never a personal name
    reviewed_on: date
    basis: str  # names E2-12 + ADR-194
    retrieval_date: date
    review_packet: str | None = None
    spdx_aliases: tuple[str, ...] = ()


def load_corrections(path: str | Path) -> list[AttributionCorrection]:
    """Load a committed corrections artifact (JSON) into validated rows."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = doc.get("corrections")
    if not isinstance(rows, list):
        raise AttributionCorrectionError(f"{path}: no 'corrections' list")
    out: list[AttributionCorrection] = []
    errors: list[str] = []
    for i, row in enumerate(rows):
        try:
            corr = AttributionCorrection(
                source_id=str(row["source_id"]),
                spdx=str(row["spdx"]),
                attribution=str(row.get("attribution") or ""),
                redistributable=str(row["redistributable"]),
                derivative_permitted=str(row["derivative_permitted"]),
                terms_url=str(row.get("terms_url") or ""),
                reviewed_by=str(row["reviewed_by"]),
                reviewed_on=date.fromisoformat(str(row["reviewed_on"])),
                basis=str(row["basis"]),
                retrieval_date=date.fromisoformat(str(row["retrieval_date"])),
                review_packet=(
                    None if row.get("review_packet") is None else str(row["review_packet"])
                ),
                spdx_aliases=tuple(str(s) for s in (row.get("spdx_aliases") or ())),
            )
        except (KeyError, ValueError) as exc:
            errors.append(f"row {i} ({row.get('source_id', '?')}): {exc}")
            continue
        errors.extend(f"row {i} ({corr.source_id}): {e}" for e in validate_correction(corr))
        out.append(corr)
    if errors:
        raise AttributionCorrectionError("invalid corrections artifact:\n  " + "\n  ".join(errors))
    return out


def validate_correction(corr: AttributionCorrection) -> list[str]:
    """Fail-closed validation of one corrections row. Returns a list of problems."""
    errors: list[str] = []
    if not corr.source_id.strip():
        errors.append("source_id is empty")
    if not corr.spdx.strip():
        errors.append("spdx is empty")
    if corr.redistributable not in DECIDED_VALUES:
        errors.append(
            f"redistributable must be one of {DECIDED_VALUES}, got {corr.redistributable!r}"
        )
    if corr.derivative_permitted not in DECIDED_VALUES:
        errors.append(
            f"derivative_permitted must be one of {DECIDED_VALUES}, "
            f"got {corr.derivative_permitted!r}"
        )
    if not corr.attribution.strip() and not corr.terms_url.strip():
        errors.append(
            "attribution and terms_url are both empty — a correction that corrects "
            "nothing is not a decision"
        )
    if corr.spdx in corr.spdx_aliases:
        errors.append("spdx_aliases must not repeat the corrected spdx")
    if not corr.reviewed_by.strip():
        errors.append("reviewed_by is empty — a reviewer ROLE is required (never a name)")
    if not corr.basis.strip():
        errors.append("basis is empty — the basis names E2-12 + ADR-194")
    elif "ADR-194" not in corr.basis:
        errors.append("basis must name ADR-194 (the attribution-correction decision)")
    return errors


# --------------------------------------------------------------------------- #
# Spine reads — the priors a correction covers                                 #
# --------------------------------------------------------------------------- #


def _source_priors(conn: Any, source_id: str) -> dict[str, dict[str, Any]]:
    """Every rights_record this source's rows link to: {rights_id: record}.

    Priors are the source's own links — the ``source_registry.rights_id``, the
    claims' recorded ``rights_id`` (through the ``establishes`` evidence chain),
    and the rights recorded on the source's ``evidence_artifact`` rows — the
    same three link surfaces every effective-rights reader resolves through
    (ADR-095, ADR-194). Another source's claims that coincidentally SHARE one of
    these records are untouched: the decision is keyed on THIS source, so their
    effective rights are unchanged.
    """
    rows = conn.execute(
        "SELECT DISTINCT r.rights_id, r.spdx_expression, r.attribution_text,"
        "       r.terms_url, r.redistributable, r.derivative_permitted "
        "  FROM rights_record r "
        " WHERE r.rights_id IN ("
        "   SELECT sr.rights_id FROM source_registry sr WHERE sr.source_id = %s"
        "   UNION SELECT c.rights_id FROM claim c"
        "     JOIN claim_evidence ce ON ce.claim_id = c.claim_id AND ce.role = 'establishes'"
        "     JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "     JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        "     WHERE ea.source_id = %s"
        "   UNION SELECT ea2.rights_id FROM evidence_artifact ea2"
        "     WHERE ea2.source_id = %s"
        " )",
        (source_id, source_id, source_id),
    ).fetchall()
    return {
        str(r[0]): {
            "spdx": str(r[1]),
            "attribution": None if r[2] is None else str(r[2]),
            "terms_url": None if r[3] is None else str(r[3]),
            "redistributable": str(r[4]),
            "derivative_permitted": str(r[5]),
        }
        for r in rows
    }


def _claims_affected(conn: Any, source_id: str, prior_rights_id: str) -> int:
    """How many of the source's claims the decision covers (recorded = prior)."""
    row = conn.execute(
        "SELECT count(DISTINCT c.claim_id) FROM claim c"
        " JOIN claim_evidence ce ON ce.claim_id = c.claim_id AND ce.role = 'establishes'"
        " JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        " JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        " WHERE ea.source_id = %s AND c.rights_id = %s",
        (source_id, prior_rights_id),
    ).fetchone()
    return 0 if row is None else int(row[0])


def _artifacts_affected(conn: Any, source_id: str, prior_rights_id: str) -> int:
    """How many of the source's evidence artifacts carry the prior record."""
    row = conn.execute(
        "SELECT count(*) FROM evidence_artifact WHERE source_id = %s AND rights_id = %s",
        (source_id, prior_rights_id),
    ).fetchone()
    return 0 if row is None else int(row[0])


def _classify_prior(corr: AttributionCorrection, prior: dict[str, Any]) -> tuple[str, str | None]:
    """Classify one prior record against the corrected signature.

    Returns ``(kind, reason)`` — ``noop`` (the record already carries the
    corrected attribution/terms), ``correct`` (a resolved record whose licence
    identity is preserved — attribution/terms only), ``lift`` (an UNDETERMINED
    record resolved under ADR-095 semantics), or ``refused`` (a licence change
    on a resolved record — the reason names the differing field).
    """
    same_text = (prior["attribution"] or "") == corr.attribution and (
        prior["terms_url"] or ""
    ) == corr.terms_url
    if (
        same_text
        and prior["spdx"] == corr.spdx
        and prior["redistributable"] == corr.redistributable
        and prior["derivative_permitted"] == corr.derivative_permitted
    ):
        return "noop", "record already carries the corrected signature"
    if prior["redistributable"] == "UNDETERMINED":
        return "lift", None
    # Resolved priors may only gain corrected attribution/terms — never a
    # different licence (ADR-194: nothing is ever relicensed).
    if prior["spdx"] != corr.spdx and prior["spdx"] not in corr.spdx_aliases:
        return (
            "refused",
            f"licence change on a resolved record: {prior['spdx']!r} -> {corr.spdx!r} "
            "is not an attribution correction (ADR-194; declare the identifier "
            "normalisation in spdx_aliases or record a separate review)",
        )
    if prior["redistributable"] != corr.redistributable:
        return (
            "refused",
            f"redistributable change on a resolved record: "
            f"{prior['redistributable']!r} -> {corr.redistributable!r} "
            "(ADR-194: the correction keeps the prior's redistributability)",
        )
    if prior["derivative_permitted"] != corr.derivative_permitted:
        return (
            "refused",
            f"derivative_permitted change on a resolved record: "
            f"{prior['derivative_permitted']!r} -> {corr.derivative_permitted!r}",
        )
    if prior["spdx"] != corr.spdx:
        return (
            "correct",
            f"identifier normalisation {prior['spdx']!r} -> {corr.spdx!r} "
            "(declared in spdx_aliases; the same licence text, ADR-194)",
        )
    return "correct", None


# --------------------------------------------------------------------------- #
# Spine writes — insert-only                                                  #
# --------------------------------------------------------------------------- #


def _ensure_corrected_record(conn: Any, corr: AttributionCorrection) -> str:
    """The corrected rights_record for this source — insert once, reuse after."""
    row = conn.execute(
        "SELECT rights_id FROM rights_record "
        "WHERE spdx_expression = %s AND attribution_text IS NOT DISTINCT FROM %s "
        "AND terms_url IS NOT DISTINCT FROM %s AND redistributable = %s "
        "AND derivative_permitted = %s AND reviewed_by IS NOT DISTINCT FROM %s "
        "ORDER BY rights_id LIMIT 1",
        (
            corr.spdx,
            corr.attribution,
            corr.terms_url,
            corr.redistributable,
            corr.derivative_permitted,
            corr.reviewed_by,
        ),
    ).fetchone()
    if row is not None:
        return str(row[0])
    inserted = conn.execute(
        "INSERT INTO rights_record"
        "(spdx_expression, attribution_text, redistributable, derivative_permitted,"
        " terms_url, reviewed_by, reviewed_at, retrieval_date) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING rights_id",
        (
            corr.spdx,
            corr.attribution,
            corr.redistributable,
            corr.derivative_permitted,
            corr.terms_url,
            corr.reviewed_by,
            f"{corr.reviewed_on.isoformat()}T00:00:00Z",
            corr.retrieval_date,
        ),
    ).fetchone()
    assert inserted is not None
    return str(inserted[0])


def _insert_correction_decision(
    conn: Any,
    corr: AttributionCorrection,
    rights_id: str,
    prior_rights_id: str,
    terms_capture_id: str | None,
) -> tuple[str, bool]:
    """Append one decision row; idempotent on (source, prior, resolved)."""
    existing = conn.execute(
        "SELECT decision_id FROM rights_decision "
        "WHERE source_id = %s AND prior_rights_id = %s AND rights_id = %s "
        "ORDER BY decided_at DESC, decision_id DESC LIMIT 1",
        (corr.source_id, prior_rights_id, rights_id),
    ).fetchone()
    if existing is not None:
        return str(existing[0]), False
    inserted = conn.execute(
        "INSERT INTO rights_decision"
        "(source_id, rights_id, prior_rights_id, basis, reviewer, review_packet,"
        " terms_url, terms_capture_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
        " RETURNING decision_id",
        (
            corr.source_id,
            rights_id,
            prior_rights_id,
            corr.basis,
            corr.reviewed_by,
            corr.review_packet,
            corr.terms_url,
            terms_capture_id,
        ),
    ).fetchone()
    assert inserted is not None
    return str(inserted[0]), True


def plan_corrections(conn: Any, corrections: list[AttributionCorrection]) -> dict[str, Any]:
    """The deterministic dry-run plan (read-only): priors, classification, counts.

    A ``refused`` prior is reported, not applied — the apply path refuses the
    whole run when any refusal is present (fail closed, never a partial silent
    relicense).
    """
    per_source: list[dict[str, Any]] = []
    refused: list[str] = []
    for corr in corrections:
        priors = _source_priors(conn, corr.source_id)
        entries: list[dict[str, Any]] = []
        for rid in sorted(priors):
            kind, reason = _classify_prior(corr, priors[rid])
            entries.append(
                {
                    "prior_rights_id": rid,
                    "kind": kind,
                    "reason": reason,
                    "claims_affected": _claims_affected(conn, corr.source_id, rid),
                    "artifacts_affected": _artifacts_affected(conn, corr.source_id, rid),
                }
            )
            if kind == "refused":
                refused.append(f"{corr.source_id} prior {rid}: {reason}")
        per_source.append(
            {
                "source_id": corr.source_id,
                "spdx": corr.spdx,
                "attribution": corr.attribution,
                "terms_url": corr.terms_url,
                "priors": entries,
                "decisions_would_write": sum(
                    1 for e in entries if e["kind"] in ("correct", "lift")
                ),
                "claims_affected": sum(
                    e["claims_affected"] for e in entries if e["kind"] in ("correct", "lift")
                ),
            }
        )
    return {
        "mode": "plan",
        "sources": per_source,
        "totals": {
            "sources": len(per_source),
            "decisions_would_write": sum(s["decisions_would_write"] for s in per_source),
            "claims_affected": sum(s["claims_affected"] for s in per_source),
        },
        "refused": refused,
    }


def apply_correction(
    conn: Any,
    corr: AttributionCorrection,
    *,
    terms_capture_id: str | None = None,
) -> dict[str, Any]:
    """Record one source's correction: corrected record + decision row(s).

    INSERT-only — ``rights_record``/``rights_decision`` ``INSERT``s plus the
    idempotent existence reads. A ``refused`` prior aborts the source (and, via
    the caller's transaction, the run) BEFORE any write for that source.
    """
    problems = validate_correction(corr)
    if problems:
        raise AttributionCorrectionError(f"{corr.source_id}: " + "; ".join(problems))
    priors = _source_priors(conn, corr.source_id)
    refusals = [
        f"prior {rid}: {reason}"
        for rid in sorted(priors)
        for kind, reason in [_classify_prior(corr, priors[rid])]
        if kind == "refused"
    ]
    if refusals:
        raise AttributionCorrectionError(
            f"{corr.source_id}: the corrections row would relicense resolved "
            "record(s); refused (ADR-194):\n  " + "\n  ".join(refusals)
        )
    rights_id = _ensure_corrected_record(conn, corr)
    decisions: list[dict[str, Any]] = []
    for rid in sorted(priors):
        kind, _reason = _classify_prior(corr, priors[rid])
        if kind in ("noop", "refused"):
            continue
        decision_id, inserted = _insert_correction_decision(
            conn, corr, rights_id, rid, terms_capture_id
        )
        decisions.append(
            {
                "decision_id": decision_id,
                "prior_rights_id": rid,
                "kind": kind,
                "inserted": inserted,
                "claims_affected": _claims_affected(conn, corr.source_id, rid),
                "artifacts_affected": _artifacts_affected(conn, corr.source_id, rid),
            }
        )
    return {
        "source_id": corr.source_id,
        "spdx": corr.spdx,
        "rights_id": rights_id,
        "decisions": decisions,
        "decisions_inserted": sum(1 for d in decisions if d["inserted"]),
        "claims_affected": sum(d["claims_affected"] for d in decisions),
    }


def apply_corrections(
    conn: Any,
    corrections: list[AttributionCorrection],
    *,
    terms_captures: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Apply the whole committed list inside the caller's transaction.

    Plans first so a refused row anywhere aborts before the first write (the
    transaction rolls back whole — never a partial apply).
    """
    plan = plan_corrections(conn, corrections)
    if plan["refused"]:
        raise AttributionCorrectionError(
            "corrections refused (ADR-194 — a licence change on a resolved "
            "record is not an attribution correction):\n  " + "\n  ".join(plan["refused"])
        )
    reports = [
        apply_correction(conn, corr, terms_capture_id=(terms_captures or {}).get(corr.source_id))
        for corr in corrections
    ]
    return {
        "mode": "apply",
        "sources": reports,
        "totals": {
            "sources": len(reports),
            "decisions_inserted": sum(r["decisions_inserted"] for r in reports),
            "claims_affected": sum(r["claims_affected"] for r in reports),
        },
    }


def empty_attribution_count(conn: Any, source_ids: list[str] | None = None) -> int:
    """Claims whose EFFECTIVE record carries no attribution (the defect count).

    The effective record is the latest ``rights_decision`` matching
    ``(source_id, prior_rights_id)``, else the recorded record — the same rule
    the export/API readers apply. Run before and after an apply for the
    pre/post numbers the hosted leg records (the licence-level
    ``attribution_required`` fact lives in ``licenses.toml``; an empty
    attribution on ANY record is the spine-side defect signal this counts).
    """
    rows = conn.execute(
        "SELECT count(DISTINCT c.claim_id) FROM claim c"
        " JOIN claim_evidence ce ON ce.claim_id = c.claim_id AND ce.role = 'establishes'"
        " JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        " JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        " LEFT JOIN (SELECT DISTINCT ON (rd.source_id, rd.prior_rights_id)"
        "          rd.source_id, rd.prior_rights_id, rd.rights_id"
        "    FROM rights_decision rd"
        "   ORDER BY rd.source_id, rd.prior_rights_id, rd.decided_at DESC, rd.decision_id DESC"
        " ) ld ON ld.source_id = ea.source_id AND ld.prior_rights_id = c.rights_id"
        " JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE (rr.attribution_text IS NULL OR btrim(rr.attribution_text) = '')"
        + ("   AND ea.source_id = ANY(%s)" if source_ids else ""),
        (source_ids,) if source_ids else (),
    ).fetchone()
    return 0 if rows is None else int(rows[0])


__all__ = [
    "CORRECTIONS_SCHEMA",
    "AttributionCorrection",
    "AttributionCorrectionError",
    "apply_correction",
    "apply_corrections",
    "empty_attribution_count",
    "load_corrections",
    "plan_corrections",
    "validate_correction",
]

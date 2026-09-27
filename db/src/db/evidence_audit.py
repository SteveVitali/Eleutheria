# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Read-only audit rows for the legacy evidence audit (P32.6, SIG-TRUST-007).

This module is the **loader half** of ``evidence-audit/1`` (ADR-125): it emits
plain ``dict`` rows describing every selected claim's evidence lineage —

    claim → claim_evidence (binding) → evidence_capture → evidence_artifact
          → ingest_run + rights_record + source_registry

— plus the ``ingest_run_capture`` marks that attest each acquisition occurrence,
a spine watermark fingerprinting the audited input, and each claim's current
publication eligibility through the **shared** P32.5 fragment
(:func:`db.dispositions.claim_eligible_sql` — reused, never re-derived).

It **writes nothing**. Every function takes an already-open psycopg connection,
runs SELECTs only, and returns JSON-serializable dicts (datetimes → ISO-8601
strings, uuids → str). ``ops.evidence_audit`` groups the rows into audit units
and applies the pure classification; keeping the SQL here, next to the schema it
reads, means one file changes when the spine changes.

Row shape contract (``audit-rows/1``): each row is one *binding sighting* — a
claim joined to one ``claim_evidence`` link — plus the claim-level columns
repeated. Rows with ``capture_id IS NULL`` carry ``None`` in every ``capture_*``
column (a claim with no evidence link still appears; it is ``unrecoverable``
evidence, not a missing claim). :func:`load_claim_rows` pages keyset-style on
``claim_id`` so a hosted run reads bounded chunks and can resume after an
interruption.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from . import dispositions
from .occurrences import ESTABLISHING_ROLE

#: Version stamped on every loader result; the audit report records it so a
#: re-run compares against the same row contract (ADR-125).
AUDIT_ROW_VERSION = "evidence-audit-rows/1"

#: One claim×binding row: every claim-level column the classifier needs, plus
#: the claim_evidence link columns (P32.2 typed binding surface), the capture
#: occurrence columns (P32.2 occurrence ids), the artifact's provenance, the
#: asserting run's identity, and the rights row the claim is compartmented
#: under. Read-only by construction — SELECT over append-only tables only.
_CLAIM_ROWS = (
    "SELECT c.claim_id::text, c.predicate_id, c.subject_id::text,"
    " c.object_entity::text, c.object_type, c.value_kind::text, c.value_text,"
    " c.raw_value, c.content_digest AS claim_digest, c.observed_at,"
    " c.extraction_id::text AS claim_extraction_id,"
    " c.ingest_run_id::text, c.sensitivity_tier, c.review_status::text,"
    " ce.capture_id::text, ce.extraction_id::text AS binding_extraction_id,"
    " ce.role, ce.locator, ce.extraction_config_digest, ce.extractor_version,"
    " ce.binding_status, ce.bound_at,"
    " ec.capture_classification, ec.content_digest AS capture_digest,"
    " ec.byte_size, ec.media_type, ec.ocfl_object_id, ec.ocfl_version,"
    " ec.storage_tier, ec.retrieved_at, ec.retrieved_by_run_id::text,"
    " ec.source_uri AS capture_source_uri,"
    " ea.artifact_id::text, ea.source_id, ea.url AS artifact_url,"
    " ea.stable_locator, ea.artifact_type, ea.acquisition_method,"
    " ea.capture_status,"
    " r.connector_name, r.connector_version, r.code_commit, r.is_replay,"
    " r.started_at AS run_started_at,"
    " rr.spdx_expression, rr.redistributable, rr.derivative_permitted,"
    " rr.retrieval_date AS rights_retrieval_date,"
    " ex.extractor_name AS extraction_extractor_name,"
    " ex.extractor_version AS extraction_extractor_version,"
    " ex.method AS extraction_method "
    "FROM claim c"
    " JOIN ingest_run r ON r.run_id = c.ingest_run_id"
    " JOIN rights_record rr ON rr.rights_id = c.rights_id"
    " LEFT JOIN claim_evidence ce ON ce.claim_id = c.claim_id"
    " LEFT JOIN evidence_capture ec ON ec.capture_id = ce.capture_id"
    " LEFT JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id"
    " LEFT JOIN extraction ex ON ex.extraction_id = ce.extraction_id"
    " WHERE (%(after)s::uuid IS NULL OR c.claim_id > %(after)s::uuid)"
    "   AND (%(ids)s::uuid[] IS NULL OR c.claim_id = ANY(%(ids)s::uuid[]))"
    " ORDER BY c.claim_id, ce.capture_id, ce.role"
    " LIMIT %(limit)s"
)

#: The occurrence marks attesting an acquisition (P31.4/P32.2): run, target,
#: state, recorded digest and the pinned OCFL occurrence. One digest may carry
#: several marks (re-sightings of identical bytes; a resumed execution's
#: re-flush) — the audit reads them ALL, never dedups by run alone.
_MARK_ROWS = (
    "SELECT run_id::text, target_key, state, capture_digest, source_uri,"
    " media_type, byte_size, retrieved_at, records, ocfl_object_id, ocfl_version,"
    " recorded_at "
    "FROM ingest_run_capture WHERE capture_digest = ANY(%s::text[])"
    " ORDER BY capture_digest, recorded_at"
)


def _jsonable(value: Any) -> Any:
    """Render a psycopg cell JSON-serializable (timestamptz/uuid/date → str)."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    return value


def row_to_dict(columns: Any, row: Any) -> dict[str, Any]:
    """One SELECT row → ``{column_name: jsonable_value}``."""
    return {
        col.name if hasattr(col, "name") else col[0]: _jsonable(val)
        for col, val in zip(columns, row, strict=True)
    }


def load_claim_rows(
    conn: Any,
    *,
    claim_ids: Iterable[str] | None = None,
    chunk_size: int = 10_000,
) -> Iterator[dict[str, Any]]:
    """Yield the audit rows for the selected population, keyset-paged.

    ``claim_ids=None`` selects the whole claim corpus (the census population);
    a caller selecting a bounded population passes the ids its selection
    recorded — the report reconciles every denominator against THAT selection,
    never against an assumed corpus. Paging on ``claim_id`` keeps each read a
    bounded chunk and lets an interrupted hosted run resume at
    ``max(claim_id)`` it already emitted.
    """
    ids = [str(i) for i in claim_ids] if claim_ids is not None else None
    after: str | None = None
    while True:
        cur = conn.execute(_CLAIM_ROWS, {"after": after, "ids": ids, "limit": int(chunk_size)})
        rows = cur.fetchall()
        if not rows:
            return
        for row in rows:
            out = row_to_dict(cur.description, row)
            after = out["claim_id"]
            yield out
        if len(rows) < int(chunk_size):
            return


def load_capture_marks(conn: Any, digests: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
    """Every ``ingest_run_capture`` mark for ``digests``, keyed by digest."""
    wanted = sorted({str(d) for d in digests if d})
    if not wanted:
        return {}
    marks: dict[str, list[dict[str, Any]]] = {d: [] for d in wanted}
    # ANY(...) over the full digest set — marks are small (one row per flushed
    # target per execution); paging them would buy nothing.
    cur = conn.execute(_MARK_ROWS, (wanted,))
    for row in cur.fetchall():
        mark = row_to_dict(cur.description, row)
        marks.setdefault(str(mark["capture_digest"]), []).append(mark)
    return marks


def load_claim_eligibility(conn: Any, claim_ids: Iterable[str]) -> set[str]:
    """The sampled claims currently *publicly eligible* under `publication-eligibility/1`.

    Pure reuse: :func:`db.dispositions.eligible_claim_ids` evaluates the shared
    ``claim_eligible_sql`` fragment — the audit NEVER re-derives the policy.
    A fixture/offline input supplies ``publication_eligible`` per unit instead.
    """
    return dispositions.eligible_claim_ids(conn.cursor(), [str(i) for i in claim_ids])


def spine_watermark(conn: Any) -> dict[str, Any]:
    """A fingerprint of the audited spine, recorded on the report for replayability.

    Counts are denominators a re-run compares against; maxima are the observation
    watermark (anything newer than them was not in this audit's input).
    """

    def _one(sql: str) -> Any:
        return _jsonable(conn.execute(sql).fetchone())

    # claim.sys_period is T5 — the DB-controlled transaction time (append-only
    # spine; the lower bound is the recorded assertion time).
    claims = _one("SELECT count(*), max(lower(sys_period)) FROM claim")
    bindings = _one(
        "SELECT count(*), max(bound_at),"
        f" count(*) FILTER (WHERE role = '{ESTABLISHING_ROLE}') FROM claim_evidence"
    )
    captures = _one(
        "SELECT count(*), max(retrieved_at),"
        " count(*) FILTER (WHERE capture_classification = 'actual'),"
        " count(*) FILTER (WHERE capture_classification = 'synthetic'),"
        " count(*) FILTER (WHERE capture_classification = 'legacy')"
        " FROM evidence_capture"
    )
    marks = _one("SELECT count(*), max(recorded_at) FROM ingest_run_capture")
    disposition_rows = _one("SELECT count(*), max(decided_at) FROM publication_disposition")
    runs = _one("SELECT count(*), max(started_at) FROM ingest_run")
    return {
        "claims": {"count": claims[0], "max_asserted_at": claims[1]},
        "claim_evidence": {
            "count": bindings[0],
            "max_bound_at": bindings[1],
            "establishing": bindings[2],
        },
        "evidence_capture": {
            "count": captures[0],
            "max_retrieved_at": captures[1],
            "actual": captures[2],
            "synthetic": captures[3],
            "legacy": captures[4],
        },
        "ingest_run_capture": {"count": marks[0], "max_recorded_at": marks[1]},
        "publication_disposition": {
            "count": disposition_rows[0],
            "max_decided_at": disposition_rows[1],
        },
        "ingest_run": {"count": runs[0], "max_started_at": runs[1]},
    }


@dataclass(frozen=True)
class AuditLoad:
    """The loader result bundle handed to ``ops.evidence_audit``."""

    row_version: str = AUDIT_ROW_VERSION
    rows: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    marks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    watermark: dict[str, Any] = field(default_factory=dict)
    eligible_claim_ids: frozenset[str] = frozenset()


def load_audit_input(
    conn: Any,
    *,
    claim_ids: Iterable[str] | None = None,
    chunk_size: int = 10_000,
) -> AuditLoad:
    """Load the complete audit input from an open connection — SELECTs only.

    The caller decides the population (``claim_ids``); everything else follows
    the selection: rows are paged through it, marks are fetched for the capture
    digests the rows actually name, and eligibility is evaluated for exactly the
    selected claims so every denominator reconciles to the input.
    """
    rows = list(load_claim_rows(conn, claim_ids=claim_ids, chunk_size=chunk_size))
    digests = {r["capture_digest"] for r in rows if r.get("capture_digest")}
    marks = load_capture_marks(conn, digests)
    ids = sorted({r["claim_id"] for r in rows})
    eligible = load_claim_eligibility(conn, ids) if ids else set()
    return AuditLoad(
        rows=tuple(rows),
        marks=marks,
        watermark=spine_watermark(conn),
        eligible_claim_ids=frozenset(eligible),
    )


def dump_rows(path: str, load: AuditLoad) -> None:
    """Persist a loaded audit input as the portable ``--input-json`` document.

    The same file feeds ``sig-ops evidence-audit --input-json`` offline — the
    byte-for-byte loader output becomes the reproducible input of record
    (fixture tests build the same shape by hand).
    """
    doc = {
        "row_version": load.row_version,
        "watermark": load.watermark,
        "eligible_claim_ids": sorted(load.eligible_claim_ids),
        "marks": load.marks,
        "rows": list(load.rows),
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, sort_keys=True)
        fh.write("\n")

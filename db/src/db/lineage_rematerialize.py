# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The append-only claim-lineage rematerialization run (P35.25 / R11-L3-CP4;
SIG-CONF-014 — design CP-4, "back-populate the lineage state").

Claims minted before P35.25 carry no ``claim_lineage`` row — their lineage is
unknown, and unknown MUST NOT read as independent corroboration. This run is
the correction machinery:

- it MIRRORS the committed ``sig.source-lineage/1`` declarations artifact
  (``sig-connectors source-lineage-list``) into ``source_lineage`` — one
  immutable row per ``(source_id, registry_version)``;
- it scans current claims lacking a ``claim_lineage`` row (``ORDER BY
  claim_id``, ``--limit``-bounded, ``--batch-size``-committed) and appends one
  lineage row per claim: the claim's source resolved from its establishing
  evidence occurrence (``claim_evidence → evidence_capture →
  evidence_artifact.source_id``), the declaration's namespace/kind/class when
  the source declares one, else the explicit ``undeclared``/``unclassified``
  state with ``basis = 'undeclared'``;
- recoverable derivation ancestry is back-populated: the claim row's own
  ``derived_from_claim_ids`` is copied onto the lineage row (the claim row
  itself is never UPDATEd — append-only, P1–P3);
- a claim whose source cannot be resolved to exactly one source is recorded
  ``undeclared`` — ancestry is never guessed;
- ``INSERT … ON CONFLICT DO NOTHING`` makes a re-run ``+0``; per-batch
  transactions make an interrupted run resume where it stopped (a claim with
  a row is simply no longer pending).

The ``live_verification=false`` half lands the machinery only: the hosted
apply run is queued under OM-19/OM-20 — the operator runs ``--apply``; this
module never presumes that happened.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .lineage import UNCLASSIFIED, UNDECLARED, valid_namespace_token

#: The report artifact id stamped on every run report.
REPORT_ARTIFACT = "sig.lineage-rematerialize/1"
#: The declaration artifact schema ``load_declarations`` requires.
DECLARATIONS_SCHEMA = "sig.source-lineage/1"

_KINDS = frozenset({"primary", "mirror", "derived", "syndicated", "undeclared"})


@dataclass(frozen=True)
class Declaration:
    """One ``sig.source-lineage/1`` row (the control surface for the run)."""

    source_id: str
    kind: str
    origin: str
    mirror_of: str
    derived_from: tuple[str, ...]
    independence_class: str
    id_namespace: str
    collection_method: str
    evidence: str


def load_declarations(path: str | Path) -> tuple[dict[str, Declaration], str]:
    """Fail-closed load of the committed declarations artifact.

    Returns ``(source_id -> Declaration, registry_version)``. A malformed
    artifact — wrong schema, a non-declared kind, an invalid namespace token,
    a missing field — raises before the DB is ever opened.
    """
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(doc, dict) or doc.get("schema") != DECLARATIONS_SCHEMA:
        raise ValueError(
            f"{path}: not a {DECLARATIONS_SCHEMA} artifact (schema {doc.get('schema')!r})"
        )
    registry_version = str(doc.get("registry_version") or "")
    if not registry_version:
        raise ValueError(f"{path}: missing registry_version")
    out: dict[str, Declaration] = {}
    for i, row in enumerate(doc.get("sources") or ()):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: sources[{i}] is not a table")
        try:
            decl = Declaration(
                source_id=str(row["source_id"]),
                kind=str(row["kind"]),
                origin=str(row.get("origin", "")),
                mirror_of=str(row.get("mirror_of", "")),
                derived_from=tuple(str(u) for u in (row.get("derived_from") or ())),
                independence_class=str(row["independence_class"]),
                id_namespace=str(row["id_namespace"]),
                collection_method=str(row.get("collection_method", "")),
                evidence=str(row.get("evidence", "")),
            )
        except (KeyError, TypeError) as exc:
            raise ValueError(f"{path}: sources[{i}] malformed: {exc}") from exc
        if decl.kind not in _KINDS:
            raise ValueError(
                f"{path}: {decl.source_id!r} kind {decl.kind!r} not in {sorted(_KINDS)}"
            )
        if not decl.independence_class:
            raise ValueError(
                f"{path}: {decl.source_id!r} has no resolved independence_class — "
                "unresolvable lineage is 'unclassified', never empty"
            )
        if not valid_namespace_token(decl.id_namespace):
            raise ValueError(
                f"{path}: {decl.source_id!r} id_namespace {decl.id_namespace!r} is not a "
                "declared namespace (db/data/id_namespaces.toml or src:<source-id>)"
            )
        if decl.source_id in out:
            raise ValueError(f"{path}: duplicate declaration for {decl.source_id!r}")
        out[decl.source_id] = decl
    return out, registry_version


#: Current claims carrying no lineage row — the pending set. Ordered by
#: claim_id so a --limit bound and a resumed run are deterministic.
_PENDING_SQL = (
    "SELECT c.claim_id::text, c.derived_from_claim_ids::text[] "
    "  FROM claim c "
    "  LEFT JOIN claim_lineage cl ON cl.claim_id = c.claim_id "
    " WHERE cl.claim_id IS NULL AND upper_inf(c.sys_period) "
    "   AND c.claim_id > %s::uuid "  # keyset cursor — deterministic resume
    " ORDER BY c.claim_id "
    " LIMIT %s"
)

#: A claim's source resolves through its establishing occurrences: exactly
#: one distinct evidence-artifact source id. Zero or several sources are both
#: honest-undeclared states — a claim is never GUESSED a source.
_SOURCE_SQL = (
    "SELECT ce.claim_id::text, ea.source_id "
    "  FROM claim_evidence ce "
    "  JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
    "  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
    " WHERE ce.claim_id = ANY(%s::uuid[]) AND ce.role = 'establishes'"
)

_INSERT_CLAIM_LINEAGE = (
    "INSERT INTO claim_lineage"
    "(claim_id, source_id, id_namespace, lineage_kind, independence_class,"
    " basis, derived_from_claim_ids) "
    "VALUES (%s::uuid, %s, %s, %s, %s, %s, %s::uuid[]) "
    "ON CONFLICT (claim_id) DO NOTHING"
)

#: Mirror the artifact's rows into the versioned declaration table — the
#: (source_id, registry_version) key makes the mirror idempotent; a source the
#: registry table does not know is reported ``skipped``, never failed.
_INSERT_SOURCE_LINEAGE = (
    "INSERT INTO source_lineage"
    "(source_id, registry_version, kind, origin, mirror_of, derived_from,"
    " independence_class, id_namespace, collection_method, evidence) "
    "SELECT %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s "
    " WHERE EXISTS (SELECT 1 FROM source_registry WHERE source_id = %s) "
    "ON CONFLICT (source_id, registry_version) DO NOTHING"
)


def _resolve_sources(conn: Any, claim_ids: list[str]) -> dict[str, set[str]]:
    """claim_id -> the distinct establishing-source ids it evidences."""
    per_claim: dict[str, set[str]] = {cid: set() for cid in claim_ids}
    if not claim_ids:
        return per_claim
    for row in conn.execute(_SOURCE_SQL, (claim_ids,)).fetchall():
        if row["source_id"]:
            per_claim[str(row["claim_id"])].add(str(row["source_id"]))
    return per_claim


def _lineage_for(
    claim_id: str, source_ids: set[str], decls: dict[str, Declaration], basis: str
) -> tuple[str, str, str, str, str]:
    """The (source_id, id_namespace, kind, independence_class, basis) values one
    pending claim's lineage row records — declared when the source resolves to
    exactly one declared source, explicit ``undeclared`` otherwise."""
    if len(source_ids) != 1:
        return (UNDECLARED, UNDECLARED, "undeclared", UNCLASSIFIED, UNDECLARED)
    source = next(iter(source_ids))
    decl = decls.get(source)
    if decl is None or decl.kind == "undeclared":
        # A resolvable source with no declaration is still undeclared — the
        # source id is recorded (it's evidence-derived, not guessed) while the
        # lineage state stays honestly undeclared.
        return (source, UNDECLARED, "undeclared", UNCLASSIFIED, UNDECLARED)
    return (source, decl.id_namespace, decl.kind, decl.independence_class, basis)


def run(
    dsn: str,
    *,
    declarations: str | Path,
    apply_mode: bool = False,
    limit: int | None = None,
    batch_size: int = 1_000,
) -> dict[str, Any]:
    """Plan (default) or apply the claim-lineage backfill.

    Returns the ``sig.lineage-rematerialize/1`` report: mirrored declaration
    counts plus per-batch pending/processed/written totals. Dry-run touches
    nothing; apply is per-batch transactions so an interrupted run resumes.
    """
    import psycopg
    from psycopg.rows import dict_row

    decls, registry_version = load_declarations(declarations)
    basis = f"rematerialize:{registry_version}"
    report: dict[str, Any] = {
        "artifact": REPORT_ARTIFACT,
        "mode": "apply" if apply_mode else "plan",
        "registry_version": registry_version,
        "declarations": {
            "total": len(decls),
            "declared": sum(1 for d in decls.values() if d.kind != "undeclared"),
            "unclassified": sum(1 for d in decls.values() if d.independence_class == UNCLASSIFIED),
        },
        "totals": {
            "claims_scanned": 0,
            "lineage_rows_planned": 0,
            "lineage_rows_written": 0,
            "ancestry_recovered": 0,
            "declared": 0,
            "undeclared_source": 0,
            "unresolvable_source": 0,
            "source_lineage_mirrored": 0,
            "source_lineage_skipped_unregistered": 0,
        },
        "batches": [],
    }
    with psycopg.connect(dsn, autocommit=False, row_factory=dict_row) as conn:
        if apply_mode:
            # Mirror the declared lineage into the versioned table first —
            # readers resolve through source_lineage_current.
            for decl in decls.values():
                row = conn.execute(
                    _INSERT_SOURCE_LINEAGE,
                    (
                        decl.source_id,
                        registry_version,
                        decl.kind,
                        decl.origin,
                        decl.mirror_of,
                        json.dumps(list(decl.derived_from)),
                        decl.independence_class,
                        decl.id_namespace,
                        decl.collection_method,
                        decl.evidence,
                        decl.source_id,
                    ),
                )
                if row.rowcount:
                    report["totals"]["source_lineage_mirrored"] += row.rowcount
                else:
                    # Distinguish a prior-version conflict from an unregistered
                    # source: the row is absent only when the source isn't in
                    # source_registry (or the same version already landed).
                    present = conn.execute(
                        "SELECT 1 FROM source_lineage WHERE source_id = %s "
                        "AND registry_version = %s",
                        (decl.source_id, registry_version),
                    ).fetchone()
                    if present is None:
                        report["totals"]["source_lineage_skipped_unregistered"] += 1
            conn.commit()

        scanned = 0
        cursor = "00000000-0000-0000-0000-000000000000"  # keyset start
        while True:
            remaining = (limit - scanned) if limit is not None else batch_size
            take = min(remaining, batch_size)
            if take <= 0:
                break
            batch = conn.execute(_PENDING_SQL, (cursor, take)).fetchall()
            if not batch:
                break
            cursor = str(batch[-1]["claim_id"])
            scanned += len(batch)
            sources = _resolve_sources(conn, [r["claim_id"] for r in batch])
            stats = {"claims": len(batch), "written": 0}
            with conn.transaction():
                for r in batch:
                    claim_id = str(r["claim_id"])
                    source_ids = sources.get(claim_id, set())
                    src, ns, kind, cls, row_basis = _lineage_for(claim_id, source_ids, decls, basis)
                    ancestry = r.get("derived_from_claim_ids") or None
                    if apply_mode:
                        conn.execute(
                            _INSERT_CLAIM_LINEAGE,
                            (claim_id, src, ns, kind, cls, row_basis, ancestry),
                        )
                    stats["written"] += 1
                    if ancestry:
                        report["totals"]["ancestry_recovered"] += 1
                    if kind != "undeclared":
                        report["totals"]["declared"] += 1
                    elif src != UNDECLARED:
                        report["totals"]["undeclared_source"] += 1
                    else:
                        report["totals"]["unresolvable_source"] += 1
            report["totals"]["claims_scanned"] += stats["claims"]
            key = "lineage_rows_written" if apply_mode else "lineage_rows_planned"
            report["totals"][key] += stats["written"]
            report["batches"].append(stats)
            if limit is not None and scanned >= limit:
                break
            if len(batch) < take:
                break
        if apply_mode:
            conn.commit()
        else:
            conn.rollback()
        return report


__all__ = [
    "DECLARATIONS_SCHEMA",
    "REPORT_ARTIFACT",
    "Declaration",
    "load_declarations",
    "run",
]

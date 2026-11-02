# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.75 (R11-ACQ-30) — the append-only ``configured_access`` share-list write.

The hosted half of the Flock share-list row (D-K2-4 + OD-24 [A-22] = yes / b):
the screened, organisation-level ``configured_sharing_partner`` claims the
builder emits (``connectors.flock_share_lists``) land in the claim spine
through :class:`PgClaimSink` — INSERT-only, chunk-committed, ``ON CONFLICT``
idempotent — bound to the EXISTING evidence capture whose content digest the
input bytes re-derive byte-for-byte. The mirror snapshot's
``content_digest`` match is the binding check: a supplied snapshot that is
not the stored capture refuses before a single claim is considered (SIG-ENG-
042 — the write derives from stored evidence, never from a file someone
hands it).

Mirroring the P35.15b split: this module owns the spine-write machinery
(plan → apply → read-back, ``is_replay`` so links classify ``replayed``);
``sig-connectors flock-share-lists`` owns the emit path (the screen +
builder + feed). Dry-run by default — nothing is written until ``apply``
runs inside the OM-20 window (the GATE-G5 §4 list names P36.75 verbatim,
expires GATE-G6); restore point = the written claim set's digest list the
report records.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import psycopg

from .claim_sink import DEFAULT_COMMIT_CHUNK_SIZE, PgClaimSink
from .technology_backfill import CaptureRow

CONNECTOR_NAME = "flock-share-lists"
CONNECTOR_VERSION = "1.0.0"
PREDICATE = "configured_sharing_partner"
EVIDENCE_GENRE = "portal_snapshot"
_SUBJECT_SCHEME = "sig.connector.subject"

_CAPTURES_BY_DIGEST = (
    "SELECT ec.capture_id::text, ec.retrieved_at, ec.content_digest, "
    "ec.byte_size, ec.media_type, ec.ocfl_object_id, ec.ocfl_version, "
    "ec.retrieved_by_run_id::text, ec.capture_classification, "
    "ea.stable_locator, ea.source_id "
    "FROM evidence_capture ec "
    "JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
    "WHERE ec.content_digest = %s AND ea.source_id = %s "
    "ORDER BY ec.retrieved_at DESC NULLS LAST, ec.capture_id"
)
_EXISTING_EDGES = (
    "SELECT i.value AS subject_key, c.value_text AS to_org "
    "FROM claim c "
    "JOIN entity_identity_key i ON i.entity_id = c.subject_id "
    "AND i.scheme = %s "
    "WHERE c.predicate_id = %s AND i.value = ANY(%s::text[])"
)
_REGISTERED = (
    "SELECT (SELECT count(*) FROM vocab_predicate WHERE predicate_id = %s), "
    "(SELECT count(*) FROM vocab_artifact_genre WHERE genre_id = %s)"
)


@dataclass
class ShareUnit:
    """One evidence unit: the claims built from one screened input document."""

    source_id: str
    #: Base32 multihash of the input bytes — must equal a stored capture's
    #: ``content_digest`` for the unit to bind (fail-closed provenance).
    input_digest: str
    byte_size: int
    media_type: str
    claims: list[dict[str, Any]] = field(default_factory=list)
    feed_digest: str | None = None
    screened_portals: int = 0
    refused_portals: int = 0
    bound: CaptureRow | None = None


@dataclass
class WritePlan:
    """What a dry run reports and what ``--apply`` executes."""

    units: list[ShareUnit] = field(default_factory=list)
    existing_edges: set[tuple[str, str]] = field(default_factory=set)
    registered: dict[str, bool] = field(default_factory=dict)

    def report(self) -> dict[str, Any]:
        pending = sum(len(u.claims) for u in self.units if u.bound is not None)
        unbound = sum(len(u.claims) for u in self.units if u.bound is None)
        already = sum(
            1
            for u in self.units
            for c in u.claims
            if (str(c.get("subject_id")), str(c.get("value"))) in self.existing_edges
        )
        return {
            "mode": "plan",
            "connector": CONNECTOR_NAME,
            "predicate": PREDICATE,
            "registered": self.registered,
            "units": [
                {
                    "source_id": u.source_id,
                    "input_digest": u.input_digest,
                    "bindable": u.bound is not None,
                    "claims": len(u.claims),
                    "screened_portals": u.screened_portals,
                    "refused_portals": u.refused_portals,
                    "feed_digest": u.feed_digest,
                }
                for u in self.units
            ],
            "claims_total": sum(len(u.claims) for u in self.units),
            "claims_pending": pending,
            "claims_unbound_no_evidence": unbound,
            "edges_already_claimed": already,
            "claim_set_digest": _claim_set_digest(c for u in self.units for c in u.claims),
        }


def _claim_set_digest(claims: Any) -> str:
    """The sha256 over the sorted per-claim digests — the restore record.

    Uses the sink's own identity function so the set pin matches what the
    written rows carry modulo the extraction-binding seal (SIG-INGEST-004).
    """
    from .claim_sink import content_digest

    digests = sorted(content_digest(dict(c)) for c in claims)
    return hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()


def _captures_for(conn: Any, unit: ShareUnit) -> list[CaptureRow]:
    rows: list[CaptureRow] = []
    for row in conn.execute(_CAPTURES_BY_DIGEST, (unit.input_digest, unit.source_id)).fetchall():
        rows.append(
            CaptureRow(
                capture_id=str(row[0]),
                retrieved_at=row[1],
                content_digest=None if row[2] is None else str(row[2]),
                byte_size=row[3],
                media_type=None if row[4] is None else str(row[4]),
                ocfl_object_id=None if row[5] is None else str(row[5]),
                ocfl_version=None if row[6] is None else str(row[6]),
                retrieved_by_run_id=None if row[7] is None else str(row[7]),
                classification=None if row[8] is None else str(row[8]),
                stable_locator=None if row[9] is None else str(row[9]),
                artifact_source_id=None if row[10] is None else str(row[10]),
            )
        )
    return rows


def plan_write(conn: Any, units: Sequence[ShareUnit]) -> WritePlan:
    """Compute the write plan — the dry-run and ``--apply`` share this read.

    Per unit the plan resolves the stored ``evidence_capture`` whose
    ``content_digest`` equals the input's multihash under the unit's source —
    a supplied document that was never captured binds to nothing and its
    claims count ``unbound_no_evidence`` (never written: §16 — no claim
    without an evidence link).
    """
    row = conn.execute(_REGISTERED, (PREDICATE, EVIDENCE_GENRE)).fetchone()
    assert row is not None
    plan = WritePlan(
        registered={
            "configured_sharing_partner_predicate": bool(row[0]),
            "portal_snapshot_genre": bool(row[1]),
        }
    )
    keys = sorted(
        {str(c.get("subject_id")) for u in units for c in u.claims if c.get("subject_id")}
    )
    if keys:
        for subject_key, to_org in conn.execute(
            _EXISTING_EDGES, (_SUBJECT_SCHEME, PREDICATE, keys)
        ).fetchall():
            plan.existing_edges.add((str(subject_key), str(to_org)))
    for unit in units:
        captures = _captures_for(conn, unit)
        unit.bound = next((c for c in captures if c.bindable_for(unit.source_id)), None)
        plan.units.append(unit)
    return plan


def apply_plan(
    conn: Any,
    plan: WritePlan,
    *,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    rights_resolver: Any = None,
) -> dict[str, Any]:
    """Execute ``plan`` append-only through :class:`PgClaimSink`.

    Each bound unit's claims write in one ``assert_claims(capture=…)`` call —
    chunked commits inside, ``is_replay`` so the links classify ``replayed``
    (the write re-reads stored bytes). A re-run dedupes on ``content_digest``
    → +0. Claims on unbound units are never written (no evidence, no claim).
    """
    report = plan.report()
    report["mode"] = "apply"
    pending = [u for u in plan.units if u.bound is not None and u.claims]
    if pending and not all(plan.registered.values()):
        report["refused"] = (
            "closed-vocabulary gate: `configured_sharing_partner` predicate and "
            "`portal_snapshot` genre must be registered before --apply"
        )
        return report
    sink = PgClaimSink(
        conn,
        connector_name=CONNECTOR_NAME,
        connector_version=CONNECTOR_VERSION,
        code_commit=code_commit,
        is_replay=True,
        commit_chunk_size=commit_chunk_size or DEFAULT_COMMIT_CHUNK_SIZE,
        rights_resolver=rights_resolver,
        extra_parameters={"ticket": "P36.75", "manifest_row": "385", "write": "share-lists"},
    )
    bound_units = 0
    for unit in pending:
        sink.assert_claims(unit.claims, capture=unit.bound.binding() if unit.bound else None)
        bound_units += 1
    # Honest read-back: recount the planned edge keys now claimed.
    now = 0
    for u in plan.units:
        for c in u.claims:
            if (str(c.get("subject_id")), str(c.get("value"))) in plan.existing_edges:
                now += 1
    sink.record_completion(
        "ok",
        detail=(
            f"P36.75 share-list write: units={bound_units} "
            f"inserted={sink.report.inserted} duplicates={sink.report.duplicates} "
            f"unbound={sum(len(u.claims) for u in plan.units if u.bound is None)}"
        ),
    )
    report["apply"] = {
        "claims_added": sink.report.inserted,
        "claims_duplicate": sink.report.duplicates,
        "quarantined": sink.report.quarantined,
        "bound_units": bound_units,
        "run_id": sink.run_id,
        "execution_id": sink.execution_id,
        "edge_keys_preexisting": now,
    }
    return report


def run_write(
    dsn: str,
    *,
    units: Sequence[ShareUnit],
    apply: bool = False,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    rights_resolver: Any = None,
) -> dict[str, Any]:
    """Open the DSN, plan, and (only with ``apply=True``) write."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        plan = plan_write(conn, units)
        if not apply:
            return plan.report()
        return apply_plan(
            conn,
            plan,
            code_commit=code_commit,
            commit_chunk_size=commit_chunk_size,
            rights_resolver=rights_resolver,
        )


__all__ = [
    "CONNECTOR_NAME",
    "EVIDENCE_GENRE",
    "PREDICATE",
    "ShareUnit",
    "WritePlan",
    "apply_plan",
    "plan_write",
    "run_write",
]

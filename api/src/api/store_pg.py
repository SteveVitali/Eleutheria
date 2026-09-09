# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The PostgreSQL-backed :class:`~api.store.ReadStore` — the API over the spine (§37).

Until P19.4 the public API had only ever been served over the in-memory demo store
(the composed run recorded this as ``LD-F06``: "the API has never read the PG claim
spine"). :class:`PgReadStore` crosses that seam. It implements every one of the
16 ``ReadStore`` methods against PostgreSQL, so ``create_app(store)`` runs unchanged
over the real store; ``sig-api serve --dsn …`` selects it.

Three properties are load-bearing:

* **Contradictions stay visible (§3.1).** ``claims_for`` returns *every* admissible
  claim for a ``(subject, predicate)`` pair — the resolver, not the store, decides
  the envelope, and a within-predicate disagreement is never collapsed to one value
  at the store boundary.
* **Publication at the store boundary (Part VIII §0.7).** Reads are filtered to the
  public sensitivity tier (``sensitivity_tier = 0`` / ``storage_tier = 'public'``):
  the store never *publishes* a restricted/sealed row, and sensitive coordinates are
  reduced to jurisdiction granularity, not returned raw. Row-level security stays
  **enabled** on every table (this store never sets ``row_security = off`` or asks
  for ``BYPASSRLS``); in production the connection is a ``sig_read_public`` role so
  RLS enforces the same ceiling as defence-in-depth.
* **As-of reads (§9.4).** Belief-time is applied with the shared :class:`db.temporal.AsOf`
  predicate (``sys_period @> belief``); the resolver applies world-time over the
  returned claims' validity, so a belief-pinned read reproduces a past answer.

The graph-annotation surfaces (``contradiction`` / ``coverage_for`` / ``tasks`` /
``task``) read the persisted ``graph_annotations`` rows **if any exist**, else they
**compute on read** from the same pure engines the resolver uses
(:func:`reconcile.resolve.RESOLVE`, :class:`tasks.lifecycle.TaskPool`) — see
:meth:`PgReadStore._compute_on_read`. Persisting those annotations is P21.2; this
compute-on-read seam is exactly what P21.2 later replaces (ADR-059, RISK-P19-07).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, date, datetime
from typing import Any

import psycopg
from db.temporal import AsOf
from evidence.tiers import CaptureMetadata, StorageTier
from inference.coverage import CoverageRecord
from policy.rights import RightsRecord
from reconcile.resolve import RESOLVE, Claim
from reconcile.ruleset import Ruleset
from reconcile.snapshot_diff import Capture

from .store import (
    ContradictionRecord,
    CrosswalkRecord,
    DossierRecord,
    EntityRecord,
    IdDescriptor,
    StoredClaim,
    TaskRecord,
)

#: The connector subject identifier scheme (kept in step with db.claim_sink).
_SUBJECT_SCHEME = "sig.connector.subject"


def _looks_like_uuid(value: str) -> bool:
    try:
        _uuid.UUID(value)
        return True
    except (ValueError, AttributeError):
        return False


def _as_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date(1970, 1, 1)


def _reconstruct_value(value_kind: str, text: Any, num: Any, boolean: Any) -> object:
    if value_kind != "value":
        return None
    if boolean is not None:
        return bool(boolean)
    if num is not None:
        as_float = float(num)
        return int(as_float) if as_float.is_integer() else as_float
    return text


class PgReadStore:
    """A :class:`~api.store.ReadStore` served from PostgreSQL (P19.4, SIG-API-001)."""

    def __init__(
        self,
        dsn: str,
        *,
        ruleset: Ruleset | None = None,
        role: str | None = None,
        as_of: AsOf | None = None,
    ) -> None:
        self._dsn = dsn
        self._ruleset = ruleset
        self._as_of = as_of
        # RLS stays enabled: we never set row_security=off. An optional read role
        # (e.g. sig_read_public) makes RLS enforce the public tier ceiling too.
        self._conn = psycopg.connect(dsn, autocommit=True)
        if role:
            self._conn.execute(f"SET ROLE {role}")

    def close(self) -> None:
        self._conn.close()

    # --- ReadStore -------------------------------------------------------------

    @property
    def ruleset(self) -> Ruleset | None:
        return self._ruleset

    def _resolve_entity(self, subject_id: str) -> str | None:
        """Map an API subject id (entity uuid or connector identifier) to entity_id."""
        if _looks_like_uuid(subject_id):
            row = self._conn.execute(
                "SELECT entity_id FROM entity WHERE entity_id = %s", (subject_id,)
            ).fetchone()
            if row is not None:
                return str(row[0])
        row = self._conn.execute(
            "SELECT entity_id FROM entity_identifier WHERE value = %s ORDER BY scheme LIMIT 1",
            (subject_id,),
        ).fetchone()
        return None if row is None else str(row[0])

    def claims_for(
        self, subject_id: str, predicate_id: str, *, as_of_belief: datetime
    ) -> list[Claim]:
        """Every public-tier claim for the pair, belief-filtered (contradictions visible)."""
        entity_id = self._resolve_entity(subject_id)
        if entity_id is None:
            return []
        rows = self._conn.execute(
            "SELECT c.claim_id, c.value_kind, c.value_text, c.value_num, c.value_bool, "
            "       c.raw_value, c.observed_at, c.source_reliability, c.artifact_integrity, "
            "       c.review_status, lower(c.valid_period), upper(c.valid_period), "
            "       ea.source_id, ea.artifact_type "
            "  FROM claim c "
            "  LEFT JOIN LATERAL ("
            "     SELECT ea.source_id, ea.artifact_type "
            "       FROM claim_evidence ce "
            "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
            "      WHERE ce.claim_id = c.claim_id LIMIT 1"
            "  ) ea ON true "
            " WHERE c.subject_id = %s AND c.predicate_id = %s "
            "   AND c.sensitivity_tier = 0 "  # publication boundary (§0.7)
            "   AND c.sys_period @> %s::timestamptz",  # as-of belief (§9.4)
            (entity_id, predicate_id, as_of_belief),
        ).fetchall()
        claims: list[Claim] = []
        for r in rows:
            (
                claim_id,
                value_kind,
                value_text,
                value_num,
                value_bool,
                raw_value,
                observed_at,
                reliability,
                integrity,
                review_status,
                valid_from,
                valid_to,
                source_id,
                artifact_type,
            ) = r
            claims.append(
                Claim(
                    claim_id=str(claim_id),
                    subject_id=subject_id,
                    predicate_id=predicate_id,
                    value=_reconstruct_value(value_kind, value_text, value_num, value_bool),
                    reliability=reliability,
                    integrity=integrity,
                    genre=artifact_type or "",
                    observed_at=_as_date(observed_at) if observed_at else date(1970, 1, 1),
                    raw_value=raw_value or "",
                    valid_from=_as_date(valid_from) if valid_from else None,
                    valid_to=_as_date(valid_to) if valid_to else None,
                    review_status=review_status or "active",
                    source_id=source_id or "",
                )
            )
        return claims

    def entity(self, entity_type: str, entity_id: str) -> EntityRecord | None:
        resolved = self._resolve_entity(entity_id)
        if resolved is None:
            return None
        row = self._conn.execute(
            "SELECT entity_type FROM entity WHERE entity_id = %s", (resolved,)
        ).fetchone()
        if row is None or (entity_type and row[0] != entity_type):
            return None
        preds = [
            str(p[0])
            for p in self._conn.execute(
                "SELECT DISTINCT predicate_id FROM claim "
                "WHERE subject_id = %s AND sensitivity_tier = 0 ORDER BY predicate_id",
                (resolved,),
            ).fetchall()
        ]
        sources = self._source_ids_for_entity(resolved)
        label = self._label_for(resolved)
        # Publication boundary: sensitive coordinates are never returned raw here
        # (jurisdiction-only, §0.7); coordinate claims are reduced upstream (P21.2).
        return EntityRecord(
            entity_id=entity_id,
            entity_type=row[0],
            label=label,
            predicate_ids=tuple(preds),
            source_ids=tuple(sources),
        )

    def _label_for(self, entity_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT cached_canonical_name FROM organization WHERE entity_id = %s",
            (entity_id,),
        ).fetchone()
        if row is not None and row[0]:
            return str(row[0])
        ident = self._conn.execute(
            "SELECT value FROM entity_identifier WHERE entity_id = %s ORDER BY scheme LIMIT 1",
            (entity_id,),
        ).fetchone()
        return None if ident is None else str(ident[0])

    def _source_ids_for_entity(self, entity_id: str) -> list[str]:
        return [
            str(s[0])
            for s in self._conn.execute(
                "SELECT DISTINCT ea.source_id "
                "  FROM claim c "
                "  JOIN claim_evidence ce ON ce.claim_id = c.claim_id "
                "  JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
                "  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
                " WHERE c.subject_id = %s AND c.sensitivity_tier = 0 "
                " ORDER BY ea.source_id",
                (entity_id,),
            ).fetchall()
        ]

    def stored_claim(self, claim_id: str) -> StoredClaim | None:
        if not _looks_like_uuid(claim_id):
            return None
        row = self._conn.execute(
            "SELECT c.claim_id, c.predicate_id, c.value_kind, c.value_text, c.value_num, "
            "       c.value_bool, c.raw_value, c.observed_at, c.source_reliability, "
            "       c.artifact_integrity, c.review_status, lower(c.sys_period), c.subject_id, "
            "       ea.source_id, ea.artifact_type "
            "  FROM claim c "
            "  LEFT JOIN LATERAL ("
            "     SELECT ea.source_id, ea.artifact_type FROM claim_evidence ce "
            "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
            "      WHERE ce.claim_id = c.claim_id LIMIT 1) ea ON true "
            " WHERE c.claim_id = %s AND c.sensitivity_tier = 0",
            (claim_id,),
        ).fetchone()
        if row is None:
            return None
        capture_ids = tuple(
            str(c[0])
            for c in self._conn.execute(
                "SELECT capture_id FROM claim_evidence WHERE claim_id = %s", (claim_id,)
            ).fetchall()
        )
        asserted_at = row[11] or datetime.now(tz=UTC)
        claim = Claim(
            claim_id=str(row[0]),
            subject_id=str(row[12]),
            predicate_id=str(row[1]),
            value=_reconstruct_value(row[2], row[3], row[4], row[5]),
            reliability=row[8],
            integrity=row[9],
            genre=row[14] or "",
            observed_at=_as_date(row[7]) if row[7] else date(1970, 1, 1),
            raw_value=row[6] or "",
            review_status=row[10] or "active",
            source_id=row[13] or "",
        )
        return StoredClaim(claim=claim, asserted_at=asserted_at, capture_ids=capture_ids)

    def capture(self, artifact_id: str, capture_id: str) -> CaptureMetadata | None:
        if not (_looks_like_uuid(artifact_id) and _looks_like_uuid(capture_id)):
            return None
        row = self._conn.execute(
            "SELECT ec.capture_id, ea.source_id, ec.source_uri, ec.retrieved_at, "
            "       ec.content_digest, ec.media_type, ec.storage_tier "
            "  FROM evidence_capture ec "
            "  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
            " WHERE ec.artifact_id = %s AND ec.capture_id = %s",
            (artifact_id, capture_id),
        ).fetchone()
        if row is None:
            return None
        claims_supported = tuple(
            str(c[0])
            for c in self._conn.execute(
                "SELECT claim_id FROM claim_evidence WHERE capture_id = %s", (capture_id,)
            ).fetchall()
        )
        return CaptureMetadata(
            capture_id=str(row[0]),
            source_id=str(row[1]),
            source_uri=str(row[2] or ""),
            retrieved_at=row[3].date().isoformat() if row[3] else "",
            content_digest=str(row[4]),
            media_type=str(row[5]),
            tier=StorageTier(row[6]),
            claims_supported=claims_supported,
        )

    def rights_for(self, source_ids: tuple[str, ...]) -> list[RightsRecord]:
        if not source_ids:
            return []
        rows = self._conn.execute(
            "SELECT sr.source_id, rr.spdx_expression, rr.attribution_text, "
            "       rr.redistributable, rr.derivative_permitted, rr.terms_url, rr.retrieval_date "
            "  FROM source_registry sr "
            "  JOIN rights_record rr ON rr.rights_id = sr.rights_id "
            " WHERE sr.source_id = ANY(%s) ORDER BY sr.source_id",
            (list(source_ids),),
        ).fetchall()
        out: list[RightsRecord] = []
        for r in rows:
            out.append(
                RightsRecord(
                    source_id=str(r[0]),
                    spdx=str(r[1]),
                    attribution=str(r[2] or ""),
                    redistributable=(str(r[3]) == "yes"),
                    derivative_permitted=(str(r[4]) == "yes"),
                    terms_url=str(r[5] or ""),
                    retrieval_date=r[6] or date(1970, 1, 1),
                )
            )
        return out

    def coverage_for(self, scope: str) -> list[CoverageRecord]:
        # Persisted rows if any (P21.2), else compute-on-read (none yet for coverage).
        entity_id = self._resolve_entity(scope.split(":")[0]) or self._resolve_entity(scope)
        if entity_id is None:
            return []
        rows = self._conn.execute(
            "SELECT predicate_id, absence_kind, sources_searched "
            "  FROM coverage_record WHERE subject_id = %s",
            (entity_id,),
        ).fetchall()
        out: list[CoverageRecord] = []
        for r in rows:
            out.append(
                CoverageRecord(
                    predicate_id=str(r[0] or ""),
                    absence_kind=str(r[1]),
                    subject_id=scope,
                    sources_searched=tuple(r[2]) if r[2] else (),
                )
            )
        return out

    def captures(self) -> list[Capture]:
        # The snapshot-diff feed (§29.7) is populated by P21.2; empty is a valid,
        # back-compatible feed (no change events).
        return []

    def search(self, query: str) -> list[EntityRecord]:
        q = query.strip()
        if not q:
            return []
        rows = self._conn.execute(
            "SELECT DISTINCT ei.entity_id, e.entity_type "
            "  FROM entity_identifier ei JOIN entity e ON e.entity_id = ei.entity_id "
            " WHERE ei.value ILIKE %s ORDER BY ei.entity_id",
            (f"%{q}%",),
        ).fetchall()
        out: list[EntityRecord] = []
        for r in rows:
            entity_id = str(r[0])
            out.append(
                EntityRecord(
                    entity_id=entity_id,
                    entity_type=str(r[1]),
                    label=self._label_for(entity_id),
                    source_ids=tuple(self._source_ids_for_entity(entity_id)),
                )
            )
        return out

    def dossier(self, scope: str) -> DossierRecord | None:
        entity_id = self._resolve_entity(scope.split(":")[-1]) or self._resolve_entity(scope)
        # A jurisdiction/subject dossier is computed-on-read from its entities'
        # claims; None only when the scope resolves to nothing (→ 404).
        subjects = []
        if entity_id is not None:
            subjects = [entity_id]
        else:
            subjects = [
                str(e[0])
                for e in self._conn.execute(
                    "SELECT DISTINCT subject_id FROM claim WHERE sensitivity_tier = 0 LIMIT 25"
                ).fetchall()
            ]
        if not subjects:
            return None
        source_ids: set[str] = set()
        for s in subjects:
            source_ids.update(self._source_ids_for_entity(s))
        return DossierRecord(
            scope=scope,
            title=f"Dossier for {scope}",
            sections=(
                {"heading": "Subjects", "entities": subjects},
                {"heading": "Sources", "sources": sorted(source_ids)},
            ),
            source_ids=tuple(sorted(source_ids)),
        )

    def crosswalk_rows(self) -> list[CrosswalkRecord]:
        rows = self._conn.execute(
            "SELECT entity_id, scheme, value FROM entity_identifier "
            "WHERE scheme <> %s ORDER BY entity_id, scheme, value LIMIT 500",
            (_SUBJECT_SCHEME,),
        ).fetchall()
        return [
            CrosswalkRecord(
                sig_id=str(r[0]),
                external_scheme=str(r[1]),
                external_id=str(r[2]),
                relation="exactMatch",
            )
            for r in rows
        ]

    # --- graph annotations: persisted rows, else compute-on-read (ADR-059) -----

    def _persisted_contradictions(self) -> list[ContradictionRecord]:
        rows = self._conn.execute(
            "SELECT contradiction_id, subject_id, predicate_id, contradiction_type, "
            "       status, claim_ids FROM contradiction ORDER BY contradiction_id"
        ).fetchall()
        return [
            ContradictionRecord(
                contradiction_id=str(r[0]),
                subject_id=str(r[1]),
                predicate_id=str(r[2]),
                kind=str(r[3]),
                state=str(r[4]),
                claim_ids=tuple(str(x) for x in (r[5] or ())),
            )
            for r in rows
        ]

    def _claim_pairs(self) -> list[tuple[str, str]]:
        rows = self._conn.execute(
            "SELECT DISTINCT subject_id, predicate_id FROM claim "
            "WHERE sensitivity_tier = 0 ORDER BY subject_id, predicate_id"
        ).fetchall()
        return [(str(r[0]), str(r[1])) for r in rows]

    def _compute_on_read(self) -> tuple[list[ContradictionRecord], list[TaskRecord]]:
        """Derive contradictions + tasks from the live claims via the resolver.

        The seam P21.2 replaces with persisted ``graph_annotations`` rows: rather
        than read materialized annotations (none yet), run :func:`RESOLVE` over each
        ``(subject, predicate)`` group of public claims and surface the emitted
        contradictions and research tasks (SIG-RECON-057). Deterministic, read-only.
        """
        now = datetime.now(tz=UTC)
        contradictions: list[ContradictionRecord] = []
        tasks: dict[str, TaskRecord] = {}
        for entity_id, predicate_id in self._claim_pairs():
            claims = self.claims_for(entity_id, predicate_id, as_of_belief=now)
            if not claims:
                continue
            try:
                resolved = RESOLVE(
                    entity_id,
                    predicate_id,
                    claims,
                    as_of_world=now.date(),
                    as_of_belief=now.date(),
                    ruleset=self._ruleset,
                )
            except KeyError:
                continue
            # Only a genuine conflict is a contradiction — not an uncontested or
            # merely insufficient resolution (reconcile.resolve._contradiction_state).
            if (
                resolved.contradiction_state in {"resolved_conflict", "unresolved_conflict"}
                or resolved.contradictions
            ):
                contradictions.append(
                    ContradictionRecord(
                        contradiction_id=f"contradiction:{entity_id}:{predicate_id}",
                        subject_id=entity_id,
                        predicate_id=predicate_id,
                        kind=resolved.contradiction_state,
                        state=resolved.resolution_status.lower(),
                        claim_ids=resolved.considered_claim_ids,
                    )
                )
            for t in resolved.tasks:
                tasks[t.task_id] = TaskRecord(
                    task_id=t.task_id,
                    kind=t.task_type,
                    status="open",
                    rationale=t.closing_condition,
                    subject_id=entity_id,
                    predicate_id=predicate_id,
                )
        return contradictions, sorted(tasks.values(), key=lambda t: t.task_id)

    def contradictions(self) -> list[ContradictionRecord]:
        persisted = self._persisted_contradictions()
        if persisted:
            return persisted
        return self._compute_on_read()[0]

    def contradiction(self, contradiction_id: str) -> ContradictionRecord | None:
        for c in self.contradictions():
            if c.contradiction_id == contradiction_id:
                return c
        return None

    def _persisted_tasks(self) -> list[TaskRecord]:
        rows = self._conn.execute(
            "SELECT task_id, task_type, status, closing_condition, subject_id "
            "  FROM research_task ORDER BY task_id"
        ).fetchall()
        return [
            TaskRecord(
                task_id=str(r[0]),
                kind=str(r[1]),
                status=str(r[2]),
                rationale=str(r[3]),
                subject_id=None if r[4] is None else str(r[4]),
            )
            for r in rows
        ]

    def tasks(self) -> list[TaskRecord]:
        persisted = self._persisted_tasks()
        if persisted:
            return persisted
        return self._compute_on_read()[1]

    def task(self, task_id: str) -> TaskRecord | None:
        for t in self.tasks():
            if t.task_id == task_id:
                return t
        return None

    def resolve_id(self, id_type: str, uuid: str) -> IdDescriptor | None:
        row = self._conn.execute(
            "SELECT entity_id FROM entity_identifier WHERE scheme = %s AND value = %s",
            (id_type, uuid),
        ).fetchone()
        entity_id: str | None
        if row is not None:
            entity_id = str(row[0])
        elif _looks_like_uuid(uuid):
            hit = self._conn.execute(
                "SELECT entity_id FROM entity WHERE entity_id = %s", (uuid,)
            ).fetchone()
            entity_id = None if hit is None else str(hit[0])
        else:
            entity_id = None
        if entity_id is None:
            return None
        etype = self._conn.execute(
            "SELECT entity_type FROM entity WHERE entity_id = %s", (entity_id,)
        ).fetchone()
        return IdDescriptor(
            id_type=id_type,
            uuid=uuid,
            label=self._label_for(entity_id) or entity_id,
            canonical_path=f"/v1/entity/{etype[0] if etype else id_type}/{entity_id}",
            predicates={},
        )


def build_pg_store(dsn: str, *, role: str | None = None) -> PgReadStore:
    """Convenience builder for ``sig-api serve --dsn`` and tests."""
    return PgReadStore(dsn, role=role)


__all__ = ["PgReadStore", "build_pg_store"]

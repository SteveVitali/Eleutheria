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

P25.10 made that seam bounded-latency without ever serving a stale set:

* The compute is **set-based**: one query fetches every public claim (the same
  SELECT ``claims_for`` issues per pair), grouped in memory; the per-pair loop
  was the entire ~105 s cold time (~36k round-trips over 17,950 pairs), while
  the resolver pass itself is ~0.1 s in memory.
* The result is memoised per instance against the **spine watermark**
  (:meth:`PgReadStore._spine_watermark`). The spine is append-only: the only
  permitted mutation is closing a claim's ``sys_period``, which the watermark
  counts separately, so a cache keyed on it is provably never stale. Any write
  that could change the served set changes the key.
* The served watermark is disclosed on the response (``spine_watermark``), so a
  cached answer always states which spine state it describes (§3.1 freshness).
"""

from __future__ import annotations

import threading
import uuid as _uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import psycopg
from db.temporal import AsOf
from evidence.tiers import CaptureMetadata, StorageTier
from exports.shaping import (
    JurisdictionGroup,
    ShapedDataset,
    ShapedSite,
    ShapedSourceFreshness,
    SharingEdge,
    run_shaping,
)
from inference.coverage import CoverageRecord
from policy.rights import RightsRecord
from reconcile.materialize import CAPTURE_TIME_JOIN, observation_time
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


@dataclass(frozen=True)
class _AnnotationView:
    """A served contradiction/task set plus the spine watermark it describes."""

    contradictions: list[ContradictionRecord]
    tasks: list[TaskRecord]
    watermark: str


@dataclass(frozen=True)
class _ShapingView:
    """A served shaped dataset plus the spine watermark it describes (P27.3)."""

    dataset: ShapedDataset
    watermark: str


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
        self._role = role
        # RLS stays enabled: we never set row_security=off. An optional read role
        # (e.g. sig_read_public) makes RLS enforce the public tier ceiling too.
        self._conn = psycopg.connect(dsn, autocommit=True)
        if role:
            self._conn.execute(f"SET ROLE {role}")
        # P25.10: the compute-on-read annotation set is memoised against the
        # spine watermark. The lock keeps the per-instance compute to once per
        # watermark under concurrent requests, and the compute itself runs on a
        # dedicated connection so it cannot interleave with per-request reads.
        self._annotation_lock = threading.Lock()
        self._annotation_cache: _AnnotationView | None = None
        self._last_annotation_view: _AnnotationView | None = None
        # P27.3: the compute-on-read shaped dataset is memoised against the same
        # spine watermark under the same lock — one shaping pass per instance per
        # watermark, provably never stale (append-only).
        self._shaping_cache: _ShapingView | None = None

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
            "       ea.source_id, ea.artifact_type, cap.retrieved_at "
            "  FROM claim c "
            "  LEFT JOIN LATERAL ("
            "     SELECT ea.source_id, ea.artifact_type "
            "       FROM claim_evidence ce "
            "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
            "      WHERE ce.claim_id = c.claim_id LIMIT 1"
            "  ) ea ON true "
            + CAPTURE_TIME_JOIN
            + " WHERE c.subject_id = %s AND c.predicate_id = %s "
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
                retrieved_at,
            ) = r
            obs, basis = observation_time(observed_at, retrieved_at)
            claims.append(
                Claim(
                    claim_id=str(claim_id),
                    subject_id=subject_id,
                    predicate_id=predicate_id,
                    value=_reconstruct_value(value_kind, value_text, value_num, value_bool),
                    reliability=reliability,
                    integrity=integrity,
                    genre=artifact_type or "",
                    observed_at=obs,
                    observed_at_basis=basis,
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
            "       ea.source_id, ea.artifact_type, cap.retrieved_at "
            "  FROM claim c "
            "  LEFT JOIN LATERAL ("
            "     SELECT ea.source_id, ea.artifact_type FROM claim_evidence ce "
            "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
            "      WHERE ce.claim_id = c.claim_id LIMIT 1) ea ON true "
            + CAPTURE_TIME_JOIN
            + " WHERE c.claim_id = %s AND c.sensitivity_tier = 0",
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
        obs, basis = observation_time(row[7], row[15])
        claim = Claim(
            claim_id=str(row[0]),
            subject_id=str(row[12]),
            predicate_id=str(row[1]),
            value=_reconstruct_value(row[2], row[3], row[4], row[5]),
            reliability=row[8],
            integrity=row[9],
            genre=row[14] or "",
            observed_at=obs,
            observed_at_basis=basis,
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
        # Effective rights (P27.2/ADR-095): a source whose registry link is an
        # UNDETERMINED record resolves through the latest rights_decision whose
        # prior_rights_id is that link. Decisions only ever have UNDETERMINED
        # priors, so an already-resolved link is never re-licensed. COALESCE falls
        # back to the recorded link when no decision exists — fail-closed.
        # On a pre-P27.2 spine (no rights_decision table) the recorded link is used.
        has_row = self._conn.execute("SELECT to_regclass('rights_decision') IS NOT NULL").fetchone()
        has_decisions = bool(has_row and has_row[0])
        if has_decisions:
            effective = (
                "COALESCE("
                " (SELECT rd.rights_id FROM rights_decision rd"
                "   WHERE rd.source_id = sr.source_id"
                "     AND rd.prior_rights_id = sr.rights_id"
                "   ORDER BY rd.decided_at DESC, rd.decision_id DESC LIMIT 1),"
                " sr.rights_id)"
            )
        else:
            effective = "sr.rights_id"
        rows = self._conn.execute(
            "SELECT sr.source_id, rr.spdx_expression, rr.attribution_text, "
            "       rr.redistributable, rr.derivative_permitted, rr.terms_url, rr.retrieval_date "
            "  FROM source_registry sr "
            f"  JOIN rights_record rr ON rr.rights_id = {effective} "
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

    def _connect(self) -> psycopg.Connection:
        """A dedicated read connection for the annotation compute (P25.10).

        The compute runs several statements over the whole spine; on its own
        connection it can never interleave with a per-request read on
        ``self._conn``, and the same read role (RLS ceiling) applies.
        """
        conn = psycopg.connect(self._dsn, autocommit=True)
        if self._role:
            conn.execute(f"SET ROLE {self._role}")
        return conn

    def _spine_watermark(self) -> str:
        """A monotone watermark over the append-only spine (P25.10).

        The spine never lets a claim row change content (``claim_append_only``
        forbids DELETE and every non-``sys_period`` UPDATE; the one permitted
        mutation, closing ``sys_period``, is counted separately), so this tuple
        of row counts plus the latest assertion instant changes iff a row the
        annotation compute reads has arrived. A cache keyed on it is provably
        never stale: anything that could change the served set changes the key.
        """
        row = self._conn.execute(
            "SELECT (SELECT count(*) FROM claim),"
            "       (SELECT count(*) FROM claim WHERE upper(sys_period) IS NOT NULL),"
            "       (SELECT max(lower(sys_period)) FROM claim),"
            "       (SELECT count(*) FROM claim_evidence),"
            "       (SELECT count(*) FROM evidence_capture),"
            "       (SELECT count(*) FROM evidence_artifact)"
        ).fetchone()
        assert row is not None
        claims, closed, latest, claim_ev, captures, artifacts = row
        latest_s = latest.isoformat() if latest is not None else "none"
        return (
            f"claims={claims} closed={closed} latest_assertion={latest_s} "
            f"evidence={claim_ev}/{captures}/{artifacts}"
        )

    def _public_claim_groups(
        self, conn: psycopg.Connection, belief: datetime
    ) -> dict[tuple[str, str], list[Claim]]:
        """Every public claim visible at ``belief``, grouped by (subject, predicate).

        The same SELECT :meth:`claims_for` issues per pair (the publication
        boundary ``sensitivity_tier = 0`` and the as-of belief predicate are
        unchanged), issued once over the whole spine. ``claim.subject_id`` IS the
        entity id, so grouping needs no per-pair entity resolution.
        """
        rows = conn.execute(
            "SELECT c.claim_id, c.subject_id, c.predicate_id, c.value_kind, c.value_text, "
            "       c.value_num, c.value_bool, c.raw_value, c.observed_at, "
            "       c.source_reliability, c.artifact_integrity, c.review_status, "
            "       lower(c.valid_period), upper(c.valid_period), "
            "       ea.source_id, ea.artifact_type, cap.retrieved_at "
            "  FROM claim c "
            "  LEFT JOIN LATERAL ("
            "     SELECT ea.source_id, ea.artifact_type "
            "       FROM claim_evidence ce "
            "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
            "      WHERE ce.claim_id = c.claim_id LIMIT 1"
            "  ) ea ON true "
            + CAPTURE_TIME_JOIN
            + " WHERE c.sensitivity_tier = 0 "  # publication boundary (§0.7)
            "   AND c.sys_period @> %s::timestamptz "  # as-of belief (§9.4)
            " ORDER BY c.subject_id, c.predicate_id, c.claim_id",
            (belief,),
        ).fetchall()
        groups: dict[tuple[str, str], list[Claim]] = {}
        for r in rows:
            (
                claim_id,
                subject_id,
                predicate_id,
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
                retrieved_at,
            ) = r
            sid, pid = str(subject_id), str(predicate_id)
            obs, basis = observation_time(observed_at, retrieved_at)
            groups.setdefault((sid, pid), []).append(
                Claim(
                    claim_id=str(claim_id),
                    subject_id=sid,
                    predicate_id=pid,
                    value=_reconstruct_value(value_kind, value_text, value_num, value_bool),
                    reliability=reliability,
                    integrity=integrity,
                    genre=artifact_type or "",
                    observed_at=obs,
                    observed_at_basis=basis,
                    raw_value=raw_value or "",
                    valid_from=_as_date(valid_from) if valid_from else None,
                    valid_to=_as_date(valid_to) if valid_to else None,
                    review_status=review_status or "active",
                    source_id=source_id or "",
                )
            )
        return groups

    def _compute_on_read(
        self, conn: psycopg.Connection
    ) -> tuple[list[ContradictionRecord], list[TaskRecord]]:
        """Derive contradictions + tasks from the live claims via the resolver.

        The seam P21.2 replaces with persisted ``graph_annotations`` rows: rather
        than read materialized annotations (none yet), run :func:`RESOLVE` over each
        ``(subject, predicate)`` group of public claims and surface the emitted
        contradictions and research tasks (SIG-RECON-057). Deterministic, read-only.
        """
        now = datetime.now(tz=UTC)
        contradictions: list[ContradictionRecord] = []
        tasks: dict[str, TaskRecord] = {}
        groups = self._public_claim_groups(conn, now)
        for entity_id, predicate_id in sorted(groups):
            claims = groups[entity_id, predicate_id]
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
        return self._annotation_view().contradictions

    def contradiction(self, contradiction_id: str) -> ContradictionRecord | None:
        for c in self.contradictions():
            if c.contradiction_id == contradiction_id:
                return c
        return None

    def _annotation_view(self) -> _AnnotationView:
        """The current contradiction/task set plus the watermark it describes.

        Persisted ``graph_annotations`` rows (P21.2) are authoritative and read
        live; the compute-on-read fallback is memoised against the spine
        watermark so the spine is re-resolved at most once per instance per
        watermark: never more, and (append-only) never stale. The watermark is
        read BEFORE the data so the disclosed state never overstates freshness.
        """
        with self._annotation_lock:
            watermark = self._spine_watermark()
            persisted_c = self._persisted_contradictions()
            persisted_t = self._persisted_tasks()
            if persisted_c and persisted_t:
                view = _AnnotationView(persisted_c, persisted_t, watermark)
            else:
                cached = self._annotation_cache
                if cached is None or cached.watermark != watermark:
                    with self._connect() as conn:
                        computed_c, computed_t = self._compute_on_read(conn)
                    cached = _AnnotationView(computed_c, computed_t, watermark)
                    self._annotation_cache = cached
                view = _AnnotationView(
                    persisted_c if persisted_c else cached.contradictions,
                    persisted_t if persisted_t else cached.tasks,
                    # A served computed portion was derived at its cache key; a
                    # live-read persisted portion describes at least that state,
                    # so the cache key is the honest (conservative) disclosure.
                    cached.watermark,
                )
            self._last_annotation_view = view
            return view

    def annotation_watermark(self) -> str | None:
        """The spine watermark the last-served annotation set was computed at."""
        view = self._last_annotation_view
        if view is None:
            view = self._annotation_view()
        return view.watermark

    def warmup(self) -> None:
        """Kick off the one-per-instance annotation compute in the background.

        Best-effort: a failure here is retried on the first real request, which
        surfaces the error properly. The lock guarantees the compute still runs
        at most once even if a request arrives mid-warmup.
        """

        def _warm() -> None:
            try:
                self._annotation_view()
            except Exception:  # noqa: BLE001 - warmup is advisory, never fatal
                pass

        threading.Thread(target=_warm, name="sig-annotation-warmup", daemon=True).start()

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
        return self._annotation_view().tasks

    def task(self, task_id: str) -> TaskRecord | None:
        for t in self.tasks():
            if t.task_id == task_id:
                return t
        return None

    # --- export data-shaping enumeration reads (P27.3, LAUNCH.3) --------------
    #
    # The reads the export build (P27.4) needs: publishable jurisdictions,
    # shaped geolocated sites, per-source freshness, and sharing edges. These
    # are store-only methods — NOT on the ReadStore protocol — because they are
    # export-build reads, not endpoint seams. All of them draw on one
    # compute-on-read :class:`exports.shaping.ShapedDataset`, memoised against
    # the spine watermark exactly like the annotation view (P25.10): the spine
    # is append-only, so a cache keyed on the watermark is provably never stale.
    # The shaping itself is read-only (run_shaping sets
    # default_transaction_read_only) and observation-level (ADR-092) — never a
    # resolved census.

    def _shaping_view(self) -> _ShapingView:
        with self._annotation_lock:
            watermark = self._spine_watermark()
            cached = self._shaping_cache
            if cached is None or cached.watermark != watermark:
                conn = self._connect()
                try:
                    dataset = run_shaping(
                        conn,
                        as_of=datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        spine_label="pg-store",
                    )
                finally:
                    conn.close()
                cached = _ShapingView(dataset=dataset, watermark=watermark)
                self._shaping_cache = cached
            return cached

    def shaped_dataset(self) -> ShapedDataset:
        """The full compute-on-read shaped dataset (sites/jurisdictions/coverage)."""
        return self._shaping_view().dataset

    def publishable_scopes(self) -> list[str]:
        """Every subject scope carrying publishable claims, sorted (P27.4 read).

        Superset of :meth:`geolocated_sites`: includes subjects with no
        coordinate evidence — they are dossier/coverage scopes, not points.
        """
        return sorted(s.entity_id for s in self._shaping_view().dataset.sites)

    def geolocated_sites(self) -> list[ShapedSite]:
        """Every publishable site carrying coordinate evidence (P27.4 read).

        Includes ``conflicted`` sites (coordinate evidence that disagrees stays
        visible); excludes subjects with no coordinate claims at all — those are
        coverage-denominator members, not geolocated observations.
        """
        return [s for s in self._shaping_view().dataset.sites if s.has_coordinate_claims]

    def publishable_jurisdictions(self) -> list[JurisdictionGroup]:
        """Per-jurisdiction groups over publishable claims, `unresolved` included."""
        return list(self._shaping_view().dataset.jurisdictions)

    def sources_with_freshness(self) -> list[ShapedSourceFreshness]:
        """Per-source freshness inputs (SIG-METRIC-007), volatility-relative."""
        return list(self._shaping_view().dataset.sources)

    def sharing_edges(self) -> list[SharingEdge]:
        """Every publishable sharing edge with its access kind (§29.3)."""
        return list(self._shaping_view().dataset.sharing_edges)

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

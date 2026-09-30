# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The PostgreSQL claim sink — connector output persisted to the L0-L3 spine (§16).

Until P19.4 the only :class:`connectors.stages.ClaimSink` was ``InMemoryClaimSink``:
connector claims were produced, fingerprinted, and diffed, but never written to the
canonical PostgreSQL store (the composed run recorded this as ``LD-F06b``). This
module crosses that seam. :class:`PgClaimSink` implements ``assert_claims`` by
inserting, with psycopg and **append-only** (INSERTs only — no in-place mutation
or row removal anywhere in this module, SIG-STORE-011/012):

* **L0 evidence** — one synthetic ``evidence_artifact`` + ``evidence_capture`` per
  source per run, so every persisted claim resolves to a real ``evidence_capture``
  row (``claim_evidence`` links it with role ``establishes``), and an
  ``extraction`` that becomes the claim's origin.
* **L2 identity** — the connector's opaque string ``subject_id`` is resolved to an
  ``entity`` row via ``entity_identifier(scheme='sig.connector.subject')``; the
  same string always resolves to the same entity (idempotent identity).
* **L1 claim** — the append-only ``claim`` row itself. ``recorded_at`` (its
  ``sys_period`` lower bound) is set **by the database** (``clock_timestamp()``
  default), never by this code.

**Idempotency** (ADR-059): a connector replay is byte-reproducible modulo the two
non-deterministic columns the fingerprint excludes (``claim_id``, ``sys_period``;
SIG-INGEST-003). Each claim carries a ``content_digest`` — the sha256 over its
reproducible payload — and the ``claim_content_digest`` unique index makes the
insert ``ON CONFLICT DO NOTHING``. Replaying the same run therefore inserts each
claim exactly once: N>0 rows the first time, 0 new rows on every replay. A
correction is still a *new* row (a different payload → a different digest).

The connector packages must not import psycopg directly (see
``connectors/src/connectors/sinks.py``); they build a sink through that factory,
which imports this module from the ``db`` package.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import psycopg

from .run_completion import append_completion

#: Columns excluded from the reproducibility payload (SIG-INGEST-003, SIG-EVID-017):
#: the generated id and the two DB-controlled time columns. Kept byte-identical to
#: ``evidence.ingest_run.NON_DETERMINISTIC_COLUMNS`` without importing it (``db`` is
#: a leaf package; no new dependency edge).
_NON_DETERMINISTIC = frozenset({"claim_id", "sys_period", "recorded_at"})

#: Conservative epistemic defaults for a connector-asserted claim whose dict does
#: not declare them (documented in ADR-059). A connector emits candidate evidence,
#: never an authoritative verdict, so the defaults are deliberately middling.
_DEFAULT_RELIABILITY = "R3"  # credible secondary source (§10.4)
_DEFAULT_DIRECTNESS = "D2"  # direct statement in a secondary record (§10.5)
_DEFAULT_INTEGRITY = "I1"  # intact original capture (§10.6)
_DEFAULT_ENTITY_TYPE = "deployment"  # the atlas/osm subjects are adoption bridges (§11.7)

#: The identifier scheme the sink keys connector subjects on (idempotent identity).
SUBJECT_SCHEME = "sig.connector.subject"

#: Environment variables recorded on each ``ingest_run.environment`` (SIG-EVID-018
#: asks for the locale + timezone; the Cloud Run ids tie a run to its job execution).
#: Only variables that are actually set are recorded, and none of them is a secret.
_RECORDED_ENV = (
    "TZ",
    "LC_ALL",
    "CLOUD_RUN_JOB",
    "CLOUD_RUN_EXECUTION",
    "CLOUD_RUN_TASK_INDEX",
    "CLOUD_RUN_TASK_ATTEMPT",
)

#: Default number of claims committed per :meth:`PgClaimSink.assert_claims`
#: transaction (P26.18 / SOURCES.17). Sized so a chunk commits in well under a
#: Cloud Run task timeout even on the small ``db-f1-micro`` spine (~20–45
#: committed claims/s aggregate observed in P26.16 → ~10k claims ≈ 4–8 min),
#: while leaving every ordinary source — all well below this size — committing
#: in a *single* chunk, i.e. byte-for-byte the pre-P26.18 all-in-one-transaction
#: behaviour. Only the handful of very-large sources (OSM's ~1.37M mirror) span
#: multiple chunks, which makes their ingest resumable rather than all-or-nothing.
DEFAULT_COMMIT_CHUNK_SIZE = 10_000


def content_digest(claim: Mapping[str, Any]) -> str:
    """The sha256 over a claim's reproducible payload (its idempotency key).

    Drops the non-deterministic columns and renders the rest with sorted keys, so
    two runs of a pinned connector over pinned inputs digest identically — the same
    rule the connector reproducibility fingerprint uses (SIG-INGEST-003).
    """
    stable = {k: v for k, v in claim.items() if k not in _NON_DETERMINISTIC}
    payload = json.dumps(stable, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class ClaimSinkReport:
    """What one :meth:`PgClaimSink.assert_claims` call did (for the CLI / tests)."""

    considered: int = 0
    inserted: int = 0
    duplicates: int = 0
    non_claim_records: int = 0
    entities: int = 0


def _coerce_observed_at(value: Any) -> datetime | None:
    """Best-effort parse of a connector ``observed_at`` into a timestamptz."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=UTC)
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _value_datatype(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    return "string"


class PgClaimSink:
    """A :class:`connectors.stages.ClaimSink` that persists claims to PostgreSQL.

    Constructed with an open psycopg connection (the factory owns opening it from a
    DSN). Connector run metadata identifies the ``ingest_run``.

    **One sink = one execution = one ``ingest_run``** (P31.2 / ADR-109). Each sink
    carries an ``execution_id``, recorded in ``ingest_run.parameters``. If the
    caller passes none, a fresh one is generated, so two executions of the same
    connector version get two runs. (Before P31.2 the run was reused by
    ``(connector, version, commit, is_replay)``, so one row folded many executions
    together.) A caller that passes an explicit ``execution_id`` is resuming the
    same logical execution, and its sink reuses that run. When the execution ends,
    :meth:`record_completion` appends its ``ingest_run_completion`` row;
    ``ingest_run`` itself is never rewritten.
    """

    def __init__(
        self,
        conn: psycopg.Connection[Any],
        *,
        connector_name: str = "connector",
        connector_version: str = "0",
        code_commit: str = "unknown",
        ruleset_version: str = "ruleset/1",
        vocab_version: str = "1.0.0",
        is_replay: bool = False,
        commit_chunk_size: int = DEFAULT_COMMIT_CHUNK_SIZE,
        execution_id: str | None = None,
        run_record_uri: str | None = None,
    ) -> None:
        if commit_chunk_size < 1:
            raise ValueError(
                f"commit_chunk_size must be >= 1 (got {commit_chunk_size!r}); a chunk "
                "spans at least one claim"
            )
        self._conn = conn
        self._connector_name = connector_name
        self._connector_version = connector_version
        self._code_commit = code_commit
        self._ruleset_version = ruleset_version
        self._vocab_version = vocab_version
        self._is_replay = is_replay
        self._commit_chunk_size = commit_chunk_size
        # The execution discriminator (ADR-109): explicit = resume that execution's
        # run; absent = a fresh execution, so a fresh run.
        self._resume_execution = execution_id is not None
        self._execution_id = execution_id or uuid.uuid4().hex
        # The WORM run row the scheduled wrapper writes for this execution (gs://…),
        # recorded on the run and on its completion so the two cross-reference.
        self._run_record_uri = run_record_uri
        # Per-instance caches so prerequisites are resolved once, not per claim.
        self._run_id: str | None = None
        self._rights_by_spdx: dict[str, str] = {}
        self._entity_by_subject: dict[str, str] = {}
        # (source_id, artifact_type) -> (capture_id, extraction_id)
        self._capture_by_source: dict[tuple[str, str], tuple[str, str]] = {}
        self._chunk_exhausted = False
        self.report = ClaimSinkReport()

    @classmethod
    def from_dsn(cls, dsn: str, **kwargs: Any) -> PgClaimSink:
        """Open an autocommit connection from ``dsn`` and wrap it in a sink.

        This is the single place psycopg opens a connection for the connector
        write path, so ``connectors`` can build a PG sink (via
        ``connectors.sinks.make_claim_sink``) without importing psycopg itself.
        """
        conn = psycopg.connect(dsn, autocommit=True)
        return cls(conn, **kwargs)

    # --- ClaimSink protocol ----------------------------------------------------

    def assert_claims(self, claims: Sequence[Mapping[str, Any]]) -> None:
        """Persist ``claims`` append-only and idempotently (the L1 write path).

        Commits in **bounded chunks** of ``commit_chunk_size`` claims (P26.18 /
        SOURCES.17): each chunk is its own ``self._conn.transaction()``, so a
        very-large source (OSM's ~1.37M-claim mirror) commits progressively
        instead of holding one multi-hour transaction that a Cloud Run task
        deadline rolls back whole. A claim and **all** its prerequisite/evidence
        inserts run inside a single ``_insert_claim`` call and therefore land in
        the SAME chunk transaction — a chunk boundary never bisects a claim
        (append-only invariant, root AGENTS.md §5). Because every write is
        content-keyed ``ON CONFLICT DO NOTHING``, chunks that already committed
        dedupe to +0 on a re-run, so an interrupted run (chunks 1..k committed,
        process dies) is safe to resume: the re-walk tops up from where it
        stopped and reaches the same final count. The default leaves every
        ordinary source committing in one chunk — unchanged behaviour.

        ``SinkReport`` counters stay exact across chunk boundaries: they are
        instance state accumulated as each record is considered, independent of
        how the transactions are split. ``inserted``/``duplicates``/``entities``
        count only committed chunks: a chunk that raises restores them (P31.2).
        """
        chunk_size = self._commit_chunk_size
        remaining = iter(claims)
        exhausted = False
        while not exhausted:
            # P31.2 / ADR-109: a chunk that raises rolls back everything it wrote,
            # so the ids cached during it and its inserted/duplicate counts must go
            # with it. Otherwise a failed run's completion would name a rolled-back
            # ingest_run, or count claims that never landed.
            snapshot = self._chunk_snapshot()
            try:
                self._assert_chunk(remaining, chunk_size)
            except BaseException:
                self._restore_chunk_snapshot(snapshot)
                raise
            exhausted = self._chunk_exhausted

    def _chunk_snapshot(self) -> tuple[Any, ...]:
        return (
            self._run_id,
            dict(self._rights_by_spdx),
            dict(self._entity_by_subject),
            dict(self._capture_by_source),
            self.report.inserted,
            self.report.duplicates,
            self.report.entities,
        )

    def _restore_chunk_snapshot(self, snapshot: tuple[Any, ...]) -> None:
        (
            self._run_id,
            self._rights_by_spdx,
            self._entity_by_subject,
            self._capture_by_source,
            self.report.inserted,
            self.report.duplicates,
            self.report.entities,
        ) = snapshot

    def _assert_chunk(self, remaining: Any, chunk_size: int) -> None:
        """One chunk transaction; sets ``_chunk_exhausted`` when the input ran out."""
        committed_this_chunk = 0
        self._chunk_exhausted = False
        with self._conn.transaction():
            for claim in remaining:
                self.report.considered += 1
                if claim.get("record_kind", "claim") != "claim":
                    # unmapped-category / vocabulary-event rows are not L1
                    # claims; their task/coverage projections are owned
                    # elsewhere (P21.2). They do no spine write, so they do
                    # not count toward the chunk's claim budget.
                    self.report.non_claim_records += 1
                    continue
                self._insert_claim(claim)
                committed_this_chunk += 1
                if committed_this_chunk >= chunk_size:
                    # Chunk full — close this transaction (the `with` commits
                    # on exit) and open a fresh one for the next chunk.
                    break
            else:
                # The `for` ran to exhaustion without breaking: this is the
                # final (possibly partial / empty) chunk.
                self._chunk_exhausted = True

    # --- prerequisites (all INSERT ... ON CONFLICT DO NOTHING, append-only) ----

    def _ensure_resolution_strategy(self, strategy_id: str) -> None:
        self._conn.execute(
            "INSERT INTO vocab_resolution_strategy(strategy_id, definition) "
            "VALUES (%s, %s) ON CONFLICT (strategy_id) DO NOTHING",
            (strategy_id, "connector-asserted claim (P19.4 PgClaimSink)"),
        )

    def _ensure_predicate(self, predicate_id: str, value: Any) -> None:
        self._ensure_resolution_strategy("authoritative_source_wins")
        self._conn.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id, vocab_version, value_datatype, object_type, definition,"
            " volatility_class, half_life_days, resolution_strategy) "
            "VALUES (%s, %s, %s, 'literal', %s, 'MODERATE', 365,"
            " 'authoritative_source_wins') ON CONFLICT (predicate_id) DO NOTHING",
            (
                predicate_id,
                self._vocab_version,
                _value_datatype(value),
                f"connector predicate {predicate_id!r} (registered by PgClaimSink)",
            ),
        )

    def _rights_id(self, spdx: str, attribution: str | None) -> str:
        spdx = spdx or "UNDETERMINED"
        cached = self._rights_by_spdx.get(spdx)
        if cached is not None:
            return cached
        # Reuse an existing rights_record for this licence if one is already stored
        # (idempotent across replays); else insert one.
        row = self._conn.execute(
            "SELECT rights_id FROM rights_record WHERE spdx_expression = %s "
            "ORDER BY rights_id LIMIT 1",
            (spdx,),
        ).fetchone()
        if row is not None:
            self._rights_by_spdx[spdx] = str(row[0])
            return str(row[0])
        redistributable = "UNDETERMINED" if spdx == "UNDETERMINED" else "yes"
        inserted = self._conn.execute(
            "INSERT INTO rights_record"
            "(spdx_expression, attribution_text, redistributable, derivative_permitted,"
            " retrieval_date) VALUES (%s, %s, %s, %s, %s) RETURNING rights_id",
            (spdx, attribution, redistributable, redistributable, date.today()),
        ).fetchone()
        assert inserted is not None
        self._rights_by_spdx[spdx] = str(inserted[0])
        return str(inserted[0])

    @property
    def run_id(self) -> str | None:
        """This execution's ``ingest_run`` id, or ``None`` before anything was written."""
        return self._run_id

    @property
    def execution_id(self) -> str:
        """The execution discriminator recorded in ``ingest_run.parameters``."""
        return self._execution_id

    def _ensure_run(self) -> str:
        if self._run_id is not None:
            return self._run_id
        if self._resume_execution:
            # A caller-supplied execution id resumes that execution's run.
            row = self._conn.execute(
                "SELECT run_id FROM ingest_run WHERE connector_name = %s "
                "AND parameters ->> 'execution_id' = %s ORDER BY started_at LIMIT 1",
                (self._connector_name, self._execution_id),
            ).fetchone()
            if row is not None:
                self._run_id = str(row[0])
                return self._run_id
        parameters: dict[str, str] = {"execution_id": self._execution_id}
        if self._run_record_uri:
            parameters["run_record_uri"] = self._run_record_uri
        environment = {k: os.environ[k] for k in _RECORDED_ENV if os.environ.get(k)}
        inserted = self._conn.execute(
            "INSERT INTO ingest_run"
            "(connector_name, connector_version, code_commit, ruleset_version,"
            " vocab_version, parameters, environment, input_digests, is_replay) "
            "VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, '{}', %s) RETURNING run_id",
            (
                self._connector_name,
                self._connector_version,
                self._code_commit,
                self._ruleset_version,
                self._vocab_version,
                json.dumps(parameters, sort_keys=True),
                json.dumps(environment, sort_keys=True),
                self._is_replay,
            ),
        ).fetchone()
        assert inserted is not None
        self._run_id = str(inserted[0])
        return self._run_id

    def record_completion(
        self, status: str, *, source_id: str | None = None, detail: str | None = None
    ) -> str | None:
        """Append this execution's ``ingest_run_completion`` row (ADR-109).

        ``finished_at`` is the database clock at the moment of the call. The counts
        are this sink's exact report. The run is created if nothing was written yet:
        an execution that inserted no claims still ran, and it records that. Only
        one live completion exists per run; a second call returns ``None`` (+0).
        ``detail`` must stay secret-free, so callers pass an exception class name,
        never its message.
        """
        run_id = self._ensure_run()
        return append_completion(
            self._conn,
            run_id=run_id,
            source_id=source_id,
            status=status,
            claims_considered=self.report.considered,
            claims_inserted=self.report.inserted,
            claims_duplicate=self.report.duplicates,
            run_record_uri=self._run_record_uri,
            detail=detail,
        )

    def _ensure_source(self, source_id: str, rights_id: str) -> None:
        self._conn.execute(
            "INSERT INTO source_registry"
            "(source_id, name, source_kind, default_reliability, reliability_provisional,"
            " reliability_justification, rights_id, custody_posture, compact_status,"
            " ingestion_permitted, robots_policy) "
            "VALUES (%s, %s, 'connector', %s, false, %s, %s, 'REFERENCE', 'compact',"
            " true, 'obeyed') ON CONFLICT (source_id) DO NOTHING",
            (
                source_id,
                f"connector source {source_id}",
                _DEFAULT_RELIABILITY,
                "connector-registered source (P19.4 PgClaimSink)",
                rights_id,
            ),
        )

    def _ensure_evidence(
        self, source_id: str, rights_id: str, artifact_type: str = "connector_run"
    ) -> tuple[str, str]:
        """Return ``(capture_id, extraction_id)`` for this ``(source, genre)``.

        Creates the L0 artifact/capture/extraction chain once per source per genre
        per run (idempotent). ``artifact_type`` carries the claim's evidence genre
        so it becomes the resolver's directness genre on read (§10.5)."""
        cache_key = (source_id, artifact_type)
        cached = self._capture_by_source.get(cache_key)
        if cached is not None:
            return cached
        self._ensure_source(source_id, rights_id)
        run_id = self._ensure_run()
        stable_locator = f"sig:connector:{self._connector_name}:{source_id}:{artifact_type}"
        # evidence_artifact — UNIQUE(source_id, stable_locator).
        art = self._conn.execute(
            "INSERT INTO evidence_artifact"
            "(source_id, stable_locator, artifact_type, acquisition_method,"
            " primary_or_secondary, rights_id, capture_status) "
            "VALUES (%s, %s, %s, 'connector', 'secondary', %s, 'captured') "
            "ON CONFLICT (source_id, stable_locator) DO NOTHING RETURNING artifact_id",
            (source_id, stable_locator, artifact_type, rights_id),
        ).fetchone()
        if art is None:
            art = self._conn.execute(
                "SELECT artifact_id FROM evidence_artifact "
                "WHERE source_id = %s AND stable_locator = %s",
                (source_id, stable_locator),
            ).fetchone()
        assert art is not None
        artifact_id = str(art[0])
        # evidence_blob — the deduplicated byte registry (SIG-EVID-004): the
        # (blob_digest, source_uri) PK makes a re-fetch of unchanged bytes idempotent.
        cap_digest = hashlib.sha256(
            f"{self._connector_name}|{source_id}|{run_id}".encode()
        ).hexdigest()
        ocfl_object_id = f"sig:evidence:{artifact_id}"
        self._conn.execute(
            "INSERT INTO evidence_blob"
            "(blob_digest, source_uri, byte_size, ocfl_object_id, ocfl_version) "
            "VALUES (%s, %s, 0, %s, 'v1') ON CONFLICT (blob_digest, source_uri) DO NOTHING",
            (cap_digest, stable_locator, ocfl_object_id),
        )
        # evidence_capture — no natural uniqueness (N captures per blob, SIG-EVID-004),
        # so dedup this synthetic one-per-source-per-run capture with SELECT-first.
        cap = self._conn.execute(
            "SELECT capture_id FROM evidence_capture "
            "WHERE artifact_id = %s AND retrieved_by_run_id = %s AND content_digest = %s "
            "ORDER BY capture_id LIMIT 1",
            (artifact_id, run_id, cap_digest),
        ).fetchone()
        if cap is None:
            cap = self._conn.execute(
                "INSERT INTO evidence_capture"
                "(artifact_id, content_digest, byte_size, media_type, retrieved_at,"
                " retrieved_by_run_id, ocfl_object_id, ocfl_version, storage_tier,"
                " capture_method, capture_tool_version, source_uri, blob_digest) "
                "VALUES (%s, %s, 0, 'application/octet-stream', clock_timestamp(), %s,"
                " %s, 'v1', 'public', 'connector', %s, %s, %s) RETURNING capture_id",
                (
                    artifact_id,
                    cap_digest,
                    run_id,
                    ocfl_object_id,
                    self._connector_version,
                    stable_locator,
                    cap_digest,
                ),
            ).fetchone()
        assert cap is not None
        capture_id = str(cap[0])
        # extraction — the claim's origin (satisfies claim_origin_present).
        row = self._conn.execute(
            "SELECT extraction_id FROM extraction WHERE capture_id = %s "
            "AND extractor_name = %s ORDER BY extracted_at LIMIT 1",
            (capture_id, self._connector_name),
        ).fetchone()
        if row is not None:
            extraction_id = str(row[0])
        else:
            ex = self._conn.execute(
                "INSERT INTO extraction"
                "(capture_id, method, extractor_name, extractor_version,"
                " normalizer_version, parameters, run_id) "
                "VALUES (%s, 'deterministic', %s, %s, %s, '{}', %s) RETURNING extraction_id",
                (
                    capture_id,
                    self._connector_name,
                    self._connector_version,
                    self._connector_version,
                    run_id,
                ),
            ).fetchone()
            assert ex is not None
            extraction_id = str(ex[0])
        self._capture_by_source[cache_key] = (capture_id, extraction_id)
        return capture_id, extraction_id

    def _entity_for_subject(self, subject_id: str) -> str:
        """Resolve a connector subject string to an entity uuid (idempotent)."""
        cached = self._entity_by_subject.get(subject_id)
        if cached is not None:
            return cached
        row = self._conn.execute(
            "SELECT entity_id FROM entity_identifier WHERE scheme = %s AND value = %s",
            (SUBJECT_SCHEME, subject_id),
        ).fetchone()
        if row is not None:
            self._entity_by_subject[subject_id] = str(row[0])
            return str(row[0])
        created = self._conn.execute(
            "INSERT INTO entity(entity_type) VALUES (%s) RETURNING entity_id",
            (_DEFAULT_ENTITY_TYPE,),
        ).fetchone()
        assert created is not None
        entity_id = str(created[0])
        self._conn.execute(
            "INSERT INTO entity_identifier(entity_id, scheme, value) "
            "VALUES (%s, %s, %s) ON CONFLICT (entity_id, scheme, value) DO NOTHING",
            (entity_id, SUBJECT_SCHEME, subject_id),
        )
        self._entity_by_subject[subject_id] = entity_id
        self.report.entities += 1
        return entity_id

    # --- the L1 claim insert ---------------------------------------------------

    def _insert_claim(self, claim: Mapping[str, Any]) -> None:
        subject = str(claim.get("subject_id") or "")
        predicate = str(claim.get("predicate_id") or "")
        if not subject or not predicate:
            self.report.non_claim_records += 1
            return
        value = claim.get("value")
        spdx = str(claim.get("license") or claim.get("spdx") or "UNDETERMINED")
        attribution = claim.get("source_attribution") or claim.get("attribution")
        source_id = str(claim.get("source_id") or self._connector_name)

        genre = str(claim.get("evidence_genre") or "connector_run")
        rights_id = self._rights_id(spdx, attribution)
        self._ensure_predicate(predicate, value)
        subject_entity = self._entity_for_subject(subject)
        capture_id, extraction_id = self._ensure_evidence(source_id, rights_id, genre)
        run_id = self._ensure_run()

        observed_at = _coerce_observed_at(claim.get("observed_at"))
        observed_unknown_reason = (
            None if observed_at is not None else "connector run did not record an observation time"
        )
        # The canonical scalar value: an explicit ``value``, else the P2-preserved
        # ``raw_value`` (the source's literal text), else no value at all.
        raw_field = claim.get("raw_value")
        raw_value = (
            str(raw_field) if raw_field is not None else (str(value) if value is not None else "")
        )
        if value is not None:
            value_kind = "value"
            value_text = str(value)
            value_bool = value if isinstance(value, bool) else None
            value_num = (
                value if isinstance(value, (int, float)) and not isinstance(value, bool) else None
            )
        elif raw_field is not None and str(raw_field) != "":
            value_kind = "value"
            value_text = str(raw_field)
            value_bool = None
            value_num = None
        else:
            # A connector row that asserts a subject/predicate with no value yet
            # (§16.2 'novalue'): every value_* column stays null.
            value_kind = "novalue"
            value_text = None
            value_bool = None
            value_num = None
        digest = content_digest(claim)

        inserted = self._conn.execute(
            "INSERT INTO claim"
            "(subject_id, predicate_id, object_type, value_kind, value_text, value_num,"
            " value_bool, unit, raw_value, observed_at, observed_unknown_reason,"
            " source_reliability, claim_directness, artifact_integrity, extraction_id,"
            " ingest_run_id, rights_id, sensitivity_tier, content_digest) "
            "VALUES (%s, %s, 'literal', %s, %s, %s, %s, NULL, %s, %s, %s,"
            " %s, %s, %s, %s, %s, %s, 0, %s) "
            "ON CONFLICT (content_digest) WHERE content_digest IS NOT NULL "
            "DO NOTHING RETURNING claim_id",
            (
                subject_entity,
                predicate,
                value_kind,
                value_text,
                value_num,
                value_bool,
                raw_value,
                observed_at,
                observed_unknown_reason,
                _DEFAULT_RELIABILITY,
                _DEFAULT_DIRECTNESS,
                _DEFAULT_INTEGRITY,
                extraction_id,
                run_id,
                rights_id,
                digest,
            ),
        ).fetchone()
        if inserted is None:
            self.report.duplicates += 1
            return
        claim_id = str(inserted[0])
        # Link the claim to its establishing capture (§16.5).
        self._conn.execute(
            "INSERT INTO claim_evidence(claim_id, capture_id, role) "
            "VALUES (%s, %s, 'establishes') "
            "ON CONFLICT (claim_id, capture_id, role) DO NOTHING",
            (claim_id, capture_id),
        )
        self.report.inserted += 1


__all__ = ["ClaimSinkReport", "PgClaimSink", "SUBJECT_SCHEME", "content_digest"]

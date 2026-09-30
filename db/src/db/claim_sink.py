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
  same string always resolves to the same entity (idempotent identity). Since
  P31.3 the resolution goes through the **identity guard**
  (:mod:`db.identity_guard`, ADR-110): the ``entity_identity_key`` primary key
  makes two concurrent sinks agree on ONE entity per subject.
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

**Batched writes** (P31.3 / ADR-110, closes D-P30.1-1): the sink used to spend
three to five round trips per claim (register the predicate, look up the subject,
insert the claim, link its evidence). Now each claim is *staged* in memory, and at
the end of its chunk the whole chunk is written with a fixed handful of multi-row
statements. The predicates go in one ``INSERT … SELECT FROM unnest``. The new
subjects go through the guard, in up to four statements. The claims go in one
``INSERT … ON CONFLICT (content_digest) DO NOTHING RETURNING`` per
``insert_batch_size`` rows. Their ``claim_evidence`` links go in one statement per
batch. Everything a claim needs still lands in the same chunk transaction as the
claim.

The connector packages must not import psycopg directly (see
``connectors/src/connectors/sinks.py``); they build a sink through that factory,
which imports this module from the ``db`` package.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import psycopg

from .identity_guard import SUBJECT_SCHEME, resolve_identity_batch
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

#: Rows per multi-row claim ``INSERT`` inside a chunk (P31.3 / ADR-110). Measured
#: (docs/build/runs/P31.3.md): 500, 2,000 and 10,000 land 100k claims within the run
#: to run noise of each other, because the write is DB-bound. They differ only in
#: round trips (474 / 174 / 94 per 100k claims), which is under 2 s at hosted
#: latency. 2,000 keeps each statement's parameter arrays bounded.
DEFAULT_INSERT_BATCH_SIZE = 2_000


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


@dataclass(frozen=True)
class EntityRef:
    """An entity named by an identity-bearing identifier, for the object seam.

    Returned by an ``object_resolver`` (P31.5). The sink resolves it through the
    identity guard, so an object entity is minted at most once per
    ``(scheme, value)``, exactly like a subject.
    """

    scheme: str
    value: str
    entity_type: str


@dataclass(frozen=True)
class DuplicateBatch:
    """The claims of one chunk whose content was already in the spine (P31.7 seam).

    Handed to ``on_duplicates`` INSIDE the chunk transaction, so anything the hook
    writes through ``conn`` commits or rolls back with the chunk.
    """

    conn: Any
    run_id: str
    #: content_digest -> the ``claim_id`` already stored for it.
    existing: Mapping[str, str]
    #: content_digest -> the ``evidence_capture`` this execution would have linked.
    capture_by_digest: Mapping[str, str]


#: Maps a claim record to the entity its object names, or ``None`` for a literal.
ObjectResolver = Callable[[Mapping[str, Any]], "EntityRef | None"]
#: Receives each chunk's already-present claims (see :class:`DuplicateBatch`).
DuplicateHook = Callable[[DuplicateBatch], None]


@dataclass(frozen=True)
class _Staged:
    """One claim, validated and resolved to its prerequisites, awaiting its chunk write."""

    digest: str
    subject: str
    predicate: str
    value_kind: str
    value_text: str | None
    value_int: str | None  # an int value as exact decimal text
    value_float: str | None  # a float value as its shortest round-trip repr
    value_bool: str | None
    raw_value: str
    observed_at: str | None
    observed_unknown_reason: str | None
    extraction_id: str
    run_id: str
    rights_id: str
    capture_id: str
    object_ref: EntityRef | None


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


# --- the chunk statements (all INSERT/SELECT; every array is passed as text[] and
# cast in SQL, so a list that happens to be all-NULL still has a type) -----------

_REGISTER_PREDICATES = (
    "INSERT INTO vocab_predicate"
    "(predicate_id, vocab_version, value_datatype, object_type, definition,"
    " volatility_class, half_life_days, resolution_strategy) "
    "SELECT p.predicate_id, %s, p.value_datatype, 'literal', p.definition, 'MODERATE', 365,"
    " 'authoritative_source_wins' "
    "FROM unnest(%s::text[], %s::text[], %s::text[])"
    " AS p(predicate_id, value_datatype, definition) "
    "ORDER BY p.predicate_id "
    "ON CONFLICT (predicate_id) DO NOTHING"
)

# The float column goes text -> float8 -> numeric: the same float8 -> numeric
# assignment cast the row-at-a-time path applied to a Python float, so the stored
# numeric is byte-identical. An int goes text -> numeric (exact), as before.
_INSERT_CLAIMS = (
    "INSERT INTO claim"
    "(subject_id, predicate_id, object_entity, object_type, value_kind, value_text,"
    " value_num, value_bool, unit, raw_value, observed_at, observed_unknown_reason,"
    " source_reliability, claim_directness, artifact_integrity, extraction_id,"
    " ingest_run_id, rights_id, sensitivity_tier, content_digest) "
    "SELECT r.subject_id::uuid, r.predicate_id, r.object_entity::uuid,"
    " CASE WHEN r.object_entity IS NULL THEN 'literal' ELSE 'entity_ref' END,"
    " r.value_kind::value_kind, r.value_text,"
    " COALESCE(r.value_int::numeric, r.value_float::float8::numeric), r.value_bool::boolean,"
    " NULL, r.raw_value, r.observed_at::timestamptz, r.observed_unknown_reason,"
    " %s, %s, %s, r.extraction_id::uuid, r.run_id::uuid, r.rights_id::uuid, 0,"
    " r.content_digest "
    "FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[]) WITH ORDINALITY AS r(subject_id, predicate_id, object_entity,"
    " value_kind, value_text, value_int, value_float, value_bool, raw_value, observed_at,"
    " observed_unknown_reason, extraction_id, run_id, rights_id, content_digest, ord) "
    "ORDER BY r.ord "
    "ON CONFLICT (content_digest) WHERE content_digest IS NOT NULL "
    "DO NOTHING RETURNING claim_id, content_digest"
)

_LINK_EVIDENCE = (
    "INSERT INTO claim_evidence(claim_id, capture_id, role) "
    "SELECT l.claim_id::uuid, l.capture_id::uuid, 'establishes' "
    "FROM unnest(%s::text[], %s::text[]) AS l(claim_id, capture_id) "
    "ON CONFLICT (claim_id, capture_id, role) DO NOTHING"
)

_EXISTING_CLAIMS = (
    "SELECT content_digest, claim_id FROM claim "
    "WHERE content_digest = ANY(%s::text[]) AND content_digest IS NOT NULL"
)


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

    **Extension points** (P31.3 / ADR-110; the behaviour is unchanged until a caller
    uses them):

    * ``on_duplicates`` receives each chunk's already-present claims with their
      stored ``claim_id``s (the P31.7 re-sighting seam). With no hook, the sink does
      not even look them up.
    * ``object_resolver`` maps a claim record to the :class:`EntityRef` its object
      names (the P31.5 entity-ref seam). The object entity is resolved through the
      identity guard and written as ``object_entity`` with ``object_type
      'entity_ref'``. With no resolver every object stays a literal.
    * **Each** :meth:`assert_claims` **call is a commit boundary** (the P31.4
      per-capture flush). Everything handed to one call has committed when it
      returns, in chunks of at most ``commit_chunk_size`` claims. Calling it once
      per capture therefore commits per capture, still under one run.
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
        insert_batch_size: int = DEFAULT_INSERT_BATCH_SIZE,
        on_duplicates: DuplicateHook | None = None,
        object_resolver: ObjectResolver | None = None,
    ) -> None:
        if commit_chunk_size < 1:
            raise ValueError(
                f"commit_chunk_size must be >= 1 (got {commit_chunk_size!r}); a chunk "
                "spans at least one claim"
            )
        if insert_batch_size < 1:
            raise ValueError(f"insert_batch_size must be >= 1 (got {insert_batch_size!r})")
        self._conn = conn
        self._connector_name = connector_name
        self._connector_version = connector_version
        self._code_commit = code_commit
        self._ruleset_version = ruleset_version
        self._vocab_version = vocab_version
        self._is_replay = is_replay
        self._commit_chunk_size = commit_chunk_size
        self._insert_batch_size = insert_batch_size
        self._on_duplicates = on_duplicates
        self._object_resolver = object_resolver
        # The execution discriminator (ADR-109): explicit = resume that execution's
        # run; absent = a fresh execution, so a fresh run.
        self._resume_execution = execution_id is not None
        self._execution_id = execution_id or uuid.uuid4().hex
        # The WORM run row the scheduled wrapper writes for this execution (gs://…),
        # recorded on the run and on its completion so the two cross-reference.
        self._run_record_uri = run_record_uri
        # Per-instance caches so prerequisites are resolved once, not per claim.
        self._run_id: str | None = None
        self._strategy_ready = False
        self._rights_by_spdx: dict[str, str] = {}
        self._known_predicates: set[str] = set()
        # (scheme, value) -> entity_id, filled through the identity guard.
        self._entity_by_key: dict[tuple[str, str], str] = {}
        # (source_id, artifact_type) -> (capture_id, extraction_id)
        self._capture_by_source: dict[tuple[str, str], tuple[str, str]] = {}
        # The open chunk: staged claims + the predicates they introduce.
        self._staged: list[_Staged] = []
        self._pending_predicates: dict[str, str] = {}
        # Cache entries added during the open chunk; undone if the chunk rolls back.
        self._journal: list[tuple[Any, Any]] = []
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
        deadline rolls back whole. Each claim is staged by ``_insert_claim``, and
        the chunk's staged claims are written together, with all their
        prerequisite and evidence rows, before the chunk commits. So a claim and
        everything it needs land in the SAME chunk transaction, and a chunk
        boundary never bisects a claim (append-only invariant, root AGENTS.md §5).
        Because every write is content-keyed ``ON CONFLICT DO NOTHING``, chunks
        that already committed dedupe to +0 on a re-run, so an interrupted run
        (chunks 1..k committed, process dies) is safe to resume: the re-walk tops
        up from where it stopped and reaches the same final count. The default
        leaves every ordinary source committing in one chunk — unchanged behaviour.

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
            self._journal.clear()
            exhausted = self._chunk_exhausted

    def _chunk_snapshot(self) -> tuple[Any, ...]:
        # The id caches are journaled (undo on rollback) instead of copied, so a
        # chunk costs O(its own additions), not O(everything cached so far).
        self._journal.clear()
        return (
            self._run_id,
            self._strategy_ready,
            self.report.inserted,
            self.report.duplicates,
            self.report.entities,
        )

    def _restore_chunk_snapshot(self, snapshot: tuple[Any, ...]) -> None:
        (
            self._run_id,
            self._strategy_ready,
            self.report.inserted,
            self.report.duplicates,
            self.report.entities,
        ) = snapshot
        for cache, key in reversed(self._journal):
            if isinstance(cache, set):
                cache.discard(key)
            else:
                cache.pop(key, None)
        self._journal.clear()
        self._staged = []
        self._pending_predicates = {}

    def _remember(self, cache: dict[Any, Any], key: Any, value: Any) -> None:
        cache[key] = value
        self._journal.append((cache, key))

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
                    # Chunk full — write it, then close this transaction (the
                    # `with` commits on exit) and open a fresh one for the next.
                    break
            else:
                # The `for` ran to exhaustion without breaking: this is the
                # final (possibly partial / empty) chunk.
                self._chunk_exhausted = True
            self._write_chunk()

    # --- prerequisites (all INSERT ... ON CONFLICT DO NOTHING, append-only) ----

    def _ensure_resolution_strategy(self, strategy_id: str) -> None:
        self._conn.execute(
            "INSERT INTO vocab_resolution_strategy(strategy_id, definition) "
            "VALUES (%s, %s) ON CONFLICT (strategy_id) DO NOTHING",
            (strategy_id, "connector-asserted claim (P19.4 PgClaimSink)"),
        )

    def _register_predicates(self) -> None:
        """Register the chunk's new predicates in one statement (cached per sink)."""
        pending = self._pending_predicates
        if not pending:
            return
        self._pending_predicates = {}
        if not self._strategy_ready:
            self._ensure_resolution_strategy("authoritative_source_wins")
            self._strategy_ready = True
        ids = sorted(pending)
        self._conn.execute(
            _REGISTER_PREDICATES,
            (
                self._vocab_version,
                ids,
                [pending[p] for p in ids],
                [f"connector predicate {p!r} (registered by PgClaimSink)" for p in ids],
            ),
        )
        for predicate in ids:
            self._known_predicates.add(predicate)
            self._journal.append((self._known_predicates, predicate))

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
            self._remember(self._rights_by_spdx, spdx, str(row[0]))
            return str(row[0])
        redistributable = "UNDETERMINED" if spdx == "UNDETERMINED" else "yes"
        inserted = self._conn.execute(
            "INSERT INTO rights_record"
            "(spdx_expression, attribution_text, redistributable, derivative_permitted,"
            " retrieval_date) VALUES (%s, %s, %s, %s, %s) RETURNING rights_id",
            (spdx, attribution, redistributable, redistributable, date.today()),
        ).fetchone()
        assert inserted is not None
        self._remember(self._rights_by_spdx, spdx, str(inserted[0]))
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
        self._remember(self._capture_by_source, cache_key, (capture_id, extraction_id))
        return capture_id, extraction_id

    def _resolve_entities(self, refs: Sequence[tuple[str, str, str]]) -> dict[tuple[str, str], str]:
        """Resolve ``(scheme, value, entity_type)`` refs to entities through the guard.

        Cached per sink: refs seen before cost nothing, and the rest go through ONE
        guarded pass (:func:`db.identity_guard.resolve_identity_batch`). One pass for
        subjects and objects together keeps a single global key order, so concurrent
        sinks cannot deadlock. It runs only inside a chunk transaction, whose rollback
        undoes the cache entries (journaled). Entities it mints count in
        ``report.entities``.
        """
        missing = [r for r in refs if (r[0], r[1]) not in self._entity_by_key]
        if missing:
            result = resolve_identity_batch(self._conn, missing)
            for key, entity_id in result.entity_by_key.items():
                self._remember(self._entity_by_key, key, entity_id)
            self.report.entities += len(result.minted)
        return {(r[0], r[1]): self._entity_by_key[(r[0], r[1])] for r in refs}

    # --- the L1 claim write ----------------------------------------------------

    def _insert_claim(self, claim: Mapping[str, Any]) -> None:
        """Stage one claim for its chunk's batched write.

        Resolves the claim's per-run prerequisites (rights, source, evidence chain,
        run), which are cached, and computes its row. The subject entity, the
        predicate registration, the claim row and its evidence link are written
        for the whole chunk by :meth:`_write_chunk`, inside the same transaction.
        """
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
        if predicate not in self._known_predicates:
            self._pending_predicates.setdefault(predicate, _value_datatype(value))
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
        value_int: str | None = None
        value_float: str | None = None
        value_bool: str | None = None
        if value is not None:
            value_kind = "value"
            value_text: str | None = str(value)
            if isinstance(value, bool):
                value_bool = "true" if value else "false"
            elif isinstance(value, int):
                value_int = str(int(value))  # int() normalises an int subclass
            elif isinstance(value, float):
                # The shortest round-trip text of the double, which float8 parses
                # back to the same double. float() normalises a float subclass
                # (e.g. numpy.float64), whose repr is not a number.
                value_float = repr(float(value))
        elif raw_field is not None and str(raw_field) != "":
            value_kind = "value"
            value_text = str(raw_field)
        else:
            # A connector row that asserts a subject/predicate with no value yet
            # (§16.2 'novalue'): every value_* column stays null.
            value_kind = "novalue"
            value_text = None
        object_ref = self._object_resolver(claim) if self._object_resolver is not None else None
        if object_ref is not None and (not object_ref.value or value_kind == "novalue"):
            # An entity reference needs a named entity and a value to stand for:
            # without either the claim stays a literal (claim_value_shape).
            object_ref = None
        self._staged.append(
            _Staged(
                digest=content_digest(claim),
                subject=subject,
                predicate=predicate,
                value_kind=value_kind,
                value_text=value_text,
                value_int=value_int,
                value_float=value_float,
                value_bool=value_bool,
                raw_value=raw_value,
                observed_at=observed_at.isoformat() if observed_at is not None else None,
                observed_unknown_reason=observed_unknown_reason,
                extraction_id=extraction_id,
                run_id=run_id,
                rights_id=rights_id,
                capture_id=capture_id,
                object_ref=object_ref,
            )
        )

    def _write_chunk(self) -> None:
        """Write the open chunk's staged claims (inside its transaction).

        Predicates first, then subject and object entities through the identity
        guard, then the claims ``ON CONFLICT (content_digest) DO NOTHING`` in
        ``insert_batch_size`` slices, each followed by the ``claim_evidence`` links
        of the rows it inserted. The counters are exact. A claim the spine already
        held, or one repeated earlier in the same chunk, is a duplicate, just as in
        the row-at-a-time path.
        """
        staged, self._staged = self._staged, []
        if not staged:
            return
        self._register_predicates()
        refs: dict[tuple[str, str], tuple[str, str, str]] = {}
        for s in staged:
            subject_key = (SUBJECT_SCHEME, s.subject)
            refs.setdefault(subject_key, (*subject_key, _DEFAULT_ENTITY_TYPE))
            if s.object_ref is not None:
                o = s.object_ref
                refs.setdefault((o.scheme, o.value), (o.scheme, o.value, o.entity_type))
        entity_ids = self._resolve_entities(list(refs.values()))

        # Within one chunk the first occurrence of a digest is the one written.
        unique: list[_Staged] = []
        seen: set[str] = set()
        for s in staged:
            if s.digest not in seen:
                seen.add(s.digest)
                unique.append(s)

        inserted: dict[str, str] = {}
        batch = self._insert_batch_size
        for start in range(0, len(unique), batch):
            part = unique[start : start + batch]
            rows = self._conn.execute(
                _INSERT_CLAIMS,
                (
                    _DEFAULT_RELIABILITY,
                    _DEFAULT_DIRECTNESS,
                    _DEFAULT_INTEGRITY,
                    [entity_ids[(SUBJECT_SCHEME, s.subject)] for s in part],
                    [s.predicate for s in part],
                    [
                        entity_ids[(s.object_ref.scheme, s.object_ref.value)]
                        if s.object_ref is not None
                        else None
                        for s in part
                    ],
                    [s.value_kind for s in part],
                    [s.value_text for s in part],
                    [s.value_int for s in part],
                    [s.value_float for s in part],
                    [s.value_bool for s in part],
                    [s.raw_value for s in part],
                    [s.observed_at for s in part],
                    [s.observed_unknown_reason for s in part],
                    [s.extraction_id for s in part],
                    [s.run_id for s in part],
                    [s.rights_id for s in part],
                    [s.digest for s in part],
                ),
            ).fetchall()
            if not rows:
                continue
            # Link each new claim to its establishing capture (§16.5).
            capture_of = {s.digest: s.capture_id for s in part}
            new = {str(r[1]): str(r[0]) for r in rows}
            self._conn.execute(_LINK_EVIDENCE, (list(new.values()), [capture_of[d] for d in new]))
            inserted.update(new)
        self.report.inserted += len(inserted)
        self.report.duplicates += len(staged) - len(inserted)

        if self._on_duplicates is not None:
            self._report_duplicates(unique, inserted)

    def _report_duplicates(self, unique: Sequence[_Staged], inserted: Mapping[str, str]) -> None:
        dup = [s for s in unique if s.digest not in inserted]
        if not dup or self._on_duplicates is None:
            return
        rows = self._conn.execute(_EXISTING_CLAIMS, ([s.digest for s in dup],)).fetchall()
        existing = {str(r[0]): str(r[1]) for r in rows}
        run_id = self._ensure_run()
        self._on_duplicates(
            DuplicateBatch(
                conn=self._conn,
                run_id=run_id,
                existing=existing,
                capture_by_digest={s.digest: s.capture_id for s in dup},
            )
        )


__all__ = [
    "DEFAULT_COMMIT_CHUNK_SIZE",
    "DEFAULT_INSERT_BATCH_SIZE",
    "ClaimSinkReport",
    "DuplicateBatch",
    "DuplicateHook",
    "EntityRef",
    "ObjectResolver",
    "PgClaimSink",
    "SUBJECT_SCHEME",
    "content_digest",
]

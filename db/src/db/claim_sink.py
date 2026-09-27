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
* **Entity-ref objects** (P31.5 / ADR-112) — a record that carries an
  ``object_ref`` (a connector's ``link()`` stage adds one to a partner claim) is
  written with ``object_type='entity_ref'`` and an ``object_entity``: an
  ``organization`` minted through the same guard, labelled by one
  ``organization`` row. Every other record stays a literal. A ``person`` object is
  refused (Part VIII).
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

**Re-sightings** (P31.7 / ADR-R9-RESIGHT): a duplicate claim is still recorded —
the ``on_duplicates`` hook reports each chunk's already-present claims inside the
chunk transaction, and the production hook :func:`record_resightings` appends one
``claim_evidence`` link per re-sighted claim to the execution's own synthetic
capture. Every sighting stays evidenced, so a restated value's capture-dating
(``capture_retrieved_at_latest``) reflects when the source last asserted it.

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
import logging
import os
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any

import psycopg

from .assertion import (
    ASSERTION_MAP_ID,
    BINDING_LEGACY,
    BINDING_REPLAYED,
    CAPTURE_ACTUAL,
    CaptureBinding,
    QuarantineReason,
    Rejection,
    TypedAssertion,
    assertion_from_record,
    binding_of,
    quarantine_payload,
)
from .identity_guard import PARTNER_NAME_SCHEME, SUBJECT_SCHEME, resolve_identity_batch
from .run_completion import SUCCESSFUL_STATUSES, append_completion

_log = logging.getLogger(__name__)

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
    #: Records the adapter failed closed into ``assertion_quarantine`` (P32.2):
    #: unknown types, bad digests, missing bindings — never silently dropped.
    quarantined: int = 0


@dataclass(frozen=True)
class EntityRef:
    """An entity named by an identity-bearing identifier, for the object seam.

    Returned by an ``object_resolver`` (P31.5). The sink resolves it through the
    identity guard, so an object entity is minted at most once per
    ``(scheme, value)``, exactly like a subject. ``label`` (optional, P31.5 /
    ADR-112) is the display name an ``organization`` object is first seen under;
    the sink records it once as the organisation's ``cached_canonical_name``, and
    ``rules`` (the identity ruleset version that decided it) in its immutable
    ``identity_basis``.
    """

    scheme: str
    value: str
    entity_type: str
    label: str | None = None
    rules: str | None = None


#: The object entity types the sink never mints (Part VIII). A person entity needs
#: the §43.4 two-reviewer record; no connector record may create one.
_REFUSED_OBJECT_TYPES = frozenset({"person"})

#: The ``organization.organization_type`` of a partner organisation minted from a
#: connector record (ADR-112): the record names the party, not its class, so the
#: class is recorded as unclassified rather than guessed.
PARTNER_ORGANIZATION_TYPE = "unclassified"


def record_object_ref(claim: Mapping[str, Any]) -> EntityRef | None:
    """The production ``object_resolver`` (P31.5 / ADR-112).

    Reads the ``object_ref`` a connector's ``link()`` stage attached to an
    entity-ref claim record (``{"scheme", "value", "entity_type", "label"}``). A
    record without one, such as every text claim, stays a literal. The identity
    decision itself (scheme, normalization, the never-a-person rule) is made
    upstream by ``resolution.partner_identity``. This function only carries it,
    and refuses a person object outright (Part VIII) instead of minting one.
    """
    ref = claim.get("object_ref")
    if not ref:
        return None
    if not isinstance(ref, Mapping):
        raise ValueError(f"object_ref must be a mapping, got {type(ref).__name__}")
    scheme = str(ref.get("scheme") or "")
    value = str(ref.get("value") or "")
    entity_type = str(ref.get("entity_type") or "")
    if not scheme or not value or not entity_type:
        raise ValueError("object_ref needs a scheme, a value and an entity_type")
    if entity_type in _REFUSED_OBJECT_TYPES:
        raise ValueError(
            f"object_ref names a {entity_type!r} entity; the sink never mints one (Part VIII)"
        )
    label = ref.get("label")
    rules = ref.get("rules")
    return EntityRef(
        scheme, value, entity_type, str(label) if label else None, str(rules) if rules else None
    )


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
    #: True when this execution is an ``is_replay`` run (ADR-113). A replay
    #: re-derives stored bytes — it is not the source re-asserting the value — so
    #: the production re-sighting hook (:func:`record_resightings`) writes nothing
    #: for it. Other hooks may ignore the flag.
    replay: bool = False
    #: content_digest -> (extraction_id, locator_json, config_digest,
    #: extractor_version, binding_status) of this execution's binding (P32.2):
    #: populated when the claims were asserted against an actual capture, so a
    #: re-sighting's link carries the same typed provenance as its sighting —
    #: never ``legacy_synthetic`` for a real capture.
    binding_by_digest: Mapping[str, tuple[str | None, str | None, str | None, str | None, str]] = (
        field(default_factory=dict)
    )


def record_resightings(batch: DuplicateBatch) -> None:
    """The production ``on_duplicates`` hook (P31.7 / ADR-R9-RESIGHT).

    Every live execution that re-asserts a claim the spine already holds records
    the re-sighting: one ``claim_evidence`` row (role ``establishes``) linking the
    existing claim to THIS execution's capture. The link is the primary evidence
    that the source was seen asserting the value again, which is what the
    resolver's latest-capture dating (``capture_retrieved_at_latest``) reads —
    without it, an A → B → A restatement keeps A's original capture date and
    ``latest_observation_wins`` wrongly prefers B.

    Uncapped and unfiltered (the ratified operator decision, ADR-R9-RESIGHT):
    every duplicate claim in the batch is linked, with no cadence window and no
    digest-changed filter. The write reuses ``_LINK_EVIDENCE`` — one statement per
    chunk, ``ON CONFLICT (claim_id, capture_id, role) DO NOTHING`` — so the same
    capture re-asserted twice (a resumed execution re-flushing a target) links +0.
    One link per (claim, capture): the per-``(source, genre, run)`` synthetic
    capture means at most one link per claim per execution per genre.

    A replay run (``batch.replay``) writes nothing: a replay re-reads stored
    bytes; it is not the source re-asserting the value, so its captured
    ``retrieved_at`` (the replay execution time) must never be treated as a
    fresh sighting of the source.
    """
    if batch.replay or not batch.existing:
        return
    if batch.binding_by_digest:
        # Typed path (P32.2): the re-sighting binds THIS execution's actual
        # capture occurrence with the same binding classification as a first
        # sighting — the sighting evidence is real captured bytes, not a
        # synthetic placeholder.
        rows = [
            (claim_id, batch.capture_by_digest[d], *batch.binding_by_digest[d])
            for d, claim_id in batch.existing.items()
            if d in batch.capture_by_digest and d in batch.binding_by_digest
        ]
        if not rows:
            return
        batch.conn.execute(
            _LINK_EVIDENCE_TYPED,
            (
                [r[0] for r in rows],
                [r[1] for r in rows],
                [r[2] for r in rows],
                ["establishes"] * len(rows),
                [r[3] for r in rows],
                [r[4] for r in rows],
                [r[5] for r in rows],
                [r[6] for r in rows],
            ),
        )
        return
    pairs = [
        (claim_id, batch.capture_by_digest[digest])
        for digest, claim_id in batch.existing.items()
        if digest in batch.capture_by_digest
    ]
    if not pairs:
        return
    batch.conn.execute(
        _LINK_EVIDENCE,
        ([claim_id for claim_id, _ in pairs], [capture_id for _, capture_id in pairs]),
    )


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
    extraction_id: str
    run_id: str
    rights_id: str
    capture_id: str
    object_ref: EntityRef | None
    #: The ``sig.assertion/1`` envelope the record was adapted into (P32.2) —
    #: every typed field the claim row preserves, plus the default-provenance
    #: map (``typed.defaulted``) stamped on the row.
    typed: TypedAssertion


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
# P32.2 (SIG-TRUST-001): every typed field the envelope carries now lands on the
# row — unit, value_json, raw_context, normalization, valid/observed-time
# kinds + edtf, the R/D/I epistemic axes (per-claim, no longer run defaults),
# polarity/rank/review_status, sensitivity_tier, the correction/derivation
# links, and the named versioned default mapping + explicit basis.
_INSERT_CLAIMS = (
    "INSERT INTO claim"
    "(subject_id, predicate_id, object_entity, object_type, value_kind, value_text,"
    " value_num, value_bool, value_json, unit, raw_value, raw_context,"
    " normalization_id, normalization_version,"
    " valid_period, valid_edtf, valid_from_kind, valid_to_kind,"
    " observed_at, observed_edtf, observed_at_kind, observed_unknown_reason,"
    " source_reliability, reliability_provisional, claim_directness,"
    " artifact_integrity, legacy_source_tier, claim_polarity, rank, review_status,"
    " assertion_rationale, derived_from_claim_ids, revises_claim, retraction_of,"
    " correction_reason,"
    " extraction_id, ingest_run_id, rights_id, sensitivity_tier, content_digest,"
    " assertion_map_id, assertion_map_basis) "
    "SELECT r.subject_id::uuid, r.predicate_id, r.object_entity::uuid,"
    " r.object_type, r.value_kind::value_kind, r.value_text,"
    " COALESCE(r.value_int::numeric, r.value_float::float8::numeric), r.value_bool::boolean,"
    " r.value_json::jsonb, r.unit, r.raw_value, r.raw_context::jsonb,"
    " r.normalization_id, r.normalization_version,"
    " tstzrange(r.valid_from::timestamptz, r.valid_to::timestamptz, '[)'),"
    " r.valid_edtf, r.valid_from_kind, r.valid_to_kind,"
    " r.observed_at::timestamptz, r.observed_edtf, r.observed_at_kind,"
    " r.observed_unknown_reason,"
    " r.source_reliability, r.reliability_provisional::boolean, r.claim_directness,"
    " r.artifact_integrity, r.legacy_source_tier, r.claim_polarity,"
    " r.rank::claim_rank, r.review_status::review_status,"
    " r.assertion_rationale,"
    " CASE WHEN r.derived IS NULL THEN NULL ELSE ('{' || r.derived || '}')::uuid[] END,"
    " r.revises_claim::uuid, r.retraction_of::uuid, r.correction_reason,"
    " r.extraction_id::uuid, r.run_id::uuid, r.rights_id::uuid,"
    " r.sensitivity_tier::smallint, r.content_digest,"
    " r.assertion_map_id, r.assertion_map_basis "
    "FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[]) WITH ORDINALITY AS r("
    " subject_id, predicate_id, object_entity, object_type, value_kind, value_text,"
    " value_int, value_float, value_bool, value_json, unit, raw_value, raw_context,"
    " normalization_id, normalization_version, valid_from, valid_to, valid_edtf,"
    " valid_from_kind, valid_to_kind, observed_at, observed_edtf, observed_at_kind,"
    " observed_unknown_reason, source_reliability, reliability_provisional,"
    " claim_directness, artifact_integrity, legacy_source_tier, claim_polarity, rank,"
    " review_status, assertion_rationale, derived, revises_claim, retraction_of,"
    " correction_reason, extraction_id, run_id, rights_id, sensitivity_tier,"
    " content_digest, assertion_map_id, assertion_map_basis, ord) "
    "ORDER BY r.ord "
    "ON CONFLICT (content_digest) WHERE content_digest IS NOT NULL "
    "DO NOTHING RETURNING claim_id, content_digest"
)

# A partner organisation's identity row (ADR-112): its first-seen display name as
# ``cached_canonical_name`` so read surfaces label it, the identity decision as its
# immutable ``identity_basis`` (SIG-IDENT-012), and the SIG-ONTO-013 review flag for a
# body known only by name. ``ON CONFLICT DO NOTHING`` keeps the first row: nothing
# here ever rewrites an organisation. Only entities that really are organisations get
# a row (an identifier a different writer keyed to another entity type gets none).
_PARTNER_ORGANIZATIONS = (
    "INSERT INTO organization"
    "(entity_id, organization_type, identity_basis, cached_canonical_name,"
    " publication_review_required) "
    "SELECT o.entity_id::uuid, %s, o.basis::jsonb, o.label, o.review::boolean "
    "FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[])"
    " AS o(entity_id, basis, label, review) "
    "JOIN entity e ON e.entity_id = o.entity_id::uuid AND e.entity_type = 'organization' "
    "ORDER BY o.entity_id "
    "ON CONFLICT (entity_id) DO NOTHING"
)

_LINK_EVIDENCE = (
    "INSERT INTO claim_evidence(claim_id, capture_id, role) "
    "SELECT l.claim_id::uuid, l.capture_id::uuid, 'establishes' "
    "FROM unnest(%s::text[], %s::text[]) AS l(claim_id, capture_id) "
    "ON CONFLICT (claim_id, capture_id, role) DO NOTHING"
)

# P32.2 (SIG-TRUST-002): the typed link — same (claim, capture, role) identity,
# plus the extraction that consumed the capture, the typed locator, the
# extractor/config identity, and the binding classification. bound_at defaults
# to the DB clock (the assertion time, not the observation time).
_LINK_EVIDENCE_TYPED = (
    "INSERT INTO claim_evidence"
    "(claim_id, capture_id, extraction_id, role, locator,"
    " extraction_config_digest, extractor_version, binding_status) "
    "SELECT l.claim_id::uuid, l.capture_id::uuid, l.extraction_id::uuid, l.role,"
    " l.locator::jsonb, l.config_digest, l.extractor_version, l.binding_status "
    "FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[]) AS l(claim_id, capture_id, extraction_id,"
    " role, locator, config_digest, extractor_version, binding_status) "
    "ON CONFLICT (claim_id, capture_id, role) DO NOTHING"
)

# P32.2: typed qualifier rows (the previously unwritten claim_qualifier surface).
_INSERT_QUALIFIERS = (
    "INSERT INTO claim_qualifier"
    "(claim_id, qualifier_id, value_text, value_num, value_bool, value_entity,"
    " unit, jurisdiction, valid_from, valid_to, extraction_id, rank) "
    "SELECT q.claim_id::uuid, q.qualifier_id, q.value_text, q.value_num::numeric,"
    " q.value_bool::boolean, q.value_entity::uuid, q.unit, q.jurisdiction,"
    " q.valid_from::date, q.valid_to::date, q.extraction_id::uuid, q.rank "
    "FROM unnest(%s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[], %s::text[], %s::text[], %s::text[], %s::text[], %s::text[],"
    " %s::text[]) AS q(claim_id, qualifier_id, value_text, value_num, value_bool,"
    " value_entity, unit, jurisdiction, valid_from, valid_to, extraction_id, rank) "
    "ON CONFLICT DO NOTHING"
)

# P32.2: the fail-closed landing for a rejected assertion. payload_digest makes
# a re-run +0; the row is immutable (trigger) and never public-readable.
_QUARANTINE = (
    "INSERT INTO assertion_quarantine"
    "(run_id, reason, connector_name, source_id, subject_ref, predicate_id,"
    " payload, payload_digest) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s) "
    "ON CONFLICT (payload_digest) DO NOTHING RETURNING quarantine_id"
)

# P32.2: the actual-capture occurrence. The artifact is keyed by the source's
# real URI (not the sig:connector:* synthetic locator); the blob dedups bytes
# (one blob row, N immutable capture occurrence rows); the capture row itself
# is the immutable occurrence — replay resolves the ORIGINAL row by
# (artifact, digest, retrieved_at) rather than asserting a new one.
_ACTUAL_ARTIFACT = (
    "INSERT INTO evidence_artifact"
    "(source_id, url, stable_locator, artifact_type, acquisition_method,"
    " primary_or_secondary, rights_id, capture_status) "
    "VALUES (%s, %s, %s, %s, %s, 'primary', %s, 'captured') "
    "ON CONFLICT (source_id, stable_locator) DO NOTHING RETURNING artifact_id"
)
_ACTUAL_ARTIFACT_ID = (
    "SELECT artifact_id FROM evidence_artifact WHERE source_id = %s AND stable_locator = %s"
)
_ACTUAL_BLOB = (
    "INSERT INTO evidence_blob"
    "(blob_digest, source_uri, byte_size, ocfl_object_id, ocfl_version) "
    "VALUES (%s, %s, %s, %s, %s) ON CONFLICT (blob_digest, source_uri) DO NOTHING"
)
_CAPTURE_OCCURRENCE = (
    "SELECT capture_id, ocfl_version FROM evidence_capture "
    "WHERE artifact_id = %s AND content_digest = %s AND retrieved_at = %s "
    "ORDER BY capture_id LIMIT 1"
)
_INSERT_OCCURRENCE = (
    "INSERT INTO evidence_capture"
    "(artifact_id, content_digest, byte_size, media_type, retrieved_at,"
    " retrieved_by_run_id, ocfl_object_id, ocfl_version, storage_tier,"
    " capture_method, capture_tool_version, source_uri, blob_digest,"
    " capture_classification) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'public', %s, %s, %s, %s, %s) "
    "RETURNING capture_id"
)
_EXTRACTION_OF = (
    "SELECT extraction_id FROM extraction "
    "WHERE capture_id = %s AND run_id = %s AND method = %s "
    "ORDER BY extracted_at LIMIT 1"
)
_INSERT_EXTRACTION = (
    "INSERT INTO extraction"
    "(capture_id, method, extractor_name, extractor_version, normalizer_version,"
    " model_id, prompt_version, parameters, run_id) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s) RETURNING extraction_id"
)

# vocab_normalization mirrors the vocab_predicate auto-registration posture: a
# connector-declared normalization id registers (it names WHAT was applied, an
# honest provenance record) instead of failing the claim on the FK.
_REGISTER_NORMALIZATIONS = (
    "INSERT INTO vocab_normalization(normalization_id, definition) "
    "SELECT n.normalization_id, 'connector-declared normalization' "
    "FROM unnest(%s::text[]) AS n(normalization_id) "
    "ON CONFLICT (normalization_id) DO NOTHING"
)

#: The marks a restarted execution resumes from (P31.4 / ADR-111): those of the
#: executions of the same logical run — same connector name, version AND code
#: commit (the rolled image digest on hosted), so a restart on different code
#: never keeps pages the old code derived — that started after the last one that
#: completed. Per target, a ``flushed`` mark wins over a ``captured`` one, and the
#: latest mark of a state wins. A backfilled completion (P31.2) never names a
#: logical run, so only live completions close one.
_RESUME_MARKS = (
    "WITH runs AS ("
    " SELECT run_id, started_at FROM ingest_run"
    " WHERE connector_name = %(connector)s AND connector_version = %(version)s"
    " AND code_commit = %(code_commit)s"
    " AND parameters ->> 'logical_run' = %(logical_run)s AND NOT is_replay"
    " AND run_id IS DISTINCT FROM %(current)s::uuid"
    "), done AS ("
    " SELECT max(r.started_at) AS at FROM runs r"
    " JOIN ingest_run_completion c ON c.run_id = r.run_id"
    " WHERE c.backfilled_from IS NULL AND c.status = ANY(%(successful)s::text[])"
    ") "
    "SELECT DISTINCT ON (m.target_key) m.target_key, m.state, m.capture_digest, m.source_uri,"
    " m.media_type, m.byte_size, m.retrieved_at, m.records,"
    " m.ocfl_object_id, m.ocfl_version, m.run_id::text "
    "FROM ingest_run_capture m JOIN runs r ON r.run_id = m.run_id "
    "WHERE r.started_at > COALESCE((SELECT at FROM done), '-infinity'::timestamptz) "
    "ORDER BY m.target_key, (m.state = 'flushed') DESC, m.recorded_at DESC"
)

_RECORD_CAPTURE = (
    "INSERT INTO ingest_run_capture(run_id, target_key, state, capture_digest, source_uri,"
    " media_type, byte_size, retrieved_at, records, ocfl_object_id, ocfl_version) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
    "ON CONFLICT (run_id, target_key, state) DO NOTHING"
)

#: The two capture-mark states (the ``ingest_run_capture`` CHECK constraint).
CAPTURE_MARK_STATES = ("captured", "flushed")

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
      not even look them up. The production wiring is
      :func:`record_resightings` (ADR-R9-RESIGHT): it appends one ``claim_evidence``
      link per re-sighted claim to the execution's own capture, inside the chunk
      transaction — uncapped, idempotent on ``(claim, capture, role)``, and silent
      on ``is_replay`` runs (a replay re-reads stored bytes; it is not a fresh
      sighting of the source).
    * ``object_resolver`` maps a claim record to the :class:`EntityRef` its object
      names (the P31.5 entity-ref seam). The object entity is resolved through the
      identity guard and written as ``object_entity`` with ``object_type
      'entity_ref'``. With no resolver every object stays a literal.
    * **Each** :meth:`assert_claims` **call is a commit boundary** (the P31.4
      per-capture flush). Everything handed to one call has committed when it
      returns, in chunks of at most ``commit_chunk_size`` claims. Calling it once
      per capture therefore commits per capture, still under one run.

    **Resume** (P31.4 / ADR-111): a sink built with a ``logical_run`` key (source +
    cadence window) records it in ``ingest_run.parameters`` and implements the
    :class:`connectors.stages.CaptureLedger` protocol. :meth:`record_capture`
    appends a per-target ``ingest_run_capture`` mark, and :meth:`resume_marks`
    returns the marks an interrupted execution of the same logical run left.
    Without a ``logical_run`` the sink records no marks and resumes nothing.
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
        logical_run: str | None = None,
        extra_parameters: Mapping[str, str] | None = None,
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
        # P31.4 / ADR-111: the logical run (source + cadence window) this execution
        # belongs to. Its executions share it; a restart resumes their marks.
        self._logical_run = logical_run or None
        # P31.6 / ADR-113: extra string-valued run parameters merged into
        # ``ingest_run.parameters`` (e.g. an asserting replay's ``replay_of``
        # lineage — the run ids its captures came from). Keys the sink already
        # owns (execution_id / run_record_uri / logical_run) cannot be shadowed.
        self._extra_parameters = dict(extra_parameters or {})
        # Per-instance caches so prerequisites are resolved once, not per claim.
        self._run_id: str | None = None
        self._strategy_ready = False
        self._rights_by_spdx: dict[str, str] = {}
        self._known_predicates: set[str] = set()
        # (scheme, value) -> entity_id, filled through the identity guard.
        self._entity_by_key: dict[tuple[str, str], str] = {}
        # Partner organisations whose ``organization`` row this sink has written.
        self._org_rows: set[str] = set()
        # (source_id, artifact_type) -> (capture_id, extraction_id)
        self._capture_by_source: dict[tuple[str, str], tuple[str, str]] = {}
        # The open chunk: staged claims + the predicates they introduce.
        self._staged: list[_Staged] = []
        self._pending_predicates: dict[str, str] = {}
        # P32.2: the binding of the in-flight assert_claims call — the actual
        # CaptureBinding, a Rejection (the whole call fails closed into
        # quarantine), or None (the legacy synthetic path).
        self._active_binding: CaptureBinding | Rejection | None = None
        # (capture_id, method, config_digest) -> extraction_id, per run.
        self._extraction_by_key: dict[tuple[str, str, str | None], str] = {}
        # (source_uri) -> artifact_id of the real-capture artifact.
        self._artifact_by_uri: dict[tuple[str, str], str] = {}
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

    def assert_claims(self, claims: Sequence[Mapping[str, Any]], *, capture: Any = None) -> None:
        """Persist ``claims`` append-only and idempotently (the L1 write path).

        P32.2 (SIG-TRUST-002): ``capture`` is the actual :class:`CaptureRef` the
        extractor consumed. When given, every claim binds that capture
        occurrence — digest, source URI, byte size, retrieval time, OCFL
        object/version — instead of the synthetic per-run placeholder the
        pre-P32.2 sink invented. A binding that cannot be normalised fails
        closed: every record of the call quarantines with the rejection reason,
        and nothing is silently written against the wrong provenance. Without
        ``capture`` the legacy path still lands claims, but their
        ``claim_evidence`` links are honestly classified ``legacy_synthetic``
        (and the synthetic capture ``synthetic``) — never mistaken for real
        byte provenance.


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
        self._active_binding = (
            binding_of(capture, replayed=self._is_replay) if capture is not None else None
        )
        remaining = iter(claims)
        exhausted = False
        try:
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
        finally:
            self._active_binding = None

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
        if self._logical_run:
            parameters["logical_run"] = self._logical_run
        for key, value in self._extra_parameters.items():
            parameters.setdefault(key, value)
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

    # --- resume (P31.4 / ADR-111) ----------------------------------------------

    @property
    def logical_run(self) -> str | None:
        """The logical run key (source + cadence window), or ``None`` (no resume)."""
        return self._logical_run

    def resume_marks(self) -> list[dict[str, Any]]:
        """The capture marks an interrupted execution of this logical run left.

        One mark per target key: ``flushed`` if any resumable execution flushed the
        target, else its latest ``captured`` mark. Empty without a logical run, or
        once an execution of the logical run completed (the next one is a fresh
        run and never skips). Read-only.
        """
        if not self._logical_run or self._is_replay:
            return []
        try:
            rows = self._conn.execute(
                _RESUME_MARKS,
                {
                    "connector": self._connector_name,
                    "version": self._connector_version,
                    "code_commit": self._code_commit,
                    "logical_run": self._logical_run,
                    "current": self._run_id,
                    "successful": list(SUCCESSFUL_STATUSES),
                },
            ).fetchall()
        except psycopg.errors.UndefinedTable:
            # A spine without the ``ingest_run_capture`` change (an image rolled
            # ahead of its schema): run without resume rather than fail the ingest.
            _log.warning("ingest_run_capture is absent; running without resume (ADR-111)")
            self._logical_run = None
            return []
        keys = (
            "target_key",
            "state",
            "capture_digest",
            "source_uri",
            "media_type",
            "byte_size",
            "retrieved_at",
            "records",
            "ocfl_object_id",
            "ocfl_version",
            "run_id",
        )
        return [dict(zip(keys, row, strict=True)) for row in rows]

    def record_capture(
        self,
        target_key: str,
        *,
        state: str,
        capture_digest: str,
        source_uri: str,
        media_type: str,
        byte_size: int,
        retrieved_at: datetime | None = None,
        records: int | None = None,
        ocfl_object_id: str | None = None,
        ocfl_version: str | None = None,
    ) -> None:
        """Append this execution's ``state`` mark for one fetch target (append-only).

        The ``ocfl_*`` pair (P32.2) names the immutable store occurrence the
        mark's bytes were committed under, so a later resume or replay binds
        THAT version, never whatever a re-fetch moved ``head`` to.

        ``captured`` is written once the target's bytes are in the capture store;
        ``flushed`` once every claim of the capture has committed, with the number
        of records the capture emitted. A no-op without a logical run. A second
        mark of the same state for the same target is +0.
        """
        if not self._logical_run:
            return
        if state not in CAPTURE_MARK_STATES:
            raise ValueError(f"capture mark state {state!r} is not one of {CAPTURE_MARK_STATES}")
        if (state == "flushed") != (records is not None):
            raise ValueError("a flushed mark carries its record count; a captured mark none")
        run_id = self._ensure_run()
        self._conn.execute(
            _RECORD_CAPTURE,
            (
                run_id,
                target_key,
                state,
                capture_digest,
                source_uri,
                media_type,
                byte_size,
                retrieved_at,
                records,
                ocfl_object_id,
                ocfl_version,
            ),
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
                " capture_method, capture_tool_version, source_uri, blob_digest,"
                " capture_classification) "
                "VALUES (%s, %s, 0, 'application/octet-stream', clock_timestamp(), %s,"
                " %s, 'v1', 'public', 'connector', %s, %s, %s, 'synthetic') RETURNING capture_id",
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

        P32.2 (SIG-TRUST-001/002): the record is first adapted into the
        ``sig.assertion/1`` envelope — every typed field preserved, every default
        basis-labelled, every unknown type rejected. A binding that cannot be
        normalised fails the whole ``assert_claims`` call closed into quarantine;
        a record-level rejection quarantines just that record and the rest of the
        chunk still lands (one bad assertion never makes an entity disappear).
        """
        active = self._active_binding
        if isinstance(active, Rejection):
            # The capture this call's claims were extracted from is unusable —
            # fail closed into quarantine (a bad digest/missing binding must
            # never be silently re-anchored to synthetic provenance).
            self._quarantine(claim, active)
            return
        source_id_for_q = str(claim.get("source_id") or self._connector_name)
        adapted = assertion_from_record(
            claim,
            binding=active if isinstance(active, CaptureBinding) else None,
            replayed=self._is_replay,
        )
        if isinstance(adapted, Rejection):
            self._quarantine(claim, adapted, source_id=source_id_for_q)
            return
        typed = adapted
        subject = typed.subject
        predicate = typed.predicate

        value = claim.get("value")
        spdx = str(claim.get("license") or claim.get("spdx") or "UNDETERMINED")
        attribution = claim.get("source_attribution") or claim.get("attribution")
        source_id = str(claim.get("source_id") or self._connector_name)

        genre = str(claim.get("evidence_genre") or "connector_run")
        rights_id = self._rights_id(spdx, attribution)
        if predicate not in self._known_predicates:
            self._pending_predicates.setdefault(predicate, _value_datatype(value))
        run_id = self._ensure_run()
        if isinstance(active, CaptureBinding):
            capture_id = self._ensure_actual_capture(
                active, source_id=source_id, rights_id=rights_id, genre=genre
            )
            if capture_id is None:
                # Occurrence/version resolution failed (the stored occurrence's
                # OCFL version disagrees with the binding) — quarantine, no claim.
                self._quarantine(
                    claim,
                    Rejection(
                        QuarantineReason.VERSION_MISMATCH,
                        "the binding's declared OCFL version disagrees with the "
                        "stored occurrence's recorded version",
                        quarantine_payload(
                            claim, connector_name=self._connector_name, source_id=source_id
                        ),
                    ),
                    source_id=source_id,
                )
                return
            extraction_id = self._ensure_extraction(
                capture_id,
                run_id,
                method=typed.extraction_method,
                config_digest=typed.extraction_config_digest,
                extractor_version=typed.extractor_version,
                model_id=typed.extraction_model_id,
                prompt_version=typed.extraction_prompt_version,
            )
        else:
            capture_id, extraction_id = self._ensure_evidence(source_id, rights_id, genre)

        object_ref = self._object_resolver(claim) if self._object_resolver is not None else None
        if object_ref is not None and object_ref.entity_type in _REFUSED_OBJECT_TYPES:
            raise ValueError(
                f"object resolver named a {object_ref.entity_type!r} entity; the sink "
                "never mints one (Part VIII)"
            )
        if object_ref is not None and (not object_ref.value or typed.value_kind == "novalue"):
            # An entity reference needs a named entity and a value to stand for:
            # without either the claim stays a literal (claim_value_shape).
            object_ref = None
        if object_ref is not None and typed.object_type == "literal" and "object_type" not in claim:
            # The object seam (P31.5) resolved an entity for this record: the
            # object_type upgrades to entity_ref with its basis recorded —
            # a literal a connector explicitly DECLARED is never flipped.
            typed.object_type = "entity_ref"
            typed.defaulted["object_type"] = "object_resolver"
        self._staged.append(
            _Staged(
                digest=content_digest(claim),
                subject=subject,
                predicate=predicate,
                extraction_id=extraction_id,
                run_id=run_id,
                rights_id=rights_id,
                capture_id=capture_id,
                object_ref=object_ref,
                typed=typed,
            )
        )

    def _quarantine(
        self, record: Mapping[str, Any], rejection: Rejection, *, source_id: str | None = None
    ) -> None:
        """Append the rejection to ``assertion_quarantine`` (append-only, +0 re-run)."""
        run_id = self._ensure_run()
        payload = rejection.payload or quarantine_payload(
            record, connector_name=self._connector_name, source_id=source_id
        )
        digest = rejection.payload_digest
        row = self._conn.execute(
            _QUARANTINE,
            (
                run_id,
                rejection.reason.value,
                self._connector_name,
                source_id,
                str(record.get("subject_id") or "") or None,
                str(record.get("predicate_id") or "") or None,
                json.dumps(payload, sort_keys=True, default=str),
                digest,
            ),
        ).fetchone()
        if row is not None:
            self.report.quarantined += 1

    def _ensure_actual_capture(
        self, binding: CaptureBinding, *, source_id: str, rights_id: str, genre: str
    ) -> str | None:
        """Resolve/insert the actual ``evidence_capture`` occurrence the binding names.

        The artifact is keyed by the capture's real source URI (never the
        synthetic ``sig:connector:`` locator); the blob row dedups identical
        bytes; the capture row is the immutable occurrence — a replay binding
        resolves the ORIGINAL occurrence row by ``(artifact, digest,
        retrieved_at)`` instead of asserting a fresh one, so the occurrence's
        provenance stays the original acquisition's.

        Returns ``None`` when a stored occurrence exists but disagrees with the
        binding's declared OCFL version (a version mismatch is quarantined by
        the caller, never silently rebound).
        """
        cache_key = (source_id, binding.source_uri)
        artifact_id = self._artifact_by_uri.get(cache_key)
        if artifact_id is None:
            self._ensure_source(source_id, rights_id)
            acquisition = "replay" if binding.replayed else "http_get"
            art = self._conn.execute(
                _ACTUAL_ARTIFACT,
                (
                    source_id,
                    binding.source_uri,
                    binding.source_uri,
                    genre,
                    acquisition,
                    rights_id,
                ),
            ).fetchone()
            if art is None:
                art = self._conn.execute(
                    _ACTUAL_ARTIFACT_ID, (source_id, binding.source_uri)
                ).fetchone()
            assert art is not None
            artifact_id = str(art[0])
            self._remember(self._artifact_by_uri, cache_key, artifact_id)
        run_id = self._ensure_run()
        self._conn.execute(
            _ACTUAL_BLOB,
            (
                binding.digest,
                binding.source_uri,
                binding.byte_size,
                binding.ocfl_object_id,
                binding.ocfl_version or "v1",
            ),
        )
        retrieved_at = binding.retrieved_at
        if retrieved_at is not None:
            row = self._conn.execute(
                _CAPTURE_OCCURRENCE, (artifact_id, binding.digest, retrieved_at)
            ).fetchone()
            if row is not None:
                stored_version = str(row[1])
                if binding.ocfl_version is not None and stored_version != binding.ocfl_version:
                    return None  # version mismatch — quarantined by the caller
                return str(row[0])
        method = "replay" if binding.replayed else "http_get"
        ins = self._conn.execute(
            _INSERT_OCCURRENCE,
            (
                artifact_id,
                binding.digest,
                binding.byte_size,
                binding.media_type,
                retrieved_at,
                binding.original_run_id or run_id,
                binding.ocfl_object_id,
                binding.ocfl_version or "v1",
                method,
                self._connector_version,
                binding.source_uri,
                binding.digest,
                CAPTURE_ACTUAL,
            ),
        ).fetchone()
        assert ins is not None
        return str(ins[0])

    def _ensure_extraction(
        self,
        capture_id: str,
        run_id: str,
        *,
        method: str,
        config_digest: str | None,
        extractor_version: str | None,
        model_id: str | None = None,
        prompt_version: str | None = None,
    ) -> str:
        """Resolve/insert the ``extraction`` for this (capture, run, method, config).

        One extraction row per extraction invocation identity: a replay run
        writes a NEW row against the same original capture (the original
        extraction stays linked to the original run), so the extraction's own
        time is the replay's assertion time while the capture's is the source's
        observation time.
        """
        key = (capture_id, method, config_digest)
        cached = self._extraction_by_key.get(key)
        if cached is not None:
            return cached
        row = self._conn.execute(_EXTRACTION_OF, (capture_id, run_id, method)).fetchone()
        if row is not None:
            extraction_id = str(row[0])
        else:
            params = json.dumps(
                {
                    "config_digest": config_digest,
                    "assertion_schema": "sig.assertion/1",
                },
                sort_keys=True,
            )
            ins = self._conn.execute(
                _INSERT_EXTRACTION,
                (
                    capture_id,
                    method,
                    self._connector_name,
                    extractor_version or self._connector_version,
                    self._connector_version,
                    model_id,
                    prompt_version,
                    params,
                    run_id,
                ),
            ).fetchone()
            assert ins is not None
            extraction_id = str(ins[0])
        self._remember(self._extraction_by_key, key, extraction_id)
        return extraction_id

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
        self._write_partner_organizations(staged, entity_ids)
        # Register the normalization ids this chunk declares (the vocab FK on
        # claim.normalization_id must never fail a valid claim — SIG-TRUST-001).
        norm_ids = sorted({s.typed.normalization_id for s in staged if s.typed.normalization_id})
        if norm_ids:
            self._conn.execute(_REGISTER_NORMALIZATIONS, (norm_ids,))

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
                    # --- 44 staged arrays, the WITH ORDINALITY order ---
                    [entity_ids[(SUBJECT_SCHEME, s.subject)] for s in part],
                    [s.predicate for s in part],
                    [
                        entity_ids[(s.object_ref.scheme, s.object_ref.value)]
                        if s.object_ref is not None
                        else None
                        for s in part
                    ],
                    [s.typed.object_type for s in part],
                    [s.typed.value_kind for s in part],
                    [s.typed.value_text for s in part],
                    [s.typed.value_int for s in part],
                    [s.typed.value_float for s in part],
                    [
                        None if s.typed.value_bool is None else str(s.typed.value_bool).lower()
                        for s in part
                    ],
                    [s.typed.value_json for s in part],
                    [s.typed.unit for s in part],
                    [s.typed.raw_value for s in part],
                    [s.typed.raw_context for s in part],
                    [s.typed.normalization_id for s in part],
                    [s.typed.normalization_version for s in part],
                    [s.typed.valid_from for s in part],
                    [s.typed.valid_to for s in part],
                    [s.typed.valid_edtf for s in part],
                    [s.typed.valid_from_kind for s in part],
                    [s.typed.valid_to_kind for s in part],
                    [s.typed.observed_at for s in part],
                    [s.typed.observed_edtf for s in part],
                    [s.typed.observed_at_kind for s in part],
                    [s.typed.observed_unknown_reason for s in part],
                    [s.typed.source_reliability for s in part],
                    [str(s.typed.reliability_provisional).lower() for s in part],
                    [s.typed.claim_directness for s in part],
                    [s.typed.artifact_integrity for s in part],
                    [s.typed.legacy_source_tier for s in part],
                    [s.typed.claim_polarity for s in part],
                    [s.typed.rank for s in part],
                    [s.typed.review_status for s in part],
                    [s.typed.assertion_rationale for s in part],
                    [",".join(s.typed.derived_from_claim_ids) or None for s in part],
                    [s.typed.revises_claim for s in part],
                    [s.typed.retraction_of for s in part],
                    [s.typed.correction_reason for s in part],
                    [s.extraction_id for s in part],
                    [s.run_id for s in part],
                    [s.rights_id for s in part],
                    [str(s.typed.sensitivity_tier) for s in part],
                    [s.digest for s in part],
                    [ASSERTION_MAP_ID] * len(part),
                    [
                        s.typed.map_basis(
                            replayed=s.typed.binding_status == BINDING_REPLAYED,
                            synthetic=s.typed.binding_status == BINDING_LEGACY,
                        )
                        for s in part
                    ],
                ),
            ).fetchall()
            if not rows:
                continue
            # Link each new claim to the capture its extraction actually consumed
            # — the typed locator, the extraction identity, and the binding
            # classification (§16.5; SIG-TRUST-002).
            by_digest = {s.digest: s for s in part}
            new = {str(r[1]): str(r[0]) for r in rows}
            self._conn.execute(
                _LINK_EVIDENCE_TYPED,
                (
                    list(new.values()),
                    [by_digest[d].capture_id for d in new],
                    [by_digest[d].extraction_id for d in new],
                    [by_digest[d].typed.evidence_role for d in new],
                    [
                        json.dumps(by_digest[d].typed.locator_row)
                        if by_digest[d].typed.locator_row
                        else None
                        for d in new
                    ],
                    [by_digest[d].typed.extraction_config_digest for d in new],
                    [by_digest[d].typed.extractor_version or self._connector_version for d in new],
                    [by_digest[d].typed.binding_status for d in new],
                ),
            )
            inserted.update(new)
            self._insert_qualifiers(by_digest, new)
        self.report.inserted += len(inserted)
        self.report.duplicates += len(staged) - len(inserted)

        if self._on_duplicates is not None:
            self._report_duplicates(unique, inserted)

    def _insert_qualifiers(
        self, by_digest: Mapping[str, _Staged], inserted: Mapping[str, str]
    ) -> None:
        """Write the chunk's ``claim_qualifier`` rows (the P32.2 typed surface).

        The qualifier vocabulary is the same registered ``vocab_predicate``
        surface claims name (FIELD_MAP §3): a qualifier id the registry does
        not know fails closed into ``assertion_quarantine`` naming the claim —
        never guessed, never registered — while the claim itself still lands.
        """
        rows: list[tuple[_Staged, Any]] = []
        qids = {q.qualifier_id for digest in inserted for q in by_digest[digest].typed.qualifiers}
        if not qids:
            return
        known = {
            str(r[0])
            for r in self._conn.execute(
                "SELECT predicate_id FROM vocab_predicate WHERE predicate_id = ANY(%s::text[])",
                (sorted(qids),),
            ).fetchall()
        }
        for digest in inserted:
            staged = by_digest[digest]
            for q in staged.typed.qualifiers:
                if q.qualifier_id in known:
                    rows.append((staged, q))
                else:
                    self._quarantine(
                        {
                            "subject_id": staged.subject,
                            "predicate_id": staged.predicate,
                            "qualifier": {"qualifier_id": q.qualifier_id},
                        },
                        Rejection(
                            QuarantineReason.UNKNOWN_QUALIFIER,
                            f"qualifier_id {q.qualifier_id!r} is not a registered "
                            "predicate (vocab_predicate); never guessed",
                            {
                                "claim_digest": staged.digest,
                                "claim_id": inserted[digest],
                                "qualifier": {
                                    "qualifier_id": q.qualifier_id,
                                    "value_text": q.value_text,
                                    "value_num": q.value_num,
                                    "value_bool": q.value_bool,
                                    "value_entity": q.value_entity,
                                    "unit": q.unit,
                                    "jurisdiction": q.jurisdiction,
                                    "rank": q.rank,
                                },
                            },
                        ),
                    )
        if not rows:
            return
        self._conn.execute(
            _INSERT_QUALIFIERS,
            (
                [inserted[s.digest] for s, _ in rows],
                [q.qualifier_id for _, q in rows],
                [q.value_text for _, q in rows],
                [q.value_num for _, q in rows],
                [None if q.value_bool is None else str(q.value_bool).lower() for _, q in rows],
                [q.value_entity for _, q in rows],
                [q.unit for _, q in rows],
                [q.jurisdiction for _, q in rows],
                [q.valid_from.isoformat() if q.valid_from else None for _, q in rows],
                [q.valid_to.isoformat() if q.valid_to else None for _, q in rows],
                [s.extraction_id for s, _ in rows],
                [q.rank for _, q in rows],
            ),
        )

    def _write_partner_organizations(
        self, staged: Sequence[_Staged], entity_ids: Mapping[tuple[str, str], str]
    ) -> None:
        """Write the ``organization`` row of each newly seen partner organisation.

        One statement per chunk, only for organisation objects this sink has not
        written yet (the cache is journaled, so a rolled-back chunk rewrites them).
        The first label seen wins, and ``ON CONFLICT DO NOTHING`` never replaces a
        row another run already wrote (ADR-112).
        """
        rows: dict[str, tuple[str, str, str]] = {}
        for s in staged:
            o = s.object_ref
            if o is None or o.entity_type != "organization" or not o.label:
                continue
            entity_id = entity_ids[(o.scheme, o.value)]
            if entity_id in self._org_rows or entity_id in rows:
                continue
            basis = json.dumps(
                {"scheme": o.scheme, "value": o.value, "rules": o.rules, "decided_by": "ADR-112"},
                sort_keys=True,
            )
            review = "true" if o.scheme == PARTNER_NAME_SCHEME else "false"
            rows[entity_id] = (basis, o.label, review)
        if not rows:
            return
        ids = sorted(rows)
        self._conn.execute(
            _PARTNER_ORGANIZATIONS,
            (
                PARTNER_ORGANIZATION_TYPE,
                ids,
                [rows[i][0] for i in ids],
                [rows[i][1] for i in ids],
                [rows[i][2] for i in ids],
            ),
        )
        for entity_id in ids:
            self._org_rows.add(entity_id)
            self._journal.append((self._org_rows, entity_id))

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
                replay=self._is_replay,
                binding_by_digest={
                    s.digest: (
                        s.extraction_id,
                        json.dumps(s.typed.locator_row) if s.typed.locator_row else None,
                        s.typed.extraction_config_digest,
                        s.typed.extractor_version or self._connector_version,
                        s.typed.binding_status,
                    )
                    for s in dup
                },
            )
        )


__all__ = [
    "CAPTURE_MARK_STATES",
    "DEFAULT_COMMIT_CHUNK_SIZE",
    "DEFAULT_INSERT_BATCH_SIZE",
    "ClaimSinkReport",
    "DuplicateBatch",
    "DuplicateHook",
    "EntityRef",
    "ObjectResolver",
    "PARTNER_ORGANIZATION_TYPE",
    "PgClaimSink",
    "SUBJECT_SCHEME",
    "content_digest",
    "record_object_ref",
    "record_resightings",
]

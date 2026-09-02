# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The read-store seam the API assembles responses over.

The public API is a hand-written contract, not a schema reflection (SIG-API-001):
it never touches storage directly. Instead it reads through :class:`ReadStore`,
so the same endpoints run over Postgres in production and over the deterministic
:class:`InMemoryStore` in tests. The store's one load-bearing rule is
**belief-time filtering** (§9.4, SIG-TIME-008): :meth:`ReadStore.claims_for` returns
only the claims asserted on or before ``as_of_belief``. That is what makes a
belief-pinned request reproducible after a later correction (SIG-API-006) — the
correction is simply a claim asserted later, and a past-belief read cannot see it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Protocol

from evidence.tiers import CaptureMetadata, StorageTier
from inference.coverage import CoverageRecord
from policy.rights import RightsRecord
from policy.sensitivity import SensitivityClass
from reconcile.resolve import Claim
from reconcile.ruleset import Ruleset
from reconcile.snapshot_diff import Capture


@dataclass(frozen=True)
class StoredClaim:
    """A claim plus the belief instant it was asserted at (T5, its sys_period start).

    ``asserted_at`` is the assertion-time axis the API filters on: a correction is
    a new :class:`StoredClaim` with a later ``asserted_at``, never an edit
    (append-only, P1–P3), so belief-pinning to before the correction reproduces
    the earlier answer byte-for-byte.
    """

    claim: Claim
    asserted_at: datetime
    capture_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class EntityRecord:
    """An entity and the metadata the ``/entity`` endpoint needs to assemble it."""

    entity_id: str
    entity_type: str
    label: str | None
    predicate_ids: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    lat: float | None = None
    lon: float | None = None
    sensitivity_class: SensitivityClass | None = None
    visibility: StorageTier = StorageTier.PUBLIC


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    kind: str
    status: str
    rationale: str
    subject_id: str | None = None
    predicate_id: str | None = None


@dataclass(frozen=True)
class ContradictionRecord:
    contradiction_id: str
    subject_id: str
    predicate_id: str
    kind: str
    state: str
    claim_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class CrosswalkRecord:
    sig_id: str
    external_scheme: str
    external_id: str
    relation: str


@dataclass(frozen=True)
class DossierRecord:
    scope: str
    title: str
    sections: tuple[dict[str, object], ...]
    source_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdDescriptor:
    """What ``/id/{type}/{uuid}`` needs to render a dereferenceable identifier."""

    id_type: str
    uuid: str
    label: str
    canonical_path: str
    predicates: dict[str, str] = field(default_factory=dict)


class ReadStore(Protocol):
    """The read seam the API depends on (SIG-API-001 keeps storage refactorable)."""

    @property
    def ruleset(self) -> Ruleset | None: ...

    def claims_for(
        self, subject_id: str, predicate_id: str, *, as_of_belief: datetime
    ) -> list[Claim]: ...

    def entity(self, entity_type: str, entity_id: str) -> EntityRecord | None: ...

    def stored_claim(self, claim_id: str) -> StoredClaim | None: ...

    def capture(self, artifact_id: str, capture_id: str) -> CaptureMetadata | None: ...

    def rights_for(self, source_ids: tuple[str, ...]) -> list[RightsRecord]: ...

    def coverage_for(self, scope: str) -> list[CoverageRecord]: ...

    def captures(self) -> list[Capture]: ...

    def search(self, query: str) -> list[EntityRecord]: ...

    def dossier(self, scope: str) -> DossierRecord | None: ...

    def crosswalk_rows(self) -> list[CrosswalkRecord]: ...

    def tasks(self) -> list[TaskRecord]: ...

    def task(self, task_id: str) -> TaskRecord | None: ...

    def contradictions(self) -> list[ContradictionRecord]: ...

    def contradiction(self, contradiction_id: str) -> ContradictionRecord | None: ...

    def resolve_id(self, id_type: str, uuid: str) -> IdDescriptor | None: ...


class InMemoryStore:
    """A deterministic, seedable :class:`ReadStore` for tests and the demo app."""

    def __init__(self, *, ruleset: Ruleset | None = None) -> None:
        self._ruleset = ruleset
        self._claims: dict[tuple[str, str], list[StoredClaim]] = {}
        self._claims_by_id: dict[str, StoredClaim] = {}
        self._entities: dict[tuple[str, str], EntityRecord] = {}
        self._captures_meta: dict[tuple[str, str], CaptureMetadata] = {}
        self._rights: dict[str, RightsRecord] = {}
        self._coverage: dict[str, list[CoverageRecord]] = {}
        self._snapshot_captures: list[Capture] = []
        self._dossiers: dict[str, DossierRecord] = {}
        self._crosswalk: list[CrosswalkRecord] = []
        self._tasks: dict[str, TaskRecord] = {}
        self._contradictions: dict[str, ContradictionRecord] = {}
        self._ids: dict[tuple[str, str], IdDescriptor] = {}

    # --- seeding ---------------------------------------------------------------

    def add_claim(self, stored: StoredClaim) -> None:
        key = (stored.claim.subject_id, stored.claim.predicate_id)
        self._claims.setdefault(key, []).append(stored)
        self._claims_by_id[stored.claim.claim_id] = stored

    def add_entity(self, record: EntityRecord) -> None:
        self._entities[(record.entity_type, record.entity_id)] = record

    def add_capture(self, meta: CaptureMetadata, *, artifact_id: str) -> None:
        self._captures_meta[(artifact_id, meta.capture_id)] = meta

    def add_rights(self, record: RightsRecord) -> None:
        self._rights[record.source_id] = record

    def add_coverage(self, scope: str, records: list[CoverageRecord]) -> None:
        self._coverage[scope] = records

    def add_snapshot_capture(self, capture: Capture) -> None:
        self._snapshot_captures.append(capture)

    def add_dossier(self, record: DossierRecord) -> None:
        self._dossiers[record.scope] = record

    def add_crosswalk(self, row: CrosswalkRecord) -> None:
        self._crosswalk.append(row)

    def add_task(self, record: TaskRecord) -> None:
        self._tasks[record.task_id] = record

    def add_contradiction(self, record: ContradictionRecord) -> None:
        self._contradictions[record.contradiction_id] = record

    def add_id(self, descriptor: IdDescriptor) -> None:
        self._ids[(descriptor.id_type, descriptor.uuid)] = descriptor

    # --- ReadStore -------------------------------------------------------------

    @property
    def ruleset(self) -> Ruleset | None:
        return self._ruleset

    def claims_for(
        self, subject_id: str, predicate_id: str, *, as_of_belief: datetime
    ) -> list[Claim]:
        stored = self._claims.get((subject_id, predicate_id), [])
        return [s.claim for s in stored if s.asserted_at <= as_of_belief]

    def entity(self, entity_type: str, entity_id: str) -> EntityRecord | None:
        return self._entities.get((entity_type, entity_id))

    def stored_claim(self, claim_id: str) -> StoredClaim | None:
        return self._claims_by_id.get(claim_id)

    def capture(self, artifact_id: str, capture_id: str) -> CaptureMetadata | None:
        return self._captures_meta.get((artifact_id, capture_id))

    def rights_for(self, source_ids: tuple[str, ...]) -> list[RightsRecord]:
        return [self._rights[s] for s in source_ids if s in self._rights]

    def coverage_for(self, scope: str) -> list[CoverageRecord]:
        return list(self._coverage.get(scope, []))

    def captures(self) -> list[Capture]:
        return list(self._snapshot_captures)

    def search(self, query: str) -> list[EntityRecord]:
        q = query.strip().lower()
        if not q:
            return []
        hits = [
            e
            for e in self._entities.values()
            if q in (e.label or "").lower() or q in e.entity_id.lower()
        ]
        return sorted(hits, key=lambda e: e.entity_id)

    def dossier(self, scope: str) -> DossierRecord | None:
        return self._dossiers.get(scope)

    def crosswalk_rows(self) -> list[CrosswalkRecord]:
        return list(self._crosswalk)

    def tasks(self) -> list[TaskRecord]:
        return sorted(self._tasks.values(), key=lambda t: t.task_id)

    def task(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def contradictions(self) -> list[ContradictionRecord]:
        return sorted(self._contradictions.values(), key=lambda c: c.contradiction_id)

    def contradiction(self, contradiction_id: str) -> ContradictionRecord | None:
        return self._contradictions.get(contradiction_id)

    def resolve_id(self, id_type: str, uuid: str) -> IdDescriptor | None:
        return self._ids.get((id_type, uuid))

    def correct_claim(self, claim_id: str, *, value: object, asserted_at: datetime) -> StoredClaim:
        """Assert a correction as a NEW claim (append-only, never an edit).

        Returns the newly-stored correcting claim. The original remains; a read
        pinned to a belief instant before ``asserted_at`` still resolves to the
        pre-correction answer (SIG-API-006).
        """
        original = self._claims_by_id[claim_id]
        corrected_claim = replace(
            original.claim,
            claim_id=f"{claim_id}~corrected@{asserted_at.isoformat()}",
            value=value,
            raw_value=str(value),
        )
        stored = StoredClaim(
            claim=corrected_claim, asserted_at=asserted_at, capture_ids=original.capture_ids
        )
        self.add_claim(stored)
        return stored


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)

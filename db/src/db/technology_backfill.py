# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.15b — the append-only ``technology``-claim backfill (PKG-07 / F-329 / F-523).

Every camera-registry subject ingested before P35.15a was keyed
``traffic_camera:<source>:<target>:<ref>`` with no ``technology`` claim — an
ALPR reader, a police CCTV and a traffic-management camera were publicly
indistinguishable (F-329; ~77.4% of ~232,628 subjects are non-traffic by their
own registry target, F-523). P35.15a made each target declare its SKOS slug in
``camera_registry_targets.toml`` / ``dot_511_targets.toml`` and emit the
``technology`` claim for NEW subjects. This module is the committed
dry-run-by-default command that writes the same claim onto the EXISTING
subjects:

* **Dry-run by default.** :func:`plan_backfill` enumerates every keyed
  ``traffic_camera:*`` subject, resolves ``(source, target)`` from the subject
  key itself (the key already encodes the target), consults the committed
  target declarations the caller supplies, and returns the full
  per-target/per-slug plan. Nothing is written until :func:`apply_plan` runs.
* **Declared, never inferred.** The slug comes from the target row's
  ``technology`` field — the same declaration the emit path reads — so the
  backfill and the emitter can never disagree. A subject whose ``(source,
  target)`` declares nothing is counted and left untouched (no substring
  inference — the NEW-7/FM-05 defect this family replaced).
* **Ordinary append-only claims.** Claims are staged through
  :class:`db.claim_sink.PgClaimSink` — the real ``sig.assertion/1`` adapter,
  the closed-vocabulary gate, chunked commits, ``ON CONFLICT DO NOTHING``
  idempotence — never a bespoke INSERT that bypasses provenance. The sink runs
  ``is_replay``: a backfill re-reads stored bytes, so its evidence links
  classify ``replayed`` (ADR-113), honestly.
* **Evidence links to EXISTING captures.** For each pending subject the plan
  picks its latest *bindable* actual capture (multihash digest, artifact
  source agreeing with the subject's source) and the sink writes the claim
  bound to that occurrence — resolving the ORIGINAL ``evidence_capture`` row,
  never minting a new one. Supplementary ``claim_evidence`` rows then link the
  claim to the subject's other existing captures (``establishes`` on the
  chosen capture, ``corroborates`` on the rest). A subject with no captures
  gains nothing — no claim is written without an evidence link.
* **Labelled backfill-derived.** ``assertion_rationale`` names the ticket and
  the derivation; ``derived_from_claim_ids`` cites the subject's existing
  ``traffic_camera`` registry-record claims; the extraction method reads
  ``declared_technology_backfill`` and the run writes
  ``connector_name='technology-backfill'`` — the claims are never passed off
  as connector-fresh.
* **Resumable, +0-convergent.** Subjects already carrying a ``technology``
  claim are skipped (claims written by THIS connector additionally get their
  evidence links topped up, so an interrupted run's partial link pass
  completes on re-run). Every write is ``ON CONFLICT DO NOTHING``; a clean
  re-run appends +0.

CLI home: ``sig-connectors technology-backfill`` (the connectors package owns
the target registry and the emit path; ``db`` stays free of connector
concepts — the same split P34.21a used for its rights backfill, mirrored).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import psycopg
from evidence.digest import decode_multihash

from .assertion import CAPTURE_ACTUAL
from .claim_sink import DEFAULT_COMMIT_CHUNK_SIZE, PgClaimSink

#: The ingest_run.connector_name / quarantine connector these claims stamp —
#: honest run provenance, never the emit connector's name.
CONNECTOR_NAME = "technology-backfill"
CONNECTOR_VERSION = "1.0.0"
#: extraction.method the backfill's extraction rows carry — the derivation
#: label every written claim's provenance resolves through.
EXTRACTION_METHOD = "declared_technology_backfill"
PREDICATE = "technology"
#: The registry-record claim whose ids a backfilled claim cites in
#: ``derived_from_claim_ids`` (the claim is derived from the registry's
#: record of the subject, evidence included).
REGISTRY_RECORD_PREDICATE = "traffic_camera"
EVIDENCE_GENRE = "camera_registry"
SUBJECT_PREFIX = "traffic_camera:"
RATIONALE = (
    "P35.15b technology backfill (PKG-07 / F-329 / F-523): the registry "
    "target's declared SKOS technology slug asserted onto a pre-PKG-07 "
    "subject identity; derived from the subject's existing registry claims "
    "and the committed target declaration — never a name-substring "
    "inference (NEW-7 / FM-05)."
)

#: Read passes batch over entity-id arrays of this size (~200k subjects stay
#: a handful of round trips, never one giant ANY()).
READ_BATCH_SIZE = 5_000
#: Supplementary claim_evidence links commit in batches of this size.
LINK_BATCH_SIZE = 10_000
#: Report example lists are capped; the COUNTS are always exact.
_EXAMPLE_CAP = 100

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

_SUBJECT_KEYS = (
    "SELECT value, entity_id::text FROM entity_identity_key "
    "WHERE scheme = 'sig.connector.subject' "
    "AND value LIKE 'traffic/_camera:%' ESCAPE '/' "
    "ORDER BY value"
)
_TECH_CLAIMS = (
    "SELECT c.subject_id::text, c.claim_id::text, r.connector_name "
    "FROM claim c JOIN ingest_run r ON r.run_id = c.ingest_run_id "
    "WHERE c.predicate_id = %s AND c.subject_id = ANY(%s::uuid[])"
)
_CAPTURES = (
    "SELECT c.subject_id::text, ce.capture_id::text, ec.retrieved_at, "
    "ec.content_digest, ec.byte_size, ec.media_type, ec.ocfl_object_id, "
    "ec.ocfl_version, ec.retrieved_by_run_id::text, ec.capture_classification, "
    "ea.stable_locator, ea.source_id "
    "FROM claim c "
    "JOIN claim_evidence ce ON ce.claim_id = c.claim_id "
    "JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
    "JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
    "WHERE c.subject_id = ANY(%s::uuid[])"
)
_DERIVED_CLAIMS = (
    "SELECT subject_id::text, claim_id::text FROM claim "
    "WHERE predicate_id = %s AND subject_id = ANY(%s::uuid[])"
)
_TECH_CLAIM_IDS = (
    "SELECT subject_id::text, claim_id::text FROM claim "
    "WHERE predicate_id = %s AND subject_id = ANY(%s::uuid[])"
)
_REGISTERED = (
    "SELECT (SELECT count(*) FROM vocab_predicate WHERE predicate_id = %s), "
    "(SELECT count(*) FROM vocab_artifact_genre WHERE genre_id = %s)"
)

# The supplementary link: (claim, capture, role) identity, plain (untyped)
# columns — the bound capture's typed 'establishes' row is written by the sink;
# this pass adds the roles the binding path cannot (other existing captures,
# and the claim rows a partial earlier run left unlinked). ON CONFLICT makes
# the whole pass +0-convergent.
_LINK_EVIDENCE_ROLES = (
    "INSERT INTO claim_evidence(claim_id, capture_id, role) "
    "SELECT l.claim_id::uuid, l.capture_id::uuid, l.role "
    "FROM unnest(%s::text[], %s::text[], %s::text[]) AS l(claim_id, capture_id, role) "
    "ON CONFLICT (claim_id, capture_id, role) DO NOTHING"
)


def parse_subject(value: str) -> tuple[str, str, str] | None:
    """``traffic_camera:<source>:<target>:<ref>`` -> (source, target, ref).

    The ref segment may itself contain ``:`` (only the first three colons are
    separators). ``None`` when the key is not the expected 4-part shape — a
    malformed key is counted, never guessed at.
    """
    parts = value.split(":", 3)
    if len(parts) != 4 or parts[0] != "traffic_camera":
        return None
    source, target, ref = parts[1], parts[2], parts[3]
    if not source or not target or not ref:
        return None
    return source, target, ref


@dataclass(frozen=True)
class CaptureRow:
    """One of a subject's existing ``evidence_capture`` rows (read-only plan data)."""

    capture_id: str
    retrieved_at: datetime | None
    content_digest: str | None
    byte_size: int | None
    media_type: str | None
    ocfl_object_id: str | None
    ocfl_version: str | None
    retrieved_by_run_id: str | None
    classification: str | None
    stable_locator: str | None
    artifact_source_id: str | None

    def bindable_for(self, source_id: str) -> bool:
        """True when this occurrence can be rebound verbatim (SIG-TRUST-002).

        The binding must name byte-bearing bytes: an ``actual`` capture with a
        decodable multihash digest, a stable locator and a retrieval time, and
        — because the sink keys the artifact on ``(source_id, stable_locator)``
        — an artifact registered under the SUBJECT's own source id. Anything
        else (synthetic per-run captures, hex digests, source mismatches) is
        never rebound; the subject falls back to link-only evidence.
        """
        if self.classification != CAPTURE_ACTUAL:
            return False
        if self.artifact_source_id != source_id or not self.stable_locator:
            return False
        if self.retrieved_at is None or not self.content_digest:
            return False
        try:
            decode_multihash(self.content_digest)
        except Exception:  # noqa: BLE001 - any decode failure is unbindable
            return False
        return True

    def binding(self) -> dict[str, Any]:
        """The ``capture`` mapping ``assert_claims`` binds (replays resolve the
        original occurrence by ``(artifact, digest, retrieved_at)``)."""
        return {
            "digest": self.content_digest,
            "source_uri": self.stable_locator,
            "media_type": self.media_type or "application/octet-stream",
            "byte_size": self.byte_size or 0,
            "retrieved_at": self.retrieved_at,
            "ocfl_object_id": self.ocfl_object_id,
            "ocfl_version": self.ocfl_version,
            "original_run_id": self.retrieved_by_run_id,
        }


def _sort_key(cap: CaptureRow) -> tuple[datetime, str]:
    """Latest retrieval wins; capture_id breaks ties deterministically."""
    return (cap.retrieved_at or _EPOCH, cap.capture_id)


@dataclass
class PlannedSubject:
    """One in-scope registry subject and what the backfill will do to it."""

    subject: str
    entity_id: str
    source_id: str
    target_id: str
    slug: str
    license_spdx: str | None
    captures: list[CaptureRow] = field(default_factory=list)
    #: Chosen binding capture (bindable actual occurrences only).
    bound: CaptureRow | None = None
    #: The capture the 'establishes' link targets — bound when bindable, else
    #: the latest existing capture of any classification.
    chosen: CaptureRow | None = None
    #: The subject's registry-record claim ids cited via derived_from_claim_ids.
    derived_from: list[str] = field(default_factory=list)
    #: ``technology`` claim ids the subject already carries from THIS
    #: connector's runs (link top-up targets; the claims themselves are +0).
    ours_claim_ids: list[str] = field(default_factory=list)

    def claim_record(self) -> dict[str, Any]:
        """The ``sig.assertion/1`` record for this subject's technology claim.

        Deterministic per plan: the same subject + declaration + derived ids
        digest identically, so a re-run dedupes on ``content_digest`` even
        before the subject-level skip engages.
        """
        record: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": self.subject,
            "predicate_id": PREDICATE,
            "value": self.slug,
            "raw_value": self.slug,
            "evidence_genre": EVIDENCE_GENRE,
            "extraction_method": EXTRACTION_METHOD,
            "assertion_rationale": RATIONALE,
            "derived_from_claim_ids": list(self.derived_from),
            "source_id": self.source_id,
        }
        if self.license_spdx:
            record["license"] = self.license_spdx
        return record


@dataclass
class BackfillPlan:
    """What a dry run reports and what ``--apply`` executes (the same plan)."""

    scanned: int = 0
    #: Subjects needing the technology claim (+ their links).
    pending: list[PlannedSubject] = field(default_factory=list)
    #: Subjects already carrying THIS connector's technology claim — the
    #: claims are skipped but their evidence links are topped up (resumes a
    #: partial earlier run to +0 convergence).
    link_only: list[PlannedSubject] = field(default_factory=list)
    #: Already typed by another writer (the emit path, a manual claim) —
    #: counted, never touched: the predicate is multi-cardinality only for
    #: genuinely different declarations, never for a guessed extra row, and a
    #: claim this run did not write never gains evidence links from it.
    typed_other_ids: list[str] = field(default_factory=list)
    #: keyed subjects whose (source, target) declares no slug — "source/target".
    undeclared: dict[str, int] = field(default_factory=dict)
    malformed: list[str] = field(default_factory=list)
    #: Declared subjects with ZERO existing captures — never written (a claim
    #: without an evidence link would violate §16).
    no_evidence: list[PlannedSubject] = field(default_factory=list)
    #: Subject keys that resolved to an entity another key already claimed
    #: (an identity merge): one entity carries one claim — the extra keys are
    #: counted, never double-written.
    aliased: int = 0

    @property
    def pending_count(self) -> int:
        return len(self.pending)

    def by_slug(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for ps in self.pending:
            out[ps.slug] = out.get(ps.slug, 0) + 1
        return dict(sorted(out.items()))

    def by_target(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for ps in self.pending:
            key = f"{ps.source_id}/{ps.target_id}"
            out[key] = out.get(key, 0) + 1
        return dict(sorted(out.items()))

    def links_planned(self) -> int:
        return sum(len(ps.captures) * len(ps.ours_claim_ids) for ps in self.link_only) + sum(
            len(ps.captures) for ps in self.pending
        )

    def report(self) -> dict[str, Any]:
        """The dry-run document: full counts, capped examples, no writes."""
        return {
            "mode": "plan",
            "subjects_scanned": self.scanned,
            "pending_claims": self.pending_count,
            "pending_by_slug": self.by_slug(),
            "pending_by_target": self.by_target(),
            "link_topup_subjects": len(self.link_only),
            "links_planned": self.links_planned(),
            "already_typed": {
                "total": len(self.typed_other_ids) + len(self.link_only),
                "this_connector": len(self.link_only),
                "other": len(self.typed_other_ids),
            },
            "skipped": {
                "undeclared": sum(self.undeclared.values()),
                "malformed": len(self.malformed),
                "no_evidence": len(self.no_evidence),
                "aliased_entity_keys": self.aliased,
            },
            "undeclared_by_target": dict(sorted(self.undeclared.items())),
            "examples": {
                "malformed": self.malformed[:_EXAMPLE_CAP],
                "no_evidence": [ps.subject for ps in self.no_evidence[:_EXAMPLE_CAP]],
            },
        }


def _batched(ids: Sequence[str], size: int = READ_BATCH_SIZE) -> list[list[str]]:
    return [list(ids[i : i + size]) for i in range(0, len(ids), size)]


def plan_backfill(
    conn: Any,
    declared: Mapping[tuple[str, str], str],
    licenses: Mapping[tuple[str, str], str] | None = None,
) -> BackfillPlan:
    """Compute the backfill plan — the dry-run and ``--apply`` share this read.

    ``declared`` maps ``(source_id, target_id)`` -> the committed target
    declaration's technology slug (``connectors.dot_511.declared_technologies``
    output — the same table the emit path reads); ``licenses`` carries each
    target's ``license_spdx`` so the claim's rights resolve exactly as the
    emit path's do. Read-only.
    """
    licenses = licenses or {}
    plan = BackfillPlan()
    subject_rows = conn.execute(_SUBJECT_KEYS).fetchall()
    plan.scanned = len(subject_rows)
    in_scope: dict[str, PlannedSubject] = {}  # entity_id -> subject
    for value, entity_id in subject_rows:
        parsed = parse_subject(str(value))
        if parsed is None:
            plan.malformed.append(str(value))
            continue
        source_id, target_id, _ref = parsed
        slug = declared.get((source_id, target_id))
        if not slug:
            key = f"{source_id}/{target_id}"
            plan.undeclared[key] = plan.undeclared.get(key, 0) + 1
            continue
        # A claim lands on the ENTITY, so two keys sharing one entity take one
        # claim — the second key is counted aliased, never double-written.
        if str(entity_id) in in_scope:
            plan.aliased += 1
            continue
        in_scope[str(entity_id)] = PlannedSubject(
            subject=str(value),
            entity_id=str(entity_id),
            source_id=source_id,
            target_id=target_id,
            slug=str(slug),
            license_spdx=licenses.get((source_id, target_id)) or None,
        )
    if not in_scope:
        return plan

    ids = sorted(in_scope)
    # Existing `technology` claims: subjects carrying one from THIS connector
    # join the link top-up set; claims from any other writer make the subject
    # already-typed (untouched). A subject may carry both — ours still tops up.
    tech: dict[str, list[tuple[str, str]]] = {}
    for batch in _batched(ids):
        for subject_id, claim_id, connector in conn.execute(
            _TECH_CLAIMS, (PREDICATE, batch)
        ).fetchall():
            tech.setdefault(str(subject_id), []).append((str(claim_id), str(connector)))
    needs: list[PlannedSubject] = []
    capture_targets: list[PlannedSubject] = []
    for entity_id in ids:
        ps = in_scope[entity_id]
        claims = tech.get(entity_id, [])
        ours = [cid for cid, conn_name in claims if conn_name == CONNECTOR_NAME]
        if ours:
            # Ours — top its links up to +0 convergence; any other-writer
            # claims on the same subject stay untouched.
            ps.ours_claim_ids = sorted(ours)
            plan.link_only.append(ps)
            capture_targets.append(ps)
        elif claims:
            # Another writer typed the subject: skipped entirely — no claim,
            # no link writes against a claim this run did not produce.
            plan.typed_other_ids.append(entity_id)
        else:
            needs.append(ps)
            capture_targets.append(ps)

    # Existing captures for every capture target — pending subjects get their
    # binding chosen here; ours-typed subjects only need the link roles.
    captures: dict[str, dict[str, CaptureRow]] = {}
    capture_ids = sorted(ps.entity_id for ps in capture_targets)
    for batch in _batched(capture_ids):
        for row in conn.execute(_CAPTURES, (batch,)).fetchall():
            (
                subject_id,
                capture_id,
                retrieved_at,
                digest,
                byte_size,
                media_type,
                ocfl_object_id,
                ocfl_version,
                retrieved_by_run_id,
                classification,
                stable_locator,
                artifact_source_id,
            ) = row
            captures.setdefault(str(subject_id), {})[str(capture_id)] = CaptureRow(
                capture_id=str(capture_id),
                retrieved_at=retrieved_at,
                content_digest=None if digest is None else str(digest),
                byte_size=byte_size,
                media_type=None if media_type is None else str(media_type),
                ocfl_object_id=None if ocfl_object_id is None else str(ocfl_object_id),
                ocfl_version=None if ocfl_version is None else str(ocfl_version),
                retrieved_by_run_id=(
                    None if retrieved_by_run_id is None else str(retrieved_by_run_id)
                ),
                classification=None if classification is None else str(classification),
                stable_locator=None if stable_locator is None else str(stable_locator),
                artifact_source_id=(
                    None if artifact_source_id is None else str(artifact_source_id)
                ),
            )
    for ps in capture_targets:
        rows = sorted(captures.get(ps.entity_id, {}).values(), key=_sort_key, reverse=True)
        ps.captures = rows
        ps.bound = next((c for c in rows if c.bindable_for(ps.source_id)), None)
        ps.chosen = ps.bound or (rows[0] if rows else None)

    # Registry-record claim ids — the derivation basis — for pending subjects.
    pending_ids = sorted(ps.entity_id for ps in needs)
    for batch in _batched(pending_ids):
        for subject_id, claim_id in conn.execute(
            _DERIVED_CLAIMS, (REGISTRY_RECORD_PREDICATE, batch)
        ).fetchall():
            derived_ps = in_scope.get(str(subject_id))
            if derived_ps is not None:
                derived_ps.derived_from.append(str(claim_id))
    for ps in needs:
        ps.derived_from.sort()
        if ps.captures:
            plan.pending.append(ps)
        else:
            plan.no_evidence.append(ps)
    plan.pending.sort(key=lambda ps: ps.subject)
    plan.link_only.sort(key=lambda ps: ps.subject)
    plan.no_evidence.sort(key=lambda ps: ps.subject)
    return plan


def _registration(conn: Any) -> dict[str, bool]:
    """The closed-vocabulary precheck the live leg requires (P35.14a).

    An unregistered ``technology`` predicate or ``camera_registry`` genre would
    quarantine every claim under the closed sink — the leg refuses BEFORE
    writing instead of landing 200k quarantine rows.
    """
    row = conn.execute(_REGISTERED, (PREDICATE, EVIDENCE_GENRE)).fetchone()
    assert row is not None
    return {"technology_predicate": bool(row[0]), "camera_registry_genre": bool(row[1])}


def apply_plan(
    conn: Any,
    plan: BackfillPlan,
    *,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    rights_resolver: Any = None,
    link_batch_size: int = LINK_BATCH_SIZE,
) -> dict[str, Any]:
    """Execute ``plan`` append-only through :class:`PgClaimSink`.

    Pending subjects are grouped by their chosen binding capture and written
    one ``assert_claims(capture=binding)`` call per capture — chunked commits
    of ``commit_chunk_size`` claims inside each call, ``is_replay`` so the
    links classify ``replayed`` (a backfill re-reads stored bytes). Subjects
    with no bindable occurrence write through the legacy (synthetic) evidence
    path and still gain ``establishes``/``corroborates`` links to their real
    captures in the supplementary pass. Subjects carrying only OUR earlier
    claims get links topped up — an interrupted run resumes to +0.
    """
    registered = _registration(conn)
    report = plan.report()
    report["mode"] = "apply"
    report["registered"] = registered
    if plan.pending and not all(registered.values()):
        # The leg's voided-by condition: refuse loud BEFORE any write rather
        # than landing a spine of unknown_predicate quarantine rows.
        report["refused"] = (
            "closed-vocabulary gate: `technology` predicate and "
            "`camera_registry` genre must be registered before --apply "
            "(live: P35.15a's hosted registrations land first)"
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
        extra_parameters={
            "ticket": "P35.15b",
            "manifest_row": "275",
            "backfill": "technology",
        },
    )
    bound_groups: dict[str, list[PlannedSubject]] = {}
    unbound: list[PlannedSubject] = []
    for ps in plan.pending:
        if ps.bound is not None:
            bound_groups.setdefault(ps.bound.capture_id, []).append(ps)
        else:
            unbound.append(ps)
    for capture_id in sorted(bound_groups):
        group = bound_groups[capture_id]
        sink.assert_claims(
            [ps.claim_record() for ps in group],
            capture=group[0].bound.binding() if group[0].bound else None,
        )
    if unbound:
        sink.assert_claims([ps.claim_record() for ps in unbound])

    # Supplementary evidence links: every pending subject's just-written claim
    # and every earlier claim of OURS links each of the subject's existing
    # captures — 'establishes' on the chosen capture (the bound one already
    # carries the sink's typed row; the conflict dedupes), 'corroborates' on
    # the rest. Other writers' claims are never touched: a pending subject had
    # no `technology` claim before this run, so the query returns ours alone,
    # and ours-typed subjects link only the ids recorded at plan time.
    # Chunked commits, ON CONFLICT -> +0-convergent.
    claim_ids: dict[str, list[str]] = {}
    pending_ids = sorted(ps.entity_id for ps in plan.pending)
    for batch in _batched(pending_ids):
        for subject_id, claim_id in conn.execute(_TECH_CLAIM_IDS, (PREDICATE, batch)).fetchall():
            claim_ids.setdefault(str(subject_id), []).append(str(claim_id))
    for ps in plan.link_only:
        claim_ids[ps.entity_id] = list(ps.ours_claim_ids)
    rows: list[tuple[str, str, str]] = []
    for ps in (*plan.pending, *plan.link_only):
        chosen_id = ps.chosen.capture_id if ps.chosen else None
        for cid in claim_ids.get(ps.entity_id, []):
            for cap in ps.captures:
                role = "establishes" if cap.capture_id == chosen_id else "corroborates"
                rows.append((cid, cap.capture_id, role))
    links_inserted = 0
    for start in range(0, len(rows), link_batch_size):
        part = rows[start : start + link_batch_size]
        with conn.transaction():
            cur = conn.execute(
                _LINK_EVIDENCE_ROLES,
                (
                    [r[0] for r in part],
                    [r[1] for r in part],
                    [r[2] for r in part],
                ),
            )
            links_inserted += cur.rowcount if cur.rowcount and cur.rowcount > 0 else 0

    sink.record_completion(
        "ok",
        detail=(
            f"P35.15b technology backfill: pending={plan.pending_count} "
            f"inserted={sink.report.inserted} duplicates={sink.report.duplicates} "
            f"links_planned={len(rows)} links_inserted={links_inserted}"
        ),
    )
    # Honest read-back: the leg records the post counts, never assumes them.
    typed_now = 0
    for batch in _batched(sorted(in_scope_ids(plan))):
        rows_back = conn.execute(
            "SELECT count(DISTINCT subject_id) FROM claim "
            "WHERE predicate_id = %s AND subject_id = ANY(%s::uuid[])",
            (PREDICATE, batch),
        ).fetchone()
        typed_now += int(rows_back[0]) if rows_back else 0
    report["apply"] = {
        "claims_added": sink.report.inserted,
        "claims_duplicate": sink.report.duplicates,
        "quarantined": sink.report.quarantined,
        "bound_groups": len(bound_groups),
        "unbound_subjects": len(unbound),
        "links_planned": len(rows),
        "links_inserted": links_inserted,
        "run_id": sink.run_id,
        "execution_id": sink.execution_id,
    }
    report["post"] = {
        "in_scope_subjects_with_technology": typed_now,
        "in_scope_subjects_without_technology": len(in_scope_ids(plan)) - typed_now,
    }
    return report


def in_scope_ids(plan: BackfillPlan) -> list[str]:
    """Every declared in-scope subject id (pending + typed + evidence-less)."""
    return [
        *[ps.entity_id for ps in plan.pending],
        *[ps.entity_id for ps in plan.link_only],
        *[ps.entity_id for ps in plan.no_evidence],
        *plan.typed_other_ids,
    ]


def run_backfill(
    dsn: str,
    *,
    declared: Mapping[tuple[str, str], str],
    licenses: Mapping[tuple[str, str], str] | None = None,
    apply: bool = False,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    rights_resolver: Any = None,
) -> dict[str, Any]:
    """Open the DSN, plan, and (only with ``apply=True``) write.

    The conn is ``autocommit=True``: chunk commits are explicit
    ``conn.transaction()`` blocks inside the sink and the link pass — the
    P35.14a fixture defect was a sink staged on a non-autocommit conn, which
    made every write stall behind the caller's implicit transaction.
    """
    with psycopg.connect(dsn, autocommit=True) as conn:
        plan = plan_backfill(conn, declared, licenses)
        if not apply:
            report = plan.report()
            report["registered"] = _registration(conn)
            return report
        return apply_plan(
            conn,
            plan,
            code_commit=code_commit,
            commit_chunk_size=commit_chunk_size,
            rights_resolver=rights_resolver,
        )


__all__ = [
    "BackfillPlan",
    "CaptureRow",
    "CONNECTOR_NAME",
    "EXTRACTION_METHOD",
    "PlannedSubject",
    "RATIONALE",
    "apply_plan",
    "parse_subject",
    "plan_backfill",
    "run_backfill",
]

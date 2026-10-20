# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.16 — the append-only geometry-defect correction pass (R11-DATA-01 / F-322).

F-322 found seven defect groups where pre-P35.16 ingest asserted published
coordinate pairs that contradict their declared bounds: axis-swapped pairs
(Nottingham, 562 rows; mark43, 561), points sitting inside a jurisdiction
their record's declared jurisdiction contradicts (trafficops D5, gmh_emc,
bangla, oosgis) and null-island ``(0,0)`` placeholders (dot_511_ga,
camreg_fl511_fl). P35.16's ingest path now declares ``axis_order`` per target
and marks detector-flagged records at emit. This module is the committed
dry-run-by-default command that assembles the append-only correction claims
onto the EXISTING subjects — the stored claims are never rewritten:

* **Dry-run by default.** :func:`plan_corrections` reads the declared
  ``sig.geometry-corrections/1`` scope (the caller supplies it — the
  connectors package owns the registry + the committed artifact) and builds
  the full per-group plan before anything is written.
* **Declared scope, evaluated per point.** A defect group is a committed
  declaration naming ``(source_id, target_id)``, the finding's class and the
  declared bound to evaluate against; each subject's latest original
  ``camera_latitude``/``camera_longitude`` claims are classified against
  that bound — transposed-rescue → ``axis_swap``, near-(0,0) →
  ``null_island``, single-axis negation rescue → ``sign_flip``, else
  ``wrong_jurisdiction``. The recorded class is whatever the detectors
  derive; a group row's ``expected_class`` is the finding's headline class,
  never a forced label.
* **Marks, plus provable corrections only.** Every flagged subject gains a
  ``geometry_defect`` claim (the recorded class + observed pair + the bound
  it failed ride the claim evidence). An ``axis_swap`` verdict additionally
  mints corrected ``camera_latitude``/``camera_longitude`` claims carrying
  ``revises_claim`` + ``correction_reason='axis_swap'`` — the transposed
  pair is a proof, not a guess. ``sign_flip``/``wrong_jurisdiction``/
  ``null_island`` mint NO replacement value: the record is marked, the
  truth is not fabricated.
* **Ordinary append-only claims.** Everything stages through
  :class:`db.claim_sink.PgClaimSink` — the ``sig.assertion/1`` adapter, the
  closed-vocabulary gate, chunked commits, ``ON CONFLICT DO NOTHING``
  idempotence; the sink runs ``is_replay`` so evidence links classify
  ``replayed`` (ADR-113), honestly.
* **Originals stay.** No ``UPDATE``/``DELETE`` exists here or anywhere in
  ``db/``; the wrong claims remain queryable and carry the defect claim as
  the recorded verdict.
* **Resumable, +0-convergent.** A subject already carrying THIS connector's
  ``geometry_defect`` claim is skipped (its evidence links top up); a
  subject carrying our corrected coordinate claims does not gain a second
  pair. Every write is conflict-safe; a clean re-run appends +0.

CLI home: ``sig-connectors geometry-corrections`` (the connectors package
owns the registry/artifact; ``db`` stays free of connector concepts — the
same split P34.21a and P35.15b used).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import psycopg

from .claim_sink import DEFAULT_COMMIT_CHUNK_SIZE, PgClaimSink
from .technology_backfill import CaptureRow

#: The ingest_run.connector_name / quarantine connector these claims stamp —
#: honest run provenance, never the emit connector's name.
CONNECTOR_NAME = "geometry-corrections"
CONNECTOR_VERSION = "1.0.0"
#: extraction.method the correction pass's extraction rows carry — the
#: derivation label every written claim's provenance resolves through.
EXTRACTION_METHOD = "declared_geometry_correction"
#: The defect-marking predicate (closed vocabulary — registered by the
#: ``vocab_geometry_defect`` sqitch change and the connector's predicate
#: allowlist).
PREDICATE = "geometry_defect"
#: The device-point predicates the pass reads (latest original pair) and —
#: for ``axis_swap`` only — revises with the provable transposed values.
COORD_PREDICATES = ("camera_latitude", "camera_longitude")
EVIDENCE_GENRE = "camera_registry"
SUBJECT_PREFIX = "traffic_camera:"
#: The registry-record claim cited via ``derived_from_claim_ids``.
REGISTRY_RECORD_PREDICATE = "traffic_camera"
RATIONALE = (
    "P35.16 geometry-defect corrections (R11-DATA-01 / F-322 / SIG-GEO-008): "
    "the published coordinate pair failed its declared detector bound; the "
    "defect claim marks the recorded verdict and — where the transposed "
    "pair is provable — corrected claims revise the originals. Originals "
    "are never rewritten; the truth is never fabricated."
)
#: The detector build stamped into each defect claim's evidence — kept in
#: parity with ``connectors.dot_511``'s ``_DETECTOR_VERSION``.
DETECTOR_VERSION = "sig.p35-16-geometry-detector/1"
#: The committed artifact schema the caller resolves scopes from.
ARTIFACT_SCHEMA = "sig.geometry-corrections/1"

#: The null-island bound — the F-322 measure ("within 1 degree of (0,0)").
_NULL_ISLAND_EPSILON_DEG = 1.0
#: The closed defect-class vocabulary — parity with the ingest detector.
DEFECT_CLASSES = frozenset({"axis_swap", "null_island", "sign_flip", "wrong_jurisdiction"})

#: Read passes batch over entity-id arrays of this size.
READ_BATCH_SIZE = 5_000
#: Supplementary claim_evidence links commit in batches of this size.
LINK_BATCH_SIZE = 10_000
#: Report example lists are capped; the COUNTS are always exact.
_EXAMPLE_CAP = 100

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)

_GROUP_SUBJECT_KEYS = (
    "SELECT value, entity_id::text FROM entity_identity_key "
    "WHERE scheme = 'sig.connector.subject' AND value LIKE %s "
    "ORDER BY value"
)
_SCAN_SUBJECT_KEYS = (
    "SELECT value, entity_id::text FROM entity_identity_key "
    "WHERE scheme = 'sig.connector.subject' "
    "AND value LIKE 'traffic/_camera:%' ESCAPE '/' "
    "ORDER BY value"
)
#: Latest claim per (subject, predicate): originals rank before corrections
#: of ours (``correction_reason`` set), then latest observation wins.
_COORD_CLAIMS = (
    "SELECT c.subject_id::text, c.predicate_id, c.claim_id::text, "
    "c.value_num::text, c.value_text, c.observed_at, c.correction_reason, "
    "r.connector_name "
    "FROM claim c JOIN ingest_run r ON r.run_id = c.ingest_run_id "
    "WHERE c.predicate_id = ANY(%s::text[]) AND c.subject_id = ANY(%s::uuid[]) "
    "ORDER BY c.subject_id, c.predicate_id, "
    "(c.correction_reason IS NULL) DESC, "
    "c.observed_at DESC NULLS LAST, c.claim_id DESC"
)
_DEFECT_CLAIMS = (
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
_REGISTERED = (
    "SELECT (SELECT count(*) FROM vocab_predicate WHERE predicate_id = %s), "
    "(SELECT count(*) FROM vocab_artifact_genre WHERE genre_id = %s)"
)

#: The supplementary link pass — (claim, capture, role) identity,
#: ON CONFLICT makes it +0-convergent (mirrors P35.15b).
_LINK_EVIDENCE_ROLES = (
    "INSERT INTO claim_evidence(claim_id, capture_id, role) "
    "SELECT l.claim_id::uuid, l.capture_id::uuid, l.role "
    "FROM unnest(%s::text[], %s::text[], %s::text[]) AS l(claim_id, capture_id, role) "
    "ON CONFLICT (claim_id, capture_id, role) DO NOTHING"
)


def parse_subject(value: str) -> tuple[str, str, str] | None:
    """``traffic_camera:<source>:<target>:<ref>`` -> (source, target, ref).

    ``None`` when the key is not the expected 4-part shape — a malformed key
    is counted, never guessed at.
    """
    parts = value.split(":", 3)
    if len(parts) != 4 or parts[0] != "traffic_camera":
        return None
    source, target, ref = parts[1], parts[2], parts[3]
    if not source or not target or not ref:
        return None
    return source, target, ref


# --- the defect classifier (parity with connectors.dot_511's detectors) ------


def _inside_extent(lat: float, lon: float, extent: Sequence[float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = extent
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def classify_defect(lat: float, lon: float, extent: Sequence[float] | None) -> str | None:
    """Classify an ORIGINAL stored pair against its declared bound.

    Deliberate parity with ``connectors.dot_511.detect_geometry_defect`` —
    the correction pass evaluates the claims the OLD emit wrote, so it runs
    the same rules on the same bound semantics (``db`` never imports a
    connector concept; the shared fixtures pin the parity). ``None`` means
    clean or not evaluable (no extent → ``null_island`` still evaluates; any
    other verdict needs a bound).
    """
    if abs(lat) <= _NULL_ISLAND_EPSILON_DEG and abs(lon) <= _NULL_ISLAND_EPSILON_DEG:
        return "null_island"
    if extent is None or _inside_extent(lat, lon, extent):
        return None
    if _inside_extent(lon, lat, extent):
        return "axis_swap"
    flips = int(_inside_extent(-lat, lon, extent)) + int(_inside_extent(lat, -lon, extent))
    if flips == 1:
        return "sign_flip"
    return "wrong_jurisdiction"


@dataclass(frozen=True)
class DefectScope:
    """One declared F-322 defect-group row (the committed artifact).

    ``extent`` is the declared bound the stored pair evaluates against —
    the target's own ``extent`` where declared, else its jurisdiction's
    ``jurisdiction_extents`` row (the CLI resolves it; ``None`` means the
    group evaluates ``null_island`` only). ``expected_class`` is the
    finding's headline class — the per-point classifier still derives the
    recorded class; the expectation is reported, never forced.
    """

    group: str
    source_id: str
    target_id: str
    expected_class: str
    extent: tuple[float, float, float, float] | None
    extent_ref: str
    license_spdx: str | None = None

    def subject_pattern(self) -> str:
        """The ``entity_identity_key`` LIKE pattern for the group's subjects."""
        return f"{SUBJECT_PREFIX}{self.source_id}:{self.target_id}:%"


def _sort_key(cap: CaptureRow) -> tuple[datetime, str]:
    """Latest retrieval wins; capture_id breaks ties deterministically."""
    return (cap.retrieved_at or _EPOCH, cap.capture_id)


def _batched(ids: Sequence[str], size: int = READ_BATCH_SIZE) -> list[list[str]]:
    return [list(ids[i : i + size]) for i in range(0, len(ids), size)]


@dataclass
class PlannedCorrection:
    """One in-scope subject flagged defective and what the pass will write."""

    subject: str
    entity_id: str
    scope: DefectScope
    defect_class: str
    observed_latitude: float
    observed_longitude: float
    #: The latest ORIGINAL coordinate claim ids — ``derived_from`` basis and
    #: (for axis_swap) the ``revises_claim`` targets.
    lat_claim_id: str
    lon_claim_id: str
    #: Registry-record claim ids additionally cited via derived_from_claim_ids.
    derived_from: list[str] = field(default_factory=list)
    #: Chosen binding capture (bindable actual occurrences only).
    bound: CaptureRow | None = None
    captures: list[CaptureRow] = field(default_factory=list)
    chosen: CaptureRow | None = None
    #: OUR defect-claim ids already on the subject (link top-up, +0 resume).
    ours_claim_ids: list[str] = field(default_factory=list)

    def defect_evidence(self) -> dict[str, Any]:
        """The recorded verdict carried in the defect claim's evidence."""
        return {
            "defect_class": self.defect_class,
            "observed_latitude": self.observed_latitude,
            "observed_longitude": self.observed_longitude,
            "declared_extent": (list(self.scope.extent) if self.scope.extent is not None else None),
            "extent_ref": self.scope.extent_ref,
            "defect_group": self.scope.group,
            "detector": DETECTOR_VERSION,
            "artifact": ARTIFACT_SCHEMA,
        }

    def defect_claim_record(self) -> dict[str, Any]:
        """The ``sig.assertion/1`` record for the subject's defect claim."""
        record: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": self.subject,
            "predicate_id": PREDICATE,
            "value": self.defect_class,
            "raw_value": self.defect_class,
            "evidence_genre": EVIDENCE_GENRE,
            "extraction_method": EXTRACTION_METHOD,
            "assertion_rationale": RATIONALE,
            "derived_from_claim_ids": sorted(
                {self.lat_claim_id, self.lon_claim_id, *self.derived_from}
            ),
            "source_id": self.scope.source_id,
            # The recorded verdict is the claim's citation anchor — the
            # adapter drops unknown top-level record keys, so the defect
            # record rides ``raw_context`` and lands durable on the row.
            "raw_context": {"geometry_defect": self.defect_evidence()},
        }
        if self.scope.license_spdx:
            record["license"] = self.scope.license_spdx
        return record

    def correction_claim_records(self) -> list[dict[str, Any]]:
        """The corrected coordinate claims — ``axis_swap`` verdicts only.

        The transposed pair is the PROVABLE correction (the declared bound
        accepts it, the observed pair fails it): the corrected latitude
        claim revises the original latitude claim, and symmetrically for
        longitude — both cite both originals via ``derived_from_claim_ids``.
        Every other class mints no replacement value.
        """
        if self.defect_class != "axis_swap":
            return []
        base: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": self.subject,
            "evidence_genre": EVIDENCE_GENRE,
            "extraction_method": EXTRACTION_METHOD,
            "assertion_rationale": RATIONALE,
            "correction_reason": "axis_swap",
            "derived_from_claim_ids": sorted({self.lat_claim_id, self.lon_claim_id}),
            "source_id": self.scope.source_id,
            "raw_context": {
                "geometry_correction": {
                    "defect_class": "axis_swap",
                    "observed_latitude": self.observed_latitude,
                    "observed_longitude": self.observed_longitude,
                    "extent_ref": self.scope.extent_ref,
                    "defect_group": self.scope.group,
                    "detector": DETECTOR_VERSION,
                }
            },
        }
        lat_claim = {
            **base,
            "predicate_id": "camera_latitude",
            "value": self.observed_longitude,
            "raw_value": str(self.observed_longitude),
            "revises_claim": self.lat_claim_id,
        }
        lon_claim = {
            **base,
            "predicate_id": "camera_longitude",
            "value": self.observed_latitude,
            "raw_value": str(self.observed_latitude),
            "revises_claim": self.lon_claim_id,
        }
        if self.scope.license_spdx:
            lat_claim["license"] = self.scope.license_spdx
            lon_claim["license"] = self.scope.license_spdx
        return [lat_claim, lon_claim]

    def claim_records(self) -> list[dict[str, Any]]:
        """Every claim row the subject's plan writes (defect + corrections)."""
        return [self.defect_claim_record(), *self.correction_claim_records()]


@dataclass
class CorrectionPlan:
    """What a dry run reports and what ``--apply`` executes (the same plan)."""

    scopes: list[DefectScope] = field(default_factory=list)
    #: group -> subjects keyed under it.
    scanned_by_group: dict[str, int] = field(default_factory=dict)
    pending: list[PlannedCorrection] = field(default_factory=list)
    #: Subjects already carrying OUR defect claim — links top up only.
    link_only: list[PlannedCorrection] = field(default_factory=list)
    #: Subjects already carrying ANOTHER writer's geometry_defect claim.
    marked_other: list[str] = field(default_factory=list)
    #: In-scope subjects whose stored pair classifies clean (e.g. a target's
    #: declared axis_order fix already landed via a later re-ingest).
    clean: dict[str, int] = field(default_factory=dict)
    #: In-scope subjects with no usable stored coordinate pair to evaluate.
    no_coordinates: dict[str, int] = field(default_factory=dict)
    #: Subjects whose stored pair is defective but carry no captures — never
    #: written (a claim without an evidence link violates §16).
    no_evidence: list[PlannedCorrection] = field(default_factory=list)
    malformed: list[str] = field(default_factory=list)
    aliased: int = 0
    #: The out-of-scope scan: (source/target) -> flagged subject count for
    #: targets whose (scheme,code) extent resolves but whose group is NOT
    #: declared — counted + reported, NEVER written (a defect group is
    #: corrected only under its committed declaration).
    flagged_outside_scope: dict[str, int] = field(default_factory=dict)
    scan_scanned: int = 0

    def by_group(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for pc in self.pending:
            out[pc.scope.group] = out.get(pc.scope.group, 0) + 1
        return dict(sorted(out.items()))

    def by_class(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for pc in self.pending:
            out[pc.defect_class] = out.get(pc.defect_class, 0) + 1
        return dict(sorted(out.items()))

    def planned_claims(self) -> int:
        return sum(1 + len(pc.correction_claim_records()) for pc in self.pending)

    def report(self) -> dict[str, Any]:
        """The dry-run document: full counts, capped examples, no writes."""
        return {
            "mode": "plan",
            "artifact": ARTIFACT_SCHEMA,
            "declared_groups": len(self.scopes),
            "subjects_scanned": dict(sorted(self.scanned_by_group.items())),
            "pending_subjects": len(self.pending),
            "pending_by_group": self.by_group(),
            "pending_by_class": self.by_class(),
            "planned_claims": self.planned_claims(),
            "link_topup_subjects": len(self.link_only),
            "marked_by_other_writers": len(self.marked_other),
            "skipped": {
                "clean": sum(self.clean.values()),
                "no_coordinates": sum(self.no_coordinates.values()),
                "no_evidence": len(self.no_evidence),
                "malformed": len(self.malformed),
                "aliased_entity_keys": self.aliased,
            },
            "clean_by_group": dict(sorted(self.clean.items())),
            "out_of_scope_scan": {
                "subjects_scanned": self.scan_scanned,
                "flagged_by_target": dict(sorted(self.flagged_outside_scope.items())),
                "note": (
                    "flagged subjects outside the declared groups are counted "
                    "and reported only — a defect group is corrected solely "
                    "under its committed sig.geometry-corrections declaration"
                ),
            },
            "examples": {
                "malformed": self.malformed[:_EXAMPLE_CAP],
                "no_evidence": [pc.subject for pc in self.no_evidence[:_EXAMPLE_CAP]],
                "pending": [pc.subject for pc in self.pending[:_EXAMPLE_CAP]],
            },
        }


def _coord_claims(conn: Any, entity_ids: Sequence[str]) -> dict[str, dict[str, Any]]:
    """Latest claims per (entity, coord predicate) + the original pair ids.

    Returns ``entity_id -> {"lat": (claim_id, value), "lon": (...),
    "corrected": bool}`` — ``corrected`` when OUR correction claims already
    landed (a re-run does not mint a second corrected pair).
    """
    out: dict[str, dict[str, Any]] = {}
    for batch in _batched(sorted(entity_ids)):
        for row in conn.execute(_COORD_CLAIMS, (list(COORD_PREDICATES), batch)).fetchall():
            (
                subject_id,
                predicate,
                claim_id,
                value_num,
                value_text,
                _observed_at,
                correction_reason,
                connector,
            ) = row
            slot = "lat" if predicate == "camera_latitude" else "lon"
            entry = out.setdefault(str(subject_id), {})
            if connector == CONNECTOR_NAME or correction_reason is not None:
                entry["corrected"] = True
                continue
            if slot in entry:
                continue  # ordered: first non-correction row is the latest original
            raw = value_num if value_num is not None else value_text
            try:
                entry[slot] = (str(claim_id), float(raw))
            except (TypeError, ValueError):
                entry.setdefault("bad", True)
    return out


def plan_corrections(
    conn: Any,
    scopes: Sequence[DefectScope],
    *,
    scan_extents: Mapping[tuple[str, str], tuple[float, float, float, float]] | None = None,
) -> CorrectionPlan:
    """Compute the correction plan — the dry-run and ``--apply`` share it.

    ``scopes`` is the resolved ``sig.geometry-corrections/1`` declaration
    (caller-owned; the connectors CLI resolves the committed artifact against
    the registry + jurisdiction extents). ``scan_extents`` optionally maps
    EVERY keyed ``(source, target)`` to its resolvable bound for the
    out-of-scope flag scan — reported counts only, never written.
    Read-only.
    """
    plan = CorrectionPlan(scopes=list(scopes))
    subjects: dict[str, tuple[DefectScope, str]] = {}  # entity -> (scope, key)
    for scope in scopes:
        rows = conn.execute(_GROUP_SUBJECT_KEYS, (scope.subject_pattern(),)).fetchall()
        plan.scanned_by_group[scope.group] = len(rows)
        for value, entity_id in rows:
            if parse_subject(str(value)) is None:
                plan.malformed.append(str(value))
                continue
            if str(entity_id) in subjects:
                plan.aliased += 1
                continue
            subjects[str(entity_id)] = (scope, str(value))
    if not subjects:
        _scan_out_of_scope(conn, plan, scopes, scan_extents)
        return plan

    ids = sorted(subjects)
    # Existing defect marks: ours top up links; other writers leave the
    # subject entirely untouched.
    marks: dict[str, list[tuple[str, str]]] = {}
    for batch in _batched(ids):
        for subject_id, claim_id, connector in conn.execute(
            _DEFECT_CLAIMS, (PREDICATE, batch)
        ).fetchall():
            marks.setdefault(str(subject_id), []).append((str(claim_id), str(connector)))

    coord = _coord_claims(conn, ids)
    # Registry-record claim ids — the derivation basis.
    derived: dict[str, list[str]] = {}
    for batch in _batched(ids):
        for subject_id, claim_id in conn.execute(
            _DERIVED_CLAIMS, (REGISTRY_RECORD_PREDICATE, batch)
        ).fetchall():
            derived.setdefault(str(subject_id), []).append(str(claim_id))

    flagged: list[PlannedCorrection] = []
    for entity_id in ids:
        scope, key = subjects[entity_id]
        claims = coord.get(entity_id, {})
        lat_slot, lon_slot = claims.get("lat"), claims.get("lon")
        corrected = bool(claims.get("corrected"))
        ours = [cid for cid, cname in marks.get(entity_id, []) if cname == CONNECTOR_NAME]
        other = [cid for cid, cname in marks.get(entity_id, []) if cname != CONNECTOR_NAME]
        if not lat_slot or not lon_slot or claims.get("bad"):
            plan.no_coordinates[scope.group] = plan.no_coordinates.get(scope.group, 0) + 1
            continue
        if corrected:
            # Our corrected pair (or any reasoned correction) already landed:
            # the stored "latest original" we read is pre-correction — the
            # verdict was recorded; nothing further to write.
            plan.link_only.append(
                PlannedCorrection(
                    subject=key,
                    entity_id=entity_id,
                    scope=scope,
                    defect_class=scope.expected_class,
                    observed_latitude=lat_slot[1],
                    observed_longitude=lon_slot[1],
                    lat_claim_id=lat_slot[0],
                    lon_claim_id=lon_slot[0],
                    ours_claim_ids=sorted(ours),
                )
            )
            continue
        defect = classify_defect(lat_slot[1], lon_slot[1], scope.extent)
        if defect is None:
            plan.clean[scope.group] = plan.clean.get(scope.group, 0) + 1
            continue
        if other and not ours:
            plan.marked_other.append(entity_id)
            continue
        pc = PlannedCorrection(
            subject=key,
            entity_id=entity_id,
            scope=scope,
            defect_class=defect,
            observed_latitude=lat_slot[1],
            observed_longitude=lon_slot[1],
            lat_claim_id=lat_slot[0],
            lon_claim_id=lon_slot[0],
            derived_from=sorted(set(derived.get(entity_id, []))),
            ours_claim_ids=sorted(ours),
        )
        if ours:
            plan.link_only.append(pc)
        else:
            flagged.append(pc)

    # Captures for pending + link-only subjects (evidence binding / top-up).
    capture_targets = [*flagged, *plan.link_only]
    captures: dict[str, dict[str, CaptureRow]] = {}
    cap_ids = sorted(ps.entity_id for ps in capture_targets)
    for batch in _batched(cap_ids):
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
        ps.bound = next((c for c in rows if c.bindable_for(ps.scope.source_id)), None)
        ps.chosen = ps.bound or (rows[0] if rows else None)
    for ps in flagged:
        if ps.captures:
            plan.pending.append(ps)
        else:
            plan.no_evidence.append(ps)
    plan.pending.sort(key=lambda pc: pc.subject)
    plan.link_only.sort(key=lambda pc: pc.subject)
    plan.no_evidence.sort(key=lambda pc: pc.subject)

    _scan_out_of_scope(conn, plan, scopes, scan_extents)
    return plan


def _scan_out_of_scope(
    conn: Any,
    plan: CorrectionPlan,
    scopes: Sequence[DefectScope],
    scan_extents: Mapping[tuple[str, str], tuple[float, float, float, float]] | None,
) -> None:
    """Flag-count every OTHER keyed subject — disclosure, never writes."""
    if not scan_extents:
        return
    declared = {(s.source_id, s.target_id) for s in scopes}
    rows = conn.execute(_SCAN_SUBJECT_KEYS).fetchall()
    plan.scan_scanned = len(rows)
    in_scope_ids: list[str] = []
    pairs: dict[str, tuple[tuple[str, str], str]] = {}
    for value, entity_id in rows:
        parsed = parse_subject(str(value))
        if parsed is None:
            continue
        source_id, target_id, _ref = parsed
        if (source_id, target_id) in declared:
            continue  # the group's own plan already evaluates these
        if (source_id, target_id) not in scan_extents:
            continue  # no resolvable bound — not evaluable, never flagged
        in_scope_ids.append(str(entity_id))
        pairs[str(entity_id)] = ((source_id, target_id), str(value))
    coord = _coord_claims(conn, in_scope_ids)
    for entity_id, ((source_id, target_id), _key) in pairs.items():
        claims = coord.get(entity_id, {})
        lat_slot, lon_slot = claims.get("lat"), claims.get("lon")
        if not lat_slot or not lon_slot or claims.get("bad") or claims.get("corrected"):
            continue
        extent = scan_extents[(source_id, target_id)]
        if classify_defect(lat_slot[1], lon_slot[1], extent) is not None:
            label = f"{source_id}/{target_id}"
            plan.flagged_outside_scope[label] = plan.flagged_outside_scope.get(label, 0) + 1


def _registration(conn: Any) -> dict[str, bool]:
    """The closed-vocabulary precheck the write leg requires (P35.14a).

    An unregistered ``geometry_defect`` predicate or ``camera_registry``
    genre would quarantine every claim under the closed sink — the leg
    refuses BEFORE writing instead of landing quarantine rows.
    """
    row = conn.execute(_REGISTERED, (PREDICATE, EVIDENCE_GENRE)).fetchone()
    assert row is not None
    return {
        "geometry_defect_predicate": bool(row[0]),
        "camera_registry_genre": bool(row[1]),
    }


def apply_plan(
    conn: Any,
    plan: CorrectionPlan,
    *,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    rights_resolver: Any = None,
    link_batch_size: int = LINK_BATCH_SIZE,
) -> dict[str, Any]:
    """Execute ``plan`` append-only through :class:`PgClaimSink`.

    Pending subjects group by their chosen binding capture and write one
    ``assert_claims(capture=binding)`` call per capture — chunked commits,
    ``is_replay`` so links classify ``replayed``. Unbound subjects write
    through the legacy evidence path; the supplementary pass then links
    every written claim to the subject's real captures. Originals are never
    touched — the pass reads them, it cannot rewrite them.
    """
    registered = _registration(conn)
    report = plan.report()
    report["mode"] = "apply"
    report["registered"] = registered
    if plan.pending and not all(registered.values()):
        # The leg's voided-by condition: refuse loud BEFORE any write.
        report["refused"] = (
            "closed-vocabulary gate: `geometry_defect` predicate and "
            "`camera_registry` genre must be registered before --apply "
            "(the vocab_geometry_defect sqitch change lands it)"
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
            "ticket": "P35.16",
            "manifest_row": "R11-DATA-01",
            "backfill": "geometry-corrections",
            "artifact": ARTIFACT_SCHEMA,
        },
    )
    bound_groups: dict[str, list[PlannedCorrection]] = {}
    unbound: list[PlannedCorrection] = []
    for pc in plan.pending:
        if pc.bound is not None:
            bound_groups.setdefault(pc.bound.capture_id, []).append(pc)
        else:
            unbound.append(pc)
    for capture_id in sorted(bound_groups):
        group = bound_groups[capture_id]
        records: list[dict[str, Any]] = []
        for pc in group:
            records.extend(pc.claim_records())
        sink.assert_claims(records, capture=group[0].bound.binding() if group[0].bound else None)
    for pc in unbound:
        sink.assert_claims(pc.claim_records())

    # Supplementary evidence links: every pending subject's written claims
    # and every earlier claim of OURS link each of the subject's existing
    # captures — 'establishes' on the chosen one, 'corroborates' on the rest.
    claim_ids: dict[str, list[str]] = {}
    pending_ids = sorted(pc.entity_id for pc in plan.pending)
    for batch in _batched(pending_ids):
        for subject_id, claim_id in conn.execute(
            "SELECT c.subject_id::text, c.claim_id::text FROM claim c "
            "JOIN ingest_run r ON r.run_id = c.ingest_run_id "
            "WHERE c.subject_id = ANY(%s::uuid[]) AND r.connector_name = %s",
            (batch, CONNECTOR_NAME),
        ).fetchall():
            claim_ids.setdefault(str(subject_id), []).append(str(claim_id))
    for pc in plan.link_only:
        claim_ids[pc.entity_id] = list(pc.ours_claim_ids)
    rows: list[tuple[str, str, str]] = []
    for pc in (*plan.pending, *plan.link_only):
        chosen_id = pc.chosen.capture_id if pc.chosen else None
        for cid in claim_ids.get(pc.entity_id, []):
            for cap in pc.captures:
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
            f"P35.16 geometry-defect corrections: pending={len(plan.pending)} "
            f"inserted={sink.report.inserted} duplicates={sink.report.duplicates} "
            f"links_planned={len(rows)} links_inserted={links_inserted}"
        ),
    )
    # Honest read-back: post counts are read, never assumed.
    marked_now = 0
    all_ids = sorted(
        {pc.entity_id for pc in (*plan.pending, *plan.link_only)} | set(plan.marked_other)
    )
    for batch in _batched(all_ids):
        rows_back = conn.execute(
            "SELECT count(DISTINCT subject_id) FROM claim "
            "WHERE predicate_id = %s AND subject_id = ANY(%s::uuid[])",
            (PREDICATE, batch),
        ).fetchone()
        marked_now += int(rows_back[0]) if rows_back else 0
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
        "in_scope_subjects_marked": marked_now,
        "in_scope_subjects_unmarked": len(all_ids) - marked_now,
    }
    return report


def run_corrections(
    dsn: str,
    *,
    scopes: Sequence[DefectScope],
    scan_extents: Mapping[tuple[str, str], tuple[float, float, float, float]] | None = None,
    apply: bool = False,
    code_commit: str = "unknown",
    commit_chunk_size: int | None = None,
    rights_resolver: Any = None,
) -> dict[str, Any]:
    """Open the DSN, plan, and (only with ``apply=True``) write."""
    with psycopg.connect(dsn, autocommit=True) as conn:
        plan = plan_corrections(conn, scopes, scan_extents=scan_extents)
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
    "ARTIFACT_SCHEMA",
    "CONNECTOR_NAME",
    "CONNECTOR_VERSION",
    "COORD_PREDICATES",
    "DEFECT_CLASSES",
    "DETECTOR_VERSION",
    "DefectScope",
    "CorrectionPlan",
    "EXTRACTION_METHOD",
    "PREDICATE",
    "PlannedCorrection",
    "RATIONALE",
    "apply_plan",
    "classify_defect",
    "parse_subject",
    "plan_corrections",
    "run_corrections",
]

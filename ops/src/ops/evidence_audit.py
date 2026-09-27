# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The legacy evidence audit — ``evidence-audit/1`` (P32.6, SIG-TRUST-007, ADR-125).

An offline, reproducible, read-only audit of the claim spine's evidence lineage,
built for the corpus that predates the 2026-09-25 persistent-capture roll
(ADR-111): captures written to container disk before the mount was durable are
*gone*, and this audit's job is to say exactly which claims can still be proven
— and which cannot — without ever pretending otherwise.

Three independent axes are reported for every sampled claim, because they are
independent questions:

1. **Capture availability** — are the recorded bytes still present at the pinned
   OCFL occurrence, and do they hash to the recorded ``content_digest``?
   (``verified_bytes`` / ``digest_mismatch`` / ``missing_object`` /
   ``unverified`` / ``no_byte_reference`` — the last an honest "no probe was
   mounted", never a silent "absent".)
2. **Occurrence confidence** — is the acquisition *event* provable? ``exact``
   (capture row + a matching ``ingest_run_capture`` mark agree on run, digest and
   occurrence), ``bounded`` (the capture row records the event but no mark
   corroborates), or ``unknown`` (dangling, contested or absent lineage).
3. **Locatability + extractor pinning** — does a *typed* locator address the
   bytes the extractor consumed, and is the extractor identity recorded?

The axes compose into the five DESIGN evidence states — ``exact_replayable``,
``document_locatable``, ``source_attributed_only``, ``unrecoverable`` and
``restricted_not_public`` — plus per-unit flags (``digest_mismatch``,
``ambiguous_lineage``, ``unsupported_role_mapping``, ``replay_disagreement``, …)
that explain *why* a unit landed where it did. No state is ever derived from
``source_id`` alone: ``exact_replayable`` requires bytes a probe actually
verified.

Semantic support is reported in the three forms the S1 research correction
requires — over ALL sampled eligible claims (unresolved counts as not
established), conditional fidelity over the adjudicated set, and the
adjudication yield — so missing evidence can never inflate a fidelity number by
disappearing from a denominator.

Everything here is pure: DB access is :mod:`db.evidence_audit` (the row loader),
capture bytes come through the narrow :class:`CaptureProbe` protocol, and the
reproducible report is deterministic given (population, seed, marks, bytes,
adjudications). The recovery planner is :mod:`ops.recovery_plan`.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol

__all__ = [
    "AUDIT_VERSION",
    "DEFAULT_ROLL_BOUNDARY",
    "PILOT_BYTE_BUDGET",
    "EvidenceGrade",
    "CaptureVerdict",
    "OccurrenceConfidence",
    "Adjudication",
    "CaptureRecord",
    "ClaimBinding",
    "ClaimUnit",
    "StratumKey",
    "CaptureProbe",
    "OcflCaptureProbe",
    "FixtureCaptureProbe",
    "NullCaptureProbe",
    "CaptureCheck",
    "UnitResult",
    "AuditReport",
    "units_from_rows",
    "load_input_json",
    "stratum_of",
    "run_audit",
    "verify_digest",
]

#: The audit contract version — stamped on every report so a later run can tell
#: which taxonomy produced it (ADR-125).
AUDIT_VERSION = "evidence-audit/1"

#: The persistent-capture-storage boundary. ADR-111/P31.4 added the durable
#: capture mount; captures retrieved before this instant lived on container
#: disk and are presumptively lost (the audit verifies, never assumes).
#: The date is the six-stream planning day the roll is anchored to.
DEFAULT_ROLL_BOUNDARY = "2026-09-25T00:00:00Z"

#: The S1 pilot ceiling: at most 2 GiB of distinct capture bytes are read in one
#: audit pass (research §6). Recovery batches get the tighter 250 MiB bound in
#: ops.recovery_plan.
PILOT_BYTE_BUDGET = 2 * 1024 * 1024 * 1024

#: The OCFL logical path the connector capture store writes raw bytes under —
#: duplicated here (rather than importing connectors) so the audit stays an
#: ops-layer concern; a connectors change MUST update both (both read the same
#: contract in the OCFL object).
_CAPTURE_LOGICAL_PATH = "capture"


class EvidenceGrade(StrEnum):
    """The five DESIGN evidence states (§55 / S1 research §5)."""

    #: Verified bytes + occurrence + valid locator + pinned extractor.
    EXACT_REPLAYABLE = "exact_replayable"
    #: Verified bytes + occurrence, but locator document-only/absent or the
    #: extractor identity is not recorded.
    DOCUMENT_LOCATABLE = "document_locatable"
    #: Source attribution exists (a document citation or a synthetic run
    #: record) but no preserved bytes prove the capture.
    SOURCE_ATTRIBUTED_ONLY = "source_attributed_only"
    #: Recorded evidence is gone or invalid — a capture row expects bytes the
    #: store cannot produce, or no lineage exists at all.
    UNRECOVERABLE = "unrecoverable"
    #: Preserved bytes exist but their recorded storage tier seals them from
    #: public verification — a distinct state, NEVER conflated with loss.
    RESTRICTED_NOT_PUBLIC = "restricted_not_public"


class CaptureVerdict(StrEnum):
    """What the probe could establish about one capture's recorded bytes."""

    #: Bytes present at the pinned occurrence and hash to ``content_digest``.
    VERIFIED = "verified_bytes"
    #: Bytes present but hash to a DIFFERENT digest — never adopted as the old
    #: capture; a recorded corruption/mis-keying finding.
    DIGEST_MISMATCH = "digest_mismatch"
    #: The OCFL object (or pinned version) is absent.
    MISSING = "missing_object"
    #: No probe was mounted or the read failed — an honest "not checked",
    #: distinct from proven-absent.
    UNVERIFIED = "unverified"
    #: The capture row records no byte expectation (synthetic zero-byte row
    #: with no marks, transcription placeholder) — nothing to verify.
    NO_BYTE_REFERENCE = "no_byte_reference"


class OccurrenceConfidence(StrEnum):
    """How provable the acquisition *event* is (independent of the bytes)."""

    #: Capture row + a run mark agree on run/digest/occurrence identity.
    EXACT = "exact"
    #: The capture row records the event (run + retrieved_at) but no run mark
    #: corroborates it (marks only exist post-P31.4).
    BOUNDED = "bounded"
    #: No provable acquisition: no capture row, dangling capture reference, or
    #: contested lineage (marks disagree).
    UNKNOWN = "unknown"


class Adjudication(StrEnum):
    """The semantic-support verdict for a sampled claim."""

    ESTABLISHED = "established"
    NOT_ESTABLISHED = "not_established"
    #: Cannot be determined offline — missing/ambiguous evidence, or a locator
    #: kind the audit cannot mechanically replay. Counts AGAINST
    #: ``support_all`` and against the adjudication yield, never vanishes.
    UNRESOLVED = "unresolved"


class CaptureClassification(StrEnum):
    ACTUAL = "actual"
    SYNTHETIC = "synthetic"
    LEGACY = "legacy"


RESTRICTED_TIERS = frozenset({"restricted", "sealed"})


# ---------------------------------------------------------------------------
# Input model — one ClaimUnit per claim, the audit's selected population.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaptureRecord:
    """One ``evidence_capture`` row (or the mark-only reference a binding names)."""

    capture_id: str | None
    classification: str | None = None  # actual|synthetic|legacy|None
    content_digest: str | None = None
    byte_size: int | None = None
    media_type: str | None = None
    ocfl_object_id: str | None = None
    ocfl_version: str | None = None
    storage_tier: str = "public"
    retrieved_at: str | None = None
    retrieved_by_run_id: str | None = None
    source_uri: str | None = None
    artifact_stable_locator: str | None = None
    artifact_type: str | None = None
    artifact_source_id: str | None = None
    capture_status: str | None = None
    #: ``ingest_run_capture`` marks naming this digest (occurrence attestation).
    marks: tuple[Mapping[str, Any], ...] = ()

    @property
    def expects_bytes(self) -> bool:
        """Whether the row records a real byte expectation (vs a placeholder)."""
        if self.classification == CaptureClassification.ACTUAL:
            return True
        if self.marks:
            return True
        if self.ocfl_object_id or self.ocfl_version:
            return True
        return bool(self.byte_size and self.byte_size > 0) or bool(
            self.content_digest and self.classification != CaptureClassification.SYNTHETIC
        )

    @property
    def restricted(self) -> bool:
        return (self.storage_tier or "public") in RESTRICTED_TIERS


@dataclass(frozen=True)
class ClaimBinding:
    """One ``claim_evidence`` link (P32.2 typed binding surface)."""

    role: str
    binding_status: str | None = None
    locator: Mapping[str, Any] | None = None
    extraction_id: str | None = None
    extraction_config_digest: str | None = None
    extractor_version: str | None = None
    extractor_name: str | None = None
    extraction_method: str | None = None
    bound_at: str | None = None
    capture: CaptureRecord | None = None
    #: set when ``ce.capture_id`` named a row that does not exist (dangling).
    dangling_capture_id: str | None = None

    @property
    def extractor_pinned(self) -> bool:
        return bool(self.extractor_version or self.extraction_method or self.extraction_id)


@dataclass(frozen=True)
class ClaimUnit:
    """One audited claim — the unit every denominator reconciles against."""

    claim_id: str
    predicate_id: str
    subject_id: str | None = None
    object_entity: str | None = None
    object_type: str | None = None
    value_kind: str | None = None
    value_text: str | None = None
    raw_value: str | None = None
    observed_at: str | None = None
    source_id: str | None = None
    connector_name: str | None = None
    connector_version: str | None = None
    code_commit: str | None = None
    is_replay: bool = False
    run_started_at: str | None = None
    ingest_run_id: str | None = None
    sensitivity_tier: int = 0
    review_status: str | None = None
    rights_spdx: str | None = None
    redistributable: str | None = None
    #: The licence compartment this claim's rights fall into (audit strata).
    compartment: str = "uncompartmented"
    bindings: tuple[ClaimBinding, ...] = ()
    #: None = eligibility unknown (fixture inputs); True/False = the shared
    #: `publication-eligibility/1` verdict from `claim_eligible_sql`.
    publication_eligible: bool | None = None
    #: Original loader row order — report determinism.
    row_index: int = 0


@dataclass(frozen=True)
class StratumKey:
    """The four-axis stratification the audit reports over."""

    source_family: str  # connector family / source family
    capture_epoch: str  # pre_roll | post_roll | undated
    predicate_role: str  # organisation-role of the predicate, or 'unmapped'
    compartment: str  # licence compartment of the claim's rights


# ---------------------------------------------------------------------------
# Capture probes — the byte store, behind the narrowest contract.
# ---------------------------------------------------------------------------


class CaptureProbe(Protocol):
    """The read side of a capture store. ``None`` from ``exists``/``read`` means
    "could not determine" — an unmounted or unreadable store is UNVERIFIED,
    never proven-absent."""

    def exists(self, object_id: str) -> bool | None: ...

    def read(self, object_id: str, version: str | None, logical_path: str) -> bytes | None: ...

    def describe(self) -> str: ...


class OcflCaptureProbe:
    """A probe over a real OCFL root (``OcflStore`` + a ``BlobStore``)."""

    def __init__(self, ocfl_store: Any, *, root_desc: str) -> None:
        self._store = ocfl_store
        self._desc = root_desc

    def exists(self, object_id: str) -> bool | None:
        try:
            return bool(self._store.object_exists(object_id))
        except Exception:
            return None

    def read(self, object_id: str, version: str | None, logical_path: str) -> bytes | None:
        try:
            if version is None:
                version = self._store.read_inventory(object_id)["head"]
            return self._store.resolve(object_id, version, logical_path)
        except Exception:
            return None

    def describe(self) -> str:
        return f"ocfl:{self._desc}"


class FixtureCaptureProbe:
    """An in-memory probe — ``{object_id: {version: bytes}}``. The dry-run
    fixtures and unit tests use it; a real mounted root uses OcflCaptureProbe."""

    def __init__(self, objects: Mapping[str, Mapping[str, bytes]], desc: str = "fixture") -> None:
        self._objects = dict(objects)
        self._desc = desc

    def exists(self, object_id: str) -> bool | None:
        return object_id in self._objects

    def read(self, object_id: str, version: str | None, logical_path: str) -> bytes | None:
        versions = self._objects.get(object_id)
        if versions is None:
            return None
        if version is not None:
            # A pinned version is either there or it isn't — never silently
            # fall back to head (that would mask a missing-occurrence finding).
            return versions.get(version)
        # unpinned: the newest version (mirrors OCFL head resolution)
        return versions[sorted(versions)[-1]] if versions else None

    def describe(self) -> str:
        return f"fixture:{self._desc}"


class NullCaptureProbe:
    """No store mounted — every read reports UNVERIFIED (honest unknown)."""

    def exists(self, object_id: str) -> bool | None:
        return None

    def read(self, object_id: str, version: str | None, logical_path: str) -> bytes | None:
        return None

    def describe(self) -> str:
        return "none-mounted"


NULL_PROBE = NullCaptureProbe()


# ---------------------------------------------------------------------------
# Digest verification — the recorded digest governs; we never adopt new bytes.
# ---------------------------------------------------------------------------


def verify_digest(recorded: str | None, data: bytes) -> str | None:
    """Return the algorithm whose digest of ``data`` equals ``recorded``.

    Two recorded formats exist in the corpus (P32.2 report §capture-format):
    the connectors' content multihash (base32 sha256 multihash — actual
    captures) and a plain sha256 hexdigest (the sink's synthetic per-run
    placeholder). Both are tried; ``None`` means the stored bytes do NOT match
    the recorded digest under either recorded algorithm — a real
    ``digest_mismatch``, never silently re-keyed.
    """
    if not recorded:
        return None
    from evidence.digest import multihash  # lazy: the workspace evidence pkg

    try:
        if multihash(data) == recorded:
            return "multihash-sha256-b32"
    except Exception:
        pass
    if hashlib.sha256(data).hexdigest() == recorded:
        return "sha256-hex"
    return None


# ---------------------------------------------------------------------------
# Capture verification + occurrence attestation.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CaptureCheck:
    """The probe verdict for one capture, with the attestation detail."""

    capture: CaptureRecord
    verdict: CaptureVerdict
    object_id: str | None = None
    version: str | None = None
    matched_algorithm: str | None = None
    restricted_access: bool = False
    detail: str = ""


def _mark_ocfl(marks: Sequence[Mapping[str, Any]]) -> tuple[str | None, str | None]:
    """The (object_id, version) the marks agree on, or (None, None)."""
    pairs = {(m.get("ocfl_object_id"), m.get("ocfl_version")) for m in marks}
    pairs = {p for p in pairs if p[0]}
    return next(iter(pairs)) if len(pairs) == 1 else (None, None)


def verify_capture(
    capture: CaptureRecord, probe: CaptureProbe, *, byte_budget: _ByteBudget | None = None
) -> CaptureCheck:
    """Verify one capture's recorded bytes against the probed store.

    The pinned ``ocfl_version`` is the occurrence of record; when the row lacks
    it the marks' agreeing pin is used, and a row with neither reads head
    flagged ``unpinned``. A restricted/sealed tier still attempts the read (the
    audit runner may hold privileged access) but records ``restricted_access``
    so the state never reads as a public verification.
    """
    restricted = capture.restricted
    if not capture.content_digest or not capture.expects_bytes:
        return CaptureCheck(
            capture,
            CaptureVerdict.NO_BYTE_REFERENCE,
            restricted_access=restricted,
            detail="capture row records no byte-bearing occurrence",
        )
    object_id = capture.ocfl_object_id
    version = capture.ocfl_version
    if not object_id:
        object_id, mark_version = _mark_ocfl(capture.marks)
        version = version or mark_version
    if not object_id:
        # The content-addressed convention: pre-P32.2 rows may lack the id but
        # the object is still keyed sig:capture:<digest>. Deriving it is honest
        # — it follows the connectors' own recorded address rule.
        object_id = f"sig:capture:{capture.content_digest}"
    exists = probe.exists(object_id)
    if exists is False and not restricted:
        return CaptureCheck(
            capture,
            CaptureVerdict.MISSING,
            object_id=object_id,
            version=version,
            restricted_access=restricted,
            detail="the recorded OCFL object is absent from the probed root",
        )
    if exists is False:
        # A restricted/sealed capture's absence from this root cannot be told
        # from "sealed away from us" — restriction is never conflated with loss.
        return CaptureCheck(
            capture,
            CaptureVerdict.UNVERIFIED,
            object_id=object_id,
            version=version,
            restricted_access=restricted,
            detail="restricted-tier object not readable at this root; cannot "
            "distinguish sealed-from-us from absent — reported unverified",
        )
    if exists is None:
        return CaptureCheck(
            capture,
            CaptureVerdict.UNVERIFIED,
            object_id=object_id,
            version=version,
            restricted_access=restricted,
            detail="the probe could not determine whether the object exists",
        )
    if byte_budget is not None and not byte_budget.take(capture.byte_size or 0):
        return CaptureCheck(
            capture,
            CaptureVerdict.UNVERIFIED,
            object_id=object_id,
            version=version,
            restricted_access=restricted,
            detail="byte budget exhausted before this capture could be read",
        )
    data = probe.read(object_id, version, _CAPTURE_LOGICAL_PATH)
    if data is None:
        if restricted:
            verdict = CaptureVerdict.UNVERIFIED
            detail = "restricted-tier bytes unreadable at this root — never 'missing'"
        elif version is not None:
            verdict = CaptureVerdict.MISSING
            detail = "the pinned version/logical path could not be resolved"
        else:
            verdict = CaptureVerdict.UNVERIFIED
            detail = "the object exists but the capture bytes could not be read"
        return CaptureCheck(
            capture,
            verdict,
            object_id=object_id,
            version=version,
            restricted_access=restricted,
            detail=detail,
        )
    algorithm = verify_digest(capture.content_digest, data)
    if algorithm is None:
        return CaptureCheck(
            capture,
            CaptureVerdict.DIGEST_MISMATCH,
            object_id=object_id,
            version=version,
            restricted_access=restricted,
            detail=(
                f"stored bytes hash to neither recorded format for "
                f"content_digest {capture.content_digest!r}"
            ),
        )
    return CaptureCheck(
        capture,
        CaptureVerdict.VERIFIED,
        object_id=object_id,
        version=version,
        matched_algorithm=algorithm,
        restricted_access=restricted,
        detail=(
            f"bytes verified under {algorithm}"
            + (" (restricted tier — privileged read)" if restricted else "")
        ),
    )


class _ByteBudget:
    """A bounded byte-read counter (the 2 GiB pilot ceiling)."""

    def __init__(self, limit: int) -> None:
        self.limit = int(limit)
        self.used = 0
        self.distinct: set[str] = set()
        self.exhausted = False

    def take(self, size: int, key: str | None = None) -> bool:
        """Consume ``size`` bytes of budget; False when the limit would be crossed."""
        if self.exhausted or self.used + int(size or 0) > self.limit:
            self.exhausted = True
            return False
        self.used += int(size or 0)
        if key:
            self.distinct.add(key)
        return True


def occurrence_confidence(
    capture: CaptureRecord, check: CaptureCheck
) -> tuple[OccurrenceConfidence, bool, str]:
    """Attest the acquisition event for one establishing capture.

    Returns ``(confidence, ambiguous, detail)``. ``exact`` needs the capture
    row's run and a mark agreeing on run + occurrence; ``bounded`` is the
    capture row alone; ``unknown`` is dangling/contested/none. ``ambiguous`` is
    the planner's zero-write trigger — set whenever the marks DISAGREE about
    the occurrence and the row cannot arbitrate.
    """
    if capture.capture_id is None:
        return OccurrenceConfidence.UNKNOWN, False, "no capture row exists"
    marks = list(capture.marks)
    if check.verdict == CaptureVerdict.NO_BYTE_REFERENCE and capture.classification in (
        CaptureClassification.SYNTHETIC,
        CaptureClassification.LEGACY,
    ):
        # A placeholder row still attests a run event, bounded at best.
        return (
            OccurrenceConfidence.BOUNDED
            if capture.retrieved_by_run_id
            else OccurrenceConfidence.UNKNOWN,
            False,
            "synthetic/legacy placeholder — run-recorded, never a byte acquisition",
        )
    if capture.retrieved_by_run_id:
        agreeing = [
            m
            for m in marks
            if m.get("run_id") == capture.retrieved_by_run_id
            and (
                not m.get("ocfl_object_id")
                or not capture.ocfl_object_id
                or m.get("ocfl_object_id") == capture.ocfl_object_id
            )
            and (
                not m.get("ocfl_version")
                or not capture.ocfl_version
                or m.get("ocfl_version") == capture.ocfl_version
            )
        ]
        if agreeing:
            return (
                OccurrenceConfidence.EXACT,
                False,
                f"run mark {agreeing[0].get('run_id')} attests the recorded occurrence",
            )
        if marks and not agreeing:
            return (
                OccurrenceConfidence.UNKNOWN,
                True,
                f"{len(marks)} mark(s) exist for the digest but none agrees with the "
                "capture row's run/occurrence",
            )
        return (
            OccurrenceConfidence.BOUNDED,
            False,
            "capture row records the acquisition run; no mark corroborates it",
        )
    # No recorded run → the capture row alone cannot attest the event.
    if marks:
        distinct = {(m.get("ocfl_object_id"), m.get("ocfl_version")) for m in marks}
        if len(distinct) == 1:
            return OccurrenceConfidence.BOUNDED, False, "marks agree but the row lacks a run"
        return (
            OccurrenceConfidence.UNKNOWN,
            True,
            f"marks disagree across {len(distinct)} occurrences and the row cannot arbitrate",
        )
    return OccurrenceConfidence.UNKNOWN, False, "no acquisition run and no marks recorded"


# ---------------------------------------------------------------------------
# Locator validation (SIG-PARSE-003) — reuse parsing.locator's typed contract.
# ---------------------------------------------------------------------------


def locator_check(locator: Mapping[str, Any] | None) -> tuple[bool, str]:
    """Whether ``locator`` is a valid typed locator row; ``(valid, kind)``."""
    if not locator:
        return False, "none"
    kind = locator.get("kind")
    if not kind:
        return False, "untyped"
    try:
        from parsing.locator import Locator, LocatorKind

        Locator(LocatorKind(str(kind)), {k: v for k, v in locator.items() if k != "kind"})
        return True, str(kind)
    except Exception as exc:
        return False, f"invalid:{type(exc).__name__}"


# ---------------------------------------------------------------------------
# Mechanical replay — where cheap and honest.
# ---------------------------------------------------------------------------


def _replay_located_bytes(
    data: bytes, locator: Mapping[str, Any], raw_value: str | None
) -> tuple[bool | None, str]:
    """Mechanically check that the located bytes support ``raw_value``.

    ``True`` = the located slice contains the recorded raw value;
    ``False`` = it does not (a real disagreement — an audit result, not an
    overwrite); ``None`` = the locator kind is not mechanically resolvable
    here (page/bbox/dom_path need the parsing stack; left to the adjudicator).
    """
    if raw_value is None:
        return None, "no raw_value recorded"
    kind = locator.get("kind")
    try:
        if kind == "byte_range":
            start, end = int(locator["start"]), int(locator["end"])
            located = data[start:end]
            return (
                raw_value.encode("utf-8") in located
                or located.decode("utf-8", "replace") == raw_value
            ), f"byte_range[{start}:{end}]"
        if kind == "row":
            # A record/row locator addresses the n-th non-blank line of a
            # line-oriented capture (CSV/JSONL feeds).
            row = int(locator["row"])
            text = data.decode("utf-8", "replace")
            lines = [ln for ln in text.splitlines() if ln.strip()]
            if row >= len(lines):
                return False, f"row {row} beyond {len(lines)} lines"
            return (raw_value in lines[row]), f"row {row}"
        if kind == "cell":
            row, col = int(locator["row"]), int(locator["column"])
            text = data.decode("utf-8", "replace")
            rows = list(csv.reader(io.StringIO(text)))
            if row >= len(rows) or col >= len(rows[row]):
                return False, f"cell[{row},{col}] out of range"
            return (raw_value in rows[row][col]), f"cell[{row},{col}]"
    except Exception as exc:
        return None, f"replay error:{type(exc).__name__}"
    return None, f"locator kind {kind!r} not mechanically resolvable"


# ---------------------------------------------------------------------------
# Unit construction — loader rows → ClaimUnits.
# ---------------------------------------------------------------------------


def compartment_of(unit_spdx: str | None, upstream: str | None = None) -> str:
    """The licence compartment a claim's rights record falls into.

    Uses ``policy.licensing.effective_license`` (upstream share-alike included)
    and the declared ``compartments()`` registry — never a hand-rolled map.
    """
    try:
        from policy.rights import RightsRecord

        from policy import licensing
    except Exception:  # pragma: no cover - policy is a workspace dep
        return unit_spdx or "undetermined"
    if not unit_spdx or unit_spdx.strip().upper() == "UNDETERMINED":
        return "undetermined"
    record = RightsRecord(
        source_id="audit",
        spdx=unit_spdx,
        attribution="",
        redistributable=True,
        derivative_permitted=True,
        terms_url="",
        retrieval_date=date(1970, 1, 1),  # compartment-name lookup only
        upstream_license=upstream,
    )
    try:
        license_id = licensing.effective_license(record)
    except Exception:
        license_id = unit_spdx
    try:
        for name, comp in licensing.compartments().items():
            if comp.get("license") == license_id:
                return str(name)
    except Exception:
        pass
    return license_id or "undetermined"


def units_from_rows(
    rows: Iterable[Mapping[str, Any]],
    marks: Mapping[str, Iterable[Mapping[str, Any]]],
    eligible_ids: Iterable[str] | None = None,
) -> list[ClaimUnit]:
    """Group flat loader rows into ``ClaimUnit``s.

    Rows with a ``capture_id`` that named no ``evidence_capture`` row surface a
    ``dangling_capture_id`` on the binding — the spine recorded a link to a
    capture it does not hold; that is real lineage damage, reported, not hidden.
    """
    eligible = set(eligible_ids) if eligible_ids is not None else None
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    order: list[str] = []
    for row in rows:
        cid = str(row["claim_id"])
        if cid not in grouped:
            grouped[cid] = []
            order.append(cid)
        grouped[cid].append(row)
    units: list[ClaimUnit] = []
    for idx, cid in enumerate(order):
        group = grouped[cid]
        first = group[0]
        bindings: list[ClaimBinding] = []
        seen_links: set[tuple[str | None, str]] = set()
        for row in group:
            capture_id = row.get("capture_id")
            link_key = (capture_id, str(row.get("role") or ""))
            if link_key in seen_links:
                continue
            seen_links.add(link_key)
            capture: CaptureRecord | None = None
            dangling: str | None = None
            if capture_id:
                if row.get("capture_digest") or row.get("artifact_id") or row.get("retrieved_at"):
                    digest = row.get("capture_digest")
                    capture = CaptureRecord(
                        capture_id=str(capture_id),
                        classification=row.get("capture_classification"),
                        content_digest=digest,
                        byte_size=row.get("byte_size"),
                        media_type=row.get("media_type"),
                        ocfl_object_id=row.get("ocfl_object_id"),
                        ocfl_version=row.get("ocfl_version"),
                        storage_tier=row.get("storage_tier") or "public",
                        retrieved_at=row.get("retrieved_at"),
                        retrieved_by_run_id=row.get("retrieved_by_run_id"),
                        source_uri=row.get("capture_source_uri"),
                        artifact_stable_locator=row.get("stable_locator"),
                        artifact_type=row.get("artifact_type"),
                        artifact_source_id=row.get("source_id"),
                        capture_status=row.get("capture_status"),
                        marks=tuple(marks.get(str(digest), ())) if digest else (),
                    )
                else:
                    dangling = str(capture_id)
            bindings.append(
                ClaimBinding(
                    role=str(row.get("role") or "establishes"),
                    binding_status=row.get("binding_status"),
                    locator=row.get("locator"),
                    extraction_id=row.get("binding_extraction_id"),
                    extraction_config_digest=row.get("extraction_config_digest"),
                    extractor_version=row.get("extractor_version")
                    or row.get("extraction_extractor_version"),
                    extractor_name=row.get("extraction_extractor_name"),
                    extraction_method=row.get("extraction_method"),
                    bound_at=row.get("bound_at"),
                    capture=capture,
                    dangling_capture_id=dangling,
                )
            )
        units.append(
            ClaimUnit(
                claim_id=cid,
                predicate_id=str(first.get("predicate_id") or ""),
                subject_id=first.get("subject_id"),
                object_entity=first.get("object_entity"),
                object_type=first.get("object_type"),
                value_kind=first.get("value_kind"),
                value_text=first.get("value_text"),
                raw_value=first.get("raw_value"),
                observed_at=first.get("observed_at"),
                source_id=first.get("source_id"),
                connector_name=first.get("connector_name"),
                connector_version=first.get("connector_version"),
                code_commit=first.get("code_commit"),
                is_replay=bool(first.get("is_replay")),
                run_started_at=first.get("run_started_at"),
                ingest_run_id=first.get("ingest_run_id"),
                sensitivity_tier=int(first.get("sensitivity_tier") or 0),
                review_status=first.get("review_status"),
                rights_spdx=first.get("spdx_expression"),
                redistributable=first.get("redistributable"),
                compartment=compartment_of(first.get("spdx_expression")),
                bindings=tuple(bindings),
                publication_eligible=(None if eligible is None else cid in eligible),
                row_index=idx,
            )
        )
    return units


def load_input_json(path: str | Path) -> tuple[list[ClaimUnit], dict[str, Any], set[str] | None]:
    """Load a dumped audit input (``db.evidence_audit.dump_rows`` shape)."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    eligible = set(doc.get("eligible_claim_ids") or []) or None
    units = units_from_rows(doc.get("rows", []), doc.get("marks", {}), eligible)
    return units, doc.get("watermark", {}), eligible


# ---------------------------------------------------------------------------
# Stratification + sampling.
# ---------------------------------------------------------------------------


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    except ValueError:
        return None


def _role_of(predicate_id: str) -> str:
    try:
        from db.organization_roles import role_for_predicate

        role = role_for_predicate(predicate_id)
        return role.value if role is not None else "unmapped"
    except Exception:
        return "unmapped"


def capture_epoch_of(unit: ClaimUnit, boundary: str) -> str:
    """The capture epoch the claim's newest establishing capture falls into."""
    bound = _parse_time(boundary)
    newest: datetime | None = None
    for b in unit.bindings:
        if b.role != "establishes" or not b.capture:
            continue
        at = _parse_time(b.capture.retrieved_at)
        if at is not None and (newest is None or at > newest):
            newest = at
    if newest is None:
        return "undated"
    return "post_roll" if (bound is None or newest >= bound) else "pre_roll"


def stratum_of(unit: ClaimUnit, boundary: str) -> StratumKey:
    """The four-axis stratum — every claim lands in exactly one bucket."""
    return StratumKey(
        source_family=unit.connector_name or unit.source_id or "unattributed",
        capture_epoch=capture_epoch_of(unit, boundary),
        predicate_role=_role_of(unit.predicate_id),
        compartment=unit.compartment,
    )


def _sample_key(seed: str, claim_id: str) -> str:
    return hashlib.sha256(f"{seed}|{claim_id}".encode()).hexdigest()


def draw_sample(
    strata: Mapping[StratumKey, list[ClaimUnit]], sample_size: int, seed: str
) -> dict[StratumKey, list[ClaimUnit]]:
    """A deterministic stratified probability sample.

    Within each stratum, claims order by ``sha256(seed|claim_id)`` — a seed the
    report records, so the frame is exactly reproducible and nothing outside it
    was sampled. Allocation is proportional with a largest-remainder floor of
    one drawn claim per non-empty stratum (an empty stratum draws zero).
    """
    total = sum(len(v) for v in strata.values())
    if sample_size <= 0 or total == 0:
        return {k: [] for k in strata}
    if sample_size >= total:
        return {k: list(v) for k, v in strata.items()}
    nonempty = {k: v for k, v in strata.items() if v}
    # Largest-remainder proportional allocation over non-empty strata; each
    # non-empty stratum gets a floor of one draw where the budget allows. When
    # the floor overshoots (more strata than draws), the least-undersized
    # strata give their floor up deterministically — the total drawn is ALWAYS
    # exactly min(sample_size, total).
    quotas = {k: sample_size * len(v) / total for k, v in nonempty.items()}
    alloc = {k: max(1, int(quotas[k])) for k in nonempty}
    while sum(alloc.values()) > sample_size:
        k = max(alloc, key=lambda k: (alloc[k] - quotas[k], alloc[k], str(k)))
        alloc[k] -= 1
    while sum(alloc.values()) < sample_size:
        k = max(alloc, key=lambda k: (quotas[k] - alloc[k], str(k)))
        alloc[k] += 1
    drawn: dict[StratumKey, list[ClaimUnit]] = {k: [] for k in strata}
    for k, units in nonempty.items():
        ordered = sorted(units, key=lambda u: (_sample_key(seed, u.claim_id), u.claim_id))
        drawn[k] = ordered[: min(alloc[k], len(units))]
    return drawn


# ---------------------------------------------------------------------------
# Unit classification.
# ---------------------------------------------------------------------------


@dataclass
class UnitResult:
    """The audit verdict for one claim."""

    unit: ClaimUnit
    grade: EvidenceGrade
    occurrence: OccurrenceConfidence
    capture_checks: list[CaptureCheck]
    flags: list[str] = field(default_factory=list)
    adjudication: Adjudication = Adjudication.UNRESOLVED
    adjudication_basis: str = ""
    replay_check: str = "not_checked"
    locator_kind: str | None = None
    #: For unresolved units: ``evidence_unavailable`` (missing/mismatched/
    #: ambiguous/restricted bytes prevented a verdict — stays in the fidelity
    #: denominator so missing evidence can never inflate it) vs
    #: ``needs_adjudication`` (a human/reviewer verdict is genuinely required).
    unresolved_reason: str | None = None

    @property
    def verified_public(self) -> bool:
        return any(
            c.verdict == CaptureVerdict.VERIFIED and not c.restricted_access
            for c in self.capture_checks
        )


def _best_establishing(unit: ClaimUnit) -> list[ClaimBinding]:
    return [b for b in unit.bindings if b.role == "establishes"]


def classify_unit(
    unit: ClaimUnit,
    checks: Mapping[int, CaptureCheck],
    *,
    adjudications: Mapping[str, str] | None = None,
    probe: CaptureProbe = NULL_PROBE,
    byte_budget: _ByteBudget | None = None,
) -> UnitResult:
    """Grade one claim from its (already verified) binding checks.

    ``checks`` maps ``index(unit.bindings)`` → :class:`CaptureCheck` for every
    establishing binding that had a capture to probe. The classification is a
    pure function of the unit + checks — nothing reads ``source_id`` to decide
    replayability.
    """
    establishing = _best_establishing(unit)
    flags: list[str] = []
    if any(b.dangling_capture_id for b in establishing):
        flags.append("dangling_capture")
    # Per-establishing-binding verdicts.
    verified_public: list[tuple[ClaimBinding, CaptureCheck]] = []
    verified_restricted: list[tuple[ClaimBinding, CaptureCheck]] = []
    unverified_records: list[tuple[ClaimBinding, CaptureCheck]] = []
    ambiguous = False
    occurrence_best = OccurrenceConfidence.UNKNOWN
    for idx, binding in enumerate(unit.bindings):
        if binding.role != "establishes":
            continue
        check = checks.get(idx)
        if binding.dangling_capture_id:
            ambiguous = True
            continue
        if binding.capture is None:
            continue
        if check is None:
            continue
        confidence, amb, _detail = occurrence_confidence(binding.capture, check)
        ambiguous = ambiguous or amb
        if _confidence_rank(confidence) > _confidence_rank(occurrence_best):
            occurrence_best = confidence
        if check.verdict == CaptureVerdict.VERIFIED:
            (verified_restricted if check.restricted_access else verified_public).append(
                (binding, check)
            )
        else:
            unverified_records.append((binding, check))
        if check.verdict == CaptureVerdict.DIGEST_MISMATCH:
            flags.append("digest_mismatch")
    if ambiguous:
        flags.append("ambiguous_lineage")

    # --- grade rollup ------------------------------------------------------
    grade = EvidenceGrade.UNRECOVERABLE
    if verified_public:
        # Best verified public binding: a valid locator + pinned extractor make
        # the claim exactly replayable; deterministic tie-break on capture_id.
        def _rank(item: tuple[ClaimBinding, CaptureCheck]) -> tuple[bool, bool, str]:
            binding, _check = item
            locator_ok = locator_check(binding.locator)[0]
            return (
                not locator_ok,
                not binding.extractor_pinned,
                (binding.capture.capture_id if binding.capture else "") or "",
            )

        chosen_binding, _chosen_check = min(verified_public, key=_rank)
        valid, kind = locator_check(chosen_binding.locator)
        if valid and chosen_binding.extractor_pinned:
            grade = EvidenceGrade.EXACT_REPLAYABLE
        else:
            grade = EvidenceGrade.DOCUMENT_LOCATABLE
            if not valid:
                flags.append("no_exact_locator")
            if not chosen_binding.extractor_pinned:
                flags.append("no_extractor_identity")
    elif verified_restricted:
        # Every entry here is VERIFIED; the tier alone makes it non-public.
        grade = EvidenceGrade.RESTRICTED_NOT_PUBLIC
    elif unverified_records or establishing:
        # A recorded evidence link exists — decide whether preserved bytes were
        # expected (and are therefore genuinely missing) vs only source
        # attribution ever existed.
        byte_expected = any(
            (b.capture and b.capture.expects_bytes) or b.dangling_capture_id for b in establishing
        )
        restricted_rows = [b for b in establishing if b.capture and b.capture.restricted]
        if restricted_rows and not any(byte_expected_public(b) for b in establishing):
            grade = EvidenceGrade.RESTRICTED_NOT_PUBLIC
            flags.append("restricted_unverified")
        elif byte_expected:
            grade = EvidenceGrade.UNRECOVERABLE
        else:
            grade = EvidenceGrade.SOURCE_ATTRIBUTED_ONLY
    elif unit.source_id or unit.connector_name:
        # No evidence link at all — the ingestion run attributes a source
        # family but nothing proves a capture.
        grade = EvidenceGrade.UNRECOVERABLE

    # --- unsupported-role flag ---------------------------------------------
    try:
        from db.organization_roles import mints_entity_ref

        if mints_entity_ref(unit.predicate_id) and unit.object_entity:
            support = any(c.verdict == CaptureVerdict.VERIFIED for c in checks.values())
            if not support:
                flags.append("unsupported_role_mapping")
    except Exception:
        pass

    result = UnitResult(
        unit=unit,
        grade=grade,
        occurrence=occurrence_best,
        capture_checks=list(checks.values()),
        flags=flags,
    )

    # --- adjudication ------------------------------------------------------
    supplied = (adjudications or {}).get(unit.claim_id)
    if supplied in {a.value for a in Adjudication}:
        result.adjudication = Adjudication(supplied)
        result.adjudication_basis = "adjudicator-supplied"
        if supplied == Adjudication.UNRESOLVED:
            result.unresolved_reason = (
                "evidence_unavailable"
                if grade in (EvidenceGrade.UNRECOVERABLE, EvidenceGrade.RESTRICTED_NOT_PUBLIC)
                or ambiguous
                else "needs_adjudication"
            )
        return result
    if grade == EvidenceGrade.EXACT_REPLAYABLE:
        # Mechanical replay where the locator kind allows it.
        chosen_idx: int | None = None
        for idx, b in enumerate(unit.bindings):
            check = checks.get(idx)
            if (
                b.role == "establishes"
                and b.capture is not None
                and b.locator
                and check is not None
                and check.verdict == CaptureVerdict.VERIFIED
                and not check.restricted_access
            ):
                chosen_idx = idx
                break
        chosen = unit.bindings[chosen_idx] if chosen_idx is not None else None
        if chosen is not None and chosen.locator and chosen_idx is not None:
            check = checks[chosen_idx]
            data = probe.read(check.object_id or "", check.version, _CAPTURE_LOGICAL_PATH)
            if data is not None:
                verdict, detail = _replay_located_bytes(data, chosen.locator, unit.raw_value)
                result.replay_check = detail
                if verdict is True:
                    result.adjudication = Adjudication.ESTABLISHED
                    result.adjudication_basis = "mechanical replay of located bytes"
                elif verdict is False:
                    result.adjudication = Adjudication.NOT_ESTABLISHED
                    result.adjudication_basis = "located bytes disagree with the recorded value"
                    result.flags.append("replay_disagreement")
                else:
                    result.adjudication_basis = detail
            else:
                result.replay_check = "bytes_unreadable"
                result.adjudication_basis = "verified bytes could not be re-read for replay"
        else:
            result.adjudication_basis = "no replayable binding selected"
    elif grade == EvidenceGrade.UNRECOVERABLE:
        result.adjudication_basis = "evidence unavailable — cannot be adjudicated"
        result.unresolved_reason = "evidence_unavailable"
    elif grade == EvidenceGrade.RESTRICTED_NOT_PUBLIC:
        result.adjudication_basis = "restricted bytes — public adjudication not permitted"
        result.unresolved_reason = "evidence_unavailable"
    elif grade == EvidenceGrade.DOCUMENT_LOCATABLE:
        result.adjudication_basis = "bytes verified but no exact locator/extractor to replay"
        result.unresolved_reason = "needs_adjudication"
    else:
        result.adjudication_basis = "source attribution only — nothing to replay"
        result.unresolved_reason = "needs_adjudication"
    # An EXACT_REPLAYABLE unit the mechanical check could not resolve (locator
    # kind needing a human/parser) is needs_adjudication, not evidence loss.
    if result.adjudication == Adjudication.UNRESOLVED and result.unresolved_reason is None:
        result.unresolved_reason = (
            "evidence_unavailable"
            if grade in (EvidenceGrade.UNRECOVERABLE, EvidenceGrade.RESTRICTED_NOT_PUBLIC)
            else "needs_adjudication"
        )
    if ambiguous:
        result.adjudication = Adjudication.UNRESOLVED
        result.unresolved_reason = "evidence_unavailable"
        result.adjudication_basis += "; ambiguous lineage"
    return result


def _confidence_rank(c: OccurrenceConfidence) -> int:
    return {
        OccurrenceConfidence.UNKNOWN: 0,
        OccurrenceConfidence.BOUNDED: 1,
        OccurrenceConfidence.EXACT: 2,
    }[c]


def byte_expected_public(b: ClaimBinding) -> bool:
    return bool(b.capture and b.capture.expects_bytes and not b.capture.restricted)


# ---------------------------------------------------------------------------
# The audit report.
# ---------------------------------------------------------------------------


@dataclass
class StratumReport:
    key: StratumKey
    universe: int
    drawn: int
    weight: float
    grades: dict[str, int] = field(default_factory=dict)
    metrics: dict[str, dict[str, int]] = field(default_factory=dict)


@dataclass
class AuditReport:
    """The reproducible audit report — JSON-serializable end to end."""

    audit_version: str
    generated_at: str | None
    input: dict[str, Any]
    census: dict[str, Any]
    strata: list[dict[str, Any]]
    units: list[dict[str, Any]]
    metrics: dict[str, Any]
    adjudication: dict[str, Any]
    findings: list[dict[str, Any]]
    limitations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "audit_version": self.audit_version,
            "generated_at": self.generated_at,
            "input": self.input,
            "census": self.census,
            "strata": self.strata,
            "units": self.units,
            "metrics": self.metrics,
            "adjudication": self.adjudication,
            "findings": self.findings,
            "limitations": self.limitations,
        }

    def dumps(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"

    def digest(self) -> str:
        return hashlib.sha256(self.dumps().encode("utf-8")).hexdigest()

    def write(self, path: str | Path) -> None:
        Path(path).write_text(self.dumps(), encoding="utf-8")


def _stratum_dict(key: StratumKey) -> str:
    return "|".join([key.source_family, key.capture_epoch, key.predicate_role, key.compartment])


def run_audit(
    units: Sequence[ClaimUnit],
    probe: CaptureProbe = NULL_PROBE,
    *,
    seed: str,
    sample_size: int,
    boundary: str = DEFAULT_ROLL_BOUNDARY,
    targeted_ids: Iterable[str] = (),
    adjudications: Mapping[str, str] | None = None,
    watermark: Mapping[str, Any] | None = None,
    input_source: str = "rows",
    code_commit: str | None = None,
    generated_at: str | None = None,
    byte_budget: int = PILOT_BYTE_BUDGET,
) -> AuditReport:
    """Run the audit over a selected population and produce the report.

    ``units`` IS the selected population — every denominator reconciles to it.
    ``targeted_ids`` names the publication-sensitive/known-problem set drawn
    separately (always included, never weighted into the probability metrics).
    """
    boundary = boundary or DEFAULT_ROLL_BOUNDARY
    # --- strata over the FULL population (the census) ----------------------
    strata_map: dict[StratumKey, list[ClaimUnit]] = {}
    for u in units:
        strata_map.setdefault(stratum_of(u, boundary), []).append(u)
    # --- the probability sample + the targeted set --------------------------
    targeted = set(targeted_ids)
    sample_strata = draw_sample(strata_map, sample_size, seed)
    sampled_ids = {u.claim_id for units_ in sample_strata.values() for u in units_} | (
        targeted & {u.claim_id for u in units}
    )
    weights: dict[str, float] = {}
    for key, drawn in sample_strata.items():
        universe = len(strata_map.get(key, ()))
        for u in drawn:
            if u.claim_id in targeted:
                continue
            weights[u.claim_id] = (universe / len(drawn)) if drawn else 0.0

    # --- per-unit verification + classification ----------------------------
    budget = _ByteBudget(byte_budget)
    results: list[UnitResult] = []
    for unit in units:
        checks: dict[int, CaptureCheck] = {}
        for idx, binding in enumerate(unit.bindings):
            if binding.role != "establishes" or binding.capture is None:
                continue
            checks[idx] = verify_capture(binding.capture, probe, byte_budget=budget)
        result = classify_unit(unit, checks, adjudications=adjudications, probe=probe)
        results.append(result)

    # --- census + denominators ---------------------------------------------
    def _bucket(values: Iterable[str]) -> dict[str, int]:
        out: dict[str, int] = {}
        for v in values:
            out[v] = out.get(v, 0) + 1
        return dict(sorted(out.items()))

    census: dict[str, Any] = {
        "claims": len(units),
        "bindings": sum(len(u.bindings) for u in units),
        "establishing_bindings": sum(len(_best_establishing(u)) for u in units),
        "claims_with_evidence_links": sum(1 for u in units if u.bindings),
        "by_source_family": _bucket(stratum_of(u, boundary).source_family for u in units),
        "by_capture_epoch": _bucket(stratum_of(u, boundary).capture_epoch for u in units),
        "by_predicate_role": _bucket(stratum_of(u, boundary).predicate_role for u in units),
        "by_compartment": _bucket(u.compartment for u in units),
        "reconciles": True,
    }
    census["reconciles"] = all(
        sum(census[k].values()) == census["claims"]
        for k in ("by_source_family", "by_capture_epoch", "by_predicate_role", "by_compartment")
    )

    # --- metrics over the sampled units ------------------------------------
    sampled = [r for r in results if r.unit.claim_id in sampled_ids]
    targeted_results = [r for r in sampled if r.unit.claim_id in targeted]
    prob_results = [r for r in sampled if r.unit.claim_id not in targeted]

    def _num_den(
        numerator: Iterable[UnitResult], denominator: Iterable[UnitResult]
    ) -> dict[str, Any]:
        num = list(numerator)
        den = list(denominator)
        w_num = sum(weights.get(r.unit.claim_id, 1.0) for r in num)
        w_den = sum(weights.get(r.unit.claim_id, 1.0) for r in den)
        return {
            "numerator": len(num),
            "denominator": len(den),
            "fraction": (len(num) / len(den)) if den else None,
            "weighted_fraction": (w_num / w_den) if w_den else None,
        }

    def _establishing_verified(r: UnitResult) -> bool:
        return any(c.verdict == CaptureVerdict.VERIFIED for c in r.capture_checks)

    def _locator_ok(r: UnitResult) -> bool:
        return any(locator_check(b.locator)[0] for b in _best_establishing(r.unit))

    def _document_only(r: UnitResult) -> bool:
        return any(b.binding_status == "document_only" for b in _best_establishing(r.unit))

    eligible_known = [r for r in prob_results if r.unit.publication_eligible is not None]

    metrics: dict[str, Any] = {
        "source_attribution": _num_den(
            (r for r in prob_results if r.unit.source_id or r.capture_checks),
            prob_results,
        ),
        "verified_capture_availability": _num_den(
            (r for r in prob_results if _establishing_verified(r)), prob_results
        ),
        "occurrence_confidence": {
            "exact": _num_den(
                (r for r in prob_results if r.occurrence == OccurrenceConfidence.EXACT),
                prob_results,
            ),
            "bounded": _num_den(
                (r for r in prob_results if r.occurrence == OccurrenceConfidence.BOUNDED),
                prob_results,
            ),
            "unknown": _num_den(
                (r for r in prob_results if r.occurrence == OccurrenceConfidence.UNKNOWN),
                prob_results,
            ),
        },
        "exact_locator_coverage": {
            **_num_den((r for r in prob_results if _locator_ok(r)), prob_results),
            "document_occurrence_without_locator": sum(
                1 for r in prob_results if _document_only(r) and not _locator_ok(r)
            ),
        },
        "replay_success": _num_den(
            (
                r
                for r in prob_results
                if r.adjudication == Adjudication.ESTABLISHED
                and r.adjudication_basis == "mechanical replay of located bytes"
            ),
            (r for r in prob_results if r.grade == EvidenceGrade.EXACT_REPLAYABLE),
        ),
        "publication_eligibility": _num_den(
            (r for r in eligible_known if r.unit.publication_eligible), eligible_known
        ),
        "legacy_synthetic_exposure": _num_den(
            (
                r
                for r in prob_results
                if _best_establishing(r.unit)
                and all(
                    (b.capture is None)
                    or (b.capture.classification in ("synthetic", "legacy"))
                    or b.binding_status in ("legacy_synthetic", "document_only")
                    for b in _best_establishing(r.unit)
                )
            ),
            prob_results,
        ),
        "grade_distribution": _bucket(r.grade.value for r in prob_results),
        "occurrence_distribution": _bucket(r.occurrence.value for r in prob_results),
    }
    # Per-stratum metric slices for the headline fractions.
    metrics["by_stratum"] = {}
    for key, drawn in sample_strata.items():
        drawn_results = [
            r
            for r in results
            if r.unit.claim_id in {u.claim_id for u in drawn} and r.unit.claim_id not in targeted
        ]
        metrics["by_stratum"][_stratum_dict(key)] = {
            "universe": len(strata_map.get(key, ())),
            "drawn": len(drawn),
            "verified_capture_availability": _num_den(
                (r for r in drawn_results if _establishing_verified(r)), drawn_results
            )["fraction"],
            "exact_replayable": sum(
                1 for r in drawn_results if r.grade == EvidenceGrade.EXACT_REPLAYABLE
            ),
            "unrecoverable": sum(
                1 for r in drawn_results if r.grade == EvidenceGrade.UNRECOVERABLE
            ),
        }

    # --- the semantic trio --------------------------------------------------
    sampled_eligible = prob_results  # the audit's eligible population = sampled
    adjudicated = [r for r in sampled_eligible if r.adjudication != Adjudication.UNRESOLVED]
    established = [r for r in adjudicated if r.adjudication == Adjudication.ESTABLISHED]
    unresolved = [r for r in sampled_eligible if r.adjudication == Adjudication.UNRESOLVED]
    # Units whose EVIDENCE prevented a verdict (missing/mismatched/ambiguous/
    # restricted) stay in the fidelity denominator — the anti-inflation rule:
    # losing evidence can never push conditional_fidelity up by removing the
    # unit from it. Units unresolved only because a human verdict is owed
    # (needs_adjudication) leave it — that is the honest "conditional" part.
    unadjudicable = [r for r in unresolved if r.unresolved_reason == "evidence_unavailable"]
    fidelity_denominator = len(adjudicated) + len(unadjudicable)
    adjudication_block = {
        "sampled_eligible": len(sampled_eligible),
        "adjudicated": len(adjudicated),
        "established": len(established),
        "not_established": sum(
            1 for r in adjudicated if r.adjudication == Adjudication.NOT_ESTABLISHED
        ),
        "unresolved": len(unresolved),
        "unresolved_evidence_unavailable": len(unadjudicable),
        "unresolved_needs_adjudication": len(unresolved) - len(unadjudicable),
        # Form 1: support over ALL sampled eligible claims — unresolved counts
        # as not established (missing evidence never leaves the denominator).
        "support_all": (len(established) / len(sampled_eligible) if sampled_eligible else None),
        # Form 2: conditional fidelity — over units a verdict could apply to:
        # the adjudicated set PLUS the unadjudicable-by-evidence-loss set
        # (conservative: evidence loss counts against fidelity, never for it).
        "conditional_fidelity": (
            len(established) / fidelity_denominator if fidelity_denominator else None
        ),
        "conditional_fidelity_denominator": fidelity_denominator,
        # Form 3: how much of the sample could be adjudicated at all.
        "adjudication_yield": (
            len(adjudicated) / len(sampled_eligible) if sampled_eligible else None
        ),
    }

    # --- targeted set, reported separately ----------------------------------
    targeted_block = [
        {
            "claim_id": r.unit.claim_id,
            "grade": r.grade.value,
            "occurrence": r.occurrence.value,
            "adjudication": r.adjudication.value,
            "flags": r.flags,
        }
        for r in targeted_results
    ]

    # --- findings -----------------------------------------------------------
    findings: list[dict[str, Any]] = []
    for r in results:
        if "digest_mismatch" in r.flags:
            findings.append(
                {
                    "kind": "digest_mismatch",
                    "claim_id": r.unit.claim_id,
                    "detail": "stored bytes do not match the recorded content_digest",
                }
            )
        if "ambiguous_lineage" in r.flags:
            findings.append(
                {
                    "kind": "ambiguous_lineage",
                    "claim_id": r.unit.claim_id,
                    "detail": "marks disagree or a capture reference dangles",
                }
            )
        if "unsupported_role_mapping" in r.flags:
            findings.append(
                {
                    "kind": "unsupported_role_mapping",
                    "claim_id": r.unit.claim_id,
                    "predicate_id": r.unit.predicate_id,
                    "detail": "entity-ref predicate with no verified evidence supporting the role",
                }
            )
    missing = [
        r for r in results if any(c.verdict == CaptureVerdict.MISSING for c in r.capture_checks)
    ]
    for r in missing:
        findings.append(
            {
                "kind": "missing_bytes",
                "claim_id": r.unit.claim_id,
                "detail": "recorded capture bytes absent from the probed root",
            }
        )

    unit_rows: list[dict[str, Any]] = []
    for r in results:
        unit_rows.append(
            {
                "claim_id": r.unit.claim_id,
                "predicate_id": r.unit.predicate_id,
                "source_family": stratum_of(r.unit, boundary).source_family,
                "stratum": _stratum_dict(stratum_of(r.unit, boundary)),
                "in_sample": r.unit.claim_id in sampled_ids,
                "in_targeted_set": r.unit.claim_id in targeted,
                "sample_weight": weights.get(r.unit.claim_id),
                "grade": r.grade.value,
                "occurrence_confidence": r.occurrence.value,
                "flags": r.flags,
                "adjudication": r.adjudication.value,
                "adjudication_basis": r.adjudication_basis,
                "unresolved_reason": r.unresolved_reason,
                "replay_check": r.replay_check,
                "publication_eligible": r.unit.publication_eligible,
                "capture_checks": [
                    {
                        "capture_id": c.capture.capture_id,
                        "verdict": c.verdict.value,
                        "object_id": c.object_id,
                        "version": c.version,
                        "byte_size": c.capture.byte_size,
                        "matched_algorithm": c.matched_algorithm,
                        "restricted_access": c.restricted_access,
                        "detail": c.detail,
                    }
                    for c in r.capture_checks
                ],
            }
        )

    strata_rows = [
        {
            "key": _stratum_dict(k),
            "source_family": k.source_family,
            "capture_epoch": k.capture_epoch,
            "predicate_role": k.predicate_role,
            "compartment": k.compartment,
            "universe": len(strata_map[k]),
            "drawn": len(sample_strata.get(k, ())),
            "weight": (len(strata_map[k]) / len(sample_strata[k]))
            if sample_strata.get(k)
            else None,
        }
        for k in sorted(strata_map, key=_stratum_dict)
    ]

    population_digest = hashlib.sha256(
        json.dumps(sorted(u.claim_id for u in units)).encode()
    ).hexdigest()
    input_block = {
        "population_source": input_source,
        "claim_count": len(units),
        "population_digest": f"sha256:{population_digest}",
        "seed": seed,
        "sample_size_requested": sample_size,
        "sampled": len(sampled_ids),
        "targeted": len(targeted & {u.claim_id for u in units}),
        "roll_boundary": boundary,
        "capture_probe": probe.describe(),
        "byte_budget": byte_budget,
        "bytes_read": budget.used,
        "byte_budget_exhausted": budget.exhausted,
        "code_commit": code_commit,
        "watermark": dict(watermark or {}),
    }

    limitations = [
        "Offline read-only audit: no live fetch, no spine mutation, no publication change.",
        "occurrence 'exact' requires post-P31.4 ingest_run_capture marks; pre-roll "
        "acquisitions are 'bounded' by construction, not 'exact'.",
        "Mechanical replay covers byte_range/row/cell locators; page/bbox/dom_path "
        "and normalization-level fidelity need the adjudicator instrument (HUMAN-H4).",
        "unverified captures (no probe mounted / restricted unreadable) are reported "
        "as unverified, never counted as missing.",
    ]

    return AuditReport(
        audit_version=AUDIT_VERSION,
        generated_at=generated_at,
        input=input_block,
        census=census,
        strata=strata_rows,
        units=unit_rows,
        metrics=metrics,
        adjudication={**adjudication_block, "targeted_set": targeted_block},
        findings=findings,
        limitations=limitations,
    )


def render_audit_markdown(report: AuditReport) -> str:
    """A human-readable summary of the audit report (AUDIT_REPORT.md)."""
    d = report.to_dict()
    inp, cen, met, adj = d["input"], d["census"], d["metrics"], d["adjudication"]

    def _pct(value: Any) -> str:
        return "n/a" if value is None else f"{value * 100:.1f}%"

    def _frac(block: Mapping[str, Any]) -> str:
        return (
            f"{block['numerator']}/{block['denominator']} "
            f"({_pct(block['fraction'])}; weighted {_pct(block.get('weighted_fraction'))})"
        )

    strata_rows = "\n".join(
        "| {key} | {universe} | {drawn} | {weight} |".format(
            key=s["key"],
            universe=s["universe"],
            drawn=s["drawn"],
            weight="n/a" if s["weight"] is None else f"{s['weight']:.3f}",
        )
        for s in d["strata"]
    )
    metrics_rows = "\n".join(
        [
            f"| source attribution | {_frac(met['source_attribution'])} |",
            f"| verified capture availability | {_frac(met['verified_capture_availability'])} |",
            f"| occurrence — exact | {_frac(met['occurrence_confidence']['exact'])} |",
            f"| occurrence — bounded | {_frac(met['occurrence_confidence']['bounded'])} |",
            f"| occurrence — unknown | {_frac(met['occurrence_confidence']['unknown'])} |",
            f"| exact locator coverage | {_frac(met['exact_locator_coverage'])} "
            f"(document-occurrence w/o locator: "
            f"{met['exact_locator_coverage']['document_occurrence_without_locator']}) |",
            f"| replay success (mechanical) | {_frac(met['replay_success'])} |",
            f"| publication eligibility | {_frac(met['publication_eligibility'])} |",
            f"| legacy/synthetic exposure | {_frac(met['legacy_synthetic_exposure'])} |",
        ]
    )
    grade_rows = "\n".join(
        f"| {grade} | {count} |" for grade, count in met["grade_distribution"].items()
    )
    findings_rows = (
        "\n".join(
            f"| {f['kind']} | {f['claim_id']} | {f.get('detail', '')} |" for f in d["findings"]
        )
        or "| — | — | — |"
    )
    limitations = "\n".join(f"- {item}" for item in d["limitations"])
    targeted = (
        "\n".join(
            f"| {t['claim_id']} | {t['grade']} | {t['occurrence']} | {t['adjudication']} |"
            for t in adj.get("targeted_set", [])
        )
        or "| — | — | — | — |"
    )
    sample_row = f"{inp['sample_size_requested']}/{inp['sampled']} (+{inp['targeted']} targeted)"
    bytes_row = (
        f"{inp['bytes_read']}/{inp['byte_budget']} (exhausted: {inp['byte_budget_exhausted']})"
    )
    claims_row = (
        f"{cen['claims']} claims; links {cen['bindings']}; "
        f"establishing {cen['establishing_bindings']}"
    )
    sem_rows = "\n".join(
        [
            f"| support over ALL sampled eligible claims | {adj['established']}/"
            f"{adj['sampled_eligible']} = {_pct(adj['support_all'])} |",
            f"| conditional adjudicated fidelity | {adj['established']}/"
            f"{adj['conditional_fidelity_denominator']} = {_pct(adj['conditional_fidelity'])} |",
            f"| adjudication yield | {adj['adjudicated']}/{adj['sampled_eligible']}"
            f" = {_pct(adj['adjudication_yield'])} |",
            "| unresolved — evidence unavailable (stays in fidelity denominator) "
            f"| {adj['unresolved_evidence_unavailable']} |",
            f"| unresolved — needs adjudication | {adj['unresolved_needs_adjudication']} |",
        ]
    )

    return f"""# Legacy evidence audit — `{d["audit_version"]}`

> Read-only, offline, reproducible. Generated {d.get("generated_at") or "(deterministic run)"}.

## Input identity (the reproducibility contract)

| field | value |
|---|---|
| population source | `{inp["population_source"]}` |
| claims selected | {inp["claim_count"]} |
| population digest | `{inp["population_digest"]}` |
| seed | `{inp["seed"]}` |
| sample requested/drawn | {sample_row} |
| roll boundary | `{inp["roll_boundary"]}` |
| capture probe | `{inp["capture_probe"]}` |
| bytes read/budget | {bytes_row} |
| code commit | `{inp.get("code_commit")}` |

## Census (denominators reconcile: {cen["reconciles"]})

- {claims_row}
- by source family: `{cen["by_source_family"]}`
- by capture epoch: `{cen["by_capture_epoch"]}`
- by predicate role: `{cen["by_predicate_role"]}`
- by compartment: `{cen["by_compartment"]}`

## Strata

| stratum (family|epoch|role|compartment) | universe | drawn | weight |
|---|---|---|---|
{strata_rows}

## Metrics (probability sample)

| metric | n/d |
|---|---|
{metrics_rows}

### Grade distribution

| grade | claims |
|---|---|
{grade_rows}

## Semantic support (the three required forms)

| form | value |
|---|---|
{sem_rows}

### Targeted set (reported separately, never weighted)

| claim | grade | occurrence | adjudication |
|---|---|---|---|
{targeted}

## Findings

| kind | claim | detail |
|---|---|---|
{findings_rows}

## Limitations

{limitations}
"""

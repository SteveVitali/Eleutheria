# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The versioned typed-assertion contract (P32.2, SIG-TRUST-001/002).

``sig.assertion/1`` is the production assertion interface a connector record is
adapted into before the sink persists it. It exists so the fields connectors and
parsers already know — typed value, raw lexical value, unit, scope, valid time,
epistemic axes, sensitivity, compartment/rights, derivation and correction
links, qualifiers, and the actual capture the extraction consumed — survive the
trip to the spine instead of being flattened to a string claim.

Three rules the module enforces mechanically:

* **Defaults are named, versioned and basis-labelled.** Every default the
  adapter applies is recorded in ``defaulted`` (field → basis); the sink stamps
  ``claim.assertion_map_id``/``assertion_map_basis`` with them, so an absent
  field can never silently become stronger evidence or lower sensitivity.
* **Unknown fails closed, never guessed.** A record whose declared
  ``object_type``/``value_kind`` is not in the vocabulary, whose binding digest
  does not decode, or whose locator is not a valid :mod:`parsing.locator` shape
  yields a :class:`Rejection` — the sink appends an ``assertion_quarantine`` row
  and the claim is not written. The rest of the batch still lands: one bad
  assertion cannot make a valid entity disappear.
* **The binding is the actual capture.** ``CaptureBinding`` carries the digest,
  source URI, byte size, retrieval time (the *source observation* time a replay
  preserves) and the OCFL object/version of the captured artifact consumed —
  never the synthetic per-run placeholder the pre-P32.2 sink invented.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from evidence.digest import decode_multihash
from parsing.locator import InvalidLocator, Locator, LocatorKind

#: The schema version of the envelope this module produces.
ASSERTION_SCHEMA_VERSION = "sig.assertion/1"

#: The named versioned connector→sink mapping (SIG-TRUST-001: "a named
#: versioned mapping and an explicit basis"). Stamped on every new claim row.
ASSERTION_MAP_ID = "sig.assertion.map.v1"


class QuarantineReason(StrEnum):
    """The ``assertion_quarantine.reason`` vocabulary (deploy CHECK).

    Each value names ONE machine-checkable failure so a rejected assertion is
    auditable without exposing its unreviewed content.
    """

    BAD_DIGEST = "bad_digest"
    UNKNOWN_PREDICATE = "unknown_predicate"
    UNKNOWN_OBJECT_TYPE = "unknown_object_type"
    UNKNOWN_VALUE_KIND = "unknown_value_kind"
    MISSING_CAPTURE_BINDING = "missing_capture_binding"
    UNSUPPORTED_LOCATOR = "unsupported_locator"
    EXTRACTOR_FAILURE = "extractor_failure"
    VERSION_MISMATCH = "version_mismatch"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    UNKNOWN_QUALIFIER = "unknown_qualifier"


#: The ``claim_evidence.binding_status`` vocabulary (deploy CHECK).
BINDING_ACTUAL = "actual_capture"
BINDING_REPLAYED = "replayed"
BINDING_DOCUMENT_ONLY = "document_only"
BINDING_LEGACY = "legacy_synthetic"

#: The ``evidence_capture.capture_classification`` vocabulary (deploy CHECK).
CAPTURE_ACTUAL = "actual"
CAPTURE_SYNTHETIC = "synthetic"
CAPTURE_LEGACY = "legacy"

#: The vocabularies the adapter validates against (mirrors seed_vocab.sql /
#: claim_enums.sql; the DB CHECK remains the final word).
_VALUE_KINDS = frozenset({"value", "somevalue", "novalue"})
_OBJECT_TYPES = frozenset(
    {
        "literal",
        "entity_ref",
        "vocab_term",
        "quantity",
        "money",
        "geometry",
        "duration",
        "interval",
        "document_ref",
    }
)
_EVIDENCE_ROLES = frozenset(
    {
        "establishes",
        "corroborates",
        "contextualizes",
        "contradicts",
        "supersedes_basis",
        "attests_absence",
    }
)
_LOCATOR_KINDS = frozenset(k.value for k in LocatorKind)
_RANKS = frozenset({"preferred", "normal", "deprecated"})
_REVIEW_STATUSES = frozenset(
    {"unreviewed", "machine_accepted", "human_verified", "disputed", "retracted"}
)
_POLARITIES = frozenset({"affirms", "denies"})
_DIRECTNESS = frozenset({"D1", "D2", "D3", "D4", "D5", "D6"})
_INTEGRITY = frozenset({"I1", "I2", "I3"})
_RELIABILITY = frozenset({"R1", "R2", "R3", "R4", "R5", "R6"})
_OBSERVED_KINDS = frozenset({"exact", "approximate", "bounded_above", "unknown"})
_VALID_KINDS = frozenset({"exact", "ongoing", "unknown", "before", "after", "never"})


@dataclass(frozen=True)
class Rejection:
    """A fail-closed refusal of one record, destined for ``assertion_quarantine``."""

    reason: QuarantineReason
    detail: str
    payload: dict[str, Any]

    @property
    def payload_digest(self) -> str:
        """The idempotency key of the quarantine row (content-keyed, +0 re-run)."""
        return hashlib.sha256(
            json.dumps(self.payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class CaptureBinding:
    """The actual captured artifact an extraction consumed (SIG-TRUST-002).

    ``retrieved_at`` is the **source observation time** — a replay preserves the
    original value while the replay's own assertion time lands on
    ``claim.sys_period``. ``ocfl_version`` pins the immutable occurrence version;
    a binding never resolves a mutable "latest" sidecar.
    """

    digest: str
    source_uri: str
    media_type: str
    byte_size: int
    retrieved_at: datetime
    ocfl_object_id: str
    ocfl_version: str | None
    replayed: bool = False
    #: The ``ingest_run`` that originally acquired these bytes (replay lineage —
    #: the occurrence row keeps it as ``retrieved_by_run_id``; ``None`` on a live
    #: binding, where the current run is the acquirer).
    original_run_id: str | None = None


def _get(obj: Any, name: str) -> Any:
    """Read ``name`` off a mapping or an attribute-bearing object (CaptureRef)."""
    if isinstance(obj, Mapping):
        return obj.get(name)
    return getattr(obj, name, None)


def binding_of(capture: Any, *, replayed: bool = False) -> CaptureBinding | Rejection:
    """Normalise a ``CaptureRef``/mapping into a :class:`CaptureBinding`, or reject.

    A binding MUST name the bytes consumed: a non-decodable multihash digest is
    ``bad_digest``; a missing digest or source URI is ``missing_capture_binding``.
    """
    if capture is None:
        return Rejection(
            QuarantineReason.MISSING_CAPTURE_BINDING,
            "the claim was asserted with no capture binding",
            {"capture": None},
        )
    digest = str(_get(capture, "digest") or "")
    source_uri = str(_get(capture, "source_uri") or "")
    if not digest or not source_uri:
        return Rejection(
            QuarantineReason.MISSING_CAPTURE_BINDING,
            "a capture binding MUST name its digest and source URI",
            {"digest": digest, "source_uri": source_uri},
        )
    try:
        decode_multihash(digest)
    except Exception as exc:  # noqa: BLE001 - any decode failure is bad_digest
        return Rejection(
            QuarantineReason.BAD_DIGEST,
            f"capture digest {digest!r} is not a decodable multihash ({type(exc).__name__})",
            {"digest": digest},
        )
    retrieved = _get(capture, "retrieved_at")
    if isinstance(retrieved, date) and not isinstance(retrieved, datetime):
        retrieved = datetime(retrieved.year, retrieved.month, retrieved.day, tzinfo=UTC)
    if isinstance(retrieved, datetime) and retrieved.tzinfo is None:
        retrieved = retrieved.replace(tzinfo=UTC)
    if not isinstance(retrieved, datetime):
        # evidence_capture.retrieved_at is NOT NULL: a capture MUST name when the
        # bytes were acquired. None is never fabricated (SIG-TRUST-002).
        return Rejection(
            QuarantineReason.MISSING_CAPTURE_BINDING,
            "a capture binding MUST carry its retrieval time (the source "
            "observation time evidence_capture.retrieved_at records)",
            {"digest": digest, "source_uri": source_uri},
        )
    size = _get(capture, "byte_size")
    ocfl_object = str(_get(capture, "ocfl_object_id") or f"sig:capture:{digest}")
    ocfl_version = _get(capture, "ocfl_version")
    original_run = _get(capture, "original_run_id")
    return CaptureBinding(
        digest=digest,
        source_uri=source_uri,
        media_type=str(_get(capture, "media_type") or "application/octet-stream"),
        byte_size=int(size) if size is not None else 0,
        retrieved_at=retrieved,
        ocfl_object_id=ocfl_object,
        ocfl_version=str(ocfl_version) if ocfl_version else None,
        replayed=replayed,
        original_run_id=str(original_run) if original_run else None,
    )


@dataclass(frozen=True)
class TypedLocator:
    """One validated locator row destined for ``claim_evidence.locator``."""

    row: dict[str, Any]


def locator_of(
    record: Mapping[str, Any], *, byte_size: int
) -> tuple[TypedLocator, str] | Rejection:
    """Resolve the claim's typed locator, or the explicit document-only limitation.

    Sources consulted in order: ``record["locator"]``, then
    ``record["evidence"]["locator"]``. The value must be a valid
    :meth:`parsing.locator.Locator.to_row` shape — an unknown kind or malformed
    fields is ``unsupported_locator`` (fail closed, never silently re-anchored).

    With no locator at all the binding is honestly document-scoped: a
    ``byte_range`` covering the whole capture plus binding_status
    ``document_only`` (SIG-TRUST-002's "explicit document-only limitation").
    """
    raw = record.get("locator")
    if raw is None:
        ev = record.get("evidence")
        if isinstance(ev, Mapping):
            raw = ev.get("locator")
    if raw is None:
        return (
            TypedLocator({"kind": "byte_range", "start": 0, "end": int(byte_size)}),
            BINDING_DOCUMENT_ONLY,
        )
    rows = raw if isinstance(raw, Sequence) and not isinstance(raw, (str, Mapping)) else [raw]
    first = rows[0] if rows else None
    if not isinstance(first, Mapping):
        return Rejection(
            QuarantineReason.UNSUPPORTED_LOCATOR,
            f"locator must be a mapping of kind+fields, got {type(first).__name__}",
            {"locator": str(first)[:200]},
        )
    kind = str(first.get("kind") or "")
    if kind not in _LOCATOR_KINDS:
        return Rejection(
            QuarantineReason.UNSUPPORTED_LOCATOR,
            f"locator kind {kind!r} is not one of {sorted(_LOCATOR_KINDS)}",
            {"locator": dict(first)},
        )
    fields = {k: v for k, v in first.items() if k != "kind"}
    try:
        locator = Locator(LocatorKind(kind), fields)
    except InvalidLocator as exc:
        return Rejection(
            QuarantineReason.UNSUPPORTED_LOCATOR,
            str(exc),
            {"locator": dict(first)},
        )
    return (TypedLocator(locator.to_row()), BINDING_ACTUAL)


@dataclass(frozen=True)
class AssertionQualifier:
    """One typed qualifier row destined for ``claim_qualifier`` (FIELD_MAP §3).

    ``qualifier_id`` is a ``vocab_predicate`` id — the qualifier vocabulary is
    the same registered predicate surface, never a free-text key. Value columns
    are exclusive in practice; the widened unique index keys them all.
    """

    qualifier_id: str
    value_text: str | None = None
    value_num: str | None = None
    value_bool: bool | None = None
    value_entity: str | None = None
    unit: str | None = None
    jurisdiction: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    rank: str = "normal"


def qualifier_of(raw: Mapping[str, Any]) -> AssertionQualifier | Rejection:
    """Normalise one record qualifier, or reject (``unknown_qualifier``)."""
    qid = str(raw.get("qualifier_id") or raw.get("key") or "")
    if not qid:
        return Rejection(
            QuarantineReason.UNKNOWN_QUALIFIER,
            "a qualifier MUST name its qualifier_id (a registered predicate id)",
            {"qualifier": dict(raw)},
        )
    value = raw.get("value")
    rank = str(raw.get("rank") or "normal")
    vf, vt = _coerce_date(raw.get("valid_from")), _coerce_date(raw.get("valid_to"))
    if isinstance(value, bool):
        return AssertionQualifier(
            qid,
            value_bool=value,
            unit=_str_or_none(raw.get("unit")),
            jurisdiction=_str_or_none(raw.get("jurisdiction")),
            valid_from=vf,
            valid_to=vt,
            rank=rank,
        )
    if isinstance(value, (int, float)) and value is not None:
        return AssertionQualifier(
            qid,
            value_num=str(value),
            unit=_str_or_none(raw.get("unit")),
            jurisdiction=_str_or_none(raw.get("jurisdiction")),
            valid_from=vf,
            valid_to=vt,
            rank=rank,
        )
    entity = raw.get("value_entity") or raw.get("entity_ref")
    return AssertionQualifier(
        qid,
        value_text=str(value) if value is not None else None,
        value_entity=str(entity) if entity else None,
        unit=_str_or_none(raw.get("unit")),
        jurisdiction=_str_or_none(raw.get("jurisdiction")),
        valid_from=vf,
        valid_to=vt,
        rank=rank,
    )


def _coerce_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _datetime_or_none(value: Any) -> datetime | None:
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


@dataclass
class TypedAssertion:
    """The ``sig.assertion/1`` envelope: every field the claim row preserves.

    Field names mirror the ``claim`` columns they persist to; ``defaulted``
    records field → basis for every adapter-applied default (SIG-TRUST-001).
    """

    subject: str
    predicate: str
    object_type: str
    value_kind: str
    value_text: str | None
    value_int: str | None
    value_float: str | None
    value_bool: bool | None
    value_json: str | None
    unit: str | None
    raw_value: str
    raw_context: str | None
    normalization_id: str | None
    normalization_version: str | None
    valid_from: str | None
    valid_to: str | None
    valid_edtf: str | None
    valid_from_kind: str
    valid_to_kind: str
    observed_at: str | None
    observed_edtf: str | None
    observed_at_kind: str
    observed_unknown_reason: str | None
    source_reliability: str
    reliability_provisional: bool
    claim_directness: str
    artifact_integrity: str
    legacy_source_tier: str | None
    claim_polarity: str
    rank: str
    review_status: str
    sensitivity_tier: int
    assertion_rationale: str | None
    derived_from_claim_ids: list[str]
    revises_claim: str | None
    retraction_of: str | None
    correction_reason: str | None
    evidence_role: str
    extraction_method: str
    extractor_version: str | None
    extraction_config_digest: str | None
    #: The model identity an ``llm_assisted`` extraction MUST carry (the
    #: ``extraction`` CHECK); ``None`` for deterministic methods.
    extraction_model_id: str | None
    extraction_prompt_version: str | None
    locator_row: dict[str, Any] | None
    binding_status: str
    qualifiers: list[AssertionQualifier]
    defaulted: dict[str, str] = field(default_factory=dict)

    def map_basis(self, *, replayed: bool = False, synthetic: bool = False) -> str:
        """The explicit basis string for ``claim.assertion_map_basis``."""
        if synthetic:
            return "legacy_synthetic"
        parts = [f"replay_of:{self.extraction_method}"] if replayed else ["connector_record"]
        for name in sorted(self.defaulted):
            parts.append(f"{name}={self.defaulted[name]}")
        return "|".join(parts)


def assertion_from_record(
    record: Mapping[str, Any],
    *,
    binding: CaptureBinding | None = None,
    replayed: bool = False,
) -> TypedAssertion | Rejection:
    """Adapt one connector claim record into the ``sig.assertion/1`` envelope.

    ``binding=None`` produces the legacy-synthetic envelope (pre-P32.2 path):
    the claim still lands, but its evidence link is honestly classified
    ``legacy_synthetic`` and no capture provenance is claimed. With a binding,
    every carried field is preserved; an unknown/malformed one yields a
    :class:`Rejection` instead of a claim (fail closed, quarantine upstream).
    """
    subject = str(record.get("subject_id") or "")
    predicate = str(record.get("predicate_id") or "")
    if not subject or not predicate:
        return Rejection(
            QuarantineReason.MISSING_REQUIRED_FIELD,
            "a claim MUST name subject_id and predicate_id",
            {"subject_id": subject, "predicate_id": predicate, "record": dict(record)},
        )
    defaulted: dict[str, str] = {}

    # -- object type: declared, never inferred silently -----------------------
    object_type = str(record.get("object_type") or "")
    if not object_type:
        object_type = "entity_ref" if record.get("object_ref") else "literal"
        defaulted["object_type"] = "inferred_from_value_shape"
    elif object_type not in _OBJECT_TYPES:
        return Rejection(
            QuarantineReason.UNKNOWN_OBJECT_TYPE,
            f"object_type {object_type!r} is not in vocab_object_type {sorted(_OBJECT_TYPES)}",
            {"record": dict(record)},
        )

    # -- value kind: declared or derived from the value, basis recorded --------
    value = record.get("value")
    raw_field = record.get("raw_value")
    declared_kind = record.get("value_kind")
    if declared_kind is not None:
        value_kind = str(declared_kind)
        if value_kind not in _VALUE_KINDS:
            return Rejection(
                QuarantineReason.UNKNOWN_VALUE_KIND,
                f"value_kind {value_kind!r} is not in {sorted(_VALUE_KINDS)}",
                {"record": dict(record)},
            )
    elif value is not None or (raw_field is not None and str(raw_field) != ""):
        value_kind = "value"
        defaulted["value_kind"] = "derived_from_value_presence"
    else:
        value_kind = "novalue"
        defaulted["value_kind"] = "absent_value_is_novalue"

    value_text: str | None = None
    value_int: str | None = None
    value_float: str | None = None
    value_bool: bool | None = None
    if value is not None and value_kind == "value":
        value_text = str(value)
        if isinstance(value, bool):
            value_bool = value
        elif isinstance(value, int):
            value_int = str(int(value))
        elif isinstance(value, float):
            value_float = repr(float(value))
    elif raw_field is not None and str(raw_field) != "" and value_kind == "value":
        value_text = str(raw_field)

    raw_value = (
        str(raw_field) if raw_field is not None else (str(value) if value is not None else "")
    )
    raw_context = record.get("raw_context")
    unit = _str_or_none(record.get("unit"))
    if object_type == "quantity" and not unit:
        return Rejection(
            QuarantineReason.MISSING_REQUIRED_FIELD,
            "object_type 'quantity' REQUIRES a unit (claim_unit_required)",
            {"record": dict(record)},
        )
    value_json = record.get("value_json")
    normalization_id = _str_or_none(record.get("normalization_id"))
    normalization_version = _str_or_none(record.get("normalization_version"))

    # -- T1 valid time: absent stays honestly unknown, never a fabricated date --
    valid_from = _datetime_or_none(record.get("valid_from"))
    valid_to = _datetime_or_none(record.get("valid_to"))
    valid_from_kind = str(record.get("valid_from_kind") or ("exact" if valid_from else "unknown"))
    valid_to_kind = str(record.get("valid_to_kind") or ("exact" if valid_to else "unknown"))
    if valid_from_kind not in _VALID_KINDS or valid_to_kind not in _VALID_KINDS:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"valid-time kinds must be in {sorted(_VALID_KINDS)}; got "
            f"{valid_from_kind!r}/{valid_to_kind!r}",
            {"record": dict(record)},
        )
    if "valid_from" not in record and "valid_from_kind" not in record:
        defaulted["valid_from_kind"] = "absent_is_unknown"
    if "valid_to" not in record and "valid_to_kind" not in record:
        defaulted["valid_to_kind"] = "absent_is_unknown"

    # -- T2 observation time ---------------------------------------------------
    observed_at = _datetime_or_none(record.get("observed_at"))
    if observed_at is None and binding is not None and binding.retrieved_at is not None:
        # The capture's retrieval time is the source observation time — an
        # honest basis, recorded (SIG-TRUST-002: replay retains original time).
        observed_at = binding.retrieved_at
        defaulted["observed_at"] = "capture_retrieved_at"
    observed_at_kind = str(
        record.get("observed_at_kind") or ("exact" if observed_at else "unknown")
    )
    if observed_at_kind not in _OBSERVED_KINDS:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"observed_at_kind {observed_at_kind!r} not in {sorted(_OBSERVED_KINDS)}",
            {"record": dict(record)},
        )
    observed_unknown_reason = _str_or_none(record.get("observed_unknown_reason"))
    if observed_at is None and not observed_unknown_reason:
        observed_unknown_reason = "connector run did not record an observation time"

    # -- Epistemic axes: only as strong as declared, never strengthened --------
    reliability = str(record.get("source_reliability") or "R3")
    if reliability not in _RELIABILITY:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"source_reliability {reliability!r} not in R1..R6",
            {"record": dict(record)},
        )
    if "source_reliability" not in record:
        defaulted["source_reliability"] = "connector_default_R3"
    directness = str(record.get("claim_directness") or "D2")
    if directness not in _DIRECTNESS:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"claim_directness {directness!r} not in D1..D6",
            {"record": dict(record)},
        )
    if "claim_directness" not in record:
        defaulted["claim_directness"] = "connector_default_D2"
    integrity = str(record.get("artifact_integrity") or "I1")
    if integrity not in _INTEGRITY:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"artifact_integrity {integrity!r} not in I1..I3",
            {"record": dict(record)},
        )
    if "artifact_integrity" not in record:
        defaulted["artifact_integrity"] = "connector_default_I1"

    polarity = str(record.get("claim_polarity") or "affirms")
    if polarity not in _POLARITIES:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"claim_polarity {polarity!r} not in {sorted(_POLARITIES)}",
            {"record": dict(record)},
        )
    rank = str(record.get("rank") or "normal")
    if rank not in _RANKS:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"rank {rank!r} not in {sorted(_RANKS)}",
            {"record": dict(record)},
        )
    review_status = str(record.get("review_status") or "unreviewed")
    if review_status not in _REVIEW_STATUSES:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"review_status {review_status!r} not in {sorted(_REVIEW_STATUSES)}",
            {"record": dict(record)},
        )

    # -- Sensitivity: never lowered, never silently raised ---------------------
    tier_raw = record.get("sensitivity_tier")
    if tier_raw is None:
        sensitivity_tier = 0
        defaulted["sensitivity_tier"] = "absent_is_public_0"
    else:
        try:
            sensitivity_tier = int(tier_raw)
        except (TypeError, ValueError):
            return Rejection(
                QuarantineReason.MISSING_REQUIRED_FIELD,
                f"sensitivity_tier must be an int 0..2, got {tier_raw!r}",
                {"record": dict(record)},
            )
        if not 0 <= sensitivity_tier <= 2:
            return Rejection(
                QuarantineReason.UNKNOWN_VALUE_KIND,
                f"sensitivity_tier {sensitivity_tier} outside 0..2",
                {"record": dict(record)},
            )

    # -- Evidence + extraction provenance --------------------------------------
    evidence_role = str(record.get("evidence_role") or "establishes")
    if evidence_role not in _EVIDENCE_ROLES:
        return Rejection(
            QuarantineReason.UNKNOWN_VALUE_KIND,
            f"evidence_role {evidence_role!r} not in {sorted(_EVIDENCE_ROLES)}",
            {"record": dict(record)},
        )
    evidence_block = record.get("evidence")
    evidence_map = evidence_block if isinstance(evidence_block, Mapping) else {}
    extraction_method = str(
        record.get("extraction_method") or evidence_map.get("extraction_method") or "deterministic"
    )
    model_id = _str_or_none(record.get("model_id") or evidence_map.get("model_id"))
    prompt_version = _str_or_none(
        record.get("prompt_version") or evidence_map.get("prompt_version")
    )
    if extraction_method == "llm_assisted" and (not model_id or not prompt_version):
        return Rejection(
            QuarantineReason.MISSING_REQUIRED_FIELD,
            "extraction_method 'llm_assisted' REQUIRES model_id and prompt_version "
            "(the extraction row's CHECK); a model identity is never fabricated",
            {"record": dict(record)},
        )
    extractor_version = _str_or_none(
        record.get("extractor_version") or evidence_map.get("extractor_version")
    )
    config_digest = _str_or_none(
        record.get("extraction_config_digest")
        or record.get("config_digest")
        or evidence_map.get("extraction_config_digest")
    )

    # -- Locator / document-only limitation ------------------------------------
    if binding is not None:
        located = locator_of(record, byte_size=binding.byte_size)
        if isinstance(located, Rejection):
            return located
        locator, located_status = located
        binding_status = BINDING_REPLAYED if replayed else located_status
        locator_row = locator.row
    else:
        binding_status = BINDING_LEGACY
        locator_row = None

    # -- Qualifiers -------------------------------------------------------------
    qualifiers: list[AssertionQualifier] = []
    for raw_q in record.get("qualifiers") or ():
        if not isinstance(raw_q, Mapping):
            return Rejection(
                QuarantineReason.UNKNOWN_QUALIFIER,
                f"qualifier must be a mapping, got {type(raw_q).__name__}",
                {"qualifier": str(raw_q)[:200]},
            )
        adapted = qualifier_of(raw_q)
        if isinstance(adapted, Rejection):
            return adapted
        qualifiers.append(adapted)

    derived = record.get("derived_from_claim_ids") or []
    rationale = _str_or_none(record.get("assertion_rationale"))
    return TypedAssertion(
        subject=subject,
        predicate=predicate,
        object_type=object_type,
        value_kind=value_kind,
        value_text=value_text,
        value_int=value_int,
        value_float=value_float,
        value_bool=value_bool,
        value_json=json.dumps(value_json, sort_keys=True, default=str) if value_json else None,
        unit=unit,
        raw_value=raw_value,
        raw_context=json.dumps(raw_context, sort_keys=True, default=str) if raw_context else None,
        normalization_id=normalization_id,
        normalization_version=normalization_version,
        valid_from=valid_from.isoformat() if valid_from else None,
        valid_to=valid_to.isoformat() if valid_to else None,
        valid_edtf=_str_or_none(record.get("valid_edtf")),
        valid_from_kind=valid_from_kind,
        valid_to_kind=valid_to_kind,
        observed_at=observed_at.isoformat() if observed_at else None,
        observed_edtf=_str_or_none(record.get("observed_edtf")),
        observed_at_kind=observed_at_kind,
        observed_unknown_reason=observed_unknown_reason,
        source_reliability=reliability,
        reliability_provisional=bool(record.get("reliability_provisional") or False),
        claim_directness=directness,
        artifact_integrity=integrity,
        legacy_source_tier=_str_or_none(record.get("legacy_source_tier")),
        claim_polarity=polarity,
        rank=rank,
        review_status=review_status,
        sensitivity_tier=sensitivity_tier,
        assertion_rationale=rationale,
        derived_from_claim_ids=[str(x) for x in derived],
        revises_claim=_str_or_none(record.get("revises_claim")),
        retraction_of=_str_or_none(record.get("retraction_of")),
        correction_reason=_str_or_none(record.get("correction_reason")),
        evidence_role=evidence_role,
        extraction_method=extraction_method,
        extractor_version=extractor_version,
        extraction_config_digest=config_digest,
        extraction_model_id=model_id,
        extraction_prompt_version=prompt_version,
        locator_row=locator_row,
        binding_status=binding_status,
        qualifiers=qualifiers,
        defaulted=defaulted,
    )


def quarantine_payload(
    record: Mapping[str, Any], *, connector_name: str, source_id: str | None = None
) -> dict[str, Any]:
    """The ``assertion_quarantine.payload`` shape — the full rejected record."""
    return {
        "schema": ASSERTION_SCHEMA_VERSION,
        "connector_name": connector_name,
        "source_id": source_id,
        "subject_ref": record.get("subject_id"),
        "predicate_id": record.get("predicate_id"),
        "record": dict(record),
    }


__all__ = [
    "ASSERTION_MAP_ID",
    "ASSERTION_SCHEMA_VERSION",
    "BINDING_ACTUAL",
    "BINDING_DOCUMENT_ONLY",
    "BINDING_LEGACY",
    "BINDING_REPLAYED",
    "CAPTURE_ACTUAL",
    "CAPTURE_LEGACY",
    "CAPTURE_SYNTHETIC",
    "AssertionQualifier",
    "CaptureBinding",
    "QuarantineReason",
    "Rejection",
    "TypedAssertion",
    "assertion_from_record",
    "binding_of",
    "locator_of",
    "qualifier_of",
    "quarantine_payload",
]

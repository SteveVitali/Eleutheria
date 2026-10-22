# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Truthful claim identity — the single claim-digest function (P35.22 / F-504).

A claim's ``content_digest`` is its identity: the ``claim_content_digest``
unique index makes it the dedup key, and a re-observation of the same fact must
re-bind to the same claim (a ``claim_evidence`` re-sighting via the P31.7
``on_duplicates`` hook), never mint a new id (SIG-INGEST-003/004). Pre-P35.22
the digest covered the whole emitted record minus ``claim_id``/``sys_period``/
``recorded_at`` — so row position, page URL, capture digest, fetch date and
upstream version counters (F-504's named volatile classes) churned identity and
an upstream row deletion or re-capture minted a second claim for an unchanged
fact, each mint falsely counting as an independent support class.

This module is the ONE identity function the emitter side and the sink side both
run (``connectors.claim_identity_ingest`` mints emitted digests from it;
``db.claim_sink.content_digest`` delegates to it). A divergence between the two
is a bug, not a tolerated difference — the dedup-parity harness compares them.

The composition is declared, not implicit:

* **Volatile / acquisition fields never enter identity.** Keys naming row
  position (``row_index``/``feature_index``/``page``/…), the page or capture URL
  (``source_url``/``page_url``), capture identity (``capture_digest``/
  ``capture_id``/``artifact_id``), fetch time (``retrieved_at``/
  ``retrieved_date``/``fetched_at``/``captured_at``) and upstream record-version
  counters (``osm_version``/``release_digest``/…) are stripped — recursively, so
  the same acquisition metadata nested in ``evidence``/``release``/
  ``provenance`` mappings leaves too. Every one of them stays recorded: the
  binding writes the capture/locator to ``claim_evidence`` and
  ``evidence_capture.retrieved_at`` — only their *identity* role ends.
  ``value_json`` is the single exception: it is the asserted payload, so the
  volatile projection never descends into it (a ``retrieved_at`` INSIDE a
  payload is content someone asserted, not our acquisition metadata).
* **The ``obs``/``ref`` split (registry-read, never guessed).** A predicate's
  temporal class comes from the predicate registry — ``is_windowed`` or an
  interval ``resolution_strategy`` (``interval_union``/``interval_intersection``,
  the SIG-RECON-011 windowed family) marks the observational ``obs`` class. An
  ``obs`` claim keeps its temporal qualifier in identity — ``valid_*`` bounds
  and the source-declared ``observed_at`` (e.g. a portal's own snapshot date)
  are what the windowed claim IS. A ``ref`` claim drops them all: a
  re-observation of the same fact under a different declared window or sighting
  date re-binds; the differing qualifier is preserved on the stored row and the
  evidence binding, it just stops minting ids.
* **`value_json` canonicalisation.** The stored form the digest consumes is
  canonicalised: mapping keys recursively sorted, strings NFC-normalised,
  integral floats within the exact-float range collapse to ints, datetimes and
  ``Decimal``s render in one canonical text form, and absent-vs-``null`` is
  unified (a ``None`` member is the same as an omitted member — both read as
  "no value" everywhere in the schema). Serialisation is compact
  ``sort_keys`` JSON, so key order, whitespace and Unicode-escape noise can
  never mint a second claim.
* **`payload_version` seals the scheme.** The digest base carries
  ``payload_version`` and the claim row's ``payload_version`` column records
  which normalisation produced it — a future change to this function is a
  declared new shape (a new version mints distinct digests by construction),
  never silent drift. Pre-versioning rows carry ``payload_version IS NULL``.
* **Binding versions are identity (SIG-INGEST-004, P35.34).** The claim's
  logical identity includes ``extractor_version`` and ``normalizer_version`` —
  the versions of the code that extracted and normalised the claim, so a
  better parser over identical input produces genuinely new claim rows
  rather than silently re-binding. The mint seals the versions the evidence
  binding records (the record's declared ``extractor_version`` else the
  connector's; the connector's ``normalizer_version``), under the canonical
  key names — a caller-supplied seal overrides a record-carried value so the
  identity names the version actually bound. Paths minting a claim with no
  extraction binding (asserted-origin corrections) pass none and the keys
  stay honestly absent. The seal lands for NEW minting only — stored digests
  are never recomputed or rewritten (``sig.claim-payload/2`` declares the
  new shape).
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

#: The declared payload-normalisation version. Written onto ``claim.payload_version``
#: and sealed into the digest base; bump on ANY change to this module's
#: canonicalisation so a new shape mints distinctly by construction.
#: ``/2`` (P35.34 / SIG-INGEST-004): the digest base gains the sealed binding
#: versions (``extractor_version`` / ``normalizer_version``) — a new shape.
PAYLOAD_VERSION = "sig.claim-payload/2"

#: The two registry predicate classes for identity. ``obs`` — the observational /
#: windowed family (SIG-RECON-011): the temporal qualifier is part of what the
#: claim is, so it stays in the digest. ``ref`` — every other predicate: a
#: reference/state assertion where the qualifier is a sighting detail.
PredicateClass = Literal["obs", "ref"]

#: The ``vocab_predicate.resolution_strategy`` values that mark a predicate as
#: observational: the interval family merges a window's observations — the
#: window IS the claim. Combined with the registry's ``is_windowed`` flag by
#: :func:`temporal_class`. Read from the registry (``vocab_predicate`` sink-side,
#: ``ontology/vocab/predicates.yaml`` emitter-side), never inferred.
OBSERVATION_STRATEGIES = frozenset({"interval_union", "interval_intersection"})


def temporal_class(
    *, resolution_strategy: str | None = None, is_windowed: bool | None = None
) -> PredicateClass:
    """The predicate's identity class, from its REGISTRY row — never guessed.

    ``obs`` iff the registry marks the predicate windowed (``is_windowed``) or
    resolves by an interval strategy (the observational family). Anything else —
    including an absent registry row — is ``ref`` (conservative: keep the
    qualifier only when the registry says it is identity; an unregistered
    predicate never reaches minting anyway, it quarantines upstream).
    """
    if is_windowed or (resolution_strategy or "") in OBSERVATION_STRATEGIES:
        return "obs"
    return "ref"


#: Generated/transaction columns and envelope fields — never identity (the
#: pre-P35.22 exclusion plus the record envelope: ``record_kind`` routes the
#: record, it is not part of what the claim asserts — a claim record emitted
#: with ``record_kind: "claim"`` and the same record emitted bare are ONE claim;
#: non-claim records never reach minting anyway).
_SYSTEM_KEYS = frozenset(
    {
        "claim_id",
        "sys_period",
        "recorded_at",
        "content_digest",
        "record_kind",
        "assertion_schema_version",
        "payload_version",
    }
)

#: Capture/fetch time — SIG's acquisition clock, never claim identity. The
#: source-DECLARED observation time (``observed_*``) is NOT here: it is a
#: temporal qualifier, class-conditional (kept for ``obs``, dropped for ``ref``).
_CAPTURE_TIME_KEYS = frozenset(
    {
        "retrieved_at",
        "retrieved_date",
        "fetched_at",
        "captured_at",
        "fetch_date",
        "capture_date",
        "capture_time",
        "bound_at",
    }
)

#: Capture/binding identity and locator keys — the evidence binding's job.
_ACQUISITION_KEYS = frozenset(
    {
        "capture_digest",
        "capture_id",
        "evidence_capture_id",
        "evidence_id",
        "artifact_id",
        "blob_digest",
        "byte_size",
        "ocfl_object_id",
        "ocfl_version",
        "locator",
        "source_url",
        "source_uri",
        "page_url",
        "capture_url",
        "data_file_urls",
        "run_id",
        "original_run_id",
        "ingest_run_id",
        "extraction_id",
        "assertion_map_id",
        "assertion_map_basis",
    }
)

#: Row position and upstream record/version counters (F-504's named classes).
_POSITION_AND_VERSION_KEYS = frozenset(
    {
        "row_index",
        "feature_index",
        "page_index",
        "page",
        "record_index",
        "result_index",
        "position",
        "osm_version",
        "upstream_version",
        "element_version",
        "source_version",
        "release_id",
        "release_version",
        "release_digest",
    }
)

#: Temporal-qualifier keys — the observation's declared time. In identity for
#: ``obs`` predicates only; a ``ref`` re-observation under another window or
#: sighting date re-binds (the stored row + binding still record them).
_TEMPORAL_QUALIFIER_KEYS = frozenset(
    {
        "valid_from",
        "valid_to",
        "valid_edtf",
        "valid_from_kind",
        "valid_to_kind",
        "valid_period",
        "observed_at",
        "observed_edtf",
        "observed_at_kind",
        "observed_unknown_reason",
    }
)

#: Keys never in identity for ANY class — applied recursively at every level of
#: the record EXCEPT inside ``value_json`` (the asserted payload is opaque).
NEVER_IDENTITY_KEYS = frozenset(
    _SYSTEM_KEYS | _CAPTURE_TIME_KEYS | _ACQUISITION_KEYS | _POSITION_AND_VERSION_KEYS
)

#: ``derived_from_claim_ids`` and ``qualifiers`` are order-insensitive
#: collections — their canonical form is sorted, so a reserialised record never
#: digests differently.
_ORDER_INSENSITIVE_KEYS = frozenset({"derived_from_claim_ids"})


def _canonical_scalar(value: Any) -> Any:
    """The canonical form of a scalar for digesting and storing.

    Strings NFC-normalise; integral floats inside the exact-double range
    collapse to ints (``30.0`` and ``30`` are the same number); datetimes render
    ISO (``str()``'s space separator and ``isoformat()``'s ``T`` must not
    diverge); ``Decimal`` renders its shortest exact form; anything else falls
    back to ``str`` — the pre-existing ``default=str`` behaviour.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() and abs(value) < 2**53 else value
    if isinstance(value, Decimal):
        # 30.0 -> "30"; 30.50 -> "30.5" — one canonical exact text form.
        normalized = value.normalize()
        return format(normalized, "f")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if value is None:
        return None
    return str(value)


def canonicalize(value: Any) -> Any:
    """The canonical JSON form: mappings sorted, scalars normalised, list order kept."""
    if isinstance(value, Mapping):
        return {
            str(k): canonicalize(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
            if v is not None
        }
    if isinstance(value, (list, tuple)):
        return [canonicalize(v) for v in value]
    return _canonical_scalar(value)


def _project(value: Any, *, temporal_class_: PredicateClass) -> Any:
    """Strip volatile keys recursively; a mapping that loses every member drops."""
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for key, val in sorted(value.items(), key=lambda item: str(item[0])):
            if val is None or str(key) in NEVER_IDENTITY_KEYS:
                continue
            if temporal_class_ == "ref" and str(key) in _TEMPORAL_QUALIFIER_KEYS:
                continue
            projected = _project(val, temporal_class_=temporal_class_)
            if projected == {}:
                # A nested mapping that projected to nothing (all-volatile
                # acquisition metadata) is identical to an absent key.
                continue
            out[str(key)] = projected
        return out
    if isinstance(value, (list, tuple)):
        return [_project(v, temporal_class_=temporal_class_) for v in value if v is not None]
    return _canonical_scalar(value)


def _canonical_value_json(value: Any) -> Any:
    """Canonicalise the asserted payload — a dict OR its serialised text form.

    The emitter-side record carries ``value_json`` as a Python object; a stored
    row read back (replay/dedup-parity comparisons) may carry the serialised
    string. Both canonicalise to the same base, so the two never digest
    differently.
    """
    if isinstance(value, str):
        try:
            return canonicalize(json.loads(value))
        except (json.JSONDecodeError, TypeError, ValueError):
            return _canonical_scalar(value)
    return canonicalize(value)


def canonical_qualifiers(qualifiers: Any, *, temporal_class: PredicateClass) -> list[Any]:
    """The canonical qualifier set — per-qualifier volatile projection, then
    sorted by canonical form so list order is never identity."""
    if not qualifiers:
        return []
    projected = [
        p
        for p in (_project(q, temporal_class_=temporal_class) for q in qualifiers)
        if p not in (None, {})
    ]
    return sorted(
        projected,
        key=lambda q: json.dumps(q, sort_keys=True, ensure_ascii=False, default=str),
    )


def digest_base(
    record: Mapping[str, Any],
    *,
    temporal_class: PredicateClass,
    extractor_version: str | None = None,
    normalizer_version: str | None = None,
) -> dict[str, Any]:
    """The identity projection of one claim record — what the digest covers.

    Volatile acquisition keys are dropped at every level, the temporal
    qualifier is class-conditional, ``value_json`` is canonicalised as opaque
    asserted content, and ``payload_version`` seals the scheme.

    ``extractor_version`` / ``normalizer_version`` (P35.34 / SIG-INGEST-004)
    seal the binding versions into identity under their canonical key names —
    a supplied seal overrides a record-carried value so the base names the
    version actually bound, and ``None`` leaves whatever the record carries
    (a record without the keys mints unsealed — asserted-origin mints).
    """
    base: dict[str, Any] = {}
    for key, value in sorted(record.items(), key=lambda item: str(item[0])):
        if value is None or str(key) in NEVER_IDENTITY_KEYS:
            continue
        if temporal_class == "ref" and str(key) in _TEMPORAL_QUALIFIER_KEYS:
            continue
        if str(key) == "value_json":
            base["value_json"] = _canonical_value_json(value)
        elif str(key) == "qualifiers":
            base["qualifiers"] = canonical_qualifiers(value, temporal_class=temporal_class)
        elif str(key) in _ORDER_INSENSITIVE_KEYS and isinstance(value, (list, tuple)):
            base[str(key)] = sorted(
                (canonicalize(v) for v in value if v is not None),
                key=lambda v: json.dumps(v, sort_keys=True, ensure_ascii=False, default=str),
            )
        else:
            projected = _project(value, temporal_class_=temporal_class)
            if projected == {}:
                # Same as _project: an all-volatile sub-mapping is an absent key.
                continue
            base[str(key)] = projected
    if extractor_version is not None:
        base["extractor_version"] = _canonical_scalar(extractor_version)
    if normalizer_version is not None:
        base["normalizer_version"] = _canonical_scalar(normalizer_version)
    base["payload_version"] = PAYLOAD_VERSION
    return base


def claim_digest(
    record: Mapping[str, Any],
    *,
    temporal_class: PredicateClass = "ref",
    extractor_version: str | None = None,
    normalizer_version: str | None = None,
) -> str:
    """The sha256 over a claim record's identity — the ``content_digest``.

    ``temporal_class`` is the predicate's registry class (``obs`` keeps the
    temporal qualifier in identity; ``ref`` drops it). Callers that never
    resolve the registry get ``ref`` — identical for any record that carries no
    temporal qualifier, and the conservative merge direction for one that does.

    ``extractor_version`` / ``normalizer_version`` (SIG-INGEST-004) seal the
    binding versions into identity — the sink passes the versions its
    extraction/evidence-binding writes; a caller with none to bind leaves
    them out.
    """
    payload = json.dumps(
        digest_base(
            record,
            temporal_class=temporal_class,
            extractor_version=extractor_version,
            normalizer_version=normalizer_version,
        ),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def canonical_json(value: Any) -> str:
    """The canonical text form of a JSON value — the stored ``value_json`` shape."""
    return json.dumps(
        canonicalize(value),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        default=str,
    )


__all__ = [
    "NEVER_IDENTITY_KEYS",
    "OBSERVATION_STRATEGIES",
    "PAYLOAD_VERSION",
    "PredicateClass",
    "canonical_json",
    "canonicalize",
    "claim_digest",
    "digest_base",
    "temporal_class",
]

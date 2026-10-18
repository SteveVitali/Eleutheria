# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Compute-on-read export data-shaping over the claim spine (P27.3, LAUNCH.3).

The P27.1 audit measured the gap: ~1.06M claims carry coordinates as **text** under
``camera_latitude``/``camera_longitude`` while ``value_geom`` and the modeling tables
(``resolution``/``jurisdiction``/``coverage_record``/``physical_asset``) are empty.
This module is the layer that turns those raw claims into the shaped datasets the
public surfaces (P27.4) consume — point geometry, per-jurisdiction grouping,
observation-level dedup framing, and coverage aggregates — **computed at export
build time**, never materialized back into the spine.

Posture (ADR-092, operator-ratified): **compute-on-read + honest observation-level
framing.** ``reconcile.RESOLVE`` cannot decide ``camera_*`` predicates — they are
connector-registered, not ontology-registered, so the §29 resolver raises
``KeyError`` on them. Instead of fabricating a resolved census, shaping computes a
lightweight *observation envelope* per ``(subject, predicate)``: one distinct
normalized value → ``resolved``; several → ``conflicted`` with **every** candidate
value and claim id retained (contradictions stay visible, §3.1); none →
``unreported``. A site is then framed as "N observations across M sources" — the
observation-level count a public surface may honestly show (SIG-RECON-058), never
a device census.

Design constraints (the invariants this module never relaxes):

* **Read-only (append-only spine, §16).** Every statement is a ``SELECT``;
  :func:`run_shaping` puts the session in read-only mode. Nothing is written —
  no ``value_geom``, no ``resolution`` row, no ``jurisdiction`` row.
* **The normalization path, never a hand-edit.** Coordinates are normalized per
  the §24 contract (:class:`parsing.claim.ParsedValue` — raw literal preserved,
  typed value preferred, parse failure kept as data). Unparseable or missing
  coordinates are **gaps, not guesses**.
* **Sensitivity reduction (§19.4/§43.3).** Every emitted point passes through
  :func:`policy.sensitivity.apply_tier` at the site's claim tier — today all
  claims are tier-0 (full precision), but the mechanism is the only path a
  coordinate ever takes.
* **Publishable scope only (P27.2/ADR-095).** A claim shapes the public dataset
  iff its *effective* rights (the latest ``rights_decision`` over the recorded
  record) are ``redistributable='yes'`` and it sits at the public sensitivity
  tier. Excluded claims are counted honestly, never dropped silently.
* **Licence posture per site (§42).** A site carries every distinct effective
  rights record behind its claims (``rights``) plus the sorted SPDX set
  (``licenses``) — everything P27.4 needs to place each row through the real
  gate (:func:`policy.licensing.compute_export_license` +
  :func:`exports.compartments.compartment_for_license`) at table granularity.
  A mix the gate itself refuses is flagged ``licence_conflict`` so P27.4 splits
  the row per compartment — never a silent merge.
* **Never a bare total (§32 / SIG-METRIC-003/008/010).** Every published count is
  a :class:`inference.denominators.PublishedAggregate` with a named denominator
  and a not-evaluable count; the web-contract metrics carry
  ``is_population_total: false``. No capture–recapture, no population estimate.
* **Deterministic.** SQL orders every result; the assembler re-sorts. Two runs
  over the same spine state differ only in ``generated_at``.

The pure assembler :func:`build_shaped_dataset` builds a :class:`ShapedDataset`
from already-fetched rows (unit-tested with no database); :func:`run_shaping` is
the thin executor that fetches those rows from a live connection.
"""

from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping, Sequence, Set
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Protocol

from db.dispositions import claim_eligible_sql, entity_eligible_sql
from db.occurrences import (
    BELIEF_NOW,
    BELIEF_PARAM,
    claim_source_cte,
    lineage_candidates,
)
from db.occurrences import (
    spine_watermark as _spine_watermark_read,
)
from inference.denominators import PublishedAggregate, provenance_completeness
from inference.freshness import SourceFreshness, source_freshness
from parsing.claim import ParsedValue
from policy.licensing import (
    ExportGateClosed,
    LicenseIncompatibilityError,
    RightsRecord,
    compute_export_license,
)
from policy.sensitivity import apply_tier, assert_public_layer_subject
from policy.source_aliases import load_source_aliases
from reconcile.weight import predicate_meta
from resolution.partner_identity import PARTNER_PREDICATES

from .audit import _LATEST_DECISION_CTE, GEO_PREDICATES, JURISDICTION_PREDICATE
from .jurisdictions import (
    CONNECTOR_DATA_DIR,
    DECLARED_SCHEME_FROM_CLAIM,
    JurisdictionSchemeConfig,
    jurisdiction_key,
    load_jurisdiction_scheme_config,
)

#: The shaped-dataset output schema version — bumped when the emitted shape changes.
#: p35.18/1.2.0 — JUR-02a: jurisdiction buckets key on the declared
#: ``(scheme, value)`` (canonical key, never a bare code); envelope
#: observations carry ``scheme``/``scheme_basis`` provenance.
SHAPING_SCHEMA_VERSION = "p35.18/1.2.0"

LAT_PREDICATE = GEO_PREDICATES[0]  # camera_latitude
LON_PREDICATE = GEO_PREDICATES[1]  # camera_longitude

#: The label predicate — a deployment's display name when a source provides one.
LABEL_PREDICATE = "camera_name"

#: P35.15a / PKG-07: the declared SKOS technology slug (a `technology` claim —
#: multi-cardinality, so a subject CAN assert several; the envelope keeps that
#: contradiction visible and the resolved value stays ``None`` when disputed).
TECHNOLOGY_PREDICATE = "technology"

#: The claim predicates the shaping layer reads to assemble sites. Anything else a
#: subject carries (camera_operator, external refs, …) is evidence for P27.4
#: dossiers but not needed to shape geometry/jurisdiction/coverage.
SHAPING_PREDICATES = (
    LAT_PREDICATE,
    LON_PREDICATE,
    JURISDICTION_PREDICATE,
    LABEL_PREDICATE,
    TECHNOLOGY_PREDICATE,
)

#: The literal value a source asserts when it cannot name a jurisdiction — an
#: honest first-class bucket, never dropped (P27.3 deliverable 2).
UNRESOLVED_JURISDICTION = "unresolved"

#: Buckets the shaping itself assigns when no honest jurisdiction label exists.
UNASSERTED_JURISDICTION = "(unasserted)"
CONFLICTED_JURISDICTION = "(conflicted)"

EnvelopeStatus = Literal["resolved", "conflicted", "unreported"]

#: Observation-envelope statuses (§29-shaped, observation-level — ADR-092).
ENVELOPE_RESOLVED: EnvelopeStatus = "resolved"  # one distinct normalized value
ENVELOPE_CONFLICTED: EnvelopeStatus = "conflicted"  # several — contradiction visible
ENVELOPE_UNREPORTED: EnvelopeStatus = "unreported"  # no claims (a gap, not a guess)

#: How a site's point ended up — the honest geometry state.
PointStatus = Literal["resolved", "conflicted", "unreported"]

#: The three access kinds a sharing edge may carry (§29.3, SIG-MON-012); edges a
#: predicate name cannot justify are emitted flagged ``unclassified``, never
#: coerced into a kind they did not declare.
ACCESS_KINDS = ("configured_access", "observed_use", "declared_policy", "unclassified")


class _Cursor(Protocol):
    """The minimal cursor surface :func:`run_shaping` uses (psycopg-compatible)."""

    def execute(self, query: str, params: Sequence[Any] | None = ...) -> Any: ...
    def fetchone(self) -> Any: ...
    def fetchall(self) -> list[Any]: ...


class _Connection(Protocol):
    def cursor(self) -> _Cursor: ...
    def execute(self, query: str, params: Sequence[Any] | None = ...) -> Any: ...


# --------------------------------------------------------------------------- #
# Records                                                                      #
# --------------------------------------------------------------------------- #


#: The explicit honest-absence token a freshness field carries when the spine records no
#: value (web ``metrics.ts#NOT_RECORDED``; SIG-METRIC-007 still SHOWS the field, as "not
#: recorded", rather than dropping it or guessing a date — §3.1).
NOT_RECORDED = "not-recorded"

#: The explicit honest-absence token a freshness row carries when staleness is
#: NOT evaluable for the source (P35.20b / ED-43 / GQ-15): no declared §28.3
#: volatility class, or no evaluable dated observation. The surface reads
#: "not evaluable" — never "ok", never a fabricated stale-0 (§3.1).
NOT_EVALUABLE = "not_evaluable"

#: The closed §28.3 volatility vocabulary a source may declare (P35.20b) —
#: mirrors ``connectors.registry.VOLATILITY_CLASSES`` / the ontology's
#: ``PredicateVolatility``; ``connectors`` is not an exports dependency, so the
#: tuple is duplicated here and a test pins the two equal.
DECLARED_VOLATILITY_CLASSES: tuple[str, ...] = (
    "IMMUTABLE",
    "GLACIAL",
    "SLOW",
    "MODERATE",
    "FAST",
    "VOLATILE",
)


@lru_cache(maxsize=4)
def _declared_volatility_classes_cached(data_dir: str) -> dict[str, str]:
    """Read the declared per-source volatility classes out of ``sources.toml``.

    Fail-closed: a row declaring a class outside the §28.3 vocabulary, or a
    class with no recorded basis, raises — the same validation
    ``connectors.registry.SourceRecord`` runs (P35.20b). A source with no
    declaration is simply absent from the map: undeclared, not guessed.
    """
    path = Path(data_dir) / "sources.toml"
    if not path.exists():
        return {}
    doc = tomllib.loads(path.read_bytes().decode("utf-8"))
    out: dict[str, str] = {}
    for source_id, row in (doc.get("sources") or {}).items():
        if not isinstance(row, Mapping):
            continue
        declared = row.get("volatility_class")
        if declared is None:
            continue
        cls = str(declared).strip()
        if cls not in DECLARED_VOLATILITY_CLASSES:
            raise ValueError(
                f"source {source_id!r} declares volatility_class {cls!r} — not a "
                f"§28.3 class ({', '.join(DECLARED_VOLATILITY_CLASSES)})"
            )
        if not str(row.get("volatility_basis", "")).strip():
            raise ValueError(
                f"source {source_id!r} declares volatility_class {cls!r} with no "
                "volatility_basis — a class is a claim and names its evidence"
            )
        out[str(source_id)] = cls
    return out


def declared_volatility_classes(data_dir: Path | str | None = None) -> dict[str, str]:
    """The committed ``sources.toml`` per-source declared volatility classes."""
    root = Path(data_dir) if data_dir is not None else CONNECTOR_DATA_DIR
    return dict(_declared_volatility_classes_cached(str(root)))


@dataclass(frozen=True)
class ShapingClaim:
    """One spine claim row plus its *effective* rights — the shaping input record.

    ``effective_*`` is the licence posture the claim carries today: the latest
    ``rights_decision`` over its recorded ``rights_id`` when one exists, else the
    recorded record (P27.2/ADR-095). ``publishable`` is the public-dataset test.
    """

    claim_id: str
    subject_id: str
    predicate_id: str
    value_kind: str
    value_text: str | None
    value_num: float | None
    raw_value: str
    observed_at: date | None
    sensitivity_tier: int
    source_id: str | None
    connector_name: str | None
    effective_rights_id: str
    effective_spdx: str
    effective_redistributable: str
    effective_derivative_permitted: str
    effective_attribution: str
    effective_terms_url: str
    #: P32.4 (ADR-123): the claim's selected latest *eligible* establishing
    #: occurrence — the sighting the shared contract picked (refs preserved).
    occurrence_capture_id: str | None = None
    occurrence_retrieved_at: datetime | None = None
    occurrence_bound_at: datetime | None = None
    #: The exact ordering instant under the shared contract: the claim's own
    #: ``observed_at`` when dated, else the occurrence's ``retrieved_at`` — what
    #: per-lineage candidate selection orders by (a claim id is never a clock).
    observed_instant: datetime | None = None
    #: The contract's dating basis: ``"claim"`` (self-dated),
    #: ``"capture_retrieved_at_latest"`` (capture-dated fallback — labelled, an
    #: inference not an asserted date) or ``"undated"``.
    observed_basis: str = "undated"
    #: P32.5 (ADR-124, SIG-TRUST-006): the shared eligibility selector, evaluated
    #: in the SAME query — a claim under a current deny disposition, or whose
    #: subject or referenced entity is withheld, is not publishable (and is
    #: honestly counted in ``claims_excluded_not_publishable``).
    publication_permitted: bool = True
    #: P34.21b (E2-12 / ADR-194): when the effective rights resolve through a
    #: recorded ``rights_decision``, its ``decided_at`` + ``basis`` — the
    #: export names the attribution corrections it carries from the basis
    #: marker. ``None`` when the recorded rights stand (no decision).
    effective_decision_decided_at: datetime | None = None
    effective_decision_basis: str | None = None
    #: P35.18 / JUR-02a (K4 §3.2): the claim's stored ``value_json`` blob —
    # ``jsonb::text`` verbatim. New claims carry the declared
    # ``candidate_identifier`` ``{scheme, value}`` pair here; pre-P35.18
    # claims carry none and shape through the config-declared scheme instead.
    value_json: str | None = None
    #: P35.25 (SIG-CONF-014): the claim's resolved independence class from
    #: ``claim_lineage`` — ``None`` when the spine predates the lineage record
    #: or the claim has no row (both read as undeclared, never independent).
    independence_class: str | None = None

    @property
    def publishable(self) -> bool:
        """Whether this claim may shape the public dataset (P27.2 + P32.5)."""
        return (
            self.effective_redistributable == "yes"
            and self.sensitivity_tier == 0
            and self.publication_permitted
        )

    def rights_record(self) -> RightsRecord:
        """The effective rights as a :class:`RightsRecord` for the licence gate."""
        return RightsRecord(
            source_id=self.source_id or "(unattributed)",
            spdx=self.effective_spdx,
            attribution=self.effective_attribution,
            redistributable=self.effective_redistributable == "yes",
            derivative_permitted=self.effective_derivative_permitted == "yes",
            terms_url=self.effective_terms_url,
            retrieval_date=date(1970, 1, 1),  # provenance lives on the rights row
        )


@dataclass(frozen=True)
class ValueObservation:
    """One claim's observed value inside an envelope — the dedup-visible unit."""

    claim_id: str
    source_id: str
    raw_value: str
    display_value: str  # the normalized, comparable form
    observed_at: str | None
    #: P32.4 (ADR-123): how this observation was dated under the shared contract
    #: — ``"claim"`` (its own observed_at), ``"capture_retrieved_at_latest"``
    #: (the undated fallback basis, labelled) or ``"undated"``.
    observed_basis: str = "claim"
    #: The occurrence reference of the claim's latest eligible establishing
    #: capture (evidence ref preserved in output), when one exists.
    capture_id: str | None = None
    #: P35.18 (JUR-02a): the identifier scheme the observation's display value
    #: was keyed under, when one was declared — ``None`` = the claim kept its
    #: bare asserted value (undeclared, honest).
    scheme: str | None = None
    #: P35.18 (JUR-02a): where ``scheme`` came from — ``candidate_identifier``
    #: (the claim's own persisted pair) or ``declared_scheme_from_config@<sha256>``
    #: (the labelled config derivation for a legacy claim).
    scheme_basis: str | None = None


@dataclass(frozen=True)
class ObservationEnvelope:
    """The §29-shaped, observation-level envelope over one (subject, predicate).

    Not a materialized ``resolution`` row — computed on read (ADR-092). A
    ``conflicted`` envelope keeps every candidate: ``supporting_claim_ids`` back
    the modal value, ``dissenting_claim_ids`` the rest, and ``observations``
    carries every raw value verbatim. Nothing is silently reconciled.
    """

    predicate_id: str
    status: EnvelopeStatus
    value: str | None  # the single agreed display value (resolved only)
    value_is_parseable: bool  # resolved value came from a real parse (not a gap)
    n_observations: int
    n_sources: int
    #: P35.25 (SIG-CONF-014): the DISTINCT declared independence classes among
    #: the candidate claims — the truthful corroboration count. ``n_sources``
    #: counts sources (a mirror inflates it); this never counts an
    #: ``unclassified`` claim as a class, and unclassified candidates are
    #: disclosed by ``n_unclassified_candidates`` rather than read as
    #: independent voices. 0/0 on a pre-P35.25 spine.
    n_independence_classes: int = 0
    n_unclassified_candidates: int = 0
    considered_claim_ids: tuple[str, ...] = ()
    supporting_claim_ids: tuple[str, ...] = ()
    dissenting_claim_ids: tuple[str, ...] = ()
    distinct_values: tuple[str, ...] = ()
    observations: tuple[ValueObservation, ...] = ()

    def as_json(self) -> dict[str, Any]:
        return {
            "predicate_id": self.predicate_id,
            "status": self.status,
            "value": self.value,
            "value_is_parseable": self.value_is_parseable,
            "n_observations": self.n_observations,
            "n_sources": self.n_sources,
            # P35.25: declared-voice accounting — the corroboration truth
            # ``n_sources`` never carries.
            "n_independence_classes": self.n_independence_classes,
            "n_unclassified_candidates": self.n_unclassified_candidates,
            "considered_claim_ids": list(self.considered_claim_ids),
            "supporting_claim_ids": list(self.supporting_claim_ids),
            "dissenting_claim_ids": list(self.dissenting_claim_ids),
            "distinct_values": list(self.distinct_values),
            "observations": [
                {
                    "claim_id": o.claim_id,
                    "source_id": o.source_id,
                    "raw_value": o.raw_value,
                    "display_value": o.display_value,
                    "observed_at": o.observed_at,
                    "observed_basis": o.observed_basis,
                    "capture_id": o.capture_id,
                    # P35.18 (JUR-02a): the declared identifier scheme behind a
                    # keyed value, and the provenance label naming where the
                    # scheme came from (the claim's pair or the config sha).
                    "scheme": o.scheme,
                    "scheme_basis": o.scheme_basis,
                }
                for o in self.observations
            ],
        }


@dataclass(frozen=True)
class ShapedSite:
    """One geolocated-observation site — the GeoJSON-ready row P27.4 consumes.

    ``observation_level`` is always ``"observation"``: the record is "N
    observations across M sources", never a resolved census (SIG-RECON-058).
    ``latitude``/``longitude`` are the tier-reduced point when both coordinate
    envelopes resolved; ``None`` otherwise — a conflicted site keeps its
    candidate values inside the envelopes and emits a null geometry rather than
    a picked point.
    """

    entity_id: str
    entity_type: str
    observation_level: str  # always "observation" (ADR-092)
    label: str | None
    #: P35.15a / PKG-07: the subject's declared SKOS technology slug when one
    #: resolved (``None`` when unreported or conflicted — the envelope keeps the
    #: disagreement visible); ``technology_status`` is the envelope status.
    technology: str | None
    technology_status: EnvelopeStatus
    jurisdiction: str
    jurisdiction_status: EnvelopeStatus
    latitude: float | None
    longitude: float | None
    point_status: PointStatus
    # Whether the subject carries coordinate claims at all — the geolocation
    # evidence flag. A subject with none is a coverage denominator member, not
    # a "geolocated site"; one with only unparseable coordinates has evidence
    # but no honest point (a gap, not a guess).
    has_coordinate_claims: bool
    sensitivity_tier: int
    precision: str
    source_ids: tuple[str, ...]
    n_observation_claims: int
    n_sources: int
    licenses: tuple[str, ...]  # distinct effective SPDX ids across the site's claims
    # The per-(source, rights-record) effective rights the site's claims carry —
    # everything P27.4 needs to place the row through the real licence gate
    # (compute_export_license + compartment_for_license over the table's rights).
    rights: tuple[dict[str, Any], ...]
    # True when the site's OWN licence mix is mutually incompatible per
    # compute_export_license — such a site cannot ship as one single-licence
    # row; P27.4 splits it per compartment (never a silent merge).
    licence_conflict: bool
    conflicted_predicates: tuple[str, ...]
    claim_ids: tuple[str, ...]
    observation_group: str | None  # exact-coordinate key shared across sources
    lat_envelope: ObservationEnvelope
    lon_envelope: ObservationEnvelope
    jurisdiction_envelope: ObservationEnvelope
    technology_envelope: ObservationEnvelope

    def geojson_feature(self) -> dict[str, Any]:
        """The GeoJSON Feature: Point when resolved, null geometry otherwise."""
        geometry = None
        if self.latitude is not None and self.longitude is not None:
            geometry = {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            }
        return {
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "entity_id": self.entity_id,
                "entity_type": self.entity_type,
                "observation_level": self.observation_level,
                "label": self.label,
                "technology": self.technology,
                "technology_status": self.technology_status,
                "jurisdiction": self.jurisdiction,
                "jurisdiction_status": self.jurisdiction_status,
                "point_status": self.point_status,
                "has_coordinate_claims": self.has_coordinate_claims,
                "sensitivity_tier": self.sensitivity_tier,
                "precision": self.precision,
                "source_ids": list(self.source_ids),
                "n_observation_claims": self.n_observation_claims,
                "n_sources": self.n_sources,
                "licenses": list(self.licenses),
                "licence_conflict": self.licence_conflict,
                "conflicted_predicates": list(self.conflicted_predicates),
                "claim_ids": list(self.claim_ids),
                "observation_group": self.observation_group,
            },
        }

    def as_json(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "observation_level": self.observation_level,
            "label": self.label,
            "technology": self.technology,
            "technology_status": self.technology_status,
            "jurisdiction": self.jurisdiction,
            "jurisdiction_status": self.jurisdiction_status,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "point_status": self.point_status,
            "has_coordinate_claims": self.has_coordinate_claims,
            "sensitivity_tier": self.sensitivity_tier,
            "precision": self.precision,
            "source_ids": list(self.source_ids),
            "n_observation_claims": self.n_observation_claims,
            "n_sources": self.n_sources,
            "licenses": list(self.licenses),
            "rights": [dict(r) for r in self.rights],
            "licence_conflict": self.licence_conflict,
            "conflicted_predicates": list(self.conflicted_predicates),
            "claim_ids": list(self.claim_ids),
            "observation_group": self.observation_group,
            "envelopes": {
                LAT_PREDICATE: self.lat_envelope.as_json(),
                LON_PREDICATE: self.lon_envelope.as_json(),
                JURISDICTION_PREDICATE: self.jurisdiction_envelope.as_json(),
                TECHNOLOGY_PREDICATE: self.technology_envelope.as_json(),
            },
        }


@dataclass(frozen=True)
class JurisdictionGroup:
    """One queryable jurisdiction bucket — incl. the honest ``unresolved`` one."""

    jurisdiction: str
    subjects: int  # the evaluable denominator: subjects asserting this bucket
    sites: PublishedAggregate  # geolocated of subjects (named denominator)
    conflicted_subjects: int  # have coordinate evidence that disagrees
    source_ids: tuple[str, ...]
    is_unresolved: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "jurisdiction": self.jurisdiction,
            "subjects": self.subjects,
            "sites": self.sites.as_json(),
            "conflicted_subjects": self.conflicted_subjects,
            "source_ids": list(self.source_ids),
            "is_unresolved": self.is_unresolved,
        }


@dataclass(frozen=True)
class SharingEdge:
    """One observed sharing edge (§29.3) — subject → partner, access-kind tagged."""

    subject_id: str
    predicate_id: str
    partner_ref: str | None
    access_kind: str  # one of ACCESS_KINDS
    source_id: str | None
    claim_id: str
    observed_at: str | None

    def as_json(self) -> dict[str, Any]:
        return {
            "subject_id": self.subject_id,
            "predicate_id": self.predicate_id,
            "partner_ref": self.partner_ref,
            "access_kind": self.access_kind,
            "source_id": self.source_id,
            "claim_id": self.claim_id,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True)
class ShapedSourceFreshness:
    """``SourceFreshness`` plus the declared-class staleness gate (P35.20b).

    ``volatility_class`` is the source's DECLARED §28.3 class from the registry
    (``sources.toml``), or :data:`NOT_EVALUABLE` when undeclared — never a
    class voted up from the claim mix (that was a guess, ED-43).
    ``staleness_not_evaluable`` counts the dated observations staleness was
    never evaluated for — every observation when no class is declared, else
    the unregistered-predicate share.
    """

    freshness: SourceFreshness
    staleness_not_evaluable: int  # dated observations never evaluated
    volatility_class: str  # the declared class, or NOT_EVALUABLE
    claims: int

    def freshness_row(self) -> dict[str, Any]:
        """The ``web/src/lib/metrics.ts`` ``FreshnessRow`` contract (SIG-METRIC-007).

        P35.20b (ED-43, GQ-15): when staleness cannot be evaluated — no
        declared volatility class, or no evaluable dated observation — the
        row's ``status`` and ``volatility_class`` read ``not_evaluable`` and
        the not-evaluable observation count is emitted. A non-evaluable row
        NEVER reads ``ok`` or ``stale 0``.
        """
        evaluable = self.freshness.staleness_evaluable
        return {
            "source": self.freshness.source_id,
            # A value the spine does not record is published as the explicit honest-absence
            # token (P30.3) — never an empty string (a DROPPED field, which the web refuses)
            # and never a guessed date (§3.1). Since P31.2 (ADR-109) the dates come from the
            # appended ingest_run_completion rows; a source with no completed (or no
            # claim-inserting) execution keeps the token.
            "last_successful_run": (
                self.freshness.last_successful_run.isoformat()
                if self.freshness.last_successful_run
                else NOT_RECORDED
            ),
            "last_content_change": (
                self.freshness.last_content_change.isoformat()
                if self.freshness.last_content_change
                else NOT_RECORDED
            ),
            "status": self.freshness.status if evaluable else NOT_EVALUABLE,
            "stale_entity_count": self.freshness.stale_count,
            "staleness_not_evaluable": self.staleness_not_evaluable,
            "volatility_class": self.volatility_class,
        }

    def as_json(self) -> dict[str, Any]:
        return {
            **self.freshness.as_json(),
            "staleness_not_evaluable": self.staleness_not_evaluable,
            "volatility_class": self.volatility_class,
            "claims": self.claims,
        }


@dataclass(frozen=True)
class ShapedDataset:
    """The complete compute-on-read shaped dataset P27.4 emits from (LAUNCH.3)."""

    as_of: str
    generated_at: str
    spine_label: str
    note: str
    schema_version: str
    spine_watermark: str

    sites: tuple[ShapedSite, ...]
    jurisdictions: tuple[JurisdictionGroup, ...]
    sources: tuple[ShapedSourceFreshness, ...]
    sharing_edges: tuple[SharingEdge, ...]
    aggregates: tuple[PublishedAggregate, ...]
    coverage_metrics: tuple[dict[str, Any], ...]  # web CoverageMetric contract

    # Honest exclusions — counted, never silently dropped.
    claims_read: int
    claims_shaped: int
    claims_excluded_not_publishable: int
    #: P35.66 (SIG-PUB-011/013): subjects refused outright — candidate assets
    #: and residential-parcel-flagged subjects never reach a public device
    #: layer, so they are counted here, not in ``subjects_total``.
    candidate_subjects_excluded: int
    subjects_total: int  # subjects carrying ≥1 publishable shaping claim
    subjects_geolocated: int  # with a resolved point
    subjects_conflicted: int  # coordinate evidence disagrees
    observation_groups_multi_source: int  # coordinate cells seen by ≥2 sources
    provenance: dict[str, Any]  # provenance_completeness over shaped claims

    def to_geojson(self) -> dict[str, Any]:
        """A FeatureCollection — null geometries for unreported/conflicted sites."""
        return {
            "type": "FeatureCollection",
            "sig:schema_version": self.schema_version,
            "sig:as_of": self.as_of,
            "sig:spine_label": self.spine_label,
            "sig:note": self.note,
            "features": [s.geojson_feature() for s in self.sites],
        }

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "as_of": self.as_of,
            "generated_at": self.generated_at,
            "spine_label": self.spine_label,
            "note": self.note,
            "spine_watermark": self.spine_watermark,
            "totals": {
                "claims_read": self.claims_read,
                "claims_shaped": self.claims_shaped,
                "claims_excluded_not_publishable": self.claims_excluded_not_publishable,
                "candidate_subjects_excluded": self.candidate_subjects_excluded,
                "subjects_total": self.subjects_total,
                "subjects_geolocated": self.subjects_geolocated,
                "subjects_conflicted": self.subjects_conflicted,
                "observation_groups_multi_source": self.observation_groups_multi_source,
            },
            "aggregates": [a.as_json() for a in self.aggregates],
            "coverage_metrics": list(self.coverage_metrics),
            "jurisdictions": [j.as_json() for j in self.jurisdictions],
            "sources": [s.as_json() for s in self.sources],
            "sharing_edges": [e.as_json() for e in self.sharing_edges],
            "provenance": dict(self.provenance),
            "sites": [s.as_json() for s in self.sites],
        }

    def to_json_str(self) -> str:
        return json.dumps(self.to_json(), indent=2, sort_keys=True) + "\n"

    def to_markdown(self) -> str:
        lines: list[str] = []
        w = lines.append
        w("# Export data-shaping — shaped dataset snapshot (P27.3, LAUNCH.3)")
        w("")
        w("> **Observation-level, not a resolved census (ADR-092, SIG-RECON-058).**")
        w('> Every site below is a *subject* carrying publishable claims — "N')
        w('> observations across M sources" — never a deduplicated device count.')
        w("> Cross-source duplicate cameras are labelled by a shared observation")
        w("> group, not merged.")
        w("")
        w(f"- **as_of:** `{self.as_of}` · **generated_at (UTC):** `{self.generated_at}`")
        w(f"- **spine:** `{self.spine_label}` · **watermark:** `{self.spine_watermark}`")
        w(f"- **note:** {self.note or '(none)'} · **schema:** `{self.schema_version}`")
        w("")
        w("## Headline (denominator-bearing — §32)")
        w("")
        w("| aggregate | phrasing |")
        w("|---|---|")
        for a in self.aggregates:
            w(f"| {a.label} | {a.phrase()} |")
        w("")
        w("## Jurisdiction groups (incl. the honest `unresolved` bucket)")
        w("")
        w("| jurisdiction | subjects | geolocated | conflicted | sources |")
        w("|---|---:|---:|---:|---|")
        for j in self.jurisdictions:
            w(
                f"| {j.jurisdiction} | {j.subjects:,} | {j.sites.phrase()} "
                f"| {j.conflicted_subjects:,} | {len(j.source_ids)} |"
            )
        w("")
        w("## Caveats")
        w("")
        w("- Observation-level: subjects are claims-grouped entities, not resolved")
        w("  devices; `observation_groups_multi_source` counts coordinate cells")
        w("  reported by ≥2 sources — probable duplicates, labelled not merged.")
        w("- `conflicted` subjects keep every candidate coordinate/jurisdiction in")
        w("  their envelopes; no value was picked (§3.1).")
        w("- No total and no population estimate is published (SIG-METRIC-008/010).")
        w("")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# The read-only query set. Every query is a SELECT; ordering is deterministic. #
# --------------------------------------------------------------------------- #

QUERIES: dict[str, str] = {
    # Every current claim over the shaping predicate set, with its source and its
    # EFFECTIVE rights (latest rights_decision over the recorded rights_id) and
    # its latest *eligible* establishing occurrence refs (P32.4/ADR-123) — the
    # {EFFECTIVE} marker is replaced at fetch time with the decision CTE +
    # claim_source_cte bound at the request's belief instant.
    "shaping_claims": (
        "{EFFECTIVE}" + "SELECT c.claim_id::text, c.subject_id::text, c.predicate_id, c.value_kind,"
        "       c.value_text, c.value_num, c.raw_value, c.observed_at,"
        "       c.sensitivity_tier, cs.source_id, ir.connector_name,"
        "       cs.capture_id::text, cs.retrieved_at, cs.bound_at,"
        "       COALESCE(ld.rights_id, c.rights_id)::text AS effective_rights_id,"
        "       rr.spdx_expression, rr.redistributable, rr.derivative_permitted,"
        "       rr.attribution_text, rr.terms_url,"
        # P32.5/ADR-124: the shared eligibility selector — one fragment, every
        # consumer (API + export + analytics + tiles all decide identically).
        # ``{PUB_GATE}`` expands to ``true`` on a pre-P32.5 spine (no registry).
        "       {PUB_GATE} AS publication_permitted,"
        # P34.21b (E2-12): the effective decision's stamp + basis (trailing
        # columns, NULL when the recorded rights stand) — the export names the
        # ADR-194 attribution corrections it carries from these.
        # P35.18 (JUR-02a): ``c.value_json::text`` trails the decision pair —
        # the persisted {scheme, value} identifier a new claim declares.
        # P35.25 (SIG-CONF-014): the claim's declared independence_class trails
        # value_json — ``{LINEAGE_JOIN}``/``{LINEAGE_COL}`` collapse to "" / NULL
        # on a pre-P35.25 spine (no claim_lineage table).
        "       ld.decided_at, ld.basis, c.value_json::text{LINEAGE_COL}"
        "  FROM claim c"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        "  LEFT JOIN ingest_run ir ON ir.run_id = c.ingest_run_id"
        "{LINEAGE_JOIN}"
        " WHERE c.predicate_id = ANY(%s)"
        "   AND upper_inf(c.sys_period)"
        " ORDER BY c.subject_id, c.predicate_id, c.claim_id"
    ),
    # Subject entity types (for the site record) + the candidate's recorded
    # residential-parcel flag (P35.66, SIG-PUB-011/013): a candidate_asset row
    # stamps the emit-path parcel verdict on the spine; the publish path reads
    # it and refuses the subject outright — never a device-layer row.
    "subject_entities": (
        "SELECT e.entity_id::text, e.entity_type,"
        "       COALESCE(ca.residential_parcel_flag, false)"
        "  FROM entity e"
        "  LEFT JOIN candidate_asset ca ON ca.entity_id = e.entity_id"
        " WHERE EXISTS (SELECT 1 FROM claim c WHERE c.subject_id = e.entity_id"
        "              AND c.predicate_id = ANY(%s) AND upper_inf(c.sys_period)"
        "              AND {PUB_GATE})"
        # P32.5/ADR-124: a fully-withheld subject contributes no entity-type row
        # — its claims (and the entity itself) stay on the spine for review.
        "   AND {PUB_ENTITY_GATE}"
        " ORDER BY e.entity_id"
    ),
    # Sources present on ANY current publishable-eligible claim, with run +
    # observation stats. P35.20b (ED-43): the predicate filter is gone — the
    # freshness surface covers every source with publishable claims, including
    # the non-site evidence sources (procurement/legislative/CCOPS/federal),
    # not only the site-predicate emitters.
    # {PUB_GATE} (P32.5/ADR-124): withheld claims never pad a source's public
    # claim/observation counts — a count that included them would leak that
    # something was withheld.
    "source_stats": (
        "{EFFECTIVE}" + "SELECT cs.source_id, count(*) AS claims,"
        "       max(c.observed_at) AS last_content_change,"
        "       count(*) FILTER (WHERE c.observed_at IS NOT NULL) AS observed_claims"
        "  FROM claim c"
        "  JOIN claim_source cs ON cs.claim_id = c.claim_id"
        " WHERE upper_inf(c.sys_period)"
        "   AND {PUB_GATE}"
        " GROUP BY cs.source_id ORDER BY cs.source_id"
    ),
    # Per-source run freshness inputs: the last SUCCESSFUL run's finish, plus the
    # latest run's status verbatim (a still-running land reads 'degraded').
    # P35.20b: over every predicate, not only the shaping set (ED-43).
    "source_runs": (
        "{EFFECTIVE}" + "SELECT cs.source_id,"
        "       max(ir.finished_at) FILTER ("
        "           WHERE ir.status IN ('succeeded','completed','success','ok')"
        "       ) AS last_successful_run,"
        "       (array_agg(ir.status ORDER BY ir.finished_at DESC NULLS LAST,"
        "                                   ir.run_id DESC))[1] AS last_status"
        "  FROM claim c"
        "  JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  JOIN ingest_run ir ON ir.run_id = c.ingest_run_id"
        " WHERE upper_inf(c.sys_period)"
        "   AND {PUB_GATE}"
        " GROUP BY cs.source_id ORDER BY cs.source_id"
    ),
    # P35.20b (ED-43, SIG-METRIC-006): the per-source staleness inputs over EVERY
    # predicate — the latest dated observation per (source, subject, predicate),
    # publishable-effective claims only (the same tier-0/redistributable/pub-gate
    # semantics the freshness surface already claimed). The dedupe happens in
    # SQL so the non-site sources' claims never travel as claim rows.
    "freshness_observations": (
        "{EFFECTIVE}" + "SELECT cs.source_id, c.subject_id::text, c.predicate_id,"
        "       max(c.observed_at) AS latest_observed_at"
        "  FROM claim c"
        "  JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE upper_inf(c.sys_period)"
        "   AND c.observed_at IS NOT NULL"
        "   AND rr.redistributable = 'yes'"
        "   AND c.sensitivity_tier = 0"
        "   AND {PUB_GATE}"
        " GROUP BY cs.source_id, c.subject_id, c.predicate_id"
        " ORDER BY cs.source_id, c.subject_id, c.predicate_id"
    ),
    # Sharing-edge claims: entity_ref / sharing predicates at the public tier,
    # publishable-effective only (the public dataset never names a partner a
    # non-redistributable claim asserted). The P31.5 partner-organisation entity-refs
    # (a buyer, a seller, a camera's operator — ADR-112) are not sharing edges and
    # are left out, so they never surface as "unclassified" access edges.
    "sharing_edges": (
        "{EFFECTIVE}" + "SELECT c.claim_id::text, c.subject_id::text, c.predicate_id,"
        "       COALESCE(c.object_entity::text, c.value_text) AS partner_ref,"
        "       cs.source_id, c.observed_at"
        "  FROM claim c"
        "  LEFT JOIN claim_source cs ON cs.claim_id = c.claim_id"
        "  LEFT JOIN latest_decision ld"
        "         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        "  JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE ((c.object_entity IS NOT NULL AND c.predicate_id NOT IN ("
        + ", ".join(f"'{p}'" for p in sorted(PARTNER_PREDICATES))
        + ")) OR c.predicate_id LIKE '%sharing%'"
        "        OR c.predicate_id LIKE '%partner%')"
        "   AND rr.redistributable = 'yes'"
        "   AND upper_inf(c.sys_period) AND c.sensitivity_tier = 0"
        # P32.5/ADR-124: a withheld partner entity is absent from edges — no
        # topology leak, not merely an unlabelled node.
        "   AND {PUB_GATE}"
        " ORDER BY c.subject_id, c.predicate_id, c.claim_id"
    ),
    # The append-only spine watermark (P25.10; the bounded trigger-maintained
    # table since P32.4 / D-P31.1-1) — read via db.occurrences.spine_watermark,
    # which also covers a pre-change spine with the legacy count fallback.
    "spine_watermark": "__WATERMARK__",
}

#: The same queries minus the rights_decision CTE, for a pre-P27.2 spine. The
#: occurrence ordering matches the shared contract (latest establishing
#: occurrence); ``bound_at`` is not referenced so the query still runs on a
#: pre-P32.2 schema — a spine that old has no bound_at column.
_FALLBACK_CLAIM_SOURCE_CTE = (
    "WITH claim_source AS ("
    "  SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id,"
    "         ce.capture_id, ec.retrieved_at, NULL::timestamptz AS bound_at"
    "    FROM claim_evidence ce"
    "    JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
    "    JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
    "   WHERE ce.role = 'establishes'"
    "   ORDER BY ce.claim_id, ec.retrieved_at DESC NULLS LAST, ce.capture_id ASC"
    ") "
)


#: P35.25 (SIG-CONF-014): the additive claim-lineage projection. ``{LINEAGE_JOIN}``
#: joins the append-only per-claim lineage record; ``{LINEAGE_COL}`` selects the
#: resolved ``independence_class`` — ``NULL`` when the spine predates P35.25.
_LINEAGE_JOIN = "  LEFT JOIN claim_lineage cl ON cl.claim_id = c.claim_id"
_LINEAGE_COL = ", cl.independence_class"


def expand_query(
    sql: str,
    *,
    bound: str = BELIEF_NOW,
    pub_gate: str | None = None,
    pub_entity_gate: str | None = None,
) -> str:
    """Expand the markers into executable SQL (a raw query string is not
    executable until expanded).

    ``bound`` is the occurrence bound expression — ``BELIEF_NOW`` for a
    current-knowledge read, ``BELIEF_PARAM`` for a ``%s`` belief placeholder
    (one leading parameter is then required). ``{PUB_GATE}``/``{PUB_ENTITY_GATE}``
    (P32.5/ADR-124) default to the real shared fragments — the registry is part
    of the spine now; a pre-P32.5 dump goes through :func:`_queries_for`, which
    substitutes ``true`` BEFORE this call. ``{LINEAGE_JOIN}``/``{LINEAGE_COL}``
    (P35.25) default to the real join/projection; a pre-P35.25 dump substitutes
    ``""``/``, NULL`` in :func:`_queries_for`.
    """
    return (
        sql.replace("{EFFECTIVE}", _LATEST_DECISION_CTE + claim_source_cte(bound))
        .replace(
            "{PUB_GATE}",
            pub_gate if pub_gate is not None else claim_eligible_sql("c"),
        )
        .replace(
            "{PUB_ENTITY_GATE}",
            pub_entity_gate if pub_entity_gate is not None else entity_eligible_sql("e.entity_id"),
        )
        .replace("{LINEAGE_JOIN}", _LINEAGE_JOIN)
        .replace("{LINEAGE_COL}", _LINEAGE_COL)
    )


def _queries_for(
    has_decisions: bool,
    *,
    has_dispositions: bool = True,
    has_lineage: bool = True,
) -> dict[str, str]:
    """The query set for this spine — effective rights when decisions exist.

    ``{PUB_GATE}`` (P32.5/ADR-124) expands to the shared
    :func:`db.dispositions.claim_eligible_sql` selector on a spine carrying the
    ``publication_disposition`` registry, and to ``true`` on a pre-P32.5 dump —
    the registry is absent there and no disposition can be recorded (the
    review-flag half is in the same fragment, so it is gated together).
    ``has_lineage=False`` (a pre-P35.25 spine — no ``claim_lineage``) projects
    ``independence_class`` as NULL: an absent lineage is the honest undeclared
    state, never an independent voice.
    """
    gate = claim_eligible_sql("c") if has_dispositions else "true"
    entity_gate = entity_eligible_sql("e.entity_id") if has_dispositions else "true"
    lineage_join = _LINEAGE_JOIN if has_lineage else ""
    lineage_col = _LINEAGE_COL if has_lineage else ", NULL AS independence_class"
    if has_decisions:
        return {
            key: sql.replace("{PUB_GATE}", gate)
            .replace("{PUB_ENTITY_GATE}", entity_gate)
            .replace("{LINEAGE_JOIN}", lineage_join)
            .replace("{LINEAGE_COL}", lineage_col)
            for key, sql in QUERIES.items()
        }
        return {
            key: sql.replace("{PUB_GATE}", gate).replace("{PUB_ENTITY_GATE}", entity_gate)
            for key, sql in QUERIES.items()
        }
    out: dict[str, str] = {}
    for key, sql in QUERIES.items():
        # A pre-P27.2 spine has no rights_decision; the recorded rights_id IS the
        # effective one (fail-closed), so the ld join collapses to NULL.
        out[key] = (
            sql.replace("{EFFECTIVE}", _FALLBACK_CLAIM_SOURCE_CTE)
            .replace("{PUB_GATE}", gate)
            .replace("{PUB_ENTITY_GATE}", entity_gate)
            .replace("{LINEAGE_JOIN}", lineage_join)
            .replace("{LINEAGE_COL}", lineage_col)
            .replace("COALESCE(ld.rights_id, c.rights_id)", "c.rights_id")
            .replace(
                "  LEFT JOIN latest_decision ld"
                "         ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id",
                "",
            )
            # No rights_decision table → no decision columns to project: the
            # trailing pair collapses to NULLs (the parse defaults apply).
            .replace("ld.decided_at, ld.basis", "NULL, NULL")
        )
    return out


# --------------------------------------------------------------------------- #
# Pure layer                                                                   #
# --------------------------------------------------------------------------- #


def parse_coordinate(
    *, predicate_id: str, value_num: Any, value_text: str | None, raw_value: str
) -> ParsedValue:
    """Normalize one coordinate claim through the §24 parsing contract.

    Prefers the claim's typed ``value_num`` shadow (the sink's own normalization),
    else Decimal-parses ``value_text``/``raw_value`` — never a float() on raw text,
    so ``40.67730276104826`` keeps full precision. Range-checked per predicate.
    A failure is ``unparseable``: the raw literal is kept, ``parsed`` stays None —
    a gap, never a guess (SIG-PARSE-004).
    """
    raw = raw_value if raw_value is not None else (value_text or "")
    bounds = (-90.0, 90.0) if predicate_id == LAT_PREDICATE else (-180.0, 180.0)
    value: float | None = None
    if value_num is not None:
        value = float(value_num)
    else:
        text = value_text if value_text is not None else raw
        try:
            value = float(Decimal(str(text).strip()))
        except (InvalidOperation, ValueError, AttributeError):
            return ParsedValue.unparseable(raw, note="coordinate is not numeric")
    if not (bounds[0] <= value <= bounds[1]):
        return ParsedValue.unparseable(
            raw, note=f"coordinate {value} out of range {bounds} for {predicate_id}"
        )
    return ParsedValue.typed(raw, value, value_kind="coordinate")


def _display_value(claim: ShapingClaim) -> ParsedValue:
    """The normalized display value used for envelope distinctness."""
    if claim.predicate_id in GEO_PREDICATES:
        return parse_coordinate(
            predicate_id=claim.predicate_id,
            value_num=claim.value_num,
            value_text=claim.value_text,
            raw_value=claim.raw_value,
        )
    if claim.value_kind != "value":
        return ParsedValue.unparseable(claim.raw_value, note=f"value_kind={claim.value_kind}")
    text = claim.value_text
    if text is None and claim.value_num is not None:
        text = str(claim.value_num)
    if text is None:
        return ParsedValue.unparseable(claim.raw_value, note="no typed value")
    return ParsedValue.typed(claim.raw_value, text.strip(), value_kind="text")


@lru_cache(maxsize=1)
def _default_jurisdiction_config() -> JurisdictionSchemeConfig:
    """The committed declared-scheme config, read once per process."""
    return load_jurisdiction_scheme_config()


def _declared_jurisdiction_pair(claim: ShapingClaim) -> tuple[str, str] | None:
    """The ``{scheme, value}`` identifier pair persisted on the claim (P35.18).

    ``value_json`` carries the connector's declared ``candidate_identifier``
    verbatim (K4 §3.2 — stored there so the text value and digest stay
    unchanged). A missing or malformed blob is *not* an error — pre-P35.18
    claims carry none and still shape through the config basis; a blob without
    a usable pair is likewise undeclared, never guessed.
    """
    blob = claim.value_json
    if not blob:
        return None
    doc: Any = blob
    if isinstance(doc, str):
        try:
            doc = json.loads(doc)
        except ValueError:
            return None
    if not isinstance(doc, Mapping):
        return None
    scheme = doc.get("scheme")
    value = doc.get("value")
    if isinstance(scheme, str) and scheme.strip() and isinstance(value, str) and value.strip():
        return scheme.strip(), value.strip()
    return None


def _jurisdiction_display(
    claim: ShapingClaim, config: JurisdictionSchemeConfig | None
) -> tuple[ParsedValue, str | None, str | None]:
    """The scheme-keyed display value + its provenance (P35.18 / JUR-02a).

    A ``camera_jurisdiction`` claim's bucket is its *declared* ``(scheme,
    value)`` resolved through :func:`exports.jurisdictions.jurisdiction_key`
    (canonical keys like ``iso3166-2:US-OK``) — never the bare asserted code:

    * a new claim's persisted ``{scheme, value}`` pair keys it directly, with
      basis ``candidate_identifier`` (the claim itself declared it);
    * a legacy claim's scheme comes from the source's declared config, with
      basis ``declared_scheme_from_config@<sha256>`` — derived and labelled,
      never laundered into a re-adjudication (§3.1);
    * a claim with neither keeps its bare display value (undeclared — honest);
    * ``sig.unresolved`` (and a pair whose value is empty) keeps the honest
      ``unresolved`` bucket — no fabricated key is minted for it.

    Returns ``(parsed, scheme, scheme_basis)``; both provenance fields are
    ``None`` when the claim is not a jurisdiction claim or stays undeclared.
    """
    parsed = _display_value(claim)
    if claim.predicate_id != JURISDICTION_PREDICATE or not parsed.parse_ok:
        return parsed, None, None
    pair = _declared_jurisdiction_pair(claim)
    if pair is not None:
        scheme, value = pair
        basis = DECLARED_SCHEME_FROM_CLAIM
    else:
        cfg = config if config is not None else _default_jurisdiction_config()
        declared = cfg.for_claim(claim.source_id, str(parsed.parsed))
        if declared is None:
            return parsed, None, None
        scheme, value = declared.scheme, str(parsed.parsed)
        basis = declared.basis
    key = jurisdiction_key(scheme, value)
    bucket = key if key is not None else UNRESOLVED_JURISDICTION
    return (
        ParsedValue.typed(claim.raw_value, bucket, value_kind="jurisdiction_key"),
        scheme,
        basis,
    )


def observation_envelope(
    predicate_id: str,
    claims: Sequence[ShapingClaim],
    *,
    jurisdiction_config: JurisdictionSchemeConfig | None = None,
) -> ObservationEnvelope:
    """Compute the observation-level envelope for one (subject, predicate).

    Deterministic: claims are sorted by ``(claim_id)``; the modal value is the
    lexicographically-smallest among the most-supported distinct values (a pure
    function of the claim set). A conflict keeps every candidate visible.

    P32.4 / ADR-123: ``status``/``distinct_values``/``supporting``/``dissenting``
    are computed over the *candidates* — the latest eligible claim per source
    lineage — so a superseded same-source assertion stays visible in
    ``observations`` (labelled history) without posing as a current candidate,
    while genuinely independent sources remain concurrent candidates.
    """
    if not claims:
        return ObservationEnvelope(
            predicate_id=predicate_id,
            status=ENVELOPE_UNREPORTED,
            value=None,
            value_is_parseable=False,
            n_observations=0,
            n_sources=0,
            considered_claim_ids=(),
            supporting_claim_ids=(),
            dissenting_claim_ids=(),
            distinct_values=(),
            observations=(),
        )
    # P35.18 (JUR-02a): for the jurisdiction predicate the display value is the
    # declared-(scheme, value) canonical key — never the bare code — and each
    # observation carries the scheme + where it came from. The committed config
    # is consulted lazily, only for claims the predicate actually requires.
    parsed_by_id: dict[str, tuple[ParsedValue, str | None, str | None]] = {
        c.claim_id: _jurisdiction_display(c, jurisdiction_config) for c in claims
    }
    observations: list[ValueObservation] = []
    parseable_values: set[str] = set()
    # P32.4 / ADR-123: the envelope's CANDIDATES are the latest eligible claim
    # per source lineage (concurrent independent candidates stay concurrent — a
    # superseded same-source claim is history, not a current candidate, while
    # two sources disagreeing still conflict). ``observations``/``considered``
    # keep every claim as labelled history.
    candidates = lineage_candidates(list(claims))
    by_value: dict[str, list[str]] = {}
    for claim in sorted(claims, key=lambda c: c.claim_id):
        parsed, scheme, scheme_basis = parsed_by_id[claim.claim_id]
        display = parsed.parsed if parsed.parse_ok else f"(unparseable: {parsed.raw_value})"
        display_str = str(display)
        observations.append(
            ValueObservation(
                claim_id=claim.claim_id,
                source_id=claim.source_id or "(unattributed)",
                raw_value=claim.raw_value,
                display_value=display_str,
                observed_at=claim.observed_at.isoformat() if claim.observed_at else None,
                observed_basis=claim.observed_basis,
                capture_id=claim.occurrence_capture_id,
                scheme=scheme,
                scheme_basis=scheme_basis,
            )
        )
    for claim in sorted(candidates, key=lambda c: c.claim_id):
        parsed, _scheme, _scheme_basis = parsed_by_id[claim.claim_id]
        display = parsed.parsed if parsed.parse_ok else f"(unparseable: {parsed.raw_value})"
        display_str = str(display)
        if parsed.parse_ok:
            parseable_values.add(display_str)
        by_value.setdefault(display_str, []).append(claim.claim_id)
    distinct = sorted(by_value)
    considered = tuple(c.claim_id for c in sorted(claims, key=lambda c: c.claim_id))
    n_sources = len({c.source_id or "(unattributed)" for c in candidates})
    # P35.25 (SIG-CONF-014): corroboration truth. DISTINCT declared
    # independence classes among the candidates — a ``unclassified`` claim (or
    # one with no lineage row) never becomes an independence class; it is
    # counted as one of the unclassified candidates instead.
    declared_classes = {
        c.independence_class
        for c in candidates
        if c.independence_class and c.independence_class != "unclassified"
    }
    n_unclassified = sum(
        1 for c in candidates if not c.independence_class or c.independence_class == "unclassified"
    )
    if len(distinct) == 1:
        return ObservationEnvelope(
            predicate_id=predicate_id,
            status=ENVELOPE_RESOLVED,
            value=distinct[0],
            value_is_parseable=distinct[0] in parseable_values,
            n_observations=len(observations),
            n_sources=n_sources,
            n_independence_classes=len(declared_classes),
            n_unclassified_candidates=n_unclassified,
            considered_claim_ids=considered,
            supporting_claim_ids=tuple(sorted(by_value[distinct[0]])),
            dissenting_claim_ids=(),
            distinct_values=tuple(distinct),
            observations=tuple(observations),
        )
    # Conflicted: supporting = the modal value's backers (deterministic: most
    # claim ids, ties broken by smallest display value); the rest dissent.
    modal = min(distinct, key=lambda v: (-len(by_value[v]), v))
    supporting = tuple(sorted(by_value[modal]))
    dissenting = tuple(sorted(cid for v in distinct if v != modal for cid in by_value[v]))
    return ObservationEnvelope(
        predicate_id=predicate_id,
        status=ENVELOPE_CONFLICTED,
        value=None,
        value_is_parseable=False,
        n_observations=len(observations),
        n_sources=n_sources,
        n_independence_classes=len(declared_classes),
        n_unclassified_candidates=n_unclassified,
        considered_claim_ids=considered,
        supporting_claim_ids=supporting,
        dissenting_claim_ids=dissenting,
        distinct_values=tuple(distinct),
        observations=tuple(observations),
    )


def _resolved_coordinate(env: ObservationEnvelope) -> float | None:
    """The resolved coordinate as a float, or None when there is no usable one.

    A resolved-but-unparseable envelope (all claims agree on a non-numeric raw
    value) is a *gap*, not a point — ``None`` keeps it out of the geometry.
    """
    if env.status != ENVELOPE_RESOLVED or not env.value_is_parseable:
        return None
    try:
        return float(str(env.value))
    except (TypeError, ValueError):
        return None


def precision_for_tier(tier: int) -> str:
    """The §19.4 precision label for a claim sensitivity tier (data-driven)."""
    from policy._data import load_table

    spec = load_table("sensitivity")["tiers"].get(str(tier))
    return "unknown" if spec is None else str(spec["transform"])


def _classify_access_kind(predicate_id: str) -> str:
    """Map a sharing-edge predicate to a §12.2 access kind, honestly.

    Delegates to the reconciler's predicate-hint vocabulary
    (``reconcile.materialize.classify_access_kind`` — the same classification
    the §29.3 materializer writes onto materialized edges) so the export and
    the reconciler can never disagree; a predicate the vocabulary cannot
    classify reports ``unclassified`` rather than a guessed kind
    (SIG-ONTO-042). P34.34a drops the old bare ``"use" in predicate`` rule,
    which misclassified unrelated predicates like ``portal_stated_permitted_use``.
    """
    from reconcile.materialize import classify_access_kind

    return classify_access_kind(predicate_id) or "unclassified"


def _site_licence_conflict(records: Sequence[RightsRecord]) -> bool:
    """Whether the site's own licence mix is mutually incompatible (§42 gate).

    The gate is invoked per site only as a *conflict detector*: a site whose
    claims cannot resolve to one export licence cannot ship as one row (P27.4
    splits it per compartment). The single-table licence/compartment assignment
    itself stays with the export build — a standalone per-site licence would
    mislead (a lone CC0 site computes to CC-BY-SA under the most-constraining
    rule, although the real table licence is computed over all rows together).

    A site carrying an export-*refused* record (``UNDETERMINED`` /
    non-derivative / recorded-exclusion) is **not** a licence-mix conflict: that
    is a publishability decision the export gate makes per (source, rights) at
    build time (``partition_exportable`` drops it loudly), not a reason to crash
    site shaping — so ``ExportGateClosed`` is swallowed here and returns ``False``.
    """
    try:
        compute_export_license(records)
        return False
    except LicenseIncompatibilityError:
        return True
    except ExportGateClosed:
        # A refused record is handled by the export-time gate, not the mix detector.
        return False


def shape_sites(
    claims: Sequence[ShapingClaim],
    *,
    entity_types: Mapping[str, str],
    refused_subjects: Set[str] = frozenset(),
    jurisdiction_config: JurisdictionSchemeConfig | None = None,
) -> list[ShapedSite]:
    """Assemble publishable claims into observation-level sites (deterministic).

    P35.66 (SIG-PUB-011/013): ``refused_subjects`` — candidate assets and
    residential-parcel-flagged subjects, resolved by
    :func:`build_shaped_dataset` — never become sites; a candidate in a public
    device layer is a build error, so the refusal is enforced here and
    re-asserted post-shape.
    """
    by_subject: dict[str, list[ShapingClaim]] = {}
    for claim in claims:
        if claim.publishable and claim.subject_id not in refused_subjects:
            by_subject.setdefault(claim.subject_id, []).append(claim)

    sites: list[ShapedSite] = []
    for subject_id in sorted(by_subject):
        subject_claims = by_subject[subject_id]
        by_pred: dict[str, list[ShapingClaim]] = {}
        for claim in subject_claims:
            by_pred.setdefault(claim.predicate_id, []).append(claim)

        lat_env = observation_envelope(LAT_PREDICATE, by_pred.get(LAT_PREDICATE, ()))
        lon_env = observation_envelope(LON_PREDICATE, by_pred.get(LON_PREDICATE, ()))
        jur_env = observation_envelope(
            JURISDICTION_PREDICATE,
            by_pred.get(JURISDICTION_PREDICATE, ()),
            jurisdiction_config=jurisdiction_config,
        )
        label_env = observation_envelope(LABEL_PREDICATE, by_pred.get(LABEL_PREDICATE, ()))
        tech_env = observation_envelope(TECHNOLOGY_PREDICATE, by_pred.get(TECHNOLOGY_PREDICATE, ()))

        tier = max(c.sensitivity_tier for c in subject_claims)
        precision = precision_for_tier(tier)

        # The §19.4 reduction is the only path a published coordinate takes.
        # `sensitivity_tier` on a claim is the RLS *visibility* tier (§0.7):
        # publishable claims are tier-0 today, so apply_tier is the identity —
        # but a claim at a publishable-but-reduced tier would truncate/bin here.
        lat_full = _resolved_coordinate(lat_env)
        lon_full = _resolved_coordinate(lon_env)
        lat: float | None = None
        lon: float | None = None
        if lat_full is not None and lon_full is not None:
            reduced = apply_tier(lat_full, lon_full, tier)
            if reduced is not None:
                lat, lon = reduced
            point_status: PointStatus = "resolved"
        elif lat_env.status == ENVELOPE_CONFLICTED or lon_env.status == ENVELOPE_CONFLICTED:
            point_status = "conflicted"
        else:
            point_status = "unreported"

        if jur_env.status == ENVELOPE_RESOLVED and jur_env.value_is_parseable:
            jurisdiction = str(jur_env.value)
        elif jur_env.status == ENVELOPE_CONFLICTED:
            jurisdiction = CONFLICTED_JURISDICTION
        else:
            jurisdiction = UNASSERTED_JURISDICTION

        conflicted = tuple(
            sorted(
                p
                for p, env in (
                    (LAT_PREDICATE, lat_env),
                    (LON_PREDICATE, lon_env),
                    (JURISDICTION_PREDICATE, jur_env),
                    (LABEL_PREDICATE, label_env),
                    (TECHNOLOGY_PREDICATE, tech_env),
                )
                if env.status == ENVELOPE_CONFLICTED
            )
        )

        # Licence posture: keep every distinct effective rights record so P27.4
        # can place the row through the real gate; flag a mix the gate itself
        # refuses as incompatible.
        seen: set[tuple[str, str]] = set()
        records: list[RightsRecord] = []
        rights: list[dict[str, Any]] = []
        for c in sorted(subject_claims, key=lambda c: c.claim_id):
            key = (c.source_id or "(unattributed)", c.effective_rights_id)
            if key not in seen:
                seen.add(key)
                records.append(c.rights_record())
                rights.append(
                    {
                        "source_id": c.source_id or "(unattributed)",
                        "rights_id": c.effective_rights_id,
                        "spdx": c.effective_spdx,
                        "redistributable": c.effective_redistributable,
                        "derivative_permitted": c.effective_derivative_permitted,
                        "attribution": c.effective_attribution,
                        "terms_url": c.effective_terms_url,
                    }
                )
        rights.sort(key=lambda r: (r["source_id"], r["rights_id"]))
        licence_conflict = _site_licence_conflict(records)

        sources = tuple(sorted({c.source_id for c in subject_claims if c.source_id}))
        # The observation-level dedup key: the identical recorded coordinate
        # (pre-reduction, ~0.1 m at 6dp). Sites sharing it are labelled as
        # observations of possibly the same installation — never merged.
        observation_group = (
            f"{lat_full:.6f},{lon_full:.6f}"
            if point_status == "resolved" and lat_full is not None and lon_full is not None
            else None
        )
        sites.append(
            ShapedSite(
                entity_id=subject_id,
                entity_type=entity_types.get(subject_id, "(unknown)"),
                observation_level="observation",
                label=label_env.value if label_env.status == ENVELOPE_RESOLVED else None,
                technology=(str(tech_env.value) if tech_env.status == ENVELOPE_RESOLVED else None),
                technology_status=tech_env.status,
                jurisdiction=jurisdiction,
                jurisdiction_status=jur_env.status,
                latitude=lat,
                longitude=lon,
                point_status=point_status,
                has_coordinate_claims=bool(
                    by_pred.get(LAT_PREDICATE) or by_pred.get(LON_PREDICATE)
                ),
                sensitivity_tier=tier,
                precision=precision,
                source_ids=sources,
                n_observation_claims=len(subject_claims),
                n_sources=len(sources),
                licenses=tuple(sorted({c.effective_spdx for c in subject_claims})),
                rights=tuple(rights),
                licence_conflict=licence_conflict,
                conflicted_predicates=conflicted,
                claim_ids=tuple(sorted(c.claim_id for c in subject_claims)),
                observation_group=observation_group,
                lat_envelope=lat_env,
                lon_envelope=lon_env,
                jurisdiction_envelope=jur_env,
                technology_envelope=tech_env,
            )
        )
    return sites


def group_jurisdictions(
    sites: Sequence[ShapedSite],
    *,
    all_subjects: Mapping[str, str],
) -> list[JurisdictionGroup]:
    """Per-jurisdiction grouping over shaped sites + ungeoed subjects.

    ``all_subjects`` maps every publishable subject id → its jurisdiction bucket
    (resolved value, or ``(unasserted)``/``(conflicted)``); sites carry the
    geolocated side. Every count is denominated; ``unresolved`` is a first-class
    bucket, never dropped.
    """
    buckets: dict[str, dict[str, Any]] = {}
    for jurisdiction in all_subjects.values():
        buckets.setdefault(
            jurisdiction, {"subjects": 0, "geolocated": 0, "conflicted": 0, "sources": set()}
        )
        buckets[jurisdiction]["subjects"] += 1
    for site in sites:
        bucket = buckets.setdefault(
            site.jurisdiction,
            {"subjects": 0, "geolocated": 0, "conflicted": 0, "sources": set()},
        )
        bucket["sources"].update(site.source_ids)
        if site.point_status == "resolved":
            bucket["geolocated"] += 1
        elif site.point_status == "conflicted":
            bucket["conflicted"] += 1
    groups: list[JurisdictionGroup] = []
    for jurisdiction in sorted(buckets):
        b = buckets[jurisdiction]
        subjects = b["subjects"]
        geolocated = int(b["geolocated"])
        conflicted = int(b["conflicted"])
        groups.append(
            JurisdictionGroup(
                jurisdiction=jurisdiction,
                subjects=subjects,
                sites=PublishedAggregate(
                    label=f"geolocated site observations in {jurisdiction}",
                    count=geolocated,
                    denominator=subjects,
                    # Not evaluable = subjects with no usable coordinate evidence
                    # at all (a gap, not a zero). Conflicted subjects carry
                    # evidence — they are disclosed separately, not hidden here.
                    not_evaluable=subjects - geolocated - conflicted,
                ),
                conflicted_subjects=conflicted,
                source_ids=tuple(sorted(b["sources"])),
                is_unresolved=jurisdiction == UNRESOLVED_JURISDICTION,
            )
        )
    # Deterministic: unresolved first? No — name asc is the canonical order; the
    # unresolved bucket is flagged, not reordered.
    return groups


def jurisdiction_scheme_mix_violations(
    claims: Sequence[ShapingClaim],
    *,
    jurisdiction_config: JurisdictionSchemeConfig | None = None,
) -> list[str]:
    """The JUR-02a regression: no jurisdiction bucket may mix schemes.

    Every ``camera_jurisdiction`` claim derives its bucket from its declared
    ``(scheme, value)`` — its own persisted pair, or the labelled config basis
    — or honestly stays bare. A bucket is *mixed* when a scheme-keyed claim
    shares it with a claim that declared nothing: that is a bare value
    colliding with a derived key, the exact bug this row removes. Two declared
    schemes mapping onto one canonical key (``us.state_abbr:OK`` and
    ``iso.3166_2:US-OK``) are not a mix — the K4 §3.2 map merges them by
    design. Returns one message per violation; empty = clean.
    """
    buckets: dict[str, list[tuple[str | None, str]]] = {}
    for claim in claims:
        if claim.predicate_id != JURISDICTION_PREDICATE:
            continue
        parsed, scheme, _basis = _jurisdiction_display(claim, jurisdiction_config)
        display = parsed.parsed if parsed.parse_ok else f"(unparseable: {parsed.raw_value})"
        buckets.setdefault(str(display), []).append((scheme, claim.claim_id))
    violations: list[str] = []
    for bucket, members in sorted(buckets.items()):
        keyed = sorted(cid for s, cid in members if s is not None)
        bare = sorted(cid for s, cid in members if s is None)
        if keyed and bare:
            violations.append(
                f"jurisdiction bucket {bucket!r} mixes scheme-keyed claims "
                f"({', '.join(keyed)}) with undeclared claims ({', '.join(bare)})"
                " — a bare value must never land in a scheme-keyed bucket"
            )
    return violations


def coverage_aggregates(
    sites: Sequence[ShapedSite],
    jurisdictions: Sequence[JurisdictionGroup],
    *,
    subjects_total: int,
    claims_shaped: int,
    claim_ids_with_source: Sequence[str],
    all_shaped_claim_ids: Sequence[str],
) -> tuple[PublishedAggregate, ...]:
    """The §32 counted quantities — every one denominated, never a total."""
    geolocated = sum(1 for s in sites if s.point_status == "resolved")
    resolved_jurisdiction = sum(1 for s in sites if s.jurisdiction_status == ENVELOPE_RESOLVED)
    with_coordinate_evidence = sum(1 for s in sites if s.has_coordinate_claims)
    # Cross-source duplication is an *observation-group* property, not a per-site
    # one: two sources describing the same coordinate cell produce two subjects
    # (one source each) that share an observation-group key. Counting per-site
    # ``n_sources >= 2`` would read 0 while the group total is non-zero — the
    # honest dedup signal is sites whose coordinate cell was seen by ≥2 sources.
    group_sources: dict[str, set[str]] = {}
    for s in sites:
        if s.observation_group:
            group_sources.setdefault(s.observation_group, set()).update(s.source_ids)
    multi_source = sum(
        1 for s in sites if s.observation_group and len(group_sources[s.observation_group]) >= 2
    )
    return (
        PublishedAggregate(
            label="geolocated site observations",
            count=geolocated,
            denominator=subjects_total,
            # Not evaluable = no coordinate evidence at all. Conflicted subjects
            # carry evidence (it disagrees) and are disclosed, not hidden here.
            not_evaluable=subjects_total - with_coordinate_evidence,
        ),
        PublishedAggregate(
            label="site observations in a coordinate cell observed by two or more sources",
            count=multi_source,
            denominator=len(sites),
        ),
        PublishedAggregate(
            label="site observations with a resolved jurisdiction",
            count=resolved_jurisdiction,
            denominator=len(sites),
            not_evaluable=sum(1 for s in sites if s.jurisdiction_status == ENVELOPE_UNREPORTED),
        ),
        PublishedAggregate(
            label="publishable claims carrying source attribution",
            count=len(set(claim_ids_with_source)),
            denominator=len(set(all_shaped_claim_ids)),
        ),
    )


def coverage_metrics(
    aggregates: Sequence[PublishedAggregate],
    jurisdictions: Sequence[JurisdictionGroup],
) -> tuple[dict[str, Any], ...]:
    """The ``web/src/lib/metrics.ts`` ``CoverageMetric``-shaped rows (§32.5).

    ``is_population_total`` is pinned ``false``; the denominator names exactly
    what was counted; ``population_note`` states the true population is unknown.
    """
    population_note = (
        "The true population of surveillance devices is unknown. These are "
        "recorded observations from named sources — an observation-level "
        "inventory, not a census or an estimate (SIG-METRIC-008)."
    )
    metrics: list[dict[str, Any]] = []
    for agg in aggregates:
        metrics.append(
            {
                "id": "agg_" + agg.label.replace(" ", "_"),
                "kind": "counted_quantity",
                "label": agg.label,
                "value": agg.phrase(),
                "denominator": f"evaluable {agg.label.split(' in ')[0]} "
                f"(of {agg.denominator} publishable subjects/observations)",
                "population_note": population_note,
                "is_population_total": False,
            }
        )
    for group in jurisdictions:
        metrics.append(
            {
                "id": f"jurisdiction_{group.jurisdiction}",
                "kind": "counted_quantity",
                "label": f"geolocated site observations in {group.jurisdiction}",
                "value": group.sites.phrase(),
                "denominator": (
                    f"{group.subjects} publishable subjects asserting "
                    f"jurisdiction {group.jurisdiction!r}"
                ),
                "population_note": population_note,
                "is_population_total": False,
            }
        )
    return tuple(metrics)


def source_freshness_rows(
    observations: Sequence[Sequence[Any]],
    *,
    run_stats: Mapping[str, Mapping[str, Any]],
    as_of: date,
    volatility_classes: Mapping[str, str] | None = None,
) -> list[ShapedSourceFreshness]:
    """Per-source freshness (SIG-METRIC-007), volatility-relative (SIG-METRIC-006).

    ``observations`` rows are ``(source_id, subject_id, predicate_id,
    latest_observed_at)`` — the ``freshness_observations`` read, already deduped
    to the latest dated claim per (source, subject, predicate) and covering
    EVERY predicate, so the non-site evidence sources (procurement,
    legislative, CCOPS, federal — ED-43) carry rows alongside the site
    emitters. The population is the union of the read's sources and the
    run-stat sources (a source with a recorded run but no publishable dated
    claim still gets a row — an honest ``not_evaluable``, never absent).

    P35.20b (SIG-METRIC-006, GQ-15): staleness is evaluable ONLY against the
    source's *declared* registry volatility class (``sources.toml``
    ``volatility_class``, ADR-104(e)-grounded, never inferred). For a declared
    source, registered-predicate observations are evaluated and the rest count
    as ``staleness_not_evaluable``; an undeclared source's entire dated set is
    ``not_evaluable`` — the row reads ``not_evaluable``, never ``ok`` or a
    fabricated stale-0. ``volatility_classes=None`` loads the committed
    declarations; an explicit mapping overrides them (test seam).
    """
    classes = declared_volatility_classes() if volatility_classes is None else volatility_classes

    by_source: dict[str, list[tuple[str, str, date]]] = {}
    for r in observations:
        source_id, subject_id, predicate_id, observed_at = r[:4]
        if source_id is None or observed_at is None:
            continue
        observed = (
            observed_at.date()
            if isinstance(observed_at, datetime)
            else observed_at
            if isinstance(observed_at, date)
            else None
        )
        if observed is None:
            continue
        by_source.setdefault(str(source_id), []).append(
            (str(subject_id), str(predicate_id), observed)
        )

    rows: list[ShapedSourceFreshness] = []
    for source_id in sorted(set(by_source) | set(run_stats)):
        declared = classes.get(source_id)
        evaluable: list[tuple[str, date]] = []
        not_evaluable = 0
        for _subject_id, predicate_id, observed in by_source.get(source_id, ()):
            if declared is None:
                not_evaluable += 1
                continue
            try:
                predicate_meta(predicate_id)
            except KeyError:
                not_evaluable += 1
                continue
            evaluable.append((predicate_id, observed))
        stats = run_stats.get(source_id, {})
        freshness = source_freshness(
            source_id,
            status=_map_run_status(stats.get("status")),
            last_successful_run=stats.get("last_successful_run"),
            last_content_change=stats.get("last_content_change"),
            observations=evaluable,
            as_of=as_of,
            declared_volatility_class=declared,
            not_evaluable_count=not_evaluable,
        )
        rows.append(
            ShapedSourceFreshness(
                freshness=freshness,
                staleness_not_evaluable=freshness.not_evaluable_count,
                volatility_class=declared if declared is not None else NOT_EVALUABLE,
                claims=int(stats.get("claims", len(by_source.get(source_id, ())))),
            )
        )
    return rows


def shape_sharing_edges(rows: Sequence[Sequence[Any]]) -> list[SharingEdge]:
    """Sharing-edge claims → typed edges with the three access kinds (§29.3)."""
    edges: list[SharingEdge] = []
    for r in rows:
        claim_id, subject_id, predicate_id, partner_ref, source_id, observed_at = r
        edges.append(
            SharingEdge(
                subject_id=str(subject_id),
                predicate_id=str(predicate_id),
                partner_ref=None if partner_ref is None else str(partner_ref),
                access_kind=_classify_access_kind(str(predicate_id)),
                source_id=None if source_id is None else str(source_id),
                claim_id=str(claim_id),
                observed_at=(
                    observed_at.isoformat()
                    if isinstance(observed_at, (datetime, date))
                    else (None if observed_at is None else str(observed_at))
                ),
            )
        )
    edges.sort(key=lambda e: (e.subject_id, e.predicate_id, e.claim_id))
    return edges


def parse_shaping_claims(rows: Sequence[Sequence[Any]]) -> list[ShapingClaim]:
    """Parse raw ``shaping_claims`` rows into :class:`ShapingClaim` records.

    Extracted for P27.4: the spine-export orchestrator needs the same parsed
    claims to licence-slice each site per (source, rights) pair — it must not
    re-derive the parse.

    P34.18 / ADR-178 (S0 RI-01): the keyed-digest alias table projects every
    retired identifier — source id, and any handle-bearing token inside a
    subject/claim id or value — to its neutral public form at this single seam
    (claims keep their recorded ids; resolution is an export-time projection,
    never a spine rewrite, SIG-STORE-011). A ``camera_operator`` value that
    digests onto the suppressed set is marked non-publishable (the full
    predicate fix is P35.26's).
    """
    aliases = load_source_aliases()
    claims: list[ShapingClaim] = []
    for r in rows:
        (
            claim_id,
            subject_id,
            predicate_id,
            value_kind,
            value_text,
            value_num,
            raw_value,
            observed_at,
            sensitivity_tier,
            source_id,
            connector_name,
            occurrence_capture_id,
            occurrence_retrieved_at,
            occurrence_bound_at,
            effective_rights_id,
            spdx,
            redistributable,
            derivative_permitted,
            attribution,
            terms_url,
        ) = r[:20]
        # P32.5/ADR-124: the eligibility gate column is the 21st; a pre-P32.5
        # row set (synthetic fixtures, older dumps) carries none — absent a
        # recorded registry the pre-change posture applies (no dispositions can
        # exist, so nothing is withheld by them).
        publication_permitted = r[20] if len(r) > 20 else True
        # P34.21b: the decision stamp + basis are trailing columns 22–23 —
        # absent on a pre-P27.2 row set (they default to "no decision").
        decision_decided_at = r[21] if len(r) > 21 else None
        decision_basis = r[22] if len(r) > 22 else None
        # P35.18 (JUR-02a): the claim's stored ``value_json`` blob is the 24th
        # column — absent on a pre-P35.18 row set (declared-scheme derivation
        # then falls to the config basis, exactly the legacy path).
        value_json = r[23] if len(r) > 23 else None
        # P35.25 (SIG-CONF-014): the resolved independence class is the 25th
        # column — absent/NULL on a pre-P35.25 row set (the claim reads
        # undeclared, never independent).
        independence_class = r[24] if len(r) > 24 else None
        observed_date = (
            observed_at.date()
            if isinstance(observed_at, datetime)
            else (observed_at if isinstance(observed_at, date) else None)
        )
        # The shared contract's dating (ADR-123): the claim's own observed_at
        # instant when dated, else the latest eligible occurrence's retrieved_at
        # (the labelled undated fallback), else undated.
        if observed_at is not None:
            observed_instant = observed_at if isinstance(observed_at, datetime) else None
            observed_basis = "claim"
        elif occurrence_retrieved_at is not None:
            observed_instant = occurrence_retrieved_at
            observed_basis = "capture_retrieved_at_latest"
        else:
            observed_instant = None
            observed_basis = "undated"
        # P34.18: a suppressed camera_operator value is not publishable.
        if (
            predicate_id == "camera_operator"
            and publication_permitted
            and (
                aliases.is_suppressed_value("" if value_text is None else str(value_text))
                or aliases.is_suppressed_value("" if raw_value is None else str(raw_value))
            )
        ):
            publication_permitted = False
        claims.append(
            ShapingClaim(
                claim_id=aliases.resolve_text(str(claim_id)),
                subject_id=aliases.resolve_text(str(subject_id)),
                predicate_id=str(predicate_id),
                value_kind=str(value_kind),
                value_text=None if value_text is None else aliases.resolve_text(str(value_text)),
                value_num=None if value_num is None else float(value_num),
                raw_value="" if raw_value is None else aliases.resolve_text(str(raw_value)),
                observed_at=observed_date,
                sensitivity_tier=int(sensitivity_tier),
                source_id=None if source_id is None else aliases.resolve_text(str(source_id)),
                connector_name=None if connector_name is None else str(connector_name),
                effective_rights_id=str(effective_rights_id),
                effective_spdx=str(spdx),
                effective_redistributable=str(redistributable),
                effective_derivative_permitted=str(derivative_permitted),
                effective_attribution=""
                if attribution is None
                else aliases.resolve_text(str(attribution)),
                effective_terms_url="" if terms_url is None else str(terms_url),
                occurrence_capture_id=None
                if occurrence_capture_id is None
                else str(occurrence_capture_id),
                occurrence_retrieved_at=occurrence_retrieved_at,
                occurrence_bound_at=occurrence_bound_at,
                observed_instant=observed_instant,
                observed_basis=observed_basis,
                publication_permitted=bool(publication_permitted),
                effective_decision_decided_at=(
                    decision_decided_at if isinstance(decision_decided_at, datetime) else None
                ),
                effective_decision_basis=(None if decision_basis is None else str(decision_basis)),
                value_json=(
                    None
                    if value_json is None
                    else (
                        json.dumps(value_json, sort_keys=True, default=str)
                        if isinstance(value_json, Mapping)
                        else str(value_json)
                    )
                ),
                independence_class=(
                    None if independence_class is None else str(independence_class)
                ),
            )
        )
    return claims


def _freshness_observations_from_claims(
    claims: Sequence[ShapingClaim],
) -> list[tuple[str, str, str, date]]:
    """Legacy-raw fallback: dedupe publishable claims to the latest dated
    observation per (source, subject, predicate) — the same shape the
    ``freshness_observations`` read serves (P35.20b). Used only when ``raw``
    carries no ``freshness_observations`` key (the pre-change fixture seam);
    the production fetch always serves the all-predicate read.
    """
    latest: dict[tuple[str, str, str], date] = {}
    for c in claims:
        if c.source_id is None or c.observed_at is None:
            continue
        key = (c.source_id, c.subject_id, c.predicate_id)
        if key not in latest or c.observed_at > latest[key]:
            latest[key] = c.observed_at
    return [(s, subj, pred, d) for (s, subj, pred), d in sorted(latest.items())]


def build_shaped_dataset(
    raw: Mapping[str, Any],
    *,
    as_of: str,
    generated_at: str,
    spine_label: str,
    note: str = "",
    jurisdiction_config: JurisdictionSchemeConfig | None = None,
    volatility_classes: Mapping[str, str] | None = None,
) -> ShapedDataset:
    """Assemble the :class:`ShapedDataset` from fetched rows (pure — no database).

    ``raw`` maps each :data:`QUERIES` key to its fetched result rows. This is the
    unit-testable core; every decision is a pure function of ``raw``.

    ``jurisdiction_config`` overrides the committed declared-scheme config
    (P35.18/JUR-02a) — a test injection; ``None`` reads the committed TOMLs.
    """
    claims = parse_shaping_claims(raw.get("shaping_claims") or [])

    subject_rows = list(raw.get("subject_entities") or [])
    entity_types = {str(r[0]): str(r[1]) for r in subject_rows}
    subject_flags = {str(r[0]): bool(r[2]) for r in subject_rows if len(r) > 2}

    # P35.66 (SIG-PUB-011/013): a `candidate_asset` subject — or any subject
    # whose emit-stamped `residential_parcel_flag` is set — never shapes a
    # site. Refusal here is by CONSTRUCTION (the subject is excluded before
    # shaping), and the post-shape guard below re-asserts it as a build error
    # in case a refused subject is ever smuggled past the filter.
    refused_subjects = {
        sid
        for sid, etype in entity_types.items()
        if etype == "candidate_asset" or subject_flags.get(sid, False)
    }

    claims_read = len(claims)
    publishable_claims = [c for c in claims if c.publishable]
    claims_shaped = len(publishable_claims)

    sites = shape_sites(
        claims,
        entity_types=entity_types,
        refused_subjects=refused_subjects,
        jurisdiction_config=jurisdiction_config,
    )

    # P35.18 (JUR-02a): the no-mix regression guard — a scheme-keyed claim may
    # never share a bucket with an undeclared bare value. A violation is a
    # build error (fail closed), never a warning.
    mix_violations = jurisdiction_scheme_mix_violations(
        publishable_claims, jurisdiction_config=jurisdiction_config
    )
    if mix_violations:
        raise ValueError("jurisdiction buckets mix schemes (JUR-02a): " + "; ".join(mix_violations))

    # The post-shape guard (P35.66): a refused subject that reached a site is
    # a BUILD ERROR — raise, never warn. `assert_public_layer_subject` is the
    # shared enforcement every publish surface runs.
    for site in sites:
        assert_public_layer_subject(
            site.entity_type,
            residential_parcel_flag=subject_flags.get(site.entity_id, False),
            surface="exports/shaping",
        )

    # P35.66: the exclusion is counted honestly — a refused subject that
    # carried publishable shaping claims is named in the totals, never
    # silently dropped (§3.1).
    publishable_subjects = {c.subject_id for c in publishable_claims}
    candidate_subjects_excluded = len(refused_subjects & publishable_subjects)

    # Every publishable subject belongs to exactly one jurisdiction bucket —
    # the resolved value, or the honest unasserted/conflicted bucket.
    all_subjects: dict[str, str] = {}
    for site in sites:
        all_subjects[site.entity_id] = site.jurisdiction
    # Subjects with publishable claims but no shaping predicates resolved are
    # still sites (they carry SOME shaping claim) — sites covers all subjects.
    jurisdictions = group_jurisdictions(sites, all_subjects=all_subjects)

    # Observation groups: identical recorded coordinates seen by ≥2 sources —
    # the labelled (never merged) cross-source duplicate signal.
    group_sources: dict[str, set[str]] = {}
    for site in sites:
        if site.observation_group:
            group_sources.setdefault(site.observation_group, set()).update(site.source_ids)
    multi_source_groups = sum(1 for s in group_sources.values() if len(s) >= 2)

    run_stats: dict[str, dict[str, Any]] = {}
    for r in raw.get("source_stats") or []:
        source_id, n_claims, last_content_change, _observed_claims = r
        run_stats[str(source_id)] = {
            "claims": int(n_claims),
            "last_content_change": last_content_change,
        }
    for r in raw.get("source_runs") or []:
        source_id, last_successful_run, last_status = r
        stats = run_stats.setdefault(str(source_id), {})
        stats["last_successful_run"] = last_successful_run
        stats["status"] = _map_run_status(last_status)
    # P31.2 / ADR-109: the appended ingest_run_completion rows are the run-lifecycle
    # record. Where a source has completions, they win. The legacy ingest_run columns
    # above stay the fallback (a pre-P31.2 spine, or a run inserted already closed).
    for r in raw.get("source_completions") or []:
        source_id, last_ok, last_change, last_status = r
        stats = run_stats.setdefault(str(source_id), {})
        legacy_ok = stats.get("last_successful_run")
        if last_ok is not None:
            stats["last_successful_run"] = last_ok if legacy_ok is None else max(last_ok, legacy_ok)
        # Content change = the latest completion that INSERTED claims, never merely
        # the latest completion (a +0 re-run changed nothing).
        if last_change is not None:
            stats["last_content_change"] = last_change
        stats["status"] = _map_run_status(last_status)
    as_of_date = date.fromisoformat(as_of[:10]) if as_of else date.today()
    # P35.20b (ED-43): freshness reads the all-predicate ``freshness_observations``
    # rows when served; a row set without the key (the pre-change fixture seam)
    # falls back to the same shape derived from the publishable shaping claims —
    # never a widened read the spine did not serve.
    freshness_observations = raw.get("freshness_observations")
    if freshness_observations is None:
        freshness_observations = _freshness_observations_from_claims(publishable_claims)
    sources = source_freshness_rows(
        freshness_observations,
        run_stats=run_stats,
        as_of=as_of_date,
        volatility_classes=volatility_classes,
    )

    sharing_edges = shape_sharing_edges(raw.get("sharing_edges") or [])

    subjects_total = len(all_subjects)
    geolocated = sum(1 for s in sites if s.point_status == "resolved")
    conflicted = sum(1 for s in sites if s.point_status == "conflicted")

    provenance = provenance_completeness(
        [c.claim_id for c in publishable_claims],
        claims_with_resolvable_evidence=[c.claim_id for c in publishable_claims if c.source_id],
    ).as_json()

    aggregates = coverage_aggregates(
        sites,
        jurisdictions,
        subjects_total=subjects_total,
        claims_shaped=claims_shaped,
        claim_ids_with_source=[c.claim_id for c in publishable_claims if c.source_id],
        all_shaped_claim_ids=[c.claim_id for c in publishable_claims],
    )
    metrics = coverage_metrics(aggregates, jurisdictions)

    return ShapedDataset(
        as_of=as_of,
        generated_at=generated_at,
        spine_label=spine_label,
        note=note,
        schema_version=SHAPING_SCHEMA_VERSION,
        spine_watermark=str(raw.get("spine_watermark", "")),
        sites=tuple(sites),
        jurisdictions=tuple(jurisdictions),
        sources=tuple(sources),
        sharing_edges=tuple(sharing_edges),
        aggregates=aggregates,
        coverage_metrics=metrics,
        claims_read=claims_read,
        claims_shaped=claims_shaped,
        claims_excluded_not_publishable=claims_read - claims_shaped,
        candidate_subjects_excluded=candidate_subjects_excluded,
        subjects_total=subjects_total,
        subjects_geolocated=geolocated,
        subjects_conflicted=conflicted,
        observation_groups_multi_source=multi_source_groups,
        provenance=provenance,
    )


def _map_run_status(status: Any) -> str:
    """Map an ingest_run status onto the web FreshnessRow status enum.

    Already-mapped values pass through unchanged, so the map is idempotent.
    """
    s = str(status).lower()
    if s in {"succeeded", "completed", "success", "ok"}:
        return "ok"
    if s in {"failed", "error", "crashed", "failing"}:
        return "failing"
    if s in {"retired", "disabled", "decommissioned"}:
        return "retired"
    return "degraded"  # running / unknown — honest non-ok


#: Completion statuses that count as a successful run (the execution ended
#: normally). Mirrors ``db.run_completion.SUCCESSFUL_STATUSES`` without adding a
#: direct ``exports → db`` dependency edge; a test pins the two equal.
SUCCESSFUL_RUN_STATUSES = ("ok", "partial", "quota_reached")

#: Per-source run completion (P31.2 / ADR-109), read only when the
#: ``ingest_run_completion`` table exists. ``last_successful_run`` = the latest
#: completion whose execution ended normally. ``last_content_change`` = the latest
#: completion that inserted > 0 claims. ``last_status`` = the latest completion's
#: status verbatim. A belief pin (§9.4) also hides completions recorded after it.
SOURCE_COMPLETIONS_QUERY = (
    "SELECT source_id,"
    "       max(finished_at) FILTER (WHERE status = ANY(%s)) AS last_successful_run,"
    "       max(finished_at) FILTER (WHERE claims_inserted > 0) AS last_content_change,"
    "       (array_agg(status ORDER BY finished_at DESC, completion_id DESC))[1]"
    "         AS last_status"
    "  FROM ingest_run_completion"
    " WHERE source_id IS NOT NULL{belief}"
    " GROUP BY source_id ORDER BY source_id"
)


def fetch_source_completions(cur: _Cursor, *, belief: datetime | None = None) -> list[Any]:
    """The per-source completion stats, or ``[]`` on a spine without the table."""
    cur.execute("SELECT to_regclass('ingest_run_completion') IS NOT NULL")
    present = cur.fetchone()
    if not (present and present[0]):
        return []
    if belief is None:
        cur.execute(SOURCE_COMPLETIONS_QUERY.format(belief=""), (list(SUCCESSFUL_RUN_STATUSES),))
    else:
        cur.execute(
            SOURCE_COMPLETIONS_QUERY.format(belief=" AND recorded_at <= %s::timestamptz"),
            (list(SUCCESSFUL_RUN_STATUSES), belief),
        )
    return list(cur.fetchall())


def fetch_shaping_raw(
    cur: _Cursor,
    queries: Mapping[str, str],
    *,
    belief: datetime | None = None,
) -> dict[str, Any]:
    """Fetch every shaping query inside the caller's transaction (read-only).

    Extracted for P27.4: :func:`run_spine_export` runs this inside its own
    ``REPEATABLE READ READ ONLY`` snapshot so the supplementary export reads see
    the *same* spine state — it must not open a second snapshot.

    The belief predicate is injected into the fixed query text — a constant of
    this module, never caller SQL. P32.4 / ADR-123: the same belief instant
    bounds the ``claim_source`` CTE's ``bound_at`` (evidence-knowledge time)
    inside ``{EFFECTIVE}``, so a belief-pinned fetch sees exactly the claims and
    the evidence bindings known at that instant — nothing later leaks backward.
    """
    belief_filter = (
        "upper_inf(c.sys_period)" if belief is None else "c.sys_period @> %s::timestamptz"
    )
    occ_bound = BELIEF_PARAM if belief is not None else BELIEF_NOW
    raw: dict[str, Any] = {}
    predicates = list(SHAPING_PREDICATES)
    for key, query in queries.items():
        sql = expand_query(query, bound=occ_bound).replace("upper_inf(c.sys_period)", belief_filter)
        if key == "spine_watermark":
            raw[key] = _spine_watermark_read(cur)
            continue
        params: list[Any] = []
        if "{EFFECTIVE}" in query and belief is not None:
            params.append(belief)  # the CTE's bound_at — the first %s in the SQL
        if "%s" in sql:
            if "ANY(%s)" in sql:
                params.append(predicates)
            if "@> %s" in sql:
                params.append(belief)
        cur.execute(sql, tuple(params) if params else None)
        raw[key] = cur.fetchall()
    raw["source_completions"] = fetch_source_completions(cur, belief=belief)
    return raw


def run_shaping(
    conn: _Connection,
    *,
    as_of: str | None = None,
    belief: datetime | None = None,
    note: str = "",
    spine_label: str = "(unlabelled spine)",
    volatility_classes: Mapping[str, str] | None = None,
) -> ShapedDataset:
    """Execute the read-only query set against ``conn`` and assemble the dataset.

    Read-only and snapshot-consistent:

    * The session is put in read-only mode (``default_transaction_read_only =
      on``) so no query can mutate the spine — append-only held trivially (§16).
    * When the connection is idle the fetch runs inside an explicit
      ``REPEATABLE READ READ ONLY`` transaction, so every SELECT sees one spine
      snapshot and the disclosed watermark *is* the fetched state. When the
      caller already holds an open transaction (the test seam) the fetch runs
      inside it unchanged.
    * ``belief`` optionally pins the read to an assertion-time instant
      (``sys_period @> belief``, §9.4): the same spine + the same belief pin
      reproduces the same dataset (SIG-EXPORT-003). Default is "current"
      (``upper_inf(sys_period)``), labelled by ``as_of``.
    """
    generated_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    as_of = as_of or generated_at

    cur = conn.cursor()
    cur.execute("SET default_transaction_read_only = on")

    # Snapshot when the connection is idle (autocommit production path); when a
    # caller-owned transaction is already open we fetch inside it and leave its
    # lifecycle alone (the test seam relies on this).
    status = getattr(getattr(conn, "info", None), "transaction_status", None)
    snapshot = status is None or int(status) == 0  # IDLE (or uninstrumented)
    if snapshot:
        cur.execute("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY")
    try:
        cur.execute("SELECT to_regclass('rights_decision') IS NOT NULL")
        has_row = cur.fetchone()
        has_decisions = bool(has_row and has_row[0])
        cur.execute("SELECT to_regclass('publication_disposition') IS NOT NULL")
        has_row = cur.fetchone()
        has_dispositions = bool(has_row and has_row[0])
        cur.execute("SELECT to_regclass('claim_lineage') IS NOT NULL")
        has_row = cur.fetchone()
        queries = _queries_for(
            has_decisions,
            has_dispositions=has_dispositions,
            has_lineage=bool(has_row and has_row[0]),
        )

        raw = fetch_shaping_raw(cur, queries, belief=belief)
    finally:
        if snapshot:
            cur.execute("ROLLBACK")  # nothing to commit — the snapshot is spent

    return build_shaped_dataset(
        raw,
        as_of=as_of,
        generated_at=generated_at,
        spine_label=spine_label,
        note=note,
        # P35.20b: ``None`` loads the committed ``sources.toml`` declarations;
        # an explicit mapping is the test seam (a fabricated source declares
        # its class here, never in the registry file).
        volatility_classes=volatility_classes,
    )

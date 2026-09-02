# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The hand-written, versioned response contract for the public read API (§37).

These Pydantic models ARE the contract (SIG-API-001): the wire shape is written
by hand and never reflected from the storage schema, so the storage layer stays
refactorable and schema changes never leak to consumers. Every model that
carries a material fact embeds the full :class:`ResolutionEnvelope` (SIG-API-002)
— a bare value is never a top-level response — and every response echoes the
resolved as-of pair (:class:`AsOfEcho`, SIG-API-005) and a coverage statement
(:class:`CoverageStatement`, SIG-API-003).
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

#: The §37.1 resolution-envelope fields, in canonical order (SIG-API-002). The
#: contract test asserts every material-fact response carries exactly these keys,
#: so this tuple is the single source of truth for "what the envelope must have".
RESOLUTION_ENVELOPE_FIELDS: tuple[str, ...] = (
    "value",
    "resolution_status",
    "support",
    "agreement",
    "currency",
    "rationale",
    "supporting_claim_ids",
    "dissenting_claim_ids",
    "as_of_world",
    "as_of_belief",
    "ruleset_version",
)


class _Model(BaseModel):
    """Base: forbid unspecified fields so the wire contract cannot drift silently."""

    model_config = ConfigDict(extra="forbid")


class Rationale(_Model):
    """The resolver's rationale (§16.4): a stable code plus human-readable text.

    The §37.1 envelope names a single ``rationale`` field; the resolver splits it
    into a machine code and prose, and both are preserved here rather than
    flattened, so a consumer can branch on the code and still show the text.
    """

    code: str
    text: str


class ResolutionEnvelope(_Model):
    """The §37.1 resolution envelope carried by every material fact (SIG-API-002).

    A material fact is NEVER returned as a bare value: the value only ever appears
    inside this envelope, alongside the support/agreement/currency signals, the
    supporting and dissenting claim ids, the as-of pair the value was resolved at,
    and the ruleset version that decided it.
    """

    value: Any
    resolution_status: str
    support: str
    agreement: str
    currency: str | None
    rationale: Rationale
    supporting_claim_ids: list[str]
    dissenting_claim_ids: list[str]
    as_of_world: date
    as_of_belief: date
    ruleset_version: str
    # Additional provenance the envelope carries beyond the SIG-API-002 minimum;
    # optional so the contract's required set stays exactly the tuple above.
    contradiction_state: str | None = None
    winning_claim_id: str | None = None
    considered_claim_ids: list[str] = []
    resolver_version: str | None = None
    input_digest: str | None = None
    unresolved_code: str | None = None


class AsOfEcho(_Model):
    """The resolved two-axis as-of pair, echoed back on every read (SIG-API-005).

    Omitting the parameters never means an implicit "latest": the response states
    the exact world/belief instants it used and flags which were defaulted.
    ``belief_pinned`` drives the cache lifetime (SIG-API-006).
    """

    as_of_world: datetime
    as_of_belief: datetime
    world_defaulted: bool
    belief_defaulted: bool
    question: str
    belief_pinned: bool


class CoverageStatement(_Model):
    """The per-response coverage statement (§32.2, SIG-API-003).

    States what was evaluable, what was not, and why — never an unexplained gap.
    ``records`` are :meth:`inference.coverage.CoverageRecord.public_view` dicts.
    """

    scope: str
    complete: bool
    evaluated: int
    not_evaluable: int
    records: list[dict[str, Any]] = []


class CoverageResponse(_Model):
    """The ``/coverage/{scope}`` resource: a coverage statement that also echoes
    the as-of pair it was computed at (SIG-API-003/005)."""

    coverage: CoverageStatement
    as_of: AsOfEcho


class Attribution(_Model):
    """Upstream attribution for one constituent source (SIG-API-004, SIG-CONTRIB-020)."""

    source_id: str
    attribution: str
    license: str
    attribution_required: bool
    share_alike: bool
    terms_url: str
    upstream_license: str | None = None


class LicenseStatement(_Model):
    """The licence statement a collection response carries (§42.4, SIG-API-004).

    Computed from the constituent rights records via :mod:`policy.licensing`:
    ``effective_license`` is the single SPDX the collection may be redistributed
    under when one exists; when the constituents span mutually-incompatible
    compartments there is no single licence and ``compartments`` lists them.
    """

    effective_license: str | None
    single_license: bool
    compartments: list[str]
    obligations: list[Attribution]


class MaterialFact(_Model):
    """A resolved (subject, predicate) material fact and its envelope."""

    subject_id: str
    predicate_id: str
    envelope: ResolutionEnvelope


class ResolutionResponse(_Model):
    """A single material-fact resolution response (SIG-API-002/003/005)."""

    fact: MaterialFact
    coverage: CoverageStatement
    attribution: list[Attribution]
    as_of: AsOfEcho


class GeoPoint(_Model):
    """A published coordinate, already reduced to the asset's sensitivity tier.

    ``lat``/``lon`` are ``None`` when the sensitivity class permits only the
    jurisdiction (geo tier 3, §19.4); ``precision`` states the published rule so
    a consumer never mistakes a tier-reduced point for a rooftop fix.
    """

    lat: float | None
    lon: float | None
    sensitivity_class: str
    precision: str


class EntityResponse(_Model):
    """An entity resource (§37.3 ``/entity/{type}/{id}``).

    Carries its resolved material facts (each enveloped, SIG-API-002), its upstream
    attribution (SIG-API-004), a coverage statement, and — when the entity has a
    location — a coordinate already reduced to its sensitivity tier (SIG-API-012).
    """

    entity_id: str
    entity_type: str
    label: str | None
    facts: list[MaterialFact]
    attribution: list[Attribution]
    location: GeoPoint | None
    coverage: CoverageStatement
    as_of: AsOfEcho


class ClaimResponse(_Model):
    """A single claim resource (§37.3 ``/claim/{id}``): provenance, not a verdict.

    A claim is one asserted observation with its evidence, not the resolved value
    for its (subject, predicate) — the resolution lives at ``/resolution`` and is
    linked here — so this response is provenance and carries no bare "current
    value".
    """

    claim_id: str
    subject_id: str
    predicate_id: str
    value: Any
    raw_value: str
    observed_at: date
    source_id: str
    genre: str
    review_status: str
    evidence_capture_ids: list[str]
    resolution_ref: str
    coverage: CoverageStatement
    as_of: AsOfEcho


class EvidenceResponse(_Model):
    """An evidence-capture resource (§37.3 ``/evidence/{artifact}/{capture}``).

    ``representation`` is the tier-gated public view (:func:`evidence.tiers.public_representation`):
    a ``sealed`` capture yields metadata only and never its bytes (SIG-API-012);
    a ``restricted`` capture yields metadata with a redacted excerpt. This is the
    designed public representation (SIG-EVID-009/010), not a tier bypass — the
    bytes are gated separately and never reach this surface.
    """

    artifact_id: str
    capture_id: str
    tier: str
    bytes_available: bool
    representation: dict[str, Any]
    coverage: CoverageStatement
    as_of: AsOfEcho


class EntityRef(_Model):
    """A lightweight reference to an entity in a collection response."""

    entity_id: str
    entity_type: str
    label: str | None
    href: str


class SearchResponse(_Model):
    """A search collection (§37.3 ``/search``): refs + licence + coverage."""

    query: str
    results: list[EntityRef]
    coverage: CoverageStatement
    license: LicenseStatement
    as_of: AsOfEcho


class CrosswalkRow(_Model):
    """One external-identifier crosswalk row (§37.3 ``/crosswalk``)."""

    sig_id: str
    external_scheme: str
    external_id: str
    relation: str


class CrosswalkResponse(_Model):
    """A crosswalk collection: rows + licence + coverage."""

    rows: list[CrosswalkRow]
    coverage: CoverageStatement
    license: LicenseStatement
    as_of: AsOfEcho


class DossierResponse(_Model):
    """A dossier resource (§37.3 ``/dossier/{jurisdiction|org}``)."""

    scope: str
    title: str
    sections: list[dict[str, Any]]
    coverage: CoverageStatement
    license: LicenseStatement
    as_of: AsOfEcho


class TaskResponse(_Model):
    """A research-task resource (§37.3 ``/task``)."""

    task_id: str
    kind: str
    status: str
    subject_id: str | None
    predicate_id: str | None
    rationale: str
    coverage: CoverageStatement
    as_of: AsOfEcho


class TaskCollection(_Model):
    tasks: list[TaskResponse]
    coverage: CoverageStatement
    as_of: AsOfEcho


class ContradictionResponse(_Model):
    """A contradiction resource (§37.3 ``/contradiction``): always visible (§3.1)."""

    contradiction_id: str
    subject_id: str
    predicate_id: str
    kind: str
    state: str
    claim_ids: list[str]
    coverage: CoverageStatement
    as_of: AsOfEcho


class ContradictionCollection(_Model):
    contradictions: list[ContradictionResponse]
    coverage: CoverageStatement
    as_of: AsOfEcho


class ChangeEvent(_Model):
    """One field-level change (§29.7 snapshot diff), the /changes feed unit."""

    artifact_id: str
    field: str
    change_type: str
    old_value: Any
    new_value: Any
    old_date: date | None
    new_date: date | None
    old_capture_digest: str
    new_capture_digest: str


class ChangesResponse(_Model):
    """The ``/changes`` feed (§37.3, SIG-API-009): incremental follow, not re-download."""

    since: date | None
    events: list[ChangeEvent]
    coverage: CoverageStatement
    as_of: AsOfEcho


class ExportDescriptor(_Model):
    """One available bulk-export artifact descriptor.

    The read API only *lists* what P14.2 publishes; it computes no bulk artifact
    and no export licence here (that is P14.2 / SIG-EXPORT-*).
    """

    name: str
    format: str
    href: str
    description: str


class ExportIndexResponse(_Model):
    """The ``/export`` index (§37.3): descriptors of the bulk artifacts P14.2 builds."""

    exports: list[ExportDescriptor]
    note: str
    coverage: CoverageStatement
    as_of: AsOfEcho


class TermsResponse(_Model):
    """Acceptable-use terms with a stated remedy (SIG-API-013)."""

    version: str
    tiers: dict[str, str]
    prohibitions: list[str]
    remedy: str
    reidentification_prohibited: bool

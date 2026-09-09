# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The versioned ``/v1`` resource families (§37.3, SIG-API-007).

Every read endpoint here follows one shape: it takes the shared as-of dependency
(SIG-API-005), resolves material facts through the resolver so the value is always
enveloped (SIG-API-002), attaches a coverage statement (SIG-API-003) and — for
collections — a licence statement (SIG-API-004), echoes the as-of pair, and sets
the cache lifetime from whether the request was belief-pinned (SIG-API-006). The
resource families are exactly the §37.3 list; no prohibited surface (SIG-API-012)
is mounted (asserted structurally by :mod:`api.prohibitions`).
"""

from __future__ import annotations

from datetime import date

from evidence.tiers import StorageTier
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from policy.sensitivity import apply_tier, geo_tier_for, published_precision
from reconcile.resolve import RESOLVE
from reconcile.snapshot_diff import diff_series

from .asof import AsOfContext, as_of_dependency
from .envelope import (
    attribution_for,
    coverage_statement,
    empty_coverage,
    license_statement,
    material_fact,
)
from .models import (
    ChangeEvent,
    ChangesResponse,
    ClaimResponse,
    ContradictionCollection,
    ContradictionResponse,
    CoverageResponse,
    CrosswalkResponse,
    CrosswalkRow,
    DossierResponse,
    EntityRef,
    EntityResponse,
    EvidenceResponse,
    ExportDescriptor,
    ExportIndexResponse,
    GeoPoint,
    ResolutionResponse,
    SearchResponse,
    TaskCollection,
    TaskResponse,
)
from .prohibitions import ProhibitedEndpointError, assert_entity_type_allowed
from .store import ContradictionRecord, EntityRecord, ReadStore, TaskRecord
from .tiers import AccessTier, assert_public_visibility, tier_dependency


def get_store(request: Request) -> ReadStore:
    """Dependency: the read store the app was built with (SIG-API-001 seam)."""
    store: ReadStore = request.app.state.store
    return store


def build_router() -> APIRouter:
    """Assemble the ``/v1`` router with every §37.3 resource family."""
    router = APIRouter(prefix="/v1")

    # --- /resolution — the core material-fact endpoint (SIG-API-002) ----------
    @router.get("/resolution/{subject_id}/{predicate_id}", response_model=ResolutionResponse)
    def resolution(
        subject_id: str,
        predicate_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ResolutionResponse:
        claims = store.claims_for(subject_id, predicate_id, as_of_belief=asof.asof.belief)
        try:
            resolved = RESOLVE(
                subject_id,
                predicate_id,
                claims,
                as_of_world=asof.asof.world.date(),
                as_of_belief=asof.asof.belief.date(),
                ruleset=store.ruleset,
            )
        except KeyError as exc:
            # The predicate is not in the resolver's registry — an unknown
            # resource, not a bare-value leak. 404 rather than a fabricated value.
            raise HTTPException(
                status_code=404, detail=f"unknown predicate {predicate_id!r}"
            ) from exc
        rights = store.rights_for(tuple(sorted({c.source_id for c in claims if c.source_id})))
        cov = coverage_statement(
            f"{subject_id}:{predicate_id}", store.coverage_for(f"{subject_id}:{predicate_id}")
        )
        asof.apply_cache(response)
        return ResolutionResponse(
            fact=material_fact(resolved),
            coverage=cov,
            attribution=attribution_for(rights),
            as_of=asof.echo(),
        )

    # --- /entity --------------------------------------------------------------
    @router.get("/entity/{entity_type}/{entity_id}", response_model=EntityResponse)
    def entity(
        entity_type: str,
        entity_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> EntityResponse:
        # A per-person entity type is refused before any lookup (SIG-API-012).
        try:
            assert_entity_type_allowed(entity_type)
        except ProhibitedEndpointError as exc:
            raise HTTPException(status_code=404, detail="entity not found") from exc
        record = store.entity(entity_type, entity_id)
        if record is None:
            raise HTTPException(status_code=404, detail="entity not found")
        assert_public_visibility(record.visibility)
        facts = []
        for predicate_id in record.predicate_ids:
            claims = store.claims_for(entity_id, predicate_id, as_of_belief=asof.asof.belief)
            try:
                resolved = RESOLVE(
                    entity_id,
                    predicate_id,
                    claims,
                    as_of_world=asof.asof.world.date(),
                    as_of_belief=asof.asof.belief.date(),
                    ruleset=store.ruleset,
                )
            except KeyError as exc:
                raise HTTPException(
                    status_code=404, detail=f"unknown predicate {predicate_id!r}"
                ) from exc
            facts.append(material_fact(resolved))
        rights = store.rights_for(record.source_ids)
        asof.apply_cache(response)
        return EntityResponse(
            entity_id=record.entity_id,
            entity_type=record.entity_type,
            label=record.label,
            facts=facts,
            attribution=attribution_for(rights),
            location=_geo_point(record),
            coverage=coverage_statement(entity_id, store.coverage_for(entity_id)),
            as_of=asof.echo(),
        )

    # --- /claim (provenance, not a verdict) -----------------------------------
    @router.get("/claim/{claim_id}", response_model=ClaimResponse)
    def claim(
        claim_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ClaimResponse:
        stored = store.stored_claim(claim_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="claim not found")
        c = stored.claim
        asof.apply_cache(response)
        return ClaimResponse(
            claim_id=c.claim_id,
            subject_id=c.subject_id,
            predicate_id=c.predicate_id,
            value=c.value,
            raw_value=c.raw_value,
            observed_at=c.observed_at,
            source_id=c.source_id,
            genre=c.genre,
            review_status=c.review_status,
            evidence_capture_ids=list(stored.capture_ids),
            resolution_ref=f"/v1/resolution/{c.subject_id}/{c.predicate_id}",
            coverage=empty_coverage(f"claim:{claim_id}"),
            as_of=asof.echo(),
        )

    # --- /evidence — tier-gated; sealed bytes never returned (SIG-API-012) ----
    @router.get("/evidence/{artifact_id}/{capture_id}", response_model=EvidenceResponse)
    def evidence(
        artifact_id: str,
        capture_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> EvidenceResponse:
        from evidence.tiers import public_representation

        meta = store.capture(artifact_id, capture_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="capture not found")
        # public_representation IS the tier gate for a capture (SIG-EVID-009/010):
        # sealed → metadata only, no bytes; restricted → redacted excerpt. The
        # bytes are gated separately and never reach this surface (SIG-API-012).
        rep = public_representation(meta)
        asof.apply_cache(response)
        return EvidenceResponse(
            artifact_id=artifact_id,
            capture_id=capture_id,
            tier=meta.tier.value,
            bytes_available=bool(rep["bytes_available"]),
            representation=rep,
            coverage=empty_coverage(f"evidence:{artifact_id}/{capture_id}"),
            as_of=asof.echo(),
        )

    # --- /search (collection: licence + coverage) -----------------------------
    @router.get("/search", response_model=SearchResponse)
    def search(
        response: Response,
        q: str = "",
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> SearchResponse:
        hits = [e for e in store.search(q) if e.visibility is StorageTier.PUBLIC]
        source_ids: tuple[str, ...] = tuple(sorted({s for e in hits for s in e.source_ids}))
        asof.apply_cache(response)
        return SearchResponse(
            query=q,
            results=[
                EntityRef(
                    entity_id=e.entity_id,
                    entity_type=e.entity_type,
                    label=e.label,
                    href=f"/v1/entity/{e.entity_type}/{e.entity_id}",
                )
                for e in hits
            ],
            coverage=empty_coverage(f"search:{q}"),
            license=license_statement(store.rights_for(source_ids)),
            as_of=asof.echo(),
        )

    # --- /dossier (collection) ------------------------------------------------
    @router.get("/dossier/{scope}", response_model=DossierResponse)
    def dossier(
        scope: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> DossierResponse:
        record = store.dossier(scope)
        if record is None:
            raise HTTPException(status_code=404, detail="dossier not found")
        asof.apply_cache(response)
        return DossierResponse(
            scope=record.scope,
            title=record.title,
            sections=list(record.sections),
            coverage=coverage_statement(scope, store.coverage_for(scope)),
            license=license_statement(store.rights_for(record.source_ids)),
            as_of=asof.echo(),
        )

    # --- /coverage (the §32.2 metrics surface, SIG-API-003) -------------------
    @router.get("/coverage/{scope}", response_model=CoverageResponse)
    def coverage(
        scope: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> CoverageResponse:
        asof.apply_cache(response)
        return CoverageResponse(
            coverage=coverage_statement(scope, store.coverage_for(scope)),
            as_of=asof.echo(),
        )

    # --- /contradiction (always visible, §3.1) --------------------------------
    @router.get("/contradiction", response_model=ContradictionCollection)
    def contradictions(
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ContradictionCollection:
        asof.apply_cache(response)
        return ContradictionCollection(
            contradictions=[_contradiction(c, asof) for c in store.contradictions()],
            coverage=empty_coverage("contradiction"),
            as_of=asof.echo(),
        )

    @router.get("/contradiction/{contradiction_id}", response_model=ContradictionResponse)
    def contradiction(
        contradiction_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ContradictionResponse:
        record = store.contradiction(contradiction_id)
        if record is None:
            raise HTTPException(status_code=404, detail="contradiction not found")
        asof.apply_cache(response)
        return _contradiction(record, asof)

    # --- /task ----------------------------------------------------------------
    @router.get("/task", response_model=TaskCollection)
    def tasks(
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> TaskCollection:
        asof.apply_cache(response)
        return TaskCollection(
            tasks=[_task(t, asof) for t in store.tasks()],
            coverage=empty_coverage("task"),
            as_of=asof.echo(),
        )

    @router.get("/task/{task_id}", response_model=TaskResponse)
    def task(
        task_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> TaskResponse:
        record = store.task(task_id)
        if record is None:
            raise HTTPException(status_code=404, detail="task not found")
        asof.apply_cache(response)
        return _task(record, asof)

    # --- /crosswalk (collection) ----------------------------------------------
    @router.get("/crosswalk", response_model=CrosswalkResponse)
    def crosswalk(
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> CrosswalkResponse:
        rows = store.crosswalk_rows()
        asof.apply_cache(response)
        return CrosswalkResponse(
            rows=[
                CrosswalkRow(
                    sig_id=r.sig_id,
                    external_scheme=r.external_scheme,
                    external_id=r.external_id,
                    relation=r.relation,
                )
                for r in rows
            ],
            coverage=empty_coverage("crosswalk"),
            license=license_statement(store.rights_for(())),
            as_of=asof.echo(),
        )

    # --- /export (index only; P14.2 builds the bulk artifacts) ----------------
    @router.get("/export", response_model=ExportIndexResponse)
    def export_index(
        response: Response,
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ExportIndexResponse:
        asof.apply_cache(response)
        return ExportIndexResponse(
            exports=[
                ExportDescriptor(
                    name="entities",
                    format="parquet",
                    href="/exports/entities.parquet",
                    description="Bulk entity table (built and licensed by the P14.2 export layer).",
                ),
            ],
            note="This index lists bulk artifacts; the read API computes no bulk "
            "export or export licence here (P14.2 owns SIG-EXPORT-*).",
            coverage=empty_coverage("export"),
            as_of=asof.echo(),
        )

    # --- /changes — the snapshot-diff feed (§29.7, SIG-API-009) ---------------
    @router.get("/changes", response_model=ChangesResponse)
    def changes(
        response: Response,
        since: str | None = None,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ChangesResponse:
        try:
            since_date = date.fromisoformat(since) if since else None
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"invalid since parameter: {since!r} is not an ISO date"
            ) from exc
        events = diff_series(store.captures())
        selected = [e for e in events if since_date is None or e.new_date >= since_date]
        asof.apply_cache(response)
        return ChangesResponse(
            since=since_date,
            events=[
                ChangeEvent(
                    artifact_id=e.artifact_id,
                    field=e.field,
                    change_type=e.change_type,
                    old_value=e.old_value,
                    new_value=e.new_value,
                    old_date=e.old_date,
                    new_date=e.new_date,
                    old_capture_digest=e.old_capture_digest,
                    new_capture_digest=e.new_capture_digest,
                )
                for e in selected
            ],
            coverage=empty_coverage("changes"),
            as_of=asof.echo(),
        )

    return router


def _geo_point(record: EntityRecord) -> GeoPoint | None:
    """Reduce a stored coordinate to the entity's sensitivity tier (SIG-API-012, §19.4)."""
    if record.sensitivity_class is None or record.lat is None or record.lon is None:
        return None
    tier = geo_tier_for(record.sensitivity_class)
    reduced = apply_tier(record.lat, record.lon, tier)
    lat, lon = (None, None) if reduced is None else reduced
    return GeoPoint(
        lat=lat,
        lon=lon,
        sensitivity_class=record.sensitivity_class.value,
        precision=published_precision(record.sensitivity_class),
    )


def _contradiction(record: ContradictionRecord, asof: AsOfContext) -> ContradictionResponse:
    return ContradictionResponse(
        contradiction_id=record.contradiction_id,
        subject_id=record.subject_id,
        predicate_id=record.predicate_id,
        kind=record.kind,
        state=record.state,
        claim_ids=list(record.claim_ids),
        coverage=empty_coverage(f"contradiction:{record.contradiction_id}"),
        as_of=asof.echo(),
    )


def _task(record: TaskRecord, asof: AsOfContext) -> TaskResponse:
    return TaskResponse(
        task_id=record.task_id,
        kind=record.kind,
        status=record.status,
        subject_id=record.subject_id,
        predicate_id=record.predicate_id,
        rationale=record.rationale,
        coverage=empty_coverage(f"task:{record.task_id}"),
        as_of=asof.echo(),
    )

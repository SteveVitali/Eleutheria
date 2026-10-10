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

import re
from datetime import date
from typing import Any

from evidence.tiers import StorageTier
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from policy.sensitivity import apply_tier, geo_tier_for, published_precision
from reconcile.resolve import RESOLVE
from reconcile.snapshot_diff import diff_series

from .asof import AsOfContext, as_of_dependency
from .basis_middleware import BASIS_RELEASE
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
    PublicationTombstone,
    ResolutionResponse,
    SearchResponse,
    TaskCollection,
    TaskResponse,
)
from .prohibitions import ProhibitedEndpointError, assert_entity_type_allowed
from .release_serving import (
    ReleaseIdentity,
    ReleaseServingError,
    ReleaseServingStore,
)
from .store import (
    SEARCH_DEFAULT_LIMIT,
    SEARCH_MAX_LIMIT,
    SEARCH_MIN_QUERY_LENGTH,
    ContradictionRecord,
    EntityRecord,
    InvalidSearchCursor,
    ReadStore,
    StoreQueryTimeout,
    TaskRecord,
)
from .tiers import AccessTier, assert_public_visibility, tier_dependency


class ScopeNotAvailableError(Exception):
    """A dossier/coverage scope the store does not hold (P34.25).

    Mapped to a 404 with a typed body — ``{"detail": "scope not available",
    "code": "scope_not_available", "scope": scope}`` — by the handler
    :func:`api.app.create_app` installs. The API must never substitute an
    arbitrary sample for a scope it cannot answer (C3 NEW-1).
    """

    def __init__(self, scope: str) -> None:
        super().__init__(scope)
        self.scope = scope


#: The OpenAPI disclosure on every live-spine route (P35.57, SIG-REL-010): the
#: answer is computed from the current claim spine, not a promoted release.
LIVE_SPINE_DESCRIPTION = (
    "Live-spine read — answers from the current claim spine: newer than the site; not a citation."
)

#: The OpenAPI disclosure on the release-backed routes (P35.57, G3 §6.4): the
#: answer is the promoted release's own pinned bytes — the same answer the
#: site shows. ``?release=<publication_id>`` selects any promoted release.
RELEASE_BACKED_DESCRIPTION = (
    "Release-backed read — answers from the current promoted release's files, "
    "the same answer the site shows; ?release=<publication_id> selects any "
    "promoted release. Falls back to the live spine only when no release "
    "registry is configured on this service."
)


def _release_serving(request: Request) -> ReleaseServingStore | None:
    """The mounted release registry's serving store — ``None`` on a service
    with no release registry configured (the live-spine fallback)."""
    return getattr(request.app.state, "release_serving", None)


def _mark_release(request: Request, identity: ReleaseIdentity | None = None) -> None:
    """Mark this request's basis class as ``release`` — the basis middleware
    reads the mark (and the release block) from ``scope["state"]`` so every
    response, errors included, is labelled by the authority that answered."""
    state = request.scope.setdefault("state", {})
    state["sig_basis"] = BASIS_RELEASE
    if identity is not None:
        state["sig_release"] = identity.block()


def _release_payload(
    request: Request,
    family: str,
    name: str | None,
    release: str | None,
    *,
    absent_status: int,
    absent_code: str,
) -> dict[str, Any] | None:
    """Serve an api-slice document from the promoted release — ``None`` when
    no release registry is configured (the caller keeps its live-spine path)."""
    serving = _release_serving(request)
    if serving is None:
        return None
    _mark_release(request)
    payload, identity = serving.api_document(
        release, family, name, absent_status=absent_status, absent_code=absent_code
    )
    _mark_release(request, identity)
    return payload


def _release_document(
    request: Request,
    family: str,
    name: str | None,
    release: str | None,
    *,
    absent_status: int,
    absent_code: str,
) -> JSONResponse | None:
    payload = _release_payload(
        request,
        family,
        name,
        release,
        absent_status=absent_status,
        absent_code=absent_code,
    )
    return JSONResponse(payload) if payload is not None else None


def _require_release_serving(request: Request) -> ReleaseServingStore:
    serving = _release_serving(request)
    if serving is None:
        raise ReleaseServingError(
            503,
            "release_serving_unconfigured",
            "release-backed serving is not configured on this service",
        )
    return serving


#: A searchable term has a run of SEARCH_MIN_QUERY_LENGTH letters/digits (P31.1,
#: ADR-108): the shortest term the trigram index can serve.
_SEARCHABLE = re.compile(rf"[^\W_]{{{SEARCH_MIN_QUERY_LENGTH}}}")


def get_store(request: Request) -> ReadStore:
    """Dependency: the read store the app was built with (SIG-API-001 seam)."""
    store: ReadStore = request.app.state.store
    return store


def _tombstone(decision: Any) -> PublicationTombstone:
    """Render a store ``PublicationDecision`` as the API tombstone model (safe
    fields only — reason category + authority class + policy version)."""
    return PublicationTombstone(
        permitted=False,
        reason_category=decision.reason_category.value
        if getattr(decision, "reason_category", None) is not None
        else None,
        authority=getattr(decision, "authority", None),
        policy_version=decision.policy_version,
    )


def build_router() -> APIRouter:
    """Assemble the ``/v1`` router with every §37.3 resource family."""
    router = APIRouter(prefix="/v1")

    # --- /resolution — the core material-fact endpoint (SIG-API-002) ----------
    @router.get(
        "/resolution/{subject_id}/{predicate_id}",
        response_model=ResolutionResponse,
        description=LIVE_SPINE_DESCRIPTION,
    )
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
            f"{subject_id}:{predicate_id}",
            store.coverage_for(f"{subject_id}:{predicate_id}") or [],
        )
        asof.apply_cache(response)
        return ResolutionResponse(
            fact=material_fact(resolved),
            coverage=cov,
            attribution=attribution_for(rights),
            as_of=asof.echo(),
        )

    # --- /entity --------------------------------------------------------------
    @router.get(
        "/entity/{entity_type}/{entity_id}",
        response_model=EntityResponse,
        description=LIVE_SPINE_DESCRIPTION,
    )
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
        # P32.5/ADR-124 (SIG-TRUST-006): the shared eligibility selector withheld
        # this entity — serve the honest tombstone (id + type + safe reason)
        # with NO label, facts, sources or location.
        if record.publication is not None:
            asof.apply_cache(response)
            return EntityResponse(
                entity_id=record.entity_id,
                entity_type=record.entity_type,
                label=None,
                facts=[],
                attribution=[],
                location=None,
                coverage=coverage_statement(entity_id, store.coverage_for(entity_id) or []),
                as_of=asof.echo(),
                publication=_tombstone(record.publication),
            )
        facts = []
        unregistered: list[str] = []
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
            except KeyError:
                # P32.2 / D-P31.1-3 (SIG-TRUST-001): an unregistered predicate
                # must not make an otherwise valid entity disappear — serve the
                # registered facts and name the unresolved predicates
                # explicitly instead of a whole-entity 404.
                unregistered.append(predicate_id)
                continue
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
            coverage=coverage_statement(entity_id, store.coverage_for(entity_id) or []),
            as_of=asof.echo(),
            unregistered_predicates=unregistered,
        )

    # --- /claim (provenance, not a verdict) -----------------------------------
    @router.get(
        "/claim/{claim_id}", response_model=ClaimResponse, description=LIVE_SPINE_DESCRIPTION
    )
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
        rights = store.rights_for((c.source_id,) if c.source_id else ())
        asof.apply_cache(response)
        # P32.5/ADR-124 (SIG-TRUST-006): a claim withheld under current policy
        # answers with a truthful tombstone — value/raw_value/evidence links
        # nulled, the reason category + policy version stated.
        withheld = stored.publication is not None
        return ClaimResponse(
            claim_id=c.claim_id,
            subject_id=c.subject_id,
            predicate_id=c.predicate_id,
            value=None if withheld else c.value,
            raw_value=None if withheld else c.raw_value,
            observed_at=c.observed_at,
            source_id=c.source_id,
            attribution=attribution_for(rights),
            genre=c.genre,
            review_status=c.review_status,
            count_scope=c.count_scope,
            count_scope_detail=c.count_scope_detail,
            count_scope_jurisdiction=c.count_scope_jurisdiction,
            evidence_origin=c.evidence_origin,
            evidence_capture_ids=[] if withheld else list(stored.capture_ids),
            resolution_ref=f"/v1/resolution/{c.subject_id}/{c.predicate_id}",
            coverage=empty_coverage(f"claim:{claim_id}"),
            as_of=asof.echo(),
            publication=_tombstone(stored.publication) if withheld else None,
        )

    # --- /evidence — tier-gated; sealed bytes never returned (SIG-API-012) ----
    @router.get(
        "/evidence/{artifact_id}/{capture_id}",
        response_model=EvidenceResponse,
        description=LIVE_SPINE_DESCRIPTION,
    )
    def evidence(
        artifact_id: str,
        capture_id: str,
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> EvidenceResponse:
        from evidence.tiers import bytes_unavailable_reason, public_representation

        meta = store.capture(artifact_id, capture_id)
        if meta is None:
            raise HTTPException(status_code=404, detail="capture not found")
        # public_representation IS the tier gate for a capture (SIG-EVID-009/010):
        # sealed → metadata only, no bytes; restricted → redacted excerpt. The
        # bytes are gated separately and never reach this surface (SIG-API-012).
        # P34.25: bytes_available is claimed only where the bytes are public —
        # a public-tier capture not recorded byte-bearing does not claim it,
        # and the safe reason is disclosed.
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
            bytes_unavailable_reason=bytes_unavailable_reason(meta),
        )

    # --- /search (collection: licence + coverage) -----------------------------
    # Bounded (P31.1, ADR-108): a minimum query length, a capped page size, and
    # keyset pagination (``next_cursor``). The page is fetched one row long so
    # "is there more?" costs no count query.
    @router.get("/search", response_model=SearchResponse, description=LIVE_SPINE_DESCRIPTION)
    def search(
        response: Response,
        q: str = "",
        limit: int = Query(default=SEARCH_DEFAULT_LIMIT, ge=1, le=SEARCH_MAX_LIMIT),
        cursor: str | None = None,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> SearchResponse:
        term = q.strip()
        page: list[EntityRecord] = []
        if term:
            if not _SEARCHABLE.search(term):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"search query must contain at least {SEARCH_MIN_QUERY_LENGTH} "
                        "consecutive letters or digits; resolve an exact identifier "
                        "with /id/{type}/{id}"
                    ),
                )
            try:
                page = store.search(term, limit=limit + 1, after=cursor)
            except InvalidSearchCursor as exc:
                raise HTTPException(status_code=422, detail="invalid search cursor") from exc
            except StoreQueryTimeout as exc:
                raise HTTPException(
                    status_code=503,
                    detail="search exceeded its time budget; use a more specific query",
                ) from exc
        has_more = len(page) > limit
        page = page[:limit]
        next_cursor = page[-1].entity_id if has_more and page else None
        hits = [e for e in page if e.visibility is StorageTier.PUBLIC]
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
            limit=limit,
            next_cursor=next_cursor,
        )

    # --- /dossier (collection) — release-backed (P35.57, SIG-REL-010) ---------
    # The dossier answer the site shows is a release file; the API serves the
    # same pinned document (or ?release=<pub> for any promoted release). Only a
    # service with no release registry configured falls back to the live spine.
    @router.get(
        "/dossier/{scope}",
        response_model=DossierResponse,
        description=RELEASE_BACKED_DESCRIPTION,
    )
    def dossier(
        scope: str,
        request: Request,
        response: Response,
        release: str | None = Query(default=None),
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> Any:
        served = _release_document(
            request,
            "dossier",
            scope,
            release,
            absent_status=404,
            absent_code="scope_not_available",
        )
        if served is not None:
            return served
        record = store.dossier(scope)
        if record is None:
            # P34.25 (C3 NEW-1): an unheld scope is a typed 404, never an
            # arbitrary unrelated subject set.
            raise ScopeNotAvailableError(scope)
        asof.apply_cache(response)
        return DossierResponse(
            scope=record.scope,
            title=record.title,
            sections=list(record.sections),
            coverage=coverage_statement(scope, store.coverage_for(scope) or []),
            license=license_statement(store.rights_for(record.source_ids)),
            as_of=asof.echo(),
        )

    # --- /coverage (the §32.2 metrics surface) — release-backed (P35.57) ------
    @router.get(
        "/coverage/{scope}",
        response_model=CoverageResponse,
        description=RELEASE_BACKED_DESCRIPTION,
    )
    def coverage(
        scope: str,
        request: Request,
        response: Response,
        release: str | None = Query(default=None),
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> Any:
        served = _release_document(
            request,
            "coverage",
            scope,
            release,
            absent_status=404,
            absent_code="scope_not_available",
        )
        if served is not None:
            return served
        records = store.coverage_for(scope)
        if records is None:
            # P34.25 (C3 NEW-1): an unheld scope is a typed 404, never an
            # empty-but-"complete" statement.
            raise ScopeNotAvailableError(scope)
        asof.apply_cache(response)
        return CoverageResponse(
            coverage=coverage_statement(scope, records),
            as_of=asof.echo(),
        )

    # --- /contradiction (always visible, §3.1) --------------------------------
    @router.get(
        "/contradiction", response_model=ContradictionCollection, description=LIVE_SPINE_DESCRIPTION
    )
    def contradictions(
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> ContradictionCollection:
        records = store.contradictions()
        # Freshness is disclosed, not implied (§3.1): the served set states the
        # spine watermark it was computed at (P25.10).
        watermark = store.annotation_watermark()
        asof.apply_cache(response)
        return ContradictionCollection(
            contradictions=[_contradiction(c, asof, watermark) for c in records],
            coverage=empty_coverage("contradiction"),
            as_of=asof.echo(),
            spine_watermark=watermark,
        )

    @router.get(
        "/contradiction/{contradiction_id}",
        response_model=ContradictionResponse,
        description=LIVE_SPINE_DESCRIPTION,
    )
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
        return _contradiction(record, asof, store.annotation_watermark())

    # --- /task ----------------------------------------------------------------
    @router.get("/task", response_model=TaskCollection, description=LIVE_SPINE_DESCRIPTION)
    def tasks(
        response: Response,
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> TaskCollection:
        records = store.tasks()
        watermark = store.annotation_watermark()
        asof.apply_cache(response)
        return TaskCollection(
            tasks=[_task(t, asof, watermark) for t in records],
            coverage=empty_coverage("task"),
            as_of=asof.echo(),
            spine_watermark=watermark,
        )

    @router.get("/task/{task_id}", response_model=TaskResponse, description=LIVE_SPINE_DESCRIPTION)
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
        return _task(record, asof, store.annotation_watermark())

    # --- /crosswalk (collection) ----------------------------------------------
    @router.get("/crosswalk", response_model=CrosswalkResponse, description=LIVE_SPINE_DESCRIPTION)
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

    # --- /export (index) — release-backed (P35.57); P14.2 builds the bytes ----
    @router.get(
        "/export",
        response_model=ExportIndexResponse,
        description=RELEASE_BACKED_DESCRIPTION,
    )
    def export_index(
        request: Request,
        response: Response,
        release: str | None = Query(default=None),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> Any:
        served = _release_document(
            request,
            "export",
            None,
            release,
            absent_status=503,
            absent_code="release_artifact_absent",
        )
        if served is not None:
            return served
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

    # --- /changes — the change feed — release-backed (P35.57) ------------------
    @router.get(
        "/changes",
        response_model=ChangesResponse,
        description=RELEASE_BACKED_DESCRIPTION,
    )
    def changes(
        request: Request,
        response: Response,
        since: str | None = None,
        release: str | None = Query(default=None),
        store: ReadStore = Depends(get_store),
        asof: AsOfContext = Depends(as_of_dependency),
        tier: AccessTier = Depends(tier_dependency),
    ) -> Any:
        try:
            since_date = date.fromisoformat(since) if since else None
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"invalid since parameter: {since!r} is not an ISO date"
            ) from exc
        payload = _release_payload(
            request,
            "changes",
            None,
            release,
            absent_status=503,
            absent_code="release_artifact_absent",
        )
        if payload is not None:
            # The release document is a fixed snapshot; ``since`` filters its
            # events the same way the live feed filters the spine's.
            if since_date is not None and isinstance(payload.get("events"), list):
                payload = {
                    **payload,
                    "since": since_date.isoformat(),
                    "events": [
                        e
                        for e in payload["events"]
                        if isinstance(e, dict)
                        and e.get("new_date")
                        and str(e["new_date"]) >= since_date.isoformat()
                    ],
                }
            return JSONResponse(payload)
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

    # --- /sources — the transparency surface, release-backed (P35.57; the J3
    #     copy is P37.23/TX-15's — this row places the route family on the
    #     release-backed class only) -----------------------------------------
    @router.get("/sources", description=RELEASE_BACKED_DESCRIPTION)
    def sources_index(
        request: Request,
        release: str | None = Query(default=None),
        tier: AccessTier = Depends(tier_dependency),
    ) -> JSONResponse:
        payload = _release_payload(
            request,
            "sources",
            None,
            release,
            absent_status=503,
            absent_code="release_artifact_absent",
        )
        if payload is None:
            raise ReleaseServingError(
                503,
                "release_serving_unconfigured",
                "release-backed serving is not configured on this service",
            )
        return JSONResponse(payload)

    @router.get("/sources/{source_id}", description=RELEASE_BACKED_DESCRIPTION)
    def source(
        source_id: str,
        request: Request,
        release: str | None = Query(default=None),
        tier: AccessTier = Depends(tier_dependency),
    ) -> JSONResponse:
        payload = _release_payload(
            request,
            "sources",
            source_id,
            release,
            absent_status=404,
            absent_code="scope_not_available",
        )
        if payload is None:
            raise ReleaseServingError(
                503,
                "release_serving_unconfigured",
                "release-backed serving is not configured on this service",
            )
        return JSONResponse(payload)

    # --- /releases — the promoted-release registry routes (P35.57, G3 §6.4) --
    # The literal /latest must register before the {publication_id} parameter
    # route so "latest" resolves to the current pointer, never a pub lookup.
    @router.get("/releases", description=RELEASE_BACKED_DESCRIPTION)
    def releases_index(
        request: Request,
        tier: AccessTier = Depends(tier_dependency),
    ) -> JSONResponse:
        serving = _require_release_serving(request)
        _mark_release(request)
        payload, identity = serving.releases_index()
        _mark_release(request, identity)
        return JSONResponse(payload)

    @router.get("/releases/latest", description=RELEASE_BACKED_DESCRIPTION)
    def releases_latest(
        request: Request,
        tier: AccessTier = Depends(tier_dependency),
    ) -> JSONResponse:
        serving = _require_release_serving(request)
        _mark_release(request)
        payload, identity = serving.latest_document()
        _mark_release(request, identity)
        return JSONResponse(payload)

    @router.get("/releases/{publication_id}", description=RELEASE_BACKED_DESCRIPTION)
    def releases_show(
        publication_id: str,
        request: Request,
        tier: AccessTier = Depends(tier_dependency),
    ) -> JSONResponse:
        serving = _require_release_serving(request)
        _mark_release(request)
        payload, identity = serving.release_document(publication_id)
        _mark_release(request, identity)
        return JSONResponse(payload)

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


def _contradiction(
    record: ContradictionRecord, asof: AsOfContext, watermark: str | None
) -> ContradictionResponse:
    return ContradictionResponse(
        contradiction_id=record.contradiction_id,
        subject_id=record.subject_id,
        predicate_id=record.predicate_id,
        kind=record.kind,
        state=record.state,
        claim_ids=list(record.claim_ids),
        coverage=empty_coverage(f"contradiction:{record.contradiction_id}"),
        as_of=asof.echo(),
        spine_watermark=watermark,
    )


def _task(record: TaskRecord, asof: AsOfContext, watermark: str | None) -> TaskResponse:
    return TaskResponse(
        task_id=record.task_id,
        kind=record.kind,
        status=record.status,
        subject_id=record.subject_id,
        predicate_id=record.predicate_id,
        rationale=record.rationale,
        coverage=empty_coverage(f"task:{record.task_id}"),
        as_of=asof.echo(),
        spine_watermark=watermark,
    )

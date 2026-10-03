# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The FastAPI application factory for the public read API (§37, SIG-API-001).

:func:`create_app` builds the *hand-written, versioned* app: a ``/v1`` router of
the §37.3 resource families, the ``/id/{type}/{uuid}`` dereference surface with
content negotiation (SIG-API-008), and the ``/terms`` acceptable-use document
(SIG-API-013). Construction fails closed if any prohibited surface (SIG-API-012)
is mounted — the bar is checked structurally at build time, not left to review.
OpenAPI is generated from the hand-written routes/models, never reflected from
storage, and the contract is versioned via the ``/v1`` prefix and the app version.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from . import __version__
from .dereference import (
    HTML_MEDIA_TYPE,
    JSONLD_MEDIA_TYPE,
    TURTLE_MEDIA_TYPE,
    render_html,
    render_jsonld,
    render_turtle,
    select_media_type,
)
from .models import HealthResponse, TermsResponse
from .prohibitions import assert_no_prohibited_routes, route_paths
from .release_search import KNOWN_PARAMS, ReleaseSearchStore, render_search_html
from .routes import build_router, get_store
from .store import ReadStore, StoreUnavailable
from .terms import acceptable_use_terms

#: The wire-contract API version (SIG-API-001: the contract is versioned). Bumped
#: only on a breaking change; the URL is additionally versioned via ``/v1``.
API_VERSION = "1.0.0"


def create_app(store: ReadStore, release_search: ReleaseSearchStore | None = None) -> FastAPI:
    """Build the read-API app over ``store`` (SIG-API-001).

    Raises :class:`api.prohibitions.ProhibitedEndpointError` at construction if a
    SIG-API-012 forbidden surface is ever mounted — the app cannot be built in a
    prohibited state.
    """
    app = FastAPI(
        title="SIG public read API",
        version=API_VERSION,
        description=(
            "The hand-written, versioned §37 read contract. Every material fact "
            "carries its full resolution envelope (SIG-API-002); every response "
            "echoes the as-of pair it used (SIG-API-005)."
        ),
    )
    app.state.store = store
    app.state.release_search = release_search
    app.include_router(build_router())

    # --- /v1/releases/{pub}/compartments/{comp}/search -------------------------
    # P32.14 (SIG-FIND-003, ADR-133): released-corpus search over the verified
    # immutable per-compartment FTS5 index. JSON by default; a browser GET (or
    # format=html) selects the complete no-JS representation. No current-only
    # PG fallback exists beneath released pages — cold/missing indexes answer
    # an explicit 503, withdrawn namespaces 410.
    from exports.search_index import SearchIndexError, parse_params

    @app.get("/v1/releases/{publication_id}/compartments/{compartment}/search")
    def released_search(
        request: Request,
        publication_id: str,
        compartment: str,
        q: str | None = Query(default=None),
        kind: str | None = Query(default=None),
        jurisdiction: str | None = Query(default=None),
        source: str | None = Query(default=None),
        location: str | None = Query(default=None),
        technology: str | None = Query(default=None),
        # `limit` is bounded inside parse_params so every rejection shares
        # the same explicit {detail, code} error shape.
        limit: int | None = Query(default=None),
        cursor: str | None = Query(default=None),
        format: str | None = Query(default=None),
        accept: str | None = Header(default=None),
    ) -> Response:
        rstore: ReleaseSearchStore | None = request.app.state.release_search
        if rstore is None:
            raise SearchIndexError(
                503,
                "release_search_unconfigured",
                "released-corpus search is not configured on this service",
            )
        unknown = sorted(set(request.query_params.keys()) - KNOWN_PARAMS)
        params = parse_params(
            q=q,
            kind=kind,
            jurisdiction=jurisdiction,
            source=source,
            location=location,
            technology=technology,
            limit=limit,
            cursor=cursor,
            extra=unknown,
        )
        result = rstore.search(publication_id, compartment, params)
        wants_html = format == "html" or (format is None and "text/html" in (accept or ""))
        if wants_html:
            return HTMLResponse(
                render_search_html(rstore, publication_id, compartment, params, result)
            )
        return JSONResponse(result)

    @app.exception_handler(SearchIndexError)
    def _search_index_error(_request: Request, exc: SearchIndexError) -> JSONResponse:
        headers = {"Retry-After": "5"} if exc.status == 503 else None
        return JSONResponse(
            status_code=exc.status,
            content={"detail": exc.detail, "code": exc.code, **exc.extra},
            headers=headers,
        )

    # --- /id/{type}/{uuid} — dereferenceable identifiers (SIG-API-008) --------
    @app.get("/id/{id_type}/{uuid}")
    def dereference(
        id_type: str,
        uuid: str,
        accept: str | None = Header(default=None),
        store: ReadStore = Depends(get_store),
    ) -> Response:
        descriptor = store.resolve_id(id_type, uuid)
        if descriptor is None:
            raise HTTPException(status_code=404, detail="unknown identifier")
        media_type = select_media_type(accept)
        if media_type == JSONLD_MEDIA_TYPE:
            return Response(render_jsonld(descriptor), media_type=JSONLD_MEDIA_TYPE)
        if media_type == TURTLE_MEDIA_TYPE:
            return PlainTextResponse(render_turtle(descriptor), media_type=TURTLE_MEDIA_TYPE)
        return HTMLResponse(render_html(descriptor), media_type=HTML_MEDIA_TYPE)

    # --- /terms — acceptable-use with a stated remedy (SIG-API-013) -----------
    @app.get("/terms", response_model=TermsResponse)
    def terms() -> TermsResponse:
        return acceptable_use_terms()

    # --- /health — store readiness (P31.1) -------------------------------------
    # Not under /v1 and not an as-of envelope: it describes this process and its
    # database connection, never a device (SIG-API-012 governs device liveness).
    # `/healthz` is avoided on purpose: Cloud Run reserves some paths ending in
    # `z`, so a `/healthz` route would never reach the container (ADR-108).
    @app.get("/health", response_model=HealthResponse)
    def health(response: Response, store: ReadStore = Depends(get_store)) -> HealthResponse:
        state = store.health()
        response.headers["Cache-Control"] = "no-store"
        if not state.ok:
            response.status_code = 503
        return HealthResponse(
            status="ok" if state.ok else "unavailable",
            backend=state.backend,
            detail=state.detail,
            pool=state.pool,
        )

    # A store that cannot answer (DB restarting, pool exhausted) is a 503 with a
    # retry hint, never a 500 (P31.1, D-P30.4-1).
    @app.exception_handler(StoreUnavailable)
    def _store_unavailable(_request: Request, exc: StoreUnavailable) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"detail": "the read store is temporarily unavailable; retry shortly"},
            headers={"Retry-After": "5"},
        )

    # --- / — a minimal service descriptor -------------------------------------
    @app.get("/")
    def root() -> dict[str, object]:
        return {
            "service": "SIG public read API",
            "api_version": API_VERSION,
            "package_version": __version__,
            "versioned_base": "/v1",
            "openapi": "/openapi.json",
            "terms": "/terms",
            "health": "/health",
        }

    # Fail closed: no prohibited surface may be mounted (SIG-API-012).
    paths = route_paths([r for r in app.routes if isinstance(r, Route)])
    assert_no_prohibited_routes(paths)
    return app

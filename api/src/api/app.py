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

import os
import re

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response
from starlette.routing import Route

from . import __version__
from .alias_middleware import IdentifierAliasMiddleware
from .basis_middleware import BasisLabelMiddleware
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
from .release_serving import (
    PUBLICATION_RE,
    ReleaseServingError,
    ReleaseServingStore,
)
from .routes import ScopeNotAvailableError, build_router, get_store
from .store import ReadStore, StoreUnavailable
from .terms import acceptable_use_terms

#: The wire-contract API version (SIG-API-001: the contract is versioned). Bumped
#: only on a breaking change; the URL is additionally versioned via ``/v1``.
API_VERSION = "1.0.0"


def _release_block(request: Request) -> dict[str, str] | None:
    """The promoted release this service serves — ``{label, publication_id,
    as_of_world}`` from the mounted registry, or the ``release_id`` pin when no
    registry is mounted. ``None`` answers "not pinned", never a fabricated id."""
    serving: ReleaseServingStore | None = getattr(request.app.state, "release_serving", None)
    if serving is not None:
        ident = serving.current_identity()
        if ident is not None:
            return ident.block()
    release_id = getattr(request.app.state, "basis_release_id", None)
    if release_id:
        if PUBLICATION_RE.match(release_id):
            return {"publication_id": release_id}
        return {"label": release_id}
    return None


def create_app(
    store: ReadStore,
    release_search: ReleaseSearchStore | None = None,
    *,
    release_id: str | None = None,
    release_serving: ReleaseServingStore | None = None,
) -> FastAPI:
    """Build the read-API app over ``store`` (SIG-API-001).

    Raises :class:`api.prohibitions.ProhibitedEndpointError` at construction if a
    SIG-API-012 forbidden surface is ever mounted — the app cannot be built in a
    prohibited state.

    ``release_id`` is the promoted release this service is pinned to, where one
    exists — the live-spine basis label discloses it on every response (P34.25,
    A-20=a). ``None`` answers "not pinned", never a fabricated id.

    ``release_serving`` is the promoted-release file server (P35.57,
    SIG-REL-010): when present, the release-backed routes
    (``/v1/dossier/{scope}``, ``/v1/coverage/{scope}``, ``/v1/export``,
    ``/v1/changes``, ``/v1/sources…``, ``/v1/releases/**``) answer from release
    files, not the spine. It defaults to the ``release_search`` registry —
    one mounted registry backs both surfaces.
    """
    if release_serving is None and release_search is not None:
        release_serving = ReleaseServingStore(release_search.registry_root)
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
    app.state.release_serving = release_serving
    app.state.basis_release_id = release_id
    app.include_router(build_router())

    # --- /v1/releases/{pub}/compartments/{comp}/search -------------------------
    # P32.14 (SIG-FIND-003, ADR-133): released-corpus search over the verified
    # immutable per-compartment FTS5 index. JSON by default; a browser GET (or
    # format=html) selects the complete no-JS representation — for results AND
    # for every error state (C4 NEW-13 / DR-C4-10, P34.36). No current-only
    # PG fallback exists beneath released pages — cold/missing indexes answer
    # an explicit 503, withdrawn namespaces 410.
    from exports.search_index import SearchIndexError, parse_params

    from . import release_search as rs
    from .basis_middleware import BASIS_RELEASE

    def _mark_release_basis(request: Request, publication_id: str | None = None) -> None:
        """Mark a release-namespaced route's basis class (P35.57, SIG-REL-010)
        — ``/v1/releases/**`` answers release-pinned bytes, never the spine.
        The release block is resolved from the serving registry when it can be
        (the id itself when it is well-formed but unpromoted — the search
        store may still serve its staged index)."""
        state = request.scope.setdefault("state", {})
        state["sig_basis"] = BASIS_RELEASE
        if not publication_id or not PUBLICATION_RE.match(publication_id):
            return
        serving: ReleaseServingStore | None = getattr(request.app.state, "release_serving", None)
        block: dict[str, str] = {"publication_id": publication_id}
        if serving is not None:
            try:
                block = serving.identity(publication_id).block()
            except ReleaseServingError:
                pass  # staged-but-unpromoted still names its own id
        state["sig_release"] = block

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
        # P35.57: release-pinned FTS5 bytes are a release-basis answer — mark
        # before any refusal so errors carry the class that answered.
        _mark_release_basis(request, publication_id)
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
        if rs.wants_html(request):
            return HTMLResponse(
                render_search_html(rstore, publication_id, compartment, params, result)
            )
        return JSONResponse(result)

    def _html_search_error(request: Request, exc: SearchIndexError) -> HTMLResponse:
        """The no-JS error page — status + Retry-After semantics preserved."""
        headers = {"Retry-After": "5"} if exc.status == 503 else None
        pub = str(request.path_params.get("publication_id") or "")
        comp = str(request.path_params.get("compartment") or "")
        return HTMLResponse(
            rs.render_search_error_html(pub, comp, exc),
            status_code=exc.status,
            headers=headers,
        )

    @app.exception_handler(SearchIndexError)
    def _search_index_error(request: Request, exc: SearchIndexError) -> Response:
        # The SearchIndexError surface is the release-namespaced search route —
        # its refusals are release-basis answers too.
        _mark_release_basis(request, str(request.path_params.get("publication_id") or ""))
        if rs.wants_html(request):
            return _html_search_error(request, exc)
        headers = {"Retry-After": "5"} if exc.status == 503 else None
        return JSONResponse(
            status_code=exc.status,
            content={"detail": exc.detail, "code": exc.code, **exc.extra},
            headers=headers,
        )

    # Params that fail FastAPI parsing (e.g. ``limit=abc``) raise
    # RequestValidationError before the handler runs — an HTML client on the
    # search route still gets an HTML 422; every other route delegates to the
    # framework's default unchanged (DR-C4-10).
    _search_route_re = re.compile(r"^/v1/releases/[^/]+/compartments/[^/]+/search/?$")

    @app.exception_handler(RequestValidationError)
    async def _request_validation_error(request: Request, exc: RequestValidationError) -> Response:
        if _search_route_re.match(request.url.path):
            # Parsing failed before the handler could mark the basis — a 422
            # on this route is still a release-basis refusal (P35.57).
            _mark_release_basis(request, str(request.path_params.get("publication_id") or ""))
        if _search_route_re.match(request.url.path) and rs.wants_html(request):
            fields = sorted({str(err.get("loc", ("?",))[-1]) for err in exc.errors()})
            err = SearchIndexError(
                422,
                "invalid_search_parameters",
                "invalid search parameters: " + (", ".join(fields) or "request"),
            )
            return _html_search_error(request, err)
        return await request_validation_exception_handler(request, exc)

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
    def health(
        request: Request,
        response: Response,
        store: ReadStore = Depends(get_store),
    ) -> HealthResponse:
        state = store.health()
        response.headers["Cache-Control"] = "no-store"
        if not state.ok:
            response.status_code = 503
        # P35.57 / SIG-REL-010: the service names the promoted release it
        # serves (``release``), the code commit (``SIG_CODE_COMMIT``) and the
        # image digest (``SIG_IMAGE_DIGEST``), both set at deploy — None means
        # not pinned, never a fabricated value.
        return HealthResponse(
            status="ok" if state.ok else "unavailable",
            backend=state.backend,
            detail=state.detail,
            pool=state.pool,
            release=_release_block(request),
            code_commit=os.environ.get("SIG_CODE_COMMIT") or None,
            image=os.environ.get("SIG_IMAGE_DIGEST") or None,
        )

    # A scope the store does not hold is a typed 404 (P34.25, C3 NEW-1) — never
    # a substituted sample. The same {detail, code, **extra} error shape as
    # SearchIndexError.
    @app.exception_handler(ScopeNotAvailableError)
    def _scope_not_available(_request: Request, exc: ScopeNotAvailableError) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content={
                "detail": "scope not available",
                "code": "scope_not_available",
                "scope": exc.scope,
            },
        )

    # Release-serving refusals carry the same typed {detail, code, **extra}
    # shape as SearchIndexError (P35.57 / SIG-REL-010); the basis middleware
    # still stamps the release class — the request was already marked by the
    # release-backed route before it refused.
    @app.exception_handler(ReleaseServingError)
    def _release_serving_error(_request: Request, exc: ReleaseServingError) -> JSONResponse:
        headers = {"Retry-After": "5"} if exc.status == 503 else None
        return JSONResponse(
            status_code=exc.status,
            content={"detail": exc.detail, "code": exc.code, **exc.extra},
            headers=headers,
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
    def root(request: Request) -> dict[str, object]:
        # P35.57 / SIG-REL-010: names the promoted release, the code commit and
        # the image digest (None = not pinned, never fabricated).
        return {
            "service": "SIG public read API",
            "api_version": API_VERSION,
            "package_version": __version__,
            "versioned_base": "/v1",
            "openapi": "/openapi.json",
            "terms": "/terms",
            "health": "/health",
            "release": _release_block(request),
            "code_commit": os.environ.get("SIG_CODE_COMMIT") or None,
            "image": os.environ.get("SIG_IMAGE_DIGEST") or None,
        }

    # Fail closed: no prohibited surface may be mounted (SIG-API-012).
    paths = route_paths([r for r in app.routes if isinstance(r, Route)])
    assert_no_prohibited_routes(paths)
    # P34.18 / ADR-178 (S0 RI-01): every JSON/JSON-LD/HTML/Turtle response body
    # passes the keyed-digest alias projection — retired identifiers resolve or
    # redact at the response boundary so nothing publicly renderable repeats a
    # handle. Output-side only; recorded ids still query.
    app.add_middleware(IdentifierAliasMiddleware)
    # P34.25 / A-20=a (SIG-REL-010): the outermost wrapper stamps the
    # ``live-spine`` basis label — an X-SIG-Basis header on EVERY response and
    # a ``basis`` field on every JSON object body (errors included). Added last
    # so the label survives the alias projection and every error handler.
    app.add_middleware(BasisLabelMiddleware)
    return app

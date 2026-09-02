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

from fastapi import Depends, FastAPI, Header, HTTPException
from starlette.responses import HTMLResponse, PlainTextResponse, Response
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
from .models import TermsResponse
from .prohibitions import assert_no_prohibited_routes, route_paths
from .routes import build_router, get_store
from .store import ReadStore
from .terms import acceptable_use_terms

#: The wire-contract API version (SIG-API-001: the contract is versioned). Bumped
#: only on a breaking change; the URL is additionally versioned via ``/v1``.
API_VERSION = "1.0.0"


def create_app(store: ReadStore) -> FastAPI:
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
    app.include_router(build_router())

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
        }

    # Fail closed: no prohibited surface may be mounted (SIG-API-012).
    paths = route_paths([r for r in app.routes if isinstance(r, Route)])
    assert_no_prohibited_routes(paths)
    return app

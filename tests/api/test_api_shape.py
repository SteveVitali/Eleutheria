# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-API-001/007 — a hand-written, versioned REST contract with OpenAPI.

The contract is versioned (a ``/v1`` prefix and an explicit app version), OpenAPI
is generated from the hand-written routes/models, and every §37.3 resource family
is present.
"""

from __future__ import annotations

from api.app import API_VERSION
from starlette.testclient import TestClient

# The §37.3 resource families, as (method-agnostic) path fragments.
_FAMILY_PATHS = [
    "/v1/entity/{entity_type}/{entity_id}",
    "/v1/claim/{claim_id}",
    "/v1/resolution/{subject_id}/{predicate_id}",
    "/v1/evidence/{artifact_id}/{capture_id}",
    "/v1/dossier/{scope}",
    "/v1/search",
    "/v1/task",
    "/v1/coverage/{scope}",
    "/v1/contradiction",
    "/v1/crosswalk",
    "/v1/export",
    "/v1/changes",
]


def _paths(client: TestClient) -> set[str]:
    return set(client.get("/openapi.json").json()["paths"].keys())


def test_openapi_is_generated_and_versioned(client: TestClient) -> None:
    doc = client.get("/openapi.json").json()
    assert doc["openapi"].startswith("3.")
    assert doc["info"]["version"] == API_VERSION


def test_every_section_37_3_resource_family_is_present(client: TestClient) -> None:
    paths = _paths(client)
    for family in _FAMILY_PATHS:
        assert family in paths, f"missing §37.3 resource family {family!r} (SIG-API-007)"


def test_the_contract_is_url_versioned(client: TestClient) -> None:
    # Every resource-family route lives under the versioned prefix.
    families = [p for p in _paths(client) if p.startswith("/v1/")]
    assert families
    # The dereference + terms surfaces are intentionally unversioned cool-URIs.
    assert "/id/{id_type}/{uuid}" in _paths(client)
    assert "/terms" in _paths(client)


def test_root_descriptor_advertises_the_versioned_base_and_openapi(client: TestClient) -> None:
    body = client.get("/").json()
    assert body["versioned_base"] == "/v1"
    assert body["openapi"] == "/openapi.json"
    assert body["api_version"] == API_VERSION


def test_response_models_are_hand_written_pydantic_not_reflected(client: TestClient) -> None:
    """SIG-API-001: schemas come from our hand-written models, not DB reflection.

    The OpenAPI components include our named response models — evidence the wire
    shape is authored, not derived from a storage schema.
    """
    schemas = client.get("/openapi.json").json()["components"]["schemas"]
    for name in ("ResolutionResponse", "ResolutionEnvelope", "CoverageStatement", "AsOfEcho"):
        assert name in schemas

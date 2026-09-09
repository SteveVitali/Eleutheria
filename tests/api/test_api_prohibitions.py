# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""AC4 — no prohibited endpoint exists (SIG-API-012, Part VIII).

The API MUST NOT expose a device-liveness signal, a per-person lookup, sealed
capture bytes, or over-precise coordinates. The bar is enforced structurally
(no such route is mounted) and behaviourally (sealed bytes withheld; coordinates
reduced to the sensitivity tier).
"""

from __future__ import annotations

import pytest
from api.demo import build_demo_store
from api.prohibitions import (
    ProhibitedEndpointError,
    assert_no_prohibited_routes,
    check_path,
    route_paths,
)
from fastapi import FastAPI
from starlette.routing import Route
from starlette.testclient import TestClient

from api import create_app


def test_no_mounted_route_is_a_prohibited_surface(client: TestClient) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    paths = route_paths([r for r in app.routes if isinstance(r, Route)])
    # Must not raise: construction already asserts this, re-checked explicitly here.
    assert_no_prohibited_routes(paths)
    for path in paths:
        assert check_path(path) is None, f"{path} is a prohibited surface (SIG-API-012)"


@pytest.mark.parametrize(
    "path",
    [
        "/v1/device/live",
        "/v1/person/{name}",
        "/v1/plate/{plate}",
        "/v1/evidence/{a}/{c}/sealed-bytes",
        "/v1/asset/{id}/precise-location",
        "/v1/track/{id}",
    ],
)
def test_known_forbidden_paths_are_recognised(path: str) -> None:
    assert check_path(path) is not None


def test_building_an_app_with_a_prohibited_route_fails_closed() -> None:
    app = create_app(build_demo_store())

    @app.get("/v1/device/{id}/liveness")
    def _live(id: str) -> dict[str, str]:  # pragma: no cover - must never be reachable
        return {"id": id}

    paths = route_paths([r for r in app.routes if isinstance(r, Route)])
    with pytest.raises(ProhibitedEndpointError, match="device-liveness"):
        assert_no_prohibited_routes(paths)


def test_sealed_capture_never_returns_its_bytes(client: TestClient) -> None:
    body = client.get("/v1/evidence/art:contract/cap:sealed:1").json()
    assert body["tier"] == "sealed"
    assert body["bytes_available"] is False
    rep = body["representation"]
    # Metadata only: existence, source, date, digest, claims — never excerpt/title.
    assert "excerpt" not in rep and "title" not in rep
    assert rep["exists"] is True


def test_restricted_capture_metadata_is_served_with_a_redacted_excerpt(
    client: TestClient,
) -> None:
    """A restricted capture exposes metadata with a redacted excerpt and no bytes —
    the designed public representation (SIG-EVID-009/010), never the raw content."""
    body = client.get("/v1/evidence/art:contract/cap:restricted:1").json()
    assert body["tier"] == "restricted"
    assert body["bytes_available"] is False
    assert body["representation"]["excerpt"] == "[redacted]"


def test_a_person_entity_type_is_refused_by_the_generic_entity_route(
    client: TestClient,
) -> None:
    """SIG-API-012: the generic /entity route cannot become a per-person lookup."""
    for entity_type in ("person", "individual", "citizen", "human"):
        assert client.get(f"/v1/entity/{entity_type}/anyone").status_code == 404


def test_coordinates_are_reduced_to_the_sensitivity_tier(client: TestClient) -> None:
    # C2 (geo tier 1): truncated toward zero to 2 decimal places — never the stored
    # rooftop fix (35.4676234, -97.5164276).
    c2 = client.get("/v1/entity/asset/asset:c2").json()["location"]
    assert c2["lat"] == 35.46 and c2["lon"] == -97.51
    assert c2["sensitivity_class"] == "C2"

    # C4 (geo tier 3): no coordinates published at all, jurisdiction only.
    c4 = client.get("/v1/entity/asset/asset:c4").json()["location"]
    assert c4["lat"] is None and c4["lon"] is None
    assert c4["sensitivity_class"] == "C4"

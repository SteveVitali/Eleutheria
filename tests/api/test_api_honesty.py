# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.25 (S0 RI-02) — the public API only answers what it can answer.

* ``/v1/dossier/{scope}`` and ``/v1/coverage/{scope}`` return a **typed 404**
  (``scope_not_available``) for a scope the store does not hold — never the
  pre-P34.25 arbitrary 25-subject sample or an empty-but-``complete``
  statement (C3 NEW-1 / C3 NEW-10).
* ``bytes_available`` is claimed only where the bytes are public: a
  public-tier ``actual`` capture claims it; every other tier/classification
  answers ``False`` with a safe machine-readable reason.
* ``/terms`` names no board and no counsel (E2 H-5) while the
  re-identification prohibition and an explicit remedy still stand
  (SIG-API-013).
* Every response carries the ``live-spine`` basis label — the
  ``X-SIG-Basis`` header plus the ``basis`` body field — including error
  bodies (A-20=a / SIG-REL-010).
"""

from __future__ import annotations

import dataclasses
import json

from api.store import EntityRecord, InMemoryStore
from evidence.redaction import RedactionDerivative
from evidence.tiers import CaptureMetadata, StorageTier
from starlette.testclient import TestClient

from api import create_app

# --- scope honesty: typed 404, never a substituted answer ---------------------


def test_dossier_unknown_scope_is_a_typed_404_not_a_sample(client: TestClient) -> None:
    """C3 NEW-1: an unheld dossier scope must not return the arbitrary
    25-subject sample the pre-P34.25 fallback served."""
    resp = client.get("/v1/dossier/jurisdiction:nowhere-held")
    assert resp.status_code == 404
    body = resp.json()
    assert body["detail"] == "scope not available"
    assert body["code"] == "scope_not_available"
    assert body["scope"] == "jurisdiction:nowhere-held"
    # The typed error carries no subjects/sections — nothing substituted.
    assert "sections" not in body and "subjects" not in body


def test_dossier_held_scope_still_answers(client: TestClient) -> None:
    resp = client.get("/v1/dossier/jurisdiction:okc")
    assert resp.status_code == 200
    assert resp.json()["scope"] == "jurisdiction:okc"


def test_coverage_unknown_scope_is_a_typed_404(client: TestClient) -> None:
    resp = client.get("/v1/coverage/agency:nowhere-held")
    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "scope_not_available"
    assert body["scope"] == "agency:nowhere-held"


def test_coverage_held_scope_never_says_complete_with_nothing_evaluated() -> None:
    """C3 NEW-10: a held scope with zero records is "not evaluated" —
    never ``complete: true``."""
    store = InMemoryStore()
    store.add_entity(EntityRecord(entity_id="agency:quiet", entity_type="agency", label="quiet"))
    store.add_coverage("agency:quiet", [])  # held, but nothing evaluated
    client = TestClient(create_app(store))
    resp = client.get("/v1/coverage/agency:quiet")
    assert resp.status_code == 200
    cov = resp.json()["coverage"]
    assert cov["complete"] is False
    assert cov["evaluated"] == 0
    assert cov["records"] == []


def test_coverage_with_an_evaluated_record_can_be_complete(client: TestClient) -> None:
    cov = client.get("/v1/coverage/agency:okcpd:active_device_count").json()["coverage"]
    assert cov["evaluated"] == 1 and cov["not_evaluable"] == 0
    assert cov["complete"] is True


# --- honest byte availability ---------------------------------------------------


def _evidence_client(meta: CaptureMetadata, *, artifact_id: str = "art:x") -> TestClient:
    store = InMemoryStore()
    store.add_capture(meta, artifact_id=artifact_id)
    return TestClient(create_app(store))


def _meta(tier: StorageTier, classification: str | None) -> CaptureMetadata:
    return CaptureMetadata(
        capture_id="cap:x",
        source_id="src:x",
        source_uri="https://example/x",
        retrieved_at="2026-07-01T12:30:05Z",
        content_digest="d" + "0" * 40,
        media_type="application/pdf",
        tier=tier,
        capture_classification=classification,
    )


def test_bytes_available_only_for_public_byte_bearing_captures() -> None:
    ok = _evidence_client(_meta(StorageTier.PUBLIC, "actual")).get("/v1/evidence/art:x/cap:x")
    assert ok.status_code == 200
    assert ok.json()["bytes_available"] is True
    assert ok.json()["bytes_unavailable_reason"] is None
    assert ok.json()["representation"]["bytes_available"] is True


def test_public_but_not_proven_byte_bearing_never_claims_bytes() -> None:
    for cls in ("synthetic", "legacy", None):
        body = (
            _evidence_client(_meta(StorageTier.PUBLIC, cls)).get("/v1/evidence/art:x/cap:x").json()
        )
        assert body["bytes_available"] is False, cls
        assert body["bytes_unavailable_reason"] == f"classification:{cls or 'unclassified'}"
        assert body["representation"]["bytes_available"] is False


def test_non_public_tiers_never_claim_bytes() -> None:
    for tier in (StorageTier.RESTRICTED, StorageTier.SEALED):
        body = _evidence_client(_meta(tier, "actual")).get("/v1/evidence/art:x/cap:x").json()
        assert body["bytes_available"] is False
        assert body["bytes_unavailable_reason"] == f"tier:{tier.value}"


def test_source_uri_publishes_only_for_a_public_tier_capture() -> None:
    """P35.31 (F-400 / SIG-TRANSP-020): the upstream URI is a public-tier fact —
    a restricted or sealed capture's representation does not carry it at all."""
    ok = _evidence_client(_meta(StorageTier.PUBLIC, "actual")).get("/v1/evidence/art:x/cap:x")
    assert ok.json()["representation"]["source_uri"] == "https://example/x"
    for tier in (StorageTier.RESTRICTED, StorageTier.SEALED):
        body = _evidence_client(_meta(tier, "actual")).get("/v1/evidence/art:x/cap:x").json()
        assert "source_uri" not in body["representation"], tier
        assert "https://example" not in json.dumps(body)


def test_retrieved_at_is_a_full_iso_timestamp_never_date_only() -> None:
    """P35.31 (J4 S-10): the served retrieved_at carries the full timestamp."""
    body = (
        _evidence_client(_meta(StorageTier.PUBLIC, "actual")).get("/v1/evidence/art:x/cap:x").json()
    )
    assert body["representation"]["retrieved_at"] == "2026-07-01T12:30:05Z"


def test_every_evidence_representation_names_its_tier_basis() -> None:
    """P35.31 (F-400): a tightened/derived tier must label its basis — the API
    carries ``tier_basis`` (and ``recorded_tier`` where they differ) so a
    served value is never a silent upgrade."""
    body = (
        _evidence_client(_meta(StorageTier.RESTRICTED, "actual"))
        .get("/v1/evidence/art:x/cap:x")
        .json()
    )
    rep = body["representation"]
    assert rep["tier"] == "restricted" and rep["tier_basis"] == "recorded"
    tightened = dataclasses.replace(
        _meta(StorageTier.SEALED, "actual"),
        tier_basis="derived_at_read",
        recorded_tier="public",
    )
    rep = _evidence_client(tightened).get("/v1/evidence/art:x/cap:x").json()["representation"]
    assert rep["tier_basis"] == "derived_at_read" and rep["recorded_tier"] == "public"


def test_evidence_endpoint_serves_the_derivative_excerpt() -> None:
    """P36.15 (SIG-PUB-015/016): where a redaction derivative exists, the API
    excerpt surface serves the derivative's excerpt and names the derivative —
    the parent's raw excerpt never reaches the response."""
    meta = dataclasses.replace(
        _meta(StorageTier.PUBLIC, "actual"),
        excerpt="the raw parent excerpt with Officer Jane M. Doe",
        derivative=RedactionDerivative(
            capture_id="cap:x-red",
            content_digest="d" + "1" * 40,
            method="text-layer-substitution",
            version="1",
            excerpt="the derivative excerpt with [redacted]",
        ),
    )
    body = _evidence_client(meta).get("/v1/evidence/art:x/cap:x").json()
    rep = body["representation"]
    assert rep["excerpt"] == "the derivative excerpt with [redacted]"
    assert rep["redaction_derivative"]["capture_id"] == "cap:x-red"
    assert rep["redaction_derivative"]["redaction_method"] == "text-layer-substitution"
    assert "Jane M. Doe" not in json.dumps(body)


# --- /terms: no board, no counsel (E2 H-5) --------------------------------------


def test_terms_names_no_board_or_counsel(client: TestClient) -> None:
    body = client.get("/terms").json()
    payload = " ".join(
        [body["remedy"], *body["prohibitions"], *body["tiers"].values(), *body["licenses"].values()]
    ).lower()
    assert "board" not in payload
    assert "counsel" not in payload
    # SIG-API-013: the re-identification prohibition and an explicit remedy
    # still stand — only the fabricated entities were removed.
    assert body["reidentification_prohibited"] is True
    assert body["prohibitions"]
    assert "revocation" in body["remedy"]


# --- the live-spine basis label on every response (A-20=a) ----------------------

_BASIS_ROUTES = [
    "/",
    "/health",
    "/terms",
    "/openapi.json",
    "/v1/resolution/agency:okcpd/active_device_count",
    "/v1/entity/agency/agency:okcpd",
    "/v1/claim/portal",
    "/v1/evidence/art:portal/cap:portal:1",
    "/v1/search?q=oklahoma",
    "/v1/dossier/jurisdiction:okc",
    "/v1/coverage/agency:okcpd:active_device_count",
    "/v1/crosswalk",
    "/v1/task",
    "/v1/task/task:okcpd-count",
    "/v1/contradiction",
    "/v1/contradiction/contradiction:okcpd-count",
    "/v1/changes",
    "/v1/export",
    "/id/agency/okcpd",
    # Error bodies carry the label too — a 404 is a live-spine answer.
    "/v1/dossier/jurisdiction:nowhere-held",
    "/v1/entity/agency/nonexistent",
]


def test_every_response_carries_the_live_spine_basis_label(client: TestClient) -> None:
    for path in _BASIS_ROUTES:
        resp = client.get(path)
        assert resp.headers.get("x-sig-basis") == "live-spine", f"{path}: missing header"
        ctype = resp.headers.get("content-type", "")
        if ctype.startswith(("application/json", "application/ld+json")):
            body = resp.json()
            assert isinstance(body.get("basis"), dict), f"{path}: missing basis field"
            assert body["basis"]["type"] == "live-spine", f"{path}: wrong basis"
            # The demo store derives from no spine: no watermark is fabricated.
            assert "watermark" not in body["basis"]


def test_basis_header_and_field_on_error_and_html_surfaces(client: TestClient) -> None:
    not_found = client.get("/v1/dossier/jurisdiction:nowhere-held")
    assert not_found.status_code == 404
    assert not_found.headers["x-sig-basis"] == "live-spine"
    assert not_found.json()["basis"]["type"] == "live-spine"
    # Non-JSON bodies still carry the header.
    html = client.get("/id/agency/okcpd", headers={"accept": "text/html"})
    assert html.headers["x-sig-basis"] == "live-spine"


def test_basis_label_discloses_release_id_and_watermark_when_known() -> None:
    store = InMemoryStore()
    # A store that knows a watermark discloses it; release id is disclosed
    # only where configured (the service is "pinned" to a promoted release).
    store.spine_watermark = lambda: "claims=2 closed=0 latest_assertion=none evidence=0/0/0 v=3"  # type: ignore[method-assign]
    app = create_app(store, release_id="p-release-1")
    body = TestClient(app).get("/v1/search", params={"q": "oklahoma"})
    assert body.headers["x-sig-basis"] == "live-spine"
    assert body.headers["x-sig-basis-release"] == "p-release-1"
    assert "claims=2" in (body.headers.get("x-sig-basis-watermark") or "")
    basis = body.json()["basis"]
    assert basis["type"] == "live-spine"
    assert basis["watermark"].startswith("claims=2")
    assert basis["release_id"] == "p-release-1"

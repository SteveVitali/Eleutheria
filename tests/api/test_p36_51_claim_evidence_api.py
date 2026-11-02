# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.51 (R11-K13-TX-08b) — the claim/evidence API fixes (J3 §5.5, SIG-EVUI-007).

* ``/v1/claim/{id}`` returns ``artifact_id``, the binding rows (capture ids +
  roles + binding states) and the ``provenance`` href — every claim is
  navigable to its evidence, or shows the typed absent state.
* ``/v1/evidence/{a}/{c}`` returns ``capture_classification`` and the S-6-gated
  ``upstream`` block — the full URL only where the lane permits; ``None`` on a
  restricted/sealed capture whose upstream URI is not a public fact.
"""

from __future__ import annotations

import dataclasses

from api.store import InMemoryStore
from evidence.tiers import CaptureMetadata, StorageTier
from starlette.testclient import TestClient

from api import create_app


def _client(meta: CaptureMetadata | None = None) -> TestClient:
    store = InMemoryStore()
    if meta is not None:
        store.add_capture(meta, artifact_id="art:x")
    return TestClient(create_app(store))


def _meta(
    tier: StorageTier, lane: str | None = "raw-ok", cls: str | None = "actual"
) -> CaptureMetadata:
    return CaptureMetadata(
        capture_id="cap:x",
        source_id="src:x",
        source_uri="https://city.example/docs/contract.pdf?token=sekret",
        retrieved_at="2026-07-01T12:30:05Z",
        content_digest="d" + "0" * 40,
        media_type="application/pdf",
        tier=tier,
        capture_classification=cls,
        lane=lane,
    )


# --- /v1/claim → evidence navigable (SIG-EVUI-007) ----------------------------


def test_claim_carries_artifact_id_bindings_and_provenance(client: TestClient) -> None:
    """The demo claim's capture binding resolves to its artifact — ``/v1/claim``
    answers the fields a client needs to reach ``/v1/evidence``."""
    body = client.get("/v1/claim/portal").json()
    assert body["artifact_id"] == "art:portal"
    assert body["binding_status"] == "legacy_synthetic"
    assert body["provenance"] == "/v1/evidence/art:portal/cap:portal:1"
    binding = body["evidence"][0]
    assert binding["capture_id"] == "cap:portal:1"
    assert binding["artifact_id"] == "art:portal"
    assert binding["href"] == "/v1/evidence/art:portal/cap:portal:1"


def test_claim_with_no_binding_states_the_typed_absence() -> None:
    """A claim without a published binding shows the named absence — never a
    dead ``/v1/evidence`` link."""
    from datetime import UTC, date, datetime

    from api.store import StoredClaim
    from reconcile.resolve import Claim

    store = InMemoryStore()
    store.add_claim(
        StoredClaim(
            claim=Claim(
                claim_id="bare",
                subject_id="s",
                predicate_id="p",
                value=1,
                reliability="R2",
                integrity="I1",
                genre="g",
                observed_at=date(2026, 7, 1),
                raw_value="1",
                source_id="src:x",
            ),
            asserted_at=datetime(2026, 7, 2, tzinfo=UTC),
        )
    )
    body = TestClient(create_app(store)).get("/v1/claim/bare").json()
    assert body["artifact_id"] is None
    assert body["binding_status"] == "not_recorded"
    assert body["provenance"] is None
    assert body["evidence"] == []


# --- /v1/evidence — classification + the S-6-gated upstream ---------------------


def test_evidence_returns_capture_classification_and_full_retrieved_at() -> None:
    body = _client(_meta(StorageTier.PUBLIC)).get("/v1/evidence/art:x/cap:x").json()
    assert body["capture_classification"] == "actual"
    assert body["representation"]["capture_classification"] == "actual"
    assert body["representation"]["retrieved_at"] == "2026-07-01T12:30:05Z"


def test_evidence_upstream_is_s6_gated_for_a_publishing_lane() -> None:
    body = _client(_meta(StorageTier.PUBLIC, lane="raw-ok")).get("/v1/evidence/art:x/cap:x").json()
    up = body["upstream"]
    assert up["status"] == "full_url"
    assert up["url"] == "https://city.example/docs/contract.pdf"  # credential-stripped
    assert "token" not in up["url"]
    assert body["representation"]["source_uri"] == up["url"]


def test_evidence_upstream_host_only_drops_the_url() -> None:
    """A non-publishing lane serves host + path-hash — the full URL never leaks."""
    body = (
        _client(_meta(StorageTier.PUBLIC, lane="link-only")).get("/v1/evidence/art:x/cap:x").json()
    )
    up = body["upstream"]
    assert up["status"] == "host_only" and up["url"] is None
    assert up["host"] == "city.example" and up["path_sha256"]
    assert "source_uri" not in body["representation"]
    import json

    assert "contract.pdf" not in json.dumps(body)


def test_evidence_upstream_absent_for_restricted_and_sealed() -> None:
    """A restricted or sealed capture's upstream URI is not a public fact."""
    for tier in (StorageTier.RESTRICTED, StorageTier.SEALED):
        body = _client(_meta(tier)).get("/v1/evidence/art:x/cap:x").json()
        assert body["upstream"] is None, tier
        assert "source_uri" not in body["representation"]


def test_evidence_classification_absent_for_sealed() -> None:
    """The sealed representation stays the §17.5 minimal field set."""
    body = _client(_meta(StorageTier.SEALED)).get("/v1/evidence/art:x/cap:x").json()
    assert body["capture_classification"] is None
    assert "capture_classification" not in body["representation"]


def test_evidence_unrecorded_lane_fails_closed() -> None:
    """An unrecorded lane serves no full URL (fail-closed ``unknown`` lane)."""
    meta = dataclasses.replace(_meta(StorageTier.PUBLIC), lane=None)
    body = _client(meta).get("/v1/evidence/art:x/cap:x").json()
    assert body["upstream"]["status"] == "host_only"
    assert "source_uri" not in body["representation"]

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.2 / D-P31.1-3 (SIG-TRUST-001): an entity that carries claims under a
predicate the resolver's registry does not know must still serve its registered,
admissible facts — the unknown predicate is surfaced explicitly, never a
whole-entity 404 and never a fabricated value.
"""

from __future__ import annotations

import pytest
from api.demo import build_demo_store
from api.store import EntityRecord
from starlette.testclient import TestClient

from api import create_app

_UNREGISTERED = "sig.test.unregistered_p32_2"


@pytest.fixture
def client() -> TestClient:
    store = build_demo_store()
    # The demo entity gains a second predicate id the ruleset registry does not
    # know — the mixed-registered entity of D-P31.1-3.
    store.add_entity(
        EntityRecord(
            entity_id="agency:mixed",
            entity_type="agency",
            label="Mixed-registry agency",
            predicate_ids=("active_device_count", _UNREGISTERED),
            source_ids=("src:portal",),
        )
    )
    return TestClient(create_app(store))


def test_mixed_entity_serves_registered_facts_and_names_the_unknown(
    client: TestClient,
) -> None:
    """The entity exists: HTTP 200, its registered predicate resolves as a fact,
    and the unregistered predicate is listed explicitly — not 404, not a guess."""
    r = client.get("/v1/entity/agency/agency:mixed")
    assert r.status_code == 200
    body = r.json()
    assert body["unregistered_predicates"] == [_UNREGISTERED]
    # The registered predicate produced a fact envelope (UNRESOLVED is also a
    # fact envelope — what matters is the entity did not disappear).
    assert isinstance(body["facts"], list) and len(body["facts"]) == 1


def test_an_entity_without_claims_still_names_the_unknown(
    client: TestClient,
) -> None:
    """No fabricated value: the unknown predicate appears only in the explicit
    surface, never as a fact with a guessed definition."""
    body = client.get("/v1/entity/agency/agency:mixed").json()
    for fact in body["facts"]:
        assert fact.get("predicate_id") != _UNREGISTERED


def test_a_truly_absent_entity_still_404s(client: TestClient) -> None:
    """The fix does not weaken the absent-entity contract."""
    assert client.get("/v1/entity/agency/agency:absent").status_code == 404


def test_a_direct_resolution_request_for_an_unknown_predicate_still_404s(
    client: TestClient,
) -> None:
    """Scoped fix (D-P31.1-3): the direct resolution route keeps its honest 404 —
    a caller asking specifically for an unknown predicate gets the unknown-
    resource answer, not a silently degraded response."""
    r = client.get(f"/v1/resolution/agency:okcpd/{_UNREGISTERED}")
    assert r.status_code == 404
    assert "unknown predicate" in r.json()["detail"]


def test_entities_with_only_registered_predicates_report_none(
    client: TestClient,
) -> None:
    body = client.get("/v1/entity/agency/agency:okcpd").json()
    assert body["unregistered_predicates"] == []

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""AC1 — no material fact is returned as a bare value (SIG-API-002).

Every material-fact response carries the full §37.1 resolution envelope. The
required key set is :data:`api.models.RESOLUTION_ENVELOPE_FIELDS`, the single
source of truth the contract is checked against.
"""

from __future__ import annotations

from api.models import RESOLUTION_ENVELOPE_FIELDS
from starlette.testclient import TestClient


def _assert_full_envelope(envelope: dict[str, object]) -> None:
    for field in RESOLUTION_ENVELOPE_FIELDS:
        assert field in envelope, f"envelope missing required §37.1 field {field!r}"
    # The value is present, but only *inside* the envelope alongside its signals —
    # never as a bare scalar.
    assert set(RESOLUTION_ENVELOPE_FIELDS).issubset(envelope.keys())


def test_resolution_response_carries_the_full_envelope(client: TestClient) -> None:
    body = client.get("/v1/resolution/agency:okcpd/active_device_count").json()
    assert "fact" in body and "envelope" in body["fact"]
    _assert_full_envelope(body["fact"]["envelope"])
    # rationale is the §37.1 field; the resolver's code+text are both preserved.
    assert set(body["fact"]["envelope"]["rationale"].keys()) == {"code", "text"}


def test_entity_facts_each_carry_the_full_envelope(client: TestClient) -> None:
    body = client.get("/v1/entity/agency/agency:okcpd").json()
    assert body["facts"], "an entity with predicates must expose enveloped facts"
    for fact in body["facts"]:
        _assert_full_envelope(fact["envelope"])


def test_a_material_fact_is_never_a_top_level_bare_value(client: TestClient) -> None:
    """The response body is an object with the value nested in the envelope."""
    body = client.get("/v1/resolution/agency:okcpd/active_device_count").json()
    assert isinstance(body, dict)
    # The scalar 38 must not appear as a top-level value; it lives under fact.envelope.value.
    assert body["fact"]["envelope"]["value"] == 38
    assert "value" not in body  # no bare value at the top level


def test_envelope_echoes_the_ruleset_version_and_asof(client: TestClient) -> None:
    env = client.get("/v1/resolution/agency:okcpd/active_device_count").json()["fact"]["envelope"]
    assert env["ruleset_version"]
    assert env["as_of_world"] and env["as_of_belief"]
    assert env["resolution_status"] in {"RESOLVED", "UNRESOLVED"}


def test_unresearched_subject_returns_an_unresolved_envelope_not_a_bare_value(
    client: TestClient,
) -> None:
    """A known predicate with no claims resolves to an UNRESOLVED envelope, never a
    bare null — the gap is stated inside the envelope (§3.1)."""
    body = client.get("/v1/resolution/agency:nowhere/active_device_count").json()
    _assert_full_envelope(body["fact"]["envelope"])
    assert body["fact"]["envelope"]["resolution_status"] == "UNRESOLVED"


def test_an_unknown_predicate_is_404_not_a_fabricated_value(client: TestClient) -> None:
    """An unknown predicate is a missing resource (404), never a synthesised answer."""
    assert client.get("/v1/resolution/agency:x/nonexistent_predicate").status_code == 404

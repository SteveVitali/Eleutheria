# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-API-003/004 — coverage on every response; licence + attribution on collections."""

from __future__ import annotations

from datetime import date

from api.envelope import license_statement
from policy.rights import RightsRecord
from starlette.testclient import TestClient

_READ_URLS = [
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
]


def test_every_v1_read_response_carries_a_coverage_statement(client: TestClient) -> None:
    """SIG-API-003: every /v1 read response carries a coverage statement."""
    for url in _READ_URLS:
        body = client.get(url).json()
        cov = body["coverage"]
        assert set(cov.keys()) >= {"scope", "complete", "evaluated", "not_evaluable", "records"}, (
            url
        )


def test_coverage_states_the_explained_gap(client: TestClient) -> None:
    # The entity has an unresearched predicate — an explicit, explained gap (§32.2).
    cov = client.get("/v1/entity/agency/agency:okcpd").json()["coverage"]
    assert cov["not_evaluable"] >= 1
    assert cov["complete"] is False
    assert any(r["absence_kind"] == "not_researched" for r in cov["records"])


def test_collection_response_carries_a_licence_statement(client: TestClient) -> None:
    lic = client.get("/v1/search", params={"q": "oklahoma"}).json()["license"]
    # OKCPD's two CC-BY-4.0 sources merge into a single licence.
    assert lic["single_license"] is True
    assert lic["effective_license"] == "CC-BY-4.0"
    assert lic["obligations"], "attribution obligations are passed downstream (SIG-LIC-011)"


def test_entity_response_carries_upstream_attribution(client: TestClient) -> None:
    attribution = client.get("/v1/entity/agency/agency:okcpd").json()["attribution"]
    sources = {a["source_id"] for a in attribution}
    assert {"src:portal", "src:records"} <= sources
    assert all(a["attribution"] for a in attribution)


def _rights(source_id: str, spdx: str) -> RightsRecord:
    return RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution=f"{source_id} attribution",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 7, 1),
    )


def test_incompatible_compartments_yield_no_single_licence() -> None:
    """CC-BY-4.0 and ODbL-1.0 cannot merge; the statement lists both, never fabricates one."""
    lic = license_statement([_rights("a", "CC-BY-4.0"), _rights("b", "ODbL-1.0")])
    assert lic.effective_license is None
    assert lic.single_license is False
    assert set(lic.compartments) == {"CC-BY-4.0", "ODbL-1.0"}


def test_single_compartment_yields_a_single_licence() -> None:
    lic = license_statement([_rights("a", "CC-BY-4.0"), _rights("b", "CC-BY-4.0")])
    assert lic.single_license is True
    assert lic.effective_license == "CC-BY-4.0"


def test_a_non_redistributable_source_closes_the_licence_gate() -> None:
    """SIG-LIC-004: a non-redistributable source has no publishable licence — the
    statement reports the gate closed, never a fabricated licence (no 500)."""
    blocked = RightsRecord(
        source_id="blocked",
        spdx="CC-BY-4.0",
        attribution="blocked",
        redistributable=False,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 7, 1),
    )
    lic = license_statement([_rights("a", "CC-BY-4.0"), blocked])
    assert lic.effective_license is None
    assert lic.single_license is False
    assert lic.compartments == ["EXPORT-GATE-CLOSED"]


def test_task_and_contradiction_single_resources_carry_coverage(client: TestClient) -> None:
    """SIG-API-003: single-resource responses carry a coverage statement too."""
    for url in ("/v1/task/task:okcpd-count", "/v1/contradiction/contradiction:okcpd-count"):
        body = client.get(url).json()
        assert "coverage" in body and "scope" in body["coverage"]

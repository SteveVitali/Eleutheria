# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-API-013 — acceptable-use terms prohibit re-identification and state a remedy."""

from __future__ import annotations

from starlette.testclient import TestClient


def test_terms_prohibit_reidentification(client: TestClient) -> None:
    body = client.get("/terms").json()
    assert body["reidentification_prohibited"] is True
    assert any("re-identif" in p.lower() for p in body["prohibitions"])


def test_terms_state_a_remedy_not_a_decorative_prohibition(client: TestClient) -> None:
    # Terms without a stated remedy are decorative (SIG-API-013).
    remedy = client.get("/terms").json()["remedy"]
    assert remedy.strip()
    assert "revocation" in remedy.lower()


def test_terms_describe_all_three_tiers(client: TestClient) -> None:
    tiers = client.get("/terms").json()["tiers"]
    assert set(tiers.keys()) == {"anonymous", "registered", "partner"}

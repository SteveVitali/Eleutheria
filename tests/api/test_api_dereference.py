# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""SIG-API-008 — dereferenceable identifiers with content negotiation.

``/id/{type}/{uuid}`` resolves to HTML, JSON-LD, or RDF (Turtle) by ``Accept``.
"""

from __future__ import annotations

import json

from starlette.testclient import TestClient


def test_html_is_the_default_representation(client: TestClient) -> None:
    r = client.get("/id/agency/okcpd", headers={"accept": "text/html"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert "Oklahoma City Police Department" in r.text


def test_jsonld_representation_is_valid_json_ld(client: TestClient) -> None:
    r = client.get("/id/agency/okcpd", headers={"accept": "application/ld+json"})
    assert r.headers["content-type"].startswith("application/ld+json")
    doc = json.loads(r.text)
    assert doc  # a non-empty JSON-LD document
    assert "sig.example/id/agency/okcpd" in r.text


def test_rdf_turtle_representation(client: TestClient) -> None:
    r = client.get("/id/agency/okcpd", headers={"accept": "text/turtle"})
    assert r.headers["content-type"].startswith("text/turtle")
    assert "okcpd" in r.text


def test_star_accept_falls_back_to_html(client: TestClient) -> None:
    r = client.get("/id/agency/okcpd", headers={"accept": "*/*"})
    assert r.headers["content-type"].startswith("text/html")


def test_unknown_identifier_is_404(client: TestClient) -> None:
    assert client.get("/id/agency/does-not-exist").status_code == 404

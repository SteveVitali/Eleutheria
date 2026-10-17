# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.13 / SIG-REL-009 (G3 §6.3) — the API provenance headers.

Every sig-api answer — release-basis, live-spine, and error bodies alike —
carries ``X-SIG-Code: <commit12>`` (the first twelve hex of the deploy-pinned
``SIG_CODE_COMMIT``) and ``X-SIG-Conf-Gen: <n>`` (``SIG_CONF_GEN``). Both are
read from the environment per request like the health handler's
``SIG_CODE_COMMIT``; an unset env means the deploy pinned nothing and the
header is absent — never a placeholder value.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from api.release_serving import ReleaseServingStore
from starlette.testclient import TestClient

from api import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "release_registry"
COMMIT = "f7f67f16257e7ee0ab508a9ae24c5015475d23dc"
COMMIT12 = COMMIT[:12]


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    target = tmp_path / "registry"
    shutil.copytree(FIXTURES, target)
    return target


@pytest.fixture
def release_client(store, registry: Path) -> TestClient:
    return TestClient(create_app(store, release_serving=ReleaseServingStore(registry)))


def test_code_and_conf_gen_headers_on_every_basis_class(
    release_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIG_CODE_COMMIT", COMMIT)
    monkeypatch.setenv("SIG_CONF_GEN", "7")
    # release basis
    r = release_client.get("/v1/dossier/jurisdiction:okc")
    assert r.headers["x-sig-basis"] == "release"
    assert r.headers["x-sig-code"] == COMMIT12
    assert r.headers["x-sig-conf-gen"] == "7"
    # live-spine basis
    r = release_client.get("/v1/contradiction")
    assert r.headers["x-sig-basis"] == "live-spine"
    assert r.headers["x-sig-code"] == COMMIT12
    assert r.headers["x-sig-conf-gen"] == "7"
    # a release-basis error body carries them too — an error is still an answer
    r = release_client.get("/v1/dossier/jurisdiction:nowhere")
    assert r.status_code == 404
    assert r.headers["x-sig-code"] == COMMIT12
    assert r.headers["x-sig-conf-gen"] == "7"
    # service routes
    for path in ("/health", "/"):
        r = release_client.get(path)
        assert r.headers["x-sig-code"] == COMMIT12, path
        assert r.headers["x-sig-conf-gen"] == "7", path


def test_unset_env_means_absent_headers_never_placeholders(
    release_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SIG_CODE_COMMIT", raising=False)
    monkeypatch.delenv("SIG_CONF_GEN", raising=False)
    r = release_client.get("/v1/dossier/jurisdiction:okc")
    assert "x-sig-code" not in r.headers
    assert "x-sig-conf-gen" not in r.headers
    r = release_client.get("/health")
    assert "x-sig-code" not in r.headers
    assert "x-sig-conf-gen" not in r.headers


def test_code_header_is_the_commit12_not_the_full_hex(
    release_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The stamp's printed short form — twelve hex, matching the release
    stamp's linked commit — never the raw forty."""
    monkeypatch.setenv("SIG_CODE_COMMIT", COMMIT)
    r = release_client.get("/v1/contradiction")
    assert r.headers["x-sig-code"] == COMMIT12
    assert len(r.headers["x-sig-code"]) == 12


def test_headers_survive_a_non_json_response(
    release_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The middleware's header pass runs on the response-start regardless of
    body type — a non-JSON answer (or an upstream error) still names its code
    and conf generation."""
    monkeypatch.setenv("SIG_CODE_COMMIT", COMMIT)
    monkeypatch.setenv("SIG_CONF_GEN", "3")
    r = release_client.get("/v1/releases")
    assert r.status_code == 200
    assert r.headers["x-sig-code"] == COMMIT12
    assert r.headers["x-sig-conf-gen"] == "3"

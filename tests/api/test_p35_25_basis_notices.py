# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.25 (SIG-CONF-014, CP-4) — ``basis.notices``, the deploy-declared
material-basis disclosures.

The lineage/independence backfill changes what downstream answers are based
on (corroboration counts, shared-ref resolution). ``SIG_API_BASIS_NOTICES``
carries a JSON array — or a ``;``-separated list — of notice strings the
basis block echoes verbatim on BOTH basis classes. An absent env is an
absent key, never an empty list or a fabricated notice.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from api.release_serving import ReleaseServingStore
from starlette.testclient import TestClient

from api import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "release_registry"


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    target = tmp_path / "registry"
    shutil.copytree(FIXTURES, target)
    return target


@pytest.fixture
def client(store, registry: Path) -> TestClient:
    return TestClient(create_app(store, release_serving=ReleaseServingStore(registry)))


def test_absent_env_means_absent_key_never_an_empty_list(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SIG_API_BASIS_NOTICES", raising=False)
    for path in ("/v1/contradiction", "/v1/dossier/jurisdiction:okc"):
        r = client.get(path)
        assert r.status_code == 200
        assert "notices" not in r.json()["basis"], path


def test_empty_env_means_absent_key(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIG_API_BASIS_NOTICES", "   ")
    r = client.get("/v1/contradiction")
    assert "notices" not in r.json()["basis"]


def test_json_array_notices_echo_verbatim_on_live_spine(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(
        "SIG_API_BASIS_NOTICES",
        '["corroboration basis changed by the lineage backfill", "second"]',
    )
    r = client.get("/v1/contradiction")
    assert r.headers["x-sig-basis"] == "live-spine"
    assert r.json()["basis"]["notices"] == [
        "corroboration basis changed by the lineage backfill",
        "second",
    ]


def test_notices_ride_the_release_basis_too(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The notice is never class-conditional — a release byte-set pinned
    before the backfill is equally changed in what it is based on."""
    monkeypatch.setenv("SIG_API_BASIS_NOTICES", '["the notice"]')
    r = client.get("/v1/dossier/jurisdiction:okc")
    assert r.headers["x-sig-basis"] == "release"
    assert r.json()["basis"]["notices"] == ["the notice"]


def test_semicolon_separated_form_for_awkward_envs(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIG_API_BASIS_NOTICES", "notice one ;  notice two;; ")
    r = client.get("/v1/contradiction")
    assert r.json()["basis"]["notices"] == ["notice one", "notice two"]


def test_malformed_json_falls_through_to_the_separator_parse(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``["unterminated`` is not valid JSON — the value is still disclosed
    via the ``;`` parse rather than silently dropped or failing the answer."""
    monkeypatch.setenv("SIG_API_BASIS_NOTICES", '["unterminated')
    r = client.get("/v1/contradiction")
    assert r.status_code == 200
    assert r.json()["basis"]["notices"] == ['["unterminated']


def test_blank_entries_never_emit_empty_notices(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIG_API_BASIS_NOTICES", '["real", "  ", ""]')
    r = client.get("/v1/contradiction")
    assert r.json()["basis"]["notices"] == ["real"]


def test_notices_are_additive_never_replacing_the_basis_fields(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The kind/watermark/legacy keys survive alongside — older clients see
    exactly the basis they saw before plus one new key."""
    monkeypatch.setenv("SIG_API_BASIS_NOTICES", '["n"]')
    r = client.get("/v1/contradiction")
    basis = r.json()["basis"]
    assert basis["kind"] == "live-spine"
    assert basis["notices"] == ["n"]

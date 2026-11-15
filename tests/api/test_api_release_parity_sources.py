# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.42 / SIG-TRANSP-025 (TX-15, J3 §6.10) — API parity over the fixture
registry (``tests/api/fixtures/release_registry``).

The release-namespaced source routes serve the promoted release's own api-slice
JSON twins addressed by the publication id in the path (a citation-grade URL —
the same ``sig.source-row/1`` / ``sig.source-page/2`` / ``sig.source-runs/1``
facts the site's ``/sources/…`` pages and their ``index.json`` twins carry):

    /v1/releases/<pub>/sources           ->  r/<pub>/api/sources.json
    /v1/releases/<pub>/sources/<id>      ->  r/<pub>/api/sources/<id>.json
    /v1/releases/<pub>/sources/<id>/runs ->  r/<pub>/api/sources/<id>/runs.json

``/v1/export`` answers the release's real catalog — the manifest-pinned
``releases/<pub>/data/download_listing.json`` (``sig.download-listing/1``:
absolute mirror URLs, sizes, sha256, licences — the document ``/data/`` and
``/releases/<pub>/data/`` render), falling back to a pre-TX-10b release's
pinned ``api/export.json``.

The parity assertion: every answer the API serves is the release's own file —
the served body (minus the server-injected ``release``/``basis`` blocks) equals
the staged document field by field, so a drift between the release's twin and
the API's answer fails loud. The web-side HTML↔twin leg of the same parity is
``web/tests/e2e/acceptance-parity.spec.ts``; this suite pins twin↔API.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from api.release_serving import ReleaseServingStore
from starlette.testclient import TestClient

from api import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "release_registry"
PUB_A = "p-" + "a" * 64
PUB_B = "p-" + "b" * 64
LABEL_A = "sig-2026-10-01-fixture"


@pytest.fixture
def registry(tmp_path: Path) -> Path:
    """A private copy of the committed fixture registry — the serving path is
    read-only, but a copy keeps the committed bytes provably untouched."""
    target = tmp_path / "registry"
    shutil.copytree(FIXTURES, target)
    return target


@pytest.fixture
def client(store, registry: Path) -> TestClient:
    return TestClient(create_app(store, release_serving=ReleaseServingStore(registry)))


def _staged_json(registry: Path, rel: str) -> dict:
    return json.loads((registry / "staged" / rel).read_text())


def _served_fields(body: dict) -> dict:
    """The payload minus the blocks the serving layer injects — what must
    equal the release file field by field."""
    return {k: v for k, v in body.items() if k not in ("release", "basis")}


def _file_fields(doc: dict) -> dict:
    """The staged document minus its embedded ``release`` block — the served
    answer re-stamps it with the resolved identity."""
    return {k: v for k, v in doc.items() if k != "release"}


# --------------------------------------------------------------------------- #
# The release-namespaced source routes                                          #
# --------------------------------------------------------------------------- #


def test_release_sources_index_serves_the_release_twin(client: TestClient, registry: Path) -> None:
    r = client.get(f"/v1/releases/{PUB_A}/sources")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    assert r.headers["x-sig-release"] == f"{LABEL_A} {PUB_A}"
    body = r.json()
    doc = _staged_json(registry, f"r/{PUB_A}/api/sources.json")
    assert _served_fields(body) == _file_fields(doc)
    assert body["sources"][0]["source_id"] == "src_okc"
    assert body["release"]["publication_id"] == PUB_A


def test_release_source_serves_the_page_twin(client: TestClient, registry: Path) -> None:
    r = client.get(f"/v1/releases/{PUB_A}/sources/src_okc")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    body = r.json()
    doc = _staged_json(registry, f"r/{PUB_A}/api/sources/src_okc.json")
    assert _served_fields(body) == _file_fields(doc)
    assert body["source_id"] == "src_okc"
    assert body["homepage_url"] == "https://example/okc"
    assert body["terms"] == {"summary": "fixture terms"}


def test_release_source_runs_serves_the_runs_twin(client: TestClient, registry: Path) -> None:
    r = client.get(f"/v1/releases/{PUB_A}/sources/src_okc/runs")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    body = r.json()
    doc = _staged_json(registry, f"r/{PUB_A}/api/sources/src_okc/runs.json")
    assert _served_fields(body) == _file_fields(doc)
    # The same sig.source-runs/1 shape the site's runs/index.json twin emits.
    assert body["schema"] == "sig.source-runs/1"
    assert body["source_id"] == "src_okc"
    assert body["execution_count"] == 2
    assert [e["execution_id"] for e in body["executions"]] == [
        "exec-src-okc-2",
        "exec-src-okc-1",
    ]
    assert all(e["schema"] == "sig.execution-record/1" for e in body["executions"])


def test_namespaced_answers_equal_the_unnamespaced_ones(
    client: TestClient,
) -> None:
    """``/v1/releases/<pub>/sources…`` is the citation-grade spelling of
    ``/v1/sources…?release=<pub>`` — same release bytes, same fields."""
    for namespaced, unnamespaced in (
        (f"/v1/releases/{PUB_A}/sources", f"/v1/sources?release={PUB_A}"),
        (
            f"/v1/releases/{PUB_A}/sources/src_okc",
            f"/v1/sources/src_okc?release={PUB_A}",
        ),
    ):
        a = client.get(namespaced)
        b = client.get(unnamespaced)
        assert a.status_code == b.status_code == 200
        assert _served_fields(a.json()) == _served_fields(b.json())


def test_release_source_unknown_id_is_a_release_404(client: TestClient) -> None:
    r = client.get(f"/v1/releases/{PUB_A}/sources/src_missing")
    assert r.status_code == 404
    assert r.json()["code"] == "scope_not_available"
    assert r.headers["x-sig-basis"] == "release"

    r = client.get(f"/v1/releases/{PUB_A}/sources/src_missing/runs")
    assert r.status_code == 404
    assert r.json()["code"] == "scope_not_available"


def test_release_source_runs_absent_doc_is_a_release_404(
    client: TestClient, registry: Path
) -> None:
    """A source whose release carries no runs twin answers the typed
    absence — never a fabricated feed."""
    (registry / "staged" / f"r/{PUB_A}/api/sources/src_okc/runs.json").unlink()
    r = client.get(f"/v1/releases/{PUB_A}/sources/src_okc/runs")
    assert r.status_code == 404
    assert r.json()["code"] == "scope_not_available"


def test_release_sources_on_the_prior_promotion(client: TestClient) -> None:
    """``{pub}`` names ANY promoted release — release B has no sources
    twin, so its honest absence answers, still release-labelled."""
    r = client.get(f"/v1/releases/{PUB_B}/sources")
    assert r.status_code == 503
    assert r.json()["code"] == "release_artifact_absent"
    assert r.headers["x-sig-basis"] == "release"


def test_release_sources_refuse_an_unpromoted_publication(
    client: TestClient,
) -> None:
    pub = "p-" + "9" * 64
    for suffix in ("sources", "sources/src_okc", "sources/src_okc/runs"):
        r = client.get(f"/v1/releases/{pub}/{suffix}")
        assert r.status_code == 404
        assert r.json()["code"] == "unknown_publication"


def test_release_sources_unconfigured_is_an_honest_503(store) -> None:
    client = TestClient(create_app(store))
    r = client.get(f"/v1/releases/{PUB_A}/sources")
    assert r.status_code == 503
    assert r.json()["code"] == "release_serving_unconfigured"


# --------------------------------------------------------------------------- #
# /v1/export — the real catalog                                                 #
# --------------------------------------------------------------------------- #


def test_export_serves_the_real_download_catalog(client: TestClient, registry: Path) -> None:
    r = client.get("/v1/export")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    assert r.headers["x-sig-release"] == f"{LABEL_A} {PUB_A}"
    body = r.json()
    doc = _staged_json(registry, f"releases/{PUB_A}/data/download_listing.json")
    assert _served_fields(body) == _file_fields(doc)
    # The real catalog: every file carries an absolute mirror URL, size,
    # sha256 and licence — never the hard-coded stub index.
    assert body["schema"] == "sig.download-listing/1"
    assert body["mirror"]["base_url"].startswith("https://")
    assert len(body["files"]) == 3
    for f in body["files"]:
        assert f["href"].startswith(body["mirror"]["base_url"])
        assert len(f["sha256"]) == 64
        assert isinstance(f["byte_size"], int) and f["byte_size"] > 0
        assert f["license"]


def test_export_release_param_selects_a_promoted_release(
    client: TestClient,
) -> None:
    """A release built before TX-10b has no download listing — its pinned
    api-slice ``api/export.json`` keeps answering (the changes_document
    fallback idiom)."""
    r = client.get(f"/v1/export?release={PUB_B}")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    body = r.json()
    assert body["release"]["publication_id"] == PUB_B
    assert body["exports"][0]["name"] == "entities"
    assert body["exports"][0]["href"].startswith(f"/r/{PUB_B}/")


def test_export_with_neither_artifact_is_an_honest_503(client: TestClient, registry: Path) -> None:
    """No listing and no api-slice doc → the typed absence, never a stub."""
    (registry / "staged" / f"releases/{PUB_A}/data/download_listing.json").unlink()
    (registry / "staged" / f"r/{PUB_A}/api/export.json").unlink()
    r = client.get(f"/v1/export?release={PUB_A}")
    assert r.status_code == 503
    assert r.json()["code"] == "release_artifact_absent"
    assert r.headers["x-sig-basis"] == "release"


def test_export_refuses_an_unpromoted_publication(client: TestClient) -> None:
    r = client.get(f"/v1/export?release={'p-' + '9' * 64}")
    assert r.status_code == 404
    assert r.json()["code"] == "unknown_publication"


# --------------------------------------------------------------------------- #
# The parity check — every declared slice doc answers its route byte-for-byte   #
# --------------------------------------------------------------------------- #


def test_every_declared_slice_document_is_served(client: TestClient, registry: Path) -> None:
    """Walk the fixture release's ``api/index.json``: every document the
    sig.api-slice/1 index declares answers an API route, and the served body
    equals the staged file field by field (a drift fails loud)."""
    index = _staged_json(registry, f"r/{PUB_A}/api/index.json")
    export_rel = f"r/{PUB_A}/api/export.json"
    served_routes = {
        export_rel: f"/v1/export?release={PUB_A}",
        f"r/{PUB_A}/api/changes.json": f"/v1/changes?release={PUB_A}",
        f"r/{PUB_A}/api/sources.json": f"/v1/releases/{PUB_A}/sources",
        f"r/{PUB_A}/api/dossier/jurisdiction/okc.json": (
            f"/v1/dossier/jurisdiction:okc?release={PUB_A}"
        ),
        f"r/{PUB_A}/api/coverage/jurisdiction/okc.json": (
            f"/v1/coverage/jurisdiction:okc?release={PUB_A}"
        ),
        f"r/{PUB_A}/api/sources/src_okc.json": (f"/v1/releases/{PUB_A}/sources/src_okc"),
        f"r/{PUB_A}/api/sources/src_okc/runs.json": (f"/v1/releases/{PUB_A}/sources/src_okc/runs"),
    }
    declared = [str(d["path"]) for d in index["documents"]]
    assert set(declared) == set(served_routes)
    # /v1/export prefers the real catalog over the declared api-slice twin —
    # the listing is the document /data/ shows (J3 §6.10).
    expected_docs = {rel: rel for rel in declared if rel != export_rel}
    expected_docs[export_rel] = f"releases/{PUB_A}/data/download_listing.json"
    failures: list[str] = []
    for rel in declared:
        route = served_routes[rel]
        r = client.get(route)
        if r.status_code != 200:
            failures.append(f"{route} -> {r.status_code}")
            continue
        doc = _staged_json(registry, expected_docs[rel])
        served = _served_fields(r.json())
        if served != _file_fields(doc):
            failures.append(f"{route}: served fields != {expected_docs[rel]} fields")
    assert not failures, "slice/serve parity failures: " + "; ".join(failures)


def test_withdrawal_of_a_served_twin_answers_410(client: TestClient, registry: Path) -> None:
    """The withdrawal barrier dominates on the namespaced routes too — a
    denied artifact answers 410, never stale bytes."""
    w = json.loads((registry / "withdrawals.json").read_text())
    w["entries"].append(
        {
            "target_kind": "release_artifact",
            "target_id": PUB_A,
            "disposition": "withdraw",
            "reason_category": "rights_withdrawal",
            "authority": "policy",
            "decided_at": "2026-10-02T00:00:00+00:00",
            "policy_version": "publication-eligibility/1",
            "seq": 2,
        }
    )
    (registry / "withdrawals.json").write_text(json.dumps(w))
    r = client.get(f"/v1/releases/{PUB_A}/sources/src_okc")
    assert r.status_code == 410
    assert r.json()["code"] == "withdrawn"

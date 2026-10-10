# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.57 / SIG-REL-010 (G3 §6.4, REL-05) — the two API basis classes.

Served over the committed fixture registry
(``tests/api/fixtures/release_registry``): two promoted publications —
``p-aa…`` (current, label ``sig-2026-10-01-fixture``) with a full api slice
and ``p-bb…`` (a prior promotion) with a dossier document — so both the
current-pointer and the ``?release=<pub>`` selection are exercised.

* release-backed routes answer release-file bytes + ``release {label,
  publication_id, as_of_world}`` + ``X-SIG-Basis: release``;
* an unknown scope answers 404 ``scope_not_available``, still release-labelled;
* an unpromoted ``?release=`` answers 404 ``unknown_publication``;
* live-spine routes keep ``X-SIG-Basis: live-spine`` with the full basis
  block (kind, as_of, spine_watermark, latest_release);
* ``/`` + ``/health`` name the release / code commit / image digest;
* a file present but not manifest-pinned, or digest-drifted, fails closed.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from api.release_serving import (
    ReleaseIdentity,
    ReleaseServingError,
    ReleaseServingStore,
    api_path,
)
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
def serving(registry: Path) -> ReleaseServingStore:
    return ReleaseServingStore(registry)


@pytest.fixture
def release_client(store, registry: Path) -> TestClient:
    """The app over the demo spine PLUS the mounted release registry — the
    production posture after the P35.57 roll."""
    return TestClient(create_app(store, release_serving=ReleaseServingStore(registry)))


# --------------------------------------------------------------------------- #
# The store — resolution, identity, verified reads                             #
# --------------------------------------------------------------------------- #


def test_current_identity_is_the_latest_pointer(serving: ReleaseServingStore) -> None:
    ident = serving.current_identity()
    assert ident is not None
    assert ident.publication_id == PUB_A
    assert ident.label == LABEL_A
    assert ident.as_of_world == "2026-10-01"


def test_api_path_maps_scope_segments() -> None:
    assert api_path(PUB_A, "dossier", "jurisdiction:okc") == (
        f"r/{PUB_A}/api/dossier/jurisdiction/okc.json"
    )
    assert api_path(PUB_A, "export") == f"r/{PUB_A}/api/export.json"


@pytest.mark.parametrize("scope", ["..", "a/../b", "a/b", "a b", "a:b c", ""])
def test_api_path_rejects_unsafe_scopes(scope: str) -> None:
    serving = ReleaseServingStore(FIXTURES)
    with pytest.raises(ReleaseServingError) as ei:
        serving.api_document(None, "dossier", scope)
    assert ei.value.status == 404
    assert ei.value.code == "scope_not_available"


def test_resolve_publication(serving: ReleaseServingStore) -> None:
    assert serving.resolve_publication(None) == PUB_A
    assert serving.resolve_publication(PUB_B) == PUB_B
    with pytest.raises(ReleaseServingError) as ei:
        serving.resolve_publication("p-" + "9" * 64)
    assert ei.value.status == 404
    assert ei.value.code == "unknown_publication"
    with pytest.raises(ReleaseServingError) as ei:
        serving.resolve_publication("not-a-pub")
    assert ei.value.status == 404


def test_no_current_release(serving: ReleaseServingStore, registry: Path) -> None:
    (registry / "latest.json").unlink()
    with pytest.raises(ReleaseServingError) as ei:
        serving.resolve_publication(None)
    assert ei.value.status == 503
    assert ei.value.code == "no_current_release"


def test_unpinned_file_fails_closed(serving: ReleaseServingStore, registry: Path) -> None:
    target = registry / "staged" / f"r/{PUB_A}/api/dossier/jurisdiction/tulsa.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'{"scope": "jurisdiction:tulsa"}')
    with pytest.raises(ReleaseServingError) as ei:
        serving.api_document(None, "dossier", "jurisdiction:tulsa")
    assert ei.value.status == 503
    assert ei.value.code == "release_artifact_unpinned"


def test_drifted_bytes_fail_closed(serving: ReleaseServingStore, registry: Path) -> None:
    target = registry / "staged" / f"r/{PUB_A}/api/dossier/jurisdiction/okc.json"
    target.write_bytes(b'{"scope": "jurisdiction:okc", "title": "tampered"}')
    with pytest.raises(ReleaseServingError) as ei:
        serving.api_document(None, "dossier", "jurisdiction:okc")
    assert ei.value.status == 503
    assert ei.value.code == "release_verification_failed"


def test_embedded_release_mismatch_fails_closed(
    serving: ReleaseServingStore, registry: Path
) -> None:
    """A document embedded with another publication's release block can never
    be served under this one."""
    doc = {
        "scope": "jurisdiction:okc",
        "release": {"publication_id": PUB_B},
    }
    raw = json.dumps(doc).encode()
    import hashlib

    rel = f"r/{PUB_A}/api/dossier/jurisdiction/mismatch.json"
    target = registry / "staged" / rel
    target.write_bytes(raw)
    manifest_path = registry / "staged" / f"releases/{PUB_A}/integrity_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["artifacts"].append(
        {
            "path": rel,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "byte_size": len(raw),
            "compartment": "sig_graph",
            "license": "CC-BY-4.0",
        }
    )
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ReleaseServingError) as ei:
        serving.api_document(None, "dossier", "jurisdiction:mismatch")
    assert ei.value.status == 503
    assert ei.value.code == "release_metadata_mismatch"


def test_release_withdrawal_answers_410(serving: ReleaseServingStore, registry: Path) -> None:
    """A release-level deny under the CURRENT withdrawal registry denies its
    api-slice routes too — the barrier is re-evaluated per request."""
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
            "seq": 1,
        }
    )
    (registry / "withdrawals.json").write_text(json.dumps(w))
    with pytest.raises(ReleaseServingError) as ei:
        serving.api_document(None, "dossier", "jurisdiction:okc")
    assert ei.value.status == 410
    assert ei.value.code == "withdrawn"


# --------------------------------------------------------------------------- #
# The routes — release basis                                                   #
# --------------------------------------------------------------------------- #


def test_dossier_serves_release_bytes(release_client: TestClient) -> None:
    r = release_client.get("/v1/dossier/jurisdiction:okc")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    assert r.headers["x-sig-release"] == f"{LABEL_A} {PUB_A}"
    body = r.json()
    assert body["title"] == "Oklahoma City (release A)"
    assert body["release"] == {
        "publication_id": PUB_A,
        "label": LABEL_A,
        "as_of_world": "2026-10-01",
    }
    assert body["basis"]["kind"] == "release"
    assert body["basis"]["release"]["publication_id"] == PUB_A


def test_dossier_release_param_selects_a_promoted_release(
    release_client: TestClient,
) -> None:
    r = release_client.get(f"/v1/dossier/jurisdiction:okc?release={PUB_B}")
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Oklahoma City (release B — the prior promotion)"
    assert body["release"]["publication_id"] == PUB_B
    assert body["release"]["label"] == "sig-2026-09-01-fixture"


def test_dossier_unknown_scope_is_a_release_404(release_client: TestClient) -> None:
    r = release_client.get("/v1/dossier/jurisdiction:nowhere")
    assert r.status_code == 404
    assert r.json()["code"] == "scope_not_available"
    # The refusal is still a release-basis answer — the release answered "no".
    assert r.headers["x-sig-basis"] == "release"


def test_release_param_refuses_an_unpromoted_publication(
    release_client: TestClient,
) -> None:
    r = release_client.get(f"/v1/dossier/jurisdiction:okc?release={'p-' + '9' * 64}")
    assert r.status_code == 404
    assert r.json()["code"] == "unknown_publication"


def test_coverage_serves_release_bytes(release_client: TestClient) -> None:
    r = release_client.get("/v1/coverage/jurisdiction:okc")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    assert r.json()["coverage"]["records"] == 3


def test_export_and_changes_and_sources(release_client: TestClient) -> None:
    r = release_client.get("/v1/export")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "release"
    assert r.json()["exports"][0]["name"] == "entities"

    r = release_client.get("/v1/changes")
    assert r.status_code == 200
    assert len(r.json()["events"]) == 2
    # since filters the fixed release snapshot the same way it filters the spine
    r = release_client.get("/v1/changes?since=2026-09-20")
    assert [e["artifact_id"] for e in r.json()["events"]] == ["art:2"]

    r = release_client.get("/v1/sources")
    assert r.status_code == 200
    assert r.json()["sources"][0]["source_id"] == "src_okc"
    r = release_client.get("/v1/sources/src_okc")
    assert r.status_code == 200
    assert r.json()["source_id"] == "src_okc"
    r = release_client.get("/v1/sources/src_missing")
    assert r.status_code == 404
    assert r.json()["code"] == "scope_not_available"


def test_releases_routes(release_client: TestClient) -> None:
    r = release_client.get("/v1/releases")
    assert r.status_code == 200
    body = r.json()
    assert {p["publication_id"] for p in body["publications"]} == {PUB_A, PUB_B}
    assert body["latest"]["publication_id"] == PUB_A
    assert body["release"]["publication_id"] == PUB_A

    r = release_client.get("/v1/releases/latest")
    assert r.status_code == 200
    assert r.json()["descriptor"]["data_release_id"] == LABEL_A
    assert r.json()["release"]["publication_id"] == PUB_A

    r = release_client.get(f"/v1/releases/{PUB_B}")
    assert r.status_code == 200
    assert r.json()["release"]["publication_id"] == PUB_B
    assert r.json()["publication"]["label"] == "sig-2026-09-01-fixture"

    r = release_client.get("/v1/releases/not-a-publication")
    assert r.status_code == 404
    assert r.json()["code"] == "unknown_publication"


def test_missing_singleton_artifact_is_honest_503(
    release_client: TestClient, registry: Path
) -> None:
    """A family file the release should carry but does not is a servability
    defect (V7's target), never a placeholder."""
    (registry / "staged" / f"r/{PUB_A}/api/export.json").unlink()
    r = release_client.get("/v1/export")
    assert r.status_code == 503
    assert r.json()["code"] == "release_artifact_absent"
    assert r.headers["Retry-After"] == "5"


# --------------------------------------------------------------------------- #
# The routes — live-spine basis stays live-spine                               #
# --------------------------------------------------------------------------- #


def test_live_spine_routes_carry_the_full_basis_block(store, registry: Path) -> None:
    store.spine_watermark = lambda: "claims=42 latest_assertion=2026-10-01"  # type: ignore[method-assign]
    client = TestClient(create_app(store, release_serving=ReleaseServingStore(registry)))
    r = client.get("/v1/contradiction")
    assert r.status_code == 200
    assert r.headers["x-sig-basis"] == "live-spine"
    basis = r.json()["basis"]
    assert basis["kind"] == "live-spine"
    assert basis["type"] == "live-spine"  # the P34.25 key is kept
    assert basis["spine_watermark"] == "claims=42 latest_assertion=2026-10-01"
    assert basis["watermark"] == basis["spine_watermark"]  # legacy key kept
    assert basis["as_of"] == basis["spine_watermark"]
    assert basis["latest_release"] == {
        "publication_id": PUB_A,
        "label": LABEL_A,
        "as_of_world": "2026-10-01",
    }


def test_live_spine_watermark_is_absent_not_fabricated(
    release_client: TestClient,
) -> None:
    """The seeded in-memory store has no spine watermark — the basis block
    discloses that by absence, never a fabricated value."""
    r = release_client.get("/v1/contradiction")
    basis = r.json()["basis"]
    assert basis["kind"] == "live-spine"
    assert "spine_watermark" not in basis
    assert "as_of" not in basis
    assert basis["latest_release"]["publication_id"] == PUB_A


def test_live_spine_basis_without_a_registry(client: TestClient) -> None:
    """Unconfigured (today's posture): the label degrades honestly — live-spine
    with no release pin, and the release-backed routes fall back to the spine."""
    r = client.get("/v1/contradiction")
    assert r.headers["x-sig-basis"] == "live-spine"
    basis = r.json()["basis"]
    assert basis["kind"] == "live-spine"
    assert "latest_release" not in basis
    # The dossier route keeps its live-spine answer.
    r = client.get("/v1/dossier/jurisdiction:okc")
    assert r.status_code in (200, 404)
    assert r.headers["x-sig-basis"] == "live-spine"
    # Registry-only routes honestly refuse.
    r = client.get("/v1/releases")
    assert r.status_code == 503
    assert r.json()["code"] == "release_serving_unconfigured"
    r = client.get("/v1/sources")
    assert r.status_code == 503


def test_released_search_route_is_release_basis(release_client: TestClient) -> None:
    """``/v1/releases/{pub}/compartments/{comp}/search`` serves release-pinned
    FTS5 bytes — its answers (and its refusals) carry the release class, never
    live-spine. The fixture registry has no search index, so the honest
    refusal is what's asserted."""
    r = release_client.get(f"/v1/releases/{PUB_A}/compartments/sig_graph/search?q=cam")
    assert r.headers["x-sig-basis"] == "release"
    assert r.headers.get("x-sig-release", "").endswith(PUB_A)
    # A malformed publication token is still a release-route refusal.
    r = release_client.get("/v1/releases/not-a-pub/compartments/sig_graph/search?q=cam")
    assert r.headers["x-sig-basis"] == "release"


# --------------------------------------------------------------------------- #
# Service routes name the release                                              #
# --------------------------------------------------------------------------- #


def test_health_and_root_name_the_release(
    release_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SIG_CODE_COMMIT", "deadbeefcafe")
    monkeypatch.setenv("SIG_IMAGE_DIGEST", "sha256:" + "0" * 64)
    r = release_client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["release"] == {
        "publication_id": PUB_A,
        "label": LABEL_A,
        "as_of_world": "2026-10-01",
    }
    assert body["code_commit"] == "deadbeefcafe"
    assert body["image"] == "sha256:" + "0" * 64
    r = release_client.get("/")
    assert r.json()["release"]["publication_id"] == PUB_A
    assert r.json()["code_commit"] == "deadbeefcafe"


def test_health_reports_no_release_unpinned(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["release"] is None
    assert r.json()["code_commit"] is None
    assert r.json()["image"] is None


# --------------------------------------------------------------------------- #
# Identity block                                                               #
# --------------------------------------------------------------------------- #


def test_identity_block_omits_absent_fields() -> None:
    assert ReleaseIdentity(publication_id="p-x").block() == {"publication_id": "p-x"}
    assert ReleaseIdentity(publication_id="p-x", label="lab").header() == "lab p-x"

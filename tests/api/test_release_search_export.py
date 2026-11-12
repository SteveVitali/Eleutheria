# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.43 / K3 SRCH-08 — the search-result export route
``GET /v1/releases/{pub or latest}/search/export``: a deterministic
``application/zip`` download of a result set (≤ 10,000 rows), per licence
group with licence files (J3 TX download conventions — results +
LICENCE.txt + ATTRIBUTION.txt per group, manifest.json + SHA256SUMS), the
same verified engine, withdrawal barrier, cache contract and dark-ship
posture as the federated route. Never a mixed-compartment file."""

from __future__ import annotations

import io
import json
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.demo import build_demo_store
from api.release_search_v2 import ReleaseSearchV2Store
from exports.release import ReleaseRegistry, activate, build_release
from exports.search_query_v2 import SearchEngineV2, parse_params_v2
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)
from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "exports"))
from test_release import REVISION, _write_export  # noqa: E402

COMP = "sig_graph"


@pytest.fixture
def released(tmp_path: Path) -> tuple[Path, str]:
    export = _write_export(tmp_path / "export", n_records=30)
    b = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    registry = tmp_path / "registry"
    activate(registry, b.out_dir)
    return registry, b.publication_id


@pytest.fixture
def client(released: tuple[Path, str], tmp_path: Path) -> TestClient:
    registry, _pub = released
    return TestClient(
        create_app(
            build_demo_store(),
            release_search_v2=ReleaseSearchV2Store(registry, cache_dir=tmp_path / "vcache"),
            search_v2="on",
        )
    )


def _export(client: TestClient, pub: str, **params):
    return client.get(f"/v1/releases/{pub}/search/export", params=params)


def _deny(registry: Path, kind: TargetKind, target: str, day: int = 27) -> None:
    reg = ReleaseRegistry(registry)
    entries = reg.withdrawals()
    entries.append(
        new_disposition(
            target_kind=kind,
            target_id=target,
            disposition=Disposition.WITHHOLD,
            reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
            authority="test-authority",
            decided_at=datetime(2026, 9, day, tzinfo=UTC),
        )
    )
    reg.save_withdrawals(entries)


def _members(resp) -> zipfile.ZipFile:
    return zipfile.ZipFile(io.BytesIO(resp.content))


def test_posture_off_mounts_nothing(released) -> None:
    registry, pub = released
    c = TestClient(
        create_app(
            build_demo_store(),
            release_search_v2=ReleaseSearchV2Store(registry),
            search_v2="off",
        )
    )
    r = _export(c, pub, q="Site", format="csv")
    assert r.status_code == 404


def test_csv_export_zip_shape(client: TestClient, released) -> None:
    _reg, pub = released
    r = _export(client, pub, q="Site", format="csv")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"].startswith("attachment;")
    assert r.headers["content-disposition"].endswith('-csv.zip"')
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"
    z = _members(r)
    names = set(z.namelist())
    assert {"manifest.json", "README.txt", "SHA256SUMS"} <= names
    for comp in (COMP, "osm_physical"):
        assert f"{comp}/results.csv" in names
        assert f"{comp}/LICENCE.txt" in names
        assert f"{comp}/ATTRIBUTION.txt" in names
    man = json.loads(z.read("manifest.json"))
    assert man["schema"] == "sig.search-export/1"
    assert man["release"]["publication_id"] == pub
    assert man["export"]["row_cap"] == 10_000
    assert man["export"]["exported_records"] > 0
    # Never a mixed-compartment file: each results.csv names only its own
    # compartment's rows and licence.
    sg = z.read(f"{COMP}/results.csv").decode()
    assert "# licence: CC-BY-4.0" in sg
    assert "record_key" in sg.splitlines()[-31] or "record_key" in sg
    osm = z.read("osm_physical/results.csv").decode()
    assert "# licence: ODbL-1.0" in osm
    sg_keys = {ln.split(",")[0] for ln in sg.splitlines() if ln.startswith(f"{COMP}:")}
    assert sg_keys and all(k.startswith(f"{COMP}:") for k in sg_keys)
    om_keys = {ln.split(",")[0] for ln in osm.splitlines() if ln.startswith("osm_physical:")}
    assert om_keys and all(k.startswith("osm_physical:") for k in om_keys)


def test_json_export(client: TestClient, released) -> None:
    _reg, pub = released
    r = _export(client, pub, q="Site", format="json")
    assert r.status_code == 200
    doc = json.loads(_members(r).read(f"{COMP}/results.json"))
    assert doc["schema"] == "sig.search-export-records/1"
    assert doc["compartment"] == COMP
    assert doc["rows"] and all(row["license"] == "CC-BY-4.0" for row in doc["rows"])


def test_default_format_is_csv(client: TestClient, released) -> None:
    _reg, pub = released
    r = _export(client, pub, q="Site")
    assert r.status_code == 200
    assert f"{COMP}/results.csv" in _members(r).namelist()


def test_latest_pointer_cache(client: TestClient, released) -> None:
    _reg, pub = released
    r = _export(client, "latest", q="Site", format="csv")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=300"
    man = json.loads(_members(r).read("manifest.json"))
    assert man["release"]["publication_id"] == pub


def test_collection_scope_one_group(client: TestClient, released) -> None:
    _reg, pub = released
    r = _export(client, pub, q="Site", collection=COMP, format="csv")
    assert r.status_code == 200
    names = _members(r).namelist()
    assert f"{COMP}/results.csv" in names
    assert "osm_physical/results.csv" not in names


def test_deterministic_bytes(client: TestClient, released) -> None:
    _reg, pub = released
    a = _export(client, pub, q="Site", format="csv").content
    b = _export(client, pub, q="Site", format="csv").content
    assert a == b


def test_refusals_422(client: TestClient, released) -> None:
    _reg, pub = released
    for params in (
        {"format": "yaml"},
        {"format": "html"},
        {"cursor": "sig_graph:abc"},
        {"limit": 10},
        {"bogus": "x"},
        {"within": "entity:ent-1"},
        {"location": "located"},
    ):
        r = _export(client, pub, **params)
        assert r.status_code == 422, (params, r.status_code, r.text[:200])


def test_unknown_publication_404(client: TestClient) -> None:
    assert _export(client, "not-a-publication").status_code == 404
    assert _export(client, "p-" + "0" * 64).status_code == 404


def test_withdrawal_410(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.RELEASE_ARTIFACT, pub, day=28)
    r = _export(client, pub, q="Site", format="csv")
    assert r.status_code == 410
    assert r.json()["code"] == "withdrawn"


def test_denial_barrier_never_exports_denied(client: TestClient, released) -> None:
    """An access-time-denied record is never exported, and the manifest
    counts the denial (DR-C4-09 carried) — the export mirrors the page."""
    registry, pub = released
    _deny(registry, TargetKind.ENTITY, "ent-src_a-0")
    r = _export(client, pub, format="csv")
    assert r.status_code == 200
    z = _members(r)
    sg = z.read(f"{COMP}/results.csv").decode()
    assert "ent-src_a-0" not in sg
    man = json.loads(z.read("manifest.json"))
    assert man["scope"]["excluded_records_by_reason"].get("safety_withdrawal", 0) >= 1


def test_row_cap_and_truncation(released) -> None:
    """The ≤ 10,000 bound: export_records honours an injected cap, keeps
    each group's exact matching total and marks the export truncated."""
    registry, pub = released
    engine = SearchEngineV2.open_release(registry / "staged", publication_id=pub)
    try:
        payload = engine.export_records(parse_params_v2(q="Site", limit=None), row_cap=3)
    finally:
        engine.close()
    export = payload["export"]
    assert export["exported_records"] == 3
    assert export["truncated"] is True
    assert sum(g["exported"] for g in export["groups"]) == 3
    assert any(g["total"] > g["exported"] for g in export["groups"])


def test_exported_rows_match_the_page_rows(client: TestClient, released) -> None:
    """The export enumerates what the page shows — the same record keys in
    the same compartments (never a second query path)."""
    _reg, pub = released
    page = client.get(f"/v1/releases/{pub}/search", params={"q": "Site"}).json()
    page_keys = {
        h["record_key"]
        for g in page["record_groups"]
        for h in g["results"]
    }
    z = _members(_export(client, pub, q="Site", format="json"))
    exported = set()
    for comp in (COMP, "osm_physical"):
        doc = json.loads(z.read(f"{comp}/results.json"))
        exported |= {r["record_key"] for r in doc["rows"]}
    assert page_keys <= exported


def test_openapi_lists_the_route(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/v1/releases/{publication_id}/search/export" in spec["paths"]


def test_html_page_advertises_the_export(client: TestClient, released) -> None:
    _reg, pub = released
    r = client.get(f"/v1/releases/{pub}/search", params={"q": "Site", "format": "html"})
    assert r.status_code == 200
    assert "Download these results" in r.text
    assert f"/v1/releases/{pub}/search/export?" in r.text
    assert "format=csv" in r.text and "format=json" in r.text
    assert "<script" not in r.text

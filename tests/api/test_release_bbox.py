# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.20 / K1 MAP-06 — the release-pinned bbox site list:

``GET /v1/releases/{pub or latest}/compartments/{comp}/sites?bbox=&page=``
(per-compartment JSON) and ``GET /v1/releases/{pub or latest}/sites`` (the
cross-compartment grouped answer — ``format=html`` or a browser Accept
selects the no-JS page) over the ``site_points`` R*Tree the P37.20 record
index emits. Verify-and-copy of the ``sig.release-search-index/2``
artifacts into a bounded set of verified publications, ``latest`` via the
conf-gen pointer, the access-time withdrawal barrier with scope-count
denials (DR-C4-09), ≤ 100 rows per page, the cache-header contract, the
no-query-logging pin, and the ``SIG_API_BBOX`` dark-ship posture (default
``off`` mounts nothing — the operator's roll is the flip, never
pre-authorised)."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.demo import build_demo_store
from api.rate_limit import RateLimitConfig
from api.release_bbox import ReleaseBboxStore, bbox_posture, parse_bbox, parse_page
from exports.release import ReleaseRegistry, activate, build_release
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
# The fixture points: lon = -97.5 + i*0.01, lat = 35.46 (test_release._site_row).
BBOX_ALL = "-98.0,35.0,-97.0,36.0"
BBOX_ONE = "-97.51,35.45,-97.49,35.47"  # only i=0 (-97.5, 35.46)
BBOX_NONE = "-90.0,40.0,-89.0,41.0"


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
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bcache"),
            bbox="on",
        )
    )


def _comp_sites(client: TestClient, pub: str, comp: str = COMP, **params):
    return client.get(f"/v1/releases/{pub}/compartments/{comp}/sites", params=params)


def _sites(client: TestClient, pub: str, **params):
    return client.get(f"/v1/releases/{pub}/sites", params=params)


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


# --------------------------------------------------------------------------- #
# The dark-ship posture (SIG_API_BBOX)                                        #
# --------------------------------------------------------------------------- #


def test_off_posture_mounts_nothing(released) -> None:
    """Default off: the routes are not mounted — the same 404 the routes
    gave before the code landed (the flip is the roll's)."""
    registry, pub = released
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry),
            bbox="off",
        )
    )
    assert _comp_sites(c, pub, bbox=BBOX_ALL).status_code == 404
    assert _sites(c, pub, bbox=BBOX_ALL).status_code == 404
    spec = c.get("/openapi.json").json()
    assert "/v1/releases/{publication_id}/sites" not in spec["paths"]
    assert "/v1/releases/{publication_id}/compartments/{compartment}/sites" not in spec["paths"]


def test_env_drives_the_posture(released, monkeypatch) -> None:
    registry, pub = released
    monkeypatch.setenv("SIG_API_BBOX", "on")
    c = TestClient(create_app(build_demo_store(), release_bbox=ReleaseBboxStore(registry)))
    assert _sites(c, pub, bbox=BBOX_ALL).status_code == 200
    monkeypatch.setenv("SIG_API_BBOX", "bogus")
    with pytest.raises(ValueError):
        create_app(build_demo_store())
    assert bbox_posture({}) == "off"
    assert bbox_posture({"SIG_API_BBOX": "on"}) == "on"


def test_enabled_without_store_503(released) -> None:
    c = TestClient(create_app(build_demo_store(), bbox="on"))
    r = _sites(c, "p-" + "0" * 64, bbox=BBOX_ALL)
    assert r.status_code == 503
    assert r.headers.get("retry-after") == "5"
    assert r.json()["code"] == "release_bbox_unconfigured"


# --------------------------------------------------------------------------- #
# bbox + page parsing                                                         #
# --------------------------------------------------------------------------- #


def test_parse_bbox_happy_and_antimeridian() -> None:
    assert parse_bbox("-98,35,-96,36") == [(-98.0, 35.0, -96.0, 36.0)]
    # Antimeridian crossing splits into two spans, never a clamp.
    assert parse_bbox("170,-10,-170,10") == [
        (170.0, -10.0, 180.0, 10.0),
        (-180.0, -10.0, -170.0, 10.0),
    ]


@pytest.mark.parametrize(
    "raw",
    [
        None,
        "",
        "1,2,3",
        "a,b,c,d",
        "-200,0,0,10",  # longitude out of range
        "0,-95,10,10",  # latitude out of range
        "0,10,10,5",  # south >= north
        "nan,0,10,10",
    ],
)
def test_parse_bbox_refuses(raw) -> None:
    from api.release_bbox import ReleaseBboxError

    with pytest.raises(ReleaseBboxError) as excinfo:
        parse_bbox(raw)
    assert excinfo.value.status == 422
    assert excinfo.value.code in {"missing_bbox", "invalid_bbox"}


def test_parse_page() -> None:
    assert parse_page(None) == 1
    assert parse_page("3") == 3
    from api.release_bbox import ReleaseBboxError

    for bad in ("0", "-1", "abc"):
        with pytest.raises(ReleaseBboxError):
            parse_page(bad)


# --------------------------------------------------------------------------- #
# Happy path — per-compartment JSON + cross-compartment grouped answer        #
# --------------------------------------------------------------------------- #


def test_compartment_json_envelope(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub, bbox=BBOX_ALL)
    assert r.status_code == 200
    body = r.json()
    assert body["schema"] == "sig.sites-bbox/1"
    assert body["release"]["publication_id"] == pub
    assert body["compartment"] == COMP
    assert body["license"]
    assert body["query"]["page_size"] == 100
    assert len(body["results"]) == 30
    assert body["scope"]["matched"] == 30
    row = body["results"][0]
    assert row["name"]
    assert row["location"]["kind"] == "point"
    assert row["location"]["lat"] == pytest.approx(35.46)
    assert row["location"]["precision"] == "full_precision"
    assert row["href"].startswith(f"/r/{pub}/c/{COMP}/entity/")
    assert row["json_href"].endswith(".json")
    assert r.headers["Cache-Control"] == "public, max-age=31536000, immutable"


def test_bbox_filters_points(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub, bbox=BBOX_ONE)
    assert r.status_code == 200
    body = r.json()
    assert body["scope"]["matched"] == 1
    assert len(body["results"]) == 1
    r2 = _comp_sites(client, pub, bbox=BBOX_NONE)
    assert r2.status_code == 200
    assert r2.json()["scope"]["matched"] == 0
    assert r2.json()["results"] == []


def test_grouped_json_envelope(client: TestClient, released) -> None:
    _reg, pub = released
    r = _sites(client, pub, bbox=BBOX_ALL)
    assert r.status_code == 200
    body = r.json()
    assert body["schema"] == "sig.sites-bbox/1"
    groups = {g["compartment"]: g for g in body["groups"]}
    assert {COMP, "osm_physical"} <= set(groups)
    # Compartments stay licence-separated — each group names its own licence.
    assert groups["osm_physical"]["license"].startswith("ODbL")
    assert groups[COMP]["license"] == "CC-BY-4.0"
    assert body["scope"]["matched"] == 60


def test_html_grouped_page(client: TestClient, released) -> None:
    _reg, pub = released
    r = _sites(client, pub, bbox=BBOX_ALL, format="html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    text = r.text
    assert "<script" not in text  # the no-JS surface ships no script (T0)
    assert "osm_physical" in text and "sig_graph" in text
    assert "ODbL-1.0" in text  # per-group licence line (compartments unmixed)
    assert "Site src_a" in text
    assert "/map/?bbox=" in text  # the "Open this area on the map" link
    # A browser Accept header selects the same representation.
    r2 = client.get(
        f"/v1/releases/{pub}/sites",
        params={"bbox": BBOX_ALL},
        headers={"accept": "text/html"},
    )
    assert "text/html" in r2.headers["content-type"]


def test_compartment_route_serves_html_too(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub, bbox=BBOX_ALL, format="html")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "osm_physical" not in r.text  # one group only


def test_latest_resolves_and_mutable_cache(client: TestClient, released) -> None:
    _reg, _pub = released
    r = _sites(client, "latest", bbox=BBOX_ALL)
    assert r.status_code == 200
    assert r.headers["Cache-Control"] == "public, max-age=300"


def test_page_bound_and_pagination(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub, bbox=BBOX_ALL, page="1")
    assert r.status_code == 200
    assert len(r.json()["results"]) == 30
    assert r.json()["page"]["has_more"] is False
    r2 = _comp_sites(client, pub, bbox=BBOX_ALL, page="2")
    assert r2.status_code == 200
    assert r2.json()["results"] == []


# --------------------------------------------------------------------------- #
# Refusals                                                                    #
# --------------------------------------------------------------------------- #


def test_missing_bbox_422(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub)
    assert r.status_code == 422
    assert r.json()["code"] == "missing_bbox"


def test_bad_bbox_422_html_error_page(client: TestClient, released) -> None:
    _reg, pub = released
    r = _sites(client, pub, bbox="bogus", format="html")
    assert r.status_code == 422
    assert "text/html" in r.headers["content-type"]
    assert "invalid_bbox" in r.text  # DR-C4-10: HTML error for HTML clients


def test_unknown_param_422(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub, bbox=BBOX_ALL, bogus="1")
    assert r.status_code == 422
    assert r.json()["code"] == "unsupported_query"


def test_unknown_publication_404(client: TestClient) -> None:
    r = _comp_sites(client, "p-" + "f" * 64, bbox=BBOX_ALL)
    assert r.status_code == 404
    assert r.json()["code"] == "unknown_publication"
    assert _comp_sites(client, "latest", bbox=BBOX_ALL).status_code in (200, 503)


def test_unknown_compartment_404(client: TestClient, released) -> None:
    _reg, pub = released
    r = _comp_sites(client, pub, comp="nope", bbox=BBOX_ALL)
    assert r.status_code == 404
    assert r.json()["code"] == "unknown_compartment"
    r2 = _comp_sites(client, pub, comp="web", bbox=BBOX_ALL)
    assert r2.status_code == 404
    assert r2.json()["code"] == "compartment_not_listable"


def test_no_spatial_index_typed_absence(released, tmp_path: Path) -> None:
    """A release whose record index predates P37.20 (no site_points) answers
    the honest typed absence — never an empty list as 'no sites'."""
    registry, pub = released
    # Rebuild a v2 index WITHOUT site_points and stage it over the real one.
    import sqlite3 as _sq

    idx = registry / "staged" / "r" / pub / "c" / COMP / "search_index_v2.sqlite"
    con = _sq.connect(idx)
    con.execute("DROP TABLE site_points")
    con.commit()
    con.close()
    # Re-pin the drifted bytes into the integrity manifest so verification
    # passes and the absence is what surfaces.
    import hashlib
    import json as _json

    mpath = registry / "staged" / "releases" / pub / "integrity_manifest.json"
    manifest = _json.loads(mpath.read_text())
    data = idx.read_bytes()
    for a in manifest["artifacts"]:
        if a["path"] == f"r/{pub}/c/{COMP}/search_index_v2.sqlite":
            a["sha256"] = hashlib.sha256(data).hexdigest()
            a["byte_size"] = len(data)
    mpath.write_text(_json.dumps(manifest))
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bc2"),
            bbox="on",
        )
    )
    r = _comp_sites(c, pub, bbox=BBOX_ALL)
    assert r.status_code == 404
    assert r.json()["code"] == "spatial_index_not_published"


def test_tampered_index_503(released, tmp_path: Path) -> None:
    registry, pub = released
    idx = registry / "staged" / "r" / pub / "c" / COMP / "search_index_v2.sqlite"
    idx.write_bytes(idx.read_bytes() + b"x")
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bc3"),
            bbox="on",
        )
    )
    r = _comp_sites(c, pub, bbox=BBOX_ALL)
    assert r.status_code == 503
    assert r.json()["code"] == "index_verification_failed"


# --------------------------------------------------------------------------- #
# The withdrawal barrier                                                      #
# --------------------------------------------------------------------------- #


def test_entity_deny_filters_and_counts(released, tmp_path: Path) -> None:
    registry, pub = released
    _deny(registry, TargetKind.ENTITY, "ent-src_a-0")
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bc4"),
            bbox="on",
        )
    )
    r = _comp_sites(c, pub, bbox=BBOX_ALL)
    assert r.status_code == 200
    body = r.json()
    assert body["scope"]["matched"] == 29
    assert body["scope"]["excluded_records_by_reason"] == {"safety_withdrawal": 1}
    eids = {row["entity"]["id"] for row in body["results"]}
    assert "ent-src_a-0" not in eids


def test_claim_deny_filters_via_claim_ref(released, tmp_path: Path) -> None:
    registry, pub = released
    _deny(registry, TargetKind.CLAIM, "claim-src_a-0-a")
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bc5"),
            bbox="on",
        )
    )
    body = _comp_sites(c, pub, bbox=BBOX_ALL).json()
    assert body["scope"]["matched"] == 29
    assert all("ent-src_a-0" != row["entity"]["id"] for row in body["results"])


def test_release_deny_410_whole(released, tmp_path: Path) -> None:
    """A release-namespace deny dominates every compartment group — both
    routes answer 410, never an empty list presented as 'no sites'."""
    registry, pub = released
    _deny(registry, TargetKind.RELEASE_ARTIFACT, pub, day=28)
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bc6"),
            bbox="on",
        )
    )
    r = _comp_sites(c, pub, bbox=BBOX_ALL)
    assert r.status_code == 410
    assert r.json()["code"] == "withdrawn"
    r2 = _sites(c, pub, bbox=BBOX_ALL)
    assert r2.status_code == 410


# --------------------------------------------------------------------------- #
# Privacy + rate limit surface                                                #
# --------------------------------------------------------------------------- #


def test_no_query_logging(client: TestClient, caplog) -> None:
    """A fixture query leaves no server-side log record — the bbox never
    persists (SIG-SRCH-012 / D-K3-4). The ``httpx`` record is the test
    client's OWN transport log (the requester's record, not the server's)
    and is excluded by name."""
    sentinel = "bbox-secret-9f27"
    with caplog.at_level(logging.DEBUG):
        _comp_sites(client, "latest", bbox=f"{sentinel},0,0,0")
    offenders = [
        r for r in caplog.records if sentinel in r.getMessage() and not r.name.startswith("httpx")
    ]
    assert not offenders, [f"{r.name}: {r.getMessage()}" for r in offenders]


def test_rate_limit_headers_on_route(released, tmp_path: Path) -> None:
    """The app-wide token bucket (P36.13) covers the route — the bbox list
    is not an escape hatch around the served limits."""
    registry, pub = released
    c = TestClient(
        create_app(
            build_demo_store(),
            release_bbox=ReleaseBboxStore(registry, cache_dir=tmp_path / "bc7"),
            bbox="on",
            rate_limit=RateLimitConfig(posture="enforce", trusted_proxy_hops=0),
        )
    )
    seen_429 = False
    for _ in range(40):
        if _comp_sites(c, pub, bbox=BBOX_ALL).status_code == 429:
            seen_429 = True
            break
    assert seen_429


def test_eviction_drops_copies(released, tmp_path: Path) -> None:
    """The bounded publication set evicts its verified local copies."""
    registry, pub = released
    store = ReleaseBboxStore(registry, cache_dir=tmp_path / "bc8", max_publications=1)
    c = TestClient(create_app(build_demo_store(), release_bbox=store, bbox="on"))
    assert _comp_sites(c, pub, bbox=BBOX_ALL).status_code == 200
    copied = store.cache_dir / pub
    assert copied.is_dir()
    # A second release pushes the first out of the bound.
    export2 = _write_export(tmp_path / "export2", n_records=5)
    b2 = build_release(export2, tmp_path / "rel2", renderer_revision=REVISION)
    activate(registry, b2.out_dir)
    assert _comp_sites(c, b2.publication_id, bbox=BBOX_ALL).status_code == 200
    assert not copied.exists()

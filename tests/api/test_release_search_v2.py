# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.38 / K3 SRCH-03 (SIG-UI-076, SIG-SRCH-001, SIG-SRCH-003, SIG-SRCH-012) —
the federated v2 search route ``GET /v1/releases/{pub or latest}/search``:
verify-and-copy of the ``sig.release-search-index/2`` artifacts into a bounded
LRU of open engines, ``latest`` via the conf-gen pointer, the access-time
withdrawal barrier with scope-count denials (DR-C4-09), the cache-header
contract, the no-query-logging pin, and the ``SIG_API_SEARCH_V2`` dark-ship
posture (default ``off`` mounts nothing — the operator's roll is the flip,
never pre-authorised). The v1 per-compartment route is untouched."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.demo import build_demo_store
from api.rate_limit import RateLimitConfig
from api.release_search_v2 import ReleaseSearchV2Store, search_v2_posture
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


def _search(client: TestClient, pub: str, **params):
    return client.get(f"/v1/releases/{pub}/search", params=params)


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
# The dark-ship posture (SIG_API_SEARCH_V2)                                    #
# --------------------------------------------------------------------------- #


def test_off_posture_mounts_nothing(released) -> None:
    """Default off: the route is not mounted — the same 404 the route gave
    before the code landed (v1 keeps serving; the flip is the roll's)."""
    registry, pub = released
    c = TestClient(
        create_app(
            build_demo_store(),
            release_search_v2=ReleaseSearchV2Store(registry),
            search_v2="off",
        )
    )
    assert _search(c, pub, q="Site").status_code == 404
    spec = c.get("/openapi.json").json()
    assert "/v1/releases/{publication_id}/search" not in spec["paths"]


def test_env_drives_the_posture(released, monkeypatch) -> None:
    registry, pub = released
    monkeypatch.setenv("SIG_API_SEARCH_V2", "on")
    c = TestClient(create_app(build_demo_store(), release_search_v2=ReleaseSearchV2Store(registry)))
    assert _search(c, pub, q="Site").status_code == 200
    monkeypatch.setenv("SIG_API_SEARCH_V2", "bogus")
    with pytest.raises(ValueError):
        create_app(build_demo_store())
    assert search_v2_posture({}) == "off"
    assert search_v2_posture({"SIG_API_SEARCH_V2": "on"}) == "on"


def test_enabled_without_store_503(released) -> None:
    c = TestClient(create_app(build_demo_store(), search_v2="on"))
    r = _search(c, "p-" + "0" * 64)
    assert r.status_code == 503
    assert r.headers.get("retry-after") == "5"
    assert r.json()["code"] == "release_search_v2_unconfigured"


# --------------------------------------------------------------------------- #
# Happy path — one request across every compartment (SIG-SRCH-001)             #
# --------------------------------------------------------------------------- #


def test_federated_json_envelope(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, q="Site")
    assert r.status_code == 200
    body = r.json()
    assert body["schema"] == "sig.search-results/2"
    assert body["release"]["publication_id"] == pub
    groups = {g["compartment"] for g in body["record_groups"]}
    assert {COMP, "osm_physical"} <= groups
    assert body["scope"]["records_indexed"] > 0
    for g in body["record_groups"]:
        assert g["license"]
        for hit in g["results"]:
            assert hit["href"].startswith(f"/r/{pub}/c/{g['compartment']}/entity/")
            assert hit["matched"]  # a stated match reason per result (SIG-SRCH-003)


def test_latest_resolves_the_pointer(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, "latest", q="Site")
    assert r.status_code == 200
    assert r.json()["release"]["publication_id"] == pub
    assert r.headers["cache-control"] == "public, max-age=300"


def test_pub_pinned_is_immutable(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, q="Site")
    assert r.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_identifier_lookup(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, q="ent-src_a-3")
    assert r.status_code == 200
    body = r.json()
    assert body["top"][0]["matched"] == "identifier"
    assert body["top"][0]["record_key"] == f"{COMP}:deployment:ent-src_a-3"


def test_type_filter(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, q="Site", type="record")
    assert r.status_code == 200
    assert r.json()["query"]["types"] == ["record"]
    r2 = _search(client, pub, q="Site", type="nonsense")
    assert r2.status_code == 422


def test_group_cursor_round_trip(client: TestClient, released) -> None:
    _reg, pub = released
    r1 = _search(client, pub, limit=1)
    assert r1.status_code == 200
    body = r1.json()
    group = next(g for g in body["record_groups"] if g["total"] > 1)
    cursor = group["next_cursor"]
    assert cursor and cursor.startswith(f"{group['compartment']}:")
    r2 = _search(client, pub, limit=1, cursor=cursor)
    assert r2.status_code == 200
    first_keys = {h["record_key"] for g in body["record_groups"] for h in g["results"]}
    for h in next(
        g for g in r2.json()["record_groups"] if g["compartment"] == group["compartment"]
    )["results"]:
        assert h["record_key"] not in first_keys


def test_openapi_lists_the_route(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert "/v1/releases/{publication_id}/search" in spec["paths"]


# --------------------------------------------------------------------------- #
# Explicit error states                                                        #
# --------------------------------------------------------------------------- #


def test_unknown_and_malformed_publication_404(client: TestClient) -> None:
    assert _search(client, "p-" + "0" * 64).status_code == 404
    r = _search(client, "not-a-publication")
    assert r.status_code == 404 and r.json()["code"] == "unknown_publication"


def test_unsupported_params_422(client: TestClient, released) -> None:
    _reg, pub = released
    for params in (
        {"bogus": "x"},
        {"limit": 0},
        {"limit": 51},
        {"q": "x" * 201},
        {"cursor": "%%%bad%%%"},
        {"format": "yaml"},
    ):
        r = _search(client, pub, **params)
        assert r.status_code == 422, (params, r.status_code)


def test_cursor_context_mismatch_409(client: TestClient, released) -> None:
    _reg, pub = released
    cursor = next(
        g["next_cursor"]
        for g in _search(client, pub, q="Site", limit=1).json()["record_groups"]
        if g["next_cursor"]
    )
    r = _search(client, pub, q="Camera", cursor=cursor)
    assert r.status_code == 409
    assert r.json()["code"] == "cursor_context_mismatch"


def test_format_html_is_a_typed_501(client: TestClient, released) -> None:
    """P36.39 owns the no-JS representation — an explicit 501, never silent
    JSON served as the negotiated type."""
    _reg, pub = released
    r = _search(client, pub, format="html")
    assert r.status_code == 501
    assert r.json()["code"] == "html_representation_pending"


def test_tampered_index_bytes_refused(client: TestClient, released, tmp_path: Path) -> None:
    registry, pub = released
    victim = registry / "staged" / f"r/{pub}/c/{COMP}/search_index_v2.sqlite"
    victim.write_bytes(victim.read_bytes() + b"tamper")
    r = _search(client, pub, q="Site")
    assert r.status_code == 503
    assert r.json()["code"] == "index_verification_failed"


def test_missing_index_file_503(released, tmp_path: Path) -> None:
    registry, pub = released
    (registry / "staged" / f"r/{pub}/c/{COMP}/search_index_v2.sqlite").unlink()
    c = TestClient(
        create_app(
            build_demo_store(),
            release_search_v2=ReleaseSearchV2Store(registry, cache_dir=tmp_path / "vc2"),
            search_v2="on",
        )
    )
    r = _search(c, pub, q="Site")
    assert r.status_code == 503
    assert r.headers.get("retry-after") == "5"
    assert r.json()["code"] == "index_not_staged"


def test_v1_era_release_404s_v2(released, tmp_path: Path) -> None:
    """A release carrying no sig.release-search-index/2 entries answers 404
    v2_indexes_not_published — the v1 route keeps working for it."""
    registry, pub = released
    manifest_path = registry / "staged" / f"releases/{pub}/integrity_manifest.json"
    manifest = __import__("json").loads(manifest_path.read_text())
    v2 = ("search_index_v2", "claim_ref", "catalog")
    manifest["artifacts"] = [
        a for a in manifest["artifacts"] if not any(k in a["path"] for k in v2)
    ]
    manifest_path.write_text(__import__("json").dumps(manifest))
    c = TestClient(
        create_app(
            build_demo_store(),
            release_search_v2=ReleaseSearchV2Store(registry, cache_dir=tmp_path / "vc3"),
            search_v2="on",
        )
    )
    r = _search(c, pub, q="Site")
    assert r.status_code == 404
    assert r.json()["code"] == "v2_indexes_not_published"


# --------------------------------------------------------------------------- #
# The withdrawal barrier + scope-count denials (DR-C4-09)                      #
# --------------------------------------------------------------------------- #


def test_entity_withdrawal_filters_and_counts(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.ENTITY, "ent-src_a-0")
    r = _search(client, pub, q="ent-src_a-0")
    assert r.status_code == 200
    body = r.json()
    assert all(
        "ent-src_a-0" not in h["record_key"] for g in body["record_groups"] for h in g["results"]
    )
    assert body["scope"]["excluded_records_by_reason"]["safety_withdrawal"] >= 1


def test_claim_withdrawal_filters_carrier(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.CLAIM, "claim-src_a-1-a")
    r = _search(client, pub)
    assert f"{COMP}:deployment:ent-src_a-1" not in {
        h["record_key"] for g in r.json()["record_groups"] for h in g["results"]
    }


def test_release_withdrawal_410(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.RELEASE_ARTIFACT, pub, day=28)
    r = _search(client, pub, q="Site")
    assert r.status_code == 410
    assert r.json()["code"] == "withdrawn"
    assert r.json()["tombstone"]["reason_category"] == "safety_withdrawal"


# --------------------------------------------------------------------------- #
# Privacy (SIG-SRCH-012) + the rate-limit surface (P36.13)                     #
# --------------------------------------------------------------------------- #


def test_no_query_logging(client: TestClient, released, caplog) -> None:
    """A fixture query leaves no server-side log record — the query string
    never persists (SIG-SRCH-012 / D-K3-4). The ``httpx`` record is the
    test client's OWN transport log (the requester's record, not the
    server's) and is excluded by name."""
    _reg, pub = released
    sentinel = "unique-sentinel-query-9xq7"
    with caplog.at_level(logging.DEBUG):
        assert _search(client, pub, q=sentinel).status_code == 200
        assert _search(client, "latest", q=sentinel).status_code == 200
    offenders = [
        r for r in caplog.records if sentinel in r.getMessage() and not r.name.startswith("httpx")
    ]
    assert not offenders, [f"{r.name}: {r.getMessage()}" for r in offenders]


def test_rate_limit_covers_the_v2_route(released, tmp_path: Path) -> None:
    registry, pub = released
    c = TestClient(
        create_app(
            build_demo_store(),
            release_search_v2=ReleaseSearchV2Store(registry, cache_dir=tmp_path / "vc4"),
            search_v2="on",
            rate_limit=RateLimitConfig(posture="enforce", trusted_proxy_hops=0),
        )
    )
    assert _search(c, pub, q="Site").status_code == 200
    assert _search(c, pub, q="Site").headers.get("ratelimit-limit") == "30"
    seen_429 = False
    for _ in range(40):
        if _search(c, pub, q="Site").status_code == 429:
            seen_429 = True
            break
    assert seen_429


def test_engine_survives_cross_thread_use(client: TestClient, released) -> None:
    """P36.38 CI fix-arc: the LRU-cached engine's connections are created on
    one threadpool thread and used on another (P36.32's open() now carries
    ``check_same_thread=False``). Two sequential requests force the store to
    serve an engine whose conns outlive their creating thread — a regression
    here re-raises sqlite3.ProgrammingError."""
    from concurrent.futures import ThreadPoolExecutor

    _reg, pub = released
    assert _search(client, pub, q="Site").status_code == 200
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda q: _search(client, pub, q="Site").status_code, range(8)))
    assert all(code == 200 for code in results)


# --------------------------------------------------------------------------- #
# The LRU bound                                                                #
# --------------------------------------------------------------------------- #


def test_lru_evicts_oldest_publication(released, tmp_path: Path) -> None:
    registry, pub = released
    store = ReleaseSearchV2Store(registry, cache_dir=tmp_path / "lru", max_engines=1)
    from exports.search_query_v2 import parse_params_v2

    params = parse_params_v2(q="Site", limit=1)
    store.search(pub, params)
    assert (tmp_path / "lru" / pub).is_dir()
    # A second publication forces eviction — the copies drop with the engine.
    export = _write_export(tmp_path / "export2", n_records=5)
    b2 = build_release(export, tmp_path / "rel2", renderer_revision=REVISION)
    activate(registry, b2.out_dir)
    store.search(b2.publication_id, params)
    assert not (tmp_path / "lru" / pub).exists()
    assert (tmp_path / "lru" / b2.publication_id).is_dir()
    assert store.readiness()["open_engines"] == 1

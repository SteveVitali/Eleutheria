# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.14 / ADR-133 (SIG-FIND-003) — released-corpus search serving: verified
read-only FTS5 index access behind the existing read API, JSON + no-JS HTML
representations, the access-time withdrawal barrier, explicit 404/410/409/422/
503 states, and the ≤50-row / ≤100 KiB response bounds. No current-only PG
fallback exists beneath released pages."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from api.app import create_app
from api.demo import build_demo_store
from api.release_search import ReleaseSearchStore
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
def client(released: tuple[Path, str]) -> TestClient:
    registry, _pub = released
    return TestClient(create_app(build_demo_store(), release_search=ReleaseSearchStore(registry)))


def _search(client: TestClient, pub: str, comp: str = COMP, **params):
    return client.get(f"/v1/releases/{pub}/compartments/{comp}/search", params=params)


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
# Happy path                                                                   #
# --------------------------------------------------------------------------- #


def test_search_json_envelope(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, q="Site")
    assert r.status_code == 200
    body = r.json()
    assert body["publication_id"] == pub and body["compartment"] == COMP
    assert body["license"] == "CC-BY-4.0"
    assert body["scope"]["indexed_records"] == 30
    assert body["scope"]["eligible_records"] == 30
    assert body["total_matches"] == {"value": None, "relation": "not_computed"}
    assert len(body["results"]) == 30
    hit = body["results"][0]
    assert hit["href"].startswith(f"/r/{pub}/c/{COMP}/entity/")
    assert hit["record_key"].startswith(f"{COMP}:")


def test_row_bound_and_response_size(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, limit=50)
    assert r.status_code == 200 and len(r.json()["results"]) == 30
    # ≤100 KiB compressed bound — far under at this size
    assert len(r.content) < 100 * 1024


def test_exact_id_route(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, q="ent-src_a-3")
    assert r.status_code == 200
    body = r.json()
    assert body["query"]["exact_id"] is True
    assert [h["record_key"] for h in body["results"]] == [f"{COMP}:deployment:ent-src_a-3"]


def test_pagination_exhaustion(client: TestClient, released, tmp_path: Path) -> None:
    # a bigger corpus: rebuild with 130 records so pages turn
    export = _write_export(tmp_path / "big", n_records=130, two_compartments=False)
    b = build_release(export, tmp_path / "big-rel", renderer_revision=REVISION)
    registry = tmp_path / "big-reg"
    activate(registry, b.out_dir)
    c = TestClient(create_app(build_demo_store(), release_search=ReleaseSearchStore(registry)))
    seen: set[str] = set()
    cursor = None
    for _page in range(10):
        r = _search(c, b.publication_id, limit=50, cursor=cursor)
        assert r.status_code == 200
        body = r.json()
        assert len(body["results"]) <= 50
        for h in body["results"]:
            assert h["record_key"] not in seen  # no duplicates across pages
            seen.add(h["record_key"])
        cursor = body["next_cursor"]
        if cursor is None:
            break
    else:
        pytest.fail("pagination never terminated")
    assert len(seen) == 130


def test_cross_compartment_isolation(client: TestClient, released) -> None:
    _reg, pub = released
    # osm rows never appear in a sig_graph answer and vice versa
    for comp, prefix in ((COMP, "src_a"), ("osm_physical", "src_osm")):
        r = _search(client, pub, comp=comp)
        assert r.status_code == 200
        for h in r.json()["results"]:
            assert h["record_key"].startswith(f"{comp}:")
            assert h["sources"] == [prefix] or h["sources"] != []


def test_no_js_html_representation(client: TestClient, released) -> None:
    _reg, pub = released
    r = client.get(
        f"/v1/releases/{pub}/compartments/{COMP}/search",
        params={"q": "Site"},
        headers={"Accept": "text/html"},
    )
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<script" not in r.text.lower()
    # results + the form + compartment identity
    assert "ent-src_a-0" in r.text
    assert 'name="q"' in r.text and 'method="get"' in r.text.lower()
    assert COMP in r.text and pub in r.text
    # explicit format param selects the same representation
    r2 = _search(client, pub, format="html")
    assert "text/html" in r2.headers["content-type"]


# --------------------------------------------------------------------------- #
# Explicit error states                                                        #
# --------------------------------------------------------------------------- #


def test_unknown_publication_404(client: TestClient) -> None:
    r = _search(client, "p-" + "0" * 64)
    assert r.status_code == 404 and r.json()["code"] == "unknown_publication"


def test_malformed_publication_404(client: TestClient) -> None:
    r = _search(client, "not-a-publication")
    assert r.status_code == 404


def test_unknown_compartment_404(client: TestClient, released) -> None:
    _reg, pub = released
    r = _search(client, pub, comp="nonexistent")
    assert r.status_code == 404 and r.json()["code"] == "unknown_compartment"


def test_release_search_unconfigured_503() -> None:
    c = TestClient(create_app(build_demo_store()))
    r = _search(c, "p-" + "0" * 64)
    assert r.status_code == 503
    assert r.headers.get("retry-after") == "5"
    assert r.json()["code"] == "release_search_unconfigured"


def test_cold_index_503(released) -> None:
    registry, pub = released
    victim = registry / "staged" / f"r/{pub}/c/{COMP}/search_index.sqlite"
    victim.unlink()
    c = TestClient(create_app(build_demo_store(), release_search=ReleaseSearchStore(registry)))
    r = _search(c, pub)
    assert r.status_code == 503
    assert r.headers.get("retry-after") == "5"
    assert r.json()["code"] == "index_not_staged"


def test_unsupported_params_422(client: TestClient, released) -> None:
    _reg, pub = released
    assert _search(client, pub, bogus="x").status_code == 422
    assert _search(client, pub, limit=0).status_code == 422
    assert _search(client, pub, limit=51).status_code == 422
    assert _search(client, pub, limit="abc").status_code == 422
    assert _search(client, pub, location="nope").status_code == 422
    assert _search(client, pub, q="x" * 201).status_code == 422
    r = _search(client, pub, q="zz")
    assert r.status_code == 422 and r.json()["code"] == "query_too_short"


def test_cursor_context_mismatch_409(client: TestClient, released) -> None:
    _reg, pub = released
    r1 = _search(client, pub, q="Site", limit=10)
    cursor = r1.json()["next_cursor"]
    r2 = _search(client, pub, q="Camera", cursor=cursor)
    assert r2.status_code == 409 and r2.json()["code"] == "cursor_context_mismatch"
    r3 = _search(client, pub, comp="osm_physical", q="Site", cursor=cursor)
    assert r3.status_code == 409
    r4 = _search(client, pub, cursor="%%%bad%%%")
    assert r4.status_code == 422


# --------------------------------------------------------------------------- #
# The withdrawal barrier (access time)                                         #
# --------------------------------------------------------------------------- #


def test_entity_withdrawal_filters_result(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.ENTITY, "ent-src_a-0")
    r = _search(client, pub, q="ent-src_a-0")
    assert r.status_code == 200
    assert all("ent-src_a-0" not in h["record_key"] for h in r.json()["results"])
    # ...and it never appears in browse pages either
    r2 = _search(client, pub)
    assert all("ent-src_a-0" not in h["record_key"] for h in r2.json()["results"])


def test_claim_withdrawal_filters_carriers(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.CLAIM, "claim-src_a-1-a")
    r = _search(client, pub)
    assert f"{COMP}:deployment:ent-src_a-1" not in {h["record_key"] for h in r.json()["results"]}


def test_release_withdrawal_410(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.RELEASE_ARTIFACT, pub, day=28)
    r = _search(client, pub)
    assert r.status_code == 410
    assert r.json()["code"] == "withdrawn"
    assert r.json()["tombstone"]["reason_category"] == "safety_withdrawal"


def test_allow_after_deny_restores(client: TestClient, released) -> None:
    registry, pub = released
    reg = ReleaseRegistry(registry)
    _deny(registry, TargetKind.ENTITY, "ent-src_a-0")
    entries = reg.withdrawals() + [
        new_disposition(
            target_kind=TargetKind.ENTITY,
            target_id="ent-src_a-0",
            disposition=Disposition.ALLOW,
            reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
            authority="test-authority",
            decided_at=datetime(2026, 9, 29, tzinfo=UTC),
        )
    ]
    reg.save_withdrawals(entries)
    r = _search(client, pub, q="ent-src_a-0")
    assert r.status_code == 200
    assert any("ent-src_a-0" in h["record_key"] for h in r.json()["results"])


# --------------------------------------------------------------------------- #
# Tamper / verification                                                        #
# --------------------------------------------------------------------------- #


def test_tampered_index_bytes_refused(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", n_records=10)
    b = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    registry = tmp_path / "registry"
    activate(registry, b.out_dir)
    idx = registry / "staged" / f"r/{b.publication_id}/c/{COMP}/search_index.sqlite"
    idx.write_bytes(idx.read_bytes() + b"tamper")
    c = TestClient(create_app(build_demo_store(), release_search=ReleaseSearchStore(registry)))
    r = _search(c, b.publication_id)
    assert r.status_code == 503
    assert r.json()["code"] == "index_verification_failed"


# --------------------------------------------------------------------------- #
# P34.36 — release-search states                                               #
# (C4 NEW-4 empty copy, NEW-12 scope counts, NEW-13 HTML errors, NEW-28        #
# pager/copy, NEW-29 pseudo-compartment; DR-C4-05/09/10)                       #
# --------------------------------------------------------------------------- #


def _html_get(client: TestClient, pub: str, comp: str = COMP, *, by: str, **params):
    """One GET as an HTML client — ``by='accept'`` negotiates the header,
    ``by='format'`` uses the explicit ``format=html`` param."""
    headers = {"Accept": "text/html"} if by == "accept" else {}
    if by == "format":
        params = {**params, "format": "html"}
    return client.get(
        f"/v1/releases/{pub}/compartments/{comp}/search",
        params=params,
        headers=headers,
    )


def _assert_html_error(r, status: int, code: str) -> None:
    assert r.status_code == status, r.text
    assert "text/html" in r.headers["content-type"]
    assert "<html" in r.text and "<script" not in r.text.lower()
    assert code in r.text


@pytest.mark.parametrize("by", ["accept", "format"])
def test_html_client_gets_html_error_pages(client: TestClient, released, by: str) -> None:
    """C4 NEW-13 / DR-C4-10: every error status answers an HTML client with an
    HTML page — never a raw JSON body a no-JS reader cannot use."""
    registry, pub = released
    # a real cursor minted for one filter set, replayed under another → 409
    cursor = _search(client, pub, q="Site", limit=10).json()["next_cursor"]
    cases: list[tuple[int, str, str, str, dict]] = [
        (404, "unknown_publication", "p-" + "0" * 64, COMP, {}),
        (404, "unknown_publication", "not-a-publication", COMP, {}),
        (404, "unknown_compartment", pub, "nonexistent", {}),
        (404, "compartment_not_searchable", pub, "web", {}),
        (404, "compartment_not_searchable", pub, "metadata", {}),
        (409, "cursor_context_mismatch", pub, COMP, {"q": "Camera", "cursor": cursor}),
        (422, "query_too_short", pub, COMP, {"q": "zz"}),
        (422, "unsupported_query", pub, COMP, {"bogus": "x"}),
        (422, "unsupported_query", pub, COMP, {"limit": 0}),
        (422, "malformed_cursor", pub, COMP, {"cursor": "%%%bad%%%"}),
    ]
    for status, code, target, comp, kw in cases:
        _assert_html_error(_html_get(client, target, comp, by=by, **kw), status, code)
    # whole-release withdrawal → 410 (last: it denies every later request)
    _deny(registry, TargetKind.RELEASE_ARTIFACT, pub, day=28)
    _assert_html_error(_html_get(client, pub, COMP, by=by), 410, "withdrawn")


def test_410_html_carries_the_tombstone_category(client: TestClient, released) -> None:
    registry, pub = released
    _deny(registry, TargetKind.RELEASE_ARTIFACT, pub, day=28)
    r = _html_get(client, pub, by="accept")
    assert r.status_code == 410
    assert "text/html" in r.headers["content-type"]
    assert "safety_withdrawal" in r.text


def test_html_error_on_cold_index_503(released) -> None:
    registry, pub = released
    victim = registry / "staged" / f"r/{pub}/c/{COMP}/search_index.sqlite"
    victim.unlink()
    c = TestClient(create_app(build_demo_store(), release_search=ReleaseSearchStore(registry)))
    for by in ("accept", "format"):
        r = _html_get(c, pub, by=by)
        assert r.status_code == 503 and "text/html" in r.headers["content-type"]
        assert "index_not_staged" in r.text
        assert r.headers.get("retry-after") == "5"


def test_html_error_when_search_unconfigured_503() -> None:
    c = TestClient(create_app(build_demo_store()))
    for by in ("accept", "format"):
        r = _html_get(c, "p-" + "0" * 64, by=by)
        assert r.status_code == 503 and "text/html" in r.headers["content-type"]
        assert "release_search_unconfigured" in r.text


def test_validation_422_is_html_for_html_clients(client: TestClient, released) -> None:
    """``limit=abc`` fails FastAPI parsing before the handler — a RequestValidationError,
    not a SearchIndexError. It still owes an HTML client an HTML page."""
    _reg, pub = released
    for by in ("accept", "format"):
        r = _html_get(client, pub, by=by, limit="abc")
        assert r.status_code == 422 and "text/html" in r.headers["content-type"]
    # a JSON client gets the same 422 as a plain JSON body
    r = client.get(
        f"/v1/releases/{pub}/compartments/{COMP}/search",
        params={"limit": "abc"},
        headers={"Accept": "application/json"},
    )
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/json")


def test_json_clients_keep_json_errors(client: TestClient, released) -> None:
    """Back-compat: without an HTML signal the JSON error body is unchanged."""
    _reg, pub = released
    r = client.get(
        f"/v1/releases/{pub}/compartments/{COMP}/search",
        params={"q": "zz"},
    )
    assert r.status_code == 422
    assert r.headers["content-type"].startswith("application/json")
    assert r.json()["code"] == "query_too_short"
    # a JSON-accept client is never handed the HTML page
    r2 = client.get(
        f"/v1/releases/{pub}/compartments/{COMP}/search",
        params={"q": "zz"},
        headers={"Accept": "application/json"},
    )
    assert r2.status_code == 422
    assert r2.headers["content-type"].startswith("application/json")


def test_empty_result_html_states_only_the_mismatch(client: TestClient, released) -> None:
    """C4 NEW-4 / DR-C4-05: the no-match page says no released record in this
    compartment matches — never 'recorded absence' or a research claim."""
    _reg, pub = released
    for by in ("accept", "format"):
        r = _html_get(client, pub, by=by, q="zzqx-nonexistent")
        assert r.status_code == 200 and "text/html" in r.headers["content-type"]
        assert "no released record in this compartment matches" in r.text.lower()
        assert "recorded absence" not in r.text.lower()
        assert "missing research" not in r.text.lower()


def test_scope_counts_access_time_denials(client: TestClient, released) -> None:
    """C4 NEW-12 / DR-C4-09: denials recorded AFTER activation are counted in
    the scope — eligible drops, exclusions carry the public-safe reason."""
    registry, pub = released
    _deny(registry, TargetKind.ENTITY, "ent-src_a-0")  # one record
    _deny(registry, TargetKind.CLAIM, "claim-src_a-1-a")  # one carrier record
    r = _search(client, pub)
    scope = r.json()["scope"]
    assert scope["indexed_records"] == 30  # the pinned index truth, unmoved
    assert scope["eligible_records"] == 28
    assert scope["excluded_records_by_reason"] == {"safety_withdrawal": 2}
    # …and the HTML summary agrees with the JSON scope (humanised label)
    r2 = _html_get(client, pub, by="accept")
    assert "28 eligible" in r2.text and "safety withdrawal" in r2.text


def test_pager_uses_the_requested_limit(client: TestClient, released, tmp_path: Path) -> None:
    """C4 NEW-28: 'next N' names N — the requested page size."""
    export = _write_export(tmp_path / "big", n_records=130, two_compartments=False)
    b = build_release(export, tmp_path / "big-rel", renderer_revision=REVISION)
    registry = tmp_path / "big-reg"
    activate(registry, b.out_dir)
    c = TestClient(create_app(build_demo_store(), release_search=ReleaseSearchStore(registry)))
    r = _html_get(c, b.publication_id, by="format", limit="10")
    assert r.status_code == 200
    assert "next 10" in r.text and "next 50" not in r.text


def test_no_raw_enums_or_duplicated_copy_in_html(client: TestClient, released) -> None:
    """C4 NEW-28: no raw enum names as visible labels and no duplicated
    gate/browse text."""
    _reg, pub = released
    r = _html_get(client, pub, by="accept", q="Site")
    assert ">public-point<" not in r.text and ">no-public-point<" not in r.text
    assert r.text.count("static browse") <= 1


def test_non_record_compartment_is_404_not_searchable(
    client: TestClient, released, tmp_path: Path
) -> None:
    """C4 NEW-29 (pseudo-compartment part): `web` is a page surface, never a
    searchable record compartment — 404 'compartment_not_searchable', not the
    readiness 503. Even if a ``c/web`` dir is staged, the answer is the same."""
    registry, pub = released
    # mirror the observed state: a c/web dir exists (page artifacts)
    webdir = registry / "staged" / f"r/{pub}/c/web"
    webdir.mkdir(parents=True, exist_ok=True)
    (webdir / "index.html").write_text("<p>web surface</p>", encoding="utf-8")
    for comp in ("web", "metadata", "code", "ontology"):
        r = _search(client, pub, comp=comp)
        assert r.status_code == 404, (comp, r.text)
        assert r.json()["code"] == "compartment_not_searchable"
        r_html = _html_get(client, pub, comp, by="accept")
        assert r_html.status_code == 404
        assert "text/html" in r_html.headers["content-type"]
    # a genuinely absent compartment keeps its distinct 404
    r = _search(client, pub, comp="no_such_compartment")
    assert r.status_code == 404 and r.json()["code"] == "unknown_compartment"

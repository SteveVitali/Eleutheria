# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.14 / ADR-133 (SIG-FIND-003) — the deterministic per-compartment SQLite
FTS5 release index: byte-determinism, the normalized record/identifier/facet
tables, exact-id lookup, facet filters, keyset cursors, access-time
withdrawals, explicit empty/unsupported answers and the 2 s query budget."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from exports.search_index import (
    APPLICATION_ID,
    INDEX_DESCRIPTOR_FILE,
    INDEX_FILE,
    SEARCH_INDEX_SCHEMA,
    SEARCH_INDEX_VERSION,
    SearchIndexError,
    build_search_index,
    check_index_contract,
    decode_cursor,
    encode_cursor,
    facet_values,
    fts_match,
    index_descriptor_from_file,
    normalize_query,
    normalize_sort_key,
    parse_params,
    search,
)

PUB = "p-" + "ab" * 32
COMP = "sig_graph"


def _rows(n: int = 120) -> list[dict]:
    rows = []
    for i in range(n):
        rows.append(
            {
                "record_key": f"{COMP}:deployment:ent-{i:04d}",
                "entity_id": f"ent-{i:04d}",
                "entity_type": "deployment",
                "label": (f"Camera Site {i} OKC" if i % 7 else f"Ünïcödé stand {i}"),
                "jurisdiction": "OK" if i % 3 else None,
                "location_kind": "public-point" if i % 5 else "no-public-point",
                "source_id": "src_a" if i % 2 else "src_b",
                "technology": "alpr" if i % 11 == 0 else "",
                "claim_ids": [f"claim-{i}-a", f"claim-{i}-b"],
            }
        )
    return rows


def _build(tmp_path: Path, n: int = 120) -> tuple[Path, dict]:
    out = tmp_path / INDEX_FILE
    desc = build_search_index(
        _rows(n), publication_id=PUB, compartment=COMP, license_id="CC-BY-4.0", out=out
    )
    return out, desc


def _conn(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def _params(**kw) -> object:
    kw.setdefault("q", None)
    kw.setdefault("kind", None)
    kw.setdefault("jurisdiction", None)
    kw.setdefault("source", None)
    kw.setdefault("location", None)
    kw.setdefault("technology", None)
    kw.setdefault("limit", None)
    kw.setdefault("cursor", None)
    kw.setdefault("extra", ())
    return parse_params(**kw)


# --------------------------------------------------------------------------- #
# Determinism + contract                                                       #
# --------------------------------------------------------------------------- #


def test_identical_inputs_identical_bytes(tmp_path: Path) -> None:
    a, _ = _build(tmp_path / "a")
    b, _ = _build(tmp_path / "b")
    assert a.read_bytes() == b.read_bytes()


def test_different_inputs_different_bytes(tmp_path: Path) -> None:
    a, _ = _build(tmp_path / "a")
    rows = _rows()
    rows[0]["label"] = "renamed"
    out = tmp_path / "b" / INDEX_FILE
    build_search_index(rows, publication_id=PUB, compartment=COMP, license_id="CC-BY-4.0", out=out)
    assert a.read_bytes() != out.read_bytes()


def test_descriptor_and_meta_contract(tmp_path: Path) -> None:
    path, desc = _build(tmp_path)
    assert desc["schema"] == SEARCH_INDEX_SCHEMA
    assert desc["version"] == SEARCH_INDEX_VERSION
    assert desc["scope"] == {
        "indexed_records": 120,
        "eligible_records": 120,
        "excluded_records_by_reason": {},
    }
    assert desc["format"]["tokenizer"] == "unicode61"
    assert desc["sqlite_version"] == sqlite3.sqlite_version
    # meta re-read from the file reconciles with the emitted descriptor
    again = index_descriptor_from_file(path)
    for k in ("schema", "version", "publication_id", "compartment", "license", "scope"):
        assert again[k] == desc[k]
    conn = _conn(path)
    meta = check_index_contract(conn)
    assert meta["scope"]["indexed_records"] == 120
    # physical layout pins
    (appid,) = conn.execute("PRAGMA application_id").fetchone()
    (psize,) = conn.execute("PRAGMA page_size").fetchone()
    assert appid == APPLICATION_ID and psize == 4096
    conn.close()


def test_index_includes_unlocated_and_unknown_jurisdiction(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=60)
    conn = _conn(path)
    meta = check_index_contract(conn)
    # i % 5 == 0 rows are unlocated; i % 3 == 0 rows are unreported-jurisdiction
    n_unlocated = sum(1 for r in _rows(60) if r["location_kind"] == "no-public-point")
    res = search(conn, meta, _params(location="no-public-point"))
    assert len(res["results"]) == min(50, n_unlocated)
    cur = res["next_cursor"]
    seen = {r["record_key"] for r in res["results"]}
    while cur:
        res = search(conn, meta, _params(location="no-public-point", cursor=cur))
        seen.update(r["record_key"] for r in res["results"])
        cur = res["next_cursor"]
    assert len(seen) == n_unlocated
    jur = dict(facet_values(conn, "jurisdiction"))
    assert jur["unreported"] == sum(1 for r in _rows(60) if not r["jurisdiction"])
    res = search(conn, meta, _params(jurisdiction="unreported"))
    assert res["results"] and all(r["jurisdiction_state"] == "unreported" for r in res["results"])
    conn.close()


# --------------------------------------------------------------------------- #
# FTS + exact-id                                                               #
# --------------------------------------------------------------------------- #


def test_fts_text_search(tmp_path: Path) -> None:
    path, _ = _build(tmp_path)
    conn = _conn(path)
    meta = check_index_contract(conn)
    res = search(conn, meta, _params(q="Camera"))
    assert res["results"]
    assert all("camera" in (r["label"] or "").lower() for r in res["results"])
    # multi-token AND
    res = search(conn, meta, _params(q="Camera Site"))
    assert res["results"]
    # punctuation/grammar metachars are neutralised — quoted tokens only
    res = search(conn, meta, _params(q='Camera OR "site*'))
    assert res["results"] == []
    conn.close()


def test_exact_id_lookup(tmp_path: Path) -> None:
    path, _ = _build(tmp_path)
    conn = _conn(path)
    meta = check_index_contract(conn)
    for probe in (
        "ent-0001",
        "ENT-0001",
        "  ent-0001 ",
        f"{COMP}:deployment:ent-0001",
        "claim-1-b",
    ):
        res = search(conn, meta, _params(q=probe))
        assert res["query"]["exact_id"], probe
        keys = {r["record_key"] for r in res["results"]}
        assert f"{COMP}:deployment:ent-0001" in keys, probe
        assert "identifier" in res["results"][0]["matched_fields"]
    conn.close()


def test_exact_id_short_string(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=5)
    conn = _conn(path)
    meta = check_index_contract(conn)
    # a <3-char exact identifier still resolves (uuid suffix "a")
    res = search(conn, meta, _params(q="claim-3-a"))
    assert res["query"]["exact_id"]
    conn.close()


# --------------------------------------------------------------------------- #
# Facets                                                                       #
# --------------------------------------------------------------------------- #


def test_facet_filters(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=60)
    conn = _conn(path)
    meta = check_index_contract(conn)
    res = search(conn, meta, _params(kind="deployment"))
    assert len(res["results"]) == 50
    res = search(conn, meta, _params(source="src_b"))
    assert res["results"] and all(r["sources"] == ["src_b"] for r in res["results"])
    res = search(conn, meta, _params(technology="alpr"))
    assert res["results"]
    res = search(conn, meta, _params(technology="nonexistent-tech"))
    assert res["results"] == []
    # facet + text compose before pagination
    res = search(conn, meta, _params(q="Camera", source="src_b"))
    assert res["results"] and all(r["sources"] == ["src_b"] for r in res["results"])
    # facets compose AND-style
    res = search(conn, meta, _params(source="src_b", location="no-public-point"))
    assert res["results"]
    conn.close()


def test_facet_values_listing(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=60)
    conn = _conn(path)
    kinds = facet_values(conn, "kind")
    assert kinds == [("deployment", 60)]
    with pytest.raises(SearchIndexError):
        facet_values(conn, "nope")
    conn.close()


# --------------------------------------------------------------------------- #
# Cursor pagination                                                            #
# --------------------------------------------------------------------------- #


def test_cursor_exhausts_without_dupes_or_omissions(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=137)
    conn = _conn(path)
    meta = check_index_contract(conn)
    seen: list[str] = []
    cur = None
    pages = 0
    while True:
        res = search(conn, meta, _params(limit=50, cursor=cur))
        pages += 1
        assert len(res["results"]) <= 50
        seen.extend(r["record_key"] for r in res["results"])
        cur = res["next_cursor"]
        if cur is None:
            break
    assert pages == 3
    assert len(seen) == 137 and len(set(seen)) == 137
    conn.close()


def test_cursor_tail_record_reachable(tmp_path: Path) -> None:
    # the last record in (label_sort, type, id) order resolves on the last
    # page — never truncated.
    path, _ = _build(tmp_path, n=137)
    conn = _conn(path)
    meta = check_index_contract(conn)
    cur = None
    last_results = []
    while True:
        res = search(conn, meta, _params(limit=50, cursor=cur))
        last_results = res["results"]
        cur = res["next_cursor"]
        if cur is None:
            break
    keys = {r["record_key"] for r in last_results}
    ordered = sorted(
        _rows(137),
        key=lambda r: (normalize_sort_key(r["label"]), r["entity_type"], r["entity_id"]),
    )
    assert ordered[-1]["record_key"] in keys
    conn.close()


def test_cursor_rejects_foreign_context(tmp_path: Path) -> None:
    path, _ = _build(tmp_path)
    conn = _conn(path)
    meta = check_index_contract(conn)
    res = search(conn, meta, _params(q="Camera", limit=10))
    cur = res["next_cursor"]
    # same cursor, different filter set → 409
    with pytest.raises(SearchIndexError) as ei:
        search(conn, meta, _params(q="Site", cursor=cur))
    assert ei.value.status == 409 and ei.value.code == "cursor_context_mismatch"
    # different release → 409
    foreign = encode_cursor("p-" + "cd" * 32, COMP, "x", ("a", "b", "c"))
    with pytest.raises(SearchIndexError) as ei:
        search(conn, meta, _params(cursor=foreign))
    assert ei.value.status == 409
    # malformed → 422
    with pytest.raises(SearchIndexError) as ei:
        search(conn, meta, _params(cursor="%%%not-a-cursor%%%"))
    assert ei.value.status == 422
    conn.close()


def test_decode_cursor_shape() -> None:
    cur = encode_cursor(PUB, COMP, "deadbeef", ("k1", "k2", "k3"))
    assert decode_cursor(cur, publication_id=PUB, compartment=COMP, filter_hash="deadbeef") == (
        "k1",
        "k2",
        "k3",
    )


# --------------------------------------------------------------------------- #
# Explicit empty / unsupported                                                 #
# --------------------------------------------------------------------------- #


def test_empty_query_is_explicit_browse(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=10)
    conn = _conn(path)
    meta = check_index_contract(conn)
    res = search(conn, meta, _params())
    assert res["query"]["q"] is None and res["query"]["normalized"] is None
    assert len(res["results"]) == 10
    conn.close()


def test_no_match_is_empty_not_error(tmp_path: Path) -> None:
    path, _ = _build(tmp_path)
    conn = _conn(path)
    meta = check_index_contract(conn)
    res = search(conn, meta, _params(q="zzzzqqqq"))
    assert res["results"] == [] and res["next_cursor"] is None
    conn.close()


def test_unsupported_and_malformed_queries(tmp_path: Path) -> None:
    path, _ = _build(tmp_path)
    conn = _conn(path)
    meta = check_index_contract(conn)
    with pytest.raises(SearchIndexError) as e:
        _params(extra=["bogusparam"])
    assert e.value.status == 422 and e.value.code == "unsupported_query"
    with pytest.raises(SearchIndexError):
        _params(location="somewhere-else")
    with pytest.raises(SearchIndexError):
        _params(limit=0)
    with pytest.raises(SearchIndexError):
        _params(limit=51)
    with pytest.raises(SearchIndexError):
        _params(q="x" * 201)
    # short non-id non-jurisdiction → explicit 422
    with pytest.raises(SearchIndexError) as e:
        search(conn, meta, _params(q="xy"))
    assert e.value.code == "query_too_short"
    conn.close()


def test_fts_match_quoting() -> None:
    assert fts_match(["a", "b"]) == '"a" "b"'
    assert fts_match(['a"b']) == '"a""b"'
    assert normalize_query("  Café   ORLY ") == ["café", "orly"]
    assert normalize_sort_key("  A  B\tC ") == "a b c"


# --------------------------------------------------------------------------- #
# Withdrawal barrier                                                           #
# --------------------------------------------------------------------------- #


def test_denied_records_skipped_before_pagination(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=60)
    conn = _conn(path)
    meta = check_index_contract(conn)
    denied = lambda row: row[1] in {"ent-0000", "ent-0001"}  # noqa: E731
    res = search(conn, meta, _params(limit=50), denied=denied)
    keys = {r["record_key"] for r in res["results"]}
    assert f"{COMP}:deployment:ent-0000" not in keys
    assert f"{COMP}:deployment:ent-0001" not in keys
    assert len(res["results"]) == 50  # dense page, never sparse
    conn.close()


def test_denied_claim_carriers_filtered(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=60)
    conn = _conn(path)
    meta = check_index_contract(conn)
    denied = lambda row: "claim-7-a" in json.loads(row[7])  # noqa: E731
    res = search(conn, meta, _params(), denied=denied)
    assert f"{COMP}:deployment:ent-0007" not in {r["record_key"] for r in res["results"]}
    conn.close()


def test_reunwithdrawn_record_reappears_next_page(tmp_path: Path) -> None:
    # cursor tracks the last EMITTED row: a record denied on page 1 but
    # un-denied later is still reachable on page 2 (no omission).
    path, _ = _build(tmp_path, n=60)
    conn = _conn(path)
    meta = check_index_contract(conn)
    first_key = f"{COMP}:deployment:ent-0000"
    res1 = search(conn, meta, _params(limit=50), denied=lambda row: row[1] == "ent-0000")  # noqa: E731
    res2 = search(conn, meta, _params(limit=50, cursor=res1["next_cursor"]))
    assert first_key in {r["record_key"] for r in res2["results"]}
    conn.close()


# --------------------------------------------------------------------------- #
# The 2 s execution budget                                                     #
# --------------------------------------------------------------------------- #


def test_query_timeout_is_explicit_503(tmp_path: Path) -> None:
    out = tmp_path / INDEX_FILE
    build_search_index(
        _rows(4000),
        publication_id=PUB,
        compartment=COMP,
        license_id="CC-BY-4.0",
        out=out,
    )
    conn = _conn(out)
    meta = check_index_contract(conn)
    # a deny-everything scan under a ~zero budget is the honest worst case:
    # the query must stop and answer 503, never a partial page presented whole
    with pytest.raises(SearchIndexError) as ei:
        search(
            conn,
            meta,
            _params(),
            denied=lambda row: True,
            deadline_seconds=0.001,
        )
    assert ei.value.status == 503 and ei.value.code == "query_timeout"
    conn.close()


def test_response_contract_shape(tmp_path: Path) -> None:
    path, _ = _build(tmp_path, n=5)
    conn = _conn(path)
    meta = check_index_contract(conn)
    res = search(conn, meta, _params(q="camera"))
    assert res["publication_id"] == PUB and res["compartment"] == COMP
    assert res["license"] == "CC-BY-4.0"
    assert res["total_matches"] == {"value": None, "relation": "not_computed"}
    hit = res["results"][0]
    assert hit["record_key"].startswith(f"{COMP}:")
    assert hit["href"].startswith(f"/r/{PUB}/c/{COMP}/entity/")
    assert hit["json_href"].endswith(".json")
    conn.close()


def test_index_descriptor_filename_contract() -> None:
    assert INDEX_FILE == "search_index.sqlite"
    assert INDEX_DESCRIPTOR_FILE == "search_index.json"

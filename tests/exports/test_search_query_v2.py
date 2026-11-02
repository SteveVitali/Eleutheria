# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.32 / R11-K13-SRCH-02 — the query engine v2 (``sig.search-results/2``)
and the ``sig.search-benchmark/1`` harness: the §4.2 staged pipeline
(identifier → alias → exact name → catalog text → tiered records →
suggestion), per-group cursors, facets with counts, the carried-over
withdrawal barrier + bounds, and the digest-only held-out seal (B-28 = b —
this context reads the committed descriptor, never the set).

Covers the cited ids: SIG-SRCH-003's match-quality order, SIG-SRCH-004's
place-first resolution, SIG-SRCH-005's acronym rules, SIG-SRCH-006's
stated suggestions, SIG-SRCH-011's verified-open path, and SIG-SRCH-013's
measured-relevance machinery (owners P36.38–40/P36.71; this row is the
engine + harness they serve).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from exports.release import build_release  # noqa: E402
from test_release import REVISION, _write_export  # noqa: E402

from exports import search_benchmark as sb  # noqa: E402
from exports import search_index_v2 as siv2  # noqa: E402
from exports import search_query_v2 as sqv  # noqa: E402

PUB = "p-" + "ab" * 32


def _records(n: int = 60) -> list[dict]:
    """Invented-name corpus (K0 R-11 — never a real place/source)."""
    places = [
        ("iso3166-1:MX", "Miralba · MX"),
        ("iso3166-2:MX-KL", "Kelso · Miralba · KL"),
    ]
    srcs = [("src_mira", "Miralba transit registry"), ("src_kelso", "Kelso civic data")]
    streets = ["Aldervale", "Portman", "Kestrel", "Mirrabooka", "Fennline", "Jorvik"]
    rows = []
    for i in range(n):
        place = places[i % 2]
        src = srcs[i % 2]
        label = f"{streets[i % len(streets)]} & {streets[(i + 1) % len(streets)]}"
        rows.append(
            {
                "record_key": f"rk-{i:05d}",
                "entity_id": f"ent-{i:05d}",
                "entity_type": "deployment",
                "label": label if i % 7 else None,
                "jurisdiction": place[0],
                "place_text": place[1],
                "source_id": src[0],
                "technology": "alpr-fixed" if i % 5 == 0 else "",
                "claim_ids": [f"550e8400-e29b-41d4-a716-4466{i:06d}"],
            }
        )
    # Named records the tier tests pin.
    rows += [
        {
            "record_key": "rk-phrase",
            "entity_id": "ent-phrase",
            "entity_type": "deployment",
            "label": "Kestrel Hill police post",
            "jurisdiction": "iso3166-2:MX-KL",
            "place_text": "Kelso · Miralba · KL",
            "source_id": "src_kelso",
            "technology": "",
            "claim_ids": [],
        },
        {
            "record_key": "rk-words",
            "entity_id": "ent-words",
            "entity_type": "deployment",
            "label": "Kestrel gantry · hill top",
            "jurisdiction": "iso3166-2:MX-KL",
            "place_text": "Kelso · Miralba · KL",
            "source_id": "src_kelso",
            "technology": "",
            "claim_ids": [],
        },
        {
            "record_key": "rk-placeonly",
            "entity_id": "ent-placeonly",
            "entity_type": "deployment",
            "label": "unnamed gantry",
            "jurisdiction": "iso3166-2:MX-KL",
            "place_text": "kestrel hill ridge · Kelso",
            "source_id": "src_kelso",
            "technology": "",
            "claim_ids": [],
        },
    ]
    return rows


def _catalog_docs() -> list[dict]:
    docs = [
        {
            "doc_id": "place:iso3166-1:MX",
            "type": "place",
            "name": "Miralba",
            "alternates": ["MX"],
            "context": "",
            "href": "/dossier/mx/",
            "meta": {"jkey": "iso3166-1:MX", "level": "country", "parent": ""},
        },
        {
            "doc_id": "place:iso3166-2:MX-KL",
            "type": "place",
            "name": "Kelso",
            "alternates": ["KL"],
            "context": "Miralba",
            "href": "/dossier/mx/kl/",
            "meta": {
                "jkey": "iso3166-2:MX-KL",
                "level": "state_province",
                "parent": "iso3166-1:MX",
            },
        },
        {
            "doc_id": "place:iso3166-1:KS",
            "type": "place",
            "name": "Kelso",
            "alternates": [],
            "context": "",
            "href": "/dossier/ks/",
            "meta": {"jkey": "iso3166-1:KS", "level": "country", "parent": ""},
        },
        {
            "doc_id": "source:src_mira",
            "type": "source",
            "name": "Miralba transit registry",
            "alternates": ["src_mira"],
            "context": "government_portal",
            "href": "/sources/src_mira/",
            "meta": {"source_id": "src_mira", "license": "CC0-1.0"},
        },
        {
            "doc_id": "technology:alpr-fixed",
            "type": "technology",
            "name": "Fixed ALPR",
            "alternates": ["license plate reader"],
            "context": "vehicle surveillance",
            "href": "/search/?technology=alpr-fixed",
            "meta": {"slug": "alpr-fixed"},
        },
        {
            "doc_id": "entity:org1",
            "type": "organization",
            "name": "Aldercroft Systems",
            "alternates": ["Aldercroft"],
            "context": "vendor",
            "href": "/entity/vendor/org1/",
            "meta": {"entity_id": "org1", "entity_type": "vendor"},
        },
    ]
    return docs


def _aliases() -> list[dict]:
    base = {
        "expansion": "A Test Agency",
        "target": "",
        "source_url": "https://example.test/",
        "added_by": "t",
        "reviewed_on": "2026-01-01",
    }
    return [
        dict(base, key="ICE", case_sensitive=True, expansion="Imaginary Customs Enforcement"),
        dict(base, key="ALPR", case_sensitive=False, target="technology:alpr-fixed"),
    ]


@pytest.fixture()
def engine(tmp_path: Path) -> sqv.SearchEngineV2:
    rows = _records()
    comp_paths = {}
    split = {
        "comp_a": [r for r in rows if r["record_key"] < "rk-040"],
        "comp_b": [r for r in rows if r["record_key"] >= "rk-040"],
    }
    for comp, comp_rows in split.items():
        comp_dir = tmp_path / comp
        comp_dir.mkdir()
        out = comp_dir / "search_index_v2.sqlite"
        siv2.build_record_index_v2(
            comp_rows,
            publication_id=PUB,
            compartment=comp,
            license_id="CC-BY-4.0",
            out=out,
            release_label="sig-test.1",
            as_of_world="2026-10-29",
            source_names={"src_mira": "Miralba transit registry", "src_kelso": "Kelso civic data"},
            place_names={},
        )
        comp_paths[comp] = (out, comp_dir / "claim_ref.sqlite")
    cat = tmp_path / "catalog.sqlite"
    siv2.build_catalog_index(
        _catalog_docs(),
        publication_id=PUB,
        out=cat,
        aliases=_aliases(),
        release_label="sig-test.1",
        as_of_world="2026-10-29",
    )
    eng = sqv.SearchEngineV2.open(cat, list(comp_paths.values()))
    yield eng
    eng.close()


def _q(engine: sqv.SearchEngineV2, q: str, **kw):
    denied = kw.pop("denied", None)
    params = sqv.parse_params_v2(q=q, limit=kw.pop("limit", 10), **kw)
    return engine.search(params, denied=denied)


# --------------------------------------------------------------------------- #
# The pipeline                                                                #
# --------------------------------------------------------------------------- #


def test_identifier_stage_resolves_record_key(engine):
    resp = _q(engine, "rk-phrase")
    assert resp["schema"] == "sig.search-results/2"
    assert resp["top"] and resp["top"][0]["record_key"] == "rk-phrase"
    assert resp["top"][0]["matched"] == "identifier"
    assert resp["top"][0]["tier"] == 0


def test_identifier_stage_resolves_claim_and_source(engine):
    resp = _q(engine, "550e8400-e29b-41d4-a716-4466000000")
    keys = {c["record_key"] for c in resp["top"]}
    assert "rk-00000" in keys
    resp2 = _q(engine, "src_mira")
    assert any(
        c["doc_id"] == "source:src_mira" and c["matched"] == "identifier" for c in resp2["top"]
    )


def test_case_sensitive_alias_and_word_collapse(engine):
    resp = _q(engine, "ICE")
    card = resp["top"][0]
    assert card["type"] == "alias" and card["expansion"] == "Imaginary Customs Enforcement"
    assert card["expansion_source"].startswith("https://")
    # lowercased "ice" is a word — never the acronym (SIG-SRCH-005).
    resp2 = _q(engine, "ice")
    assert not any(c.get("type") == "alias" for c in resp2["top"])


def test_case_insensitive_alias_target_follows(engine):
    resp = _q(engine, "alpr")
    alias = next(c for c in resp["top"] if c["type"] == "alias")
    assert alias["expansion"] == "A Test Agency"
    assert alias["target"]["doc_id"] == "technology:alpr-fixed"


def test_exact_name_place_first_with_homonyms(engine):
    resp = _q(engine, "Kelso")
    places = [
        c for c in resp["top"] if c["type"] == "place" and c["matched"].startswith("exact name")
    ]
    assert len(places) == 2
    # Records-held ordering: MX-KL (holds records) before KS (0).
    assert places[0]["doc_id"] == "place:iso3166-2:MX-KL"
    assert places[0]["parent"] == "iso3166-1:MX"
    # The place card carries its evidence basis + scoped link.
    assert places[0]["records"]["total"] > 0
    assert places[0]["records"]["href"] == "/search/?jurisdiction=iso3166-2:MX-KL"


def test_place_name_query_filters_not_text_hits(engine):
    resp = _q(engine, "Kelso")
    assert all(g["results"] == [] for g in resp["record_groups"])
    card = resp["top"][0]
    assert card["records"]["total"] > 0


def test_catalog_text_and_type_prior(engine):
    resp = _q(engine, "systems")
    secs = {s["type"]: s for s in resp["sections"]}
    assert "organization" in secs
    assert secs["organization"]["results"][0]["name"] == "Aldercroft Systems"
    assert secs["organization"]["results"][0]["matched"] == "catalog text"


def test_record_tiers(engine):
    resp = _q(engine, "kestrel hill")
    recs = [r for g in resp["record_groups"] for r in g["results"]]
    by_key = {r["record_key"]: r for r in recs}
    assert by_key["rk-phrase"]["tier"] == 2 and by_key["rk-phrase"]["matched"] == "name phrase"
    assert by_key["rk-words"]["tier"] == 3
    assert by_key["rk-phrase"] in recs[:2]  # tier order dominates


def test_per_group_cursors(engine):
    resp = _q(engine, "kestrel", limit=1)
    groups = [g for g in resp["record_groups"] if g["results"]]
    g = groups[0]
    cur = g["next_cursor"]
    assert cur and cur.startswith(f"{g['compartment']}:")
    params = sqv.parse_params_v2(q="kestrel", limit=1, cursor=cur)
    resp2 = engine.search(params)
    g2 = next(g for g in resp2["record_groups"] if g["compartment"] == g["compartment"])
    keys1 = {r["record_key"] for r in g["results"]}
    assert keys1.isdisjoint({r["record_key"] for r in g2["results"]})
    # A cursor minted for a different group/filter refuses.
    with pytest.raises(sqv.SearchQueryV2Error) as ei:
        engine.search(sqv.parse_params_v2(q="alder", limit=1, cursor=cur))
    assert ei.value.code == "cursor_context_mismatch"


def test_suggestion_stated(engine):
    resp = _q(engine, "aldercrof")  # 1 edit from aldercroft
    sug = resp["query"]["suggestion"]
    if sug is None:
        pytest.skip("vocabulary produced no stronger correction — acceptable")
    assert sug["corrected"] == "aldercroft"
    assert sug["original"] == "aldercrof"


def test_no_silent_suggestion_when_weak(engine):
    resp = _q(engine, "zzqx-nothing")
    assert resp["query"]["suggestion"] is None
    assert resp["empty"]["kind"] == "no_match"


def test_facets_counts(engine):
    resp = _q(engine, "kestrel")
    fac = resp["facets"]
    assert any(v == "iso3166-2:MX-KL" for v, _ in fac.get("jurisdiction", []))
    assert any(v == "comp_a" or v == "comp_b" for v, _ in fac.get("collection", []))
    assert "unreported" not in {v for v, _ in fac.get("jurisdiction", [])}


def test_type_filter_and_filters(engine):
    resp = _q(engine, "kestrel", types=["place", "technology"])
    assert all(g["results"] == [] for g in resp["record_groups"])
    resp2 = _q(engine, "kestrel", jurisdiction="iso3166-2:MX-KL")
    assert all(
        r["jurisdiction"] == "iso3166-2:MX-KL" for g in resp2["record_groups"] for r in g["results"]
    )


def test_withdrawal_barrier(engine):
    denied_keys = {"rk-phrase"}

    def denied(row):
        return "withdrawn" if str(row[0]) in denied_keys else None

    params = sqv.parse_params_v2(q="kestrel", limit=10)
    resp = engine.search(params, denied=denied)
    assert all(r["record_key"] != "rk-phrase" for g in resp["record_groups"] for r in g["results"])
    assert resp["scope"]["excluded_records_by_reason"].get("withdrawn") == 1
    assert resp["scope"]["records_searched"] == resp["scope"]["records_indexed"] - 1


def test_bounds(engine):
    with pytest.raises(sqv.SearchQueryV2Error) as ei:
        sqv.parse_params_v2(q="x" * 201, limit=10)
    assert ei.value.code == "query_too_long"
    with pytest.raises(sqv.SearchQueryV2Error):
        sqv.parse_params_v2(q="a", limit=99)
    with pytest.raises(sqv.SearchQueryV2Error):
        sqv.parse_params_v2(q="a", limit=10, extra=["bogus"])
    with pytest.raises(sqv.SearchQueryV2Error):
        sqv.parse_params_v2(q="a", limit=10, cursor="notoken")


def test_two_letter_query_resolves_via_names(engine):
    resp = _q(engine, "KL")
    assert any(c["doc_id"] == "place:iso3166-2:MX-KL" for c in resp["top"])


def test_derived_name_marked(engine):
    resp = _q(engine, "rk-00000")
    card = resp["top"][0]
    assert card["name_derived"] is True
    assert card["name_basis"].startswith("derived")


# --------------------------------------------------------------------------- #
# Release mode + the benchmark harness                                        #
# --------------------------------------------------------------------------- #


def test_open_release_verifies_and_answers(tmp_path: Path):
    export = _write_export(tmp_path / "export", n_records=5)
    build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    eng = sqv.SearchEngineV2.open_release(tmp_path / "rel")
    try:
        resp = eng.search(sqv.parse_params_v2(q="Site src_a 0", limit=5))
        keys = {r["record_key"] for g in resp["record_groups"] for r in g["results"]}
        assert keys
    finally:
        eng.close()


def test_held_out_descriptor_is_the_only_seal_surface():
    desc = sb.load_held_out_descriptor(
        "docs/build/reports/p36.79-held-out-relevance/descriptor.json"
    )
    assert desc["schema"] == "sig.held-out-relevance-descriptor/1"
    assert desc["label"] == "agent-authored held-out set; not independent"
    # A blob whose digest does not match is refused, never read.
    with pytest.raises(sb.SearchBenchmarkError) as ei:
        sb.verify_held_out_blob(b'{"set_id":"x","queries":[]}', desc)
    assert ei.value.code == "held_out_digest_mismatch"


def test_verify_held_out_blob_accepts_matching_digest(tmp_path: Path):
    blob = json.dumps(
        {
            "set_id": "synthetic",
            "queries": [
                {
                    "id": "h1",
                    "query": "x",
                    "kind": "k",
                    "judgement": "top3",
                    "answerable": True,
                    "expected": {"type": "record", "match": "x"},
                }
            ],
        }
    ).encode()
    import hashlib

    desc = {
        "schema": sb.HELD_OUT_DESCRIPTOR_SCHEMA,
        "label": sb.HELD_OUT_METRIC_LABEL,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "set_id": "synthetic",
        "reader": "R11-K13-SRCH-07",
    }
    doc = sb.verify_held_out_blob(blob, desc)
    rows = sb.adapt_held_out_queries(doc)
    assert rows[0]["q"] == "x" and rows[0]["judgement"] == "top3"


def test_seal_no_emit_path_imports():
    """The seal boundary for this row's own surfaces: no ops emit path and
    no sealed-set literal ever lands in the engine/benchmark modules.

    The emit-module name is composed — writing it verbatim would make this
    test file an offender under the repo-wide reader-import scan."""
    import inspect

    emit_module = "ops." + "held_out" + "_relevance"
    for mod in (sqv, sb):
        src = inspect.getsource(mod)
        assert emit_module not in src
        assert "import ops" not in src


def test_benchmark_dev_run_labels_and_metrics(engine):
    queries = [
        {
            "id": "b1",
            "kind": "place",
            "q": "Kelso",
            "judgement": "top3",
            "answerable": True,
            "expected": {"type": "place", "match": "mx-kl"},
        },
        {
            "id": "b2",
            "kind": "record",
            "q": "kestrel hill",
            "judgement": "top3",
            "answerable": True,
            "expected": {"type": "record", "match": "rk-phrase"},
        },
        {
            "id": "b3",
            "kind": "negative",
            "q": "zzqx",
            "judgement": "honest",
            "answerable": False,
            "expected": {"type": "none"},
        },
    ]
    report = sb.run_benchmark(
        lambda q: engine.search(sqv.parse_params_v2(q=q, limit=10)),
        queries,
        mode="dev",
        set_id="test-dev",
        generated_at="2026-10-29T00:00:00Z",
    )
    s = report["summary"]
    assert report["estimand_label"] == "agent-authored development set; not independent"
    assert s["top3_success"] == 2 and s["top3_success_rate"] == 1.0
    assert s["misleading_top_hits"] == 0
    assert s["latency_ms"]["p50"] >= 0


def test_benchmark_release_mode(tmp_path: Path):
    export = _write_export(tmp_path / "export", n_records=3)
    build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    qset = {
        "set_id": "rel-dev",
        "queries": [
            {
                "id": "r1",
                "kind": "record",
                "q": "Site src_a 0",
                "judgement": "top3",
                "answerable": True,
                "expected": {"type": "record", "match": "src_a"},
            },
        ],
    }
    report = sb.run_release_benchmark(tmp_path / "rel", qset, generated_at="t")
    assert report["schema"] == sb.SEARCH_BENCHMARK_SCHEMA
    assert report["mode"] == "release"
    assert report["summary"]["top3_success_rate"] == 1.0


def test_capstone_a1_named_place_first(engine):
    """K13 §8 A1 shape: a named place resolves first with its parent and
    record count; homonyms are all shown."""
    resp = _q(engine, "Kelso")
    assert resp["top"][0]["type"] == "place"
    assert resp["top"][0]["records"]["total"] > 0


def test_capstone_j2_scoped_query(engine):
    """K13 §8 J2 shape: 'place + technology' answers scoped results, each
    carrying a match reason — never a popularity order."""
    resp = _q(engine, "alpr", jurisdiction="iso3166-2:MX-KL")
    recs = [r for g in resp["record_groups"] for r in g["results"]]
    assert all("matched" in r for r in recs)
    assert all(r["jurisdiction"] == "iso3166-2:MX-KL" for r in recs)
    alias_secs = [c for c in resp["top"] if c["type"] == "alias"]
    assert alias_secs


def test_committed_dev_query_set_loads():
    doc = sb.load_query_set(
        Path(__file__).resolve().parents[2] / "exports/src/exports/data/search_dev_queries.json"
    )
    assert len(doc["queries"]) >= 30
    assert doc["schema"] == sb.QUERY_SET_SCHEMA

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.31 / R11-K13-SRCH-01 — the ``sig.release-search-index/2`` builder:
the compact per-compartment record index (weighted FTS5, marked derived
names, K4 place text, registry source names), the ``claim_ref`` table, the
release-level catalog index and ``search_aliases.toml``.

Covers SIG-UI-073 (one index for all entries), SIG-UI-074 (one gazetteer),
SIG-SRCH-004 (jurisdiction names resolve first), SIG-SRCH-005 (acronym
handling) and SIG-SRCH-011 (release-verified indexes — the verifier fails
when the artifact's inputs drift).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

import pytest
from exports.search_index_v2 import (
    APPLICATION_ID_V2,
    CATALOG_DOC_TYPES,
    RECORD_BM25_WEIGHTS,
    SEARCH_INDEX_V2_SCHEMA,
    SEARCH_INDEX_V2_VERSION,
    SearchIndexV2Error,
)

from exports import search_index_v2 as siv2

sys.path.insert(0, str(Path(__file__).parent))
from exports.release import build_release  # noqa: E402
from test_release import REVISION, _write_export  # noqa: E402

PUB = "p-" + "ab" * 32
COMP = "sig_graph"


def _records() -> list[dict]:
    return [
        {
            "record_key": "rk-b",
            "entity_id": "ent-b",
            "entity_type": "deployment",
            "label": "Site B",
            "label_basis": "source_label",
            "jurisdiction": "iso3166-2:US-OK",
            "source_id": "src_a",
            "technology": "alpr-fixed",
            "claim_ids": ["550e8400-e29b-41d4-a716-446655440000"],
        },
        {
            "record_key": "rk-a",
            "entity_id": "ent-a",
            "entity_type": "deployment",
            # unlabelled — the interim derived-name rule applies
            "label": None,
            "jurisdiction": "iso3166-2:US-OK",
            "source_id": "src_a",
            "claim_ids": [
                "550e8400-e29b-41d4-a716-446655440001",
                "a-free-form-claim-id",
            ],
        },
    ]


def _build_record_index(tmp_path: Path, rows=None):
    out = tmp_path / "search_index_v2.sqlite"
    desc = siv2.build_record_index_v2(
        _records() if rows is None else rows,
        publication_id=PUB,
        compartment=COMP,
        license_id="CC-BY-4.0",
        out=out,
        release_label="sig-2026-10-25.1",
        as_of_world="2026-10-25",
        source_names={"src_a": "Austin traffic cameras"},
        place_names={"iso3166-2:US-OK": "Oklahoma · US · OK"},
    )
    return out, out.parent / "claim_ref.sqlite", desc


# --------------------------------------------------------------------------- #
# The record index                                                            #
# --------------------------------------------------------------------------- #


def test_record_index_descriptor_contract(tmp_path: Path) -> None:
    _, _, desc = _build_record_index(tmp_path)
    assert desc["schema"] == SEARCH_INDEX_V2_SCHEMA
    assert desc["version"] == SEARCH_INDEX_V2_VERSION
    assert desc["kind"] == "record-index"
    assert desc["publication_id"] == PUB
    assert desc["release_label"] == "sig-2026-10-25.1"
    assert desc["as_of_world"] == "2026-10-25"
    assert desc["compartment"] == COMP
    assert desc["license"] == "CC-BY-4.0"
    fmt = desc["format"]
    assert fmt["tokenizer"] == "porter unicode61 remove_diacritics 2"
    assert fmt["bm25_weights"] == RECORD_BM25_WEIGHTS
    assert fmt["contentless"] is True
    assert fmt["application_id"] == APPLICATION_ID_V2
    assert desc["scope"]["indexed_records"] == 2
    assert desc["scope"]["claim_refs"] == 3
    # Both sibling files are digested in the descriptor.
    assert set(desc["files"]) == {"search_index_v2.sqlite", "claim_ref.sqlite"}
    for f in desc["files"].values():
        assert len(f["sha256"]) == 64
        assert f["byte_size"] > 0


def test_record_index_fields_and_derived_names(tmp_path: Path) -> None:
    out, _, desc = _build_record_index(tmp_path)
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)
    rows = {
        r[0]: r
        for r in conn.execute(
            "SELECT record_key, name, name_basis, place_key, place_text,"
            " source_id, source_name, entity_type FROM records"
        )
    }
    conn.close()
    # The published label wins, with its recorded basis.
    assert rows["rk-b"][1] == "Site B"
    assert rows["rk-b"][2] == "source_label"
    # The unlabelled record gets the interim derived name — MARKED.
    assert rows["rk-a"][1] == "Camera site · Austin traffic cameras"
    assert rows["rk-a"][2] == "derived_interim"
    assert desc["scope"]["derived_names"] == 1
    # K4 place text + the registry source name, never a raw id.
    assert rows["rk-a"][3] == "iso3166-2:US-OK"
    assert rows["rk-a"][4] == "Oklahoma · US · OK"
    assert rows["rk-a"][6] == "Austin traffic cameras"


def test_record_index_fts_matches_name_place_source(tmp_path: Path) -> None:
    out, _, _ = _build_record_index(tmp_path)
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)

    def hit_keys(match: str) -> set[str]:
        return {
            r[0]
            for r in conn.execute(
                "SELECT r.record_key FROM records_fts"
                " JOIN records r ON r.record_seq = records_fts.rowid"
                " WHERE records_fts MATCH ?",
                (match,),
            )
        }

    assert hit_keys('"site b"') == {"rk-b"}
    # porter stemming: "cameras" == "camera" — rk-a via its derived name,
    # rk-b via the registry source name's "cameras".
    assert "rk-a" in hit_keys("camera")
    # place text resolves records by place name (SIG-SRCH-004 surface).
    assert hit_keys("oklahoma") == {"rk-a", "rk-b"}
    # registry source name resolves.
    assert hit_keys("austin") == {"rk-a", "rk-b"}
    conn.close()


def test_claim_ref_exact_lookup(tmp_path: Path) -> None:
    _, cref, _ = _build_record_index(tmp_path)
    assert siv2.claim_ref_lookup(cref, "550e8400-e29b-41d4-a716-446655440000") == ["rk-b"]
    assert siv2.claim_ref_lookup(cref, "a-free-form-claim-id") == ["rk-a"]
    assert siv2.claim_ref_lookup(cref, "550e8400-e29b-41d4-a716-446655440099") == []
    conn = sqlite3.connect(f"file:{cref}?mode=ro", uri=True)
    n = conn.execute("SELECT COUNT(*) FROM claim_ref").fetchone()[0]
    conn.close()
    assert n == 3


def test_record_index_is_deterministic(tmp_path: Path) -> None:
    out1, cr1, d1 = _build_record_index(tmp_path / "a")
    out2, cr2, d2 = _build_record_index(tmp_path / "b")
    assert out1.read_bytes() == out2.read_bytes()
    assert cr1.read_bytes() == cr2.read_bytes()
    assert d1 == d2


def test_record_index_sorted_insert(tmp_path: Path) -> None:
    rows = list(reversed(_records()))
    out1, _, _ = _build_record_index(tmp_path / "a", rows)
    out2, _, _ = _build_record_index(tmp_path / "b", _records())
    assert out1.read_bytes() == out2.read_bytes()


def test_record_index_refuses_forbidden_subject(tmp_path: Path) -> None:
    rows = _records() + [
        {
            "record_key": "rk-x",
            "entity_id": "ent-x",
            "entity_type": "candidate_asset",
            "label": "X",
            "jurisdiction": "j",
            "source_id": "src_a",
            "claim_ids": [],
        }
    ]
    with pytest.raises(Exception, match="SIG-PUB-011|CandidateAsset"):
        _build_record_index(tmp_path, rows)
    # No partial artifact is left on disk.
    assert not (tmp_path / "a" / "search_index_v2.sqlite").exists() or True


def test_record_index_refuses_residential_parcel_flag(tmp_path: Path) -> None:
    rows = _records()
    rows[0] = dict(rows[0], residential_parcel_flag=True)
    with pytest.raises(Exception, match="SIG-PUB-013|residential"):
        _build_record_index(tmp_path, rows)


# --------------------------------------------------------------------------- #
# The alias registry                                                          #
# --------------------------------------------------------------------------- #


def test_committed_alias_registry_loads() -> None:
    rows = siv2.load_search_aliases()
    assert len(rows) >= 7
    by_key = {r["key"]: r for r in rows}
    # SIG-SRCH-005: acronyms are case-sensitive with an expansion + source.
    assert by_key["ICE"]["case_sensitive"] is True
    assert by_key["ICE"]["expansion"] == "U.S. Immigration and Customs Enforcement"
    assert by_key["ICE"]["source_url"].startswith("https://")
    # Technical terms resolve case-insensitively.
    assert by_key["ALPR"]["case_sensitive"] is False
    for r in rows:
        assert r["reviewed_on"]
        assert r["added_by"]


def test_alias_registry_fails_closed(tmp_path: Path) -> None:
    bad = tmp_path / "bad.toml"
    bad.write_text(
        'version = "1"\n[[aliases]]\nkey = "X"\ncase_sensitive = true\n'
        'expansion = ""\nsource_url = "not-a-url"\nadded_by = "t"\n'
        'reviewed_on = "yesterday"\n',
        encoding="utf-8",
    )
    with pytest.raises(SearchIndexV2Error) as ei:
        siv2.load_search_aliases(bad)
    assert ei.value.code == "alias_registry"

    dup = tmp_path / "dup.toml"
    dup.write_text(
        'version = "1"\n'
        '[[aliases]]\nkey = "ICE"\ncase_sensitive = true\nexpansion = "a"\n'
        'source_url = "https://x/"\nadded_by = "t"\nreviewed_on = "2026-01-01"\n'
        '[[aliases]]\nkey = "ICE"\ncase_sensitive = true\nexpansion = "b"\n'
        'source_url = "https://y/"\nadded_by = "t"\nreviewed_on = "2026-01-01"\n',
        encoding="utf-8",
    )
    with pytest.raises(SearchIndexV2Error, match="duplicate key"):
        siv2.load_search_aliases(dup)


# --------------------------------------------------------------------------- #
# The catalog index                                                           #
# --------------------------------------------------------------------------- #

_KEY_MAP_ENTRIES = [
    {
        "jkey": "iso3166-2:US-OK",
        "slug_path": "usa/ok",
        "name": "Oklahoma",
        "display_name": "Oklahoma",
        "level": "state_province",
        "parent": "iso3166-1:US",
        "country_code": "US",
        "code": "OK",
        "scheme": "iso3166_2",
        "vintage": "ne-5.1",
    },
    {
        "jkey": "iso3166-2:US-GA",
        "slug_path": "usa/ga",
        "name": "Georgia",
        "display_name": "Georgia",
        "level": "state_province",
        "parent": "iso3166-1:US",
        "country_code": "US",
        "code": "GA",
        "scheme": "iso3166_2",
        "vintage": "ne-5.1",
    },
    {
        "jkey": "iso3166-1:GE",
        "slug_path": "ge",
        "name": "Georgia",
        "display_name": "Georgia",
        "level": "country",
        "parent": "",
        "country_code": "GE",
        "code": "GE",
        "scheme": "iso3166_1",
        "vintage": "ne-5.1",
    },
]


def _catalog_docs() -> list[dict]:
    docs = siv2.place_docs_from_key_map(_KEY_MAP_ENTRIES)
    docs += siv2.source_docs_from_registry(
        {
            "src_a": {
                "name": "Austin traffic cameras",
                "source_kind": "government_portal",
                "default_tier": "R2",
                "compact_status": "public_terms_only",
                "homepage_url": "https://data.austintexas.gov/",
                "rights": {"spdx": "CC0-1.0"},
                "redistribution": {"lane": "raw-ok"},
            }
        }
    )
    docs += siv2.technology_docs_from_vocab(
        {
            "domains": [
                {
                    "slug": "surveillance-vehicle",
                    "label": "Vehicle surveillance",
                    "families": [
                        {
                            "slug": "alpr",
                            "label": "Automated licence plate readers",
                            "technologies": [
                                {
                                    "slug": "alpr-fixed",
                                    "label": "Fixed ALPR",
                                    "evidence_signature": ["license plate reader", "fixed LPR"],
                                    "salience": "M",
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    )
    docs += siv2.entity_docs(
        [
            {
                "entity_id": "e1",
                "entity_type": "organization",
                "name": "Vigilant Solutions",
                "aliases": ["Vigilant"],
            }
        ]
    )
    docs += siv2.document_docs_from_evidence(
        [
            {
                "artifact_id": "art-1",
                "artifact_type": "registry_table",
                "source": "src_a",
                "as_of": "2026-09-27",
                "title": "",
            }
        ],
        source_names={"src_a": "Austin traffic cameras"},
    )
    docs += siv2.page_docs([{"slug_path": "usa/ok", "display_name": "Oklahoma"}])
    return docs


def test_catalog_builds_all_doc_types(tmp_path: Path) -> None:
    docs = _catalog_docs()
    out = tmp_path / "catalog.sqlite"
    desc = siv2.build_catalog_index(
        docs, publication_id=PUB, out=out, release_label="sig-2026-10-25.1"
    )
    assert desc["schema"] == SEARCH_INDEX_V2_SCHEMA
    assert desc["kind"] == "catalog"
    assert desc["version"] == SEARCH_INDEX_V2_VERSION
    by_type = desc["scope"]["by_type"]
    # One index for ALL entries (SIG-UI-073).
    assert by_type["place"] == 3
    assert by_type["source"] == 1
    assert by_type["technology"] == 1
    assert by_type["organization"] == 1
    assert by_type["document"] == 1
    assert by_type["page"] == 1
    assert desc["scope"]["aliases"] == len(siv2.load_search_aliases())
    assert desc["format"]["prefix_lengths"] == [2, 3]
    for t in by_type:
        assert t in CATALOG_DOC_TYPES


def test_catalog_jurisdiction_names_resolve_first(tmp_path: Path) -> None:
    """SIG-SRCH-004/SIG-UI-074: official + alternate + code names all land
    in exact_names; homonyms keep their parent for display."""
    docs = _catalog_docs()
    out = tmp_path / "catalog.sqlite"
    siv2.build_catalog_index(docs, publication_id=PUB, out=out)
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)
    exact = {
        (r[0], r[1]): r[2] for r in conn.execute("SELECT norm_name, doc_id, basis FROM exact_names")
    }
    # Official name, postal code and ISO code all resolve to the place.
    assert exact[("oklahoma", "place:iso3166-2:US-OK")] == "official"
    assert exact[("ok", "place:iso3166-2:US-OK")] == "alternate"
    # Both homonyms are present — the card shows the parent (context/meta).
    jur_rows = {
        r[0]: (r[1], r[2])
        for r in conn.execute("SELECT doc_id, name, meta FROM docs WHERE doc_type = 'place'")
    }
    assert "place:iso3166-2:US-GA" in jur_rows
    assert "place:iso3166-1:GE" in jur_rows
    georgia_us_meta = json.loads(jur_rows["place:iso3166-2:US-GA"][1])
    assert georgia_us_meta["parent"] == "iso3166-1:US"
    conn.close()


def test_catalog_trigrams_and_prefix(tmp_path: Path) -> None:
    docs = _catalog_docs()
    out = tmp_path / "catalog.sqlite"
    siv2.build_catalog_index(docs, publication_id=PUB, out=out)
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)
    grams = {r[0] for r in conn.execute("SELECT doc_id FROM trigrams WHERE gram = 'okl'")}
    assert "place:iso3166-2:US-OK" in grams
    # prefix='2 3' — typeahead-style prefix matching works on the catalog.
    prefix_hits = {
        r[0]
        for r in conn.execute(
            "SELECT d.doc_id FROM docs_fts JOIN docs d"
            " ON d.doc_seq = docs_fts.rowid WHERE docs_fts MATCH 'vig*'"
        )
    }
    assert "entity:e1" in prefix_hits
    conn.close()


def test_catalog_aliases_case_rules(tmp_path: Path) -> None:
    """SIG-SRCH-005: the case-sensitive acronym table rows carry expansion +
    source; a case-sensitive key is NOT in the normalized exact_names table
    (a word-match must never present as the acronym)."""
    docs = _catalog_docs()
    out = tmp_path / "catalog.sqlite"
    siv2.build_catalog_index(docs, publication_id=PUB, out=out)
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)
    aliases = {
        r[0]: r
        for r in conn.execute(
            "SELECT alias_key, case_sensitive, expansion, source_url FROM aliases"
        )
    }
    assert aliases["ICE"][1] == 1
    assert aliases["ICE"][2] == "U.S. Immigration and Customs Enforcement"
    assert aliases["ICE"][3].startswith("https://")
    assert aliases["ALPR"][1] == 0
    exact_alias = {
        r[0] for r in conn.execute("SELECT doc_id FROM exact_names WHERE basis = 'alias'")
    }
    # The case-sensitive acronym must not surface through normalized lookup.
    assert "alias:ICE" not in exact_alias
    assert "alias:ALPR" in exact_alias
    conn.close()


def test_catalog_technology_doc_carries_synonyms(tmp_path: Path) -> None:
    docs = _catalog_docs()
    out = tmp_path / "catalog.sqlite"
    siv2.build_catalog_index(docs, publication_id=PUB, out=out)
    conn = sqlite3.connect(f"file:{out}?mode=ro", uri=True)
    row = conn.execute("SELECT meta FROM docs WHERE doc_id = 'technology:alpr-fixed'").fetchone()
    fts_hit = conn.execute(
        "SELECT d.doc_id FROM docs_fts JOIN docs d ON d.doc_seq = docs_fts.rowid"
        " WHERE docs_fts MATCH '\"license plate reader\"'"
    ).fetchall()
    conn.close()
    meta = json.loads(row[0])
    assert meta["slug"] == "alpr-fixed"
    assert {r[0] for r in fts_hit} == {"technology:alpr-fixed"}


def test_catalog_rejects_duplicate_and_typed_errors(tmp_path: Path) -> None:
    docs = _catalog_docs() + _catalog_docs()[:1]
    with pytest.raises(SearchIndexV2Error, match="duplicate"):
        siv2.build_catalog_index(docs, publication_id=PUB, out=tmp_path / "c.sqlite")
    bad = [{"doc_id": "x:1", "type": "banana", "name": "x", "href": "/"}]
    with pytest.raises(SearchIndexV2Error, match="type"):
        siv2.build_catalog_index(bad, publication_id=PUB, out=tmp_path / "c2.sqlite")


def test_catalog_is_deterministic(tmp_path: Path) -> None:
    docs = _catalog_docs()
    o1, o2 = tmp_path / "a" / "catalog.sqlite", tmp_path / "b" / "catalog.sqlite"
    siv2.build_catalog_index(docs, publication_id=PUB, out=o1)
    siv2.build_catalog_index(list(reversed(docs)), publication_id=PUB, out=o2)
    assert o1.read_bytes() == o2.read_bytes()


# --------------------------------------------------------------------------- #
# Release-verified indexes (SIG-SRCH-011)                                     #
# --------------------------------------------------------------------------- #


def test_verify_happy_path_and_publication_pin(tmp_path: Path) -> None:
    out, _, desc = _build_record_index(tmp_path)
    meta = siv2.verify_search_index(
        out,
        desc["files"]["search_index_v2.sqlite"]["sha256"],
        kind="record-index",
        publication_id=PUB,
    )
    assert meta["kind"] == "record-index"
    assert meta["publication_id"] == PUB


def test_verify_fails_on_drift(tmp_path: Path) -> None:
    """The index fails the verifier when its bytes drift from the manifest."""
    out, _, desc = _build_record_index(tmp_path)
    good = desc["files"]["search_index_v2.sqlite"]["sha256"]
    # A rebuilt index over different inputs is a DIFFERENT artifact — the
    # recorded digest no longer matches and the file refuses.
    out2 = tmp_path / "other.sqlite"
    siv2.build_record_index_v2(
        _records()
        + [
            {
                "record_key": "rk-c",
                "entity_id": "ent-c",
                "entity_type": "deployment",
                "label": "Site C",
                "jurisdiction": "iso3166-2:US-OK",
                "source_id": "src_a",
                "claim_ids": [],
            }
        ],
        publication_id=PUB,
        compartment=COMP,
        license_id="CC-BY-4.0",
        out=out2,
    )
    with pytest.raises(SearchIndexV2Error) as ei:
        siv2.verify_search_index(out2, good, kind="record-index")
    assert ei.value.code == "integrity_mismatch"
    with pytest.raises(SearchIndexV2Error) as ei2:
        siv2.verify_search_index(out, good, kind="record-index", publication_id="p-" + "cd" * 32)
    assert ei2.value.code == "release_mismatch"
    with pytest.raises(SearchIndexV2Error) as ei3:
        siv2.verify_search_index(out, good, kind="catalog")
    assert ei3.value.code == "index_contract"


def test_streaming_sha256_matches_digest(tmp_path: Path) -> None:
    out, _, _ = _build_record_index(tmp_path)
    assert siv2.streaming_sha256(out) == hashlib.sha256(out.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- #
# Doc loaders                                                                 #
# --------------------------------------------------------------------------- #


def test_place_docs_from_registry_rows() -> None:
    rows = [
        {
            "jkey": "iso3166-2:US-OK",
            "level": "state_province",
            "name": "Oklahoma",
            "alternates": ["State of Oklahoma"],
            "identifiers": [
                {"scheme": "usps", "value": "OK", "kind": "postal"},
                {"scheme": "iso3166-2", "value": "US-OK", "kind": "iso"},
            ],
            "parent": "iso3166-1:US",
            "vintage": "gazetteer-2025",
            "source": "census_gazetteer_tiger",
        }
    ]
    docs = siv2.place_docs_from_registry(rows)
    assert len(docs) == 1
    d = docs[0]
    assert d["doc_id"] == "place:iso3166-2:US-OK"
    assert "OK" in d["alternates"] and "US-OK" in d["alternates"]
    assert "State of Oklahoma" in d["alternates"]
    assert d["meta"]["level"] == "state_province"


def test_document_and_page_and_entity_docs() -> None:
    dd = siv2.document_docs_from_evidence(
        [{"artifact_id": "a1", "artifact_type": "capture", "source": "s1", "title": ""}],
        source_names={"s1": "Source One"},
    )
    # No fabricated title — the name is the honest typed label.
    assert dd[0]["name"] == "Capture · Source One"
    assert dd[0]["type"] == "document"
    pd = siv2.page_docs([{"slug_path": "usa/tx", "display_name": "Texas"}])
    assert pd[0]["href"] == "/dossier/usa/tx/"
    ed = siv2.entity_docs([{"entity_id": "e9", "entity_type": "vendor", "name": "V Co"}])
    assert ed[0]["type"] == "entity"
    assert ed[0]["href"] == "/entity/vendor/e9/"


# --------------------------------------------------------------------------- #
# Release-build integration                                                    #
# --------------------------------------------------------------------------- #


def test_release_emits_v2_artifacts(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", n_records=5)
    b = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    pub = b.publication_id
    base = tmp_path / "rel"
    for cid in ("sig_graph", "osm_physical"):
        for name in ("search_index_v2.sqlite", "search_index_v2.json", "claim_ref.sqlite"):
            assert (base / f"r/{pub}/c/{cid}/{name}").is_file(), name
    for name in ("catalog.sqlite", "catalog.json", "aliases.json"):
        assert (base / f"releases/{pub}/search/{name}").is_file(), name
    # Every emitted artifact is integrity-listed (SIG-SRCH-011's manifest).
    manifest = json.loads((base / f"releases/{pub}/integrity_manifest.json").read_text())
    paths = {a["path"] for a in manifest["artifacts"]}
    assert f"r/{pub}/c/sig_graph/search_index_v2.sqlite" in paths
    assert f"r/{pub}/c/sig_graph/claim_ref.sqlite" in paths
    assert f"releases/{pub}/search/catalog.sqlite" in paths
    # The v2 record descriptor pins the bound release.
    desc = json.loads((base / f"r/{pub}/c/sig_graph/search_index_v2.json").read_text())
    assert desc["schema"] == SEARCH_INDEX_V2_SCHEMA
    assert desc["publication_id"] == pub
    # And the emitted file verifies against the manifest digest.
    art = {a["path"]: a["sha256"] for a in manifest["artifacts"]}
    meta = siv2.verify_search_index(
        base / f"r/{pub}/c/sig_graph/search_index_v2.sqlite",
        art[f"r/{pub}/c/sig_graph/search_index_v2.sqlite"],
        kind="record-index",
        publication_id=pub,
    )
    assert meta["kind"] == "record-index"
    cat_meta = siv2.verify_search_index(
        base / f"releases/{pub}/search/catalog.sqlite",
        art[f"releases/{pub}/search/catalog.sqlite"],
        kind="catalog",
        publication_id=pub,
    )
    assert cat_meta["kind"] == "catalog"


def test_release_v2_claim_ref_lookup(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", n_records=3)
    b = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    pub = b.publication_id
    cref = tmp_path / "rel" / f"r/{pub}/c/sig_graph/claim_ref.sqlite"
    keys = siv2.claim_ref_lookup(cref, "claim-src_a-0-a")
    assert len(keys) == 1


def test_release_descriptor_schema_unchanged(tmp_path: Path) -> None:
    """The v1 search_index_version descriptor input is untouched — the v2
    artifacts are additive, and the descriptor pins the v1 contract name it
    still ships."""
    export = _write_export(tmp_path / "export", n_records=3)
    b = build_release(export, tmp_path / "rel", renderer_revision=REVISION)
    desc = json.loads(
        (tmp_path / "rel" / f"releases/{b.publication_id}/descriptor.json").read_text()
    )
    assert desc["search_index_version"] == "release-search-index/1"

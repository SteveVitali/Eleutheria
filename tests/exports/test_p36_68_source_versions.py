# SPDX-License-Identifier: Apache-2.0
"""P36.68 (R11-K13-UX9-4, K9 §7.2, SIG-TRANSP-032) — per-source extracts'
datapackage, the sig.source-versions/1 index (incl. manifest-only prior
releases + the per-source TX-14 diff filter), and the bounded
digest-verified release-path push."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exports.distribution import ObjectStore
from exports.downloads import (
    SOURCE_EXTRACT_SCHEMA,
    emit_source_slice,
    source_datapackage,
)
from exports.push import (
    PushRefusal,
    push_release_paths,
    release_integrity_digests,
    resolve_release_pub,
)
from exports.source_versions import (
    MANIFEST_ONLY_REASON,
    SOURCE_VERSIONS_SCHEMA,
    load_previous_versions,
    manifest_files_from_integrity,
    manifest_only_entry,
    per_source_diff_counts,
    slice_files_from_listing,
    version_entry,
    versions_document,
)

ATTR = {
    "license": "CC-BY-4.0",
    "license_url": "https://x",
    "attribution_required": True,
    "sources": [
        {"source_id": "src_a", "name": "A", "rows": 3, "license": "CC-BY-4.0"},
    ],
}
SITES = b"a,source_id\n1,src_a\n2,src_a\n"
STMTS = b'{"source_id":"src_a","id":1}\n{"source_id":"src_a","id":2}\n'


def test_source_datapackage_shape_and_digests():
    files, counts = emit_source_slice(
        "src_a",
        sites_csv=SITES,
        statements_jsonl=STMTS,
        slice_ids=frozenset({"src_a"}),
        attribution_payload=ATTR,
        license_id="CC-BY-4.0",
        license_url="https://x",
        compartment="sig_graph",
        release_id="rel-1",
    )
    assert set(files) == {
        "by-source/src_a/sites.csv.gz",
        "by-source/src_a/statements.jsonl.gz",
        "by-source/src_a/ATTRIBUTION.txt",
        "by-source/src_a/LICENCE.txt",
        "by-source/src_a/datapackage.json",
    }
    doc = json.loads(files["by-source/src_a/datapackage.json"])
    assert doc["schema"] == SOURCE_EXTRACT_SCHEMA
    assert doc["source_id"] == "src_a"
    assert doc["release_id"] == "rel-1"
    assert doc["licenses"][0]["name"] == "CC-BY-4.0"
    names = {r["name"] for r in doc["resources"]}
    assert {"sites.csv.gz", "statements.jsonl.gz", "ATTRIBUTION.txt", "LICENCE.txt"} <= names
    rows = {r["name"]: r.get("rows") for r in doc["resources"]}
    assert rows["sites.csv.gz"] == 2 and rows["statements.jsonl.gz"] == 2
    for res in doc["resources"]:
        assert len(res["sha256"]) == 64 and res["bytes"] > 0


def test_source_datapackage_licenseref_has_no_path():
    doc = json.loads(
        source_datapackage(
            "s",
            {"by-source/s/statements.jsonl.gz": b"x"},
            {},
            license_id="LicenseRef-Y",
            license_url=None,
            compartment="c",
        )
    )
    assert doc["licenses"][0] == {"name": "LicenseRef-Y", "title": "LicenseRef-Y"}


LISTING = {
    "files": [
        {
            "path": "by-source/src_a/sites.csv.gz",
            "name": "sites.csv.gz",
            "format": "csv.gz",
            "byte_size": 10,
            "sha256": "a" * 64,
            "href": "h1",
            "row_count": 7,
            "source_id": "src_a",
        },
        {
            "path": "by-source/src_a/statements.jsonl.gz",
            "name": "statements.jsonl.gz",
            "format": "jsonl.gz",
            "byte_size": 20,
            "sha256": "b" * 64,
            "href": "h2",
            "row_count": 9,
            "source_id": "src_a",
        },
        {
            "path": "by-source/other/statements.jsonl.gz",
            "name": "statements.jsonl.gz",
            "format": "jsonl.gz",
            "byte_size": 5,
            "sha256": "c" * 64,
            "href": "h3",
            "row_count": 1,
            "source_id": "other",
        },
    ]
}


def test_slice_files_from_listing_is_source_scoped():
    files = slice_files_from_listing(LISTING, "src_a")
    assert [f["name"] for f in files] == ["sites.csv.gz", "statements.jsonl.gz"]
    assert files[0]["href"] == "h1" and files[0]["rows"] == 7


def _write_record_tree(root: Path, pub: str, comp: str, records: dict[str, dict]):
    idx = root / "r" / pub / "c" / comp
    idx.mkdir(parents=True, exist_ok=True)
    lines = []
    for key, doc in records.items():
        rel = f"r/{pub}/c/{comp}/{key}.json"
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(json.dumps(doc))
        lines.append(
            json.dumps(
                {
                    "record_key": key,
                    "entity_type": "site",
                    "entity_id": doc.get("entity_id"),
                    "label": doc.get("label", key),
                    "json_path": rel,
                }
            )
        )
    (idx / "records.index.jsonl").write_text("\n".join(lines) + "\n")


def test_per_source_diff_counts():
    cur, prev = Path("/nonexistent-cur"), Path("/nonexistent-prev")
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        cur = Path(td) / "cur"
        prev = Path(td) / "prev"
        _write_record_tree(
            cur,
            "p-cur",
            "comp",
            {
                "k1": {
                    "entity_id": "e1",
                    "label": "one",
                    "claim_anchors": [{"claim_id": "c1", "source_id": "src_a"}],
                },
                "k2": {"entity_id": "e2", "label": "two", "source_refs": [{"source_id": "src_b"}]},
            },
        )
        _write_record_tree(
            prev,
            "p-prev",
            "comp",
            {
                "k1": {
                    "entity_id": "e1",
                    "label": "one-old",
                    "claim_anchors": [{"claim_id": "c0", "source_id": "src_a"}],
                },
                "k3": {
                    "entity_id": "e3",
                    "label": "three",
                    "source_refs": [{"source_id": "src_a"}],
                },
            },
        )
        diff = {
            "comp": {
                "added": [{"record_key": "k2"}],
                "removed": [{"record_key": "k3"}],
                "changed": [{"record_key": "k1", "changed_columns": "label"}],
            }
        }
        counts = per_source_diff_counts(
            diff, cur_root=cur, cur_pub="p-cur", prev_root=prev, prev_pub="p-prev"
        )
        assert counts["src_a"] == {"added": 0, "removed": 1, "changed": 1}
        assert counts["src_b"] == {"added": 1, "removed": 0, "changed": 0}


def test_version_entry_states_and_changed_flag():
    files = slice_files_from_listing(LISTING, "src_a")
    e = version_entry(
        "src_a",
        release={"publication_id": "p1"},
        files=files,
        diff_counts={"added": 1, "removed": 0, "changed": 0},
        baseline=False,
        previous_slice_sha="0" * 64,
        published_claims=9,
    )
    assert e["state"] == "extract" and e["changed"] is True
    assert e["rows"] == {"sites": 7, "statements": 9}
    e2 = version_entry(
        "src_a",
        release={"publication_id": "p2"},
        files=files,
        diff_counts={"added": 0, "removed": 0, "changed": 0},
        baseline=False,
        previous_slice_sha="b" * 64,
    )
    assert e2["changed"] is False and e2["diff"]["state"] == "evaluated"
    e3 = version_entry(
        "src_a", release={"publication_id": "p3"}, files=[], diff_counts=None, baseline=True
    )
    assert e3["state"] == "extract_absent" and "absence" in e3 and e3["changed"] is True


def test_manifest_only_entry():
    integrity = {
        "artifacts": [
            {"path": "by-source/src_a/sites.csv.gz", "sha256": "a" * 64, "byte_size": 11},
            {"path": "sig_graph/sites.csv", "sha256": "d" * 64, "byte_size": 1},
        ]
    }
    mfiles = manifest_files_from_integrity(integrity, "src_a")
    assert len(mfiles) == 1 and mfiles[0]["sha256"] == "a" * 64
    e = manifest_only_entry(
        "src_a", release={"publication_id": "p0"}, manifest_files=mfiles, published_claims=4
    )
    assert e["state"] == "manifest_only" and e["extract"] == "not_republished"
    assert MANIFEST_ONLY_REASON in e["reason"]
    doc = versions_document("src_a", [e])
    assert doc["schema"] == SOURCE_VERSIONS_SCHEMA and doc["entry_count"] == 1


def test_load_previous_versions_superset(tmp_path):
    root = tmp_path
    p = root / "r" / "p-prev" / "transparency" / "sources" / "src_a"
    p.mkdir(parents=True)
    (p / "versions.json").write_text(
        json.dumps(
            {
                "schema": SOURCE_VERSIONS_SCHEMA,
                "source_id": "src_a",
                "entries": [{"release": {"publication_id": "p0"}, "state": "extract"}],
            }
        )
    )
    entries = load_previous_versions(root, "p-prev", "src_a")
    assert entries is not None and len(entries) == 1
    assert load_previous_versions(root, "p-prev", "other") is None
    assert load_previous_versions(None, "p-prev", "src_a") is None


class _FakeS3:
    def __init__(self):
        self.puts: list[dict] = []
        self.exists: set[str] = set()

    def put_object(self, **kw):
        self.puts.append(kw)

    def head_object(self, **kw):
        if kw["Key"] in self.exists:
            return {}
        raise Exception("NoSuchKey")


def _release_tree(tmp: Path, files: dict[str, str]) -> tuple[Path, str]:
    pub = "p-" + "a" * 60
    (tmp / "releases" / pub).mkdir(parents=True)
    arts = []
    import hashlib

    for rel, body in files.items():
        rel = rel.format(pub=pub)
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(body)
        arts.append({"path": rel, "sha256": hashlib.sha256(body.encode()).hexdigest()})
    (tmp / "releases" / pub / "integrity_manifest.json").write_text(json.dumps({"artifacts": arts}))
    return tmp, pub


def test_push_release_paths_digest_verified_content_keys(tmp_path):
    rel = "r/{pub}/transparency/sources/src_a/versions.json"
    tree, pub = _release_tree(tmp_path, {rel: "{}"})
    rel = rel.format(pub=pub)
    client = _FakeS3()
    store = ObjectStore(provider="cloudflare-r2", bucket="sig-bulk")
    out = push_release_paths(tree, store, client, paths=[rel], strip_prefix=f"r/{pub}/")
    assert len(out) == 1
    assert out[0].key.startswith(f"{pub}/transparency/sources/src_a/versions.")
    assert out[0].key.endswith(".json")
    assert client.puts[0]["CacheControl"].startswith("public")
    # second push of the same bytes is an append-only no-op
    client.exists.add(out[0].key)
    out2 = push_release_paths(tree, store, client, paths=[rel], strip_prefix=f"r/{pub}/")
    assert out2[0].skipped is True and len(client.puts) == 1


def test_push_release_paths_refuses_unlisted_and_mismatch(tmp_path):
    rel = "r/{pub}/transparency/sources/src_a/versions.json"
    tree, pub = _release_tree(tmp_path, {rel: "{}"})
    rel = rel.format(pub=pub)
    client = _FakeS3()
    store = ObjectStore(provider="cloudflare-r2", bucket="sig-bulk")
    unlisted = f"r/{pub}/transparency/sources/x/versions.json"
    p = tree / unlisted
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("{}")
    with pytest.raises(PushRefusal, match="not an integrity-manifest artifact"):
        push_release_paths(tree, store, client, paths=[unlisted])
    (tree / rel).write_text('{"tampered": true}')
    with pytest.raises(PushRefusal, match="sha256"):
        push_release_paths(tree, store, client, paths=[rel])


def test_release_integrity_digests_and_pub_resolution(tmp_path):
    tree, pub = _release_tree(tmp_path, {"r/x/f.json": "{}"})
    assert resolve_release_pub(tree) == pub
    assert release_integrity_digests(tree, pub)["r/x/f.json"]
    empty = tmp_path / "empty"
    (empty / "releases").mkdir(parents=True)
    with pytest.raises(PushRefusal):
        resolve_release_pub(empty)

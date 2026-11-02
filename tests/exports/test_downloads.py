# SPDX-License-Identifier: Apache-2.0
"""P36.50 (R11-K13-TX-10b / J3 §6, SIG-TRANSP-014/015/018, D-J3-8 = a): the
downloads-center artifacts — per-source slices, ATTRIBUTION/LICENCE.txt,
SHA256SUMS + the minisign pair, and the sig.download-listing/1 document.
"""

from __future__ import annotations

import csv
import gzip
import io
import json
import tempfile
from datetime import date
from pathlib import Path

import pytest
from exports.manifest import BuildSpec
from exports.shaping import ShapingClaim, build_shaped_dataset, parse_shaping_claims
from exports.spine_export import build_spine_export

from exports import downloads


def _claim(
    cid: str, sid: str, pred: str, val: str, source_id: str, spdx: str = "CC-BY-4.0"
) -> ShapingClaim:
    return ShapingClaim(
        claim_id=cid,
        subject_id=sid,
        predicate_id=pred,
        value_kind="value",
        value_text=val,
        value_num=None,
        raw_value=val,
        observed_at=date(2026, 11, 1),
        sensitivity_tier=0,
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id=f"r-{source_id}",
        effective_spdx=spdx,
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution=f"© {source_id}",
        effective_terms_url="https://x/t",
    )


def _export(sources=("/src_a/",), spdx="CC-BY-4.0"):
    claims = [
        c
        for i, sid in enumerate(sources)
        for c in (
            _claim(f"c{i}", "S0", "camera_latitude", "35.5", sid, spdx),
            _claim(f"c{i}l", "S0", "camera_longitude", "-97.5", sid, spdx),
        )
    ]
    rows = [
        (
            c.claim_id,
            c.subject_id,
            c.predicate_id,
            c.value_kind,
            c.value_text,
            c.value_num,
            c.raw_value,
            c.observed_at,
            c.sensitivity_tier,
            c.source_id,
            c.connector_name,
            c.occurrence_capture_id,
            c.occurrence_retrieved_at,
            c.occurrence_bound_at,
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
        )
        for c in claims
    ]
    raw = {
        "shaping_claims": rows,
        "subject_entities": [("S0", "deployment")],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    ds = build_shaped_dataset(
        raw,
        as_of="2026-11-01",
        generated_at="2026-11-01T00:00:00Z",
        spine_label="unit",
    )
    return build_spine_export(
        ds,
        {},
        build_spec=BuildSpec(
            as_of_snapshot=date(2026, 11, 1),
            as_of_belief=date(2026, 11, 1),
            ruleset_version="r/1",
            resolver_version="v/1",
        ),
        generated_at="2026-11-01T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={"S0": "deployment"},
    )


# --- unit-level ------------------------------------------------------------


def test_sha256sums_gnu_format() -> None:
    text = downloads.sha256sums_bytes([("b.txt", "a" * 64), ("a.txt", "b" * 64)])
    lines = text.decode().splitlines()
    assert lines[0] == f"{'b' * 64}  a.txt"  # sorted by path
    assert lines[1] == f"{'a' * 64}  b.txt"


def test_csv_and_jsonl_slices_filter_on_source_id() -> None:
    csv_bytes = b"source_id,name\na,x\nb,y\na,z\n"
    out, kept = downloads._csv_slice(csv_bytes, frozenset({"a"}))
    rows = list(csv.reader(io.StringIO(out.decode())))
    assert kept == 2 and rows[0] == ["source_id", "name"] and len(rows) == 3
    jl = b'{"source_id":"a","x":1}\n{"source_id":"b","x":2}\n{"source_id":"a","x":3}\n'
    out, kept = downloads._jsonl_slice(jl, frozenset({"a"}))
    assert kept == 2 and len(out.splitlines()) == 2


def test_slice_source_ids_groups_rights_suffixed_ids() -> None:
    m = downloads.slice_source_ids(
        [{"source_id": "src@r1"}, {"source_id": "src@r2"}, {"source_id": "other"}]
    )
    assert m["src"] == frozenset({"src@r1", "src@r2"})
    assert m["other"] == frozenset({"other"})


def test_attribution_txt_carries_terms_and_basis() -> None:
    payload = {
        "license": "LicenseRef",
        "license_url": None,
        "attribution_required": True,
        "publication_basis": "basis",
        "note": "n",
        "sources": [
            {
                "source_id": "s1",
                "name": "S One",
                "rows": 3,
                "license": "LicenseRef",
                "attribution_required": True,
                "attribution": "© S One",
                "terms_url": "https://t",
                "captured_terms_verbatim": "verbatim terms",
                "captured_terms_evidence": "cap/1",
                "publication_basis": "accepted",
            }
        ],
    }
    txt = downloads.attribution_txt(payload, title="t").decode()
    assert "verbatim terms" in txt and downloads.ADR_183_BASIS in txt
    with pytest.raises(downloads.DownloadError):
        downloads.attribution_txt(None, title="x")  # type: ignore[arg-type]


def test_emit_source_slice_refuses_empty_attribution() -> None:
    with pytest.raises(downloads.DownloadError):
        downloads.emit_source_slice(
            "s1",
            sites_csv=b"source_id\ns1\n",
            statements_jsonl=b"",
            slice_ids=frozenset({"s1"}),
            attribution_payload=None,
            license_id="CC-BY-4.0",
            license_url="https://u",
        )


# --- the built export ------------------------------------------------------


def test_export_emits_slices_txt_and_listing() -> None:
    ex = _export(sources=("src_a",))
    paths = {a.path for a in ex.manifest.artifacts}
    assert "by-source/src_a/statements.jsonl.gz" in paths
    assert "by-source/src_a/ATTRIBUTION.txt" in paths
    assert "by-source/src_a/LICENCE.txt" in paths
    assert "sig_graph/ATTRIBUTION.txt" in paths
    assert "sig_graph/LICENCE.txt" in paths
    assert "web/downloads.json" in paths
    doc = json.loads(ex.metadata_artifacts["web/downloads.json"])
    assert doc["schema"] == "sig.download-listing/1"
    assert doc["signature"]["state"] == "unsigned"
    assert doc["signature"]["reason"]
    assert doc["mirror"]["base_url"].startswith("https://")
    src_groups = [g for g in doc["groups"] if g["kind"] == "source"]
    assert src_groups and src_groups[0]["files"]
    # every file row carries the J3 §6.1 fieldset
    for f in doc["files"]:
        assert (
            f["license"]
            and f["sha256"]
            and f["href"].startswith("https://files.surveillancegraph.org/")
        )
    # the slice's statements rows decompress to sig.statement/1 rows only
    for a in ex.manifest.artifacts:
        if a.path == "by-source/src_a/statements.jsonl.gz":
            rows = [
                json.loads(line)
                for line in gzip.decompress(ex.web_artifacts[a.path]).decode().splitlines()
                if line.strip()
            ]
            assert rows and all(r["schema"] == "sig.statement/1" for r in rows)
            assert all(r["source_id"].startswith("src_a") for r in rows)
            break
    else:
        pytest.fail("statements slice missing")


def test_write_integrity_files_and_verify() -> None:
    ex = _export(sources=("src_a",))
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        ex.write_to(root)
        sums = (root / downloads.SHA256SUMS_FILE).read_text()
        for line in sums.splitlines():
            sha, path = line.split("  ", 1)
            assert len(sha) == 64
        assert "manifest.json" in sums
        rep = downloads.verify_downloads(root)
        assert rep["state"] == "unsigned" and not rep["failures"]
        # signed export verifies
        from exports.minisign import generate_keypair

        pub, secret = generate_keypair()
        ex.write_to(root, signing_secret_b64=secret)
        assert (root / downloads.MINISIG_FILE).is_file()
        assert (root / downloads.PUBKEY_FILE).read_text() == pub
        rep = downloads.verify_downloads(root)
        assert rep["state"] == "signed" and not rep["failures"]
        # tamper → incomplete, loudly
        f = root / "sig_graph" / "LICENCE.txt"
        f.write_bytes(f.read_bytes() + b"x")
        rep = downloads.verify_downloads(root)
        assert rep["state"] == "incomplete"
        assert any("LICENCE.txt" in x for x in rep["failures"])


def test_listing_mirror_href_content_hash_form() -> None:
    href = downloads.download_href(
        "https://files.surveillancegraph.org", "rel-1", "comp/a.csv", "ab" * 32
    )
    assert href.startswith("https://files.surveillancegraph.org/rel-1/comp/a.")
    assert href.endswith(".csv")
    assert "." + ("ab" * 32)[:12] + "." in href


def test_release_emits_immutable_downloads_listing() -> None:
    """`/releases/<pub>/data/` — bound listing + T0 page + integrity copies."""
    from exports.release import build_release

    ex = _export(sources=("src_a",))
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        export_dir = root / "export"
        ex.write_to(export_dir)
        rel = build_release(
            export_dir,
            root / "rel",
            renderer_revision="rev" * 8,
        )
        pub = rel.publication_id
        base = root / "rel" / "releases" / pub / "data"
        listing = json.loads(
            (base / "download_listing.json").read_text(encoding="utf-8")
        )
        assert listing["schema"] == "sig.download-listing/1"
        assert listing["publication_id"] == pub
        assert (base / "index.html").is_file()
        html = (base / "index.html").read_text(encoding="utf-8")
        assert "<script" not in html  # T0: no script, ever
        assert "SHA256SUMS" in html and "/data/" in html
        assert (base / "SHA256SUMS").is_file()
        assert not (base / "SHA256SUMS.minisig").exists()  # unsigned is honest
        # integrity-listed: every emitted byte is in the release manifest
        manifest = json.loads(
            (root / "rel" / "releases" / pub / "integrity_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        names = {a["path"] for a in manifest["artifacts"]}
        assert f"releases/{pub}/data/download_listing.json" in names
        assert f"releases/{pub}/data/index.html" in names
        assert f"releases/{pub}/data/SHA256SUMS" in names


def test_release_without_listing_is_back_compat() -> None:
    """A pre-P36.50 export (no web/downloads.json) emits no data page."""
    from exports.release import build_release

    ex = _export(sources=("src_a",))
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        export_dir = root / "export"
        ex.write_to(export_dir)
        (export_dir / "web" / "downloads.json").unlink()
        rel = build_release(
            export_dir,
            root / "rel",
            renderer_revision="rev" * 8,
        )
        pub = rel.publication_id
        assert not (root / "rel" / "releases" / pub / "data").exists()

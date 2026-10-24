# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.51 (SIG-FIND-005, F-173, K0 §4.12.6): the deterministic synthetic
national fixture's contract tests — the state every page-type budget row is
measured under must be real-sized, deterministic and invented-names-only.

The full fixture (~232k sites / ~181 MB of tiles) is CI-generated per run and
gitignored; these tests prove the CONTRACT at reduced scale — same generator,
same seed, same renderer — plus the declared floors verbatim and the F-173
name guard as an executable check, never a comment.
"""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import pytest
from support import REPO_ROOT

FIXTURE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "build_national_fixture.py"


def _load(name: str = "sig_build_national_fixture_test"):
    spec = importlib.util.spec_from_file_location(name, FIXTURE_SCRIPT)
    assert spec and spec.loader, f"cannot load {FIXTURE_SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture()
def small(monkeypatch, tmp_path):
    """The generator at reduced counts — same seed/RNG/renderer, fast enough
    for a unit test (the full-scale floors are asserted verbatim elsewhere)."""
    mod = _load()
    monkeypatch.setattr(mod, "SITE_COUNT", 400)
    monkeypatch.setattr(mod, "AGENCY_COUNT", 40)
    monkeypatch.setattr(mod, "PARTNER_COUNT", 30)
    monkeypatch.setattr(mod, "SHARING_EDGE_COUNT", 600)
    monkeypatch.setattr(mod, "ACCESS_PATH_COUNT", 6)
    return mod


def _tree_sha256s(root: Path) -> dict[str, str]:
    return {
        str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def test_declared_floors_meet_the_ticket_counts() -> None:
    """K0 §4.12.6 verbatim: ≥ 232k sites / ≥ 5k agencies / ≥ 400k edges."""
    mod = _load()
    assert mod.SITE_COUNT >= 232_000
    assert mod.AGENCY_COUNT >= 5_000
    assert mod.SHARING_EDGE_COUNT >= 400_000
    assert mod.SEED, "the seed is a committed constant, not runtime entropy"


def test_two_runs_are_byte_identical(small, tmp_path) -> None:
    """Determinism: same committed seed → byte-identical tree, PMTiles
    included (the archive must be reproducible or the budget measurements
    under it are not)."""
    a, b = tmp_path / "a", tmp_path / "b"
    small.build(a)
    small.build(b)
    sa, sb = _tree_sha256s(a), _tree_sha256s(b)
    assert sa == sb, (
        f"fixture is not deterministic — differing artifacts: "
        f"{sorted(k for k in set(sa) | set(sb) if sa.get(k) != sb.get(k))}"
    )


def test_fixture_block_and_manifest_carry_provenance(small, tmp_path) -> None:
    block = small.build(tmp_path)
    assert block["schema"] == "sig.national-fixture/1"
    assert block["synthetic"] is True
    assert block["invented_names_only"] is True
    assert block["seed"] == small.SEED
    assert block["focus_entity_id"] == small.FOCUS_ENTITY_ID
    counts = block["counts"]
    assert counts["sites"] == small.SITE_COUNT
    assert counts["agencies"] == small.AGENCY_COUNT
    assert counts["sharing_edges"] == small.SHARING_EDGE_COUNT
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["fixture"]["seed"] == small.SEED
    assert manifest["release_id"] == "syn-national-fixture"
    # Every artifact the manifest lists exists with its recorded digest.
    for artifact in manifest["artifacts"]:
        path = tmp_path / artifact["path"]
        assert path.is_file(), f"manifest lists a missing artifact: {artifact['path']}"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_every_human_label_is_invented(small, tmp_path) -> None:
    """F-173 at the artifact level: walk every emitted label — no blocklist
    token appears and every generated name carries the synthetic marker."""
    small.build(tmp_path)
    labels: list[str] = []
    for rel in ("web/map.json", "web/network.json", "sig_graph/ATTRIBUTION.json"):
        doc = json.loads((tmp_path / rel).read_text())

        def walk(node):
            if isinstance(node, dict):
                # Entity labels only — structural layer/section labels
                # ("Physical devices") are UI vocabulary, not emitted names.
                if (
                    isinstance(node.get("id"), str)
                    and node["id"].startswith(("site:", "agency:", "vendor:", "rtcc:"))
                    and isinstance(node.get("label"), str)
                ):
                    labels.append(node["label"])
                for v in node.values():
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)

        walk(doc)
    assert labels, "the fixture emitted no labels — the check is vacuous"
    for label in labels:
        assert "syn" in label.lower(), f"non-synthetic label emitted: {label!r}"
        low = label.lower()
        for token in small.REAL_NAME_BLOCKLIST:
            assert token not in low, f"real-name token {token!r} in {label!r}"


def test_name_guard_refuses_a_real_name() -> None:
    """The F-173 guard is a test, not a comment: a doctored row carrying a
    real agency/vendor name fails — and a name without the invented marker
    is a generator bug, never a coincidence to bless."""
    mod = _load()
    for bad in (
        "Flock Safety ALPR",
        "Oklahoma City Police Department",
        "the Axon integration",
    ):
        with pytest.raises(ValueError, match="name guard"):
            mod.assert_no_real_names({"label": bad}, where="test")
    with pytest.raises(ValueError, match="invented marker"):
        mod._check_generated_name("Municipal Agency 00042")


def test_build_fails_if_a_generator_emits_a_real_name(small, tmp_path, monkeypatch) -> None:
    """End-to-end guard: if any generator row ever carries a real name, the
    build itself fails — the synthetic fixture can never masquerade as an
    observed corpus."""
    real_gen = small.gen_network

    def poisoned(rng):
        net = real_gen(rng)
        net["nodes"][0]["label"] = "Flock Safety Group"
        return net

    monkeypatch.setattr(small, "gen_network", poisoned)
    with pytest.raises(ValueError, match="name guard"):
        small.build(tmp_path)


def _read_directory(raw: bytes) -> list[tuple[int, int, int, int]]:
    """Decode one PMTiles v3 directory section into
    ``(tile_id, run_length, offset, length)`` — mirrors
    ``tests/exports/test_tiles.py``."""
    pos = 0

    def varint() -> int:
        nonlocal pos
        shift = 0
        val = 0
        while True:
            b = raw[pos]
            pos += 1
            val |= (b & 0x7F) << shift
            if not (b & 0x80):
                return val
            shift += 7

    n = varint()
    ids = []
    prev = 0
    for _ in range(n):
        prev += varint()
        ids.append(prev)
    runs = [varint() for _ in range(n)]
    lengths = [varint() for _ in range(n)]
    offsets: list[int] = []
    for i in range(n):
        stored = varint()
        if i > 0 and stored == 0:
            offsets.append(offsets[i - 1] + lengths[i - 1])
        else:
            offsets.append(stored - 1)
    return list(zip(ids, runs, offsets, lengths, strict=True))


def test_pmtiles_archive_is_valid_v3(small, tmp_path) -> None:
    """The tile path the national map measures is the production renderer's —
    the emitted archive must be a spec-valid PMTiles v3 with tile entries and
    the compartment licence metadata."""
    import struct

    small.build(tmp_path)
    # sig.map-tiles/2: the archive name carries the content hash.
    found = list((tmp_path / "web" / "tiles").glob(f"{small.COMPARTMENT}-sites*.pmtiles"))
    assert found, "no per-compartment archive was emitted"
    data = found[0].read_bytes()
    assert data[0:7] == b"PMTiles" and data[7] == 3, "not a PMTiles v3 archive"
    root_off = struct.unpack_from("<Q", data, 8)[0]
    root_len = struct.unpack_from("<Q", data, 16)[0]
    meta_off = struct.unpack_from("<Q", data, 24)[0]
    meta_len = struct.unpack_from("<Q", data, 32)[0]
    data_len = struct.unpack_from("<Q", data, 64)[0]
    addressed = struct.unpack_from("<Q", data, 72)[0]
    assert addressed >= 1, "the archive addresses no tiles"
    root = _read_directory(gzip.decompress(data[root_off : root_off + root_len]))
    assert root, "empty root directory"
    # The compressed root fits inside the reader's 16 KiB optimistic first
    # read — the leaf-directory contract P35.51 added.
    assert root_len <= 16 * 1024
    meta = json.loads(gzip.decompress(data[meta_off : meta_off + meta_len]))
    assert "vector_layers" in meta
    assert data_len > 0


def test_focus_and_ids_never_name_the_demo_corpus(small, tmp_path) -> None:
    """The national focus is the declared synthetic entity — never the
    committed demo corpus's ``agency:okcpd`` inside a national graph."""
    small.build(tmp_path)
    net = json.loads((tmp_path / "web" / "network.json").read_text())
    ids = {n["id"] for n in net["nodes"]}
    assert small.FOCUS_ENTITY_ID in ids
    assert all(
        id_.startswith(("agency:syn", "vendor:syn", "rtcc:syn", "agency:syn")) or "syn" in id_
        for id_ in ids
    )
    centrality = json.loads((tmp_path / "web" / "analytics" / "centrality.json").read_text())
    assert centrality["focus"]["entity_id"] == small.FOCUS_ENTITY_ID
    assert "okcpd" not in json.dumps(net).lower()

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""OCFL 1.1 store: readable-without-SIG, dedup, versioning (SIG-EVID-004/005)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from evidence.ocfl import OcflStore, object_path
from evidence.storage import LocalFileStore

_WHEN = datetime(2026, 5, 1, tzinfo=UTC)


def _store(tmp_path: Path) -> OcflStore:
    return OcflStore(LocalFileStore(tmp_path))


def test_object_readable_without_sig_code(tmp_path: Path) -> None:
    """AC1/SIG-EVID-005: resolve version -> digest -> path using ONLY stdlib.

    This deliberately does not call any evidence.* resolver: it reads the OCFL
    inventory.json and walks it exactly as a third party with no SIG software
    would, proving the store is recoverable on its own.
    """
    store = _store(tmp_path)
    store.add_version("urn:sig:source:portal:x", {"index.html": b"<html>v1</html>"}, created=_WHEN)

    root = tmp_path / object_path("urn:sig:source:portal:x")
    inventory = json.loads((root / "inventory.json").read_text())

    # Namaste + sidecar exist and the sidecar matches the inventory bytes.
    assert (root / "0=ocfl_object_1.1").is_file()
    sidecar = (root / "inventory.json.sha512").read_text().split()[0]
    assert sidecar == hashlib.sha512((root / "inventory.json").read_bytes()).hexdigest()

    # Walk version -> state digest -> manifest content path -> bytes, by hand.
    head = inventory["head"]
    state = inventory["versions"][head]["state"]
    (want_digest,) = [d for d, paths in state.items() if "index.html" in paths]
    content_path = inventory["manifest"][want_digest][0]
    data = (root / content_path).read_bytes()
    assert data == b"<html>v1</html>"
    assert hashlib.sha512(data).hexdigest() == want_digest


def test_storage_root_declares_ocfl_and_layout(tmp_path: Path) -> None:
    store = _store(tmp_path)
    store.add_version("urn:sig:source:portal:y", {"a.txt": b"a"}, created=_WHEN)
    assert (tmp_path / "0=ocfl_1.1").read_text() == "ocfl_1.1\n"
    layout = json.loads((tmp_path / "ocfl_layout.json").read_text())
    assert layout["extension"] == "0003-hash-and-id-n-tuple-storage-layout"


def test_unchanged_bytes_dedup_to_one_blob_many_versions(tmp_path: Path) -> None:
    """SIG-EVID-004: a re-fetch of unchanged bytes is one blob, N versions."""
    store = _store(tmp_path)
    oid = "urn:sig:source:portal:z"
    v1 = store.add_version(oid, {"index.html": b"unchanged"}, created=_WHEN)
    v2 = store.add_version(oid, {"index.html": b"unchanged"}, created=_WHEN)

    assert v1.version == "v1" and v2.version == "v2"
    assert v2.deduplicated == ("index.html",)  # no new content written
    assert v2.new_content_paths == {}

    inventory = store.read_inventory(oid)
    assert set(inventory["versions"]) == {"v1", "v2"}
    # One stored blob: exactly one manifest digest, one content file on disk.
    assert len(inventory["manifest"]) == 1
    content_files = list((tmp_path / object_path(oid)).rglob("content/*"))
    assert len(content_files) == 1


def test_changed_bytes_add_a_new_content_blob(tmp_path: Path) -> None:
    store = _store(tmp_path)
    oid = "urn:sig:source:portal:w"
    store.add_version(oid, {"index.html": b"v1"}, created=_WHEN)
    v2 = store.add_version(oid, {"index.html": b"v2-changed"}, created=_WHEN)
    assert v2.deduplicated == ()
    assert "index.html" in v2.new_content_paths
    assert len(store.read_inventory(oid)["manifest"]) == 2


def test_resolver_matches_hand_walk(tmp_path: Path) -> None:
    store = _store(tmp_path)
    oid = "urn:sig:source:portal:r"
    store.add_version(oid, {"a.txt": b"first"}, created=_WHEN)
    store.add_version(oid, {"a.txt": b"second"}, created=_WHEN)
    assert store.resolve(oid, "v1", "a.txt") == b"first"
    assert store.resolve(oid, "v2", "a.txt") == b"second"


def test_fixity_block_records_blake3(tmp_path: Path) -> None:
    store = _store(tmp_path)
    oid = "urn:sig:source:portal:f"
    store.add_version(oid, {"a.txt": b"payload"}, created=_WHEN)
    inventory = store.read_inventory(oid)
    assert inventory["fixity"]["blake3"]  # SIG-EVID-003/005


def test_object_path_is_deterministic() -> None:
    p1 = object_path("urn:sig:source:portal:x")
    p2 = object_path("urn:sig:source:portal:x")
    assert p1 == p2
    assert p1.count("/") == 3  # three tuples + encapsulation dir

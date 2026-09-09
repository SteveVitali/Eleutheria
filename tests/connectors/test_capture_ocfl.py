# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The OCFL-backed capture store adapter (§17, SIG-EVID-004/005, P21.3, LD-F03)."""

from __future__ import annotations

from datetime import UTC, datetime

from connectors.capture_ocfl import (
    CAPTURE_LOGICAL_PATH,
    WACZ_LOGICAL_PATH,
    OcflCaptureStore,
    capture_object_id,
)
from connectors.stages import InMemoryCaptureStore
from evidence.ocfl import OcflStore
from evidence.storage import LocalFileStore


def _store(tmp_path) -> OcflCaptureStore:  # type: ignore[no-untyped-def]
    return OcflCaptureStore(OcflStore(LocalFileStore(str(tmp_path))))


def test_put_then_get_round_trips_the_bytes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = _store(tmp_path)
    data = b'{"hello": "world"}'
    ref = store.put(data, media_type="application/json", source_uri="https://x.test/a")
    assert store.has(ref.digest)
    assert store.get(ref.digest) == data
    assert ref.byte_size == len(data)


def test_digest_matches_the_in_memory_store_so_replay_is_byte_identical(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    # Additive/back-compat: the CaptureRef digest is the connectors' multihash,
    # identical to InMemoryCaptureStore, so post-capture stages + replay are
    # byte-identical whichever store backs the run (shadow_replay diff = 0).
    data = b"identical-bytes"
    ocfl_ref = _store(tmp_path).put(data, media_type="text/plain", source_uri="https://x.test/a")
    mem_ref = InMemoryCaptureStore().put(
        data, media_type="text/plain", source_uri="https://x.test/a"
    )
    assert ocfl_ref.digest == mem_ref.digest


def test_metadata_sidecar_records_retrieval_provenance_not_content(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    store = _store(tmp_path)
    when = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
    ref = store.put(
        b"page-bytes",
        media_type="text/html",
        source_uri="https://x.test/page",
        retrieved_at=when,
        headers={"ETag": '"abc"', "Content-Type": "text/html"},
    )
    meta = store.metadata(ref.digest)
    assert meta["source_uri"] == "https://x.test/page"
    assert meta["retrieved_at"] == when.isoformat()
    assert meta["headers"]["ETag"] == '"abc"'  # headers are provenance, kept for audit
    assert meta["media_type"] == "text/html"


def test_identical_bytes_deduplicate_to_one_object(tmp_path) -> None:  # type: ignore[no-untyped-def]
    # SIG-EVID-004: identical bytes are content-addressed to the same OCFL object.
    store = _store(tmp_path)
    data = b"same"
    a = store.put(data, media_type="text/plain", source_uri="https://x.test/1")
    b = store.put(data, media_type="text/plain", source_uri="https://x.test/2")
    assert a.digest == b.digest
    assert capture_object_id(a.digest) == capture_object_id(b.digest)


def test_object_is_a_conformant_ocfl_object_readable_without_sig(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    store = OcflStore(LocalFileStore(str(tmp_path)))
    adapter = OcflCaptureStore(store)
    ref = adapter.put(b"x", media_type="text/plain", source_uri="https://x.test/a")
    object_id = capture_object_id(ref.digest)
    assert store.object_exists(object_id)
    inventory = store.read_inventory(object_id)
    assert inventory["digestAlgorithm"] == "sha512"
    assert CAPTURE_LOGICAL_PATH in [
        p for paths in inventory["versions"]["v1"]["state"].values() for p in paths
    ]


def test_wacz_is_written_for_html_when_a_builder_is_supplied(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    # LD-F02/LD-H02: an HTML page optionally gets a WACZ via the P02.2 path.
    def fake_wacz(url: str, data: bytes) -> bytes:
        return b"PK-WACZ:" + url.encode()

    store = OcflStore(LocalFileStore(str(tmp_path)))
    adapter = OcflCaptureStore(store, wacz_builder=fake_wacz, capture_wacz=True)
    ref = adapter.put(b"<html></html>", media_type="text/html", source_uri="https://x.test/p")
    object_id = capture_object_id(ref.digest)
    inventory = store.read_inventory(object_id)
    logical = [p for paths in inventory["versions"]["v1"]["state"].values() for p in paths]
    assert WACZ_LOGICAL_PATH in logical
    assert store.resolve(object_id, "v1", WACZ_LOGICAL_PATH).startswith(b"PK-WACZ:")


def test_no_wacz_for_non_html_even_with_a_builder(tmp_path) -> None:  # type: ignore[no-untyped-def]
    def fake_wacz(url: str, data: bytes) -> bytes:  # pragma: no cover - must not run
        raise AssertionError("WACZ must not be built for a non-HTML media type")

    store = OcflStore(LocalFileStore(str(tmp_path)))
    adapter = OcflCaptureStore(store, wacz_builder=fake_wacz, capture_wacz=True)
    ref = adapter.put(b"{}", media_type="application/json", source_uri="https://x.test/j")
    inventory = store.read_inventory(capture_object_id(ref.digest))
    logical = [p for paths in inventory["versions"]["v1"]["state"].values() for p in paths]
    assert WACZ_LOGICAL_PATH not in logical

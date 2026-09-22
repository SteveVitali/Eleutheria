# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Pure-Python `.torrent` generation (§38.5, SIG-EXPORT-009): the zero-egress mirror."""

from __future__ import annotations

import hashlib

import pytest

from exports import torrent as TT


def test_bencode_roundtrip_and_canonical_key_order() -> None:
    doc = {"b": 2, "a": [b"x", 3], "c": {"z": 1}}
    encoded = TT.bencode(doc)
    # Dict keys are emitted in sorted order (canonical bencode).
    assert encoded.startswith(b"d1:a")
    assert TT.bdecode(encoded) == {b"a": [b"x", 3], b"b": 2, b"c": {b"z": 1}}


def test_bencode_rejects_bool() -> None:
    with pytest.raises(TypeError):
        TT.bencode(True)


def test_make_torrent_is_a_valid_single_file_metainfo() -> None:
    data = b"the bulk export bytes" * 5000
    tb = TT.make_torrent(data, "devices.parquet", announce_list=["udp://tracker.example:80"])
    doc = TT.bdecode(tb)
    assert isinstance(doc, dict)
    info = doc[b"info"]
    assert info[b"name"] == b"devices.parquet"
    assert info[b"length"] == len(data)
    # SHA-1 piece hashes: length is a multiple of 20, one per piece.
    pieces = info[b"pieces"]
    piece_len = info[b"piece length"]
    assert len(pieces) % 20 == 0
    expected_pieces = -(-len(data) // piece_len)  # ceil
    assert len(pieces) // 20 == expected_pieces
    # First piece hash matches a hand-computed SHA-1 of the first chunk.
    assert pieces[:20] == hashlib.sha1(data[:piece_len]).digest()  # noqa: S324
    assert doc[b"announce"] == b"udp://tracker.example:80"


def test_torrent_is_deterministic_no_creation_date() -> None:
    data = b"reproducible"
    a = TT.make_torrent(data, "x.bin")
    b = TT.make_torrent(data, "x.bin")
    assert a == b
    # No wall-clock creation date is embedded (reproducible mirror).
    assert b"creation date" not in a


def test_trackerless_torrent_is_valid() -> None:
    tb = TT.make_torrent(b"data", "x.bin")
    doc = TT.bdecode(tb)
    assert b"announce" not in doc  # a trackerless (DHT/magnet) torrent is still valid


def test_infohash_is_sha1_of_info_dict() -> None:
    tb = TT.make_torrent(b"data", "x.bin")
    doc = TT.bdecode(tb)
    assert TT.infohash_v1(tb) == hashlib.sha1(TT.bencode(doc[b"info"])).hexdigest()  # noqa: S324

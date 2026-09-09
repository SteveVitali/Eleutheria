# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Pure-Python BitTorrent metainfo (`.torrent`) generation (§38.5, SIG-EXPORT-009).

Egress pricing is the existential cost for a bulk-data project (see
:mod:`exports.distribution`). A ``.torrent`` moves a large export to a **zero-egress
peer-distribution path**: the low-cost mirror the succession plan (SIG-GOV-022) leans on.

This is a self-contained BitTorrent v1 metainfo writer — bencode + SHA-1 piece hashes —
so it needs **no daemon and no third-party dependency** (the zero-cost posture,
SIG-STORE-003). The output is a real, spec-conformant single-file ``.torrent`` a client
opens, and is a *deterministic* function of the file bytes + the announce list (the piece
hashes are content, the metainfo carries no wall-clock ``creation date``), so a mirror can
reproduce it. See ADR-067.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence

#: Default piece length (256 KiB) — a common choice for modest single-file torrents.
DEFAULT_PIECE_LENGTH = 256 * 1024


def bencode(value: object) -> bytes:
    """Encode ``value`` as bencode (BEP-3). Supports int, bytes/str, list, dict.

    Dict keys are emitted in sorted (raw-byte) order, as the spec requires, so the
    encoding — and therefore the infohash — is canonical and reproducible.
    """
    if isinstance(value, bool):  # guard: bool is an int subclass, but not a torrent int
        raise TypeError("bencode does not encode bool")
    if isinstance(value, int):
        return b"i" + str(value).encode("ascii") + b"e"
    if isinstance(value, bytes):
        return str(len(value)).encode("ascii") + b":" + value
    if isinstance(value, str):
        return bencode(value.encode("utf-8"))
    if isinstance(value, (list, tuple)):
        return b"l" + b"".join(bencode(v) for v in value) + b"e"
    if isinstance(value, Mapping):
        items = sorted(
            (k.encode("utf-8") if isinstance(k, str) else k, v) for k, v in value.items()
        )
        out = bytearray(b"d")
        for k, v in items:
            out += bencode(k)
            out += bencode(v)
        out += b"e"
        return bytes(out)
    raise TypeError(f"cannot bencode {type(value).__name__}")


def bdecode(data: bytes) -> object:
    """Decode a bencode document (used by the tests to validate produced ``.torrent``s)."""

    def _decode(i: int) -> tuple[object, int]:
        ch = data[i : i + 1]
        if ch == b"i":
            end = data.index(b"e", i)
            return int(data[i + 1 : end]), end + 1
        if ch == b"l":
            i += 1
            out: list[object] = []
            while data[i : i + 1] != b"e":
                item, i = _decode(i)
                out.append(item)
            return out, i + 1
        if ch == b"d":
            i += 1
            d: dict[bytes, object] = {}
            while data[i : i + 1] != b"e":
                key, i = _decode(i)
                val, i = _decode(i)
                assert isinstance(key, bytes)
                d[key] = val
            return d, i + 1
        if ch.isdigit():
            colon = data.index(b":", i)
            length = int(data[i:colon])
            start = colon + 1
            return data[start : start + length], start + length
        raise ValueError(f"bad bencode at byte {i}: {ch!r}")

    value, end = _decode(0)
    if end != len(data):
        raise ValueError("trailing bytes after bencode document")
    return value


def _pieces(data: bytes, piece_length: int) -> bytes:
    """The concatenated SHA-1 hashes of each ``piece_length`` chunk of ``data``."""
    out = bytearray()
    for off in range(0, max(len(data), 1), piece_length):
        out += hashlib.sha1(data[off : off + piece_length]).digest()  # noqa: S324 - BT v1 spec
    return bytes(out)


def make_torrent(
    data: bytes,
    name: str,
    *,
    announce_list: Sequence[str] = (),
    piece_length: int = DEFAULT_PIECE_LENGTH,
    comment: str | None = None,
) -> bytes:
    """Build a single-file BitTorrent v1 ``.torrent`` for ``data`` named ``name``.

    Deterministic (no ``creation date``): the same bytes + announce list always produce
    the same metainfo and infohash, so a mirror reproduces it (SIG-EXPORT-003 spirit).
    ``announce_list`` may be empty — a trackerless torrent is still valid and works with
    DHT/magnet peers, which is the resilient offline path (§46.5).
    """
    info: dict[str, object] = {
        "name": name,
        "length": len(data),
        "piece length": piece_length,
        "pieces": _pieces(data, piece_length),
    }
    metainfo: dict[str, object] = {"info": info, "created by": "sig-exports"}
    if announce_list:
        metainfo["announce"] = announce_list[0]
        metainfo["announce-list"] = [[a] for a in announce_list]
    if comment:
        metainfo["comment"] = comment
    return bencode(metainfo)


def infohash_v1(torrent_bytes: bytes) -> str:
    """The BitTorrent v1 infohash: SHA-1 of the bencoded ``info`` dict (magnet ``btih``)."""
    doc = bdecode(torrent_bytes)
    assert isinstance(doc, dict)
    info = doc[b"info"]
    return hashlib.sha1(bencode(info)).hexdigest()  # noqa: S324 - BT v1 spec


__all__ = [
    "DEFAULT_PIECE_LENGTH",
    "bencode",
    "bdecode",
    "make_torrent",
    "infohash_v1",
]

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Content addressing: multihash round-trip + dedup (SIG-EVID-002/003/004)."""

from __future__ import annotations

import base64
import hashlib

import pytest

from evidence import digest


def test_multihash_is_base32_lowercase_multibase() -> None:
    value = digest.multihash(b"hello", "sha2-256")
    assert value[0] == "b"  # multibase base32 prefix
    assert value[1:].islower()
    # No uppercase, no padding '=' — RFC 4648 base32 lowercase, unpadded.
    assert "=" not in value


def test_multihash_round_trips_algorithm_and_digest() -> None:
    for algo in ("sha2-256", "sha2-512"):
        value = digest.multihash(b"the-bytes", algo)
        decoded = digest.decode_multihash(value)
        assert decoded.algo == algo
        raw = hashlib.new("sha256" if algo == "sha2-256" else "sha512", b"the-bytes").digest()
        assert decoded.digest == raw


def test_dedup_is_by_digest_identical_bytes_same_multihash() -> None:
    assert digest.multihash(b"same") == digest.multihash(b"same")
    assert digest.multihash(b"same") != digest.multihash(b"different")


def test_interop_digest_must_be_sha2_not_blake3() -> None:
    # SIG-EVID-003: the interop digest is SHA-2; BLAKE3 is fixity-only.
    with pytest.raises(ValueError):
        digest.multihash(b"x", "blake3")


def test_verify_detects_tampering() -> None:
    value = digest.multihash(b"original")
    assert digest.verify(b"original", value)
    assert not digest.verify(b"tampered", value)


def test_blake3_fixity_is_hex_and_stable() -> None:
    a = digest.blake3_hex(b"payload")
    assert a == digest.blake3_hex(b"payload")
    assert all(c in "0123456789abcdef" for c in a)


def test_decoded_multihash_matches_reference_multiformats_encoding() -> None:
    # Cross-check against a hand-built multihash so a third-party multiformats
    # library would decode SIG digests identically (readable without SIG code).
    raw = hashlib.sha256(b"abc").digest()
    manual = bytes([0x12, len(raw)]) + raw
    expected = "b" + base64.b32encode(manual).decode().rstrip("=").lower()
    assert digest.multihash(b"abc", "sha2-256") == expected

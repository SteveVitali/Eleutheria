# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Content addressing for the evidence store (§17.2).

Digests are stored as **multihash**, rendered as **base32-lowercase multibase**
(SIG-EVID-002), so the algorithm is part of the value and can be migrated without
re-reading the bytes. The interop digest is SHA-256 or SHA-512 (SIG-EVID-003);
BLAKE3 is carried additionally, in the OCFL fixity block, for fast local
verification. Deduplication is by digest (SIG-EVID-004).

A multihash is ``<varint algo-code><varint digest-length><digest bytes>``. The
text form is multibase base32 (a leading ``b`` then RFC 4648 base32, lowercase,
unpadded), the encoding IPFS/multiformats renders by default — so a third party
with any multiformats library can decode a SIG digest without SIG's code.
"""

from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass

# multihash algorithm codes (https://github.com/multiformats/multicodec).
_CODES: dict[str, int] = {"sha2-256": 0x12, "sha2-512": 0x13, "blake3": 0x1E}
_NAMES: dict[int, str] = {code: name for name, code in _CODES.items()}

# The interop digest MUST be one of these (SIG-EVID-003). BLAKE3 is fixity-only.
INTEROP_ALGOS: frozenset[str] = frozenset({"sha2-256", "sha2-512"})
DEFAULT_INTEROP_ALGO = "sha2-512"

_MULTIBASE_BASE32 = "b"  # multibase prefix for base32 (RFC 4648, lowercase)


def _uvarint(n: int) -> bytes:
    """Unsigned LEB128 varint, as multihash/multiformats use."""
    if n < 0:
        raise ValueError("varint cannot encode a negative value")
    out = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def _read_uvarint(data: bytes, offset: int) -> tuple[int, int]:
    """Return (value, next_offset)."""
    shift = 0
    result = 0
    while True:
        if offset >= len(data):
            raise ValueError("truncated varint")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return result, offset
        shift += 7


def _b32lower(raw: bytes) -> str:
    """RFC 4648 base32, lowercase, unpadded."""
    return base64.b32encode(raw).decode("ascii").rstrip("=").lower()


def _b32lower_decode(text: str) -> bytes:
    padded = text.upper()
    padding = (-len(padded)) % 8
    return base64.b32decode(padded + ("=" * padding))


def encode_multihash(algo: str, digest: bytes) -> str:
    """Render ``digest`` under ``algo`` as a base32-lowercase multibase multihash."""
    if algo not in _CODES:
        raise ValueError(f"unknown multihash algorithm: {algo!r}")
    raw = _uvarint(_CODES[algo]) + _uvarint(len(digest)) + digest
    return _MULTIBASE_BASE32 + _b32lower(raw)


@dataclass(frozen=True)
class DecodedMultihash:
    """A multihash decoded back into its algorithm and raw digest bytes."""

    algo: str
    digest: bytes


def decode_multihash(value: str) -> DecodedMultihash:
    """Decode a base32-lowercase multibase multihash. The inverse of encode."""
    if not value or value[0] != _MULTIBASE_BASE32:
        raise ValueError("not a base32 multibase value (missing 'b' prefix)")
    raw = _b32lower_decode(value[1:])
    code, offset = _read_uvarint(raw, 0)
    length, offset = _read_uvarint(raw, offset)
    digest = raw[offset:]
    if len(digest) != length:
        raise ValueError(f"multihash length mismatch: header {length}, got {len(digest)}")
    if code not in _NAMES:
        raise ValueError(f"unknown multihash code: {code:#x}")
    return DecodedMultihash(algo=_NAMES[code], digest=digest)


def _raw_digest(data: bytes, algo: str) -> bytes:
    if algo == "sha2-256":
        return hashlib.sha256(data).digest()
    if algo == "sha2-512":
        return hashlib.sha512(data).digest()
    if algo == "blake3":
        return _blake3_digest(data)
    raise ValueError(f"unsupported digest algorithm: {algo!r}")


def _blake3_digest(data: bytes) -> bytes:
    from blake3 import blake3  # lazy: only needed when fixity is computed

    return blake3(data).digest()


def multihash(data: bytes, algo: str = DEFAULT_INTEROP_ALGO) -> str:
    """Content-address ``data`` as a base32-lowercase multihash (SIG-EVID-002)."""
    if algo not in INTEROP_ALGOS:
        raise ValueError(
            f"interop digest must be one of {sorted(INTEROP_ALGOS)} (SIG-EVID-003), not {algo!r}"
        )
    return encode_multihash(algo, _raw_digest(data, algo))


def blake3_hex(data: bytes) -> str:
    """Lowercase-hex BLAKE3 digest for the OCFL fixity block (SIG-EVID-003)."""
    return _blake3_digest(data).hex()


def sha512_hex(data: bytes) -> str:
    """Lowercase-hex SHA-512, the digest OCFL records in its manifest (SIG-EVID-005)."""
    return hashlib.sha512(data).hexdigest()


def verify(data: bytes, expected: str) -> bool:
    """True iff ``data`` reproduces the ``expected`` multihash (fixity check)."""
    decoded = decode_multihash(expected)
    return _raw_digest(data, decoded.algo) == decoded.digest

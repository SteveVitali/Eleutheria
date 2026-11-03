# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Minisign detached signatures (P36.50, R11-K13-TX-10b / D-J3-8 [B-20] = a,
SIG-REL-015, SIG-TRANSP-018).

Release files are signed with the release pipeline's **minisign** key — the
OP-20 key the operator creates and holds in Secret Manager. The signature
proves *integrity*, never approval (SIG-REL-015's custody split: the operator's
OP-25 gate key signs gate records, the pipeline key signs manifests — never
the reverse).

This module is a dependency-free implementation of the minisign format so the
release pipeline signs and verifies without a native toolchain:

* **Ed25519** — the RFC 8032 primitive, pure Python (~60 lines). Signing is
  deterministic: the same key over the same bytes always produces the same
  signature, so a signed release stays a pure function of its inputs
  (SIG-EXPORT-003).
* **The minisign container** — the public-key file, the unencrypted secret-key
  payload and the detached-signature file, byte-compatible with the `minisign`
  tool so a re-user verifies with stock tooling:

      public key  : ``untrusted comment: minisign public key: <KEYNUM-HEX>``
                    + base64(``"Ed"`` + keynum(8) + pubkey(32))
      signature   : ``untrusted comment: signature from minisign secret key``
                    + base64(``"ED"`` + keynum(8) + sig(64))   where
                    sig = Ed25519(keynum || blake2b-512(data))
      + ``trusted comment: <text>``
                    + base64(global_sig(64))                   where
                    global_sig = Ed25519(keynum || sig || trusted_comment)

* **Key custody.** The secret key arrives as an environment variable
  (``SIG_RELEASE_MINISIGN_SECRET``) holding the base64 of the *unencrypted*
  secret payload (``"Ed"`` + keynum(8) + secret(64)), or the raw 64-byte secret
  as base64/hex — never a file the repo carries (HG-09). A password-encrypted
  ``minisign`` ``.key`` file is an operator artefact; the pipeline takes the
  provisioned plaintext payload from the secret manager.
"""

from __future__ import annotations

import base64
import hashlib
import hmac as _hmac
import secrets as _secrets

# --------------------------------------------------------------------------- #
# Ed25519 (RFC 8032) — the minimal pure-Python primitive                       #
# --------------------------------------------------------------------------- #

_Q = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _Q - 2, _Q)) % _Q
_I = pow(2, (_Q - 1) // 4, _Q)
_BY = (4 * pow(5, _Q - 2, _Q)) % _Q
_BX = None


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(_D * y * y + 1, _Q - 2, _Q)
    x = pow(xx, (_Q + 3) // 8, _Q)
    if (x * x - xx) % _Q != 0:
        x = (x * _I) % _Q
    if x % 2 != 0:
        x = _Q - x
    return x


def _edwards(P: tuple[int, int], Q: tuple[int, int]) -> tuple[int, int]:
    x1, y1 = P
    x2, y2 = Q
    denom = pow(1 + _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    denom2 = pow(1 - _D * x1 * x2 * y1 * y2, _Q - 2, _Q)
    return (
        (x1 * y2 + x2 * y1) * denom % _Q,
        (y1 * y2 + x1 * x2) * denom2 % _Q,
    )


def _scalarmult(P: tuple[int, int], e: int) -> tuple[int, int]:
    if e == 0:
        return (0, 1)
    Q = _scalarmult(P, e // 2)
    Q = _edwards(Q, Q)
    if e & 1:
        Q = _edwards(Q, P)
    return Q


def _encodeint(y: int) -> bytes:
    return y.to_bytes(32, "little")


def _encodepoint(P: tuple[int, int]) -> bytes:
    x, y = P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decodeint(s: bytes) -> int:
    return int.from_bytes(s, "little")


def _decodepoint(s: bytes) -> tuple[int, int]:
    y = _decodeint(s) & ((1 << 255) - 1)
    x = _xrecover(y)
    if (x & 1) != ((s[31] >> 7) & 1):
        x = _Q - x
    if not _isoncurve((x, y)):
        raise ValueError("point not on curve")
    return (x, y)


def _isoncurve(P: tuple[int, int]) -> bool:
    x, y = P
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _Q == 0


def _hint(m: bytes) -> int:
    return int.from_bytes(hashlib.sha512(m).digest(), "little")


_B: tuple[int, int] = (_xrecover(_BY), _BY)


def _clamped_scalar(h: bytes) -> int:
    """The RFC 8032 §5.1.5 scalar: sha512(seed)[:32] little-endian, clamped."""
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8  # clear the low 3 bits and the top byte's high bits
    return a | (1 << 254)


def _publickey(seed: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    return _encodepoint(_scalarmult(_B, _clamped_scalar(h)))


def _sign(seed: bytes, msg: bytes) -> bytes:
    h = hashlib.sha512(seed).digest()
    a = _clamped_scalar(h)
    pk = _encodepoint(_scalarmult(_B, a))
    r = _hint(h[32:64] + msg) % _L
    R = _encodepoint(_scalarmult(_B, r))
    S = (r + _hint(R + pk + msg) * a) % _L
    return R + _encodeint(S)


def _verify(pk: bytes, sig: bytes, msg: bytes) -> bool:
    if len(pk) != 32 or len(sig) != 64:
        return False
    try:
        R = _decodepoint(sig[:32])
        A = _decodepoint(pk)
    except ValueError:
        return False
    S = _decodeint(sig[32:])
    if S >= _L:
        return False
    h = _hint(sig[:32] + pk + msg) % _L
    return _encodepoint(_scalarmult(_B, S)) == _encodepoint(_edwards(R, _scalarmult(A, h)))


# --------------------------------------------------------------------------- #
# The minisign container formats                                             #
# --------------------------------------------------------------------------- #

#: Default trusted comment — fixed (never a timestamp) so a signature is a
#: deterministic function of (key, bytes) (SIG-EXPORT-003).
TRUSTED_COMMENT = "SIG release pipeline — SHA256SUMS integrity (D-J3-8)"

SECRET_ENV = "SIG_RELEASE_MINISIGN_SECRET"

_SIG_COMMENT = "untrusted comment: signature from minisign secret key"


class MinisignError(ValueError):
    """A malformed or unverifiable minisign payload — always loud."""


def generate_keypair() -> tuple[str, str]:
    """A throwaway keypair ``(public_text, secret_b64)`` — tests and key minting.

    The secret return is the base64 of the *unencrypted* secret payload
    (``"Ed"`` + keynum + 64-byte secret), the form :func:`sign_detached` and
    ``SIG_RELEASE_MINISIGN_SECRET`` take.
    """
    seed = _secrets.token_bytes(32)
    pk = _publickey(seed)
    keynum = _secrets.token_bytes(8)
    public_text = (
        "untrusted comment: minisign public key: "
        + keynum.hex().upper()
        + "\n"
        + base64.b64encode(b"Ed" + keynum + pk).decode()
        + "\n"
    )
    secret_b64 = base64.b64encode(b"Ed" + keynum + seed + pk).decode()
    return public_text, secret_b64


def parse_public_key(text: str) -> tuple[bytes, bytes]:
    """Parse a minisign public-key document → ``(keynum, pubkey)``."""
    payload: bytes | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("untrusted comment:"):
            continue
        try:
            payload = base64.b64decode(line, validate=True)
        except Exception as exc:  # noqa: BLE001
            raise MinisignError("malformed minisign public key line") from exc
        break
    if payload is None or len(payload) != 42 or payload[:2] != b"Ed":
        raise MinisignError("not a minisign public key (expected 'Ed' + keynum + 32-byte key)")
    return payload[2:10], payload[10:]


def parse_secret_key(text: str) -> tuple[bytes, bytes]:
    """Parse a provisioned secret → ``(keynum, secret64)``.

    Accepts the base64 of the unencrypted payload (``"Ed"`` + keynum + sk64 —
    possibly wrapped in a minisign secret-key document's comment lines), or a
    bare 64-byte secret as base64 or 128-hex chars. Anything else refuses —
    a key we cannot parse is never silently misused.
    """
    body = "".join(
        line.strip()
        for line in text.strip().splitlines()
        if line.strip() and not line.startswith("untrusted comment:")
    )
    raw: bytes | None = None
    try:
        raw = base64.b64decode(body, validate=True)
    except Exception:  # noqa: BLE001
        pass
    if raw is not None and len(raw) == 74 and raw[:2] == b"Ed":
        return raw[2:10], raw[10:]
    if raw is not None and len(raw) == 64:
        # Bare 64-byte secret (seed+pk); the keynum is derived from the public
        # half — a keynum-less payload still produces deterministic signatures.
        seed, pk = raw[:32], raw[32:]
        if _publickey(seed) != pk:
            raise MinisignError("64-byte secret's public half does not match its seed")
        keynum = hashlib.blake2b(pk, digest_size=8).digest()
        return keynum, raw
    try:
        raw = bytes.fromhex(body)
    except ValueError:
        raw = None
    if raw is not None and len(raw) == 64:
        seed, pk = raw[:32], raw[32:]
        if _publickey(seed) != pk:
            raise MinisignError("hex secret's public half does not match its seed")
        keynum = hashlib.blake2b(pk, digest_size=8).digest()
        return keynum, raw
    raise MinisignError(
        "unparseable minisign secret — expected the base64 of the unencrypted "
        "payload ('Ed'+keynum+64-byte secret) or a raw 64-byte secret (b64/hex)"
    )


def public_key_for_secret(secret_b64: str) -> str:
    """The public-key document matching a provisioned secret payload."""
    keynum, sk = parse_secret_key(secret_b64)
    pk = sk[32:]
    return (
        "untrusted comment: minisign public key: "
        + keynum.hex().upper()
        + "\n"
        + base64.b64encode(b"Ed" + keynum + pk).decode()
        + "\n"
    )


def sign_detached(data: bytes, secret_b64: str, *, trusted_comment: str = TRUSTED_COMMENT) -> str:
    """The minisign detached-signature document over ``data``.

    Signs ``keynum || blake2b-512(data)`` (the ``"ED"`` hashed form) plus the
    trusted-comment global signature — byte-compatible with ``minisign -S``.
    """
    keynum, sk = parse_secret_key(secret_b64)
    digest = hashlib.blake2b(data, digest_size=64).digest()
    sig = _sign(sk[:32], keynum + digest)
    global_sig = _sign(sk[:32], keynum + sig + trusted_comment.encode("utf-8"))
    return (
        _SIG_COMMENT
        + "\n"
        + base64.b64encode(b"ED" + keynum + sig).decode()
        + "\n"
        + "trusted comment: "
        + trusted_comment
        + "\n"
        + base64.b64encode(global_sig).decode()
        + "\n"
    )


def _parse_signature(sig_text: str) -> tuple[bytes, bytes, str, bytes]:
    """Split a detached-signature document → (keynum, sig64, trusted, global64)."""
    lines = [line.strip() for line in sig_text.splitlines() if line.strip()]
    if len(lines) < 4 or lines[0] != _SIG_COMMENT:
        raise MinisignError("not a minisign detached-signature document")
    try:
        body = base64.b64decode(lines[1], validate=True)
        global_sig = base64.b64decode(lines[3], validate=True)
    except Exception as exc:  # noqa: BLE001
        raise MinisignError("malformed signature payload") from exc
    if len(body) != 74 or body[:2] != b"ED":
        raise MinisignError("signature is not the hashed 'ED' minisign form")
    if len(global_sig) != 64:
        raise MinisignError("malformed trusted-comment signature")
    if not lines[2].startswith("trusted comment: "):
        raise MinisignError("missing trusted comment line")
    return body[2:10], body[10:], lines[2][len("trusted comment: ") :], global_sig


def verify_detached(data: bytes, sig_text: str, pub_text: str) -> bool:
    """Verify a minisign detached signature — message + trusted-comment sigs.

    Both signatures must verify under the document's own keynum **and** the
    keynum must match the provided public key, so a signature can never pass
    under a key it was not issued by.
    """
    keynum_pub, pk = parse_public_key(pub_text)
    keynum, sig, trusted, global_sig = _parse_signature(sig_text)
    if not _hmac.compare_digest(keynum_pub, keynum):
        return False
    digest = hashlib.blake2b(data, digest_size=64).digest()
    return _verify(pk, sig, keynum + digest) and _verify(
        pk, global_sig, keynum + sig + trusted.encode("utf-8")
    )


__all__ = [
    "MinisignError",
    "SECRET_ENV",
    "TRUSTED_COMMENT",
    "generate_keypair",
    "parse_public_key",
    "parse_secret_key",
    "public_key_for_secret",
    "sign_detached",
    "verify_detached",
]

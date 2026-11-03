# SPDX-License-Identifier: Apache-2.0
"""P36.50 (D-J3-8 [B-20] = a, SIG-REL-015): the pure-Python minisign primitive —
RFC 8032 vectors, the minisign container formats, and the tamper/refusal posture.
"""

from __future__ import annotations

import base64

import pytest

from exports import minisign


def test_rfc8032_vector_1() -> None:
    seed = bytes.fromhex("9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60")
    pk = minisign._publickey(seed)
    assert pk.hex() == ("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a")
    sig = minisign._sign(seed, b"")
    assert sig.hex() == (
        "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555"
        "fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"
    )
    assert minisign._verify(pk, sig, b"")


def test_rfc8032_vector_2() -> None:
    seed = bytes.fromhex("4ccd089b28ff96da9db6c346ec114e0f5b8a319f35aba624da8cf6ed4fb8a6fb")
    pk = minisign._publickey(seed)
    assert pk.hex() == ("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c")
    sig = minisign._sign(seed, bytes([0x72]))
    assert sig.hex() == (
        "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da"
        "085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"
    )


def test_detached_roundtrip_and_tamper() -> None:
    pub, secret = minisign.generate_keypair()
    sig = minisign.sign_detached(b"SHA256SUMS-bytes", secret)
    assert sig.startswith("untrusted comment: signature from minisign secret key\n")
    assert "trusted comment: " in sig
    assert minisign.verify_detached(b"SHA256SUMS-bytes", sig, pub)
    assert minisign.verify_detached(
        b"SHA256SUMS-bytes", sig, minisign.public_key_for_secret(secret)
    )
    assert not minisign.verify_detached(b"SHA256SUMS-bytet", sig, pub)
    pub2, _ = minisign.generate_keypair()
    assert not minisign.verify_detached(b"SHA256SUMS-bytes", sig, pub2)


def test_detached_is_deterministic() -> None:
    pub, secret = minisign.generate_keypair()
    a = minisign.sign_detached(b"data", secret)
    b = minisign.sign_detached(b"data", secret)
    assert a == b and minisign.verify_detached(b"data", a, pub)


def test_keynum_mismatch_refuses() -> None:
    pub, secret = minisign.generate_keypair()
    pub2, secret2 = minisign.generate_keypair()
    # same keynum line of pub, wrong body — must refuse, never accept
    lines1 = pub.strip().splitlines()
    lines2 = pub2.strip().splitlines()
    swapped = lines1[0] + "\n" + lines2[1] + "\n"
    sig = minisign.sign_detached(b"x", secret)
    assert not minisign.verify_detached(b"x", sig, swapped)


def test_parse_secret_forms() -> None:
    pub, secret = minisign.generate_keypair()
    keynum, sk = minisign.parse_secret_key(secret)
    # the minisign-document form also parses (comment line + payload)
    wrapped = "untrusted comment: minisign secret key\n" + secret + "\n"
    assert minisign.parse_secret_key(wrapped) == (keynum, sk)
    with pytest.raises(minisign.MinisignError):
        minisign.parse_secret_key("not-a-key")
    # a bare 64-byte secret (seed+pk) parses via b64 and hex
    k2, sk2 = minisign.parse_secret_key(base64.b64encode(sk).decode())
    assert sk2 == sk
    k3, sk3 = minisign.parse_secret_key(sk.hex())
    assert sk3 == sk


def test_bad_public_key_refuses() -> None:
    with pytest.raises(minisign.MinisignError):
        minisign.parse_public_key("untrusted comment: x\nAAA=\n")

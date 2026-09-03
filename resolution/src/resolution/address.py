# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Tiered address disambiguation keys K1–K4 (SIG-IDENT-013).

Address matching emits four keys of decreasing specificity:

* **K1** — TIGER/Line edge id + side (which side of which street segment).
* **K2** — block GEOID (15-digit).
* **K3** — census-tract GEOID (11-digit).
* **K4** — place GEOID (7-digit).

The load-bearing rule: **K1 and K2 may support identity matching; K3 and K4 are
blocking-only** and MUST NEVER be used as evidence of identity (SIG-IDENT-013). A
tract or a place contains thousands of unrelated bodies — using it as identity
evidence would merge them. K3/K4 exist only to *narrow the candidate set* before a
real key decides. :func:`assert_identity_usable` enforces that at the seam.
"""

from __future__ import annotations

from dataclasses import dataclass

from .geoid import validate_geoid

__all__ = [
    "AddressKeyKind",
    "IDENTITY_KEYS",
    "BLOCKING_ONLY_KEYS",
    "AddressKeys",
    "BlockingOnlyKeyError",
    "assert_identity_usable",
    "build_address_keys",
]

AddressKeyKind = str

K1: AddressKeyKind = "K1"
K2: AddressKeyKind = "K2"
K3: AddressKeyKind = "K3"
K4: AddressKeyKind = "K4"

# K1/K2 MAY support matching; K3/K4 are blocking-only (SIG-IDENT-013).
IDENTITY_KEYS: frozenset[str] = frozenset({K1, K2})
BLOCKING_ONLY_KEYS: frozenset[str] = frozenset({K3, K4})


class BlockingOnlyKeyError(ValueError):
    """Raised when a blocking-only key (K3/K4) is used as identity evidence."""


def assert_identity_usable(kind: AddressKeyKind) -> AddressKeyKind:
    """Return ``kind`` if it may be identity evidence, else raise (SIG-IDENT-013)."""
    if kind in BLOCKING_ONLY_KEYS:
        raise BlockingOnlyKeyError(
            f"address key {kind} is blocking-only and MUST NOT be used as identity "
            "evidence (SIG-IDENT-013); only K1/K2 may support a match"
        )
    if kind not in IDENTITY_KEYS:
        raise ValueError(f"unknown address key kind {kind!r} (SIG-IDENT-013)")
    return kind


@dataclass(frozen=True)
class AddressKeys:
    """The four tiered address keys for one address (SIG-IDENT-013).

    Any key may be ``None`` (an address seen only at coarse resolution has only
    K4). :meth:`identity_keys` returns the K1/K2 subset a matcher may use;
    :meth:`blocking_keys` returns the K3/K4 subset that may block only.
    """

    k1: str | None = None
    k2: str | None = None
    k3: str | None = None
    k4: str | None = None

    def identity_keys(self) -> dict[str, str]:
        """The present K1/K2 keys — the only ones matching may use."""
        return {k: v for k, v in (("K1", self.k1), ("K2", self.k2)) if v is not None}

    def blocking_keys(self) -> dict[str, str]:
        """The present K3/K4 keys — usable to block a candidate set, never to match."""
        return {k: v for k, v in (("K3", self.k3), ("K4", self.k4)) if v is not None}


def build_address_keys(
    *,
    tiger_line_side: str | None = None,
    block_geoid: str | None = None,
    tract_geoid: str | None = None,
    place_geoid: str | None = None,
) -> AddressKeys:
    """Assemble :class:`AddressKeys`, validating each GEOID against its level.

    K1 (TIGER line + side) is a free-form edge id and is stored as given; K2/K3/K4
    are Census GEOIDs and are validated against the ``block`` / ``census_tract`` /
    ``place`` levels respectively (SIG-IDENT-005) so a wrong-width value fails here
    rather than silently mis-blocking.
    """
    if block_geoid is not None:
        validate_geoid(block_geoid, "block")
    if tract_geoid is not None:
        validate_geoid(tract_geoid, "census_tract")
    if place_geoid is not None:
        validate_geoid(place_geoid, "place")
    return AddressKeys(k1=tiger_line_side, k2=block_geoid, k3=tract_geoid, k4=place_geoid)

# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Coordinate sensitivity classification and tier transforms (§43.3, §19.4).

Every asset carries a sensitivity class C1–C5 (SIG-PUB-004) that determines its
published precision, applied at the view layer with full precision retained only
in canonical storage. The class-to-precision matrix and the geospatial tier
transforms both live in ``policy/data/sensitivity.toml`` (data, not code).

Two rules are sharp enough to enforce directly:

* **Residential-parcel demotion (SIG-PUB-005).** An asset whose location
  intersects a residential parcel is automatically demoted to C3.
* **Candidate on a residential parcel (SIG-PUB-013).** A ``CandidateAsset`` whose
  location intersects a residential parcel MUST NOT be published at any
  precision, ever, regardless of corroboration.

Obfuscation offsets MUST be deterministic per asset with a published radius —
random jitter is forbidden (SIG-GEO-009), because repeated observation averages
non-deterministic jitter away.
"""

from __future__ import annotations

import hashlib
import math
from decimal import ROUND_DOWN, Decimal
from enum import StrEnum
from typing import Any

from ._data import load_table


class SensitivityClass(StrEnum):
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"
    C4 = "C4"
    C5 = "C5"


def _classes() -> dict[str, Any]:
    return load_table("sensitivity")["classes"]


def published_precision(cls: SensitivityClass) -> str:
    """The published-precision rule for a sensitivity class (§43.3)."""
    return str(_classes()[cls.value]["published"])


def geo_tier_for(cls: SensitivityClass) -> int:
    """The geospatial publication tier (0–3, §19.4) for a sensitivity class."""
    return int(_classes()[cls.value]["geo_tier"])


def demote_for_residential_parcel(
    cls: SensitivityClass, intersects_residential: bool
) -> SensitivityClass:
    """Automatic demotion to C3 on residential-parcel intersection (SIG-PUB-005)."""
    if intersects_residential:
        return SensitivityClass.C3
    return cls


def candidate_publishable(intersects_residential: bool) -> bool:
    """Whether a candidate asset may ever be published (SIG-PUB-011/013).

    A ``CandidateAsset`` never appears in a public device layer at all
    (SIG-PUB-011); this returns whether *promotion* could ever publish it. A
    candidate intersecting a residential parcel can never be published at any
    precision (SIG-PUB-013), so the answer is ``False``.
    """
    return not intersects_residential


def requires_human_review(provenance_is_leak: bool) -> bool:
    """Leak-provenance veto (SIG-PUB-005): leaked sensor locations need review."""
    return provenance_is_leak


def deterministic_offset(asset_id: str, radius_m: float) -> tuple[float, float]:
    """A stable, per-asset obfuscation offset within ``radius_m`` (SIG-GEO-009).

    The offset is a pure function of ``asset_id`` and the published radius — no
    randomness — so repeated observation cannot average it away. Returns
    ``(d_north_m, d_east_m)`` in metres.
    """
    digest = hashlib.sha256(f"{asset_id}:{radius_m}".encode()).digest()
    # Two independent unit fractions from disjoint bytes of the digest.
    frac_angle = int.from_bytes(digest[0:8], "big") / 2**64
    frac_radius = int.from_bytes(digest[8:16], "big") / 2**64
    angle = frac_angle * 2 * math.pi
    # sqrt keeps the offset uniformly distributed over the disc, still bounded.
    r = radius_m * (frac_radius**0.5)
    return (r * math.cos(angle), r * math.sin(angle))


def _truncate(value: float, decimal_places: int) -> float:
    """Truncate ``value`` toward zero to ``decimal_places`` — stable and idempotent.

    Uses :class:`~decimal.Decimal` so repeated application is a fixed point;
    naive ``int(value * 10**dp) / 10**dp`` drifts on values like 8.125 because
    of binary floating-point representation.
    """
    quantum = Decimal(1).scaleb(-decimal_places)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_DOWN))


def apply_tier(lat: float, lon: float, tier: int) -> tuple[float, float] | None:
    """Apply a geospatial tier transform (§19.4) to a coordinate.

    * tier 0 — full precision.
    * tier 1 — truncate to the published number of decimal places.
    * tier 2 — snap to the published binning grid (deterministic, radius known).
    * tier 3 — no geometry published (returns ``None``); jurisdiction only.
    """
    tiers = load_table("sensitivity")["tiers"]
    spec = tiers[str(tier)]
    transform = spec["transform"]
    if transform == "full_precision":
        return (lat, lon)
    if transform == "truncate":
        dp = int(spec["decimal_places"])
        return (_truncate(lat, dp), _truncate(lon, dp))
    if transform == "grid_bin":
        # Deterministic snap to a grid whose spacing derives from the published
        # radius; ~111_320 m per degree of latitude is the standard approximation.
        step_deg = int(spec["resolution_m"]) / 111_320.0
        return (round(lat / step_deg) * step_deg, round(lon / step_deg) * step_deg)
    if transform == "jurisdiction_only":
        return None
    raise ValueError(f"unknown tier transform {transform!r}")

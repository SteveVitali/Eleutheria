# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The declared residential-parcel screen (P35.66; SIG-PUB-004/005/013).

This module is the **flag producer** the residential demotion rides: at emit,
a candidate/asset row's device geography is checked against the *declared*
residential-parcel signal (``policy/data/residential_parcels.toml``) and the
verdict is stamped on the emitted record — ``parcel_screen`` plus
``residential_parcel_flag`` and the signal stamp — so the demotion
(:func:`policy.sensitivity.demote_for_residential_parcel`) and the publish
refusal (:func:`policy.sensitivity.assert_public_layer_subject`) read a
recorded fact, never a default.

The defining standard (§3.1) makes the verdict three-valued — a row whose
geography carries **no declared signal coverage** records ``unscreened``;
``unscreened`` and ``clear`` ("screened, no parcel intersects") are distinct
recorded states and are never conflated into a silent "clean". The signal
itself is declared data (id + version + provenance + coverage polygons +
parcel polygons), and the emit stamp names it (`<signal_id>@<version>`), so
"what input, when" is always answerable from the emitted record.

What the committed signal holds is honest: the parcel dataset acquisition is a
registry row (the contract's P35.6 path), not this row — so the committed
layer declares the signal, its coverage boundary (none yet), and zero parcel
geometry. Every emitted row therefore records ``unscreened`` until the
acquisition lands — a recorded coverage gap, never a fabricated clearance.
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from importlib.resources import files
from pathlib import Path
from typing import Any


class ParcelScreenVerdict(StrEnum):
    """The recorded outcome of the declared-parcel screen (the emit stamp)."""

    #: The point intersects a declared residential parcel → demote (C3) + flag.
    INTERSECTS = "intersects"
    #: The signal covers this geography and no parcel intersects.
    CLEAR = "clear"
    #: No declared signal coverage for this geography — NOT "clean".
    UNSCREENED = "unscreened"


#: Every legal ``parcel_screen`` stamp — emit-path validation fails closed on
#: a value outside the closed vocabulary.
PARCEL_SCREEN_VERDICTS = frozenset(v.value for v in ParcelScreenVerdict)


class ParcelSignalError(ValueError):
    """A malformed declared parcel signal — a config defect, never a verdict."""


@dataclass(frozen=True)
class ParcelPolygon:
    """One declared residential parcel: an id + its exterior ring."""

    parcel_id: str
    #: ``(lon, lat)`` vertices, GeoJSON order, closed (first == last).
    ring: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class ResidentialParcelSignal:
    """The declared parcel-signal a screen ran against (the stamp's payload)."""

    signal_id: str
    version: str
    provenance: str
    #: Declared coverage regions — the geographies the signal is claimed to
    #: cover — as closed ``(lon, lat)`` rings (GeoJSON order). An empty set
    #: means "no coverage is held": every point screens ``unscreened``.
    coverage: tuple[tuple[tuple[float, float], ...], ...]
    parcels: tuple[ParcelPolygon, ...]

    @property
    def stamp(self) -> str:
        """The emitted ``parcel_screen_signal`` value (``<id>@<version>``)."""
        return f"{self.signal_id}@{self.version}"

    @classmethod
    def from_doc(
        cls, doc: Mapping[str, Any], *, source: str = "<inline>"
    ) -> ResidentialParcelSignal:
        """Parse + validate a signal document; a violation is a config defect."""
        violations = signal_doc_violations(doc)
        if violations:
            raise ParcelSignalError(
                f"{source}: malformed declared parcel signal: " + "; ".join(violations)
            )
        return cls(
            signal_id=str(doc["signal_id"]).strip(),
            version=str(doc["version"]).strip(),
            provenance=str(doc["provenance"]).strip(),
            coverage=tuple(
                _ring(r, f"coverage[{i}]") for i, r in enumerate(doc.get("coverage") or [])
            ),
            parcels=tuple(
                ParcelPolygon(
                    parcel_id=str(p["id"]).strip(),
                    ring=_ring(p["ring"], f"parcel {p.get('id')!r}"),
                )
                for p in doc.get("parcels") or []
            ),
        )

    @classmethod
    def load(cls, path: str | Path) -> ResidentialParcelSignal:
        """Load a declared signal from a TOML file (the fixture/test seam)."""
        with Path(path).open("rb") as fh:
            return cls.from_doc(tomllib.load(fh), source=str(path))


def _ring(raw: Any, label: str) -> tuple[tuple[float, float], ...]:
    """One closed ``(lon, lat)`` ring; caller-validated by ``from_doc``."""
    return tuple((float(v[0]), float(v[1])) for v in raw)


def _ring_violations(raw: Any, label: str) -> list[str]:
    """A ring is a closed GeoJSON-order ``[[lon, lat], …]`` list of ≥4 points."""
    problems: list[str] = []
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)) or len(raw) < 4:
        return [f"{label}: a ring needs ≥4 closed positions"]
    for i, pos in enumerate(raw):
        ok = (
            isinstance(pos, Sequence)
            and not isinstance(pos, (str, bytes))
            and len(pos) == 2
            and isinstance(pos[0], (int, float))
            and isinstance(pos[1], (int, float))
            and -180.0 <= float(pos[0]) <= 180.0
            and -90.0 <= float(pos[1]) <= 90.0
        )
        if not ok:
            problems.append(f"{label}[{i}]: not an in-range [lon, lat] position")
    if not problems and (float(raw[0][0]), float(raw[0][1])) != (
        float(raw[-1][0]),
        float(raw[-1][1]),
    ):
        problems.append(f"{label}: ring is not closed (first != last position)")
    return problems


def signal_doc_violations(doc: Mapping[str, Any]) -> list[str]:
    """Integrity check over a declared signal document (``[]`` = clean).

    Run at ``sig-connectors validate`` (the committed file) AND at signal load
    (any injected document): a malformed ring, an out-of-range position, or a
    parcel whose centroid sits outside every declared coverage region is a
    configuration defect, never a screening outcome.
    """
    problems: list[str] = []
    for key in ("signal_id", "version", "provenance"):
        if not str(doc.get(key) or "").strip():
            problems.append(f"missing/empty {key!r}")
    coverage_raw = doc.get("coverage") or []
    parcels_raw = doc.get("parcels") or []
    if not isinstance(coverage_raw, list) or not isinstance(parcels_raw, list):
        return problems + ["coverage/parcels must be arrays"]
    for i, ring in enumerate(coverage_raw):
        problems.extend(_ring_violations(ring, f"coverage[{i}]"))
    coverage = tuple(
        tuple((float(v[0]), float(v[1])) for v in ring)
        for i, ring in enumerate(coverage_raw)
        if not _ring_violations(ring, f"coverage[{i}]")
    )
    for i, parcel in enumerate(parcels_raw):
        label = f"parcels[{i}]"
        if not isinstance(parcel, Mapping):
            problems.append(f"{label}: a parcel is a table with id + ring")
            continue
        if not str(parcel.get("id") or "").strip():
            problems.append(f"{label}: missing/empty id")
        ring_problems = _ring_violations(parcel.get("ring"), f"{label}.ring")
        problems.extend(ring_problems)
        if ring_problems or not coverage:
            continue
        ring = tuple((float(v[0]), float(v[1])) for v in parcel["ring"])
        clon = sum(p[0] for p in ring[:-1]) / (len(ring) - 1)
        clat = sum(p[1] for p in ring[:-1]) / (len(ring) - 1)
        if not any(_point_in_ring(clon, clat, region) for region in coverage):
            problems.append(
                f"{label}: parcel centroid sits outside every declared coverage "
                "region — a parcel the signal claims to hold in geography it "
                "does not cover is a contradiction, not a coverage extension"
            )
    return problems


@cache
def declared_parcel_signal() -> ResidentialParcelSignal:
    """The committed declared signal — ``policy/data/residential_parcels.toml``.

    Fail-closed: a malformed committed signal raises :class:`ParcelSignalError`
    at load, so a broken declared input stops the emit rather than minting a
    record stamped with an unchecked verdict.
    """
    resource = files("policy").joinpath("data", "residential_parcels.toml")
    with resource.open("rb") as fh:
        return ResidentialParcelSignal.from_doc(tomllib.load(fh), source=str(resource))


def _point_in_ring(lon: float, lat: float, ring: Sequence[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon over a closed ``(lon, lat)`` ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > lat) != (yj > lat):
            x_at_lat = xi + (lat - yi) * (xj - xi) / (yj - yi)
            if lon < x_at_lat:
                inside = not inside
        j = i
    return inside


def screen_point(
    lat: float,
    lon: float,
    *,
    signal: ResidentialParcelSignal | None = None,
) -> ParcelScreenVerdict:
    """The recorded verdict for one device point against the declared signal.

    * ``intersects`` — the point falls inside a declared parcel ring.
    * ``clear`` — the point falls inside a declared coverage region and outside
      every parcel ("screened, no intersection" — a real clearance).
    * ``unscreened`` — no declared coverage reaches the point. Deliberately
      NOT "clean": a geography the signal does not cover records the gap.
    """
    sig = signal if signal is not None else declared_parcel_signal()
    if not sig.coverage or not any(_point_in_ring(lon, lat, region) for region in sig.coverage):
        return ParcelScreenVerdict.UNSCREENED
    if any(_point_in_ring(lon, lat, parcel.ring) for parcel in sig.parcels):
        return ParcelScreenVerdict.INTERSECTS
    return ParcelScreenVerdict.CLEAR


def screen_geometry_descriptor(
    descriptor: Mapping[str, Any] | None,
    *,
    signal: ResidentialParcelSignal | None = None,
) -> ParcelScreenVerdict:
    """The verdict for a connector geometry descriptor (OSM ``{kind, …}``).

    A ``point``/``center`` descriptor is screened on its coordinate; ``bounds``
    and every other (or absent) shape records ``unscreened`` — the declared
    check is a point-in-parcel test, and a box/polygon claim of "no
    intersection" would assert a screen that did not run.
    """
    if isinstance(descriptor, Mapping) and descriptor.get("kind") in ("point", "center"):
        try:
            lat = float(descriptor["lat"])
            lon = float(descriptor["lon"])
        except (KeyError, TypeError, ValueError):
            return ParcelScreenVerdict.UNSCREENED
        return screen_point(lat, lon, signal=signal)
    return ParcelScreenVerdict.UNSCREENED


def parcel_fields(
    verdict: ParcelScreenVerdict,
    *,
    signal: ResidentialParcelSignal | None = None,
) -> dict[str, Any]:
    """The emitted-record stamp for a screened verdict (uniform field set)."""
    sig = signal if signal is not None else declared_parcel_signal()
    return {
        "residential_parcel_flag": verdict is ParcelScreenVerdict.INTERSECTS,
        "parcel_screen": verdict.value,
        "parcel_screen_signal": sig.stamp,
    }


__all__ = [
    "PARCEL_SCREEN_VERDICTS",
    "ParcelPolygon",
    "ParcelScreenVerdict",
    "ParcelSignalError",
    "ResidentialParcelSignal",
    "declared_parcel_signal",
    "parcel_fields",
    "screen_geometry_descriptor",
    "screen_point",
    "signal_doc_violations",
]

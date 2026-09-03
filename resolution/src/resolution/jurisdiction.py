# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Jurisdiction registry: a first-class jurisdiction with an overlapping
self-referential hierarchy, pluggable national code systems, and
**temporally-versioned** geometry (§11.1, SIG-ONTO-010/011).

A jurisdiction is not a string on some other row: a city, the city government, and
the city police department are three different things, and a device inside city
limits may be operated by the county, the state, or a university. This registry
carries the identity substrate — the type, the (possibly multiple) parents, the
set of code-system identifiers, and the boundary as it stood on a given date.
Annexations are common, so the containing jurisdiction of a point on the date it
was observed can differ from today's — hence :meth:`JurisdictionRecord.boundary_as_of`.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date

from .geoid import validate_geoid
from .identity import Identifier

# Identifier schemes whose values are Census GEOIDs and MUST pass the fixed-width /
# explicit-level check (SIG-IDENT-005).
_GEOID_SCHEMES = frozenset({"us.census.geoid"})


@dataclass(frozen=True)
class BoundaryVersion:
    """One temporal version of a jurisdiction's boundary (SIG-ONTO-011).

    ``valid_from`` / ``valid_to`` are the half-open interval ``[from, to)`` the
    geometry was in force; ``None`` means open (unknown-start / still-current). The
    geometry is a MultiPolygon in EWKT/WKT, SRID 4326.
    """

    geometry: str
    valid_from: date | None = None
    valid_to: date | None = None
    source: str | None = None

    def contains(self, as_of: date) -> bool:
        """Whether this version was in force on ``as_of`` (half-open ``[from, to)``)."""
        if self.valid_from is not None and as_of < self.valid_from:
            return False
        return not (self.valid_to is not None and as_of >= self.valid_to)


@dataclass(frozen=True)
class JurisdictionRecord:
    """A jurisdiction's identity surface (§11.1, SIG-ONTO-010).

    ``parents`` is a tuple because hierarchies **overlap** — a city may span two
    counties, so multiple parents are permitted (SIG-ONTO-010). ``level`` is
    required and disambiguates the (otherwise ambiguous) GEOIDs (SIG-IDENT-005).
    """

    jurisdiction_type: str
    level: str
    entity_id: str | None = None
    parents: tuple[str, ...] = ()
    identifiers: frozenset[Identifier] = field(default_factory=frozenset)
    names: tuple[tuple[str, str], ...] = ()  # (name, BCP-47 lang)
    boundaries: tuple[BoundaryVersion, ...] = ()
    boundary_source: str | None = None
    valid_from: date | None = None
    valid_to: date | None = None

    def __post_init__(self) -> None:
        if not self.jurisdiction_type:
            raise ValueError("jurisdiction_type is required (SIG-ONTO-010)")
        if not self.level:
            raise ValueError("every jurisdiction row MUST carry an explicit level (SIG-IDENT-005)")
        # Every GEOID identifier is validated against the declared level.
        for ident in self.identifiers:
            if ident.scheme in _GEOID_SCHEMES:
                validate_geoid(ident.value, self.level)

    def boundary_as_of(self, as_of: date) -> BoundaryVersion | None:
        """The boundary version in force on ``as_of``, or ``None`` if none (SIG-ONTO-011).

        This is why boundaries are versioned: ``boundary_as_of(observation_date)``
        can return a different polygon from ``boundary_as_of(today)`` across an
        annexation, so a point's containing jurisdiction is evaluated against the
        geometry of the observation date, not of today.
        """
        for version in self.boundaries:
            if version.contains(as_of):
                return version
        return None


def build_jurisdiction(
    *,
    jurisdiction_type: str,
    level: str,
    identifiers: Iterable[Identifier | tuple[str, str]] = (),
    parents: Iterable[str] = (),
    names: Iterable[tuple[str, str]] = (),
    boundaries: Iterable[BoundaryVersion] = (),
    boundary_source: str | None = None,
    entity_id: str | None = None,
    valid_from: date | None = None,
    valid_to: date | None = None,
) -> JurisdictionRecord:
    """Assemble a :class:`JurisdictionRecord`, coercing identifier pairs to a set."""
    idents = frozenset(i if isinstance(i, Identifier) else Identifier(*i) for i in identifiers)
    return JurisdictionRecord(
        jurisdiction_type=jurisdiction_type,
        level=level,
        entity_id=entity_id,
        parents=tuple(parents),
        identifiers=idents,
        names=tuple(names),
        boundaries=tuple(boundaries),
        boundary_source=boundary_source,
        valid_from=valid_from,
        valid_to=valid_to,
    )

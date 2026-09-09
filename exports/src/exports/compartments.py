# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Placing export rows into licence compartments, and the export-time licence gate
(§38.2, §42.4).

This is the export-time realisation of the Part VIII licence gate + ODbL separation
invariant. The rules the spec draws:

* **The compartment is keyed on the rights record (SIG-LIC-004a), not hard-coded.**
  A table's governing licence is *computed* from its constituent sources' rights via
  :func:`policy.licensing.compute_export_license`; the compartment is then the one in
  ``policy/data/licenses.toml`` that declares that licence. Adding a source under a new
  share-alike licence is a data row there, never a change here.
* **An incompatible mix fails the build (SIG-EXPORT-004 / SIG-LIC-010).** If a single
  table would combine mutually-incompatible regimes — an ODbL source and a CC-BY
  source, two different share-alike regimes, or a silently-travelling share-alike
  upstream folded into a permissive export (SIG-LIC-009a) — the licence computation
  raises and the build stops. A merged file would silently force the whole export
  share-alike; that must be loud, not silent.
* **ODbL ships separately from CC-BY (SIG-EXPORT-005).** Because each table computes to
  exactly one licence and each licence maps to one compartment file, OSM-derived assets
  (ODbL-1.0) and the SIG-original graph (CC-BY-4.0) land in physically different files
  by construction — never merged.
* **Every row carries per-row rights provenance (SIG-EXPORT-006 / SIG-LIC-011).**
  :func:`enrich_rows` stamps each row with the downstream attribution/provenance
  obligation so a consumer can determine the licence of any individual fact without
  re-deriving the chain, rather than being forced to assume the strictest.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from policy.licensing import (
    LicenseIncompatibilityError,
    compartments,
    compute_export_license,
    downstream_obligations,
)
from policy.licensing import (
    most_permissive_license as _most_permissive_license,
)
from policy.rights import RightsRecord

#: The per-row provenance key stamped onto every exported row (SIG-EXPORT-006). Named
#: with a leading underscore so it cannot collide with a domain column.
RIGHTS_KEY = "_rights"


class UnknownSourceError(Exception):
    """A row cites a ``source_id`` with no rights record — the gate fails closed."""


@dataclass(frozen=True)
class ExportRow:
    """One row of an export table, tagged with the source whose rights govern it."""

    source_id: str
    data: Mapping[str, Any]


@dataclass(frozen=True)
class ExportTable:
    """A named set of rows destined for one export file.

    ``kind`` selects the downstream wrapper: ``tabular`` rows ship inside a Frictionless
    Data Package, ``geo`` rows additionally get a GeoJSON/PMTiles geometry form, and
    ``evidence`` rows ship as an RO-Crate (§38.1, SIG-EXPORT-002). ``compartment`` may
    be declared (the OSM connector already stamps ``osm_physical`` on its ODbL rows); it
    is then *validated* against the computed licence rather than trusted.
    """

    name: str
    rows: tuple[ExportRow, ...]
    kind: str = "tabular"
    compartment: str | None = None
    #: Row keys carrying geometry, for the GeoJSON/PMTiles form of a ``geo`` table.
    geometry_key: str = "geometry"

    def source_ids(self) -> list[str]:
        """The distinct source ids present, in first-seen order (determinism)."""
        seen: dict[str, None] = {}
        for row in self.rows:
            seen.setdefault(row.source_id, None)
        return list(seen)


@dataclass(frozen=True)
class PlacedTable:
    """A table resolved to its computed licence and compartment (SIG-LIC-004a)."""

    table: ExportTable
    compartment: str
    license: str
    rights: tuple[RightsRecord, ...] = field(default_factory=tuple)


def rights_index(records: Iterable[RightsRecord]) -> dict[str, RightsRecord]:
    """Index rights records by ``source_id`` for placement lookups."""
    index: dict[str, RightsRecord] = {}
    for record in records:
        index[record.source_id] = record
    return index


def table_rights(table: ExportTable, index: Mapping[str, RightsRecord]) -> list[RightsRecord]:
    """The rights records governing ``table``, one per distinct source (fails closed)."""
    out: list[RightsRecord] = []
    for source_id in table.source_ids():
        record = index.get(source_id)
        if record is None:
            raise UnknownSourceError(
                f"table {table.name!r} cites source {source_id!r} with no rights record; "
                "the export gate fails closed (SIG-LIC-004)."
            )
        out.append(record)
    return out


def compartment_for_license(
    license_id: str, prefer: str | None, registry: Mapping[str, Any] | None
) -> str:
    """The compartment file a computed ``license_id`` lands in.

    Prefers a caller-declared compartment when it genuinely declares that licence
    (so the OSM connector's ``osm_physical`` stamp is honoured), else the first
    compartment in ``licenses.toml`` declaring the licence, by sorted name for
    determinism. A licence with no compartment is a data gap, raised loudly.
    """
    comps = compartments() if registry is None else dict(registry["compartments"])
    if prefer is not None:
        declared = comps.get(prefer)
        if declared is None:
            raise LicenseIncompatibilityError(
                f"declared compartment {prefer!r} is not in the compartment registry."
            )
        if declared["license"] != license_id:
            raise LicenseIncompatibilityError(
                f"table declares compartment {prefer!r} (licence {declared['license']!r}) "
                f"but its rights compute to {license_id!r} (SIG-EXPORT-005)."
            )
        return prefer
    matches = sorted(name for name, c in comps.items() if c["license"] == license_id)
    if not matches:
        raise LicenseIncompatibilityError(
            f"computed licence {license_id!r} has no export compartment in licenses.toml "
            "(add a [compartments.*] data row — SIG-LIC-004a)."
        )
    return matches[0]


def place_table(
    table: ExportTable,
    index: Mapping[str, RightsRecord],
    registry: Mapping[str, Any] | None = None,
) -> PlacedTable:
    """Resolve one table to its computed licence and compartment.

    Raises :class:`policy.licensing.LicenseIncompatibilityError` (or
    :class:`policy.licensing.ExportGateClosed`) if the table's sources cannot be
    combined into a single export licence — the SIG-EXPORT-004 / SIG-LIC-010 build gate.
    """
    rights = table_rights(table, index)
    license_id = compute_export_license(rights, registry)
    compartment = compartment_for_license(license_id, table.compartment, registry)
    return PlacedTable(
        table=table, compartment=compartment, license=license_id, rights=tuple(rights)
    )


def place_tables(
    tables: Iterable[ExportTable],
    index: Mapping[str, RightsRecord],
    registry: Mapping[str, Any] | None = None,
) -> list[PlacedTable]:
    """Place every table, computing its licence (fails the build on any incompatible mix)."""
    return [place_table(table, index, registry) for table in tables]


def assert_separated(placed: Sequence[PlacedTable]) -> None:
    """Assert the ODbL/CC-BY separation invariant holds across placed tables (SIG-EXPORT-005).

    Two tables in the *same* compartment file must share the same licence, and a
    share-alike licence must never co-occur in a compartment with a different licence.
    This is belt-and-suspenders over :func:`place_table` (which already computes one
    licence per file); it catches a mis-declared compartment reused across licences.
    """
    by_compartment: dict[str, set[str]] = {}
    for pt in placed:
        by_compartment.setdefault(pt.compartment, set()).add(pt.license)
    for compartment, licenses in sorted(by_compartment.items()):
        if len(licenses) > 1:
            raise LicenseIncompatibilityError(
                f"compartment {compartment!r} would merge licences {sorted(licenses)} into "
                "one file (SIG-EXPORT-005); each licence regime needs its own compartment."
            )


def row_rights(record: RightsRecord, registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The per-row rights-provenance block (SIG-EXPORT-006 / SIG-LIC-011).

    Delegates to :func:`policy.licensing.downstream_obligations` — the *same* function
    the read API uses to attach attribution to a collection (SIG-API-004) — so the
    export and the API pass identical obligations downstream.
    """
    return downstream_obligations(record, registry)


def enrich_rows(
    table: ExportTable,
    index: Mapping[str, RightsRecord],
    registry: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Materialise ``table``'s rows with their per-row rights provenance stamped in.

    Every returned row carries the domain payload plus a :data:`RIGHTS_KEY` block; a
    row can never leave the build without its provenance (SIG-EXPORT-006).
    """
    cache: dict[str, dict[str, Any]] = {}
    out: list[dict[str, Any]] = []
    for row in table.rows:
        record = index.get(row.source_id)
        if record is None:
            raise UnknownSourceError(
                f"row cites source {row.source_id!r} with no rights record (SIG-LIC-004)."
            )
        if row.source_id not in cache:
            cache[row.source_id] = row_rights(record, registry)
        merged = dict(row.data)
        merged[RIGHTS_KEY] = cache[row.source_id]
        out.append(merged)
    return out


def most_permissive_license(
    records: Iterable[RightsRecord], registry: Mapping[str, Any] | None = None
) -> str:
    """The most permissive licence a set of constituents may all be published under.

    Used by the crosswalk export (SIG-EXPORT-007). Thin pass-through to
    :func:`policy.licensing.most_permissive_license` so all licence math stays in the
    policy package; re-exported here for the export layer's convenience.
    """
    return _most_permissive_license(records, registry)


__all__ = [
    "RIGHTS_KEY",
    "UnknownSourceError",
    "ExportRow",
    "ExportTable",
    "PlacedTable",
    "rights_index",
    "table_rights",
    "compartment_for_license",
    "place_table",
    "place_tables",
    "assert_separated",
    "row_rights",
    "enrich_rows",
    "most_permissive_license",
]
